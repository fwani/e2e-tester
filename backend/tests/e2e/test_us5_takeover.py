"""US5 종단 테스트 — quickstart §7. 헌법 원칙 III (T121).

절차를 그대로 따른다. 픽스처 앱의 ⋮ 메뉴 안 삭제는 AI 가 찾기 어려운 요소로 의도적으로
둔 것이다 (fixtures/sample-app/README.md).

**2단계가 이 흐름의 전제다**: 실패했는데 브라우저가 닫히지 않는다. 닫히면 나머지 8단계가
성립하지 않는다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import click_like_a_person, replay, result_of, stop_quietly
from us3_support import current_url
from us4_support import (
    click_named,
    fill_named,
    fill_password,
    install_driver,
    observe,
    report_blocked,
    start_ai_session,
    wait_for_event,
)

DELETE_INSTRUCTION = "로그인한 다음 프로젝트 메뉴로 이동해서 TEST 프로젝트를 삭제해"

BLOCKED_AT_DELETE = [
    observe(0),
    fill_named("이메일", "tester@example.com"),
    fill_password("ai-authored-not-a-real-secret"),
    observe(0),
    click_named("로그인"),
    observe(0),
    report_blocked("⋮ 메뉴를 열어야 삭제 항목이 나타나는데 그 항목을 찾을 수 없습니다."),
]


def test_quickstart_section7_takeover_flow(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§7 1~6·10단계 — 실패 → 인수 → 계속하기 → 저장 → 재실행."""
    client = keyed_client
    install_driver(monkeypatch, BLOCKED_AT_DELETE)

    # 1단계 — 삭제 단계에서 막힌다
    sid = start_ai_session(client, fixture_app, DELETE_INSTRUCTION)
    try:
        blocked = wait_for_event(event_log, "ai_blocked")

        # 2단계 — ★ 브라우저가 닫히지 않았다. 실패 이유와 4선택지가 있다
        session = client.app.state.itb.sessions.require(sid)
        assert session.open_tabs(), "실패가 브라우저를 닫았다 — FR-069 위반"
        assert blocked["reason"]
        assert blocked["choices"] == ["takeover", "retry", "skip", "abort"]
        screen_before = current_url(client, sid)

        # 3단계 — "직접 수행". AI 가 남긴 화면 그대로다
        chosen = client.post(f"/api/sessions/{sid}/ai-choice", json={"choice": "takeover"})
        assert chosen.status_code == 200, chosen.text
        assert chosen.json()["state"] == "takeover_recording"
        assert current_url(client, sid) == screen_before

        # 4단계 — 사람이 ⋮ → 삭제를 수행하고 HUMAN Step 으로 기록된다
        page = session.tabs[session.active_tab_index].page

        async def human_delete(p: Any = page) -> None:
            await click_like_a_person(p, "button.kebab")
            await asyncio.sleep(0.4)
            await click_like_a_person(p, ".menu button[data-act=delete]")
            await asyncio.sleep(0.5)

        client.portal.call(human_delete)  # type: ignore[attr-defined]

        steps = client.get(f"/api/sessions/{sid}").json()["steps"]
        human = [s for s in steps if s["author"] == "human"]
        assert human, f"인수 중 조작이 기록되지 않았다: {[s['label'] for s in steps]}"

        # 5단계 — AI Step 과 HUMAN Step 이 같은 형태로 한 목록에 있다 (원칙 I)
        ai = [s for s in steps if s["author"] == "ai"]
        assert ai and human
        assert all("type" in s and "target" in s or s["type"] in ("navigate", "close_tab")
                   for s in steps)

        # 6단계 — "계속하기" 로 AI 가 남은 지시를 맡는다
        install_driver(monkeypatch, [observe(0)])
        event_log.clear()
        resumed = client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code == 200, resumed.text
        wait_for_event(event_log, "ai_finished")
        assert client.app.state.itb.sessions.require(sid).open_tabs()

        saved = client.post(f"/api/sessions/{sid}/save", json={"name": "AI+사람 삭제"})
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
        # 작성 방식은 시작한 방식으로 고정된다 — 사람이 이어받아도 AI 다 (FR-002a)
        assert saved.json()["authoring_mode"] == "ai"
    finally:
        stop_quietly(client, sid)

    # 10단계 — 저장 후 재실행이 통과한다
    view = replay(client, test_id)
    assert view["state"] == "completed", view
    result = result_of(client, test_id)
    assert result["outcome"] == "pass", [
        (s["label"], s["outcome"], s["error_message"]) for s in result["steps"]
    ]


def test_quickstart_section7_steps7_to_9_other_choices(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§7 7~9단계 — "AI에게 다시" / "건너뛰기" / "종료" 가 각각 동작한다."""
    client = keyed_client

    for choice, expected_state in (
        ("retry", "paused"),
        ("skip", "paused"),
        ("abort", "stopped"),
    ):
        install_driver(monkeypatch, BLOCKED_AT_DELETE)
        event_log.clear()
        sid = start_ai_session(client, fixture_app, DELETE_INSTRUCTION)
        try:
            wait_for_event(event_log, "ai_blocked")
            if choice != "abort":
                # 재개 후 AI 가 할 일을 바꿔 둔다 — 같은 대본이면 또 막힌다.
                install_driver(monkeypatch, [observe(0)])
                event_log.clear()

            resp = client.post(f"/api/sessions/{sid}/ai-choice", json={"choice": choice})
            assert resp.status_code == 200, f"{choice} → {resp.text}"

            if choice == "abort":
                assert resp.json()["state"] == expected_state
            else:
                wait_for_event(event_log, "ai_finished")
                view = client.get(f"/api/sessions/{sid}").json()
                assert view["state"] == expected_state, f"{choice} → {view['state']}"
                # 어느 선택지에서도 브라우저는 살아 있다.
                assert client.app.state.itb.sessions.require(sid).open_tabs()
        finally:
            stop_quietly(client, sid)
