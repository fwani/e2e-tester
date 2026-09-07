"""006 T054~T056 — 지정한 Step 직전에서 멈춘다 (US3).

`specs/006-edit-saved-test/contracts/rest-api.md` §3 · research R7.

**브라우저를 띄우지 않는다.** `RunnerTask` 는 진행·일시정지·취소만 책임지므로 가짜 세션과
가짜 Step 실행기로 검증된다 — 그 설계가 이 테스트를 가능하게 한다.

**가짜 세션은 004 의 것을 그대로 쓴다** (`tests.unit.test_runner_pacing._FakeSession`).
두 벌로 만들면 러너의 표면이 갈리고, 한쪽만 최신인 가짜가 생긴다.

이 파일이 지키는 것: 사용자가 **「일시정지」를 누르지 않고도** 편집 가능한 상태에 도달한다
(FR-201 · SC-305). 그것이 006 이 없애려던 E-06 이다.
"""

from __future__ import annotations

import asyncio

import pytest

from itb.domain.run_pacing import RunPacing
from itb.execution.runner import RunnerTask
from itb.execution.state_machine import Command, SessionState
from tests.unit.test_runner_pacing import _FakeSession


def _runner(
    session: _FakeSession, total: int, pause_before: int | None, executed: list[int]
) -> RunnerTask:
    async def run_one(_s: object, index: int) -> bool:
        executed.append(index)
        return True

    return RunnerTask(
        session,  # type: ignore[arg-type]
        run_one,
        total_steps=total,
        start_index=0,
        pause_before_index=pause_before,
    )


async def _run_until_settled(
    total: int, pause_before: int | None
) -> tuple[_FakeSession, list[int], RunnerTask]:
    """멈추거나 끝날 때까지 돌린다.

    일시정지 요청을 **테스트가 세우지 않는다** — 러너가 스스로 멈추는지 보는 것이 목적
    이므로, 사람의 요청을 흉내 내면 검증이 무의미해진다.
    """
    session = _FakeSession(pacing=RunPacing.FAST)
    executed: list[int] = []
    runner = _runner(session, total, pause_before, executed)
    runner.start()
    for _ in range(400):
        if session.is_paused or runner.at_boundary:
            break
        await asyncio.sleep(0.005)
    return session, executed, runner


@pytest.mark.asyncio
async def test_pauses_before_the_named_step_after_running_the_earlier_ones() -> None:
    """FR-200 — 선행 Step 은 실행하고, 그 Step 은 실행하지 않는다.

    다시 집기는 그 Step 이 다루는 요소가 **화면에 있어야** 성립하므로 선행 Step 을
    실행한다. 멈춤 지점이 "실행한 뒤" 가 아니라 "직전" 인 것은 고치려는 Step 이 대개
    실패하는 Step 이기 때문이다 — 실행한 뒤에 멈추면 고치기 전에 실패가 먼저 난다.
    """
    session, executed, _ = await _run_until_settled(total=7, pause_before=5)
    assert executed == [0, 1, 2, 3, 4]
    assert session.state is SessionState.PAUSED
    assert session.current_step_index == 5


@pytest.mark.asyncio
async def test_pause_before_zero_runs_nothing() -> None:
    """계약 §3 — `0` 이면 시작 주소만 열린 상태에서 멈춘다."""
    session, executed, _ = await _run_until_settled(total=7, pause_before=0)
    assert executed == []
    assert session.state is SessionState.PAUSED
    assert session.current_step_index == 0


@pytest.mark.asyncio
async def test_user_never_had_to_press_pause() -> None:
    """FR-201 · SC-305 · E-06 — 러너가 스스로 멈춘다.

    이 테스트는 `request_pause()` 를 한 번도 부르지 않는다. 그런데도 멈췄다는 것이
    "달리는 실행을 잡을 필요가 없다" 의 증거다.
    """
    session, _, _ = await _run_until_settled(total=7, pause_before=3)
    assert session.is_paused


@pytest.mark.asyncio
async def test_pausing_happens_only_once() -> None:
    """「계속하기」 뒤 같은 자리에 다시 걸리면 실행이 앞으로 나아가지 못한다."""
    session = _FakeSession(pacing=RunPacing.FAST)
    executed: list[int] = []
    runner = _runner(session, 4, 2, executed)
    runner.start()
    for _ in range(400):
        if session.is_paused:
            break
        await asyncio.sleep(0.005)
    assert executed == [0, 1]

    session.mark_running()
    session.state = SessionState.REPLAYING
    await asyncio.wait_for(runner.wait(), timeout=5)
    assert executed == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_without_pause_before_index_behaviour_is_unchanged() -> None:
    """기존 클라이언트 무영향 — 생략하면 끝까지 돈다."""
    session = _FakeSession(pacing=RunPacing.FAST)
    executed: list[int] = []
    runner = _runner(session, 4, None, executed)
    runner.start()
    await asyncio.wait_for(runner.wait(), timeout=5)
    assert executed == [0, 1, 2, 3]
    assert not session.is_paused


@pytest.mark.asyncio
async def test_step_pacing_still_works_beside_the_new_gate() -> None:
    """T056 · 원칙 III — 004 의 `한 스텝씩` 을 흔들지 않는다.

    상태 집합에 새 상태가 늘지 않았다는 것도 함께 본다 — 둘 다 같은 `PAUSED` 로 들어간다.
    """
    session = _FakeSession(pacing=RunPacing.STEP)
    executed: list[int] = []
    runner = _runner(session, 3, None, executed)
    runner.start()
    for _ in range(400):
        if session.is_paused:
            break
        await asyncio.sleep(0.005)
    assert executed == [0]
    assert session.state is SessionState.PAUSED
    # 새 상태가 없다 — 006 이 상태 기계를 건드리지 않았다.
    assert not [s for s in SessionState if "edit" in s.value.lower()]


@pytest.mark.asyncio
async def test_pause_gate_uses_the_existing_pause_command() -> None:
    """R7 — 새 명령을 만들지 않았다. 004 와 같은 전이를 쓴다."""
    assert Command.PAUSE in set(Command)
    session, _, _ = await _run_until_settled(total=3, pause_before=1)
    assert session.state is SessionState.PAUSED
