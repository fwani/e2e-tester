"""AI 실패가 조용히 지나가지 않는다. DR-016·DR-020 · 001 FR-067.

사용자가 겪은 것은 "AI로 만들기를 눌러도 아무 일도 일어나지 않는다" 였다. 서버 쪽에서
확인할 것은 두 가지다.

1. 실패하면 **`ai_error` 이벤트를 발행한다** — 조용히 끝나지 않는다.
2. **세션을 닫지 않는다** — 그때까지의 Step 과 브라우저가 남아 사용자가 이어갈 수 있다.

화면 쪽(그 이벤트가 실제로 그려지는가)은 `frontend/tests/AiRecord.test.tsx` 가 본다.
001 의 결함은 서버가 아니라 거기 있었다.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from tests.conftest import pin_playwright_browsers

CREDENTIAL_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """자격 증명을 지운다. 사용자가 겪은 상황을 그대로 만든다.

    `HOME` 을 비우는 이유는 SDK 가 사용자 홈의 로그인 프로필로 넘어가지 않게 하려는
    것이다. 그러면 Playwright 도 브라우저를 못 찾으므로 캐시 위치를 먼저 고정한다.
    """
    pin_playwright_browsers(monkeypatch)
    for name in CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", "/nonexistent-home-for-this-test")


@pytest.mark.usefixtures("fixture_app", "no_credentials")
def test_ai_failure_emits_an_error_and_keeps_the_session(
    project_client: TestClient, fixture_app: str, event_log: list[tuple[str, dict]]
) -> None:
    resp = project_client.post(
        "/api/sessions",
        json={
            "mode": "ai",
            "start_url": f"{fixture_app}/login.html",
            "ai_instruction": "로그인한 다음 프로젝트를 만들어",
        },
    )
    assert resp.status_code == 201, resp.text
    sid = resp.json()["session_id"]

    # 에이전트는 요청 수명과 분리돼 돌므로 결과를 기다린다.
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if any(kind == "ai_error" for kind, _ in event_log):
            break
        time.sleep(0.2)

    errors = [payload for kind, payload in event_log if kind == "ai_error"]
    assert errors, f"실패했는데 ai_error 가 없다. 받은 이벤트: {[k for k, _ in event_log]}"
    assert errors[0].get("reason"), "실패 사유가 비어 있으면 사용자가 조치할 수 없다"

    # **세션이 살아 있어야 한다** (FR-067). 닫아 버리면 그때까지의 Step 도 사라진다.
    view = project_client.get(f"/api/sessions/{sid}")
    assert view.status_code == 200, view.text
    assert view.json()["state"] != "stopped"

    project_client.post(f"/api/sessions/{sid}/discard")


@pytest.mark.usefixtures("fixture_app", "no_credentials")
def test_ai_session_reports_its_authoring_mode(
    project_client: TestClient, fixture_app: str
) -> None:
    """DR-020 의 근거 — 화면이 AI 세션임을 상태가 아니라 이것으로 판정한다.

    001 은 `state` 로 판정해, 실패로 `paused` 가 되는 순간 AI 화면과 실패 사유가
    통째로 사라졌다 (research R2).
    """
    resp = project_client.post(
        "/api/sessions",
        json={
            "mode": "ai",
            "start_url": f"{fixture_app}/login.html",
            "ai_instruction": "로그인해",
        },
    )
    sid = resp.json()["session_id"]

    assert resp.json()["authoring_mode"] == "ai"

    # 상태가 어떻게 바뀌든 authoring_mode 는 그대로다.
    view = project_client.get(f"/api/sessions/{sid}").json()
    assert view["authoring_mode"] == "ai"

    project_client.post(f"/api/sessions/{sid}/discard")


@pytest.mark.usefixtures("fixture_app")
def test_record_session_reports_record_mode(
    project_client: TestClient, fixture_app: str
) -> None:
    resp = project_client.post(
        "/api/sessions", json={"mode": "record", "start_url": f"{fixture_app}/login.html"}
    )

    assert resp.json()["authoring_mode"] == "record"
    project_client.post(f"/api/sessions/{resp.json()['session_id']}/discard")


@pytest.mark.usefixtures("fixture_app")
def test_empty_instruction_is_rejected_at_the_boundary(
    project_client: TestClient, fixture_app: str
) -> None:
    """001 FR-085 — 빈 지시문으로 세션이 시작되면 사용자는 왜 안 되는지 모른다."""
    resp = project_client.post(
        "/api/sessions",
        json={"mode": "ai", "start_url": f"{fixture_app}/login.html", "ai_instruction": "   "},
    )

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["message"], "거절 사유가 비어 있다"
