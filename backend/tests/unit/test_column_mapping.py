"""컬럼 짝짓기 (014 T097 · FR-020e~h · 2차 요청).

별칭 목록은 **우리가 아는 표기만** 담고 있다. 사용자가 화면에서 보고 있는 열을 우리가
못 알아보는 경우는 반드시 생기고, 그때 시트를 통째로 버리면 사용자는 그 열이 눈앞에
있는데도 쓸 수 없다.
"""

from __future__ import annotations

import pytest
from excel_support import build_xlsx, row
from fastapi.testclient import TestClient

from itb.portability.columns import (
    Column,
    conflicting_overrides,
    header_labels,
    map_headers,
)
from itb.portability.importer import build_plan, validate_columns
from itb.portability.workbook import read_sheets

COMMIT = "/api/import/commit"


def plan_of(sheets: dict[str, list[list[object]]], **kw: object):
    return build_plan(read_sheets(build_xlsx(sheets)), "설계서.xlsx", **kw)  # type: ignore[arg-type]


class HeaderLabelTests:
    def test_머리글을_그대로_준다(self) -> None:
        assert header_labels(["비고", "담당"]) == ["비고", "담당"]

    def test_빈_칸도_자리를_지킨다(self) -> None:
        # 위치를 잃으면 짝지을 수 없다.
        assert header_labels(["비고", None, "담당"]) == ["비고", "(2번째 열)", "담당"]

    def test_공백만_있는_칸도_이름을_준다(self) -> None:
        assert header_labels(["   "]) == ["(1번째 열)"]


class OverrideTests:
    def test_사용자_지정이_자동_판정을_이긴다(self) -> None:
        m = map_headers(["TC ID", "대상기능"], overrides={Column.NAME: 0})
        assert m.index[Column.NAME] == 0

    def test_못_알아본_열을_짝지을_수_있다(self) -> None:
        m = map_headers(["비고", "담당"], overrides={Column.TC_ID: 0, Column.NAME: 1})
        assert m.usable
        assert m.index[Column.TC_ID] == 0
        assert m.index[Column.NAME] == 1

    def test_음수는_쓰지_않음이다(self) -> None:
        m = map_headers(["TC ID", "대상기능", "결과"], overrides={Column.OUTCOME: -1})
        assert Column.OUTCOME not in m.index
        assert m.usable  # 필수가 아니므로 여전히 쓸 수 있다

    def test_필수_컬럼을_지우면_쓸_수_없어진다(self) -> None:
        m = map_headers(["TC ID", "대상기능"], overrides={Column.TC_ID: -1})
        assert not m.usable
        assert Column.TC_ID in m.missing_required

    def test_지정하지_않은_컬럼은_자동_판정이_남는다(self) -> None:
        m = map_headers(["TC ID", "대상기능", "수행자"], overrides={Column.NAME: 1})
        assert m.index[Column.ACTOR] == 2


class ConflictTests:
    def test_겹치지_않으면_비어_있다(self) -> None:
        assert conflicting_overrides({Column.TC_ID: 0, Column.NAME: 1}) == []

    def test_같은_열을_두_컬럼에_주면_잡는다(self) -> None:
        assert conflicting_overrides({Column.TC_ID: 0, Column.NAME: 0}) == [0]

    def test_쓰지_않음은_겹침이_아니다(self) -> None:
        assert conflicting_overrides({Column.TC_ID: -1, Column.NAME: -1}) == []


class ValidateTests:
    def test_올바른_짝짓기를_받는다(self) -> None:
        assert validate_columns({"TC ID": 0, "대상기능": 1}, ["a", "b"]) is None

    def test_모르는_컬럼을_거절한다(self) -> None:
        assert validate_columns({"담당부서": 0}, ["a"]) is not None

    def test_없는_열을_거절한다(self) -> None:
        assert validate_columns({"TC ID": 5}, ["a", "b"]) is not None

    def test_겹친_짝짓기를_거절한다(self) -> None:
        problem = validate_columns({"TC ID": 0, "대상기능": 0}, ["비고", "담당"])
        assert problem is not None
        assert "비고" in problem


class PlanTests:
    def test_못_읽은_시트가_계획에_남는다(self) -> None:
        plan = plan_of({"메모": [row("USER-001", "가")]}, project=None, **{})
        # 기본 머리글이 붙으므로 읽힌다. 아래에서 머리글을 바꿔 못 읽는 경우를 본다.
        assert plan.sheets[0].usable

    def test_짝지으면_살아난다(self) -> None:
        parsed = read_sheets(
            build_xlsx({"메모": [["USER-001", "로그인"]]}, header=["비고", "담당"])
        )
        before = build_plan(parsed, "f.xlsx", project=None)
        assert not before.sheets[0].usable
        assert before.needs_columns == ["메모"]

        after = build_plan(
            parsed,
            "f.xlsx",
            project=None,
            column_overrides={"메모": {"TC ID": 0, "대상기능": 1}},
        )
        assert after.sheets[0].usable
        assert [r.name for r in after.sheets[0].rows] == ["로그인"]
        assert after.draft_count == 1

    def test_짝짓기_전에는_초안_수에_들지_않는다(self) -> None:
        parsed = read_sheets(build_xlsx({"메모": [["USER-001", "가"]]}, header=["비고", "담당"]))
        assert build_plan(parsed, "f.xlsx", project=None).draft_count == 0

    def test_실제_머리글을_계획이_들고_있다(self) -> None:
        parsed = read_sheets(build_xlsx({"메모": [["x", "y"]]}, header=["비고", "담당"]))
        assert build_plan(parsed, "f.xlsx", project=None).sheets[0].headers == ["비고", "담당"]

    def test_행_수를_짝짓기_전에도_보인다(self) -> None:
        # 「여기 몇 건이 기다린다」를 보여야 사용자가 짝지을 이유를 안다.
        parsed = read_sheets(
            build_xlsx({"메모": [["a", "b"], ["c", "d"]]}, header=["비고", "담당"])
        )
        assert build_plan(parsed, "f.xlsx", project=None).sheets[0].total_rows == 2


class CommitTests:
    def preview(self, client: TestClient, data: bytes) -> dict:
        from excel_support import upload

        resp = upload(client, data)
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_미리보기가_머리글과_부족한_컬럼을_알린다(self, project_client: TestClient) -> None:
        data = build_xlsx({"메모": [["USER-001", "로그인"]]}, header=["비고", "담당"])
        sheet = self.preview(project_client, data)["sheets"][0]
        assert sheet["headers"] == ["비고", "담당"]
        assert sheet["missing_required"] == ["TC ID", "대상기능"]
        assert sheet["total_rows"] == 1

    def test_짝지어_확정하면_초안이_만들어진다(self, project_client: TestClient) -> None:
        data = build_xlsx({"메모": [["USER-001", "로그인"]]}, header=["비고", "담당"])
        plan = self.preview(project_client, data)
        resp = project_client.post(
            COMMIT,
            json={
                "plan_id": plan["plan_id"],
                "columns": {"메모": {"TC ID": 0, "대상기능": 1}},
            },
        )
        assert resp.status_code == 201, resp.text
        drafts = resp.json()["drafts"]
        assert [d["name"] for d in drafts] == ["로그인"]
        assert drafts[0]["desired_test_id"] == "USER-001"

    def test_짝짓지_않으면_그_시트를_건너뛴다(self, project_client: TestClient) -> None:
        data = build_xlsx({"메모": [["USER-001", "로그인"]]}, header=["비고", "담당"])
        plan = self.preview(project_client, data)
        resp = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["drafts"] == []
        assert [s["sheet_name"] for s in body["skipped_sheets"]] == ["메모"]

    def test_겹친_짝짓기를_확정_전에_거절한다(self, project_client: TestClient) -> None:
        data = build_xlsx({"메모": [["USER-001", "로그인"]]}, header=["비고", "담당"])
        plan = self.preview(project_client, data)
        resp = project_client.post(
            COMMIT,
            json={"plan_id": plan["plan_id"], "columns": {"메모": {"TC ID": 0, "대상기능": 0}}},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DEFINITION_INVALID"

    def test_거절되면_아무것도_만들어지지_않는다(self, project_client: TestClient) -> None:
        data = build_xlsx({"메모": [["USER-001", "로그인"]]}, header=["비고", "담당"])
        plan = self.preview(project_client, data)
        project_client.post(
            COMMIT,
            json={"plan_id": plan["plan_id"], "columns": {"메모": {"TC ID": 0, "대상기능": 0}}},
        )
        assert project_client.get("/api/drafts").json()["count"] == 0
        assert project_client.get("/api/groups").json()["groups"] == []

    @pytest.mark.parametrize(
        "columns", [{"메모": {"담당부서": 0}}, {"메모": {"TC ID": 9}}]
    )
    def test_잘못된_짝짓기를_거절한다(
        self, project_client: TestClient, columns: dict
    ) -> None:
        data = build_xlsx({"메모": [["USER-001", "로그인"]]}, header=["비고", "담당"])
        plan = self.preview(project_client, data)
        resp = project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "columns": columns}
        )
        assert resp.status_code == 400


class HeaderRowTests:
    """표가 어디서 시작하는지 짚을 수 있어야 한다 (FR-020i·j · 2차 요청).

    설계서는 위쪽에 제목·작성일·범례를 두는 일이 흔하다. 첫 행을 머리글로 못박으면 그런
    파일은 필수 컬럼을 **영영** 찾지 못하고, 사용자는 화면에서 열을 보고 있는데도 쓸 수
    없다.
    """

    def sheet_with_preamble(self) -> bytes:
        # 1행 제목 · 2행 작성일 · 3행 머리글 · 4행부터 데이터 — 흔한 설계서 모양.
        return build_xlsx(
            {
                "회원": [
                    ["2026-09-10 작성", None],
                    ["TC ID", "대상기능"],
                    ["USER-001", "로그인"],
                    ["USER-002", "로그아웃"],
                ]
            },
            header=["통합 테스트 설계서", None],
        )

    def test_머리글이_첫_행이_아니어도_찾아낸다(self) -> None:
        plan = build_plan(read_sheets(self.sheet_with_preamble()), "f.xlsx", project=None)
        sheet = plan.sheets[0]
        assert sheet.header_row == 3
        assert sheet.usable
        assert [r.name for r in sheet.rows] == ["로그인", "로그아웃"]

    def test_머리글_위쪽_행은_데이터가_아니다(self) -> None:
        plan = build_plan(read_sheets(self.sheet_with_preamble()), "f.xlsx", project=None)
        # 제목·작성일이 초안이 되면 안 된다.
        assert plan.draft_count == 2

    def test_앞부분_행을_표본으로_보여준다(self) -> None:
        # 사용자가 **어느 행이 머리글인지 눈으로 보고** 고를 수 있어야 한다.
        plan = build_plan(read_sheets(self.sheet_with_preamble()), "f.xlsx", project=None)
        sample = plan.sheets[0].sample
        assert [n for n, _cells in sample][:3] == [1, 2, 3]
        assert sample[0][1][0] == "통합 테스트 설계서"
        assert sample[2][1][0] == "TC ID"

    def test_사용자가_머리글_행을_고칠_수_있다(self) -> None:
        data = build_xlsx(
            {"회원": [["번호", "이름"], ["USER-001", "로그인"]]},
            header=["TC ID", "대상기능"],
        )
        # 자동 판정은 1행(진짜 머리글)을 고른다.
        auto = build_plan(read_sheets(data), "f.xlsx", project=None)
        assert auto.sheets[0].header_row == 1
        assert auto.sheets[0].total_rows == 2

        # 사용자가 2행을 머리글로 지정하면 그 아래만 데이터가 된다.
        picked = build_plan(
            read_sheets(data), "f.xlsx", project=None, header_rows={"회원": 2}
        )
        assert picked.sheets[0].header_row == 2
        assert picked.sheets[0].headers == ["번호", "이름"]
        assert picked.sheets[0].total_rows == 1

    def test_고른_머리글_기준으로_짝지을_수_있다(self) -> None:
        data = build_xlsx(
            {"회원": [["번호", "이름"], ["USER-001", "로그인"]]},
            header=["메모", "비고"],
        )
        plan = build_plan(
            read_sheets(data),
            "f.xlsx",
            project=None,
            header_rows={"회원": 2},
            column_overrides={"회원": {"TC ID": 0, "대상기능": 1}},
        )
        sheet = plan.sheets[0]
        assert sheet.usable
        assert [r.name for r in sheet.rows] == ["로그인"]

    def test_아무_행도_머리글로_안_보이면_첫_행을_쓴다(self) -> None:
        # 기준이 될 행은 있어야 사용자가 짝지을 수 있다.
        plan = build_plan(
            read_sheets(build_xlsx({"메모": [["b", "c"]]}, header=["비고", "담당"])),
            "f.xlsx",
            project=None,
        )
        assert plan.sheets[0].header_row == 1
        assert plan.sheets[0].headers == ["비고", "담당"]


class HeaderRowApiTests:
    def test_미리보기가_머리글_행과_표본을_싣는다(self, project_client: TestClient) -> None:
        from excel_support import upload

        data = build_xlsx(
            {"회원": [["TC ID", "대상기능"], ["USER-001", "로그인"]]},
            header=["통합 테스트 설계서", None],
        )
        sheet = upload(project_client, data).json()["sheets"][0]
        assert sheet["header_row"] == 2
        assert [r["row"] for r in sheet["sample"]] == [1, 2, 3]
        assert sheet["sample"][0]["cells"][0] == "통합 테스트 설계서"

    def test_머리글_행을_지정해_확정한다(self, project_client: TestClient) -> None:
        from excel_support import upload

        data = build_xlsx(
            {"회원": [["번호", "이름"], ["USER-001", "로그인"]]},
            header=["메모", "비고"],
        )
        plan = upload(project_client, data).json()
        resp = project_client.post(
            COMMIT,
            json={
                "plan_id": plan["plan_id"],
                "header_rows": {"회원": 2},
                "columns": {"회원": {"TC ID": 0, "대상기능": 1}},
            },
        )
        assert resp.status_code == 201, resp.text
        assert [d["name"] for d in resp.json()["drafts"]] == ["로그인"]
