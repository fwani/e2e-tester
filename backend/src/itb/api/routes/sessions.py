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
from itb.execution.session import BrowserSession, SessionError
from itb.execution.state_machine import (
    Command,
    InvalidTransitionError,
    SessionState,
    is_manipulation_phase,
    state_label,
)
from itb.recording.recorder import Recorder
from itb.secrets.keys import KeyMissingError, load_public
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


_WORK: dict[str, SessionWork] = {}
"""세션 ID → 작업 상태. 앱 수명 동안만 유지된다."""


def work_of(session_id: str) -> SessionWork:
    w = _WORK.get(session_id)
    if w is None:
        raise not_found(ErrorCode.SESSION_NOT_FOUND, f"세션을 찾을 수 없습니다: {session_id}")
    return w


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

    if body.mode == "record":
        await session.apply(Command.BEGIN_RECORD)
        work.recorder.start(author=Author.HUMAN)
        await session.bring_tab_to_front(0)
    elif body.mode == "replay":
        await session.apply(Command.BEGIN_REPLAY)
    else:
        await session.apply(Command.BEGIN_AI)

    return view_of(work)


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
    """FR-039 — 임의 Step 부터 실행. 브라우저 상태를 되돌리지 않는다 (FR-040c)."""
    w = work_of(session_id)
    if body.step_index >= len(w.steps):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"Step {body.step_index} 이 없습니다. 총 {len(w.steps)}개입니다.",
        )
    _apply(w, Command.RUN_FROM)
    w.current_step_index = body.step_index
    await w.session.apply(Command.RUN_FROM)
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
    """FR-042 — 세션을 종료한다. 저장 여부는 클라이언트가 확인 후 별도로 호출한다."""
    w = work_of(session_id)
    _apply(w, Command.STOP)
    w.recorder.stop()
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
