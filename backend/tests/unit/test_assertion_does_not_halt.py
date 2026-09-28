"""검증 실패가 그 뒤를 가리지 않는다 (020 T020·T022 · FR-033~FR-038).

## 이 제품의 목적에서 직접 나오는 요구

「저장된 스텝이 **끝까지** 패스하는지 확인한다」가 목적이면, 중간에 멈추는 실행은 답을
주지 못한다. 020 이전의 실행기는 Step 이 실패하면 거기서 멈췄다 — 알려진 결함이 7번에
있으면 8~20번이 영영 돌지 않고, **그 구간의 회귀는 아무도 모른다.** 결함 하나가 테스트의
나머지 전부를 눈멀게 한다.

## 왜 브라우저 없이 재는가

여기서 재는 것은 **판단**이다 — 어떤 Step 의 실패가 실행을 멈추는가, 그때 「멈춘 자리」가
어디로 기록되는가. 브라우저를 지나지 않으며, 실제 재생은 브라우저 계층이 돈다
(`test_step_screenshot_lifecycle.py` 가 세운 선례).
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from itb.domain.assertion import Assertion, AssertionKind
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.run_result import StepOutcome
from itb.domain.step import AssertionStep, ClickStep, Step
from itb.domain.test_case import Test
from itb.execution.artifacts import ArtifactCollector
from itb.execution.runner import ReplayEngine
from itb.execution.step_executor import StepFailure


def _target() -> TargetLocator:
    return TargetLocator(css=Candidate(value="#a", status=CandidateStatus.VERIFIED))


def _click(index: int) -> ClickStep:
    return ClickStep(id=f"step-{index:02d}", label=f"동작 {index}", target=_target())


def _assert(index: int) -> AssertionStep:
    return AssertionStep(
        id=f"step-{index:02d}",
        label=f"검증 {index}",
        assertion=Assertion(kind=AssertionKind.TEXT, value="저장되었습니다"),
    )


class _FakeSession:
    session_id = "s-1"

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def find_tab(self, _index: int) -> None:
        return None

    def open_tabs(self) -> list[object]:
        return []

    async def emit(self, name: str, **payload: Any) -> None:
        self.events.append((name, payload))


class _FakeContext:
    def on(self, *_a: Any, **_k: Any) -> None:
        return None


class _ScriptedExecutor:
    """지정한 Step id 에서만 실패한다. 실패 사유가 흔들리면 판정을 못 한다."""

    def __init__(self, failing: set[str]) -> None:
        self.failing = failing
        self.ran: list[str] = []

    async def execute(self, step: Step) -> Any:
        self.ran.append(step.id)
        if step.id in self.failing:
            raise StepFailure(f"{step.id} 실패")

        class _Record:
            attempts: list[Any] = []
            tab_wait_ms = 0
            element_wait_ms = 0
            resolved_candidate = "css"
            disagreement: list[str] = []

        return _Record()


def _engine(
    tmp_path: pathlib.Path, steps: list[Step], failing: set[str]
) -> tuple[ReplayEngine, _ScriptedExecutor, _FakeSession]:
    class _FakeResolver:
        def resolved_sensitive_values(self) -> list[str]:
            return []

    session = _FakeSession()
    executor = _ScriptedExecutor(failing)
    engine = ReplayEngine(
        session=session,  # type: ignore[arg-type]
        test=Test(
            id="TC-001",
            name="끝까지 도는 테스트",
            authoring_mode="record",
            start_url="http://127.0.0.1:1/",
            steps=steps,
        ),
        executor=executor,  # type: ignore[arg-type]
        resolver=_FakeResolver(),  # type: ignore[arg-type]
        collector=ArtifactCollector(_FakeContext()),  # type: ignore[arg-type]
        run_dir=tmp_path / ".runs" / "TC-001",
        project_root=tmp_path,
        write_result=lambda _r: None,
    )
    return engine, executor, session


# ─── 검증 실패는 멈추지 않는다 (FR-033) ─────────────────────────────────────


@pytest.mark.anyio
async def test_a_failing_assertion_lets_the_run_continue(tmp_path: pathlib.Path) -> None:
    """**이 한 줄이 020 의 US6 전부다.**

    앞쪽 검증이 실패해도 뒤 Step 이 전부 돈다 — 그래야 뒤쪽의 회귀를 볼 수 있다.
    """
    steps: list[Step] = [_click(1), _assert(2), _click(3), _assert(4), _click(5)]
    engine, executor, session = _engine(tmp_path, steps, failing={"step-02"})

    for index in range(len(steps)):
        keep_going = await engine.run_step(session, index)  # type: ignore[arg-type]
        assert keep_going, f"index {index} 에서 멈췄다"

    assert executor.ran == ["step-01", "step-02", "step-03", "step-04", "step-05"]
    assert [r.outcome for r in engine.results] == [
        StepOutcome.PASS,
        StepOutcome.FAIL,
        StepOutcome.PASS,
        StepOutcome.PASS,
        StepOutcome.PASS,
    ]


@pytest.mark.anyio
async def test_failures_after_a_failing_assertion_are_each_recorded(
    tmp_path: pathlib.Path,
) -> None:
    """뒤따르는 실패도 개별로 남는다 (FR-035).

    「실행 안 함」으로 뭉뚱그리면 사용자가 어디까지 번진 것인지 볼 수 없다.
    """
    steps: list[Step] = [_assert(1), _assert(2), _assert(3)]
    engine, _, session = _engine(tmp_path, steps, failing={"step-01", "step-03"})

    for index in range(len(steps)):
        await engine.run_step(session, index)  # type: ignore[arg-type]

    assert [r.outcome for r in engine.results] == [
        StepOutcome.FAIL,
        StepOutcome.PASS,
        StepOutcome.FAIL,
    ]
    assert not any(r.outcome is StepOutcome.NOT_RUN for r in engine.results)


@pytest.mark.anyio
async def test_step_failed_is_still_emitted_for_assertions(tmp_path: pathlib.Path) -> None:
    """화면은 실패를 즉시 봐야 한다.

    이 이벤트가 「실행이 멈췄다」를 뜻한 적은 없다 — 멈춤은 결과의 `not_run` 이 말한다.
    """
    engine, _, session = _engine(tmp_path, [_assert(1)], failing={"step-01"})
    await engine.run_step(session, 0)  # type: ignore[arg-type]
    assert any(name == "step_failed" for name, _ in session.events)


# ─── 동작 Step 은 그대로 멈춘다 (FR-034) ────────────────────────────────────


@pytest.mark.anyio
async def test_a_failing_action_still_halts(tmp_path: pathlib.Path) -> None:
    """화면 상태가 뒤따르는 Step 의 전제를 잃었으므로 이어서 도는 것이 의미가 없다."""
    steps: list[Step] = [_click(1), _click(2), _click(3)]
    engine, executor, session = _engine(tmp_path, steps, failing={"step-02"})

    assert await engine.run_step(session, 0)  # type: ignore[arg-type]
    assert not await engine.run_step(session, 1), "동작 실패가 실행을 멈추지 않았다"  # type: ignore[arg-type]
    assert executor.ran == ["step-01", "step-02"]
    assert engine.results[2].outcome is StepOutcome.NOT_RUN


# ─── 「멈춘 자리」의 의미는 보존된다 (FR-038) ───────────────────────────────


@pytest.mark.anyio
async def test_assertion_failures_never_create_a_stopping_point(
    tmp_path: pathlib.Path,
) -> None:
    """`failed_index` 의 뜻은 「실패한 Step」이 아니라 **「실행이 멈춘 자리」**다.

    재시도·건너뛰기·인수 UI 가 그 자리를 근거로 동작한다. 검증 실패로 설정하면 여러
    검증이 실패할 때 마지막 것이 「멈춘 자리」가 되어, 사용자가 거기서 재시도를 누르면
    엉뚱한 곳으로 간다.
    """
    steps: list[Step] = [_assert(1), _assert(2), _assert(3)]
    engine, _, session = _engine(tmp_path, steps, failing={"step-01", "step-02", "step-03"})

    for index in range(len(steps)):
        await engine.run_step(session, index)  # type: ignore[arg-type]

    assert engine.has_failed_step(), "실패는 분명히 있었다"
    assert engine.blocking_failure_index() is None, "검증 실패가 멈춘 자리를 만들었다"


@pytest.mark.anyio
async def test_an_action_failure_does_create_a_stopping_point(
    tmp_path: pathlib.Path,
) -> None:
    """반대쪽도 확인한다 — 멈춘 자리가 만들어지지 않으면 재시도가 대상을 잃는다."""
    steps: list[Step] = [_assert(1), _click(2)]
    engine, _, session = _engine(tmp_path, steps, failing={"step-01", "step-02"})

    await engine.run_step(session, 0)  # type: ignore[arg-type]
    await engine.run_step(session, 1)  # type: ignore[arg-type]

    assert engine.blocking_failure_index() == 1


# ─── 건너뛰기는 멈춘 자리 하나만 (FR-039) ───────────────────────────────────


@pytest.mark.anyio
async def test_skipping_leaves_the_unskipped_assertion_failure_intact(
    tmp_path: pathlib.Path,
) -> None:
    """**이것이 F1 의 실제 기전이다.**

    020 이전의 `clear_failed_steps` 는 결과에 있는 **모든** `FAIL` 을 건너뜀으로 바꿨다.
    그때는 정확했다 — 실패가 곧 중단이라 `FAIL` 이 하나뿐이었고 그 하나가 곧 사용자가
    고른 것이었다. FR-033 이 그 전제를 깨는 순간, 아무도 건너뛰지 않은 회귀까지 증거가
    사라진다. 결말 판정에 닿기도 전에 지워지는 것이다.
    """
    steps: list[Step] = [_assert(1), _click(2), _click(3)]
    engine, _, session = _engine(tmp_path, steps, failing={"step-01", "step-02"})

    await engine.run_step(session, 0)  # type: ignore[arg-type]
    await engine.run_step(session, 1)  # type: ignore[arg-type]

    engine.note_skipped_failures()
    engine.skip_blocking_failure()

    assert engine.results[0].outcome is StepOutcome.FAIL, "회귀의 증거가 지워졌다"
    assert engine.results[1].outcome is StepOutcome.SKIPPED
    assert engine.blocking_failure_index() is None


@pytest.mark.anyio
async def test_skipping_with_no_stopping_point_is_a_no_op(tmp_path: pathlib.Path) -> None:
    """멈춘 자리가 없으면 건너뛸 것도 없다. 조용히 아무것도 하지 않는다."""
    engine, _, session = _engine(tmp_path, [_assert(1)], failing={"step-01"})
    await engine.run_step(session, 0)  # type: ignore[arg-type]

    engine.skip_blocking_failure()
    assert engine.results[0].outcome is StepOutcome.FAIL
