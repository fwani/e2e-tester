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
        assert parsed.sheets[0].header[:2] == HEADER_ROW[:2]
        assert parsed.total_rows == 1

    def test_머리글_행은_데이터로_세지_않는다(self) -> None:
        parsed = read_sheets(build_xlsx({"회원": []}))
        assert parsed.total_rows == 0
        assert parsed.sheets[0].rows == []

    def test_행_번호를_함께_들고_온다(self) -> None:
        # 건너뛴 행을 사용자에게 **어디인지** 말하려면 필요하다 (FR-018).
        parsed = read_sheets(build_xlsx({"회원": [["TC-001", "가"], ["TC-002", "나"]]}))
        assert [r for r, _cells in parsed.sheets[0].rows] == [2, 3]

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
