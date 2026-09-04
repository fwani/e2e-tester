"""API 오류 응답의 FastAPI 결합부. 계약 정의는 :mod:`itb.domain.error` 에 있다.

    { "error": {
        "code": "...", "category": "...", "message": "...",
        "next_action": "...", "detail": {}
    } }

**모델은 여기에 없다.** ``ErrorCode``·``Category``·``ErrorBody``·``ErrorResponse`` 는
``itb.domain.error`` 가 권위 정의이며 거기서 JSON Schema 가 내보내진다 (헌법 Cross-language
schema duty). 이 모듈은 기존 임포트 경로를 유지하기 위해 그것들을 다시 내보내고,
FastAPI 에 결합된 부분(``ApiError`` 와 상태 코드별 생성자)만 담는다.

메시지는 **사용자에게 그대로 보여줄 수 있어야 한다.** 내부 스택이나 경로를 노출하지 않고,
무엇을 해야 하는지 알려준다.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from itb.domain.error import CATEGORY, NEXT_ACTION, Category, ErrorBody, ErrorCode, ErrorResponse

__all__ = [
    "CATEGORY",
    "NEXT_ACTION",
    "ApiError",
    "Category",
    "ErrorBody",
    "ErrorCode",
    "ErrorResponse",
    "bad_request",
    "conflict",
    "not_found",
    "not_implemented",
    "validation_error_response",
]


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
        next_action: str | None = None,
    ) -> None:
        body = ErrorBody(
            code=code, message=message, detail=detail or {}, next_action=next_action or ""
        )
        super().__init__(status_code=status_code, detail=ErrorResponse(error=body).model_dump())


# `next_action` 은 키워드 전용이다 — `**detail` 과 섞이면 같은 이름의 detail 키를 쓸 때
# 조용히 다음 행동으로 새어 나간다. 넘기지 않으면 코드별 기본 문구가 채워진다 (003 EC-004).


def bad_request(
    code: ErrorCode, message: str, *, next_action: str | None = None, **detail: Any
) -> ApiError:
    return ApiError(status.HTTP_400_BAD_REQUEST, code, message, detail, next_action)


def not_found(
    code: ErrorCode, message: str, *, next_action: str | None = None, **detail: Any
) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, code, message, detail, next_action)


def conflict(
    code: ErrorCode, message: str, *, next_action: str | None = None, **detail: Any
) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, code, message, detail, next_action)


def not_implemented(
    code: ErrorCode, message: str, *, next_action: str | None = None, **detail: Any
) -> ApiError:
    return ApiError(status.HTTP_501_NOT_IMPLEMENTED, code, message, detail, next_action)


# ─── 요청 검증 실패(422)를 계약 형태로 ──────────────────────────────────────
#
# FastAPI 기본 응답은 `{"detail": [...]}` 이고 위 계약과 형태가 다르다. 프런트엔드의
# 오류 추출기는 `body.error.message` 를 보므로 매칭에 실패하고 "요청이 실패했습니다
# (422)." 라는 폴백 한 문장만 남는다 — 사용자는 무엇이 잘못됐는지 알 수 없다
# (research R3). 아래가 그 구멍을 막는다.


def _reason(err: dict[str, Any]) -> str:
    """pydantic 오류 하나를 사람이 읽을 수 있는 한국어로 바꾼다.

    `ctx` 의 값을 **문자열로 감싸지 않고 숫자만 꺼내 쓴다** — `ctx` 에는 입력값이
    들어 있을 수 있고, 그것이 민감 값이면 오류 메시지를 타고 화면·로그로 샌다.
    """
    kind = str(err.get("type", ""))
    ctx = err.get("ctx") or {}

    match kind:
        case "missing":
            return "필수 항목입니다."
        case "string_too_short":
            return f"{ctx.get('min_length', '?')}자 이상이어야 합니다."
        case "string_too_long":
            return f"{ctx.get('max_length', '?')}자 이하여야 합니다."
        case "string_pattern_mismatch":
            return "허용된 형식이 아닙니다."
        case "extra_forbidden":
            return "허용되지 않는 항목입니다."
        case "greater_than" | "greater_than_equal":
            return f"{ctx.get('ge', ctx.get('gt', '?'))} 이상이어야 합니다."
        case "less_than" | "less_than_equal":
            return f"{ctx.get('le', ctx.get('lt', '?'))} 이하여야 합니다."
        case "literal_error" | "enum":
            return f"허용된 값 중 하나여야 합니다: {ctx.get('expected', '?')}"
        case _ if kind.endswith("_type") or kind.endswith("_parsing"):
            return "값의 형식이 올바르지 않습니다."
        case _:
            return "값이 규격에 맞지 않습니다."


def _where(loc: list[Any]) -> str:
    """오류 위치를 필드 이름으로 줄인다. `body` 접두어는 사용자에게 의미가 없다.

    **맨 앞 하나만 벗긴다.** 모든 요소에서 걸러내면 `path` 라는 **이름의 필드**가
    사라진다 — pydantic 이 주는 `("body", "path")` 에서 접두어와 필드 이름이 같은
    문자열이기 때문이다.
    """
    parts = [str(p) for p in loc]
    if parts and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    return ".".join(parts) or "요청 본문"


def validation_error_response(errors: list[dict[str, Any]]) -> ErrorResponse:
    """검증 실패 목록을 계약 형태 응답으로 바꾼다.

    코드는 **기존 `DEFINITION_INVALID` 를 재사용한다.** 의미가 이미 "요청이 규격에 맞지
    않음" 으로 같고, 새 코드를 만들면 프런트엔드의 `ErrorCode` 유니온과 계약 문서를 함께
    늘려야 하는데 얻는 것이 없다 (contracts/rest-api-delta.md §0).
    """
    fields = [{"loc": _where(e.get("loc", [])), "reason": _reason(e)} for e in errors]

    if len(fields) == 1:
        message = f"{fields[0]['loc']}: {fields[0]['reason']}"
    else:
        joined = ", ".join(f"{f['loc']}({f['reason']})" for f in fields)
        message = f"요청에서 {len(fields)}개 항목이 규격에 맞지 않습니다 — {joined}"

    return ErrorResponse(
        error=ErrorBody(
            code=ErrorCode.DEFINITION_INVALID,
            message=message,
            detail={"fields": fields},
        )
    )
