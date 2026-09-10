"""`AI_BLOCKED` 상태의 전이. FR-069~FR-074·FR-043a (T119, data-model §8).

**이 상태의 불변식은 "세션이 유지된다" 다.** 4선택지가 각각 어디로 가는지, 그리고 그
상태에서 사용자가 4선택지 대신 일시정지·저장을 요청했을 때 무엇이 일어나는지를 고정한다
(체크리스트 CHK051 이 지적한 미정의 지점).

브라우저를 띄우지 않는다 — 전이는 순수 함수이며, 그래서 전수로 볼 수 있다.
"""

from __future__ import annotations

import pytest

from itb.authoring.blocked import CHOICES, AiChoice, command_for
from itb.execution.state_machine import (
    SESSION_HELD_STATES,
    Command,
    InvalidTransitionError,
    SessionState,
    allowed_commands,
    holds_browser_session,
    is_editable,
    next_state,
)

EXPECTED: dict[AiChoice, SessionState] = {
    AiChoice.TAKEOVER: SessionState.TAKEOVER_RECORDING,
    # 2026-09-10 — 사람이 **답을 주고** AI 에게 돌려준다. 도착 상태는 `RETRY` 와 같지만
    # 명령을 갈라 두는 이유는 거절 문구다 (`Command.CHOOSE_ANSWER` 옆 주석).
    AiChoice.ANSWER: SessionState.AI_RUNNING,
    AiChoice.RETRY: SessionState.AI_RUNNING,
    AiChoice.SKIP: SessionState.AI_RUNNING,
    # 002 — FR-074 는 종료 시 "그때까지 성공한 Step 의 저장 여부를 확인" 을
    # 요구한다. STOPPED 는 아무 명령도 받지 않아 그 확인이 불가능했다.
    AiChoice.ABORT: SessionState.REVIEW,
}


def test_four_choices_are_exactly_the_contract() -> None:
    """계약(rest-api §AI 실패 시 선택)의 선택지. 더도 덜도 없다.

    2026-09-10 에 `answer` 가 더해져 다섯이 됐다 — 「대화를 통해서 답변을 하거나 인터뷰로
    답변을 하고, 그러면 다시 AI 가 테스트 스텝을 생성하거나 수정한다」 (사용자 결정).
    """
    assert CHOICES == ("takeover", "answer", "retry", "skip", "abort")


@pytest.mark.parametrize(("choice", "expected"), list(EXPECTED.items()))
def test_each_choice_transitions_as_specified(
    choice: AiChoice, expected: SessionState
) -> None:
    """FR-071~FR-074 — 선택지마다 정해진 곳으로 간다."""
    assert next_state(SessionState.AI_BLOCKED, command_for(choice)) is expected


def test_blocked_state_holds_the_browser_session() -> None:
    """**FR-069 의 핵심.** 이 상태에서 세션을 종료하면 사용자가 이어받을 화면이 사라진다."""
    assert SessionState.AI_BLOCKED in SESSION_HELD_STATES
    assert holds_browser_session(SessionState.AI_BLOCKED)


def test_pause_and_save_are_allowed_in_blocked_state() -> None:
    """FR-043a·CHK051 — 4선택지 대신 일시정지·저장을 요청할 수 있다.

    막힌 상태에서 사용자가 "일단 멈추고 고치겠다" 또는 "여기까지 저장하겠다" 를 택하는
    것은 자연스럽다. 4선택지만 받으면 그 요청이 조용히 거절된다.
    """
    allowed = allowed_commands(SessionState.AI_BLOCKED)
    assert Command.PAUSE in allowed
    assert Command.SAVE in allowed
    assert next_state(SessionState.AI_BLOCKED, Command.PAUSE) is SessionState.PAUSED
    # 저장은 상태를 바꾸지 않는다 — 저장은 조회가 아니라 부수 효과이지만 전이가 아니다.
    assert next_state(SessionState.AI_BLOCKED, Command.SAVE) is SessionState.AI_BLOCKED


def test_editing_is_not_allowed_while_blocked() -> None:
    """편집은 `PAUSED` 에서만 (불변식 2).

    막힌 상태에서 바로 편집을 받으면, 사용자가 무엇을 보고 고치는 것인지 모호해진다 —
    AI 가 다시 움직일 수 있는 상태이기 때문이다. 먼저 멈춰야 한다.
    """
    assert is_editable(SessionState.AI_BLOCKED) is False
    with pytest.raises(InvalidTransitionError):
        next_state(SessionState.AI_BLOCKED, Command.EDIT_STEPS)


def test_undefined_commands_are_rejected_with_guidance() -> None:
    """FR-043a — 거절할 때 현재 상태와 가능한 행동을 알린다."""
    with pytest.raises(InvalidTransitionError) as exc:
        next_state(SessionState.AI_BLOCKED, Command.BEGIN_REPLAY)
    message = str(exc.value)
    assert "AI 실패" in message
    assert "지금 가능한 행동" in message
    assert "직접 수행" in message


def test_takeover_recording_can_return_to_ai() -> None:
    """FR-076 — 사람이 이어받은 뒤 "계속하기" 로 AI 에게 돌려준다."""
    assert (
        next_state(SessionState.TAKEOVER_RECORDING, Command.RESUME)
        is SessionState.AI_RUNNING
    )
    # 인수 중에도 멈춰서 고칠 수 있다 (CHK052).
    assert (
        next_state(SessionState.TAKEOVER_RECORDING, Command.PAUSE) is SessionState.PAUSED
    )


def test_session_loss_is_detected_from_blocked_state() -> None:
    """FR-041 — 어느 상태에서든 유실을 감지한다. 막힌 상태도 예외가 아니다."""
    assert next_state(SessionState.AI_BLOCKED, Command.SESSION_LOST) is SessionState.LOST
    assert (
        next_state(SessionState.TAKEOVER_RECORDING, Command.SESSION_LOST)
        is SessionState.LOST
    )
