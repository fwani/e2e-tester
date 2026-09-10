"""워크북 → 가져오기 계획 (014 T040 · FR-017~FR-024a).

계획은 **아직 아무것도 만들지 않은 상태**다. 여기서 확인하는 것은 "무엇을 만들 것인가"의
판단이지 만들어진 결과가 아니다.
"""

from __future__ import annotations

from excel_support import HEADER_ROW, build_xlsx, row

from itb.domain.test_case import Project, TestGroup
from itb.portability.importer import (
    PrefixSource,
    SkipReason,
    build_plan,
    validate_prefix,
)
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME
from itb.portability.workbook import read_sheets


def plan_of(sheets: dict[str, list[list[object]]], **kw: object):
    parsed = read_sheets(build_xlsx(sheets))
    return build_plan(parsed, "설계서.xlsx", **kw)  # type: ignore[arg-type]


def project_with(*groups: tuple[str, str]) -> Project:
    return Project(
        name="P",
        default_start_url="https://example.internal",
        groups=[TestGroup(prefix=p, name=n) for p, n in groups],
    )


class PrefixTests:
    def test_행의_TC_ID_에서_접두어를_읽는다(self) -> None:
        plan = plan_of({"회원": [row("USER-001", "로그인"), row("USER-002", "로그아웃")]},
                       project=None)
        sheet = plan.sheets[0]
        assert sheet.prefix == "USER"
        assert sheet.prefix_source == PrefixSource.FROM_ROWS
        assert not sheet.needs_prefix

    def test_TC_ID_가_모두_비면_접두어를_묻는다(self) -> None:
        # 시스템이 시트 이름에서 만들어내지 않는다 (FR-022a).
        plan = plan_of({"데이터관리": [row(None, "조회"), row(None, "등록")]}, project=None)
        sheet = plan.sheets[0]
        assert sheet.prefix is None
        assert sheet.needs_prefix
        assert plan.needs_prefix == ["데이터관리"]

    def test_접두어를_몰라도_행은_만들어_둔다(self) -> None:
        # 확정에서 사용자가 접두어를 주면 이 행들이 쓰인다. 여기서 비워 두면 확정이
        # 접두어만 받고 만들 것을 잃는다.
        plan = plan_of({"데이터관리": [row(None, "조회")]}, project=None)
        assert len(plan.sheets[0].rows) == 1

    def test_접두어를_묻는_시트는_초안_수에_세지_않는다(self) -> None:
        # 비워 두면 통째로 건너뛰므로(FR-022b), 세어 두면 미리보기가 예고한 수와
        # 결과가 어긋난다 (SC-005).
        plan = plan_of({"데이터관리": [row(None, "조회")]}, project=None)
        assert plan.draft_count == 0

    def test_접두어를_주면_초안_수에_들어온다(self) -> None:
        plan = plan_of(
            {"데이터관리": [row(None, "조회")]},
            project=None,
            prefixes={"데이터관리": "DATA"},
        )
        assert plan.draft_count == 1

    def test_사용자가_준_접두어를_쓴다(self) -> None:
        plan = plan_of(
            {"데이터관리": [row(None, "조회")]},
            project=None,
            prefixes={"데이터관리": "data"},
        )
        sheet = plan.sheets[0]
        assert sheet.prefix == "DATA"  # 대문자로 맞춘다
        assert sheet.prefix_source == PrefixSource.USER_SUPPLIED
        assert len(sheet.rows) == 1

    def test_그룹없음_시트는_TC_를_쓴다(self) -> None:
        plan = plan_of({UNGROUPED_SHEET_NAME: [row("TC-001", "가")]}, project=None)
        sheet = plan.sheets[0]
        assert sheet.prefix == "TC"
        assert sheet.prefix_source == PrefixSource.UNGROUPED

    def test_TC_접두어를_쓰는_시트는_그룹없음으로_본다(self) -> None:
        # 사람이 쓴 설계서가 TC-### 를 쓰고 있다.
        plan = plan_of({"기타": [row("TC-001", "가")]}, project=None)
        assert plan.sheets[0].prefix_source == PrefixSource.UNGROUPED

    def test_접두어가_섞이면_다수결로_정하고_알린다(self) -> None:
        plan = plan_of(
            {"혼재": [row("USER-001", "가"), row("USER-002", "나"), row("DATA-003", "다")]},
            project=None,
        )
        assert plan.sheets[0].prefix == "USER"
        assert any("섞여" in w for w in plan.warnings)

    def test_소속이_다른_행도_시트의_접두어를_따른다(self) -> None:
        # 접두어가 곧 소속이므로 시트가 정한 소속을 따르고 번호만 가져온다.
        plan = plan_of(
            {"혼재": [row("USER-001", "가"), row("USER-002", "나"), row("DATA-003", "다")]},
            project=None,
        )
        assert [r.desired_test_id for r in plan.sheets[0].rows] == [
            "USER-001",
            "USER-002",
            "USER-003",
        ]


class ColumnTests:
    def test_필수_컬럼이_없으면_시트를_건너뛴다(self) -> None:
        parsed = read_sheets(build_xlsx({"메모": [["아무거나"]]}, header=["비고", "담당"]))
        plan = build_plan(parsed, "f.xlsx", project=None)
        assert plan.sheets == []
        assert [s.reason for s in plan.skipped] == [SkipReason.NO_COLUMNS]
        assert any("필수 컬럼" in w for w in plan.warnings)

    def test_열_순서가_달라도_읽는다(self) -> None:
        parsed = read_sheets(
            build_xlsx({"회원": [["로그인", "USER-001"]]}, header=["대상기능", "TC ID"])
        )
        plan = build_plan(parsed, "f.xlsx", project=None)
        assert plan.sheets[0].rows[0].name == "로그인"
        assert plan.sheets[0].prefix == "USER"

    def test_결과_칸은_무시한다(self) -> None:
        # 실행하지 않은 테스트에 결과를 만들어 줄 수 없다 (FR-020).
        plan = plan_of({"회원": [row("USER-001", "로그인", outcome="P")]}, project=None)
        assert not hasattr(plan.sheets[0].rows[0], "outcome")

    def test_모든_칸이_초안으로_옮겨진다(self) -> None:
        plan = plan_of(
            {
                "회원": [
                    row("USER-001", "로그인", "설명", "관리자", "1. 연다", "1. 보인다", "P")
                ]
            },
            project=None,
        )
        r = plan.sheets[0].rows[0]
        assert (r.name, r.description, r.actor) == ("로그인", "설명", "관리자")
        assert (r.procedure, r.expectation) == ("1. 연다", "1. 보인다")


class SkipTests:
    def test_제목이_비면_건너뛴다(self) -> None:
        plan = plan_of({"회원": [row("USER-001", None), row("USER-002", "로그인")]}, project=None)
        assert len(plan.sheets[0].rows) == 1
        assert [s.reason for s in plan.skipped] == [SkipReason.NO_TITLE]

    def test_건너뛴_행의_위치를_말한다(self) -> None:
        plan = plan_of({"회원": [row("USER-001", "가"), row("USER-002", None)]}, project=None)
        skipped = plan.skipped[0]
        assert (skipped.sheet_name, skipped.row) == ("회원", 3)

    def test_완전히_빈_행은_비어_있음으로_건너뛴다(self) -> None:
        plan = plan_of({"회원": [row("USER-001", "가"), row()]}, project=None)
        assert [s.reason for s in plan.skipped] == [SkipReason.EMPTY]

    def test_건너뛴_행이_다른_행을_막지_않는다(self) -> None:
        plan = plan_of(
            {"회원": [row("USER-001", "가"), row(None, None), row("USER-003", "다")]},
            project=None,
        )
        assert [r.name for r in plan.sheets[0].rows] == ["가", "다"]


class DuplicateTests:
    def test_파일_안_중복은_뒤엣것이_새_번호를_받는다(self) -> None:
        # 어떤 행도 이 때문에 버려지지 않는다 (FR-023a).
        plan = plan_of(
            {"회원": [row("USER-001", "가"), row("USER-001", "나")]}, project=None
        )
        rows = plan.sheets[0].rows
        assert len(rows) == 2
        assert rows[0].desired_test_id == "USER-001"
        assert rows[1].desired_test_id != "USER-001"

    def test_바뀐_번호가_원래_값을_들고_있다(self) -> None:
        plan = plan_of(
            {"회원": [row("USER-001", "가"), row("USER-001", "나")]}, project=None
        )
        assert plan.sheets[0].rows[1].renumbered_from == "USER-001"

    def test_바뀌지_않은_행은_원래_값을_들지_않는다(self) -> None:
        plan = plan_of({"회원": [row("USER-001", "가")]}, project=None)
        assert plan.sheets[0].rows[0].renumbered_from is None

    def test_이미_쓰는_번호도_피한다(self) -> None:
        plan = plan_of(
            {"회원": [row("USER-001", "가")]},
            project=project_with(("USER", "사용자관리")),
            taken_ids={"USER-001"},
        )
        assert plan.sheets[0].rows[0].desired_test_id != "USER-001"

    def test_시트를_넘어서도_번호가_겹치지_않는다(self) -> None:
        # 번호는 접두어를 넘어 프로젝트 전체에서 고유하다 (013 R3).
        plan = plan_of(
            {"회원": [row("USER-001", "가")], "데이터": [row("DATA-001", "나")]},
            project=None,
        )
        ids = [r.desired_test_id for s in plan.sheets for r in s.rows]
        numbers = [i.split("-", 1)[1] for i in ids if i]
        assert len(set(numbers)) == 2


class ExistingGroupTests:
    def test_접두어가_같으면_기존_그룹을_가리킨다(self) -> None:
        plan = plan_of(
            {"회원": [row("USER-001", "가")]},
            project=project_with(("USER", "사용자관리")),
        )
        assert plan.sheets[0].existing_group_name == "사용자관리"

    def test_이름이_다르면_그_사실을_알린다(self) -> None:
        plan = plan_of(
            {"회원": [row("USER-001", "가")]},
            project=project_with(("USER", "사용자관리")),
        )
        assert plan.sheets[0].name_differs

    def test_이름이_같으면_다르다고_하지_않는다(self) -> None:
        plan = plan_of(
            {"사용자관리": [row("USER-001", "가")]},
            project=project_with(("USER", "사용자관리")),
        )
        assert not plan.sheets[0].name_differs

    def test_없는_접두어는_기존_이름이_없다(self) -> None:
        plan = plan_of({"회원": [row("USER-001", "가")]}, project=project_with())
        assert plan.sheets[0].existing_group_name is None
        assert not plan.sheets[0].name_differs


class ValidatePrefixTests:
    def test_올바른_접두어를_받는다(self) -> None:
        assert validate_prefix("USER") is None

    def test_소문자도_받는다(self) -> None:
        assert validate_prefix("user") is None

    def test_예약어를_거절한다(self) -> None:
        assert validate_prefix("TC") is not None

    def test_형식에_맞지_않으면_거절한다(self) -> None:
        assert validate_prefix("사용자") is not None
        assert validate_prefix("TOOLONGPREFIX") is not None
        assert validate_prefix("1ABC") is not None
        assert validate_prefix("") is not None


class CountTests:
    def test_만들_초안_수를_센다(self) -> None:
        plan = plan_of(
            {
                "회원": [row("USER-001", "가"), row("USER-002", "나")],
                UNGROUPED_SHEET_NAME: [row("TC-010", "다")],
            },
            project=None,
        )
        assert plan.draft_count == 3

    def test_머리글만_있는_시트는_0건이다(self) -> None:
        plan = plan_of({"빈": []}, project=None)
        assert plan.draft_count == 0

    def test_계획마다_식별자가_다르다(self) -> None:
        a = plan_of({"회원": [row("USER-001", "가")]}, project=None)
        b = plan_of({"회원": [row("USER-001", "가")]}, project=None)
        assert a.plan_id != b.plan_id
        assert a.plan_id.startswith("pl_")


class HeaderRowTests:
    def test_기본_머리글이_일곱개다(self) -> None:
        assert len(HEADER_ROW) == 7
