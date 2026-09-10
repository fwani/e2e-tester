"""프로젝트 엔드포인트. FR-001·FR-008·FR-088b. contracts/rest-api.md §프로젝트."""

from __future__ import annotations

import contextlib
import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from itb.api.errors import ApiError, ErrorCode, bad_request, conflict, not_found
from itb.api.state import AppState, get_state
from itb.domain.test_case import BrowserKind, Project
from itb.execution.state_machine import holds_browser_session
from itb.storage import registry, trash
from itb.storage.atomic import StorageWriteError
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
    # `min_length=1` 만으로는 공백뿐인 이름이 통과한다 — 사용자는 이름을 안 넣었는데
    # 프로젝트가 만들어지고, 목록에 이름 없는 줄이 남는다 (003 AP-010).
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    default_start_url: str = Field(pattern=r"^https?://", max_length=2000)
    test_id_attribute: str = Field(default="data-testid", min_length=1, max_length=100)


class OpenProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=4096)


class ForgetProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str = Field(min_length=1, max_length=4096)


class RenameProjectRequest(BaseModel):
    """표시 이름만 바꾼다 (012 FR-400).

    `root` 를 받는 이유는 **목록의 어느 줄에나 걸 수 있어야 하기 때문**이다. 열린
    프로젝트만 대상으로 삼으면 사용자는 이름을 고치려고 프로젝트를 먼저 열어야 한다.
    대신 아무 경로나 받지 않는다 — `registry.known_project_root` 가 경계를 본다.
    """

    model_config = ConfigDict(extra="forbid")

    root: str = Field(min_length=1, max_length=4096)
    # 만들기와 **같은 규칙**이다. `min_length=1` 만으로는 공백뿐인 이름이 통과해 목록에
    # 이름 없는 줄이 남는다 (003 AP-010).
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class TrashProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root: str = Field(min_length=1, max_length=4096)


class TrashProjectResponse(BaseModel):
    """무엇을 어디로 옮겼는가 (012 FR-410).

    **204 로 끝내지 않는 이유가 이 형태다.** 옮겨진 위치를 돌려주지 않으면 사용자는
    되돌릴 수 없고, 그러면 "지우지 않고 옮긴다" 는 이 기능의 성질이 사용자에게는 그냥
    삭제와 구별되지 않는다.
    """

    model_config = ConfigDict(extra="forbid")

    root: str
    name: str
    trashed_to: str | None
    """옮겨진 자리. `None` 이면 요청 시점에 이미 없어서 목록에서 빼기만 했다 (FR-420)."""

    was_open: bool
    """이 삭제로 열린 프로젝트가 닫혔는가. 화면이 다음 행동을 정하는 근거다 (FR-416)."""


class ProjectSummary(BaseModel):
    """삭제 확인 단계가 보여줄 것 (012 FR-411).

    **목록 응답에 싣지 않고 여기서 따로 준다.** 목록을 그리려고 프로젝트 N개를 열어
    테스트를 세는 것은 `registry._probe` 가 피하려던 바로 그 비용이다 (plan.md
    Performance Goals). 확인 단계에 들어가는 순간 그 프로젝트 하나만 센다.
    """

    model_config = ConfigDict(extra="forbid")

    root: str
    name: str
    test_count: int
    origin: str


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


@router.get("/summary")
async def summary(root: str) -> ProjectSummary:
    """삭제하기 전에 무엇이 사라지는지 센다 (012 FR-411).

    **읽지 못해도 실패하지 않는다.** 깨진 프로젝트일수록 지울 수 없어지면 곤란하다 —
    셀 수 없으면 0 으로 보고하고, 사용자는 이름과 경로로 판단한다.
    """
    resolved = _known_root(root)
    count = 0
    with contextlib.suppress(Exception):
        count = len(ProjectRepository.open(resolved).list_test_paths())
    return ProjectSummary(
        root=str(resolved),
        name=_display_name(resolved),
        test_count=count,
        origin=_origin_of(resolved),
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
        known = _known_root_outside_home(body.path)
        if known is None:
            raise bad_request(
                ErrorCode.INVALID_PATH,
                "사용자 홈 디렉터리 아래의 경로, 또는 도구가 만들었거나 이전에 연 "
                "프로젝트만 열 수 있습니다.",
            ) from exc
        root = known

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


@router.patch("/name")
async def rename_project(body: RenameProjectRequest, state: State) -> ProjectListItem:
    """표시 이름을 바꾼다. 012 FR-399~FR-408. contracts/api-contract.md §1.

    **프로젝트 파일이 정본, 레지스트리가 사본이다.** 순서가 계약의 일부다 — 파일 쓰기가
    실패하면 레지스트리를 건드리지 않는다 (FR-402). 반대로 하면 목록의 이름과 파일의
    이름이 갈라지고, 다음 조회에서 되돌아간 것처럼 보인다.

    디렉터리 경로는 바뀌지 않으므로 **열린 프로젝트의 이름을 고쳐도 열린 채로 남고 세션이
    끊기지 않는다** (FR-404 · 헌법 원칙 III).
    """
    root = _known_root(body.root)
    repo = _open_for_edit(root)

    project = _read_project_or_400(repo)
    if project.name == body.name:
        # 같은 값을 쓰지 않는다 (FR-407). 파일을 건드리면 mtime 이 바뀌고, 그것을 보고
        # 있는 다른 것들(편집 중 정의 갱신 감지 등)이 이유 없이 반응한다.
        return _list_item(root)

    try:
        repo.write_project(project.model_copy(update={"name": body.name}))
    except (StorageWriteError, OSError) as exc:
        raise ApiError(
            500,
            ErrorCode.STORAGE_WRITE_FAILED,
            f"프로젝트 이름을 저장하지 못했습니다: {exc.strerror or exc}",
        ) from exc

    # 파일이 성공한 뒤에만 사본을 갱신한다. `remember()` 가 아니라 `rename()` 인 이유는
    # 목록 정렬을 흔들지 않기 위해서다 (012 research R2).
    registry.rename(root, body.name)
    return _list_item(root)


@router.post("/trash")
async def trash_project(body: TrashProjectRequest, state: State) -> TrashProjectResponse:
    """프로젝트를 휴지통으로 옮긴다. 012 FR-409~FR-421. contracts/api-contract.md §2.

    **순서가 계약이다** — 옮기기가 실패하면 레지스트리를 건드리지 않는다 (FR-414).
    그러므로 이 라우트가 500 을 낸 뒤 목록을 다시 부르면 그 프로젝트가 그대로 있다.
    목록에서는 사라졌는데 자산은 원래 자리에 남는 상태는 여기서 발생할 수 없다.
    """
    root = _known_root(body.root)
    name = _display_name(root)
    was_open = state.repository is not None and state.repository.paths.root == root

    if was_open and _has_live_session(state):
        raise ApiError(
            409,
            ErrorCode.PROJECT_IN_USE,
            "실행 중인 브라우저가 있어 이 프로젝트를 삭제할 수 없습니다.",
        )

    try:
        destination = trash.move_to_trash(root)
    except OSError as exc:
        raise ApiError(
            500,
            ErrorCode.PROJECT_DELETE_FAILED,
            f"프로젝트를 휴지통으로 옮기지 못했습니다: {exc.strerror or exc}",
        ) from exc

    registry.forget(root)
    if was_open:
        # 사라진 프로젝트를 가리키는 상태로 두지 않는다 (FR-416).
        state.repository = None

    return TrashProjectResponse(
        root=str(root),
        name=name,
        trashed_to=str(destination) if destination is not None else None,
        was_open=was_open,
    )


# ─── 012 공용 도우미 ────────────────────────────────────────────────────────


def _known_root(raw: str) -> pathlib.Path:
    """**도구가 아는 프로젝트**만 통과시킨다 (FR-419 · 헌법 §보안).

    임의 경로를 받아 파일을 쓰거나 디렉터리를 옮기는 엔드포인트를 만들지 않는다.
    """
    root = registry.known_project_root(raw)
    if root is None:
        raise bad_request(
            ErrorCode.INVALID_PATH,
            "도구가 만들었거나 이전에 연 프로젝트만 대상이 될 수 있습니다.",
        )
    return root


def _open_for_edit(root: pathlib.Path) -> ProjectRepository:
    try:
        return ProjectRepository.open(root)
    except ProjectError as exc:
        raise not_found(ErrorCode.PROJECT_NOT_FOUND, str(exc)) from exc
    except PermissionError as exc:
        raise bad_request(ErrorCode.INVALID_PATH, "이 디렉터리를 읽을 권한이 없습니다.") from exc


def _read_project_or_400(repo: ProjectRepository) -> Project:
    try:
        return repo.read_project()
    except DefinitionError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc


def _display_name(root: pathlib.Path) -> str:
    """삭제 응답에 쓸 이름. **읽지 못해도 실패하지 않는다.**

    이름 하나를 못 읽는다고 삭제를 막으면, 깨진 프로젝트일수록 지울 수 없어진다.
    """
    for entry in _list_entries():
        if pathlib.Path(entry.root) == root:
            return entry.name
    return root.name


def _list_item(root: pathlib.Path) -> ProjectListItem:
    """갱신된 줄 하나를 목록과 **같은 계산**으로 만든다.

    직접 조립하지 않는 이유는 두 번째 진실을 만들지 않기 위해서다 — 화면은 이 응답을
    목록의 그 줄과 바꿔 끼우므로, 계산이 갈리면 고친 줄만 다르게 보인다.
    """
    for entry in _list_entries():
        if pathlib.Path(entry.root) == root:
            return ProjectListItem(
                root=entry.root,
                name=entry.name,
                last_opened_at=entry.last_opened_at,
                origin=entry.origin,
                accessible=entry.accessible,
                unavailable_reason=entry.unavailable_reason,
            )
    raise not_found(
        ErrorCode.PROJECT_NOT_FOUND,
        "프로젝트를 목록에서 찾을 수 없습니다. 목록을 새로 고친 뒤 다시 시도하세요.",
    )


def _list_entries() -> list[registry.ProjectEntry]:
    entries, _warning = registry.list_projects()
    return entries


def _has_live_session(state: AppState) -> bool:
    """살아 있는 세션이 하나라도 있는가 (FR-417 · 012 research R6).

    세션은 프로젝트를 기억하지 않지만 **열린 프로젝트가 하나뿐이므로** 세션을 가질 수
    있는 프로젝트도 그 하나뿐이다. 그래서 세션에 프로젝트 식별자를 새로 달지 않고
    판정할 수 있다.

    판정 근거는 이미 있는 `ACTIVE_STATES` 다 (`holds_browser_session`). 새 목록을 만들면
    상태가 늘 때 한쪽이 빠진다.
    """
    return any(holds_browser_session(s.state) for s in state.sessions.all_sessions())


def _known_root_outside_home(raw: str) -> pathlib.Path | None:
    """홈 밖이어도 **도구가 아는 위치**면 연다 (UX U-08).

    홈 경계는 임의 파일 시스템 탐색을 막기 위한 것이다 (DR-005). 도구가 스스로 만들어
    목록에 띄운 프로젝트(관리 위치 아래)와 사용자가 이미 한 번 연 프로젝트(레지스트리)는
    그 경계가 지키려는 것과 무관하다. 둘을 막으면 "만들기는 되는데 열기는 안 되는"
    비대칭이 생긴다 — ``XDG_DATA_HOME`` 이 홈 밖을 가리킬 때 실제로 그랬고, 사용자는
    입력한 적도 없는 경로를 "지정하세요" 라는 지시를 받았다.

    판정 자체는 :func:`registry.known_project_root` 가 갖는다 (012 T007). 012 의 이름
    변경·삭제가 같은 경계를 쓰기 때문이다 — 두 벌로 두면 한쪽이 갈리고, 갈린 자리가
    경계를 무르게 한다.
    """
    return registry.known_project_root(raw)


def _origin_of(root: pathlib.Path) -> registry.Origin:
    """관리 위치 안이면 `managed`, 아니면 `external`."""
    workspace = workspace_dir().expanduser()
    return "managed" if workspace in root.parents else "external"
