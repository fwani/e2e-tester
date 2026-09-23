"""019 T021 — 내보낼 것이 없을 때 (FR-009 · US1 AS4).

비어 있는 묶음을 건네면 받는 쪽이 "가져왔는데 아무것도 없다" 를 겪는다. 보내는 쪽에서
막는 편이 낫다 — 그 시점에는 아직 파일이 나가지 않았다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sharing_support import EXPORT, PREVIEW


class EmptyExportTests:
    def test_빈_프로젝트는_묶음을_만들지_않는다(self, project_client: TestClient) -> None:
        resp = project_client.post(EXPORT, json={})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_EXPORT_EMPTY"

    def test_사용자가_할_일을_알려준다(self, project_client: TestClient) -> None:
        body = project_client.post(EXPORT, json={}).json()["error"]
        assert body["category"] == "blocked"
        assert body["next_action"]

    def test_빈_선택도_같은_사유로_막힌다(self, project_client: TestClient) -> None:
        resp = project_client.post(EXPORT, json={"test_ids": []})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_EXPORT_EMPTY"

    def test_미리보기도_같은_사유로_막힌다(self, project_client: TestClient) -> None:
        resp = project_client.get(PREVIEW)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_EXPORT_EMPTY"
