"""이상 경로 검증의 픽스처.

`product_ui` 는 **제품 서버와 제품 화면을 실제로 띄운다** (RG-105). 세션 범위라 한 번만
띄우고 화면 면 시나리오 18건이 나눠 쓴다.

`ui_browser`·`ui_context` 는 한동안 `test_ui_surface.py` 안에 있었다. 005 T126 이 같은
하니스를 쓰는 두 번째 파일을 만들면서 여기로 옮겼다 — 복사하면 한쪽이 낡고, 그 낡음은
제품의 결함처럼 보인다 (`_FakeSession` 이 정확히 그렇게 됐다).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from playwright.async_api import async_playwright

from tests.abnormal.product_ui import ProductUI, product_ui  # noqa: F401
from tests.abnormal.ui_context import UiContext

__all__ = ["ProductUI", "product_ui", "ui_browser", "ui_context"]


@pytest.fixture
async def ui_browser() -> AsyncIterator[object]:
    """제품 화면을 조작할 브라우저. 제품이 대상 사이트를 여는 브라우저와 별개다.

    **시나리오마다 새로 띄운다.** 세션 범위로 두면 픽스처가 테스트와 다른 이벤트 루프에
    놓여 첫 `await` 에서 영원히 멈춘다 — 실패도 아니고 통과도 아닌 상태가 되어 무엇이
    잘못됐는지 알 수 없다. 브라우저 기동은 1초 미만이라 그 값을 여기에 쓰지 않는다.
    (제품 서버·제품 화면은 `product_ui` 가 세션 동안 한 번만 띄운다 — 그쪽이 비싸다.)
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            yield browser
        finally:
            await browser.close()


@pytest.fixture
async def ui_context(
    product_ui: ProductUI, ui_browser: object, fixture_app: str
) -> AsyncIterator[UiContext]:
    ctx = UiContext(ui=product_ui, browser=ui_browser, fixture_app=fixture_app)  # type: ignore[arg-type]
    # 제품 서버는 세션 동안 하나다. 앞 시나리오가 남긴 세션을 치우지 않으면 다음
    # 시나리오가 다른 화면을 보게 되고, 그 차이가 있지도 않은 결함처럼 보인다.
    ctx.clear_sessions()
    try:
        yield ctx
    finally:
        ctx.clear_sessions()
        await ctx.close_all()
