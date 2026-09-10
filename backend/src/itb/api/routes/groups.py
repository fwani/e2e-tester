"""테스트 그룹. 013 FR-438~FR-451 · contracts/api-contract.md §5.

**`tests.py` 에 넣지 않는다.** 그룹은 테스트가 아니라 **프로젝트 설정**이다 —
`Project.groups` 에 살고, 테스트가 하나도 없어도 존재한다. 같은 파일에 두면 「테스트
라우트」라는 그 파일의 뜻이 흐려진다 (013 plan.md Structure Decision).

**소속을 테스트에 저장하지 않는다.** 식별자의 접두어가 곧 소속이다 (013 data-model §3) —
둘을 다 저장하면 어긋날 수 있고, 어긋났을 때 어느 쪽이 맞는지 정할 근거가 없다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, StringConstraints

from itb.api.errors import ApiError, ErrorCode, not_found
from itb.api.state import AppState, get_state
from itb.domain.test_case import (
    GROUP_PREFIX_PATTERN,
    RESERVED_PREFIX,
    TestGroup,
)
from itb.storage import test_moves
from itb.storage.repository import ProjectRepository

router = APIRouter(prefix="/api/groups", tags=["groups"])

State = Annotated[AppState, Depends(get_state)]

Prefix = Annotated[str, StringConstraints(pattern=GROUP_PREFIX_PATTERN)]
GroupName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class CreateGroupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prefix: Prefix
    """식별자에 들어가는 짧은 값 (`USER` → `USER-001`).

    **이름에서 자동으로 뽑지 않는다** (013 clarify). 이름이 한글일 수 있고, 그대로 쓰면
    식별자가 길어지며 로마자로 바꾸면 사용자가 예측하지 못하는 값이 나온다.
    """

    name: GroupName


class RenameGroupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: GroupName


class GroupView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prefix: str
    name: str
    count: int
    """이 그룹에 속한 테스트 수. 식별자의 접두어로 센다."""


class GroupListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    groups: list[GroupView]


class UngroupedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ungrouped: list[str]
    """그룹에서 풀려 `TC-###` 로 돌아간 테스트들 (013 FR-451)."""


def prefix_of(test_id: str) -> str:
    """식별자에서 소속을 읽는다. 접두어가 곧 소속이다 (data-model §3)."""
    return test_id.split("-", 1)[0]


def counts_by_prefix(repo: ProjectRepository) -> dict[str, int]:
    """접두어별 테스트 수.

    **정의 파일 이름에서 센다.** 파일을 열어 파싱하지 않는다 — 목록을 그리려고 프로젝트
    N개를 파싱하지 않는다는 기존 규칙과 같은 이유다.
    """
    counts: dict[str, int] = {}
    for path in repo.list_test_paths():
        counts[prefix_of(path.name)] = counts.get(prefix_of(path.name), 0) + 1
    return counts


@router.get("")
async def list_groups(state: State) -> GroupListResponse:
    """그룹 목록. **테스트가 없는 그룹도 싣는다.**

    `GET /api/tests` 의 `groups` 와 개수 규칙이 다르다 — 그쪽은 비어 있는 그룹을 빼서
    목록을 어지럽히지 않지만(FR-450), 여기는 **그룹을 고르는 자리**이므로 비어 있는
    그룹도 골라야 한다.
    """
    repo = state.require_repository()
    counts = counts_by_prefix(repo)
    return GroupListResponse(
        groups=[
            GroupView(prefix=g.prefix, name=g.name, count=counts.get(g.prefix, 0))
            for g in repo.read_project().groups
        ]
    )


@router.post("", status_code=201)
async def create_group(body: CreateGroupRequest, state: State) -> GroupView:
    repo = state.require_repository()
    project = repo.read_project()

    if body.prefix == RESERVED_PREFIX:
        raise ApiError(
            409,
            ErrorCode.GROUP_PREFIX_RESERVED,
            f"{RESERVED_PREFIX} 는 그룹 없는 테스트가 쓰는 접두어입니다.",
        )
    _require_unique(project.groups, prefix=body.prefix, name=body.name)

    project.groups = [*project.groups, TestGroup(prefix=body.prefix, name=body.name)]
    repo.write_project(project)
    return GroupView(prefix=body.prefix, name=body.name, count=0)


@router.patch("/{prefix}")
async def rename_group(prefix: str, body: RenameGroupRequest, state: State) -> GroupView:
    """이름만 바꾼다 (013 FR-449). **접두어는 바꾸지 않는다.**

    접두어를 바꾸면 그 그룹의 테스트 식별자가 전부 바뀌고 정의 파일과 산출물을 다 옮겨야
    한다. 그것은 「그룹 이동」이며 `POST /api/tests:move` 가 하는 일이다 — 이름을 고치는
    조작에 자산 이동을 숨기지 않는다.
    """
    repo = state.require_repository()
    project = repo.read_project()
    target = _require_group(project.groups, prefix)

    if target.name != body.name:
        _require_unique(
            [g for g in project.groups if g.prefix != prefix], prefix=None, name=body.name
        )
        project.groups = [
            TestGroup(prefix=g.prefix, name=body.name if g.prefix == prefix else g.name)
            for g in project.groups
        ]
        repo.write_project(project)

    return GroupView(
        prefix=prefix, name=body.name, count=counts_by_prefix(repo).get(prefix, 0)
    )


@router.delete("/{prefix}")
async def delete_group(prefix: str, state: State) -> UngroupedResponse:
    """그룹을 없앤다. **그 안의 테스트는 지우지 않는다** (013 FR-451).

    묶음을 푸는 것과 자산을 지우는 것은 다른 조작이다 — 012 가 「목록에서 치우기」와
    「삭제」를 가른 것과 같은 규칙이다. 그 그룹의 테스트는 전부 `TC-###` 로 돌아간다.

    **§4 의 이동을 그 그룹 전부에 적용하는 것이며 같은 원자성 규약을 따른다** — 하나라도
    옮기지 못하면 아무것도 옮기지 않는다. 그러지 않으면 「그룹은 없어졌는데 절반은 아직
    그 접두어」인 상태가 남는다.

    실행 중인 테스트가 있으면 거절한다. 그룹 해체는 자산을 옮기는 일이기 때문이다.
    """
    repo = state.require_repository()
    project = repo.read_project()
    _require_group(project.groups, prefix)

    members = [
        path.name.split("-", 2)[0] + "-" + path.name.split("-", 2)[1]
        for path in repo.list_test_paths()
        if prefix_of(path.name) == prefix
    ]

    def validate(test_id: str) -> None:
        if state.sessions.active_session_for_test(test_id) is not None:
            raise ApiError(
                409,
                ErrorCode.TEST_IN_USE,
                f"실행 중인 브라우저가 있어 「{test_id}」을(를) 옮길 수 없습니다.",
            )

    try:
        moved = test_moves.run_all(
            members,
            validate=validate,
            do=lambda tid: test_moves.move_test_to_group(repo, tid, RESERVED_PREFIX),
            undo=lambda _tid, m: test_moves.move_test_back(repo, m),
        )
    except test_moves.PartialFailureError as exc:
        raise ApiError(
            500,
            ErrorCode.TEST_DELETE_PARTIAL,
            exc.reason,
            {"stranded": [{"test": s.target, "where": s.where} for s in exc.stranded]},
        ) from exc
    except test_moves.AllOrNothingError as exc:
        raise ApiError(500, ErrorCode.TEST_MOVE_FAILED, exc.reason) from exc

    # 테스트가 전부 옮겨진 뒤에만 그룹을 뺀다. 반대로 하면 옮기다 실패했을 때
    # 「정의가 없는 접두어」의 테스트가 남는다.
    project = repo.read_project()
    project.groups = [g for g in project.groups if g.prefix != prefix]
    repo.write_project(project)

    return UngroupedResponse(ungrouped=[m.to_id for m in moved])


def _require_group(groups: list[TestGroup], prefix: str) -> TestGroup:
    found = next((g for g in groups if g.prefix == prefix), None)
    if found is None:
        raise not_found(ErrorCode.GROUP_NOT_FOUND, f"그런 그룹이 없습니다: {prefix}")
    return found


def _require_unique(groups: list[TestGroup], *, prefix: str | None, name: str) -> None:
    if prefix is not None and any(g.prefix == prefix for g in groups):
        raise ApiError(
            409, ErrorCode.GROUP_ALREADY_EXISTS, f"이미 쓰는 접두어입니다: {prefix}"
        )
    if any(g.name == name for g in groups):
        raise ApiError(409, ErrorCode.GROUP_ALREADY_EXISTS, f"이미 쓰는 이름입니다: {name}")
