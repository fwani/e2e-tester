"""API 오류 응답 형태. contracts/rest-api.md 의 공통 형태를 따른다.

    { "error": { "code": "STEP_LIST_EMPTY", "message": "...", "detail": {} } }

메시지는 **사용자에게 그대로 보여줄 수 있어야 한다.** 내부 스택이나 경로를 노출하지 않고,
무엇을 해야 하는지 알려준다.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict


class ErrorCode(StrEnum):
    # 프로젝트
    PROJECT_NOT_OPEN = "PROJECT_NOT_OPEN"
    PROJECT_ALREADY_EXISTS = "PROJECT_ALREADY_EXISTS"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    INVALID_PATH = "INVALID_PATH"

    # 테스트
    TEST_NOT_FOUND = "TEST_NOT_FOUND"
    STEP_LIST_EMPTY = "STEP_LIST_EMPTY"
    DEFINITION_INVALID = "DEFINITION_INVALID"

    # 세션
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_ALREADY_ACTIVE = "SESSION_ALREADY_ACTIVE"
    SESSION_LOST = "SESSION_LOST"
    NOT_PAUSED = "NOT_PAUSED"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    TAB_NOT_FOUND = "TAB_NOT_FOUND"
    TAB_LIMIT_REACHED = "TAB_LIMIT_REACHED"

    # 비밀 값·키
    KEY_MISSING = "KEY_MISSING"
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    PASSPHRASE_REQUIRED = "PASSPHRASE_REQUIRED"
    PASSPHRASE_INVALID = "PASSPHRASE_INVALID"
    DECRYPT_FAILED = "DECRYPT_FAILED"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    SECRET_NOT_FOUND = "SECRET_NOT_FOUND"

    # 미지원
    NOT_SUPPORTED = "NOT_SUPPORTED"


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    detail: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


class ApiError(HTTPException):
    """계약 형태로 직렬화되는 오류.

    ``detail`` 에 **민감 값이 들어가지 않도록** 호출자가 책임진다. 이 클래스는
    받은 것을 그대로 내보낸다.
    """

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        body = ErrorBody(code=code, message=message, detail=detail or {})
        super().__init__(status_code=status_code, detail=ErrorResponse(error=body).model_dump())


def bad_request(code: ErrorCode, message: str, **detail: Any) -> ApiError:
    return ApiError(status.HTTP_400_BAD_REQUEST, code, message, detail)


def not_found(code: ErrorCode, message: str, **detail: Any) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, code, message, detail)


def conflict(code: ErrorCode, message: str, **detail: Any) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, code, message, detail)


def not_implemented(code: ErrorCode, message: str, **detail: Any) -> ApiError:
    return ApiError(status.HTTP_501_NOT_IMPLEMENTED, code, message, detail)
