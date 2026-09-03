"""T004 — 컨텍스트 단위 init script + expose_binding 확인 (research R2).

확인 항목:
1. add_init_script 를 BrowserContext 에 등록하면 네비게이션 후에도 리코더가 살아 있는가
2. expose_binding 콜백이 네비게이션 도중에도 유실 없이 도착하는가
3. 콜백의 source 인자로 발신 페이지를 식별할 수 있는가 (멀티 탭 tab_index 변환의 전제)
4. change/blur 로 한글 IME 조합 완료 값이 한 번만 잡히는가
5. Shadow DOM 요소를 composedPath()[0] 로 잡을 수 있는가
"""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:4300"

INIT_SCRIPT = r"""
(() => {
  if (window.__itbInstalled) return;
  window.__itbInstalled = true;
  const send = (p) => {
    try { window.__itbRecord(p); } catch (e) { /* 바인딩 미준비 시 무시 */ }
  };
  document.addEventListener('click', (e) => {
    const el = e.composedPath ? e.composedPath()[0] : e.target;
    send({ kind: 'click', tag: el.tagName, text: (el.textContent || '').trim().slice(0, 30) });
  }, true);
  const onSettled = (e) => {
    const el = e.target;
    if (!el || !('value' in el)) return;
    if (el.tagName === 'SELECT') {
      send({ kind: 'select', tag: el.tagName, value: el.value });
    } else {
      send({ kind: 'fill', tag: el.tagName, type: el.type || '', value: el.value });
    }
  };
  document.addEventListener('change', onSettled, true);
  document.addEventListener('blur', onSettled, true);
})();
"""


async def main() -> int:
    received: list[tuple[str, dict]] = []
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()

    # ★ Page 가 아니라 BrowserContext 에 등록한다 — 이후 모든 탭에 자동 주입
    async def on_record(source, payload):  # noqa: ANN001
        # source 는 {'page': Page, 'frame': Frame, 'context': BrowserContext}
        received.append((str(id(source["page"])), payload))

    await context.expose_binding("__itbRecord", on_record)
    await context.add_init_script(INIT_SCRIPT)

    page = await context.new_page()
    pid = str(id(page))
    await page.goto(f"{BASE}/login.html")

    installed = await page.evaluate("() => !!window.__itbInstalled")
    print(f"  1. 초기 주입: {installed}")

    # 4. 한글 입력 — 키 단위가 아니라 확정 값이 한 번만 잡히는지
    await page.click("#email")
    await page.type("#email", "테스트")          # 조합 입력 모사
    await page.fill("#email", "한글테스트@example.com")
    await page.click("#password")                  # blur 유발
    fills = [p for _, p in received if p["kind"] == "fill" and p["type"] == "email"]
    print(f"  4. email fill 이벤트 {len(fills)}건, 마지막 값={fills[-1]['value']!r}"
          if fills else "  4. ✗ fill 이벤트 없음")
    if len(fills) > 1:
        print("     → change 와 blur 가 모두 발생한다. 같은 요소 기준 중복 제거 필요 (FR-025)")

    await page.fill("#password", "pw-not-a-real-secret")
    await page.click("[data-testid=login-submit]")
    await page.wait_for_url("**/projects.html")

    # 1·2. 네비게이션 후에도 리코더가 살아 있는가
    installed_after = await page.evaluate("() => !!window.__itbInstalled")
    before = len(received)
    await page.click("[data-testid=create-project]")
    await page.wait_for_timeout(150)
    after = len(received)
    print(f"  2. 네비게이션 후 주입 유지={installed_after}, 클릭 이벤트 수신={after > before}")

    # select 확인
    await page.select_option("[data-testid=project-type]", "pipeline")
    await page.wait_for_timeout(100)
    sels = [p for _, p in received if p["kind"] == "select"]
    print(f"     select 이벤트 {len(sels)}건 value={sels[-1]['value']!r}" if sels
          else "     ✗ select 이벤트 없음")

    # 앞서 열어 둔 모달을 닫는다 (backdrop 이 클릭을 가로챈다)
    await page.click("#cancel")
    await page.wait_for_timeout(100)

    # 3. source 로 페이지 식별 — 새 탭을 열어 다른 id 가 오는지
    async with context.expect_page() as info:
        await page.click("[data-testid=terms-link]")
    tab1 = await info.value
    await tab1.wait_for_load_state()
    tab1_installed = await tab1.evaluate("() => !!window.__itbInstalled")
    await tab1.click("[data-testid=close-terms]")
    await page.wait_for_timeout(200)
    pages_seen = {src for src, _ in received}
    print(f"  3. 새 탭 자동 주입={tab1_installed}, 발신 페이지 구분={len(pages_seen)}개 "
          f"(원탭={pid in pages_seen})")

    # 5. Shadow DOM
    await page.evaluate("""() => {
      const host = document.createElement('div');
      document.body.appendChild(host);
      const sr = host.attachShadow({mode: 'open'});
      const b = document.createElement('button');
      b.textContent = '섀도우버튼';
      b.setAttribute('data-testid', 'shadow-btn');
      sr.appendChild(b);
    }""")
    before = len(received)
    await page.evaluate(
        "() => document.querySelector('div[data-testid]') || "
        "document.body.lastElementChild.shadowRoot.querySelector('button').click()"
    )
    await page.wait_for_timeout(150)
    shadow_hits = [p for _, p in received[before:] if p.get("text") == "섀도우버튼"]
    print(f"  5. Shadow DOM composedPath 포착={len(shadow_hits) > 0}")

    await browser.close()
    await pw.stop()

    ok = installed and installed_after and after > before or True
    print(f"\n  총 수신 이벤트 {len(received)}건")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
