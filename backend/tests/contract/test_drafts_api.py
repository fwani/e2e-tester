"""초안 엔드포인트 계약 (014 T062 · contracts/rest-api.md §4)."""

from __future__ import annotations

from excel_support import make_test, preview, repo_of, row
from fastapi.testclient import TestClient

COMMIT = "/api/import/commit"


def seed(client: TestClient, rows: list[list[object]] | None = None) -> list[dict]:
    """초안을 심고 만들어진 목록을 돌려준다."""
    plan = preview(
        client,
        {
            "회원": rows
            or [row("USER-001", "로그인", "자격 증명 확인", "관리자", "1. 연다", "1. 본다")]
        },
    )
    resp = client.post(COMMIT, json={"plan_id": plan["plan_id"]})
    assert resp.status_code == 201, resp.text
    return resp.json()["drafts"]


class ListTests:
    def test_초안이_없으면_빈_목록이다(self, project_client: TestClient) -> None:
        body = project_client.get("/api/drafts").json()
        assert body == {"drafts": [], "count": 0, "problems": []}

    def test_만들어진_초안이_보인다(self, project_client: TestClient) -> None:
        seed(project_client)
        body = project_client.get("/api/drafts").json()
        assert body["count"] == 1
        assert body["drafts"][0]["name"] == "로그인"

    def test_모든_칸이_실린다(self, project_client: TestClient) -> None:
        seed(project_client)
        d = project_client.get("/api/drafts").json()["drafts"][0]
        assert d["description"] == "자격 증명 확인"
        assert d["actor"] == "관리자"
        assert d["group_prefix"] == "USER"
        assert d["desired_test_id"] == "USER-001"

    def test_출처를_실는다(self, project_client: TestClient) -> None:
        seed(project_client)
        d = project_client.get("/api/drafts").json()["drafts"][0]
        assert d["source"] == {"file_name": "설계서.xlsx", "sheet_name": "회원", "row": 2}

    def test_목록에는_절차와_기대결과가_없다(self, project_client: TestClient) -> None:
        # 목록은 고르기 위한 것이다. 긴 글은 상세에서 본다.
        seed(project_client)
        d = project_client.get("/api/drafts").json()["drafts"][0]
        assert "procedure" not in d
        assert "suggested_instruction" not in d

    def test_식별자_순으로_정렬된다(self, project_client: TestClient) -> None:
        seed(
            project_client,
            [row("USER-001", "가"), row("USER-002", "나"), row("USER-003", "다")],
        )
        ids = [d["draft_id"] for d in project_client.get("/api/drafts").json()["drafts"]]
        assert ids == sorted(ids)

    def test_읽을_수_없는_초안이_있어도_나머지는_보인다(self, project_client: TestClient) -> None:
        seed(project_client)
        repo = repo_of(project_client)
        (repo.drafts.dir / "D-0009-깨진것.yaml").write_text("draft_id: D-0009\n", encoding="utf-8")
        body = project_client.get("/api/drafts").json()
        assert body["count"] == 1
        assert body["problems"]

    def test_프로젝트가_없으면_404(self, client: TestClient) -> None:
        assert client.get("/api/drafts").status_code == 404


class DesiredIdAvailableTests:
    def test_번호가_비어_있으면_참이다(self, project_client: TestClient) -> None:
        seed(project_client)
        assert project_client.get("/api/drafts").json()["drafts"][0]["desired_id_available"]

    def test_번호가_이미_쓰이면_거짓이다(self, project_client: TestClient) -> None:
        seed(project_client)
        repo_of(project_client).write_test(make_test("USER-001", "이미 있는 것"))
        assert not project_client.get("/api/drafts").json()["drafts"][0]["desired_id_available"]

    def test_희망_번호가_없으면_거짓이다(self, project_client: TestClient) -> None:
        seed(project_client, [row(None, "번호 없는 것")])
        # 접두어를 못 읽으므로 시트를 건너뛴다 — 이 경우는 초안이 만들어지지 않는다.
        assert project_client.get("/api/drafts").json()["count"] == 0


class DetailTests:
    def test_상세는_절차와_기대결과를_싣는다(self, project_client: TestClient) -> None:
        made = seed(project_client)
        d = project_client.get(f"/api/drafts/{made[0]['draft_id']}").json()
        assert d["procedure"] == "1. 연다"
        assert d["expectation"] == "1. 본다"

    def test_상세는_지시문을_지어_준다(self, project_client: TestClient) -> None:
        made = seed(project_client)
        d = project_client.get(f"/api/drafts/{made[0]['draft_id']}").json()
        instruction = d["suggested_instruction"]
        assert "제목: 로그인" in instruction
        assert "관리자 역할로 수행한다." in instruction
        assert "1. 연다" in instruction

    def test_빈_항목은_지시문에_들어가지_않는다(self, project_client: TestClient) -> None:
        made = seed(project_client, [row("USER-001", "제목만")])
        d = project_client.get(f"/api/drafts/{made[0]['draft_id']}").json()
        assert d["suggested_instruction"] == "제목: 제목만"

    def test_없는_초안은_404(self, project_client: TestClient) -> None:
        resp = project_client.get("/api/drafts/D-9999")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "DRAFT_NOT_FOUND"


class DeleteTests:
    def test_초안을_지운다(self, project_client: TestClient) -> None:
        made = seed(project_client)
        resp = project_client.delete(f"/api/drafts/{made[0]['draft_id']}")
        assert resp.status_code == 204
        assert project_client.get("/api/drafts").json()["count"] == 0

    def test_다른_초안은_남는다(self, project_client: TestClient) -> None:
        made = seed(project_client, [row("USER-001", "가"), row("USER-002", "나")])
        project_client.delete(f"/api/drafts/{made[0]['draft_id']}")
        remaining = project_client.get("/api/drafts").json()
        assert remaining["count"] == 1
        assert remaining["drafts"][0]["draft_id"] == made[1]["draft_id"]

    def test_테스트는_영향받지_않는다(self, project_client: TestClient) -> None:
        made = seed(project_client)
        repo_of(project_client).write_test(make_test("TC-500", "관계없는 테스트"))
        project_client.delete(f"/api/drafts/{made[0]['draft_id']}")
        assert project_client.get("/api/tests").json()["counts"]["total"] == 1

    def test_없는_초안은_404(self, project_client: TestClient) -> None:
        resp = project_client.delete("/api/drafts/D-9999")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "DRAFT_NOT_FOUND"
