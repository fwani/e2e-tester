"""019 T037 (C7) — 확정이 실패했을 때 (FR-024 · SC-006).

**전부 성공하거나 아무것도 만들지 않는다.** 절반만 들어간 상태를 남기면 사용자는 무엇이
들어왔는지 세어 봐야 하고, 다시 시도하면 들어온 것이 두 벌이 된다.

`SHARE_IMPORT_FAILED` 와 `SHARE_IMPORT_PARTIAL` 을 가르는 이유는 **사용자가 할 일이 다르기
때문**이다 — 전자는 다시 시도하면 되고, 후자는 남은 것을 손으로 치워야 한다.
"""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient
from sharing_support import COMMIT, PLAN, export_bundle, make_test, repo_of, write_tests

from itb.storage.paths import workspace_dir


def _plan(client: TestClient, data: bytes, target: str = "new") -> str:
    resp = client.post(
        f"{PLAN}?target={target}",
        files={"file": ("team.itbshare.yaml", data, "application/yaml")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["plan_id"]


def _projects() -> set[str]:
    root = workspace_dir()
    return {p.name for p in root.iterdir()} if root.exists() else set()


class NewProjectFailureTests:
    def test_쓰기가_막히면_아무것도_남지_않는다(
        self, project_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        plan_id = _plan(project_client, export_bundle(project_client))
        before = _projects()

        # 두 번째 테스트를 쓰다 실패하게 만든다 — 첫 번째는 이미 임시 자리에 쓰였다.
        from itb.storage import repository as repo_mod

        original = repo_mod.ProjectRepository.write_test
        calls = {"n": 0}

        def flaky(self: object, test: object) -> pathlib.Path:
            calls["n"] += 1
            if calls["n"] == 2:
                msg = "디스크가 가득 찼습니다"
                raise OSError(msg)
            return original(self, test)  # type: ignore[arg-type]

        monkeypatch.setattr(repo_mod.ProjectRepository, "write_test", flaky)

        resp = project_client.post(COMMIT, json={"plan_id": plan_id})
        assert resp.status_code == 500
        assert resp.json()["error"]["code"] == "SHARE_IMPORT_FAILED"
        assert _projects() == before

    def test_임시_자리도_치운다(
        self, project_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """반쯤 만들어진 디렉터리가 남으면 다음 가져오기가 그것을 밟는다."""
        write_tests(project_client, make_test("TC-001", "가"))
        plan_id = _plan(project_client, export_bundle(project_client))

        from itb.storage import repository as repo_mod

        def always_fail(self: object, test: object) -> pathlib.Path:
            msg = "쓸 수 없습니다"
            raise OSError(msg)

        monkeypatch.setattr(repo_mod.ProjectRepository, "write_test", always_fail)
        project_client.post(COMMIT, json={"plan_id": plan_id})

        leftovers = [p.name for p in workspace_dir().iterdir() if p.name.startswith(".")]
        assert leftovers == []

    def test_실패해도_원본_프로젝트는_그대로다(
        self, project_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        plan_id = _plan(project_client, export_bundle(project_client))
        before = {t.id for t in repo_of(project_client).list_tests()[0]}

        from itb.storage import repository as repo_mod

        def always_fail(self: object, test: object) -> pathlib.Path:
            msg = "쓸 수 없습니다"
            raise OSError(msg)

        monkeypatch.setattr(repo_mod.ProjectRepository, "write_test", always_fail)
        project_client.post(COMMIT, json={"plan_id": plan_id})

        assert {t.id for t in repo_of(project_client).list_tests()[0]} == before


class CurrentProjectFailureTests:
    """US5 AS4 — 기존 프로젝트로 합치다 실패했을 때."""

    def test_실패하면_새_파일이_하나도_남지_않는다(
        self, project_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        data = export_bundle(project_client)
        plan_id = _plan(project_client, data, target="current")

        before = {p.name for p in repo_of(project_client).paths.tests_dir.iterdir()}

        from itb.storage import repository as repo_mod

        original = repo_mod.ProjectRepository.write_test
        calls = {"n": 0}

        def flaky(self: object, test: object) -> pathlib.Path:
            calls["n"] += 1
            if calls["n"] == 2:
                msg = "디스크가 가득 찼습니다"
                raise OSError(msg)
            return original(self, test)  # type: ignore[arg-type]

        monkeypatch.setattr(repo_mod.ProjectRepository, "write_test", flaky)

        resp = project_client.post(COMMIT, json={"plan_id": plan_id})
        assert resp.status_code == 500
        assert resp.json()["error"]["code"] in ("SHARE_IMPORT_FAILED", "SHARE_IMPORT_PARTIAL")

        after = {p.name for p in repo_of(project_client).paths.tests_dir.iterdir()}
        assert after == before

    def test_그룹도_되돌린다(
        self, project_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """그룹을 테스트보다 먼저 쓰므로, 실패하면 빈 그룹이 남을 수 있다 (research R5)."""
        project_client.post("/api/groups", json={"prefix": "USER", "name": "사용자관리"})
        write_tests(project_client, make_test("USER-001", "가"))
        data = export_bundle(project_client)

        # 그룹을 지운 프로젝트로 가져와야 「새로 만드는」 경로를 지난다.
        project_client.delete("/api/tests/USER-001")
        project_client.delete("/api/groups/USER")
        before = {g.prefix for g in repo_of(project_client).read_project().groups}

        plan_id = _plan(project_client, data, target="current")

        from itb.storage import repository as repo_mod

        def always_fail(self: object, test: object) -> pathlib.Path:
            msg = "쓸 수 없습니다"
            raise OSError(msg)

        monkeypatch.setattr(repo_mod.ProjectRepository, "write_test", always_fail)
        project_client.post(COMMIT, json={"plan_id": plan_id})

        after = {g.prefix for g in repo_of(project_client).read_project().groups}
        assert after == before
