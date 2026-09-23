"""019 T080 (C6) — 기존 프로젝트에 합치기 (US5 · FR-021·FR-025 · SC-005).

**기존 테스트가 사라지지 않는다**는 것이 이 파일의 절대 조건이다. 덮어쓰기는 되돌릴 수
없는 손실이고, 사용자는 그것이 일어났다는 사실조차 모른 채 지나간다.

겹치면 **들어오는 쪽이 양보한다.** 받는 사람의 자산이 먼저다.
"""

from __future__ import annotations

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


def _bundle_of(client: TestClient, *tests) -> bytes:
    """묶음을 만든 뒤 원본을 지운다 — 같은 프로젝트로 되돌려 넣기 위해서다."""
    write_tests(client, *tests)
    data = export_bundle(client)
    repo = repo_of(client)
    for test in tests:
        path = repo.find_test_path(test.id)
        if path is not None:
            path.unlink()
    return data


def _merge(client: TestClient, data: bytes) -> dict:
    plan = client.post(
        f"{PLAN}?target=current",
        files={"file": ("동료-묶음.itbshare.yaml", data, "application/yaml")},
    )
    assert plan.status_code == 201, plan.text
    report = client.post(COMMIT, json={"plan_id": plan.json()["plan_id"]})
    assert report.status_code == 201, report.text
    return report.json()


class MergeIntoCurrentTests:
    def test_이_프로젝트에_테스트가_더해진다(self, project_client: TestClient) -> None:
        data = _bundle_of(project_client, make_test("TC-001", "동료의 것"))
        write_tests(project_client, make_test("TC-005", "내 것"))

        _merge(project_client, data)

        ids = {t.id for t in repo_of(project_client).list_tests()[0]}
        assert ids == {"TC-001", "TC-005"}

    def test_겹치면_들어오는_쪽이_양보하고_둘_다_남는다(self, project_client: TestClient) -> None:
        """C6 · SC-005 — 기존 테스트가 사라지는 경우가 0건이어야 한다."""
        data = _bundle_of(project_client, make_test("TC-001", "동료의 것"))
        write_tests(project_client, make_test("TC-001", "내 것"))

        report = _merge(project_client, data)

        tests = {t.id: t.name for t in repo_of(project_client).list_tests()[0]}
        assert tests["TC-001"] == "내 것", "기존 테스트가 덮어써졌다"
        assert "동료의 것" in tests.values()
        assert report["renumbered"] == [{"from": "TC-001", "to": "TC-002"}]

    def test_바뀐_번호를_결과에_전부_알린다(self, project_client: TestClient) -> None:
        """사용자의 설계서에는 원래 번호가 적혀 있다. 조용히 바꾸면 나중에 발견한다."""
        data = _bundle_of(
            project_client, make_test("TC-001", "가"), make_test("TC-002", "나")
        )
        write_tests(project_client, make_test("TC-001", "내 것"), make_test("TC-002", "내 것2"))

        report = _merge(project_client, data)

        changed = {r["from"]: r["to"] for r in report["renumbered"]}
        assert changed == {"TC-001": "TC-003", "TC-002": "TC-004"}

    def test_빈_번호를_채운다(self, project_client: TestClient) -> None:
        data = _bundle_of(project_client, make_test("TC-001", "동료의 것"))
        write_tests(
            project_client,
            make_test("TC-001", "가"),
            make_test("TC-002", "나"),
            make_test("TC-004", "라"),
        )

        report = _merge(project_client, data)

        assert report["renumbered"] == [{"from": "TC-001", "to": "TC-003"}]

    def test_출처가_남아_어디서_왔는지_알_수_있다(self, project_client: TestClient) -> None:
        data = _bundle_of(project_client, make_test("TC-001", "동료의 것"))
        write_tests(project_client, make_test("TC-001", "내 것"))

        _merge(project_client, data)

        imported = repo_of(project_client).read_test("TC-002")
        assert imported.imported_from is not None
        assert imported.imported_from.original_id == "TC-001"
        # 내 것에는 출처가 없다 — 가져온 것과 만든 것이 구별된다.
        assert repo_of(project_client).read_test("TC-001").imported_from is None

    def test_프로젝트_설정은_바뀌지_않는다(self, project_client: TestClient) -> None:
        """기존 프로젝트로 합칠 때 남의 시작 주소로 갈아 끼우면 내 테스트가 깨진다."""
        data = _bundle_of(
            project_client, make_test("TC-001", "동료의 것", start_url="https://other.test/x")
        )
        before = repo_of(project_client).read_project()

        _merge(project_client, data)

        after = repo_of(project_client).read_project()
        assert after.default_start_url == before.default_start_url

    def test_민감_변수는_이미_있는_값을_쓴다(self, keyed_client: TestClient) -> None:
        """같은 이름이면 이미 봉인한 값이 그대로 쓰인다 (FR-046)."""
        data = _bundle_of(keyed_client, make_secret_test("TC-001"))
        keyed_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": "내-값"})

        report = _merge(keyed_client, data)

        (value,) = [v for v in report["required_values"] if v["name"] == "SECRET_LOGIN_PW"]
        assert value["already_stored"] is True
        assert keyed_client.get("/api/tests/TC-001/readiness").json()["runnable"] is True


class MergeGroupTests:
    """US5 AS3 — 그룹은 **이름**으로 대응시킨다 (FR-027)."""

    def test_같은_이름의_그룹에_들어간다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        data = _bundle_of(project_client, make_test("USER-001", "동료의 것"))
        project_client.delete("/api/groups/USER")
        project_client.post("/api/groups", json={"prefix": "USR", "name": "사용자관리"})

        report = _merge(project_client, data)

        assert report["created_tests"][0]["target_id"].startswith("USR-")
        assert report["created_groups"] == []

    def test_없는_그룹은_만들어진다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        data = _bundle_of(project_client, make_test("USER-001", "동료의 것"))
        project_client.delete("/api/groups/USER")

        report = _merge(project_client, data)

        assert report["created_groups"] == [{"prefix": "USER", "name": "사용자관리"}]

    def test_접두어가_다른_이름에_쓰이면_비껴간다(self, project_client: TestClient) -> None:
        """접두어만 같고 이름이 다르면 다른 그룹이다. 양보하는 쪽은 들어오는 쪽이다."""
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        data = _bundle_of(project_client, make_test("USER-001", "동료의 것"))
        project_client.delete("/api/groups/USER")
        project_client.post("/api/groups", json={"prefix": "USER", "name": "회원"})

        report = _merge(project_client, data)

        assert report["created_groups"] == [{"prefix": "USER2", "name": "사용자관리"}]
        assert report["created_tests"][0]["target_id"].startswith("USER2-")

    def test_기존_그룹은_그대로_남는다(self, project_client: TestClient) -> None:
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        data = _bundle_of(project_client, make_test("USER-001", "동료의 것"))
        project_client.delete("/api/groups/USER")
        project_client.post("/api/groups", json={"prefix": "USER", "name": "회원"})

        _merge(project_client, data)

        groups = {g.prefix: g.name for g in repo_of(project_client).read_project().groups}
        assert groups["USER"] == "회원"
        assert groups["USER2"] == "사용자관리"
