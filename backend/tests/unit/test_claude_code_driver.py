"""개발용 Claude Code 드라이버. `ITB_AI_DRIVER=claude-code` 전용 경로.

제품 기본 경로가 아니지만 **두 가지는 테스트로 고정한다.**

1. **브라우저 도구 밖으로 나가지 않는다** (FR-086). Claude Code 는 파일 읽기·쓰기·Bash 를
   기본으로 주고, `allowed_tools` 는 그것을 **제한하지 않는다** — 자동 승인 목록일 뿐이다.
   실제 차단은 권한 콜백이 하므로 그 콜백을 직접 검증한다.
2. **막힘이 "끝냈다" 로 보고되지 않는다** (FR-069). 상한·막힘 판정은 호출자가 매 메시지마다
   하는데, 모델이 `report_blocked` 직후 턴을 끝내면 그 뒤에 흘릴 메시지가 없다.

`claude-agent-sdk` 는 선택 의존성이므로 미설치 환경에서는 전부 건너뛴다.
"""

from __future__ import annotations

import importlib.util
from typing import Any

import pytest

_SDK_INSTALLED = importlib.util.find_spec("claude_agent_sdk") is not None
pytestmark = pytest.mark.skipif(not _SDK_INSTALLED, reason="claude-agent-sdk 미설치 (선택 의존성)")


def test_prompt_keeps_every_instruction_in_order() -> None:
    """이력을 프롬프트 하나로 편다. **인수 후 재개 지시가 사라지면 안 된다** (FR-076)."""
    from itb.authoring.claude_code_driver import _prompt_from

    prompt = _prompt_from(
        [
            {"role": "user", "content": "로그인하고 프로젝트를 만들어라"},
            {"role": "assistant", "content": "로그인까지 했습니다"},
            {"role": "user", "content": "사람이 이어받아 약관에 동의했습니다"},
            {"role": "user", "content": "   "},
            {"role": "user", "content": None},
        ]
    )

    assert "로그인하고 프로젝트를 만들어라" in prompt
    assert "사람이 이어받아 약관에 동의했습니다" in prompt
    assert prompt.index("로그인하고") < prompt.index("사람이 이어받아")
    # 빈 항목은 자리만 차지하고 지시를 흐린다.
    assert prompt.count("[지시]") == 2
    assert prompt.count("[앞선 응답]") == 1


@pytest.mark.asyncio
async def test_gate_allows_only_browser_tools() -> None:
    """브라우저 도구 11종만 통과한다 (FR-086)."""
    from itb.authoring.claude_code_driver import _deny_unknown_tools
    from itb.authoring.tools import QUALIFIED_TOOL_NAMES

    gate = _deny_unknown_tools()

    for name in QUALIFIED_TOOL_NAMES:
        result = await gate(name, {"element_ref": "e1"}, None)
        assert result.behavior == "allow", name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name",
    ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebFetch", "Task", "mcp__other__click"],
)
async def test_gate_denies_everything_else(tool_name: str) -> None:
    """내장 도구와 낯선 MCP 도구를 모두 끊는다.

    `interrupt=True` 인 이유는, 거부만 하면 모델이 조용히 다른 도구로 우회하며 상한까지
    도는 것이다 — 무엇 때문에 실패했는지 알 수 없게 된다.
    """
    from itb.authoring.claude_code_driver import _deny_unknown_tools

    gate = _deny_unknown_tools()

    result = await gate(tool_name, {}, None)

    assert result.behavior == "deny"
    assert result.interrupt is True
    assert tool_name in result.message


@pytest.mark.asyncio
async def test_blocked_run_gets_a_final_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """`report_blocked` 직후 턴이 끝나도 호출자가 판정할 기회를 갖는다 (FR-069).

    이것이 없으면 막힌 실행이 `finished` 로 보고되고, 사용자는 4선택지(FR-069)를 받지
    못한 채 "끝났다" 를 읽는다.
    """
    import claude_agent_sdk as sdk

    from itb.authoring import claude_code_driver as mod
    from itb.llm.client import LlmConfig

    async def fake_query(*, prompt: str, options: Any) -> Any:
        # 모델이 도구를 부르고 곧바로 턴을 끝낸 모양. 뒤에 오는 어시스턴트 메시지가 없다.
        yield sdk.AssistantMessage(content=[sdk.TextBlock(text="확인합니다")], model="x")
        yield sdk.ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="s",
        )

    monkeypatch.setattr(sdk, "query", fake_query)
    monkeypatch.setattr(mod, "_deny_unknown_tools", lambda: None)

    messages = [{"role": "user", "content": "x"}]
    yielded = [m async for m in mod.claude_code_driver([], messages, LlmConfig())]

    assert len(yielded) == 2, "결말 뒤에 판정 기회가 한 번 더 있어야 한다"
    assert [b.text for b in yielded[0].content] == ["확인합니다"]
    assert yielded[1].content == [], "마지막 메시지는 진행 알림을 만들지 않는다"
    # `stop_reason` 은 이 경로에 없다. 호출자가 `check_stop_reason` 에 그대로 넘긴다.
    assert all(m.stop_reason is None for m in yielded)


@pytest.mark.asyncio
async def test_failed_result_surfaces_its_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """실패한 결말은 조용히 끝나지 않는다 — 사유를 들고 예외로 올라간다."""
    import claude_agent_sdk as sdk

    from itb.authoring import claude_code_driver as mod
    from itb.llm.client import LlmConfig

    async def fake_query(*, prompt: str, options: Any) -> Any:
        yield sdk.ResultMessage(
            subtype="error_during_execution",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=1,
            session_id="s",
            terminal_reason="max_turns",
        )

    monkeypatch.setattr(sdk, "query", fake_query)
    monkeypatch.setattr(mod, "_deny_unknown_tools", lambda: None)

    with pytest.raises(RuntimeError, match="max_turns"):
        async for _ in mod.claude_code_driver([], [{"role": "user", "content": "x"}], LlmConfig()):
            pass


# ─── 016 — 편집 도구가 개발용 드라이버에도 있다 (T062) ─────────────────────


def test_editing_tools_are_on_the_dev_driver_surface_too() -> None:
    """**두 드라이버의 표면이 갈리지 않는다** (016 US3).

    `QUALIFIED_TOOL_NAMES` 는 `TOOL_SCHEMAS` 에서 파생되므로 새 도구가 자동으로 따라
    들어온다. 그 자동 전파가 실제로 도는지 확인한다 — 끊기면 기본 드라이버에서는 되고
    개발용에서는 안 되는 도구가 생기고, 개발 중에 본 동작이 제품 동작과 달라진다.
    """
    from itb.authoring.tools import MCP_SERVER_NAME, QUALIFIED_TOOL_NAMES, STEP_EDITING_TOOLS

    for name in STEP_EDITING_TOOLS:
        qualified = f"mcp__{MCP_SERVER_NAME}__{name}"
        assert qualified in QUALIFIED_TOOL_NAMES, (
            f"개발용 드라이버 표면에 {name} 이 없다 — 두 경로가 갈렸다"
        )


def test_the_dev_driver_surface_equals_the_default_one() -> None:
    """표면 전체가 같다. 016 이후 16종."""
    from itb.authoring.tools import MCP_SERVER_NAME, QUALIFIED_TOOL_NAMES, TOOL_NAMES

    expected = {f"mcp__{MCP_SERVER_NAME}__{name}" for name in TOOL_NAMES}
    assert set(QUALIFIED_TOOL_NAMES) == expected
    assert len(QUALIFIED_TOOL_NAMES) == 16


def test_builtin_tools_are_still_blocked() -> None:
    """016 이 도구를 넷 더했다고 **내장 도구 차단이 느슨해지지 않았다** (FR-086).

    편집 도구는 MCP 서버 쪽에 등록되므로 내장 도구 차단과 무관하다. 그 무관함을
    여기서 고정한다 — 새 도구를 더하다 차단 목록을 건드리면 파일 시스템이 열린다.
    """
    from itb.authoring.claude_code_driver import BLOCKED_BUILTINS

    for dangerous in ("Bash", "Write", "Edit", "Read", "WebFetch"):
        assert dangerous in BLOCKED_BUILTINS, f"{dangerous} 차단이 사라졌다"


def test_every_tool_on_the_dev_driver_actually_builds() -> None:
    """이름만 맞는 것으로는 부족하다 — **감싸는 쪽도 전수를 돈다**.

    016 은 `TOOL_SCHEMAS` 에 편집 도구 넷을 더했지만 `build_mcp_tools` 안의 핸들러
    사전은 그대로 두었다. 이름 검사(T062)는 `TOOL_SCHEMAS` 에서 파생된 목록만 보므로
    통과했고, 실제 호출은 `KeyError: 'update_step'` 로 죽었다. 목록이 두 번 적히면
    한쪽만 갱신된다 — 그 실패를 여기서 잡는다.

    툴박스는 브라우저가 필요하므로 **이름만 맞춘 대역**을 쓴다. 검사 대상은 도구
    표면이지 브라우저 동작이 아니다 (브라우저 쪽은 us3 계층이 본다).
    """
    from itb.authoring.tools import TOOL_SCHEMAS, build_mcp_tools

    class FakeToolbox:
        def __init__(self) -> None:
            self.called: list[str] = []

        def __getattr__(self, name: str) -> Any:
            async def call(**kwargs: Any) -> dict[str, Any]:
                self.called.append(name)
                return {"ok": name}

            return call

    toolbox = FakeToolbox()
    built = build_mcp_tools(toolbox)  # type: ignore[arg-type]

    assert {t.name for t in built} == set(TOOL_SCHEMAS)
    assert len(built) == 16
