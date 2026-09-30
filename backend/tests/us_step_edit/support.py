"""026 Step 수정 통합 검사 공용 도구.

016 의 `us_rerecord.support` 를 **그대로 쓴다.** 새로 필요한 것은 「수정 세션을 연다」
하나뿐이다 — 대화·상태 대기·목록 조회는 016 과 같은 일이고, 같은 일을 두 번 구현하면
한쪽이 낡는다.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.us_rerecord.support import wait_for_state


def open_step_edit(
    client: TestClient, test_id: str, step_id: str | None, expect: int = 201
) -> str | dict[str, Any]:
    """Step 수정 세션을 연다. 실패를 기대하면 응답 본문을 돌려준다."""
    body: dict[str, Any] = {"mode": "step_edit", "test_id": test_id}
    if step_id is not None:
        body["step_edit_step_id"] = step_id
    resp = client.post("/api/sessions", json=body)
    assert resp.status_code == expect, resp.text
    if expect != 201:
        return dict(resp.json())
    sid = str(resp.json()["session_id"])
    wait_for_state(client, sid, {"paused"})
    return sid


def step_edit_of(client: TestClient, sid: str) -> dict[str, Any] | None:
    view = client.get(f"/api/sessions/{sid}").json().get("step_edit")
    return None if view is None else dict(view)


def snapshot(client: TestClient, sid: str) -> list[tuple[str, str]]:
    """id 와 내용을 함께 본다. id 만 비교하면 내용이 바뀐 것을 놓친다."""
    steps = client.get(f"/api/sessions/{sid}").json()["steps"]
    return [(s["id"], repr(sorted(s.items()))) for s in steps]
