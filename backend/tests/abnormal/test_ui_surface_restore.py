"""005 T126 — 새로고침이 화면 상태를 잃지 않는다 (FR-166·FR-167 · SC-219).

**실브라우저로 본다.** 이 결함(재점검 N-01)이 자동 검증을 통과했던 이유가 그것이다 —
`frontend/tests/ScreenUrl.test.ts` 는 화면 상태 ↔ 질의 문자열 **변환 함수**를 보고, 변환은
처음부터 옳았다. 틀린 것은 앱이 아직 화면을 정하지 못한 첫 렌더(`loading`)에서 주소를
지운다는 것이었고, 그것은 **실제로 다시 불러올 때만** 드러난다.

`frontend/tests/RecheckPhase12.test.tsx` 가 그 국면을 jsdom 에서 고정하지만, 그것도
"이 조건이 코드에 남아 있는가" 를 보는 계층이다. 여기는 "실제로 그렇게 보이는가" 를 본다 —
`tests/abnormal/screen-blockers.test.tsx` 가 적어 둔 두 계층의 분업과 같다.

이 파일이 이상 경로 패키지에 있는 이유는 **실브라우저 하니스가 여기 있기** 때문이다.
정상 경로 검증의 선례는 `test_product_ui_smoke.py` 다.

**파일 이름이 `test_ui_surface` 뒤에 오도록 붙어 있다.** `product_ui` 는 세션 범위이고
제품에는 프로젝트를 닫는 경로가 없다 — 그래서 프로젝트 선택 화면을 보는 시나리오(AS-007)는
**아무도 프로젝트를 열기 전에** 돌아야 한다 (`test_ui_surface.py` 의 머리글). 이 파일은
`ensure_project()` 를 부르므로 먼저 돌면 그 시나리오의 전제를 깨뜨린다. 처음 이름
(`test_ui_state_restore.py`)이 알파벳순으로 앞에 와서 실제로 그렇게 됐다.

같은 하니스를 쓰는 파일을 또 만들면 **이름을 `test_ui_surface` 뒤로 두거나** 프로젝트를
열지 않게 해야 한다.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from tests.abnormal.ui_context import UiContext


def only_test(ctx: UiContext, name: str) -> str:
    """이 파일의 테스트 하나만 목록에 남긴다.

    `product_ui` 는 세션 범위이므로 앞선 시나리오가 만든 테스트가 목록에 쌓여 있다. 그
    상태에서 「결과 보기」를 누르면 **첫 번째 행**의 것이 눌리고, 그것은 남의 테스트다 —
    실제로 그렇게 됐고, 단독으로는 통과하고 패키지 전체에서는 실패했다.

    `ctx.api()` 는 하니스가 **상태 준비 전용**으로 둔 통로다 (`ui_context.py`). 화면을
    통해 지우면 이 파일이 재려는 것(새로고침 복원) 대신 삭제 흐름을 재게 된다.
    """
    status, body = ctx.api("GET", "/api/tests")
    if status == 200:
        for row in body.get("tests", []):
            ctx.api("DELETE", f"/api/tests/{row['id']}")
    return ctx.make_test_with_bare_result(name)


async def test_result_screen_survives_a_reload(ui_context: UiContext) -> None:
    """결과 화면에서 새로고침하면 **같은 결과 화면**으로 돌아온다 (FR-166).

    재점검 N-01 이 본 것 — F5 하면 목록으로 떨어지고 주소가 `/` 로 초기화됐다. 결과 자체는
    남아 있어 다시 열 수는 있었지만, 사용자는 자기가 보던 화면을 잃었다.
    """
    ui_context.ensure_project()
    test_id = only_test(ui_context, "새로고침으로 잃지 않는다")
    page = await ui_context.open()
    await ui_context.settle(page)

    assert await ui_context.open_result(page), (
        "결과 화면으로 들어가지 못했다 — 「결과 보기」가 없다. 이 시나리오가 재는 것에"
        " 닿기 전에 막혔으므로 조용히 통과시키지 않는다"
    )
    await ui_context.settle(page)

    # 주소가 화면을 실었는가. 이것이 없으면 새로고침이 복원할 근거 자체가 없다.
    before = urlparse(page.url)
    params_before = parse_qs(before.query)
    assert params_before.get("screen") == ["result"], (
        f"결과 화면인데 주소가 그것을 말하지 않는다: {page.url}"
    )
    assert params_before.get("test") == [test_id], (
        f"주소가 어느 테스트인지 말하지 않는다: {page.url}"
    )

    await page.reload(wait_until="domcontentloaded")
    await ui_context.settle(page)

    # 1. 주소가 유지된다. `/` 로 초기화되던 것이 N-01 의 절반이다.
    after = urlparse(page.url)
    params_after = parse_qs(after.query)
    assert params_after.get("screen") == ["result"], (
        f"새로고침이 주소를 잃었다: {page.url} (이전: {before.geturl()})"
    )
    assert params_after.get("test") == [test_id], (
        f"새로고침이 어느 테스트인지 잃었다: {page.url}"
    )

    # 2. **화면도** 유지된다. 주소만 맞고 목록이 그려지면 사용자에게는 여전히 잃은 것이다.
    #
    # 결과 화면 **고유의** 표지를 본다. "목록이 아니다" 를 부정으로 재면 두 화면이
    # 공유하는 머리글에 걸려 우연히 통과하거나 우연히 실패한다.
    text = await ui_context.visible_text(page)
    assert test_id in text, f"복원된 화면에 그 테스트가 없다: {text[:300]}"
    assert "SCREENSHOT" in text, (
        f"주소는 결과 화면인데 증거 탭이 없다 — 복원되지 않았다: {text[:300]}"
    )


async def test_reload_on_the_list_stays_on_the_list(ui_context: UiContext) -> None:
    """목록에서 새로고침하면 목록이다 — 기본 화면에 파라미터를 남기지 않는다.

    복원을 넣다가 **주소에 무엇이든 남기는** 쪽으로 가면 목록이 `?screen=list` 가 되고,
    그때부터 사용자의 북마크와 히스토리가 지저분해진다. 이 단정이 그 방향을 막는다.
    """
    ui_context.ensure_project()
    only_test(ui_context, "목록에 머문다")
    page = await ui_context.open()
    await ui_context.settle(page)

    await page.reload(wait_until="domcontentloaded")
    await ui_context.settle(page)

    assert not parse_qs(urlparse(page.url).query).get("screen"), (
        f"목록인데 주소에 화면 파라미터가 있다: {page.url}"
    )
    assert "테스트 만들기" in await ui_context.visible_text(page)


async def test_going_back_from_the_result_screen_stays_in_the_app(
    ui_context: UiContext,
) -> None:
    """뒤로가기가 앱을 이탈하지 않는다 (FR-167 · SC-219).

    리포트 U-15 가 본 것 — 결과 화면에서 뒤로가기를 누르면 `about:blank` 로 나가 앱을
    완전히 벗어났다. 로컬 도구라도 화면은 브라우저 안에 있고, 뒤로가기는 사용자가 가장
    먼저 누르는 키다.
    """
    ui_context.ensure_project()
    only_test(ui_context, "뒤로가기로 이탈하지 않는다")
    page = await ui_context.open()
    await ui_context.settle(page)

    assert await ui_context.open_result(page), "결과 화면으로 들어가지 못했다"
    await ui_context.settle(page)

    await page.go_back(wait_until="domcontentloaded")
    await ui_context.settle(page)

    assert page.url.startswith(ui_context.ui.base_url), (
        f"뒤로가기가 앱을 벗어났다: {page.url}"
    )
    # 목록으로 돌아왔는가. 빈 화면에 남는 것도 이탈과 다르지 않다.
    assert "테스트 만들기" in await ui_context.visible_text(page), (
        "뒤로가기 후 앱 화면이 그려지지 않았다"
    )
