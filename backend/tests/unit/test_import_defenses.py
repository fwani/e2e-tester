"""가져오기 파일 방어 3겹 (014 T039 · FR-036 · research R3).

**막는 시점이 늦으면 막지 않은 것과 같다.** 세 겹 모두 파일을 해석하기 *전에* 또는 흘려
읽는 *도중에* 판정하며, 다 읽고 나서 세지 않는다.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from excel_support import HEADER_ROW, build_xlsx

from itb.portability.limits import MAX_SHEETS, MAX_UNCOMPRESSED_BYTES
from itb.portability.workbook import ArchiveRejected, inspect_archive, read_sheets


class ArchiveGateTests:
    def test_정상_워크북은_통과한다(self) -> None:
        report = inspect_archive(build_xlsx({"시트": [["TC-001", "가"]]}))
        assert report.entries > 0
        assert report.uncompressed > 0

    def test_zip_이_아니면_거절한다(self) -> None:
        with pytest.raises(ArchiveRejected) as exc:
            inspect_archive(b"this is not a zip file at all")
        assert exc.value.kind == "not_xlsx"

    def test_zip_이지만_xlsx_가_아니면_거절한다(self) -> None:
        # 이름만 .xlsx 인 다른 zip 을 여기서 거른다.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("hello.txt", "hi")
        with pytest.raises(ArchiveRejected) as exc:
            inspect_archive(buffer.getvalue())
        assert exc.value.kind == "not_xlsx"

    def test_압축_해제_총량이_상한을_넘으면_거절한다(self) -> None:
        # 압축을 풀기 전에 판정한다 — 풀고 나서 재면 이미 메모리를 다 쓴 뒤다.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", "<x/>")
            zf.writestr("bomb", b"\0" * (MAX_UNCOMPRESSED_BYTES + 1))
        with pytest.raises(ArchiveRejected) as exc:
            inspect_archive(buffer.getvalue())
        assert exc.value.kind in ("uncompressed_bytes", "compression_ratio")

    def test_거절이_상한과_실제값을_함께_말한다(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", "<x/>")
            zf.writestr("bomb", b"\0" * (MAX_UNCOMPRESSED_BYTES + 1))
        with pytest.raises(ArchiveRejected) as exc:
            inspect_archive(buffer.getvalue())
        assert exc.value.limit is not None
        assert exc.value.actual is not None


class StructureGateTests:
    def test_정상_파일을_읽는다(self) -> None:
        parsed = read_sheets(build_xlsx({"회원": [["TC-001", "로그인"]]}))
        assert [s.name for s in parsed.sheets] == ["회원"]
        # 머리글 행도 rows 에 담긴다 — 어느 행이 머리글인지는 **사용자가 고른다**
        # (FR-020i). 여기서 떼어 내면 제목·범례가 위에 붙은 설계서를 다룰 수 없다.
        assert parsed.sheets[0].rows[0][1][:2] == HEADER_ROW[:2]
        assert parsed.total_rows == 1

    def test_머리글_행은_데이터로_세지_않는다(self) -> None:
        # 상한은 **데이터 행**에 대한 것이다.
        parsed = read_sheets(build_xlsx({"회원": []}))
        assert parsed.total_rows == 0
        assert [n for n, _c in parsed.sheets[0].rows] == [1]

    def test_행_번호를_함께_들고_온다(self) -> None:
        # 건너뛴 행을 사용자에게 **어디인지** 말하려면 필요하다 (FR-018).
        parsed = read_sheets(build_xlsx({"회원": [["TC-001", "가"], ["TC-002", "나"]]}))
        assert [r for r, _cells in parsed.sheets[0].rows] == [1, 2, 3]

    def test_시트가_상한을_넘으면_거절한다(self) -> None:
        sheets = {f"s{i}": [] for i in range(MAX_SHEETS + 1)}
        with pytest.raises(ArchiveRejected) as exc:
            read_sheets(build_xlsx(sheets))
        assert exc.value.kind == "sheet_count"
        assert exc.value.limit == MAX_SHEETS

    def test_행이_상한을_넘으면_거절한다(self) -> None:
        # 상한은 시트별이 아니라 **파일 전체**의 합이다.
        from itb.portability.limits import MAX_DATA_ROWS

        half = MAX_DATA_ROWS // 2 + 10
        sheets = {
            "가": [[f"TC-{i:03d}", "x"] for i in range(half)],
            "나": [[f"TC-{i:03d}", "x"] for i in range(half)],
        }
        with pytest.raises(ArchiveRejected) as exc:
            read_sheets(build_xlsx(sheets))
        assert exc.value.kind == "row_count"

    def test_손상된_파일을_거절한다(self) -> None:
        data = bytearray(build_xlsx({"s": [["TC-001", "가"]]}))
        # 중앙 디렉터리는 남기고 안쪽을 망가뜨린다.
        for i in range(40, min(200, len(data))):
            data[i] = 0
        with pytest.raises(ArchiveRejected):
            read_sheets(bytes(data))


class XmlBombTests:
    """XML 폭탄 방어 (014 T081 · research R1 미해결 항목의 해소).

    `.xlsx` 안은 XML 이다. 압축 크기·해제 총량 검사를 다 통과해도, 실체 참조가 중첩된
    작은 XML 하나가 파싱 중에 메모리를 수 GB 로 부풀릴 수 있다 (billion laughs).

    **openpyxl 은 `defusedxml` 이 설치돼 있을 때만 그것을 막는다** (`openpyxl.xml` 의
    `defusedxml_available`). 선언하지 않으면 조용히 표준 파서로 떨어지고 방어가 사라진다 —
    그래서 `pyproject.toml` 에 런타임 의존성으로 명시했고, 여기서 그 사실을 못박는다.
    """

    def test_defusedxml_이_실제로_쓰인다(self) -> None:
        from openpyxl.xml import DEFUSEDXML

        assert DEFUSEDXML, (
            "openpyxl 이 defusedxml 을 쓰지 않는다. 의존성이 빠졌거나 "
            "OPENPYXL_DEFUSEDXML 환경변수가 꺼져 있다 — XML 폭탄 방어가 사라진 상태다."
        )

    def test_파서가_defusedxml_에서_온다(self) -> None:
        from openpyxl.xml.functions import fromstring

        assert fromstring.__module__.startswith("defusedxml")

    def test_실체_참조가_든_파일을_거절한다(self) -> None:
        # 정상적인 스프레드시트에는 DOCTYPE 도 ENTITY 도 없다.
        bomb = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE r ['
            '<!ENTITY a "aaaaaaaaaa">'
            '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
            '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">'
            ']>'
            "<worksheet>&c;</worksheet>"
        )
        data = _repack_with(build_xlsx({"s": [["TC-001", "가"]]}), bomb)
        with pytest.raises(Exception) as exc:  # noqa: B017 — 어떤 방식으로든 막히면 된다
            read_sheets(data)
        # defusedxml 은 EntitiesForbidden 을, 우리 방어는 ArchiveRejected 를 낸다.
        assert exc.type.__name__ in ("EntitiesForbidden", "ArchiveRejected", "DTDForbidden")


def _repack_with(original: bytes, sheet_xml: str) -> bytes:
    """워크북의 첫 시트 XML 을 바꿔치기한다."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            payload = src.read(info.filename)
            if info.filename.startswith("xl/worksheets/sheet"):
                payload = sheet_xml.encode("utf-8")
            dst.writestr(info.filename, payload)
    return out.getvalue()


class BlankRowTests:
    """빈 행은 세지도 담지도 않는다 (014 T087 · FR-019).

    스프레드시트 도구는 값이 없는 행까지 사용 범위로 선언한다. 그것을 세면 **정상적인
    파일이 상한에 걸려 거절된다** — 구글 시트가 내보낸 파일은 시트마다 기본 1,000행이다.
    """

    def test_사용_범위에_딸린_빈_행을_세지_않는다(self) -> None:
        from openpyxl import Workbook

        wb = Workbook()
        wb.remove(wb.active)
        ws = wb.create_sheet("회원")
        ws.append(HEADER_ROW)
        ws.append(["USER-001", "로그인"])
        ws.cell(row=1000, column=1).value = None  # 구글 시트가 만드는 모양
        buffer = io.BytesIO()
        wb.save(buffer)

        parsed = read_sheets(buffer.getvalue())
        assert parsed.total_rows == 1
        assert len(parsed.sheets[0].rows) == 2  # 머리글 + 데이터 1

    def test_빈_행이_많은_시트_여섯_장을_받는다(self) -> None:
        # 이 검증이 없으면 구글 시트 파일이 통째로 거절된다.
        from openpyxl import Workbook

        wb = Workbook()
        wb.remove(wb.active)
        for i in range(6):
            ws = wb.create_sheet(f"시트{i}")
            ws.append(HEADER_ROW)
            ws.append([f"TC-{i + 1:03d}", "가"])
            ws.cell(row=1000, column=1).value = None
        buffer = io.BytesIO()
        wb.save(buffer)

        parsed = read_sheets(buffer.getvalue())
        assert parsed.total_rows == 6

    def test_가운데_빈_행도_담지_않는다(self) -> None:
        # 담으면 미리보기의 「건너뛸 행」이 빈 행으로 뒤덮여 진짜 신호가 묻힌다.
        parsed = read_sheets(
            build_xlsx({"회원": [["USER-001", "가"], [None, None], ["USER-002", "나"]]})
        )
        assert [r for r, _cells in parsed.sheets[0].rows] == [1, 2, 4]

    def test_공백만_있는_칸도_빈_행으로_본다(self) -> None:
        parsed = read_sheets(build_xlsx({"회원": [["USER-001", "가"], ["   ", "  "]]}))
        assert parsed.total_rows == 1


class MergedCellTests:
    """병합된 칸은 모든 칸이 같은 값으로 읽힌다 (2차 요청).

    엑셀은 병합 구간의 왼쪽 위 칸에만 값을 두고 나머지는 비운다. 사용자가 화면에서 보는
    것은 「모든 칸에 그 값이 있다」이므로, 우리도 그렇게 읽어야 **사용자의 눈과 제품의
    판단이 어긋나지 않는다.**

    이것이 없으면 「대상기능」이 여러 행에 걸쳐 병합된 설계서에서 둘째 행부터 제목이 빈
    행으로 보여 통째로 건너뛰어진다 — 설계서에서 아주 흔한 모양이다.
    """

    def merged(self, **kw: object) -> bytes:
        from openpyxl import Workbook

        wb = Workbook()
        wb.remove(wb.active)
        ws = wb.create_sheet("회원")
        ws.append(["TC ID", "대상기능", "테스트항목"])
        ws.append(["USER-001", "로그인", "정상 경로"])
        ws.append(["USER-002", None, "실패 경로"])
        ws.merge_cells(**kw)  # type: ignore[arg-type]
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def test_병합_구간을_찾아낸다(self) -> None:
        from itb.portability.workbook import merged_ranges

        data = self.merged(start_row=2, start_column=2, end_row=3, end_column=2)
        assert merged_ranges(data) == {"회원": [(2, 2, 3, 2)]}

    def test_아래_행에_같은_값이_채워진다(self) -> None:
        data = self.merged(start_row=2, start_column=2, end_row=3, end_column=2)
        rows = dict(read_sheets(data).sheets[0].rows)
        assert rows[2][1] == "로그인"
        assert rows[3][1] == "로그인"

    def test_병합되지_않은_칸은_그대로다(self) -> None:
        data = self.merged(start_row=2, start_column=2, end_row=3, end_column=2)
        rows = dict(read_sheets(data).sheets[0].rows)
        assert rows[3][2] == "실패 경로"

    def test_가로_병합도_채워진다(self) -> None:
        data = self.merged(start_row=1, start_column=2, end_row=1, end_column=3)
        rows = dict(read_sheets(data).sheets[0].rows)
        assert rows[1][1] == "대상기능"
        assert rows[1][2] == "대상기능"

    def test_병합이_없으면_아무것도_바꾸지_않는다(self) -> None:
        parsed = read_sheets(build_xlsx({"회원": [["USER-001", "가"], ["USER-002", None]]}))
        rows = dict(parsed.sheets[0].rows)
        assert rows[3][1] is None

    def test_병합된_행이_빈_행으로_버려지지_않는다(self) -> None:
        # 채우기가 빈 행 판정보다 **앞이어야** 한다.
        from openpyxl import Workbook

        wb = Workbook()
        wb.remove(wb.active)
        ws = wb.create_sheet("회원")
        ws.append(["TC ID", "대상기능"])
        ws.append(["USER-001", "로그인"])
        ws.append([None, None])
        ws.merge_cells(start_row=2, start_column=1, end_row=3, end_column=2)
        buffer = io.BytesIO()
        wb.save(buffer)

        rows = dict(read_sheets(buffer.getvalue()).sheets[0].rows)
        assert 3 in rows, "병합으로 값이 있어야 할 행이 빈 행으로 버려졌다"
        # 블록 전체가 **대표 칸의 값**을 갖는다. 엑셀도 병합할 때 나머지 값을 버린다.
        assert rows[3] == ["USER-001", "USER-001"]
