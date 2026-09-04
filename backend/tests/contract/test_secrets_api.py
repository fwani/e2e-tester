"""비밀 값·키 API 계약. FR-089a~c·SC-010 (T148). contracts/rest-api.md §비밀 값과 키.

**계약의 핵심은 부재다**: 복호화된 값을 돌려주는 엔드포인트가 하나도 없다. 그래서 이
테스트는 "무엇이 오는가" 만큼 "무엇이 오지 않는가" 를 본다 — 어떤 응답에도 값이 없다.

두 번째 계약은 **비대칭성**이다. `PUT` 은 공개키만으로 성공한다 (FR-089b). 값을 넣는
사람이 비밀키를 갖고 있을 필요가 없다는 것이 이 방식을 택한 실질적 이득이다.
"""

from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

SECRET_VALUE = "put-only-not-a-real-secret-9f3a"


def _generate_key(client: TestClient) -> None:
    resp = client.post("/api/keys/generate", json={"passphrase": None})
    assert resp.status_code == 201, resp.text


def test_no_endpoint_returns_a_decrypted_value(
    project_client: TestClient, tmp_path: pathlib.Path
) -> None:
    """**어떤 응답에도 값이 없다** (SC-010).

    값을 넣은 뒤 읽기 계열 엔드포인트를 전수로 훑는다. 하나라도 값을 흘리면 실패한다.
    """
    _generate_key(project_client)
    put = project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})
    assert put.status_code == 204, put.text
    assert SECRET_VALUE not in put.text

    for path in (
        "/api/secrets",
        "/api/keys/status",
        "/api/keys/permission-check",
        "/api/health",
    ):
        resp = project_client.get(path)
        assert resp.status_code == 200, f"{path} → {resp.text}"
        assert SECRET_VALUE not in resp.text, f"{path} 응답에 평문이 있다"


def test_list_returns_names_and_presence_only(project_client: TestClient) -> None:
    """FR-089c — 이름과 존재 여부만. 값을 담는 필드가 아예 없다."""
    _generate_key(project_client)
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})

    body = project_client.get("/api/secrets").json()
    assert set(body) == {"public_key_fingerprint", "fingerprint_matches_key", "names"}
    assert body["names"] == [{"name": "LOGIN_PASSWORD", "present": True}]
    assert body["fingerprint_matches_key"] is True


def test_put_succeeds_without_a_private_key(
    project_client: TestClient, tmp_path: pathlib.Path
) -> None:
    """FR-089b — **공개키만으로 봉인한다.**

    비밀키 파일을 지운 뒤에도 값을 넣을 수 있어야 한다. 이것이 비대칭 방식을 택한 이유다.
    """
    _generate_key(project_client)
    private = project_client.app.state.itb.key_paths.private
    private.unlink()
    assert not private.exists()

    resp = project_client.put("/api/secrets/API_TOKEN", json={"value": SECRET_VALUE})
    assert resp.status_code == 204, resp.text
    assert "API_TOKEN" in [n["name"] for n in project_client.get("/api/secrets").json()["names"]]


def test_put_without_any_key_is_refused_with_guidance(
    project_client: TestClient,
) -> None:
    """키가 없으면 거절한다. **값을 버리지 않는다** — 사용자가 무엇을 할지 알아야 한다."""
    resp = project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})
    assert resp.status_code == 400, resp.text
    error = resp.json()["error"]
    assert error["code"] == "KEY_MISSING"
    assert "키" in error["message"]
    assert SECRET_VALUE not in resp.text


def test_variable_name_is_validated(project_client: TestClient) -> None:
    """FR-085 — 경계에서 검증한다. 변수 이름은 `[A-Z][A-Z0-9_]*` 다."""
    _generate_key(project_client)
    resp = project_client.put("/api/secrets/lower_case", json={"value": SECRET_VALUE})
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"


def test_ciphertext_lives_outside_the_definition_files(
    project_client: TestClient,
) -> None:
    """FR-089c — 암호문조차 정의 파일에 들어가지 않는다.

    비밀 파일은 `.gitignore` 대상이고 정의 파일은 커밋 대상이다. 둘이 섞이면 그 분리가
    무의미해진다 (FR-088b).
    """
    _generate_key(project_client)
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})

    repo = project_client.app.state.itb.repository
    secrets_file = repo.paths.secrets_file
    assert secrets_file.exists()
    content = secrets_file.read_text(encoding="utf-8")
    assert "LOGIN_PASSWORD" in content
    assert SECRET_VALUE not in content, "평문이 비밀 파일에 그대로 있다"

    gitignore = repo.paths.gitignore.read_text(encoding="utf-8")
    assert "secrets.local.yaml" in gitignore


def test_delete_removes_the_ciphertext(project_client: TestClient) -> None:
    _generate_key(project_client)
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})

    resp = project_client.delete("/api/secrets/LOGIN_PASSWORD")
    assert resp.status_code == 204, resp.text
    assert project_client.get("/api/secrets").json()["names"] == []

    missing = project_client.delete("/api/secrets/LOGIN_PASSWORD")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "SECRET_NOT_FOUND"


def test_key_generation_is_refused_twice(project_client: TestClient) -> None:
    """FR-089a — 이미 있으면 `409`.

    덮어쓰면 기존 암호문을 전부 읽을 수 없게 된다 — 되돌릴 수 없는 손실이다.
    """
    _generate_key(project_client)
    again = project_client.post("/api/keys/generate", json={"passphrase": None})
    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "KEY_ALREADY_EXISTS"


def test_key_status_reports_fingerprint_and_permission(
    project_client: TestClient,
) -> None:
    """FR-089a·FR-089e-1 — 지문과 권한 경고를 보고한다. 키 자체는 돌려주지 않는다."""
    before = project_client.get("/api/keys/status").json()
    assert before["private_key_present"] is False
    assert before["public_key_fingerprint"] is None

    _generate_key(project_client)
    after = project_client.get("/api/keys/status").json()
    assert after["private_key_present"] is True
    assert after["public_key_present"] is True
    assert after["public_key_fingerprint"].startswith("SHA256:")
    # 갓 만든 키는 0600 이므로 경고가 없다.
    assert after["permission_warning"] is None
    # 키 내용을 담는 필드가 없다.
    assert set(after) == {
        "private_key_present",
        "public_key_present",
        "passphrase_protected",
        "public_key_fingerprint",
        "permission_warning",
        # UX U-09 — 실제 경로와 영향 범위. 화면이 고정 문구 대신 이것을 찍는다.
        "key_dir",
        "sealed_projects",
    }


def test_fingerprint_mismatch_is_reported(project_client: TestClient) -> None:
    """spec 엣지 케이스 — 공개키가 교체되면 재입력이 필요함을 알린다.

    조용히 새 키로 덮어쓰면 기존 암호문이 읽히지 않는데 화면은 정상으로 보인다.
    """
    _generate_key(project_client)
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})

    # 키를 교체한다 (사용자가 키를 다시 만든 상황).
    paths = project_client.app.state.itb.key_paths
    paths.private.unlink()
    paths.public.unlink()
    _generate_key(project_client)

    body = project_client.get("/api/secrets").json()
    assert body["fingerprint_matches_key"] is False

    resp = project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "FINGERPRINT_MISMATCH"
    assert SECRET_VALUE not in resp.text


# ─── 002 — 키 쌍 생성 실패를 읽을 수 있게 (DR-028~DR-031) ──────────────────


def test_short_passphrase_is_rejected_in_contract_shape(client: TestClient) -> None:
    """사용자가 겪은 "422 에러" 의 실체.

    제약 자체는 유지한다 — 8자 미만 암호구절을 받아들이는 것은 개선이 아니다. 바뀌는
    것은 **알리는 방식**이다. 이전에는 FastAPI 기본 형태가 나가 프런트엔드가 읽지
    못했고, 사용자에게는 "요청이 실패했습니다 (422)." 한 문장만 남았다 (research R3).
    """
    resp = client.post("/api/keys/generate", json={"passphrase": "short"})

    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert "error" in body, f"계약 형태가 아니다: {body}"
    assert body["error"]["code"] == "DEFINITION_INVALID"
    assert "8자 이상" in body["error"]["message"], body["error"]["message"]
    assert "422" not in body["error"]["message"], "원시 상태 코드를 노출했다 (SC-107)"


def test_generate_without_passphrase_succeeds(client: TestClient) -> None:
    """DR-028 — 기본 경로가 성공한다."""
    resp = client.post("/api/keys/generate", json={"passphrase": None})

    assert resp.status_code == 201, resp.text
    assert resp.json()["private_key_present"] is True
    assert resp.json()["passphrase_protected"] is False


def test_generate_with_valid_passphrase_succeeds(client: TestClient) -> None:
    resp = client.post("/api/keys/generate", json={"passphrase": "long-enough-pass"})

    assert resp.status_code == 201, resp.text
    assert resp.json()["passphrase_protected"] is True


def test_duplicate_generate_is_readable(client: TestClient) -> None:
    """DR-030 — 이미 있다는 사실을 사람이 읽을 수 있는 문장으로."""
    client.post("/api/keys/generate", json={"passphrase": None})

    resp = client.post("/api/keys/generate", json={"passphrase": None})

    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "KEY_ALREADY_EXISTS"
    assert resp.json()["error"]["message"], "사유가 비어 있다"


def test_unwritable_key_directory_is_reported_not_crashed(
    client: TestClient, tmp_path: pathlib.Path
) -> None:
    """DR-030 — 권한 문제가 500 "예상하지 못한 오류" 로 나가면 조치할 수 없다."""
    from itb.secrets.keys import KeyPaths

    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    client.app.state.itb.key_paths = KeyPaths(locked / "keys")
    try:
        resp = client.post("/api/keys/generate", json={"passphrase": None})

        assert resp.status_code == 400, resp.text
        message = resp.json()["error"]["message"]
        assert "권한" in message or "확인" in message
    finally:
        locked.chmod(0o700)


# ─── 키 삭제·재생성 (DR-031) ────────────────────────────────────────────────


def test_destroy_requires_the_exact_confirm_phrase(project_client: TestClient) -> None:
    """되돌릴 수 없는 조작은 확인 문구 없이는 절대 진행하지 않는다."""
    _generate_key(project_client)

    resp = project_client.request("DELETE", "/api/keys", json={"confirm": "delete"})
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "DEFINITION_INVALID"
    # 거절했으면 키는 그대로 있어야 한다.
    assert project_client.get("/api/keys/status").json()["private_key_present"] is True


def test_destroy_removes_keys_and_purges_sealed_values(project_client: TestClient) -> None:
    """키를 지우면 읽을 수 없게 된 암호문도 함께 비운다.

    남기면 사용자는 값을 읽을 수도, 새 값을 넣을 수도 없는 상태에 갇힌다.
    """
    _generate_key(project_client)
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})

    resp = project_client.request("DELETE", "/api/keys", json={"confirm": "DELETE"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["purged_secret_count"] == 1
    assert body["project_open"] is True
    assert body["status"]["private_key_present"] is False
    assert body["status"]["public_key_present"] is False

    listed = project_client.get("/api/secrets").json()
    assert listed["names"] == []
    assert listed["public_key_fingerprint"] is None


def test_destroy_without_keys_is_not_found(project_client: TestClient) -> None:
    resp = project_client.request("DELETE", "/api/keys", json={"confirm": "DELETE"})
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "KEY_MISSING"


def test_regenerate_replaces_the_key_and_lets_values_be_re_entered(
    project_client: TestClient,
) -> None:
    """교체 뒤 **새 값 저장이 곧바로 된다.**

    지문만 남기고 값을 비우면 `PUT` 이 계속 409 로 거절한다 — 그 막다른 골목이 없는지
    본다. `generate` 는 여전히 덮어쓰지 않는다는 규칙도 함께 확인한다.
    """
    _generate_key(project_client)
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})
    before = project_client.get("/api/keys/status").json()["public_key_fingerprint"]

    resp = project_client.post("/api/keys/regenerate", json={"confirm": "DELETE"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["purged_secret_count"] == 1
    after = body["status"]["public_key_fingerprint"]
    assert after is not None
    assert after != before

    again = project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})
    assert again.status_code == 204, again.text
    assert project_client.post("/api/keys/generate", json={"passphrase": None}).status_code == 409


def test_regenerate_can_switch_passphrase_protection_on_and_off(
    project_client: TestClient,
) -> None:
    project_client.post("/api/keys/generate", json={"passphrase": "long-enough-phrase"})
    assert project_client.get("/api/keys/status").json()["passphrase_protected"] is True

    resp = project_client.post("/api/keys/regenerate", json={"confirm": "DELETE"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"]["passphrase_protected"] is False


def test_regenerate_works_before_a_key_exists(project_client: TestClient) -> None:
    """지울 것이 없어도 교체는 성공한다 — 사용자에겐 '키를 만든다' 와 같은 결과다."""
    resp = project_client.post("/api/keys/regenerate", json={"confirm": "DELETE"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"]["private_key_present"] is True


def test_destroy_and_regenerate_never_echo_a_value(project_client: TestClient) -> None:
    _generate_key(project_client)
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})

    regen = project_client.post("/api/keys/regenerate", json={"confirm": "DELETE"})
    assert SECRET_VALUE not in regen.text
    project_client.put("/api/secrets/LOGIN_PASSWORD", json={"value": SECRET_VALUE})
    destroyed = project_client.request("DELETE", "/api/keys", json={"confirm": "DELETE"})
    assert SECRET_VALUE not in destroyed.text
