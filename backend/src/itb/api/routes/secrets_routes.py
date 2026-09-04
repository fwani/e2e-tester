"""비밀 값·키 엔드포인트. FR-089a~g. contracts/rest-api.md §비밀 값과 키.

**복호화된 값을 반환하는 엔드포인트가 하나도 없다.** 변수 이름과 존재 여부만 다룬다.
`PUT` 은 비밀키를 요구하지 않는다 — 공개키만으로 봉인할 수 있다는 것이 비대칭 방식을
택한 실질적 이득이다 (FR-089b).
"""

from __future__ import annotations

import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, bad_request, conflict, not_found
from itb.api.state import AppState, get_state
from itb.secrets.keys import (
    KeyMissingError,
    KeyPaths,
    KeyStoreError,
    fingerprint,
    generate,
    load_public,
    permission_warning,
    remove,
    status,
)
from itb.secrets.store import FingerprintMismatchError, SecretStore
from itb.storage import registry
from itb.storage.repository import ProjectPaths

router = APIRouter(prefix="/api", tags=["secrets"])

State = Annotated[AppState, Depends(get_state)]

VARIABLE_NAME_PATTERN = r"^[A-Z][A-Z0-9_]*$"

DESTROY_CONFIRM = "DELETE"
"""키를 지우거나 교체할 때 클라이언트가 그대로 보내야 하는 문구 (FR-089a)."""


class KeyStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    private_key_present: bool
    public_key_present: bool
    passphrase_protected: bool
    public_key_fingerprint: str | None
    permission_warning: str | None
    """FR-089e-1 — 권한이 열려 있으면 경고. 권한을 임의로 바꾸지 않는다."""

    key_dir: str
    """키가 실제로 놓인 곳. 화면이 고정 문구(`~/.config/itb/keys`)를 찍으면 격리 실행에서
    거짓이 된다 — 실제 경로를 준다 (UX U-09)."""

    sealed_projects: list[str]
    """지금 키로 봉인된 값을 가진 프로젝트 이름들 — **키 교체·삭제의 실제 영향 범위.**

    키는 장비에 하나다. 경고가 "이 프로젝트" 라고만 말하면 나머지 프로젝트의 암호문이
    아무 통보 없이 못 읽는 상태가 된다 (UX U-09). 그래서 영향 범위를 세어 준다."""


class GenerateKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passphrase: str | None = Field(default=None, min_length=8, max_length=200)


class DestroyKeyRequest(BaseModel):
    """되돌릴 수 없는 조작의 확인 문구. DR-031.

    이 비밀키로 봉인된 암호문은 키를 지우는 순간 영구히 못 읽는다. 실수로 한 번 눌러
    일어날 수 있는 일이 아니어야 하므로, 클라이언트가 사용자에게 정확한 문구를 입력받아
    보낸다. `confirm: true` 같은 불리언은 UI 만 고치면 우회되므로 쓰지 않는다.
    """

    model_config = ConfigDict(extra="forbid")

    confirm: str = Field(description=f"정확히 '{DESTROY_CONFIRM}' 여야 한다")
    passphrase: str | None = Field(default=None, min_length=8, max_length=200)
    """재생성에만 쓴다. 삭제 요청에서는 무시한다."""


class DestroyKeyResponse(BaseModel):
    """삭제·재생성 결과. **무엇이 함께 사라졌는지 숫자로 알린다.**"""

    model_config = ConfigDict(extra="forbid")

    status: KeyStatusResponse
    purged_secret_count: int
    project_open: bool
    """False 면 다른 프로젝트에 남은 암호문은 비우지 못했다는 뜻이다."""


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


def _sealed_projects(paths: KeyPaths) -> list[str]:
    """지금 공개키로 봉인된 값을 하나라도 가진, 도구가 아는 프로젝트의 이름.

    값을 열지 않는다 — 각 비밀 파일의 **지문과 이름 목록만** 읽는다. 남의 프로젝트 파일이
    깨져 있어도 키 화면은 떠야 하므로 그 프로젝트는 건너뛴다.
    """
    if not paths.public.exists():
        return []
    try:
        current = fingerprint(load_public(paths))
    except KeyStoreError:
        return []

    entries, _warning = registry.list_projects()
    return [
        entry.name
        for entry in entries
        if entry.accessible and _sealed_with(pathlib.Path(entry.root), current)
    ]


def _sealed_with(root: pathlib.Path, current_fingerprint: str) -> bool:
    store = SecretStore(ProjectPaths(root).secrets_file)
    try:
        return store.stored_fingerprint == current_fingerprint and bool(store.names())
    except Exception:  # noqa: BLE001 - 남의 프로젝트의 비밀 파일 손상이 키 화면을 막으면 안 된다
        return False


@router.get("/keys/status")
async def key_status(state: State) -> KeyStatusResponse:
    info = status(state.key_paths)
    return KeyStatusResponse(
        private_key_present=bool(info["private_key_present"]),
        public_key_present=bool(info["public_key_present"]),
        passphrase_protected=bool(info["passphrase_protected"]),
        public_key_fingerprint=info["public_key_fingerprint"],  # type: ignore[arg-type]
        permission_warning=info["permission_warning"],  # type: ignore[arg-type]
        key_dir=str(state.key_paths.directory),
        sealed_projects=_sealed_projects(state.key_paths),
    )


@router.post("/keys/generate", status_code=201)
async def generate_key(body: GenerateKeyRequest, state: State) -> KeyStatusResponse:
    """키 쌍을 만든다. DR-028·DR-030.

    **실패를 사용자가 조치할 수 있는 문장으로 돌려준다.** 이전에는 쓰기 권한이 없으면
    `OSError` 가 그대로 올라가 500 + "예상하지 못한 오류" 가 됐고, 사용자는 무엇이
    문제인지 알 수 없었다.

    암호구절 길이 위반(8자 미만)은 요청 검증에서 걸린다. 그쪽은 `app.py` 의
    `RequestValidationError` 핸들러가 계약 형태로 바꾼다 (research R3).
    """
    try:
        generate(state.key_paths, passphrase=body.passphrase)
    except KeyStoreError as exc:
        raise conflict(ErrorCode.KEY_ALREADY_EXISTS, str(exc)) from exc
    except PermissionError as exc:
        raise bad_request(
            ErrorCode.INVALID_PATH,
            f"키를 저장할 권한이 없습니다: {state.key_paths.directory}. "
            "이 디렉터리의 쓰기 권한을 확인하세요.",
        ) from exc
    except OSError as exc:
        raise bad_request(
            ErrorCode.INVALID_PATH,
            f"키를 저장할 수 없습니다: {exc.strerror or exc}. "
            f"저장 위치({state.key_paths.directory})를 확인하세요.",
        ) from exc
    return await key_status(state)


def _require_confirm(body: DestroyKeyRequest) -> None:
    if body.confirm != DESTROY_CONFIRM:
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"되돌릴 수 없는 조작입니다. 확인 문구로 '{DESTROY_CONFIRM}' 를 정확히 "
            "입력해야 진행합니다.",
        )


def _purge_secrets(state: AppState) -> int:
    """열린 프로젝트의 암호문을 전부 비운다. 프로젝트가 없으면 0.

    키가 사라지면 이 암호문들은 어떤 방법으로도 못 읽는다. 남겨 두면 값은 못 읽는데
    지문이 남아 새 값 저장까지 막는다 (`SecretStore.purge` 주석). **프로젝트가 열려
    있지 않으면 지울 대상을 알 수 없다** — 그 경우 키만 지우고, 응답이 그 사실을 알린다.
    """
    if state.repository is None:
        return 0
    return SecretStore(state.repository.paths.secrets_file).purge()


@router.delete("/keys")
async def destroy_key(body: DestroyKeyRequest, state: State) -> DestroyKeyResponse:
    """키 쌍을 지운다. DR-031.

    **봉인된 값을 함께 비운다.** 읽을 수 없게 된 암호문을 남기면 사용자는 값을 볼 수도,
    지울 수도, 새로 넣을 수도 없는 상태에 갇힌다.
    """
    _require_confirm(body)
    if not remove(state.key_paths):
        raise not_found(
            ErrorCode.KEY_MISSING,
            f"지울 키가 없습니다: {state.key_paths.directory}",
        )
    purged = _purge_secrets(state)
    return DestroyKeyResponse(
        status=await key_status(state),
        purged_secret_count=purged,
        project_open=state.repository is not None,
    )


@router.post("/keys/regenerate", status_code=201)
async def regenerate_key(body: DestroyKeyRequest, state: State) -> DestroyKeyResponse:
    """키 쌍을 교체한다. DR-031.

    `generate` 는 기존 키를 절대 덮어쓰지 않는다 (FR-089a) — 그 규칙은 그대로 두고,
    지우고 다시 만드는 것을 **한 번의 확인**으로 묶는다. 두 번 호출로 나누면 중간에
    실패했을 때 키가 없는 상태로 남는다.
    """
    _require_confirm(body)
    remove(state.key_paths)
    purged = _purge_secrets(state)
    try:
        generate(state.key_paths, passphrase=body.passphrase)
    except (PermissionError, OSError) as exc:
        raise bad_request(
            ErrorCode.INVALID_PATH,
            f"새 키를 저장할 수 없습니다: {getattr(exc, 'strerror', None) or exc}. "
            f"저장 위치({state.key_paths.directory})를 확인하세요. "
            "이전 키는 이미 삭제되었습니다.",
        ) from exc
    return DestroyKeyResponse(
        status=await key_status(state),
        purged_secret_count=purged,
        project_open=state.repository is not None,
    )


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
