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
import re
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


_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
"""엑셀 형식이 셀에 담을 수 없는 제어문자.

줄바꿈(``\n``)과 탭(``\t``)은 뺀다 — 「수행 절차」가 여러 줄이므로 그 둘은 정상이다.
"""


def escape_cell(value: str) -> str:
    """셀 값을 안전하게 만든다 (FR-009·FR-013 · research R13).

    둘을 한다.

    1. **수식으로 해석되지 않게 고정한다.** 앞에 작은따옴표를 붙이면 스프레드시트가 그
       뒤를 텍스트로 다루고, 작은따옴표 자체는 화면에 보이지 않는다.
    2. **엑셀이 담을 수 없는 제어문자를 지운다.** 녹화된 라벨에는 페이지에서 읽어 온
       글자가 섞일 수 있고, 그중 제어문자가 있으면 openpyxl 이 ``IllegalCharacterError``
       를 낸다 — 그러면 프로젝트 전체를 내보내지 못한다 (수렴 T093).

    빈 문자열은 그대로 둔다 — 붙일 것이 없다.
    """
    cleaned = _ILLEGAL.sub("", value)
    if cleaned and cleaned.startswith(_FORMULA_LEADERS):
        return f"'{cleaned}"
    return cleaned


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


_SHEET_TAG = re.compile(rb"<sheet\b[^>]*/?>")
_REL_TAG = re.compile(rb"<Relationship\b[^>]*/?>")
_ATTR = re.compile(rb'([\w:]+)="([^"]*)"')
"""**속성 순서를 가정하지 않는다.** 쓰는 도구마다 순서가 다르다 — openpyxl 은 rels 에
``Target`` 을 ``Id`` 보다 먼저 쓰고, 다른 도구는 반대로 쓴다. 순서를 가정한 정규식은
그중 하나에서만 동작한다 (실측으로 잡았다)."""
_MERGE_TAG = re.compile(rb'<mergeCell[^>]*ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"')
_CHUNK = 1 << 20
"""병합 정보를 훑을 때 한 번에 읽는 크기. 시트 XML 을 통째로 메모리에 올리지 않는다."""


def _column_number(letters: str) -> int:
    """``"AB"`` → ``28``. 엑셀의 열 문자를 1부터의 번호로."""
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def merged_ranges(data: bytes) -> dict[str, list[tuple[int, int, int, int]]]:
    """시트 이름 → 병합 구간들 ``(첫행, 첫열, 끝행, 끝열)``, 모두 1부터.

    **``read_only`` 로는 이 정보를 얻을 수 없다.** openpyxl 의 ``ReadOnlyWorksheet`` 에는
    ``merged_cells`` 가 아예 없고(실측), 병합된 칸은 값 없이 ``None`` 으로 온다. 그대로
    두면 「대상기능」이 여러 행에 걸쳐 병합된 설계서에서 **둘째 행부터 제목이 빈 행으로
    보여 통째로 건너뛰어진다** — 설계서에서 아주 흔한 모양이다.

    그렇다고 ``read_only`` 를 포기하면 5,000행짜리 파일을 통째로 메모리에 올리게 된다.
    그래서 시트 XML 에서 ``<mergeCell>`` 만 **조각내어 훑는다** — XML 을 파싱하지 않으므로
    실체 확장 공격에도 노출되지 않고, 메모리도 조각 크기로 유계다.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = set(zf.namelist())
        if "xl/workbook.xml" not in names:
            return {}

        rels: dict[bytes, bytes] = {}
        if "xl/_rels/workbook.xml.rels" in names:
            for tag in _REL_TAG.findall(zf.read("xl/_rels/workbook.xml.rels")):
                attrs = dict(_ATTR.findall(tag))
                rid, target = attrs.get(b"Id"), attrs.get(b"Target")
                if rid is not None and target is not None:
                    rels[rid] = target

        out: dict[str, list[tuple[int, int, int, int]]] = {}
        for tag in _SHEET_TAG.findall(zf.read("xl/workbook.xml")):
            attrs = dict(_ATTR.findall(tag))
            raw_name, rid = attrs.get(b"name"), attrs.get(b"r:id")
            if raw_name is None or rid is None:
                continue
            target = rels.get(rid)
            if target is None:
                continue
            path = target.decode("utf-8").lstrip("/")
            member = path if path.startswith("xl/") else f"xl/{path}"
            if member not in names:
                continue

            found: list[tuple[int, int, int, int]] = []
            with zf.open(member) as handle:
                tail = b""
                while True:
                    chunk = handle.read(_CHUNK)
                    if not chunk:
                        break
                    blob = tail + chunk
                    for c1, r1, c2, r2 in _MERGE_TAG.findall(blob):
                        found.append(
                            (
                                int(r1),
                                _column_number(c1.decode()),
                                int(r2),
                                _column_number(c2.decode()),
                            )
                        )
                    # 조각 경계에 걸친 태그를 놓치지 않게 꼬리를 남긴다.
                    tail = blob[-200:]
            if found:
                out[_unescape(raw_name.decode("utf-8"))] = found
        return out


def _unescape(name: str) -> str:
    """XML 속성에서 온 시트 이름의 실체 참조를 되돌린다."""
    return (
        name.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
    )


def fill_merged(
    excel_row: int, cells: list[object], ranges: list[tuple[int, int, int, int]],
    anchors: dict[tuple[int, int], object],
) -> list[object]:
    """병합된 칸에 **대표 칸의 값을 채워 넣는다** (2차 요청).

    엑셀은 병합 구간의 왼쪽 위 칸에만 값을 두고 나머지는 비운다. 사용자가 화면에서 보는
    것은 「모든 칸에 그 값이 있다」이므로, 우리도 그렇게 읽어야 사용자의 눈과 제품의
    판단이 어긋나지 않는다.

    위에서 아래로 읽으므로 대표 칸을 항상 먼저 지난다 — 그때 값을 기억해 두었다가
    아래 행에서 쓴다.
    """
    filled = list(cells)
    for first_row, first_col, last_row, last_col in ranges:
        if not (first_row <= excel_row <= last_row):
            continue
        key = (first_row, first_col)
        if excel_row == first_row:
            pos = first_col - 1
            if pos < len(filled) and filled[pos] is not None:
                anchors[key] = filled[pos]
        value = anchors.get(key)
        if value is None:
            continue
        for col in range(first_col, last_col + 1):
            pos = col - 1
            while len(filled) <= pos:
                filled.append(None)
            if filled[pos] is None:
                filled[pos] = value
    return filled


@dataclass(slots=True)
class ParsedSheet:
    """읽어 들인 시트 하나. openpyxl 타입을 담지 않는다."""

    name: str
    rows: list[tuple[int, list[object]]] = field(default_factory=list)
    """``(엑셀 행 번호, 셀 값들)`` — **머리글 행을 포함한** 비어 있지 않은 행 전부.

    행 번호를 들고 다니는 이유는 둘이다. 건너뛴 행을 사용자에게 **어디인지** 말해야 하고
    (FR-018), **어느 행이 머리글인지 사용자가 고를 수 있어야** 하기 때문이다 (FR-020i).

    머리글을 여기서 떼어 내지 않는 이유가 그 둘째다. 설계서는 위쪽에 제목·작성일·범례를
    두는 일이 흔해 첫 행이 머리글이 아닌 경우가 많다. 첫 행을 머리글로 못박아 두면 그런
    파일은 필수 컬럼을 영영 찾지 못한다.
    """


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

    # 병합 정보는 read_only 로 얻을 수 없어 XML 에서 따로 읽는다 (2차 요청).
    merges = merged_ranges(data)

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
            ranges = merges.get(name, [])
            anchors: dict[tuple[int, int], object] = {}
            for excel_row, raw in enumerate(ws.iter_rows(values_only=True), start=1):
                cells = list(raw)
                # **병합을 먼저 채운다.** 빈 행 판정보다 앞이어야 한다 — 병합된 칸은
                # 값 없이 오므로, 먼저 재면 「대상기능」이 여러 행에 걸쳐 병합된 행이
                # 통째로 빈 행으로 보인다.
                if ranges:
                    cells = fill_merged(excel_row, cells, ranges, anchors)
                # **전부 빈 행은 세지도 담지도 않는다** (FR-019 · 수렴 T087).
                #
                # 스프레드시트 도구는 값이 없는 행까지 사용 범위로 선언한다 — 구글 시트가
                # 내보낸 파일은 시트마다 기본 1,000행이고, `iter_rows` 는 그것을 전부
                # 돌려준다 (실측: 실데이터 1행짜리 시트가 1,000행). 그것을 세면 시트 여섯
                # 장짜리 정상 파일이 행 상한(5,000)에 걸려 **통째로 거절된다.**
                #
                # 담지 않는 이유도 같다. 담으면 미리보기의 「건너뛸 행」에 수백 건의
                # 「빈 행」이 나열돼, 사용자가 정말 봐야 하는 「제목이 빈 행」이 묻힌다
                # (SC-006).
                if all(c is None or str(c).strip() == "" for c in cells):
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
            # 상한은 **데이터 행**에 대한 것이다. 머리글 한 줄은 데이터가 아니므로 뺀다.
            if sheet.rows:
                parsed.total_rows -= 1
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
    try:
        wb.save(buffer)
    except Exception as exc:
        # openpyxl 이 내는 예외를 그대로 두면 앱의 포괄 핸들러로 떨어져 **원인도 다음
        # 행동도 없는 500** 이 된다 (수렴 T092). 여기서 감싸야 `EXPORT_FAILED` 로 나간다.
        msg = f"워크북을 만들지 못했습니다: {exc}"
        raise WorkbookError(msg) from exc
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
