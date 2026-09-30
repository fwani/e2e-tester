"""세션 시작의 경계. 026 FR-001·FR-003·FR-005~FR-008 (contracts/api-contract §1).

수정은 **화면을 대상 Step 직전 상태로 만드는 것**에서 시작한다. 그 자리가 어디인지와
시작을 거절해야 하는 자리를 경계값에서 확인한다.

**거절은 브라우저를 띄우기 전에 일어나야 한다** — 016 FR-016 이 세운 규칙이며, 띄운 뒤
거절하면 사용자는 창이 떴다 사라지는 것을 보고 무엇이 잘못됐는지는 그 뒤에야 안다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us_step_edit.support import open_step_edit

pytestmark = pytest.mark.browser


def saved_ids(client: TestClient, test_id: str) -> list[str]:
    return [s["id"] for s in client.get(f"/api/tests/{test_id}").json()["steps"]]


# ─── 시작한다 (FR-005·FR-008) ───────────────────────────────────────────────


def test_choosing_the_first_step_runs_nothing(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """대상이 첫 Step 이면 **아무것도 실행하지 않는다** (FR-008).

    도착점이 「시작 주소를 연 상태」다 — 016 FR-021 과 같다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    sid = open_step_edit(keyed_client, test_id, saved[0])
    assert isinstance(sid, str)
    try:
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] == "paused"
        assert view["current_step_index"] == 0
        assert not view.get("step_results"), (
            f"아무것도 실행하지 않아야 하는데 결과가 있다: {view.get('step_results')}"
        )
        assert view["step_edit"]["target_step_id"] == saved[0]
        assert view["step_edit"]["target_index"] == 0
        assert view["rerecord"] is None, "재녹화와 동시에 차지 않는다"
    finally:
        stop_quietly(keyed_client, sid)


def test_choosing_a_middle_step_stops_right_before_it(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """앞 구간을 실행해 **그 Step 이 동작할 화면**에서 멈춘다 (FR-005)."""
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    target = saved[-1]

    sid = open_step_edit(keyed_client, test_id, target)
    assert isinstance(sid, str)
    try:
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["current_step_index"] == len(saved) - 1
        assert view["step_edit"]["target_step_id"] == target
        assert view["step_edit"]["can_commit"] is True, (
            "만든 것이 없어도 확정할 수 있다 — 016 과 갈리는 자리 (research R5)"
        )
        assert view["step_edit"]["created_step_ids"] == []
        # 016 과 달리 옛 Step 이 그대로 목록에 있다. 버리는 것이 아니라 고치는 것이다.
        assert [s["id"] for s in view["steps"]] == saved
    finally:
        stop_quietly(keyed_client, sid)


def test_the_session_shape_matches_a_rerecord_session(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """수정 세션은 **기존 세션의 한 형태**다. 새 국면을 만들지 않는다.

    `authoring_mode` 를 016 재녹화와 **같은 값**으로 둔다. 화면은 그 값이 아니라
    `step_edit` 이 실렸는지로 이 세션을 알아본다 — 016 이 `rerecord` 에 대해 한 것과
    같은 방식이며, 검증된 길을 벗어날 이유가 없다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)

    edit_sid = open_step_edit(keyed_client, test_id, saved[0])
    assert isinstance(edit_sid, str)
    try:
        edit_view = keyed_client.get(f"/api/sessions/{edit_sid}").json()
    finally:
        stop_quietly(keyed_client, edit_sid)

    rerec = keyed_client.post(
        "/api/sessions",
        json={"mode": "rerecord", "test_id": test_id, "rerecord_step_ids": [saved[0]]},
    )
    assert rerec.status_code == 201, rerec.text
    rerec_sid = rerec.json()["session_id"]
    try:
        rerec_view = keyed_client.get(f"/api/sessions/{rerec_sid}").json()
        assert edit_view["authoring_mode"] == rerec_view["authoring_mode"]
    finally:
        stop_quietly(keyed_client, rerec_sid)


# ─── 거절한다 — 브라우저를 띄우기 전에 (FR-003·FR-007) ──────────────────────


def test_a_missing_target_is_refused(keyed_client: TestClient, fixture_app: str) -> None:
    body = open_step_edit(keyed_client, record_login(keyed_client, fixture_app), None, expect=400)
    assert isinstance(body, dict)
    assert "고칠 Step" in body["error"]["message"]


def test_a_target_that_is_not_in_the_test_is_refused(
    keyed_client: TestClient, fixture_app: str
) -> None:
    test_id = record_login(keyed_client, fixture_app)
    body = open_step_edit(keyed_client, test_id, "step-99", expect=400)
    assert isinstance(body, dict)
    assert "step-99" in body["error"]["message"]


def test_a_missing_test_id_is_refused(keyed_client: TestClient) -> None:
    resp = keyed_client.post("/api/sessions", json={"mode": "step_edit"})
    assert resp.status_code == 400, resp.text
    assert "test_id" in resp.json()["error"]["message"]


def test_an_instruction_is_refused_because_the_way_in_is_chat(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """지시는 대화로 온다 (FR-010). 두 입구를 두면 어느 쪽에 써야 하는지 모른다."""
    test_id = record_login(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    resp = keyed_client.post(
        "/api/sessions",
        json={
            "mode": "step_edit",
            "test_id": test_id,
            "step_edit_step_id": saved[0],
            "ai_instruction": "이 버튼 말고 저 버튼",
        },
    )
    assert resp.status_code == 400, resp.text
    assert "대화" in resp.json()["error"]["message"]


def test_a_list_cannot_even_be_expressed(keyed_client: TestClient, fixture_app: str) -> None:
    """**「둘 이상」이 경계에서 표현조차 되지 않는다** (data-model §4).

    화면이 먼저 막고(FR-003) 타입이 마지막으로 막는다. 목록을 보내면 요청 검증에서
    걸린다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = saved_ids(keyed_client, test_id)
    resp = keyed_client.post(
        "/api/sessions",
        json={"mode": "step_edit", "test_id": test_id, "step_edit_step_id": saved[:2]},
    )
    assert resp.status_code == 422, resp.text
