"""세션 유실 감지. FR-041·FR-041a~c.

**어느 상태에서든** 감지해야 한다. 사용자가 브라우저 창을 직접 닫는 일은 실행 중에도,
일시정지 중에도, AI 실패 대기 중에도 일어난다. 상태별로 감지 지점을 따로 두면 그중 하나가
빠지고, 빠진 상태에서는 세션이 유실됐는데 화면은 살아 있는 것처럼 보인다.

감지 지점은 두 개다.

- `Browser.on("disconnected")` — 브라우저 프로세스가 사라졌다
- `BrowserContext.on("close")` — 컨텍스트가 닫혔다 (창을 모두 닫은 경우)

둘 중 무엇이 먼저 와도 **한 번만** 처리한다. 유실 통보가 두 번 나가면 화면이 두 번 놀란다.

유실 뒤 허용되는 것은 **저장과 처음부터 재실행뿐이다** (FR-041c). 이것은 상태 기계가
`LOST` 에서 `SAVE` 만 허용하는 것으로 이미 강제된다 — 이 모듈은 `LOST` 로 옮기는 일만 한다.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from itb.execution.session import BrowserSession
from itb.execution.state_machine import Command, SessionState, uses_llm

LossHandler = Callable[[str], Awaitable[None]]
"""유실 사유를 받아 뒷정리를 하는 콜백. 부분 결과 보존이 여기서 일어난다."""

REASON_BROWSER_GONE = "브라우저가 종료되어 세션이 유실됐습니다."
REASON_CONTEXT_CLOSED = "브라우저 창이 모두 닫혀 세션이 유실됐습니다."


class SessionLossWatcher:
    """세션 하나의 유실 감시자.

    이벤트 핸들러는 Playwright 의 이벤트 루프에서 동기적으로 호출된다. 그 안에서 await 할
    수 없으므로 태스크를 띄운다 — 감지가 늦어지면 유실을 모르는 창이 생긴다.
    """

    def __init__(self, session: BrowserSession, on_lost: LossHandler | None = None) -> None:
        self._session = session
        self._on_lost = on_lost
        self._fired = False
        self._attached = False
        self._task: asyncio.Task[None] | None = None

    @property
    def fired(self) -> bool:
        return self._fired

    def attach(self) -> None:
        """감지를 시작한다. 두 번 붙이지 않는다."""
        if self._attached:
            return
        self._attached = True
        with contextlib.suppress(Exception):
            self._session.browser.on(
                "disconnected", lambda _b=None: self._schedule(REASON_BROWSER_GONE)
            )
        with contextlib.suppress(Exception):
            self._session.context.on(
                "close", lambda _c=None: self._schedule(REASON_CONTEXT_CLOSED)
            )

    def _schedule(self, reason: str) -> None:
        if self._fired:
            return
        self._fired = True
        with contextlib.suppress(RuntimeError):  # 루프가 이미 닫힌 종료 경로
            self._task = asyncio.create_task(self._handle(reason))

    async def _handle(self, reason: str) -> None:
        state = self._session.state
        if state in (
            SessionState.COMPLETED,
            SessionState.FAILED,
            SessionState.STOPPED,
            SessionState.LOST,
        ):
            # 정상 종료 과정에서도 close 이벤트가 온다. 그것은 유실이 아니다.
            return

        message = f"{reason} {_guidance(state)}"
        with contextlib.suppress(Exception):
            await self._session.apply(Command.SESSION_LOST)
        await self._session.emit("session_lost", reason=message)

        if self._on_lost is not None:
            with contextlib.suppress(Exception):
                await self._on_lost(message)

    async def wait(self) -> None:
        """감지 후처리가 끝나기를 기다린다. 테스트와 종료 경로에서 쓴다."""
        if self._task is not None:
            with contextlib.suppress(Exception):
                await self._task


def _guidance(state: SessionState) -> str:
    """상태별 안내. 무엇이 보존됐고 이제 무엇을 할 수 있는지 말한다 (FR-041a~c)."""
    if state is SessionState.REPLAYING:
        # FR-041a — 실패로 종료하되 그때까지의 Step별 결과는 남긴다.
        return (
            "실행을 실패로 종료했고 그때까지의 Step별 결과는 보존했습니다. "
            "처음부터 다시 실행하세요."
        )
    if uses_llm(state):
        # FR-041b — 루프를 중단하고 성공한 Step 을 보존한 뒤 저장 여부를 확인한다.
        return "AI 수행을 중단했고 그때까지 성공한 Step 은 보존했습니다. 저장할지 확인하세요."
    return "기록된 Step 은 보존했습니다. 저장하거나 처음부터 다시 실행할 수 있습니다."
