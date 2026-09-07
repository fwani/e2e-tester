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

from itb.storage.paths import config_dir

PRIVATE_KEY_NAME = "private.key"
PUBLIC_KEY_NAME = "public.key"
PRIVATE_KEY_MODE = 0o600
PASSPHRASE_MAGIC = b"itb-sealed-privkey-v1\n"
PASSPHRASE_ENV = "ITB_KEY_PASSPHRASE"  # noqa: S105 - 변수 이름이지 값이 아니다
"""**사람이 없는 실행**에서 암호구를 공급하는 환경 변수 (FR-089e-3).

암호구로 잠근 비밀키는 봉인(공개키만 필요)에는 지장이 없지만 재실행·AI 작성에는
개봉이 필요하다.

**일상 경로는 이것이 아니다.** 키 관리 화면에서 암호구를 입력해 잠금을 해제하면
백엔드가 그것을 프로세스 메모리에 들고 있고(`itb.secrets.unlock`), 실행 시점 복호화가
그것을 쓴다. 이 환경 변수는 CI·헤드리스처럼 화면을 거칠 수 없는 실행을 위해 남는다 —
`app.py` 가 기동 시점에 한 번 확인해 같은 자리에 넣는다.
"""


class KeyStoreError(Exception):
    """키 관련 오류의 기반. 호출자가 사유를 사용자에게 그대로 보여줄 수 있어야 한다."""


class KeyMissingError(KeyStoreError):
    """키 파일이 없다 (FR-089f)."""


class PassphraseError(KeyStoreError):
    """암호구가 올바르지 않다. **복호화 실패와 구분한다** (FR-089e-2)."""


class PassphraseRequiredError(KeyStoreError):
    """암호구로 보호된 키인데 암호구가 주어지지 않았다."""


def default_key_dir() -> pathlib.Path:
    """키 쌍이 놓이는 곳. **설정 디렉터리와 같은 규칙을 따른다** — ``XDG_CONFIG_HOME``.

    예전에는 ``Path.home() / ".config"`` 를 모듈 상수로 굳혀 두었다. 그러면 격리 실행
    (테스트·CI·다중 체크아웃)이 ``XDG_CONFIG_HOME`` 을 돌려도 키만은 사용자의 실제 키를
    읽고 **쓴다** — 그 인스턴스의 「키 교체」가 사용자의 실제 비밀값 전부를 날린다
    (UX U-09 에서 실제로 그렇게 동작하는 것을 확인했다).

    매번 계산한다. 상수로 두면 환경 변수를 바꿔도 따라오지 않는다 (`storage.paths` 와
    같은 이유).
    """
    return config_dir() / "keys"


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


# ─── 암호구 파생 비용 ───────────────────────────────────────────────────────
#
# 봉인과 개봉이 **반드시 같은 값**을 써야 한다 — 비용은 봉인된 파일에 기록되지 않으므로
# 두 쪽이 갈라지면 열 수 없는 키가 된다. 그래서 상수를 한곳에 둔다.
#
# 테스트는 이 두 상수를 더 싼 프로필로 바꿔 쓴다 (`tests/conftest.py`). argon2id 파생
# 자체는 그대로 지나므로 검증하는 성질은 같고, MODERATE 의 회당 2.7초만 사라진다.
# 제품 기본값이 MODERATE 임은 `test_secrets.py` 가 따로 못 박는다 — 테스트 편의가
# 제품의 보호 수준을 조용히 낮추지 못하게 하는 잠금이다.

KDF_OPSLIMIT = pwhash.argon2id.OPSLIMIT_MODERATE
KDF_MEMLIMIT = pwhash.argon2id.MEMLIMIT_MODERATE


def _kdf_salt(blob: bytes) -> bytes:
    return blob[: pwhash.argon2id.SALTBYTES]


def _wrap_with_passphrase(raw: bytes, passphrase: str) -> bytes:
    salt = os.urandom(pwhash.argon2id.SALTBYTES)
    key = pwhash.argon2id.kdf(
        secret.SecretBox.KEY_SIZE,
        passphrase.encode("utf-8"),
        salt,
        opslimit=KDF_OPSLIMIT,
        memlimit=KDF_MEMLIMIT,
    )
    return salt + secret.SecretBox(key).encrypt(raw)


def _unwrap_with_passphrase(blob: bytes, passphrase: str) -> bytes:
    salt = _kdf_salt(blob)
    body = blob[pwhash.argon2id.SALTBYTES :]
    key = pwhash.argon2id.kdf(
        secret.SecretBox.KEY_SIZE,
        passphrase.encode("utf-8"),
        salt,
        opslimit=KDF_OPSLIMIT,
        memlimit=KDF_MEMLIMIT,
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
            # **화면에서 할 수 있는 일을 먼저 말한다.** 예전에는 환경 변수부터 안내해서,
            # 방금 키 관리 화면에서 암호구를 입력한 사용자가 같은 값을 셸에 다시 넣고
            # 백엔드를 재기동해야 하는 줄 알았다 (UX U-26).
            msg = (
                "이 비밀키는 암호구로 보호되어 있고 지금 잠겨 있습니다. "
                "키 관리 화면에서 암호구를 입력해 잠금을 해제하세요. "
                f"사람이 없는 실행에서는 백엔드 프로세스에 환경 변수 {PASSPHRASE_ENV} "
                "로 공급할 수 있습니다."
            )
            raise PassphraseRequiredError(msg)
        blob = _unwrap_with_passphrase(blob[len(PASSPHRASE_MAGIC) :], passphrase)
    elif passphrase:
        msg = "이 비밀키는 암호구로 보호되어 있지 않습니다."
        raise PassphraseError(msg)

    return PrivateKey(blob)


def remove(paths: KeyPaths) -> bool:
    """키 쌍을 지운다. 하나라도 지웠으면 True.

    **되돌릴 수 없다.** 이 비밀키로 봉인된 암호문은 이후 어떤 방법으로도 읽을 수 없다.
    그래도 조작을 제공하는 이유는, 없으면 사용자가 파일 경로를 직접 뒤져 지우는 수밖에
    없기 때문이다 — 그 편이 더 위험하다. 호출자가 확인 절차를 세운다.
    """
    removed = False
    for path in (paths.private, paths.public):
        if path.exists():
            path.unlink()
            removed = True
    return removed


def load_private_or_reason(
    paths: KeyPaths, passphrase: str | None = None
) -> tuple[PrivateKey | None, str | None]:
    """비밀키를 열어 보고, 못 열면 **사유를 문자열로** 돌려준다.

    실행 조립부는 비밀키가 없어도 세션을 시작해야 한다 — 민감 변수를 쓰지 않는 테스트가
    비밀키 때문에 막히면 안 된다. 그렇다고 예외를 통째로 삼키면 "잠긴 키"와 "없는 키"가
    같은 문구로 보고돼 사용자가 엉뚱한 조치를 한다(실제로 그랬다). 사유를 들고 다니다가
    민감 변수를 실제로 요구하는 순간 그대로 보여준다 (FR-089f).

    암호구는 인자로 받되, 없으면 ``ITB_KEY_PASSPHRASE`` 를 본다.
    """
    if passphrase is None:
        passphrase = os.environ.get(PASSPHRASE_ENV) or None
    try:
        return load_private(paths, passphrase), None
    except KeyStoreError as exc:
        return None, str(exc)


def load_public_or_none(paths: KeyPaths) -> PublicKey | None:
    """공개키를 읽되, 없으면 `None`. 봉인 시점마다 부르는 용도다.

    세션이 공개키를 붙잡아 두지 않게 하는 것이 목적이다 — 붙잡으면 그 사이에 만든 키가
    그 세션에 반영되지 않는다.
    """
    if not paths.public.exists():
        return None
    return load_public(paths)
