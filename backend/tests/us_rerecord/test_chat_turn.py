"""US1 — 테스트를 아는 AI 와 대화한다. 016 FR-007·FR-009 (T023).

이 파일이 확인하는 것은 **대화가 성립하는가**다. Step 을 만들지 않는 질문만 던지므로
구간 교체(US2)와 독립적으로 판정된다 — 그것이 US1 을 따로 둔 이유다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import record_login, stop_quietly
from tests.us4_support import install_driver
from tests.us_rerecord.support import open_rerecord, say, step_ids, turns

pytestmark = pytest.mark.browser


def test_a_chat_turn_goes_paused_to_running_and_back(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """한 차례가 `PAUSED → AI_RUNNING → PAUSED` 를 지난다 (research R4).

    돌아오는 것이 요점이다. 돌아오지 않으면 사용자는 확정·버리기·손 편집을 할 수 없다 —
    그 셋이 전부 `paused` 국면의 조작이다.
    """
    install_driver(monkeypatch, [])  # 도구를 부르지 않는다 — 말만 한다
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        before = step_ids(keyed_client, sid)
        view = say(keyed_client, sid, "이 테스트가 뭘 하는지 요약해 줘")

        assert view["state"] == "paused", "턴이 끝나면 일시정지로 돌아와야 한다"
        assert step_ids(keyed_client, sid) == before, (
            "Step 을 만들지 않는 질문인데 목록이 바뀌었다"
        )
    finally:
        stop_quietly(keyed_client, sid)


def test_the_history_keeps_both_sides_in_order(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """사용자의 말과 AI 의 답이 **순서대로** 이력에 붙는다 (FR-009).

    새로 고침·재접속 뒤에도 대화가 살아 있어야 한다 — 그것이 이력을 서버에 두는 이유다.
    """
    install_driver(monkeypatch, [])
    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        say(keyed_client, sid, "첫 번째 질문")
        say(keyed_client, sid, "두 번째 질문")

        got = turns(keyed_client, sid)
        roles = [t["role"] for t in got]
        assert roles[0] == "user"
        assert "첫 번째 질문" == got[0]["text"]
        assert roles.count("user") == 2
        assert "assistant" in roles, "AI 의 답이 이력에 없다"

        texts = [t["text"] for t in got if t["role"] == "user"]
        assert texts == ["첫 번째 질문", "두 번째 질문"], "순서가 어긋났다"
    finally:
        stop_quietly(keyed_client, sid)


def test_the_agent_is_told_what_the_test_contains(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """에이전트가 받는 메시지에 **지금 정의**가 실려 있다 (FR-001·FR-003).

    이것이 US1 의 전부다. 실려 있지 않으면 "3번부터 다시" 가 원리적으로 성립하지 않는다.

    모델의 답을 판정하지 않는 이유: 가짜 드라이버는 대본대로만 말한다. 확인할 수 있는
    것은 **무엇이 모델에게 갔는가**이고, 그것이 이 기능이 책임지는 부분이다.
    """
    seen: list[str] = []

    def capturing_driver(_tools: list[object], messages: list[dict], _config: object):
        for m in messages:
            if m.get("role") == "user":
                seen.append(str(m.get("content", "")))

        async def run():
            yield _Reply("확인했습니다.")

        return run()

    from itb.authoring import agent as agent_mod

    monkeypatch.setattr(agent_mod, "_sdk_driver", capturing_driver)

    test_id = record_login(keyed_client, fixture_app)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        say(keyed_client, sid, "요약해 줘")

        assert seen, "모델에게 아무 메시지도 가지 않았다"
        sent = seen[-1]
        assert "[지금 테스트]" in sent, f"정의 요약이 실리지 않았다: {sent[:200]}"
        for sid_ in saved:
            assert sid_ in sent, f"Step {sid_} 이 요약에 없다"
        assert "◀ 교체 구간" in sent, "교체 구간 표시가 없다 (FR-004)"
        assert "요약해 줘" in sent, "사용자의 말이 실리지 않았다"
    finally:
        stop_quietly(keyed_client, sid)


def test_no_sensitive_value_reaches_the_model(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """녹화된 비밀번호가 **모델에게 가지 않는다** (FR-002 · SC-008).

    `record_login` 은 비밀번호 칸을 채운다. 그 값이 변수 참조로 저장되는 것은 기존
    보장이고, 여기서 보는 것은 **요약 경로**가 그 보장을 깨지 않는가다.
    """
    secret = "chat-must-not-see-this-9f3"
    seen: list[str] = []

    def capturing_driver(_tools: list[object], messages: list[dict], _config: object):
        seen.extend(str(m.get("content", "")) for m in messages)

        async def run():
            yield _Reply("확인했습니다.")

        return run()

    from itb.authoring import agent as agent_mod

    monkeypatch.setattr(agent_mod, "_sdk_driver", capturing_driver)

    test_id = record_login(keyed_client, fixture_app, password=secret)
    saved = [s["id"] for s in keyed_client.get(f"/api/tests/{test_id}").json()["steps"]]

    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        say(keyed_client, sid, "비밀번호 칸에 뭐가 들어가냐")
        blob = "\n".join(seen)
        assert secret not in blob, "녹화된 비밀번호가 모델에게 갔다 — SC-008 위반"
    finally:
        stop_quietly(keyed_client, sid)


class _Reply:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.stop_reason = "end_turn"


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text
