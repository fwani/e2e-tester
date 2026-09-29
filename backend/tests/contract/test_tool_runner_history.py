"""SDK tool runner 의 이력 계약 (025 T004, research R1).

## 이 파일이 존재하는 이유

025 의 설계 전체가 **한 가지 사실** 위에 서 있다 — `client.beta.messages.tool_runner` 는
넘겨받은 `messages` 리스트를 **복사해서** 자기 안에서만 늘리고, 호출자가 준 리스트 객체는
한 번도 수정하지 않는다.

그래서 `AuthoringAgent.messages` 에는 `run`·`chat`·`resume_*` 이 넣은 **사용자 메시지만**
쌓인다. 한 턴의 관찰·동작·막힘·모델의 답은 그 턴이 끝나는 순간 버려진다. 이것이
「대화가 거듭될수록 컨텍스트가 사라진다」의 정체다.

## 왜 지금까지 아무도 몰랐는가

`tests/us4_support.py` 의 가짜 드라이버가 `_sdk_driver` 를 **통째로** 대체한다. 그것은
도구를 직접 부르고 결과를 자기 안에서 다루므로, SDK 의 messages 처리는 검증 범위 밖이었다.
AI 경로 전체를 자격 증명 없이 검증할 수 있게 해 준 그 설계가, 동시에 이 빈칸을 만들었다.

**그래서 이 파일은 가짜 드라이버를 쓰지 않는다.** 실제 SDK 클래스를 직접 만들어 그 동작을
확인한다. 자격 증명은 필요 없다 — 객체를 만들고 메서드를 부를 뿐 요청을 보내지 않는다.

## 이 계약이 깨지면 무엇이 일어나는가

SDK 가 언젠가 호출자의 리스트를 **직접 늘리도록** 바뀌면, 025 가 턴 끝에 덧붙이는 수행
기록이 SDK 가 이미 넣은 것과 **겹친다**. 같은 턴이 두 번 실린 이력을 모델이 읽게 된다.

반대로 지금 동작이 그대로인데 025 의 코드가 「SDK 가 알아서 쌓겠지」로 바뀌면 유실이
돌아온다. 어느 쪽이든 이 파일이 먼저 실패해야 한다.
"""

from __future__ import annotations

from typing import Any

def _runner(messages: list[dict[str, Any]]) -> Any:
    """요청을 보내지 않는 runner 를 만든다.

    `BaseToolRunner` 를 직접 만드는 이유는 자격 증명이다. `create_client()` 를 지나면
    키가 필요하고, 그러면 이 검증이 CI 에서 돌지 못한다 — 돌지 않는 검증은 없는 검증이다.
    """
    from anthropic.lib.tools._beta_runner import BaseToolRunner  # noqa: PLC0415

    return BaseToolRunner(
        params={"model": "test", "max_tokens": 8, "messages": messages},
        options={},
        tools=[],
    )


def test_runner_does_not_touch_caller_list() -> None:
    """**호출자가 넘긴 리스트는 수정되지 않는다** (research R1).

    025 의 전제다. 이것이 참이므로 `AuthoringAgent` 가 턴 끝에 직접 이력을 남겨야 한다.
    """
    caller_list: list[dict[str, Any]] = [{"role": "user", "content": "첫 지시"}]
    runner = _runner(caller_list)

    runner.append_messages({"role": "assistant", "content": "도구를 부른다"})
    runner.append_messages(
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "x", "content": "관찰 결과"}
            ],
        }
    )

    assert len(caller_list) == 1, (
        "SDK 가 호출자의 messages 리스트를 직접 늘리고 있다. 025 는 그러지 않는다는 "
        "전제 위에 서 있다 — 턴 끝에 덧붙이는 수행 기록이 SDK 가 넣은 것과 겹친다. "
        "`AuthoringAgent._drive` 의 이력 추가를 다시 보라."
    )
    assert caller_list[0]["content"] == "첫 지시"


def test_runner_grows_its_own_copy() -> None:
    """runner 안에서는 늘어난다 — **유실은 리스트가 갈라져 있기 때문**이다.

    「SDK 가 이력을 안 쌓는다」가 아니라 「쌓되 호출자에게 돌려주지 않는다」가 정확한
    서술이다. 그 차이가 해법을 가른다 — 우리가 남겨야 하는 것은 SDK 가 쌓은 원문이
    아니라, 제품이 아는 사실로 만든 **수행 기록**이다 (research R2).
    """
    caller_list: list[dict[str, Any]] = [{"role": "user", "content": "첫 지시"}]
    runner = _runner(caller_list)

    runner.append_messages({"role": "assistant", "content": "도구를 부른다"})
    runner.append_messages({"role": "user", "content": "결과"})

    assert len(runner._params["messages"]) == 3  # noqa: SLF001 - 계약 확인이 목적이다
    assert runner._params["messages"] is not caller_list  # noqa: SLF001


def test_agent_history_holds_only_user_messages() -> None:
    """`AuthoringAgent` 쪽에서 본 같은 사실.

    에이전트가 이력에 넣는 것은 사용자 메시지뿐이다. 이 검증은 **025 구현 뒤에 달라진다** —
    턴 끝에 어시스턴트 차례가 들어가기 때문이다. 그때 이 파일의 이 검증을 고치는 것이
    올바른 변경이고, 고치지 않아도 통과한다면 이력 추가가 동작하지 않는 것이다.
    """
    from itb.authoring.agent import AuthoringAgent  # noqa: PLC0415

    agent = AuthoringAgent(toolbox=None)  # type: ignore[arg-type]
    agent.messages.append({"role": "user", "content": "지시"})

    roles = [m["role"] for m in agent.messages]
    assert roles == ["user"], (
        "이력에 사용자 메시지만 있다는 전제가 깨졌다. 025 가 어시스턴트 차례를 넣기 "
        "시작했다면 이 검증을 그 사실에 맞게 고쳐라 — 지우지 말고."
    )
