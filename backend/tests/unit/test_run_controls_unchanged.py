"""검증 실패가 있어도 실행 제어가 그대로다 (020 T021 · FR-037·FR-039).

## 이 파일이 지키는 것 — 「바뀌지 않아야 하는 것」

명세는 바뀌는 것을 적기 쉽고 **바뀌지 않아야 하는 것을 빠뜨리기 쉽다.** 020 의
체크리스트(C 구역)가 그 빈칸을 잡아 FR-037 을 만들었고, 이 파일이 그 표를 검사로
고정한다.

기존 검증이 각 제어를 이미 본다 (`test_stop_outcome.py`·`test_partial_run_result.py`
등). **여기서 새로 재는 것은 그것들과 다르다** — 그 검증들은 검증 실패가 **없는**
실행을 본다. FR-033 이 만든 새 상태는 「`FAIL` 이 여럿 쌓인 채 계속 도는 실행」이고,
제어들이 그 상태에서도 같은지는 아무도 보지 않았다.

## 왜 브라우저 없이 재는가

재는 것이 **판단**이기 때문이다 — 어떤 상태에서 어떤 결말이 나오는가, 건너뛰기가
무엇을 건너뛰는가. `test_assertion_does_not_halt.py` 와 같은 하네스를 쓴다.

## FR-037 의 여덟 중 **다섯**을 여기서 잰다

| 제어 | 여기서 재는가 | 왜 |
|---|---|---|
| 재시도 | ✅ | 멈춘 자리를 근거로 한다 — 020 이 그 값을 건드렸다 |
| 건너뛰고 계속 | ✅ | FR-039 가 판정을 바꿨다 |
| 부분 실행 | ✅ | `SKIPPED` 표기가 FR-039 의 조건과 겹친다 |
| 중지 | ✅ | 계속 진행 규칙보다 우선해야 한다 |
| 세션 유실 | ✅ | 같은 이유 |
| **인수 후 재개** | ❌ | 세션 상태 기계 소관이며 020 이 건드리지 않았다 |
| **일시정지·재개** | ❌ | 같음 |
| **실행 속도 조절** | ❌ | `RunPacing` 소관이며 020 이 건드리지 않았다 |

**아래 셋을 빠뜨린 것이 아니라 여기가 잴 자리가 아니다.** 020 이 고친 것은
`run_step` 의 중단 판단과 결말 판정이고, 그 셋은 어느 쪽도 지나지 않는다. 기존
검증(`test_pause_transition.py`·`test_runner_pacing.py`·US5 의 인수 재개)이 그대로
통과하는 것이 그것들의 근거다 — 통과하지 않으면 전량 검증에서 드러난다.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from itb.domain.assertion import Assertion, AssertionKind
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.run_result import (
    Outcome,
    RunScope,
    StepOutcome,
    attempted_of,
    decide_outcome,
    scope_of,
)
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
    def __init__(self, failing: set[str]) -> None:
        self.failing = failing

    async def execute(self, step: Step) -> Any:
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
) -> tuple[ReplayEngine, _FakeSession]:
    class _FakeResolver:
        def resolved_sensitive_values(self) -> list[str]:
            return []

    session = _FakeSession()
    engine = ReplayEngine(
        session=session,  # type: ignore[arg-type]
        test=Test(
            id="TC-001",
            name="제어 회귀",
            authoring_mode="record",
            start_url="http://127.0.0.1:1/",
            steps=steps,
        ),
        executor=_ScriptedExecutor(failing),  # type: ignore[arg-type]
        resolver=_FakeResolver(),  # type: ignore[arg-type]
        collector=ArtifactCollector(_FakeContext()),  # type: ignore[arg-type]
        run_dir=tmp_path / ".runs" / "TC-001",
        project_root=tmp_path,
        write_result=lambda _r: None,
    )
    return engine, session


async def _run_all(engine: ReplayEngine, session: _FakeSession, count: int) -> None:
    for index in range(count):
        if not await engine.run_step(session, index):  # type: ignore[arg-type]
            return


# 검증 하나가 실패한 채로 계속 돌고, 뒤쪽 동작 하나가 실패해 멈춘다 — 020 이 만든 새 상태.
MIXED: list[Step] = [_click(1), _assert(2), _click(3), _click(4)]
MIXED_FAILING = {"step-02", "step-03"}


# ─── 1. 재시도 — 멈춘 자리를 근거로 한다 ────────────────────────────────────


@pytest.mark.anyio
async def test_retry_targets_the_action_failure_not_the_assertion(
    tmp_path: pathlib.Path,
) -> None:
    """재시도 UI 가 가리키는 자리는 **동작 실패**다.

    검증 실패가 멈춘 자리를 만들면, 사용자가 재시도를 누를 때 이미 지나온 곳으로 간다.
    """
    engine, session = _engine(tmp_path, MIXED, MIXED_FAILING)
    await _run_all(engine, session, len(MIXED))

    assert engine.blocking_failure_index() == 2, "멈춘 자리가 동작 실패가 아니다"
    assert engine.results[1].outcome is StepOutcome.FAIL, "검증은 실패로 남아 있다"


# ─── 2. 건너뛰고 계속 — `PARTIAL_PASS` 판정 (FR-039) ───────────────────────


@pytest.mark.anyio
async def test_skip_does_not_swallow_the_assertion_failure(
    tmp_path: pathlib.Path,
) -> None:
    """**건너뛰기는 멈춘 자리 하나만 건너뛴다.**

    020 이전에는 모든 `FAIL` 을 `SKIPPED` 로 바꿨고, 그때는 정확했다 — `FAIL` 이
    하나뿐이었기 때문이다. 지금 그렇게 하면 아무도 건너뛰지 않은 회귀의 증거가
    결말 판정에 닿기 전에 사라진다.
    """
    engine, session = _engine(tmp_path, MIXED, MIXED_FAILING)
    await _run_all(engine, session, len(MIXED))

    engine.note_skipped_failures()
    engine.skip_blocking_failure()

    assert engine.results[1].outcome is StepOutcome.FAIL, "회귀의 증거가 지워졌다"
    assert engine.results[2].outcome is StepOutcome.SKIPPED
    assert (
        decide_outcome(engine.results, skipped_failures=True) is Outcome.FAIL
    ), "건너뛰지 않은 실패가 남았는데 부분 성공으로 판정됐다"


def test_a_pure_skip_is_still_partial_pass() -> None:
    """검증 실패가 없으면 **현행 그대로다** — 005 의 U-05 수정을 되돌리지 않는다."""
    from itb.domain.run_result import StepResult

    results = [
        StepResult(step_id="step-01", index=0, label="a", outcome=StepOutcome.PASS),
        StepResult(step_id="step-02", index=1, label="b", outcome=StepOutcome.SKIPPED),
        StepResult(step_id="step-03", index=2, label="c", outcome=StepOutcome.PASS),
    ]
    assert decide_outcome(results, skipped_failures=True) is Outcome.PARTIAL_PASS


# ─── 3·4. 중지와 세션 유실은 계속 진행보다 우선한다 ─────────────────────────


@pytest.mark.anyio
async def test_stop_wins_even_right_after_an_assertion_failed(
    tmp_path: pathlib.Path,
) -> None:
    """사용자가 누른 중지는 실패가 아니다 (US6 AS-5).

    계속 진행 규칙이 중지를 무시하면, 사용자는 멈추라고 했는데 계속 도는 화면을 본다.
    """
    engine, session = _engine(tmp_path, MIXED, MIXED_FAILING)
    await engine.run_step(session, 0)  # type: ignore[arg-type]
    await engine.run_step(session, 1)  # type: ignore[arg-type]

    assert engine.results[1].outcome is StepOutcome.FAIL
    assert decide_outcome(engine.results, stop_requested=True) is Outcome.STOPPED


@pytest.mark.anyio
async def test_session_loss_wins_over_everything(tmp_path: pathlib.Path) -> None:
    """유실은 사고이며 사용자가 요청한 중단이 아니다."""
    engine, session = _engine(tmp_path, MIXED, MIXED_FAILING)
    await _run_all(engine, session, len(MIXED))

    assert (
        decide_outcome(
            engine.results, session_lost=True, stop_requested=True, skipped_failures=True
        )
        is Outcome.FAIL
    )


# ─── 5. 부분 실행 — 범위와 건너뜀 표기 ──────────────────────────────────────


@pytest.mark.anyio
async def test_partial_run_marks_earlier_steps_as_skipped(
    tmp_path: pathlib.Path,
) -> None:
    """부분 실행의 앞선 Step 은 `SKIPPED` 다 — 그것이 `PARTIAL_PASS` 를 만들지 않는다.

    `decide_outcome` 의 docstring 이 경고하는 함정이며, FR-039 가 조건을 좁힐 때
    다시 밟기 쉬운 자리다.
    """
    steps: list[Step] = [_click(1), _click(2), _assert(3)]
    engine, session = _engine(tmp_path, steps, failing=set())
    engine.skip_before(2)
    await engine.run_step(session, 2)  # type: ignore[arg-type]

    assert [r.outcome for r in engine.results] == [
        StepOutcome.SKIPPED,
        StepOutcome.SKIPPED,
        StepOutcome.PASS,
    ]
    assert scope_of(2) is RunScope.PARTIAL
    assert decide_outcome(engine.results) is Outcome.PASS, (
        "부분 실행이 부분 성공으로 판정됐다 — 건너뛰기와 구별되지 않는다"
    )


# ─── 6. 분모 — 실제로 실행한 것이 늘어난다 ──────────────────────────────────


@pytest.mark.anyio
async def test_continuing_grows_the_attempted_count(tmp_path: pathlib.Path) -> None:
    """검증 실패 뒤의 Step 이 **실제로 실행되므로** 분모에 들어간다.

    이것은 의도한 변화다. 020 이전에는 그 Step 들이 `NOT_RUN` 이었고, 그때도 분모에
    남았다 — 「실행 대상이었지만 도달하지 못한 것」이기 때문이다. 바뀌는 것은 분자다.
    """
    steps: list[Step] = [_assert(1), _click(2), _click(3)]
    engine, session = _engine(tmp_path, steps, failing={"step-01"})
    await _run_all(engine, session, len(steps))

    assert attempted_of(engine.results) == 3
    assert sum(1 for r in engine.results if r.outcome is StepOutcome.PASS) == 2


# ─── 7. 이벤트 — 실패는 즉시 보인다 ─────────────────────────────────────────


@pytest.mark.anyio
async def test_each_failure_is_announced_even_while_continuing(
    tmp_path: pathlib.Path,
) -> None:
    """`step_failed` 가 실패마다 나간다.

    이 이벤트가 「실행이 멈췄다」를 뜻한 적은 없다 — 화면은 실패를 즉시 봐야 한다.
    """
    steps: list[Step] = [_assert(1), _assert(2), _click(3)]
    engine, session = _engine(tmp_path, steps, failing={"step-01", "step-02"})
    await _run_all(engine, session, len(steps))

    failed = [name for name, _ in session.events if name == "step_failed"]
    assert len(failed) == 2, f"실패 두 건 중 알려지지 않은 것이 있다: {failed}"
