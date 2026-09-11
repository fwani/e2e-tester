"""세션 엔드포인트. FR-023·FR-028~FR-043·FR-061. contracts/rest-api.md §세션.

**명령은 REST, 관찰은 WebSocket.** 이 라우터가 명령을 받아 상태 기계에 적용하고 즉시
반환한다. 실제 실행은 러너 태스크가 담당한다 (research R1).
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
from itb.api.ws.control_channel import (
    ChannelState,
    ControlRejected,
    state_message,
    validate,
)
from itb.authoring.rerecord import (
    EmptyRangeError,
    RangeNotContiguousError,
    RerecordTransaction,
    validate_range,
)
from itb.domain.draft import DRAFT_ID_PATTERN, Draft, compose_instruction
from itb.domain.run_pacing import DEFAULT_PACING, RunPacing, auto_pause, delay_ms
from itb.domain.run_result import RunScope, StepOutcome, scope_of
from itb.domain.step import Author, NavigateStep, Step
from itb.domain.test_case import (
    GROUP_PREFIX_PATTERN,
    RESERVED_PREFIX,
    TEST_ID_PATTERN,
    AuthoringMode,
    Test,
    Variable,
    derive_variables,
)
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
    is_control_phase,
    is_manipulation_phase,
    state_label,
)
from itb.execution.step_edits import StepNotFoundError, allocate_step_id
from itb.execution.step_executor import StepExecutor
from itb.mirror.prompts import BrowserPrompts
from itb.mirror.tab_switch import MirrorController
from itb.recording.inline_record import InlineRecording
from itb.recording.recorder import Recorder
from itb.secrets.keys import load_private_or_reason, load_public_or_none
from itb.secrets.resolver import VariableResolver
from itb.secrets.store import SecretStore
from itb.storage import preferences
from itb.storage.drafts import DraftNotFoundError
from itb.storage.repository import ProjectError, ProjectRepository
from itb.storage.yaml_io import DefinitionError

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
    saved_test_name: str | None = None
    """이 세션이 묶인 저장된 테스트의 **이름** (011 FR-362).

    **`saved_test_id` 만으로는 부족하다.** 화면은 「이름이 이미 있는가」로 저장 라벨과
    이름 요구를 정하는데(011 UC-011-4), id 만 알면 그 이름을 사용자에게 보여 줄 수도
    다시 저장할 때 실을 수도 없다 — 실제로 국면 띠가 이름 자리에 「TC-001」을 그리고
    있었고, 저장하려면 사용자가 이름을 처음부터 다시 쳐야 했다.

    저장된 테스트에서 세션을 열 때 채워지고, 저장할 때 갱신된다.
    """
    draft_name: str | None = None
    """출발한 초안의 제목 (014 FR-040).

    저장 이름의 기본값으로 화면에 되돌려 주기 위해 들고 있는다. **저장이 끝나면 초안
    파일이 사라지므로**, 그때 읽으려 해도 없다 — 출발할 때 받아 두는 것이 유일한 방법이다.
    """

    draft_group: str | None = None
    """출발한 초안의 소속 그룹 접두어 (014 FR-040a)."""

    draft_id: str | None = None
    """이 세션이 어느 초안에서 출발했는가 (014 US3 · FR-030·FR-032·FR-033).

    저장까지 들고 간다. 저장이 성공하면 (a) 초안의 희망 번호를 부여하려 시도하고
    (b) 초안의 설명·수행자를 테스트로 옮기고 (c) 초안 파일을 지운다.

    **새 세션 모드를 만들지 않았다.** 초안 녹화는 기존 AI 작성 경로에 지시문을 미리
    채워 진입하는 것뿐이다 — 상태 기계에 갈래를 늘리면 원칙 III 이 지키려는 것이
    복잡해지고, 원칙 I 이 막으려는 두 번째 작성 경로에 한 발 들여놓게 된다.
    """

    saved_at: datetime | None = None
    """마지막 저장 시각 (005 FR-154). 화면이 저장 성공을 스스로 알 수 있게 한다.

    **`saved_test_name` 과 다른 사실이다.** 이것은 「이 **세션에서** 저장했는가」이고
    그것은 「이 **테스트에** 이름이 있는가」다. 011 이전에는 저장 라벨이 이 값을 보고
    있었고, 그래서 저장된 테스트를 연 세션이 첫 저장 전까지 이름을 다시 물었다.
    """

    prompts: BrowserPrompts | None = None
    """브라우저 요구 가로채기 (010 FR-338·FR-339).

    **조작 국면에서 항상 켜져 있어야 한다** (research R7). 가로채지 않으면 대화상자가
    대상 페이지를 세우고, 헤드리스에서는 그 사실이 화면에 나타나지 않는다 — 사용자에게는
    「클릭했는데 아무 일도 없다」로 보인다.

    모드와 무관하게 붙이는 이유는 미러와 같다: 어느 국면에서든 대상 페이지가 대화상자를
    띄울 수 있고, 그때 멈추는 것은 국면을 가리지 않는다.
    """

    # ─── 조작 위치 (010 · data-model §6) ──────────────────────────────────
    control_surface: str = "mirror"
    """지금 조작이 어디서 이루어지는가. **기본은 미러다** (FR-352 이후).

    **전이는 사용자 요청으로만 일어난다** (FR-353). 서버가 상황을 판단해 바꾸지 않는다 —
    강등이나 처리할 수 없는 요구를 만나도 자동으로 창을 열지 않고, 화면이 전환 수단을
    그 자리에 보여 준다 (FR-353a).

    저장되지 않는다 (data-model 「저장 형식 변경 요약」).
    """

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

    # ─── 구간 재녹화 (016) ─────────────────────────────────────────────────
    rerecord: RerecordTransaction | None = None
    """진행 중인 구간 교체. 세션당 최대 하나 (data-model §1-2).

    **스냅샷을 들고 있지 않다.** FR-037 이 AI 의 편집 권한을 이 트랜잭션의
    `created_step_ids` 로 한정하므로 옛 구간과 구간 밖이 바뀌지 않는다 (research R7).

    `agent`·`compiler` 와 달리 타입을 그대로 쓴다 — `itb.authoring.rerecord` 는
    언어모델을 알지 못하는 순수 모듈이므로 API 계층이 항상 끌고 와도 비용이 없다.
    """

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
    def unsaved_step_ids(self) -> list[str]:
        """저장한 뒤에 **더해진** Step 의 id (011 FR-379).

        `has_unsaved_changes` 는 「무언가 달라졌는가」라는 한 값이고, 화면은 **어느 행이**
        아직 파일에 없는지를 행마다 표시해야 한다 (009 FR-310 이 편집 국면에 만든 그
        표식). 세션에서는 그 판정을 서버만 할 수 있다 — 저장 시점의 목록을 들고 있는
        것이 여기다.

        **고쳐진 Step 은 세지 않는다.** 이 표식의 뜻은 「파일에 없다」이고, 고친 것은
        파일에 있되 내용이 다른 것이라 다른 사실이다. 그것은 `has_unsaved_changes` 와
        국면 띠의 저장 상태 칩이 말한다.
        """
        saved = {s.id for s in self.saved_snapshot}
        return [s.id for s in self.steps if s.id not in saved]

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
        # 005 FR-135 — 사용자에게 보이는 문구에 세션 식별자를 넣지 않는다.
        #
        # 리포트는 중지 직후 화면에 "세션을 찾을 수 없습니다: f345e93a…" 라는 배너가
        # 뜨는 것을 봤다 (U-03). 내부 UUID 는 사용자가 할 수 있는 일과 아무 관계가
        # 없고, 화면을 읽는 사람에게는 잡음이자 불안 신호다.
        #
        # 식별자가 필요한 화면(그 세션으로 이동 등)은 `detail` 에서 받는다.
        raise not_found(
            ErrorCode.SESSION_NOT_FOUND,
            "세션이 이미 끝났습니다.",
            session_id=session_id,
        )
    return w


def mirror_of(session_id: str) -> MirrorController | None:
    """미러 제어기. 탭 라우터가 표시 탭을 바꿀 때 쓴다 (FR-030f).

    미러가 없어도(시작하지 못한 경우) 탭 전환 요청 자체는 성공해야 한다 — 미러 실패가
    사용자 조작을 막으면 안 된다 (FR-047b).
    """
    w = _WORK.get(session_id)
    return w.mirror if w is not None else None


def surface_of(w: SessionWork, surface: str) -> str:
    """조작 위치를 바꾸고 그 값을 돌려준다 (010 FR-349 · data-model §6).

    `control.py` 가 부른다. 값을 `SessionWork` 에 두는 이유는 화면이 세션 조회로 그것을
    다시 받을 수 있어야 하기 때문이다 — 이벤트만으로 두면 재연결한 화면이 조작 위치를
    잊는다 (`session_events.py` 의 "재전송하지 않는다" 와 같은 이유).
    """
    w.control_surface = surface
    return surface


def _control_phase_watcher(state: AppState, session_id: str):  # noqa: ANN202
    """국면이 바뀌면 조작 채널을 정리한다 (010 FR-342 · contracts §2).

    관찰 국면으로 전이하면 **서버가 사유와 함께 닫는다.** 화면이 안 보내는 것에 의존하지
    않는 것이 FR-342 의 요점이다 — 화면 단에서만 막으면 화면을 우회한 조작 경로가 남는다.

    조작 국면 사이의 전이(녹화 → 일시정지 등)에서는 닫지 않는다. 닫으면 사용자가 일시정지
    할 때마다 조작 통로가 끊기고 다시 붙기를 기다려야 한다.
    """

    async def watch(new_state: SessionState) -> None:
        control_phase = is_control_phase(new_state)

        # 010 FR-335 — 조작 국면에서는 무프레임 감시가 빨라진다. 조작이 화면을 바꾸지
        # 않을 때 2초를 기다리면 사용자는 그것을 「클릭이 안 먹었다」로 읽는다.
        w = _WORK.get(session_id)
        if w is not None and w.mirror is not None:
            with contextlib.suppress(Exception):
                w.mirror.set_control_phase(control_phase)

        channel = state.control.get(session_id)
        if channel is None or not channel.attached:
            return
        if control_phase:
            return
        await channel.close(
            f"'{state_label(new_state)}' 국면에서는 미러에서 조작할 수 없습니다. "
            "러너가 전진하는 중에 사람 조작이 끼어들면 같은 Step 이 두 번 돕니다."
        )

    return watch


def _frame_liveness_watcher(state: AppState, session_id: str):  # noqa: ANN202
    """프레임 흐름이 바뀌면 조작 채널의 상태를 옮긴다 (010 T088 · FR-346).

    **화면이 안 보내는 것에 의존하지 않는다.** 프론트도 `mirrorLive` 로 조작을 막지만,
    그것은 표시의 문제이고 이쪽은 통로의 문제다 — FR-342 가 「화면 단에서 막는 것으로
    충분하지 않다」고 정한 것과 같은 이유로 서버가 자기 상태를 갖는다.

    `close` 가 아니라 `suspend` 다. 닫으면 클라이언트가 다시 붙어야 하고, 프레임이 잠깐
    끊긴 것과 국면이 바뀐 것이 화면에서 같아 보인다 (data-model §3).
    """

    async def watch(alive: bool) -> None:
        channel = state.control.get(session_id)
        if channel is None or not channel.attached:
            return
        if alive:
            await channel.resume()
        else:
            await channel.suspend(
                "대상 화면이 끊겨 지금은 조작을 전달할 수 없습니다. "
                "화면이 멈춘 것이며 대상 페이지가 멈춘 것은 아닙니다."
            )

    return watch


def _frame_size(w: SessionWork) -> tuple[float | None, float | None]:
    """지금 표시 중인 프레임의 대상 화면 크기 (FR-333·FR-341).

    `None` 이면 프레임을 한 장도 받지 못한 상태다 — 그 상태에서는 좌표를 보낼 근거가
    없으므로 포인터 사건이 거절된다.
    """
    if w.mirror is None:
        return None, None
    frame = w.mirror.last_frame()
    if frame is None:
        return None, None
    width, height = frame.get("width"), frame.get("height")
    if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
        return None, None
    return float(width), float(height)


def _open_tabs(w: SessionWork) -> set[int]:
    """조작을 받을 수 있는 탭 번호들. 닫힌 탭은 뺀다 (FR-341)."""
    return {t.tab_index for t in w.session.tabs if not t.closed}


async def _cleanup_session_extras(
    state: AppState, w: SessionWork, session_id: str, reason: str
) -> None:
    """세션이 끝났다. 요구와 파일을 치운다 (010 FR-337b · research R7).

    **남은 요구를 응답 없이 버리지 않는다.** 가로챈 대화상자를 그대로 두면 그 페이지는
    영원히 멈춰 있고, 그 상태는 세션을 닫는 경로에서 시간 초과로 나타난다.

    **받은 파일은 세션보다 오래 남지 않는다** (FR-337b). 사용자가 보낸 것이므로 그 수명이
    세션의 수명을 넘어서는 안 된다.
    """
    if w.prompts is not None:
        with contextlib.suppress(Exception):
            await w.prompts.dismiss_all(reason)
    with contextlib.suppress(Exception):
        state.session_files.drop(session_id)


async def _close_control_channel(state: AppState, session_id: str, reason: str) -> None:
    """세션이 끝났다. 채널을 닫는다 (FR-347).

    **마지막 프레임이 남아 있어도 조작을 전달하지 않는다.** 보낼 대상이 없기 때문이다.
    """
    with contextlib.suppress(Exception):
        await state.control.drop(session_id, reason)


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

    mode: Literal["record", "replay", "ai", "rerecord"]
    """`rerecord` 는 016 의 구간 재녹화다 (contracts/api-contract.md §1).

    **`replay` 와 `ai` 를 합친 것이 아니다.** `authoring_mode` 가 `ai` 이면서 러너를
    도착점까지 돌린다 — 그 조합이 기존 세 모드 어디에도 없다 (research R5).
    `authoring_mode` 는 세션의 불변 속성이므로(001 DR-020) **만들 때 정해야 하고**,
    그래서 모드가 하나 늘었다.
    """
    test_id: str | None = Field(default=None, pattern=TEST_ID_PATTERN)
    """재실행·편집 대상 테스트.

    **패턴을 여기서 다시 쓰지 않는다** (014). 013 이 그룹 접두어를 도입했는데 이 자리는
    `^TC-\d{3}$` 로 남아 있었고, 그래서 그룹에 든 테스트(`USER-001`)를 재실행하거나
    편집하려는 요청이 **요청 검증에서 422 로 거절됐다**. 저장은 되는데 돌릴 수 없는
    테스트가 만들어지고 있었다.

    식별자 형식의 출처는 :data:`itb.domain.test_case.TEST_ID_PATTERN` 하나다.
    """
    start_url: str | None = Field(default=None, pattern=r"^https?://", max_length=2000)
    ai_instruction: str | None = Field(default=None, max_length=8000)

    draft_id: str | None = Field(default=None, pattern=DRAFT_ID_PATTERN)
    """초안에서 시작한다 (014 FR-030·FR-031).

    `record` 와 `ai` 둘 다에서 쓸 수 있다 — 초안은 **무엇을 할지**의 기록이고, 그것을
    손으로 녹화해 채우는 것도 온전한 방법이다. 화면이 두 갈래를 나란히 보여 주면서
    한쪽만 초안과 이어지면, 「저장하면 이 초안은 사라집니다」라는 안내가 거짓이 된다
    (수렴 2회차).

    지시문은 `ai` 에서만 쓰인다. `ai_instruction` 을 함께 주면 **그것이 쓰이고**
    (사용자가 고친 것), 없으면 서버가 초안에서 짓는다.
    """

    pacing: RunPacing | None = None
    """실행 속도 (004 FR-102). 없으면 저장된 취향, 그것도 없으면 기본값.

    **무인 실행은 명시해야 한다.** 저장된 취향이 CI 를 느리게 만들지 않는 유일한 방법이
    요청에 `fast` 를 넣는 것이다 (contracts/rest-api.md §1).
    """

    rerecord_step_ids: list[str] = Field(default_factory=list, max_length=500)
    """다시 만들 구간의 Step id (016 FR-015). `rerecord` 모드에서만 쓴다.

    **순번이 아니라 id 다.** 재녹화 도중 새 Step 이 구간 시작 위치에 삽입되므로 옛
    구간의 순번은 계속 밀린다 (data-model §1-1).

    받은 순서는 상관없다 — 화면의 체크 순서는 사용자가 누른 순서다. 목록 순서로
    정규화하고 **연속인지만** 본다 (`validate_range`).
    """

    pause_before_index: int | None = Field(default=None, ge=0)
    """편집을 위해 멈출 지점 (006 FR-200·FR-201). `replay` 모드에서만 쓴다.

    선행 Step 을 실행한 뒤 이 인덱스의 Step 을 실행하기 **전에** 멈춘다. 이것이 없으면
    사용자는 편집 상태에 닿기 위해 **달리는 실행을 「일시정지」로 잡아야** 했고, 빠르게
    통과하는 테스트에서는 잡을 창이 사실상 없었다 (006 E-06).

    생략하면 지금과 완전히 같다 — 기존 클라이언트에 영향이 없다.
    """


class SavedTestView(Test):
    """저장 응답 — 저장된 테스트에 **이번 저장에서만 참인 사실 둘**을 덧붙인다 (014).

    `Test` 를 상속하는 이유는 기존 소비자를 깨지 않기 위해서다. 화면과 계약 검증이
    읽던 필드가 그대로 있고, 두 필드는 더해질 뿐이다. 저장 형식에는 들어가지 않는다 —
    `repo.write_test` 는 `Test` 로 직렬화하므로 파일에는 이 둘이 남지 않는다.
    """

    from_draft: str | None = None
    """어느 초안에서 왔는가. 초안에서 출발한 세션에만 있다."""

    desired_id_taken: dict[str, str] | None = None
    """희망 번호를 주지 못했을 때만 실린다 — ``{"wanted": ..., "assigned": ...}``.

    **조용히 다른 번호를 주지 않는다** (FR-032). 사용자의 설계서에는 원래 번호가 적혀
    있고, 그것이 제품과 어긋났다는 사실을 지금 말하지 않으면 나중에 발견하게 된다.
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


class DraftOriginView(BaseModel):
    """세션이 출발한 초안. 저장 이름·그룹의 기본값이 된다 (FR-040·FR-040a)."""

    model_config = ConfigDict(extra="forbid")
    draft_id: str
    name: str
    group_prefix: str


class RerecordView(BaseModel):
    """진행 중인 구간 교체 (016 · contracts/api-contract.md §3).

    **`Step` 에 아무것도 더하지 않는다** (불변식 7). 화면이 `range_step_ids` 와 목록을
    대조해 「교체 대상」을 계산한다. Step 에 그 필드를 두면 (a) 작성 주체 외의 의미가
    저장 형식에 생겨 원칙 I 이 흔들리고 (b) 확정되지 않은 상태가 디스크에 내려갈 문이
    열린다 (FR-029 위반의 문).
    """

    model_config = ConfigDict(extra="forbid")

    range_step_ids: list[str]
    """교체 대상 (옛 Step). 확정 전까지 목록에 남아 있다 (FR-024)."""

    created_step_ids: list[str]
    """이번 세션이 만든 Step. AI 편집 도구의 권한 범위이기도 하다 (FR-037)."""

    can_commit: bool
    """확정할 수 있는가 (불변식 10).

    **서버가 판정한다.** 화면이 조건을 복제하면 서버와 갈리고, 갈리면 활성으로 그린
    버튼이 눌린 뒤 거절된다 (005 U-01 의 형태).
    """


class SessionView(BaseModel):
    """WebSocket 재연결 시 전체 상태 동기화에 쓴다 (contracts/websocket.md)."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    state: SessionState
    state_label: str
    test_id: str | None
    unsaved_step_ids: list[str] = Field(default_factory=list)
    """저장한 뒤 더해진 Step 의 id (011 FR-379).

    **선택 필드다** — 없이 온 응답도 그대로 읽힌다.
    """
    test_name: str | None = None
    """저장된 테스트의 이름 (011 FR-362). 아직 저장된 적 없으면 `None`.

    **선택 필드다** — 없이 온 응답도 그대로 읽힌다.
    """
    draft: DraftOriginView | None = None
    """이 세션이 어느 초안에서 출발했는가 (014 · 수렴 2회차).

    **화면 기억에만 두면 잃는다.** 초안 정보가 `App` 상태에만 있어서, 살아 있는 세션으로
    돌아오거나 브라우저를 새로 고치면 저장 이름·그룹의 기본값이 사라졌다 — 사용자는
    설계서에 이미 적힌 것을 다시 쳐야 했다 (FR-040b 위반).

    `SessionWork` 는 처음부터 `draft_id` 를 들고 있었으므로, 여기 실어 보내면 화면이
    세션 조회로 다시 받을 수 있다. `control_surface` 가 같은 이유로 이 응답에 실린다.
    """
    current_step_index: int
    steps: list[Step]
    tabs_open: int
    active_tab_index: int
    mirrored_tab_index: int
    control_surface: str = "mirror"
    """지금 조작이 어디서 이루어지는가 — `"mirror"` 또는 `"window"` (010 FR-349).

    **이벤트만으로 두면 재연결한 화면이 조작 위치를 잊는다.** `SessionWork` 는 이 값을
    처음부터 들고 있었고 그 주석도 「화면이 세션 조회로 다시 받을 수 있어야 한다」고
    적어 두었는데, 정작 이 응답에 실리지 않아 **쓰이지 않는 값**이었다. 새로 고치면
    서버는 「창」이라고 알고 화면은 「미러」라고 아는 상태가 됐다.
    """

    window_unavailable_reason: str | None = None
    """실제 창으로 옮겨 갈 수 없는 이유. 옮겨 갈 수 있으면 `None` (010 FR-351 · FR-234).

    **참·거짓이 아니라 문장을 보낸다.** 화면은 쓸 수 없는 조작을 이유와 함께 비활성으로
    두어야 하는데(FR-234), 그 이유를 화면이 자기 사전에 갖고 있으면 서버가 거절할 때
    쓰는 문장과 갈린다 — `wording.ts` 의 O13 옆 주석이 그것을 금지한 이유이며, 그 결정을
    깨지 않고 요구를 채우는 방법이 **서버가 문장을 주는 것**이다.

    사용자 보고 2026-09-09 「실제창에서 조작하기 변환이 안됨」이 이것이 없던 상태다.
    화면은 눌러 본 뒤에야 안 된다는 것을 알 수 있었고, 그 전에는 서버가 창 없는 세션에도
    「옮겼다」고 답하고 있었다.
    """

    edit_warnings: list[str]
    recorder_warnings: list[str]
    allowed_commands: list[str]
    has_unsaved_changes: bool = False
    """저장하지 않은 편집이 있는가. 중지 확인 대화상자의 근거다 (FR-042)."""

    pause_before_index: int | None = None
    """**아직 도달하지 않은** 목표 지점 (009 FR-293·FR-294 · 계약 §4-3).

    「이 자리에 추가」가 만든 세션은 지정한 Step 앞에서 멈춘다. 그 목표가 여기 실린다.

    **왜 스냅샷에 싣는가.** 목표를 화면 상태로만 들고 있으면 새로 고침 한 번에 「어디서
    멈출 예정인지」가 사라진다. 005 U-18 이 같은 형태였고 — Step별 결과가 화면 로컬 상태에만
    있어 다시 그리면 사라졌다 — 그 고침이 `step_results` 였다. 같은 근거로 여기 있다.

    화면이 이 값으로 문구를 가른다.

      값이 있고 실행 중        「Step nn 앞에서 멈춥니다 — 지금 Step mm」
      값이 없고 일시정지       도착했다. 일시정지 문구는 지금과 같다
      값이 있고 실패한 Step 有  「Step nn 에 도달하기 전에 Step mm 에서 실패했습니다」

    셋째 줄이 FR-294 다 — **도달하지 못했는데 도달한 것처럼 말하지 않는다.** 판정을 화면이
    조립하지 않는다: 「도달했는가」는 목표가 남아 있는지로 결정되며 그 사실은 러너가 안다.
    """

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

    rerecord: RerecordView | None = None
    """진행 중인 구간 교체 (016). 없으면 일반 세션이다.

    화면은 `authoring_mode === "ai"` 와 이 값이 있는지로 재녹화 세션을 안다 —
    `mode` 를 뷰에 싣지 않는 이유는 그것이 **만들 때의 요청**이지 지금 상태가 아니기
    때문이다.
    """

    saved_at: datetime | None = None
    """마지막 저장 시각 (005 FR-154). `None` 이면 미저장.

    저장 성공을 화면이 **스스로** 알 수 있게 한다. 이전에는 저장 응답 말고는 저장 여부를
    알 방법이 없어, 화면을 다시 그리면 다시 미저장처럼 보였고 사용자는 목록으로 나가
    확인해야 했다 (U-09).
    """


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    group: str | None = Field(default=None, pattern=GROUP_PREFIX_PATTERN)
    """어느 그룹에 저장할 것인가 (013 FR-443).

    **생략하면 그룹 없음이고 식별자는 지금과 같은 `TC-###` 이다** (FR-445b · SC-627) —
    그룹을 쓰지 않는 사용자에게 이 기능이 비용을 지우지 않는다.

    이미 저장된 테스트를 다시 저장할 때는 **무시된다.** 그룹을 바꾸는 것은 식별자와
    산출물을 옮기는 일이고, `POST /api/tests:move` 가 그것을 원자성 규약과 함께 한다 —
    저장에 자산 이동을 숨기지 않는다.
    """


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
    from itb.api.routes.control import window_unavailable_reason
    from itb.execution.state_machine import allowed_commands

    return SessionView(
        draft=_draft_origin(w),
        session_id=w.session.session_id,
        state=w.session.state,
        state_label=state_label(w.session.state),
        test_id=w.saved_test_id or w.session.test_id,
        test_name=w.saved_test_name,
        unsaved_step_ids=w.unsaved_step_ids,
        current_step_index=w.current_step_index,
        steps=w.steps,
        tabs_open=len(w.session.open_tabs()),
        active_tab_index=w.session.active_tab_index,
        mirrored_tab_index=w.session.mirrored_tab_index,
        control_surface=w.control_surface,
        # 판정은 `control.py` 하나가 갖는다 — 화면이 보는 값과 전환 요청이 받는 답이
        # 갈리면, 눌러도 되는 버튼이 눌리지 않거나 그 반대가 된다.
        window_unavailable_reason=window_unavailable_reason(w.session),
        edit_warnings=list(w.session.edit_warnings),
        recorder_warnings=list(w.recorder.warnings),
        allowed_commands=[c.value for c in allowed_commands(w.session.state)],
        has_unsaved_changes=w.has_unsaved_changes,
        pacing=w.session.pacing,
        pause_before_index=w.runner.pause_before_index if w.runner is not None else None,
        authoring_mode=w.authoring_mode,
        step_results=_progress_of(w),
        pause_settled=_pause_settled(w),
        run_scope=scope_of(w.engine.start_index if w.engine is not None else 0),
        run_start_index=w.engine.start_index if w.engine is not None else 0,
        rerecord=_rerecord_view(w),
        saved_at=w.saved_at,
    )


def _rerecord_view(w: SessionWork) -> RerecordView | None:
    """진행 중인 교체를 뷰로 옮긴다 (016).

    **끝난 트랜잭션은 `None` 이다.** 확정·버리기 뒤에도 남겨 두면 화면이 재녹화 띠를
    계속 그리고, 사용자는 아직 무언가 진행 중이라고 읽는다.
    """
    tx = w.rerecord
    if tx is None or tx.settled:
        return None
    return RerecordView(
        range_step_ids=list(tx.range.step_ids),
        created_step_ids=list(tx.created_step_ids),
        can_commit=tx.can_commit,
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
    if body.mode in ("replay", "rerecord"):
        if body.test_id is None:
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                f"{body.mode} 모드는 test_id 가 필요합니다.",
            )
        try:
            existing_test = repo.read_test(body.test_id)
        except ProjectError as exc:
            raise not_found(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc

    # 014 FR-030 — 초안에서 시작한다. **기존 AI 작성 경로 그대로다.**
    draft: Draft | None = None
    instruction = body.ai_instruction
    if body.draft_id is not None:
        if body.mode in ("replay", "rerecord"):
            # 재실행·재녹화는 이미 저장된 테스트를 다루므로 초안과 상관이 없다.
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                "초안에서 시작하는 것은 새로 만들 때만 됩니다.",
            )
        try:
            draft = repo.drafts.read(body.draft_id)
        except DraftNotFoundError as exc:
            raise not_found(ErrorCode.DRAFT_NOT_FOUND, str(exc)) from exc
        # 사용자가 고친 지시문이 있으면 그것이 이긴다 (FR-031). 화면이 미리 채워 보여
        # 주고 고칠 수 있게 한 것이 뜻을 가지려면, 고친 값이 실제로 쓰여야 한다.
        if body.mode == "ai" and (instruction is None or not instruction.strip()):
            instruction = compose_instruction(draft)

    if body.mode == "ai":
        # FR-085 — 경계에서 검증한다. 길이·공백 규칙은 작성 계층이 갖는다.
        from itb.authoring.agent import validate_instruction

        try:
            validate_instruction(instruction)
        except ValueError as exc:
            raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc

    rerecord_range = None
    if body.mode == "rerecord":
        assert existing_test is not None  # noqa: S101 - 위에서 이미 거절했다
        # 016 FR-015·FR-016 — **구간을 경계에서 검증한다.** 브라우저를 띄운 뒤에
        # 거절하면 사용자는 창이 떴다 사라지는 것을 보고, 무엇이 잘못됐는지는 그
        # 뒤에야 안다.
        if body.ai_instruction is not None:
            # 재녹화의 지시는 채팅으로 온다 (api-contract §1). 두 입구를 두면
            # 사용자는 어느 쪽에 써야 하는지 모른다.
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                "재녹화는 지시문 대신 대화로 진행합니다.",
                next_action="세션을 연 뒤 대화로 지시하세요.",
            )
        try:
            rerecord_range = validate_range(
                list(existing_test.steps), list(body.rerecord_step_ids)
            )
        except StepNotFoundError as exc:
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                str(exc),
                next_action="화면을 새로 고친 뒤 다시 고르세요.",
            ) from exc
        except (EmptyRangeError, RangeNotContiguousError) as exc:
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                str(exc),
                next_action="이어진 Step 을 하나 이상 고르세요.",
            ) from exc

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
        ai_instruction=instruction,
        saved_test_id=body.test_id,
        draft_id=draft.draft_id if draft is not None else None,
        draft_name=draft.name if draft is not None else None,
        draft_group=draft.group_prefix if draft is not None else None,
    )
    if existing_test is not None:
        # 011 FR-362 — 이름을 함께 들린다. 이것이 없으면 화면이 저장할 때 이름을 다시 묻는다.
        work.saved_test_name = existing_test.name
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
    work.loss_watcher = SessionLossWatcher(
        session, on_lost=_loss_handler(state, session.session_id)
    )
    work.loss_watcher.attach()
    work.mirror = MirrorController(session)
    # FR-030a·FR-030f — **새 탭이 열리면 미러가 그리로 옮겨간다.** 없으면 표시 탭이 0 에
    # 남고, 조작 통로는 표시 탭을 따르므로 (FR-317) 새 탭을 보며 누른다고 믿는 조작이
    # 전부 탭 0 으로 간다 — 새 탭의 Step 이 하나도 생기지 않는다.
    work.mirror.follow_new_tabs()
    # 010 FR-338 — 브라우저 요구 가로채기. **컨텍스트 단위로 건다** — 새 탭에도 자동으로
    # 붙는다 (리코더가 `add_init_script` 를 컨텍스트에 거는 것과 같은 이유다).
    work.prompts = BrowserPrompts(emit=session.emit)
    work.prompts.attach(session.context)
    # 010 FR-342 — 국면이 조작 채널의 개폐를 정한다. 채널이 상태를 감시하는 것이 아니라
    # **상태가 채널에 알린다.** 반대로 두면 그 사이에 관찰 국면으로 열린 채널이 남는 창이
    # 생기고, 그 창에서 사람 조작이 러너와 겹친다 (FR-315).
    session.observe_state(_control_phase_watcher(state, session.session_id))
    # 010 T088 FR-346 — 프레임이 끊기면 조작 채널을 `suspended` 로 내리고, 회복하면
    # 되돌린다. **닫지 않는다**: 프레임이 잠깐 끊긴 것과 국면이 바뀐 것이 화면에서 같아
    # 보이면 사용자는 「화면이 멈춘 것」과 「페이지가 멈춘 것」을 구분할 수 없다.
    work.mirror.observe_liveness(_frame_liveness_watcher(state, session.session_id))

    if body.mode == "record":
        await session.apply(Command.BEGIN_RECORD)
        work.recorder.start(author=Author.HUMAN)
        await session.bring_tab_to_front(0)
    elif body.mode == "replay":
        assert existing_test is not None  # noqa: S101 - 위에서 이미 거절했다
        await session.apply(Command.BEGIN_REPLAY)
        _build_engine(work, state, existing_test)
        # 006 FR-200 — 범위를 경계에서 검증한다 (FR-211). 벗어난 값을 그대로 넘기면
        # 러너가 영원히 만나지 못하는 지점을 기다리며 끝까지 돈다.
        if body.pause_before_index is not None and body.pause_before_index >= len(
            existing_test.steps
        ):
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                f"멈출 Step 위치가 범위를 벗어났습니다: {body.pause_before_index} "
                f"(Step {len(existing_test.steps)}개)",
            )
        await _start_runner(
            work, start_index=0, pause_before_index=body.pause_before_index
        )
    elif body.mode == "rerecord":
        # 016 (research R5 · api-contract §1) — **순서가 계약이다.**
        #
        #   1. 러너를 도착점까지 돌린다   ← 이 구간에 에이전트 태스크는 없다
        #   2. 러너가 멈춘다
        #   3. 그제서야 에이전트를 만든다 (`chat` 핸들러가 첫 턴에서)
        #
        # 원칙 II 가 요구하는 것은 임포트 금지가 아니라 **재실행 중 언어모델 호출
        # 금지**다. `itb.api` 는 `execution-no-llm` 계약의 `source_modules` 에 없으므로
        # 린터가 이 겹침을 잡지 못한다 — `tests/test_principle_ii_timeline.py` 가
        # 러너와 에이전트 태스크의 생존 구간이 겹치지 않음을 본다 (불변식 6).
        assert existing_test is not None  # noqa: S101 - 위에서 이미 거절했다
        assert rerecord_range is not None  # noqa: S101 - 위에서 만들었다
        await session.apply(Command.BEGIN_REPLAY)
        _build_engine(work, state, existing_test)
        arrival = next(
            i
            for i, st in enumerate(existing_test.steps)
            if st.id == rerecord_range.first
        )
        work.rerecord = RerecordTransaction(range=rerecord_range, arrival_index=arrival)
        await _start_runner(work, start_index=0, pause_before_index=arrival)
    else:
        await session.apply(Command.BEGIN_AI)
        _build_agent(work, state)
        _start_agent(work, body.ai_instruction)

    await work.mirror.show(0)
    # 010 FR-335 — 첫 국면도 알려 준다. 상태 관찰자는 **전이**에서만 불리므로, 녹화로
    # 시작한 세션은 통보를 한 번도 받지 못한 채 관찰 국면의 주기로 돈다.
    work.mirror.set_control_phase(is_control_phase(session.state))
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


async def _run_agent(
    session_id: str, instruction: str | None = None, answer: str | None = None
) -> None:
    """에이전트를 돌리고 결과를 이벤트로 바꾼다 (FR-059·FR-063·FR-067·FR-069).

    **취소는 결과로 기록하지 않는다** — 사용자가 일시정지·중지한 것이며 실패가 아니다.

    들어오는 길이 셋이고 **끝나는 길은 하나다** (2026-09-10). 새 지시(`instruction`)·
    사람이 준 답(`answer`)·사람 인수 후 재개(둘 다 없음) 가운데 무엇으로 시작했든
    막힘·실패·완료 처리는 아래 한 곳을 지난다 — 갈라 두면 한쪽에서 `ai_blocked` 를
    빠뜨리고, 그 세션은 선택지 없이 멈춘 것처럼 보인다.
    """
    from itb.authoring.agent import AgentStatus, AuthoringAgent
    from itb.authoring.blocked import enter_blocked

    work = _WORK.get(session_id)
    if work is None or not isinstance(work.agent, AuthoringAgent):
        return
    agent: AuthoringAgent = work.agent

    try:
        if answer is not None:
            outcome = await agent.resume_with_answer(answer)
        elif instruction is None:
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
    work: SessionWork,
    start_index: int,
    reset: bool = True,
    pause_before_index: int | None = None,
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
        pause_before_index=pause_before_index,
    )
    work.runner = runner
    # 태스크만 띄우고 즉시 반환한다. 실제 Step 실행은 요청 수명과 분리된다 (research R1).
    runner.start()


def _loss_handler(state: AppState, session_id: str):  # noqa: ANN201 - LossHandler 를 만든다
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
        # 010 FR-347 — 세션이 유실됐다. 남은 마지막 프레임을 클릭해도 보낼 대상이 없다.
        await _close_control_channel(state, session_id, reason)
        await _cleanup_session_extras(state, w, session_id, reason)
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

    **상태를 보지 않는다.** 실행 중이든 끝났든 유실됐든 받는다.

    실행 중에 받는 이유는 처음부터 그랬다 — 진행 중인 Step 을 끊지 않으며, 러너가 다음
    Step 경계에서 이 값을 다시 읽는다. 브라우저에는 아무 명령도 보내지 않는다
    (원칙 III 계열).

    취향 파일에도 남긴다 — FR-109 의 "다음 실행에서 마지막 선택이 기본값" 은 실행 중
    변경까지 반영되어야 성립한다. **다만 그 쓰기 실패로 이 호출이 실패하지는 않는다.**
    속도는 이미 바뀌었고, 취향을 못 남긴 것 때문에 실행을 방해할 이유가 없다. 대신
    조용히 넘기지 않고 ``preference_saved: false`` 로 알린다.

    ## 2026-09-09 — 거절 둘을 없앴다 (사용자 결정)

    이전에는 종료 상태(``TERMINAL_STATES``)와 유실(``LOST``)을 거절했다. 사용자가 그
    거절을 문제로 지목했다: 「속도 선택은 실행중이든 아니든 바꿀수있어야함」.

    **거절에 실질적 근거가 없었다.** 이 연산이 하는 일은 두 가지뿐이다 — 세션의 값을
    바꾸고, 취향 파일에 남긴다. 끝난 세션에는 그 값을 읽을 러너가 없으므로 첫 번째는
    아무 효과가 없고, 두 번째는 **바로 그 상태에서 가장 쓸모 있다**: 실행이 끝난 화면에는
    「처음부터 실행」이 있고 (국면 `finished`), 여기서 고른 값이 그 실행의 속도가 된다
    (FR-109). 거절은 사용자가 다음 실행을 준비하는 것을 막고 있었다.

    화면 쪽도 같은 사정이었다 — 권한표가 이 거절을 비활성으로 옮겨 그리느라, 실행 종료
    화면의 속도 컨트롤이 「실행이 이미 끝났습니다」를 달고 눌리지 않는 채 서 있었다.

    유실도 함께 받는다. 세션은 사라졌지만 취향은 사용자의 것이고, 유실 화면에서 남은
    길이 「저장하고 처음부터 다시 실행」이므로 그 실행의 속도를 여기서 정하게 된다.
    """
    w = work_of(session_id)
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
            # 005 FR-146 — **전이 안내로 표시한다.** 실행이 끝나면 러너가 걷는다.
            #
            # 재점검 U-04-a: 실행이 끝난 뒤에도 이 문장이 남아, 같은 화면의 배지가
            # 「실행 종료」라고 말하는 옆에서 「아직 실행 중」이라고 말했다.
            w.session.add_edit_warning(
                f"Step 하나가 {PAUSE_SETTLE_TIMEOUT_S:.0f}초 안에 끝나지 않아 아직 "
                "실행 중입니다. 그 Step 이 끝나면 멈춥니다 — 지금 편집한 내용은 끝난 "
                "뒤의 목록에 적용됩니다.",
                transient=True,
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

    choice: Literal["takeover", "answer", "retry", "skip", "abort"]
    """FR-071~FR-074 + `answer`. 정의되지 않은 값은 Pydantic 이 `422` 로 거절한다 (FR-043a)."""

    answer: str | None = Field(default=None, max_length=8000)
    """`choice="answer"` 일 때 사람이 준 답 (2026-09-10 사용자 결정).

    **다른 선택지에서는 받지 않는다** — 아래 라우트가 거절한다. 실어 보내 놓고 무시하면
    사용자는 자기가 쓴 문장이 전달됐다고 믿는다.
    """


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

    # **답변은 `answer` 에서만 뜻이 있다.** 다른 선택지에 실려 오면 조용히 버리지 않는다 —
    # 사용자는 자기가 쓴 문장이 AI 에게 갔다고 믿게 된다.
    answer = (body.answer or "").strip()
    if choice is AiChoice.ANSWER and not answer:
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            "답변이 비어 있습니다. AI 에게 알려 줄 내용을 적어 주세요.",
        )
    if choice is not AiChoice.ANSWER and answer:
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"「{choice.value}」 에는 답변을 실을 수 없습니다.",
        )

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

    if choice is AiChoice.ANSWER:
        # 2026-09-10 — 사람이 답을 줬다. **같은 대화에 이어 붙여** 그 자리에서 이어 간다.
        await w.session.apply(command)
        _resume_agent_with_answer(w, answer)
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


def _resume_agent_with_answer(work: SessionWork, answer: str) -> None:
    """사람이 준 답으로 에이전트를 이어서 돌린다 (2026-09-10 사용자 결정).

    `_start_agent_note` 와 갈라 둔다. 그쪽이 나르는 것은 **제품이 만든 지시**(「다시
    시도하세요」)이고 이것은 **사람이 쓴 문장**이다 — 에이전트가 둘을 같은 무게로 읽으면
    안 되므로 문장을 감싸는 일은 `resume_with_answer` 가 갖는다.
    """
    from itb.authoring.agent import AuthoringAgent

    if not isinstance(work.agent, AuthoringAgent):  # pragma: no cover - ai 세션에서만 온다
        return
    # 예산을 되돌리는 일은 `resume_with_answer` 가 한다 — 답변 경로의 규칙을 한 곳에 둔다.
    work.agent_task = asyncio.create_task(
        _run_agent(work.session.session_id, answer=answer)
    )


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
    # 010 FR-347 — 세션이 끝나면 조작을 받지 않는다. 미러를 세우기 **전에** 닫는다:
    # 순서가 반대면 프레임이 멈춘 사이에 마지막 조작이 들어올 수 있다.
    await _close_control_channel(state, session_id, "세션을 종료했습니다.")
    await _cleanup_session_extras(state, w, session_id, "세션을 종료했습니다.")
    if w.mirror is not None:
        await w.mirror.stop("세션을 종료했습니다.")
    if w.runner is not None:
        await w.runner.cancel()
    if w.inline is not None:
        w.inline.stop()

    # 005 FR-146 — 중지로 끝난 실행에서도 전이 안내를 걷는다.
    #
    # 러너가 정상 종료 경로에서 이것을 하지만, 취소는 그 경로를 지나지 않는다. 러너의
    # `finally` 에 두지 않는 이유는 그 블록이 완료 신호만 올려야 하기 때문이다 —
    # 거기서 실패하면 실행 완료를 기다리는 모든 것이 영구히 멈춘다.
    if w.session.clear_transient_edit_warnings():
        await w.session.publish_edit_warnings_now()

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
    await _close_control_channel(state, session_id, "세션을 종료했습니다.")
    await _cleanup_session_extras(state, w, session_id, "세션을 종료했습니다.")
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


def _require_known_group(repo: ProjectRepository, prefix: str | None) -> None:
    """모르는 그룹에 저장하지 않는다 (013 FR-443).

    막지 않으면 `groups` 에 없는 접두어의 테스트가 생기고, 목록에서 「정의가 없는 그룹」
    으로 뜬다 — 사용자가 만든 적 없는 그룹이다.
    """
    if prefix is None:
        return
    if prefix not in {g.prefix for g in repo.read_project().groups}:
        raise not_found(ErrorCode.GROUP_NOT_FOUND, f"그런 그룹이 없습니다: {prefix}")


@router.post("/{session_id}/save")
async def save(session_id: str, body: SaveRequest, state: State) -> SavedTestView:
    """FR-028·FR-029 — 이름을 지정해 테스트로 저장한다. Step 0개면 거절한다.

    초안에서 출발한 세션이면 여기서 셋을 더 한다 (014 FR-032·FR-033):
    희망 번호 부여 시도 · 설명·수행자 옮기기 · 초안 삭제.
    """
    w = work_of(session_id)
    repo = state.require_repository()

    if not w.steps:
        raise bad_request(
            ErrorCode.STEP_LIST_EMPTY,
            "Step 이 없어 저장할 수 없습니다. 먼저 동작을 기록하세요.",
        )

    draft = _draft_of(repo, w)
    wanted: str | None = None

    if w.saved_test_id is not None:
        test_id = w.saved_test_id
    elif draft is not None:
        # 014 FR-032 — 초안의 희망 번호를 **그대로 주려 시도한다.**
        wanted = draft.desired_test_id
        test_id = _allocate_for_draft(repo, draft)
    else:
        _require_known_group(repo, body.group)
        test_id = repo.allocate_test_id(body.group or RESERVED_PREFIX)

    variables = _variables_for(w)
    test = Test(
        id=test_id,
        name=body.name,
        # 014 FR-071 — 초안의 설명·수행자를 테스트로 옮긴다. 이것이 없으면 다시
        # 내보낼 때 두 칸이 비어 **왕복이 끊긴다**.
        description=draft.description if draft is not None else None,
        actor=draft.actor if draft is not None else None,
        authoring_mode=w.authoring_mode,
        start_url=w.start_url,
        variables=variables,
        steps=w.steps,
        ai_instruction=w.ai_instruction,
    )

    # **디스크에는 `Test` 를 쓴다.** 아래 두 필드는 이번 저장에서만 참인 사실이라
    # 파일에 남으면 다음에 읽을 때 거짓이 되고, `Test` 가 `extra="forbid"` 이므로
    # 애초에 읽히지도 않는다 (이 검증이 그것을 잡았다).
    repo.write_test(test)

    view = SavedTestView(
        **test.model_dump(),
        from_draft=draft.draft_id if draft is not None else None,
        desired_id_taken=(
            {"wanted": wanted, "assigned": test_id}
            if wanted is not None and wanted != test_id
            else None
        ),
    )

    if draft is not None:
        # FR-033 — 저장이 성공하면 초안은 사라진다. **저장 뒤에 지운다** — 먼저 지우면
        # 저장이 실패했을 때 초안도 테스트도 없는 상태가 된다.
        with contextlib.suppress(DraftNotFoundError, OSError):
            repo.drafts.delete(draft.draft_id)
        w.draft_id = None

    w.saved_test_id = test_id
    # 011 — 방금 정해진 이름이 이후 저장의 기본값이 된다. 다시 묻지 않기 위한 값이다.
    w.saved_test_name = test.name
    # 005 FR-154 — 저장 시각을 세션에 남긴다. 화면이 응답 하나에만 의존하지 않고
    # 저장 여부를 스스로 알 수 있어야, 다시 그려도 미저장으로 되돌아가지 않는다 (U-09).
    w.saved_at = datetime.now(UTC)
    w.saved_snapshot = list(w.steps)
    return view


def _draft_origin(w: SessionWork) -> DraftOriginView | None:
    """세션이 출발한 초안을 응답에 실을 형태로 (수렴 2회차).

    **세션이 만들어질 때 받아 둔 값을 쓴다.** 여기서 저장소를 읽지 않는 이유는 둘이다 —
    `view_of` 는 상태가 바뀔 때마다 불리므로 디스크를 건드릴 자리가 아니고, 저장이 끝나면
    초안 파일이 사라지므로 읽으려 해도 없다. 화면이 필요한 것은 「출발할 때 무엇이었나」다.
    """
    if w.draft_id is None or w.draft_name is None:
        return None
    return DraftOriginView(
        draft_id=w.draft_id,
        name=w.draft_name,
        group_prefix=w.draft_group or RESERVED_PREFIX,
    )


def _draft_of(repo: ProjectRepository, w: SessionWork) -> Draft | None:
    """이 세션이 출발한 초안. 없거나 이미 사라졌으면 ``None``.

    사라진 것을 오류로 만들지 않는다 — 다른 창에서 지웠을 수 있고, 그때 저장을 막으면
    사용자는 방금 녹화한 것을 잃는다.
    """
    if w.draft_id is None:
        return None
    try:
        return repo.drafts.read(w.draft_id)
    except (DraftNotFoundError, DefinitionError):
        return None


def _allocate_for_draft(repo: ProjectRepository, draft: Draft) -> str:
    """초안의 희망 번호를 주되, 이미 쓰였으면 빈 번호를 준다 (FR-032).

    **조용히 다른 번호를 주지 않는다** — 부른 쪽이 둘을 비교해 사용자에게 알린다.
    """
    wanted = draft.desired_test_id
    if wanted is not None and repo.find_test_path(wanted) is None:
        return wanted
    return repo.allocate_test_id(draft.group_prefix)


def _variables_for(w: SessionWork) -> list[dict[str, object]]:
    """세션의 Step 이 참조하는 변수를 정의로 만든다.

    **판정은 `itb.domain.test_case.derive_variables()` 가 한다** (006 T005·T006). 이 함수는
    세션에서 재료를 꺼내 넘기는 얇은 껍데기다.

    옮긴 이유: 정의 편집(`PUT /api/tests/{id}/definition`)도 같은 판정을 해야 한다. 두 벌이면
    한쪽에서 민감 표시가 강등되고, 재실행이 빈 값을 채운다 (006 FR-214 · research R5).
    """
    return derive_variables(
        w.steps,
        base_variables=w.base_variables,
        captured_names={c.variable_name for c in w.recorder.sensitive_captures},
        sealed_names=w.store.names() if w.store is not None else (),
    )



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


# ─── WebSocket (조작, 양방향) ──────────────────────────────────────────────
#
# 010 · contracts/mirror-control.md §2. **위 관찰 소켓과 별개의 소켓이다** — 그쪽의
# 단방향 계약은 그대로 유지된다 (research R4). 한 소켓이 프레임 밀기와 조작 받기를 같이
# 하면 조작 폭주가 프레임 전달을 막고 그 역도 성립한다 (FR-336).


@router.websocket("/{session_id}/control")
async def session_control(websocket: WebSocket, session_id: str) -> None:
    """조작 사건을 받아 대상 브라우저로 흘린다 (FR-314 · contracts §2).

    **조작 국면에서만 수립된다** (FR-342). 세션이 없거나 관찰 국면이면 수립 자체를
    거절한다 — 화면 단에서 막는 것으로 충분하지 않다.

    **세션당 하나** (명세 Out of Scope — 한 세션당 한 조작자). 이미 열려 있으면 새 접속을
    거절한다. 둘이 붙으면 같은 화면에 두 사람의 조작이 섞이고, 어느 조작이 어느 Step 이
    되었는지 아무도 답할 수 없다.

    **성공 응답을 보내지 않는다** (contracts §5 불변식 5). 성공의 증거는 프레임이다.
    거절과 채널 상태만 돌려준다.
    """
    state: AppState = websocket.app.state.itb

    w = _WORK.get(session_id)
    if w is None:
        await websocket.close(code=4404, reason="세션이 이미 끝났습니다.")
        return
    if not is_control_phase(w.session.state):
        await websocket.close(
            code=4403,
            reason=f"'{state_label(w.session.state)}' 국면에서는 미러에서 조작할 수 없습니다.",
        )
        return

    channel = state.control.channel(session_id)
    if channel.attached:
        await websocket.close(code=4409, reason="이 세션은 이미 다른 곳에서 조작 중입니다.")
        return

    controller = await w.mirror.attach_input() if w.mirror is not None else None
    await websocket.accept()
    await channel.open(websocket, controller)
    await websocket.send_json(state_message(ChannelState.OPEN, None))

    try:
        while True:
            event = await websocket.receive_json()
            await _handle_control_event(state, session_id, event)
    except WebSocketDisconnect:
        channel.detached()
    except Exception:  # noqa: BLE001 - 조작 채널의 장애가 실행을 실패시키지 않는다 (FR-348)
        channel.detached()
    finally:
        # 끌어놓기 도중 끊겼을 수 있다. 누른 채로 남은 포인터를 놓는다 (FR-318).
        if w.mirror is not None:
            with contextlib.suppress(Exception):
                await w.mirror.detach_input()


async def _handle_control_event(state: AppState, session_id: str, event: object) -> None:
    """조작 사건 하나. **검증 → 전달**이고 그 사이에 아무것도 없다.

    Step 을 만들지 않는다 (헌법 원칙 I). 조작은 대상 브라우저의 입력이 될 뿐이고, Step 은
    대상 페이지의 리코더가 만든다 — 주입한 입력이 페이지에서 `isTrusted: true` 이벤트가
    되기 때문에 미러 조작과 창 조작이 리코더에게 구분되지 않는다 (research R1).
    """
    channel = state.control.get(session_id)
    if channel is None:
        return
    w = _WORK.get(session_id)
    if w is None:
        await channel.close("세션이 이미 끝났습니다.")
        return

    if not channel.can_accept(w.session.state):
        await channel.send_rejection(
            ControlRejected(
                f"'{state_label(w.session.state)}' 국면에서는 조작을 전달하지 않습니다."
                if not is_control_phase(w.session.state)
                else "지금은 화면이 끊겨 조작을 전달할 수 없습니다."
            )
        )
        return

    width, height = _frame_size(w)
    try:
        clean = validate(event, frame_width=width, frame_height=height, tabs=_open_tabs(w))
    except ControlRejected as exc:
        await channel.send_rejection(exc)
        return

    # FR-317 — **보고 있는 탭**에 보낸다. 표시 탭과 조작 대상이 갈리면 사용자가 보지 않는
    # 화면이 조작된다. 요청한 탭이 표시 탭과 다르면 거절한다 — 조용히 다른 탭에 보내지 않는다.
    mirror = w.mirror
    controller = mirror.input if mirror is not None else None
    if controller is None:
        await channel.send_rejection(
            ControlRejected("조작 통로가 준비되지 않았습니다.", clean["kind"])
        )
        return
    if clean["tab"] != controller.tab_index:
        await channel.send_rejection(
            ControlRejected(
                f"지금 보고 있는 탭은 {controller.tab_index} 입니다. "
                "보고 있지 않은 탭은 조작하지 않습니다.",
                clean["kind"],
            )
        )
        return

    if clean["kind"] == "file.attach":
        # 010 T065 — **파일 자체는 이 통로로 오지 않는다** (research R6). REST 로 올린
        # 것의 식별자만 오고, 여기서 실제 경로로 바꾼다. 큰 페이로드가 조작 채널을 막으면
        # FR-336 이 깨지므로 채널의 책임을 좁게 유지한다.
        #
        # **순서 보장**: 클라이언트가 업로드 응답을 받은 뒤에 이 사건을 보낸다. 서버가
        # 아직 오지 않은 파일을 기다리게 만드는 경로를 두지 않는다 (research 미해결 항목).
        store = state.session_files.get(session_id)
        paths: list[str] = []
        for file_id in clean.get("fileIds", []):
            path = store.path_of(file_id) if store is not None else None
            if path is None:
                await channel.send_rejection(
                    ControlRejected(
                        "그 파일을 찾을 수 없습니다. 다시 올려 주세요.", clean["kind"]
                    )
                )
                return
            paths.append(str(path))
        clean["paths"] = paths

    try:
        await controller.dispatch(clean)
    except Exception as exc:  # noqa: BLE001 - 전달 실패가 실행을 실패시키지 않는다 (FR-348)
        await channel.send_rejection(
            ControlRejected(f"조작을 전달하지 못했습니다: {type(exc).__name__}", clean["kind"])
        )
