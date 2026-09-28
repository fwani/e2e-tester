"""공통 대기 도우미 (021 T009 · FR-003·FR-004).

## 이 파일이 재는 것

021 이전에 값 비교 검증의 대기 규칙은 두 갈래였다 — 주소 검증은 제한 시간까지 다시
읽고, 텍스트 검증은 **한 번 읽고 판정했다.** 긍정형에서는 그 차이가 「가끔 실패한다」로
보이지만, 부정형에서는 **「항상 통과한다」**가 된다. 부정 조건의 기본 상태는 참이고,
클릭 직후 화면이 비어 있는 찰나에 평가하면 무엇이든 통과하기 때문이다.

그래서 이 기능은 부정형을 더하는 것으로 끝나지 않고 대기 규칙을 하나로 합친다. 이
파일은 그 도우미 하나만 본다 — 실제 검증에서의 동작은
`tests/integration/test_negative_assertion.py` 가 본다.

**세 가지가 다 필요하다.** 즉시 통과만 재면 기다리지 않는 구현이 통과하고, 대기만
재면 제한 시간을 항상 소모하는 구현이 통과한다.
"""

from __future__ import annotations

import time

import pytest

from itb.execution.step_executor import settle

pytestmark = pytest.mark.asyncio


async def test_a_condition_that_is_already_true_returns_at_once() -> None:
    """이미 참이면 즉시 끝난다 — 제한 시간을 소모하지 않는다 (FR-004).

    통과하는 검증이 매번 제한 시간을 꽉 채우면, 020 이 만든 「실패해도 끝까지 돈다」와
    겹쳐 실행 시간이 감당할 수 없게 늘어난다.
    """
    calls = 0

    async def observe() -> str:
        nonlocal calls
        calls += 1
        return "저장되었습니다"

    started = time.monotonic()
    ok, observed = await settle(observe, lambda v: "저장" in v, deadline=time.monotonic() + 5.0)

    assert ok is True
    assert observed == "저장되었습니다"
    assert calls == 1, "이미 참인데 다시 읽었다"
    assert time.monotonic() - started < 0.5


async def test_a_condition_that_becomes_true_passes_at_that_moment() -> None:
    """중간에 참이 되면 그때 통과한다. **이것이 대기의 목적이다.**"""
    values = ["", "", "처리 중", "저장되었습니다"]

    async def observe() -> str:
        return values.pop(0) if values else "저장되었습니다"

    ok, observed = await settle(
        observe, lambda v: "저장되었습니다" in v, deadline=time.monotonic() + 5.0, poll_ms=10
    )

    assert ok is True
    assert observed == "저장되었습니다"


async def test_a_condition_that_never_holds_reports_the_last_observation() -> None:
    """끝까지 거짓이면 **마지막 관찰값**으로 돌아온다.

    마지막 값이 필요한 이유는 실패 설명에 「실제로는 무엇이었는가」가 들어가야 하기
    때문이다. 020 이 그 문자열을 그대로 어긋남 기록에 싣는다.
    """

    async def observe() -> str:
        return "오류가 발생했습니다"

    ok, observed = await settle(
        observe, lambda v: "오류" not in v, deadline=time.monotonic() + 0.2, poll_ms=10
    )

    assert ok is False
    assert observed == "오류가 발생했습니다"


async def test_the_observation_is_taken_at_least_once_even_past_the_deadline() -> None:
    """제한 시간이 이미 지났어도 한 번은 본다.

    앞선 Step 이 예산을 다 쓴 경우에 그렇다. 한 번도 보지 않고 실패시키면 실패 설명에
    적을 관찰값이 없고, 020 의 어긋남 기록이 빈 문자열을 받는다 — 그것은 「화면이 비어
    있었다」로 읽히는 거짓 기록이다.
    """

    async def observe() -> str:
        return "무언가 있었다"

    ok, observed = await settle(
        observe, lambda v: False, deadline=time.monotonic() - 1.0, poll_ms=10
    )

    assert ok is False
    assert observed == "무언가 있었다"
