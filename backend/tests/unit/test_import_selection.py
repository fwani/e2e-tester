"""시트 고르기 (014 T096 · FR-020a~d · 2차 요청).

**「일부러 뺀 것」과 「제품이 못 읽은 것」은 다른 사실이다.** 예전에는 접두어를 비우는 것이
곧 건너뛰기였는데, 그것은 실수로 비운 것과 뜻을 가지고 뺀 것을 구별하지 못한다.
"""

from __future__ import annotations

from excel_support import build_xlsx, row
from fastapi.testclient import TestClient

from itb.portability.importer import build_plan
from itb.portability.workbook import read_sheets

COMMIT = "/api/import/commit"


def plan_of(sheets: dict[str, list[list[object]]], **kw: object):
    return build_plan(read_sheets(build_xlsx(sheets)), "설계서.xlsx", **kw)  # type: ignore[arg-type]


TWO_SHEETS = {
    "회원": [row("USER-001", "가"), row("USER-002", "나")],
    "데이터": [row("DATA-003", "다")],
}


class DefaultTests:
    def test_기본은_전부_가져온다(self) -> None:
        plan = plan_of(TWO_SHEETS, project=None)
        assert all(s.included for s in plan.sheets)
        assert plan.draft_count == 3

    def test_고르지_않은_시트도_가져온다(self) -> None:
        # 빠진 시트는 「포함」이다. 기본이 포함이므로 화면이 전부 보내지 않아도 된다.
        plan = plan_of(TWO_SHEETS, project=None, selections={"회원": True})
        assert all(s.included for s in plan.sheets)


class ExcludeTests:
    def test_무시한_시트는_초안_수에서_빠진다(self) -> None:
        plan = plan_of(TWO_SHEETS, project=None, selections={"데이터": False})
        assert plan.draft_count == 2

    def test_무시한_시트도_계획에는_남는다(self) -> None:
        # 화면이 체크를 다시 켤 수 있어야 하므로 목록에서 사라지면 안 된다.
        plan = plan_of(TWO_SHEETS, project=None, selections={"데이터": False})
        by_name = {s.sheet_name: s for s in plan.sheets}
        assert by_name["데이터"].included is False
        assert by_name["데이터"].total_rows == 1

    def test_무시한_시트의_문제는_보고하지_않는다(self) -> None:
        # 일부러 뺀 시트의 「제목이 빈 행」을 알리는 것은 잡음이다 (FR-020c).
        plan = plan_of(
            {"회원": [row("USER-001", "가")], "메모": [row("X-001", None)]},
            project=None,
            selections={"메모": False},
        )
        assert plan.skipped == []

    def test_무시하지_않으면_문제를_보고한다(self) -> None:
        plan = plan_of(
            {"회원": [row("USER-001", "가")], "메모": [row("X-001", None)]},
            project=None,
        )
        assert [s.sheet_name for s in plan.skipped] == ["메모"]

    def test_전부_무시하면_만들_것이_없다(self) -> None:
        plan = plan_of(TWO_SHEETS, project=None, selections={"회원": False, "데이터": False})
        assert plan.draft_count == 0
        assert not any(s.included for s in plan.sheets)

    def test_무시한_시트는_접두어를_묻지_않는다(self) -> None:
        plan = plan_of(
            {"데이터관리": [row(None, "조회")]}, project=None, selections={"데이터관리": False}
        )
        assert plan.needs_prefix == []


class CommitTests:
    def preview(self, client: TestClient, sheets: dict[str, list[list[object]]]) -> str:
        from excel_support import upload

        resp = upload(client, build_xlsx(sheets))
        assert resp.status_code == 200, resp.text
        return resp.json()["plan_id"]

    def test_무시한_시트의_초안이_만들어지지_않는다(self, project_client: TestClient) -> None:
        pid = self.preview(project_client, TWO_SHEETS)
        resp = project_client.post(
            COMMIT, json={"plan_id": pid, "sheets": {"데이터": False}}
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert len(body["drafts"]) == 2
        assert {g["prefix"] for g in body["created_groups"]} == {"USER"}

    def test_무시한_시트를_결과가_알린다(self, project_client: TestClient) -> None:
        pid = self.preview(project_client, TWO_SHEETS)
        body = project_client.post(
            COMMIT, json={"plan_id": pid, "sheets": {"데이터": False}}
        ).json()
        assert body["ignored_sheets"] == ["데이터"]

    def test_무시와_건너뜀을_구별해_알린다(self, project_client: TestClient) -> None:
        # 「내가 뺀 것」과 「제품이 못 읽은 것」이 뭉치면 사용자가 구별할 수 없다.
        pid = self.preview(
            project_client,
            {
                "회원": [row("USER-001", "가")],
                "데이터": [row("DATA-002", "나")],
                "데이터관리": [row(None, "조회")],  # 접두어를 못 정한다
            },
        )
        body = project_client.post(
            COMMIT, json={"plan_id": pid, "sheets": {"데이터": False}}
        ).json()
        assert body["ignored_sheets"] == ["데이터"]
        assert [s["sheet_name"] for s in body["skipped_sheets"]] == ["데이터관리"]

    def test_전부_무시하면_확정을_막는다(self, project_client: TestClient) -> None:
        pid = self.preview(project_client, TWO_SHEETS)
        resp = project_client.post(
            COMMIT, json={"plan_id": pid, "sheets": {"회원": False, "데이터": False}}
        )
        assert resp.status_code == 400
        assert "시트를 하나도" in resp.json()["error"]["message"]

    def test_막혔을_때_아무것도_만들어지지_않는다(self, project_client: TestClient) -> None:
        pid = self.preview(project_client, TWO_SHEETS)
        project_client.post(
            COMMIT, json={"plan_id": pid, "sheets": {"회원": False, "데이터": False}}
        )
        assert project_client.get("/api/drafts").json()["count"] == 0
        assert project_client.get("/api/groups").json()["groups"] == []

    def test_무시한_시트는_수용량에_세지_않는다(self, project_client: TestClient) -> None:
        from excel_support import make_test, repo_of

        from itb.domain.test_case import MAX_TEST_NUMBER

        repo = repo_of(project_client)
        for i in range(1, MAX_TEST_NUMBER - 1):
            repo.write_test(make_test(f"TC-{i:03d}", f"기존 {i}"))

        pid = self.preview(project_client, TWO_SHEETS)
        resp = project_client.post(
            COMMIT, json={"plan_id": pid, "sheets": {"회원": False}}
        )
        # 남은 번호 2개 · 데이터 시트 1건만 만든다 → 통과해야 한다.
        assert resp.status_code == 201, resp.text
        assert len(resp.json()["drafts"]) == 1
