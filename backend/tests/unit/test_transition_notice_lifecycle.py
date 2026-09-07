"""005 T115 — 전이 안내는 실행이 끝나면 걷힌다 (FR-146 · 재점검 U-04-a).

일시정지 요청이 10초 안에 성립하지 않으면 서버는 "아직 실행 중입니다" 안내를 붙인다.
그 문장은 **그 순간에만** 참이다. 실행이 끝나면 거짓이 되는데, 재점검 리포트는 실행이
끝난 뒤에도 그것이 화면에 남아 있는 것을 봤다 — 같은 화면의 배지가 「실행 종료」라고
말하는 옆에서 「아직 실행 중」이라고 말하는 상태였다.

**브라우저를 띄우지 않는다.** 안내의 수명은 세션 상태와 러너 종료 경로의 문제이고,
그 둘은 가짜 세션으로 검증된다.

이 파일이 지키는 것은 두 가지다.

1. 보통의 편집 경고는 **남는다** — "이미 실행된 Step 이다" 같은 사실은 시간이 지나도
   그대로다. 전이 안내만 걷는 것이 요구사항이며, 전부 걷으면 다른 정보를 잃는다.
2. 러너의 `finally` 는 **신호만 올린다** — 거기서 세션 메서드를 부르면 그것이 실패하는
   순간 완료를 기다리는 모든 것이 영구히 멈춘다. 그 회귀를 이 파일이 직접 잡는다.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

from itb.domain.run_pacing import RunPacing
from itb.execution import runner as runner_mod
from itb.execution.runner import RunnerTask
from tests.unit.test_runner_pacing import _FakeSession

TRANSIENT = "Step 하나가 10초 안에 끝나지 않아 아직 실행 중입니다."
DURABLE = "Step 01 은 이미 실행된 Step 입니다."


def _session() -> _FakeSession:
    session = _FakeSession(pacing=RunPacing.FAST)
    session.add_edit_warning(DURABLE)
    session.add_edit_warning(TRANSIENT, transient=True)
    return session


async def _run_to_completion(session: _FakeSession, total: int = 3) -> RunnerTask:
    async def run_one(_s: object, _index: int) -> bool:
        return True

    runner = RunnerTask(session, run_one, total_steps=total)  # type: ignore[arg-type]
    runner.start()
    for _ in range(400):
        if not runner.running:
            break
        await asyncio.sleep(0.005)
    assert not runner.running, "러너가 끝나지 않았다 — 완료 신호가 올라가지 않는다"
    return runner


@pytest.mark.asyncio
async def test_finished_run_drops_the_transition_notice() -> None:
    """실행이 끝나면 전이 안내가 사라진다 (FR-146)."""
    session = _session()
    await _run_to_completion(session)
    assert TRANSIENT not in session.edit_warnings, (
        "실행이 끝났는데 「아직 실행 중」이 남았다 — 화면이 배지와 반대되는 말을 한다"
    )


@pytest.mark.asyncio
async def test_finished_run_keeps_durable_warnings() -> None:
    """보통의 편집 경고는 남는다 — 전부 걷으면 다른 정보를 잃는다."""
    session = _session()
    await _run_to_completion(session)
    assert DURABLE in session.edit_warnings


@pytest.mark.asyncio
async def test_clearing_republishes_so_the_screen_learns_of_it() -> None:
    """걷었다는 사실을 이벤트로 알린다.

    **빈 목록이라도 보내야 한다.** "비어 있으면 보내지 않는다" 규칙에 걸리면 화면은 낡은
    문장을 계속 들고 있는다 — 그것이 이 결함의 형태였다.
    """
    session = _FakeSession(pacing=RunPacing.FAST)
    session.add_edit_warning(TRANSIENT, transient=True)
    await _run_to_completion(session)
    published = [p for name, p in session.events if name == "edit_warning"]
    assert published, "걷어낸 사실을 알리지 않았다"
    assert TRANSIENT not in published[-1]["messages"]


@pytest.mark.asyncio
async def test_no_transition_notice_means_no_extra_event() -> None:
    """걷을 것이 없으면 이벤트를 만들지 않는다 — 실행마다 잡음이 하나 늘면 안 된다."""
    session = _FakeSession(pacing=RunPacing.FAST)
    session.add_edit_warning(DURABLE)
    await _run_to_completion(session)
    assert not [name for name, _ in session.events if name == "edit_warning"]


def test_runner_finally_only_raises_signals() -> None:
    """러너의 `finally` 는 세션을 부르지 않는다.

    구조로 본다 — 동작으로 잡으려면 세션 메서드를 실패시키는 가짜가 필요하고, 그 가짜는
    "표면이 갈린 가짜" 를 또 하나 만드는 일이다. 이 결함이 실제로 그렇게 났다: `finally`
    안의 세션 호출이 낡은 가짜에서 AttributeError 를 던졌고, 완료 신호가 올라가지 않아
    러너를 기다리는 테스트가 영구히 멈췄다.

    `finally` 에 허용하는 것은 `self._finished` · `self._boundary` 신호뿐이다.
    """
    source = inspect.getsource(RunnerTask._loop)  # noqa: SLF001 - 구조 점검이 목적이다
    lines = source.splitlines()
    at = next(i for i, line in enumerate(lines) if line.strip() == "finally:")
    body = [line.strip() for line in lines[at + 1 :] if line.strip()]
    offenders = [
        line
        for line in body
        if not line.startswith("#") and "self._session" in line
    ]
    assert not offenders, (
        f"러너의 finally 가 세션을 부른다 — 그 호출이 실패하면 완료 신호가 "
        f"올라가지 않는다: {offenders}"
    )
    assert runner_mod is not None
