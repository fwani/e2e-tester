"""T006 — CDP Page.startScreencast 실측 (research R3).

확인 항목:
1. headless 에서 프레임이 오는가 / 프레임률·크기
2. headed 에서 프레임이 오는가
3. ★ 앞에 없는(백그라운드) 탭에서도 프레임이 오는가
   — 미러는 현재 Step 대상 탭을 따라가므로, 그 탭이 앞에 없을 수 있다 (FR-030f, FR-047c)
4. WS 끊김 모사: ack 를 멈추면 어떻게 되는가 (FR-047b)
"""

from __future__ import annotations

import asyncio
import time

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:4300"


async def measure(context, page, label: str, seconds: float = 3.0,
                  ack: bool = True) -> tuple[int, float, int]:
    """label 탭에 스크린캐스트를 걸고 seconds 동안 프레임을 센다."""
    cdp = await context.new_cdp_session(page)
    frames: list[int] = []

    async def on_frame(params) -> None:  # noqa: ANN001
        frames.append(len(params["data"]))
        if ack:
            try:
                await cdp.send("Page.screencastFrameAck",
                               {"sessionId": params["sessionId"]})
            except Exception:  # noqa: BLE001 - 세션 종료 중 ack 실패는 무시
                pass

    cdp.on("Page.screencastFrame", lambda p: asyncio.create_task(on_frame(p)))
    await cdp.send("Page.startScreencast", {
        "format": "jpeg", "quality": 60,
        "maxWidth": 1280, "maxHeight": 800, "everyNthFrame": 1,
    })

    t0 = time.monotonic()
    # 화면을 계속 바꿔 프레임을 유발한다 (스크린캐스트는 변화가 있을 때만 밀어 준다)
    while time.monotonic() - t0 < seconds:
        await page.evaluate(
            "() => { document.title = 'f' + Date.now();"
            " document.body.style.background = "
            "'hsl(' + (Date.now() % 360) + ',40%,96%)'; }"
        )
        await asyncio.sleep(0.1)
    elapsed = time.monotonic() - t0

    try:
        await cdp.send("Page.stopScreencast")
    except Exception:  # noqa: BLE001
        pass
    await cdp.detach()

    avg = int(sum(frames) / len(frames)) if frames else 0
    fps = len(frames) / elapsed
    print(f"  {label:36} 프레임 {len(frames):3}건  {fps:4.1f} fps  평균 {avg:6,}B")
    return len(frames), fps, avg


async def run(headless: bool) -> dict:
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless)
    context = await browser.new_context(viewport={"width": 1280, "height": 800})
    page = await context.new_page()
    await page.goto(f"{BASE}/login.html")

    mode = "headless" if headless else "headed"
    n1, f1, _ = await measure(context, page, f"{mode} · 앞에 있는 탭")

    # ★ 백그라운드 탭: 새 탭을 열고 원래 탭을 앞으로 가져온 뒤, 새 탭을 캐스트한다
    tab1 = await context.new_page()
    await tab1.goto(f"{BASE}/terms.html")
    await page.bring_to_front()
    await asyncio.sleep(0.3)
    n2, f2, _ = await measure(context, tab1, f"{mode} · 뒤에 있는 탭(백그라운드)")

    # ack 를 멈춘 경우 (WS 끊김 모사)
    n3, f3, _ = await measure(context, page, f"{mode} · ack 없음(끊김 모사)",
                              seconds=2.0, ack=False)

    await browser.close()
    await pw.stop()
    return {"front": (n1, f1), "background": (n2, f2), "no_ack": (n3, f3)}


async def main() -> int:
    print("  [headless]")
    hl = await run(headless=True)
    print("  [headed]")
    hd = await run(headless=False)

    print("\n  판정")
    ok_front = hl["front"][0] > 0 and hd["front"][0] > 0
    ok_bg = hd["background"][0] > 0
    print(f"    앞에 있는 탭 프레임 수신: {ok_front}")
    print(f"    ★ 백그라운드 탭 프레임 수신: {ok_bg}"
          + ("" if ok_bg else "  ← 미러가 대상 탭을 따라갈 수 없다. R3 재설계 필요"))
    print(f"    ack 없이도 실행은 계속됨(예외 없음): True "
          f"(프레임 {hd['no_ack'][0]}건에서 멈춤)")
    return 0 if ok_front else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
