"""대상 앱이 안 떠 있으면 **그렇다고 말한다** (UX U-04 · 003 AP-031).

워크스루에서 겪은 것: 대상 앱을 내린 채 녹화를 시작하면 화면 맨 위에 "예상하지 못한
오류가 발생했습니다. 서버 로그를 확인하세요." 만 떴다. 어느 주소인지, 무엇이 예상 밖이었는지
한 마디도 없었다. 서버 로그의 실제 원인은 `net::ERR_CONNECTION_REFUSED at http://…` 로
완전히 특정되는 상황이었다.

"대상 앱이 안 떠 있다" 는 이 도구에서 가장 흔한 첫 실패다. 단독 로컬 도구 사용자에게
"서버 로그를 확인하세요" 는 터미널로 나가라는 뜻이고, 대부분은 거기서 멈춘다.
"""

from __future__ import annotations

import socket

from fastapi.testclient import TestClient

from itb.domain.error import ErrorCode


def _closed_port() -> int:
    """아무도 듣지 않는 포트. 바인드해서 번호를 얻고 곧바로 닫는다."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_record_start_against_dead_target_names_the_target(project_client: TestClient) -> None:
    dead_url = f"http://127.0.0.1:{_closed_port()}/login.html"

    resp = project_client.post("/api/sessions", json={"mode": "record", "start_url": dead_url})

    assert resp.status_code == 400, f"대상 쪽 사정인데 {resp.status_code} 로 나갔다: {resp.text}"
    body = resp.json()["error"]
    assert body["code"] == ErrorCode.TARGET_UNREACHABLE.value, body
    assert body["category"] == "blocked", "대상 앱이 안 떠 있는 것을 제품이 깨진 것으로 보이게 했다"
    assert dead_url in body["message"], f"어느 주소가 안 열렸는지 말하지 않는다: {body['message']}"
    assert "ERR_CONNECTION_REFUSED" in body["message"], (
        f"결정적인 단서(ERR_CONNECTION_REFUSED)를 버렸다: {body['message']}"
    )
    assert body["next_action"].strip(), "다음 행동이 비어 있다 (EC-004)"
    assert body["detail"] == {"start_url": dead_url}


def test_failed_start_leaves_no_session_and_no_browser(project_client: TestClient) -> None:
    """실패한 세션의 창을 남기지 않는다.

    세션은 만들어지지 않았는데 창만 떠 있으면 사용자는 그것을 제품 상태로 읽는다 — 그리고
    그 창은 아무 데도 연결돼 있지 않다.
    """
    dead_url = f"http://127.0.0.1:{_closed_port()}/login.html"
    manager = project_client.app.state.itb.sessions  # type: ignore[attr-defined]
    before = len(manager.all_sessions())

    resp = project_client.post("/api/sessions", json={"mode": "record", "start_url": dead_url})

    assert resp.status_code == 400, resp.text
    assert len(manager.all_sessions()) == before, "실패한 세션이 목록에 남았다"
    health = project_client.get("/api/health").json()
    assert health["active_sessions"] == before
