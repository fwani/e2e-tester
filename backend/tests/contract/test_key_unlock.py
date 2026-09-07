"""암호구로 잠긴 비밀키를 **화면에서** 연다 (FR-089e-3).

사용자가 겪은 것: 키 관리 화면에서 암호구를 입력해 키를 만들고 민감 값을 저장했는데,
실행하면 "이 비밀키는 암호구로 보호되어 있습니다. 백엔드 프로세스에 환경 변수
``ITB_KEY_PASSPHRASE`` 로 암호구를 공급하거나…" 로 실패했다.

화면이 방금 받은 암호구를 화면이 쓰지 못한 것이다. 조작할 수 있는 곳이 조작을 안내하지
않고 셸을 안내하면, 사용자는 제품 밖으로 나가 같은 값을 다시 입력하고 백엔드를 재기동해야
한다 (UX U-26).

이 파일이 고정하는 것은 네 가지다.

1. 생성·교체 시점의 암호구는 **그 자리에서** 실행에 쓸 수 있다 (재기동 없이)
2. 잠긴 키는 화면에서 열 수 있고, 틀린 암호구는 그 자리에서 거절된다
3. 옛 암호구가 새 키에 남지 않는다
4. 암호구는 **어떤 응답에도** 담기지 않는다
"""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from itb.secrets.keys import KeyPaths, load_private_or_reason
from itb.secrets.store import SecretStore

PASSPHRASE = "correct-horse-battery"
OTHER = "brand-new-passphrase"


def _generate(client: TestClient, passphrase: str | None) -> dict:
    r = client.post("/api/keys/generate", json={"passphrase": passphrase})
    assert r.status_code == 201, r.text
    return r.json()


def _regenerate(client: TestClient, passphrase: str | None) -> dict:
    r = client.post(
        "/api/keys/regenerate", json={"confirm": "DELETE", "passphrase": passphrase}
    )
    assert r.status_code == 201, r.text
    return r.json()["status"]


def test_generated_key_is_usable_without_restarting_the_backend(
    client: TestClient,
) -> None:
    """**이것이 결함의 핵심이다.** 만든 직후에 쓸 수 없으면 화면이 받은 의미가 없다."""
    status = _generate(client, PASSPHRASE)

    assert status["passphrase_protected"] is True
    assert status["unlocked"] is True, (
        "화면에서 암호구를 입력해 만든 키가 잠긴 채로 남았다 — 사용자는 같은 값을 셸에 "
        "다시 넣고 백엔드를 재기동해야 한다"
    )
    # 다음 요청에서도 유지된다. 요청 수명에 두면 여기서 무너진다.
    assert client.get("/api/keys/status").json()["unlocked"] is True


def test_key_without_passphrase_is_never_reported_as_locked(client: TestClient) -> None:
    """열 것이 없는 키를 「잠김」 으로 말하면 사용자는 없는 암호구를 찾는다."""
    status = _generate(client, None)

    assert status["passphrase_protected"] is False
    assert status["unlocked"] is True


def test_locking_then_unlocking_from_the_screen(client: TestClient) -> None:
    _generate(client, PASSPHRASE)

    locked = client.delete("/api/keys/unlock")
    assert locked.status_code == 200, locked.text
    assert locked.json()["unlocked"] is False

    opened = client.post("/api/keys/unlock", json={"passphrase": PASSPHRASE})
    assert opened.status_code == 200, opened.text
    assert opened.json()["unlocked"] is True


def test_locking_twice_is_not_an_error(client: TestClient) -> None:
    """잠긴 것을 다시 잠그라는 요청의 결과는 「잠겨 있음」 이다.

    오류로 만들면 화면이 상태를 먼저 확인해야 하는 순서 의존이 생긴다.
    """
    _generate(client, PASSPHRASE)
    client.delete("/api/keys/unlock")

    again = client.delete("/api/keys/unlock")
    assert again.status_code == 200
    assert again.json()["unlocked"] is False


def test_wrong_passphrase_is_rejected_and_does_not_take_hold(client: TestClient) -> None:
    """틀린 암호구가 조용히 들어앉으면 사용자는 해제된 줄 알다가 실행 중에 실패를 본다."""
    _generate(client, PASSPHRASE)
    client.delete("/api/keys/unlock")

    r = client.post("/api/keys/unlock", json={"passphrase": "wrong-passphrase"})
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "PASSPHRASE_INVALID", (
        "암호구 오류를 복호화 실패와 같은 코드로 내면 조치가 달라지는 두 상황이 "
        "한 문구로 보고된다 (FR-089e-2)"
    )
    assert client.get("/api/keys/status").json()["unlocked"] is False


def test_unlocking_without_a_key_says_the_key_is_missing(client: TestClient) -> None:
    """키가 없는 것과 암호구가 틀린 것은 조치가 다르다."""
    r = client.post("/api/keys/unlock", json={"passphrase": PASSPHRASE})

    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "KEY_MISSING"


def test_short_passphrase_is_rejected_before_the_kdf_runs(client: TestClient) -> None:
    """생성 제약(8자)과 같은 값이어야 한다. 다르면 만들 수는 있는데 열 수 없는 값이 생긴다."""
    _generate(client, PASSPHRASE)

    r = client.post("/api/keys/unlock", json={"passphrase": "short"})
    assert r.status_code == 422, r.text


def test_regenerating_forgets_the_old_passphrase(client: TestClient) -> None:
    """옛 암호구가 남으면 새 키에 그것을 시도해 「암호구가 올바르지 않습니다」 로 헤맨다.

    사용자는 방금 새 암호구를 입력했으므로 원인을 찾을 수 없다.
    """
    _generate(client, PASSPHRASE)
    status = _regenerate(client, OTHER)

    assert status["unlocked"] is True, "새로 입력한 암호구가 그 자리에서 쓰이지 않았다"
    client.delete("/api/keys/unlock")
    assert client.post("/api/keys/unlock", json={"passphrase": PASSPHRASE}).status_code == 400
    assert client.post("/api/keys/unlock", json={"passphrase": OTHER}).status_code == 200


def test_regenerating_without_a_passphrase_clears_the_lock_state(
    client: TestClient,
) -> None:
    """암호구를 없애는 교체다. 들고 있던 값을 남기면 상태 표시가 거짓이 된다."""
    _generate(client, PASSPHRASE)
    status = _regenerate(client, None)

    assert status["passphrase_protected"] is False
    assert status["unlocked"] is True


def test_no_response_ever_carries_the_passphrase(client: TestClient) -> None:
    """**응답에 담기지 않는다.** 담기면 브라우저 개발자 도구와 프록시 로그에 남는다."""
    bodies = [
        client.post("/api/keys/generate", json={"passphrase": PASSPHRASE}).text,
        client.get("/api/keys/status").text,
        client.post("/api/keys/unlock", json={"passphrase": PASSPHRASE}).text,
        client.delete("/api/keys/unlock").text,
        client.get("/api/keys/permission-check").text,
    ]
    for body in bodies:
        assert PASSPHRASE not in body, f"암호구가 응답에 새어 나왔다: {body[:120]}"


def test_unlocked_key_actually_decrypts_a_stored_secret(
    client: TestClient, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """실행 시점 경로까지 이어지는지 본다 — 상태 표시만 맞고 복호화가 안 되면 의미가 없다.

    `sessions.py` 가 조립하는 것과 같은 호출이다 (`load_private_or_reason` 에 들고 있는
    암호구를 넘긴다). 브라우저 없이 그 이음매만 확인한다.
    """
    monkeypatch.delenv("ITB_KEY_PASSPHRASE", raising=False)
    _generate(client, PASSPHRASE)

    key_paths = KeyPaths(pathlib.Path(client.get("/api/keys/status").json()["key_dir"]))
    unlock = client.app.state.itb.key_unlock  # type: ignore[attr-defined]

    store = SecretStore(tmp_path / "secrets.local.yaml")
    from itb.secrets.keys import load_public

    store.put("SECRET_VALUE_1", "hunter2", load_public(key_paths))

    private, reason = load_private_or_reason(key_paths, unlock.passphrase)
    assert private is not None, f"열려 있다고 했는데 비밀키를 열지 못했다: {reason}"
    assert store.get("SECRET_VALUE_1", private) == "hunter2"

    # 다시 잠그면 같은 경로가 **사유와 함께** 막힌다 — 빈 값으로 진행하지 않는다.
    client.delete("/api/keys/unlock")
    unlock = client.app.state.itb.key_unlock  # type: ignore[attr-defined]
    private, reason = load_private_or_reason(key_paths, unlock.passphrase)
    assert private is None
    assert reason is not None and "잠겨" in reason
