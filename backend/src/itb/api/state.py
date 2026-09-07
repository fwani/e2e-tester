"""앱 수명 상태와 의존성. 라우터와 `app.py` 사이의 순환 임포트를 끊는 지점이다.

라우터가 `app.py` 를 임포트하고 `app.py` 가 라우터를 임포트하면 고리가 생긴다.
공유 상태를 이 모듈에 두면 양쪽이 여기만 임포트하므로 고리가 없다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Request
from playwright.async_api import Playwright

from itb.api.errors import ErrorCode, bad_request
from itb.api.ws.session_events import EventBroker
from itb.execution.session import SessionManager
from itb.secrets.keys import KeyPaths
from itb.secrets.unlock import KeyUnlock
from itb.storage.repository import ProjectRepository

BIND_HOST = "127.0.0.1"
"""로컬 인터페이스 전용 (FR-088a).

인증을 두지 않는 전제가 이것이므로, 이 값을 넓히는 변경은 헌법 개정 사안이다.
"""

BIND_PORT = 4320


@dataclass(slots=True)
class AppState:
    """앱 수명 동안 유지되는 것들.

    브라우저 수명이 HTTP 요청 수명에서 분리되는 지점이다 (research R1).
    """

    playwright: Playwright
    sessions: SessionManager
    broker: EventBroker
    key_paths: KeyPaths
    key_unlock: KeyUnlock = field(default_factory=KeyUnlock)
    """암호구로 잠긴 비밀키의 잠금 해제 상태 (FR-089e-3).

    **앱 수명에 두는 것이 요점이다.** 요청 수명에 두면 화면에서 해제한 잠금이 다음
    요청에서 사라져, 사용자가 셸 환경 변수로 다시 공급하는 수밖에 없어진다.
    """

    repository: ProjectRepository | None = None
    startup_warnings: list[str] = field(default_factory=list)

    def require_repository(self) -> ProjectRepository:
        if self.repository is None:
            raise bad_request(
                ErrorCode.PROJECT_NOT_OPEN,
                "열린 프로젝트가 없습니다. 프로젝트를 만들거나 여세요.",
            )
        return self.repository


def get_state(request: Request) -> AppState:
    return request.app.state.itb  # type: ignore[no-any-return]
