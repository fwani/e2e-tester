"""009 T035 — 목표 지점을 상태가 말한다 (FR-293·FR-294·FR-296 · 계약 §4-3).

## 이 파일이 지키는 것

「이 앞에 추가」는 지정한 Step 앞까지 재생하고 멈춘다. 그 배관(`pause_before_index`)은
006 이 이미 만들었다. 009 가 더하는 것은 **그 목표가 상태에 실린다**는 것이다.

목표를 화면 상태로만 들고 있으면 새로 고침 한 번에 「어디서 멈출 예정인지」가 사라진다 —
005 U-18 이 같은 형태였다. 그래서 세션 뷰가 그것을 말해야 하고, 그 말이 사실이어야 한다.

**가장 중요한 것은 도달하지 못한 경우다** (FR-294). 목표 앞에서 실패했는데 화면이
「일시정지됨」만 말하면 사용자는 도달한 것으로 읽고, 없는 자리에 Step 을 넣으려 한다.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import break_first_click, record_login, stop_quietly
from us3_support import record_login_then_two_menus


def _view(client: TestClient, sid: str) -> dict[str, Any]:
    resp = client.get(f"/api/sessions/{sid}")
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def _wait_state(
    client: TestClient, sid: str, wanted: tuple[str, ...], timeout_s: float = 90.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    view: dict[str, Any] = {}
    while time.monotonic() < deadline:
        view = _view(client, sid)
        if view["state"] in wanted:
            return view
        time.sleep(0.05)
    pytest.fail(f"{wanted} 에 닿지 않았다. 마지막 상태: {view.get('state')}")
    raise AssertionError  # pragma: no cover


def _open_at(client: TestClient, test_id: str, index: int) -> str:
    created = client.post(
        "/api/sessions",
        json={"mode": "replay", "test_id": test_id, "pause_before_index": index},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["session_id"])


@pytest.mark.browser
@pytest.mark.usefixtures("fixture_app")
def test_목표_앞에서_멈추고_도달하면_목표가_비워진다(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-293 — 값의 뜻이 하나다: `None` 이 아니면 아직 닿지 않았다."""
    test_id = record_login(keyed_client, fixture_app)
    total = len(keyed_client.get(f"/api/tests/{test_id}/definition").json()["test"]["steps"])
    assert total >= 2

    target = total - 1
    sid = _open_at(keyed_client, test_id, target)
    try:
        view = _wait_state(keyed_client, sid, ("paused",))

        assert view["current_step_index"] == target, "목표 앞에서 멈추지 않았다"
        # 도달했으므로 목표가 비어 있다 — 「멈출 예정」이 아니라 「멈췄다」다.
        assert view["pause_before_index"] is None
    finally:
        stop_quietly(keyed_client, sid)


@pytest.mark.browser
@pytest.mark.usefixtures("fixture_app")
def test_목표가_맨_앞이면_시작_주소에서_멈춘다(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-296 — 재생할 Step 이 없다. 없는 진행을 지어내지 않는다."""
    test_id = record_login(keyed_client, fixture_app)

    sid = _open_at(keyed_client, test_id, 0)
    try:
        view = _wait_state(keyed_client, sid, ("paused",))

        assert view["current_step_index"] == 0
        assert view["pause_before_index"] is None
        # 아무 Step 도 돌지 않았다 — 결과가 비어 있다.
        assert view["step_results"] == []
    finally:
        stop_quietly(keyed_client, sid)


@pytest.mark.browser
@pytest.mark.usefixtures("fixture_app")
def test_도달_전_실패하면_목표가_남는다(keyed_client: TestClient, fixture_app: str) -> None:
    """**FR-294 — 이 검사가 이 파일의 이유다.**

    목표 앞의 Step 이 실패하면 러너는 그 자리에서 멈춘다. 목표에는 닿지 못했으므로
    `pause_before_index` 가 **남아 있어야** 한다 — 그것이 화면이 「도달하기 전에
    실패했습니다」를 말할 수 있는 유일한 근거다.

    비어 있으면 화면은 도달과 실패를 구별할 수 없고, 사용자는 없는 자리에 Step 을 넣으려
    한다.
    """
    # **더 긴 녹화를 쓴다.** 로그인만 녹화하면 click 이 마지막 Step 이라 실패 지점과
    # 목표가 같아져 이 검사가 성립하지 않는다 (사전 Step 5개 이상이 필요하다).
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    broken_at = break_first_click(keyed_client, test_id)
    total = len(keyed_client.get(f"/api/tests/{test_id}/definition").json()["test"]["steps"])
    target = total - 1
    assert broken_at < target, "실패가 목표보다 앞에 있어야 이 검사가 성립한다"

    sid = _open_at(keyed_client, test_id, target)
    try:
        view = _wait_state(keyed_client, sid, ("paused", "failed"))

        outcomes = {r["step_id"]: r["outcome"] for r in view["step_results"]}
        assert "fail" in outcomes.values(), f"실패를 유도하지 못했다: {outcomes}"
        # 목표에 닿지 못했다 — 상태가 그것을 말한다.
        assert view["pause_before_index"] == target, (
            "도달하지 못했는데 목표가 비었다 — 화면이 도달과 실패를 구별할 수 없다"
        )
        assert view["current_step_index"] < target
    finally:
        stop_quietly(keyed_client, sid)


@pytest.mark.browser
@pytest.mark.usefixtures("fixture_app")
def test_목표가_범위를_벗어나면_거절한다(keyed_client: TestClient, fixture_app: str) -> None:
    """006 FR-211 의 규칙이 그대로다 — 러너가 영원히 만나지 못하는 지점을 기다리지 않는다."""
    test_id = record_login(keyed_client, fixture_app)
    total = len(keyed_client.get(f"/api/tests/{test_id}/definition").json()["test"]["steps"])

    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "replay", "test_id": test_id, "pause_before_index": total},
    )

    assert created.status_code == 400
    assert created.json()["error"]["code"] == "DEFINITION_INVALID"


@pytest.mark.browser
@pytest.mark.usefixtures("fixture_app")
def test_목표_없는_재생은_목표를_말하지_않는다(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """없는 것을 있다고 말하지 않는다 — 보통 재실행에는 멈출 예정 지점이 없다."""
    test_id = record_login(keyed_client, fixture_app)

    created = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    assert created.status_code == 201, created.text
    sid = str(created.json()["session_id"])
    try:
        assert _view(keyed_client, sid)["pause_before_index"] is None
        done = _wait_state(keyed_client, sid, ("completed", "failed"))
        assert done["pause_before_index"] is None
    finally:
        stop_quietly(keyed_client, sid)
