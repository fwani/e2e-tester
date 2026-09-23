"""019 T058 — 실행 준비 상태 판정 (FR-044 · research R10).

**값을 읽지 않는다.** 판정하려고 복호화하면 잠긴 키에서 실패하고, 「잠겨 있다」와 「값이
없다」는 사용자가 할 일이 다른 별개의 사실이다.

**`VariableResolver` 와 같은 해석 순서를 따른다.** 환경 변수가 1순위이므로, 환경 변수에
값이 있으면 봉인 저장소가 비어 있어도 막지 않는다.
"""

from __future__ import annotations

import pathlib

import pytest
from sharing_support import click, fill, make_test

from itb.domain.test_case import Variable, variable_reference
from itb.secrets.keys import KeyPaths, generate, load_public
from itb.secrets.readiness import assess
from itb.secrets.store import SecretStore


def _test_with_secret(*, plain_empty: bool = False):
    steps = [fill(1, "비밀번호 입력", variable_reference("SECRET_PW"))]
    variables = [Variable(name="SECRET_PW", value=None, sensitive=True)]
    if plain_empty:
        steps.insert(0, fill(0, "아이디 입력", variable_reference("LOGIN_ID")))
        variables.append(Variable(name="LOGIN_ID", value="", sensitive=False))
    steps.append(click(2, "확인"))
    return make_test("TC-001", "로그인", steps=steps, variables=variables)


def _store(tmp_path: pathlib.Path) -> SecretStore:
    return SecretStore(tmp_path / "secrets.local.yaml")


def _sealed(tmp_path: pathlib.Path, name: str = "SECRET_PW") -> SecretStore:
    """값을 실제로 봉인한 저장소. 제품의 봉인 경로를 그대로 지난다."""
    paths = KeyPaths(tmp_path / "keys")
    generate(paths, None)
    store = _store(tmp_path)
    store.put(name, "값", load_public(paths))
    return store


# ─── 민감 값이 실행을 막는다 ───────────────────────────────────────────────


def test_missing_secret_blocks_the_run(tmp_path: pathlib.Path) -> None:
    ready = assess(_test_with_secret(), _store(tmp_path), key_available=True, env={})
    assert ready.missing_secrets == ["SECRET_PW"]
    assert ready.runnable is False


def test_sealed_secret_unblocks_the_run(tmp_path: pathlib.Path) -> None:
    store = _sealed(tmp_path)

    ready = assess(_test_with_secret(), store, key_available=True, env={})
    assert ready.missing_secrets == []
    assert ready.runnable is True


def test_env_variable_counts_as_provided(tmp_path: pathlib.Path) -> None:
    """C9 — 해석 순서에서 환경 변수가 1순위다 (FR-089g).

    봉인된 값이 없어도 막지 않는다. 비밀값을 장비에 보관하지 않는 운용이 가능해야 한다.
    """
    ready = assess(
        _test_with_secret(), _store(tmp_path), key_available=True, env={"SECRET_PW": "값"}
    )
    assert ready.missing_secrets == []
    assert ready.runnable is True


def test_no_store_means_no_values(tmp_path: pathlib.Path) -> None:
    """비밀 파일이 아직 없는 프로젝트 — 가져온 직후의 상태다."""
    ready = assess(_test_with_secret(), None, key_available=False, env={})
    assert ready.missing_secrets == ["SECRET_PW"]
    assert ready.key_available is False


# ─── 비민감 빈 값은 막지 않는다 ────────────────────────────────────────────


def test_empty_plain_variable_does_not_block(tmp_path: pathlib.Path) -> None:
    """빈 문자열이 유효한 입력일 수 있다. 제품이 이미 쓰는 판정이다 (FR-044)."""
    store = _sealed(tmp_path)

    ready = assess(_test_with_secret(plain_empty=True), store, key_available=True, env={})
    assert ready.empty_variables == ["LOGIN_ID"]
    assert ready.missing_secrets == []
    assert ready.runnable is True


def test_plain_variable_supplied_by_env_is_not_reported(tmp_path: pathlib.Path) -> None:
    ready = assess(
        _test_with_secret(plain_empty=True),
        _store(tmp_path),
        key_available=True,
        env={"LOGIN_ID": "platform-b", "SECRET_PW": "값"},
    )
    assert ready.empty_variables == []


# ─── 복호화하지 않는다 ─────────────────────────────────────────────────────


def test_assessment_never_decrypts(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """잠긴 키에서도 판정이 돌아야 한다 (research R10).

    `SecretStore.get` 이 불리면 이 검증이 실패한다 — 그것이 복호화하는 자리다.
    """
    store = _sealed(tmp_path)

    def explode(*_args: object, **_kwargs: object) -> str:
        msg = "판정이 복호화를 시도했다"
        raise AssertionError(msg)

    monkeypatch.setattr(SecretStore, "get", explode)

    ready = assess(_test_with_secret(), store, key_available=True, env={})
    assert ready.runnable is True


def test_test_without_secrets_is_always_runnable(tmp_path: pathlib.Path) -> None:
    ready = assess(make_test("TC-001", "평범"), _store(tmp_path), key_available=False, env={})
    assert ready.runnable is True
    assert ready.missing_secrets == []
