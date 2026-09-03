"""일시정지 중 자연어 Step 추가. FR-078~FR-081 (T128).

US4 와 다른 점은 범위다 — 지시 하나가 Step 하나를 만든다.

확인하는 것:

1. 만들어진 Step 이 **일시정지 위치에** 삽입된다 (FR-079)
2. 수동으로 만든 Step 과 **구조가 같다** (FR-080, 원칙 I)
3. 대상을 찾지 못하면 **Step 을 만들지 않고 일시정지를 유지한다** (FR-081)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import start_replay, stop_quietly
from us3_support import pause_after, record_login_then_two_menus
from us4_support import assert_url_contains, click_named, install_driver, observe

NL_ASSERT_SCRIPT = [observe(0), assert_url_contains(".html")]
"""자연어 요청에 대응하는 대본.

비교 값을 `.html` 로 둔 이유는 **일시정지 지점이 실행 속도에 따라 조금씩 다를 수 있기**
때문이다. 특정 화면 주소를 기대하면 검증하려는 것(자연어 → Step 삽입)이 아니라 타이밍
때문에 실패한다. 검증 종류와 삽입 경로는 그대로 지나간다.
"""


def _paused_replay(
    client: TestClient, fixture_app: str, events: list[tuple[str, dict]]
) -> tuple[str, dict]:
    test_id = record_login_then_two_menus(client, fixture_app)
    sid = start_replay(client, test_id)
    view = pause_after(client, sid, finished_steps=3, events=events)
    return sid, view


def test_nl_step_is_inserted_at_the_pause_position(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-079 — 삽입 위치는 일시정지 위치다.

    목록 끝에 붙이면 사용자가 보고 있는 화면과 정의의 순서가 어긋난다.
    """
    install_driver(monkeypatch, NL_ASSERT_SCRIPT)
    sid, view = _paused_replay(keyed_client, fixture_app, event_log)
    try:
        pause_index = view["current_step_index"]
        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-step",
            json={"instruction": "지금 주소가 픽스처 앱 화면인지 확인해"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["created"] is True, body["message"]

        inserted = body["steps"][pause_index]
        assert inserted["id"] == body["step_id"]
        assert inserted["type"] == "assertion"
        assert inserted["author"] == "ai"
    finally:
        stop_quietly(keyed_client, sid)


def test_nl_step_has_the_same_shape_as_a_manual_step(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-080·원칙 I — 자연어로 만든 Step 과 손으로 만든 Step 의 구조가 같다.

    같은 세션에서 두 경로로 각각 하나를 만들어 필드 집합을 비교한다. 다르면 실행 경로가
    갈라질 수 있고, 그것이 원칙 I 이 막으려는 것이다.
    """
    install_driver(monkeypatch, NL_ASSERT_SCRIPT)
    sid, _view = _paused_replay(keyed_client, fixture_app, event_log)
    try:
        nl = keyed_client.post(
            f"/api/sessions/{sid}/ai-step",
            json={"instruction": "지금 주소가 픽스처 앱 화면인지 확인해"},
        )
        assert nl.status_code == 200, nl.text
        assert nl.json()["created"] is True, nl.json()["message"]
        nl_step = next(
            s for s in nl.json()["steps"] if s["id"] == nl.json()["step_id"]
        )

        manual = keyed_client.post(
            f"/api/sessions/{sid}/assertions",
            json={"kind": "url", "value": ".html", "match": "contains"},
        )
        assert manual.status_code == 200, manual.text
        manual_step = next(
            s
            for s in manual.json()["steps"]
            if s["type"] == "assertion" and s["id"] != nl_step["id"]
        )

        assert set(nl_step) == set(manual_step), (
            f"필드 집합이 다르다. 자연어: {sorted(nl_step)}, 수동: {sorted(manual_step)}"
        )
        assert nl_step["assertion"].keys() == manual_step["assertion"].keys()
        # 작성 주체만 다르다 (FR-014).
        assert nl_step["author"] == "ai"
        assert manual_step["author"] == "human"
    finally:
        stop_quietly(keyed_client, sid)


def test_unfound_target_creates_no_step_and_stays_paused(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-081 — 대상을 찾지 못하면 Step 을 만들지 않고 알리며 일시정지를 유지한다.

    만들어 두면 재실행에서 반드시 실패하는 Step 이 정의에 들어간다.
    """
    from us4_support import report_blocked

    install_driver(
        monkeypatch, [observe(0), report_blocked("화면에 '우주선' 이 없습니다.")]
    )
    sid, view = _paused_replay(keyed_client, fixture_app, event_log)
    try:
        before = [s["id"] for s in view["steps"]]
        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-step", json={"instruction": "우주선을 눌러"}
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["created"] is False
        assert "찾지 못해" in body["message"] or "우주선" in body["message"]
        assert [s["id"] for s in body["steps"]] == before, "실패했는데 Step 이 생겼다"
        assert body["state"] == "paused", "실패가 일시정지를 풀었다 (FR-081 위반)"
    finally:
        stop_quietly(keyed_client, sid)


def test_nl_step_requires_paused_state(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-035a 와 같은 게이트 — 일시정지가 아니면 거절한다.

    실행 중에 화면을 분석해 Step 을 만들면, 만드는 사이에 화면이 또 바뀐다.
    """
    install_driver(monkeypatch, NL_ASSERT_SCRIPT)
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-step", json={"instruction": "확인해"}
        )
        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "NOT_PAUSED"
    finally:
        stop_quietly(keyed_client, sid)


def test_empty_instruction_is_rejected(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-085 — 경계에서 검증한다."""
    install_driver(monkeypatch, NL_ASSERT_SCRIPT)
    sid, _view = _paused_replay(keyed_client, fixture_app, event_log)
    try:
        resp = keyed_client.post(f"/api/sessions/{sid}/ai-step", json={"instruction": "  "})
        # Pydantic 의 길이 검증(422) 또는 작성 계층의 검증(400) 중 하나로 거절된다.
        assert resp.status_code in (400, 422), resp.text
    finally:
        stop_quietly(keyed_client, sid)


def test_nl_step_survives_save_and_replay(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """자연어로 추가한 Step 이 저장되고 재실행된다 (FR-080).

    재실행에서 언어모델을 부르지 않는다는 확인은 `test_replay_no_llm.py` 가 맡는다 (T133).
    """
    from us2_support import replay, result_of

    install_driver(monkeypatch, [observe(0), click_named("분석")])
    sid, view = _paused_replay(keyed_client, fixture_app, event_log)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-step", json={"instruction": "분석 메뉴를 눌러"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["created"] is True, resp.json()["message"]

        saved = keyed_client.post(
            f"/api/sessions/{sid}/save", json={"name": "자연어 Step 포함"}
        )
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
    finally:
        stop_quietly(keyed_client, sid)

    view = replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    assert view["state"] == "completed", [
        (s["label"], s["outcome"], s["error_message"]) for s in result["steps"]
    ]
    assert result["outcome"] == "pass", [
        (s["label"], s["error_message"]) for s in result["steps"]
    ]
