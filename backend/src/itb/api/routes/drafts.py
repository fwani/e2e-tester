"""초안 엔드포인트 (기능 014 · contracts/rest-api.md §4).

초안은 **테스트가 아니다.** 실행할 수 없고, 내보내기에 실리지 않으며, 녹화가 저장되는
순간 사라진다. 그래서 `/api/tests` 가 아니라 별도 경로를 쓴다 — 같은 경로 아래 두면
언젠가 목록이 섞인다 (FR-027).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, not_found
from itb.api.state import AppState, get_state
from itb.domain.draft import Draft, compose_instruction
from itb.storage.drafts import DraftNotFoundError
from itb.storage.repository import ProjectRepository

router = APIRouter(prefix="/api/drafts", tags=["drafts"])

State = Annotated[AppState, Depends(get_state)]


def _repo(state: AppState) -> ProjectRepository:
    if state.repository is None:
        raise not_found(
            ErrorCode.PROJECT_NOT_OPEN,
            "열린 프로젝트가 없습니다. 프로젝트를 만들거나 여세요.",
        )
    return state.repository


class DraftSourceView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_name: str
    sheet_name: str
    row: int


class DraftRow(BaseModel):
    """목록에 나가는 초안 하나."""

    model_config = ConfigDict(extra="forbid")
    draft_id: str
    name: str
    description: str | None
    actor: str | None
    group_prefix: str
    desired_test_id: str | None
    desired_id_available: bool
    """지금 그 번호가 비어 있는가.

    `false` 여도 막지 않는다 — 저장할 때 다른 번호를 받는다는 **예고**일 뿐이다 (FR-032).
    초안은 번호를 예약하지 않는다.
    """

    source: DraftSourceView
    created_at: datetime


class DraftDetail(DraftRow):
    procedure: str | None
    expectation: str | None
    suggested_instruction: str
    """서버가 초안에서 지은 AI 지시문 (FR-031).

    화면은 이것을 지시문 칸에 채워 보여 주고, 사용자가 고칠 수 있다. 서버가 짓는 이유는
    초안의 어떤 칸이 지시문의 어느 자리에 들어가는지가 **제품의 판단**이지 화면의 판단이
    아니기 때문이다 — 화면이 지으면 화면마다 달라진다.
    """


class DraftListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    drafts: list[DraftRow] = Field(default_factory=list)
    count: int = 0
    problems: list[str] = Field(default_factory=list)
    """읽을 수 없는 초안 파일의 사유. 하나가 깨져도 나머지는 보여야 한다."""


def _row(draft: Draft, taken: set[str]) -> DraftRow:
    return DraftRow(
        draft_id=draft.draft_id,
        name=draft.name,
        description=draft.description,
        actor=draft.actor,
        group_prefix=draft.group_prefix,
        desired_test_id=draft.desired_test_id,
        desired_id_available=draft.desired_test_id is not None
        and draft.desired_test_id not in taken,
        source=DraftSourceView(
            file_name=draft.source.file_name,
            sheet_name=draft.source.sheet_name,
            row=draft.source.row,
        ),
        created_at=draft.created_at,
    )


def _taken_ids(repo: ProjectRepository) -> set[str]:
    tests, _problems = repo.list_tests()
    return {t.id for t in tests}


@router.get("")
async def list_drafts(state: State) -> DraftListResponse:
    """초안 목록. 다음에 무엇을 녹화할지 고르는 자리다 (FR-035)."""
    repo = _repo(state)
    drafts, problems = repo.drafts.list_all()
    taken = _taken_ids(repo)
    return DraftListResponse(
        drafts=[_row(d, taken) for d in drafts],
        count=len(drafts),
        problems=problems,
    )


@router.get("/{draft_id}")
async def get_draft(draft_id: str, state: State) -> DraftDetail:
    repo = _repo(state)
    try:
        draft = repo.drafts.read(draft_id)
    except DraftNotFoundError as exc:
        raise not_found(ErrorCode.DRAFT_NOT_FOUND, str(exc)) from exc

    base = _row(draft, _taken_ids(repo))
    return DraftDetail(
        **base.model_dump(),
        procedure=draft.procedure,
        expectation=draft.expectation,
        suggested_instruction=compose_instruction(draft),
    )


@router.delete("/{draft_id}", status_code=204)
async def delete_draft(draft_id: str, state: State) -> None:
    """초안 하나를 지운다. 다른 초안과 테스트에 영향을 주지 않는다 (FR-029)."""
    repo = _repo(state)
    try:
        repo.drafts.delete(draft_id)
    except DraftNotFoundError as exc:
        raise not_found(ErrorCode.DRAFT_NOT_FOUND, str(exc)) from exc
