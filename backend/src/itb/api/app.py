"""FastAPI 앱과 lifespan. FR-088a.

**Playwright 드라이버를 lifespan 에서 1회 시작하고 앱 종료 시 정지한다.**
`async with async_playwright()` 를 쓰지 않는다 — 블록을 벗어날 때 드라이버가 닫혀
브라우저 수명이 요청 수명에 묶인다 (research R1).

공유 상태는 `itb.api.state` 에 있다 — 라우터와 이 모듈이 서로를 임포트하지 않게 하려는
것이다. 순환 임포트가 생기면 라우터가 등록되지 않는데, 그 실패가 조용하다.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright

from itb.api.errors import ApiError, ErrorBody, ErrorCode, ErrorResponse
from itb.api.routes import project, secrets_routes, sessions, steps, tabs, tests
from itb.api.state import BIND_HOST, BIND_PORT, AppState, get_state
from itb.api.ws.session_events import EventBroker
from itb.execution.session import SessionManager
from itb.secrets.keys import DEFAULT_KEY_DIR, KeyPaths

ROUTERS = (
    project.router,
    tests.router,
    sessions.router,
    steps.router,
    tabs.router,
    secrets_routes.router,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    playwright = await async_playwright().start()
    state = AppState(
        playwright=playwright,
        sessions=SessionManager(playwright),
        broker=EventBroker(),
        key_paths=KeyPaths(DEFAULT_KEY_DIR),
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

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        """처리되지 않은 오류도 계약 형태로 내보낸다 (FR-087).

        스택이나 내부 경로를 노출하지 않는다. 서버 로그에는 남는다.
        """
        body = ErrorBody(
            code=ErrorCode.DEFINITION_INVALID,
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
