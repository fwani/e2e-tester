"""결말 판정 (005 T008 · FR-131·FR-137).

**이 테스트가 지키는 것은 판정이 한 곳에 있다는 사실이다.** 이전 구현은
`Outcome.PASS if passed and not session_lost else Outcome.FAIL` 한 줄이었고, 그 `passed`
불리언을 호출자마다 따로 계산했다. 그래서 사용자가 누른 중지가 실패로 기록됐고(U-03),
실패 Step 을 건너뛴 실행이 완료로 표시됐다(U-05).
"""

from __future__ import annotations

import pytest

from itb.domain.run_result import (
    Outcome,
    RunScope,
    StepOutcome,
    StepResult,
    attempted_of,
    counts_as_failure,
    decide_outcome,
    scope_of,
)


def step(index: int, outcome: StepOutcome) -> StepResult:
    return StepResult(
        step_id=f"step-{index + 1:02d}", index=index, label=f"Step {index + 1}", outcome=outcome
    )


ALL_PASS = [step(0, StepOutcome.PASS), step(1, StepOutcome.PASS)]
WITH_FAILURE = [
    step(0, StepOutcome.PASS),
    step(1, StepOutcome.FAIL),
    step(2, StepOutcome.NOT_RUN),
]
PARTIAL_RUN = [
    step(0, StepOutcome.SKIPPED),
    step(1, StepOutcome.SKIPPED),
    step(2, StepOutcome.PASS),
]


# ─── 우선순위 ────────────────────────────────────────────────────────────────


def test_all_pass_is_pass() -> None:
    assert decide_outcome(ALL_PASS) is Outcome.PASS


def test_failed_step_is_fail() -> None:
    assert decide_outcome(WITH_FAILURE) is Outcome.FAIL


def test_stop_request_wins_over_failure() -> None:
    """사용자가 누른 중지는 실패가 아니다 (FR-131, U-03).

    실패한 Step 이 이미 있어도 중지가 이긴다 — 사용자는 자기 조작의 결과를 통보받아야
    하고, 그것이 사고(실패)로 기록되면 실행 이력이 오염된다.
    """
    assert decide_outcome(WITH_FAILURE, stop_requested=True) is Outcome.STOPPED


def test_session_loss_wins_over_stop_request() -> None:
    """유실은 중지보다 먼저 본다.

    유실 뒤에 도착한 중지 요청이 사고를 정상 중단으로 바꿔 적으면, 사용자는 브라우저가
    죽은 것을 자기가 멈춘 것으로 오해한다.
    """
    assert decide_outcome(ALL_PASS, session_lost=True, stop_requested=True) is Outcome.FAIL


def test_session_loss_is_failure_not_stopped() -> None:
    """세션 유실은 사고다 (data-model.md §1)."""
    assert decide_outcome(ALL_PASS, session_lost=True) is Outcome.FAIL


def test_skipping_failure_is_partial_pass_not_pass() -> None:
    """실패를 건너뛰고 계속한 실행은 완료가 아니다 (FR-137, U-05).

    화면이 「완료」라고 말하는데 저장된 결과가 실패인 상태가 U-05 였다.
    """
    assert decide_outcome(PARTIAL_RUN, skipped_failures=True) is Outcome.PARTIAL_PASS


def test_partial_run_without_skipped_failure_is_not_partial_pass() -> None:
    """부분 실행 자체는 `PARTIAL_PASS` 가 아니다.

    부분 실행도 앞선 Step 을 `SKIPPED` 로 적는다. 그것만으로 `PARTIAL_PASS` 를 내면
    모든 부분 실행이 부분 성공이 되어, 「실패한 Step 건너뛰고 계속」과 구분되지 않는다.
    """
    assert decide_outcome(PARTIAL_RUN) is Outcome.PASS


def test_stop_request_wins_over_skipped_failures() -> None:
    assert (
        decide_outcome(PARTIAL_RUN, stop_requested=True, skipped_failures=True) is Outcome.STOPPED
    )


# ─── 실패 집계 ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (Outcome.PASS, False),
        (Outcome.FAIL, True),
        (Outcome.STOPPED, False),
        (Outcome.PARTIAL_PASS, False),
    ],
)
def test_only_fail_counts_as_failure(outcome: Outcome, expected: bool) -> None:
    """중지와 부분 성공은 실패 집계에서 빠진다 (FR-131·SC-215)."""
    assert counts_as_failure(outcome) is expected


def test_every_outcome_is_covered_by_failure_counting() -> None:
    """결말이 늘면 이 테스트가 먼저 깨진다.

    값을 추가하고 집계 규칙을 정하지 않은 채 넘어가는 것을 막는다.
    """
    assert {o for o in Outcome} == {
        Outcome.PASS,
        Outcome.FAIL,
        Outcome.STOPPED,
        Outcome.PARTIAL_PASS,
    }


# ─── 분모와 범위 ─────────────────────────────────────────────────────────────


def test_attempted_excludes_skipped_only() -> None:
    """분모는 건너뛴 것만 뺀다 (FR-152, U-02).

    미실행(`NOT_RUN`)은 **실행 대상이었지만 앞선 실패로 도달하지 못한 것**이므로 분모에
    남는다. 그것까지 빼면 실패한 실행이 `5 / 5` 로 보인다.
    """
    assert attempted_of(WITH_FAILURE) == 3
    assert attempted_of(PARTIAL_RUN) == 1


def test_attempted_of_full_pass_is_total() -> None:
    assert attempted_of(ALL_PASS) == len(ALL_PASS)


@pytest.mark.parametrize(
    ("start", "expected"),
    [(0, RunScope.FULL), (1, RunScope.PARTIAL), (5, RunScope.PARTIAL)],
)
def test_scope_from_start_index(start: int, expected: RunScope) -> None:
    assert scope_of(start) is expected


# ─── 순수성 (헌법 원칙 II) ───────────────────────────────────────────────────


def test_decide_outcome_does_not_mutate_input() -> None:
    """판정이 입력을 바꾸지 않는다.

    결말 판정이 Step 결과를 손대면 같은 결과를 두 번 판정할 때 값이 달라지고, 유실 감지와
    러너 종료가 겹치는 경로(둘 다 finalize 를 부른다)에서 결말이 흔들린다.
    """
    before = [r.model_copy(deep=True) for r in WITH_FAILURE]
    decide_outcome(WITH_FAILURE, stop_requested=True)
    assert [r.model_dump() for r in WITH_FAILURE] == [r.model_dump() for r in before]


def test_decide_outcome_is_deterministic() -> None:
    """같은 입력에 같은 결말. 언어모델도, 시각도, 난수도 쓰지 않는다 (헌법 원칙 II)."""
    first = decide_outcome(WITH_FAILURE, skipped_failures=True)
    second = decide_outcome(WITH_FAILURE, skipped_failures=True)
    assert first is second
