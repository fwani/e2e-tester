"""탭 엔드포인트. FR-030f·FR-047c. contracts/rest-api.md §탭."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, not_found
from itb.api.state import AppState, get_state
from itb.execution.session import SessionError

router = APIRouter(prefix="/api/sessions", tags=["tabs"])

SESSION_GONE = "세션이 이미 끝났습니다."
"""005 FR-135 — 사용자에게 보이는 문구에 세션 식별자를 넣지 않는다.

`SessionError` 의 문장에는 진단을 위해 세션 UUID 가 들어 있다. 그것을 그대로 `detail`
로 올리면 화면이 "세션을 찾을 수 없습니다: f345e93a…" 를 배너로 띄운다 — 재점검
U-03-b 가 그것을 봤다. 식별자가 필요한 화면은 `detail.session_id` 에서 받는다.

`sessions.py` 의 `work_of` 와 **같은 문장을 쓴다.** 같은 사실을 두 엔드포인트가 다른
말로 부르면 사용자는 다른 일이 일어난 줄 안다 (FR-141).
"""

State = Annotated[AppState, Depends(get_state)]


class TabView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tab_index: int
    url: str
    title: str
    closed: bool


class TabsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tabs: list[TabView]
    active_tab_index: int
    mirrored_tab_index: int
    max_tabs: int


class MirrorTabRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tab_index: int = Field(ge=0)


@router.get("/{session_id}/tabs")
async def list_tabs(session_id: str, state: State) -> TabsResponse:
    try:
        session = state.sessions.require(session_id)
    except SessionError as exc:
        raise not_found(
            ErrorCode.SESSION_NOT_FOUND, SESSION_GONE, session_id=session_id
        ) from exc

    views = [
        TabView(
            tab_index=t.tab_index,
            url=t.url,
            title=await t.title(),
            closed=t.closed,
        )
        for t in session.tabs
    ]
    return TabsResponse(
        tabs=views,
        active_tab_index=session.active_tab_index,
        mirrored_tab_index=session.mirrored_tab_index,
        max_tabs=session.max_tabs,
    )


@router.post("/{session_id}/mirror-tab")
async def set_mirror_tab(
    session_id: str, body: MirrorTabRequest, state: State
) -> TabsResponse:
    """미러가 표시할 탭을 바꾼다.

    스크린캐스트는 한 번에 한 탭만 돌린다 — 모든 탭을 동시에 스트리밍하면 프레임률 목표를
    탭 수로 나누게 된다 (research R3).
    """
    try:
        session = state.sessions.require(session_id)
    except SessionError as exc:
        raise not_found(
            ErrorCode.SESSION_NOT_FOUND, SESSION_GONE, session_id=session_id
        ) from exc

    handle = session.find_tab(body.tab_index)
    if handle is None:
        raise not_found(
            ErrorCode.TAB_NOT_FOUND,
            f"탭 {body.tab_index} 이 없습니다. 열려 있는 탭 중에서 고르세요.",
        )
    if handle.closed:
        raise not_found(
            ErrorCode.TAB_NOT_FOUND,
            f"탭 {body.tab_index} 은 닫혀 있습니다.",
        )

    from itb.api.routes.sessions import mirror_of

    mirror = mirror_of(session_id)
    if mirror is not None:
        # 사용자가 직접 고른 탭이다 — 이후 실행이 다른 탭으로 옮겨가도 이 선택을 유지한다.
        await mirror.show(body.tab_index, pinned=True)
    else:
        # 미러가 아직 없거나 시작하지 못한 경우에도 선택 자체는 반영한다 (FR-047b).
        session.mirrored_tab_index = body.tab_index
        await session.emit("mirror_tab_changed", tab=body.tab_index)
    return await list_tabs(session_id, state)
