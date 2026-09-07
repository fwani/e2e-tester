"""세션 엔드포인트. FR-023·FR-028~FR-043·FR-061. contracts/rest-api.md §세션.

**명령은 REST, 관찰은 WebSocket.** 이 라우터가 명령을 받아 상태 기계에 적용하고 즉시
반환한다. 실제 실행은 러너 태스크가 담당한다 (research R1).
"""

from __future__ import annotations

import asyncio
import uuid
import contextlib
from datetime import UTC, datetime
from dataclasses import dataclass, field
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from itb.api.errors import (
    ErrorBody,
    ErrorCode,
    bad_request,
    conflict,
    error_payload,
    not_found,
)
from itb.api.state import AppState, get_state
from itb.domain.run_pacing import DEFAULT_PACING, RunPacing, auto_pause, delay_ms
from itb.domain.run_result import RunScope, StepOutcome, scope_of
from itb.domain.step import Author, NavigateStep, Step
from itb.domain.test_case import AuthoringMode, Test, Variable
from itb.execution.artifacts import ArtifactCollector
from itb.execution.runner import ReplayEngine, RunnerTask
from itb.execution.session import (
    BrowserSession,
    SessionError,
    TargetUnreachableError,
)
from itb.execution.session_loss import SessionLossWatcher
from itb.execution.state_machine import (
    TERMINAL_STATES,
    Command,
    InvalidTransitionError,
    SessionState,
    allowed_commands,
    is_manipulation_phase,
    state_label,
)
from itb.execution.step_edits import allocate_step_id
from itb.execution.step_executor import StepExecutor
from itb.mirror.tab_switch import MirrorController
from itb.recording.inline_record import InlineRecording
from itb.recording.recorder import Recorder
from itb.secrets.keys import load_private_or_reason, load_public_or_none
from itb.secrets.resolver import VariableResolver
from itb.secrets.store import SecretStore
from itb.storage import preferences
from itb.storage.repository import ProjectError, ProjectRepository

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

State = Annotated[AppState, Depends(get_state)]

STEP_ADAPTER = TypeAdapter(Step)

PAUSE_SETTLE_TIMEOUT_S = 10.0
"""일시정지가 Step 경계에 도달하기를 기다리는 상한.

Step 기본 대기 시간이 5000ms 이므로(research R8) 보통 그 안에 끝난다. 상한을 Step
최대치(60초)로 잡으면 사용자는 멈추기를 눌러 놓고 1분을 기다린다.
"""


# ─── 세션 작업 상태 (메모리 전용) ───────────────────────────────────────────


@dataclass(slots=True)
class SessionWork:
    """세션 하나의 작업 중 Step 목록과 리코더.

    Step 목록을 세션이 소유한다 — 저장 시점에 `Test` 로 커밋된다 (data-model §8).
    """

    session: BrowserSession
    recorder: Recorder
    store: SecretStore | None = None
    """이 세션의 비밀 값 보관소. **세션 안에서 하나만 쓴다.**

    `SecretStore` 는 생성 시점에 파일을 읽어 메모리에 들고 있다. 인스턴스를 둘 만들면
    한쪽이 봉인한 값이 다른 쪽에 보이지 않아, 방금 만든 민감 변수를 실행기가 "보관되어
    있지 않다" 로 거절한다 (AI 작성 테스트가 이것을 잡았다).
    """

    steps: list[Step] = field(default_factory=list)
    start_url: str = ""
    # 속도 사본을 여기 두지 않는다. **세션이 소유한다** (`BrowserSession.pacing`) —
    # `current_step_index` 를 세션이 소유하는 것과 같은 이유다. 두 곳에 두면 한쪽만
    # 갱신되는 순간 화면이 말하는 속도와 러너가 쉬는 시간이 갈린다.
    authoring_mode: AuthoringMode = AuthoringMode.RECORD
    ai_instruction: str | None = None
    saved_test_id: str | None = None
    saved_at: datetime | None = None
    """마지막 저장 시각 (005 FR-154). 화면이 저장 성공을 스스로 알 수 있게 한다."""

    # ─── 재실행 (US2) ──────────────────────────────────────────────────────
    mirror: MirrorController | None = None
    """미러는 **모든 활성 상태**에서 돈다 (FR-047d). 그래서 모드와 무관하게 붙인다."""

    loss_watcher: SessionLossWatcher | None = None
    engine: ReplayEngine | None = None
    runner: RunnerTask | None = None

    # ─── 일시정지 중 편집 (US3) ────────────────────────────────────────────
    inline: InlineRecording | None = None
    """일시정지 중 직접 동작 추가 (FR-036)."""

    # ─── AI 작성 (US4·US5·US6) ─────────────────────────────────────────────
    agent: object | None = None
    """`AuthoringAgent`. 타입을 `object` 로 둔 이유는 임포트 방향이다 — 이 모듈은
    `itb.authoring` 을 지연 임포트해 API 계층이 언어모델 경계를 항상 끌고 오지 않게 한다."""

    compiler: object | None = None
    toolbox: object | None = None
    agent_task: asyncio.Task[None] | None = None
    takeover: object | None = None
    resolver: object | None = None
    last_blocked: object | None = None
    """마지막 `ai_blocked` 결과. `retry`·`skip` 이 무엇을 재시도할지의 근거다."""

    base_variables: list[Variable] = field(default_factory=list)
    """세션이 시작될 때 불러온 테스트의 변수 정의.

    **다시 저장할 때 이것을 출발점으로 삼는다.** 세션에서 새로 포착한 것만 보고 정의를
    다시 만들면, 불러온 테스트의 민감 변수가 "포착되지 않았다" 는 이유로 비민감·빈 값으로
    강등된다. 그렇게 저장된 테스트는 재실행에서 빈 비밀번호를 채워 조용히 실패한다
    (US6 통합 테스트가 잡았다).
    """

    saved_snapshot: list[Step] = field(default_factory=list)
    """마지막 저장 시점의 Step 목록.

    중지 요청에 "저장하지 않은 편집이 있다" 를 실어 보내기 위한 것이다 (FR-042).
    개수만 세면 삭제와 삽입이 겹쳐 개수가 같은 경우를 놓친다.
    """

    @property
    def has_unsaved_changes(self) -> bool:
        """저장하지 않은 편집이 있는가 (FR-042).

        중지는 세션을 끝내는 조작이므로, 사용자가 저장 여부를 결정할 수 있어야 한다.
        서버가 대신 저장하지 않는다 — 저장은 이름을 요구하는 별개의 명령이다.
        """
        return [s.id for s in self.steps] != [s.id for s in self.saved_snapshot] or any(
            a != b for a, b in zip(self.steps, self.saved_snapshot, strict=False)
        )

    @property
    def current_step_index(self) -> int:
        """다음에 실행할 Step 위치. **세션이 소유한 값을 그대로 읽는다.**

        여기에 사본을 두면 상태 전이 이벤트가 실어 보내는 값과 REST 응답의 값이
        어긋난다 — 어느 쪽이 진실인지 모호해진다.
        """
        return self.session.current_step_index

    @current_step_index.setter
    def current_step_index(self, value: int) -> None:
        self.session.current_step_index = value


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
    """FR-035a·DR-012 — 편집 명령은 `PAUSED` 와 `REVIEW` 에서만 받는다.

    **상태 기계의 판정을 그대로 쓴다.** 여기에 상태 목록을 다시 적으면 두 곳이 어긋난다 —
    002 에서 `REVIEW` 를 더했을 때 상태 기계는 편집을 허용하는데 이 게이트가 막고 있었다.
    """
    from itb.execution.state_machine import is_editable  # noqa: PLC0415

    if not is_editable(w.session.state):
        raise conflict(
            ErrorCode.NOT_PAUSED,
            f"현재 상태가 '{state_label(w.session.state)}' 이므로 Step 을 편집할 수 없습니다. "
            "먼저 일시정지하세요.",
            state=w.session.state.value,
            # **지금 무엇이 가능한지**를 함께 싣는다 (003 AP-020). "안 된다" 만 말하면
            # 사용자는 되는 것을 하나씩 눌러 보며 찾아야 한다. 목록은 상태 기계가
            # 소유한 것을 읽어 오므로 여기서 다시 적어 어긋날 일이 없다.
            allowed=[c.value for c in allowed_commands(w.session.state)],
        )


# ─── 요청·응답 모델 ─────────────────────────────────────────────────────────


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["record", "replay", "ai"]
    test_id: str | None = Field(default=None, pattern=r"^TC-\d{3}$")
    start_url: str | None = Field(default=None, pattern=r"^https?://", max_length=2000)
    ai_instruction: str | None = Field(default=None, max_length=8000)

    pacing: RunPacing | None = None
    """실행 속도 (004 FR-102). 없으면 저장된 취향, 그것도 없으면 기본값.

    **무인 실행은 명시해야 한다.** 저장된 취향이 CI 를 느리게 만들지 않는 유일한 방법이
    요청에 `fast` 를 넣는 것이다 (contracts/rest-api.md §1).
    """


class PacingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pacing: RunPacing


class StepProgress(BaseModel):
    """세션에서 지금까지 확정된 Step 결과 하나 (005 FR-171).

    `StepResult` 전체가 아니라 **화면 복원에 필요한 최소**다. 진단 정보(로케이터 시도·
    오류 본문)는 결과 조회로 가져온다 — 세션 뷰는 폴링 대상이므로 가볍게 유지한다.
    """

    model_config = ConfigDict(extra="forbid")

    step_id: str
    outcome: StepOutcome
    duration_ms: int = Field(default=0, ge=0)


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
    has_unsaved_changes: bool = False
    """저장하지 않은 편집이 있는가. 중지 확인 대화상자의 근거다 (FR-042)."""

    pacing: RunPacing = DEFAULT_PACING
    """이 세션의 실행 속도.

    재연결 시 전체 상태를 동기화하는 것이 `SessionView` 의 목적이므로 여기 실린다.
    화면은 이 값으로 `paused` 의 **문구를 가른다** — `step` 이면 "한 스텝씩", 아니면
    "일시정지됨". 상태가 같고 의미가 다른 두 경우를 구별하는 유일한 근거다 (research R7).
    """

    authoring_mode: AuthoringMode = AuthoringMode.RECORD
    """어떻게 만드는 세션인가. **세션의 불변 속성이다.**

    화면이 AI 세션 여부를 `state` 로 판정하면, AI 가 실패해 `paused` 로 바뀌는 순간
    AI 화면과 실패 사유가 사라진다 — 001 에서 "AI 로 만들기가 아무 반응이 없다" 로
    보인 것의 원인이다 (research R2·DR-020)."""

    step_results: list[StepProgress] = Field(default_factory=list)
    """이 세션에서 지금까지 확정된 Step별 결과 (005 FR-171).

    **이벤트 없이도 화면이 복원되게 하는 것이 목적이다.** 이전에는 Step별 결과가
    WebSocket 이벤트로만 채워지는 화면 로컬 상태에 있어, 화면을 다시 그리면 사라졌다
    (U-18). 같은 뿌리가 U-05 의 "실패한 Step 이 화면에서 지워지는" 증상이다 — 실패
    이벤트를 놓친 화면은 실패가 없었던 것처럼 보인다.

    WebSocket 계약은 이미 "끊기면 세션 조회로 전체 상태를 다시 받는다" 인데, 그 전체
    상태에 Step 결과가 빠져 있던 것이 계약의 구멍이었다. 재전송 버퍼를 만드는 대신
    스냅샷을 채운다.
    """

    pause_settled: bool = True
    """일시정지가 **실제로** 걸렸는가 (005 FR-142).

    `False` 면 요청은 갔지만 아직 Step 경계에 닿지 않은 **전이 중**이다. 값은 러너의
    `at_boundary` 에서 온다.

    `SessionState` 에 새 상태를 넣지 않은 이유는 두 가지다 — 전이표 전체와 004 의
    `한 스텝씩` 재사용 결정을 흔들게 되고, "요청은 갔고 아직 경계에 닿지 않았다" 는
    상태가 아니라 러너의 사실이다 (research R7).

    이전에는 요청 즉시 `paused` 로 보이는데 실제로는 19초를 더 돌았다 (U-04).
    """

    run_scope: RunScope = RunScope.FULL
    """현재 실행의 범위 (005 FR-152)."""

    run_start_index: int = Field(default=0, ge=0)
    """현재 실행이 시작한 Step (005 FR-149·FR-150). 화면이 건너뛴 구간을 말하는 근거다."""

    saved_at: datetime | None = None
    """마지막 저장 시각 (005 FR-154). `None` 이면 미저장.

    저장 성공을 화면이 **스스로** 알 수 있게 한다. 이전에는 저장 응답 말고는 저장 여부를
    알 방법이 없어, 화면을 다시 그리면 다시 미저장처럼 보였고 사용자는 목록으로 나가
    확인해야 했다 (U-09).
    """


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class ResumeRequest(BaseModel):
    """재개 요청 (005 FR-136·FR-137, contracts/rest-api.md §3-b).

    본문을 보내지 않으면 `skip_failed=False` 와 같다 — 기존 클라이언트가 그대로 동작한다.
    """

    model_config = ConfigDict(extra="forbid")

    skip_failed: bool = False
    """실패한 Step 을 건너뛰고 다음 Step 부터 이어간다.

    **버튼이 둘이지만 엔드포인트는 하나다.** 나누면 재개 규칙(편집된 목록을 대상으로
    삼는 것, 러너를 새로 띄우지 않는 것)이 두 벌이 되고, 한쪽이 뒤처진다.
    """


class RunFromRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(ge=0)


_CREATE_LOCKS: dict[str, asyncio.Lock] = {}
"""테스트별 세션 생성 락 (005 FR-128).

**전역 락 하나를 쓰지 않는다.** 그러면 서로 다른 테스트의 실행이 브라우저 기동 동안
직렬화되어, 고치려던 것(중복 생성)보다 눈에 띄는 지연을 만든다.

락은 프로세스 수명 동안 남는다 — 테스트 수는 사람이 만드는 규모이므로 정리 정책을 둘
이유가 없다. 정리 로직을 두면 정리와 획득 사이에 또 다른 경쟁이 생긴다.
"""


def _create_lock(test_id: str) -> asyncio.Lock:
    lock = _CREATE_LOCKS.get(test_id)
    if lock is None:
        lock = asyncio.Lock()
        _CREATE_LOCKS[test_id] = lock
    return lock


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
        has_unsaved_changes=w.has_unsaved_changes,
        pacing=w.session.pacing,
        authoring_mode=w.authoring_mode,
        step_results=_progress_of(w),
        pause_settled=_pause_settled(w),
        run_scope=scope_of(w.engine.start_index if w.engine is not None else 0),
        run_start_index=w.engine.start_index if w.engine is not None else 0,
        saved_at=w.saved_at,
    )


def _progress_of(w: SessionWork) -> list[StepProgress]:
    """엔진이 들고 있는 Step 결과를 화면 복원용 형태로 옮긴다 (005 FR-171).

    **아직 돌지 않은 Step 은 싣지 않는다.** `not_run` 을 그대로 보내면 화면은 "결과가
    있다" 와 "아직 없다" 를 구분하지 못하고, 실행 전에도 모든 Step 이 결과를 가진 것처럼
    보인다. 없는 것은 없는 채로 둔다.
    """
    if w.engine is None:
        return []
    return [
        StepProgress(
            step_id=r.step_id, outcome=r.outcome, duration_ms=r.duration_ms
        )
        for r in w.engine.results
        if r.outcome is not StepOutcome.NOT_RUN
    ]


def _pause_settled(w: SessionWork) -> bool:
    """일시정지가 실제로 걸렸는가 (005 FR-142).

    일시정지 상태가 아니면 **`True` 로 둔다** — "전이 중이 아니다" 가 맞는 답이다.
    `False` 를 기본으로 두면 실행 중 화면이 전이 표시를 켠다.

    러너가 없거나 이미 끝났으면 기다릴 것이 없으므로 걸린 것으로 본다.
    """
    if w.session.state is not SessionState.PAUSED:
        return True
    runner = w.runner
    if runner is None or not runner.running:
        return True
    return runner.at_boundary


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

    if body.mode == "ai":
        # FR-085 — 경계에서 검증한다. 길이·공백 규칙은 작성 계층이 갖는다.
        from itb.authoring.agent import validate_instruction

        try:
            validate_instruction(body.ai_instruction)
        except ValueError as exc:
            raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc

    # 005 FR-128 — 확인과 예약을 **한 락 안에서** 함께 한다.
    #
    # 이전에는 확인 뒤 `create()` 까지 사이에 await 경계가 있었고 락이 없었다. 그래서
    # 100 ms 안에 도착한 다섯 요청이 모두 확인을 통과해 브라우저 창이 둘 떴다 (U-06).
    # FR-043(테스트당 동시 실행 1건)이 경계에서 지켜지지 않았던 것이다.
    #
    # 락은 **짧게 쥐고 놓는다.** 브라우저 기동(약 1초)을 락 안에 두면 다른 테스트의
    # 실행까지 직렬화된다. 대신 자리를 예약해 긴 구간을 보호한다.
    reservation: tuple[str, str] | None = None
    if body.test_id:
        async with _create_lock(body.test_id):
            held = state.sessions.reservation_for_test(body.test_id)
            if held:
                raise conflict(
                    ErrorCode.SESSION_ALREADY_ACTIVE,
                    f"{body.test_id} 가 지금 실행 중입니다.",
                    next_action="실행 중인 세션으로 이동한 뒤 중지하세요.",
                    test_id=body.test_id,
                    session_id=held,
                )
            token = uuid.uuid4().hex
            state.sessions.reserve_for_test(body.test_id, token)
            reservation = (body.test_id, token)

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
    except TargetUnreachableError as exc:
        # SessionError 의 하위 형이므로 **먼저** 잡는다. 대상 앱이 안 떠 있는 것은
        # 이 도구에서 가장 흔한 첫 실패다 — 원인이 완전히 특정되므로 그대로 말한다.
        raise bad_request(
            ErrorCode.TARGET_UNREACHABLE,
            str(exc),
            start_url=exc.url,
        ) from exc
    except SessionError as exc:
        raise conflict(ErrorCode.SESSION_ALREADY_ACTIVE, str(exc)) from exc
    finally:
        # 005 FR-128 — 예약은 여기서 반드시 놓는다.
        #
        # 성공했으면 세션이 등록됐으므로 예약은 더 이상 필요 없고, 실패했으면 남겨 두면
        # 그 테스트가 프로세스가 끝날 때까지 "실행 중" 으로 잠긴다 — 고치려던 결함보다
        # 나쁜 상태다. 그래서 두 경우를 `finally` 하나로 합친다.
        if reservation is not None:
            state.sessions.release_reservation(*reservation)

    # 요청 → 저장된 취향 → 기본값 (FR-109, contracts/rest-api.md §1).
    session.pacing = (
        body.pacing if body.pacing is not None else preferences.load().run_pacing
    )

    session.attach_sink(state.broker.sink(session.session_id))

    store = _secret_store(repo)  # 이 세션 동안 공유한다
    # **공개키를 여기서 붙잡지 않는다.** 세션이 열려 있는 동안 사용자가 키 관리 화면에서
    # 키를 만들거나 바꿀 수 있다. 붙잡아 두면 그 세션은 끝까지 옛 상태로 실패한다.
    key_paths = state.key_paths

    work = SessionWork(
        session=session,
        recorder=Recorder(
            session=session,
            sink=lambda step, index: _accept_step(session.session_id, step, index),
            test_id_attribute=project.test_id_attribute,
            store=store,
            key_source=lambda: load_public_or_none(key_paths),
        ),
        store=store,
        start_url=start_url,
        authoring_mode=AuthoringMode.AI if body.mode == "ai" else AuthoringMode.RECORD,
        ai_instruction=body.ai_instruction,
        saved_test_id=body.test_id,
    )
    if existing_test is not None:
        work.steps = list(existing_test.steps)
        work.recorder.seed_step_seq(len(existing_test.steps))
        work.saved_snapshot = list(existing_test.steps)
        work.base_variables = list(existing_test.variables)
    work.inline = InlineRecording(session=session, recorder=work.recorder)
    # Step id 를 목록 기준으로 할당한다 — 리코더가 매긴 번호와 편집으로 추가한 번호가
    # 충돌하면 저장 시점에 `Test` 검증이 거절한다 (실제로 US3 종단 테스트가 잡았다).
    work.recorder.id_allocator = lambda: allocate_step_id(work.steps)
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
        _build_agent(work, state)
        _start_agent(work, body.ai_instruction)

    await work.mirror.show(0)
    return view_of(work)


# ─── 재실행 조립 (US2) ─────────────────────────────────────────────────────


def _build_engine(
    work: SessionWork, state: AppState, test: Test, draft: bool = False
) -> ReplayEngine:
    """재실행 엔진을 조립한다. FR-044·FR-045.

    **여기서 만드는 것 중 어느 것도 언어모델을 알지 못한다.** 실행에 필요한 전부가 저장된
    정의 안에 있다는 사실이 조립 과정에 드러난다.

    비밀키를 **여기서 열지 않는다.** 여는 방법만 넘기고, 민감 변수를 실제로 요구하는
    순간에 연다. 두 가지가 여기에 걸려 있다.

    1. 민감 변수를 쓰지 않는 테스트는 비밀키 없이 실행돼야 한다.
    2. 세션이 열려 있는 동안 키 관리 화면에서 키를 만들거나 바꿀 수 있다. 시작 시점에
       붙잡아 두면 그 세션은 끝까지 옛 상태로 실패한다.

    못 열면 사유를 그대로 보여준다 — 예전에는 예외를 통째로 삼켜 암호구로 잠긴 키가
    "비밀키가 없습니다" 로 보고됐고, 사용자는 있는 키를 찾아 헤맸다 (FR-089f).
    """
    repo = state.require_repository()

    key_paths = state.key_paths
    # 잠금 해제 상태도 **여기서 값을 꺼내지 않고** 객체째 들고 간다. 값을 지금 읽으면
    # 세션이 열려 있는 동안 화면에서 해제한 잠금이 이 세션에 반영되지 않는다.
    unlock = state.key_unlock
    resolver = VariableResolver(
        test,
        store=work.store or _secret_store(repo),
        key_source=lambda: load_private_or_reason(key_paths, unlock.passphrase),
    )
    collector = ArtifactCollector(work.session.context)
    collector.attach()

    # 저장 전 초안은 결과 파일을 남기지 않는다 — 목록에 없는 테스트의 결과가 디스크에
    # 생기면 사용자가 그것을 무엇으로 읽을지 알 수 없다. 실패 스크린샷·로그는 `_draft/`
    # 에 남겨 진단은 가능하게 한다 (FR-052·FR-053).
    engine = ReplayEngine(
        session=work.session,
        test=test,
        executor=StepExecutor(work.session, resolver),
        resolver=resolver,
        collector=collector,
        run_dir=repo.paths.draft_run_dir if draft else repo.paths.run_dir(test.id),
        project_root=repo.paths.root,
        write_result=(lambda _result: None) if draft else repo.write_result,
        browser_label=f"Playwright · {test.browser.value.capitalize()}",
    )
    work.engine = engine
    return engine


# ─── AI 작성 조립 (US4) ────────────────────────────────────────────────────


def _build_agent(work: SessionWork, state: AppState) -> None:
    """AI 작성에 필요한 것을 조립한다. FR-059~FR-067.

    **`itb.authoring` 을 여기서 지연 임포트한다.** 모듈 최상단에서 임포트하면 재실행만
    쓰는 경로에서도 언어모델 경계 모듈이 항상 함께 적재된다. 원칙 II 는 임포트 계약으로
    강제되지만(`itb.execution` → `itb.llm` 금지), API 계층에서도 필요할 때만 끌어오는 것이
    그 경계를 읽기 쉽게 만든다.

    민감 값 포착기를 **리코더와 공유한다** — 사람이 이어받아 입력한 값(FR-071)과 AI 가
    입력한 값이 같은 변수 이름 공간을 써야 정의와 비밀 파일이 어긋나지 않는다.
    """
    from itb.authoring.agent import AuthoringAgent
    from itb.authoring.compiler import StepCompiler
    from itb.authoring.tools import BrowserToolbox
    from itb.secrets.capture import SensitiveCapturer

    repo = state.require_repository()
    key_paths = state.key_paths
    unlock = state.key_unlock

    store = work.store or _secret_store(repo)
    capturer = work.recorder.capturer or SensitiveCapturer(
        store=store,
        key_source=lambda: load_public_or_none(key_paths),
    )
    work.recorder.capturer = capturer

    resolver = VariableResolver(
        _draft_test(work) if work.steps else _empty_draft(work),
        store=store,
        key_source=lambda: load_private_or_reason(key_paths, unlock.passphrase),
    )
    work.resolver = resolver

    compiler = StepCompiler(
        place=lambda step, index: _accept_step(work.session.session_id, step, index)
    )
    work.compiler = compiler

    toolbox = BrowserToolbox(
        session=work.session,
        executor=StepExecutor(work.session, resolver),
        allocate_step_id=lambda: allocate_step_id(work.steps),
        on_step=compiler.accept,
        on_progress=lambda message: work.session.emit("ai_progress", message=message),
        capturer=capturer,
        on_variable=resolver.declare,
        test_id_attribute=work.recorder.test_id_attribute,
    )
    work.toolbox = toolbox
    work.agent = AuthoringAgent(
        toolbox=toolbox,
        compiler=compiler,
        on_progress=lambda message: work.session.emit("ai_progress", message=message),
    )


def _empty_draft(work: SessionWork) -> Test:
    """Step 이 없는 세션용 임시 정의.

    `Test` 는 Step 1개 이상을 요구하므로(FR-029) 변수 해석기에 넘길 껍데기를 만들 수 없다.
    해석기는 `variables` 만 보므로, 최소 Step 하나를 넣은 껍데기로 만족시킨다 —
    **이 정의는 디스크에 쓰이지 않고 실행 대상도 아니다.**
    """
    return Test(
        id=DRAFT_TEST_ID,
        name="(작성 중)",
        authoring_mode=work.authoring_mode,
        start_url=work.start_url,
        variables=[],
        steps=[
            NavigateStep(id="step-01", label="시작", tab=0, url=work.start_url),
        ],
    )


async def _run_agent(session_id: str, instruction: str | None = None) -> None:
    """에이전트를 돌리고 결과를 이벤트로 바꾼다 (FR-059·FR-063·FR-067·FR-069).

    **취소는 결과로 기록하지 않는다** — 사용자가 일시정지·중지한 것이며 실패가 아니다.
    """
    from itb.authoring.agent import AgentStatus, AuthoringAgent
    from itb.authoring.blocked import enter_blocked

    work = _WORK.get(session_id)
    if work is None or not isinstance(work.agent, AuthoringAgent):
        return
    agent: AuthoringAgent = work.agent

    try:
        if instruction is None:
            takeover = work.takeover
            note = takeover.summary() if takeover is not None else "사람이 이어받았습니다."
            outcome = await agent.resume_after_takeover(note)
        else:
            outcome = await agent.run(instruction)
    except asyncio.CancelledError:
        raise

    work.last_blocked = outcome
    if outcome.status is AgentStatus.BLOCKED:
        await enter_blocked(work.session, outcome)
        return
    if outcome.status is AgentStatus.ERROR:
        # 세션을 닫지 않는다. 그때까지의 Step 은 보존된다 (FR-067).
        await work.session.emit(
            "ai_error",
            **error_payload(ErrorCode.AI_FAILED, outcome.reason or "AI 수행이 실패했습니다."),
        )
        await _hold_for_review(work)
        return

    await work.session.emit("ai_finished", step_count=outcome.step_count)
    await _hold_for_review(work)


async def _hold_for_review(work: SessionWork) -> None:
    """AI 가 멈춘 뒤 세션을 **편집 가능한 상태로 유지한다**.

    `COMPLETED` 로 보내지 않는 이유는 그 상태가 아무 명령도 받지 않기 때문이다. AI 작성은
    끝나는 순간이 곧 사용자가 확인하고 손보는 시작점이다 — 검증 Step 을 더하거나(FR-037),
    자연어로 Step 을 추가하거나(FR-078), 이름을 붙여 저장한다(FR-028). 종료 상태로 보내면
    그 모든 것을 하려고 세션을 다시 만들어야 하고, 그때는 AI 가 만든 화면 상태가 없다.

    재실행(`REPLAYING`)이 끝났을 때와 다른 판단이다. 그쪽은 결과를 보는 것으로 끝난다.
    """
    with contextlib.suppress(InvalidTransitionError):
        await work.session.apply(Command.PAUSE)


def _start_agent(work: SessionWork, instruction: str | None) -> None:
    """에이전트 태스크를 띄우고 즉시 반환한다.

    HTTP 요청 수명과 분리하는 이유는 재실행과 같다 (research R1) — 작성은 몇 분이 걸릴 수
    있고, 그 사이 사용자는 일시정지·중지를 눌러야 한다 (FR-065).
    """
    work.agent_task = asyncio.create_task(
        _run_agent(work.session.session_id, instruction)
    )


async def _cancel_agent(work: SessionWork) -> None:
    """돌고 있는 에이전트를 세운다. 브라우저는 그대로 둔다 (FR-065)."""
    task = work.agent_task
    if task is None or task.done():
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await task
    work.agent_task = None


DRAFT_TEST_ID = "TC-000"
"""저장 전 초안 세션이 쓰는 임시 테스트 ID.

`allocate_test_id` 는 1 부터 부여하므로 이 ID 는 실제 테스트와 충돌하지 않는다.
초안은 결과 파일을 쓰지 않으므로 이 ID 로 디스크에 남는 것도 없다.
"""


def _draft_test(work: SessionWork) -> Test:
    """세션의 작업 중 Step 목록을 실행 가능한 정의로 감싼다.

    저장하지 않은 세션에서도 "이어서 실행"(FR-038)·"이 Step부터 실행"(FR-039)이 동작해야
    한다. 실행 엔진은 `Test` 를 요구하므로 초안을 그 형태로 만든다 — **디스크에 쓰지
    않는다.** 저장은 이름을 요구하는 별개의 명령이다 (FR-028).
    """
    return Test(
        id=work.saved_test_id or DRAFT_TEST_ID,
        name="(저장 전 초안)",
        authoring_mode=work.authoring_mode,
        start_url=work.start_url,
        variables=_variables_for(work),  # type: ignore[arg-type]
        steps=work.steps,
        ai_instruction=work.ai_instruction,
    )


def _ensure_engine(work: SessionWork, state: AppState) -> ReplayEngine | None:
    """실행 엔진을 확보한다. Step 이 없으면 만들지 않는다.

    녹화로 시작한 세션에는 엔진이 없다 — 녹화는 사용자가 실제 창에서 하는 것이고 제품이
    Step 을 돌리는 것이 아니기 때문이다. 그 세션에서 "계속하기" 를 누르면 그때 엔진이
    필요해진다.
    """
    if work.engine is not None:
        return work.engine
    if not work.steps:
        return None
    return _build_engine(work, state, _draft_test(work), draft=work.saved_test_id is None)


async def _start_runner(
    work: SessionWork, start_index: int, reset: bool = True
) -> None:
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

    if reset:
        # "실패한 Step부터 실행" 은 **새 실행**이다. 앞선 실행의 기록을 남기면 통과한
        # 실행이 실패로 보인다 (FR-055).
        engine.reset(start_index)
    else:
        # 일시정지 후 이어서 실행이다. 이미 실행된 Step 의 결과를 보존한다 (원칙 III).
        engine.rebase(work.steps)
    work.current_step_index = start_index

    async def run_one(session: BrowserSession, index: int) -> bool:
        """Step 하나. **실행 위치를 여기서 쓰지 않는다** — 러너가 소유한다.

        여기서 `current_step_index` 를 절대값으로 쓰면, 일시정지 중 편집이 옮긴 위치를
        되돌려 같은 Step 이 두 번 실행된다 (T093 이 잡은 결함).
        """
        if index >= len(engine.test.steps):  # 편집으로 목록이 줄었다
            return True
        step = engine.test.steps[index]
        if work.mirror is not None:
            # 실행 중에는 현재 Step 대상 탭을 따라간다 (FR-030f).
            await work.mirror.follow(step.tab)
        return await engine.run_step(session, index)

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

    # **리코더가 만든 Step 은 이미 수행된 동작이다.** 그래서 실행 위치를 그 뒤로 옮긴다 —
    # 옮기지 않으면 "계속하기" 가 사용자가 방금 손으로 한 동작을 다시 실행한다. 로그인이
    # 재실행되지 않아야 한다는 SC-007 이 정확히 이 지점에 걸려 있다.
    #
    # REST 로 삽입한 Step 은 반대다. 그것은 아직 수행되지 않은 **정의**이므로 실행 위치가
    # 그것을 가리켜야 한다 (`step_edits.insert_step`).
    w.current_step_index = max(w.current_step_index, at + 1)

    await w.session.emit(
        "step_added", step=step.model_dump(mode="json"), at_index=at
    )


# ─── 조회 ───────────────────────────────────────────────────────────────────


class SessionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions: list[SessionView]


@router.get("")
async def list_sessions() -> SessionListResponse:
    """살아 있는 세션 전부 (UX U-05).

    새로고침 한 번에 화면은 목록으로 떨어지는데 서버에는 ``recording`` · Step 5개 ·
    ``has_unsaved_changes`` 세션이 그대로 살아 있고 실제 브라우저 창도 떠 있었다. 화면
    어디에도 그 세션으로 돌아가는 길이 없었고, 세션 id 를 알아낼 방법도 없었다 — 그 상태로
    새 녹화를 시작하면 두 번째 창이 열리고 앞의 5개는 영원히 못 찾는다.

    화면이 이 목록으로 진행 중 세션을 알리고 되찾게 한다.
    """
    return SessionListResponse(sessions=[view_of(w) for w in _WORK.values()])


@router.get("/{session_id}")
async def get_session(session_id: str) -> SessionView:
    return view_of(work_of(session_id))


# ─── 실행 속도 (004 US1) ────────────────────────────────────────────────────


@router.post("/{session_id}/pacing")
async def set_pacing(session_id: str, body: PacingRequest) -> SessionView:
    """실행 속도를 바꾼다 (004 FR-103).

    **실행 중에도 부를 수 있다.** 진행 중인 Step 을 끊지 않으며, 러너가 다음 Step 경계에서
    이 값을 다시 읽는다. 브라우저에는 아무 명령도 보내지 않는다 (원칙 III 계열).

    취향 파일에도 남긴다 — FR-109 의 "다음 실행에서 마지막 선택이 기본값" 은 실행 중
    변경까지 반영되어야 성립한다. **다만 그 쓰기 실패로 이 호출이 실패하지는 않는다.**
    속도는 이미 바뀌었고, 취향을 못 남긴 것 때문에 실행을 방해할 이유가 없다. 대신
    조용히 넘기지 않고 `preference_saved: false` 로 알린다.
    """
    w = work_of(session_id)
    if w.session.state is SessionState.LOST:
        raise conflict(
            ErrorCode.SESSION_LOST,
            "세션이 유실되어 실행 속도를 바꿀 수 없습니다.",
            state=w.session.state.value,
        )
    if w.session.state in TERMINAL_STATES:
        raise conflict(
            ErrorCode.INVALID_TRANSITION,
            "이미 끝난 세션의 실행 속도는 바꿀 수 없습니다.",
            state=w.session.state.value,
            allowed=[c.value for c in allowed_commands(w.session.state)],
        )

    w.session.pacing = body.pacing

    saved = True
    try:
        preferences.save(body.pacing)
    except preferences.PreferencesWriteError:
        saved = False

    await w.session.emit(
        "pacing_changed",
        pacing=body.pacing.value,
        # 대응표를 화면이 따로 들고 있으면 서버와 갈린다. 계산한 값을 함께 보낸다
        # (contracts/websocket.md §1).
        delay_ms=delay_ms(body.pacing),
        auto_pause=auto_pause(body.pacing),
        preference_saved=saved,
    )
    return view_of(w)


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
            allowed=[c.value for c in allowed_commands(w.session.state)],
        ) from exc


@router.post("/{session_id}/pause")
async def pause(session_id: str) -> SessionView:
    """FR-031 — 언제든 멈춘다.

    **브라우저에 아무 명령도 보내지 않는다.** 러너 태스크가 `asyncio.Event` 를 await 하게
    만드는 것이 전부이며, 그래서 인증 상태·화면 위치·입력 내용이 그대로 남는다 (FR-032).
    """
    w = work_of(session_id)
    _apply(w, Command.PAUSE)
    w.recorder.stop()
    # AI 수행 중이면 루프를 세운다. 브라우저는 그대로 둔다 (FR-065·FR-032).
    await _cancel_agent(w)
    await w.session.apply(Command.PAUSE)
    if w.runner is not None and w.runner.running:
        settled = await w.runner.wait_for_boundary(PAUSE_SETTLE_TIMEOUT_S)
        if not settled:
            # 멈춘 것처럼 보여 주고 실제로는 아직 도는 상태를 만들지 않는다 (FR-087).
            w.session.add_edit_warning(
                f"Step 하나가 {PAUSE_SETTLE_TIMEOUT_S:.0f}초 안에 끝나지 않아 아직 "
                "실행 중입니다. 그 Step 이 끝나면 멈춥니다 — 지금 편집한 내용은 끝난 "
                "뒤의 목록에 적용됩니다."
            )
            await w.session.publish_edit_warnings()
    return view_of(w)


@router.post("/{session_id}/resume")
async def resume(
    session_id: str, state: State, body: ResumeRequest | None = None
) -> SessionView:
    """FR-038·FR-040c — 브라우저를 재시작하지 않고 **현재 상태에서** 이어서 실행한다.

    이어서 실행할 대상은 **편집된 목록**이다. 디스크의 정의를 계속 보면 사용자가 고친
    테스트가 아니라 고치기 전 테스트가 이어서 돈다 (`ReplayEngine.rebase`).

    러너가 이미 돌고 있으면(일시정지로 await 중) 새로 띄우지 않는다. 새로 띄우면 지금
    실행 중이던 Step 이 한 번 더 돈다.
    """
    w = work_of(session_id)
    skip_failed = body.skip_failed if body is not None else False

    # 005 FR-136 — 실패한 Step 을 **조용히** 지나가지 않는다.
    #
    # 이전에는 재개가 실패 Step 을 건너뛰고 다음 Step 만 돌린 뒤 「완료」로 표시했다.
    # 저장된 결과는 실패인데 화면은 완료라고 말했고, 사용자는 실패를 못 본 채 통과했다고
    # 믿고 넘어갈 수 있었다 (U-05). 결과 화면의 신뢰가 여기서 무너졌다.
    #
    # 넘기고 싶으면 `skip_failed` 로 **명시**한다. 그 경로의 결말은 `partial_pass` 다.
    if w.engine is not None and w.engine.has_failed_step():
        failed_index = w.engine.first_failed_index()
        if not skip_failed:
            raise conflict(
                ErrorCode.CANNOT_RESUME_PAST_FAILURE,
                f"Step {(failed_index or 0) + 1:02d} 이 실패해 이어서 갈 수 없습니다.",
                next_action=(
                    "그 Step 을 고친 뒤 이어가거나, 그 Step 부터 다시 실행하세요."
                ),
                failed_step_index=failed_index,
            )
        # 실패를 **지우지 않고** 건너뜀으로 남긴다. 지우면 결과에서 그 Step 이 왜 안
        # 돌았는지 알 수 없다.
        w.engine.note_skipped_failures()
        w.engine.clear_failed_steps()

    _apply(w, Command.RESUME)
    if w.inline is not None:
        w.inline.stop()

    # 사람 인수 후 "계속하기" 는 **AI 에게 돌려주는 것**이다 (FR-076·FR-077).
    # 별도 엔드포인트를 두지 않는다 — 사용자가 누르는 버튼이 하나이므로 계약도 하나다.
    if w.session.state is SessionState.TAKEOVER_RECORDING:
        from itb.recording.takeover import TakeoverRecording

        if isinstance(w.takeover, TakeoverRecording):
            w.takeover.stop()
        await w.session.apply(Command.RESUME)
        _start_agent(w, None)
        return view_of(w)

    engine = _ensure_engine(w, state)
    if engine is not None:
        # **편집된 목록을 실행 대상으로 삼는다.** 디스크의 정의를 계속 보면 사용자가 고친
        # 테스트가 아니라 고치기 전 테스트가 이어서 돈다.
        engine.rebase(w.steps)
    running = w.runner is not None and w.runner.running
    if running and w.runner is not None:
        w.runner.retarget(len(w.steps))
    await w.session.apply(Command.RESUME)
    if engine is not None and not running:
        await _start_runner(w, w.current_step_index, reset=False)
    return view_of(w)


@router.post("/{session_id}/run-from")
async def run_from(session_id: str, body: RunFromRequest, state: State) -> SessionView:
    """FR-039·FR-055 — 임의 Step 부터 실행. 브라우저 상태를 되돌리지 않는다 (FR-040c).

    이것이 FR-040d 가 말하는 "어긋난 화면을 정상화하는 수단" 중 하나다. 되돌리는 대신
    사용자가 고른 지점부터 다시 밟게 한다.
    """
    w = work_of(session_id)
    if body.step_index >= len(w.steps):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"Step {body.step_index} 이 없습니다. 총 {len(w.steps)}개입니다.",
        )
    _apply(w, Command.RUN_FROM)
    if w.inline is not None:
        w.inline.stop()
    engine = _ensure_engine(w, state)
    if engine is not None:
        engine.rebase(w.steps)
    w.current_step_index = body.step_index
    await w.session.apply(Command.RUN_FROM)
    if engine is not None:
        await _start_runner(w, body.step_index)
    return view_of(w)


@router.post("/{session_id}/record-actions:start")
async def record_actions_start(session_id: str) -> SessionView:
    """FR-036 — 일시정지 중 직접 동작 추가. 실제 창을 앞으로 가져온다 (FR-023a).

    기록된 Step 은 **일시정지 위치에** 삽입된다. 목록 끝에 붙이면 사용자가 보고 있는
    화면과 정의의 순서가 어긋난다.
    """
    w = work_of(session_id)
    require_paused(w)
    _apply(w, Command.RECORD_ACTIONS_START)
    await w.session.apply(Command.RECORD_ACTIONS_START)
    if w.inline is not None:
        await w.inline.start(w.current_step_index, author=Author.HUMAN)
    elif is_manipulation_phase(w.session.state):  # pragma: no cover - 방어적 경로
        await w.session.bring_tab_to_front(w.session.active_tab_index)
    return view_of(w)


# 사람이 직접 조작을 기록 중인 상태. 이 둘이 아니면 "중지" 할 대상이 없다.
RECORDING_STATES = frozenset({SessionState.RECORDING, SessionState.TAKEOVER_RECORDING})


def _is_recording(work: SessionWork) -> bool:
    return work.session.state in RECORDING_STATES


@router.post("/{session_id}/record-actions:stop")
async def record_actions_stop(session_id: str) -> SessionView:
    """녹화를 멈춘다.

    **녹화 중이 아니면 거절한다** (003 AP-020). 그러지 않으면 시작하지 않은 것을 멈추는
    조작이 성공으로 보이고, 사용자는 무언가 기록됐다고 믿게 된다.
    """
    w = work_of(session_id)
    if not _is_recording(w):
        raise conflict(
            ErrorCode.INVALID_TRANSITION,
            "지금 녹화 중이 아닙니다.",
            next_action="먼저 녹화를 시작한 뒤 중지하세요.",
            allowed=[c.value for c in allowed_commands(w.session.state)],
        )
    if w.inline is not None:
        w.inline.stop()
    else:  # pragma: no cover - 방어적 경로
        w.recorder.stop()
    _apply(w, Command.PAUSE)
    await w.session.apply(Command.PAUSE)
    return view_of(w)


# ─── AI 실패 시 선택 (US5) ────────────────────────────────────────────────


class AiChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choice: Literal["takeover", "retry", "skip", "abort"]
    """FR-071~FR-074. 정의되지 않은 값은 Pydantic 이 `422` 로 거절한다 (FR-043a)."""


class AiStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(min_length=1, max_length=8000)


class AiStepResponse(BaseModel):
    """FR-078~FR-081 — 만들어졌는지와 사유를 함께 돌려준다."""

    model_config = ConfigDict(extra="forbid")

    created: bool
    message: str
    step_id: str | None
    steps: list[Step]
    current_step_index: int
    state: SessionState

    error: ErrorBody | None = None
    """만들지 못한 경우의 계약 형태 오류 본문 (003 AP-032·AP-033).

    이 응답은 200 이다 — 요청 자체는 제대로 처리됐고, 세션도 살아 있다. 그래서 실패를
    HTTP 상태로 말할 수 없다. 그렇다고 `message` 문장만 주면 받는 쪽은 "AI 가 못한 것"과
    "제품이 깨진 것"을 문구로 짐작해야 한다 — 이 라운드가 없애려는 상황이다.
    """


@router.post("/{session_id}/ai-choice")
async def ai_choice(session_id: str, body: AiChoiceRequest, state: State) -> SessionView:
    """AI 실패 시 4선택지 (FR-071~FR-074).

    **`AI_BLOCKED` 에서만 받는다.** 다른 상태에서 오면 상태 기계가 거절한다 (FR-043a).
    어느 선택지에서도 브라우저를 되돌리지 않는다 — AI 가 남긴 화면이 출발점이다.
    """
    from itb.authoring.blocked import AiChoice, command_for

    w = work_of(session_id)
    choice = AiChoice(body.choice)
    command = command_for(choice)
    _apply(w, command)

    if choice is AiChoice.TAKEOVER:
        from itb.recording.takeover import TakeoverRecording

        takeover = TakeoverRecording(session=w.session, recorder=w.recorder)
        w.takeover = takeover
        await w.session.apply(command)
        await takeover.start()
        return view_of(w)

    if choice is AiChoice.ABORT:
        # 세션을 닫는 것은 사용자가 저장 여부를 확인한 뒤다 (FR-074). 여기서는 상태만
        # 옮기고, 실제 정리는 `stop` 이 한다 — 지금 닫으면 저장할 대상이 사라진다.
        await w.session.apply(command)
        return view_of(w)

    # retry / skip — 현재 상태에서 AI 에게 돌려준다 (FR-072·FR-073).
    await w.session.apply(command)
    note = (
        "같은 동작을 지금 화면 상태에서 다시 시도하세요."
        if choice is AiChoice.RETRY
        else (
            "그 동작은 건너뜁니다. Step 으로 기록하지 말고 다음 지시를 이어서 수행하세요."
        )
    )
    _start_agent_note(w, note)
    return view_of(w)


def _start_agent_note(work: SessionWork, note: str) -> None:
    """에이전트에게 한 줄을 덧붙여 이어서 돌린다 (FR-072·FR-073).

    새 지시문이 아니라 **같은 대화의 이어쓰기**다. 새로 시작하면 앞서 무엇을 했는지 잊고
    처음부터 다시 한다.
    """
    from itb.authoring.agent import AuthoringAgent
    from itb.authoring.tools import BrowserToolbox

    if not isinstance(work.agent, AuthoringAgent):  # pragma: no cover - ai 세션에서만 온다
        return
    # 재시도·건너뛰기는 새 예산으로 시작한다. 앞선 시도가 쓴 호출까지 상한에 포함하면
    # 사용자가 "다시" 를 누르는 순간 이미 상한에 닿아 있을 수 있다 (FR-066).
    if isinstance(work.toolbox, BrowserToolbox):
        work.toolbox.limits.reset()
    work.agent_task = asyncio.create_task(
        _run_agent(work.session.session_id, note)
    )


# ─── 자연어 Step 추가 (US6) ───────────────────────────────────────────────


@router.post("/{session_id}/ai-step")
async def ai_step(session_id: str, body: AiStepRequest, state: State) -> AiStepResponse:
    """일시정지 중 자연어로 Step 하나를 추가한다 (FR-078·FR-079).

    **`PAUSED` 게이트다.** 삽입 위치는 일시정지 위치다.

    **대상을 찾지 못하면 Step 을 만들지 않고 일시정지 상태를 유지한다** (FR-081) —
    실패할 것을 아는 Step 을 정의에 넣지 않는다.
    """
    from itb.authoring.agent import AuthoringAgent
    from itb.authoring.compiler import StepCompiler
    from itb.authoring.nl_step import add_step

    w = work_of(session_id)
    require_paused(w)

    if not isinstance(w.agent, AuthoringAgent):
        # 녹화로 시작한 세션에는 에이전트가 없다. 그때 만든다 — 자연어 Step 추가는
        # 작성 방식과 무관하게 쓸 수 있어야 한다 (FR-078).
        _build_agent(w, state)
    agent = w.agent
    compiler = w.compiler
    if not isinstance(agent, AuthoringAgent) or not isinstance(compiler, StepCompiler):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID, "자연어 Step 추가를 준비할 수 없습니다."
        )

    # 삽입 위치를 일시정지 위치로 맞춘다 (FR-079).
    compiler.insert_at = w.current_step_index
    try:
        result = await add_step(agent, compiler, body.instruction)
    except ValueError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    finally:
        compiler.insert_at = None

    failure: ErrorBody | None = None
    if not result.created:
        # 상태는 그대로 `PAUSED` 다. 실패를 이벤트로도 알리고, 응답에도 같은 본문을 싣는다.
        failure = ErrorBody(
            code=ErrorCode.AI_FAILED,
            message=result.message,
            detail={"session_id": session_id},
        )
        await w.session.emit(
            "ai_error", **error_payload(ErrorCode.AI_FAILED, result.message)
        )
    return AiStepResponse(
        created=result.created,
        message=result.message,
        step_id=result.step_id,
        steps=w.steps,
        current_step_index=w.current_step_index,
        state=w.session.state,
        error=failure,
    )


# ─── 중지 / 저장 ────────────────────────────────────────────────────────────


@router.post("/{session_id}/stop")
async def stop(session_id: str, state: State) -> SessionView:
    """중지 — **브라우저만 정리하고 기록은 남긴다.** DR-010·DR-013·DR-015.

    001 은 여기서 `sessions.close()` 와 `_WORK.pop()` 까지 했다. 그래서 중지 이후의
    저장이 `SESSION_NOT_FOUND` 로 실패했고, 화면을 붙잡아 두더라도 저장할 수 없었다 —
    사용자가 녹화한 것이 통째로 사라지는 결함의 절반이 이것이다 (research R1).

    이제 세션은 `REVIEW` 로 남는다. 실제 브라우저 창을 남길 이유는 없으므로 리코더·
    에이전트·미러·러너는 그대로 정리한다. **`SessionWork` 만 살려 둔다** — Step·변수·
    저장 스냅샷이 거기 있고, 저장에 그것이 필요하다.

    이벤트 채널도 닫지 않는다. 저장까지가 한 흐름이다.

    **이미 종료 상태인 세션에도 응답한다.** 실행이 끝난 세션을 닫는 것은 상태 전이가 아니라
    자원 정리다. 여기서 거절하면 브라우저와 세션 등록이 남아, 같은 테스트를 다시 실행할 때
    "이미 실행 중" 으로 막힌다 (FR-043).
    """
    w = work_of(session_id)
    already_terminal = w.session.state in TERMINAL_STATES

    # 005 FR-132 — **감지기를 먼저 끈다.** 아래에서 브라우저를 놓으면 close 이벤트가
    # 오는데, 그것은 사고가 아니라 우리가 시킨 일이다. 가드도 `REVIEW` 를 정상 종료로
    # 보지만(session_loss.NORMAL_END_STATES) 여기서 끄는 것이 원인 제거다.
    if w.loss_watcher is not None:
        w.loss_watcher.disarm()

    # 005 FR-131 — 결말을 정하기 전에 "사용자가 중지했다" 는 사실을 엔진에 남긴다.
    # 러너 취소와 유실 후처리가 각각 finalize 를 부를 수 있으므로, 인자로만 넘기면
    # 한쪽이 이 사실을 모른 채 실패로 확정한다.
    if w.engine is not None and not already_terminal:
        w.engine.note_stop_requested(w.current_step_index)

    w.recorder.stop()
    await _cancel_agent(w)
    if w.mirror is not None:
        await w.mirror.stop("세션을 종료했습니다.")
    if w.runner is not None:
        await w.runner.cancel()
    if w.inline is not None:
        w.inline.stop()

    if not already_terminal:
        _apply(w, Command.STOP)
        await w.session.apply(Command.STOP)
        # 중지도 결말이다 (005 FR-131). 결과를 남기지 않으면 "여기까지의 결과" 를 볼
        # 길이 없고, 사용자는 자기가 멈춘 실행이 있었다는 사실만 남는다.
        if w.engine is not None and not w.engine.finalized:
            with contextlib.suppress(Exception):
                await w.engine.finalize(False)

    # 브라우저 자원은 놓아 준다. 기록은 `_WORK` 에 남는다.
    await state.sessions.close(session_id)
    return view_of(w)


@router.post("/{session_id}/discard", status_code=204)
async def discard(session_id: str, state: State) -> None:
    """검토 중인 초안을 버린다. DR-014. **여기서 비로소 세션이 파괴된다.**

    확인 대화상자는 화면이 띄운다. 서버가 두 번 물으면 어느 쪽이 진짜 확인인지 모호해진다
    (contracts/rest-api-delta.md §7).
    """
    w = work_of(session_id)

    w.recorder.stop()
    await _cancel_agent(w)
    if w.mirror is not None:
        await w.mirror.stop("세션을 종료했습니다.")
    if w.runner is not None:
        await w.runner.cancel()
    if w.inline is not None:
        w.inline.stop()

    with contextlib.suppress(InvalidTransitionError):
        await w.session.apply(Command.DISCARD)

    await state.broker.drop(session_id)
    await state.sessions.close(session_id)
    _WORK.pop(session_id, None)


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
    # 005 FR-154 — 저장 시각을 세션에 남긴다. 화면이 응답 하나에만 의존하지 않고
    # 저장 여부를 스스로 알 수 있어야, 다시 그려도 미저장으로 되돌아가지 않는다 (U-09).
    w.saved_at = datetime.now(UTC)
    w.saved_snapshot = list(w.steps)
    return test


def _variables_for(w: SessionWork) -> list[dict[str, object]]:
    """Step 이 참조하는 변수를 정의로 만든다.

    **불러온 정의의 변수를 출발점으로 삼는다.** 세션에서 새로 포착한 것만 보면, 불러온
    테스트의 민감 변수가 비민감·빈 값으로 강등되어 재실행이 빈 값을 채운다 (FR-082 위반이자
    조용한 실패다).

    새로 나타난 이름의 판정 순서:

    1. 이 세션에서 민감 값으로 포착했다 → 민감 (값은 비밀 파일의 암호문에 있다)
    2. 비밀 파일에 같은 이름의 암호문이 있다 → 민감 (앞선 세션이 만든 것이다)
    3. 그 외 → 비민감. 값은 사용자가 정의 파일에서 채운다

    민감 변수는 **값을 갖지 않는다** — 실제 값은 비밀 파일의 암호문에 있다 (FR-082).
    """
    import re

    pattern = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
    referenced: set[str] = set()
    for step in w.steps:
        for text in (
            getattr(step, "value", None),
            getattr(getattr(step, "assertion", None), "value", None),
            getattr(step, "url", None),
        ):
            if isinstance(text, str):
                referenced.update(pattern.findall(text))

    base = {v.name: v for v in w.base_variables}
    captured = {c.variable_name for c in w.recorder.sensitive_captures}
    sealed = set(w.store.names()) if w.store is not None else set()

    out: list[dict[str, object]] = []
    for name in sorted(referenced):
        existing = base.get(name)
        if existing is not None:
            out.append(existing.model_dump(mode="json"))
        elif name in captured or name in sealed:
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
    # 005 FR-162 — 구독이 붙는 순간 현재 화면을 함께 준다. 화면이 변할 때까지
    # 기다리면 정적 화면에서는 영원히 비어 있다 (U-24).
    work = _WORK.get(session_id)
    current_frame = work.mirror.last_frame() if work is not None and work.mirror else None
    await hub.connect(websocket, current_frame)
    try:
        while True:
            # 수신은 연결 유지 확인 목적이며 내용은 무시한다 — 명령 경로가 아니다.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)
