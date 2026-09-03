"""러너 태스크. 헌법 원칙 III.

세션마다 하나의 `asyncio.Task` 가 Step 을 순차 실행한다. HTTP 요청은 명령을 적용하고 즉시
반환하며, 실제 실행은 이 태스크가 담당한다 — 그래야 브라우저 수명이 요청 수명과 분리된다.

**Pause 는 태스크가 `asyncio.Event` 를 await 하는 것이다.** 브라우저에는 아무 명령도 보내지
않는다. 이 파일에 상태 저장·복원 로직이 없는 이유다 (research R1, T003 으로 실측 확인).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from itb.execution.session import BrowserSession
from itb.execution.state_machine import Command, SessionState

StepRunner = Callable[[BrowserSession, int], Awaitable[bool]]
"""Step 하나를 실행한다. (session, step_index) → 계속 진행할지 여부."""


class RunnerTask:
    """세션 하나의 실행 태스크.

    Step 실행 자체는 주입받은 `StepRunner` 가 담당한다 — 이 클래스는 **진행·일시정지·취소**만
    책임진다. 그래서 브라우저 없이 테스트할 수 있다.
    """

    def __init__(
        self,
        session: BrowserSession,
        step_runner: StepRunner,
        total_steps: int,
        start_index: int = 0,
    ) -> None:
        self._session = session
        self._run_step = step_runner
        self._total = total_steps
        self._index = start_index
        self._task: asyncio.Task[None] | None = None
        self._finished = asyncio.Event()

    # ─── 진행 상태 ─────────────────────────────────────────────────────────

    @property
    def current_index(self) -> int:
        """다음에 실행할 Step 위치. 편집 경고 판정의 기준이다 (FR-040b)."""
        return self._index

    @property
    def total_steps(self) -> int:
        return self._total

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def retarget(self, start_index: int, total_steps: int) -> None:
        """편집 후 실행 위치를 다시 잡는다.

        Step 이 삽입·삭제되면 인덱스가 밀린다. 브라우저는 건드리지 않는다 (FR-040a).
        """
        self._index = max(0, min(start_index, total_steps))
        self._total = total_steps

    # ─── 실행 ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.running:
            msg = "이미 실행 중입니다."
            raise RuntimeError(msg)
        self._finished.clear()
        self._session.mark_running()
        self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        try:
            while self._index < self._total:
                # 일시정지 지점 — 브라우저에 아무 명령도 보내지 않는다.
                if self._session.is_paused:
                    await self._session.wait_until_resumed()
                    # 재개 시점에 편집으로 총 개수가 바뀌었을 수 있다.
                    if self._index >= self._total:
                        break

                should_continue = await self._run_step(self._session, self._index)
                self._index += 1
                if not should_continue:
                    await self._session.apply(Command.FINISH_FAIL)
                    return

            if self._session.state in (SessionState.REPLAYING, SessionState.AI_RUNNING):
                await self._session.apply(Command.FINISH_PASS)
        except asyncio.CancelledError:
            raise
        finally:
            self._finished.set()

    async def wait(self) -> None:
        await self._finished.wait()

    async def cancel(self) -> None:
        """태스크를 취소한다. 브라우저는 호출자가 정리한다."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._finished.set()
