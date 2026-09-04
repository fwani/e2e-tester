"""T047·T048 — 프로젝트·테스트 API 계약 (contracts/rest-api.md).

브라우저를 띄우지 않는다 — 계약 형태만 본다. 오류 응답이 계약의 공통 형태를 지키는지,
경계 검증이 실제로 거절하는지 확인한다.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tests.conftest import pin_playwright_browsers

from itb.api.app import create_app
from itb.secrets.keys import KeyPaths

CLOSE_TAB = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]


@pytest.fixture
def client(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """이 파일은 conftest 의 `client` 를 덮으므로 홈 격리를 여기에도 둔다.

    002 부터 프로젝트가 `~/.local/share/itb/projects/` 에 만들어진다 (DR-006).
    격리하지 않으면 계약 테스트가 개발자의 실제 홈에 프로젝트를 남긴다.
    """
    pin_playwright_browsers(monkeypatch)
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    with TestClient(create_app()) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        yield c


@pytest.fixture
def opened(client: TestClient) -> TestClient:
    """`path` 를 보내지 않는다 — 002 에서 제거됐다 (DR-001)."""
    resp = client.post(
        "/api/project/create",
        json={
            "name": "계약 프로젝트",
            "default_start_url": "http://127.0.0.1:4300/login.html",
        },
    )
    assert resp.status_code == 201, resp.text
    return client


def _project_root(client: TestClient) -> pathlib.Path:
    """열린 프로젝트의 실제 위치. 002 부터 도구가 정하므로 테스트가 가정할 수 없다."""
    return pathlib.Path(client.get("/api/project").json()["root"])


def _write_test(client: TestClient, tmp_path: pathlib.Path, test_id: str, name: str) -> None:
    """정의 파일을 직접 써서 목록 API 를 검증한다 (브라우저 불필요)."""
    from itb.domain.test_case import Test
    from itb.storage.repository import ProjectRepository

    repo = ProjectRepository.open(_project_root(client))
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
    # 002 — 사용자가 위치를 정하지 않는다. 도구가 관리하는 위치에 만들고 그 위치를
    # 응답으로 알려 준다 (DR-006). 어디에 만들어졌는지가 사용자에게 보여야 한다.
    root = pathlib.Path(body["root"])
    assert root.is_dir()
    assert (tmp_path / "home" / ".local" / "share" / "itb" / "projects") in root.parents


def test_create_with_duplicate_name_allocates_a_new_location(opened: TestClient) -> None:
    """같은 이름을 다시 만들면 **실패하지 않고** 옆자리에 만든다.

    001 에서는 `PROJECT_ALREADY_EXISTS` 로 거절했다. 그때는 사용자가 경로를 직접
    줬으므로 "그 자리에 이미 있다" 가 사용자가 고칠 수 있는 정보였다. 002 는 위치를
    묻지 않으므로(DR-001) 위치 충돌로 실패시키면 사용자가 할 수 있는 일이 없다.
    이름이 겹치면 `-2`·`-3` 을 붙인다 (contracts/rest-api-delta.md §2).
    """
    first = opened.get("/api/project").json()["root"]

    resp = opened.post(
        "/api/project/create",
        json={"name": "계약 프로젝트", "default_start_url": "http://127.0.0.1:4300/"},
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["root"] != first, "같은 디렉터리를 덮어썼다"


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "javascript:alert(1)", "ftp://x/", "not-a-url"]
)
def test_create_rejects_non_http_start_url(
    client: TestClient, tmp_path: pathlib.Path, url: str
) -> None:
    """FR-085 — 경계에서 스킴을 검증한다."""
    resp = client.post(
        "/api/project/create",
        json={"name": "x", "default_start_url": url},
    )
    assert resp.status_code == 422, resp.text


def test_create_rejects_path_field(client: TestClient) -> None:
    """`path` 는 002 에서 제거됐다 (DR-001·SC-102).

    사용자가 서버의 실행 경로를 알 방법이 없어 아무도 올바른 값을 넣을 수 없었다.
    필드를 남겨 두면 화면이 다시 그것을 묻게 되므로 경계에서 거절한다.
    """
    resp = client.post(
        "/api/project/create",
        json={
            "path": "/anywhere",
            "name": "x",
            "default_start_url": "http://127.0.0.1:4300/",
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["detail"]["fields"][0]["loc"] == "path"


def test_open_missing_project(client: TestClient, tmp_path: pathlib.Path) -> None:
    """홈 안이지만 프로젝트가 아닌 경로 — 무엇이 없어서 못 여는지 알려야 한다 (DR-008)."""
    inside = tmp_path / "home" / "nope"
    resp = client.post("/api/project/open", json={"path": str(inside)})

    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert "itb-project.yaml" in resp.json()["error"]["message"]


def test_open_outside_home_is_rejected(client: TestClient) -> None:
    """탐색·열기를 사용자 홈 아래로 한정한다 (헌법 보안 요구 · research R4)."""
    resp = client.post("/api/project/open", json={"path": "/etc"})

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "INVALID_PATH"


def test_unknown_field_is_rejected(client: TestClient, tmp_path: pathlib.Path) -> None:
    """extra="forbid" 가 API 경계에서도 동작한다."""
    resp = client.post(
        "/api/project/create",
        json={
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
    (_project_root(opened) / "tests" / "TC-002-broken.yaml").write_text(
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
