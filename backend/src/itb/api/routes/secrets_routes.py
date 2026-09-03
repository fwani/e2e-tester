"""비밀 값·키 엔드포인트. FR-089a~g. contracts/rest-api.md §비밀 값과 키.

**복호화된 값을 반환하는 엔드포인트가 하나도 없다.** 변수 이름과 존재 여부만 다룬다.
`PUT` 은 비밀키를 요구하지 않는다 — 공개키만으로 봉인할 수 있다는 것이 비대칭 방식을
택한 실질적 이득이다 (FR-089b).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, bad_request, conflict, not_found
from itb.api.state import AppState, get_state
from itb.secrets.keys import (
    KeyMissingError,
    KeyStoreError,
    generate,
    load_public,
    permission_warning,
    status,
)
from itb.secrets.store import FingerprintMismatchError, SecretStore

router = APIRouter(prefix="/api", tags=["secrets"])

State = Annotated[AppState, Depends(get_state)]

VARIABLE_NAME_PATTERN = r"^[A-Z][A-Z0-9_]*$"


class KeyStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    private_key_present: bool
    public_key_present: bool
    passphrase_protected: bool
    public_key_fingerprint: str | None
    permission_warning: str | None
    """FR-089e-1 — 권한이 열려 있으면 경고. 권한을 임의로 바꾸지 않는다."""


class GenerateKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passphrase: str | None = Field(default=None, min_length=8, max_length=200)


class SecretNameView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    present: bool


class SecretsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_key_fingerprint: str | None
    fingerprint_matches_key: bool
    """False 면 공개키가 교체된 상태다. 클라이언트는 재입력을 안내한다."""

    names: list[SecretNameView]


class PutSecretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1, max_length=4000)


def _store(state: AppState) -> SecretStore:
    repo = state.require_repository()
    return SecretStore(repo.paths.secrets_file)


@router.get("/keys/status")
async def key_status(state: State) -> KeyStatusResponse:
    info = status(state.key_paths)
    return KeyStatusResponse(
        private_key_present=bool(info["private_key_present"]),
        public_key_present=bool(info["public_key_present"]),
        passphrase_protected=bool(info["passphrase_protected"]),
        public_key_fingerprint=info["public_key_fingerprint"],  # type: ignore[arg-type]
        permission_warning=info["permission_warning"],  # type: ignore[arg-type]
    )


@router.post("/keys/generate", status_code=201)
async def generate_key(body: GenerateKeyRequest, state: State) -> KeyStatusResponse:
    try:
        generate(state.key_paths, passphrase=body.passphrase)
    except KeyStoreError as exc:
        raise conflict(ErrorCode.KEY_ALREADY_EXISTS, str(exc)) from exc
    return await key_status(state)


@router.get("/secrets")
async def list_secrets(state: State) -> SecretsResponse:
    """**변수 이름과 존재 여부만 돌려준다.** 값은 어떤 경우에도 포함하지 않는다."""
    store = _store(state)
    try:
        public = load_public(state.key_paths)
        matches = store.matches_key(public)
    except KeyMissingError:
        matches = store.stored_fingerprint is None
    return SecretsResponse(
        public_key_fingerprint=store.stored_fingerprint,
        fingerprint_matches_key=matches,
        names=[SecretNameView(name=n, present=True) for n in store.names()],
    )


@router.put("/secrets/{name}", status_code=204)
async def put_secret(name: str, body: PutSecretRequest, state: State) -> None:
    """민감 값을 공개키로 즉시 봉인해 저장한다. **값은 응답에 없다.**

    비밀키가 필요하지 않다 (FR-089b).
    """
    import re

    if not re.match(VARIABLE_NAME_PATTERN, name):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"변수 이름 형식이 올바르지 않습니다: {name} (대문자·숫자·밑줄, 대문자로 시작)",
        )
    store = _store(state)
    try:
        public = load_public(state.key_paths)
    except KeyMissingError as exc:
        raise bad_request(
            ErrorCode.KEY_MISSING,
            f"{exc} 먼저 키 쌍을 만드세요.",
        ) from exc
    try:
        store.put(name, body.value, public)
    except FingerprintMismatchError as exc:
        raise conflict(ErrorCode.FINGERPRINT_MISMATCH, str(exc)) from exc


@router.delete("/secrets/{name}", status_code=204)
async def delete_secret(name: str, state: State) -> None:
    store = _store(state)
    if not store.delete(name):
        raise not_found(ErrorCode.SECRET_NOT_FOUND, f"보관된 값이 없습니다: {name}")


@router.get("/keys/permission-check")
async def permission_check(state: State) -> dict[str, str | None]:
    """비밀키 파일 권한만 따로 확인한다 (FR-089e-1)."""
    return {"warning": permission_warning(state.key_paths.private)}
