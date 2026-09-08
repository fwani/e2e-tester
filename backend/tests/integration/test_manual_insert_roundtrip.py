"""009 T023 — 손으로 넣은 Step 의 왕복 무결성 (SC-510 · 헌법 품질 게이트 2).

**계약 테스트가 덮지 않는 자리다.** `tests/contract/test_definition_edit_api.py` 는 삽입이
정의 파일에 반영되는 것까지 본다. 그 다음 한 걸음 — **손으로 넣은 Step 을 러너가 실제로
수행하는가** — 는 실행 없이 검증할 수 없다.

1·2 만 보면 「저장은 되지만 실행되지 않는 Step」을 통과시킨다. 사용자는 고쳤다고 믿고
다음 실행에서 아무 일도 일어나지 않은 것을 본다 — 009 가 없애려던 것보다 나쁜 상태다.

**여기서만 브라우저를 쓴다.** 삽입 자체는 브라우저 없이 되고(FR-285) 그것이 이 기능의
주장이지만, 「그 Step 이 실제로 돈다」는 주장은 실행으로만 지탱된다.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, replay, stop_quietly


def _wait_state(
    client: TestClient, sid: str, wanted: tuple[str, ...], timeout_s: float = 90.0
) -> dict[str, Any]:
    """세션이 원하는 상태에 닿을 때까지 기다린다.

    `us2_support.wait_for_run` 은 **종료** 상태만 기다린다. 목표 앞에서 멈춘 상태
    (`paused`)는 종료가 아니므로 여기서 따로 기다린다.
    """
    deadline = time.monotonic() + timeout_s
    view: dict[str, Any] = {}
    while time.monotonic() < deadline:
        resp = client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 200, resp.text
        view = resp.json()
        if view["state"] in wanted:
            return view
        time.sleep(0.05)
    pytest.fail(f"{wanted} 에 닿지 않았다. 마지막 상태: {view.get('state')}")
    raise AssertionError  # pragma: no cover


def _definition(client: TestClient, test_id: str) -> dict[str, Any]:
    resp = client.get(f"/api/tests/{test_id}/definition")
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def _save(client: TestClient, test_id: str, edits: list[dict[str, Any]]) -> dict[str, Any]:
    view = _definition(client, test_id)
    resp = client.put(
        f"/api/tests/{test_id}/definition",
        json={"revision": view["revision"], "edits": edits},
    )
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


@pytest.mark.browser
@pytest.mark.usefixtures("fixture_app")
def test_손으로_넣은_주소_이동_step_이_실제로_수행된다(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """SC-510 — 넣고 → 저장하고 → 다시 읽고 → **실행한다.**

    주소 이동을 고른 이유: 요소를 지목하지 않으므로 브라우저 없이 넣을 수 있고(FR-286),
    수행됐는지를 **화면 주소**로 확인할 수 있다. 요소를 지목하는 Step 이라면 이 경로로
    넣는 것 자체가 원칙 IV 위반이다.
    """
    test_id = record_login(keyed_client, fixture_app)
    before = _definition(keyed_client, test_id)["test"]["steps"]
    assert before, "녹화가 Step 을 만들지 못했다"

    # ① 넣는다 — 맨 뒤에 「약관 화면으로 이동」과 그 주소를 확인하는 검증을 함께.
    terms = f"{fixture_app}/terms.html"
    saved = _save(
        keyed_client,
        test_id,
        [
            {"op": "insert", "at": len(before), "spec": {"kind": "navigate", "url": terms}},
            {
                "op": "insert",
                "at": len(before) + 1,
                "spec": {"kind": "assert_url", "url": "terms.html", "match": "contains"},
            },
        ],
    )
    inserted = saved["test"]["steps"]
    assert len(inserted) == len(before) + 2

    # ② 다시 읽어도 그 자리에 있다.
    reread = _definition(keyed_client, test_id)["test"]["steps"]
    assert reread[-2]["type"] == "navigate"
    assert reread[-2]["url"] == terms
    assert reread[-1]["type"] == "assertion"
    assert reread[-1]["assertion"]["kind"] == "url"
    # 손으로 넣은 것도 실행 방식이 같다 (원칙 I · FR-014).
    assert reread[-2]["author"] == "human"

    # ③ 실행한다 — 넣은 Step 이 **수행됐는가**.
    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", (
        f"손으로 넣은 Step 이 실행을 깼다: {view['state']} · {view.get('step_results')}"
    )

    outcomes = {r["step_id"]: r["outcome"] for r in view["step_results"]}
    for step in reread[-2:]:
        assert outcomes.get(step["id"]) == "pass", (
            f"{step['id']}({step['type']}) 가 수행되지 않았다 — 저장은 됐지만 실행되지 "
            f"않는 Step 이다. 결과: {outcomes}"
        )


@pytest.mark.browser
@pytest.mark.usefixtures("fixture_app")
def test_일시정지_중_손으로_넣은_step_이_이어서_수행된다(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """FR-290 · 헌법 원칙 III — 삽입이 브라우저 상태를 깨지 않고 이어서 돈다.

    삽입은 브라우저에 아무 명령도 보내지 않으므로 세션 상태가 보존되고, 넣은 Step 이
    **다음에 실행될 것**이 되어야 한다 — 실행 위치를 밀면 방금 넣은 Step 이 조용히
    건너뛰어진다.
    """
    test_id = record_login(keyed_client, fixture_app)
    total = len(_definition(keyed_client, test_id)["test"]["steps"])
    assert total >= 2, "일시정지할 자리가 없다"

    # 마지막 Step 앞에서 멈추는 재생 세션을 연다 (`pause_before_index`).
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "replay", "test_id": test_id, "pause_before_index": total - 1},
    )
    assert created.status_code == 201, created.text
    sid = str(created.json()["session_id"])

    try:
        view = _wait_state(keyed_client, sid, ("paused",))
        paused_at = view["current_step_index"]
        assert paused_at == total - 1, f"목표 앞에서 멈추지 않았다: {paused_at}"

        resp = keyed_client.post(
            f"/api/sessions/{sid}/steps:manual",
            json={"spec": {"kind": "assert_url", "url": "http", "match": "contains"}},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # 넣은 Step 이 **다음에 실행될 것**이다.
        assert body["current_step_index"] == paused_at
        assert body["steps"][paused_at]["type"] == "assertion"

        # 브라우저는 그대로다 — 삽입이 화면을 건드리지 않았다.
        after = keyed_client.get(f"/api/sessions/{sid}").json()
        assert after["state"] == "paused"
        assert after["tabs_open"] == view["tabs_open"]

        resumed = keyed_client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code in (200, 202), resumed.text
        done = _wait_state(keyed_client, sid, ("completed", "failed"))
        assert done["state"] == "completed", done.get("step_results")

        outcomes = {r["step_id"]: r["outcome"] for r in done["step_results"]}
        inserted_id = body["steps"][paused_at]["id"]
        assert outcomes.get(inserted_id) == "pass", (
            f"일시정지 중 넣은 Step 이 건너뛰어졌다: {outcomes}"
        )
    finally:
        stop_quietly(keyed_client, sid)
