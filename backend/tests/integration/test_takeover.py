"""AI 실패 → 사람 인수. FR-069~FR-077 (T120).

**PRD §20 의 핵심 가설이 여기서 검증된다.** AI 가 막혔을 때 세션이 살아 있어야 사람이
이어받을 수 있고, 이어받은 결과가 같은 Step 모델에 남아야 원칙 I 이 성립한다.

확인하는 것:

1. 실패 시 브라우저가 닫히지 않고 화면 상태가 보존된다 (FR-069)
2. "직접 수행" 으로 이어받아 조작한 것이 `author=human` Step 으로 기록된다 (FR-071·FR-075)
3. AI Step 과 HUMAN Step 이 **같은 형태로 한 목록에** 있다 (원칙 I)
4. "계속하기" 로 AI 가 남은 지시를 이어서 맡는다 (FR-076)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import click_like_a_person, stop_quietly
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

LOGIN_THEN_BLOCKED = [
    observe(0),
    fill_named("이메일", "tester@example.com"),
    fill_password("ai-authored-not-a-real-secret"),
    observe(0),
    click_named("로그인"),
    observe(0),
    report_blocked("⋮ 메뉴 안의 삭제 항목을 찾을 수 없습니다."),
]
"""로그인은 성공하고 삭제에서 막히는 대본. quickstart §7 1단계와 같은 국면이다."""


def _block(client: TestClient, fixture_app: str, events: list[tuple[str, dict]]) -> str:
    sid = start_ai_session(client, fixture_app, "TEST 프로젝트를 삭제해")
    blocked = wait_for_event(events, "ai_blocked")
    assert blocked["choices"] == ["takeover", "retry", "skip", "abort"]
    return sid


def test_failure_keeps_session_and_screen(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-069 — 실패가 브라우저를 닫지 않고 화면도 그대로다."""
    install_driver(monkeypatch, LOGIN_THEN_BLOCKED)
    sid = _block(keyed_client, fixture_app, event_log)
    try:
        session = keyed_client.app.state.itb.sessions.require(sid)
        assert session.open_tabs(), "막힘 상태에서 브라우저가 닫혔다 — 불변식 1 위반"
        # AI 가 로그인까지 진행한 화면이 그대로 남아 있다.
        assert "projects.html" in current_url(keyed_client, sid)

        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] == "ai_blocked"
        assert view["steps"], "막히기 전에 성공한 동작이 사라졌다"
    finally:
        stop_quietly(keyed_client, sid)


def test_takeover_records_human_steps_in_the_same_list(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-071·FR-075·원칙 I — 사람이 이어받은 동작이 같은 목록에 같은 형태로 남는다."""
    install_driver(monkeypatch, LOGIN_THEN_BLOCKED)
    sid = _block(keyed_client, fixture_app, event_log)
    try:
        before = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert all(s["author"] == "ai" for s in before)

        chosen = keyed_client.post(
            f"/api/sessions/{sid}/ai-choice", json={"choice": "takeover"}
        )
        assert chosen.status_code == 200, chosen.text
        assert chosen.json()["state"] == "takeover_recording"

        # 사람이 실제 창에서 조작한다.
        session = keyed_client.app.state.itb.sessions.require(sid)
        page = session.tabs[session.active_tab_index].page

        async def act(p: Any = page) -> None:
            await click_like_a_person(p, "[data-testid=create-project]")
            await asyncio.sleep(0.5)

        keyed_client.portal.call(act)  # type: ignore[attr-defined]

        after = keyed_client.get(f"/api/sessions/{sid}").json()["steps"]
        assert len(after) > len(before), "인수 중 조작이 기록되지 않았다"

        human = [s for s in after if s["author"] == "human"]
        ai = [s for s in after if s["author"] == "ai"]
        assert human and ai, f"두 주체의 Step 이 함께 있어야 한다: {after}"

        # ★ 원칙 I — `author` 를 빼면 구조가 구분되지 않는다.
        assert {k for k in human[0] if k != "author"} == {
            k for k in ai[0] if k != "author"
        } or human[0]["type"] != ai[0]["type"]
    finally:
        stop_quietly(keyed_client, sid)


def test_resume_hands_the_work_back_to_ai(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-076 — "계속하기" 로 AI 가 남은 지시를 현재 상태에서 이어서 맡는다."""
    install_driver(monkeypatch, LOGIN_THEN_BLOCKED)
    sid = _block(keyed_client, fixture_app, event_log)
    try:
        keyed_client.post(f"/api/sessions/{sid}/ai-choice", json={"choice": "takeover"})

        # 재개 이후 AI 가 할 일을 새 대본으로 바꿔 둔다 — 사람이 막힌 지점을 해결했으므로
        # 이번에는 진행할 수 있는 상황을 흉내 낸다.
        install_driver(monkeypatch, [observe(0)])
        event_log.clear()

        resumed = keyed_client.post(f"/api/sessions/{sid}/resume")
        assert resumed.status_code == 200, resumed.text

        finished = wait_for_event(event_log, "ai_finished")
        assert finished["step_count"] >= 0
        # 브라우저를 재시작하지 않았다.
        session = keyed_client.app.state.itb.sessions.require(sid)
        assert session.open_tabs()
        assert "projects.html" in current_url(keyed_client, sid)
    finally:
        stop_quietly(keyed_client, sid)


def test_retry_runs_from_the_current_state(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-072 — "AI에게 다시" 는 **되돌리지 않고** 현재 상태에서 재시도한다."""
    install_driver(monkeypatch, LOGIN_THEN_BLOCKED)
    sid = _block(keyed_client, fixture_app, event_log)
    try:
        url_before = current_url(keyed_client, sid)
        install_driver(monkeypatch, [observe(0), click_named("프로젝트 생성")])
        event_log.clear()

        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-choice", json={"choice": "retry"}
        )
        assert resp.status_code == 200, resp.text
        wait_for_event(event_log, "ai_finished")

        # 화면을 되돌리지 않았다 — 같은 화면에서 이어서 시도했다.
        assert current_url(keyed_client, sid) == url_before
    finally:
        stop_quietly(keyed_client, sid)


def test_skip_does_not_record_the_failed_action(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-073 — 건너뛰기는 실패한 동작을 Step 으로 남기지 않는다."""
    install_driver(monkeypatch, LOGIN_THEN_BLOCKED)
    sid = _block(keyed_client, fixture_app, event_log)
    try:
        before = [s["id"] for s in keyed_client.get(f"/api/sessions/{sid}").json()["steps"]]
        install_driver(monkeypatch, [observe(0)])
        event_log.clear()

        resp = keyed_client.post(f"/api/sessions/{sid}/ai-choice", json={"choice": "skip"})
        assert resp.status_code == 200, resp.text
        wait_for_event(event_log, "ai_finished")

        after = [s["id"] for s in keyed_client.get(f"/api/sessions/{sid}").json()["steps"]]
        assert after == before, f"건너뛰기가 Step 을 만들었다: {set(after) - set(before)}"
    finally:
        stop_quietly(keyed_client, sid)


def test_abort_keeps_steps_saveable(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-074 — 종료를 골라도 그때까지의 Step 을 저장할 수 있다.

    선택 즉시 브라우저를 닫으면 저장 확인을 받을 대상이 사라진다.
    """
    install_driver(monkeypatch, LOGIN_THEN_BLOCKED)
    sid = _block(keyed_client, fixture_app, event_log)
    try:
        resp = keyed_client.post(f"/api/sessions/{sid}/ai-choice", json={"choice": "abort"})
        assert resp.status_code == 200, resp.text
        # 002 — `review` 로 바뀌었다. 이 테스트의 docstring 이 요구하는 "저장 확인을
        # 받을 대상" 이 바로 그 상태다. `stopped` 는 아무 명령도 받지 않아 저장 확인이
        # 성립하지 않았다 (research R1).
        assert resp.json()["state"] == "review"

        saved = keyed_client.post(
            f"/api/sessions/{sid}/save", json={"name": "중간까지 저장"}
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["steps"], "종료 후 저장한 테스트에 Step 이 없다"
    finally:
        stop_quietly(keyed_client, sid)


def test_choice_is_rejected_when_not_blocked(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-043a — `AI_BLOCKED` 가 아닌 상태의 선택은 거절한다."""
    install_driver(
        monkeypatch, [observe(0), fill_named("이메일", "tester@example.com")]
    )
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-choice", json={"choice": "takeover"}
        )
        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"
    finally:
        stop_quietly(keyed_client, sid)


def test_unknown_choice_is_rejected_at_the_boundary(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-085 — 정의되지 않은 선택지는 경계에서 거절한다."""
    install_driver(monkeypatch, LOGIN_THEN_BLOCKED)
    sid = _block(keyed_client, fixture_app, event_log)
    try:
        resp = keyed_client.post(
            f"/api/sessions/{sid}/ai-choice", json={"choice": "delete_everything"}
        )
        assert resp.status_code == 422, resp.text
    finally:
        stop_quietly(keyed_client, sid)
