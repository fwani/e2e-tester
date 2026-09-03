"""Step 의 `tab` 참조 → 실제 `Page`. FR-030d (research R2).

**탭은 대상 앱이 여는 것이다.** 저장된 Step 이 탭 1을 가리켜도, 재실행 시점에 그 탭은 아직
없을 수 있다 — 앞선 클릭이 유발한 새 탭이 열리는 데 시간이 걸린다. 그래서 즉시 실패시키지
않고 Step 의 대기 상한까지 기다린다.

기다려도 열리지 않으면 **어느 탭을 기다렸는지**를 사유에 담아 실패시킨다. "요소를 찾을 수
없습니다" 로 뭉뚱그리면 사용자는 탭 문제인지 요소 문제인지 구분할 수 없다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.async_api import Page

from itb.execution.session import BrowserSession, TabNotFoundError


@dataclass(slots=True)
class TabResolution:
    """탭 해석 결과."""

    page: Page
    tab_index: int
    waited_ms: int
    """대상 탭이 열리기를 기다린 시간. 실패 진단에 쓴다 (RunResult.tab_wait_ms)."""


async def resolve_tab(
    session: BrowserSession, tab_index: int, timeout_ms: int
) -> TabResolution:
    """Step 의 탭 참조를 `Page` 로 바꾼다.

    이미 열려 있으면 대기 없이 돌려준다. 없으면 `timeout_ms` 까지 기다린다 — 대기는
    `BrowserSession.wait_for_tab` 이 `context.on("page")` 로 등록된 탭 이벤트를 근거로 한다.
    """
    started = time.monotonic()
    handle = session.find_tab(tab_index)
    if handle is not None and not handle.closed:
        return TabResolution(page=handle.page, tab_index=tab_index, waited_ms=0)

    handle = await session.wait_for_tab(tab_index, timeout_ms)
    waited_ms = int((time.monotonic() - started) * 1000)
    return TabResolution(page=handle.page, tab_index=tab_index, waited_ms=waited_ms)


def describe_tab_failure(exc: TabNotFoundError, tab_index: int) -> str:
    """탭 해석 실패를 사용자 문장으로 만든다.

    `BrowserSession.wait_for_tab` 이 이미 사유를 만들어 두었다. 여기서는 탭 번호가 반드시
    문장에 있음을 보장한다 — 메시지 생성 지점이 바뀌어도 번호가 빠지지 않게 하는 이중 장치다.
    """
    message = str(exc)
    if f"탭 {tab_index}" in message:
        return message
    return f"탭 {tab_index} 을 사용할 수 없습니다. {message}"
