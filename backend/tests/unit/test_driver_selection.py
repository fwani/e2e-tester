"""드라이버 선택. **기본이 Messages API 임을 고정한다.**

이 파일이 지키는 것은 하나다 — 개발용 Claude Code 드라이버가 **실수로 기본이 되지
않는다.** 그렇게 되면 개발자는 자기가 무엇을 보고 있는지 모른 채 결과를 품질 근거로
쓰게 되고, 두 드라이버는 비교 가능하지 않다 (`claude_code_driver` 모듈 설명).

`claude-agent-sdk` 는 선택 의존성이므로 **설치되지 않은 환경에서도 이 파일은 통과해야
한다.** 개발용 경로를 고르는 검사는 설치 여부를 보고 건너뛴다.
"""

from __future__ import annotations

import importlib.util

import pytest

from itb.authoring.agent import (
    DRIVER_CLAUDE_CODE,
    DRIVER_ENV,
    _sdk_driver,
    select_driver,
)
from itb.authoring.tools import build_tools

_SDK_INSTALLED = importlib.util.find_spec("claude_agent_sdk") is not None


def test_default_is_messages_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경 변수가 없으면 제품 기본 경로다."""
    monkeypatch.delenv(DRIVER_ENV, raising=False)
    driver, build = select_driver()
    assert driver is _sdk_driver
    assert build is build_tools


@pytest.mark.parametrize("value", ["", "  ", "messages-api", "claude", "claudecode", "CLAUDE-CODE"])
def test_unrecognised_values_fall_back(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """오타는 조용히 개발용 경로를 켜지 않는다.

    `CLAUDE-CODE` 를 포함하는 이유는, 대소문자를 관대하게 받으면 "켜 두었는지" 를
    환경 변수 값만 보고 판정할 수 없게 되기 때문이다. 정확히 한 값만 켠다.
    """
    monkeypatch.setenv(DRIVER_ENV, value)
    driver, build = select_driver()
    assert driver is _sdk_driver
    assert build is build_tools


def test_monkeypatched_driver_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_sdk_driver` 를 갈아 끼우면 선택 결과도 갈린다.

    US4~US6 테스트가 이 이름 하나를 monkeypatch 해서 자격 증명 없이 AI 경로 전체를
    검증한다 (`backend/tests/us4_support.py`). 선택 함수가 임포트 시점에 전역을 붙잡아
    두면 그 방식이 조용히 멈춘다.
    """
    monkeypatch.delenv(DRIVER_ENV, raising=False)
    sentinel = object()
    monkeypatch.setattr("itb.authoring.agent._sdk_driver", sentinel)
    driver, _ = select_driver()
    assert driver is sentinel


@pytest.mark.skipif(not _SDK_INSTALLED, reason="claude-agent-sdk 미설치 (선택 의존성)")
def test_switch_selects_claude_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """정확한 값을 주면 개발용 드라이버와 MCP 도구 빌더가 짝으로 나온다."""
    from itb.authoring.claude_code_driver import claude_code_driver
    from itb.authoring.tools import build_mcp_tools

    monkeypatch.setenv(DRIVER_ENV, DRIVER_CLAUDE_CODE)
    driver, build = select_driver()
    assert driver is claude_code_driver
    assert build is build_mcp_tools


@pytest.mark.skipif(not _SDK_INSTALLED, reason="claude-agent-sdk 미설치 (선택 의존성)")
def test_browser_tools_are_the_only_allowed_tools() -> None:
    """권한 게이트의 허용 목록이 도구 표면과 정확히 일치한다 (FR-086).

    Claude Code 는 파일 읽기·쓰기·Bash 를 기본으로 준다. 허용 목록이 도구 표면보다
    넓어지는 순간 에이전트가 브라우저 밖으로 나갈 수 있다.
    """
    from itb.authoring.claude_code_driver import BLOCKED_BUILTINS
    from itb.authoring.tools import QUALIFIED_TOOL_NAMES, TOOL_SCHEMAS, build_tools

    # 도구 표면이 둘로 갈라지지 않았다. `build_tools` 는 실제 도구 객체를 만든다.
    assert set(TOOL_SCHEMAS) == {tool.name for tool in build_tools(_FakeToolbox())}
    assert QUALIFIED_TOOL_NAMES == [f"mcp__itb__{name}" for name in TOOL_SCHEMAS]
    # 내장 도구는 허용 목록에 없다.
    assert not set(BLOCKED_BUILTINS) & set(QUALIFIED_TOOL_NAMES)


class _FakeToolbox:
    """`build_tools` 가 감싸기만 하는지 확인하기 위한 자리표시자.

    도구를 부르지 않으므로 메서드가 없어도 된다 — `build_tools` 는 클로저로 잡을 뿐이다.
    """

    def __getattr__(self, name: str) -> object:  # pragma: no cover - 호출되지 않는다
        msg = f"이 테스트는 도구를 실행하지 않는다: {name}"
        raise AssertionError(msg)
