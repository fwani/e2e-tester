"""다시 집기. FR-020 (T135).

깨진 Step 의 대상 요소를 다시 지정하면 후보를 새로 수집·검증해 그 Step 이 다시 통과한다.

**두 경로를 모두 본다.**

1. 셀렉터를 주는 경로 — 즉시 갱신한다
2. 대기 경로 — 브라우저에서 클릭할 때까지 기다리고, **그 클릭은 Step 이 되지 않는다**

2번이 이 기능의 본래 모습이다 (사용자는 셀렉터를 쓰지 않는다). 그 클릭이 Step 으로도
기록되면 정의에 없던 클릭이 하나 늘어난다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from us2_support import (
    break_first_click,
    click_like_a_person,
    replay,
    result_of,
    start_replay,
    stop_quietly,
)
from us3_support import pause_after, record_login_then_two_menus


def _pause_at_start(
    client: TestClient, test_id: str, events: list[tuple[str, dict]]
) -> tuple[str, dict]:
    """첫 Step 이 끝난 직후 멈춘다 — 편집 대상이 남아 있는 지점이다."""
    sid = start_replay(client, test_id)
    view = pause_after(client, sid, finished_steps=1, events=events)
    return sid, view


def test_repick_by_selector_refreshes_candidates(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-020 — 대상을 다시 지정하면 후보가 새로 수집·검증된다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    broken_index = break_first_click(keyed_client, test_id)

    sid, view = _pause_at_start(keyed_client, test_id, event_log)
    try:
        step = view["steps"][broken_index]
        assert step["type"] == "click"
        # 깨뜨린 정의에는 쓸 수 있는 후보가 없다.
        assert step["target"]["css"]["value"].startswith("존재하지-않는")

        resp = keyed_client.post(
            f"/api/sessions/{sid}/steps/{step['id']}/repick",
            json={"selector": "[data-testid=login-submit]"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["waiting"] is False
        updated = next(s for s in body["steps"] if s["id"] == step["id"])
        assert updated["target"]["test_id"]["value"] == "login-submit"
        assert updated["target"]["test_id"]["status"] == "verified"
    finally:
        stop_quietly(keyed_client, sid)


def test_repicked_step_passes_on_replay(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """**이 테스트가 FR-020 의 요점이다** — 다시 집은 뒤 실행이 다시 통과한다."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    broken_index = break_first_click(keyed_client, test_id)

    # 깨진 정의는 실패한다 (전제 확인).
    failed = replay(keyed_client, test_id)
    assert failed["state"] == "failed", failed
    assert result_of(keyed_client, test_id)["failed_step_index"] == broken_index

    sid, view = _pause_at_start(keyed_client, test_id, event_log)
    try:
        step_id = view["steps"][broken_index]["id"]
        resp = keyed_client.post(
            f"/api/sessions/{sid}/steps/{step_id}/repick",
            json={"selector": "[data-testid=login-submit]"},
        )
        assert resp.status_code == 200, resp.text
        saved = keyed_client.post(
            f"/api/sessions/{sid}/save", json={"name": "다시 집은 테스트"}
        )
        assert saved.status_code == 200, saved.text
    finally:
        stop_quietly(keyed_client, sid)

    view = replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    assert view["state"] == "completed", [
        (s["label"], s["outcome"], s["error_message"]) for s in result["steps"]
    ]
    assert result["outcome"] == "pass"


def test_repick_waits_for_a_browser_click_and_records_no_step(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-020 — 대기 경로. **그 클릭은 Step 이 되지 않는다.**"""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    broken_index = break_first_click(keyed_client, test_id)

    sid, view = _pause_at_start(keyed_client, test_id, event_log)
    try:
        step_id = view["steps"][broken_index]["id"]
        before = len(view["steps"])

        armed = keyed_client.post(
            f"/api/sessions/{sid}/steps/{step_id}/repick", json={"slot": "target"}
        )
        assert armed.status_code == 200, armed.text
        assert armed.json()["waiting"] is True
        assert "클릭하세요" in armed.json()["message"]

        session = keyed_client.app.state.itb.sessions.require(sid)
        page = session.tabs[session.active_tab_index].page

        async def act(p: Any = page) -> None:
            await click_like_a_person(p, "[data-testid=login-submit]")
            await asyncio.sleep(0.6)

        keyed_client.portal.call(act)  # type: ignore[attr-defined]

        after = keyed_client.get(f"/api/sessions/{sid}").json()
        assert len(after["steps"]) == before, (
            "다시 집기용 클릭이 Step 으로 기록됐다 — 정의에 없던 클릭이 늘어난다"
        )
        updated = next(s for s in after["steps"] if s["id"] == step_id)
        assert updated["target"]["test_id"]["value"] == "login-submit", (
            f"후보가 갱신되지 않았다: {updated['target']}"
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_repick_requires_paused_state(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """FR-035a 와 같은 게이트."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        steps = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        resp = keyed_client.post(
            f"/api/sessions/{sid}/steps/{steps[0]['id']}/repick", json={}
        )
        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "NOT_PAUSED"
    finally:
        stop_quietly(keyed_client, sid)


def test_repick_rejects_a_slot_the_step_does_not_have(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """T166 — `drag` 가 아닌 Step 에 `drop_target` 을 요구하면 거절한다.

    조용히 무시하면 사용자는 갱신됐다고 오해한다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid, view = _pause_at_start(keyed_client, test_id, event_log)
    try:
        click_step = next(s for s in view["steps"] if s["type"] == "click")
        resp = keyed_client.post(
            f"/api/sessions/{sid}/steps/{click_step['id']}/repick",
            json={"slot": "drop_target"},
        )
        assert resp.status_code == 400, resp.text
        assert "drop_target" in resp.json()["error"]["message"]
    finally:
        stop_quietly(keyed_client, sid)


def test_repick_reports_when_the_element_is_not_found(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """대상을 찾지 못하면 **갱신하지 않고** 사유를 알린다.

    조용히 빈 후보로 덮으면 Step 이 더 나빠진다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid, view = _pause_at_start(keyed_client, test_id, event_log)
    try:
        step = next(s for s in view["steps"] if s["type"] == "click")
        before = step["target"]
        resp = keyed_client.post(
            f"/api/sessions/{sid}/steps/{step['id']}/repick",
            json={"selector": "#이-요소는-없다"},
        )
        assert resp.status_code == 400, resp.text

        after = keyed_client.get(f"/api/sessions/{sid}").json()
        unchanged = next(s for s in after["steps"] if s["id"] == step["id"])
        assert unchanged["target"] == before, "찾지 못했는데 후보를 덮어썼다"
    finally:
        stop_quietly(keyed_client, sid)


def test_definition_file_reflects_the_repick(
    keyed_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    """갱신 결과가 사용자 자산(정의 파일)에 남는다 (FR-088b)."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    break_first_click(keyed_client, test_id)

    sid, view = _pause_at_start(keyed_client, test_id, event_log)
    try:
        step = next(s for s in view["steps"] if s["type"] == "click")
        keyed_client.post(
            f"/api/sessions/{sid}/steps/{step['id']}/repick",
            json={"selector": "[data-testid=login-submit]"},
        )
        keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "다시 집기 반영"})
    finally:
        stop_quietly(keyed_client, sid)

    repo = keyed_client.app.state.itb.repository
    path = repo.find_test_path(test_id)
    assert path is not None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    target = next(s for s in raw["steps"] if s["type"] == "click")["target"]
    assert target["test_id"]["value"] == "login-submit"


@pytest.mark.usefixtures("fixture_app")
def test_display_states_are_not_persisted(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-019a — 표시 상태는 파일에 저장되지 않는다.

    저장하면 다시 집은 뒤에도 옛 표기가 남는다.
    """
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    repo = keyed_client.app.state.itb.repository
    text = repo.find_test_path(test_id).read_text(encoding="utf-8")
    for token in ("사용 중", "대체", "최후", "모호"):
        assert token not in text, f"표시 상태가 정의 파일에 저장됐다: {token}"
