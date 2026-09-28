"""「진전」을 무엇으로 판정하는가 (022 US3 · FR-020).

**Step 수만 본다.** 도구 호출 성공을 함께 보면 `observe_page` 하나만 성공해도 참이 되어
**울리지 않는 경고**가 된다 — 사용자가 그것을 「진전 중이구나」로 읽기 때문에, 경고가
없는 것보다 나쁘다 (research R3).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from itb.authoring.agent import AuthoringAgent
from itb.authoring.tools import BrowserToolbox


class _Compiler:
    """`_count` 가 읽는 것은 `.count` 하나뿐이다."""

    def __init__(self, count: int) -> None:
        self.count = count


def _agent(*, steps_now: int, baseline: int | None) -> AuthoringAgent:
    toolbox = BrowserToolbox(
        session=object(),  # type: ignore[arg-type]
        executor=object(),  # type: ignore[arg-type]
        allocate_step_id=lambda: "step-1",
        on_step=lambda _step: None,  # type: ignore[arg-type]
    )
    toolbox.limits.steps_at_attempt_start = baseline

    async def driver(
        _tools: list[Any], _messages: list[dict[str, Any]], _config: Any
    ) -> AsyncIterator[Any]:
        yield type("M", (), {"content": [], "stop_reason": None})()

    return AuthoringAgent(
        toolbox=toolbox,
        driver=driver,
        compiler=_Compiler(steps_now),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_no_baseline_means_undecidable_not_stalled() -> None:
    """**첫 시도에는 판정하지 않는다** — 비교할 직전 값이 없다.

    `None` 과 `False` 를 묶으면 첫 시도에서 상한에 닿은 사용자가 근거 없는 경고를 본다.
    """
    outcome = await _agent(steps_now=0, baseline=None).run("무언가")
    assert outcome.made_progress is None


@pytest.mark.asyncio
async def test_steps_grew_is_progress() -> None:
    """이어간 뒤 Step 이 늘었으면 진전이다."""
    outcome = await _agent(steps_now=5, baseline=3).run("무언가")
    assert outcome.made_progress is True


@pytest.mark.asyncio
async def test_steps_unchanged_is_no_progress() -> None:
    """Step 이 그대로면 진전이 없다 — 화면이 이 사실을 알린다 (FR-020)."""
    outcome = await _agent(steps_now=3, baseline=3).run("무언가")
    assert outcome.made_progress is False


@pytest.mark.asyncio
async def test_progress_rides_along_with_the_cumulative_count() -> None:
    """누적과 진전은 **같은 결말에** 함께 실린다 (FR-017·FR-019·FR-020).

    화면이 셋을 한 자리에서 읽어야 「87회 썼는데 Step 은 안 늘었다」를 말할 수 있다.
    """
    agent = _agent(steps_now=3, baseline=3)
    agent.toolbox.limits.record_call()
    agent.toolbox.limits.record_call()

    outcome = await agent.run("무언가")

    assert outcome.total_tool_calls == 2
    assert outcome.step_count == 3
    assert outcome.made_progress is False
