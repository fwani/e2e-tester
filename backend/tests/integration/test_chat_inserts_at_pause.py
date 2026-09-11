"""**대화가 만든 Step 은 일시정지 위치에 끼워진다** (016 FR-023a · 2026-09-11 사용자 보고).

## 보고된 것

> 「step n 부터 실행은 거의 쓰이지 않는다. ai 로 편집하거나 할때 브라우저가 스텝을 자동으로
> 실행해줘야한다. 넣고싶은 위치에 멈춰줘야하고.」

앞 절반은 이미 있다 — 「브라우저 열어 이 Step 앞에서 멈추기」(`pause_before_index`)가 그
앞까지 실행해 멈춘다. 뒤 절반이 어긋나 있었다: 그 자리에서 **대화**로 만든 Step 이 목록
**끝**에 붙었다. 브라우저는 nn 앞의 화면을 보고 있는데 정의는 끝에 쌓이니, 저장하면
실행 순서가 화면과 어긋난다. 같은 자리의 「자연어로 Step 추가」는 일시정지 위치에 끼우고
있었으므로(FR-079), 두 입구가 같은 상황에서 다르게 굴었다.

## 이 파일이 재는 것

살아 있는 브라우저에서, 마지막 Step 앞에 멈춘 세션에 대화로 Step 하나를 만들게 한다.

1. 새 Step 이 **일시정지 위치**에 있다 — 끝이 아니다
2. 원래 마지막 Step 은 그 뒤로 밀렸다
3. 실행 위치는 새 Step **뒤**다 — AI 가 이미 수행한 동작을 「계속하기」가 다시 하지 않는다

자격 증명을 쓰지 않는다 (`us4_support`). 대본은 요소를 지목하지 않는 검증 하나만 만든다 —
여기서 보는 것은 자리이지 AI 가 아니다.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, stop_quietly
from us4_support import assert_url_contains, install_driver, observe

pytestmark = pytest.mark.browser


def wait_state(
    client: TestClient, sid: str, wanted: set[str], timeout_s: float = 60.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = dict(client.get(f"/api/sessions/{sid}").json())
        if last["state"] in wanted:
            return last
        time.sleep(0.03)
    pytest.fail(f"상태 {wanted} 에 닿지 못했다 (마지막: {last.get('state')})")
    raise AssertionError  # pragma: no cover


def test_chat_step_lands_at_the_pause_position_not_at_the_end(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_id = record_login(keyed_client, fixture_app)
    before = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    total = len(before)
    assert total >= 2, "끼울 자리가 없다"
    at = total - 1

    # 「브라우저 열어 이 Step 앞에서 멈추기」 — 마지막 Step 앞에서 멈춘다.
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "replay", "test_id": test_id, "pause_before_index": at},
    )
    assert created.status_code == 201, created.text
    sid = str(created.json()["session_id"])
    try:
        paused = wait_state(keyed_client, sid, {"paused"})
        assert paused["current_step_index"] == at

        install_driver(monkeypatch, [observe(0), assert_url_contains("http")])
        resp = keyed_client.post(f"/api/sessions/{sid}/chat", json={"text": "지금 주소를 확인해"})
        assert resp.status_code == 200, resp.text
        after = wait_state(keyed_client, sid, {"paused", "ai_blocked"})
        assert after["state"] == "paused", after

        ids = [s["id"] for s in after["steps"]]
        assert len(ids) == total + 1, f"Step 이 하나 늘어야 한다: {ids}"
        (made,) = [i for i in ids if i not in before]

        # (1) 일시정지 위치에 끼워졌다 — 끝이 아니다.
        assert ids.index(made) == at, f"새 Step 이 끝에 붙었다: {ids}"
        # (2) 원래 마지막 Step 은 그 뒤로 밀렸다.
        assert ids[at + 1] == before[-1]
        # (3) 실행 위치는 새 Step 뒤다.
        assert after["current_step_index"] == at + 1, after["current_step_index"]
    finally:
        stop_quietly(keyed_client, sid)
