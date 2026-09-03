"""T051 — 멀티 탭 녹화 통합 테스트 (FR-030a~c·FR-030g).

`add_init_script` 와 `expose_binding` 을 컨텍스트 단위로 등록했기 때문에 새 탭에 리코더가
자동 주입된다. 이 테스트가 그 사실을 보증한다 (research R2).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _record_session(client: TestClient, fixture_app: str) -> dict[str, Any]:
    resp = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _steps(client: TestClient, sid: str) -> list[dict[str, Any]]:
    return client.get(f"/api/sessions/{sid}").json()["steps"]


async def _login(page: Any) -> None:
    await page.fill("#email", "tester@example.com")
    await page.fill("#password", "pw-not-a-real-secret")
    await page.click("[data-testid=login-submit]")
    await page.wait_for_url("**/projects.html")
    await asyncio.sleep(0.4)


@pytest.mark.usefixtures("fixture_app")
def test_new_tab_actions_are_recorded_with_tab_reference(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-030a — 새 탭 조작도 기록되고 각 Step 에 탭 참조가 남는다."""
    sid = _record_session(project_client, fixture_app)["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await _login(page)
            # target="_blank" 링크 → 새 탭
            await page.click("[data-testid=terms-link]")
            await asyncio.sleep(0.8)
            tab1 = session.tabs[1].page
            await tab1.wait_for_load_state()
            await tab1.click("[data-testid=close-terms]")
            await asyncio.sleep(0.6)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = _steps(project_client, sid)
        tabs_used = {s["tab"] for s in steps}
        assert 0 in tabs_used, f"최초 탭 Step 이 없다: {steps}"
        assert 1 in tabs_used, f"새 탭 Step 이 없다. 탭 참조: {tabs_used}"

        # 새 탭에서 일어난 클릭이 tab=1 로 기록됐는지
        tab1_steps = [s for s in steps if s["tab"] == 1]
        assert tab1_steps, "새 탭에서 기록된 Step 이 없다 — 리코더가 자동 주입되지 않았다"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_window_open_popup_is_also_tracked(
    project_client: TestClient, fixture_app: str
) -> None:
    """T005 실측 — window.open 경로도 context.on("page") 로 잡힌다."""
    sid = _record_session(project_client, fixture_app)["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await _login(page)
            await page.click("#terms-popup")
            await asyncio.sleep(0.8)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        tabs = project_client.get(f"/api/sessions/{sid}/tabs").json()
        assert len(tabs["tabs"]) >= 2, f"팝업이 탭으로 등록되지 않았다: {tabs}"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_tab_index_is_not_reused_after_close(
    project_client: TestClient, fixture_app: str
) -> None:
    """data-model §8 불변식 — 번호를 재사용하면 저장된 Step 의 탭 참조가 어긋난다."""
    sid = _record_session(project_client, fixture_app)["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await _login(page)
            await page.click("[data-testid=terms-link]")
            await asyncio.sleep(0.7)
            await session.tabs[1].page.close()
            await asyncio.sleep(0.4)
            await page.click("#terms-popup")
            await asyncio.sleep(0.7)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        tabs = project_client.get(f"/api/sessions/{sid}/tabs").json()["tabs"]
        indexes = [t["tab_index"] for t in tabs]
        assert len(indexes) == len(set(indexes)), f"탭 번호가 재사용됐다: {indexes}"
        assert indexes == sorted(indexes)
        assert max(indexes) >= 2, f"닫은 뒤 새 탭이 이전 번호를 재사용했다: {indexes}"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_mirror_tab_can_be_switched(
    project_client: TestClient, fixture_app: str
) -> None:
    """FR-030f·FR-047c — 미러 표시 탭을 사용자가 고를 수 있다."""
    sid = _record_session(project_client, fixture_app)["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await _login(page)
            await page.click("[data-testid=terms-link]")
            await asyncio.sleep(0.8)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        resp = project_client.post(f"/api/sessions/{sid}/mirror-tab", json={"tab_index": 1})
        assert resp.status_code == 200, resp.text
        assert resp.json()["mirrored_tab_index"] == 1

        missing = project_client.post(
            f"/api/sessions/{sid}/mirror-tab", json={"tab_index": 99}
        )
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "TAB_NOT_FOUND"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_tab_limit_is_enforced(project_client: TestClient, fixture_app: str) -> None:
    """FR-030g — 상한을 넘으면 기록을 중단하고 알린다."""
    sid = _record_session(project_client, fixture_app)["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        session.max_tabs = 3  # 테스트를 빠르게 하려고 상한을 낮춘다

        async def act() -> None:
            for _ in range(5):
                await session.context.new_page()
                await asyncio.sleep(0.15)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        open_tabs = [t for t in session.tabs if not t.closed]
        assert len(open_tabs) <= session.max_tabs, (
            f"상한 {session.max_tabs} 을 넘겨 {len(open_tabs)}개가 등록됐다"
        )
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_closing_a_tab_records_a_close_tab_step(
    project_client: TestClient, fixture_app: str
) -> None:
    """T159·FR-030c — 탭을 닫으면 `close_tab` Step 이 기록된다.

    이벤트(`tab_closed`)만 나가고 Step 이 없으면, 사용자가 브라우저 UI 로 탭을 닫은
    동작은 재실행에서 재현되지 않는다. "팝업을 닫은 뒤 원래 탭 상태를 검증하는 흐름"이
    성립하려면 닫기가 정의에 남아야 한다.
    """
    sid = _record_session(project_client, fixture_app)["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await _login(page)
            await page.click("[data-testid=terms-link]")
            await asyncio.sleep(0.9)
            await session.tabs[1].page.close()  # 브라우저 UI 로 닫은 것과 같은 경로
            await asyncio.sleep(0.6)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = _steps(project_client, sid)
        closes = [s for s in steps if s["type"] == "close_tab"]
        assert closes, (
            "탭을 닫았는데 close_tab Step 이 없다 — FR-030c 위반. "
            f"기록된 종류: {[s['type'] for s in steps]}"
        )
        assert closes[-1]["tab"] == 1, f"닫은 탭 번호가 어긋났다: {closes[-1]}"
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")


@pytest.mark.usefixtures("fixture_app")
def test_new_tab_navigation_is_recorded(
    project_client: TestClient, fixture_app: str
) -> None:
    """T159 부수 — 새 탭의 화면 이동도 기록된다 (FR-024).

    새 탭에 네비게이션 감시가 붙지 않으면 그 탭의 이동이 Step 으로 남지 않는다.
    리코더가 세션의 새 탭 통보를 받아야 성립한다.
    """
    sid = _record_session(project_client, fixture_app)["session_id"]
    try:
        manager = project_client.app.state.itb.sessions
        session = manager.require(sid)
        page = session.tabs[0].page

        async def act() -> None:
            await _login(page)
            await page.click("[data-testid=terms-link]")
            await asyncio.sleep(0.9)
            tab1 = session.tabs[1].page
            await tab1.wait_for_load_state()
            # 새 탭 안에서 직접 주소를 옮긴다 — 클릭이 유발한 이동이 아니다.
            await tab1.goto(f"{fixture_app}/analysis.html")
            await asyncio.sleep(0.8)

        project_client.portal.call(act)  # type: ignore[attr-defined]

        steps = _steps(project_client, sid)
        tab1_navs = [
            s for s in steps if s["type"] == "navigate" and s["tab"] == 1
        ]
        assert tab1_navs, (
            "새 탭의 화면 이동이 기록되지 않았다 — 새 탭에 네비게이션 감시가 붙지 않았다. "
            f"기록된 (종류, 탭): {[(s['type'], s['tab']) for s in steps]}"
        )
    finally:
        project_client.post(f"/api/sessions/{sid}/stop")
