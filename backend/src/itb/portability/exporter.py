"""프로젝트 → 워크북 시트·행 (기능 014 US1).

**민감 값을 읽지 않는다.** 이 모듈은 :mod:`itb.secrets` 를 임포트하지 않는다 — 내보내는 것은
Step 의 ``label`` 과 변수 **참조**(`{{SECRET_LOGIN_PW}}`)뿐이고, 그 값이 무엇인지는 알 필요도
알 방법도 없다. 구조로 보장하는 편이 검사로 보장하는 것보다 낫다 (FR-007 · SC-008).

워크북은 **파생 산출물**이다. 이 파일을 고쳐서 다시 넣어도 저장된 테스트의 스텝은 바뀌지
않는다 — 표의 글로는 스텝을 만들 수 없기 때문이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from itb.domain.run_result import Outcome
from itb.domain.step import StepType
from itb.domain.test_case import RESERVED_PREFIX, Project, Test
from itb.portability.columns import ORDER, Column
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME, SheetRename, assign
from itb.portability.workbook import SheetSpec

OUTCOME_TEXT: dict[Outcome, str] = {
    Outcome.PASS: "P",
    Outcome.FAIL: "F",
    Outcome.PARTIAL_PASS: "P(부분)",
    Outcome.STOPPED: "중지",
}
"""실행 결말 → 「결과」 칸 (FR-006·FR-006a · research R5).

**네 값을 둘로 접지 않는다.** 실패한 단계를 건너뛰고 얻은 통과를 `P` 로 적으면 보고서에
거짓이 실리고, 사용자가 중지한 실행을 `F` 로 적으면 실패하지 않은 것을 실패로 보고하게
된다. 컬럼 이름이 「결과(P/F)」인 것은 흔한 두 값을 가리킬 뿐, 다른 값을 그 둘 중 하나로
욱여넣으라는 뜻이 아니다.

결과가 없거나 읽을 수 없으면 빈 칸이다 — 이 표에 없다.
"""


@dataclass(frozen=True, slots=True)
class Truncation:
    test_id: str
    column: str
    kept_lines: int
    dropped_lines: int


@dataclass(slots=True)
class ExportReport:
    """내보내기에서 무엇이 바뀌었는가 (FR-008·FR-010·FR-013)."""

    sheet_renames: list[SheetRename] = field(default_factory=list)
    truncations: list[Truncation] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)
    test_count: int = 0
    sheet_count: int = 0

    @property
    def warning_count(self) -> int:
        return len(self.sheet_renames) + len(self.truncations) + len(self.unreadable)


def numbered(labels: list[str]) -> str:
    """스텝 라벨들을 번호 매긴 여러 줄로 만든다 (FR-005).

    비어 있으면 빈 문자열이다 — `1.` 만 있는 칸을 만들지 않는다.
    """
    return "\n".join(f"{i}. {label}" for i, label in enumerate(labels, start=1))


def split_steps(test: Test) -> tuple[list[str], list[str]]:
    """(수행 절차, 기대 결과) — 검증 스텝과 나머지를 가른다 (FR-005).

    검증 스텝은 `type == assertion` 인 것이다. 별도의 배열이 아니라 `steps` 안에 섞여
    있으므로 여기서 갈라야 한다 — 그것이 원칙 I 이 요구하는 단일 스텝 모델의 모습이다.

    실행 순서를 유지한다. 순서를 잃으면 절차가 아니라 목록이 된다.
    """
    procedure = [s.label for s in test.steps if s.type != StepType.ASSERTION]
    expectation = [s.label for s in test.steps if s.type == StepType.ASSERTION]
    return procedure, expectation


def prefix_of(test_id: str) -> str:
    """식별자에서 그룹 접두어를 읽는다. 접두어가 곧 소속이다 (013)."""
    return test_id.split("-", 1)[0]


def row_for(test: Test, outcome: Outcome | None) -> list[str]:
    """테스트 하나 → 행 하나. 컬럼 순서는 :data:`ORDER` 가 정한다."""
    procedure, expectation = split_steps(test)
    values: dict[Column, str] = {
        Column.TC_ID: test.id,
        Column.NAME: test.name,
        Column.DESCRIPTION: test.description or "",
        Column.ACTOR: test.actor or "",
        Column.PROCEDURE: numbered(procedure),
        Column.EXPECTATION: numbered(expectation),
        Column.OUTCOME: OUTCOME_TEXT.get(outcome, "") if outcome else "",
    }
    return [values[c] for c in ORDER]


def build_sheets(
    project: Project,
    tests: list[Test],
    outcomes: dict[str, Outcome | None],
    *,
    unreadable: list[str] | None = None,
) -> tuple[list[SheetSpec], ExportReport]:
    """프로젝트를 시트 목록으로 만든다.

    **시트 순서**: `그룹 없음` 이 맨 앞, 그 뒤로 ``Project.groups`` 의 **저장된 순서**다
    (research R6). 정렬하지 않는 이유는 그것이 정본의 순서이기 때문이다 — 화면이 보기 좋으려고
    하는 정렬은 자산의 순서가 아니다.

    테스트가 없는 그룹도 머리글만 있는 시트를 갖는다 (FR-002). 그룹이 사라진 것처럼 보이면
    사용자는 자기가 만든 그룹을 파일에서 찾지 못한다.
    """
    report = ExportReport(unreadable=list(unreadable or []))

    by_prefix: dict[str, list[Test]] = {RESERVED_PREFIX: []}
    for group in project.groups:
        by_prefix[group.prefix] = []
    for test in tests:
        by_prefix.setdefault(prefix_of(test.id), []).append(test)

    # 이름 짓기: 그룹 없음 먼저, 그다음 저장된 그룹 순서, 마지막으로 정의 없는 접두어.
    ordered_prefixes = [RESERVED_PREFIX]
    ordered_prefixes += [g.prefix for g in project.groups]
    ordered_prefixes += [
        p for p in by_prefix if p not in ordered_prefixes
    ]

    names_by_prefix = {g.prefix: g.name for g in project.groups}
    raw_names = [
        UNGROUPED_SHEET_NAME if p == RESERVED_PREFIX else names_by_prefix.get(p, p)
        for p in ordered_prefixes
    ]
    sheet_names, renames = assign(raw_names)
    report.sheet_renames = renames

    header = [c.value for c in ORDER]
    outcome_column = ORDER.index(Column.OUTCOME)

    specs: list[SheetSpec] = []
    for prefix, sheet_name in zip(ordered_prefixes, sheet_names, strict=True):
        group_tests = sorted(by_prefix.get(prefix, []), key=lambda t: t.id)
        rows = [row_for(t, outcomes.get(t.id)) for t in group_tests]
        _record_truncations(group_tests, report)
        specs.append(
            SheetSpec(
                name=sheet_name,
                header=header,
                rows=rows,
                outcome_column=outcome_column,
            )
        )
        report.test_count += len(group_tests)

    report.sheet_count = len(specs)
    return specs, report


def _record_truncations(tests: list[Test], report: ExportReport) -> None:
    """셀 한도를 넘을 칸을 미리 기록한다 (FR-010).

    실제로 자르는 것은 :func:`itb.portability.workbook.clamp_cell` 이다. 여기서는
    사용자에게 **어느 테스트의 어느 칸이** 잘렸는지 말하려고 다시 센다 — 자르는 쪽은
    셀 값만 알고 그것이 어느 테스트의 것인지 모른다.
    """
    from itb.portability.limits import MAX_CELL_CHARS

    for test in tests:
        procedure, expectation = split_steps(test)
        for column, labels in (
            (Column.PROCEDURE, procedure),
            (Column.EXPECTATION, expectation),
        ):
            text = numbered(labels)
            if len(text) <= MAX_CELL_CHARS:
                continue
            kept = 0
            used = 0
            for line in text.splitlines():
                if used + len(line) + 1 > MAX_CELL_CHARS - 40:
                    break
                kept += 1
                used += len(line) + 1
            report.truncations.append(
                Truncation(
                    test_id=test.id,
                    column=column.value,
                    kept_lines=kept,
                    dropped_lines=len(labels) - kept,
                )
            )
