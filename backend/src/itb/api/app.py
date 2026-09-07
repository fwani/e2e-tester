"""FastAPI 앱과 lifespan. FR-088a.

**Playwright 드라이버를 lifespan 에서 1회 시작하고 앱 종료 시 정지한다.**
`async with async_playwright()` 를 쓰지 않는다 — 블록을 벗어날 때 드라이버가 닫혀
브라우저 수명이 요청 수명에 묶인다 (research R1).

공유 상태는 `itb.api.state` 에 있다 — 라우터와 이 모듈이 서로를 임포트하지 않게 하려는
것이다. 순환 임포트가 생기면 라우터가 등록되지 않는데, 그 실패가 조용하다.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
from starlette.exceptions import HTTPException as StarletteHTTPException

from itb.api.errors import (
    ApiError,
    ErrorBody,
    ErrorCode,
    ErrorResponse,
    validation_error_response,
)
from itb.api.routes import (
    ai,
    fs,
    preferences_routes,
    project,
    secrets_routes,
    sessions,
    steps,
    tabs,
    tests,
)
from itb.api.state import BIND_HOST, BIND_PORT, AppState, get_state
from itb.api.ws.session_events import EventBroker
from itb.execution.session import SessionManager
from itb.secrets.keys import KeyPaths, default_key_dir

# 처리되지 않은 오류는 응답에 스택을 싣지 않는다. 진단은 서버 로그가 맡는다 (003 EC-005).
logger = logging.getLogger(__name__)

ROUTERS = (
    project.router,
    fs.router,
    ai.router,
    tests.router,
    sessions.router,
    steps.router,
    tabs.router,
    secrets_routes.router,
    preferences_routes.router,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    playwright = await async_playwright().start()
    state = AppState(
        playwright=playwright,
        sessions=SessionManager(playwright),
        broker=EventBroker(),
        key_paths=KeyPaths(default_key_dir()),
    )
    app.state.itb = state
    try:
        yield
    finally:
        await state.broker.close_all()
        await state.sessions.close_all()
        await playwright.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Interactive AI Test Builder",
        version="0.1.0",
        summary="브라우저 기반 E2E 테스트 자동화 도구 (단독 로컬 도구)",
        lifespan=lifespan,
    )

    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """요청 검증 실패도 계약 형태로 내보낸다 (DR-022·DR-030).

        기본 동작은 `{"detail": [...]}` 이라 프런트엔드의 오류 추출기가 읽지 못하고,
        결과적으로 앱의 **모든** 422 가 원인을 알 수 없는 한 문장이 된다. 사용자가
        "키 쌍 만들기를 하면 422 가 난다" 고 겪은 것의 실체가 이것이다 (research R3).
        """
        return JSONResponse(
            status_code=422,
            content=validation_error_response(list(exc.errors())).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """라우팅이 낸 오류(없는 경로 404, 허용되지 않은 방법 405)도 계약 형태로 낸다.

        기본 동작은 `{"detail": "Not Found"}` 라 화면의 오류 추출기가 읽지 못한다. 002 가
        422 에서 고친 것과 같은 구멍이며, 003 에서 이름에 경로 구분자를 넣은 요청이 이
        경로로 빠지면서 드러났다 (AS-003).

        `ApiError` 는 위에서 이미 처리되므로 여기 오지 않는다.
        """
        if exc.status_code == 405:
            body = ErrorBody(
                code=ErrorCode.NOT_SUPPORTED,
                message="이 주소에서 지원하지 않는 요청 방법입니다.",
                next_action="화면을 새로 고친 뒤 다시 시도하세요.",
            )
        else:
            body = ErrorBody(
                code=ErrorCode.INVALID_PATH,
                message="요청한 주소를 찾을 수 없습니다.",
                next_action="이름에 `/` 같은 경로 구분자가 들어가지 않았는지 확인하세요.",
                detail={"status": exc.status_code},
            )
        return JSONResponse(
            status_code=exc.status_code, content=ErrorResponse(error=body).model_dump()
        )

    @app.exception_handler(OSError)
    async def _storage_failed(_request: Request, exc: OSError) -> JSONResponse:
        """파일 계층이 실패했다 (003 AP-042).

        디스크가 가득 찼거나 권한이 없거나 쓰기가 중간에 끊긴 경우다. **제품이 깨진 것이
        아니라 환경이 지금 안 되는 것**이므로 `INTERNAL_ERROR`(broken) 로 내보내면
        사용자는 할 수 있는 일이 없다고 읽는다 — 실제로는 공간을 비우거나 권한을 고치면
        된다. `SESSION_LOST` 를 `blocked` 로 둔 것과 같은 판단이다.

        **직전 내용은 남아 있다.** 자산을 쓰는 모든 경로가 `storage/atomic.py` 를
        지나므로, 끊긴 쓰기는 임시 파일에만 남고 원본은 그대로다.
        """
        logger.warning("파일 쓰기 실패", exc_info=exc)
        body = ErrorBody(
            code=ErrorCode.STORAGE_WRITE_FAILED,
            message="저장하지 못했습니다. 직전 내용은 그대로 남아 있습니다.",
            detail={"kind": type(exc).__name__},
        )
        return JSONResponse(status_code=500, content=ErrorResponse(error=body).model_dump())

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        """처리되지 않은 오류도 계약 형태로 내보낸다 (FR-087).

        코드는 **``INTERNAL_ERROR`` 전용이다** (003 EC-003). 003 이전에는
        ``DEFINITION_INVALID`` 를 썼는데, 그 코드는 사용자가 잘못된 정의를 넣어
        **정상적으로 거부당했을 때**도 쓰인다. 받는 쪽은 "내가 고칠 수 있는 것" 과
        "제품이 깨진 것" 을 구별할 수 없었다 — 이 라운드가 존재하는 이유다.

        스택이나 내부 경로를 노출하지 않는다. 서버 로그에는 남는다.
        """
        logger.exception("처리되지 않은 오류", exc_info=exc)
        body = ErrorBody(
            code=ErrorCode.INTERNAL_ERROR,
            message="예상하지 못한 오류가 발생했습니다. 서버 로그를 확인하세요.",
            detail={"kind": type(exc).__name__},
        )
        return JSONResponse(status_code=500, content=ErrorResponse(error=body).model_dump())

    @app.get("/api/health")
    async def health(request: Request) -> dict[str, Any]:
        state = get_state(request)
        return {
            "status": "ok",
            "bind": f"{BIND_HOST}:{BIND_PORT}",
            "project_open": state.repository is not None,
            "active_sessions": len(state.sessions.all_sessions()),
        }

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()
