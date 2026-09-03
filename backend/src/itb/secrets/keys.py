"""비대칭 키 쌍 관리. FR-089a·FR-089e.

PyNaCl 의 `SealedBox`(libsodium `crypto_box_seal`, X25519 + XSalsa20-Poly1305)를 쓴다.
요구되는 모양과 정확히 같다 — 공개키만으로 봉인하고 비밀키로만 개봉한다. 모드·패딩·IV
같은 결정이 하나도 없고 인증까지 포함된다 (research R7).

**공개키와 비밀키가 같은 장비에 있으면** 실질 보호 수준은 비밀키 파일 하나를 지키는 것과
같다. 그래도 이 방식이 값어치가 있는 이유는 ① 정의 파일과 비밀값이 물리적으로 분리되고
② 암호문은 커밋·공유해도 안전하며 ③ 작성 단계가 비밀키를 요구하지 않아 노출 면적이
실행 시점으로 좁혀지기 때문이다. 암호구 보호는 비밀키 파일 자체가 유출되는 경우의 층이다.
"""

from __future__ import annotations

import base64
import hashlib
import os
import pathlib
import stat
from dataclasses import dataclass

from nacl import pwhash, secret
from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, PublicKey

DEFAULT_KEY_DIR = pathlib.Path.home() / ".config" / "itb" / "keys"
PRIVATE_KEY_NAME = "private.key"
PUBLIC_KEY_NAME = "public.key"
PRIVATE_KEY_MODE = 0o600
PASSPHRASE_MAGIC = b"itb-sealed-privkey-v1\n"


class KeyStoreError(Exception):
    """키 관련 오류의 기반. 호출자가 사유를 사용자에게 그대로 보여줄 수 있어야 한다."""


class KeyMissingError(KeyStoreError):
    """키 파일이 없다 (FR-089f)."""


class PassphraseError(KeyStoreError):
    """암호구가 올바르지 않다. **복호화 실패와 구분한다** (FR-089e-2)."""


class PassphraseRequiredError(KeyStoreError):
    """암호구로 보호된 키인데 암호구가 주어지지 않았다."""


@dataclass(frozen=True, slots=True)
class KeyPaths:
    directory: pathlib.Path

    @property
    def private(self) -> pathlib.Path:
        return self.directory / PRIVATE_KEY_NAME

    @property
    def public(self) -> pathlib.Path:
        return self.directory / PUBLIC_KEY_NAME


def fingerprint(public: PublicKey) -> str:
    """공개키 지문. 비밀 파일에 함께 기록해 키 교체를 감지한다."""
    digest = hashlib.sha256(bytes(public)).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def status(paths: KeyPaths) -> dict[str, object]:
    """키 상태. **비밀키 내용을 읽거나 반환하지 않는다.**"""
    have_priv = paths.private.exists()
    have_pub = paths.public.exists()
    info: dict[str, object] = {
        "private_key_present": have_priv,
        "public_key_present": have_pub,
        "passphrase_protected": False,
        "public_key_fingerprint": None,
        "permission_warning": None,
    }
    if have_priv:
        info["passphrase_protected"] = paths.private.read_bytes().startswith(PASSPHRASE_MAGIC)
        info["permission_warning"] = permission_warning(paths.private)
    if have_pub:
        info["public_key_fingerprint"] = fingerprint(load_public(paths))
    return info


def permission_warning(path: pathlib.Path) -> str | None:
    """비밀키 파일 권한을 확인한다 (FR-089e-1).

    소유자 외에 읽기 권한이 열려 있으면 경고 문구를 돌려준다. **권한을 임의로 바꾸지
    않는다** — 사용자 환경의 파일 권한을 제품이 마음대로 고치면 안 된다.
    """
    if not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        return (
            f"비밀키 파일 권한이 {mode:04o} 입니다. 소유자 외에 접근이 열려 있습니다. "
            f"chmod 600 {path} 로 좁히는 것을 권합니다."
        )
    return None


def generate(paths: KeyPaths, passphrase: str | None = None) -> str:
    """키 쌍을 만든다. 이미 있으면 덮어쓰지 않는다. 공개키 지문을 돌려준다."""
    if paths.private.exists() or paths.public.exists():
        msg = f"키가 이미 존재한다: {paths.directory}"
        raise KeyStoreError(msg)

    paths.directory.mkdir(parents=True, exist_ok=True)
    sk = PrivateKey.generate()

    blob = bytes(sk)
    if passphrase:
        blob = PASSPHRASE_MAGIC + _wrap_with_passphrase(blob, passphrase)

    # 파일을 만들 때부터 좁은 권한으로 연다 — 쓰고 나서 chmod 하면 그 사이가 열려 있다.
    fd = os.open(paths.private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, PRIVATE_KEY_MODE)
    try:
        os.write(fd, blob)
    finally:
        os.close(fd)

    paths.public.write_bytes(bytes(sk.public_key))
    paths.public.chmod(0o644)
    return fingerprint(sk.public_key)


def _kdf_salt(blob: bytes) -> bytes:
    return blob[: pwhash.argon2id.SALTBYTES]


def _wrap_with_passphrase(raw: bytes, passphrase: str) -> bytes:
    salt = os.urandom(pwhash.argon2id.SALTBYTES)
    key = pwhash.argon2id.kdf(
        secret.SecretBox.KEY_SIZE,
        passphrase.encode("utf-8"),
        salt,
        opslimit=pwhash.argon2id.OPSLIMIT_MODERATE,
        memlimit=pwhash.argon2id.MEMLIMIT_MODERATE,
    )
    return salt + secret.SecretBox(key).encrypt(raw)


def _unwrap_with_passphrase(blob: bytes, passphrase: str) -> bytes:
    salt = _kdf_salt(blob)
    body = blob[pwhash.argon2id.SALTBYTES :]
    key = pwhash.argon2id.kdf(
        secret.SecretBox.KEY_SIZE,
        passphrase.encode("utf-8"),
        salt,
        opslimit=pwhash.argon2id.OPSLIMIT_MODERATE,
        memlimit=pwhash.argon2id.MEMLIMIT_MODERATE,
    )
    try:
        return secret.SecretBox(key).decrypt(body)
    except CryptoError as exc:
        # 암호구 오류를 복호화 실패와 구분한다 — 조치가 다르다 (FR-089e-2).
        msg = "암호구가 올바르지 않습니다."
        raise PassphraseError(msg) from exc


def load_public(paths: KeyPaths) -> PublicKey:
    """공개키를 읽는다. **봉인은 이것만으로 가능하다** (FR-089b)."""
    if not paths.public.exists():
        msg = f"공개키가 없습니다: {paths.public}"
        raise KeyMissingError(msg)
    return PublicKey(paths.public.read_bytes())


def load_private(paths: KeyPaths, passphrase: str | None = None) -> PrivateKey:
    """비밀키를 읽는다. **실행 시점에만 필요하다.**"""
    if not paths.private.exists():
        msg = (
            f"비밀키가 없습니다: {paths.private}\n"
            "민감 변수를 사용하는 테스트를 실행할 수 없습니다 (FR-089f)."
        )
        raise KeyMissingError(msg)

    blob = paths.private.read_bytes()
    if blob.startswith(PASSPHRASE_MAGIC):
        if not passphrase:
            msg = "이 비밀키는 암호구로 보호되어 있습니다. 암호구가 필요합니다."
            raise PassphraseRequiredError(msg)
        blob = _unwrap_with_passphrase(blob[len(PASSPHRASE_MAGIC) :], passphrase)
    elif passphrase:
        msg = "이 비밀키는 암호구로 보호되어 있지 않습니다."
        raise PassphraseError(msg)

    return PrivateKey(blob)
