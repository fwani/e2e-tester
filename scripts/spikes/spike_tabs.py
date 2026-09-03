"""T005 — context.on("page") 가 새 탭 두 경로 모두에서 발생하는지 확인 (research R1).

target="_blank" 링크와 window.open 팝업은 브라우저 내부에서 다르게 처리된다.
한쪽만 잡히면 page.on("popup") 보완이 필요하다 (FR-030a).
탭 닫힘 감지(FR-030c)와 tab_index 재사용 금지 전제도 함께 본다.
"""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:4300"


async def main() -> int:
    opened: list[str] = []
    closed: list[str] = []
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()

    order: dict[int, int] = {}   # id(page) -> tab_index
    next_index = 0

    def on_page(p) -> None:  # noqa: ANN001
        nonlocal next_index
        order[id(p)] = next_index
        opened.append(f"tab{next_index}:{p.url or '(about:blank)'}")
        next_index += 1
        p.on("close", lambda pg=p: closed.append(f"tab{order[id(pg)]}"))

    context.on("page", on_page)

    page = await context.new_page()          # 최초 탭 → tab0
    await page.goto(f"{BASE}/login.html")
    await page.fill("#email", "tester@example.com")
    await page.fill("#password", "pw-not-a-real-secret")
    await page.click("[data-testid=login-submit]")
    await page.wait_for_url("**/projects.html")

    # 경로 A: target="_blank" 링크
    await page.click("[data-testid=terms-link]")
    await asyncio.sleep(0.6)
    via_blank = len(opened) - 1
    print(f"  A. target=_blank 링크 → on('page') 발생 {via_blank}회")

    # 경로 B: window.open 팝업
    before = len(opened)
    await page.click("#terms-popup")
    await asyncio.sleep(0.6)
    via_open = len(opened) - before
    print(f"  B. window.open 팝업  → on('page') 발생 {via_open}회")

    print(f"  열린 탭: {opened}")

    # 탭 닫힘 감지 (FR-030c)
    pages = context.pages
    if len(pages) >= 2:
        await pages[1].close()
        await asyncio.sleep(0.4)
    print(f"  탭 닫힘 감지: {closed}")

    # tab_index 재사용 금지 확인 — 닫은 뒤 새 탭을 열면 다음 번호를 받아야 한다
    before_idx = next_index
    newp = await context.new_page()
    await asyncio.sleep(0.3)
    print(f"  닫은 뒤 새 탭 번호={order.get(id(newp))} (재사용 금지 → {before_idx} 이어야 함)")

    await browser.close()
    await pw.stop()

    ok = via_blank >= 1 and via_open >= 1
    print(f"\n  판정: 두 경로 모두 on('page') 로 포착 → {ok}")
    if not ok:
        print("  ✗ page.on('popup') 보완이 필요하다")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
