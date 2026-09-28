"""어긋남은 상한에 대해 중립이다 (020 T010 · FR-009).

**이 검사가 지키는 것은 「틀린 답이 보상받지 않는다」이다.**

020 이전 구조에서 모델 앞에 놓인 선택지는 이랬다.

| 모델의 선택 | 결과 |
|---|---|
| 지시문의 기대값을 고수한다 | 기록 실패 → 재시도 → 연속 실패 상한 → **세션이 막힘으로 끝난다** |
| 관찰한 버그값으로 바꾼다 | 통과 → Step 기록 → **작성이 완료된다** |

지침을 아무리 고쳐도 이 카운터가 계속 반대 방향으로 민다. 그래서 어긋남은 연속 실패에
**세어지지도, 그것을 지우지도** 않아야 한다.
"""

from __future__ import annotations

from itb.authoring.tools import MAX_CONSECUTIVE_ELEMENT_FAILURES, AttemptLimits


def test_mismatch_does_not_count_toward_consecutive_failures() -> None:
    """상한만큼 어긋나도 막히지 않는다 — 그것이 이 기능의 전부다."""
    limits = AttemptLimits()
    for _ in range(MAX_CONSECUTIVE_ELEMENT_FAILURES + 2):
        limits.record_mismatch("assert:text")
    assert not limits.exceeded
    assert limits.exceeded_reason is None


def test_mismatch_does_not_reset_an_ongoing_failure_streak() -> None:
    """어긋남이 **다른 요소의** 실패 흐름을 지우면 상한이 약해진다.

    `record_success` 를 부르지 않는 이유가 이것이다. 중립은 「세지 않는다」와
    「지우지도 않는다」 **양쪽**이어야 성립한다.
    """
    limits = AttemptLimits()
    for _ in range(MAX_CONSECUTIVE_ELEMENT_FAILURES - 1):
        limits.record_failure("#save")
    limits.record_mismatch("assert:text")
    assert limits.failures_by_element["#save"] == MAX_CONSECUTIVE_ELEMENT_FAILURES - 1
    assert limits.last_failed_element == "#save"

    limits.record_failure("#save")
    assert limits.exceeded, "어긋남이 흐름을 끊어 상한이 무력해졌다"


def test_success_still_resets_the_streak() -> None:
    """기존 동작은 그대로다 — 이 기능은 성공의 뜻을 바꾸지 않는다."""
    limits = AttemptLimits()
    limits.record_failure("#save")
    limits.record_success("#save")
    assert limits.last_failed_element is None
    assert "#save" not in limits.failures_by_element


def test_total_call_limit_still_stops_endless_mismatching() -> None:
    """총 호출 상한은 그대로 걸린다 (FR-009 후반부).

    어긋남을 연속 실패에서 빼면 모델이 같은 검증을 무한히 시도할 여지가 생긴다.
    그 여지를 막는 것은 **진입 시점의 `record_call()`** 이다 — `assert_condition` 이
    도구 본문에 들어가기 전에 먼저 돈다.
    """
    limits = AttemptLimits(max_calls=3)
    allowed = 0
    for _ in range(10):
        if not limits.record_call():
            break
        limits.record_mismatch("assert:text")
        allowed += 1
    assert allowed == 3
    assert limits.exceeded
    assert "상한" in (limits.exceeded_reason or "")


def test_reset_clears_everything_including_after_mismatches() -> None:
    """재시도·건너뛰기는 예산을 새로 준다 (FR-072·FR-073). 어긋남이 그것을 바꾸지 않는다."""
    limits = AttemptLimits()
    limits.record_failure("#save")
    limits.record_mismatch("assert:text")
    limits.reset()
    assert limits.calls == 0
    assert limits.last_failed_element is None
    assert not limits.exceeded
