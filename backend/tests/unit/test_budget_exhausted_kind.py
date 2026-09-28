"""예산 소진이 다른 막힘과 갈리는가 (022 US1 · FR-001~FR-004).

**판정은 제품이 센 값으로만 한다.** 모델이 무엇을 신고하든 그것은 근거가 아니다 —
근거로 삼으면 모델이 「예산이 없다」고 말하는 것만으로 사용자가 다른 화면을 본다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from itb.authoring.agent import AgentStatus, AuthoringAgent
from itb.authoring.tools import BlockedKind, BrowserToolbox, DriverTurnLimitError


def _toolbox() -> BrowserToolbox:
    """`_drive` 가 읽는 것은 `limits` 와 막힘 표시뿐이다."""
    return BrowserToolbox(
        session=object(),  # type: ignore[arg-type]
        executor=object(),  # type: ignore[arg-type]
        allocate_step_id=lambda: "step-1",
        on_step=lambda _step: None,  # type: ignore[arg-type]
    )


def _driver_yielding_nothing() -> Any:
    """메시지 하나를 흘리고 끝나는 드라이버. 판정은 그 메시지에서 일어난다."""

    async def driver(
        _tools: list[Any], _messages: list[dict[str, Any]], _config: Any
    ) -> AsyncIterator[Any]:
        yield type("M", (), {"content": [], "stop_reason": None})()

    return driver


@pytest.mark.asyncio
async def test_call_ceiling_is_budget_exhaustion() -> None:
    """도구 호출 총 상한 도달은 `budget_exhausted` 다 (FR-001)."""
    toolbox = _toolbox()
    toolbox.limits.max_calls = 1
    toolbox.limits.record_call()
    toolbox.limits.record_call()  # 상한 도달

    agent = AuthoringAgent(toolbox=toolbox, driver=_driver_yielding_nothing())
    outcome = await agent.run("무언가 한다")

    assert outcome.status is AgentStatus.BLOCKED
    assert outcome.blocked_kind is BlockedKind.BUDGET_EXHAUSTED


@pytest.mark.asyncio
async def test_driver_turn_limit_is_budget_exhaustion_too() -> None:
    """**두 상한이 사용자에게 같게 보인다** (FR-004).

    세는 주체만 다를 뿐 같은 사실이고, 어느 쪽에 닿았는지로 할 일이 갈리지 않는다.
    """

    async def driver(
        _tools: list[Any], _messages: list[dict[str, Any]], _config: Any
    ) -> AsyncIterator[Any]:
        msg = "대화 turn 이 상한(120회)에 도달해 중단했습니다."
        raise DriverTurnLimitError(msg)
        yield  # pragma: no cover - 제너레이터로 만들기 위한 줄

    agent = AuthoringAgent(toolbox=_toolbox(), driver=driver)
    outcome = await agent.run("무언가 한다")

    assert outcome.status is AgentStatus.BLOCKED
    assert outcome.blocked_kind is BlockedKind.BUDGET_EXHAUSTED


@pytest.mark.asyncio
async def test_consecutive_failures_are_not_budget_exhaustion() -> None:
    """같은 요소에 연속 실패한 것은 예산 소진이 **아니다** (FR-002).

    예산은 남아 있고 그 경로가 막힌 것이다 — 사람이 알려 주면 풀릴 수 있으므로
    답변 칸이 열려야 한다.
    """
    toolbox = _toolbox()
    toolbox.limits.max_element_failures = 2
    toolbox.limits.record_failure("#save")
    toolbox.limits.record_failure("#save")

    agent = AuthoringAgent(toolbox=toolbox, driver=_driver_yielding_nothing())
    outcome = await agent.run("무언가 한다")

    assert outcome.status is AgentStatus.BLOCKED
    assert outcome.blocked_kind is not BlockedKind.BUDGET_EXHAUSTED


@pytest.mark.asyncio
async def test_what_the_model_reports_does_not_decide_budget() -> None:
    """**모델의 말은 판정 근거가 아니다** (FR-003).

    모델이 「예산이 없다」는 뜻으로 막힘을 신고해도, 제품이 센 값이 그렇지 않으면
    예산 소진이 아니다.
    """
    toolbox = _toolbox()

    # `_drive` 는 시작할 때 막힘 표시를 비운다(앞선 시도의 표시가 남지 않게). 그래서
    # 도구가 그러듯 **루프가 도는 중에** 신고한다.
    async def driver(
        _tools: list[Any], _messages: list[dict[str, Any]], _config: Any
    ) -> AsyncIterator[Any]:
        toolbox.blocked_reason = "예산이 떨어져서 더 못 합니다"
        toolbox.blocked_kind = BlockedKind.NEEDS_INPUT
        yield type("M", (), {"content": [], "stop_reason": None})()

    agent = AuthoringAgent(toolbox=toolbox, driver=driver)
    outcome = await agent.run("무언가 한다")

    assert outcome.status is AgentStatus.BLOCKED
    assert outcome.blocked_kind is BlockedKind.NEEDS_INPUT, (
        "문구가 아니라 제품이 센 값이 판정한다"
    )


@pytest.mark.asyncio
async def test_budget_exhaustion_carries_no_question() -> None:
    """예산 소진에는 물을 것이 없다 (FR-013 의 전제).

    모델이 남긴 질문이 있어도 그것은 다른 막힘의 질문이며, 예산이 떨어진 사실에 대한
    답은 아니다.
    """
    toolbox = _toolbox()
    toolbox.limits.max_calls = 1
    toolbox.limits.record_call()
    toolbox.limits.record_call()
    toolbox.blocked_question = "어느 계정으로 로그인할까요?"

    agent = AuthoringAgent(toolbox=toolbox, driver=_driver_yielding_nothing())
    outcome = await agent.run("무언가 한다")

    assert outcome.blocked_kind is BlockedKind.BUDGET_EXHAUSTED
    assert outcome.question is None
