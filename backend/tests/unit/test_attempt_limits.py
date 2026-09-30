"""시도 상한. FR-066·research R5 (T107).

**하드 루프 카운터가 1차 방어선이다.** 모델에게 페이스 조절을 맡기는 장치는 권고적이며
이것을 대체하지 못한다. 상한이 없으면 막힌 화면에서 같은 버튼을 무한히 누르고, 사용자는
비용이 쌓이는 것만 본다.

**상한 도달을 예외로 알리지 않는다.** SDK 의 tool runner 는 도구가 던진 예외를 모두 잡아
`is_error` 도구 결과로 바꿔 모델에게 돌려주므로, 예외로는 루프를 끊을 수 없다. 그래서
상한은 상태로 남고, 우리가 소유한 `async for` 본문이 그 상태를 보고 끊는다. 이 테스트가
그 계약을 고정한다 — 예외 기반으로 되돌리면 상한이 조용히 무력해진다.
"""

from __future__ import annotations

from itb.authoring.tools import (
    MAX_CONSECUTIVE_ELEMENT_FAILURES,
    MAX_TOOL_CALLS,
    STOP_NOTICE,
    AttemptLimits,
)


def test_declared_limits_match_research_decision() -> None:
    """총 300회, 동일 요소 연속 3회.

    총 상한은 001 research R5 의 40 에서 **300 으로 옮겼다** (2026-09-30 사용자 지시).
    40 이 실제로 끊던 것은 헛도는 실행이 아니라 긴 작성이었다 — 헛도는 쪽은 연속 실패
    상한이 세 번에 끊으며, 그 값은 그대로다.

    **값을 검사로 고정하는 이유는 바뀌지 않았다.** 상한이 조용히 움직이면 「같은 지시가
    어제는 되고 오늘은 안 된다」가 되고, 사용자는 원인을 지시에서 찾는다.
    """
    assert MAX_TOOL_CALLS == 300
    assert MAX_CONSECUTIVE_ELEMENT_FAILURES == 3


def test_total_call_limit_marks_exceeded_instead_of_raising() -> None:
    limits = AttemptLimits(max_calls=3)
    for _ in range(3):
        assert limits.record_call() is True
    assert limits.exceeded is False

    assert limits.record_call() is False, "상한을 넘긴 호출이 허용됐다"
    assert limits.exceeded is True
    assert "상한(3회)" in (limits.exceeded_reason or "")
    assert "성공한 동작은 Step 으로 남아 있습니다" in (limits.exceeded_reason or "")


def test_calls_after_limit_are_all_refused() -> None:
    """상한을 넘긴 뒤에는 어떤 호출도 진행하지 않는다.

    허용하면 화면이 더 바뀌는데 그 동작은 Step 으로 남지 않아, 사용자가 보는 상태와
    기록된 정의가 어긋난다.
    """
    limits = AttemptLimits(max_calls=1)
    limits.record_call()
    assert limits.record_call() is False
    assert limits.record_call() is False
    assert limits.calls == 1, "거절된 호출까지 세면 안 된다"


def test_consecutive_element_failures_mark_exceeded() -> None:
    """같은 요소를 연달아 실패하면 끊는다. 세 번이면 그 경로는 막힌 것이다."""
    limits = AttemptLimits(max_element_failures=3)
    limits.record_failure("e1")
    limits.record_failure("e1")
    assert limits.exceeded is False
    limits.record_failure("e1")
    assert limits.exceeded is True
    assert "e1" in (limits.exceeded_reason or "")


def test_failures_on_different_elements_are_not_consecutive() -> None:
    """**연속 실패만 센다.**

    서로 다른 요소를 각각 한 번 실패한 것은 막힌 것이 아니라 화면을 탐색하는 중이다.
    그것을 상한에 넣으면 정상적인 탐색이 중단된다.
    """
    limits = AttemptLimits(max_element_failures=3)
    for ref in ("e1", "e2", "e3", "e1", "e2", "e3"):
        limits.record_failure(ref)
    assert limits.exceeded is False
    assert limits.failures_by_element == {"e1": 1, "e2": 1, "e3": 1}


def test_success_clears_the_failure_streak() -> None:
    """성공하면 연속 실패가 끊긴다.

    한 번 실패하고 성공한 요소를 나중에 두 번 더 실패했을 때 끊으면, 실제로는 세 번
    연속이 아닌데 중단된다.
    """
    limits = AttemptLimits(max_element_failures=3)
    limits.record_failure("e1")
    limits.record_failure("e1")
    limits.record_success("e1")
    limits.record_failure("e1")
    limits.record_failure("e1")
    assert limits.exceeded is False
    assert limits.failures_by_element["e1"] == 2


def test_reset_gives_a_fresh_budget() -> None:
    """FR-072·FR-073 — 재시도·건너뛰기는 새 예산으로 시작한다."""
    limits = AttemptLimits(max_calls=2)
    limits.record_call()
    limits.record_call()
    limits.record_call()
    assert limits.exceeded is True

    limits.reset_attempt()
    assert limits.exceeded is False
    assert limits.record_call() is True


# ─── 022 — 누적은 리셋을 건너 남는다 ───────────────────────────────────────


def test_total_calls_survives_a_fresh_budget() -> None:
    """**누적은 예산을 새로 줘도 남는다** (022 FR-018).

    사용자가 「더 할지」를 정하는 근거다. 한 시도의 수만 보이면 이어갈 때마다 작은 수가
    다시 나와, 몇 번을 이어갔든 처음처럼 보인다.
    """
    limits = AttemptLimits(max_calls=2)
    limits.record_call()
    limits.record_call()
    assert (limits.calls, limits.total_calls) == (2, 2)

    limits.reset_attempt()
    assert limits.calls == 0, "이번 시도의 예산은 되돌아간다"
    assert limits.total_calls == 2, "누적은 남는다"

    limits.record_call()
    assert (limits.calls, limits.total_calls) == (1, 3)


def test_fresh_budget_moves_the_progress_baseline() -> None:
    """진전 판정의 기준점은 이어갈 때마다 지금 Step 수로 옮긴다 (022 FR-020)."""
    limits = AttemptLimits()
    assert limits.steps_at_attempt_start is None, "첫 시도에는 비교할 값이 없다"

    limits.reset_attempt(step_count=4)
    assert limits.steps_at_attempt_start == 4

    # 넘기지 않으면 기준점을 건드리지 않는다 — 옮길 값을 모르는 호출부가 있다.
    limits.reset_attempt()
    assert limits.steps_at_attempt_start == 4


def test_only_the_call_ceiling_counts_as_budget_exhaustion() -> None:
    """**연속 실패는 예산 소진이 아니다** (022 FR-002).

    둘은 같은 필드(`exceeded_reason`)로 멈춤을 알리지만 종류가 다르다 — 예산 소진은
    이어가면 진행되고, 연속 실패는 그 경로가 막힌 것이라 사람이 알려 줄 것이 있다.
    """
    budget = AttemptLimits(max_calls=1)
    budget.record_call()
    budget.record_call()
    assert budget.exceeded and budget.exceeded_is_budget

    blocked = AttemptLimits(max_element_failures=2)
    blocked.record_failure("#save")
    blocked.record_failure("#save")
    assert blocked.exceeded, "연속 실패도 멈추게 한다"
    assert not blocked.exceeded_is_budget, "그러나 예산 소진은 아니다"


def test_continuing_is_not_capped_by_a_count() -> None:
    """**이어가기 횟수에 상한을 두지 않는다** (022 FR-010).

    이것은 「아무것도 하지 않음」으로 지켜지는 결정이라, 나중에 누가 제한을 넣어도
    울릴 것이 없다. 그래서 여기서 못 박는다 — 사람이 매번 누르는 행동 자체가 통제이며,
    정당한 긴 작업과 헛도는 반복은 횟수로 구별되지 않는다 (spec 「어려운 질문」).
    """
    limits = AttemptLimits(max_calls=1)
    for _ in range(5):
        assert limits.record_call() is True, "예산 안의 호출은 통과한다"
        assert limits.record_call() is False, "예산을 넘긴 호출은 거절된다"
        assert limits.exceeded
        limits.reset_attempt()
        assert not limits.exceeded, "몇 번을 이어가도 다시 쓸 수 있다"
    # 거절된 호출은 세지 않으므로 라운드당 1 이다 — 카운터는 **실제로 진행한** 수다.
    assert limits.total_calls == 5, "그래도 쓴 만큼은 누적에 남는다"


def test_stop_notice_tells_the_model_to_stop() -> None:
    """상한 뒤 도구 결과는 모델에게도 멈추라고 말한다.

    조용히 실패만 돌려주면 모델이 같은 시도를 반복하고, 그 호출들은 아무 일도 하지
    않으면서 비용을 쓴다.
    """
    assert STOP_NOTICE["stop"] is True
    assert "더 이상 도구를 부르지 마세요" in str(STOP_NOTICE["message"])


# ─── 016 — 상한은 구간 크기와 무관하다 (T065 · FR-042) ─────────────────────


def test_the_budget_does_not_scale_with_the_rerecord_range() -> None:
    """**구간이 크다고 상한이 늘지 않는다** (FR-042).

    늘리면 상한이 뜻을 잃는다 — 사용자가 목록 전체를 골라 재녹화를 걸면 예산이 Step
    수만큼 늘어나고, 그때 총 상한은 아무것도 막지 못한다.

    상한은 `AttemptLimits` 의 기본값 하나이며, 트랜잭션이나 구간을 **알지 못한다.**
    그 무지가 이 성질의 구현이다.
    """
    import inspect

    from itb.authoring import tools as tools_mod

    source = inspect.getsource(tools_mod.AttemptLimits)
    for leak in ("rerecord", "range", "step_ids", "transaction"):
        assert leak not in source, (
            f"상한이 구간을 알게 됐다: {leak} — 구간 크기에 비례하면 상한이 뜻을 잃는다"
        )


def test_editing_tools_share_the_one_budget() -> None:
    """편집 도구도 **같은 예산**을 쓴다 (FR-042).

    따로 두면 「만들고 지우기」를 반복하며 우회할 수 있다 — 만들기 예산이 떨어져도
    고치기로 계속 도는 상태가 된다.
    """
    import inspect

    from itb.authoring.tools import STEP_EDITING_TOOLS, BrowserToolbox

    for name in STEP_EDITING_TOOLS:
        source = inspect.getsource(getattr(BrowserToolbox, name))
        assert "self.limits.record_call()" in source, (
            f"{name} 이 예산을 세지 않는다 — 상한을 우회할 수 있다"
        )
