"""지나가며 스친 hover (FR-023c 오탐, TC-012 회귀).

hover Step 은 사람이 지시해서 만들어지지 않는다. 주입 스크립트가 **"포인터가 올라간 뒤
화면이 바뀌었는가"** 로 추론한다. 사람은 클릭하러 가는 길에 여러 요소를 스치므로, 앞선
클릭이 화면을 다시 그리는 중이면 포인터 밑의 **무관한 요소**가 그 변화의 원인으로 기록된다.

실측(TC-012): 자동 감지된 hover 5개가 전부 이 형태였고, 그중 하나(`작업중` 체크박스)는
재실행에서 `<div class="accordion-body">` 에 덮인 요소를 hover 하려다 10초를 쓰고 실패했다.

**정상 hover 를 함께 잃지 않는지 같은 화면에서 본다.** 오탐을 막는다며 감지를 죽이면
`interactions.html` 의 도구 메뉴처럼 hover 없이는 닿을 수 없는 흐름이 깨진다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

from tests.step_wait import wait_for_steps

SETTLE_S = 1.6
"""화면 다시 그리기(8회 × 120ms)가 끝나고 hover 판정 창까지 지나갈 시간."""


def _steps_after(client: TestClient, fixture_app: str, act: Any) -> list[dict[str, Any]]:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/passing-hover.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        page = client.app.state.itb.sessions.require(sid).tabs[0].page
        client.portal.call(act, page)  # type: ignore[attr-defined]
        return wait_for_steps(client, sid, lambda s: bool(s))
    finally:
        stop_quietly(client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_elements_passed_over_on_the_way_to_a_click_are_not_hover_steps(
    project_client: TestClient, fixture_app: str
) -> None:
    """클릭이 다른 곳을 다시 그리는 동안 스친 요소는 hover Step 이 되지 않는다."""

    async def act(p: Any) -> None:
        await p.click("[data-testid=apply]")
        # 다시 그리기가 이어지는 동안 무관한 버튼 위에 포인터를 얹는다.
        await p.hover("[data-testid=reset]")
        await asyncio.sleep(SETTLE_S)

    steps = _steps_after(project_client, fixture_app, act)
    hovers = [
        s["target"].get("accessible_name")
        for s in steps
        if s["type"] == "hover"
    ]
    assert "초기화" not in hovers, (
        f"지나가며 스친 요소가 hover Step 이 됐다: {[(s['type'], s['label']) for s in steps]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_a_css_only_hover_menu_is_still_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """CSS `:hover` 로만 열리는 메뉴는 그대로 기록된다.

    이 신호(렌더된 텍스트 길이 변화)가 살아 있어야 FR-023c 가 성립한다 — 그 메뉴 항목은
    hover 없이는 누를 수 없다.
    """

    async def act(p: Any) -> None:
        await p.hover("[data-testid=menu]")
        await asyncio.sleep(0.6)

    steps = _steps_after(project_client, fixture_app, act)
    hovers = [
        s["target"].get("accessible_name") for s in steps if s["type"] == "hover"
    ]
    assert "도구" in hovers, (
        f"정상 hover 메뉴까지 잃었다: {[(s['type'], s['label']) for s in steps]}"
    )
