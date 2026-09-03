"""세션 엔드포인트. FR-023·FR-028~FR-043·FR-061. contracts/rest-api.md §세션.

**명령은 REST, 관찰은 WebSocket.** 이 라우터가 명령을 받아 상태 기계에 적용하고 즉시
반환한다. 실제 실행은 러너 태스크가 담당한다 (research R1).
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from itb.api.errors import ErrorCode, bad_request, conflict, not_found
from itb.api.state import AppState, get_state
from itb.domain.step import Author, Step
from itb.domain.test_case import AuthoringMode, Test
from itb.execution.artifacts import ArtifactCollector
from itb.execution.runner import ReplayEngine, RunnerTask
from itb.execution.session import BrowserSession, SessionError
from itb.execution.session_loss import SessionLossWatcher
from itb.execution.state_machine import (
    TERMINAL_STATES,
    Command,
    InvalidTransitionError,
    SessionState,
    is_manipulation_phase,
    state_label,
)
from itb.execution.step_executor import StepExecutor
from itb.mirror.tab_switch import MirrorController
from itb.recording.recorder import Recorder
from itb.secrets.keys import KeyMissingError, KeyStoreError, load_private, load_public
from itb.secrets.resolver import VariableResolver
from itb.secrets.store import SecretStore
from itb.storage.repository import ProjectError, ProjectRepository

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

State = Annotated[AppState, Depends(get_state)]

STEP_ADAPTER = TypeAdapter(Step)


# ─── 세션 작업 상태 (메모리 전용) ───────────────────────────────────────────


@dataclass(slots=True)
class SessionWork:
    """세션 하나의 작업 중 Step 목록과 리코더.

    Step 목록을 세션이 소유한다 — 저장 시점에 `Test` 로 커밋된다 (data-model §8).
    """

    session: BrowserSession
    recorder: Recorder
    steps: list[Step] = field(default_factory=list)
    current_step_index: int = 0
    start_url: str = ""
    authoring_mode: AuthoringMode = AuthoringMode.RECORD
    ai_instruction: str | None = None
    saved_test_id: str | None = None

    # ─── 재실행 (US2) ──────────────────────────────────────────────────────
    mirror: MirrorController | None = None
    """미러는 **모든 활성 상태**에서 돈다 (FR-047d). 그래서 모드와 무관하게 붙인다."""

    loss_watcher: SessionLossWatcher | None = None
    engine: ReplayEngine | None = None
    runner: RunnerTask | None = None


_WORK: dict[str, SessionWork] = {}
"""세션 ID → 작업 상태. 앱 수명 동안만 유지된다."""


def work_of(session_id: str) -> SessionWork:
    w = _WORK.get(session_id)
    if w is None:
        raise not_found(ErrorCode.SESSION_NOT_FOUND, f"세션을 찾을 수 없습니다: {session_id}")
    return w


def mirror_of(session_id: str) -> MirrorController | None:
    """미러 제어기. 탭 라우터가 표시 탭을 바꿀 때 쓴다 (FR-030f).

    미러가 없어도(시작하지 못한 경우) 탭 전환 요청 자체는 성공해야 한다 — 미러 실패가
    사용자 조작을 막으면 안 된다 (FR-047b).
    """
    w = _WORK.get(session_id)
    return w.mirror if w is not None else None


def require_paused(w: SessionWork) -> None:
    """FR-035a — 편집 명령은 일시정지에서만 받는다."""
    if w.session.state is not SessionState.PAUSED:
        raise conflict(
            ErrorCode.NOT_PAUSED,
            f"현재 상태가 '{state_label(w.session.state)}' 이므로 Step 을 편집할 수 없습니다. "
            "먼저 일시정지하세요.",
            state=w.session.state.value,
        )


# ─── 요청·응답 모델 ─────────────────────────────────────────────────────────


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["record", "replay", "ai"]
    test_id: str | None = Field(default=None, pattern=r"^TC-\d{3}$")
    start_url: str | None = Field(default=None, pattern=r"^https?://", max_length=2000)
    ai_instruction: str | None = Field(default=None, max_length=8000)


class SessionView(BaseModel):
    """WebSocket 재연결 시 전체 상태 동기화에 쓴다 (contracts/websocket.md)."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    state: SessionState
    state_label: str
    test_id: str | None
    current_step_index: int
    steps: list[Step]
    tabs_open: int
    active_tab_index: int
    mirrored_tab_index: int
    edit_warnings: list[str]
    recorder_warnings: list[str]
    allowed_commands: list[str]


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class RunFromRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(ge=0)


def view_of(w: SessionWork) -> SessionView:
    from itb.execution.state_machine import allowed_commands

    return SessionView(
        session_id=w.session.session_id,
        state=w.session.state,
        state_label=state_label(w.session.state),
        test_id=w.saved_test_id or w.session.test_id,
        current_step_index=w.current_step_index,
        steps=w.steps,
        tabs_open=len(w.session.open_tabs()),
        active_tab_index=w.session.active_tab_index,
        mirrored_tab_index=w.session.mirrored_tab_index,
        edit_warnings=list(w.session.edit_warnings),
        recorder_warnings=list(w.recorder.warnings),
        allowed_commands=[c.value for c in allowed_commands(w.session.state)],
    )


# ─── 생성 ───────────────────────────────────────────────────────────────────


def _secret_store(repo: ProjectRepository) -> SecretStore:
    return SecretStore(repo.paths.secrets_file)


@router.post("", status_code=201)
async def create_session(body: CreateSessionRequest, state: State) -> SessionView:
    repo = state.require_repository()
    project = repo.read_project()

    existing_test: Test | None = None
    if body.mode == "replay":
        if body.test_id is None:
            raise bad_request(
                ErrorCode.DEFINITION_INVALID, "replay 모드는 test_id 가 필요합니다."
            )
        try:
            existing_test = repo.read_test(body.test_id)
        except ProjectError as exc:
            raise not_found(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc

    if body.mode == "ai" and not body.ai_instruction:
        raise bad_request(
            ErrorCode.DEFINITION_INVALID, "ai 모드는 자연어 지시문이 필요합니다."
        )

    if body.test_id and state.sessions.active_session_for_test(body.test_id):
        raise conflict(
            ErrorCode.SESSION_ALREADY_ACTIVE,
            f"{body.test_id} 에 이미 실행 중인 세션이 있습니다. 먼저 중지하세요.",
        )

    start_url = (
        existing_test.start_url
        if existing_test
        else (body.start_url or project.default_start_url)
    )

    try:
        session = await state.sessions.create(
            start_url=start_url,
            test_id=body.test_id,
            max_tabs=project.max_tabs,
            test_id_attribute=project.test_id_attribute,
        )
    except SessionError as exc:
        raise conflict(ErrorCode.SESSION_ALREADY_ACTIVE, str(exc)) from exc

    session.attach_sink(state.broker.sink(session.session_id))

    store = _secret_store(repo)
    public = None
    with contextlib.suppress(KeyMissingError):
        public = load_public(state.key_paths)

    work = SessionWork(
        session=session,
        recorder=Recorder(
            session=session,
            sink=lambda step, index: _accept_step(session.session_id, step, index),
            test_id_attribute=project.test_id_attribute,
            store=store,
            public_key=public,
        ),
        start_url=start_url,
        authoring_mode=AuthoringMode.AI if body.mode == "ai" else AuthoringMode.RECORD,
        ai_instruction=body.ai_instruction,
        saved_test_id=body.test_id,
    )
    if existing_test is not None:
        work.steps = list(existing_test.steps)
        work.recorder.seed_step_seq(len(existing_test.steps))
    _WORK[session.session_id] = work

    await work.recorder.install()

    # 미러와 유실 감지는 모드와 무관하게 붙인다 — 미러는 모든 활성 상태에서 돌아야 하고
    # (FR-047d), 세션 유실은 어느 상태에서든 감지해야 한다 (FR-041).
    work.loss_watcher = SessionLossWatcher(session, on_lost=_loss_handler(session.session_id))
    work.loss_watcher.attach()
    work.mirror = MirrorController(session)

    if body.mode == "record":
        await session.apply(Command.BEGIN_RECORD)
        work.recorder.start(author=Author.HUMAN)
        await session.bring_tab_to_front(0)
    elif body.mode == "replay":
        assert existing_test is not None  # noqa: S101 - 위에서 이미 거절했다
        await session.apply(Command.BEGIN_REPLAY)
        _build_engine(work, state, existing_test)
        await _start_runner(work, start_index=0)
    else:
        await session.apply(Command.BEGIN_AI)

    await work.mirror.show(0)
    return view_of(work)


# ─── 재실행 조립 (US2) ─────────────────────────────────────────────────────


def _build_engine(work: SessionWork, state: AppState, test: Test) -> ReplayEngine:
    """재실행 엔진을 조립한다. FR-044·FR-045.

    **여기서 만드는 것 중 어느 것도 언어모델을 알지 못한다.** 실행에 필요한 전부가 저장된
    정의 안에 있다는 사실이 조립 과정에 드러난다.

    비밀키는 **있으면 쓴다.** 암호구로 잠긴 키는 요청 맥락에서 열 수 없으므로 없는 것으로
    본다 — 그 경우 민감 변수는 환경 변수로 공급되어야 하고, 아니면 해당 Step 이 사유와 함께
    실패한다 (FR-089f). 조용히 빈 값으로 진행하지 않는다.
    """
    repo = state.require_repository()

    private = None
    with contextlib.suppress(KeyStoreError):
        private = load_private(state.key_paths)

    resolver = VariableResolver(
        test,
        store=SecretStore(repo.paths.secrets_file),
        private_key=private,
    )
    collector = ArtifactCollector(work.session.context)
    collector.attach()

    engine = ReplayEngine(
        session=work.session,
        test=test,
        executor=StepExecutor(work.session, resolver),
        resolver=resolver,
        collector=collector,
        run_dir=repo.paths.run_dir(test.id),
        project_root=repo.paths.root,
        write_result=repo.write_result,
        browser_label=f"Playwright · {test.browser.value.capitalize()}",
    )
    work.engine = engine
    return engine


async def _start_runner(work: SessionWork, start_index: int) -> None:
    """러너 태스크를 (다시) 띄운다.

    이미 돌고 있으면 **먼저 취소를 끝낸 뒤** 새로 시작한다. 취소를 기다리지 않으면 앞선
    실행이 그 사이에 완료 상태를 올리고 결과를 써 버린다 — 사용자가 "실패한 Step부터
    실행"을 눌렀는데 이전 실행의 결과가 최신으로 남는 상황이다.

    돌고 있는 태스크의 인덱스만 바꾸는 방법도 쓰지 않는다. 지금 실행 중인 Step 이 끝난
    뒤에야 위치가 반영되어, 사용자가 고른 Step 앞의 Step 이 한 번 더 돈다.
    """
    engine = work.engine
    if engine is None:  # pragma: no cover - 호출자가 replay 모드에서만 부른다
        return

    if work.runner is not None:
        await work.runner.cancel()

    engine.reset(start_index)
    work.current_step_index = start_index

    async def run_one(session: BrowserSession, index: int) -> bool:
        step = engine.test.steps[index]
        work.current_step_index = index
        if work.mirror is not None:
            # 실행 중에는 현재 Step 대상 탭을 따라간다 (FR-030f).
            await work.mirror.follow(step.tab)
        outcome = await engine.run_step(session, index)
        work.current_step_index = index + 1
        return outcome

    runner = RunnerTask(
        session=work.session,
        step_runner=run_one,
        total_steps=len(engine.test.steps),
        start_index=start_index,
        on_finished=engine.finalize,
    )
    work.runner = runner
    # 태스크만 띄우고 즉시 반환한다. 실제 Step 실행은 요청 수명과 분리된다 (research R1).
    runner.start()


def _loss_handler(session_id: str):  # noqa: ANN201 - LossHandler 를 만든다
    """세션 유실 뒷정리. FR-041a~c.

    실행 중이던 태스크를 세우고 **그때까지의 Step별 결과를 보존**한다. 결과를 버리면
    사용자는 어디까지 갔는지 알 수 없고, 유실이 곧 진단 정보 상실이 된다.
    """

    async def handle(reason: str) -> None:
        w = _WORK.get(session_id)
        if w is None:
            return
        if w.runner is not None:
            with contextlib.suppress(Exception):
                await w.runner.cancel()
        if w.engine is not None:
            with contextlib.suppress(Exception):
                await w.engine.finalize(False, session_lost=True)
        if w.mirror is not None:
            with contextlib.suppress(Exception):
                await w.mirror.stop(reason)

    return handle


async def _accept_step(session_id: str, step: Step, index: int) -> None:
    """리코더가 만든 Step 을 목록에 넣고 이벤트를 발행한다.

    **평문은 여기 도달하지 않는다** — 리코더가 치환을 끝낸 Step 만 넘긴다 (T157).
    """
    w = _WORK.get(session_id)
    if w is None:
        return

    if index == -2:  # 같은 요소 반복 입력 — 기존 Step 갱신 (FR-025)
        for i, existing in enumerate(w.steps):
            if existing.id == step.id:
                w.steps[i] = step
                await w.session.emit("step_updated", step=step.model_dump(mode="json"))
                return
        index = -1

    if index < 0 or index >= len(w.steps):
        w.steps.append(step)
        at = len(w.steps) - 1
    else:
        w.steps.insert(index, step)
        at = index

    await w.session.emit(
        "step_added", step=step.model_dump(mode="json"), at_index=at
    )


# ─── 조회 ───────────────────────────────────────────────────────────────────


@router.get("/{session_id}")
async def get_session(session_id: str) -> SessionView:
    return view_of(work_of(session_id))


# ─── 일시정지 / 이어서 실행 (원칙 III) ─────────────────────────────────────


def _apply(w: SessionWork, command: Command) -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:  # pragma: no cover - 항상 루프 안에서 호출된다
        pass
    try:
        from itb.execution.state_machine import next_state

        next_state(w.session.state, command)
    except InvalidTransitionError as exc:
        raise conflict(
            ErrorCode.INVALID_TRANSITION,
            str(exc),
            state=w.session.state.value,
        ) from exc


@router.post("/{session_id}/pause")
async def pause(session_id: str) -> SessionView:
    w = work_of(session_id)
    _apply(w, Command.PAUSE)
    w.recorder.stop()
    await w.session.apply(Command.PAUSE)
    return view_of(w)


@router.post("/{session_id}/resume")
async def resume(session_id: str) -> SessionView:
    """FR-038 — 브라우저를 재시작하지 않고 현재 상태에서 이어서 실행한다."""
    w = work_of(session_id)
    _apply(w, Command.RESUME)
    await w.session.apply(Command.RESUME)
    return view_of(w)


@router.post("/{session_id}/run-from")
async def run_from(session_id: str, body: RunFromRequest) -> SessionView:
    """FR-039·FR-055 — 임의 Step 부터 실행. 브라우저 상태를 되돌리지 않는다 (FR-040c)."""
    w = work_of(session_id)
    if body.step_index >= len(w.steps):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"Step {body.step_index} 이 없습니다. 총 {len(w.steps)}개입니다.",
        )
    _apply(w, Command.RUN_FROM)
    w.current_step_index = body.step_index
    await w.session.apply(Command.RUN_FROM)
    if w.engine is not None:
        await _start_runner(w, body.step_index)
    return view_of(w)


@router.post("/{session_id}/record-actions:start")
async def record_actions_start(session_id: str) -> SessionView:
    """FR-036 — 일시정지 중 직접 동작 추가. 실제 창을 앞으로 가져온다 (FR-023a)."""
    w = work_of(session_id)
    require_paused(w)
    _apply(w, Command.RECORD_ACTIONS_START)
    await w.session.apply(Command.RECORD_ACTIONS_START)
    w.recorder.start(author=Author.HUMAN, insert_at=w.current_step_index)
    if is_manipulation_phase(w.session.state):
        await w.session.bring_tab_to_front(w.session.active_tab_index)
    return view_of(w)


@router.post("/{session_id}/record-actions:stop")
async def record_actions_stop(session_id: str) -> SessionView:
    w = work_of(session_id)
    w.recorder.stop()
    _apply(w, Command.PAUSE)
    await w.session.apply(Command.PAUSE)
    return view_of(w)


# ─── 중지 / 저장 ────────────────────────────────────────────────────────────


@router.post("/{session_id}/stop")
async def stop(session_id: str, state: State) -> SessionView:
    """FR-042 — 세션을 종료한다. 저장 여부는 클라이언트가 확인 후 별도로 호출한다.

    **이미 종료 상태인 세션에도 응답한다.** 실행이 끝난 세션을 닫는 것은 상태 전이가 아니라
    자원 정리다. 여기서 거절하면 브라우저와 세션 등록이 남아, 같은 테스트를 다시 실행할 때
    "이미 실행 중" 으로 막힌다 (FR-043).
    """
    w = work_of(session_id)
    already_terminal = w.session.state in TERMINAL_STATES
    if not already_terminal:
        _apply(w, Command.STOP)

    w.recorder.stop()
    if w.mirror is not None:
        await w.mirror.stop("세션을 종료했습니다.")
    if w.runner is not None:
        await w.runner.cancel()
    if not already_terminal:
        await w.session.apply(Command.STOP)
    snapshot = view_of(w)
    await state.broker.drop(session_id)
    await state.sessions.close(session_id)
    _WORK.pop(session_id, None)
    return snapshot


@router.post("/{session_id}/save")
async def save(session_id: str, body: SaveRequest, state: State) -> Test:
    """FR-028·FR-029 — 이름을 지정해 테스트로 저장한다. Step 0개면 거절한다."""
    w = work_of(session_id)
    repo = state.require_repository()

    if not w.steps:
        raise bad_request(
            ErrorCode.STEP_LIST_EMPTY,
            "Step 이 없어 저장할 수 없습니다. 먼저 동작을 기록하세요.",
        )

    test_id = w.saved_test_id or repo.allocate_test_id()
    variables = _variables_for(w)
    test = Test(
        id=test_id,
        name=body.name,
        authoring_mode=w.authoring_mode,
        start_url=w.start_url,
        variables=variables,
        steps=w.steps,
        ai_instruction=w.ai_instruction,
    )
    repo.write_test(test)
    w.saved_test_id = test_id
    return test


def _variables_for(w: SessionWork) -> list[dict[str, object]]:
    """Step 이 참조하는 변수를 정의로 만든다.

    민감 변수는 **값을 갖지 않는다** — 실제 값은 비밀 파일의 암호문에 있다 (FR-082).
    """
    import re

    pattern = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
    referenced: set[str] = set()
    for step in w.steps:
        for text in (
            getattr(step, "value", None),
            getattr(getattr(step, "assertion", None), "value", None),
        ):
            if isinstance(text, str):
                referenced.update(pattern.findall(text))

    captured = {c.variable_name for c in w.recorder.sensitive_captures}
    out: list[dict[str, object]] = []
    for name in sorted(referenced):
        if name in captured:
            out.append({"name": name, "value": None, "sensitive": True})
        else:
            out.append({"name": name, "value": "", "sensitive": False})
    return out


# ─── WebSocket (관찰, 단방향) ──────────────────────────────────────────────


@router.websocket("/{session_id}/events")
async def session_events(websocket: WebSocket, session_id: str) -> None:
    """서버 → 클라이언트 단방향. 클라이언트는 아무것도 보내지 않는다."""
    state: AppState = websocket.app.state.itb
    hub = state.broker.hub(session_id)
    await hub.connect(websocket)
    try:
        while True:
            # 수신은 연결 유지 확인 목적이며 내용은 무시한다 — 명령 경로가 아니다.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)
