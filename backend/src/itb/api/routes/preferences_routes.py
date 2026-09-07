"""사용자 취향 엔드포인트. 004 FR-109. contracts/rest-api.md §3.

**프로젝트를 열지 않아도 동작한다.** 취향은 사람에 속하고 프로젝트에 속하지 않으므로
`PROJECT_NOT_OPEN` 을 낼 이유가 없다. 첫 화면이 속도 기본값을 물어볼 수 있어야 한다.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from itb.api.errors import ApiError, ErrorCode
from itb.domain.run_pacing import RunPacing
from itb.storage import preferences

router = APIRouter(prefix="/api/preferences", tags=["preferences"])


class PreferencesView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_pacing: RunPacing

    warning: str | None = None
    """읽지 못한 사유. **조회 자체는 실패하지 않는다.**

    취향을 못 읽었다고 첫 화면이 안 열리면 사용자는 아무것도 할 수 없다 — 프로젝트 목록이
    레지스트리 읽기 실패를 경고로만 처리하는 것과 같은 판단이다 (003 DR-003).
    """


class UpdatePreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_pacing: RunPacing
    """**취향만 받는다.** 자격 증명·경로·프로젝트 식별자를 이 엔드포인트로 저장할 수
    없다. `extra="forbid"` 가 그것을 구조로 막는다 (조직 보안 요건)."""


@router.get("")
async def get_preferences() -> PreferencesView:
    loaded = preferences.load()
    return PreferencesView(run_pacing=loaded.run_pacing, warning=loaded.warning)


@router.put("")
async def put_preferences(body: UpdatePreferencesRequest) -> PreferencesView:
    try:
        preferences.save(body.run_pacing)
    except preferences.PreferencesWriteError as exc:
        # 조용히 넘기지 않는다. 저장했다고 말한 뒤 다음 실행에서 사라지면, 사용자는
        # 무엇이 잘못됐는지 알 방법이 없다.
        raise ApiError(
            status_code=500,
            code=ErrorCode.STORAGE_WRITE_FAILED,
            message=str(exc),
        ) from exc
    return PreferencesView(run_pacing=body.run_pacing)
