"""019 T093 (C10) — 공유 경로에도 프로젝트 대조 가드가 걸린다 (contracts §머리말).

`/api/project` 아래에 두지 않은 이유가 이것이다. 그 아래 두면 가드가 걸리지 않아, 화면이
프로젝트 A 를 보여 주는데 서버가 연 B 를 조용히 내보낸다 — 2026-09-10 사용자 보고 1번과
같은 모양의 사고다.
"""

from __future__ import annotations

import urllib.parse

from fastapi.testclient import TestClient
from sharing_support import EXPORT, PLAN, PREVIEW, export_bundle, make_test, write_tests

HEADER = "X-ITB-Project-Root"

ELSEWHERE = {HEADER: "/somewhere/else/project"}
"""화면이 **다른** 프로젝트를 보고 있다고 말하는 헤더.

실재하지 않는 경로여도 된다 — 가드는 열린 프로젝트와 **다른가**만 보고, 다르면 아무 일도
하기 전에 거절한다.
"""


class ShareGuardTests:
    def test_내보내기가_어긋난_프로젝트를_거절한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        resp = project_client.post(EXPORT, json={}, headers=ELSEWHERE)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PROJECT_MISMATCH"

    def test_미리보기도_거절한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        resp = project_client.get(PREVIEW, headers=ELSEWHERE)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PROJECT_MISMATCH"

    def test_가져오기_계획도_거절한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"))
        data = export_bundle(project_client)
        resp = project_client.post(
            f"{PLAN}?target=current",
            files={"file": ("b.itbshare.yaml", data, "application/yaml")},
            headers=ELSEWHERE,
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "PROJECT_MISMATCH"

    def test_맞는_프로젝트면_통과한다(self, project_client: TestClient) -> None:
        """헤더는 **퍼센트 인코딩**되어 온다 — 프로젝트 이름에 한글이 흔하고, HTTP 헤더
        값은 ISO-8859-1 이라 인코딩하지 않으면 브라우저가 요청을 보내지도 않는다.
        """
        write_tests(project_client, make_test("TC-001", "가"))
        root = project_client.get("/api/project").json()["root"]
        encoded = urllib.parse.quote(root)
        resp = project_client.post(EXPORT, json={}, headers={HEADER: encoded})
        assert resp.status_code == 200

    def test_헤더가_없으면_가드가_걸리지_않는다(self, project_client: TestClient) -> None:
        """기존 클라이언트·계약 테스트·curl 이 그대로 동작해야 한다 (app.py 주석)."""
        write_tests(project_client, make_test("TC-001", "가"))
        assert project_client.post(EXPORT, json={}).status_code == 200
