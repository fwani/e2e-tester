"""공유 묶음 엔드포인트 (기능 019 · contracts/rest-api.md).

내보내기·가져오기·값 인계가 여기 모인다.

**`/api/project` 아래에 두지 않는다.** 프로젝트 대조 가드(:func:`itb.api.app._project_guard`,
`client.ts` 의 `isProjectPath`)는 `/api/project` 로 시작하는 경로를 **제외한다** — 프로젝트를
바꾸는 조작 자체가 거기 있으므로 헤더로 막으면 화면이 프로젝트를 옮길 수 없기 때문이다.
내보내기를 그 아래 두면 가드가 걸리지 않아, 화면이 프로젝트 A 를 보여 주는데 서버가 B 를 연
상태에서 조용히 B 를 내보낸다. 014 가 `/api/export` 를 쓴 이유와 같다.

**민감 값 교차 조회는 이 모듈이 맡는다.** :mod:`itb.sharing` 은 `itb.secrets` 를 임포트할 수
없다(`.importlinter`). 「이 변수에 이미 값이 있는가」·「환경 변수로 공급되는가」는 여기서
채워 넣는다 — 라우터는 양쪽을 다 임포트할 수 있고, 묶음을 만드는 쪽은 이름만 다룬다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from itb.api.errors import ErrorCode, not_found
from itb.api.state import AppState, get_state
from itb.storage.repository import ProjectRepository

router = APIRouter(prefix="/api/share", tags=["sharing"])

State = Annotated[AppState, Depends(get_state)]


def _repo(state: AppState) -> ProjectRepository:
    if state.repository is None:
        raise not_found(
            ErrorCode.PROJECT_NOT_OPEN,
            "열린 프로젝트가 없습니다. 프로젝트를 만들거나 여세요.",
        )
    return state.repository
