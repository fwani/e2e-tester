"""공유 묶음 내보내기 계약 (019 T017·T018·T020 · contracts/rest-api.md §2).

**T018 이 이 파일의 중심이다.** 응답 바이트에 민감 값이 어떤 형태로도 나타나지 않는다는
것이 이 기능의 유일한 절대 조건이고(SC-004), 그것을 확인하는 자리가 여기다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sharing_support import (
    EXPORT,
    KNOWN_PASSWORD,
    ciphertexts,
    load_bundle,
    make_secret_test,
    make_test,
    repo_of,
    seal_secret,
    write_tests,
)


class ShareExportResponseTests:
    def test_열린_프로젝트를_내보낸다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        resp = project_client.post(EXPORT, json={})
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/yaml")

    def test_받은_바이트가_읽히는_묶음이다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        bundle = load_bundle(project_client.post(EXPORT, json={}).content)
        assert bundle["bundle_version"] == 1
        assert len(bundle["tests"]) == 1

    def test_파일_이름을_붙여_내려보낸다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        disposition = project_client.post(EXPORT, json={}).headers["content-disposition"]
        assert disposition.startswith("attachment;")
        assert ".itbshare.yaml" in disposition

    def test_한글_이름을_두_가지로_싣는다(self, project_client: TestClient) -> None:
        # 픽스처 프로젝트 이름이 한글이다. 헤더는 ASCII 제한이므로 두 이름이 함께 가야 한다.
        write_tests(project_client, make_test("TC-001", "로그인"))
        disposition = project_client.post(EXPORT, json={}).headers["content-disposition"]
        assert "filename=" in disposition
        assert "filename*=UTF-8''" in disposition
        disposition.encode("ascii")  # 예외가 나면 실패다

    def test_담긴_테스트_수를_헤더로_알린다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        assert project_client.post(EXPORT, json={}).headers["x-itb-share-test-count"] == "2"

    def test_빠진_것이_없으면_그_헤더가_없다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        assert "x-itb-share-unreadable" not in project_client.post(EXPORT, json={}).headers

    def test_프로젝트가_없으면_404(self, client: TestClient) -> None:
        resp = client.post(EXPORT, json={})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PROJECT_NOT_OPEN"


class ShareExportSelectionTests:
    def test_고른_테스트만_담는다(self, project_client: TestClient) -> None:
        write_tests(
            project_client,
            make_test("TC-001", "가"),
            make_test("TC-002", "나"),
            make_test("TC-003", "다"),
        )
        bundle = load_bundle(project_client.post(EXPORT, json={"test_ids": ["TC-002"]}).content)
        assert [t["id"] for t in bundle["tests"]] == ["TC-002"]

    def test_목록을_주지_않으면_전체다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        bundle = load_bundle(project_client.post(EXPORT, json={"test_ids": None}).content)
        assert {t["id"] for t in bundle["tests"]} == {"TC-001", "TC-002"}

    def test_없는_식별자를_고르면_404(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        resp = project_client.post(EXPORT, json={"test_ids": ["TC-999"]})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"


class ShareExportSecretLeakTests:
    """C1 — 민감 값이 묶음에 나타나지 않는다 (SC-004).

    **이 기능의 유일한 절대 조건이다.** 하나라도 걸리면 실패다.
    """

    def test_평문_비밀값이_바이트에_없다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        seal_secret(keyed_client, "SECRET_LOGIN_PW")

        data = keyed_client.post(EXPORT, json={}).content
        assert KNOWN_PASSWORD.encode("utf-8") not in data

    def test_암호문도_바이트에_없다(self, keyed_client: TestClient) -> None:
        """암호문은 열 수 없지만, 실려 나가면 어느 변수가 있는지가 드러난다."""
        write_tests(keyed_client, make_secret_test())
        seal_secret(keyed_client, "SECRET_LOGIN_PW")

        repo = repo_of(keyed_client)
        sealed = ciphertexts(repo)
        assert sealed, "봉인된 값이 없으면 이 검증은 아무것도 확인하지 않는다"

        text = keyed_client.post(EXPORT, json={}).content.decode("utf-8")
        assert [c for c in sealed if c in text] == []

    def test_민감_변수는_이름과_참조만_실린다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        seal_secret(keyed_client, "SECRET_LOGIN_PW")

        bundle = load_bundle(keyed_client.post(EXPORT, json={}).content)
        (test,) = bundle["tests"]
        (variable,) = [v for v in test["variables"] if v["name"] == "SECRET_LOGIN_PW"]
        assert variable["sensitive"] is True
        assert variable["value"] is None
        assert test["steps"][0]["value"] == "{{SECRET_LOGIN_PW}}"

    def test_필요_값_목록에_이름과_쓰이는_자리가_실린다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        bundle = load_bundle(keyed_client.post(EXPORT, json={}).content)
        (required,) = bundle["required_values"]
        assert required["name"] == "SECRET_LOGIN_PW"
        assert required["sensitive"] is True
        assert required["usages"][0]["step_label"] == "비밀번호 입력"

    def test_값이_빈_비민감_변수도_필요_값이다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test(plain_name="LOGIN_ID"))
        bundle = load_bundle(keyed_client.post(EXPORT, json={}).content)
        by_name = {v["name"]: v for v in bundle["required_values"]}
        assert by_name["LOGIN_ID"]["sensitive"] is False
        assert by_name["SECRET_LOGIN_PW"]["sensitive"] is True


class ShareExportDoesNotTouchProjectTests:
    """T020 — FR-008. 미리보기만이 아니라 **내보내기 자체**가 프로젝트를 바꾸지 않는다."""

    def _snapshot(self, client: TestClient) -> dict[str, tuple[int, bytes]]:
        root = repo_of(client).paths.root
        return {
            str(p.relative_to(root)): (p.stat().st_mtime_ns, p.read_bytes())
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    def test_파일_목록과_내용이_그대로다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        before = self._snapshot(project_client)

        assert project_client.post(EXPORT, json={}).status_code == 200

        assert self._snapshot(project_client) == before

    def test_테스트_목록_응답도_그대로다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        before = project_client.get("/api/tests").json()
        project_client.post(EXPORT, json={})
        assert project_client.get("/api/tests").json() == before
