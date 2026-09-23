"""내보내기 확인 계약 (019 T071·T072 · contracts/rest-api.md §1 · US4).

**되돌릴 수 없는 조작 앞의 유일한 방어선이다.** 파일이 나간 뒤에는 회수할 방법이 없으므로,
나가기 전에 보이는 것이 전부다.

평문 값을 **가리지 않는다**는 것이 이 파일의 중심 단언이다. 가려 놓으면 사번이나 사내
계정이 섞여 있어도 발견할 수 없다 — 그러면 이 화면이 있으나 마나다 (research R11).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sharing_support import (
    PREVIEW,
    click,
    fill,
    make_secret_test,
    make_test,
    navigate,
    repo_of,
    write_tests,
)

from itb.domain.test_case import variable_reference
from itb.sharing.limits import MAX_PLAINTEXT_PREVIEW_CHARS


class PreviewContentTests:
    def test_담길_것의_수를_알린다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        body = project_client.get(PREVIEW).json()
        assert body["test_count"] == 2
        assert body["project_name"] == "픽스처 프로젝트"

    def test_평문_값을_가리지_않고_위치와_함께_나열한다(self, project_client: TestClient) -> None:
        """이 표의 목적이 값을 보여 주는 것이다 (research R11)."""
        write_tests(
            project_client,
            make_test(
                "TC-001",
                "로그인",
                steps=[fill(1, "아이디 입력", "platform-user"), click(2, "확인")],
            ),
        )
        (row,) = project_client.get(PREVIEW).json()["plaintext_values"]
        assert row["value"] == "platform-user"
        assert row["test_id"] == "TC-001"
        assert row["step_label"] == "아이디 입력"
        assert row["truncated"] is False

    def test_변수_참조는_값이_아니므로_제외한다(self, keyed_client: TestClient) -> None:
        """`{{VAR}}` 는 자리표시자다. 값으로 세면 「비밀번호가 나간다」로 오해된다."""
        write_tests(keyed_client, make_secret_test())
        values = keyed_client.get(PREVIEW).json()["plaintext_values"]
        assert all("{{" not in v["value"] for v in values)

    def test_참조가_섞인_문자열은_남긴다(self, project_client: TestClient) -> None:
        """`https://사내주소/{{ID}}/detail` 의 앞부분이 사내 주소일 수 있다."""
        write_tests(
            project_client,
            make_test(
                "TC-001",
                "이동",
                steps=[
                    navigate(1, "상세로", f"https://internal.test/{variable_reference('ID')}"),
                    click(2, "확인"),
                ],
                variables=[{"name": "ID", "value": "42", "sensitive": False}],  # type: ignore[list-item]
            ),
        )
        values = project_client.get(PREVIEW).json()["plaintext_values"]
        assert any("internal.test" in v["value"] for v in values)

    def test_긴_값은_자르고_잘렸음을_표시한다(self, project_client: TestClient) -> None:
        long_value = "가" * (MAX_PLAINTEXT_PREVIEW_CHARS + 50)
        write_tests(
            project_client,
            make_test("TC-001", "긴 값", steps=[fill(1, "메모", long_value), click(2, "확인")]),
        )
        (row,) = project_client.get(PREVIEW).json()["plaintext_values"]
        assert len(row["value"]) == MAX_PLAINTEXT_PREVIEW_CHARS
        assert row["truncated"] is True

    def test_시작_주소를_함께_나가는_정보로_보인다(self, project_client: TestClient) -> None:
        """US4 AS3 — 사내 주소가 나간다는 사실을 보내는 사람이 알아야 한다."""
        write_tests(project_client, make_test("TC-001", "로그인"))
        urls = project_client.get(PREVIEW).json()["start_urls"]
        assert any(u["scope"] == "project" for u in urls)

    def test_테스트별로_다른_시작_주소도_보인다(self, project_client: TestClient) -> None:
        write_tests(
            project_client,
            make_test("TC-001", "다른 곳", start_url="https://other.internal/admin"),
        )
        urls = project_client.get(PREVIEW).json()["start_urls"]
        assert any(u["scope"] == "test" and u["test_id"] == "TC-001" for u in urls)

    def test_받는_사람이_채울_것을_미리_알린다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        (required,) = keyed_client.get(PREVIEW).json()["required_values"]
        assert required["name"] == "SECRET_LOGIN_PW"
        assert required["sensitive"] is True

    def test_고른_테스트만_미리_본다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        body = project_client.get(f"{PREVIEW}?test_ids=TC-002").json()
        assert body["test_count"] == 1


class PreviewIsReadOnlyTests:
    """T072 — 미리보기는 **파일을 만들지 않고 프로젝트를 바꾸지 않는다** (FR-008)."""

    def _snapshot(self, client: TestClient) -> dict[str, tuple[int, bytes]]:
        root = repo_of(client).paths.root
        return {
            str(p.relative_to(root)): (p.stat().st_mtime_ns, p.read_bytes())
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    def test_호출_전후로_프로젝트가_그대로다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        before = self._snapshot(project_client)

        assert project_client.get(PREVIEW).status_code == 200

        assert self._snapshot(project_client) == before

    def test_여러_번_불러도_같은_답이다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        first = project_client.get(PREVIEW).json()
        assert project_client.get(PREVIEW).json() == first

    def test_프로젝트가_없으면_404(self, client: TestClient) -> None:
        resp = client.get(PREVIEW)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PROJECT_NOT_OPEN"
