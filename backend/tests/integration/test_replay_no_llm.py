"""T071 — 재실행 경로에 언어모델이 없다 (SC-006, 헌법 원칙 II 동적 검증).

임포트 경계(import-linter)는 **정적** 보증이다. 이 파일은 **동적** 보증을 맡는다:
실제 재실행을 한 번 돌리는 동안 `anthropic` 클라이언트가 한 번도 만들어지지 않았는지 본다.

정적 검사만으로 충분해 보이지만 그렇지 않다. `importlib` 로 지연 임포트하거나 실행 경로가
API 계층을 우회해 언어모델에 닿는 경로는 임포트 계약이 잡지 못한다. 두 검사가 겹치더라도
서로 놓치는 곳이 다르다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, replay, result_of


def _spy_on_llm_clients(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """`anthropic` 클라이언트 생성마다 이름을 기록하는 스파이를 심는다."""
    import anthropic

    constructions: list[str] = []
    for class_name in ("Anthropic", "AsyncAnthropic"):
        cls = getattr(anthropic, class_name, None)
        if cls is None:  # pragma: no cover - SDK 구조가 바뀐 경우
            continue
        original = cls.__init__

        def spy(self, *args, _name=class_name, _original=original, **kwargs):  # noqa: ANN001, ANN202
            constructions.append(_name)
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(cls, "__init__", spy)
    assert constructions == []
    return constructions


@pytest.mark.usefixtures("fixture_app")
def test_replay_never_constructs_an_llm_client(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-006 — 재실행 중 언어모델 클라이언트 생성 0건."""
    constructions = _spy_on_llm_clients(monkeypatch)

    test_id = record_login(keyed_client, fixture_app)
    assert not constructions, "녹화 단계에서 이미 언어모델 클라이언트가 생성됐다"

    view = replay(keyed_client, test_id)

    assert view["state"] == "completed", f"재실행이 통과하지 않았다: {view['state']}"
    assert not constructions, (
        f"재실행 중 언어모델 클라이언트가 {len(constructions)}회 생성됐다 "
        f"({constructions}) — 헌법 원칙 II 위반"
    )
    assert result_of(keyed_client, test_id)["outcome"] == "pass"


@pytest.mark.usefixtures("fixture_app")
def test_replay_session_emits_no_ai_events(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """contracts/websocket.md — `replay` 세션에서 `ai_*` 이벤트가 관측되면 원칙 II 위반."""
    test_id = record_login(keyed_client, fixture_app)
    event_log.clear()  # 녹화 단계의 이벤트는 검사 대상이 아니다

    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", f"재실행이 통과하지 않았다: {view['state']}"

    ai_events = [name for name, _ in event_log if name.startswith("ai_")]
    assert not ai_events, f"replay 세션에서 AI 이벤트가 나왔다: {ai_events}"
    assert any(name == "step_finished" for name, _ in event_log), (
        f"실행 이벤트 자체가 없다 — 검증이 성립하지 않는다: "
        f"{sorted({n for n, _ in event_log})}"
    )


# ─── T118 — AI 로 만든 테스트의 재실행 (US4) ────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_ai_authored_test_replays_without_any_llm_call(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SC-006 — **AI 로 만든** 테스트의 재실행에서도 호출 0건 (T118).

    이것이 원칙 II 의 핵심 증거다. AI 가 작성한 테스트가 재실행에서도 언어모델을 부르지
    않아야, "작성에만 쓴다" 가 실제로 성립한다. 녹화로 만든 테스트만 검증하면 이 경로가
    비어 있는 채로 통과한다.
    """
    from us4_support import (
        click_named,
        fill_named,
        fill_password,
        install_driver,
        observe,
        start_ai_session,
        wait_for_event,
    )

    install_driver(
        monkeypatch,
        [
            observe(0),
            fill_named("이메일", "tester@example.com"),
            fill_password("ai-authored-not-a-real-secret"),
            observe(0),
            click_named("로그인"),
        ],
    )
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        saved = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "AI 작성"})
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
    finally:
        keyed_client.post(f"/api/sessions/{sid}/stop")

    # ★ 여기서부터 스파이를 심는다. 작성 단계는 언어모델을 쓰는 것이 정상이다.
    constructions = _spy_on_llm_clients(monkeypatch)
    event_log.clear()

    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", f"AI 로 만든 테스트가 재실행에서 실패했다: {view}"
    assert not constructions, (
        f"AI 로 만든 테스트의 재실행이 언어모델 클라이언트를 만들었다 ({constructions}) "
        "— 헌법 원칙 II 위반"
    )
    ai_events = [name for name, _ in event_log if name.startswith("ai_")]
    assert not ai_events, f"replay 세션에서 AI 이벤트가 나왔다: {ai_events}"
    assert result_of(keyed_client, test_id)["outcome"] == "pass"


# ─── T133 — 자연어로 추가한 Step 의 재실행 (US6) ───────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_nl_added_step_replays_without_any_llm_call(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-080 — 자연어로 추가한 Step 도 재실행에서 언어모델을 부르지 않는다 (T133).

    자연어는 **Step 을 만드는 데만** 쓰인다. 만들어진 Step 은 수동 Step 과 구조가 같고,
    실행기는 그것이 어떻게 만들어졌는지 알지 못한다 — 알 필요가 없고, 아는 코드가 생기면
    원칙 II 경계가 흐려진다.
    """
    from us2_support import start_replay, stop_quietly
    from us3_support import pause_after, record_login_then_two_menus
    from us4_support import click_named, install_driver, observe

    install_driver(monkeypatch, [observe(0), click_named("분석")])
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    sid = start_replay(keyed_client, test_id)
    try:
        pause_after(keyed_client, sid, finished_steps=3, events=event_log)
        added = keyed_client.post(
            f"/api/sessions/{sid}/ai-step", json={"instruction": "분석 메뉴를 눌러"}
        )
        assert added.status_code == 200, added.text
        assert added.json()["created"] is True, added.json()["message"]

        saved = keyed_client.post(
            f"/api/sessions/{sid}/save", json={"name": "자연어 Step 재실행"}
        )
        assert saved.status_code == 200, saved.text
        saved_id = saved.json()["id"]
    finally:
        stop_quietly(keyed_client, sid)

    # ★ 스파이는 여기서 심는다. 추가 단계는 언어모델을 쓰는 것이 정상이다.
    constructions = _spy_on_llm_clients(monkeypatch)
    event_log.clear()

    view = replay(keyed_client, saved_id)
    assert view["state"] == "completed", f"자연어 Step 포함 테스트가 실패했다: {view}"
    assert not constructions, (
        f"자연어로 추가한 Step 의 재실행이 언어모델 클라이언트를 만들었다 ({constructions})"
    )
    assert [name for name, _ in event_log if name.startswith("ai_")] == []
