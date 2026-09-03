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

        hovers = [s for s in _steps(project_client, sid) if s["type"] == "hover"]
        assert hovers, (
            "메뉴를 여는 hover 가 기록되지 않았다. "
            f"기록된 종류: {[s['type'] for s in _steps(project_client, sid)]}"
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

        drags = [s for s in _steps(project_client, sid) if s["type"] == "drag"]
        assert drags, (
            "끌어다 놓기가 기록되지 않았다. "
            f"기록된 종류: {[s['type'] for s in _steps(project_client, sid)]}"
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

        steps = _steps(project_client, sid)
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
        assert any(s["type"] == "drag" for s in _steps(project_client, sid))

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
