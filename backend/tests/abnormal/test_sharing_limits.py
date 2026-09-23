"""019 T092 — 상한 (research R12).

**막는 시점이 중요하다.** 바이트 상한은 해석을 시작하기 **전에** 판정한다 — 늦게 막으면
막지 않은 것과 같다. 014 가 압축 해제 총량을 열기 전에 판정한 것과 같은 판단이다.
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient
from sharing_support import PLAN

from itb.sharing.limits import MAX_BUNDLE_BYTES, MAX_BUNDLE_GROUPS, MAX_BUNDLE_TESTS


def _upload(client: TestClient, data: bytes):
    return client.post(
        f"{PLAN}?target=new",
        files={"file": ("big.itbshare.yaml", data, "application/yaml")},
    )


class ByteLimitTests:
    def test_상한을_넘는_파일을_거절한다(self, project_client: TestClient) -> None:
        data = b"bundle_version: 1\nfiller: " + b"x" * MAX_BUNDLE_BYTES
        resp = _upload(project_client, data)
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_TOO_LARGE"

    def test_파싱하지_않고_거절한다(self, project_client: TestClient) -> None:
        """이 입력은 YAML 로 읽히지 않는다. 그래도 상한으로 먼저 걸려야 한다."""
        data = b"[" * (MAX_BUNDLE_BYTES + 1)
        started = time.monotonic()
        resp = _upload(project_client, data)
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_TOO_LARGE"
        assert time.monotonic() - started < 10.0

    def test_무엇의_상한인지_알린다(self, project_client: TestClient) -> None:
        data = b"bundle_version: 1\nfiller: " + b"x" * MAX_BUNDLE_BYTES
        assert _upload(project_client, data).json()["error"]["detail"]["kind"] == "bytes"

    def test_나눠_보내라고_안내한다(self, project_client: TestClient) -> None:
        data = b"bundle_version: 1\nfiller: " + b"x" * MAX_BUNDLE_BYTES
        body = _upload(project_client, data).json()["error"]
        assert body["next_action"]


class CountLimitTests:
    """바이트를 통과해도 건수로 다시 막는다. 둘은 다른 것을 잰다."""

    def test_테스트가_너무_많으면_거절한다(self, project_client: TestClient) -> None:
        entries = "\n".join(
            f"- dsl_version: 1\n  id: TC-{i % 999 + 1:03d}\n  name: t{i}\n"
            f"  authoring_mode: record\n  start_url: https://x.test\n"
            f"  steps: [{{id: s1, label: l, type: click, target: {{tag: b, "
            f"css: {{value: '#x', status: verified}}}}}}]"
            for i in range(MAX_BUNDLE_TESTS + 1)
        )
        data = f"bundle_version: 1\ncreated_at: 2026-09-23T00:00:00Z\ntests:\n{entries}\n"
        resp = _upload(project_client, data.encode("utf-8"))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_TOO_LARGE"
        assert resp.json()["error"]["detail"]["kind"] == "tests"

    def test_그룹이_너무_많으면_거절한다(self, project_client: TestClient) -> None:
        groups = "\n".join(
            f"  - prefix: G{i:03d}\n    name: 그룹{i}" for i in range(MAX_BUNDLE_GROUPS + 1)
        )
        data = (
            "bundle_version: 1\ncreated_at: 2026-09-23T00:00:00Z\n"
            "project:\n  name: p\n  default_start_url: https://x.test\n"
            f"  groups:\n{groups}\n"
            "tests: []\n"
        )
        resp = _upload(project_client, data.encode("utf-8"))
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_TOO_LARGE"
        assert resp.json()["error"]["detail"]["kind"] == "groups"

    def test_상한을_넘어도_아무것도_만들어지지_않는다(self, project_client: TestClient) -> None:
        from itb.storage.paths import workspace_dir

        before = {p.name for p in workspace_dir().iterdir()} if workspace_dir().exists() else set()
        _upload(project_client, b"bundle_version: 1\nfiller: " + b"x" * MAX_BUNDLE_BYTES)
        after = {p.name for p in workspace_dir().iterdir()} if workspace_dir().exists() else set()
        assert after == before
