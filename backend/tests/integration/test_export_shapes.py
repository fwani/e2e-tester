"""내보낸 워크북의 모양 (014 T029 · FR-002~FR-006a·FR-010).

파일을 만들고 **다시 읽어** 확인한다. 우리가 만든 자료구조를 그대로 보면 "썼다고 생각한 것"을
보게 된다.
"""

from __future__ import annotations

from excel_support import check, click, make_result, make_test, read_back, repo_of, sheet_names
from fastapi.testclient import TestClient

from itb.domain.run_result import Outcome
from itb.portability.columns import ORDER
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME

EXPORT = "/api/export"
HEADER = [c.value for c in ORDER]


def export(client: TestClient) -> bytes:
    resp = client.get(EXPORT)
    assert resp.status_code == 200, resp.text
    return resp.content


class SheetLayoutTests:
    def test_테스트가_없어도_그룹없음_시트가_있다(self, project_client: TestClient) -> None:
        assert sheet_names(export(project_client)) == [UNGROUPED_SHEET_NAME]

    def test_그룹마다_시트가_하나씩(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        project_client.post("/api/groups", json={"prefix": "DATA", "name": "데이터"})
        assert sheet_names(export(project_client)) == [UNGROUPED_SHEET_NAME, "사용자관리", "데이터"]

    def test_그룹없음이_맨_앞이다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "AAA", "name": "가나다"})
        assert sheet_names(export(project_client))[0] == UNGROUPED_SHEET_NAME

    def test_저장된_순서를_따르고_정렬하지_않는다(self, project_client: TestClient) -> None:
        # 정본의 순서를 따른다 (research R6). 이름순으로 정렬하면 "히읗"이 앞에 와야 한다.
        project_client.post("/api/groups", json={"prefix": "H", "name": "히읗"})
        project_client.post("/api/groups", json={"prefix": "G", "name": "기역"})
        assert sheet_names(export(project_client)) == [UNGROUPED_SHEET_NAME, "히읗", "기역"]

    def test_테스트가_없는_그룹도_머리글만_있는_시트를_갖는다(
        self, project_client: TestClient
    ) -> None:
        project_client.post("/api/groups", json={"prefix": "TEMP", "name": "임시"})
        sheets = read_back(export(project_client))
        assert sheets["임시"] == [HEADER]

    def test_모든_시트의_첫_행이_같은_머리글이다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        for rows in read_back(export(project_client)).values():
            assert rows[0] == HEADER


class RowTests:
    def test_테스트가_행으로_나간다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "로그인", description="설명", actor="관리자"))
        row = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1]
        assert row[0] == "TC-001"
        assert row[1] == "로그인"
        assert row[2] == "설명"
        assert row[3] == "관리자"

    def test_행이_TC_ID_순으로_정렬된다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        for tid in ("TC-003", "TC-001", "TC-002"):
            repo.write_test(make_test(tid, f"테스트 {tid}"))
        rows = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1:]
        assert [r[0] for r in rows] == ["TC-001", "TC-002", "TC-003"]

    def test_그룹_테스트는_그_시트에_들어간다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        repo = repo_of(project_client)
        repo.write_test(make_test("USER-001", "로그인"))
        repo.write_test(make_test("TC-002", "그룹 없는 것"))
        sheets = read_back(export(project_client))
        assert [r[0] for r in sheets["사용자관리"][1:]] == ["USER-001"]
        assert [r[0] for r in sheets[UNGROUPED_SHEET_NAME][1:]] == ["TC-002"]

    def test_비어_있는_칸은_빈_값이다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "로그인"))
        row = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1]
        assert row[2] in (None, "")
        assert row[3] in (None, "")


class ProcedureAndExpectationTests:
    def test_검증_스텝과_나머지가_갈린다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(
            make_test(
                "TC-001",
                "로그인",
                steps=[
                    click(1, "화면을 연다"),
                    click(2, "버튼을 누른다"),
                    check(3, "대시보드가 보인다", "대시보드"),
                    check(4, "이름이 보인다", "이름"),
                ],
            )
        )
        row = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1]
        assert row[4] == "1. 화면을 연다\n2. 버튼을 누른다"
        assert row[5] == "1. 대시보드가 보인다\n2. 이름이 보인다"

    def test_실행_순서를_유지한다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(
            make_test(
                "TC-001",
                "순서",
                steps=[click(1, "첫째"), check(2, "중간 검증", "x"), click(3, "셋째")],
            )
        )
        row = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1]
        assert row[4] == "1. 첫째\n2. 셋째"

    def test_검증_스텝이_없으면_기대_결과가_빈_칸이다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "동작만", steps=[click(1, "누른다")]))
        row = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1]
        assert row[5] in (None, "")


class OutcomeTests:
    def test_통과는_P_실패는_F(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "통과"))
        repo.write_test(make_test("TC-002", "실패"))
        repo.write_result(make_result("TC-001", Outcome.PASS))
        repo.write_result(make_result("TC-002", Outcome.FAIL))
        rows = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1:]
        assert [r[6] for r in rows] == ["P", "F"]

    def test_실행된_적이_없으면_빈_칸이다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "안 돌림"))
        row = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1]
        assert row[6] in (None, "")

    def test_부분_통과를_P_로_접지_않는다(self, project_client: TestClient) -> None:
        # 실패한 단계를 건너뛰고 얻은 통과다. P 로 적으면 보고서에 거짓이 실린다.
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "부분"))
        repo.write_result(make_result("TC-001", Outcome.PARTIAL_PASS))
        assert read_back(export(project_client))[UNGROUPED_SHEET_NAME][1][6] == "P(부분)"

    def test_중지를_F_로_접지_않는다(self, project_client: TestClient) -> None:
        # 실패하지 않은 것을 실패로 보고하게 된다.
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "중지"))
        repo.write_result(make_result("TC-001", Outcome.STOPPED))
        assert read_back(export(project_client))[UNGROUPED_SHEET_NAME][1][6] == "중지"

    def test_네_결말이_서로_다른_표기를_갖는다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        for i, outcome in enumerate(
            [Outcome.PASS, Outcome.FAIL, Outcome.PARTIAL_PASS, Outcome.STOPPED], start=1
        ):
            tid = f"TC-{i:03d}"
            repo.write_test(make_test(tid, f"t{i}"))
            repo.write_result(make_result(tid, outcome))
        marks = [r[6] for r in read_back(export(project_client))[UNGROUPED_SHEET_NAME][1:]]
        assert len(set(marks)) == 4


class SafetyTests:
    def test_수식으로_시작하는_이름을_텍스트로_고정한다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "=1+1"))
        row = read_back(export(project_client))[UNGROUPED_SHEET_NAME][1]
        # 값이 계산되지 않고 글자 그대로 남는다.
        assert row[1] in ("'=1+1", "=1+1")
        assert row[1] != 2

    def test_긴_절차가_잘려도_내보내기가_성공한다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        steps = [click(i, f"{i}번 " + "가" * 180) for i in range(1, 300)]
        repo.write_test(make_test("TC-001", "아주 긴 것", steps=steps))
        resp = project_client.get(EXPORT)
        assert resp.status_code == 200

    def test_잘린_사실이_경고에_잡힌다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        steps = [click(i, f"{i}번 " + "가" * 180) for i in range(1, 300)]
        repo.write_test(make_test("TC-001", "아주 긴 것", steps=steps))
        warnings = project_client.get("/api/export/warnings").json()
        assert warnings["truncations"]
        assert warnings["truncations"][0]["test_id"] == "TC-001"


class UnreadableTests:
    def test_읽을_수_없는_정의가_있어도_내보내진다(self, project_client: TestClient) -> None:
        # 깨진 파일 하나 때문에 프로젝트 전체를 못 내보내면 안 된다.
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "정상"))
        (repo.paths.tests_dir / "TC-002-깨진것.yaml").write_text(
            "dsl_version: 1\nid: TC-002\n", encoding="utf-8"
        )
        resp = project_client.get(EXPORT)
        assert resp.status_code == 200
        rows = read_back(resp.content)[UNGROUPED_SHEET_NAME][1:]
        assert [r[0] for r in rows] == ["TC-001"]

    def test_읽을_수_없는_정의가_경고에_잡힌다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        (repo.paths.tests_dir / "TC-002-깨진것.yaml").write_text(
            "dsl_version: 1\nid: TC-002\n", encoding="utf-8"
        )
        assert project_client.get("/api/export/warnings").json()["unreadable"]
