"""재개가 이어지는가 — 지난 턴이 다음 턴에 남는다 (025 US1 · T008).

## 이 파일이 확인하는 것

제품은 「막힌 자리에서 이어서 하라」고 말해 왔다. **그 자리가 모델에게 남아 있지
않았다.** SDK 의 tool runner 가 넘겨받은 `messages` 를 복사해 자기 안에서만 늘리므로,
한 턴의 관찰·동작·막힘·답이 턴이 끝나는 순간 버려졌다 (research R1).

여기서 확인하는 것은 **모델이 두 번째 턴에 실제로 무엇을 받는가**다. 그래서 가짜 모델을
「대본대로 도구를 부르는 것」이 아니라 **받은 이력을 기록하는 것**으로 둔다 — 대본은
무엇을 할지를 정하고, 이 파일이 보는 것은 그 앞에 무엇이 실려 왔는가다.

## 왜 단위 검증으로 대신하지 않는가

`AuthoringAgent` 만 떼어 내면 「이력에 어시스턴트 차례가 들어간다」는 확인할 수 있지만,
**그 내용이 실제 도구 호출에서 나온 것인지**는 확인하지 못한다. 저널을 채우는 것은
도구이고, 도구는 실제 브라우저를 지난다. 그 배선이 끊겨도 단위 검증은 통과한다.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly
from us4_support import (
    fill_named,
    observe,
    report_blocked,
    start_ai_session,
    wait_for_event,
)


class _HistorySpy:
    """드라이버가 받은 이력을 턴마다 기록한다.

    `us4_support.scripted_driver` 를 감싸지 않고 따로 두는 이유는 목적이 다르기
    때문이다 — 그쪽은 「무엇을 할지」를 대본으로 주고, 이쪽은 「무엇을 받았는지」를 본다.
    """

    def __init__(self, script: list[Any]) -> None:
        self.script = script
        self.turns: list[list[dict[str, Any]]] = []

    def __call__(self, tools: list[Any], messages: list[dict[str, Any]], _config: Any):
        # **사본을 뜬다.** 리스트는 다음 턴에 계속 자라므로, 참조를 들고 있으면 모든
        # 턴이 마지막 상태를 가리킨다.
        self.turns.append([dict(m) for m in messages])
        by_name = {tool.name: tool for tool in tools}
        script = self.script

        async def run() -> Any:
            state: dict[str, Any] = {}
            for action in script:
                planned = action(state)
                if planned is None:
                    continue
                name, kwargs = planned
                tool = by_name.get(name)
                if tool is None:  # pragma: no cover - 대본이 표면을 벗어났다
                    pytest.fail(f"도구 표면에 없는 도구를 불렀다: {name}")
                result = await tool.call(kwargs)
                if name == "observe_page" and isinstance(result, dict):
                    state = result
                yield _Message(f"{name} 을 수행했습니다.")
            yield _Message("이번 차례를 끝냈습니다.")

        return run()


def _wait_for_turns(spy: _HistorySpy, count: int, timeout_s: float = 60.0) -> None:
    """`chat` 은 태스크로 띄운다 — 응답 200 은 시작만 뜻한다.

    이벤트가 아니라 **드라이버 호출 횟수**를 기다리는 이유는, 이 파일이 보는 것이
    「모델이 무엇을 받았는가」이기 때문이다. 이벤트는 그 뒤에 온다.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if len(spy.turns) >= count:
            return
        time.sleep(0.02)
    pytest.fail(f"{timeout_s}초 안에 {count}번째 턴이 시작되지 않았다 (지금 {len(spy.turns)})")


class _Message:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.stop_reason = "end_turn"


class _Block:
    def __init__(self, text: str) -> None:
        self.text = text
        self.type = "text"


def test_next_turn_sees_what_the_last_turn_did(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**두 번째 턴의 이력에 첫 턴의 수행 기록이 있다** (FR-001·FR-007).

    이것이 없으면 「이어서 하라」는 말이 근거를 갖지 못한다.
    """
    from itb.authoring import agent as agent_mod

    spy = _HistorySpy(
        [
            observe(0),
            fill_named("이메일", "tester@example.com"),
            report_blocked("비밀번호를 모릅니다.", question="어떤 비밀번호를 쓸까요?"),
        ]
    )
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = start_ai_session(keyed_client, fixture_app, "로그인한다")
    wait_for_event(event_log, "ai_blocked")

    # 두 번째 턴 — 사람이 답을 주어 재개한다 (spec US1 시나리오 1)
    sent = keyed_client.post(
        f"/api/sessions/{session_id}/ai-choice",
        json={"choice": "answer", "answer": "테스트 계정 비밀번호를 쓰세요"},
    )
    assert sent.status_code == 200, sent.text
    _wait_for_turns(spy, 2)
    second = spy.turns[1]

    roles = [m["role"] for m in second]
    assert "assistant" in roles, (
        "두 번째 턴의 이력에 어시스턴트 차례가 없다. 한 턴의 기록이 그 턴과 함께 "
        "버려지고 있다 — 025 FR-007 이 고치려는 바로 그 상태다."
    )

    record = next(str(m["content"]) for m in second if m["role"] == "assistant")
    assert "[내가 한 일]" in record
    assert "화면 관찰" in record, "관찰했다는 사실이 남아야 한다 (FR-004)"
    assert "이메일" in record, "무엇을 조작했는지가 남아야 한다"
    assert "막힘" in record, "무엇을 하다 막혔는지가 남아야 한다 (FR-002)"
    assert "어떤 비밀번호를 쓸까요?" in record, (
        "물음이 남아야 한다 — 다음 턴이 그 물음에 대한 답으로 시작한다"
    )

    stop_quietly(keyed_client, session_id)


def test_record_does_not_carry_stale_references_or_values(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """수행 기록에 **낡을 것과 새면 안 될 것**이 실리지 않는다 (FR-003).

    - 요소 참조(`e17`)는 다음 턴에 낡는다. 낡은 참조를 본 모델이 그것을 집어 들면
      거절되지만 예산을 깎는다.
    - 입력값은 016 정의 요약과 같은 규칙으로 실리지 않는다.
    - 화면 요소 목록·본문 텍스트는 이 기능이 없애려는 바로 그 크기다.
    """
    from itb.authoring import agent as agent_mod

    secret_ish = "tester@example.com"
    spy = _HistorySpy(
        [
            observe(0),
            fill_named("이메일", secret_ish),
            report_blocked("이어갈 수 없습니다."),
        ]
    )
    monkeypatch.setattr(agent_mod, "_sdk_driver", spy)

    session_id = start_ai_session(keyed_client, fixture_app, "로그인한다")
    wait_for_event(event_log, "ai_blocked")
    keyed_client.post(
        f"/api/sessions/{session_id}/ai-choice",
        json={"choice": "answer", "answer": "계속하세요"},
    )
    _wait_for_turns(spy, 2)
    record = next(
        str(m["content"]) for m in spy.turns[1] if m["role"] == "assistant"
    )

    assert secret_ish not in record, "조작에 넘긴 값이 수행 기록에 실렸다"
    assert "element_ref" not in record, "요소 참조가 수행 기록에 실렸다"
    assert '"css"' not in record, "화면 요소 목록이 수행 기록에 실렸다"
    assert len(record.encode()) < 4000, (
        "수행 기록이 너무 크다. 화면 원문이 섞여 들어갔을 수 있다 — 이 기능은 "
        "그 크기를 없애려는 것이다."
    )

    stop_quietly(keyed_client, session_id)
