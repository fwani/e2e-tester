"""새로고침 뒤에도 진행 중 세션을 되찾을 수 있다 (UX U-05).

워크스루에서 겪은 것: 녹화 도중 화면을 새로 고치면 아무 확인 없이 테스트 목록으로 떨어졌다.
서버에는 ``recording`` · Step 5개 · ``has_unsaved_changes`` 세션이 그대로 살아 있고 실제
브라우저 창도 떠 있는데, 화면 어디에도 그 세션으로 돌아가는 길이 없었고 세션 id 를 알아낼
방법도 없었다. 그 상태로 새 녹화를 시작하면 두 번째 창이 열리고 앞의 5개는 영원히 못 찾는다.

여기서 보는 것은 서버 쪽 — 살아 있는 세션을 **목록으로 돌려주는가**. 화면 쪽 배너는
`TestList` 가 맡는다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_live_sessions_are_listed_and_discardable(
    project_client: TestClient, fixture_app: str
) -> None:
    assert project_client.get("/api/sessions").json() == {"sessions": []}

    created = project_client.post(
        "/api/sessions", json={"mode": "record", "start_url": f"{fixture_app}/login.html"}
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["session_id"]

    listed = project_client.get("/api/sessions").json()["sessions"]
    assert [s["session_id"] for s in listed] == [session_id], (
        "살아 있는 세션이 목록에 없다 — 새로고침한 사용자는 이 세션을 영영 못 찾는다"
    )
    # 화면이 배너를 그리는 데 필요한 것들이 그대로 실려 있다.
    assert listed[0]["state"] == "recording"
    assert "state_label" in listed[0]
    assert "steps" in listed[0]

    assert project_client.post(f"/api/sessions/{session_id}/discard").status_code == 204
    assert project_client.get("/api/sessions").json() == {"sessions": []}
