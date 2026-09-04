"""프로젝트 엔드포인트. FR-001·FR-008·FR-088b. contracts/rest-api.md §프로젝트."""

from __future__ import annotations

import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, bad_request, conflict, not_found
from itb.api.state import AppState, get_state
from itb.domain.test_case import BrowserKind, Project
from itb.storage import registry
from itb.storage.paths import (
    PathOutsideHomeError,
    allocate_workspace_path,
    resolve_within_home,
    workspace_dir,
)
from itb.storage.repository import ProjectError, ProjectRepository
from itb.storage.yaml_io import DefinitionError

router = APIRouter(prefix="/api/project", tags=["project"])

State = Annotated[AppState, Depends(get_state)]


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # `path` 가 없다 (DR-001). 서버가 어느 경로에서 실행 중인지 사용자는 알 방법이
    # 없으므로 위치를 물으면 아무도 올바른 값을 넣을 수 없다. 도구가 관리하는 위치에
    # 만들고 그 위치를 응답으로 알려 준다 (DR-006).
    name: str = Field(min_length=1, max_length=100)
    default_start_url: str = Field(pattern=r"^https?://", max_length=2000)
    test_id_attribute: str = Field(default="data-testid", min_length=1, max_length=100)


class OpenProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=4096)


class ForgetProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str = Field(min_length=1, max_length=4096)


class ProjectListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str
    name: str
    last_opened_at: str
    origin: str
    accessible: bool
    unavailable_reason: str | None


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projects: list[ProjectListItem]
    warning: str | None = None
    """레지스트리를 읽지 못했을 때의 사유. 목록 조회 자체는 실패하지 않는다 —
    첫 화면이 열리지 않으면 사용자는 아무것도 할 수 없다."""


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


@router.get("/list")
async def list_all() -> ProjectListResponse:
    """첫 화면에 그릴 프로젝트 목록. DR-002·DR-003·DR-004·DR-007.

    관리 위치 스캔 ∪ 레지스트리를 최근 연 순으로 준다. 프로젝트가 하나도 없으면 빈
    목록과 **200** 이다 — 빈 목록은 오류가 아니다.
    """
    entries, warning = registry.list_projects()
    return ProjectListResponse(
        projects=[
            ProjectListItem(
                root=e.root,
                name=e.name,
                last_opened_at=e.last_opened_at,
                origin=e.origin,
                accessible=e.accessible,
                unavailable_reason=e.unavailable_reason,
            )
            for e in entries
        ],
        warning=warning,
    )


@router.post("/create", status_code=201)
async def create(body: CreateProjectRequest, state: State) -> ProjectView:
    """새 프로젝트를 만든다. **위치를 묻지 않는다** (DR-001·DR-006).

    이름이 겹치면 `-2`·`-3` 을 붙여 피한다. `PROJECT_ALREADY_EXISTS` 를 내지 않는다 —
    사용자가 위치를 모르는데 위치 충돌로 실패시킬 수 없다.
    """
    project = Project(
        name=body.name,
        default_start_url=body.default_start_url,
        test_id_attribute=body.test_id_attribute,
    )
    root = allocate_workspace_path(body.name)
    try:
        repo = ProjectRepository.create(root, project)
    except ProjectError as exc:
        raise conflict(ErrorCode.INVALID_PATH, str(exc)) from exc
    except OSError as exc:
        raise bad_request(
            ErrorCode.INVALID_PATH,
            f"프로젝트를 만들 수 없습니다: {exc.strerror or exc}. "
            f"저장 위치({workspace_dir()})의 권한을 확인하세요.",
        ) from exc

    registry.remember(repo.paths.root, project.name, "managed")
    state.repository = repo
    return _view(repo)


@router.post("/open")
async def open_project(body: OpenProjectRequest, state: State) -> ProjectView:
    """경로를 지정해 연다. **사용자가 위치를 지정하는 경로는 이것 하나뿐이다** (DR-005).

    사용자가 파일 선택기로 자기 파일을 고른 결과이므로 경로를 받는다. 다만 홈 경계
    안이어야 한다 — 임의 파일 시스템 접근을 열어 줄 이유가 없다 (research R4).
    """
    try:
        root = resolve_within_home(body.path)
    except PathOutsideHomeError as exc:
        raise bad_request(ErrorCode.INVALID_PATH, str(exc)) from exc

    try:
        repo = ProjectRepository.open(root)
    except ProjectError as exc:
        raise not_found(ErrorCode.PROJECT_NOT_FOUND, str(exc)) from exc
    except DefinitionError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    except PermissionError as exc:
        raise bad_request(
            ErrorCode.INVALID_PATH, "이 디렉터리를 읽을 권한이 없습니다."
        ) from exc

    # 열 때도 .gitignore 를 확인한다 — 사용자가 지웠거나 예전 버전으로 만든 프로젝트일 수 있다.
    repo.ensure_gitignore()
    registry.remember(repo.paths.root, repo.read_project().name, _origin_of(repo.paths.root))
    state.repository = repo
    return _view(repo)


@router.delete("/registry", status_code=204)
async def forget_project(body: ForgetProjectRequest) -> None:
    """목록에서 항목을 치운다. DR-009.

    **디스크의 프로젝트는 지우지 않는다.** 목록 정리와 자산 삭제는 다른 조작이고,
    되돌릴 수 없는 쪽을 조용히 하지 않는다. 관리 위치에 실재하는 프로젝트는 스캔에
    다시 걸려 목록에 남는다 — `GET /list` 가 스캔 ∪ 레지스트리이기 때문이다.
    """
    registry.forget(pathlib.Path(body.root))


def _origin_of(root: pathlib.Path) -> registry.Origin:
    """관리 위치 안이면 `managed`, 아니면 `external`."""
    workspace = workspace_dir().expanduser()
    return "managed" if workspace in root.parents else "external"
