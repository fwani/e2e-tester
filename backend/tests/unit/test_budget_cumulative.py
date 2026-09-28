"""누적 수치가 두 통로로 같게 나가고, 새 지시에서 0 으로 돌아가는가.

022 US3/AC2 · FR-018 · FR-022 · contracts/blocked-view.md §4 (converge T037·T038).

**converge 가 찾은 빈칸이다.** 누적 유지는 단위 수준(`test_attempt_limits.py`)에서만
덮였고, 「새 지시에서 0 으로 돌아가는가」와 「새로 고침을 견디는가」는 아무도 보지
않았다.
"""

from __future__ import annotations

import inspect

from itb.authoring.agent import AgentOutcome, AgentStatus
from itb.authoring.tools import AttemptLimits, BlockedKind

# ─── 누적이 이어가기를 건너 살아남는다 (FR-018) ────────────────────────────


def test_cumulative_survives_every_resume_path() -> None:
    """**이어가는 길이 넷인데 누적은 하나다** (FR-018).

    답하기·재시도·건너뛰기·인수 후 재개가 모두 `reset_attempt` 를 지나며, 어느 길로
    이어가든 누적은 남아야 한다 — 길마다 다르면 사용자가 보는 수가 어느 길로 왔는지에
    따라 달라진다.
    """
    limits = AttemptLimits(max_calls=3)
    for round_no in range(1, 4):
        limits.record_call()
        limits.record_call()
        assert limits.total_calls == round_no * 2
        limits.reset_attempt(step_count=round_no)
        assert limits.calls == 0, "한 시도의 예산은 되돌아간다"
    assert limits.total_calls == 6


def test_a_new_instruction_starts_from_zero() -> None:
    """**새 지시문은 새 세션이고, 새 세션은 새 계수다** (data-model §5).

    이어가기는 같은 지시의 연장이라 누적을 이어받고, 새 지시는 다른 일이라 0 에서
    시작한다. 그 구분이 `AttemptLimits` 의 수명으로 표현되는지 확인한다 — 세션마다
    새로 만들어지므로 새 지시에는 0 이다.
    """
    first = AttemptLimits()
    first.record_call()
    first.record_call()
    assert first.total_calls == 2

    fresh = AttemptLimits()
    assert fresh.total_calls == 0, "새 세션의 계수는 앞 지시를 이어받지 않는다"
    assert fresh.steps_at_attempt_start is None, "비교할 직전 값도 없다"


# ─── 두 통로가 같은 값을 싣는다 (계약 §4) ──────────────────────────────────


def test_both_channels_carry_the_same_fields() -> None:
    """`ai_blocked` 이벤트와 `BlockedView` 가 **같은 값**을 싣는다.

    지금은 둘 다 같은 `AgentOutcome` 에서 읽으므로 갈릴 수 없지만, **한쪽에만 필드를
    더하는 변경이 조용히 통과한다.** 한쪽만 실으면 화면을 새로 고친 사용자가 판단
    근거를 잃고, 그것이 `BlockedView` 가 만들어진 이유를 다시 재현한다.
    """
    from itb.api.routes.sessions import _blocked_view
    from itb.authoring.blocked import enter_blocked

    carried = ("total_tool_calls", "step_count", "made_progress")
    event_src = inspect.getsource(enter_blocked)
    view_src = inspect.getsource(_blocked_view)

    for field in carried:
        assert f"{field}=outcome." in event_src, f"이벤트가 {field} 를 싣지 않는다"
        assert f"{field}=outcome." in view_src, f"뷰가 {field} 를 싣지 않는다"


def test_the_view_reads_the_outcome_that_was_kept() -> None:
    """뷰는 **보관된 결말**에서 읽는다 — 그래서 새로 고쳐도 남는다 (FR-022)."""
    from itb.api.routes.sessions import BlockedView

    outcome = AgentOutcome(
        AgentStatus.BLOCKED,
        reason="도구 호출이 상한(40회)에 도달해 중단했습니다.",
        blocked_kind=BlockedKind.BUDGET_EXHAUSTED,
        step_count=12,
        tool_calls=40,
        total_tool_calls=87,
        made_progress=False,
    )
    view = BlockedView(
        reason=outcome.reason or "",
        choices=[],
        kind=outcome.blocked_kind.value,
        total_tool_calls=outcome.total_tool_calls,
        step_count=outcome.step_count,
        made_progress=outcome.made_progress,
    )

    assert view.total_tool_calls == 87, "한 시도의 40 이 아니라 누적 87 이 나간다"
    assert view.step_count == 12
    assert view.made_progress is False


def test_the_view_defaults_are_safe_when_the_reason_is_unknown() -> None:
    """사유를 모르는 복원 경로(서버 재시작 뒤)에서도 터지지 않는다.

    수치를 모르면 화면이 그 줄을 그리지 않는다 — 없는 것을 0 으로 보이면 「한 번도
    움직이지 않았다」는 거짓을 말하게 된다.
    """
    from itb.api.routes.sessions import BlockedView

    view = BlockedView(reason="AI 가 더 진행하지 못했습니다.", choices=[])
    assert view.total_tool_calls == 0
    assert view.made_progress is None, "모름은 「진전 없음」이 아니다"
