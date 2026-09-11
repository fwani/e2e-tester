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
    REVIEW = "review"
    """중지 후 검토 (DR-010~DR-014).

    **종료 상태가 아니다.** 브라우저는 닫혔지만 기록된 Step 은 살아 있어 보고·고치고
    저장할 수 있다. 001 의 `STOPPED` 는 아무 명령도 받지 않아, 중지하는 순간 녹화 결과가
    통째로 유실됐다 — 그것이 이 라운드가 고치는 결함이다 (research R1).
    """

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
    CHOOSE_ANSWER = "choose_answer"
    """사람이 **답을 주고** AI 에게 돌려준다 (2026-09-10 사용자 결정).

    `CHOOSE_RETRY` 와 도착 상태는 같지만 뜻이 다르다 — 그쪽은 「같은 것을 다시 해 봐라」
    이고 이것은 「막힌 것에 대한 답이 여기 있다」다. 갈라 두는 이유는 거절 문구다:
    상태 기계가 명령 이름으로 사유를 만들므로, 합치면 답변이 거절될 때 「AI에게 다시」로
    안내된다.
    """

    CHOOSE_RETRY = "choose_retry"
    CHOOSE_SKIP = "choose_skip"
    CHOOSE_ABORT = "choose_abort"
    FINISH_PASS = "finish_pass"
    FINISH_FAIL = "finish_fail"
    SESSION_LOST = "session_lost"
    SAVE = "save"
    """저장. 상태를 바꾸지 않지만 허용 여부가 상태에 따라 다르다."""

    DISCARD = "discard"
    """검토 중인 초안을 버린다 (DR-014). **여기서 비로소 세션이 파괴된다.**"""


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

REVIEW_STATES: frozenset[SessionState] = frozenset({SessionState.REVIEW})
"""**브라우저는 없지만 기록은 살아 있는 상태** (DR-010~DR-014).

`ACTIVE_STATES` 도 `TERMINAL_STATES` 도 아니다. 활성이 아닌 이유는 브라우저 세션이
닫혔기 때문이고, 종료가 아닌 이유는 편집·저장 명령을 받기 때문이다. 001 에는 이 범주가
없어 중지가 곧 기록 유실이었다.
"""

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
        Command.STOP: SessionState.REVIEW,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.RECORDING: {
        Command.PAUSE: SessionState.PAUSED,
        Command.STOP: SessionState.REVIEW,
        Command.SAVE: SessionState.RECORDING,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.REPLAYING: {
        Command.PAUSE: SessionState.PAUSED,
        # FR-039·FR-055 — 결과 화면의 "실패한 Step부터 실행" 은 새 세션을 만든 뒤 곧바로
        # 실행 위치를 옮긴다. 그 사이에 일시정지를 끼우게 하면 브라우저가 한 번 더 멈췄다
        # 풀리고, 사용자가 요청하지 않은 상태 전이가 화면에 보인다.
        Command.RUN_FROM: SessionState.REPLAYING,
        Command.STOP: SessionState.REVIEW,
        Command.FINISH_PASS: SessionState.COMPLETED,
        Command.FINISH_FAIL: SessionState.FAILED,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.AI_RUNNING: {
        Command.PAUSE: SessionState.PAUSED,
        Command.AI_BLOCK: SessionState.AI_BLOCKED,
        Command.STOP: SessionState.REVIEW,
        Command.FINISH_PASS: SessionState.COMPLETED,
        Command.FINISH_FAIL: SessionState.FAILED,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.AI_BLOCKED: {
        # 4선택지 (FR-070). 세션은 유지된다.
        Command.CHOOSE_TAKEOVER: SessionState.TAKEOVER_RECORDING,
        Command.CHOOSE_ANSWER: SessionState.AI_RUNNING,
        Command.CHOOSE_RETRY: SessionState.AI_RUNNING,
        Command.CHOOSE_SKIP: SessionState.AI_RUNNING,
        Command.CHOOSE_ABORT: SessionState.REVIEW,
        # CHK051 이 지적한 미정의 지점: 4선택지 대신 일시정지·저장을 요청하는 경우.
        Command.PAUSE: SessionState.PAUSED,
        Command.SAVE: SessionState.AI_BLOCKED,
        Command.STOP: SessionState.REVIEW,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.TAKEOVER_RECORDING: {
        Command.RESUME: SessionState.AI_RUNNING,
        Command.PAUSE: SessionState.PAUSED,
        Command.RECORD_ACTIONS_STOP: SessionState.TAKEOVER_RECORDING,
        Command.STOP: SessionState.REVIEW,
        Command.SAVE: SessionState.TAKEOVER_RECORDING,
        Command.SESSION_LOST: SessionState.LOST,
    },
    SessionState.PAUSED: {
        Command.EDIT_STEPS: SessionState.PAUSED,
        Command.RECORD_ACTIONS_START: SessionState.RECORDING,
        # 016 (research R4) — **AI 가 이어 만드는 자리.** 위 `RECORD_ACTIONS_START` 와
        # 대칭이다: 사람이 이어 녹화하는 자리가 있으면 AI 가 이어 만드는 자리도 있어야
        # 한다. 016 의 채팅 턴과 구간 재녹화가 여기로 들어온다.
        #
        # ## 원칙 II 와의 관계 — 2026-09-11 사용자 결정
        #
        # 이 한 줄은 「일시정지를 경유해 AI 상태에 도달할 수 없다」는 옛 단언을 깬다.
        # 깨도 되는 이유는 **헌법이 이미 이 동작을 요구하기 때문**이다:
        #
        #   원칙 III — "Steps executed while paused — recorded by direct user operation,
        #   **or added via natural language** — MUST be captured into the same Step Model
        #   and inserted at the paused position."
        #
        # 헌법이 한편에서 요구하는 것을 다른 편에서 금지할 수는 없다. 따라서 원칙 II 의
        # "replay path" 는 **저장된 Step 의 자동 실행**을 뜻하고, 사용자가 손으로
        # 일시정지하는 순간 그 경로를 벗어나 작성으로 들어간다.
        #
        # 그리고 제품은 이 선을 **이미 넘고 있었다.** `ai_step`(US6)이 재실행을
        # 일시정지한 세션에서 언어모델을 부른다. 옛 단언이 그것을 못 잡은 이유는 하나뿐
        # 이다 — 그 경로가 상태 전이를 하지 않아서. 즉 옛 단언은 「LLM 호출」이 아니라
        # 「상태 이름」을 지키고 있었다.
        #
        # 그래서 016 은 약한 단언을 **더 강한 단언으로 갈아 끼운다**:
        #   - 여기(전이): 자동으로는 못 간다. `BEGIN_AI` 라는 사용자 명령으로만 간다
        #   - `tests/test_principle_ii_timeline.py`: **러너가 도는 동안 드라이버 호출 0회**
        # 상태 이름이 아니라 실제 호출을 본다 — 이것이 원칙 II 가 요구한 것이다.
        #
        # 턴이 끝나면 호출자가 `PAUSE` 를 적용해 돌아온다 (기존 `AI_RUNNING` 행).
        # 막힘·5선택지도 기존 경로 그대로다 — **이 한 줄이 016 의 유일한 전이 변경이다.**
        #
        # 상태를 `PAUSED` 로 둔 채 플래그로 「AI 가 도는 중」을 표현하는 방법도 있었다
        # (`ai_step` 이 지금 그렇게 한다). 쓰지 않은 이유: 막힘을 표현하려면
        # `PAUSED → AI_BLOCKED` 를 더해야 하고, 그러면 5선택지의 복귀 지점
        # (`CHOOSE_* → AI_RUNNING`)이 재녹화에서만 달라져야 한다 — **전이표가 세션
        # 종류를 알아야 하는 상태**가 된다. 전이표는 지금 세션 종류를 모르고, 그것이
        # 이 표가 읽히는 이유다.
        Command.BEGIN_AI: SessionState.AI_RUNNING,
        Command.RESUME: SessionState.REPLAYING,
        Command.RUN_FROM: SessionState.REPLAYING,
        Command.SAVE: SessionState.PAUSED,
        Command.STOP: SessionState.REVIEW,
        Command.SESSION_LOST: SessionState.LOST,
        # 005 FR-146 에 관한 결정 — **여기에 `FINISH_*` 를 넣지 않는다.**
        #
        # 처음에는 "결말이 일시정지를 이긴다" 로 보고 `PAUSED → COMPLETED/FAILED` 전이를
        # 더했다. 불변식 1 테스트가 그것을 거절했고, 그 거절이 옳다 —
        # `PAUSED` 에서 브라우저 세션은 절대 종료되지 않는다 (FR-032, 헌법 원칙 III).
        # 실행이 끝났다고 해서 사용자가 고쳐서 다시 돌릴 세션을 빼앗을 이유가 없다.
        #
        # 문제의 정체는 전이가 아니라 **두 축을 한 값으로 읽은 것**이었다. 실행 결말과
        # 세션 상태는 다른 축이다 — 실행은 끝났고(결말 있음), 세션은 일시정지다(브라우저
        # 살아 있음, 편집 가능). U-04 가 본 "PAUSED 배지와 FAIL 요약이 동시에" 는 사실
        # 둘 다 참이었고, 화면이 그 관계를 설명하지 않은 것이 결함이었다.
        #
        # 그래서 FR-146 은 화면에서 이행한다 — "멈추기 전에 실행이 끝났습니다" 를 말하고
        # 실패 사유·결과 보기 경로를 붙이며 낡은 전이 안내를 걷는다.
    },
    # 불변식 5 — 유실 후에는 저장만 허용한다. 이어서 실행·편집은 불가하다.
    SessionState.REVIEW: {
        # 브라우저가 없으므로 실행 계열 명령은 받지 않는다 (001 FR-043a). 편집·저장만.
        Command.EDIT_STEPS: SessionState.REVIEW,
        Command.SAVE: SessionState.REVIEW,
        Command.DISCARD: SessionState.STOPPED,
    },
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
    Command.CHOOSE_ANSWER: "답하고 AI에게 돌려주기",
    Command.CHOOSE_RETRY: "AI에게 다시",
    Command.CHOOSE_SKIP: "건너뛰기",
    Command.CHOOSE_ABORT: "종료",
    Command.FINISH_PASS: "실행 완료",
    Command.FINISH_FAIL: "실행 실패",
    Command.SESSION_LOST: "세션 유실",
    Command.DISCARD: "버리기",
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
    SessionState.REVIEW: "검토 중",
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
    """**불변식 2** — 편집은 `PAUSED` 와 `REVIEW` 에서만 (FR-035·FR-035a·DR-012).

    002 에서 `REVIEW` 가 더해졌다. 중지 후 기록을 검토하며 고칠 수 있어야 하고(DR-012),
    그러지 못하면 사용자는 잘못 기록된 Step 하나 때문에 녹화 전체를 버려야 한다.
    브라우저가 없다는 점은 실행 계열 명령을 막는 것으로 이미 지켜진다.
    """
    return state in {SessionState.PAUSED, SessionState.REVIEW}


def mirror_should_run(state: SessionState) -> bool:
    """**FR-047d** — 미러는 모든 활성 상태에서 동작한다."""
    return state in MIRROR_ACTIVE_STATES


CONTROL_PHASE_STATES: frozenset[SessionState] = frozenset(
    {
        SessionState.RECORDING,
        SessionState.TAKEOVER_RECORDING,
        SessionState.PAUSED,
    }
)
"""**조작 국면** — 사용자가 대상 브라우저를 직접 조작하는 상태들 (010 FR-314 · contracts §1).

010 이 이 집합을 세운다. 조작 채널은 여기서만 열리고 (FR-342), 나머지에서는 채널 자체가
사건을 받지 않는다 — 화면 단에서 막는 것으로 충분하지 않다.

`is_manipulation_phase` 와 **다르다.** 그것은 「실제 브라우저 창을 앞으로 가져와야 하는가」
를 묻고 `PAUSED` 를 뺀다. 이것은 「사람이 지금 브라우저를 조작하는가」를 묻고 `PAUSED` 를
넣는다 — 일시정지에서 사람이 막힌 곳을 손으로 지나야 하기 때문이다 (US3). 실행이 멈춰
있으므로 러너 명령과 경쟁하지도 않는다.

`REPLAYING`·`AI_RUNNING` 이 빠진 이유는 러너가 전진하는 중이기 때문이다. 사람 조작이
끼어들면 같은 Step 이 두 번 도는 것을 막던 기존 잠금과 같은 이유다 (FR-315).
`AI_BLOCKED` 도 빠진다 — 사용자가 네 선택지 중 하나를 고르기 전이고, 「직접 수행」을
고르면 `TAKEOVER_RECORDING` 으로 전이해 조작 국면이 된다.
"""


def is_control_phase(state: SessionState) -> bool:
    """조작 채널을 열 수 있는 국면인가 (010 FR-314·FR-342 · contracts §1).

    **채널의 개폐가 이 함수 하나를 지난다.** 판정이 여러 곳에 있으면 한 곳이 빠지고,
    빠진 자리에서 관찰 국면에 열린 채널이 남는다.
    """
    return state in CONTROL_PHASE_STATES


def is_manipulation_phase(state: SessionState) -> bool:
    """조작 국면인가. 실제 브라우저 창을 앞으로 가져와야 한다 (FR-023a·FR-030e).

    **`is_control_phase` 와 다르다** — 위 `CONTROL_PHASE_STATES` 의 설명을 보라.
    """
    return state in {SessionState.RECORDING, SessionState.TAKEOVER_RECORDING}


def is_observation_phase(state: SessionState) -> bool:
    """관찰 국면인가 (FR-047)."""
    return state in {SessionState.REPLAYING, SessionState.AI_RUNNING}


def uses_llm(state: SessionState) -> bool:
    """이 상태가 언어모델을 쓰는가.

    `REPLAYING` 이 True 를 돌려주면 원칙 II 위반이다. 테스트로 고정한다.
    """
    return state in {SessionState.AI_RUNNING, SessionState.AI_BLOCKED}
