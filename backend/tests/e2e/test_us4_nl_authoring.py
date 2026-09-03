"""US4 종단 테스트 — quickstart §6. 헌법 원칙 II (T109).

**7단계가 원칙 II 의 가장 직관적인 증거다**: 네트워크를 끊고 저장된 테스트를 재실행해도
통과한다. 실행이 언어모델에 의존하지 않는다는 사실을 사용자가 눈으로 확인하는 방법이다.

네트워크 차단은 **루프백을 제외한 모든 연결을 거절**하는 방식으로 구현한다. 스파이로
"부르지 않았다" 를 세는 것(T071·T118)과 **다른 각도**다 — 여기서는 부르려 해도 못 하는
환경에서 실행이 끝까지 간다는 것을 본다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from us2_support import replay, result_of, stop_quietly
from us4_support import (
    assert_url_contains,
    click_named,
    fill_named,
    fill_password,
    install_driver,
    observe,
    report_blocked,
    start_ai_session,
    wait_for_event,
)

AUTHORING_SCRIPT = [
    observe(0),
    fill_named("이메일", "tester@example.com"),
    fill_password("ai-authored-not-a-real-secret"),
    observe(0),
    click_named("로그인"),
    observe(0),
    assert_url_contains("projects.html"),
]


def _sever_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """외부 네트워크를 끊는다. **루프백은 남긴다.**

    끊어야 할 것은 언어모델 API 로 나가는 경로뿐이다. 전부 막으면 픽스처 앱(127.0.0.1)과
    브라우저 제어까지 끊겨 무엇이 실패했는지 알 수 없게 되고, 테스트가 검증하려는 것과
    다른 이유로 실패한다.

    HTTP 계층(`httpx2`)을 막는 방법은 쓸 수 없다 — 테스트 클라이언트 자신이 그 계층을
    쓴다. 그래서 이름 해석과 연결을 주소 기준으로 막는다: 루프백이 아니면 거절한다.
    """
    import socket

    allowed_hosts = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}  # noqa: S104
    original_getaddrinfo = socket.getaddrinfo
    original_connect = socket.socket.connect

    def guarded_getaddrinfo(host, *args, **kwargs):  # noqa: ANN001, ANN202
        if str(host) not in allowed_hosts:
            msg = f"네트워크가 차단된 환경입니다: {host}"
            raise OSError(msg)
        return original_getaddrinfo(host, *args, **kwargs)

    def guarded_connect(self, address, *args, **kwargs):  # noqa: ANN001, ANN202
        host = address[0] if isinstance(address, tuple) else address
        if str(host) not in allowed_hosts:
            msg = f"네트워크가 차단된 환경입니다: {host}"
            raise OSError(msg)
        return original_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


def test_quickstart_section6_ai_authoring_end_to_end(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§6 1~7단계."""
    instruction = "로그인해서 프로젝트 화면으로 이동하고, 주소가 맞는지 확인해"
    install_driver(monkeypatch, AUTHORING_SCRIPT)

    # 1단계 — AI 세션이 열리고 `AI 수행 중` 상태가 된다
    sid = start_ai_session(keyed_client, fixture_app, instruction)
    try:
        # 2단계 — 성공한 동작만 Step 으로 쌓인다
        finished = wait_for_event(event_log, "ai_finished")
        assert finished["step_count"] >= 3, finished

        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert all(s["author"] == "ai" for s in view["steps"])

        # 4단계 — `authoring_mode: ai` 로 저장된다
        saved = keyed_client.post(
            f"/api/sessions/{sid}/save", json={"name": "AI 로그인 확인"}
        )
        assert saved.status_code == 200, saved.text
        test_id = saved.json()["id"]
        assert saved.json()["authoring_mode"] == "ai"
    finally:
        stop_quietly(keyed_client, sid)

    # 5단계 — 저장 파일에 지시문 원문이 있고 steps 는 결정적 Step 이다
    definition = keyed_client.get(f"/api/tests/{test_id}").json()
    assert definition["ai_instruction"] == instruction
    assert definition["steps"]

    # 목록에 `AI` 배지 근거가 실린다 (FR-002a)
    listing = keyed_client.get("/api/tests").json()
    row = next(t for t in listing["tests"] if t["id"] == test_id)
    assert row["authoring_mode"] == "ai"

    # 6단계 — 재실행이 통과한다
    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", view
    assert result_of(keyed_client, test_id)["outcome"] == "pass"

    # 7단계 — ★ 네트워크를 끊고 재실행해도 통과한다
    _sever_network(monkeypatch)
    view = replay(keyed_client, test_id)
    assert view["state"] == "completed", (
        f"네트워크 없이 재실행이 실패했다 — 실행이 언어모델에 의존한다는 뜻이다: {view}"
    )
    assert result_of(keyed_client, test_id)["outcome"] == "pass"


def test_quickstart_section6_step8_impossible_instruction_stops_within_limits(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§6 8단계 — 수행 불가능한 지시는 상한 안에서 중단하고 무엇을 못 했는지 알린다 (FR-066).

    **세션은 유지된다.** 사용자가 이어받거나 저장할 수 있어야 한다 (FR-069).
    """
    install_driver(
        monkeypatch,
        [observe(0), report_blocked("화면에 '우주선 발사' 버튼이 없습니다.")],
    )
    sid = start_ai_session(keyed_client, fixture_app, "우주선을 발사해")
    try:
        blocked = wait_for_event(event_log, "ai_blocked")
        assert blocked["choices"] == ["takeover", "retry", "skip", "abort"]
        assert "우주선" in (blocked["reason"] or "")

        view = keyed_client.get(f"/api/sessions/{sid}").json()
        assert view["state"] == "ai_blocked"
        session = keyed_client.app.state.itb.sessions.require(sid)
        assert session.open_tabs(), "막힘 상태에서 브라우저가 닫혔다 — FR-069 위반"
    finally:
        stop_quietly(keyed_client, sid)


def test_quickstart_section6_step9_pause_during_ai_allows_editing(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§6 9단계 — AI 수행 중 일시정지하면 US3 와 동일하게 편집할 수 있다 (FR-065)."""
    install_driver(monkeypatch, AUTHORING_SCRIPT)
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        wait_for_event(event_log, "ai_finished")
        view = keyed_client.get(f"/api/sessions/{sid}").json()
        # AI 가 멈춘 뒤 세션은 편집 가능한 상태로 유지된다.
        assert view["state"] == "paused"
        assert "edit_steps" in view["allowed_commands"]

        target = view["steps"][0]["id"]
        patched = keyed_client.patch(
            f"/api/sessions/{sid}/steps/{target}", json={"label": "사람이 고친 이름"}
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["steps"][0]["label"] == "사람이 고친 이름"
    finally:
        stop_quietly(keyed_client, sid)


def test_quickstart_section6_step10_bad_credentials_preserve_steps(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§6 10단계 — 자격 증명이 잘못되면 실패를 알리고 그때까지의 Step 을 보존한다 (FR-067)."""
    from us4_support import failing_driver

    from itb.authoring import agent as agent_mod
    from itb.llm.client import LlmUnavailableError

    monkeypatch.setattr(
        agent_mod,
        "_sdk_driver",
        failing_driver(LlmUnavailableError("언어모델 자격 증명을 찾을 수 없습니다.")),
    )
    sid = start_ai_session(keyed_client, fixture_app, "로그인해")
    try:
        error = wait_for_event(event_log, "ai_error")
        assert "자격 증명" in (error["reason"] or "")

        view = keyed_client.get(f"/api/sessions/{sid}").json()
        # 세션이 살아 있고 편집·저장이 가능하다.
        assert view["state"] == "paused"
        session = keyed_client.app.state.itb.sessions.require(sid)
        assert session.open_tabs(), "자격 증명 실패가 브라우저를 닫았다 — FR-067 위반"
    finally:
        stop_quietly(keyed_client, sid)
