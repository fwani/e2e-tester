"""어긋남 기록의 도메인 규칙 (020 T008 · FR-005·FR-008·FR-011).

**이 파일이 지키는 것은 「어긋남은 검증에만 있다」와 「없으면 통과였다」 둘이다.**
전자가 깨지면 채워질 수 없는 칸이 Step 종류 여덟에 생기고, 후자가 깨지면 020 이전에
저장된 모든 정의가 재검증에서 거절된다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from itb.domain.assertion import (
    MAX_OBSERVED_CHARS,
    Assertion,
    AssertionKind,
    AuthoringMismatch,
)
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import (
    AssertionStep,
    Author,
    ClickStep,
    CloseTabStep,
    DragStep,
    FillStep,
    HoverStep,
    NavigateStep,
    SelectStep,
    UploadStep,
)

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def _assertion() -> Assertion:
    return Assertion(kind=AssertionKind.TEXT, value="저장되었습니다")


def _target() -> TargetLocator:
    return TargetLocator(
        tag="button",
        test_id=Candidate(value="save", status=CandidateStatus.VERIFIED),
        css=Candidate(value="#save", status=CandidateStatus.VERIFIED),
    )


# ─── AuthoringMismatch 자체 ──────────────────────────────────────────────────


def test_observed_cannot_be_empty() -> None:
    """빈 관찰값은 「화면이 비어 있었다」로 읽힌다.

    적을 것이 없는 상황은 어긋남이 아니라 **대상 없음**이며, 그때는 Step 자체가
    만들어지지 않는다 (FR-007). 빈 문자열을 허용하면 그 구별이 기록에서 사라진다.
    """
    with pytest.raises(ValidationError):
        AuthoringMismatch(observed="", recorded_at=NOW)


def test_observed_accepts_the_limit_and_rejects_beyond() -> None:
    """상한은 `Assertion.value` 와 같은 4000자다 (FR-008 · research R2)."""
    AuthoringMismatch(observed="가" * MAX_OBSERVED_CHARS, recorded_at=NOW)
    with pytest.raises(ValidationError):
        AuthoringMismatch(observed="가" * (MAX_OBSERVED_CHARS + 1), recorded_at=NOW)


def test_truncated_defaults_to_false() -> None:
    """잘리지 않은 것이 기본이다. 잘렸다는 사실은 **명시해야** 남는다."""
    assert AuthoringMismatch(observed="처리 완료", recorded_at=NOW).truncated is False


def test_expected_value_is_not_duplicated_here() -> None:
    """기대값의 유일한 출처는 `assertion.value` 다 (research R1).

    여기에 기대값 칸이 생기면 Step 편집으로 조건을 고쳤을 때 둘이 갈리고, 그때 어느
    쪽이 맞는지 아무도 모른다.
    """
    assert set(AuthoringMismatch.model_fields) == {"observed", "truncated", "recorded_at"}


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AuthoringMismatch(observed="x", recorded_at=NOW, expected="y")


# ─── AssertionStep 에 붙는 방식 ──────────────────────────────────────────────


def test_default_is_none_so_old_definitions_still_validate() -> None:
    """**020 이전에 저장된 모든 정의가 여기 해당한다.**

    그 정의들은 통과할 때만 기록됐으므로 「표시 없음 = 작성 시점 통과」가 참이다.
    그래서 마이그레이션이 없다.
    """
    old = {
        "id": "step-01",
        "type": "assertion",
        "label": "문구 확인",
        "assertion": {"kind": "text", "match": "equals", "value": "저장되었습니다"},
    }
    assert AssertionStep.model_validate(old).mismatch is None


def test_mismatch_survives_a_serialization_round_trip() -> None:
    """공유·저장은 모델 왕복이다 (FR-017). 왕복에서 사라지면 받는 쪽은 모든 알려진
    결함을 회귀로 본다."""
    step = AssertionStep(
        id="step-01",
        label="문구 확인",
        assertion=_assertion(),
        mismatch=AuthoringMismatch(observed="처리 완료", recorded_at=NOW),
    )
    again = AssertionStep.model_validate(step.model_dump(mode="json"))
    assert again.mismatch is not None
    assert again.mismatch.observed == "처리 완료"
    assert again.mismatch.recorded_at == NOW


@pytest.mark.parametrize("author", [Author.HUMAN, Author.AI])
def test_author_does_not_gate_the_field(author: Author) -> None:
    """사람이 만든 검증도 같은 필드를 갖는다 (FR-011 · 헌법 원칙 I).

    사람이 아직 구현되지 않은 동작에 대한 검증을 미리 적는 것도 같은 표현이다.
    """
    step = AssertionStep(
        id="step-01",
        label="문구 확인",
        author=author,
        assertion=_assertion(),
        mismatch=AuthoringMismatch(observed="처리 완료", recorded_at=NOW),
    )
    assert step.mismatch is not None


# ─── 다른 Step 종류에는 없다 ─────────────────────────────────────────────────


def _other_steps() -> list[object]:
    """검증을 뺀 Step 종류 여덟 전부."""
    return [
        ClickStep(id="step-01", label="클릭", target=_target()),
        FillStep(id="step-01", label="입력", target=_target(), value="가"),
        SelectStep(id="step-01", label="선택", target=_target(), value="가"),
        NavigateStep(id="step-01", label="이동", url="https://example.test/"),
        HoverStep(id="step-01", label="올리기", target=_target()),
        DragStep(id="step-01", label="끌기", target=_target(), drop_target=_target()),
        UploadStep(id="step-01", label="올리기", target=_target(), file_name="a.csv"),
        CloseTabStep(id="step-01", label="탭 닫기", tab=1),
    ]


def test_no_other_step_type_carries_a_mismatch() -> None:
    """「어긋난 클릭 Step」은 원리적으로 존재할 수 없다 (research R1 · FR-006).

    동작 Step 은 실패하면 기록되지 않는다. 공통 필드로 올리면 여덟 종류에 **영원히
    `None` 인 칸**이 생기고, 읽는 쪽은 그 칸이 왜 비어 있는지를 매번 판단해야 한다.
    """
    for step in _other_steps():
        assert "mismatch" not in type(step).model_fields, (
            f"{type(step).__name__} 이 어긋남 칸을 갖는다 — 채울 수 없는 칸이다"
        )


def test_other_step_types_reject_a_mismatch_argument() -> None:
    """`extra="forbid"` 가 그 사실을 강제한다."""
    with pytest.raises(ValidationError):
        ClickStep(
            id="step-01",
            label="클릭",
            target=_target(),
            mismatch=AuthoringMismatch(observed="x", recorded_at=NOW),
        )
