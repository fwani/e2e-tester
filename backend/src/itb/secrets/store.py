"""민감 값 보관소. FR-089b·FR-089c.

암호문은 **테스트 정의 파일과 분리된** `secrets.local.yaml` 에 둔다. 정의 파일에는
`{{변수명}}` 참조만 남으며 암호문조차 들어가지 않는다.

봉인은 공개키만으로 가능하다 — 녹화·작성 단계는 비밀키를 요구하지 않는다 (FR-089b).
"""

from __future__ import annotations

import base64
import pathlib

import yaml
from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, PublicKey, SealedBox

from itb.secrets.keys import KeyStoreError, fingerprint

SECRETS_FILE_NAME = "secrets.local.yaml"


class DecryptError(KeyStoreError):
    """복호화 실패. 암호구 오류(`PassphraseError`)와 구분한다 (FR-089e-2)."""


class FingerprintMismatchError(KeyStoreError):
    """공개키가 교체되어 기존 암호문을 읽을 수 없다."""


class SecretStore:
    """변수 이름 → 암호문 맵. 공개키로 쓰고 비밀키로 읽는다."""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self._values: dict[str, str] = {}
        self._fingerprint: str | None = None
        self._mtime: int | None = None
        if path.exists():
            self._load()

    # ─── 입출력 ─────────────────────────────────────────────────────────────

    def _stamp(self) -> int | None:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None

    def _refresh(self) -> None:
        """디스크가 바뀌었으면 다시 읽는다.

        한 세션이 이 객체를 붙잡고 있는 동안 키 관리 화면이 파일을 비울 수 있다
        (`purge`). 메모리 상태를 그대로 두면 다음 `put` 이 지워진 암호문을 되살려 쓰고,
        읽을 수 없는 값이 파일에 다시 나타난다.
        """
        current = self._stamp()
        if current == self._mtime:
            return
        if current is None:
            self._values = {}
            self._fingerprint = None
            self._mtime = None
            return
        self._load()

    def _load(self) -> None:
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            msg = f"{self.path} 형식이 올바르지 않습니다. 최상위가 매핑이어야 합니다."
            raise KeyStoreError(msg)
        self._fingerprint = raw.get("public_key_fingerprint")
        values = raw.get("values") or {}
        if not isinstance(values, dict):
            msg = f"{self.path} 의 values 가 매핑이 아닙니다."
            raise KeyStoreError(msg)
        self._values = {str(k): str(v) for k, v in values.items()}
        self._mtime = self._stamp()

    def _save(self) -> None:
        payload = {
            "public_key_fingerprint": self._fingerprint,
            "values": dict(sorted(self._values.items())),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        self.path.chmod(0o600)
        self._mtime = self._stamp()

    # ─── 조회 (값을 절대 노출하지 않는다) ───────────────────────────────────

    @property
    def stored_fingerprint(self) -> str | None:
        self._refresh()
        return self._fingerprint

    def names(self) -> list[str]:
        """보관된 변수 이름 목록. **값은 반환하지 않는다.**"""
        self._refresh()
        return sorted(self._values)

    def has(self, name: str) -> bool:
        self._refresh()
        return name in self._values

    def matches_key(self, public: PublicKey) -> bool:
        """저장된 지문이 현재 공개키와 같은가. 다르면 재입력이 필요하다."""
        self._refresh()
        if self._fingerprint is None:
            return True
        return self._fingerprint == fingerprint(public)

    # ─── 쓰기 — 공개키만 필요 (FR-089b) ────────────────────────────────────

    def put(self, name: str, value: str, public: PublicKey) -> None:
        """민감 값을 공개키로 봉인해 저장한다. 비밀키가 필요하지 않다."""
        self._refresh()
        current = fingerprint(public)
        if self._fingerprint is not None and self._fingerprint != current:
            msg = (
                "공개키가 교체되었습니다. 기존 암호문은 새 키로 읽을 수 없으므로 "
                "모든 민감 값을 다시 입력해야 합니다."
            )
            raise FingerprintMismatchError(msg)
        self._fingerprint = current
        sealed = SealedBox(public).encrypt(value.encode("utf-8"))
        self._values[name] = base64.b64encode(sealed).decode("ascii")
        self._save()

    def delete(self, name: str) -> bool:
        self._refresh()
        if name not in self._values:
            return False
        del self._values[name]
        self._save()
        return True

    def purge(self) -> int:
        """모든 암호문과 **기록된 지문까지** 지운다. 지운 개수를 돌려준다.

        키를 교체하면 기존 암호문은 어떤 방법으로도 못 읽는다. 그때 값만 지우고 지문을
        남기면 `put` 이 계속 `FingerprintMismatchError` 로 거절해 새 값도 못 넣는 막다른
        골목이 된다. 지문을 함께 비우는 것이 이 메서드의 핵심이다.
        """
        self._refresh()
        count = len(self._values)
        self._values = {}
        self._fingerprint = None
        if count or self.path.exists():
            self._save()
        return count

    # ─── 읽기 — 비밀키 필요 (실행 시점) ────────────────────────────────────

    def get(self, name: str, private: PrivateKey) -> str:
        """암호문을 복호화한다. 실행 시점에만 호출한다."""
        self._refresh()
        if name not in self._values:
            msg = f"민감 값이 보관되어 있지 않습니다: {name}"
            raise KeyStoreError(msg)
        if not self.matches_key(private.public_key):
            msg = (
                f"저장된 암호문의 공개키 지문({self._fingerprint})이 현재 키와 다릅니다. "
                "민감 값을 다시 입력해야 합니다."
            )
            raise FingerprintMismatchError(msg)
        try:
            raw = SealedBox(private).decrypt(base64.b64decode(self._values[name]))
        except (CryptoError, ValueError) as exc:
            msg = f"민감 값 복호화에 실패했습니다: {name}"
            raise DecryptError(msg) from exc
        return raw.decode("utf-8")
