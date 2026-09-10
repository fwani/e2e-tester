"""AI 실패 처리. FR-069·FR-070 (T122).

**세션을 유지한다.** 이것이 이 모듈의 전부다. 도구가 실패했거나 에이전트가 수행 불가를
선언했을 때 브라우저를 닫으면, 사용자가 이어받을 화면이 사라진다 — PRD §8 Human Takeover
는 세션이 실패보다 오래 살아야만 성립한다 (헌법 원칙 III).

상태 기계가 `AI_BLOCKED` 를 `SESSION_HELD_STATES` 에 넣어 이 규칙을 강제한다. 이 모듈은
그 상태로 옮기고 사용자에게 무엇이 막았는지와 4선택지를 알리는 일만 한다.
"""

from __future__ import annotations

from enum import StrEnum

from itb.authoring.agent import AgentOutcome, AgentStatus
from itb.execution.session import BrowserSession
from itb.execution.state_machine import Command


class AiChoice(StrEnum):
    """FR-071~FR-074 의 선택지. 다른 값은 받지 않는다 (FR-043a).

    2026-09-10 에 `ANSWER` 가 더해져 다섯이 됐다 (사용자 결정).
    """

    TAKEOVER = "takeover"
    """직접 수행 — 사람이 이어받아 녹화한다 (FR-071)."""

    ANSWER = "answer"
    """답하고 AI 에게 돌려준다 (2026-09-10 사용자 결정).

    「문제가 생기면 사람에게 넘기는데, 넘기는 방법이 현재는 직접 클릭으로 takeover 하는
    개념이다. 대화를 통해서 답변을 하거나 인터뷰로 답변을 하고, 그러면 다시 AI 가 테스트
    스텝을 생성하거나 수정하는 것이다」.

    **`TAKEOVER` 와 `RETRY` 사이의 빈칸이었다.** 막힘의 상당수는 AI 가 화면을 못 다루는
    것이 아니라 **모르는 것이 있어서**다 — 어느 계정으로 로그인할지, 두 개의 「저장」 중
    어느 것인지, 이 값이 무엇인지. 그때 사람이 할 수 있는 일이 「내가 대신 조작한다」와
    「그냥 다시 해 봐라」 둘뿐이면, 한 문장이면 풀릴 일에 사람이 브라우저를 잡는다.

    답은 **같은 대화에 이어 붙는다** — 새 지시가 아니다. 그래야 AI 가 앞서 무엇을 하다
    막혔는지 알고 그 자리에서 이어 간다.
    """

    RETRY = "retry"
    """AI 에게 다시 — **현재 상태에서** 재시도한다 (FR-072). 되돌리지 않는다."""

    SKIP = "skip"
    """건너뛰기 — 실패한 동작을 Step 으로 남기지 않고 다음으로 (FR-073)."""

    ABORT = "abort"
    """종료 — 세션을 닫고 저장 여부를 확인한다 (FR-074)."""


CHOICES: tuple[str, ...] = tuple(c.value for c in AiChoice)

_CHOICE_COMMANDS: dict[AiChoice, Command] = {
    AiChoice.TAKEOVER: Command.CHOOSE_TAKEOVER,
    AiChoice.ANSWER: Command.CHOOSE_ANSWER,
    AiChoice.RETRY: Command.CHOOSE_RETRY,
    AiChoice.SKIP: Command.CHOOSE_SKIP,
    AiChoice.ABORT: Command.CHOOSE_ABORT,
}


def command_for(choice: AiChoice) -> Command:
    return _CHOICE_COMMANDS[choice]


async def enter_blocked(session: BrowserSession, outcome: AgentOutcome) -> None:
    """`AI_BLOCKED` 로 옮기고 `ai_blocked` 를 발행한다 (FR-069·FR-070).

    **브라우저를 닫지 않는다.** 상태 전이만 하고, 사용자가 4선택지 중 하나를 고를 때까지
    기다린다. 실패한 동작·이유·선택지를 함께 실어 보내는 이유는, 무엇이 막았는지 모르면
    "직접 수행" 을 골라도 무엇을 해야 하는지 알 수 없기 때문이다.
    """
    if outcome.status is not AgentStatus.BLOCKED:  # pragma: no cover - 호출자가 지킨다
        msg = f"막힌 결과가 아닙니다: {outcome.status}"
        raise ValueError(msg)

    await session.apply(Command.AI_BLOCK)
    await session.emit(
        "ai_blocked",
        attempted=outcome.attempted,
        reason=outcome.reason,
        # 2026-09-10 — AI 가 **사람에게 물을 것**을 남겼으면 함께 싣는다. 없으면 `None`
        # 이고, 그때도 사람이 먼저 말할 수 있다 (질문이 답변의 전제는 아니다).
        question=outcome.question,
        choices=list(CHOICES),
    )
