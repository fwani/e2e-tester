"""내보내기 엔드포인트 계약 (014 T027 · contracts/rest-api.md §1)."""

from __future__ import annotations

import io
import zipfile

from fastapi.testclient import TestClient

from itb.portability.limits import XLSX_MEDIA_TYPE

EXPORT = "/api/export"
WARNINGS = "/api/export/warnings"


class ExportResponseTests:
    def test_열린_프로젝트를_내보낸다(self, project_client: TestClient) -> None:
        resp = project_client.get(EXPORT)
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith(XLSX_MEDIA_TYPE)

    def test_받은_바이트가_열리는_워크북이다(self, project_client: TestClient) -> None:
        resp = project_client.get(EXPORT)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            assert "[Content_Types].xml" in zf.namelist()

    def test_파일_이름을_붙여_내려보낸다(self, project_client: TestClient) -> None:
        disposition = project_client.get(EXPORT).headers["content-disposition"]
        assert disposition.startswith("attachment;")
        assert ".xlsx" in disposition

    def test_한글_이름을_두_가지로_싣는다(self, project_client: TestClient) -> None:
        # HTTP 헤더는 ASCII 제한이고 프로젝트 이름은 한글일 수 있다 (research R9).
        disposition = project_client.get(EXPORT).headers["content-disposition"]
        assert "filename=" in disposition
        assert "filename*=UTF-8''" in disposition

    def test_헤더가_ASCII_로만_이루어진다(self, project_client: TestClient) -> None:
        disposition = project_client.get(EXPORT).headers["content-disposition"]
        disposition.encode("ascii")  # 예외가 나면 실패다

    def test_경고가_없으면_경고_헤더가_없다(self, project_client: TestClient) -> None:
        assert "x-itb-export-warnings" not in project_client.get(EXPORT).headers

    def test_프로젝트가_없으면_404(self, client: TestClient) -> None:
        resp = client.get(EXPORT)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PROJECT_NOT_OPEN"

    def test_내보내기가_프로젝트를_바꾸지_않는다(self, project_client: TestClient) -> None:
        before = project_client.get("/api/tests").json()
        project_client.get(EXPORT)
        assert project_client.get("/api/tests").json() == before


class ExportWarningsTests:
    def test_빈_프로젝트의_경고는_비어_있다(self, project_client: TestClient) -> None:
        body = project_client.get(WARNINGS).json()
        assert body["sheet_renames"] == []
        assert body["truncations"] == []
        assert body["unreadable"] == []

    def test_시트와_테스트_수를_알린다(self, project_client: TestClient) -> None:
        body = project_client.get(WARNINGS).json()
        assert body["test_count"] == 0
        # 테스트가 없어도 「그룹 없음」 시트는 있다.
        assert body["sheet_count"] == 1

    def test_그룹을_만들면_시트가_는다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        assert project_client.get(WARNINGS).json()["sheet_count"] == 2

    def test_시트_이름_변환을_알린다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자/권한"})
        renames = project_client.get(WARNINGS).json()["sheet_renames"]
        assert renames == [
            {"group_name": "사용자/권한", "sheet_name": "사용자_권한", "reason": "forbidden_char"}
        ]

    def test_경고가_있으면_내보내기_헤더에_수가_실린다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자/권한"})
        assert project_client.get(EXPORT).headers["x-itb-export-warnings"] == "1"

    def test_프로젝트가_없으면_404(self, client: TestClient) -> None:
        assert client.get(WARNINGS).status_code == 404
