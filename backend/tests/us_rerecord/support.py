"""016 구간 재녹화 통합 테스트 공용 도구.

기존 `us2_support`(녹화·재실행)와 `us4_support`(가짜 모델)를 **그대로 쓴다.** 016 이
새로 필요한 것은 「재녹화 세션을 열고 대화를 보내고 결말을 기다린다」뿐이다.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

SETTLED = frozenset({"paused", "ai_blocked", "review", "failed", "stopped", "lost"})


def open_rerecord(
    client: TestClient, test_id: str, step_ids: list[str], expect: int = 201
) -> str | dict[str, Any]:
    """재녹화 세션을 연다. 실패를 기대하면 응답 본문을 돌려준다."""
    resp = client.post(
        "/api/sessions",
        json={"mode": "rerecord", "test_id": test_id, "rerecord_step_ids": step_ids},
    )
    assert resp.status_code == expect, resp.text
    if expect != 201:
        return dict(resp.json())
    sid = str(resp.json()["session_id"])
    wait_for_state(client, sid, {"paused"})
    return sid


def wait_for_state(
    client: TestClient, sid: str, wanted: set[str], timeout_s: float = 90.0
) -> dict[str, Any]:
    """세션이 원하는 상태에 닿을 때까지 기다린다."""
    deadline = time.monotonic() + timeout_s
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = dict(client.get(f"/api/sessions/{sid}").json())
        if last["state"] in wanted:
            return last
        if last["state"] in SETTLED - wanted:
            pytest.fail(f"기대하지 않은 상태에 멈췄다: {last['state']} (기대: {wanted})")
        time.sleep(0.03)
    pytest.fail(f"상태 {wanted} 에 닿지 못했다 (마지막: {last.get('state')})")
    raise AssertionError  # pragma: no cover


def say(client: TestClient, sid: str, text: str, expect: int = 200) -> dict[str, Any]:
    """AI 에게 말을 걸고 **턴이 끝날 때까지** 기다린다."""
    resp = client.post(f"/api/sessions/{sid}/chat", json={"text": text})
    assert resp.status_code == expect, resp.text
    if expect != 200:
        return dict(resp.json())
    return wait_for_state(client, sid, {"paused", "ai_blocked"})


def turns(client: TestClient, sid: str) -> list[dict[str, Any]]:
    resp = client.get(f"/api/sessions/{sid}/chat")
    assert resp.status_code == 200, resp.text
    return list(resp.json()["turns"])


def step_ids(client: TestClient, sid: str) -> list[str]:
    return [s["id"] for s in client.get(f"/api/sessions/{sid}").json()["steps"]]


def saved_step_ids(client: TestClient, test_id: str) -> list[str]:
    return [s["id"] for s in client.get(f"/api/tests/{test_id}").json()["steps"]]
