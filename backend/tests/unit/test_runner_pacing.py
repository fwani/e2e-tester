"""러너의 Step 간 간격 규칙. 004 FR-101·FR-103·FR-105, spec 엣지 케이스.

**브라우저 없이 본다.** 간격은 언제 쉬고 언제 쉬지 않는지를 정하는 규칙이며, 그 판단에
브라우저가 필요하지 않다. 실제 실행에서의 확인은 `tests/integration/test_pacing_interrupt.py`
가 맡는다 — 여기서는 규칙 자체를 전수로 본다.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from itb.domain.run_pacing import RunPacing
from itb.execution.runner import RunnerTask
from itb.execution.state_machine import Command, SessionState


class _FakeSession:
    """러너가 요구하는 최소 표면. 일시정지 신호 두 개를 실제로 흉내 낸다."""

    def __init__(
        self,
        state: SessionState = SessionState.REPLAYING,
        pacing: RunPacing = RunPacing.FAST,
    ) -> None:
        self.state = state
        self.pacing = pacing
        self.current_step_index = 0
        self.events: list[tuple[str, dict]] = []
        # 005 FR-146 — 러너가 실행 종료 시 전이 안내를 걷는다. 가짜도 그 표면을
        # 가져야 한다: 없으면 러너의 종료 경로가 가짜에서만 터지고, 그 실패는 제품이
        # 아니라 가짜의 낡음을 알린다.
        self.edit_warnings: list[str] = []
        self.transient_edit_warnings: set[str] = set()
        self._resume = asyncio.Event()
        self._resume.set()
        self._pause_requested = asyncio.Event()

    @property
    def is_paused(self) -> bool:
        return not self._resume.is_set()

    def mark_running(self) -> None:
        self._resume.set()
        self._pause_requested.clear()

    async def wait_until_resumed(self) -> None:
        await self._resume.wait()

    async def wait_pause_requested(self) -> None:
        await self._pause_requested.wait()

    def request_pause(self) -> None:
        """다른 태스크가 일시정지를 요청한 것처럼 만든다."""
        self._resume.clear()
        self._pause_requested.set()

    async def emit(self, event_type: str, **payload: object) -> None:
        self.events.append((event_type, payload))

    def add_edit_warning(self, message: str, *, transient: bool = False) -> None:
        if message not in self.edit_warnings:
            self.edit_warnings.append(message)
        if transient:
            self.transient_edit_warnings.add(message)

    def clear_transient_edit_warnings(self) -> bool:
        if not self.transient_edit_warnings:
            return False
        self.edit_warnings = [
            m for m in self.edit_warnings if m not in self.transient_edit_warnings
        ]
        self.transient_edit_warnings.clear()
        return True

    async def publish_edit_warnings_now(self) -> None:
        await self.emit("edit_warning", messages=list(self.edit_warnings))

    async def apply(self, command: Command) -> SessionState:
        if command is Command.PAUSE:
            self.state = SessionState.PAUSED
            self._resume.clear()
            self._pause_requested.set()
        elif command is Command.FINISH_PASS:
            self.state = SessionState.COMPLETED
        elif command is Command.FINISH_FAIL:
            self.state = SessionState.FAILED
        return self.state


def _task(session: _FakeSession, total: int = 3) -> RunnerTask:
    async def _noop(_s: object, _i: int) -> bool:
        return True

    return RunnerTask(session, _noop, total_steps=total)  # type: ignore[arg-type]


async def _elapsed(coro: object) -> float:
    started = time.monotonic()
    await coro  # type: ignore[misc]
    return (time.monotonic() - started) * 1000


# ─── FR-101 — 간격이 실제로 생긴다 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_slow_pacing_sleeps_between_steps() -> None:
    session = _FakeSession(pacing=RunPacing.SLOW)
    task = _task(session)
    took = await _elapsed(task._pace(next_index=1))
    assert took >= 1200, f"`느림` 인데 {took:.0f}ms 만 쉬었다"


@pytest.mark.asyncio
async def test_fast_pacing_does_not_sleep() -> None:
    """`빠름` 은 004 이전 동작이다 — 아무것도 얹지 않는다."""
    session = _FakeSession(pacing=RunPacing.FAST)
    task = _task(session)
    took = await _elapsed(task._pace(next_index=1))
    assert took < 50, f"`빠름` 인데 {took:.0f}ms 쉬었다"


# ─── spec 엣지 케이스 — 쉬지 않아야 하는 자리 ──────────────────────────────


@pytest.mark.asyncio
async def test_no_delay_after_the_last_step() -> None:
    """마지막 Step 뒤에는 쉬지 않는다.

    끝난 실행이 끝나지 않은 것처럼 보이면 안 된다. 존재하지 않는 다음 Step 을 기다릴
    이유도 없다.
    """
    session = _FakeSession(pacing=RunPacing.SLOW)
    task = _task(session, total=3)
    took = await _elapsed(task._pace(next_index=3))
    assert took < 50, f"마지막 Step 뒤에 {took:.0f}ms 쉬었다"


@pytest.mark.asyncio
async def test_no_delay_while_ai_is_deciding() -> None:
    """AI 가 다음 동작을 판단하는 시간에는 간격을 적용하지 않는다 (spec 엣지 케이스).

    그 시간은 Step 실행이 아니다. 거기에 간격을 더하면 이미 느린 것을 더 느리게 만들 뿐,
    사람이 볼 것이 늘지 않는다.
    """
    session = _FakeSession(state=SessionState.AI_RUNNING, pacing=RunPacing.SLOW)
    task = _task(session)
    took = await _elapsed(task._pace(next_index=1))
    assert took < 50, f"AI 실행 구간에서 {took:.0f}ms 쉬었다"


@pytest.mark.asyncio
async def test_no_delay_when_already_paused() -> None:
    """이미 멈춰 있으면 더 쉬지 않는다. 일시정지 지점이 그다음에 온다."""
    session = _FakeSession(pacing=RunPacing.SLOW)
    session.request_pause()
    task = _task(session)
    took = await _elapsed(task._pace(next_index=1))
    assert took < 50


# ─── FR-106 — 간격 도중 일시정지 ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_pause_request_cuts_the_gap_short() -> None:
    """일시정지 요청이 들어오면 간격이 끝나기를 기다리지 않는다.

    `_resume` 만으로는 불가능하다 — `asyncio.Event` 는 set 을 기다릴 수 있을 뿐 clear 를
    기다릴 수 없다 (research R6). 이 테스트가 `_pause_requested` 의 존재 이유다.
    """
    session = _FakeSession(pacing=RunPacing.SLOW)
    task = _task(session)

    async def _pause_soon() -> None:
        await asyncio.sleep(0.1)
        session.request_pause()

    started = time.monotonic()
    await asyncio.gather(task._pace(next_index=1), _pause_soon())
    took = (time.monotonic() - started) * 1000
    assert took < 500, f"일시정지 요청 후에도 {took:.0f}ms 더 잤다"


@pytest.mark.asyncio
async def test_gap_is_cancellable() -> None:
    """중지는 태스크 취소다. 간격이 취소를 막지 않는다."""
    session = _FakeSession(pacing=RunPacing.SLOW)
    task = _task(session)
    running = asyncio.create_task(task._pace(next_index=1))
    await asyncio.sleep(0.05)
    running.cancel()
    started = time.monotonic()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert (time.monotonic() - started) * 1000 < 200


# ─── FR-108 — 한 스텝씩 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_step_pacing_pauses_instead_of_sleeping() -> None:
    """`한 스텝씩` 은 자지 않고 **기존 `PAUSED` 에 들어간다** (research R7).

    새 상태를 만들지 않는 것이 요점이다. 편집·조작 허용 규칙이 이미 검증된 경로를 그대로
    쓴다.
    """
    session = _FakeSession(pacing=RunPacing.STEP)
    task = _task(session)
    took = await _elapsed(task._pace(next_index=1))
    assert session.state is SessionState.PAUSED
    assert took < 50, "자동 일시정지는 시간이 아니라 사용자 지시로 풀린다"


@pytest.mark.asyncio
async def test_step_pacing_does_not_pause_after_the_last_step() -> None:
    """마지막 Step 뒤에는 멈추지 않는다 — 실행이 끝나야 한다."""
    session = _FakeSession(pacing=RunPacing.STEP)
    task = _task(session, total=2)
    await task._pace(next_index=2)
    assert session.state is SessionState.REPLAYING


# ─── FR-103 — 속도는 매 경계에서 다시 읽는다 ───────────────────────────────


@pytest.mark.asyncio
async def test_pacing_is_reread_at_every_boundary() -> None:
    """실행 중 변경이 다음 Step 부터 반영된다.

    값을 루프 시작 때 잡아 두면 실행 중 변경이 그 실행에 영향을 주지 못한다.
    """
    session = _FakeSession(pacing=RunPacing.FAST)
    task = _task(session)
    assert await _elapsed(task._pace(next_index=1)) < 50

    session.pacing = RunPacing.SLOW
    assert await _elapsed(task._pace(next_index=1)) >= 1200
