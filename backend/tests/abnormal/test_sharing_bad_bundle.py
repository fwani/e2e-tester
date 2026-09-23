"""019 T032·T033 (C3·C4·C5) — 나쁜 파일을 받았을 때.

세 경우 모두 **디스크가 그대로여야 한다** (FR-023·FR-030 · SC-006). 부분 복원을 시도하면
실행되지 않는 테스트가 조용히 만들어지고, 사용자는 그것이 언제 들어왔는지 알 수 없다.
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient
from sharing_support import PLAN, export_bundle, make_test, write_tests

from itb.storage.paths import workspace_dir

ALIAS_BOMB = b"""\
bundle_version: 1
a: &a ["x","x","x","x","x","x","x","x","x"]
b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]
d: &d [*c,*c,*c,*c,*c,*c,*c,*c,*c]
e: &e [*d,*d,*d,*d,*d,*d,*d,*d,*d]
f: &f [*e,*e,*e,*e,*e,*e,*e,*e,*e]
g: &g [*f,*f,*f,*f,*f,*f,*f,*f,*f]
h: [*g,*g,*g,*g,*g,*g,*g,*g,*g]
"""


UNKNOWN_STEP_TYPE = "type: 알수없음".encode()
"""이 도구가 모르는 스텝 종류. 손으로 편집된 묶음의 모양이다."""


def _projects() -> set[str]:
    root = workspace_dir()
    return {p.name for p in root.iterdir()} if root.exists() else set()


def _upload(client: TestClient, data: bytes, name: str = "bad.itbshare.yaml"):
    return client.post(
        f"{PLAN}?target=new",
        files={"file": (name, data, "application/yaml")},
    )


class CorruptBundleTests:
    """C3 — 손상된 파일은 거절하고, 그 뒤 디스크가 그대로다."""

    def test_깨진_YAML_을_거절한다(self, project_client: TestClient) -> None:
        resp = _upload(project_client, b"bundle_version: [\n  broken")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_MALFORMED"

    def test_거절_후_아무것도_만들어지지_않는다(self, project_client: TestClient) -> None:
        before = _projects()
        _upload(project_client, b"bundle_version: [\n  broken")
        assert _projects() == before

    def test_이_도구가_만들지_않은_파일을_거절한다(self, project_client: TestClient) -> None:
        resp = _upload(project_client, b"- just\n- a\n- list\n")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_MALFORMED"

    def test_전송_중_손상된_바이트를_거절한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = bytearray(export_bundle(project_client))
        data[len(data) // 2] = 0xFF  # UTF-8 로 읽히지 않는 바이트
        resp = _upload(project_client, bytes(data))
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_MALFORMED"

    def test_사용자가_할_일을_알려준다(self, project_client: TestClient) -> None:
        body = _upload(project_client, b"bundle_version: [\n").json()["error"]
        assert body["category"] == "blocked"
        assert body["next_action"]


class UnsupportedVersionTests:
    """C4 — 읽을 수 없는 형식 버전. **부분 복원을 시도하지 않는다.**"""

    def test_더_새로운_형식을_거절한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client).replace(b"bundle_version: 1", b"bundle_version: 99")
        resp = _upload(project_client, data)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_UNSUPPORTED_VERSION"

    def test_거절_후_아무것도_만들어지지_않는다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client).replace(b"bundle_version: 1", b"bundle_version: 99")
        before = _projects()
        _upload(project_client, data)
        assert _projects() == before

    def test_도구를_올리라고_안내한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client).replace(b"bundle_version: 1", b"bundle_version: 99")
        message = _upload(project_client, data).json()["error"]["message"]
        assert "99" in message


class AliasBombTests:
    """C5 — YAML 별칭 폭탄. **전개 없이 즉시** 거절한다 (research R4)."""

    def test_별칭을_쓴_파일을_거절한다(self, project_client: TestClient) -> None:
        resp = _upload(project_client, ALIAS_BOMB)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_MALFORMED"

    def test_전개하지_않고_즉시_끝난다(self, project_client: TestClient) -> None:
        """전개하면 9^8 ≈ 4,300만 개의 문자열이 만들어진다. 시간으로 드러난다."""
        started = time.monotonic()
        _upload(project_client, ALIAS_BOMB)
        assert time.monotonic() - started < 2.0

    def test_별칭을_썼다는_사실을_말한다(self, project_client: TestClient) -> None:
        message = _upload(project_client, ALIAS_BOMB).json()["error"]["message"]
        assert "별칭" in message


class InvalidTestDefinitionTests:
    """정의가 검증에 실패하면 **전체**를 거부한다 (FR-023·FR-024)."""

    def test_모르는_스텝_종류를_거절한다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client).replace(b"type: fill", UNKNOWN_STEP_TYPE, 1)
        resp = _upload(project_client, data)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SHARE_BUNDLE_INVALID_TEST"

    def test_어느_테스트의_무엇인지_말한다(self, project_client: TestClient) -> None:
        """「읽을 수 없다」만으로는 사용자가 보낸 사람에게 무엇을 물어야 할지 모른다."""
        write_tests(project_client, make_test("TC-001", "로그인"))
        data = export_bundle(project_client).replace(b"type: fill", UNKNOWN_STEP_TYPE, 1)
        problems = _upload(project_client, data).json()["error"]["detail"]["problems"]
        assert problems
        assert any("TC-001" in p for p in problems)

    def test_한_건이_깨져도_전체가_들어오지_않는다(self, project_client: TestClient) -> None:
        write_tests(project_client, make_test("TC-001", "가"), make_test("TC-002", "나"))
        data = export_bundle(project_client).replace(b"type: fill", UNKNOWN_STEP_TYPE, 1)
        before = _projects()
        _upload(project_client, data)
        assert _projects() == before
