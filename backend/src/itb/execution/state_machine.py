"""RunSession 상태 기계. 헌법 원칙 III (Stateful Interactive Runner).

이 모듈이 원칙 III의 구현체다. 순수 상태 전이 로직만 담으며 Playwright 를 임포트하지
않는다 — 그래야 브라우저 없이 전수 테스트할 수 있다.

    ┌──────────┐
    │ STARTING │
    └────┬─────┘
   ┌─────┼─────────────────┐
   ▼     ▼                 ▼
RECORDING REPLAYING   AI_RUNNING ──실패──▶ AI_BLOCKED
   │        │              │                  │
   └────────┴──── PAUSE ───┘         직접수행 ─┤─ 재시도 → AI_RUNNING
            ▼                                 │  건너뛰기 → AI_RUNNING
        ┌────────┐                            ▼  종료 → STOPPED
        │ PAUSED │◀──────────── TAKEOVER_RECORDING
        └───┬────┘   계속하기
            ▼
   COMPLETED / FAILED / STOPPED        LOST (어느 상태에서든)

**불변식**

1. `PAUSED`·`AI_BLOCKED` 에서 브라우저 세션은 절대 종료되지 않는다 (FR-032, FR-069).
2. 편집 명령은 `PAUSED` 에서만 받는다 (FR-035a).
3. 편집은 테스트 정의만 바꾸고 브라우저에 명령을 보내지 않는다 (FR-040a~c).
4. 정의되지 않은 명령은 거절하고 현재 상태와 가능한 행동을 알린다 (FR-043a).
5. 세션 유실 후에는 저장과 처음부터 재실행만 허용한다 (FR-041c).
"""

from __future__ import annotations

from enum import StrEnum


class SessionState(StrEnum):
    STARTING = "starting"
    RECORDING = "recording"
    """사람이 직접 녹화 중. 실제 브라우저 창에서 조작한다 (FR-023a)."""

    REPLAYING = "replaying"
    """저장된 테스트를 결정적으로 실행 중. 언어모델을 호출하지 않는다 (FR-044)."""

    AI_RUNNING = "ai_running"
    AI_BLOCKED = "ai_blocked"
    """AI 가 막혔고 사용자 선택을 기다린다. **세션은 유지된다** (FR-069)."""

    TAKEOVER_RECORDING = "takeover_recording"
    """AI 실패 후 사람이 이어받아 녹화 중 (FR-071)."""

    PAUSED = "paused"
    """**브라우저 세션이 유지되는 유일한 편집 가능 상태** (FR-032, FR-035)."""

    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    LOST = "lost"
    """브라우저 세션이 외부 요인으로 유실됐다 (FR-041)."""


class Command(StrEnum):
    """세션에 보낼 수 있는 명령."""

    BEGIN_RECORD = "begin_record"
    BEGIN_REPLAY = "begin_replay"
    BEGIN_AI = "begin_ai"
    PAUSE = "pause"
    RESUME = "resume"
    RUN_FROM = "run_from"
    STOP = "stop"
    EDIT_STEPS = "edit_steps"
    """Step 삽입·수정·삭제·순서 변경. `PAUSED` 에서만 (FR-035a)."""

    RECORD_ACTIONS_START = "record_actions_start"
    RECORD_ACTIONS_STOP = "record_actions_stop"
    AI_BLOCK = "ai_block"
    CHOOSE_TAKEOVER = "choose_takeover"
    CHOOSE_RETRY = "choose_retry"
    CHOOSE_SKIP = "choose_skip"
    CHOOSE_ABORT = "choose_abort"
    FINISH_PASS = "finish_pass"
    FINISH_FAIL = "finish_fail"
    SESSION_LOST = "session_lost"
    SAVE = "save"
    """저장. 상태를 바꾸지 않지만 허용 여부가 상태에 따라 다르다."""


ACTIVE_STATES: frozenset[SessionState] = frozenset(
    {
        SessionState.STARTING,
        SessionState.RECORDING,
        SessionState.REPLAYING,
        SessionState.AI_RUNNING,
        SessionState.AI_BLOCKED,
        SessionState.TAKEOVER_RECORDING,
        SessionState.PAUSED,
    }
)
"""브라우저 세션이 살아 있는 상태들."""

TERMINAL_STATES: frozenset[SessionState] = frozenset(
    {
        SessionState.COMPLETED,
        SessionState.FAILED,
        SessionState.STOPPED,
        SessionState.LOST,
    }
)

SESSION_HELD_STATES: frozenset[SessionState] = frozenset(
    {SessionState.PAUSED, SessionState.AI_BLOCKED}
)
"""**불변식 1** — 이 상태에서 세션을 종료하면 원칙 III·FR-069 위반이다."""

PAUSABLE_STATES: frozenset[SessionState] = frozenset(
    {
        SessionState.RECORDING,
        SessionState.REPLAYING,
        SessionState.AI_RUNNING,
        SessionState.TAKEOVER_RECORDING,
    }
)
"""일시정지할 수 있는 상태. `TAKEOVER_RECORDING` 도 포함한다 — 사람이 이어받는 중에도
멈춰서 고칠 수 있어야 한다 (checklist CHK052 가 지적한 미정의 지점)."""

MIRROR_ACTIVE_STATES: frozenset[SessionState] = ACTIVE_STATES
"""**미러는 모든 활성 상태에서 동작한다** (FR-047d).

조작 국면에서도 읽기 전용으로 화면을 계속 보여준다. 일시정지·AI 실패 대기에서도
마지막 화면을 계속 보여준다 — 브라우저 세션이 유지되고 있음을 사용자가 눈으로 확인하는
수단이기 때문이다 (FR-033).
"""

# 상태별 허용 명령 → 다음 상태. 여기에 없는 (상태, 명령) 조합은 모두 거절된다 (불변식 4).
_TRANSITIONS: dict[SessionState, dict[Command, SessionState]] = {
    SessionState.STARTING: {
        Command.BEGIN_RECORD: SessionState.RECORDING,
        Command.BEGIN_REPLAY: SessionState.REPLAYING,
        Command.BEGIN_AI: SessionState.AI_RUNNING,
        Command.STOP: SessionState.STOPPED,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.RECORDING: {
        Command.PAUSE: SessionState.PAUSED,
        Command.STOP: SessionState.STOPPED,
        Command.SAVE: SessionState.RECORDING,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.REPLAYING: {
        Command.PAUSE: SessionState.PAUSED,
        # FR-039·FR-055 — 결과 화면의 "실패한 Step부터 실행" 은 새 세션을 만든 뒤 곧바로
        # 실행 위치를 옮긴다. 그 사이에 일시정지를 끼우게 하면 브라우저가 한 번 더 멈췄다
        # 풀리고, 사용자가 요청하지 않은 상태 전이가 화면에 보인다.
        Command.RUN_FROM: SessionState.REPLAYING,
        Command.STOP: SessionState.STOPPED,
        Command.FINISH_PASS: SessionState.COMPLETED,
        Command.FINISH_FAIL: SessionState.FAILED,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.AI_RUNNING: {
        Command.PAUSE: SessionState.PAUSED,
        Command.AI_BLOCK: SessionState.AI_BLOCKED,
        Command.STOP: SessionState.STOPPED,
        Command.FINISH_PASS: SessionState.COMPLETED,
        Command.FINISH_FAIL: SessionState.FAILED,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.AI_BLOCKED: {
        # 4선택지 (FR-070). 세션은 유지된다.
        Command.CHOOSE_TAKEOVER: SessionState.TAKEOVER_RECORDING,
        Command.CHOOSE_RETRY: SessionState.AI_RUNNING,
        Command.CHOOSE_SKIP: SessionState.AI_RUNNING,
        Command.CHOOSE_ABORT: SessionState.STOPPED,
        # CHK051 이 지적한 미정의 지점: 4선택지 대신 일시정지·저장을 요청하는 경우.
        Command.PAUSE: SessionState.PAUSED,
        Command.SAVE: SessionState.AI_BLOCKED,
        Command.STOP: SessionState.STOPPED,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.TAKEOVER_RECORDING: {
        Command.RESUME: SessionState.AI_RUNNING,
        Command.PAUSE: SessionState.PAUSED,
        Command.RECORD_ACTIONS_STOP: SessionState.TAKEOVER_RECORDING,
        Command.STOP: SessionState.STOPPED,
        Command.SAVE: SessionState.TAKEOVER_RECORDING,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.PAUSED: {
        Command.EDIT_STEPS: SessionState.PAUSED,
        Command.RECORD_ACTIONS_START: SessionState.RECORDING,
        Command.RESUME: SessionState.REPLAYING,
        Command.RUN_FROM: SessionState.REPLAYING,
        Command.SAVE: SessionState.PAUSED,
        Command.STOP: SessionState.STOPPED,
        Command.SESSION_LOST: SessionState.LOST,
    },
    # 불변식 5 — 유실 후에는 저장만 허용한다. 이어서 실행·편집은 불가하다.
    SessionState.LOST: {Command.SAVE: SessionState.LOST},
    SessionState.COMPLETED: {},
    SessionState.FAILED: {},
    SessionState.STOPPED: {},
}

_COMMAND_LABELS: dict[Command, str] = {
    Command.BEGIN_RECORD: "녹화 시작",
    Command.BEGIN_REPLAY: "실행 시작",
    Command.BEGIN_AI: "AI 수행 시작",
    Command.PAUSE: "일시정지",
    Command.RESUME: "계속하기",
    Command.RUN_FROM: "이 Step부터 실행",
    Command.STOP: "중지",
    Command.EDIT_STEPS: "Step 편집",
    Command.RECORD_ACTIONS_START: "직접 동작 추가",
    Command.RECORD_ACTIONS_STOP: "직접 동작 추가 종료",
    Command.AI_BLOCK: "AI 실패 처리",
    Command.CHOOSE_TAKEOVER: "직접 수행",
    Command.CHOOSE_RETRY: "AI에게 다시",
    Command.CHOOSE_SKIP: "건너뛰기",
    Command.CHOOSE_ABORT: "종료",
    Command.FINISH_PASS: "실행 완료",
    Command.FINISH_FAIL: "실행 실패",
    Command.SESSION_LOST: "세션 유실",
    Command.SAVE: "저장",
}

_STATE_LABELS: dict[SessionState, str] = {
    SessionState.STARTING: "브라우저 실행 중",
    SessionState.RECORDING: "녹화 중",
    SessionState.REPLAYING: "실행 중",
    SessionState.AI_RUNNING: "AI 수행 중",
    SessionState.AI_BLOCKED: "AI 실패 — 선택 대기",
    SessionState.TAKEOVER_RECORDING: "사람이 녹화 중",
    SessionState.PAUSED: "일시정지",
    SessionState.COMPLETED: "완료",
    SessionState.FAILED: "실패",
    SessionState.STOPPED: "중지됨",
    SessionState.LOST: "세션 유실",
}


class InvalidTransitionError(Exception):
    """정의되지 않은 명령. 현재 상태와 가능한 행동을 함께 알린다 (FR-043a).

    조용히 무시하거나 부분 적용하지 않는다.
    """

    def __init__(self, state: SessionState, command: Command) -> None:
        self.state = state
        self.command = command
        self.allowed = allowed_commands(state)
        allowed_text = ", ".join(_COMMAND_LABELS[c] for c in self.allowed) or "없음"
        super().__init__(
            f"현재 상태가 '{state_label(state)}' 이므로 "
            f"'{_COMMAND_LABELS[command]}' 을 처리할 수 없습니다. "
            f"지금 가능한 행동: {allowed_text}"
        )


def state_label(state: SessionState) -> str:
    """사용자에게 보여줄 상태 이름."""
    return _STATE_LABELS[state]


def command_label(command: Command) -> str:
    return _COMMAND_LABELS[command]


def allowed_commands(state: SessionState) -> tuple[Command, ...]:
    """그 상태에서 처리할 수 있는 명령 목록."""
    return tuple(_TRANSITIONS.get(state, {}))


def can(state: SessionState, command: Command) -> bool:
    return command in _TRANSITIONS.get(state, {})


def next_state(state: SessionState, command: Command) -> SessionState:
    """전이 결과를 돌려준다. 정의되지 않은 조합이면 `InvalidTransitionError`."""
    table = _TRANSITIONS.get(state, {})
    if command not in table:
        raise InvalidTransitionError(state, command)
    return table[command]


def holds_browser_session(state: SessionState) -> bool:
    """이 상태에서 브라우저 세션이 살아 있어야 하는가."""
    return state in ACTIVE_STATES


def is_editable(state: SessionState) -> bool:
    """**불변식 2** — 편집은 `PAUSED` 에서만 (FR-035·FR-035a)."""
    return state is SessionState.PAUSED


def mirror_should_run(state: SessionState) -> bool:
    """**FR-047d** — 미러는 모든 활성 상태에서 동작한다."""
    return state in MIRROR_ACTIVE_STATES


def is_manipulation_phase(state: SessionState) -> bool:
    """조작 국면인가. 실제 브라우저 창을 앞으로 가져와야 한다 (FR-023a·FR-030e)."""
    return state in {SessionState.RECORDING, SessionState.TAKEOVER_RECORDING}


def is_observation_phase(state: SessionState) -> bool:
    """관찰 국면인가 (FR-047)."""
    return state in {SessionState.REPLAYING, SessionState.AI_RUNNING}


def uses_llm(state: SessionState) -> bool:
    """이 상태가 언어모델을 쓰는가.

    `REPLAYING` 이 True 를 돌려주면 원칙 II 위반이다. 테스트로 고정한다.
    """
    return state in {SessionState.AI_RUNNING, SessionState.AI_BLOCKED}
