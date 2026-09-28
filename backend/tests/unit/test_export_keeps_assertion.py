"""어긋난 검증도 통상의 검증과 **동일하게** 생성된다 (020 T052 · FR-016 · 헌법 원칙 V).

## 왜 이 검사가 필요한가

원칙 V 는 「생성한 테스트 자산을 제품 없이도 계속 쓸 수 있다」를 요구한다. 020 이
정의에 「이 검증은 지금 실패한다」는 기록을 넣으므로, 어느 시점엔가 「알려진 결함이면
내보낼 때 빼자」나 「주석으로 바꾸자」가 합리적으로 들릴 수 있다. 그 한 줄이 들어오는
순간 내보낸 테스트는 제품 안에서 돌린 것과 **다른 결과**를 내고, 원칙 V 가 거짓이 된다.

`test_mismatch_isolation.py` 가 생성기 소스에 이름이 없음을 고정한다. 이 파일은 그
결과 — **생성된 코드가 표시 유무와 무관하게 같다** — 를 고정한다. 둘 다 필요하다:
앞은 원인을, 뒤는 증상을 막는다.

## 고정 데이터를 사람이 만든 검증으로 잡는다 (정합성 점검 F5)

작성 주체를 기본값(사람)으로 둔다. 원칙 I 상 AI 가 만든 것과 같아야 하며, AI 경로에서만
확인하면 그 요구가 밖에서도 성립하는지 알 수 없다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from itb.domain.assertion import Assertion, AssertionKind, AuthoringMismatch, MatchMode
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import AssertionStep
from itb.domain.test_case import AuthoringMode, Test
from itb.generator.playwright_gen import ValueRenderer, generate_spec, step_lines

RECORDED_AT = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def _target() -> TargetLocator:
    return TargetLocator(
        tag="p",
        test_id=Candidate(value="save-notice", status=CandidateStatus.VERIFIED),
        css=Candidate(value="#notice", status=CandidateStatus.VERIFIED),
    )


def _check(*, mismatched: bool, kind: AssertionKind, **extra: object) -> AssertionStep:
    return AssertionStep(
        id="step-01",
        label="저장 문구 확인",
        assertion=Assertion(kind=kind, **extra),  # type: ignore[arg-type]
        mismatch=(
            AuthoringMismatch(observed="처리 완료", recorded_at=RECORDED_AT)
            if mismatched
            else None
        ),
    )


CASES = [
    (AssertionKind.TEXT, {"value": "저장되었습니다", "match": MatchMode.EQUALS}),
    (AssertionKind.TEXT, {"value": "저장", "match": MatchMode.CONTAINS}),
    (AssertionKind.URL, {"value": "https://example.test/list"}),
    (AssertionKind.VISIBLE, {"target": _target()}),
    (AssertionKind.HIDDEN, {"target": _target()}),
]


@pytest.mark.parametrize(("kind", "extra"), CASES)
def test_generated_lines_are_identical_with_or_without_the_mark(
    kind: AssertionKind, extra: dict[str, object]
) -> None:
    """**네 종류 전부** 표시 유무와 무관하게 같은 코드가 나온다 (FR-016).

    같은지 다른지를 사람이 눈으로 비교하지 않는다 — 두 벌을 만들어 대조한다.
    """
    clean_step = _check(mismatched=False, kind=kind, **extra)
    values = ValueRenderer.of(
        Test(
            id="TC-020",
            name="t",
            authoring_mode=AuthoringMode.RECORD,
            start_url="https://example.test/",
            steps=[clean_step],
        )
    )
    clean = step_lines(clean_step, values)
    marked = step_lines(_check(mismatched=True, kind=kind, **extra), values)
    assert clean == marked, f"{kind} 검증이 표시 때문에 다르게 생성됐다"


def test_the_whole_spec_is_identical() -> None:
    """한 줄이 아니라 **파일 전체**가 같다.

    줄만 비교하면 생성기가 머리말이나 주석에 표시를 흘리는 것을 잡지 못한다.
    """

    def spec(mismatched: bool) -> str:
        return generate_spec(
            Test(
                id="TC-020",
                name="저장 문구",
                authoring_mode=AuthoringMode.RECORD,
                start_url="https://example.test/",
                steps=[
                    _check(
                        mismatched=mismatched,
                        kind=AssertionKind.TEXT,
                        value="저장되었습니다",
                    )
                ],
            )
        )

    assert spec(False) == spec(True)


def test_the_expected_value_is_what_reaches_the_exported_code() -> None:
    """내보낸 코드가 검사하는 것은 **사용자가 요구한 값**이다.

    관찰값이 새어 나가면 내보낸 테스트가 결함을 정답으로 삼는다 — 제품 안에서 고친
    문제가 밖에서 되살아난다.
    """
    spec = generate_spec(
        Test(
            id="TC-020",
            name="저장 문구",
            authoring_mode=AuthoringMode.RECORD,
            start_url="https://example.test/",
            steps=[
                _check(
                    mismatched=True,
                    kind=AssertionKind.TEXT,
                    value="저장되었습니다",
                )
            ],
        )
    )
    assert "저장되었습니다" in spec
    assert "처리 완료" not in spec, "작성 시점 관찰값이 내보낸 코드로 새어 나갔다"
