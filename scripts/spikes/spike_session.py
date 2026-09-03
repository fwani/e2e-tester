"""T003 — 장수명 BrowserContext 유지 확인 (research R1).

async_playwright().start() 로 띄운 컨텍스트가 유지되는 동안 CDP 연결이 끊기지 않는지,
그리고 Pause = asyncio.Event await 로 상태가 보존되는지 확인한다.

기본은 짧게(20초) 돌린다. 장시간 확인은 --minutes 로 늘린다.
"""

from __future__ import annotations

import argparse
import asyncio
import time

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:4300"


async def main(minutes: float) -> int:
    pw = await async_playwright().start()  # 컨텍스트 매니저를 쓰지 않는다 (R1)
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    await page.goto(f"{BASE}/login.html")
    await page.fill("#email", "tester@example.com")
    await page.fill("#password", "pw-not-a-real-secret")
    await page.click("[data-testid=login-submit]")
    await page.wait_for_url("**/projects.html")
    print("  로그인 완료, 프로젝트 화면 진입")

    # 화면에 흔적을 남겨 상태 보존을 확인한다
    await page.click("#open-create")
    await page.fill("#pname", "SPIKE")
    print("  모달 열고 이름 입력 — 이 상태가 유지되어야 한다")

    # Pause 를 asyncio.Event 로 모사한다. 브라우저에 아무 명령도 보내지 않는다.
    resume = asyncio.Event()
    deadline = time.monotonic() + minutes * 60

    async def waiter() -> None:
        try:
            await asyncio.wait_for(resume.wait(), timeout=minutes * 60)
        except TimeoutError:
            pass

    task = asyncio.create_task(waiter())
    checks = 0
    while time.monotonic() < deadline:
        await asyncio.sleep(5)
        checks += 1
        # CDP 연결이 살아 있는지: 간단한 평가를 시도한다
        alive = await page.evaluate("() => document.readyState")
        val = await page.input_value("#pname")
        modal_open = not await page.locator("#create-modal").evaluate(
            "el => el.classList.contains('hidden')"
        )
        print(f"  +{checks * 5:>3}s  readyState={alive}  #pname={val!r}  모달열림={modal_open}")
        if val != "SPIKE" or not modal_open:
            print("  ✗ 일시정지 중 상태가 보존되지 않았다")
            await browser.close()
            await pw.stop()
            return 1

    resume.set()
    await task
    print("  ✓ 일시정지 중 CDP 연결과 화면 상태가 모두 보존됨")

    # Resume 후 이어서 진행 — 재시작 없이 저장이 되는지
    await page.click("[data-testid=save-project]")
    await page.wait_for_selector("text=SPIKE")
    print("  ✓ Resume 후 브라우저 재시작 없이 이어서 실행 성공")

    await browser.close()
    await pw.stop()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--minutes", type=float, default=0.35)
    raise SystemExit(asyncio.run(main(ap.parse_args().minutes)))
