"""앱 수명 상태와 의존성. 라우터와 `app.py` 사이의 순환 임포트를 끊는 지점이다.

라우터가 `app.py` 를 임포트하고 `app.py` 가 라우터를 임포트하면 고리가 생긴다.
공유 상태를 이 모듈에 두면 양쪽이 여기만 임포트하므로 고리가 없다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Request
from playwright.async_api import Playwright

from itb.api.errors import ErrorCode, bad_request
from itb.api.ws.control_channel import ControlChannelRegistry
from itb.api.ws.session_events import EventBroker
from itb.execution.session import SessionManager
from itb.portability.plan_store import ImportPlanStore
from itb.secrets.keys import KeyPaths
from itb.secrets.unlock import KeyUnlock
from itb.storage.repository import ProjectRepository
from itb.storage.session_files import SessionFileRegistry

BIND_HOST = "127.0.0.1"
"""로컬 인터페이스 전용 (FR-088a).

인증을 두지 않는 전제가 이것이므로, 이 값을 넓히는 변경은 헌법 개정 사안이다.
"""

BIND_PORT = 4320

PROJECT_ROOT_HEADER = "X-ITB-Project-Root"
"""화면이 「내가 보고 있는 프로젝트」를 말하는 헤더 (2026-09-10 사용자 보고 1번).

**선택적이다.** 없으면 서버는 지금까지처럼 열린 프로젝트로 처리한다 — 계약 테스트와
`curl` 이 그대로 동작해야 한다. 있으면 `app.py` 의 미들웨어가 열린 프로젝트와 대조하고,
다르면 `PROJECT_MISMATCH` 로 **아무 일도 하기 전에** 거절한다.
"""


@dataclass(slots=True)
class AppState:
    """앱 수명 동안 유지되는 것들.

    브라우저 수명이 HTTP 요청 수명에서 분리되는 지점이다 (research R1).
    """

    playwright: Playwright
    sessions: SessionManager
    broker: EventBroker
    key_paths: KeyPaths
    import_plans: ImportPlanStore = field(default_factory=ImportPlanStore)
    """가져오기 계획 (014 · research R8).

    **디스크에 쓰지 않는다.** 확정 전에는 아무것도 만들지 않아야 하는데(FR-016), 디스크에
    쓰면 그 자체가 "만든 것"이 된다. 앱 수명에 두는 이유는 세션과 무관하기 때문이다 —
    새 프로젝트를 만들며 가져오는 경로에는 열린 프로젝트조차 없다.
    """

    control: ControlChannelRegistry = field(default_factory=ControlChannelRegistry)
    session_files: SessionFileRegistry = field(default_factory=SessionFileRegistry)
    """사용자가 보낸 파일 (010 FR-337b).

    **세션과 함께 사라진다.** 앱 수명에 두는 이유는 그 정리를 한 곳에서 보장하기
    위해서다 — 세션마다 흩어 두면 비정상 종료 경로에서 한 곳이 빠진다.
    """

    """조작 채널 모음 (010 · contracts §2).

    `broker` 와 **나란히 두는 것이 요점이다.** 둘은 방향이 반대인 두 통로이고, 한쪽의
    장애가 다른 쪽에 번지지 않아야 한다 (FR-336·FR-348). 같은 객체에 담으면 그 독립성이
    구조에서 사라진다.
    """

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
