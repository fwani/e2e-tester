"""개발용 드라이버 — 이미 로그인된 Claude Code 로 에이전트 루프를 돈다.

**기본 경로가 아니다.** `ITB_AI_DRIVER=claude-code` 일 때만 선택된다
(`itb.authoring.agent.select_driver`). 기본은 Messages API 다.

이 모듈이 존재하는 이유는 **로컬 개발 중 자격 증명 때문에 AI 경로를 눈으로 못 보는 것**이다.
UX 워크스루에서 S6·S7 이 미검증으로 남은 것이 그 경우다. API 키가 없어도 이미 로그인된
`claude` 를 그대로 쓰면 화면·이벤트·Step 기록을 끝까지 확인할 수 있다.

**결과를 품질 근거로 쓰지 않는다.** Messages API 전용 파라미터
(`output_config.effort`·`betas`·`fallbacks`·`stop_reason: "refusal"`)가 이 경로에서는
전달되지 않고, 모델도 로그인된 Claude Code 의 기본값을 따른다. 두 드라이버의 결과는
비교 가능하지 않으므로 SC-002 같은 성공 기준 측정은 기본 드라이버로만 한다.

**원칙 II** — `claude_agent_sdk` 를 아는 유일한 모듈이다. `itb.authoring` 안에 두어
`.importlinter` 의 `execution-no-llm` 계약이 실행 경로의 도달을 막는다. `itb.llm` 이 아닌
이유는 임포트 방향이다 — 드라이버는 도구 표면(`itb.authoring.tools`)을 알아야 하고,
`itb.llm` 이 `itb.authoring` 을 거꾸로 임포트하면 경계가 뒤집힌다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from itb.authoring.tools import MAX_TOOL_CALLS, MCP_SERVER_NAME, QUALIFIED_TOOL_NAMES

if TYPE_CHECKING:  # pragma: no cover - 타입 검사 전용
    from itb.llm.client import LlmConfig

BLOCKED_BUILTINS = [
    "Read",
    "Write",
    "Edit",
    "NotebookEdit",
    "Bash",
    "BashOutput",
    "KillShell",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "Task",
    "TodoWrite",
]
"""Claude Code 가 기본으로 주는 도구. **브라우저 조작 범위를 넘으므로 전부 막는다**
(FR-086). 이것이 없으면 에이전트가 사용자 파일 시스템을 만질 수 있다.

`disallowed_tools` 는 방어의 2선이다. 1선은 `_deny_unknown_tools` 로, 이 목록에 없는
새 내장 도구가 생겨도 막힌다 — 목록을 세는 방식은 SDK 가 도구를 더할 때 뚫린다.
"""


@dataclass(slots=True)
class _TextBlock:
    """`AuthoringAgent._report` 가 읽는 모양. `.text` 하나면 된다."""

    text: str


@dataclass(slots=True)
class _Message:
    """`AuthoringAgent._drive` 가 읽는 모양.

    `stop_reason` 은 항상 `None` 이다 — Claude Code 경로에는 Messages API 의
    `stop_reason: "refusal"` 에 대응하는 신호가 없다. 거부는 모델이 텍스트로 말하고,
    도구를 부르지 않으므로 `max_turns` 상한에서 끝난다.
    """

    content: list[_TextBlock] = field(default_factory=list)
    stop_reason: None = None


def _prompt_from(messages: list[dict[str, Any]]) -> str:
    """대화 이력을 프롬프트 하나로 편다.

    Claude Code 는 세션을 자체적으로 소유하므로 이력을 그대로 주입할 자리가 없다.
    이 드라이버는 매 호출을 **새 세션**으로 돌리고 이력을 프롬프트에 편다 —
    인수 후 재개(FR-076)가 "지금 화면을 다시 확인하라" 를 지시에 담고 있고 브라우저
    상태는 실제로 남아 있으므로, 사용자 쪽 이력만으로도 이어서 진행할 수 있다.
    """
    parts: list[str] = []
    for message in messages:
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        role = "지시" if message.get("role") == "user" else "앞선 응답"
        parts.append(f"[{role}]\n{content.strip()}")
    return "\n\n".join(parts)


def _deny_unknown_tools() -> Any:
    """브라우저 도구가 아닌 모든 호출을 거부하는 권한 콜백.

    **`allowed_tools` 는 도구를 제한하지 않는다** — 자동 승인 목록일 뿐이고, 거기 없는
    도구는 여전히 부를 수 있다. 실제 차단은 이 콜백이 한다. `interrupt=True` 로 루프를
    끊어 조용히 다른 도구로 우회하는 것을 막는다.
    """
    from claude_agent_sdk import (  # noqa: PLC0415 - SDK 경계를 함수 안에 둔다
        PermissionResultAllow,
        PermissionResultDeny,
    )

    allowed = frozenset(QUALIFIED_TOOL_NAMES)

    async def gate(tool_name: str, input_data: dict[str, Any], _context: Any) -> Any:
        if tool_name in allowed:
            return PermissionResultAllow(updated_input=input_data)
        return PermissionResultDeny(
            message=(
                f"{tool_name} 은 이 작업에서 쓸 수 없습니다. "
                "브라우저 조작 도구만 사용하세요 (FR-086)."
            ),
            interrupt=True,
        )

    return gate


async def claude_code_driver(
    tools: list[Any], messages: list[dict[str, Any]], config: LlmConfig
) -> AsyncIterator[_Message]:
    """`Driver` 계약의 개발용 구현. 로그인된 Claude Code 를 쓴다.

    `config` 의 모델·effort·폴백은 **쓰지 않는다.** 모델은 로그인된 Claude Code 의
    기본값을 따른다 — 여기서 `config.model` 을 강제하면 그 모델을 쓸 수 없는 요금제에서
    무슨 일이 일어났는지 알기 어려운 실패가 된다. 상한(`max_turns`)만 옮긴다.
    """
    from claude_agent_sdk import (  # noqa: PLC0415 - SDK 경계를 함수 안에 둔다
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        create_sdk_mcp_server,
        query,
    )

    # `agent` 는 이 모듈을 지연 임포트해 고른다. 여기서도 지연 임포트해 순환을 피한다.
    from itb.authoring.agent import SYSTEM_PROMPT  # noqa: PLC0415

    server = create_sdk_mcp_server(name=MCP_SERVER_NAME, version="1.0.0", tools=tools)
    options = ClaudeAgentOptions(
        mcp_servers={MCP_SERVER_NAME: server},
        allowed_tools=list(QUALIFIED_TOOL_NAMES),
        disallowed_tools=list(BLOCKED_BUILTINS),
        can_use_tool=_deny_unknown_tools(),
        # 콜백이 실제로 불리려면 기본 모드여야 한다. `bypassPermissions` 는 게이트를
        # 건너뛰므로 내장 도구가 열린다.
        permission_mode="default",
        # 사용자의 settings·CLAUDE.md·훅을 읽지 않는다. 읽으면 개발자 환경마다 다른
        # 지시가 섞여 들어와 무엇을 보고 있는지 알 수 없게 된다.
        setting_sources=[],
        system_prompt=SYSTEM_PROMPT,
        max_turns=MAX_TOOL_CALLS,
    )

    stream = query(prompt=_prompt_from(messages), options=options)
    try:
        async for message in stream:
            if isinstance(message, AssistantMessage):
                blocks = [
                    _TextBlock(block.text)
                    for block in message.content
                    if isinstance(block, TextBlock)
                ]
                yield _Message(content=blocks)
            elif isinstance(message, ResultMessage):
                if message.subtype != "success":
                    reason = message.terminal_reason or message.subtype
                    msg = f"Claude Code 가 작업을 끝내지 못했습니다: {reason}"
                    raise RuntimeError(msg)
                # **마지막으로 한 번 더 흘린다.** 상한·막힘 판정은 호출자가 매 메시지마다
                # 하는데(`AuthoringAgent._drive`), 모델이 `report_blocked` 를 부른 직후
                # 턴이 끝나면 그 뒤에 흘릴 메시지가 없다. 그러면 막힌 실행이 "끝냈다"
                # 로 보고된다 (FR-069). 빈 메시지는 진행 알림을 만들지 않는다.
                yield _Message()
    finally:
        close = getattr(stream, "aclose", None)
        if close is not None:
            await close()
