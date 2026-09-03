"""일시정지 → 이어서 실행. 헌법 원칙 III·FR-031~FR-038·SC-007 (T092).

**이 파일이 원칙 III 의 동적 증거다.** 확인하는 것은 세 가지다.

1. 일시정지가 브라우저 세션을 종료하지 않는다 (FR-032)
2. 화면 상태·인증 상태가 그대로 남는다 (FR-032)
3. 이어서 실행할 때 **사전 Step 이 재실행되지 않는다** (FR-038, SC-007)

3번이 핵심이다. 로그인이 다시 돌면 원칙 III 가 구현되지 않은 것이다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from us2_support import start_replay, stop_quietly
from us3_support import (
    current_url,
    pause_after,
    record_login_then_two_menus,
    started_ids,
    wait_until_terminal,
)


def test_pause_keeps_browser_session_and_screen(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-032 — 일시정지 시 세션이 살아 있고 화면이 그대로다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = pause_after(keyed_client, sid, finished_steps=3, events=event_log)

        session = keyed_client.app.state.itb.sessions.require(sid)
        assert session.open_tabs(), "일시정지에서 탭이 하나도 남지 않았다 — 불변식 1 위반"
        assert not session.context.pages[0].is_closed()
        # 로그인을 지난 뒤이므로 로그인 화면이 아니어야 한다 = 인증 상태가 유지된다.
        assert "login.html" not in current_url(keyed_client, sid)
        assert view["state"] == "paused"
        assert "edit_steps" in view["allowed_commands"]
    finally:
        stop_quietly(keyed_client, sid)


def test_resume_does_not_replay_preceding_steps(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """SC-007·FR-038 — 이어서 실행이 사전 Step 을 다시 돌리지 않는다.

    판정은 **Step id 기준**이다. 인덱스는 편집으로 밀리지만 id 는 그대로이므로, 같은
    Step 이 두 번 시작됐는지를 정확히 셀 수 있다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        before = started_ids(event_log)
        assert before, "일시정지 전에 실행된 Step 이 없다 — 시나리오가 성립하지 않는다"

        resumed = keyed_client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code == 200, resumed.text
        wait_until_terminal(keyed_client, sid)

        after = started_ids(event_log)
        for step_id in before:
            assert after.count(step_id) == 1, (
                f"{step_id} 이 이어서 실행에서 다시 돌았다 — 원칙 III 위반. "
                f"실행 순서: {after}"
            )
    finally:
        stop_quietly(keyed_client, sid)


def test_resume_reuses_the_same_browser(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-038 — 브라우저를 재시작하지 않는다.

    같은 `BrowserContext`·같은 `Page` 객체가 유지되는지 본다. 새 브라우저를 띄우면
    인증 상태가 사라지므로 SC-007 이 성립할 수 없다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        session = keyed_client.app.state.itb.sessions.require(sid)
        context_before = id(session.context)
        page_before = id(session.tabs[0].page)

        keyed_client.post(f"/api/sessions/{sid}/resume")
        wait_until_terminal(keyed_client, sid)

        session_after = keyed_client.app.state.itb.sessions.require(sid)
        assert id(session_after.context) == context_before
        assert id(session_after.tabs[0].page) == page_before
    finally:
        stop_quietly(keyed_client, sid)


def test_pause_is_rejected_when_not_pausable(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-043a — 정의되지 않은 명령은 현재 상태와 함께 거절한다.

    끝난 세션에 "계속하기" 를 보내면 거절되어야 한다. 조용히 성공으로 응답하면 사용자는
    이어서 도는 줄 알고 기다린다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        wait_until_terminal(keyed_client, sid)
        resp = keyed_client.post(f"/api/sessions/{sid}/resume")
        assert resp.status_code == 409, resp.text
        body = resp.json()["error"]
        assert body["code"] == "INVALID_TRANSITION"
        assert "지금 가능한 행동" in body["message"]
    finally:
        stop_quietly(keyed_client, sid)


def test_inline_recording_inserts_at_pause_position(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-036 — 직접 동작 추가는 일시정지 위치에 삽입된다.

    목록 끝에 붙으면 사용자가 보고 있는 화면과 정의의 순서가 어긋난다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        pause_index = view["current_step_index"]
        total_before = len(view["steps"])

        started = keyed_client.post(f"/api/sessions/{sid}/record-actions:start")
        assert started.status_code == 200, started.text
        assert started.json()["state"] == "recording"

        session = keyed_client.app.state.itb.sessions.require(sid)
        page = session.tabs[session.active_tab_index].page

        async def act(p: object = page) -> None:
            import asyncio

            from us2_support import click_like_a_person

            await click_like_a_person(p, "nav a[href='analysis.html']")
            await asyncio.sleep(0.6)

        keyed_client.portal.call(act)  # type: ignore[attr-defined]

        stopped = keyed_client.post(f"/api/sessions/{sid}/record-actions:stop")
        assert stopped.status_code == 200, stopped.text
        steps = stopped.json()["steps"]
        assert len(steps) > total_before, "직접 동작이 Step 으로 기록되지 않았다"

        inserted = steps[pause_index]
        assert inserted["author"] == "human"
        # 삽입된 Step 은 **이미 수행된** 동작이므로 실행 위치가 그 뒤로 옮겨져야 한다.
        assert stopped.json()["current_step_index"] > pause_index
    finally:
        stop_quietly(keyed_client, sid)
