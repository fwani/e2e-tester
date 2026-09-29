"""정제가 **실제 SDK 경로를 지난다** (025 사용자 보고 2026-09-29).

## 이 파일이 존재하는 이유

사용자가 정제를 돌렸고 이것을 받았다.

    지시문을 정제하지 못했습니다: TypeError

원인은 `beta_tool`(동기)로 만든 도구를 `AsyncAnthropic` 의 tool_runner 에 넘긴 것이었다.
요청 본문을 만드는 단계에서 터진다.

    TypeError: Object of type BetaFunctionTool is not JSON serializable

**그리고 검증은 전부 통과하고 있었다.** `test_instruction_refine.py` 가
`refine_instruction` 자체를 갈아 끼우므로, SDK 를 지나는 경로를 한 번도 밟지 않았다.

이것은 025 의 research R1 이 지적한 것과 **같은 함정이다.** 그쪽은
「`us4_support` 의 가짜 드라이버가 SDK 의 messages 처리를 대체해 이력 유실을 가렸다」
였고, 이쪽은 「가짜 `refine_instruction` 이 SDK 의 도구 직렬화를 대체해 타입 오류를
가렸다」다. 같은 해법을 쓴다 — **실제 SDK 를 지나되 네트워크만 막는다.**

## 자격 증명이 필요 없다

`httpx2.MockTransport` 로 전송 계층만 갈아 끼운다. 요청 본문을 만드는 것도, 응답을
해석하는 것도, 도구를 부르는 것도 전부 실제 SDK 코드가 한다.
"""

from __future__ import annotations

import json
from typing import Any

import httpx2
import pytest
from anthropic import AsyncAnthropic

from itb.authoring import refine as refine_mod


def _client(handler: Any) -> AsyncAnthropic:
    return AsyncAnthropic(
        api_key="test-only-not-a-real-key",
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )


def _tool_use_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5",
        "content": [
            {"type": "tool_use", "id": "tu_1", "name": refine_mod.SUBMIT_TOOL, "input": payload}
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


async def test_the_request_body_is_serializable(monkeypatch: pytest.MonkeyPatch) -> None:
    """**요청 본문이 만들어진다** — 이것이 깨졌던 자리다.

    도구를 잘못된 데코레이터로 만들면 여기서 `TypeError` 가 난다. 사용자는 그것을
    「지시문을 정제하지 못했습니다: TypeError」로 봤다.
    """
    captured: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured["body"] = json.loads(request.content)
        return httpx2.Response(200, json=_tool_use_response({"items": [{"text": "로그인한다"}]}))

    monkeypatch.setattr("itb.llm.client.create_client", lambda: _client(handler))

    result = await refine_mod.refine_instruction("관리자로 로그인한다")

    assert result.refined is True, (
        f"정제가 실패했다: {result.notes}. SDK 경로에서 터졌을 수 있다."
    )
    assert [t["name"] for t in captured["body"]["tools"]] == [refine_mod.SUBMIT_TOOL]


async def test_the_model_reply_becomes_a_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    """모델이 제출한 것이 계획이 된다 — 변환 경로 전체."""

    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json=_tool_use_response(
                {
                    "items": [{"text": "로그인한다"}, {"text": "메뉴를 등록한다"}],
                    "constraints": [
                        {"text": "기존 데이터는 검증에 쓰지 않는다", "scope": "global"},
                        {
                            "text": "주소는 https://a.example 를 쓴다",
                            "scope": "item",
                            "item_index": 2,
                        },
                    ],
                    "notes": ["자격 증명 1건을 바꿨습니다."],
                }
            ),
        )

    monkeypatch.setattr("itb.llm.client.create_client", lambda: _client(handler))

    result = await refine_mod.refine_instruction("로그인하고 메뉴를 등록한다")

    assert result.plan is not None
    assert [i.text for i in result.plan.items] == ["로그인한다", "메뉴를 등록한다"]
    assert result.plan.constraints[1].item_id == result.plan.items[1].id
    assert result.notes


async def test_a_model_that_does_not_call_the_tool_is_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """도구를 부르지 않으면 **정제 실패**다 (FR-020).

    실패해도 예외가 아니라 결과다 — 원문으로 진행하는 것이 정상 경로의 하나다.
    """

    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5",
                "content": [{"type": "text", "text": "무엇을 도와드릴까요?"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    monkeypatch.setattr("itb.llm.client.create_client", lambda: _client(handler))

    result = await refine_mod.refine_instruction("로그인한다")

    assert result.refined is False
    assert result.plan is None
    assert result.notes


async def test_a_transport_error_is_also_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """호출 자체가 실패해도 같은 자리로 수렴한다 (FR-020)."""

    def handler(_request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("끊겼다")

    monkeypatch.setattr("itb.llm.client.create_client", lambda: _client(handler))

    result = await refine_mod.refine_instruction("로그인한다")

    assert result.refined is False
    assert result.notes
