"""T041 — RunSession 상태 기계 전수 테스트. 헌법 원칙 III + 품질 게이트 3.

**10상태 × 19명령 = 190 조합을 전수로 확인한다.** 정의되지 않은 조합이 조용히 통과하면
FR-043a 위반이며, 상태별 규정을 빠뜨린 것을 발견할 수 없다.
"""

from __future__ import annotations

import pytest

from itb.execution.state_machine import (
    ACTIVE_STATES,
    PAUSABLE_STATES,
    REVIEW_STATES,
    SESSION_HELD_STATES,
    TERMINAL_STATES,
    Command,
    InvalidTransitionError,
    SessionState,
    allowed_commands,
    can,
    command_label,
    holds_browser_session,
    is_editable,
    is_manipulation_phase,
    is_observation_phase,
    mirror_should_run,
    next_state,
    state_label,
    uses_llm,
)

ALL_STATES = tuple(SessionState)
ALL_COMMANDS = tuple(Command)


# ─── 전수 확인 (FR-043a) ────────────────────────────────────────────────────


@pytest.mark.parametrize("state", ALL_STATES)
@pytest.mark.parametrize("command", ALL_COMMANDS)
def test_every_state_command_pair_is_decided(
    state: SessionState, command: Command
) -> None:
    """모든 조합이 '허용되어 전이' 또는 '거절' 중 하나로 결정되어야 한다.

    조용히 무시되거나 예외 없이 상태가 그대로 남는 경우가 없어야 한다.
    """
    if can(state, command):
        assert isinstance(next_state(state, command), SessionState)
    else:
        with pytest.raises(InvalidTransitionError):
            next_state(state, command)


@pytest.mark.parametrize("state", ALL_STATES)
def test_labels_exist_for_every_state(state: SessionState) -> None:
    assert state_label(state)


@pytest.mark.parametrize("command", ALL_COMMANDS)
def test_labels_exist_for_every_command(command: Command) -> None:
    assert command_label(command)


def test_rejection_message_names_state_and_allowed_actions() -> None:
    """거절 시 현재 상태와 가능한 행동을 함께 알려야 한다 (FR-043a)."""
    with pytest.raises(InvalidTransitionError) as exc:
        next_state(SessionState.REPLAYING, Command.EDIT_STEPS)
    msg = str(exc.value)
    assert "실행 중" in msg
    assert "Step 편집" in msg
    assert "일시정지" in msg  # 지금 가능한 행동


# ─── 불변식 1: PAUSED·AI_BLOCKED 에서 세션 종료 금지 (FR-032, FR-069) ──────


@pytest.mark.parametrize("state", sorted(SESSION_HELD_STATES))
def test_session_held_states_keep_browser_alive(state: SessionState) -> None:
    assert holds_browser_session(state) is True


@pytest.mark.parametrize("state", sorted(SESSION_HELD_STATES))
def test_session_held_states_do_not_auto_terminate(state: SessionState) -> None:
    """사용자가 명시적으로 중지하거나 세션이 유실되지 않는 한 종료되지 않는다."""
    for command in ALL_COMMANDS:
        if not can(state, command):
            continue
        result = next_state(state, command)
        if result in TERMINAL_STATES:
            assert command in {Command.STOP, Command.CHOOSE_ABORT, Command.SESSION_LOST}, (
                f"{state} 에서 {command} 이 세션을 종료시킨다 — 불변식 1 위반"
            )


@pytest.mark.parametrize("state", sorted(ACTIVE_STATES))
def test_active_states_hold_a_browser_session(state: SessionState) -> None:
    assert holds_browser_session(state) is True


@pytest.mark.parametrize("state", sorted(TERMINAL_STATES))
def test_terminal_states_hold_no_session(state: SessionState) -> None:
    assert holds_browser_session(state) is False


def test_states_are_partitioned_into_active_review_and_terminal() -> None:
    """002 — `REVIEW` 가 제3의 범주로 더해졌다.

    브라우저가 없으므로 활성이 아니고, 편집·저장을 받으므로 종료가 아니다. 세 범주가
    서로 겹치지 않고 전체를 덮는다는 것이 여전히 불변식이다 (research R1).
    """
    assert ACTIVE_STATES | REVIEW_STATES | TERMINAL_STATES == set(ALL_STATES)
    assert not (ACTIVE_STATES & TERMINAL_STATES)
    assert not (ACTIVE_STATES & REVIEW_STATES)
    assert not (REVIEW_STATES & TERMINAL_STATES)


# ─── 불변식 2: 편집은 PAUSED·REVIEW 에서만 (FR-035a·DR-012) ────────────────


@pytest.mark.parametrize("state", ALL_STATES)
def test_edit_only_in_paused_or_review(state: SessionState) -> None:
    """002 — `REVIEW` 가 더해졌다.

    중지 후 기록을 검토하며 고칠 수 있어야 한다(DR-012). 그러지 못하면 잘못 기록된
    Step 하나 때문에 녹화 전체를 버려야 한다. **다른 어느 상태에서도 여전히 불가하다** —
    이 단언의 요점은 그쪽이다.
    """
    expected = state in {SessionState.PAUSED, SessionState.REVIEW}
    assert can(state, Command.EDIT_STEPS) is expected
    assert is_editable(state) is expected


def test_edit_keeps_paused_state() -> None:
    """불변식 3 — 편집은 정의만 바꾼다. 상태도 브라우저도 바뀌지 않는다."""
    assert next_state(SessionState.PAUSED, Command.EDIT_STEPS) is SessionState.PAUSED


@pytest.mark.parametrize(
    "state",
    [
        SessionState.RECORDING,
        SessionState.REPLAYING,
        SessionState.AI_RUNNING,
        SessionState.AI_BLOCKED,
        SessionState.TAKEOVER_RECORDING,
        SessionState.LOST,
    ],
)
def test_edit_rejected_outside_paused(state: SessionState) -> None:
    with pytest.raises(InvalidTransitionError, match="Step 편집"):
        next_state(state, Command.EDIT_STEPS)


# ─── 일시정지 (FR-031) ─────────────────────────────────────────────────────


@pytest.mark.parametrize("state", sorted(PAUSABLE_STATES))
def test_pausable_states_go_to_paused(state: SessionState) -> None:
    assert next_state(state, Command.PAUSE) is SessionState.PAUSED


def test_takeover_recording_can_be_paused() -> None:
    """CHK052 — 사람이 이어받는 중에도 멈춰서 고칠 수 있어야 한다."""
    assert can(SessionState.TAKEOVER_RECORDING, Command.PAUSE)


def test_ai_blocked_can_be_paused_instead_of_choosing() -> None:
    """CHK051 — 4선택지 대신 일시정지를 요청하는 경우도 정의돼 있어야 한다."""
    assert next_state(SessionState.AI_BLOCKED, Command.PAUSE) is SessionState.PAUSED


def test_ai_blocked_allows_save_without_choosing() -> None:
    assert next_state(SessionState.AI_BLOCKED, Command.SAVE) is SessionState.AI_BLOCKED


@pytest.mark.parametrize("state", [*sorted(TERMINAL_STATES), SessionState.PAUSED])
def test_pause_rejected_when_not_running(state: SessionState) -> None:
    with pytest.raises(InvalidTransitionError):
        next_state(state, Command.PAUSE)


# ─── 이어서 실행 (FR-038·FR-039) ───────────────────────────────────────────


def test_resume_from_paused_replays() -> None:
    assert next_state(SessionState.PAUSED, Command.RESUME) is SessionState.REPLAYING


def test_run_from_step_allowed_in_paused() -> None:
    assert next_state(SessionState.PAUSED, Command.RUN_FROM) is SessionState.REPLAYING


def test_begin_ai_from_paused_enters_ai_running() -> None:
    """016 research R4 — **AI 가 이어 만드는 자리.** 016 의 유일한 전이 추가다.

    `RECORD_ACTIONS_START`(사람이 이어 녹화한다)와 대칭이다. 016 의 채팅 턴과 구간
    재녹화가 이 전이로 들어오고, 턴이 끝나면 `PAUSE` 로 돌아온다.
    """
    assert next_state(SessionState.PAUSED, Command.BEGIN_AI) is SessionState.AI_RUNNING
    # 돌아오는 길이 있어야 턴이 끝난다.
    assert next_state(SessionState.AI_RUNNING, Command.PAUSE) is SessionState.PAUSED
    # 막힘도 기존 경로 그대로다 — 016 은 이 길을 새로 만들지 않는다.
    assert next_state(SessionState.AI_RUNNING, Command.AI_BLOCK) is SessionState.AI_BLOCKED


def test_016_added_exactly_one_transition() -> None:
    """**다른 상태의 전이표는 바뀌지 않았다** (T009).

    016 은 전이 하나만 더한다. 그보다 많이 바뀌었다면 계획(research R4)이 어긋난 것이고,
    국면표·화면·검사가 따라오지 못한 자리가 생긴다.

    여기 적은 수는 016 **이후**의 값이다. 전이를 더하거나 빼면 이 검사가 먼저 실패하고,
    작성자는 그 변경이 의도된 것인지 답해야 한다.
    """
    expected = {
        SessionState.STARTING: 5,
        SessionState.RECORDING: 4,
        SessionState.REPLAYING: 6,
        SessionState.AI_RUNNING: 6,
        SessionState.AI_BLOCKED: 9,
        SessionState.TAKEOVER_RECORDING: 6,
        SessionState.PAUSED: 8,  # 016 에서 7 → 8 (BEGIN_AI)
        SessionState.REVIEW: 3,
        SessionState.LOST: 1,
        SessionState.COMPLETED: 0,
        SessionState.FAILED: 0,
        SessionState.STOPPED: 0,
    }
    actual = {state: len(allowed_commands(state)) for state in SessionState}
    assert actual == expected


def test_pausing_itself_does_not_use_an_llm() -> None:
    """016 이 원칙 II 판정을 흔들지 않았다.

    `PAUSED → AI_RUNNING` 이 생겼으므로 「일시정지에서 언어모델로 갈 수 있다」가 참이
    됐다. 그것은 의도된 것이고(작성 경로다), 흔들리면 안 되는 것은 **재실행 상태**와
    **일시정지 상태 자체**다 — 멈춰 있는 동안에는 아무 호출도 일어나지 않는다.
    """
    assert uses_llm(SessionState.REPLAYING) is False
    assert uses_llm(SessionState.PAUSED) is False
    assert uses_llm(SessionState.AI_RUNNING) is True


def test_resume_after_takeover_returns_to_ai() -> None:
    """FR-076 — 사람이 이어받은 뒤 계속하기를 누르면 AI 가 남은 지시를 맡는다."""
    assert next_state(SessionState.TAKEOVER_RECORDING, Command.RESUME) is SessionState.AI_RUNNING


def test_record_actions_from_paused_enters_recording() -> None:
    """FR-036 — 일시정지 중 직접 동작 추가."""
    assert (
        next_state(SessionState.PAUSED, Command.RECORD_ACTIONS_START) is SessionState.RECORDING
    )


# ─── AI 실패 4선택지 (FR-070~FR-074) ───────────────────────────────────────


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (Command.CHOOSE_TAKEOVER, SessionState.TAKEOVER_RECORDING),
        (Command.CHOOSE_RETRY, SessionState.AI_RUNNING),
        (Command.CHOOSE_SKIP, SessionState.AI_RUNNING),
        # 002 — REVIEW 로 바뀌었다. FR-074 는 "종료를 선택하면 세션을 종료하고
        # **그때까지 성공한 Step 의 저장 여부를 확인해야 한다**" 고 요구하는데,
        # STOPPED 는 아무 명령도 받지 않아 그 확인이 불가능했다 (research R1).
        (Command.CHOOSE_ABORT, SessionState.REVIEW),
    ],
)
def test_four_choices(command: Command, expected: SessionState) -> None:
    assert next_state(SessionState.AI_BLOCKED, command) is expected


def test_abort_can_still_save_what_the_ai_managed(  ) -> None:
    """FR-074 — 종료해도 그때까지 성공한 Step 을 저장할 수 있어야 한다."""
    after = next_state(SessionState.AI_BLOCKED, Command.CHOOSE_ABORT)
    assert after is not None
    assert can(after, Command.SAVE)


@pytest.mark.parametrize(
    "command",
    [
        Command.CHOOSE_TAKEOVER,
        Command.CHOOSE_RETRY,
        Command.CHOOSE_SKIP,
        Command.CHOOSE_ABORT,
    ],
)
@pytest.mark.parametrize("state", [s for s in ALL_STATES if s is not SessionState.AI_BLOCKED])
def test_choices_rejected_outside_ai_blocked(state: SessionState, command: Command) -> None:
    with pytest.raises(InvalidTransitionError):
        next_state(state, command)


def test_ai_block_only_from_ai_running() -> None:
    assert next_state(SessionState.AI_RUNNING, Command.AI_BLOCK) is SessionState.AI_BLOCKED
    for state in ALL_STATES:
        if state is SessionState.AI_RUNNING:
            continue
        assert not can(state, Command.AI_BLOCK)


# ─── 세션 유실 (FR-041·FR-041a~c) ──────────────────────────────────────────


@pytest.mark.parametrize("state", sorted(ACTIVE_STATES))
def test_session_loss_reachable_from_every_active_state(state: SessionState) -> None:
    """FR-041 — 어느 상태에서든 유실이 처리되어야 한다.

    analyze C2/CHK048 가 지적한 빈틈: 이전 명세는 '일시정지 중' 만 다뤘다.
    """
    assert next_state(state, Command.SESSION_LOST) is SessionState.LOST


@pytest.mark.parametrize("state", sorted(TERMINAL_STATES))
def test_session_loss_not_applicable_after_termination(state: SessionState) -> None:
    assert not can(state, Command.SESSION_LOST)


def test_lost_allows_only_save() -> None:
    """FR-041c — 유지할 브라우저 상태가 없으므로 이어서 실행·편집은 불가하다."""
    assert allowed_commands(SessionState.LOST) == (Command.SAVE,)
    assert next_state(SessionState.LOST, Command.SAVE) is SessionState.LOST


@pytest.mark.parametrize(
    "command", [Command.RESUME, Command.RUN_FROM, Command.EDIT_STEPS, Command.PAUSE]
)
def test_lost_rejects_resume_and_edit(command: Command) -> None:
    with pytest.raises(InvalidTransitionError):
        next_state(SessionState.LOST, command)


# ─── 미러 (FR-047d) ───────────────────────────────────────────────────────


@pytest.mark.parametrize("state", sorted(ACTIVE_STATES))
def test_mirror_runs_in_every_active_state(state: SessionState) -> None:
    """analyze CHK050 이 지적한 빈틈. 조작 국면·일시정지·AI 대기에서도 미러가 돈다."""
    assert mirror_should_run(state) is True


@pytest.mark.parametrize("state", sorted(TERMINAL_STATES))
def test_mirror_stops_after_termination(state: SessionState) -> None:
    """FR-047e — 세션이 종료·유실되면 미러를 중단한다."""
    assert mirror_should_run(state) is False


# ─── 국면 구분 (clarify 결정 3) ────────────────────────────────────────────


@pytest.mark.parametrize(
    "state", [SessionState.RECORDING, SessionState.TAKEOVER_RECORDING]
)
def test_manipulation_phases(state: SessionState) -> None:
    """조작 국면에서는 실제 브라우저 창을 앞으로 가져온다 (FR-023a·FR-030e)."""
    assert is_manipulation_phase(state) is True
    assert is_observation_phase(state) is False


@pytest.mark.parametrize("state", [SessionState.REPLAYING, SessionState.AI_RUNNING])
def test_observation_phases(state: SessionState) -> None:
    assert is_observation_phase(state) is True
    assert is_manipulation_phase(state) is False


def test_paused_is_neither_phase() -> None:
    """일시정지는 조작도 관찰도 아니다. 미러는 마지막 화면을 계속 보여준다."""
    assert not is_manipulation_phase(SessionState.PAUSED)
    assert not is_observation_phase(SessionState.PAUSED)
    assert mirror_should_run(SessionState.PAUSED)


# ─── 원칙 II: REPLAYING 은 언어모델을 쓰지 않는다 (FR-044) ────────────────


def test_replaying_never_uses_llm() -> None:
    """NON-NEGOTIABLE. 이 단정이 깨지면 원칙 II 위반이다."""
    assert uses_llm(SessionState.REPLAYING) is False


def test_recording_never_uses_llm() -> None:
    assert uses_llm(SessionState.RECORDING) is False
    assert uses_llm(SessionState.TAKEOVER_RECORDING) is False


@pytest.mark.parametrize("state", [SessionState.AI_RUNNING, SessionState.AI_BLOCKED])
def test_only_ai_states_use_llm(state: SessionState) -> None:
    assert uses_llm(state) is True


def test_replay_path_cannot_reach_ai_states() -> None:
    """REPLAYING 에서 어떤 명령으로도 AI 상태에 도달할 수 없어야 한다."""
    reachable = {
        next_state(SessionState.REPLAYING, c)
        for c in allowed_commands(SessionState.REPLAYING)
    }
    assert not (reachable & {SessionState.AI_RUNNING, SessionState.AI_BLOCKED})


def test_paused_reaches_ai_only_by_an_explicit_user_command() -> None:
    """일시정지에서 AI 상태로 가는 길은 **사용자 명령 하나뿐**이다 (016, 2026-09-11).

    ## 이 단언은 016 에서 좁혀졌다

    이전 문장은 「일시정지를 경유해도 AI 상태로 넘어갈 수 없다」였다. 016 이 채팅 턴을
    위해 `PAUSED + BEGIN_AI → AI_RUNNING` 을 더하면서 그 문장이 깨졌다. 약화가 아니라
    **교체**이며, 근거는 셋이다.

    **1. 헌법이 이미 이 동작을 요구한다.** 원칙 III: "Steps executed while paused —
    recorded by direct user operation, **or added via natural language** — MUST be
    captured into the same Step Model." 헌법이 한편에서 요구하는 것을 다른 편에서
    금지할 수는 없다. 원칙 II 의 "replay path" 는 저장된 Step 의 **자동 실행**이고,
    사용자가 손으로 멈추는 순간 그 경로를 벗어나 작성으로 들어간다.

    **2. 제품은 이미 이 선을 넘고 있었다.** `ai_step`(US6, FR-078)이 재실행을 일시정지한
    세션에서 언어모델을 부른다. 옛 단언이 그것을 못 잡은 이유는 하나뿐이다 — 그 경로가
    상태 전이를 하지 않아서. 즉 옛 단언은 「LLM 호출」이 아니라 **「상태 이름」**을 지키고
    있었고, 이름을 우회하면 그대로 통과했다.

    **3. 더 강한 단언으로 갈아 끼웠다.** `tests/test_principle_ii_timeline.py` 가
    **러너가 도는 동안 드라이버 호출이 0회**임을 본다. 상태 이름이 아니라 실제 호출을
    보므로 `ai_step` 같은 우회가 통하지 않는다.

    ## 그래서 여기서 지키는 것

    **자동으로는 못 간다.** AI 상태로 가는 유일한 길이 `BEGIN_AI` 라는 명시적 사용자
    명령이어야 한다. 이어서 실행(`RESUME`)·이 Step 부터(`RUN_FROM`)·편집(`EDIT_STEPS`)
    어느 것도 AI 로 흘러들어서는 안 된다 — 그것이 원칙 II 가 실제로 막으려는 것이다.
    """
    to_ai = {
        c
        for c in allowed_commands(SessionState.PAUSED)
        if next_state(SessionState.PAUSED, c)
        in {SessionState.AI_RUNNING, SessionState.AI_BLOCKED}
    }
    assert to_ai == {Command.BEGIN_AI}, (
        f"일시정지에서 AI 로 가는 길이 늘었다: {sorted(c.value for c in to_ai)}. "
        "사용자가 명시적으로 AI 를 부르는 명령 하나여야 한다 (원칙 II)."
    )

    # 실행 계열은 여전히 실행으로만 간다. 이것이 「자동으로는 못 간다」의 실체다.
    assert next_state(SessionState.PAUSED, Command.RESUME) is SessionState.REPLAYING
    assert next_state(SessionState.PAUSED, Command.RUN_FROM) is SessionState.REPLAYING
    assert next_state(SessionState.PAUSED, Command.EDIT_STEPS) is SessionState.PAUSED


def test_replay_still_cannot_pause_itself_into_ai() -> None:
    """**한 걸음으로는 여전히 못 간다.** `REPLAYING` 에서 AI 로 직행하는 길은 없다.

    위 단언이 좁혀졌으므로 그 앞단을 여기서 따로 고정한다 — 재실행 중인 세션이 스스로
    AI 상태로 넘어가는 일은 어떤 명령으로도 일어나지 않는다.
    """
    reachable = {
        next_state(SessionState.REPLAYING, c)
        for c in allowed_commands(SessionState.REPLAYING)
    }
    assert not (reachable & {SessionState.AI_RUNNING, SessionState.AI_BLOCKED})


# ─── 시작·종료 ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (Command.BEGIN_RECORD, SessionState.RECORDING),
        (Command.BEGIN_REPLAY, SessionState.REPLAYING),
        (Command.BEGIN_AI, SessionState.AI_RUNNING),
    ],
)
def test_start_transitions(command: Command, expected: SessionState) -> None:
    assert next_state(SessionState.STARTING, command) is expected


@pytest.mark.parametrize("state", sorted(TERMINAL_STATES - {SessionState.LOST}))
def test_terminal_states_accept_nothing(state: SessionState) -> None:
    assert allowed_commands(state) == ()


def test_replay_can_finish_pass_or_fail() -> None:
    assert next_state(SessionState.REPLAYING, Command.FINISH_PASS) is SessionState.COMPLETED
    assert next_state(SessionState.REPLAYING, Command.FINISH_FAIL) is SessionState.FAILED


def test_recording_cannot_finish_by_itself() -> None:
    """녹화는 사용자가 정지·저장할 때 끝난다. 스스로 완료되지 않는다."""
    assert not can(SessionState.RECORDING, Command.FINISH_PASS)
    assert not can(SessionState.RECORDING, Command.FINISH_FAIL)
