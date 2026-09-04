"""중지한 뒤에도 기록을 저장할 수 있다. DR-010·DR-012·DR-013·DR-014·DR-015.

**이 라운드의 핵심 회귀 테스트다.** 사용자가 겪은 것은 이랬다 — 직접 녹화로 조작을
기록한 뒤 중지를 누르면 화면이 목록으로 튕겨 나가고, 기록한 Step 을 보지도 저장하지도
못했다. 녹화가 통째로 사라졌다.

원인은 두 겹이었다 (research R1).

1. 화면이 중지 직후 `onFinished()` 로 목록으로 갔다.
2. **서버가 `stop` 에서 `_WORK.pop()` 까지 해 세션을 파괴했다.** 그래서 화면을 붙잡아
   두더라도 저장이 `SESSION_NOT_FOUND` 로 실패했다.

여기서 보는 것은 2번이다. 1번은 `SessionScreen` 이 맡는다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _record_session(client: TestClient, fixture_app: str) -> str:
    resp = client.post(
        "/api/sessions", json={"mode": "record", "start_url": f"{fixture_app}/login.html"}
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["session_id"])


def _capture_a_few_steps(client: TestClient, session_id: str) -> None:
    manager = client.app.state.itb.sessions  # type: ignore[attr-defined]
    session = manager.require(session_id)
    page = session.tabs[0].page

    async def act() -> None:
        await page.fill("#email", "tester@example.com")
        await page.click("#password")
        await page.click("[data-testid=login-submit]")
        await asyncio.sleep(0.6)

    client.portal.call(act)  # type: ignore[attr-defined]


def _view(client: TestClient, session_id: str) -> dict[str, Any]:
    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


@pytest.mark.usefixtures("fixture_app")
def test_stop_keeps_the_recording_and_save_succeeds(
    project_client: TestClient, fixture_app: str
) -> None:
    """**중지 → 저장이 성공한다.** 시작 시점에는 SESSION_NOT_FOUND 로 실패했다."""
    sid = _record_session(project_client, fixture_app)
    _capture_a_few_steps(project_client, sid)

    before = _view(project_client, sid)["steps"]
    assert len(before) > 0, "기록된 Step 이 없어 이 테스트가 의미를 갖지 못한다"

    stopped = project_client.post(f"/api/sessions/{sid}/stop")
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["state"] == "review", "중지가 세션을 종료 상태로 보냈다"

    # 세션이 살아 있어야 한다 — 이것이 이 라운드의 수정이다.
    after = _view(project_client, sid)
    assert [s["id"] for s in after["steps"]] == [s["id"] for s in before]

    saved = project_client.post(f"/api/sessions/{sid}/save", json={"name": "중지 후 저장"})
    assert saved.status_code == 200, saved.text
    assert saved.json()["name"] == "중지 후 저장"

    listing = project_client.get("/api/tests").json()
    assert "중지 후 저장" in [t["name"] for t in listing["tests"]]


@pytest.mark.usefixtures("fixture_app")
def test_steps_can_be_edited_after_stop(project_client: TestClient, fixture_app: str) -> None:
    """DR-012 — 검토 중에도 고칠 수 있다.

    그러지 못하면 잘못 기록된 Step 하나 때문에 녹화 전체를 버려야 한다.
    """
    sid = _record_session(project_client, fixture_app)
    _capture_a_few_steps(project_client, sid)
    project_client.post(f"/api/sessions/{sid}/stop")

    steps = _view(project_client, sid)["steps"]
    assert len(steps) >= 2, f"삭제를 검증하려면 2개 이상 필요하다: {len(steps)}"

    victim = steps[0]["id"]
    removed = project_client.delete(f"/api/sessions/{sid}/steps/{victim}")
    assert removed.status_code == 200, removed.text

    remaining = [s["id"] for s in _view(project_client, sid)["steps"]]
    assert victim not in remaining


@pytest.mark.usefixtures("fixture_app")
def test_review_rejects_browser_commands(project_client: TestClient, fixture_app: str) -> None:
    """001 FR-043a — 브라우저가 없으므로 실행 계열 명령은 거절한다.

    거절이 조용하면 사용자는 눌렀는데 아무 일도 없는 것을 또 겪는다.
    """
    sid = _record_session(project_client, fixture_app)
    _capture_a_few_steps(project_client, sid)
    project_client.post(f"/api/sessions/{sid}/stop")

    for path, body in [
        (f"/api/sessions/{sid}/resume", None),
        (f"/api/sessions/{sid}/pause", None),
        (f"/api/sessions/{sid}/run-from", {"step_index": 0}),
    ]:
        resp = project_client.post(path, json=body)
        assert resp.status_code == 409, (path, resp.status_code, resp.text)
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"
        assert resp.json()["error"]["message"], "거절 사유가 비어 있다"


@pytest.mark.usefixtures("fixture_app")
def test_discard_destroys_the_session(project_client: TestClient, fixture_app: str) -> None:
    """DR-014 — 버리기에서 비로소 세션이 사라진다."""
    sid = _record_session(project_client, fixture_app)
    _capture_a_few_steps(project_client, sid)
    project_client.post(f"/api/sessions/{sid}/stop")

    dropped = project_client.post(f"/api/sessions/{sid}/discard")
    assert dropped.status_code == 204, dropped.text

    gone = project_client.get(f"/api/sessions/{sid}")
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "SESSION_NOT_FOUND"


@pytest.mark.usefixtures("fixture_app")
def test_unsaved_changes_flag_survives_stop(
    project_client: TestClient, fixture_app: str
) -> None:
    """DR-014 의 근거 — 화면이 유실 경고를 띄울지 판단하는 값이다."""
    sid = _record_session(project_client, fixture_app)
    _capture_a_few_steps(project_client, sid)

    stopped = project_client.post(f"/api/sessions/{sid}/stop").json()
    assert stopped["has_unsaved_changes"] is True

    project_client.post(f"/api/sessions/{sid}/save", json={"name": "저장했다"})
    assert _view(project_client, sid)["has_unsaved_changes"] is False


@pytest.mark.usefixtures("fixture_app")
def test_empty_recording_still_cannot_be_saved(
    project_client: TestClient, fixture_app: str
) -> None:
    """001 FR-029 — Step 0개는 저장할 수 없다. 검토 상태에서도 마찬가지다."""
    sid = _record_session(project_client, fixture_app)
    project_client.post(f"/api/sessions/{sid}/stop")

    resp = project_client.post(f"/api/sessions/{sid}/save", json={"name": "빈 것"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "STEP_LIST_EMPTY"
