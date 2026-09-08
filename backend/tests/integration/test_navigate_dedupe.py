"""이동 Step 의 중복 (FR-030b, TC-010 회귀).

SPA 는 한 번의 조작에 라우트를 여러 번 바꾼다. `framenavigated` 는 `pushState`·
`replaceState` 에도 발생하고 **같은 주소도 그대로 다시 온다**(실측). 그래서 두 종류의
중복이 생겼다.

1. **한 클릭이 만든 이동 사슬.** `_nav_suppress` 를 첫 이동에서 소비했기 때문에 나머지가
   모두 Step 으로 남았다. 실측(TC-010)에서 로그인 한 번이 이동 다섯 번을 만들었고 넷이
   Step 이 됐다. 그 정의를 재실행하면 로그인 클릭 뒤에 `goto /portal-auth/login` 이
   실행되어 **로그인 화면으로 되돌아간다** — 마지막 주소가 우연히 같아서 통과했을 뿐이다.
2. **같은 주소 연속 반복.** 상세 화면 주소가 3번 연달아 Step 이 됐고, 재실행이 같은 곳으로
   `goto` 를 반복했다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from tests.step_wait import wait_for_steps

WINDOW_TAIL_S = 4.4
"""시간창(3000ms) 뒤에 오는 이동까지 관측할 시간. 픽스처의 `after` 기본값(3300ms)보다 뒤."""


def _navigate_urls(client: TestClient, fixture_app: str) -> list[str]:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/spa-routes.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        page = client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.click("[data-testid=spa-go]")
            await asyncio.sleep(WINDOW_TAIL_S)

        client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(
            client, sid, lambda s: any(x["type"] == "navigate" for x in s)
        )
    finally:
        stop_quietly(client, sid)
    return [s["url"] for s in steps if s["type"] == "navigate"]


@pytest.mark.usefixtures("fixture_app")
def test_a_click_that_causes_a_chain_of_navigations_adds_no_navigate_step(
    project_client: TestClient, fixture_app: str
) -> None:
    """클릭이 유발한 이동은 **하나도** Step 이 되지 않는다.

    클릭 Step 이 재실행에서 같은 이동을 다시 만들기 때문이다 (FR-030b). 첫 하나만
    억제하면 나머지가 남아, 재실행이 클릭으로 이미 지나온 주소들을 다시 `goto` 한다.
    """
    urls = _navigate_urls(project_client, fixture_app)
    in_window = [u for u in urls if u.endswith(("?r=a", "?r=b"))]
    assert not in_window, (
        f"클릭이 유발한 이동이 Step 으로 남았다: {in_window} (전체 {urls})"
    )


@pytest.mark.usefixtures("fixture_app")
def test_the_same_url_in_a_row_is_one_navigate_step(
    project_client: TestClient, fixture_app: str
) -> None:
    """같은 주소로 연달아 온 이동은 Step 하나다.

    시간창을 넘긴 뒤에 오는 이동이므로 클릭 억제에는 걸리지 않는다 — 여기서 접는 근거는
    **주소가 직전과 같다** 는 것이다.
    """
    urls = _navigate_urls(project_client, fixture_app)
    repeated = [u for u in urls if u.endswith("?r=c")]
    assert len(repeated) == 1, (
        f"같은 주소가 Step 여러 개로 남았다: {repeated} (전체 {urls})"
    )
