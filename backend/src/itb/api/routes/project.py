"""프로젝트 엔드포인트. FR-001·FR-008·FR-088b. contracts/rest-api.md §프로젝트."""

from __future__ import annotations

import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, bad_request, conflict, not_found
from itb.api.state import AppState, get_state
from itb.domain.test_case import BrowserKind, Project
from itb.storage.repository import ProjectError, ProjectRepository
from itb.storage.yaml_io import DefinitionError

router = APIRouter(prefix="/api/project", tags=["project"])

State = Annotated[AppState, Depends(get_state)]


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=4096)
    name: str = Field(min_length=1, max_length=100)
    default_start_url: str = Field(pattern=r"^https?://", max_length=2000)
    test_id_attribute: str = Field(default="data-testid", min_length=1, max_length=100)


class OpenProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=4096)


class ProjectView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str
    name: str
    default_start_url: str
    browser: BrowserKind
    test_id_attribute: str
    max_tabs: int
    gitignore_present: bool
    secrets_file_present: bool


def _view(repo: ProjectRepository) -> ProjectView:
    project = repo.read_project()
    return ProjectView(
        root=str(repo.paths.root),
        name=project.name,
        default_start_url=project.default_start_url,
        browser=project.browser,
        test_id_attribute=project.test_id_attribute,
        max_tabs=project.max_tabs,
        gitignore_present=repo.paths.gitignore.exists(),
        secrets_file_present=repo.paths.secrets_file.exists(),
    )


@router.get("")
async def current(state: State) -> ProjectView:
    if state.repository is None:
        raise not_found(
            ErrorCode.PROJECT_NOT_OPEN,
            "열린 프로젝트가 없습니다. 프로젝트를 만들거나 여세요.",
        )
    return _view(state.repository)


@router.post("/create", status_code=201)
async def create(body: CreateProjectRequest, state: State) -> ProjectView:
    project = Project(
        name=body.name,
        default_start_url=body.default_start_url,
        test_id_attribute=body.test_id_attribute,
    )
    try:
        repo = ProjectRepository.create(pathlib.Path(body.path), project)
    except ProjectError as exc:
        code = (
            ErrorCode.PROJECT_ALREADY_EXISTS
            if "이미 프로젝트" in str(exc)
            else ErrorCode.INVALID_PATH
        )
        raise conflict(code, str(exc)) from exc
    state.repository = repo
    return _view(repo)


@router.post("/open")
async def open_project(body: OpenProjectRequest, state: State) -> ProjectView:
    try:
        repo = ProjectRepository.open(pathlib.Path(body.path))
    except ProjectError as exc:
        raise not_found(ErrorCode.PROJECT_NOT_FOUND, str(exc)) from exc
    except DefinitionError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    # 열 때도 .gitignore 를 확인한다 — 사용자가 지웠거나 예전 버전으로 만든 프로젝트일 수 있다.
    repo.ensure_gitignore()
    state.repository = repo
    return _view(repo)
