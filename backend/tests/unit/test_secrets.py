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
    PASSPHRASE_ENV,
    KeyMissingError,
    KeyPaths,
    KeyStoreError,
    PassphraseError,
    PassphraseRequiredError,
    fingerprint,
    generate,
    load_private,
    load_private_or_reason,
    load_public,
    permission_warning,
    remove,
    status,
)
from itb.secrets.resolver import VariableResolutionError, VariableResolver
from itb.secrets.scrubber import MASK, Scrubber
from itb.secrets.store import DecryptError, FingerprintMismatchError, SecretStore
from itb.secrets.unlock import KeyUnlock

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


# ─── 암호구로 잠긴 키 (FR-089e-3) ───────────────────────────────────────────


def test_locked_key_reports_being_locked_not_missing(tmp_path: pathlib.Path) -> None:
    """**"없다" 와 "잠겼다" 는 조치가 다르다.**

    예전에는 조립부가 `KeyStoreError` 를 통째로 삼켜, 암호구로 잠긴 키가 "비밀키가
    없습니다" 로 보고됐다. 사용자는 멀쩡히 있는 키를 찾아 헤맸다.
    """
    kp = KeyPaths(tmp_path / "keys")
    generate(kp, passphrase="long-enough-phrase")

    private, reason = load_private_or_reason(kp)
    assert private is None
    assert reason is not None
    assert "없습니다" not in reason
    assert "암호구로 보호" in reason
    assert PASSPHRASE_ENV in reason


def test_locked_key_opens_with_the_passphrase_from_env(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kp = KeyPaths(tmp_path / "keys")
    generate(kp, passphrase="long-enough-phrase")
    monkeypatch.setenv(PASSPHRASE_ENV, "long-enough-phrase")

    private, reason = load_private_or_reason(kp)
    assert reason is None
    assert private is not None

    store = SecretStore(tmp_path / "secrets.local.yaml")
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(kp))
    assert store.get("LOGIN_PASSWORD", private) == SECRET_VALUE


def test_wrong_env_passphrase_is_reported_as_a_passphrase_problem(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kp = KeyPaths(tmp_path / "keys")
    generate(kp, passphrase="long-enough-phrase")
    monkeypatch.setenv(PASSPHRASE_ENV, "wrong-phrase-entirely")

    private, reason = load_private_or_reason(kp)
    assert private is None
    assert reason is not None
    assert "암호구가 올바르지" in reason


def test_empty_env_passphrase_is_treated_as_absent(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """빈 문자열을 암호구로 넘기면 "보호되지 않은 키" 오류가 나 사유가 엉뚱해진다."""
    kp = KeyPaths(tmp_path / "keys")
    generate(kp)
    monkeypatch.setenv(PASSPHRASE_ENV, "")

    private, reason = load_private_or_reason(kp)
    assert reason is None
    assert private is not None


def test_resolver_shows_the_key_reason_for_a_sensitive_variable(
    tmp_path: pathlib.Path, store: SecretStore
) -> None:
    kp = KeyPaths(tmp_path / "keys")
    generate(kp, passphrase="long-enough-phrase")
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(kp))
    private, reason = load_private_or_reason(kp)
    assert private is None

    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(t, store, private_key=None, env={}, key_unavailable_reason=reason)
    with pytest.raises(VariableResolutionError, match="암호구로 보호"):
        r.resolve("LOGIN_PASSWORD")


# ─── 키 삭제·교체 (DR-031) ──────────────────────────────────────────────────


def test_remove_deletes_both_files_and_reports_whether_it_did(keys: KeyPaths) -> None:
    assert remove(keys) is True
    assert not keys.private.exists()
    assert not keys.public.exists()
    assert remove(keys) is False


def test_purge_clears_the_fingerprint_so_new_values_can_be_stored(
    tmp_path: pathlib.Path, store: SecretStore
) -> None:
    """지문을 남기면 새 키로도 값을 넣을 수 없는 막다른 골목이 된다."""
    first = KeyPaths(tmp_path / "k1")
    generate(first)
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(first))

    second = KeyPaths(tmp_path / "k2")
    generate(second)
    with pytest.raises(FingerprintMismatchError):
        store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(second))

    assert store.purge() == 1
    assert store.names() == []
    assert store.stored_fingerprint is None

    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(second))
    assert store.get("LOGIN_PASSWORD", load_private(second)) == SECRET_VALUE


def test_purge_survives_a_reload(tmp_path: pathlib.Path, store: SecretStore) -> None:
    kp = KeyPaths(tmp_path / "keys")
    generate(kp)
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(kp))
    store.purge()

    reloaded = SecretStore(store.path)
    assert reloaded.names() == []
    assert reloaded.stored_fingerprint is None


# ─── 세션 도중 키가 바뀌는 경우 (DR-031 회귀) ────────────────────────────────


def test_capturer_seals_with_the_key_that_exists_at_capture_time(
    tmp_path: pathlib.Path, store: SecretStore
) -> None:
    """사용자가 겪은 것: **키를 만들었는데도 민감 값이 저장되지 않는다.**

    세션 시작 시점에 공개키를 붙잡아 두면, 그 사이 키 관리 화면에서 만든 키가 그 세션에
    반영되지 않는다. 봉인하는 순간에 물어야 한다.
    """
    from itb.secrets.capture import SensitiveCapturer
    from itb.secrets.keys import load_public_or_none

    kp = KeyPaths(tmp_path / "keys")
    # 세션이 시작될 때는 키가 없다.
    capturer = SensitiveCapturer(store=store, key_source=lambda: load_public_or_none(kp))
    assert load_public_or_none(kp) is None

    # 사용자가 키 관리 화면에서 키를 만든다.
    generate(kp)

    ref = capturer.to_reference(SECRET_VALUE, cache_key="css:#pw")
    assert ref == "{{SECRET_VALUE_1}}"
    assert capturer.captures[0].sealed is True
    assert store.get("SECRET_VALUE_1", load_private(kp)) == SECRET_VALUE
    assert capturer.warnings == []


def test_capturer_reports_the_real_reason_when_sealing_fails(
    tmp_path: pathlib.Path, store: SecretStore
) -> None:
    """지문 불일치를 "공개키가 없다" 로 알리면 사용자는 엉뚱한 조치를 한다."""
    from itb.secrets.capture import SensitiveCapturer

    first = KeyPaths(tmp_path / "k1")
    generate(first)
    store.put("SEEDED", SECRET_VALUE, load_public(first))

    second = KeyPaths(tmp_path / "k2")
    generate(second)
    capturer = SensitiveCapturer(store=store, public_key=load_public(second))

    capturer.to_reference(SECRET_VALUE, cache_key="css:#pw")

    assert capturer.captures[0].sealed is False
    assert any("공개키가 교체" in w for w in capturer.warnings)
    assert not any("공개키가 없어" in w for w in capturer.warnings)


def test_resolver_opens_the_key_when_the_value_is_needed_not_at_build_time(
    tmp_path: pathlib.Path, store: SecretStore
) -> None:
    """조립 시점에 키가 없어도, 값을 요구할 때 있으면 성공한다."""
    from itb.secrets.keys import load_private_or_reason

    kp = KeyPaths(tmp_path / "keys")
    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(t, store, env={}, key_source=lambda: load_private_or_reason(kp))

    generate(kp)
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(kp))

    assert r.resolve("LOGIN_PASSWORD") == SECRET_VALUE


def test_resolver_reports_the_live_reason_from_the_key_source(
    tmp_path: pathlib.Path, store: SecretStore
) -> None:
    from itb.secrets.keys import load_private_or_reason

    kp = KeyPaths(tmp_path / "keys")
    generate(kp, passphrase="long-enough-phrase")
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(kp))
    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(t, store, env={}, key_source=lambda: load_private_or_reason(kp))

    with pytest.raises(VariableResolutionError, match="암호구로 보호"):
        r.resolve("LOGIN_PASSWORD")


def test_store_picks_up_a_purge_done_elsewhere(tmp_path: pathlib.Path) -> None:
    """세션이 붙잡은 보관소가 키 관리 화면의 비우기를 못 보면 지운 값이 되살아난다."""
    path = tmp_path / "secrets.local.yaml"
    kp = KeyPaths(tmp_path / "k1")
    generate(kp)

    held = SecretStore(path)  # 세션이 붙잡은 것
    held.put("OLD", SECRET_VALUE, load_public(kp))
    assert held.names() == ["OLD"]

    # 키 관리 화면이 키를 교체하며 같은 파일을 비운다.
    SecretStore(path).purge()
    new_keys = KeyPaths(tmp_path / "k2")
    generate(new_keys)

    assert held.names() == []
    assert held.stored_fingerprint is None
    held.put("NEW", SECRET_VALUE, load_public(new_keys))

    reloaded = SecretStore(path)
    assert reloaded.names() == ["NEW"]


# ─── 잠금 해제 상태 (FR-089e-3) ─────────────────────────────────────────────


def test_unlock_holder_never_exposes_the_passphrase_through_held() -> None:
    """`held` 는 **여부**다. 값을 알려주는 통로가 되면 응답에 실려 나갈 길이 생긴다."""
    holder = KeyUnlock()
    assert holder.held is False
    assert holder.passphrase is None

    holder.remember("long-enough-phrase")
    assert holder.held is True
    assert isinstance(holder.held, bool)

    assert holder.forget() is True
    assert holder.forget() is False, "두 번째 버리기는 버린 것이 없다고 말해야 한다"


def test_unlock_verifies_before_it_remembers(tmp_path: pathlib.Path) -> None:
    """확인 없이 기억하면 틀린 암호구가 들어앉고, 실패는 실행 도중으로 미뤄진다."""
    kp = KeyPaths(tmp_path / "keys")
    generate(kp, passphrase="long-enough-phrase")
    holder = KeyUnlock()

    with pytest.raises(PassphraseError):
        holder.unlock(kp, "wrong-but-long-enough")
    assert holder.held is False, "거절된 암호구가 기억에 남았다"

    holder.unlock(kp, "long-enough-phrase")
    assert holder.held is True


def test_unlock_reports_a_missing_key_apart_from_a_wrong_passphrase(
    tmp_path: pathlib.Path,
) -> None:
    """키가 없는 것과 암호구가 틀린 것은 사용자가 할 일이 다르다."""
    holder = KeyUnlock()
    with pytest.raises(KeyMissingError):
        holder.unlock(KeyPaths(tmp_path / "nowhere"), "long-enough-phrase")


def test_held_passphrase_opens_the_key_for_the_resolver(tmp_path: pathlib.Path) -> None:
    """실행 조립부가 하는 것과 같은 이음매다 — 들고 있는 값이 해석기까지 이어진다."""
    kp = KeyPaths(tmp_path / "keys")
    generate(kp, passphrase="long-enough-phrase")
    store = SecretStore(tmp_path / "secrets.local.yaml")
    store.put("LOGIN_PASSWORD", SECRET_VALUE, load_public(kp))
    holder = KeyUnlock()
    holder.unlock(kp, "long-enough-phrase")

    t = make_test(variables=[{"name": "LOGIN_PASSWORD", "sensitive": True}])
    r = VariableResolver(
        t, store, env={}, key_source=lambda: load_private_or_reason(kp, holder.passphrase)
    )

    assert r.resolve("LOGIN_PASSWORD") == SECRET_VALUE
