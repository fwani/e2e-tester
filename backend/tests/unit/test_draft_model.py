"""초안 도메인 모델 (014 T024 · data-model §2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from itb.domain.draft import (
    MAX_DRAFT_NUMBER,
    Draft,
    DraftSource,
    compose_instruction,
    draft_number,
    format_draft_id,
)
from itb.domain.test_case import MAX_INSTRUCTION_CHARS, RESERVED_PREFIX


def make(**over: object) -> Draft:
    base: dict[str, object] = {
        "draft_id": "D-0001",
        "name": "로그인",
        "source": DraftSource(file_name="설계서.xlsx", sheet_name="회원", row=4),
    }
    base.update(over)
    return Draft(**base)  # type: ignore[arg-type]


class ShapeTests:
    def test_초안에는_steps_필드가_없다(self) -> None:
        # 원칙 I — 두면 Test.steps 의 min_length=1 을 우회하는 두 번째 테스트 표현이 된다.
        assert "steps" not in Draft.model_fields

    def test_모르는_필드를_거절한다(self) -> None:
        with pytest.raises(ValidationError):
            make(steps=[])

    def test_기본_소속은_그룹없음이다(self) -> None:
        assert make().group_prefix == RESERVED_PREFIX

    def test_제목은_비어_있을_수_없다(self) -> None:
        with pytest.raises(ValidationError):
            make(name="")

    def test_행_번호는_2부터다(self) -> None:
        # 1행은 머리글이다.
        with pytest.raises(ValidationError):
            DraftSource(file_name="a.xlsx", sheet_name="s", row=1)


class DesiredIdTests:
    def test_접두어가_소속과_같으면_받는다(self) -> None:
        d = make(desired_test_id="USER-003", group_prefix="USER")
        assert d.desired_test_id == "USER-003"

    def test_접두어가_소속과_다르면_거절한다(self) -> None:
        with pytest.raises(ValidationError, match="접두어"):
            make(desired_test_id="USER-003", group_prefix="DATA")

    def test_그룹없음_초안은_TC_식별자를_받는다(self) -> None:
        assert make(desired_test_id="TC-007").desired_test_id == "TC-007"

    def test_그룹없음_초안이_다른_접두어를_희망하면_거절한다(self) -> None:
        with pytest.raises(ValidationError):
            make(desired_test_id="USER-003")

    def test_형식에_맞지_않으면_거절한다(self) -> None:
        with pytest.raises(ValidationError):
            make(desired_test_id="TC-1")

    def test_비워둘_수_있다(self) -> None:
        assert make().desired_test_id is None


class IdHelpersTests:
    def test_번호를_읽는다(self) -> None:
        assert draft_number("D-0007") == 7

    def test_형식이_아니면_거절한다(self) -> None:
        with pytest.raises(ValueError, match="형식"):
            draft_number("TC-001")

    def test_번호를_식별자로_만든다(self) -> None:
        assert format_draft_id(7) == "D-0007"

    def test_왕복한다(self) -> None:
        assert draft_number(format_draft_id(4321)) == 4321

    @pytest.mark.parametrize("bad", [0, -1, MAX_DRAFT_NUMBER + 1])
    def test_범위를_벗어나면_거절한다(self, bad: int) -> None:
        with pytest.raises(ValueError, match="범위"):
            format_draft_id(bad)


class ComposeInstructionTests:
    def test_제목만_있어도_성립한다(self) -> None:
        assert compose_instruction(make()) == "제목: 로그인"

    def test_빈_항목은_줄째로_뺀다(self) -> None:
        # "수행자: None" 같은 줄이 들어가면 모델이 그것을 지시로 읽는다.
        text = compose_instruction(make(description="설명만 있다"))
        assert "수행자" not in text
        assert "수행 절차" not in text
        assert "설명: 설명만 있다" in text

    def test_모든_항목이_순서대로_들어간다(self) -> None:
        text = compose_instruction(
            make(
                description="자격 증명 확인",
                actor="관리자",
                procedure="1. 연다\n2. 누른다",
                expectation="1. 이동한다",
            )
        )
        assert text.index("제목:") < text.index("설명:") < text.index("수행자:")
        assert text.index("수행자:") < text.index("수행 절차:") < text.index("기대 결과:")

    def test_수행자는_역할로_표현된다(self) -> None:
        # 자격 증명이 아니라 역할이다 (FR-026a).
        assert "관리자 역할로 수행한다." in compose_instruction(make(actor="관리자"))

    def test_절차의_줄바꿈을_보존한다(self) -> None:
        assert "1. 연다\n2. 누른다" in compose_instruction(make(procedure="1. 연다\n2. 누른다"))


class InstructionLengthTests:
    def test_필드_상한의_합이_지시문_상한_안에_든다(self) -> None:
        # 구조로 보장한다 — 최대치로 채운 초안이 상한을 넘으면 안 된다.
        d = make(
            name="가" * 200,
            description="나" * 2000,
            actor="다" * 100,
            procedure="라" * 2000,
            expectation="마" * 2000,
        )
        assert len(compose_instruction(d)) <= MAX_INSTRUCTION_CHARS

    def test_상한을_넘는_초안은_만들어지지_않는다(self) -> None:
        # 만들어 두면 녹화를 시작하는 순간에야 막히고, 그때는 이미 하겠다고 마음먹은 뒤다.
        with pytest.raises(ValidationError):
            make(procedure="가" * 2001)
