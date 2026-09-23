"""019 T060 — 값 인계 전체 흐름 (US3 · FR-040~FR-048).

가져오기 → 값 채우기 → 실행 가능까지를 한 줄로 확인한다.

**입력한 평문이 어디에도 다시 나타나지 않는다**는 것이 이 파일의 두 번째 축이다 (FR-043).
정의 파일·API 응답·비밀 파일 어디를 봐도 평문이 없어야 한다 — 봉인은 그래야 봉인이다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sharing_support import (
    COMMIT,
    PLAN,
    export_bundle,
    make_secret_test,
    repo_of,
    write_tests,
)

RECEIVED_PASSWORD = "받는-사람의-비밀번호-019"
"""받는 쪽이 채워 넣는 값. 보내는 쪽의 값과 **다르다** — 그래야 섞이지 않았음을 안다."""


def _import(client: TestClient, data: bytes, target: str = "new") -> dict:
    plan = client.post(
        f"{PLAN}?target={target}",
        files={"file": ("동료-묶음.itbshare.yaml", data, "application/yaml")},
    )
    assert plan.status_code == 201, plan.text
    report = client.post(COMMIT, json={"plan_id": plan.json()["plan_id"]})
    assert report.status_code == 201, report.text
    return report.json()


class SecretHandoverTests:
    def test_가져온_직후에는_채워야_할_것이_남는다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test(plain_name="LOGIN_ID"))
        report = _import(keyed_client, export_bundle(keyed_client))

        by_name = {v["name"]: v for v in report["required_values"]}
        assert by_name["SECRET_LOGIN_PW"]["blocks_run"] is True
        assert by_name["SECRET_LOGIN_PW"]["already_stored"] is False

    def test_쓰이는_자리를_함께_알려준다(self, keyed_client: TestClient) -> None:
        """이름만으로는 무엇을 넣을지 모른다 (FR-040)."""
        write_tests(keyed_client, make_secret_test())
        report = _import(keyed_client, export_bundle(keyed_client))

        (value,) = report["required_values"]
        (usage,) = value["usages"]
        assert usage["step_label"] == "비밀번호 입력"
        assert usage["test_id"] == "TC-001"

    def test_채우기_전에는_실행이_막힌다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        _import(keyed_client, export_bundle(keyed_client))

        resp = keyed_client.post("/api/sessions", json={"mode": "replay", "test_id": "TC-001"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SECRET_VALUE_MISSING"

    def test_채우면_실행_가능해진다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        _import(keyed_client, export_bundle(keyed_client))

        assert keyed_client.get("/api/tests/TC-001/readiness").json()["runnable"] is False

        put = keyed_client.put(
            "/api/secrets/SECRET_LOGIN_PW", json={"value": RECEIVED_PASSWORD}
        )
        assert put.status_code == 204, put.text

        assert keyed_client.get("/api/tests/TC-001/readiness").json()["runnable"] is True

    def test_채운_평문이_어디에도_다시_나타나지_않는다(self, keyed_client: TestClient) -> None:
        """FR-043 — 봉인은 그래야 봉인이다."""
        write_tests(keyed_client, make_secret_test())
        _import(keyed_client, export_bundle(keyed_client))
        keyed_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": RECEIVED_PASSWORD})

        repo = repo_of(keyed_client)
        needle = RECEIVED_PASSWORD

        # 정의 파일
        for path in repo.paths.tests_dir.iterdir():
            assert needle not in path.read_text(encoding="utf-8")
        # 비밀 파일 (암호문이어야 한다)
        assert needle not in repo.paths.secrets_file.read_text(encoding="utf-8")
        # 목록 응답
        assert needle not in keyed_client.get("/api/secrets").text
        # 다시 내보낸 묶음
        assert needle.encode("utf-8") not in export_bundle(keyed_client)

    def test_비민감_값은_정의에_남고_봉인되지_않는다(self, keyed_client: TestClient) -> None:
        """FR-048 — 저장 위치가 다르다. 어느 쪽인지 사용자가 알아야 한다."""
        write_tests(keyed_client, make_secret_test(plain_name="LOGIN_ID"))
        data = export_bundle(keyed_client)

        plan = keyed_client.post(
            f"{PLAN}?target=new",
            files={"file": ("동료-묶음.itbshare.yaml", data, "application/yaml")},
        ).json()
        keyed_client.post(
            COMMIT,
            json={"plan_id": plan["plan_id"], "variable_values": {"LOGIN_ID": "platform-b"}},
        )

        test = repo_of(keyed_client).read_test("TC-001")
        (login_id,) = [v for v in test.variables if v.name == "LOGIN_ID"]
        assert login_id.value == "platform-b"
        assert login_id.sensitive is False
        # 봉인 저장소에는 들어가지 않는다.
        assert "LOGIN_ID" not in keyed_client.get("/api/secrets").text

    def test_이미_값이_있으면_그대로_두고_알린다(self, keyed_client: TestClient) -> None:
        """FR-046 — 조용히 덮어쓰지 않는다."""
        write_tests(keyed_client, make_secret_test())
        keyed_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": "기존-값"})
        data = export_bundle(keyed_client)

        plan = keyed_client.post(
            f"{PLAN}?target=current",
            files={"file": ("동료-묶음.itbshare.yaml", data, "application/yaml")},
        ).json()
        (value,) = [v for v in plan["required_values"] if v["name"] == "SECRET_LOGIN_PW"]
        assert value["already_stored"] is True

        # 가져오기가 그 값을 건드리지 않았다.
        keyed_client.post(COMMIT, json={"plan_id": plan["plan_id"]})
        assert keyed_client.get("/api/tests/TC-001/readiness").json()["runnable"] is True


class NoKeyTests:
    """FR-045 — 키가 없어도 **가져오기 자체는 완료된다.** 막히는 것은 값 입력 시점이다."""

    def test_키가_없어도_가져올_수_있다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_secret_test())
        report = _import(project_client, export_bundle(project_client))
        assert len(report["created_tests"]) == 1

    def test_키가_없다는_사실을_알린다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_secret_test())
        _import(project_client, export_bundle(project_client))

        body = project_client.get("/api/tests/TC-001/readiness").json()
        assert body["key_available"] is False
        assert body["runnable"] is False

    def test_값을_채우려면_키가_먼저다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_secret_test())
        _import(project_client, export_bundle(project_client))

        resp = project_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": "값"})
        assert resp.status_code >= 400
