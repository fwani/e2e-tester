"""T037 — 민감 값 처리 단위 테스트 (FR-082·FR-089a~g, SC-010·SC-011).

보안 요구사항이므로 성공 경로가 아니라 **실패 모드를 전수 확인**한다.
"""

from __future__ import annotations

import base64
import json
import pathlib
import urllib.parse
from collections.abc import Callable

import pytest

from itb.domain.test_case import Test
from itb.secrets.keys import (
    KeyMissingError,
    KeyPaths,
    KeyStoreError,
    PassphraseError,
    PassphraseRequiredError,
    fingerprint,
    generate,
    load_private,
    load_public,
    permission_warning,
    status,
)
from itb.secrets.resolver import VariableResolutionError, VariableResolver
from itb.secrets.scrubber import MASK, Scrubber
from itb.secrets.store import DecryptError, FingerprintMismatchError, SecretStore

SECRET_VALUE = "s3cr3t-passphrase-value"
CLOSE_TAB = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]


@pytest.fixture
def keys(tmp_path: pathlib.Path) -> KeyPaths:
    kp = KeyPaths(tmp_path / "keys")
    generate(kp)
    return kp


@pytest.fixture
def store(tmp_path: pathlib.Path) -> SecretStore:
    return SecretStore(tmp_path / "secrets.local.yaml")


def make_test(**overrides: object) -> Test:
    payload: dict[str, object] = {
        "id": "TC-001",
        "name": "로그인",
        "authoring_mode": "record",
        "start_url": "http://127.0.0.1:4300/login.html",
        "steps": CLOSE_TAB,
    }
    payload.update(overrides)
    return Test(**payload)  # type: ignore[arg-type]


# ─── 키 생성·권한 (FR-089a, FR-089e·e-1) ───────────────────────────────────


def test_generated_private_key_is_owner_only(keys: KeyPaths) -> None:
    assert keys.private.stat().st_mode & 0o777 == 0o600
    assert permission_warning(keys.private) is None


def test_permission_warning_when_group_readable(keys: KeyPaths) -> None:
    """FR-089e-1 — 권한이 열려 있으면 경고한다. 권한을 임의로 바꾸지 않는다."""
    keys.private.chmod(0o644)
    warning = permission_warning(keys.private)
    assert warning is not None
    assert "0644" in warning
    # 제품이 권한을 고치지 않았음을 확인한다
    assert keys.private.stat().st_mode & 0o777 == 0o644


def test_generate_refuses_to_overwrite(keys: KeyPaths) -> None:
    with pytest.raises(KeyStoreError, match="이미 존재"):
        generate(keys)


def test_status_does_not_expose_private_key(keys: KeyPaths) -> None:
    info = status(keys)
    flat = repr(info)
    assert keys.private.read_bytes().hex() not in flat
    assert info["private_key_present"] is True
    assert str(info["public_key_fingerprint"]).startswith("SHA256:")


# ─── 공개키만으로 봉인 (FR-089b) — 이 설계의 핵심 이점 ────────────────────


def test_sealing_needs_only_public_key(keys: KeyPaths, store: SecretStore) -> None:
    """녹화·작성 단계가 비밀키 없이 동작함을 보증한다."""
    public = load_public(keys)
    store.put("LOGIN_PASSWORD", SECRET_VALUE, public)
    assert store.has("LOGIN_PASSWORD")
    # 비밀키 파일을 지워도 봉인은 계속 가능하다
    keys.private.unlink()
    store.put("OTHER_SECRET", "another-value", public)
    assert store.names() == ["LOGIN_PASSWORD", "OTHER_SECRET"]


def test_roundtrip(keys: KeyPaths, store: SecretStore) -> None:
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(keys))
    assert store.get("LOGIN_PASSWORD", load_private(keys)) == SECRET_VALUE


def test_store_never_returns_plaintext_in_listing(keys: KeyPaths, store: SecretStore) -> None:
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(keys))
    assert SECRET_VALUE not in repr(store.names())
    assert SECRET_VALUE not in store.path.read_text(encoding="utf-8")


def test_stored_file_is_owner_only(keys: KeyPaths, store: SecretStore) -> None:
    store.put("A_SECRET", SECRET_VALUE, load_public(keys))
    assert store.path.stat().st_mode & 0o777 == 0o600


# ─── 실패 모드 (FR-089f, SC-011) ───────────────────────────────────────────


def test_missing_private_key_raises_clear_reason(tmp_path: pathlib.Path) -> None:
    with pytest.raises(KeyMissingError, match="비밀키가 없습니다"):
        load_private(KeyPaths(tmp_path / "nope"))


def test_missing_public_key_raises_clear_reason(tmp_path: pathlib.Path) -> None:
    with pytest.raises(KeyMissingError, match="공개키가 없습니다"):
        load_public(KeyPaths(tmp_path / "nope"))


def test_decrypt_with_wrong_key_fails(tmp_path: pathlib.Path, store: SecretStore) -> None:
    a = KeyPaths(tmp_path / "a")
    b = KeyPaths(tmp_path / "b")
    generate(a)
    generate(b)
    store.put("S", SECRET_VALUE, load_public(a))
    with pytest.raises(FingerprintMismatchError, match="지문"):
        store.get("S", load_private(b))


def test_corrupted_ciphertext_raises_decrypt_error(keys: KeyPaths, store: SecretStore) -> None:
    store.put("S", SECRET_VALUE, load_public(keys))
    raw = store.path.read_text(encoding="utf-8")
    store.path.write_text(raw.replace("S: ", "S: AAAA"), encoding="utf-8")
    reloaded = SecretStore(store.path)
    with pytest.raises(DecryptError, match="복호화에 실패"):
        reloaded.get("S", load_private(keys))


def test_public_key_rotation_is_detected(tmp_path: pathlib.Path, store: SecretStore) -> None:
    """공개키가 교체되면 재입력이 필요함을 알린다 (spec 엣지 케이스)."""
    a = KeyPaths(tmp_path / "a")
    b = KeyPaths(tmp_path / "b")
    generate(a)
    generate(b)
    store.put("S", SECRET_VALUE, load_public(a))
    assert store.matches_key(load_public(a))
    assert not store.matches_key(load_public(b))
    with pytest.raises(FingerprintMismatchError, match="다시 입력"):
        store.put("S2", "v", load_public(b))


def test_get_unknown_name(keys: KeyPaths, store: SecretStore) -> None:
    with pytest.raises(KeyStoreError, match="보관되어 있지 않"):
        store.get("NOPE", load_private(keys))


# ─── 암호구 (FR-089e-2) ────────────────────────────────────────────────────


def test_passphrase_protected_key_requires_passphrase(tmp_path: pathlib.Path) -> None:
    kp = KeyPaths(tmp_path / "k")
    generate(kp, passphrase="correct horse battery")
    assert status(kp)["passphrase_protected"] is True
    with pytest.raises(PassphraseRequiredError):
        load_private(kp)


def test_wrong_passphrase_is_distinguished_from_decrypt_failure(
    tmp_path: pathlib.Path,
) -> None:
    """조치가 다르므로 사유를 구분해야 한다 (FR-089e-2)."""
    kp = KeyPaths(tmp_path / "k")
    generate(kp, passphrase="correct horse battery")
    with pytest.raises(PassphraseError, match="암호구가 올바르지"):
        load_private(kp, passphrase="wrong")
    assert load_private(kp, passphrase="correct horse battery") is not None


def test_passphrase_given_for_unprotected_key(keys: KeyPaths) -> None:
    with pytest.raises(PassphraseError, match="보호되어 있지 않"):
        load_private(keys, passphrase="unnecessary")


def test_fingerprint_is_stable_and_key_specific(tmp_path: pathlib.Path) -> None:
    a = KeyPaths(tmp_path / "a")
    b = KeyPaths(tmp_path / "b")
    fa = generate(a)
    fb = generate(b)
    assert fa == fingerprint(load_public(a))
    assert fa != fb


# ─── 스크러버 (FR-089d, SC-010) ────────────────────────────────────────────


def test_scrubber_masks_plain_value() -> None:
    s = Scrubber([SECRET_VALUE])
    assert SECRET_VALUE not in s.scrub(f"로그인 실패: {SECRET_VALUE} 로 시도")
    assert MASK in s.scrub(f"x {SECRET_VALUE} y")


@pytest.mark.parametrize(
    "render",
    [
        pytest.param(lambda v: v, id="plain"),
        pytest.param(urllib.parse.quote, id="urlquote"),
        pytest.param(urllib.parse.quote_plus, id="urlquote_plus"),
        pytest.param(lambda v: json.dumps(v)[1:-1], id="json"),
        pytest.param(lambda v: base64.b64encode(v.encode()).decode(), id="base64"),
    ],
)
def test_scrubber_masks_encoded_forms(render: Callable[[str], str]) -> None:
    """대상 앱이 값을 인코딩해 로그·네트워크 기록에 남길 수 있다 (research R7)."""
    value = "p@ss w/ord+special"
    s = Scrubber([value])
    rendered = render(value)
    assert rendered not in s.scrub(f"payload={rendered}")


def test_scrubber_masks_substring_occurrence() -> None:
    s = Scrubber([SECRET_VALUE])
    assert SECRET_VALUE not in s.scrub(f"prefix{SECRET_VALUE}suffix")


def test_scrubber_handles_nested_structures() -> None:
    s = Scrubber([SECRET_VALUE])
    obj = {"body": {"password": SECRET_VALUE}, "list": [SECRET_VALUE, 1, None]}
    out = s.scrub_obj(obj)
    assert SECRET_VALUE not in repr(out)


def test_scrubber_masks_dict_keys() -> None:
    s = Scrubber([SECRET_VALUE])
    out = s.scrub_obj({SECRET_VALUE: "v"})
    assert SECRET_VALUE not in repr(out)


def test_scrubber_ignores_short_values() -> None:
    """너무 짧은 값을 마스킹하면 무관한 텍스트를 대량으로 가린다."""
    s = Scrubber(["ab"])
    assert s.scrub("about") == "about"


def test_empty_scrubber_is_identity() -> None:
    s = Scrubber([])
    assert not s
    assert s.scrub("아무것도 마스킹하지 않는다") == "아무것도 마스킹하지 않는다"


def test_scrubber_masks_bytes() -> None:
    s = Scrubber([SECRET_VALUE])
    assert SECRET_VALUE.encode() not in s.scrub_bytes(f"log {SECRET_VALUE}".encode())


# ─── 변수 해석 순서 (FR-015, FR-089f·g) ────────────────────────────────────


def test_env_variable_wins_over_ciphertext(keys: KeyPaths, store: SecretStore) -> None:
    """FR-089g — 비밀값을 장비에 보관하지 않는 운용을 가능하게 한다."""
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(keys))
    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(t, store, load_private(keys), env={"LOGIN_PASSWORD": "from-env"})
    assert r.resolve("LOGIN_PASSWORD") == "from-env"


def test_env_variable_wins_for_non_sensitive_too() -> None:
    t = make_test(variables=[{"name": "PROJECT_NAME", "value": "TEST"}])
    r = VariableResolver(t, env={"PROJECT_NAME": "OVERRIDDEN"})
    assert r.resolve("PROJECT_NAME") == "OVERRIDDEN"


def test_ciphertext_used_when_no_env(keys: KeyPaths, store: SecretStore) -> None:
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(keys))
    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(t, store, load_private(keys), env={})
    assert r.resolve("LOGIN_PASSWORD") == SECRET_VALUE


def test_missing_private_key_fails_with_reason_not_empty_value(
    store: SecretStore, keys: KeyPaths
) -> None:
    """SC-011 — 빈 값으로 통과하지 않고 명확한 사유로 실패한다."""
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(keys))
    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(t, store, private_key=None, env={})
    with pytest.raises(VariableResolutionError, match="비밀키가 없습니다"):
        r.resolve("LOGIN_PASSWORD")


def test_missing_ciphertext_fails_with_reason(keys: KeyPaths, store: SecretStore) -> None:
    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(t, store, load_private(keys), env={})
    with pytest.raises(VariableResolutionError, match="보관되어 있지 않"):
        r.resolve("LOGIN_PASSWORD")


def test_non_sensitive_variable_without_value_fails() -> None:
    t = make_test(variables=[{"name": "PROJECT_NAME"}])
    r = VariableResolver(t, env={})
    with pytest.raises(VariableResolutionError, match="값을 구할 수 없습니다"):
        r.resolve("PROJECT_NAME")


def test_undeclared_variable_fails() -> None:
    r = VariableResolver(make_test(), env={})
    with pytest.raises(VariableResolutionError, match="정의되지 않은 변수"):
        r.resolve("NOPE")


def test_substitute_replaces_all_references() -> None:
    t = make_test(variables=[{"name": "A", "value": "1"}, {"name": "B", "value": "2"}])
    r = VariableResolver(t, env={})
    assert r.substitute("{{A}}-{{B}}-{{A}}") == "1-2-1"


def test_resolved_sensitive_values_feeds_scrubber(keys: KeyPaths, store: SecretStore) -> None:
    """복호화된 값만 스크러버에 들어가야 한다 — 비민감 값은 마스킹 대상이 아니다."""
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(keys))
    t = make_test(
        variables=[
            {"name": "LOGIN_PASSWORD", "sensitive": True},
            {"name": "PROJECT_NAME", "value": "TEST"},
        ]
    )
    r = VariableResolver(t, store, load_private(keys), env={})
    r.resolve("LOGIN_PASSWORD")
    r.resolve("PROJECT_NAME")
    assert r.resolved_sensitive_values() == [SECRET_VALUE]


def test_no_private_key_needed_when_test_has_no_sensitive_vars() -> None:
    """민감 변수가 없는 테스트는 비밀키 없이 실행된다."""
    t = make_test(variables=[{"name": "PROJECT_NAME", "value": "TEST"}])
    r = VariableResolver(t, store=None, private_key=None, env={})
    assert r.resolve("PROJECT_NAME") == "TEST"
