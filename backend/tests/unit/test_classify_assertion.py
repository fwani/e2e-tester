"""검증 실패의 분류 (020 T033 · FR-018~FR-022).

**분류는 결말과 다른 축이다.** 결말은 실행 전체가 어떻게 끝났는가이고, 이것은 검증
하나가 「원래 알던 것」인지 「오늘 깨진 것」인지다. 그 둘을 한 값에 섞으면 함께 말할 수
없고, 그래서 `Outcome` 에 값을 더하지 않았다 (FR-021).

이 파일은 data-model.md §3 의 **판정표 여섯 줄 전부**를 고정한다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from itb.domain.assertion import Assertion, AssertionKind, AuthoringMismatch, MatchMode
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.run_result import (
    AssertionClass,
    StepOutcome,
    StepResult,
    classify_assertion,
    counts_by_class,
)
from itb.domain.step import AssertionStep, ClickStep

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def _assertion_step(*, mismatched: bool) -> AssertionStep:
    return AssertionStep(
        id="step-01",
        label="문구 확인",
        assertion=Assertion(kind=AssertionKind.TEXT, value="저장되었습니다"),
        mismatch=(
            AuthoringMismatch(observed="처리 완료", recorded_at=NOW) if mismatched else None
        ),
    )


def _click_step() -> ClickStep:
    return ClickStep(
        id="step-01",
        label="저장",
        target=TargetLocator(
            tag="button",
            test_id=Candidate(value="save", status=CandidateStatus.VERIFIED),
            css=Candidate(value="#save", status=CandidateStatus.VERIFIED),
        ),
    )


def _result(outcome: StepOutcome) -> StepResult:
    return StepResult(step_id="step-01", index=0, label="Step 1", outcome=outcome)


# ─── 판정표 여섯 줄 ──────────────────────────────────────────────────────────


def test_mismatched_and_failing_is_a_known_defect() -> None:
    """작성 시점에도 실패했고 지금도 실패한다 — 이미 아는 결함이다."""
    step = _assertion_step(mismatched=True)
    assert classify_assertion(step, _result(StepOutcome.FAIL)) is AssertionClass.KNOWN_DEFECT


def test_clean_and_failing_is_a_regression() -> None:
    """작성 시점에는 통과했는데 지금 실패한다 — **오늘 깨진 것이다.**

    이것이 사용자가 먼저 봐야 할 것이며, 020 이전에는 알려진 결함과 구별되지 않았다.
    """
    step = _assertion_step(mismatched=False)
    assert classify_assertion(step, _result(StepOutcome.FAIL)) is AssertionClass.REGRESSION


def test_mismatched_and_passing_is_resolved() -> None:
    """결함이 고쳐졌다 — 표시를 걷어낼 시점임을 알리는 신호다 (FR-022)."""
    step = _assertion_step(mismatched=True)
    assert classify_assertion(step, _result(StepOutcome.PASS)) is AssertionClass.RESOLVED


def test_clean_and_passing_has_nothing_to_say() -> None:
    """평범하게 통과한 검증에는 분류가 없다. 0건 분류를 싣지 않는 규칙의 뿌리다."""
    step = _assertion_step(mismatched=False)
    assert classify_assertion(step, _result(StepOutcome.PASS)) is None


@pytest.mark.parametrize("outcome", [StepOutcome.SKIPPED, StepOutcome.NOT_RUN])
def test_unexecuted_steps_have_no_class(outcome: StepOutcome) -> None:
    """실행되지 않은 것에 대해서는 아무 말도 하지 않는다.

    `NOT_RUN` 을 회귀로 적으면 앞선 실패가 만든 미실행이 전부 회귀로 보인다.
    """
    step = _assertion_step(mismatched=True)
    assert classify_assertion(step, _result(outcome)) is None


def test_non_assertion_steps_have_no_class() -> None:
    """동작 Step 의 실패는 분류 대상이 아니다. 그쪽은 실행을 멈춘다 (FR-034)."""
    assert classify_assertion(_click_step(), _result(StepOutcome.FAIL)) is None


# ─── 집계 ────────────────────────────────────────────────────────────────────


def test_counts_omit_classes_with_no_members() -> None:
    """**0건인 분류는 열쇠 자체가 없다** (FR-019).

    규칙을 여기서 한 번 정해 두면, 화면 셋이 「없는 것을 0으로 표시할지」를 각자
    판단하지 않는다.
    """
    results = [
        StepResult(
            step_id="step-01",
            index=0,
            label="a",
            outcome=StepOutcome.FAIL,
            assertion_class=AssertionClass.REGRESSION,
        ),
        StepResult(
            step_id="step-02",
            index=1,
            label="b",
            outcome=StepOutcome.FAIL,
            assertion_class=AssertionClass.KNOWN_DEFECT,
        ),
        StepResult(
            step_id="step-03",
            index=2,
            label="c",
            outcome=StepOutcome.FAIL,
            assertion_class=AssertionClass.KNOWN_DEFECT,
        ),
        StepResult(step_id="step-04", index=3, label="d", outcome=StepOutcome.PASS),
    ]
    counts = counts_by_class(results)
    assert counts == {
        AssertionClass.REGRESSION: 1,
        AssertionClass.KNOWN_DEFECT: 2,
    }
    assert AssertionClass.RESOLVED not in counts


def test_counts_of_an_empty_run_are_empty() -> None:
    assert counts_by_class([]) == {}


def test_old_result_files_read_as_unclassified() -> None:
    """020 이전에 저장된 결과에는 이 필드가 없다 (data-model §6).

    마이그레이션이 없다는 주장이 여기서 확인된다.
    """
    old = {"step_id": "step-01", "index": 0, "label": "a", "outcome": "fail"}
    assert StepResult.model_validate(old).assertion_class is None


# ─── 021 — 새 어휘에서도 분류가 나온다 (T039 · FR-025) ──────────────────────
#
# 분류 함수는 검증의 `kind` 를 보지 않으므로 **구조상 동작한다.** 그런데 구조상
# 그렇다는 것과 앞으로도 그렇다는 것은 다르다 — 누군가 종류별 분기를 넣으면 조용히
# 깨지고, 그때 사용자는 부정 검증의 실패가 회귀인지 알려진 결함인지 알 수 없게 된다.


def _assertion_step_of(kind: AssertionKind, **extra: object) -> AssertionStep:
    from itb.domain.locator import Candidate, CandidateStatus, TargetLocator

    payload = dict(extra)
    if kind in (
        AssertionKind.VISIBLE,
        AssertionKind.HIDDEN,
        AssertionKind.ENABLED,
        AssertionKind.DISABLED,
    ):
        payload["target"] = TargetLocator(
            css=Candidate(value="#x", status=CandidateStatus.VERIFIED)
        )
    return AssertionStep(
        id="step-01",
        label="검증",
        assertion=Assertion(kind=kind, **payload),  # type: ignore[arg-type]
        mismatch=AuthoringMismatch(observed="관찰값", recorded_at=NOW),
    )


NEW_VOCABULARY = [
    (AssertionKind.DISABLED, {}),
    (AssertionKind.ENABLED, {}),
    (AssertionKind.TEXT, {"value": "오류", "match": MatchMode.NOT_CONTAINS}),
    (AssertionKind.URL, {"value": "/login", "match": MatchMode.NOT_EQUALS}),
]


@pytest.mark.parametrize(("kind", "extra"), NEW_VOCABULARY)
def test_new_kinds_are_classified_as_a_known_defect_when_they_keep_failing(
    kind: AssertionKind, extra: dict
) -> None:
    step = _assertion_step_of(kind, **extra)
    assert (
        classify_assertion(step, _result(StepOutcome.FAIL)) is AssertionClass.KNOWN_DEFECT
    )


@pytest.mark.parametrize(("kind", "extra"), NEW_VOCABULARY)
def test_new_kinds_are_classified_as_resolved_when_they_start_passing(
    kind: AssertionKind, extra: dict
) -> None:
    step = _assertion_step_of(kind, **extra)
    assert classify_assertion(step, _result(StepOutcome.PASS)) is AssertionClass.RESOLVED


@pytest.mark.parametrize(("kind", "extra"), NEW_VOCABULARY)
def test_new_kinds_are_classified_as_a_regression_without_a_mark(
    kind: AssertionKind, extra: dict
) -> None:
    step = _assertion_step_of(kind, **extra)
    clean = step.model_copy(update={"mismatch": None})
    assert classify_assertion(clean, _result(StepOutcome.FAIL)) is AssertionClass.REGRESSION


# ─── 023 — 새 검증 종류도 같은 대상이다 (T049) ──────────────────────────────


@pytest.mark.parametrize(
    ("outcome", "had_mismatch", "expected"),
    [
        (StepOutcome.FAIL, True, AssertionClass.KNOWN_DEFECT),
        (StepOutcome.FAIL, False, AssertionClass.REGRESSION),
        (StepOutcome.PASS, True, AssertionClass.RESOLVED),
        (StepOutcome.PASS, False, None),
    ],
)
def test_value_assertion_is_classified_like_every_other_kind(
    outcome: StepOutcome, had_mismatch: bool, expected: AssertionClass | None
) -> None:
    """입력값 검증도 실행 결과 분류의 대상이다 (023 FR-010).

    ## 왜 이 검증이 필요한가 — 저절로 만족되기 때문이다

    `classify_assertion` 은 `step.type` 과 `mismatch` 유무만 본다. 검증 종류를 보지
    않으므로 `value` 를 더해도 **아무것도 하지 않아도 동작한다.**

    그것이 문제다. **저절로 만족된다는 사실이 어디에도 적혀 있지 않으면**, 나중에 읽는
    사람은 023 이 이 요구를 잊은 것인지 의도적으로 넘긴 것인지 알 수 없다. 이 검증이
    그 기록이며, 누가 종류별 분기를 넣으면 여기서 깨진다.
    """
    step = AssertionStep(
        id="step-01",
        label="입력값 확인",
        assertion=Assertion(
            kind=AssertionKind.VALUE,
            target=TargetLocator(css=Candidate(value="#name", status=CandidateStatus.VERIFIED)),
            value="E2E역할테스트",
        ),
        mismatch=(
            AuthoringMismatch(observed="실제: ''", recorded_at=datetime.now(UTC))
            if had_mismatch
            else None
        ),
    )
    result = StepResult(index=0, step_id="step-01", label="입력값 확인", outcome=outcome)
    assert classify_assertion(step, result) is expected
