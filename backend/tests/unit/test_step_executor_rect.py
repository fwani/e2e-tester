"""실행기가 돌려주는 요소의 자리 (024 T018·T019 · FR-001·FR-002·FR-006).

## 여기서 재는 것

`ElementRect` 는 「무엇이 자리인가」를 정하는 규칙이다. 그 규칙이 느슨하면 화면 전체를
덮는 테두리나 사라진 테두리가 그려지고, 둘 다 원인을 찾기 어렵다.

**측정 실패가 실행을 멈추지 않는다**는 것도 여기서 못 박는다 (FR-006). 표시는 곁가지이고,
그것 때문에 테스트가 실패하면 이 기능은 도움이 아니라 새 고장 지점이 된다.
"""

from __future__ import annotations

import math

from itb.execution.step_executor import (
    ElementRect,
    StepExecution,
    StepFailure,
    _measure,
)

# ─── 무엇이 자리이고 무엇이 아닌가 (data-model §2) ──────────────────────────


def test_a_normal_box_becomes_a_place() -> None:
    rect = ElementRect.of({"x": 471.0, "y": 243.0, "width": 338.0, "height": 39.0})
    assert rect == ElementRect(x=471.0, y=243.0, width=338.0, height=39.0)


def test_negative_coordinates_are_valid() -> None:
    """스크롤 위의 요소다 — 자리가 **없는** 것이 아니라 보이지 않는 것이다.

    실측에서 뷰포트 높이 800 인 화면의 요소가 `y=2008` 로 나왔다. 그릴지 말지는 화면이
    정한다 (FR-019) — 여기서 걸러 내면 화면은 판정할 기회를 잃는다.
    """
    rect = ElementRect.of({"x": -20.0, "y": 2008.0, "width": 80.0, "height": 30.0})
    assert rect is not None
    assert rect.y == 2008.0


def test_zero_size_is_not_a_place() -> None:
    """조작은 가능하지만 그릴 자리가 없다."""
    assert ElementRect.of({"x": 1, "y": 1, "width": 0, "height": 10}) is None
    assert ElementRect.of({"x": 1, "y": 1, "width": 10, "height": -3}) is None


def test_non_numbers_are_not_a_place() -> None:
    """`NaN` 은 모든 비교를 거짓으로 만들어 크기 검사를 그대로 통과한다.

    막지 않으면 화면이 그린 자리가 사라지거나 화면 전체를 덮는다.
    """
    assert ElementRect.of({"x": math.nan, "y": 1, "width": 10, "height": 10}) is None
    assert ElementRect.of({"x": 1, "y": 1, "width": math.inf, "height": 10}) is None
    assert ElementRect.of({"x": "a", "y": 1, "width": 10, "height": 10}) is None


def test_missing_or_absent_box_is_not_a_place() -> None:
    """보이지 않는 요소는 경계 상자 자체가 없다 — 정상 경로다."""
    assert ElementRect.of(None) is None
    assert ElementRect.of({"x": 1, "y": 1}) is None


def test_payload_shape_matches_the_contract() -> None:
    """contracts/ai-focus.md §2 — 네 필드, 그 이름 그대로."""
    rect = ElementRect(x=1.0, y=2.0, width=3.0, height=4.0)
    assert rect.as_payload() == {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0}


# ─── 기록과 실패가 자리를 나른다 (data-model §3·§4) ─────────────────────────


def test_a_record_without_a_place_is_normal() -> None:
    """요소를 대상으로 하지 않는 Step(이동·탭 닫기)이 그렇다.

    **`None` 은 정상 값이다.** 「자리를 모른다」와 「자리가 없다」를 구별하지 않는다 —
    둘 다 「그리지 않는다」로 귀결되므로 구별할 이유가 없다.
    """
    assert StepExecution().rect is None


def test_a_failure_can_carry_a_place() -> None:
    """요소는 찾았는데 동작이 실패한 경우 — 024 US2 가 겨냥하는 자리다."""
    rect = ElementRect(x=10.0, y=20.0, width=30.0, height=40.0)
    assert StepFailure("가려져 있습니다", rect=rect).rect == rect


def test_a_failure_without_a_place_is_normal() -> None:
    """요소를 못 찾은 실패에는 잴 것이 없었다 (FR-010)."""
    assert StepFailure("요소를 찾지 못했습니다").rect is None


# ─── T019 — 측정 실패가 실행을 멈추지 않는다 (FR-006) ───────────────────────


async def test_an_exploding_measurement_yields_no_place() -> None:
    """경계 상자 읽기가 터져도 **자리만 잃는다.**

    `_measure` 가 예외를 삼키지 않으면 요소가 사라지는 중인 화면에서 Step 이 실패한다 —
    표시를 위해 실행을 깨는 것이며, 정확히 FR-006 이 막으려는 것이다.
    """

    class ExplodingLocator:
        async def bounding_box(self, timeout: int | None = None) -> dict[str, float]:
            msg = "요소가 사라졌다"
            raise RuntimeError(msg)

    class Located:
        locator = ExplodingLocator()

    assert await _measure(Located()) is None


async def test_an_unmeasurable_element_yields_no_place() -> None:
    """보이지 않는 요소는 `None` 을 돌려준다 — 예외가 아니라 정상 응답이다."""

    class InvisibleLocator:
        async def bounding_box(self, timeout: int | None = None) -> None:
            return None

    class Located:
        locator = InvisibleLocator()

    assert await _measure(Located()) is None
