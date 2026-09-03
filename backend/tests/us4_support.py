"""US4~US6 (AI 작성) 테스트 공용 도구.

**자격 증명 없이 AI 경로 전체를 검증한다.** 갈아 끼우는 지점은 `AuthoringAgent` 의
`driver` 하나이며, 그 자리에 **대본대로 도구를 부르는 가짜 모델**을 넣는다.

가짜 모델이 부르는 것은 실제 도구 객체다(`tool.call(...)`). 그래서 검증되는 것이 도구
표면·후보 수집·Step 실행·컴파일·이벤트 발행까지 실제 경로 전부이고, 대체되는 것은
"다음에 무엇을 할지 정하는 판단" 뿐이다 — 그 판단만이 언어모델의 몫이다.

`itb.authoring.agent._sdk_driver` 를 monkeypatch 하는 이유는, API 라우터가 에이전트를
직접 조립하기 때문이다. 라우터에 테스트용 인자를 뚫으면 그 인자가 제품 코드에 남는다.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient

TERMINAL_STATES = frozenset({"completed", "failed", "stopped", "lost"})

# ─── 대본 ───────────────────────────────────────────────────────────────────

Action = Callable[[dict[str, Any]], tuple[str, dict[str, Any]] | None]
"""마지막 관찰 결과를 받아 (도구 이름, 인자) 를 돌려준다. None 이면 아무것도 하지 않는다."""


def observe(tab: int = 0) -> Action:
    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return ("observe_page", {"tab": tab})

    return action


def _pick(state: dict[str, Any], predicate: Callable[[dict[str, Any]], bool]) -> str:
    """관찰 결과에서 요소 참조를 고른다. 없으면 테스트를 명확한 사유로 실패시킨다."""
    for element in state.get("elements") or []:
        if predicate(element):
            return str(element["element_ref"])
    names = [(e.get("tag"), e.get("name")) for e in state.get("elements") or []]
    pytest.fail(f"관찰 결과에서 대상 요소를 찾지 못했다. 관찰된 요소: {names}")
    raise AssertionError  # pragma: no cover


def click_named(name: str) -> Action:
    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        ref = _pick(state, lambda e: (e.get("name") or "") == name)
        return ("click", {"element_ref": ref})

    return action


def fill_named(name: str, value: str) -> Action:
    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        ref = _pick(state, lambda e: (e.get("name") or "") == name)
        return ("fill", {"element_ref": ref, "value": value})

    return action


def fill_password(value: str) -> Action:
    """비밀번호 유형 필드에 값을 넣는다. 민감 값 처리 경로를 지난다 (FR-082a)."""

    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        ref = _pick(state, lambda e: e.get("type") == "password")
        return ("fill", {"element_ref": ref, "value": value})

    return action


def select_named(name: str, value: str) -> Action:
    def action(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        ref = _pick(state, lambda e: (e.get("name") or "") == name)
        return ("select", {"element_ref": ref, "value": value})

    return action


def assert_url_contains(value: str) -> Action:
    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return (
            "assert_condition",
            {"kind": "url", "value": value, "match": "contains"},
        )

    return action


def click_missing() -> Action:
    """존재하지 않는 참조로 클릭한다. 도구 실패 경로를 만든다."""

    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return ("click", {"element_ref": "e-does-not-exist"})

    return action


def report_blocked(reason: str = "삭제 메뉴를 찾을 수 없습니다.") -> Action:
    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return ("report_blocked", {"reason": reason})

    return action


# ─── 가짜 모델 ──────────────────────────────────────────────────────────────


class _FakeMessage:
    """모델 응답 한 건. `stop_reason` 과 `content` 만 흉내 낸다."""

    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.stop_reason = stop_reason
        self.content = [_FakeText(text)]


class _FakeText:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


def scripted_driver(
    script: Sequence[Action], stop_reason: str = "end_turn"
) -> Callable[..., Any]:
    """대본대로 도구를 부르는 가짜 모델.

    한 동작마다 메시지 하나를 낸다 — 실제 tool runner 도 턴마다 메시지를 내므로, 에이전트
    루프가 **매 턴 상한·실패 선언을 확인하는지**를 이 구조가 검증한다.
    """

    def driver(tools: list[Any], _messages: list[Any], _config: Any) -> Any:
        by_name = {tool.name: tool for tool in tools}

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
                yield _FakeMessage(f"{name} 을 수행했습니다.", stop_reason)
            yield _FakeMessage("지시를 끝냈습니다.", stop_reason)

        return run()

    return driver


def install_driver(
    monkeypatch: pytest.MonkeyPatch, script: Sequence[Action], stop_reason: str = "end_turn"
) -> None:
    """라우터가 조립하는 에이전트에 가짜 모델을 끼운다."""
    from itb.authoring import agent as agent_mod

    monkeypatch.setattr(agent_mod, "_sdk_driver", scripted_driver(script, stop_reason))


def failing_driver(exc: Exception) -> Callable[..., Any]:
    """호출 자체가 실패하는 모델. 자격 증명 오류·거부를 흉내 낸다 (FR-067)."""

    def driver(_tools: list[Any], _messages: list[Any], _config: Any) -> Any:
        async def run() -> Any:
            raise exc
            yield  # pragma: no cover - 도달하지 않는다

        return run()

    return driver


# ─── 대기 ───────────────────────────────────────────────────────────────────


def wait_for_event(
    events: list[tuple[str, dict]], event_type: str, timeout_s: float = 60.0
) -> dict[str, Any]:
    """특정 이벤트가 도착할 때까지 기다린다.

    폴링 대상이 세션 상태가 아니라 **이벤트**인 이유는, AI 경로의 종료가 상태 전이 없이도
    일어나기 때문이다 — `ai_error` 는 세션을 유지한다 (FR-067).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for kind, payload in events:
            if kind == event_type:
                return dict(payload)
        time.sleep(0.02)
    kinds = [k for k, _ in events]
    pytest.fail(f"{timeout_s}초 안에 {event_type} 이벤트가 오지 않았다. 받은 이벤트: {kinds}")
    raise AssertionError  # pragma: no cover


def start_ai_session(client: TestClient, fixture_app: str, instruction: str) -> str:
    created = client.post(
        "/api/sessions",
        json={
            "mode": "ai",
            "start_url": f"{fixture_app}/login.html",
            "ai_instruction": instruction,
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["session_id"])
