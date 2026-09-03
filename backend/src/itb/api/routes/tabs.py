"""탭 엔드포인트. FR-030f·FR-047c. contracts/rest-api.md §탭."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, not_found
from itb.api.state import AppState, get_state
from itb.execution.session import SessionError

router = APIRouter(prefix="/api/sessions", tags=["tabs"])

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
        raise not_found(ErrorCode.SESSION_NOT_FOUND, str(exc)) from exc

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
        raise not_found(ErrorCode.SESSION_NOT_FOUND, str(exc)) from exc

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

    session.mirrored_tab_index = body.tab_index
    await session.emit("mirror_tab_changed", tab=body.tab_index)
    return await list_tabs(session_id, state)
