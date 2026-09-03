"""US3 종단 테스트 — quickstart §5 의 13단계. 헌법 원칙 III.

절차를 그대로 따른다. **9단계가 이 기능 전체의 핵심 증거다** — 로그인이 다시 돌면 원칙
III 가 구현되지 않은 것이다.

한 함수에 13단계를 몰지 않고 흐름별로 나눴다. 한 곳에서 깨졌을 때 어느 단계가 깨졌는지
실패 메시지로 알 수 있어야 한다 — 13단계 한 덩어리는 "US3 가 깨졌다" 밖에 알려주지 않는다.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi.testclient import TestClient
from us2_support import (
    DEFAULT_EMAIL,
    click_like_a_person,
    replay,
    result_of,
    stop_quietly,
)
from us3_support import current_url, started_ids


def _record_login_and_wrong_menu(client: TestClient, fixture_app: str) -> str:
    """§5 1단계 — 로그인 → 프로젝트 메뉴 → **실수로** 데이터 메뉴."""
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    session = client.app.state.itb.sessions.require(sid)
    page = session.tabs[0].page

    async def act(p: Any = page) -> None:
        await p.fill("#email", DEFAULT_EMAIL)
        await asyncio.sleep(0.25)
        await p.fill("#password", "record-only-not-a-real-secret")
        await asyncio.sleep(0.25)
        await click_like_a_person(p, "[data-testid=login-submit]")
        await p.wait_for_url("**/projects.html")
        await asyncio.sleep(0.5)
        await click_like_a_person(p, "nav a[href='data.html']")
        await p.wait_for_url("**/data.html")
        await asyncio.sleep(0.5)

    client.portal.call(act)  # type: ignore[attr-defined]
    return sid


def test_quickstart_section5_pause_edit_resume(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """§5 1~10단계."""
    client = keyed_client
    sid = _record_login_and_wrong_menu(client, fixture_app)
    try:
        # 1단계 — Step 이 기록됐다
        view = client.get(f"/api/sessions/{sid}").json()
        assert len(view["steps"]) >= 3, [s["label"] for s in view["steps"]]

        # 2단계 — 일시정지. 브라우저 창이 닫히지 않는다
        paused = client.post(f"/api/sessions/{sid}/pause")
        assert paused.status_code == 200, paused.text
        assert paused.json()["state"] == "paused"
        session = client.app.state.itb.sessions.require(sid)
        assert session.open_tabs(), "일시정지에서 세션이 종료됐다 — 불변식 1 위반"

        # 3단계 — 데이터 화면 그대로. 로그인 상태 유지
        assert "data.html" in current_url(client, sid)

        # 4단계 — 이미 실행된 마지막 Step(데이터 메뉴) 삭제 → 경고
        steps = paused.json()["steps"]
        wrong = steps[-1]["id"]
        removed = client.delete(f"/api/sessions/{sid}/steps/{wrong}")
        assert removed.status_code == 200, removed.text
        assert removed.json()["edit_warnings"], "실행된 Step 삭제에 경고가 없다 (FR-040b)"
        assert all(s["id"] != wrong for s in removed.json()["steps"])

        # 5단계 — 브라우저는 되돌아가지 않았다
        assert "data.html" in current_url(client, sid)

        # 6단계 — 직접 동작 추가: 프로젝트 메뉴 → 생성 → 이름 입력 → 저장
        before_count = len(removed.json()["steps"])
        started = client.post(f"/api/sessions/{sid}/record-actions:start")
        assert started.status_code == 200, started.text
        page = session.tabs[session.active_tab_index].page

        async def add_actions(p: Any = page) -> None:
            await click_like_a_person(p, "nav a[href='projects.html']")
            await p.wait_for_url("**/projects.html")
            await asyncio.sleep(0.5)
            await click_like_a_person(p, "[data-testid=create-project]")
            await asyncio.sleep(0.4)
            await p.fill("#pname", "TEST")
            await asyncio.sleep(0.3)
            await click_like_a_person(p, "[data-testid=save-project]")
            await asyncio.sleep(0.6)

        client.portal.call(add_actions)  # type: ignore[attr-defined]
        stopped = client.post(f"/api/sessions/{sid}/record-actions:stop")
        assert stopped.status_code == 200, stopped.text
        assert len(stopped.json()["steps"]) > before_count, "직접 동작이 기록되지 않았다"

        # 7단계 — Assertion 추가 (요소 보임)
        added = client.post(
            f"/api/sessions/{sid}/assertions",
            json={
                "kind": "text",
                "target_selector": "#rows",
                "value": "TEST",
                "match": "contains",
            },
        )
        assert added.status_code == 200, added.text
        assertion_step = next(
            s for s in added.json()["steps"] if s["type"] == "assertion"
        )
        assert assertion_step["assertion"]["kind"] == "text"
        # 후보는 **제품이** 수집했다 (원칙 IV) — 클라이언트는 셀렉터만 줬다
        assert assertion_step["assertion"]["target"] is not None

        # 8단계 — 순서 변경 (아직 실행되지 않은 구간만 바꾼다)
        current = client.get(f"/api/sessions/{sid}").json()
        ids = [s["id"] for s in current["steps"]]
        pause_at = current["current_step_index"]
        if len(ids) - pause_at >= 2:
            order = [*ids[:pause_at], ids[pause_at + 1], ids[pause_at], *ids[pause_at + 2 :]]
            reordered = client.post(
                f"/api/sessions/{sid}/steps:reorder", json={"order": order}
            )
            assert reordered.status_code == 200, reordered.text
            assert [s["id"] for s in reordered.json()["steps"]] == order

        # 9단계 — ★ 계속하기. 로그인이 재실행되지 않는다 (SC-007)
        login_steps = [
            s["id"]
            for s in client.get(f"/api/sessions/{sid}").json()["steps"]
            if s["type"] == "fill" or "로그인" in s["label"]
        ]
        resumed = client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code == 200, resumed.text
        for step_id in login_steps:
            assert step_id not in started_ids(event_log), (
                f"이어서 실행이 로그인 Step({step_id})을 다시 돌렸다 — 원칙 III 위반"
            )

        # 10단계 — 저장 후 재실행이 처음부터 통과한다
        saved = client.post(
            f"/api/sessions/{sid}/save", json={"name": "일시정지 편집 흐름"}
        )
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
    finally:
        stop_quietly(client, sid)

    replay(client, test_id)
    result = result_of(client, test_id)
    assert result["outcome"] == "pass", [
        (s["label"], s["outcome"], s["error_message"]) for s in result["steps"]
    ]


def test_quickstart_section5_step11_all_four_assertion_kinds(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """§5 11단계 — 4종 검증을 각각 추가해 모두 동작한다 (FR-013a)."""
    client = keyed_client
    sid = _record_login_and_wrong_menu(client, fixture_app)
    try:
        client.post(f"/api/sessions/{sid}/pause")
        session = client.app.state.itb.sessions.require(sid)
        page = session.tabs[session.active_tab_index].page

        requests = [
            {"kind": "visible", "target_selector": "nav .brand"},
            {"kind": "hidden", "target_selector": "#존재하지-않는-요소"},
            {"kind": "text", "target_selector": "nav .brand", "value": "데이터 플랫폼"},
            {"kind": "url", "value": "data.html", "match": "contains"},
        ]
        for body in requests:
            resp = client.post(f"/api/sessions/{sid}/assertions", json=body)
            if body["kind"] == "hidden":
                # 처음부터 없는 요소는 후보를 수집할 수 없다 → Step 을 만들지 않고 알린다.
                # 재실행에서 반드시 실패할 Step 을 만들어 두는 것이 더 나쁘다.
                assert resp.status_code == 400, resp.text
                assert "찾지 못해" in resp.json()["error"]["message"]
                continue
            assert resp.status_code == 200, f"{body} → {resp.text}"

        kinds = {
            s["assertion"]["kind"]
            for s in client.get(f"/api/sessions/{sid}").json()["steps"]
            if s["type"] == "assertion"
        }
        assert kinds == {"visible", "text", "url"}, kinds

        # 12단계 — 존재했다가 사라진 요소에 대한 `hidden` 검증은 통과한다.
        async def open_and_close(p: Any = page) -> None:
            await p.goto(f"{fixture_app}/projects.html")
            await asyncio.sleep(0.4)
            await click_like_a_person(p, "[data-testid=create-project]")
            await asyncio.sleep(0.4)

        client.portal.call(open_and_close)  # type: ignore[attr-defined]
        resp = client.post(
            f"/api/sessions/{sid}/assertions",
            json={"kind": "hidden", "target_selector": "#create-modal"},
        )
        assert resp.status_code == 200, resp.text

        saved = client.post(f"/api/sessions/{sid}/save", json={"name": "4종 검증"})
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
    finally:
        stop_quietly(client, sid)

    replay(client, test_id)
    result = result_of(client, test_id)
    failures = [
        (s["label"], s["error_message"]) for s in result["steps"] if s["outcome"] == "fail"
    ]
    # `hidden` 검증 Step 은 모달이 닫힌 상태에서 통과해야 한다 (spec 엣지 케이스).
    assert all("사라짐" not in label for label, _ in failures), failures


def test_quickstart_section5_step13_session_loss_preserves_steps(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """§5 13단계 — 일시정지 중 창을 직접 닫으면 유실을 알리고 **Step 은 보존**한다 (FR-041)."""
    client = keyed_client
    sid = _record_login_and_wrong_menu(client, fixture_app)
    try:
        paused = client.post(f"/api/sessions/{sid}/pause")
        recorded = [s["id"] for s in paused.json()["steps"]]
        assert recorded

        session = client.app.state.itb.sessions.require(sid)

        async def close_everything(s: Any = session) -> None:
            for tab in list(s.open_tabs()):
                await tab.page.close()
            await asyncio.sleep(0.5)

        client.portal.call(close_everything)  # type: ignore[attr-defined]

        view = client.get(f"/api/sessions/{sid}").json()
        assert view["state"] == "lost", view["state"]
        assert [s["id"] for s in view["steps"]] == recorded, "유실이 Step 을 지웠다"
        # 유실 후에는 저장만 허용된다 (FR-041c)
        assert view["allowed_commands"] == ["save"]
        assert any(kind == "session_lost" for kind, _ in event_log)

        blocked = client.post(f"/api/sessions/{sid}/resume")
        assert blocked.status_code == 409, blocked.text
    finally:
        stop_quietly(client, sid)
