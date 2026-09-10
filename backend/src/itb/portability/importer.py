"""워크북 → 가져오기 계획 (기능 014 US2).

**계획은 아직 아무것도 만들지 않은 상태다.** 미리보기가 이것을 보여 주고, 사용자가 확정해야
비로소 그룹과 초안이 생긴다 (FR-016). 그래서 계획은 디스크에 쓰지 않고 서버 메모리에만 있다 —
디스크에 쓰면 그 자체가 "만든 것"이 된다.

이 모듈은 openpyxl 타입을 받지 않는다. :func:`itb.portability.workbook.read_sheets` 가
돌려주는 순수한 자료구조만 본다.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from itb.domain.test_case import (
    GROUP_PREFIX_PATTERN,
    RESERVED_PREFIX,
    TEST_ID_PATTERN,
    Project,
)
from itb.portability.columns import (
    ORDER,
    REQUIRED,
    Column,
    HeaderMap,
    conflicting_overrides,
    header_labels,
    map_headers,
)
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME
from itb.portability.workbook import ParsedWorkbook

_TEST_ID_RE = re.compile(TEST_ID_PATTERN)
_GROUP_PREFIX_RE = re.compile(GROUP_PREFIX_PATTERN)

MAX_TEXT = 2000
"""초안의 긴 텍스트 칸 상한. :class:`itb.domain.draft.Draft` 의 필드 상한과 같아야 한다."""

MAX_NAME = 200
MAX_ACTOR = 100


class PrefixSource(StrEnum):
    """이 시트의 접두어를 어디서 알았는가."""

    FROM_ROWS = "from_rows"
    """행의 TC ID 에서 읽었다 (FR-022)."""

    USER_SUPPLIED = "user_supplied"
    """사용자가 미리보기에서 입력했다 (FR-022a)."""

    UNGROUPED = "ungrouped"
    """그룹 없음 시트다."""


class SkipReason(StrEnum):
    NO_TITLE = "no_title"
    """「대상기능」 칸이 비었다 (FR-018)."""

    NO_COLUMNS = "no_columns"
    """필수 컬럼을 찾지 못했다 (FR-017). 시트 전체가 대상이다."""

    EMPTY = "empty"
    """완전히 빈 행 (FR-019).

    **실제 경로에서는 여기까지 오지 않는다** — :func:`itb.portability.workbook.read_sheets`
    가 읽는 단계에서 이미 걸러낸다 (T087). 남겨 두는 이유는 :func:`plan_sheet` 이 행의
    출처를 모르기 때문이다: 읽기를 거치지 않은 행이 들어와도 판정이 성립해야 한다.
    """


@dataclass(frozen=True, slots=True)
class RowPlan:
    row: int
    name: str
    description: str | None
    actor: str | None
    procedure: str | None
    expectation: str | None
    desired_test_id: str | None
    renumbered_from: str | None = None
    """파일 안 중복이라 번호가 바뀌었으면 원래 값 (FR-023b)."""


@dataclass(frozen=True, slots=True)
class SkippedRow:
    sheet_name: str
    row: int
    reason: SkipReason


@dataclass(slots=True)
class SheetPlan:
    sheet_name: str
    prefix: str | None
    prefix_source: PrefixSource | None
    group_name: str
    existing_group_name: str | None = None
    rows: list[RowPlan] = field(default_factory=list)

    headers: list[str] = field(default_factory=list)
    """이 시트의 실제 머리글 목록 (FR-020f).

    사용자가 컬럼을 짝지으려면 **어떤 열이 있는지** 봐야 한다.
    """

    column_index: dict[str, int] = field(default_factory=dict)
    """지금 정해진 컬럼 → 열 번호. 자동 판정과 사용자 지정이 합쳐진 결과다."""

    missing_required: list[str] = field(default_factory=list)
    """찾지 못한 필수 컬럼. 비어 있지 않으면 짝지어야 쓸 수 있다 (FR-020g)."""

    included: bool = True
    """이 시트를 가져오는가 (FR-020a). 기본은 가져오기다."""

    header_row: int | None = None
    """머리글로 쓰는 엑셀 행 번호 (FR-020i). 사용자가 고칠 수 있다."""

    sample: list[tuple[int, list[str]]] = field(default_factory=list)
    """앞부분 몇 줄 (FR-020j). 사용자가 **어느 행이 머리글인지 눈으로 보고** 고른다."""

    total_rows: int = 0
    """머리글을 뺀 실제 행 수. 필수 컬럼이 없어 :attr:`rows` 를 못 채웠을 때도
    사용자에게 「여기 몇 건이 있다」를 보여 주기 위해 따로 센다."""

    @property
    def usable(self) -> bool:
        """필수 컬럼이 다 있는가 (FR-020g)."""
        return not self.missing_required

    @property
    def needs_prefix(self) -> bool:
        """접두어를 사용자에게 물어야 하는가 (FR-022a)."""
        return self.prefix is None and self.usable

    @property
    def name_differs(self) -> bool:
        """이미 있는 그룹의 이름이 시트 이름과 다른가 (FR-024a).

        다르면 **기존 이름을 유지한다.** 가져오기는 더하는 일이지 고치는 일이 아니다.
        """
        return self.existing_group_name is not None and self.existing_group_name != self.group_name


@dataclass(slots=True)
class ImportPlan:
    plan_id: str
    file_name: str
    created_at: datetime
    sheets: list[SheetPlan] = field(default_factory=list)
    skipped: list[SkippedRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def draft_count(self) -> int:
        """실제로 만들어질 초안 수.

        **접두어가 정해진 시트만 센다.** 접두어를 묻는 시트는 사용자가 비워 두면 통째로
        건너뛰므로(FR-022b), 세어 두면 미리보기가 예고한 수와 결과가 어긋난다 (SC-005).
        """
        return sum(
            len(s.rows) for s in self.sheets if s.included and s.usable and s.prefix is not None
        )

    @property
    def needs_prefix(self) -> list[str]:
        return [s.sheet_name for s in self.sheets if s.included and s.needs_prefix]

    @property
    def needs_columns(self) -> list[str]:
        """필수 컬럼을 짝지어야 하는 시트들 (FR-020g)."""
        return [s.sheet_name for s in self.sheets if s.included and not s.usable]


def new_plan_id() -> str:
    return f"pl_{secrets.token_hex(4)}"


def _text(raw: object, limit: int) -> str | None:
    """셀 값을 초안이 받을 수 있는 문자열로 만든다 (FR-037).

    **길이를 넘으면 자른다.** 거절하지 않는 이유는, 설계서의 설명이 조금 길다는 이유로
    행 하나를 버리면 사용자가 잃는 것이 더 크기 때문이다. 자른 사실은 원본 파일이 그대로
    남아 있으므로 되짚을 수 있다.
    """
    if raw is None:
        return None
    text = unicodedata.normalize("NFC", str(raw)).strip()
    if not text:
        return None
    return text[:limit]


def _desired_id(raw: object, prefix: str) -> str | None:
    """TC ID 칸을 식별자로 만든다. 형식에 안 맞으면 ``None``.

    접두어가 그 시트의 접두어와 다르면 **번호만 가져온다** — 접두어가 곧 소속이므로
    시트가 정한 소속을 따른다 (FR-023 이 혼재를 미리보기에서 알린다).
    """
    text = _text(raw, 32)
    if text is None:
        return None
    upper = text.upper()
    if not _TEST_ID_RE.match(upper):
        return None
    number = upper.split("-", 1)[1]
    return f"{prefix}-{number}"


def read_prefix(rows: list[tuple[int, list[object]]], headers: HeaderMap) -> str | None:
    """행의 TC ID 들에서 그룹 접두어를 읽는다 (FR-022).

    **가장 많이 나온 접두어**를 쓴다. 한 시트에 접두어가 섞여 있으면 그것이 다수결로
    정해지고, 섞였다는 사실은 :func:`plan_sheet` 이 경고로 알린다 (FR-023).

    읽을 수 없으면 ``None`` — 시스템이 시트 이름 등에서 **만들어내지 않는다** (FR-022a).
    """
    counts: dict[str, int] = {}
    for _row, cells in rows:
        text = _text(headers.value(cells, Column.TC_ID), 32)
        if text is None:
            continue
        upper = text.upper()
        if not _TEST_ID_RE.match(upper):
            continue
        prefix = upper.split("-", 1)[0]
        counts[prefix] = counts.get(prefix, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def is_ungrouped_sheet(name: str) -> bool:
    """그룹 없음 시트인가.

    우리가 내보낸 파일이 다시 들어오는 경우를 위해 이름으로 알아본다. 사람이 쓴 설계서에는
    이 이름이 없을 것이므로, 그때는 접두어가 `TC` 인지로 판단한다.
    """
    return name.strip() == UNGROUPED_SHEET_NAME


SAMPLE_ROWS = 8
"""미리보기에 실어 보내는 앞부분 행 수 (FR-020j).

사용자가 「어느 행이 머리글인가」를 고르려면 **그 행들을 봐야 한다.** 여덟 줄이면
제목·작성일·범례가 위에 붙은 흔한 설계서의 머리글까지 닿는다.
"""


def detect_header_row(rows: list[tuple[int, list[object]]]) -> int | None:
    """머리글로 보이는 행의 엑셀 행 번호 (FR-020i).

    **필수 컬럼을 가장 많이 알아볼 수 있는 행**을 고르고, 같으면 위쪽을 쓴다. 첫 행을
    못박지 않는 이유는 설계서가 위에 제목·작성일·범례를 두는 일이 흔하기 때문이다 —
    그런 파일에서 첫 행을 머리글로 삼으면 필수 컬럼을 영영 찾지 못한다.

    아무 행도 필수 컬럼을 갖지 못하면 **첫 행**을 돌려준다. 사용자가 열을 짝지을 때
    기준이 될 행은 있어야 하고, 어느 행인지는 사용자가 고칠 수 있다 (FR-020i).
    """
    if not rows:
        return None

    best: tuple[int, int] | None = None  # (알아본 필수 컬럼 수, 행 번호)
    for excel_row, cells in rows[:SAMPLE_ROWS]:
        found = len(REQUIRED) - len(map_headers(cells).missing_required)
        if best is None or found > best[0]:
            best = (found, excel_row)

    if best is not None and best[0] > 0:
        return best[1]
    return rows[0][0]


def split_at_header(
    rows: list[tuple[int, list[object]]], header_row: int | None
) -> tuple[list[object], list[tuple[int, list[object]]]]:
    """``(머리글 셀들, 그 아래 데이터 행들)``.

    머리글 **위쪽 행은 버린다** — 제목·작성일 같은 것이고 데이터가 아니다.
    """
    if header_row is None:
        return [], []
    header: list[object] = []
    data: list[tuple[int, list[object]]] = []
    for excel_row, cells in rows:
        if excel_row == header_row:
            header = cells
        elif excel_row > header_row:
            data.append((excel_row, cells))
    return header, data


def plan_sheet(
    sheet_name: str,
    all_rows: list[tuple[int, list[object]]],
    *,
    existing_groups: dict[str, str],
    user_prefix: str | None = None,
    included: bool = True,
    column_overrides: dict[Column, int] | None = None,
    header_row_number: int | None = None,
) -> tuple[SheetPlan, list[SkippedRow], list[str]]:
    """시트 하나를 계획으로 만든다.

    돌려주는 것은 ``(계획, 건너뛴 행들, 경고들)``.

    **필수 컬럼을 못 찾아도 계획을 돌려준다** (FR-020g). 예전에는 여기서 ``None`` 을
    돌려 시트가 계획에서 통째로 사라졌고, 그래서 사용자는 화면에서 그 열을 보고 있는데도
    짝지을 자리가 없었다. 이제는 계획에 남기고 :attr:`SheetPlan.missing_required` 로
    무엇이 없는지 말한다 — 사용자가 짝지으면 그때 살아난다.
    """
    skipped: list[SkippedRow] = []
    warnings: list[str] = []

    chosen_header = header_row_number or detect_header_row(all_rows)
    header_row, rows = split_at_header(all_rows, chosen_header)
    sample = [
        (n, [("" if c is None else str(c).strip()) for c in cells])
        for n, cells in all_rows[:SAMPLE_ROWS]
    ]

    labels = header_labels(header_row)
    headers = map_headers(header_row, overrides=column_overrides)
    missing = sorted(c.value for c in headers.missing_required)

    if not headers.usable:
        joined = ", ".join(missing)
        warnings.append(
            f"「{sheet_name}」 시트에서 필수 컬럼({joined})을 찾지 못했습니다. "
            "미리보기에서 열을 직접 짝지어 주세요."
        )
        skipped.append(SkippedRow(sheet_name=sheet_name, row=1, reason=SkipReason.NO_COLUMNS))
        return (
            SheetPlan(
                sheet_name=sheet_name,
                prefix=None,
                prefix_source=None,
                group_name=sheet_name,
                headers=labels,
                column_index={c.value: pos for c, pos in headers.index.items()},
                missing_required=missing,
                included=included,
                header_row=chosen_header,
                sample=sample,
                total_rows=len(rows),
            ),
            skipped,
            warnings,
        )

    ungrouped = is_ungrouped_sheet(sheet_name)
    if ungrouped:
        prefix: str | None = RESERVED_PREFIX
        source: PrefixSource | None = PrefixSource.UNGROUPED
    elif user_prefix:
        prefix = user_prefix.upper()
        source = PrefixSource.USER_SUPPLIED
    else:
        prefix = read_prefix(rows, headers)
        source = PrefixSource.FROM_ROWS if prefix else None
        if prefix == RESERVED_PREFIX:
            # 사람이 쓴 설계서가 TC-### 를 쓰고 있다. 그룹이 아니라 그룹 없음이다.
            source = PrefixSource.UNGROUPED

    # 한 시트에 접두어가 섞여 있으면 알린다 (FR-023).
    seen = {
        t.split("-", 1)[0]
        for _r, cells in rows
        if (t := (_text(headers.value(cells, Column.TC_ID), 32) or "").upper())
        and _TEST_ID_RE.match(t)
    }
    if len(seen) > 1:
        warnings.append(
            f"「{sheet_name}」 시트에 접두어가 섞여 있습니다 ({', '.join(sorted(seen))}). "
            f"{prefix} 를 이 시트의 그룹으로 삼습니다."
        )

    plan = SheetPlan(
        sheet_name=sheet_name,
        prefix=prefix,
        prefix_source=source,
        group_name=UNGROUPED_SHEET_NAME if ungrouped else sheet_name,
        existing_group_name=existing_groups.get(prefix) if prefix else None,
        headers=labels,
        column_index={c.value: pos for c, pos in headers.index.items()},
        missing_required=missing,
        included=included,
        header_row=chosen_header,
        sample=sample,
        total_rows=len(rows),
    )

    # **접두어를 몰라도 행은 만든다.** 확정에서 사용자가 접두어를 주면 그때 이 행들이
    # 쓰인다 — 여기서 비워 두면 확정이 접두어만 받고 만들 것을 잃는다. 미리보기가
    # "이 시트에 6건이 기다린다" 를 보여 줄 수 있는 것도 이 덕분이다.
    #
    # 다만 **수용량과 초안 수에는 세지 않는다** (:attr:`ImportPlan.draft_count`) —
    # 접두어를 비워 두면 이 시트는 통째로 건너뛰기 때문이다 (FR-022b).
    for excel_row, cells in rows:
        if all(_text(c, MAX_TEXT) is None for c in cells):
            skipped.append(
                SkippedRow(sheet_name=sheet_name, row=excel_row, reason=SkipReason.EMPTY)
            )
            continue
        name = _text(headers.value(cells, Column.NAME), MAX_NAME)
        if name is None:
            skipped.append(
                SkippedRow(sheet_name=sheet_name, row=excel_row, reason=SkipReason.NO_TITLE)
            )
            continue
        plan.rows.append(
            RowPlan(
                row=excel_row,
                name=name,
                description=_text(headers.value(cells, Column.DESCRIPTION), MAX_TEXT),
                actor=_text(headers.value(cells, Column.ACTOR), MAX_ACTOR),
                procedure=_text(headers.value(cells, Column.PROCEDURE), MAX_TEXT),
                expectation=_text(headers.value(cells, Column.EXPECTATION), MAX_TEXT),
                desired_test_id=(
                    _desired_id(headers.value(cells, Column.TC_ID), prefix)
                    if prefix is not None
                    else None
                ),
                # 「결과」 칸은 읽지 않는다 (FR-020) — 실행하지 않은 테스트에 결과를
                # 만들어 줄 수는 없다.
            )
        )

    return plan, skipped, warnings


def resolve_duplicates(plan: ImportPlan, *, taken: set[str]) -> None:
    """이미 쓰인 번호를 희망하는 행에 빈 번호를 준다 (FR-023a).

    **그룹 안에서 번호가 겹치는지를 본다** (014 3차 요청). `USER-001` 과 `DATA-001` 은
    서로 다른 자리이므로 한 통에 넣고 세면 있지도 않은 충돌을 만들어 낸다.

    **어떤 행도 이 때문에 버려지지 않는다.** 설계서의 복사·붙여넣기 실수는 흔하고, 그것
    때문에 행을 잃으면 사용자는 무엇이 사라졌는지 알기 어렵다.

    `taken` 은 프로젝트가 이미 쓰고 있는 식별자들이다. 초안은 번호를 예약하지 않지만
    (FR-032), 미리보기에서 미리 다른 번호를 보여 주는 편이 정직하다.
    """
    # **번호는 그룹마다 센다** (014 3차 요청). `USER-001` 과 `DATA-001` 은 서로 다른
    # 자리이므로 한 통에 넣고 세면 있지도 않은 충돌을 만들어 낸다.
    used: dict[str, set[int]] = {}
    for t in taken:
        n = _number_of(t)
        if n is not None:
            used.setdefault(t.split("-", 1)[0], set()).add(n)

    for sheet in plan.sheets:
        if sheet.prefix is None:
            continue
        mine = used.setdefault(sheet.prefix, set())
        resolved: list[RowPlan] = []
        for row in sheet.rows:
            wanted = row.desired_test_id
            number = _number_of(wanted) if wanted else None

            if number is not None and number not in mine:
                mine.add(number)
                resolved.append(row)
                continue
            if wanted is None:
                # 희망 번호가 없는 행. 저장 시점에 받는다.
                resolved.append(row)
                continue

            free = _next_free(sheet.prefix, mine)
            free_number = _number_of(free)
            if free_number is not None:
                mine.add(free_number)
            resolved.append(
                RowPlan(
                    row=row.row,
                    name=row.name,
                    description=row.description,
                    actor=row.actor,
                    procedure=row.procedure,
                    expectation=row.expectation,
                    desired_test_id=free,
                    renumbered_from=wanted,
                )
            )
        sheet.rows = resolved


def _number_of(test_id: str) -> int | None:
    """식별자의 번호 부분. 형식이 아니면 ``None``."""
    if "-" not in test_id:
        return None
    tail = test_id.split("-", 1)[1]
    return int(tail) if tail.isdigit() else None


def _next_free(prefix: str, used: set[int]) -> str:
    """그 그룹에서 비어 있는 번호 하나. 번호는 **그룹마다** 센다 (014 3차 요청)."""
    from itb.domain.test_case import MAX_TEST_NUMBER

    number = 1
    while number in used:
        number += 1
    if number > MAX_TEST_NUMBER:
        # 수용량 검사(FR-036b)가 확정 직전에 막지만, 계획을 세우는 중에도 넘칠 수 있다.
        # 그때는 상한 번호를 두고 저장 시점에 실제 번호를 받게 한다.
        return f"{prefix}-{MAX_TEST_NUMBER:03d}"
    return f"{prefix}-{number:03d}"


def build_plan(
    parsed: ParsedWorkbook,
    file_name: str,
    *,
    project: Project | None,
    taken_ids: set[str] | None = None,
    prefixes: dict[str, str] | None = None,
    selections: dict[str, bool] | None = None,
    column_overrides: dict[str, dict[str, int]] | None = None,
    header_rows: dict[str, int] | None = None,
) -> ImportPlan:
    """워크북 전체를 계획으로 만든다.

    `project` 가 ``None`` 이면 새 프로젝트를 만들며 가져오는 경우다 — 기존 그룹도
    쓰고 있는 식별자도 없다.

    `selections` 는 시트마다 가져올지 여부다 (FR-020a). 없으면 전부 가져온다.
    `column_overrides` 는 시트별 ``{컬럼 이름: 열 번호}`` 이며 자동 판정을 이긴다
    (FR-020e). 둘 다 미리보기에서 사용자가 정한다.
    """
    existing_groups = {g.prefix: g.name for g in project.groups} if project else {}
    supplied = {k: v for k, v in (prefixes or {}).items() if v}
    chosen = selections or {}
    overrides = column_overrides or {}

    plan = ImportPlan(
        plan_id=new_plan_id(),
        file_name=file_name,
        created_at=datetime.now(UTC),
    )

    for sheet in parsed.sheets:
        sheet_plan, skipped, warnings = plan_sheet(
            sheet.name,
            sheet.rows,
            existing_groups=existing_groups,
            user_prefix=supplied.get(sheet.name),
            included=chosen.get(sheet.name, True),
            column_overrides=_columns_of(overrides.get(sheet.name)),
            header_row_number=(header_rows or {}).get(sheet.name),
        )
        plan.sheets.append(sheet_plan)
        # **무시한 시트의 문제는 보고하지 않는다** — 사용자가 일부러 뺀 시트의 「제목이
        # 빈 행」을 알리는 것은 잡음이다 (FR-020c).
        if sheet_plan.included:
            plan.skipped.extend(skipped)
            plan.warnings.extend(warnings)

    resolve_duplicates(plan, taken=set(taken_ids or ()))
    return plan


def _columns_of(raw: dict[str, int] | None) -> dict[Column, int] | None:
    """``{"TC ID": 0}`` 을 ``{Column.TC_ID: 0}`` 으로. 모르는 이름은 무시한다."""
    if not raw:
        return None
    by_value = {c.value: c for c in ORDER}
    return {by_value[k]: v for k, v in raw.items() if k in by_value}


def validate_columns(raw: dict[str, int], headers: list[str]) -> str | None:
    """사용자가 준 컬럼 짝짓기를 검사한다 (FR-020h). 문제가 없으면 ``None``."""
    by_value = {c.value: c for c in ORDER}
    for name, pos in raw.items():
        if name not in by_value:
            return f"모르는 컬럼입니다: {name}"
        if pos >= len(headers):
            return f"「{name}」 에 지정한 열이 이 시트에 없습니다."
    clashes = conflicting_overrides(_columns_of(raw) or {})
    if clashes:
        names = ", ".join(headers[p] if p < len(headers) else str(p) for p in clashes)
        return f"한 열을 두 컬럼에 지정했습니다: {names}"
    return None


def validate_prefix(prefix: str) -> str | None:
    """사용자가 준 접두어를 검사한다 (FR-022c). 문제가 없으면 ``None``."""
    upper = prefix.strip().upper()
    if not _GROUP_PREFIX_RE.match(upper):
        return "그룹 접두어는 영문 대문자로 시작하는 8자 이내여야 합니다 (예: USER)."
    if upper == RESERVED_PREFIX:
        return f"{RESERVED_PREFIX} 는 그룹 없는 테스트가 씁니다. 다른 접두어를 쓰세요."
    return None
