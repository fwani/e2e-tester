"""에이전트 루프. FR-059·FR-060·FR-065·FR-066·FR-067·FR-076 (T112·T125, research R5).

`client.beta.messages.tool_runner(...)` 를 `async for` 로 돈다. 루프를 직접 짜지 않는다 —
직접 짜서 얻을 것이 없고, 개입 지점은 `async for` 본문에서 확보된다.

**하드 루프 카운터가 1차 방어선이다** (FR-066). 도구 호출 총 상한과 동일 요소 연속 실패
상한을 `BrowserToolbox` 가 세고, 상한에 닿으면 예외로 루프를 끊는다. 모델에게 페이스
조절을 맡기는 장치(task budget)는 권고적이며 이것을 대체하지 못한다.

**서버 도구를 쓰지 않으므로 `pause_turn` 을 다루지 않는다.** 브라우저 도구는 전부 클라이언트
측 도구다 — Python tool runner 가 `pause_turn` 을 자동 재개하지 못하는 알려진 함정을
구조적으로 회피한다.

**언어모델이 실패해도 그때까지의 Step 은 보존된다** (FR-067). 이 모듈은 어떤 실패 경로에서도
Step 목록을 건드리지 않는다 — 목록은 세션이 소유하고, 확정은 도구가 성공한 시점에 이미
끝나 있다.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from itb.authoring.compiler import StepCompiler
from itb.authoring.tools import MAX_TOOL_CALLS, BrowserToolbox, build_tools
from itb.llm.client import LlmConfig, LlmUnavailableError, RefusalError, check_stop_reason

MAX_INSTRUCTION_LENGTH = 8000
"""자연어 지시문 길이 상한 (FR-085). 경계에서 검증한다."""

SYSTEM_PROMPT = """\
당신은 웹 브라우저를 조작해 E2E 테스트를 만드는 도구입니다.

규칙:
- 화면을 조작하기 전에 반드시 observe_page 로 지금 화면을 확인하세요.
- 다른 도구에는 observe_page 가 준 element_ref 만 넘기세요. CSS 셀렉터를 직접 만들지 마세요.
- 화면이 바뀌었을 수 있으면 observe_page 를 다시 부르세요. 참조는 화면이 바뀌면 낡습니다.
- 한 지시를 여러 동작으로 나누어 차례로 수행하세요. 성공한 동작만 테스트로 남습니다.
- 지시를 완료했으면 무엇을 했는지 짧게 정리하고 끝내세요.
- 지시를 수행할 수 없으면 report_blocked 로 **무엇이 막았는지 구체적으로** 알리세요.
  추측으로 다른 요소를 누르지 마세요. 사람이 이어받을 수 있습니다.
- 로그인 화면을 만나면 지시문에 있는 자격 증명만 쓰세요. 값을 만들어 내지 마세요.
"""


class AgentStatus(StrEnum):
    FINISHED = "finished"
    """지시를 끝냈다. 성공한 동작이 Step 으로 남아 있다 (FR-063)."""

    BLOCKED = "blocked"
    """막혔다. **세션은 유지된다** — 사용자가 4선택지 중 하나를 고른다 (FR-069)."""

    ERROR = "error"
    """언어모델 호출이 실패했다. 그때까지의 Step 은 보존된다 (FR-067)."""

    CANCELLED = "cancelled"
    """사용자가 일시정지·중지했다 (FR-065)."""


@dataclass(slots=True)
class AgentOutcome:
    """루프 종료 결과. 호출자가 이벤트로 바꾼다."""

    status: AgentStatus
    reason: str | None = None
    attempted: str | None = None
    """막힌 시점에 시도하던 동작. `ai_blocked` 이벤트의 `attempted` 다 (FR-070)."""

    step_count: int = 0
    tool_calls: int = 0


Driver = Callable[[list[Any], list[dict[str, Any]], LlmConfig], AsyncIterator[Any]]
"""도구 루프를 실제로 도는 것. 기본은 SDK 의 `tool_runner`.

**테스트가 갈아 끼우는 지점이다.** 자격 증명 없이 도구 동작과 상한을 검증할 수 있어야
한다 — 원칙 II 검증 테스트(SC-006)도 이 지점을 쓴다.
"""


def _sdk_driver(
    tools: list[Any], messages: list[dict[str, Any]], config: LlmConfig
) -> AsyncIterator[Any]:
    """실제 SDK 루프. 이 함수만 `anthropic` 을 안다."""
    from itb.llm.client import create_client  # noqa: PLC0415

    client = create_client()
    runner = client.beta.messages.tool_runner(
        messages=messages,
        tools=tools,
        system=SYSTEM_PROMPT,
        # 두 번째 방어선. 1차는 제품이 세는 도구 호출 상한이고(FR-066), 이것은 모델이
        # 도구를 부르지 않으면서 계속 말하는 경우까지 막는다.
        max_iterations=MAX_TOOL_CALLS,
        **config.request_kwargs(),
    )
    return runner.__aiter__()


DRIVER_ENV = "ITB_AI_DRIVER"
"""드라이버를 고르는 환경 변수. **개발용 스위치이므로 화면에 두지 않는다** — 확정
디자인에 없는 요소를 더하는 것이고(DC-007), 제품 설정이 되면 사용자가 실수로 바꾼다."""

DRIVER_CLAUDE_CODE = "claude-code"
"""이미 로그인된 Claude Code 로 돈다. 개발·수동 확인 전용 (`claude_code_driver`)."""

ToolBuilder = Callable[[Any], list[Any]]
"""도구 표면을 만드는 것. 드라이버와 짝이다 — 감싸는 방식이 SDK 마다 다르다."""


def select_driver() -> tuple[Driver, ToolBuilder]:
    """드라이버와 도구 빌더를 고른다. **기본은 Messages API 다.**

    인식하지 못한 값은 기본으로 떨어진다 — 오타가 조용히 개발용 경로를 켜면, 개발자는
    자기가 무엇을 보고 있는지 모른 채 결과를 품질 근거로 쓴다.

    `_sdk_driver` 를 **모듈 전역으로 읽는다.** 테스트가 그 이름 하나를 monkeypatch 해서
    자격 증명 없이 AI 경로 전체를 검증하기 때문이다 (`backend/tests/us4_support.py`).
    """
    if os.environ.get(DRIVER_ENV, "").strip() == DRIVER_CLAUDE_CODE:
        from itb.authoring.claude_code_driver import claude_code_driver  # noqa: PLC0415
        from itb.authoring.tools import build_mcp_tools  # noqa: PLC0415

        return claude_code_driver, build_mcp_tools
    return _sdk_driver, build_tools


def validate_instruction(text: str | None) -> str:
    """지시문을 경계에서 검증한다 (FR-085).

    길이만 보는 것이 아니라 **비어 있지 않음**도 본다. 빈 지시문으로 세션을 만들면
    에이전트가 무엇을 해야 하는지 알 수 없고, 그 실패는 도구 호출 상한에 닿아서야 끝난다.
    """
    if text is None or not text.strip():
        msg = "자연어 지시문이 비어 있습니다. 무엇을 하고 싶은지 적어 주세요."
        raise ValueError(msg)
    if len(text) > MAX_INSTRUCTION_LENGTH:
        msg = (
            f"지시문이 너무 깁니다({len(text)}자). "
            f"{MAX_INSTRUCTION_LENGTH}자 이내로 줄이거나 여러 테스트로 나누세요."
        )
        raise ValueError(msg)
    return text.strip()


@dataclass(slots=True)
class AuthoringAgent:
    """한 작성 세션의 에이전트.

    Step 목록을 소유하지 않는다 — 도구가 성공할 때마다 `compiler` 를 통해 세션에 넣는다.
    그래서 어떤 실패 경로에서도 Step 이 사라지지 않는다 (FR-067).
    """

    toolbox: BrowserToolbox
    config: LlmConfig = field(default_factory=LlmConfig)
    driver: Driver | None = None
    on_progress: Callable[[str], Awaitable[None]] | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    """대화 이력. **사람이 이어받은 뒤 재개할 때 그대로 이어 쓴다** (FR-076, T125)."""

    compiler: StepCompiler | None = None
    """확정된 Step 을 센 주체. `ai_finished` 의 `step_count` 근거다 (FR-063)."""

    async def run(self, instruction: str) -> AgentOutcome:
        """지시문 하나를 수행한다.

        새 지시를 이력에 덧붙인다 — 재개(FR-076)는 같은 이력에 "사람이 이어받아 처리했다"
        를 덧붙여 부르므로, 에이전트가 앞서 무엇을 했는지 알고 이어서 진행한다.
        """
        text = validate_instruction(instruction)
        self.messages.append({"role": "user", "content": text})
        return await self._drive()

    async def resume_after_takeover(self, note: str) -> AgentOutcome:
        """사람이 이어받아 처리한 뒤 남은 지시를 이어서 수행한다 (FR-076, T125).

        **브라우저 상태를 되돌리지 않는다.** 사람이 남긴 화면이 지금 상태이며, 에이전트는
        그 상태에서 이어서 관찰하고 판단한다. 그래서 재개 지시에 "지금 화면을 다시
        확인하라" 를 명시한다 — 앞선 관찰 결과는 낡았다.
        """
        # 사람이 막힌 지점을 풀었다. 앞선 시도가 쓴 예산을 이어서 세면 재개가 곧바로
        # 상한에 닿을 수 있다 (FR-066).
        self.toolbox.limits.reset()
        self.messages.append(
            {
                "role": "user",
                "content": (
                    f"사람이 이어받아 다음을 처리했습니다: {note}\n"
                    "지금 화면을 observe_page 로 다시 확인한 뒤, 남은 지시를 이어서 "
                    "수행하세요. 이미 처리된 동작을 다시 하지 마세요."
                ),
            }
        )
        return await self._drive()

    async def _drive(self) -> AgentOutcome:
        """도구 루프를 돌린다. 모든 종료 경로가 `AgentOutcome` 으로 수렴한다."""
        # **막힘 표시를 지우고 시작한다.** 앞선 시도의 표시가 남아 있으면 재시도·건너뛰기·
        # 인수 후 재개가 첫 메시지에서 곧바로 다시 막힌 것으로 판정된다 (US5 통합 테스트가
        # 잡았다). 앞선 결과는 이미 호출자에게 보고됐으므로 여기서 들고 있을 이유가 없다.
        self.toolbox.blocked_reason = None
        try:
            selected, build = select_driver()
            driver = self.driver or selected
            tools = build(self.toolbox)
        except ImportError as exc:
            # 기본 경로의 SDK 는 설치되어 있다. 여기 닿는 것은 개발용 드라이버를 켜 놓고
            # 선택 의존성을 설치하지 않은 경우다 (`uv sync --extra claude-code`).
            return AgentOutcome(
                AgentStatus.ERROR,
                reason=f"도구를 준비할 수 없습니다: {exc}",
                tool_calls=self.toolbox.limits.calls,
            )

        stopped: str | None = None
        try:
            iterator = driver(tools, self.messages, self.config)
            async for message in iterator:
                # `content` 를 읽기 전에 `stop_reason` 을 확인한다 (research R5).
                check_stop_reason(getattr(message, "stop_reason", None))
                await self._report(message)

                # ★ **여기가 상한과 실패 선언을 실제로 끊는 지점이다.**
                # SDK 는 도구가 던진 예외를 잡아 모델에게 돌려주므로, 도구 안에서 예외로
                # 루프를 끊을 수 없다. 도구는 상태만 남기고, 우리가 소유한 이 본문이
                # 그 상태를 보고 나온다 (FR-066·FR-069).
                stopped = self.toolbox.blocked_reason or self.toolbox.limits.exceeded_reason
                if stopped is not None:
                    break
        except asyncio.CancelledError:
            # 사용자가 일시정지·중지했다. 취소는 실패가 아니므로 결과로 기록하지 않는다.
            raise
        except (LlmUnavailableError, RefusalError) as exc:
            return AgentOutcome(
                AgentStatus.ERROR,
                reason=str(exc),
                step_count=self._count(),
                tool_calls=self.toolbox.limits.calls,
            )
        except Exception as exc:  # noqa: BLE001 - 예상 못한 실패도 사유와 함께 알린다
            return AgentOutcome(
                AgentStatus.ERROR,
                reason=(
                    f"AI 수행 중 예상하지 못한 오류가 발생했습니다: {type(exc).__name__}: {exc} "
                    "그때까지 기록된 Step 은 보존됩니다."
                ),
                step_count=self._count(),
                tool_calls=self.toolbox.limits.calls,
            )

        if stopped is not None:
            return AgentOutcome(
                AgentStatus.BLOCKED,
                reason=stopped,
                attempted=self.toolbox.limits.last_failed_element,
                step_count=self._count(),
                tool_calls=self.toolbox.limits.calls,
            )

        return AgentOutcome(
            AgentStatus.FINISHED,
            step_count=self._count(),
            tool_calls=self.toolbox.limits.calls,
        )

    async def _report(self, message: Any) -> None:
        """모델이 낸 텍스트를 진행 상황으로 알린다 (FR-060).

        도구 실행 자체의 진행은 도구가 알린다. 여기서는 **모델의 판단**을 전한다 —
        사용자가 "AI 가 지금 무엇을 하는 중인지" 를 읽는 것이 이 이벤트의 목적이다.
        """
        if self.on_progress is None:
            return
        for block in getattr(message, "content", None) or []:
            text = getattr(block, "text", None)
            if isinstance(text, str) and text.strip():
                await self.on_progress(" ".join(text.split())[:400])

    def _count(self) -> int:
        """이 세션에서 확정된 Step 수. 컴파일러가 센다.

        에이전트가 따로 세지 않는 이유는, 세는 주체가 둘이면 어긋나기 때문이다 —
        Step 확정은 도구가 성공한 시점에 컴파일러를 지나므로 그것이 유일한 근거다.
        """
        return self.compiler.count if self.compiler is not None else 0
