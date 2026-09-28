"""turn 상한 도달이 **막힘으로** 보고되는지 (2026-09-28 사용자 보고).

사용자가 본 것은 이 문장이었다 —

    AI 수행 중 예상하지 못한 오류가 발생했습니다: RuntimeError: Claude Code 가 작업을
    끝내지 못했습니다: max_turns

정상적인 상한 도달이 오류로 표시됐고, **막힘에만 열리는 이어가기 칸이 열리지 않아**
그때까지 만든 Step 을 두고 처음부터 다시 해야 했다. 여기서 고정하는 것은 그 결말이다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from itb.authoring.agent import AgentStatus, AuthoringAgent
from itb.authoring.tools import BrowserToolbox, DriverTurnLimitError


def _toolbox() -> BrowserToolbox:
    """`_drive` 가 읽는 것은 `limits` 와 막힘 표시뿐이다. 나머지는 닿지 않는다."""
    return BrowserToolbox(
        session=object(),  # type: ignore[arg-type]
        executor=object(),  # type: ignore[arg-type]
        allocate_step_id=lambda: "step-1",
        on_step=lambda _step: None,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_turn_limit_is_blocked_not_error() -> None:
    """드라이버가 turn 상한에서 멈추면 막힘이다 — 세션이 살아 있어야 한다."""

    async def driver(
        _tools: list[Any], _messages: list[dict[str, Any]], _config: Any
    ) -> AsyncIterator[Any]:
        msg = "대화 turn 이 상한(120회)에 도달해 중단했습니다."
        raise DriverTurnLimitError(msg)
        yield  # pragma: no cover - 제너레이터로 만들기 위한 줄

    agent = AuthoringAgent(toolbox=_toolbox(), driver=driver)
    outcome = await agent.run("로그인하고 목록을 연다")

    assert outcome.status is AgentStatus.BLOCKED, "상한 도달은 실패가 아니다"
    assert outcome.reason is not None
    assert "상한" in outcome.reason
    assert "예상하지 못한 오류" not in outcome.reason
    # 모델이 물은 것이 아니라 예산이 떨어진 것이므로 답할 질문이 없다.
    assert outcome.question is None


@pytest.mark.asyncio
async def test_other_driver_failures_are_still_errors() -> None:
    """**상한만 갈라낸다.** 진짜 실패까지 막힘으로 보이면 이어가기가 헛돈다."""

    async def driver(
        _tools: list[Any], _messages: list[dict[str, Any]], _config: Any
    ) -> AsyncIterator[Any]:
        msg = "Claude Code 가 작업을 끝내지 못했습니다: api_error"
        raise RuntimeError(msg)
        yield  # pragma: no cover - 제너레이터로 만들기 위한 줄

    agent = AuthoringAgent(toolbox=_toolbox(), driver=driver)
    outcome = await agent.run("로그인하고 목록을 연다")

    assert outcome.status is AgentStatus.ERROR
