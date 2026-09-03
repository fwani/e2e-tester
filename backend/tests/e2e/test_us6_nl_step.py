"""US6 종단 테스트 — quickstart §8 (T129).

자연어 지시 하나가 Step 하나를 만들고, 그 Step 이 수동 Step 과 같은 형태로 실행된다.
4단계(화면에 없는 대상)가 이 흐름의 안전장치다 — 만들 수 없으면 만들지 않는다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import replay, result_of, start_replay, stop_quietly
from us3_support import pause_after, record_login_then_two_menus
from us4_support import (
    assert_url_contains,
    click_named,
    install_driver,
    observe,
    report_blocked,
)


def test_quickstart_section8_natural_language_step(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§8 1~4단계."""
    client = keyed_client
    test_id = record_login_then_two_menus(client, fixture_app)
    sid = start_replay(client, test_id)
    try:
        view = pause_after(client, sid, finished_steps=3, events=event_log)
        pause_index = view["current_step_index"]

        # 1단계 — 자연어 지시로 검증 Step 이 일시정지 위치에 삽입된다
        install_driver(monkeypatch, [observe(0), assert_url_contains(".html")])
        first = client.post(
            f"/api/sessions/{sid}/ai-step",
            json={"instruction": "지금 주소가 픽스처 앱 화면인지 확인해"},
        )
        assert first.status_code == 200, first.text
        assert first.json()["created"] is True, first.json()["message"]
        inserted = first.json()["steps"][pause_index]
        assert inserted["type"] == "assertion"

        # 2단계 — 수동 Assertion 과 구조가 같다
        manual = client.post(
            f"/api/sessions/{sid}/assertions",
            json={"kind": "url", "value": ".html", "match": "contains"},
        )
        assert manual.status_code == 200, manual.text
        manual_step = next(
            s
            for s in manual.json()["steps"]
            if s["type"] == "assertion" and s["id"] != inserted["id"]
        )
        assert set(inserted) == set(manual_step)

        # 4단계 — 화면에 없는 대상을 지시하면 Step 을 만들지 않고 알린다
        install_driver(
            monkeypatch, [observe(0), report_blocked("화면에 '결제' 버튼이 없습니다.")]
        )
        before = [s["id"] for s in manual.json()["steps"]]
        missing = client.post(
            f"/api/sessions/{sid}/ai-step", json={"instruction": "결제 버튼을 눌러"}
        )
        assert missing.status_code == 200, missing.text
        assert missing.json()["created"] is False
        assert [s["id"] for s in missing.json()["steps"]] == before
        assert missing.json()["state"] == "paused"

        # 동작 Step 도 자연어로 추가해 본다 (검증 3 · 동작 2 중 동작 경로)
        install_driver(monkeypatch, [observe(0), click_named("분석")])
        action = client.post(
            f"/api/sessions/{sid}/ai-step", json={"instruction": "분석 메뉴를 눌러"}
        )
        assert action.status_code == 200, action.text
        assert action.json()["created"] is True, action.json()["message"]

        saved = client.post(f"/api/sessions/{sid}/save", json={"name": "자연어 Step"})
        assert saved.status_code == 200, saved.text
        saved_id = saved.json()["id"]
    finally:
        stop_quietly(client, sid)

    # 3단계 — 재실행이 통과한다 (언어모델 미호출 확인은 T133 이 맡는다)
    view = replay(client, saved_id)
    assert view["state"] == "completed", view
    result = result_of(client, saved_id)
    assert result["outcome"] == "pass", [
        (s["label"], s["error_message"]) for s in result["steps"]
    ]
