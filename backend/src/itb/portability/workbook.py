"""openpyxl 과 닿는 유일한 지점 (기능 014).

이 모듈 밖으로 openpyxl 타입이 나가지 않는다. 나가기 시작하면 라이브러리를 바꾸는 일이
패키지 전체를 고치는 일이 되고, 더 나쁘게는 셀 객체가 도메인 코드까지 흘러든다.

담는 것:

- :func:`escape_cell` — 수식 주입 방어 (research R13)
- :func:`inspect_archive` — 열기 **전에** zip 폭탄을 판정 (research R3)
- :func:`read_sheets` — 읽기. ``read_only`` 스트리밍
- :func:`write_workbook` — 쓰기. ``BytesIO`` 로 바이트를 만든다
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field

from itb.portability.limits import (
    MAX_CELL_CHARS,
    MAX_COMPRESSION_RATIO,
    MAX_DATA_ROWS,
    MAX_SHEETS,
    MAX_UNCOMPRESSED_BYTES,
)

_FORMULA_LEADERS = ("=", "+", "-", "@", "\t", "\r")
"""이 문자로 시작하는 셀은 일부 스프레드시트가 **수식으로 해석한다**.

`=cmd|' /C calc'!A1` 같은 값은 실행 가능한 것으로 다뤄지기도 한다. 우리가 내보낸 파일은
남이 연다 — 우리 손을 떠난 곳에서 터진다.
"""

TRUNCATION_MARK = "… (이하 {n}줄 생략)"


class WorkbookError(Exception):
    """워크북을 읽거나 쓰지 못했다."""


class ArchiveRejected(WorkbookError):
    """파일을 해석하기 **전에** 거절했다 (FR-036).

    :attr:`kind` 가 어느 상한인지 말한다 — ``uncompressed_bytes`` · ``compression_ratio`` ·
    ``not_xlsx`` · ``corrupt``.
    """

    def __init__(self, kind: str, message: str, *, limit: int | None = None,
                 actual: int | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.limit = limit
        self.actual = actual


def escape_cell(value: str) -> str:
    """셀 값이 수식으로 해석되지 않게 고정한다 (FR-009 · research R13).

    앞에 작은따옴표를 붙이면 스프레드시트가 그 뒤를 텍스트로 다룬다. 작은따옴표 자체는
    화면에 보이지 않는다.

    빈 문자열은 그대로 둔다 — 붙일 것이 없다.
    """
    if value and value.startswith(_FORMULA_LEADERS):
        return f"'{value}"
    return value


def clamp_cell(value: str) -> str:
    """셀 한도를 넘는 값을 자르고 잘렸음을 남긴다 (FR-010).

    **파일 생성을 실패시키지 않는다.** 스텝이 아주 많은 테스트 하나 때문에 프로젝트 전체를
    내보내지 못하면, 사용자는 그 하나를 찾아 지우기 전에는 아무것도 할 수 없다.

    잘린 사실을 칸 안에 남기는 이유는, 파일만 보는 사람에게도 그것이 전부가 아님을 알리기
    위해서다 — 경고는 화면에만 있고 파일은 남에게 전달된다.
    """
    if len(value) <= MAX_CELL_CHARS:
        return value

    lines = value.splitlines()
    kept: list[str] = []
    used = 0
    # 표시 문구가 들어갈 자리를 미리 비워 둔다.
    budget = MAX_CELL_CHARS - len(TRUNCATION_MARK.format(n=len(lines)))
    for line in lines:
        if used + len(line) + 1 > budget:
            break
        kept.append(line)
        used += len(line) + 1
    dropped = len(lines) - len(kept)
    kept.append(TRUNCATION_MARK.format(n=dropped))
    return "\n".join(kept)[:MAX_CELL_CHARS]


@dataclass(frozen=True, slots=True)
class ArchiveReport:
    """zip 검사 결과."""

    entries: int
    compressed: int
    uncompressed: int


def inspect_archive(data: bytes) -> ArchiveReport:
    """``.xlsx`` 를 **열기 전에** 압축 폭탄을 판정한다 (research R3).

    ``.xlsx`` 는 zip 이다. 100MB 짜리 파일이 압축을 풀면 수십 GB 가 될 수 있으므로 업로드
    바이트 상한만으로는 부족하다. ``infolist()`` 는 중앙 디렉터리만 읽으므로 내용을 풀지
    않고도 총량을 알 수 있다.

    **압축비도 함께 본다.** 총량이 상한 안에 들어도 비가 비정상적으로 높으면 정상적인
    스프레드시트가 아니다 — 총량 검사만으로는 작은 폭탄을 놓친다.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = zf.infolist()
            uncompressed = sum(i.file_size for i in infos)
            compressed = sum(i.compress_size for i in infos)
            names = {i.filename for i in infos}
    except zipfile.BadZipFile as exc:
        raise ArchiveRejected(
            "not_xlsx",
            "스프레드시트 파일(.xlsx)이 아니거나 파일이 손상됐습니다.",
        ) from exc

    # .xlsx 라면 반드시 있는 항목. 이름만 .xlsx 인 다른 zip 을 여기서 거른다.
    if "[Content_Types].xml" not in names:
        raise ArchiveRejected(
            "not_xlsx",
            "스프레드시트 파일(.xlsx)이 아닙니다.",
        )

    if uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise ArchiveRejected(
            "uncompressed_bytes",
            f"압축을 푼 크기가 상한을 넘습니다 "
            f"({uncompressed:,}B > {MAX_UNCOMPRESSED_BYTES:,}B).",
            limit=MAX_UNCOMPRESSED_BYTES,
            actual=uncompressed,
        )

    if compressed > 0 and uncompressed // max(compressed, 1) > MAX_COMPRESSION_RATIO:
        raise ArchiveRejected(
            "compression_ratio",
            "압축비가 비정상적으로 높습니다. 정상적인 스프레드시트가 아닙니다.",
            limit=MAX_COMPRESSION_RATIO,
            actual=uncompressed // max(compressed, 1),
        )

    return ArchiveReport(entries=len(infos), compressed=compressed, uncompressed=uncompressed)


@dataclass(slots=True)
class ParsedSheet:
    """읽어 들인 시트 하나. openpyxl 타입을 담지 않는다."""

    name: str
    header: list[object] = field(default_factory=list)
    rows: list[tuple[int, list[object]]] = field(default_factory=list)
    """``(엑셀 행 번호, 셀 값들)``. 행 번호를 들고 다니는 이유는 건너뛴 행을 사용자에게
    **어디인지** 말해 주기 위해서다 (FR-018)."""


@dataclass(slots=True)
class ParsedWorkbook:
    sheets: list[ParsedSheet] = field(default_factory=list)
    total_rows: int = 0


def read_sheets(data: bytes) -> ParsedWorkbook:
    """워크북을 읽는다. 상한을 넘으면 :class:`ArchiveRejected` (FR-036).

    ``read_only=True`` 로 흘려 읽으며 세다가 상한에서 **즉시 중단한다** — 다 읽고 나서 세면
    상한이 없는 것과 같다.

    ``data_only=True`` 로 연다: 수식이 든 셀은 마지막으로 계산된 값을 준다. 우리는 표의 글을
    읽으려는 것이지 계산을 재현하려는 것이 아니다.
    """
    inspect_archive(data)

    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl 은 다양한 예외를 낸다
        raise ArchiveRejected(
            "corrupt",
            "스프레드시트를 열지 못했습니다. 파일이 손상됐을 수 있습니다.",
        ) from exc

    try:
        names = wb.sheetnames
        if len(names) > MAX_SHEETS:
            raise ArchiveRejected(
                "sheet_count",
                f"시트가 상한({MAX_SHEETS}개)을 넘습니다. 이 파일은 {len(names)}개입니다.",
                limit=MAX_SHEETS,
                actual=len(names),
            )

        parsed = ParsedWorkbook()
        for name in names:
            ws = wb[name]
            sheet = ParsedSheet(name=name)
            for excel_row, raw in enumerate(ws.iter_rows(values_only=True), start=1):
                cells = list(raw)
                if excel_row == 1:
                    sheet.header = cells
                    continue
                sheet.rows.append((excel_row, cells))
                parsed.total_rows += 1
                if parsed.total_rows > MAX_DATA_ROWS:
                    raise ArchiveRejected(
                        "row_count",
                        f"데이터 행이 상한({MAX_DATA_ROWS:,}개)을 넘습니다.",
                        limit=MAX_DATA_ROWS,
                        actual=parsed.total_rows,
                    )
            parsed.sheets.append(sheet)
        return parsed
    finally:
        wb.close()


@dataclass(slots=True)
class SheetSpec:
    """쓸 시트 하나."""

    name: str
    header: list[str]
    rows: list[list[str]]
    outcome_column: int | None = None
    """결과 칸의 열 번호 (0부터). 서식을 입힐 자리를 알려 준다."""


def write_workbook(sheets: list[SheetSpec]) -> bytes:
    """시트들을 ``.xlsx`` 바이트로 만든다 (research R9).

    ``BytesIO`` 로 만들어 바이트를 돌려준다 — 임시 파일을 쓰면 정리 책임이 생기고, 테스트
    999개 규모에서도 수 MB 라 메모리에 두는 편이 단순하다.

    모든 셀 값에 :func:`escape_cell` 과 :func:`clamp_cell` 을 적용한다. 호출자가 잊을 수
    있는 자리를 남기지 않는다.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    # Workbook() 이 만들어 두는 기본 시트를 지운다. 남기면 빈 "Sheet" 가 딸려 나간다.
    wb.remove(wb.active)

    header_font = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="EEEEEE")
    wrap = Alignment(vertical="top", wrap_text=True)
    center = Alignment(vertical="center", horizontal="center")

    for spec in sheets:
        ws = wb.create_sheet(title=spec.name)
        ws.append([escape_cell(h) for h in spec.header])
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        for row in spec.rows:
            ws.append([clamp_cell(escape_cell(v)) for v in row])

        # 머리글 고정 — 아래로 스크롤해도 컬럼 이름이 보인다 (US4).
        ws.freeze_panes = "A2"

        for pos, _name in enumerate(spec.header, start=1):
            letter = get_column_letter(pos)
            ws.column_dimensions[letter].width = _WIDTHS.get(pos - 1, 18)
        for row_cells in ws.iter_rows(min_row=2):
            for cell in row_cells:
                cell.alignment = wrap

        # 결과 칸 서식 (US4 · FR-006a). **다섯 상태가 눈으로 구분돼야 한다** — 이 파일은
        # 회의 자료가 되고, 거기서 통과와 부분 통과가 같아 보이면 보고가 틀린다.
        if spec.outcome_column is not None:
            letter = get_column_letter(spec.outcome_column + 1)
            for pos in range(2, ws.max_row + 1):
                cell = ws[f"{letter}{pos}"]
                style = _OUTCOME_STYLE.get(str(cell.value or ""))
                cell.alignment = center
                if style is None:
                    continue
                cell.fill = PatternFill("solid", fgColor=style[0])
                cell.font = Font(bold=True, color=style[1])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


_WIDTHS = {0: 12, 1: 28, 2: 34, 3: 12, 4: 46, 5: 46, 6: 10}
"""열 너비. 「수행 절차」·「기대 결과」는 여러 줄이라 넓게 잡는다 (US4)."""

_OUTCOME_STYLE: dict[str, tuple[str, str]] = {
    "P": ("DFF3E3", "1B5E20"),
    "F": ("FBE3E3", "8E1B1B"),
    "P(부분)": ("FFF3D6", "7A5200"),
    "중지": ("EDEDED", "4A4A4A"),
}
"""결과 표기 → (배경, 글자) 색 (US4 · FR-006a).

**색만으로 구분하지 않는다.** 칸 안에 글자가 이미 있고(`P`·`F`·`P(부분)`·`중지`) 색은
그것을 거드는 것뿐이다 — 색을 못 보는 사람도 표를 읽을 수 있어야 한다. 미실행은 빈 칸이라
여기 없다.
"""
