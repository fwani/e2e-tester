"""내보낸 워크북에 민감 값이 없다 (014 T028 · FR-007 · SC-008).

**값이 실제로 존재하는 상태에서 확인한다.** 값이 어디에도 저장돼 있지 않아서 새지 않은
것을 통과로 착각하면 안 되므로, 비밀 값을 봉인해 둔 뒤 내보낸다.

내보낸 바이트를 **압축을 풀어** 훑는다. `.xlsx` 는 zip 이므로 겉바이트만 보면 안에 든 XML 의
글자를 놓친다 — 그 안이 실제로 사람이 읽는 곳이다.
"""

from __future__ import annotations

import io
import zipfile

from excel_support import check, fill, make_test, read_back, repo_of
from fastapi.testclient import TestClient

from itb.domain.test_case import Variable
from itb.portability.sheet_name import UNGROUPED_SHEET_NAME

SECRET_VALUE = "Tr0ub4dor-3-not-a-real-password"
"""워크북 어디에도 나타나면 안 되는 값. 우연히 겹치지 않도록 길게 잡는다."""

EXPORT = "/api/export"


def unpacked_text(data: bytes) -> str:
    """워크북 안의 모든 항목을 이어 붙인 텍스트.

    `.xlsx` 는 zip 이다. 겉바이트만 grep 하면 압축된 XML 안의 글자를 놓친다.
    """
    chunks: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            chunks.append(zf.read(name).decode("utf-8", errors="replace"))
    return "\n".join(chunks)


def seed_secret_test(client: TestClient) -> None:
    """민감 변수를 참조하는 스텝이 있는 테스트를 심는다."""
    repo = repo_of(client)
    repo.write_test(
        make_test(
            "TC-001",
            "로그인",
            variables=[Variable(name="SECRET_LOGIN_PW", value=None, sensitive=True)],
            steps=[
                fill(1, "비밀번호 입력", "{{SECRET_LOGIN_PW}}"),
                check(2, "대시보드 확인", "대시보드"),
            ],
        )
    )


class SecretsNeverExportedTests:
    def test_봉인된_값이_워크북에_없다(self, keyed_client: TestClient) -> None:
        resp = keyed_client.put(
            "/api/secrets/SECRET_LOGIN_PW", json={"value": SECRET_VALUE}
        )
        assert resp.status_code in (200, 201, 204), resp.text
        seed_secret_test(keyed_client)

        data = keyed_client.get(EXPORT).content
        assert SECRET_VALUE not in unpacked_text(data)

    def test_봉인된_값이_겉바이트에도_없다(self, keyed_client: TestClient) -> None:
        keyed_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": SECRET_VALUE})
        seed_secret_test(keyed_client)
        assert SECRET_VALUE.encode() not in keyed_client.get(EXPORT).content

    def test_변수_참조는_참조_그대로_나간다(self, keyed_client: TestClient) -> None:
        # 값은 감추되 참조는 보여야 한다 — 그래야 무엇을 쓰는 테스트인지 읽힌다 (FR-007).
        keyed_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": SECRET_VALUE})
        seed_secret_test(keyed_client)
        row = read_back(keyed_client.get(EXPORT).content)[UNGROUPED_SHEET_NAME][1]
        assert "비밀번호 입력" in row[4]

    def test_값이_실제로_저장돼_있음을_먼저_확인한다(self, keyed_client: TestClient) -> None:
        # 이 검사가 없으면 "값이 없어서 새지 않은" 상태를 통과로 착각한다.
        keyed_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": SECRET_VALUE})
        seed_secret_test(keyed_client)
        repo = repo_of(keyed_client)
        assert repo.paths.secrets_file.exists()
        assert repo.paths.secrets_file.read_text(encoding="utf-8").strip()

    def test_민감_변수의_값은_정의에도_없다(self, keyed_client: TestClient) -> None:
        keyed_client.put("/api/secrets/SECRET_LOGIN_PW", json={"value": SECRET_VALUE})
        seed_secret_test(keyed_client)
        definition = keyed_client.get("/api/tests/TC-001").json()
        sensitive = [v for v in definition["variables"] if v["sensitive"]]
        assert sensitive
        assert all(v["value"] is None for v in sensitive)


class StructuralGuaranteeTests:
    def test_내보내기_모듈이_비밀_계층을_임포트하지_않는다(self) -> None:
        """구조로 보장한다 — 검사로 보장하는 것보다 낫다.

        :mod:`itb.portability.exporter` 가 :mod:`itb.secrets` 를 임포트하지 않으면, 값이
        무엇인지 **알 방법 자체가 없다**. 나중에 누가 실수로 값을 실으려 해도 임포트를
        먼저 추가해야 하고, 그 줄은 리뷰에서 눈에 띈다.
        """
        import ast
        import pathlib

        # 문자열 검색이 아니라 **임포트문**을 본다. 주석이나 설명에 이름이 나오는 것과
        # 실제로 의존하는 것은 다르다.
        tree = ast.parse(
            pathlib.Path("src/itb/portability/exporter.py").read_text(encoding="utf-8")
        )
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        assert not any(m.startswith("itb.secrets") for m in imported), imported
