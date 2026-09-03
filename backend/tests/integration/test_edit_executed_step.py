"""이미 실행된 Step 편집. FR-040a~d (T093).

계약은 **요청이 성공하고 경고가 실려 온다** 는 것이다. 거절하지 않는 이유는 디자인의
대표 흐름(`RunnerPaused.dc.html`)이 실행이 끝난 Step 을 지우는 것이기 때문이다.

여기서 확인하는 것은 "무엇이 일어나지 **않는가**" 다 — 브라우저가 되돌아가지 않는다.
되돌리는 코드가 있으면 이 테스트가 잡는다.
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


def test_deleting_executed_step_warns_and_keeps_screen(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-040a·FR-040b — 정의만 바뀌고 화면은 그대로, 경고가 실려 온다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        url_before = current_url(keyed_client, sid)
        executed_step_id = view["steps"][0]["id"]

        resp = keyed_client.delete(f"/api/sessions/{sid}/steps/{executed_step_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["edit_warnings"], "이미 실행된 Step 을 지웠는데 경고가 없다 (FR-040b)"
        assert "적용되지 않았습니다" in body["edit_warnings"][0]
        assert all(s["id"] != executed_step_id for s in body["steps"])

        # ★ 브라우저는 그대로다. 되돌리는 코드가 있으면 여기서 잡힌다.
        assert current_url(keyed_client, sid) == url_before

        # 경고는 이벤트로도 나간다 (contracts/websocket.md `edit_warning`).
        assert any(kind == "edit_warning" for kind, _ in event_log)
    finally:
        stop_quietly(keyed_client, sid)


def test_editing_executed_step_label_warns(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-035·FR-040b — 수정도 같은 계약이다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        step_id = view["steps"][0]["id"]

        resp = keyed_client.patch(
            f"/api/sessions/{sid}/steps/{step_id}",
            json={"label": "이름을 바꿨다", "timeout_ms": 7000},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["edit_warnings"]
        updated = next(s for s in body["steps"] if s["id"] == step_id)
        assert updated["label"] == "이름을 바꿨다"
        assert updated["timeout_ms"] == 7000
    finally:
        stop_quietly(keyed_client, sid)


def test_editing_future_step_does_not_warn(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """아직 실행되지 않은 Step 편집에는 경고가 없다.

    모든 편집에 경고를 달면 경고가 의미를 잃는다 — 사용자는 그때부터 읽지 않는다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        future = view["steps"][-1]
        assert view["current_step_index"] <= len(view["steps"]) - 1

        resp = keyed_client.patch(
            f"/api/sessions/{sid}/steps/{future['id']}", json={"label": "나중 Step"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["edit_warnings"] == []
    finally:
        stop_quietly(keyed_client, sid)


def test_resume_after_deleting_executed_step_continues_from_current_state(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-040c — 이어서 실행은 브라우저의 **실제 현재 상태**를 기준으로 진행한다.

    지워진 Step 은 다시 돌지 않고, 이미 지난 Step 도 다시 돌지 않는다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        removed = view["steps"][0]["id"]
        keyed_client.delete(f"/api/sessions/{sid}/steps/{removed}")
        before = started_ids(event_log)

        resumed = keyed_client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code == 200, resumed.text
        wait_until_terminal(keyed_client, sid)

        after = started_ids(event_log)
        assert after.count(removed) == before.count(removed), (
            "삭제한 Step 이 이어서 실행에서 다시 돌았다"
        )
        for step_id in before:
            assert after.count(step_id) == 1, f"{step_id} 이 두 번 실행됐다: {after}"
    finally:
        stop_quietly(keyed_client, sid)


def test_reorder_moving_executed_region_warns(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-040b — 이미 실행된 구간의 순서가 달라지면 경고한다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        view = pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        ids = [s["id"] for s in view["steps"]]
        assert view["current_step_index"] >= 2, view["current_step_index"]

        swapped = [ids[1], ids[0], *ids[2:]]
        resp = keyed_client.post(
            f"/api/sessions/{sid}/steps:reorder", json={"order": swapped}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["edit_warnings"], "실행된 구간을 바꿨는데 경고가 없다"
        assert [s["id"] for s in resp.json()["steps"]] == swapped
    finally:
        stop_quietly(keyed_client, sid)
