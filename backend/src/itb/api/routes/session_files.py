"""파일 업로드 엔드포인트 (010 T062 · FR-337·FR-337a·FR-337c · contracts §3).

**사용자가 자기 기계에서 고른 파일을 제품이 받아 대상 브라우저에 전달한다** (FR-337).
제품이 동작하는 기계의 파일 경로를 사용자가 입력하는 방식이 아니다 — 그러면 화면 없는
원격 기계에서 파일 첨부 녹화가 성립하지 않는다 (SC-518).

**파일은 REST 로 올리고 조작 채널로는 식별자만 보낸다** (research R6). 조작 채널이 큰
페이로드에 막히면 FR-336(조작과 프레임이 서로를 막지 않는다)이 깨진다. 채널의 책임을
좁게 유지하는 것이 그 요구의 구현이다.

저장소와 상한·정리 규칙은 `itb.storage.session_files` 가 갖는다 — 그쪽 머리말을 보라.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict

from itb.api.errors import ErrorCode, bad_request
from itb.api.state import AppState, get_state
from itb.storage.session_files import (
    MAX_FILE_BYTES,
    MAX_FILES_PER_SESSION,
    sanitize_display_name,
)

router = APIRouter(prefix="/api/sessions", tags=["session-files"])

State = Annotated[AppState, Depends(get_state)]


class UploadedFileView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    display_name: str
    size: int


@router.post("/{session_id}/files", status_code=201)
async def upload_file(
    session_id: str, state: State, file: Annotated[UploadFile, File()]
) -> UploadedFileView:
    """파일 하나를 받는다 (FR-337·FR-337a·FR-337c · contracts §3).

    **상한을 넘으면 사유와 함께 거절한다.** 자르지 않는다 — 잘린 파일을 대상 페이지가
    받으면 그 실패는 원인을 드러내지 않는다.
    """
    from itb.api.routes.sessions import work_of

    work_of(session_id)  # 세션이 없으면 여기서 404 가 난다
    store = state.session_files.store(session_id)

    if len(store.files) >= MAX_FILES_PER_SESSION:
        raise bad_request(
            ErrorCode.UPLOAD_REJECTED,
            f"한 세션에 올릴 수 있는 파일은 {MAX_FILES_PER_SESSION}개까지입니다. "
            "세션을 끝내면 올린 파일이 정리됩니다.",
            limit=MAX_FILES_PER_SESSION,
        )

    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise bad_request(
            ErrorCode.UPLOAD_REJECTED,
            f"파일이 상한({MAX_FILE_BYTES // (1024 * 1024)}MB)을 넘습니다. "
            "잘라서 받지 않고 거절합니다.",
            limit_bytes=MAX_FILE_BYTES,
        )

    entry = store.add(sanitize_display_name(file.filename), data)
    return UploadedFileView(
        file_id=entry.file_id, display_name=entry.display_name, size=entry.size
    )
