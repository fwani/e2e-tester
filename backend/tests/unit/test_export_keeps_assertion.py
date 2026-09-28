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
    # 021 — 부정 비교 6개와 상태 검증 2개. 생성기 분기는 알 수 없는 조합을 만나면
    # 예외를 던지므로, 목록에 없는 조합은 조용히 잘못 생성되지 않고 명확히 실패한다.
    (AssertionKind.TEXT, {"value": "오류", "match": MatchMode.NOT_EQUALS}),
    (AssertionKind.TEXT, {"value": "오류", "match": MatchMode.NOT_CONTAINS}),
    (
        AssertionKind.TEXT,
        {"target": _target(), "value": "오류", "match": MatchMode.NOT_EQUALS},
    ),
    (
        AssertionKind.TEXT,
        {"target": _target(), "value": "오류", "match": MatchMode.NOT_CONTAINS},
    ),
    (AssertionKind.URL, {"value": "https://example.test/login", "match": MatchMode.NOT_EQUALS}),
    (AssertionKind.URL, {"value": "/login", "match": MatchMode.NOT_CONTAINS}),
    (AssertionKind.ENABLED, {"target": _target()}),
    (AssertionKind.DISABLED, {"target": _target()}),
]


@pytest.mark.parametrize(("kind", "extra"), CASES)
def test_generated_lines_are_identical_with_or_without_the_mark(
    kind: AssertionKind, extra: dict[str, object]
) -> None:
    """**여섯 종류 전부** 표시 유무와 무관하게 같은 코드가 나온다 (FR-016).

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


# ─── 021 — 부정 비교와 상태 검증의 내보내기 형태 ─────────────────────────────


def _lines(kind: AssertionKind, **extra: object) -> str:
    step = _check(mismatched=False, kind=kind, **extra)
    test = Test(
        id="TC-021",
        name="t",
        authoring_mode=AuthoringMode.RECORD,
        start_url="https://example.test/",
        steps=[step],
    )
    return "\n".join(step_lines(step, ValueRenderer.of(test)))


@pytest.mark.parametrize("kind", [AssertionKind.ENABLED, AssertionKind.DISABLED])
def test_state_assertions_map_to_playwright_state_matchers(kind: AssertionKind) -> None:
    matcher = "toBeEnabled" if kind is AssertionKind.ENABLED else "toBeDisabled"
    assert matcher in _lines(kind, target=_target())


@pytest.mark.parametrize(
    ("extra", "needle"),
    [
        ({"value": "오류", "match": MatchMode.NOT_CONTAINS}, "not.toContainText"),
        ({"value": "오류", "match": MatchMode.NOT_EQUALS}, "not.toHaveText"),
    ],
)
def test_negated_text_uses_the_not_modifier(extra: dict, needle: str) -> None:
    assert needle in _lines(AssertionKind.TEXT, **extra)


@pytest.mark.parametrize(
    "extra",
    [
        {"value": "오류", "match": MatchMode.NOT_CONTAINS},
        {"value": "오류", "match": MatchMode.NOT_EQUALS},
    ],
)
def test_negated_checks_are_watched_for_the_whole_window(extra: dict) -> None:
    """**부정 검증은 `.not` 만으로 끝내지 않는다** (021 export-mapping §2).

    `.not` 은 조건이 참이 **되면** 통과한다. 부정 조건의 기본 상태가 참이므로 첫
    판정에서 바로 끝나고, 늦게 나타나는 것을 놓친다 — 제품 안에서 잡은 결함을 내보낸
    테스트가 놓치는 것이고 원칙 V 위반이다. 기간 동안 지켜보는 루프로 감싼다.
    """
    code = _lines(AssertionKind.TEXT, **extra)
    assert "const deadline" in code, "관찰 기간이 없다 — 늦게 나타나는 것을 놓친다"
    assert "timeout: 1" in code, "안쪽 판정의 재시도를 꺼야 바깥 기간과 겹치지 않는다"
    assert "waitForTimeout(50)" in code


@pytest.mark.parametrize(
    "match", [MatchMode.EQUALS, MatchMode.CONTAINS]
)
def test_positive_checks_are_not_wrapped_in_a_window(match: MatchMode) -> None:
    """긍정 검증은 감싸지 않는다 — 참이 되면 끝이므로 지켜볼 이유가 없다."""
    code = _lines(AssertionKind.TEXT, value="저장", match=match)
    assert "const deadline" not in code


def test_negated_url_does_not_become_a_regex() -> None:
    """화면에서 온 값이 패턴으로 해석되면 뜻이 달라진다. 기존 판단을 부정형에도 적용한다."""
    code = _lines(AssertionKind.URL, value="/login", match=MatchMode.NOT_CONTAINS)
    assert "not.toContain" in code
    assert "RegExp" not in code and "/login/" not in code
