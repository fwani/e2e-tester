"""가져오기 엔드포인트 계약 (014 T041 · contracts/rest-api.md §2·§3)."""

from __future__ import annotations

from excel_support import build_xlsx, preview, row, upload
from fastapi.testclient import TestClient

from itb.portability.limits import MAX_SHEETS
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME

COMMIT = "/api/import/commit"


class PreviewShapeTests:
    def test_계획을_돌려준다(self, project_client: TestClient) -> None:
        body = preview(project_client, {"회원": [row("USER-001", "로그인")]})
        assert body["plan_id"].startswith("pl_")
        assert body["file_name"] == "설계서.xlsx"
        assert body["draft_count"] == 1
        assert body["group_count"] == 1

    def test_시트마다_계획이_있다(self, project_client: TestClient) -> None:
        body = preview(
            project_client,
            {
                "회원": [row("USER-001", "가"), row("USER-002", "나")],
                UNGROUPED_SHEET_NAME: [row("TC-010", "다")],
            },
        )
        by_name = {s["sheet_name"]: s for s in body["sheets"]}
        assert by_name["회원"]["row_count"] == 2
        assert by_name["회원"]["prefix"] == "USER"
        assert by_name[UNGROUPED_SHEET_NAME]["prefix"] == "TC"

    def test_그룹없음_시트는_그룹으로_세지_않는다(self, project_client: TestClient) -> None:
        body = preview(project_client, {UNGROUPED_SHEET_NAME: [row("TC-001", "가")]})
        assert body["group_count"] == 0

    def test_접두어를_물어야_하는_시트를_표시한다(self, project_client: TestClient) -> None:
        body = preview(project_client, {"데이터관리": [row(None, "조회")]})
        sheet = body["sheets"][0]
        assert sheet["needs_prefix"] is True
        assert sheet["prefix"] is None

    def test_수용량을_알린다(self, project_client: TestClient) -> None:
        body = preview(project_client, {"회원": [row("USER-001", "가")]})
        assert body["capacity"]["needed"] == 1
        assert body["capacity"]["ok"] is True
        assert body["capacity"]["available"] > 0

    def test_건너뛴_행을_알린다(self, project_client: TestClient) -> None:
        body = preview(project_client, {"회원": [row("USER-001", None), row("USER-002", "가")]})
        assert body["skipped"] == [{"sheet_name": "회원", "row": 2, "reason": "no_title"}]

    def test_바뀐_번호를_알린다(self, project_client: TestClient) -> None:
        body = preview(project_client, {"회원": [row("USER-001", "가"), row("USER-001", "나")]})
        renumbered = body["sheets"][0]["renumbered"]
        assert len(renumbered) == 1
        assert renumbered[0]["from"] == "USER-001"
        assert renumbered[0]["row"] == 3

    def test_만료_시각을_알린다(self, project_client: TestClient) -> None:
        assert preview(project_client, {"회원": [row("USER-001", "가")]})["expires_at"]

    def test_미리보기가_아무것도_만들지_않는다(self, project_client: TestClient) -> None:
        before = project_client.get("/api/tests").json()
        preview(project_client, {"회원": [row("USER-001", "가")]})
        after = project_client.get("/api/tests").json()
        assert after == before
        assert project_client.get("/api/drafts").json()["count"] == 0
        assert project_client.get("/api/groups").json()["groups"] == []


class PreviewRejectionTests:
    def test_스프레드시트가_아니면_거절한다(self, project_client: TestClient) -> None:
        resp = upload(project_client, b"not a spreadsheet at all")
        assert resp.status_code == 400
        body = resp.json()["error"]
        assert body["code"] == "IMPORT_FILE_REJECTED"
        assert body["detail"]["kind"] == "not_xlsx"

    def test_거절이_다음_행동을_말한다(self, project_client: TestClient) -> None:
        body = upload(project_client, b"nope").json()["error"]
        assert body["next_action"]
        assert body["category"] == "blocked"

    def test_시트_상한을_넘으면_거절한다(self, project_client: TestClient) -> None:
        data = build_xlsx({f"s{i}": [] for i in range(MAX_SHEETS + 1)})
        body = upload(project_client, data).json()["error"]
        assert body["code"] == "IMPORT_FILE_REJECTED"
        assert body["detail"]["kind"] == "sheet_count"
        assert body["detail"]["limit"] == MAX_SHEETS

    def test_거절해도_프로젝트가_그대로다(self, project_client: TestClient) -> None:
        upload(project_client, b"nope")
        assert project_client.get("/api/drafts").json()["count"] == 0


class CommitTests:
    def test_그룹과_초안을_만든다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "로그인")]})
        resp = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["created_groups"] == [{"prefix": "USER", "name": "회원"}]
        assert len(body["drafts"]) == 1
        assert body["drafts"][0]["desired_test_id"] == "USER-001"

    def test_만들어진_초안이_목록에_보인다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "로그인")]})
        project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        drafts = project_client.get("/api/drafts").json()
        assert drafts["count"] == 1
        assert drafts["drafts"][0]["name"] == "로그인"

    def test_초안이_테스트_목록에_섞이지_않는다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "로그인")]})
        project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        listing = project_client.get("/api/tests").json()
        assert listing["tests"] == []
        assert listing["draft_count"] == 1

    def test_같은_계획을_두_번_쓸_수_없다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "가")]})
        project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        again = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        assert again.status_code == 400
        assert again.json()["error"]["code"] == "IMPORT_PLAN_NOT_FOUND"

    def test_없는_계획을_거절한다(self, project_client: TestClient) -> None:
        resp = project_client.post(COMMIT, json={"plan_id": "pl_deadbeef"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "IMPORT_PLAN_NOT_FOUND"

    def test_사용자가_준_접두어를_쓴다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"데이터관리": [row(None, "조회")]})
        resp = project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"데이터관리": "DATA"}}
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["created_groups"] == [{"prefix": "DATA", "name": "데이터관리"}]

    def test_접두어를_비우면_시트를_건너뛴다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"데이터관리": [row(None, "조회")]})
        body = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]}).json()
        assert body["drafts"] == []
        assert body["skipped_sheets"] == [{"sheet_name": "데이터관리", "reason": "no_prefix"}]

    def test_잘못된_접두어를_거절한다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"데이터관리": [row(None, "조회")]})
        resp = project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"데이터관리": "사용자"}}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "DEFINITION_INVALID"

    def test_예약_접두어를_거절한다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"데이터관리": [row(None, "조회")]})
        resp = project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"데이터관리": "TC"}}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "GROUP_PREFIX_RESERVED"

    def test_거절되면_아무것도_만들어지지_않는다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"데이터관리": [row(None, "조회")]})
        project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"데이터관리": "TC"}}
        )
        assert project_client.get("/api/drafts").json()["count"] == 0
        assert project_client.get("/api/groups").json()["groups"] == []

    def test_이미_있는_그룹은_다시_만들지_않는다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        plan = preview(project_client, {"회원": [row("USER-001", "가")]})
        body = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]}).json()
        assert body["created_groups"] == []
        assert body["reused_groups"] == [{"prefix": "USER", "name": "사용자관리"}]

    def test_기존_그룹의_이름을_바꾸지_않는다(self, project_client: TestClient) -> None:
        # 가져오기는 더하는 일이지 고치는 일이 아니다 (FR-024a).
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        plan = preview(project_client, {"회원": [row("USER-001", "가")]})
        project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        names = [g["name"] for g in project_client.get("/api/groups").json()["groups"]]
        assert names == ["사용자관리"]

    def test_이름이_다르다는_사실을_미리보기가_알린다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        body = preview(project_client, {"회원": [row("USER-001", "가")]})
        sheet = body["sheets"][0]
        assert sheet["existing_group_name"] == "사용자관리"
        assert sheet["name_differs"] is True

    def test_그룹없음_시트는_그룹을_만들지_않는다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {UNGROUPED_SHEET_NAME: [row("TC-001", "가")]})
        body = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]}).json()
        assert body["created_groups"] == []
        assert body["drafts"][0]["group_prefix"] == "TC"

    def test_프로젝트가_없으면_404(self, client: TestClient) -> None:
        assert client.post(COMMIT, json={"plan_id": "pl_x"}).status_code == 404


class CreateProjectImportTests:
    ENDPOINT = "/api/import/create-project"

    def test_새_프로젝트를_만들며_가져온다(self, client: TestClient) -> None:
        resp = upload(client, build_xlsx({"회원": [row("USER-001", "로그인")]}))
        assert resp.status_code == 200, resp.text
        plan_id = resp.json()["plan_id"]

        made = client.post(
            self.ENDPOINT,
            json={
                "plan_id": plan_id,
                "name": "가져온 프로젝트",
                "default_start_url": "https://example.internal",
            },
        )
        assert made.status_code == 201, made.text
        body = made.json()
        assert body["project"]["name"] == "가져온 프로젝트"
        assert len(body["drafts"]) == 1

    def test_만든_프로젝트가_열린_상태가_된다(self, client: TestClient) -> None:
        plan_id = upload(client, build_xlsx({"회원": [row("USER-001", "가")]})).json()["plan_id"]
        client.post(
            self.ENDPOINT,
            json={
                "plan_id": plan_id,
                "name": "열림 확인",
                "default_start_url": "https://example.internal",
            },
        )
        assert client.get("/api/project").json()["name"] == "열림 확인"
        assert client.get("/api/drafts").json()["count"] == 1

    def test_시작_URL_형식을_검사한다(self, client: TestClient) -> None:
        plan_id = upload(client, build_xlsx({"회원": [row("USER-001", "가")]})).json()["plan_id"]
        resp = client.post(
            self.ENDPOINT,
            json={"plan_id": plan_id, "name": "x", "default_start_url": "ftp://nope"},
        )
        assert resp.status_code == 422
