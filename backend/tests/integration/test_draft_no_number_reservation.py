"""초안은 번호를 예약하지 않는다 (014 T064 · FR-032 · quickstart §3 회귀 3·4).

이 사실이 설계의 뼈대다. 예약하기로 했다면 「번호 정리」·새 테스트 만들기·그룹 이동이
모두 초안을 함께 봐야 하고, 그 셋 중 하나라도 빠뜨리면 번호가 겹친다. 예약하지 않기로
한 덕분에 **기존 도구들과 아무 상호작용이 없다** — 그 없음을 여기서 못박는다.
"""

from __future__ import annotations

from excel_support import make_test, preview, repo_of, row
from fastapi.testclient import TestClient

COMMIT = "/api/import/commit"


def seed(client: TestClient, rows: list[list[object]]) -> None:
    plan = preview(client, {"회원": rows})
    resp = client.post(COMMIT, json={"plan_id": plan["plan_id"]})
    assert resp.status_code == 201, resp.text


class NewTestTests:
    def test_초안이_있어도_새_테스트가_번호를_받는다(self, project_client: TestClient) -> None:
        seed(project_client, [row("USER-001", "가"), row("USER-002", "나")])
        repo = repo_of(project_client)
        assert repo.allocate_test_id() == "TC-001"

    def test_초안이_희망하는_번호를_새_테스트가_가져갈_수_있다(
        self, project_client: TestClient
    ) -> None:
        # 예약이 아니므로 막지 않는다. 초안은 저장할 때 다른 번호를 받는다 (FR-032).
        seed(project_client, [row("USER-005", "초안")])
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-005", "먼저 만든 것"))
        assert repo.find_test_path("TC-005") is not None

    def test_그때_초안_목록이_그_사실을_알린다(self, project_client: TestClient) -> None:
        seed(project_client, [row("USER-005", "초안")])
        repo_of(project_client).write_test(make_test("USER-005", "먼저 만든 것"))
        d = project_client.get("/api/drafts").json()["drafts"][0]
        assert d["desired_id_available"] is False


class RenumberTests:
    def test_초안이_있어도_번호_정리가_동작한다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-003", "셋"))
        repo.write_test(make_test("TC-007", "일곱"))
        seed(project_client, [row("USER-001", "초안")])

        resp = project_client.post("/api/tests:renumber")
        assert resp.status_code == 200, resp.text
        assert [m["to_id"] for m in resp.json()["renumbered"]] == ["TC-001", "TC-002"]

    def test_번호_정리가_초안을_건드리지_않는다(self, project_client: TestClient) -> None:
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-003", "셋"))
        seed(project_client, [row("USER-009", "초안")])

        before = project_client.get("/api/drafts").json()["drafts"][0]
        project_client.post("/api/tests:renumber")
        after = project_client.get("/api/drafts").json()["drafts"][0]
        assert after == before

    def test_번호_정리_뒤에도_초안_수가_그대로다(self, project_client: TestClient) -> None:
        repo_of(project_client).write_test(make_test("TC-005", "다섯"))
        seed(project_client, [row("USER-001", "가"), row("USER-002", "나")])
        project_client.post("/api/tests:renumber")
        assert project_client.get("/api/drafts").json()["count"] == 2


class GroupOperationTests:
    def test_그룹을_없애도_초안은_남는다(self, project_client: TestClient) -> None:
        seed(project_client, [row("USER-001", "초안")])
        resp = project_client.delete("/api/groups/USER")
        assert resp.status_code in (200, 204), resp.text
        assert project_client.get("/api/drafts").json()["count"] == 1

    def test_그룹_이름을_바꿔도_초안은_그대로다(self, project_client: TestClient) -> None:
        seed(project_client, [row("USER-001", "초안")])
        project_client.patch("/api/groups/USER", json={"name": "사용자관리"})
        d = project_client.get("/api/drafts").json()["drafts"][0]
        assert d["group_prefix"] == "USER"


class ListingTests:
    def test_초안은_테스트_수에_들어가지_않는다(self, project_client: TestClient) -> None:
        seed(project_client, [row("USER-001", "가"), row("USER-002", "나")])
        listing = project_client.get("/api/tests").json()
        assert listing["counts"]["total"] == 0
        assert listing["draft_count"] == 2

    def test_초안은_그룹_개수에_들어가지_않는다(self, project_client: TestClient) -> None:
        # `groups` 는 **테스트가 있는** 그룹만 싣는다 (013 FR-450).
        seed(project_client, [row("USER-001", "가")])
        listing = project_client.get("/api/tests").json()
        assert listing["groups"] == []
