"""수용량은 파일 상한과 별개다 (014 T043 · FR-036a·b · SC-010).

파일을 **읽는** 상한(100MB·시트 200·행 5,000)과 프로젝트가 **수용하는** 양(테스트 번호 999)은
다른 것이다. 후자를 확인하지 않으면 초안을 만들다가 번호가 바닥나 반쯤 만들어진 상태로 끝난다.

**아무것도 만들기 전에 거절한다.** 만들다 멈추면 되돌릴 것이 생기고, 되돌림은 언제나
안 만드는 것보다 나쁘다.
"""

from __future__ import annotations

from excel_support import make_test, preview, repo_of, row
from fastapi.testclient import TestClient

from itb.domain.test_case import MAX_TEST_NUMBER

COMMIT = "/api/import/commit"


def fill_project(client: TestClient, count: int) -> None:
    """테스트를 count 개 심어 남은 번호를 줄인다."""
    repo = repo_of(client)
    for i in range(1, count + 1):
        repo.write_test(make_test(f"TC-{i:03d}", f"기존 {i}"))


class CapacityTests:
    def test_남은_번호보다_많으면_거절한다(self, project_client: TestClient) -> None:
        fill_project(project_client, MAX_TEST_NUMBER - 2)
        plan = preview(
            project_client,
            {"회원": [row(None, f"새 {i}") for i in range(5)]},
        )
        resp = project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"회원": "USER"}}
        )
        assert resp.status_code == 400, resp.text
        assert resp.json()["error"]["code"] == "IMPORT_CAPACITY_EXCEEDED"

    def test_필요한_수와_남은_수를_함께_말한다(self, project_client: TestClient) -> None:
        fill_project(project_client, MAX_TEST_NUMBER - 2)
        plan = preview(project_client, {"회원": [row(None, f"새 {i}") for i in range(5)]})
        detail = project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"회원": "USER"}}
        ).json()["error"]["detail"]
        assert detail["needed"] == 5
        assert detail["available"] == 2

    def test_거절되면_아무것도_만들어지지_않는다(self, project_client: TestClient) -> None:
        # SC-010 — 만들다 만 상태로 끝나는 경우가 0건이다.
        fill_project(project_client, MAX_TEST_NUMBER - 2)
        before = project_client.get("/api/groups").json()["groups"]
        plan = preview(project_client, {"회원": [row(None, f"새 {i}") for i in range(5)]})
        project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"회원": "USER"}}
        )

        assert project_client.get("/api/drafts").json()["count"] == 0
        assert project_client.get("/api/groups").json()["groups"] == before

    def test_딱_맞으면_받는다(self, project_client: TestClient) -> None:
        fill_project(project_client, MAX_TEST_NUMBER - 3)
        plan = preview(project_client, {"회원": [row(None, f"새 {i}") for i in range(3)]})
        resp = project_client.post(
            COMMIT, json={"plan_id": plan["plan_id"], "prefixes": {"회원": "USER"}}
        )
        assert resp.status_code == 201, resp.text
        assert project_client.get("/api/drafts").json()["count"] == 3

    def test_미리보기가_수용_불가를_미리_알린다(self, project_client: TestClient) -> None:
        # 미리보기는 200 이다 — 막는 것은 확정이다. 사용자가 무엇이 문제인지 보고
        # 행을 줄이거나 프로젝트를 나눌 수 있어야 한다.
        #
        # 접두어를 **알 수 있게** TC ID 를 준다. 비워 두면 그 시트는 아직 초안 수에
        # 세지 않으므로(FR-022b) 수용량 판정에도 들어가지 않는다.
        fill_project(project_client, MAX_TEST_NUMBER - 1)
        body = preview(
            project_client,
            {"회원": [row(f"USER-{i:03d}", f"새 {i}") for i in range(1, 6)]},
        )
        assert body["capacity"]["needed"] == 5
        assert body["capacity"]["available"] == 1
        assert body["capacity"]["ok"] is False

    def test_접두어를_모르는_시트는_미리보기_수용량에_들어가지_않는다(
        self, project_client: TestClient
    ) -> None:
        # 세어 두면 미리보기가 예고한 수와 결과가 어긋난다 (SC-005).
        fill_project(project_client, MAX_TEST_NUMBER - 1)
        body = preview(project_client, {"데이터관리": [row(None, f"새 {i}") for i in range(5)]})
        assert body["capacity"]["needed"] == 0
        assert body["capacity"]["ok"] is True
        assert body["sheets"][0]["needs_prefix"] is True
        # 다만 행이 몇 개 기다리는지는 보여 준다.
        assert body["sheets"][0]["row_count"] == 5

    def test_건너뛸_시트는_수용량에_세지_않는다(self, project_client: TestClient) -> None:
        # 접두어를 비워 건너뛰는 시트의 행은 만들어지지 않으므로 자리를 차지하지 않는다.
        fill_project(project_client, MAX_TEST_NUMBER - 1)
        plan = preview(project_client, {"데이터관리": [row(None, f"새 {i}") for i in range(5)]})
        resp = project_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        assert resp.status_code == 201, resp.text
        assert resp.json()["drafts"] == []
