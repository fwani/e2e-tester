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
    """research R5 가 정한 값 — 총 40회, 동일 요소 연속 3회."""
    assert MAX_TOOL_CALLS == 40
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

    limits.reset()
    assert limits.exceeded is False
    assert limits.record_call() is True


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
    수만큼 늘어나고, 그때 「40회」는 아무것도 막지 못한다.

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
