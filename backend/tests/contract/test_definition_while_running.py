"""006 T076~T078 — 실행 중인 테스트의 편집 계약 (US5).

`specs/006-edit-saved-test/contracts/rest-api.md` §1·§2 V3.

**브라우저를 띄우지 않는다.** 실행 중 상태는 005 가 만든 예약(`reserve_for_test`)을 직접
세워 만든다 — 판정 근거가 그 예약 하나이므로(research R9), 실제 브라우저 없이도 같은 경로를
지난다. 새 판정 기준을 만들지 않았다는 것이 이 테스트의 요점이다.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.domain.test_case import Test
from itb.secrets.keys import KeyPaths
from itb.storage.repository import ProjectRepository
from tests.conftest import pin_playwright_browsers

START_URL = "http://127.0.0.1:4300/login.html"
STEPS = [
    {"type": "navigate", "id": "step-01", "label": "이동", "url": START_URL},
    {
        "type": "fill",
        "id": "step-02",
        "label": "아이디",
        "target": {"tag": "input", "css": {"value": "#u", "status": "verified"}},
        "value": "admin",
    },
]


@pytest.fixture
def saved(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    pin_playwright_browsers(monkeypatch)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    with TestClient(create_app()) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        resp = c.post(
            "/api/project/create",
            json={"name": "실행 중 편집", "default_start_url": START_URL},
        )
        assert resp.status_code == 201, resp.text
        repo = ProjectRepository.open(
            pathlib.Path(c.get("/api/project").json()["root"])
        )
        repo.write_test(
            Test(
                id="TC-001",
                name="로그인",
                authoring_mode="record",
                start_url=START_URL,
                steps=STEPS,
            )
        )
        yield c


def _hold(client: TestClient, test_id: str = "TC-001") -> None:
    """005 의 예약으로 "실행 중" 을 만든다 (research R9)."""
    client.app.state.itb.sessions.reserve_for_test(test_id, "session-token")


def _release(client: TestClient, test_id: str = "TC-001") -> None:
    client.app.state.itb.sessions.release_reservation(test_id, "session-token")


def test_get_definition_is_readonly_while_running(saved: TestClient) -> None:
    """FR-206 — 화면은 열린다. 못 열게 하면 무엇이 실행 중인지도 볼 수 없다."""
    _hold(saved)
    resp = saved.get("/api/tests/TC-001/definition")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["editable"] is False
    assert body["blocked_by"] == "running"
    assert body["blocking_session_id"] == "session-token"
    # 정의 자체는 그대로 보인다.
    assert len(body["test"]["steps"]) == 2


def test_save_is_rejected_while_running(saved: TestClient) -> None:
    """FR-207 — 실행 중인 정의를 밑에서 바꾸지 않는다."""
    revision = saved.get("/api/tests/TC-001/definition").json()["revision"]
    _hold(saved)
    resp = saved.put(
        "/api/tests/TC-001/definition",
        json={
            "revision": revision,
            "edits": [{"op": "update", "step_id": "step-02", "value": "x"}],
        },
    )
    assert resp.status_code == 409
    err = resp.json()["error"]
    assert err["code"] == "SESSION_ALREADY_ACTIVE"
    assert err["detail"]["session_id"] == "session-token"


def test_rejection_message_hides_the_session_identifier(saved: TestClient) -> None:
    """005 FR-135 — 사용자에게 보이는 문장에 세션 식별자를 넣지 않는다.

    `detail.session_id` 는 화면이 이동 버튼을 만들기 위한 것이다.
    """
    revision = saved.get("/api/tests/TC-001/definition").json()["revision"]
    _hold(saved)
    err = saved.put(
        "/api/tests/TC-001/definition",
        json={
            "revision": revision,
            "edits": [{"op": "update", "step_id": "step-02", "value": "x"}],
        },
    ).json()["error"]
    assert "session-token" not in err["message"]
    assert "session-token" not in err["next_action"]


def test_editing_works_again_after_the_run_ends(saved: TestClient) -> None:
    """US5 시나리오 3 — 끝난 뒤에는 정상적으로 열리고 저장된다."""
    _hold(saved)
    assert saved.get("/api/tests/TC-001/definition").json()["editable"] is False

    _release(saved)
    body = saved.get("/api/tests/TC-001/definition").json()
    assert body["editable"] is True
    assert body["blocking_session_id"] is None

    resp = saved.put(
        "/api/tests/TC-001/definition",
        json={
            "revision": body["revision"],
            "edits": [{"op": "update", "step_id": "step-02", "value": "operator"}],
        },
    )
    assert resp.status_code == 200, resp.text
