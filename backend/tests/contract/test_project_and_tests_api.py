"""T047·T048 — 프로젝트·테스트 API 계약 (contracts/rest-api.md).

브라우저를 띄우지 않는다 — 계약 형태만 본다. 오류 응답이 계약의 공통 형태를 지키는지,
경계 검증이 실제로 거절하는지 확인한다.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from itb.api.app import create_app
from itb.secrets.keys import KeyPaths

CLOSE_TAB = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]


@pytest.fixture
def client(tmp_path: pathlib.Path) -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        yield c


@pytest.fixture
def opened(client: TestClient, tmp_path: pathlib.Path) -> TestClient:
    resp = client.post(
        "/api/project/create",
        json={
            "path": str(tmp_path / "proj"),
            "name": "계약 프로젝트",
            "default_start_url": "http://127.0.0.1:4300/login.html",
        },
    )
    assert resp.status_code == 201, resp.text
    return client


def _write_test(client: TestClient, tmp_path: pathlib.Path, test_id: str, name: str) -> None:
    """정의 파일을 직접 써서 목록 API 를 검증한다 (브라우저 불필요)."""
    from itb.domain.test_case import Test
    from itb.storage.repository import ProjectRepository

    repo = ProjectRepository.open(tmp_path / "proj")
    repo.write_test(
        Test(
            id=test_id,
            name=name,
            authoring_mode="record",
            start_url="http://127.0.0.1:4300/login.html",
            steps=CLOSE_TAB,
        )
    )


# ─── 오류 응답 공통 형태 ────────────────────────────────────────────────────


def test_error_shape_is_contract_compliant(client: TestClient) -> None:
    resp = client.get("/api/project")
    assert resp.status_code == 404
    body = resp.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "detail"}
    assert body["error"]["code"] == "PROJECT_NOT_OPEN"
    assert body["error"]["message"]


def test_operations_without_project_are_rejected(client: TestClient) -> None:
    for method, path in (
        ("get", "/api/tests"),
        ("get", "/api/tests/TC-001"),
        ("get", "/api/secrets"),
    ):
        resp = getattr(client, method)(path)
        assert resp.status_code in (400, 404), (path, resp.status_code)
        assert resp.json()["error"]["code"] == "PROJECT_NOT_OPEN"


# ─── 프로젝트 (FR-001·FR-085) ──────────────────────────────────────────────


def test_create_then_get_project(opened: TestClient, tmp_path: pathlib.Path) -> None:
    body = opened.get("/api/project").json()
    assert body["name"] == "계약 프로젝트"
    assert body["gitignore_present"] is True
    assert pathlib.Path(body["root"]) == (tmp_path / "proj").resolve()


def test_create_rejects_duplicate(opened: TestClient, tmp_path: pathlib.Path) -> None:
    resp = opened.post(
        "/api/project/create",
        json={
            "path": str(tmp_path / "proj"),
            "name": "중복",
            "default_start_url": "http://127.0.0.1:4300/",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "PROJECT_ALREADY_EXISTS"


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "javascript:alert(1)", "ftp://x/", "not-a-url"]
)
def test_create_rejects_non_http_start_url(
    client: TestClient, tmp_path: pathlib.Path, url: str
) -> None:
    """FR-085 — 경계에서 스킴을 검증한다."""
    resp = client.post(
        "/api/project/create",
        json={"path": str(tmp_path / "p2"), "name": "x", "default_start_url": url},
    )
    assert resp.status_code == 422, resp.text


def test_create_rejects_relative_path(client: TestClient) -> None:
    resp = client.post(
        "/api/project/create",
        json={
            "path": "relative/dir",
            "name": "x",
            "default_start_url": "http://127.0.0.1:4300/",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVALID_PATH"


def test_open_missing_project(client: TestClient, tmp_path: pathlib.Path) -> None:
    resp = client.post("/api/project/open", json={"path": str(tmp_path / "nope")})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_unknown_field_is_rejected(client: TestClient, tmp_path: pathlib.Path) -> None:
    """extra="forbid" 가 API 경계에서도 동작한다."""
    resp = client.post(
        "/api/project/create",
        json={
            "path": str(tmp_path / "p3"),
            "name": "x",
            "default_start_url": "http://127.0.0.1:4300/",
            "typo_field": 1,
        },
    )
    assert resp.status_code == 422


# ─── 테스트 목록 (FR-002~FR-006) ───────────────────────────────────────────


def test_empty_list_has_zero_counts(opened: TestClient) -> None:
    body = opened.get("/api/tests").json()
    assert body["counts"] == {"total": 0, "pass": 0, "fail": 0}
    assert body["tests"] == []
    assert body["problems"] == []


def test_list_reports_rows_and_counts(opened: TestClient, tmp_path: pathlib.Path) -> None:
    _write_test(opened, tmp_path, "TC-001", "프로젝트 생성")
    _write_test(opened, tmp_path, "TC-002", "프로젝트 삭제")
    body = opened.get("/api/tests").json()
    assert body["counts"]["total"] == 2
    assert [t["id"] for t in body["tests"]] == ["TC-001", "TC-002"]
    assert body["tests"][0]["step_count"] == 1
    assert body["tests"][0]["authoring_mode"] == "record"
    assert body["tests"][0]["outcome"] is None  # 미실행


def test_list_search_filters_by_name_and_id(
    opened: TestClient, tmp_path: pathlib.Path
) -> None:
    _write_test(opened, tmp_path, "TC-001", "프로젝트 생성")
    _write_test(opened, tmp_path, "TC-002", "데이터 업로드")

    by_name = opened.get("/api/tests", params={"q": "데이터"}).json()
    assert [t["id"] for t in by_name["tests"]] == ["TC-002"]

    by_id = opened.get("/api/tests", params={"q": "tc-001"}).json()
    assert [t["id"] for t in by_id["tests"]] == ["TC-001"]


def test_list_surfaces_broken_definition_without_hiding_others(
    opened: TestClient, tmp_path: pathlib.Path
) -> None:
    """깨진 파일 하나가 목록 전체를 막지 않는다."""
    _write_test(opened, tmp_path, "TC-001", "정상")
    (tmp_path / "proj" / "tests" / "TC-002-broken.yaml").write_text(
        "steps: []\n", encoding="utf-8"
    )
    body = opened.get("/api/tests").json()
    assert [t["id"] for t in body["tests"]] == ["TC-001"]
    assert len(body["problems"]) == 1
    assert "TC-002-broken.yaml" in body["problems"][0]


def test_get_rename_delete_roundtrip(opened: TestClient, tmp_path: pathlib.Path) -> None:
    _write_test(opened, tmp_path, "TC-001", "원래 이름")

    got = opened.get("/api/tests/TC-001").json()
    assert got["name"] == "원래 이름"
    assert got["dsl_version"] == 1

    renamed = opened.patch("/api/tests/TC-001", json={"name": "새 이름"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "새 이름"

    assert opened.delete("/api/tests/TC-001").status_code == 204
    assert opened.get("/api/tests/TC-001").status_code == 404


def test_delete_unknown_test(opened: TestClient) -> None:
    resp = opened.delete("/api/tests/TC-404")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"


def test_result_missing(opened: TestClient, tmp_path: pathlib.Path) -> None:
    _write_test(opened, tmp_path, "TC-001", "x")
    resp = opened.get("/api/tests/TC-001/result")
    assert resp.status_code == 404


def test_trace_artifact_is_not_implemented(opened: TestClient, tmp_path: pathlib.Path) -> None:
    """spec 디자인 차이 1 — TRACE 탭은 MVP 미지원이며 비활성으로 표시한다."""
    _write_test(opened, tmp_path, "TC-001", "x")
    resp = opened.get("/api/tests/TC-001/result/artifacts/trace")
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "NOT_SUPPORTED"


def test_unknown_artifact_kind_is_rejected(opened: TestClient, tmp_path: pathlib.Path) -> None:
    _write_test(opened, tmp_path, "TC-001", "x")
    assert opened.get("/api/tests/TC-001/result/artifacts/video").status_code == 422


# ─── 비밀 값·키 (FR-089) — 값이 절대 나오지 않는다 ────────────────────────


def test_key_status_before_generation(opened: TestClient) -> None:
    body = opened.get("/api/keys/status").json()
    assert body["private_key_present"] is False
    assert body["public_key_fingerprint"] is None


def test_generate_then_put_secret_without_private_key(opened: TestClient) -> None:
    """FR-089b — 봉인은 공개키만으로 가능하다. 응답에 값이 없다."""
    gen = opened.post("/api/keys/generate", json={})
    assert gen.status_code == 201
    assert gen.json()["public_key_fingerprint"].startswith("SHA256:")

    secret = "not-a-real-secret-abc123"
    put = opened.put("/api/secrets/LOGIN_PASSWORD", json={"value": secret})
    assert put.status_code == 204
    assert secret not in put.text

    listing = opened.get("/api/secrets")
    assert secret not in listing.text, "목록 응답에 평문이 들어갔다"
    assert listing.json()["names"] == [{"name": "LOGIN_PASSWORD", "present": True}]
    assert listing.json()["fingerprint_matches_key"] is True


def test_generate_twice_conflicts(opened: TestClient) -> None:
    opened.post("/api/keys/generate", json={})
    resp = opened.post("/api/keys/generate", json={})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "KEY_ALREADY_EXISTS"


def test_put_secret_without_key_is_rejected(opened: TestClient) -> None:
    resp = opened.put("/api/secrets/LOGIN_PASSWORD", json={"value": "x"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "KEY_MISSING"


@pytest.mark.parametrize("name", ["lower", "has-dash", "1START", "has space"])
def test_put_secret_rejects_bad_variable_name(opened: TestClient, name: str) -> None:
    opened.post("/api/keys/generate", json={})
    resp = opened.put(f"/api/secrets/{name}", json={"value": "x"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_delete_unknown_secret(opened: TestClient) -> None:
    resp = opened.delete("/api/secrets/NOPE")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SECRET_NOT_FOUND"


# ─── 세션 (FR-043) ─────────────────────────────────────────────────────────


def test_unknown_session(opened: TestClient) -> None:
    resp = opened.get("/api/sessions/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_replay_session_requires_test_id(opened: TestClient) -> None:
    resp = opened.post("/api/sessions", json={"mode": "replay"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_ai_session_requires_instruction(opened: TestClient) -> None:
    resp = opened.post("/api/sessions", json={"mode": "ai"})
    assert resp.status_code == 400


def test_invalid_mode_is_rejected(opened: TestClient) -> None:
    assert opened.post("/api/sessions", json={"mode": "telepathy"}).status_code == 422


def test_replay_of_missing_test(opened: TestClient) -> None:
    resp = opened.post("/api/sessions", json={"mode": "replay", "test_id": "TC-404"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"


def test_health_reports_local_binding(client: TestClient) -> None:
    """FR-088a — 로컬 인터페이스에만 바인딩한다."""
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["bind"].startswith("127.0.0.1:")
