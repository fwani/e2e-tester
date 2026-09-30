"""Step 진입 전 화면 전환 대기 (2026-09-30 사용자 보고).

## 무엇이 문제였나

보고 문장: 「실행 속도 조절이 있는데, 빠름을 했을때 … 그냥 속도만 빠르게 조절되는거같아서,
다음 동작을 하는데 있어서 앞선 스텝이 이루어져야하는데 그냥 지나가버려서 작성한 테스트가
중간에 실패한다.」

진단이 맞다. 실행 속도(004)는 Step 사이에 **쉬는 시간**일 뿐 아무것도 확인하지 않는다
(`itb.domain.run_pacing`). `NORMAL` 의 500ms 가 우연히 메워 주던 전환의 틈이 `FAST` 에서
그대로 드러난 것이고, 그 결과 **속도 설정이 테스트의 성패를 갈랐다.**

## 여기서 못 박는 것

1. 모든 Step 이 진입 전에 진행 중인 문서 전환을 기다린다 — 속도와 무관하게
2. 기다림이 Step 예산을 통째로 쓰지 않는다 — 판정은 뒤에 온다
3. 전환이 안 끝나도 여기서 실패시키지 않는다 — 원인을 가리키지 않는 실패가 늘지 않는다
4. 제품과 내보낸 코드가 **같은 자리에서 같은 것을 기다린다** (원칙 IV·V)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from playwright.async_api import Error as PlaywrightError

from itb.domain.assertion import Assertion, AssertionKind
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    CloseTabStep,
    NavigateStep,
)
from itb.domain.test_case import AuthoringMode, Test
from itb.execution.step_executor import _TRANSITION_WAIT_MS, StepExecutor
from itb.generator.playwright_gen import generate_spec

SETTLE_LINE = "waitForLoadState('domcontentloaded')"


class FakePage:
    """`wait_for_load_state` 만 있는 page. 부른 인자와 횟수를 기록한다."""

    def __init__(self, *, raises: Exception | None = None, delay_s: float = 0.0) -> None:
        self.calls: list[tuple[str, int]] = []
        self._raises = raises
        self._delay_s = delay_s

    async def wait_for_load_state(self, state: str, *, timeout: float) -> None:
        self.calls.append((state, int(timeout)))
        if self._delay_s:
            await asyncio.sleep(self._delay_s)
        if self._raises is not None:
            raise self._raises


def executor() -> StepExecutor:
    """세션도 해석기도 쓰지 않는 경로다 — `_settle_transition` 은 `_left` 만 부른다."""
    return StepExecutor(None, None)  # type: ignore[arg-type]


def deadline_in(seconds: float) -> float:
    import time

    return time.monotonic() + seconds


# ─── 1. 무엇을 기다리는가 ───────────────────────────────────────────────────


async def test_waits_for_the_document_not_for_the_network() -> None:
    """`networkidle` 이 아니다.

    대상 화면이 WebSocket 이나 폴링을 쓰면 idle 은 영영 오지 않는다. 그러면 모든 Step 이
    예산을 통째로 버리고, 증상은 「빠름에서 실패한다」보다 나쁜 「전부 느려졌다」가 된다.
    """
    page = FakePage()
    await executor()._settle_transition(page, deadline_in(10))  # type: ignore[arg-type]
    assert [state for state, _ in page.calls] == ["domcontentloaded"]


async def test_the_wait_is_capped_below_the_step_budget() -> None:
    """Step 예산(기본 10초)이 넉넉해도 상한을 넘지 않는다.

    이 대기는 보조이고 판정은 뒤에 온다. 여기서 예산을 다 쓰면 정작 요소를 찾을 시간이
    남지 않는다 — 그것은 고치려던 증상을 다른 모양으로 되살린다.
    """
    page = FakePage()
    await executor()._settle_transition(page, deadline_in(60))  # type: ignore[arg-type]
    assert page.calls[0][1] <= _TRANSITION_WAIT_MS


async def test_a_short_budget_shrinks_the_wait() -> None:
    """남은 예산이 상한보다 적으면 남은 만큼만 기다린다 (FR-057)."""
    page = FakePage()
    await executor()._settle_transition(page, deadline_in(0.5))  # type: ignore[arg-type]
    assert page.calls[0][1] < _TRANSITION_WAIT_MS


# ─── 2. 여기서 판정하지 않는다 ──────────────────────────────────────────────


async def test_a_timeout_does_not_fail_the_step() -> None:
    """전환이 안 끝났다는 것은 그 자체로 판정이 아니다.

    화면이 아직 아니라면 이어지는 요소 탐색이 남은 예산으로 같은 사실을 훨씬 정확한
    문장으로 알린다 — 「무엇을 못 찾았는가」. 여기서 던지면 원인을 가리키지 않는 실패
    유형이 하나 더 생길 뿐이다.
    """
    page = FakePage(raises=PlaywrightError("Timeout 5000ms exceeded"))
    waited = await executor()._settle_transition(page, deadline_in(10))  # type: ignore[arg-type]
    assert waited >= 0


async def test_a_closed_page_does_not_fail_the_step() -> None:
    """전환 도중 탭이 닫히는 경우도 같은 경로다."""
    page = FakePage(raises=PlaywrightError("Target page, context or browser has been closed"))
    await executor()._settle_transition(page, deadline_in(10))  # type: ignore[arg-type]


@pytest.mark.timing
async def test_it_reports_how_long_it_waited() -> None:
    """기다린 시간은 `tab_wait_ms` 에 더해진다 — 예산이 어디로 갔는지 남아야 한다."""
    page = FakePage(delay_s=0.12)
    waited = await executor()._settle_transition(page, deadline_in(10))  # type: ignore[arg-type]
    assert waited >= 100


# ─── 3. 내보낸 코드가 같은 자리에서 같은 것을 기다린다 (원칙 IV·V) ──────────


def cand(value: str) -> Candidate:
    return Candidate(value=value, status=CandidateStatus.VERIFIED)


def test_exported_code_settles_before_every_step() -> None:
    """제품에서 통과한 정의가 내보낸 뒤 깨지면 원칙 V 가 약속한 이식성이 무너진다.

    그 차이는 앞선 Step 이 전환을 일으키는 화면에서만 나타나므로, 내보내기를 시험한
    사람에게는 「가끔 깨진다」로 보인다 — 그래서 문장이 아니라 검사로 고정한다.
    """
    test = Test(
        id="TC-900",
        name="전환 뒤 입력",
        authoring_mode=AuthoringMode.RECORD,
        start_url="https://example.internal/",
        steps=[
            ClickStep(id="step-01", label="저장", tab=0, target=target_of("save")),
            AssertionStep(
                id="step-02",
                label="완료 표시",
                tab=0,
                assertion=Assertion(
                    kind=AssertionKind.VISIBLE, target=target_of("done")
                ),
            ),
            NavigateStep(id="step-03", label="목록", tab=0, url="https://example.internal/list"),
        ],
    )
    code = generate_spec(test)
    assert code.count(SETTLE_LINE) == len(test.steps)


def test_closing_a_tab_does_not_wait_for_it_to_load() -> None:
    """없어질 탭의 로드를 기다릴 이유가 없다. 실행기도 그 종류를 대기 앞에서 돌려보낸다."""
    test = Test(
        id="TC-901",
        name="탭 닫기",
        authoring_mode=AuthoringMode.RECORD,
        start_url="https://example.internal/",
        steps=[
            ClickStep(id="step-01", label="열기", tab=0, target=target_of("open")),
            CloseTabStep(id="step-02", label="닫기", tab=0),
        ],
    )
    code = generate_spec(test)
    assert code.count(SETTLE_LINE) == 1


def target_of(test_id: str) -> Any:
    return TargetLocator(test_id=cand(test_id))
