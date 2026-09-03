"""T007 — Locator 후보 해석 실측 (research R4).

확인 항목:
1. get_by_role(role, name=...) 의 이름 매칭이 기본 부분 일치인가 완전 일치인가
2. set_test_id_attribute 호출 위치 (Playwright 인스턴스 / 모듈)
3. 후보별 즉시 count() 순회가 실제로 저렴한가
4. 기록 시점 검증이 가능한가 — 수집한 후보가 그 요소를 실제로 가리키는지
"""

from __future__ import annotations

import asyncio
import time

from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:4300"


async def main() -> int:
    pw = await async_playwright().start()

    # 2. set_test_id_attribute 위치 확인
    where = []
    if hasattr(pw, "selectors") and hasattr(pw.selectors, "set_test_id_attribute"):
        where.append("playwright.selectors.set_test_id_attribute")
        pw.selectors.set_test_id_attribute("data-testid")
    print(f"  2. testId 속성 설정 지점: {where or '찾지 못함'}")

    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto(f"{BASE}/login.html")
    await page.fill("#email", "tester@example.com")
    await page.fill("#password", "pw-not-a-real-secret")
    await page.click("[data-testid=login-submit]")
    await page.wait_for_url("**/projects.html")

    # 1. 이름 매칭: "프로젝트 생성" 버튼에 대해 부분 문자열 "프로젝트" 로 찾아본다
    full = await page.get_by_role("button", name="프로젝트 생성").count()
    partial = await page.get_by_role("button", name="프로젝트").count()
    exact_flag = await page.get_by_role("button", name="프로젝트", exact=True).count()
    print(f"  1. get_by_role 이름 매칭 — 완전값 '프로젝트 생성'={full}, "
          f"부분값 '프로젝트'={partial}, exact=True 부분값={exact_flag}")
    if partial > 0 and exact_flag == 0:
        print("     → 기본이 부분 일치다. 후보 해석 시 exact=True 를 써야 다른 요소를 잡지 않는다")
    elif partial == 0:
        print("     → 기본이 완전 일치다. exact 인자 불필요")

    # 3. 후보별 즉시 count() 비용
    target = "[data-testid=create-project]"
    cands = [
        ("test_id", lambda: page.get_by_test_id("create-project")),
        ("role+name", lambda: page.get_by_role("button", name="프로젝트 생성", exact=True)),
        ("label", lambda: page.get_by_label("없는라벨")),
        ("text", lambda: page.get_by_text("프로젝트 생성", exact=True)),
        ("css", lambda: page.locator(".card button")),
    ]
    t0 = time.monotonic()
    results = []
    for name, mk in cands:
        n = await mk().count()
        results.append((name, n))
    cost_ms = (time.monotonic() - t0) * 1000
    print(f"  3. 후보 5종 즉시 count() 총 {cost_ms:.1f}ms → {results}")

    # 4. 기록 시점 검증: 후보로 찾은 요소가 실제 그 요소인지 비교
    handle = await page.query_selector(target)
    verified = {}
    for name, mk in cands:
        loc = mk()
        if await loc.count() != 1:
            verified[name] = "not_collected" if await loc.count() == 0 else "ambiguous"
            continue
        other = await loc.element_handle()
        same = await page.evaluate("([a,b]) => a === b", [handle, other])
        verified[name] = "verified" if same else "unverified"
    print(f"  4. 기록 시점 검증 결과: {verified}")

    await browser.close()
    await pw.stop()
    ok = verified.get("test_id") == "verified"
    print(f"\n  판정: 기록 시점 검증 가능 → {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
