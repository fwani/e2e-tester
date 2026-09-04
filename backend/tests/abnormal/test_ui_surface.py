"""T023 — 화면(ui) 면의 이상 조작 18건을 판정한다. **실브라우저로 제품 화면을 연다** (RG-105).

시나리오마다 검증 함수를 쓰지 않는다. 목록을 읽어 등록된 실행 수단으로 펼친다 (research R8).

이 면은 제품 서버와 제품 화면을 **둘 다** 띄운다. 그래서 느리다 — 세션 동안 한 번만 띄우고
18건이 나눠 쓴다. 도구·포트가 없으면 건너뛰지 않고 실패한다 (RG-106).

**시나리오는 목록 순서대로 돈다.** 프로젝트 선택 화면(AS-007)은 프로젝트가 열리기 전에만
닿을 수 있고, 제품에 프로젝트를 닫는 경로가 없기 때문이다. 순서가 어긋나면 그 수단이
사유와 함께 실패한다 — 조용히 지나가지 않는다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from playwright.async_api import async_playwright

import tests.abnormal.drivers  # noqa: F401  (수단 등록 부작용)
from tests.abnormal.catalogue import DRIVERS, Scenario, judge, scenarios
from tests.abnormal.product_ui import ProductUI
from tests.abnormal.ui_context import UiContext

UI_SCENARIOS = scenarios("ui")


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


@pytest.mark.parametrize("scenario", UI_SCENARIOS, ids=[s.id for s in UI_SCENARIOS])
async def test_abnormal_screen_operation_is_handled(
    scenario: Scenario, ui_context: UiContext
) -> None:
    """이상 조작 하나를 화면에 가하고 판정 3축을 모두 잰다.

    수단이 없으면 **건너뛰지 않고 실패한다** (RG-106).
    """
    run = DRIVERS.get(scenario.id)
    assert run is not None, f"{scenario}\n  실행 수단이 등록되지 않았다 (RG-106)"

    judge(scenario, await run(ui_context))


def test_the_surface_has_scenarios() -> None:
    """목록을 못 읽은 채 통과하는 상태를 막는다."""
    assert len(UI_SCENARIOS) >= 15, f"ui 면 시나리오를 {len(UI_SCENARIOS)}건밖에 읽지 못했다"


def test_the_project_setup_scenario_runs_first() -> None:
    """프로젝트 선택 화면 시나리오가 화면 면의 **첫 번째**여야 한다.

    그 화면은 프로젝트가 열리기 전에만 닿을 수 있고, 제품에 프로젝트를 닫는 경로가
    없다. 목록 순서가 바뀌면 그 시나리오는 닿을 수 없는 화면을 기다리다 실패한다 —
    실패 사유가 "순서" 라는 것을 아는 데 시간이 걸리므로, 순서 자체를 여기서 못 박는다.
    """
    setup = [s for s in UI_SCENARIOS if s.target == "ProjectSetup"]
    assert setup, "ProjectSetup 시나리오가 목록에 없다"
    assert UI_SCENARIOS[0].target == "ProjectSetup", (
        f"화면 면의 첫 시나리오가 {UI_SCENARIOS[0].id}({UI_SCENARIOS[0].target}) 다. "
        "ProjectSetup 시나리오를 목록에서 화면 면 맨 앞으로 옮기세요 — 그 화면은 "
        "프로젝트가 열리기 전에만 닿을 수 있습니다."
    )
