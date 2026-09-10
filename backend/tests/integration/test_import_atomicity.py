"""가져오기는 전부 아니면 전무다 (014 T042 · FR-025 · data-model §8).

**되돌림을 실물로 확인한다.** 초안 쓰기를 실패시키고, 그때 그룹 쓰기까지 되돌아갔는지 본다.
그룹만 남으면 사용자는 빈 그룹이 왜 생겼는지 알 수 없고, 다시 시도하면 그 그룹이 이미 있다.

`IMPORT_FAILED`(되돌렸다)와 `IMPORT_PARTIAL`(되돌리지 못했다)을 나누는 것은 사용자가
「다시 시도하면 되는가」에 답할 수 있어야 하기 때문이다 — `TEST_MOVE_FAILED` 와
`TEST_MOVE_PARTIAL` 을 나눈 것과 같은 판단이다.
"""

from __future__ import annotations

from excel_support import draft_write_fails, preview, repo_of, row
from fastapi.testclient import TestClient

COMMIT = "/api/import/commit"


def sheets_of(client: TestClient) -> dict[str, object]:
    return {
        "groups": client.get("/api/groups").json()["groups"],
        "drafts": client.get("/api/drafts").json()["count"],
        "tests": client.get("/api/tests").json()["counts"]["total"],
    }


class RollbackTests:
    def test_초안_쓰기가_실패하면_그룹도_되돌아간다(self, project_client: TestClient) -> None:
        before = sheets_of(project_client)
        plan = preview(
            project_client,
            {"회원": [row("USER-001", "가"), row("USER-002", "나"), row("USER-003", "다")]},
        )

        with draft_write_fails(on_call=2):
            resp = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})

        assert resp.status_code == 500, resp.text
        assert resp.json()["error"]["code"] in ("IMPORT_FAILED", "IMPORT_PARTIAL")
        assert sheets_of(project_client) == before

    def test_되돌린_경우_초안이_하나도_남지_않는다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "가"), row("USER-002", "나")]})

        with draft_write_fails(on_call=2):
            project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})

        assert repo_of(project_client).drafts.list_paths() == []

    def test_되돌린_경우_그룹이_남지_않는다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "가")]})

        with draft_write_fails():
            project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})

        assert project_client.get("/api/groups").json()["groups"] == []

    def test_이미_있던_그룹은_되돌림에_지워지지_않는다(self, project_client: TestClient) -> None:
        # 되돌림은 **이번 가져오기가 만든 것**만 치운다. 남의 것을 건드리면 안 된다.
        project_client.post("/api/groups", json={"prefix": "OLD", "name": "기존"})
        plan = preview(project_client, {"회원": [row("USER-001", "가")]})

        with draft_write_fails():
            project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})

        prefixes = [g["prefix"] for g in project_client.get("/api/groups").json()["groups"]]
        assert prefixes == ["OLD"]

    def test_실패해도_기존_테스트가_그대로다(self, project_client: TestClient) -> None:
        from excel_support import make_test

        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "기존 테스트"))
        plan = preview(project_client, {"회원": [row("USER-002", "가")]})

        with draft_write_fails():
            project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})

        tests, problems = repo_of(project_client).list_tests()
        assert [t.id for t in tests] == ["TC-001"]
        assert problems == []


class SuccessTests:
    def test_성공하면_전부_만들어진다(self, project_client: TestClient) -> None:
        plan = preview(
            project_client,
            {
                "회원": [row("USER-001", "가"), row("USER-002", "나")],
                "데이터": [row("DATA-003", "다")],
            },
        )
        resp = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        assert resp.status_code == 201, resp.text
        assert project_client.get("/api/drafts").json()["count"] == 3
        assert len(project_client.get("/api/groups").json()["groups"]) == 2

    def test_초안_파일이_디스크에_남는다(self, project_client: TestClient) -> None:
        # 초안은 사용자 자산이다 (FR-028). 메모리에만 있으면 재시작에 사라진다.
        plan = preview(project_client, {"회원": [row("USER-001", "가")]})
        project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})

        repo = repo_of(project_client)
        paths = repo.drafts.list_paths()
        assert len(paths) == 1
        assert paths[0].suffix == ".yaml"
        assert paths[0].parent.name == "drafts"

    def test_초안_파일은_사람이_읽는_형식이다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "로그인", "설명", "관리자")]})
        project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})

        text = repo_of(project_client).drafts.list_paths()[0].read_text(encoding="utf-8")
        assert "로그인" in text
        assert "관리자" in text
        assert "draft_id: D-0001" in text

    def test_출처가_보존된다(self, project_client: TestClient) -> None:
        plan = preview(project_client, {"회원": [row("USER-001", "가")]})
        project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        source = project_client.get("/api/drafts").json()["drafts"][0]["source"]
        assert source == {"file_name": "설계서.xlsx", "sheet_name": "회원", "row": 2}

    def test_초안_식별자가_서로_다르다(self, project_client: TestClient) -> None:
        plan = preview(
            project_client,
            {"회원": [row("USER-001", "가"), row("USER-002", "나"), row("USER-003", "다")]},
        )
        body = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]}).json()
        ids = [d["draft_id"] for d in body["drafts"]]
        assert len(set(ids)) == 3

    def test_두_번_가져오면_초안이_두_벌_생긴다(self, project_client: TestClient) -> None:
        # 저장된 테스트와 대조해 갱신하지 않는다는 것이 기본 동작이다 (Assumptions).
        for _ in range(2):
            plan = preview(project_client, {"회원": [row("USER-001", "가")]})
            resp = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
            assert resp.status_code == 201, resp.text
        assert project_client.get("/api/drafts").json()["count"] == 2
