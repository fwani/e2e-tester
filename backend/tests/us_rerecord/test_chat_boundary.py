"""대화 입구의 경계 검증. 016 FR-010·FR-016·FR-022 (T024).

헌법 보안 요구 — 「모든 외부 입력은 경계에서 검증한다」. 이 파일은 **거절되는 것들**을
모아 둔 자리이며, 거절이 조용하지 않은지(사유가 있는지)도 함께 본다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, stop_quietly
from tests.us4_support import install_driver
from tests.us_rerecord.support import open_rerecord

pytestmark = pytest.mark.browser


# ─── 구간 검증 (FR-015·FR-016) — 브라우저를 띄우기 **전에** 거절한다 ────────


def test_a_gap_in_the_range_is_refused_before_opening_a_browser(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """불연속 구간은 세션을 만들기 전에 거절된다 (FR-016).

    **브라우저를 띄운 뒤에 거절하면 안 된다.** 사용자는 창이 떴다 사라지는 것을 보고,
    무엇이 잘못됐는지는 그 뒤에야 안다.
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    if len(saved) < 3:
        pytest.skip("불연속을 만들려면 Step 이 셋 이상 필요하다")

    before = len(keyed_client.get("/api/sessions").json()["sessions"])
    body = open_rerecord(keyed_client, test_id, [saved[0], saved[2]], expect=400)

    assert isinstance(body, dict)
    assert "이어" in body["error"]["message"] or "연속" in body["error"]["message"]
    assert body["error"].get("next_action"), "무엇을 하면 되는지 말해야 한다 (003 계약)"
    after = len(keyed_client.get("/api/sessions").json()["sessions"])
    assert after == before, "거절했는데 세션이 만들어졌다"


def test_an_empty_range_is_refused(keyed_client: TestClient, fixture_app: str) -> None:
    test_id = record_login(keyed_client, fixture_app)
    body = open_rerecord(keyed_client, test_id, [], expect=400)
    assert isinstance(body, dict)
    assert body["error"].get("next_action")


def test_an_unknown_step_id_is_refused(
    keyed_client: TestClient, fixture_app: str
) -> None:
    test_id = record_login(keyed_client, fixture_app)
    body = open_rerecord(keyed_client, test_id, ["step-99"], expect=400)
    assert isinstance(body, dict)
    assert "step-99" in body["error"]["message"]


def test_an_instruction_is_refused_in_rerecord_mode(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """재녹화는 지시문을 받지 않는다 (api-contract §1).

    두 입구(지시문·대화)를 두면 사용자는 어느 쪽에 써야 하는지 모른다. 조용히
    무시하는 것이 아니라 **거절하고 어디에 쓰라고 말한다.**
    """
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    resp = keyed_client.post(
        "/api/sessions",
        json={
            "mode": "rerecord",
            "test_id": test_id,
            "rerecord_step_ids": [saved[-1]],
            "ai_instruction": "로그인해",
        },
    )
    assert resp.status_code == 400, resp.text
    assert "대화" in resp.json()["error"]["message"]


def test_rerecord_needs_a_saved_test(keyed_client: TestClient) -> None:
    resp = keyed_client.post(
        "/api/sessions", json={"mode": "rerecord", "rerecord_step_ids": ["step-01"]}
    )
    assert resp.status_code == 400, resp.text
    assert "test_id" in resp.json()["error"]["message"]


# ─── 대화 입력 검증 (FR-010) ────────────────────────────────────────────────


def test_an_empty_message_is_refused(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_driver(monkeypatch, [])
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        blank = keyed_client.post(f"/api/sessions/{sid}/chat", json={"text": "   "})
        assert blank.status_code == 400, blank.text
        empty = keyed_client.post(f"/api/sessions/{sid}/chat", json={"text": ""})
        assert empty.status_code == 422, "길이 0 은 요청 스키마가 거절한다"
    finally:
        stop_quietly(keyed_client, sid)


def test_an_overlong_message_is_refused(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """상한은 지시문과 **같은 출처**다 (FR-010).

    두 입구가 다른 상한을 가지면 사용자는 어느 쪽이 얼마까지인지 외워야 한다.
    """
    from itb.domain.test_case import MAX_INSTRUCTION_CHARS

    install_driver(monkeypatch, [])
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]
    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/chat", json={"text": "가" * (MAX_INSTRUCTION_CHARS + 1)}
        )
        assert resp.status_code == 422, resp.text
    finally:
        stop_quietly(keyed_client, sid)


def test_chat_is_refused_while_the_runner_is_going(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """실행 중에는 말을 걸 수 없다 (api-contract §2-1 의 `paused` 게이트).

    **원칙 II 가 여기서도 지켜진다** — 러너가 도는 동안 에이전트가 시작되면 불변식 6 이
    깨진다. 게이트가 그 문을 닫는다.
    """
    install_driver(monkeypatch, [])
    test_id = record_login(keyed_client, fixture_app)

    created = keyed_client.post(
        "/api/sessions", json={"mode": "replay", "test_id": test_id, "pacing": "slow"}
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]
    try:
        resp = keyed_client.post(f"/api/sessions/{sid}/chat", json={"text": "안녕"})
        # 실행이 이미 끝났으면 게이트가 아니라 상태가 막는다 — 어느 쪽이든 거절이다.
        assert resp.status_code == 409, resp.text
        assert resp.json()["error"].get("next_action")
    finally:
        stop_quietly(keyed_client, sid)


def test_chat_on_an_unknown_session_is_refused(keyed_client: TestClient) -> None:
    resp = keyed_client.post("/api/sessions/nope/chat", json={"text": "안녕"})
    assert resp.status_code == 404, resp.text
