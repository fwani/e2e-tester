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


async def test_a_schema_violating_reply_is_still_usable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**모델이 스키마를 지킨다고 믿지 않는다** (2026-09-29).

    스키마는 `items: [{"text": "…"}]` 를 요구하지만 모델은 `items: ["…"]` 를 주기도
    한다. 거기서 변환이 죽으면 사용자는 원문으로 진행할 기회조차 잃는다 — 정제는
    관문이 아니다 (FR-020).
    """

    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json=_tool_use_response(
                {
                    "items": ["로그인한다", "메뉴관리로 이동한다"],
                    "constraints": ["기존 데이터는 검증에 쓰지 않는다"],
                }
            ),
        )

    monkeypatch.setattr("itb.llm.client.create_client", lambda: _client(handler))

    result = await refine_mod.refine_instruction("로그인한다")

    assert result.refined is True
    assert result.plan is not None
    assert [i.text for i in result.plan.items] == ["로그인한다", "메뉴관리로 이동한다"]
    assert result.plan.constraints[0].text == "기존 데이터는 검증에 쓰지 않는다"


async def test_a_failure_says_what_went_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    """**실패 사유에 무엇이 잘못됐는지가 있다** (2026-09-29 사용자 보고).

    초안은 `type(exc).__name__` 만 남겼고, 사용자는 「정제하지 못했습니다: TypeError」를
    두 번 받았다. 그 문장으로는 고칠 수도, 물어볼 수도 없다 — **진단할 수 없는 오류
    메시지는 오류를 숨기는 것과 같다.**
    """

    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"쓸 수 없는": "응답"})

    monkeypatch.setattr("itb.llm.client.create_client", lambda: _client(handler))

    result = await refine_mod.refine_instruction("로그인한다")

    assert result.refined is False
    note = result.notes[0]
    assert "정제하지 못했습니다" in note
    assert "원문 그대로 진행할 수 있습니다" in note, "무엇을 할 수 있는지 말해야 한다"
    # 타입 이름만으로는 진단할 수 없다 — 괄호 안에 예외 종류가 있어야 한다.
    assert "(" in note and ")" in note


async def test_missing_credentials_says_what_to_do(monkeypatch: pytest.MonkeyPatch) -> None:
    """**자격 증명이 없으면 무엇을 하면 되는지 말한다** (2026-09-29 사용자 보고).

    SDK 는 자격 증명이 하나도 없어도 클라이언트를 **만든다** — 실패는 첫 요청에서 난다.
    그때 나오던 것은 SDK 내부의 영문 메시지였고, 사용자는 이것을 받았다:

        지시문을 정제하지 못했습니다 (TypeError): "Could not resolve authentication
        method. Expected one of api_key, auth_token, or credentials to be set…"

    무엇을 하면 되는지가 없다. 같은 판정이 `itb.api.routes.ai` 에 있었지만 그쪽은
    **화면이 미리 물을 때만** 쓰였고 실제 호출 경로는 지나지 않았다.

    판정을 `create_client` 로 옮겼으므로 **정제도 작성 에이전트도 같은 말을 한다.**
    """
    from itb.llm.client import NO_CREDENTIALS

    # 자격 증명이 하나도 없는 클라이언트 — SDK 가 실제로 만드는 그 상태다.
    class _NoCreds:
        api_key = None
        auth_token = None
        credentials = None

    monkeypatch.setattr("anthropic.AsyncAnthropic", lambda *a, **k: _NoCreds())

    result = await refine_mod.refine_instruction("로그인한다")

    assert result.refined is False
    assert result.notes == [NO_CREDENTIALS]
    assert "ANTHROPIC_API_KEY" in result.notes[0], "무엇을 하면 되는지가 있어야 한다"


async def test_the_driver_choice_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """**`ITB_AI_DRIVER` 가 정제에도 적용된다** (2026-09-29 사용자 보고).

    드라이버 선택은 「무엇으로 모델을 부르는가」이고, 모델을 부르는 **모든 자리**에
    적용되어야 한다. 초안은 정제만 Messages API 를 직접 불러서, 개발용 드라이버로 띄운
    서버에서 작성은 되는데 정제만 자격 증명을 요구했다.
    """
    from itb.authoring.agent import DRIVER_CLAUDE_CODE, DRIVER_ENV

    called: list[str] = []

    async def fake_dev(instruction: str) -> dict[str, Any]:
        called.append("claude-code")
        return {"items": [{"text": instruction}]}

    async def fake_api(instruction: str, _config: Any) -> dict[str, Any]:
        called.append("messages-api")
        return {"items": [{"text": instruction}]}

    monkeypatch.setattr(refine_mod, "_submit_via_claude_code", fake_dev)
    monkeypatch.setattr(refine_mod, "_submit_via_messages_api", fake_api)

    monkeypatch.setenv(DRIVER_ENV, DRIVER_CLAUDE_CODE)
    await refine_mod.refine_instruction("로그인한다")
    assert called == ["claude-code"], "개발용 드라이버를 골랐는데 기본 경로로 갔다"

    called.clear()
    monkeypatch.delenv(DRIVER_ENV, raising=False)
    await refine_mod.refine_instruction("로그인한다")
    assert called == ["messages-api"], "기본은 Messages API 여야 한다"

    called.clear()
    monkeypatch.setenv(DRIVER_ENV, "오타-난-값")
    await refine_mod.refine_instruction("로그인한다")
    assert called == ["messages-api"], (
        "인식하지 못한 값은 기본으로 떨어져야 한다 — 오타가 조용히 개발용 경로를 켜면 "
        "개발자는 자기가 무엇을 보고 있는지 모른다 (`select_driver` 와 같은 판단)."
    )
