"""T012 확인 — 제품 UI 가 실제로 뜨는가.

이 저장소에서 **제품 화면을 실제로 여는 첫 검증**이다. 이것이 통과해야 화면 면 18건을
판정할 수 있다 (RG-105).
"""

from __future__ import annotations

from playwright.async_api import async_playwright

from tests.abnormal.product_ui import ProductUI


async def test_product_ui_actually_renders(product_ui: ProductUI) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto(product_ui.base_url, wait_until="networkidle")
            body = (await page.inner_text("body")).strip()
            assert body, "제품 화면이 비어 있다 — 화면이 뜨지 않았다"
            print(f"\n제목: {await page.title()!r}")
            print(f"화면 첫 200자:\n{body[:200]}")
        finally:
            await browser.close()
