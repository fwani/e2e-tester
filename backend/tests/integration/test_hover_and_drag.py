"""T161 — hover·drag 조작 충실도 (FR-023c).

`interactions.html` 은 **클릭만으로는 도달할 수 없는 요소**를 둔다. `도구` 하위 메뉴는
CSS `:hover` 로만 열리므로, hover 가 Step 으로 남지 않으면 `내보내기` 를 누르는 재실행이
실패한다 — 이 화면이 hover 기록이 실제로 필요한지를 판정한다.

**녹화만 보지 않고 재실행까지 본다.** Step 이 만들어졌다는 것과 그 Step 으로 같은 결과를
재현할 수 있다는 것은 다른 주장이다 (헌법 품질 게이트 2).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import replay, result_of, stop_quietly

from tests.step_wait import has_kinds, wait_for_steps

HOVER_SETTLE_S = 0.4
"""hover 가 화면을 바꿨는지 리코더가 관측할 시간. 주입 스크립트의 창(300ms)보다 넉넉하다."""


def _record_session(client: TestClient, fixture_app: str) -> str:
    resp = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/interactions.html"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["session_id"])


def _steps(client: TestClient, sid: str) -> list[dict[str, Any]]:
    return list(client.get(f"/api/sessions/{sid}").json()["steps"])


@pytest.mark.usefixtures("fixture_app")
def test_hover_that_changes_the_screen_is_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-023c — hover 로 메뉴가 열리면 그 hover 가 Step 으로 남는다."""
    sid = _record_session(project_client, fixture_app)
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.hover("[data-testid=tools-menu]")
            await asyncio.sleep(HOVER_SETTLE_S)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(project_client, sid, has_kinds("hover"))
        hovers = [s for s in steps if s["type"] == "hover"]
        assert hovers, (
            "메뉴를 여는 hover 가 기록되지 않았다. "
            f"기록된 종류: {[s['type'] for s in steps]}"
        )
        target = hovers[-1]["target"]
        assert target["test_id"]["value"] == "tools-menu"
        assert target["test_id"]["status"] == "verified"
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_hover_without_effect_is_not_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """화면을 바꾸지 않은 hover 는 기록하지 않는다.

    포인터가 지나간 모든 요소를 Step 으로 만들면 정의가 쓸모없이 길어지고, 어느 hover 가
    의미 있었는지 사람이 다시 판단해야 한다.
    """
    sid = _record_session(project_client, fixture_app)
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            # nav 링크는 hover 로 아무것도 열지 않는다.
            await p.hover("nav a[href='data.html']")
            await asyncio.sleep(HOVER_SETTLE_S)
            await p.hover("nav a[href='analysis.html']")
            await asyncio.sleep(HOVER_SETTLE_S)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = _steps(project_client, sid)
        assert not [s for s in steps if s["type"] == "hover"], (
            f"효과 없는 hover 가 Step 으로 기록됐다: {steps}"
        )
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_drag_is_recorded_with_both_ends(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-023c — 끌어다 놓기는 끄는 대상과 놓는 위치를 모두 담은 Step 하나가 된다."""
    sid = _record_session(project_client, fixture_app)
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.drag_and_drop("[data-testid=chip-events]", "#archive")
            await asyncio.sleep(0.5)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(project_client, sid, has_kinds("drag"))
        drags = [s for s in steps if s["type"] == "drag"]
        assert drags, (
            "끌어다 놓기가 기록되지 않았다. "
            f"기록된 종류: {[s['type'] for s in steps]}"
        )
        step = drags[-1]
        assert step["target"]["test_id"]["value"] == "chip-events"
        assert step["drop_target"] is not None, "놓는 위치가 없는 drag Step 은 재실행할 수 없다"
    finally:
        stop_quietly(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_hover_menu_flow_replays(project_client: TestClient, fixture_app: str) -> None:
    """헌법 품질 게이트 2 — hover 로만 열리는 메뉴 흐름이 녹화 → 저장 → 재실행된다.

    hover Step 이 없으면 재실행에서 메뉴가 닫힌 상태이므로 `내보내기` 클릭이 실패한다.
    이 테스트가 통과하는 것이 hover Step 이 실제로 쓰인다는 증거다.
    """
    sid = _record_session(project_client, fixture_app)
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.hover("[data-testid=tools-menu]")
            await asyncio.sleep(HOVER_SETTLE_S)
            await p.click("[data-testid=tools-export]")
            await asyncio.sleep(0.4)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = wait_for_steps(project_client, sid, has_kinds("hover", "click"))
        kinds = [s["type"] for s in steps]
        assert "hover" in kinds, f"hover Step 이 없다: {kinds}"
        assert "click" in kinds, f"메뉴 항목 클릭이 없다: {kinds}"

        saved = project_client.post(
            f"/api/sessions/{sid}/save", json={"name": "도구 내보내기"}
        )
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
    finally:
        stop_quietly(project_client, sid)

    view = replay(project_client, test_id)
    assert view["state"] == "completed", (
        f"hover 메뉴 흐름 재실행이 실패했다: {view['state']}"
    )
    result = result_of(project_client, test_id)
    assert result["outcome"] == "pass"
    assert all(s["outcome"] == "pass" for s in result["steps"]), (
        f"실패한 Step: {[(s['step_id'], s['error_message']) for s in result['steps']]}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_drag_flow_replays(project_client: TestClient, fixture_app: str) -> None:
    """끌어다 놓기가 재실행에서 같은 결과를 만든다 (헌법 품질 게이트 2)."""
    sid = _record_session(project_client, fixture_app)
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.drag_and_drop("[data-testid=chip-events]", "#archive")
            await asyncio.sleep(0.5)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(project_client, sid, has_kinds("drag"))
        assert any(s["type"] == "drag" for s in steps), (
            f"끌어다 놓기가 기록되지 않았다. 기록된 종류: {[s['type'] for s in steps]}"
        )

        saved = project_client.post(
            f"/api/sessions/{sid}/save", json={"name": "칩 보관"}
        )
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
    finally:
        stop_quietly(project_client, sid)

    view = replay(project_client, test_id)
    assert view["state"] == "completed", f"끌어다 놓기 재실행이 실패했다: {view['state']}"

    result = result_of(project_client, test_id)
    assert result["outcome"] == "pass"
    dragged = [s for s in result["steps"] if s["label"].endswith("끌어다 놓기")]
    assert dragged, f"drag Step 결과가 없다: {[s['label'] for s in result['steps']]}"
    assert dragged[0]["locator_attempts"], (
        "끌어다 놓기의 시도 내역이 비어 있다 — 두 요소를 모두 해석했다는 근거가 없다"
    )


@pytest.mark.usefixtures("fixture_app")
def test_hover_then_click_on_the_same_element_is_one_step(
    project_client: TestClient, fixture_app: str
) -> None:
    """같은 요소의 `hover → click` 은 Step **하나**다.

    `click()` 은 그 자체가 포인터를 옮기고 누르고 떼는 동작이다. 앞에 hover Step 을 따로
    두면 같은 이동을 두 번 표현하는 것이고, 정의를 읽는 사람은 그 hover 에 별도의 뜻이
    있다고 오해한다. 실측(TC-010)에서 37 Step 중 6쌍이 이 형태였다.

    **위의 `test_hover_menu_flow_replays` 와 함께 읽어야 한다.** 그쪽은 hover 대상과 클릭
    대상이 **다른** 경우이며 hover 가 반드시 남아야 한다. 접는 기준은 "클릭이 뒤따랐는가"
    가 아니라 **"같은 요소를 클릭했는가"** 다.
    """
    sid = _record_session(project_client, fixture_app)
    try:
        page = project_client.app.state.itb.sessions.require(sid).tabs[0].page

        async def act(p: Any = page) -> None:
            await p.hover("[data-testid=tools-menu]")
            await asyncio.sleep(HOVER_SETTLE_S)  # hover Step 이 만들어질 시간을 준다
            await p.click("[data-testid=tools-menu]")
            await asyncio.sleep(0.4)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        steps = wait_for_steps(project_client, sid, has_kinds("click"))
    finally:
        stop_quietly(project_client, sid)

    mine = [
        s
        for s in steps
        if ((s.get("target") or {}).get("test_id") or {}).get("value") == "tools-menu"
    ]
    assert [s["type"] for s in mine] == ["click"], (
        "같은 요소의 hover 와 click 이 Step 두 개로 남았다: "
        f"{[(s['id'], s['type'], s['label']) for s in mine]}"
    )
