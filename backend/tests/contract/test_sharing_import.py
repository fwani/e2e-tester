"""공유 묶음 가져오기 계약 (019 T035 · contracts/rest-api.md §3~§5).

**계획 단계가 디스크를 건드리지 않는다**는 것이 이 파일의 중심이다. 확정 전에 무언가
만들면 그 자체가 "만든 것" 이 되고, 사용자가 취소했을 때 치울 것이 생긴다.
"""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient
from sharing_support import (
    COMMIT,
    PLAN,
    export_bundle,
    make_secret_test,
    make_test,
    repo_of,
    write_tests,
)

from itb.storage.paths import workspace_dir


def _upload(client: TestClient, data: bytes, target: str = "new", name: str = "team.itbshare.yaml"):
    return client.post(
        f"{PLAN}?target={target}",
        files={"file": (name, data, "application/yaml")},
    )


def _projects() -> set[str]:
    root = workspace_dir()
    return {p.name for p in root.iterdir()} if root.exists() else set()


class SharePlanTests:
    def test_계획을_세운다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client)

        resp = _upload(project_client, data)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["plan_id"]
        assert [t["source_id"] for t in body["tests"]] == ["TC-001"]
        assert body["blocking"] == []

    def test_계획_단계는_아무것도_만들지_않는다(self, project_client: TestClient) -> None:
        """확정 전에 만들면 그 자체가 「만든 것」이 된다 (FR-022·FR-023)."""
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client)
        before = _projects()

        assert _upload(project_client, data).status_code == 201

        assert _projects() == before

    def test_시작_주소를_확인거리로_알린다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        body = _upload(project_client, export_bundle(project_client)).json()
        assert any(n["code"] == "START_URL_CHECK" for n in body["notices"])

    def test_필요한_값을_미리_보여_준다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test(plain_name="LOGIN_ID"))
        body = _upload(keyed_client, export_bundle(keyed_client)).json()
        by_name = {v["name"]: v for v in body["required_values"]}
        assert by_name["SECRET_LOGIN_PW"]["blocks_run"] is True
        assert by_name["LOGIN_ID"]["blocks_run"] is False

    def test_이미_값이_있으면_그_사실을_싣는다(self, keyed_client: TestClient) -> None:
        """조용히 덮어쓰지 않으려면 사용자가 먼저 알아야 한다 (FR-046)."""
        from sharing_support import seal_secret

        write_tests(keyed_client, make_secret_test())
        seal_secret(keyed_client, "SECRET_LOGIN_PW")
        data = export_bundle(keyed_client)

        body = _upload(keyed_client, data, target="current").json()
        (value,) = [v for v in body["required_values"] if v["name"] == "SECRET_LOGIN_PW"]
        assert value["already_stored"] is True

    def test_계획을_다시_조회할_수_있다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        plan_id = _upload(project_client, export_bundle(project_client)).json()["plan_id"]

        again = project_client.get(f"/api/share/import/plan/{plan_id}")
        assert again.status_code == 200
        assert again.json()["plan_id"] == plan_id

    def test_없는_계획은_404(self, project_client: TestClient) -> None:
        resp = project_client.get("/api/share/import/plan/없는것")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SHARE_PLAN_NOT_FOUND"

    def test_모르는_대상은_거절한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        resp = _upload(project_client, export_bundle(project_client), target="어딘가")
        assert resp.status_code == 400


class ShareCommitTests:
    def test_새_프로젝트로_복원한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client)
        plan_id = _upload(project_client, data).json()["plan_id"]

        resp = project_client.post(COMMIT, json={"plan_id": plan_id})
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert [t["source_id"] for t in body["created_tests"]] == ["TC-001"]
        assert pathlib.Path(body["project_root"]).is_dir()

    def test_복원한_테스트가_목록에_나타난다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        plan_id = _upload(project_client, export_bundle(project_client)).json()["plan_id"]
        project_client.post(COMMIT, json={"plan_id": plan_id})

        listing = project_client.get("/api/tests").json()
        assert [t["id"] for t in listing["tests"]] == ["TC-001"]

    def test_이름이_겹치면_비껴_만들고_알린다(self, project_client: TestClient) -> None:
        """기존 프로젝트를 덮어쓰지 않는다 (US2 AS3)."""
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client)
        plan = _upload(project_client, data).json()

        assert plan["project_renamed_from"] == "픽스처 프로젝트"
        assert plan["target_project_name"] != "픽스처 프로젝트"
        assert any(n["code"] == "PROJECT_RENAMED" for n in plan["notices"])

    def test_확정_후_새_프로젝트가_열린다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        plan_id = _upload(project_client, export_bundle(project_client)).json()["plan_id"]

        report = project_client.post(COMMIT, json={"plan_id": plan_id}).json()
        opened = project_client.get("/api/project").json()
        assert opened["root"] == report["project_root"]

    def test_시작_주소를_바꿔_받을_수_있다(self, project_client: TestClient) -> None:
        """받는 쪽 환경이 다를 수 있다 (spec Edge Cases)."""
        write_tests(project_client, make_test("TC-001", "로그인"))
        plan_id = _upload(project_client, export_bundle(project_client)).json()["plan_id"]

        project_client.post(
            COMMIT,
            json={"plan_id": plan_id, "default_start_url": "https://staging.example.test"},
        )
        assert (
            repo_of(project_client).read_project().default_start_url
            == "https://staging.example.test"
        )

    def test_같은_계획을_두_번_확정할_수_없다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        plan_id = _upload(project_client, export_bundle(project_client)).json()["plan_id"]

        assert project_client.post(COMMIT, json={"plan_id": plan_id}).status_code == 201
        again = project_client.post(COMMIT, json={"plan_id": plan_id})
        assert again.status_code == 404
        assert again.json()["error"]["code"] == "SHARE_PLAN_NOT_FOUND"

    def test_없는_계획을_확정하면_404(self, project_client: TestClient) -> None:
        resp = project_client.post(COMMIT, json={"plan_id": "없는것"})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SHARE_PLAN_NOT_FOUND"

    def test_민감_값을_이_경로로_받지_않는다(self, keyed_client: TestClient) -> None:
        """C12 — 봉인 경로는 하나뿐이다 (contracts §5)."""
        write_tests(keyed_client, make_secret_test())
        plan_id = _upload(keyed_client, export_bundle(keyed_client)).json()["plan_id"]

        resp = keyed_client.post(
            COMMIT,
            json={"plan_id": plan_id, "variable_values": {"SECRET_LOGIN_PW": "몰래"}},
        )
        assert resp.status_code == 400
        assert "SECRET_LOGIN_PW" in resp.json()["error"]["detail"]["names"]

    def test_비민감_값은_정의에_기록된다(self, keyed_client: TestClient) -> None:
        """FR-048 — 민감 값과 저장 위치가 다르다."""
        write_tests(keyed_client, make_secret_test(plain_name="LOGIN_ID"))
        plan_id = _upload(keyed_client, export_bundle(keyed_client)).json()["plan_id"]

        keyed_client.post(
            COMMIT, json={"plan_id": plan_id, "variable_values": {"LOGIN_ID": "platform-b"}}
        )
        test = repo_of(keyed_client).read_test("TC-001")
        (login_id,) = [v for v in test.variables if v.name == "LOGIN_ID"]
        assert login_id.value == "platform-b"

    def test_가져온_테스트에_출처가_남는다(self, project_client: TestClient) -> None:
        """반년 뒤 「이거 어디서 왔지」의 답이 테스트 파일에 있어야 한다 (FR-028)."""
        write_tests(project_client, make_test("TC-001", "로그인"))
        plan_id = _upload(
            project_client, export_bundle(project_client), name="동료-묶음.itbshare.yaml"
        ).json()["plan_id"]
        project_client.post(COMMIT, json={"plan_id": plan_id})

        test = repo_of(project_client).read_test("TC-001")
        assert test.imported_from is not None
        assert test.imported_from.source_file == "동료-묶음.itbshare.yaml"
        assert test.imported_from.original_id == "TC-001"
