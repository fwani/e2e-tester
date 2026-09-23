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

import datetime as dt
import os
import pathlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from itb.api.errors import ApiError, ErrorCode, bad_request, not_found
from itb.api.routes._download import content_disposition
from itb.api.state import AppState, get_state
from itb.domain.test_case import RESERVED_PREFIX, Project, Test
from itb.secrets.store import SecretStore
from itb.sharing import applier, builder, planner, reader
from itb.sharing.applier import ApplyError, ApplyPartialError
from itb.sharing.bundle import RequiredValue
from itb.sharing.limits import BUNDLE_MEDIA_TYPE, BUNDLE_SUFFIX, MAX_BUNDLE_BYTES
from itb.sharing.reader import (
    BundleError,
    BundleTooLargeError,
    BundleVersionError,
    InvalidTestError,
)
from itb.storage import registry
from itb.storage.repository import ProjectError, ProjectRepository, slugify
from itb.storage.session_files import sanitize_display_name

router = APIRouter(prefix="/api/share", tags=["sharing"])

State = Annotated[AppState, Depends(get_state)]

_VIEW_CONFIG = ConfigDict(extra="forbid")


def _repo(state: AppState) -> ProjectRepository:
    if state.repository is None:
        raise not_found(
            ErrorCode.PROJECT_NOT_OPEN,
            "열린 프로젝트가 없습니다. 프로젝트를 만들거나 여세요.",
        )
    return state.repository


def _selected(
    repo: ProjectRepository, test_ids: list[str] | None
) -> tuple[Project, list[Test], list[str], bool]:
    """내보낼 프로젝트·테스트와 빠진 것들을 모은다.

    **읽을 수 없는 정의가 있어도 전체를 실패시키지 않는다** — 그 테스트는 빠지고 사유에
    잡힌다. 깨진 파일 하나 때문에 프로젝트 전체를 내보내지 못하면, 사용자는 그것을 찾아
    고치기 전에는 아무것도 할 수 없다 (014 `_collect` 와 같은 판단).

    다만 **사용자가 이름을 짚어 고른 테스트**가 없으면 조용히 빼지 않는다. 고른 것이
    빠지는 것은 사용자가 뜻한 바가 아니다.
    """
    project = repo.read_project()
    if test_ids is None:
        tests, problems = repo.list_tests()
        return project, tests, problems, True

    picked: list[Test] = []
    for test_id in test_ids:
        try:
            picked.append(repo.read_test(test_id))
        except ProjectError as exc:
            raise not_found(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc
    picked.sort(key=lambda t: t.id)
    return project, picked, [], False


def _require_something(tests: list[Test]) -> None:
    if not tests:
        raise bad_request(
            ErrorCode.SHARE_EXPORT_EMPTY,
            "내보낼 테스트가 없습니다. 파일을 만들지 않았습니다.",
        )


# ─── 내보내기 (US1 · US4) ───────────────────────────────────────────────────


class ExportRequest(BaseModel):
    model_config = _VIEW_CONFIG

    test_ids: list[str] | None = None
    """``None`` 이거나 없으면 프로젝트 전체 (FR-001·FR-002)."""


class StartUrlView(BaseModel):
    model_config = _VIEW_CONFIG
    scope: str
    test_id: str | None
    url: str


class PlaintextValueView(BaseModel):
    model_config = _VIEW_CONFIG
    test_id: str
    step_id: str
    step_label: str | None
    field: str
    value: str
    truncated: bool


class ExportPreviewView(BaseModel):
    """내보내면 무엇이 나가는가 (FR-006). 파일을 만들지 않는다."""

    model_config = _VIEW_CONFIG
    project_name: str
    test_count: int
    group_count: int
    start_urls: list[StartUrlView] = Field(default_factory=list)
    plaintext_values: list[PlaintextValueView] = Field(default_factory=list)
    required_values: list[RequiredValue] = Field(default_factory=list)
    unreadable: list[str] = Field(default_factory=list)


def _review_view(review: builder.ExportReview) -> ExportPreviewView:
    return ExportPreviewView(
        project_name=review.project_name,
        test_count=review.test_count,
        group_count=review.group_count,
        start_urls=[
            StartUrlView(scope=u.scope, test_id=u.test_id, url=u.url)
            for u in review.start_urls
        ],
        plaintext_values=[
            PlaintextValueView(
                test_id=v.test_id,
                step_id=v.step_id,
                step_label=v.step_label,
                field=v.field,
                value=v.value,
                truncated=v.truncated,
            )
            for v in review.plaintext_values
        ],
        required_values=review.required_values,
        unreadable=review.unreadable,
    )


@router.get("/export/preview")
async def export_preview(
    state: State,
    test_ids: Annotated[str | None, Query()] = None,
) -> ExportPreviewView:
    """파일을 만들기 전에 **무엇이 나가는지** 보여 준다 (FR-006 · US4).

    평문 값을 **가리지 않는다.** 이 화면의 목적이 값을 보여 주는 것이고, 가려 놓으면
    사번이나 사내 계정이 섞여 있어도 발견할 수 없다 (research R11).
    """
    repo = _repo(state)
    picked = [t.strip() for t in test_ids.split(",") if t.strip()] if test_ids else None
    project, tests, problems, whole = _selected(repo, picked)
    _require_something(tests)
    review = builder.review_export(
        project, tests, unreadable=problems, whole_project=whole
    )
    return _review_view(review)


@router.post("/export")
async def export_bundle(body: ExportRequest, state: State) -> Response:
    """묶음 파일 하나를 만들어 내려보낸다 (FR-001·FR-002·FR-010).

    **프로젝트의 어떤 파일도 바꾸지 않는다** (FR-008).

    묶음은 메모리에서 완성된 뒤에야 응답 본문이 되므로, 실패는 언제나 "파일이 없다" 이지
    "파일이 이상하다" 가 아니다. 반쯤 만들어진 파일을 사용자에게 주지 않는다.
    """
    repo = _repo(state)
    project, tests, problems, whole = _selected(repo, body.test_ids)
    _require_something(tests)

    bundle = builder.build_bundle(project, tests, whole_project=whole)
    data = builder.dump_bundle(bundle)

    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    filename = f"{slugify(project.name)}-{stamp}{BUNDLE_SUFFIX}"

    headers = {
        "Content-Disposition": content_disposition(
            filename, fallback=f"itb-share{BUNDLE_SUFFIX}"
        ),
        "X-ITB-Share-Test-Count": str(len(tests)),
    }
    if problems:
        headers["X-ITB-Share-Unreadable"] = str(len(problems))

    return Response(
        content=data,
        media_type=f"{BUNDLE_MEDIA_TYPE}; charset=utf-8",
        headers=headers,
    )


# ─── 가져오기 (US2 · US5) ───────────────────────────────────────────────────


class ValueUsageView(BaseModel):
    model_config = _VIEW_CONFIG
    test_id: str
    step_id: str
    step_label: str | None
    field: str


class PlannedValueView(BaseModel):
    """받는 사람이 채워야 할 것 하나 (FR-040).

    ``already_stored`` 와 ``env_provided`` 는 **이 라우터가 채운다** — `itb.sharing` 은
    암호문과 환경에 닿을 수 없다 (research R3).
    """

    model_config = _VIEW_CONFIG
    name: str
    sensitive: bool
    declared: bool
    usages: list[ValueUsageView]
    already_stored: bool | None
    env_provided: bool | None
    blocks_run: bool


class GroupPlanView(BaseModel):
    model_config = _VIEW_CONFIG
    source_prefix: str
    source_name: str
    target_prefix: str
    target_name: str
    action: str
    reason: str | None


class TestPlanView(BaseModel):
    model_config = _VIEW_CONFIG
    source_id: str
    target_id: str
    name: str
    group_prefix: str
    status: str
    reason: str | None
    renumbered: bool


class GroupCapacityView(BaseModel):
    model_config = _VIEW_CONFIG
    prefix: str
    needed: int
    available: int
    ok: bool


class NoticeView(BaseModel):
    model_config = _VIEW_CONFIG
    code: str
    message: str
    detail: dict[str, object] | None


class RepairedVariableView(BaseModel):
    model_config = _VIEW_CONFIG
    test_id: str
    name: str
    sensitive: bool


class SharePlanView(BaseModel):
    model_config = _VIEW_CONFIG
    plan_id: str
    file_name: str
    expires_at: datetime
    target: str
    target_project_name: str | None
    project_renamed_from: str | None
    generator: str
    created_at: datetime
    groups: list[GroupPlanView] = Field(default_factory=list)
    tests: list[TestPlanView] = Field(default_factory=list)
    capacity: list[GroupCapacityView] = Field(default_factory=list)
    required_values: list[PlannedValueView] = Field(default_factory=list)
    repaired_variables: list[RepairedVariableView] = Field(default_factory=list)
    notices: list[NoticeView] = Field(default_factory=list)
    blocking: list[str] = Field(default_factory=list)


class CreatedTestView(BaseModel):
    model_config = _VIEW_CONFIG
    target_id: str
    source_id: str
    name: str
    group_prefix: str


class RenumberedView(BaseModel):
    model_config = _VIEW_CONFIG
    from_id: str = Field(serialization_alias="from")
    to_id: str = Field(serialization_alias="to")


class GroupRefView(BaseModel):
    model_config = _VIEW_CONFIG
    prefix: str
    name: str


class SkippedView(BaseModel):
    model_config = _VIEW_CONFIG
    source_id: str
    reason: str


class ShareReportView(BaseModel):
    model_config = _VIEW_CONFIG
    project_root: str
    project_name: str
    project_renamed_from: str | None
    created_tests: list[CreatedTestView] = Field(default_factory=list)
    renumbered: list[RenumberedView] = Field(default_factory=list)
    created_groups: list[GroupRefView] = Field(default_factory=list)
    skipped: list[SkippedView] = Field(default_factory=list)
    required_values: list[PlannedValueView] = Field(default_factory=list)
    repaired_variables: list[RepairedVariableView] = Field(default_factory=list)
    notices: list[NoticeView] = Field(default_factory=list)


def _notice_view(notice: planner.Notice) -> NoticeView:
    return NoticeView(code=notice.code, message=notice.message, detail=notice.detail)


def _repaired_view(item: reader.RepairedVariable) -> RepairedVariableView:
    return RepairedVariableView(
        test_id=item.test_id, name=item.name, sensitive=item.sensitive
    )


class CommitRequest(BaseModel):
    model_config = _VIEW_CONFIG
    plan_id: str = Field(min_length=1, max_length=64)
    project_name: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=100)
    ] = None
    """`Project.name` 과 같은 상한이다. 여기서 막지 않으면 저장 시점에 터져 500 이 된다."""
    default_start_url: str | None = Field(default=None, pattern=r"^https?://", max_length=2000)
    variable_values: dict[str, str] = Field(default_factory=dict)
    """**비민감** 변수의 값만 받는다 (FR-048).

    민감 값은 이 경로로 받지 않는다 — 봉인은 `PUT /api/secrets/{name}` 하나뿐이고, 두 벌이
    되면 마스킹·오류 처리가 갈려 한쪽에서 평문이 샌다 (research R13).
    """


def _bundle_error(exc: BundleError) -> ApiError:
    """읽기 실패를 사용자에게 보여 줄 오류로 옮긴다.

    **사유마다 코드를 가른다.** 사용자가 할 일이 다르기 때문이다 — 상한 초과는 나눠
    보내야 하고, 손상은 다시 받아야 하고, 버전은 도구를 올려야 한다.
    """
    if isinstance(exc, BundleTooLargeError):
        status = 413 if exc.kind == "bytes" else 400
        return ApiError(status, ErrorCode.SHARE_BUNDLE_TOO_LARGE, str(exc), {"kind": exc.kind})
    if isinstance(exc, BundleVersionError):
        return bad_request(ErrorCode.SHARE_BUNDLE_UNSUPPORTED_VERSION, str(exc))
    if isinstance(exc, InvalidTestError):
        return bad_request(
            ErrorCode.SHARE_BUNDLE_INVALID_TEST, str(exc), problems=exc.problems
        )
    return bad_request(ErrorCode.SHARE_BUNDLE_MALFORMED, str(exc))


def _fill_secret_state(
    values: list[planner.PlannedValue], repo: ProjectRepository | None
) -> list[PlannedValueView]:
    """민감 변수의 대상 쪽 사정을 채운다 (FR-046 · R10).

    **값을 읽지 않는다.** 있는지만 본다 — 판정하려고 복호화하면 잠긴 키에서 실패하고,
    잠겨 있다는 것과 값이 없다는 것은 다른 사실이다.
    """
    store = SecretStore(repo.paths.secrets_file) if repo is not None else None
    out: list[PlannedValueView] = []
    for value in values:
        stored = store.has(value.name) if (store is not None and value.sensitive) else None
        out.append(
            PlannedValueView(
                name=value.name,
                sensitive=value.sensitive,
                declared=value.declared,
                usages=[
                    ValueUsageView(
                        test_id=u.test_id,
                        step_id=u.step_id,
                        step_label=u.step_label,
                        field=u.field,
                    )
                    for u in value.usages
                ],
                already_stored=stored,
                env_provided=os.environ.get(value.name) is not None,
                blocks_run=value.blocks_run,
            )
        )
    return out


def _plan_view(plan: planner.SharePlan, repo: ProjectRepository | None) -> SharePlanView:
    return SharePlanView(
        plan_id=plan.plan_id,
        file_name=plan.file_name,
        expires_at=plan.expires_at,
        target=plan.target,
        target_project_name=plan.target_project_name,
        project_renamed_from=plan.project_renamed_from,
        generator=plan.bundle.bundle.generator,
        created_at=plan.bundle.bundle.created_at,
        groups=[
            GroupPlanView(
                source_prefix=g.source_prefix,
                source_name=g.source_name,
                target_prefix=g.target_prefix,
                target_name=g.target_name,
                action=g.action,
                reason=g.reason,
            )
            for g in plan.groups
        ],
        tests=[
            TestPlanView(
                source_id=t.source_id,
                target_id=t.target_id,
                name=t.name,
                group_prefix=t.group_prefix,
                status=t.status,
                reason=t.reason,
                renumbered=t.renumbered,
            )
            for t in plan.tests
        ],
        capacity=[
            GroupCapacityView(
                prefix=c.prefix, needed=c.needed, available=c.available, ok=c.ok
            )
            for c in plan.capacity
        ],
        required_values=_fill_secret_state(plan.required_values, repo),
        repaired_variables=[_repaired_view(r) for r in plan.repaired],
        notices=[_notice_view(n) for n in plan.notices],
        blocking=plan.blocking,
    )


def _reimported(repo: ProjectRepository | None, file_name: str) -> int:
    """이 묶음을 이미 가져온 적이 있는가 (FR-029 · notices REIMPORT)."""
    if repo is None:
        return 0
    tests, _problems = repo.list_tests()
    return sum(
        1
        for t in tests
        if t.imported_from is not None and t.imported_from.source_file == file_name
    )


def _build_plan(
    read: reader.ReadBundle, *, target: str, file_name: str, state: AppState
) -> planner.SharePlan:
    """계획을 세운다. **디스크에 아무것도 쓰지 않는다.**"""
    repo = _repo(state) if target == "current" else state.repository
    project = repo.read_project() if (repo is not None and target == "current") else None
    used: dict[str, set[int]] = {}
    groups: list = []

    if target == "current" and repo is not None and project is not None:
        groups = list(project.groups)
        # **파일 이름에서 읽는다.** `list_tests` 는 읽을 수 있는 정의만 주므로, 깨진
        # 파일만 쓰고 있는 접두어를 빠뜨린다 — 그러면 그 번호를 새로 배정했다가 확정
        # 직전 검증에서 「이미 있는 식별자」로 전체가 실패한다.
        prefixes = {RESERVED_PREFIX}
        prefixes |= {g.prefix for g in project.groups}
        prefixes |= {p.name.split("-", 1)[0] for p in repo.list_test_paths()}
        used = {prefix: repo.used_numbers(prefix) for prefix in prefixes}

    # 표시 이름과 디렉터리 이름은 다른 것이다 — 디렉터리 충돌은
    # `allocate_workspace_path` 가 확정 시점에 따로 감당한다 (applier).
    reserved = _free_project_name(read.bundle.project.name) if target == "new" else None

    plan = planner.plan_import(
        read,
        target=target,  # type: ignore[arg-type]
        file_name=file_name,
        existing_project=project,
        existing_groups=groups,
        used_numbers=used,
        reserved_project_name=reserved,
        reimported_tests=_reimported(repo if target == "current" else None, file_name),
    )
    # 어느 프로젝트를 보고 세운 계획인지 남긴다 (B1). 확정 때 그것이 바뀌었으면 멈춘다.
    plan.target_root = _root_of(repo if target == "current" else None)
    return plan


def _free_project_name(wanted: str) -> str:
    """이미 쓰이는 이름이면 비껴 만든다 (FR-026 · US2 AS3).

    **기존 프로젝트를 덮어쓰지 않는다.** 목록의 이름으로 판정하고, 디렉터리 충돌은
    `allocate_workspace_path` 가 따로 감당한다 — 둘은 다른 것이며, 이름이 같아도 자리는
    다를 수 있다.
    """
    entries, _warning = registry.load()
    taken = {e.name for e in entries}
    taken |= {e.name for e in registry.scan_workspace()}
    if wanted not in taken:
        return wanted
    for suffix in range(2, 1000):
        candidate = f"{wanted} ({suffix})"
        if candidate not in taken:
            return candidate[:100]
    return wanted


@router.post("/import/plan", status_code=201)
async def plan_import_route(
    state: State,
    file: Annotated[UploadFile, File()],
    target: Annotated[str, Query()] = "new",
) -> SharePlanView:
    """묶음 파일을 올려 **계획**을 만든다 (FR-022·FR-023).

    **디스크에 아무것도 쓰지 않는다.** 확정 전에는 아무것도 만들지 않아야 하는데, 여기서
    무언가 쓰면 그 자체가 "만든 것" 이 된다.

    ``target`` 은 **질의 파라미터**다. 본문의 multipart 필드로 두지 않는 이유는 화면이
    `postFile`(014 가 만든 공용 업로드)을 그대로 쓰기 위해서다 — 그것이 경계 문자열 처리와
    프로젝트 대조 헤더를 함께 다루고, 필드 하나 때문에 그 둘을 다시 만들면 한쪽만 고쳐지는
    날이 온다.
    """
    if target not in ("new", "current"):
        raise bad_request(
            ErrorCode.SHARE_BUNDLE_MALFORMED, "가져올 대상은 new 또는 current 여야 합니다."
        )

    # 상한 + 1 바이트만 읽어 판정한다. 전체를 올린 뒤 재는 것은 상한이 없는 것과 같다.
    data = await file.read(MAX_BUNDLE_BYTES + 1)
    try:
        read = reader.read_bundle(data)
    except BundleError as exc:
        raise _bundle_error(exc) from exc

    file_name = sanitize_display_name(file.filename) or f"bundle{BUNDLE_SUFFIX}"
    plan = _build_plan(read, target=target, file_name=file_name, state=state)
    state.share_plans.put(plan)
    return _plan_view(plan, state.repository if target == "current" else None)


@router.get("/import/plan/{plan_id}")
async def get_plan_route(plan_id: str, state: State) -> SharePlanView:
    """만료 전 계획을 다시 본다. 화면 새로 고침에 쓴다."""
    plan = state.share_plans.get(plan_id)
    if plan is None:
        raise not_found(
            ErrorCode.SHARE_PLAN_NOT_FOUND,
            "가져오기 미리보기가 만료됐거나 없습니다. 파일을 다시 고르세요.",
        )
    return _plan_view(plan, state.repository if plan.target == "current" else None)


@router.post("/import/commit", status_code=201)
async def commit_import_route(body: CommitRequest, state: State) -> ShareReportView:
    """계획을 확정한다. **전부 성공하거나 아무것도 만들지 않는다** (FR-024).

    **계획을 다시 세운다.** 사용자가 미리보기를 본 뒤 다른 창에서 테스트를 만들었을 수
    있고, 그러면 예고한 식별자가 이미 차 있다. 조용히 옛 계획대로 만들면 사용자가 본 적
    없는 결과가 나온다.
    """
    stored = state.share_plans.get(body.plan_id)
    if stored is None:
        raise not_found(
            ErrorCode.SHARE_PLAN_NOT_FOUND,
            "가져오기 미리보기가 만료됐거나 없습니다. 파일을 다시 고르세요.",
        )

    fresh = _build_plan(
        stored.bundle, target=stored.target, file_name=stored.file_name, state=state
    )
    target_repo = state.repository if fresh.target == "current" else None
    if _differs(stored, fresh) or stored.target_root != _root_of(target_repo):
        state.share_plans.drop(body.plan_id)
        state.share_plans.put(fresh)
        raise ApiError(
            409,
            ErrorCode.SHARE_PLAN_STALE,
            "그 사이 프로젝트가 바뀌어 가져올 내용이 달라졌습니다. 다시 확인하세요.",
            {"plan": _plan_view(fresh, target_repo).model_dump(mode="json")},
        )

    if fresh.blocking:
        raise ApiError(
            409,
            ErrorCode.SHARE_IMPORT_BLOCKED,
            "막고 있는 항목이 있어 가져올 수 없습니다.",
            {"blocking": fresh.blocking},
        )

    _reject_sensitive_values(fresh, body.variable_values)

    try:
        if fresh.target == "new":
            report = applier.apply_new_project(
                fresh,
                project_name=body.project_name or fresh.target_project_name or "가져온 프로젝트",
                default_start_url=body.default_start_url,
                variable_values=body.variable_values,
            )
        else:
            report = applier.apply_current_project(
                fresh, _repo(state), variable_values=body.variable_values
            )
    except ApplyPartialError as exc:
        raise ApiError(
            500, ErrorCode.SHARE_IMPORT_PARTIAL, str(exc), {"stranded": exc.stranded}
        ) from exc
    except ApplyError as exc:
        raise ApiError(500, ErrorCode.SHARE_IMPORT_FAILED, str(exc)) from exc

    state.share_plans.drop(body.plan_id)

    if fresh.target == "new":
        # 만든 프로젝트를 연다 — `POST /api/project/create` 와 같은 동작이다.
        state.repository = ProjectRepository.open(pathlib.Path(report.project_root))

    return _report_view(report, state.repository)


def _reject_sensitive_values(plan: planner.SharePlan, values: dict[str, str]) -> None:
    """민감 변수 이름이 오면 거절한다 (contracts §5 · C12).

    **봉인 경로는 하나뿐이다.** 여기서 받아 주면 값이 테스트 정의에 평문으로 들어가고,
    그것은 `Variable._no_plaintext_secret` 이 막으려는 바로 그 상태다.
    """
    sensitive = {v.name for v in plan.required_values if v.sensitive}
    offending = sorted(sensitive & set(values))
    if offending:
        raise bad_request(
            ErrorCode.SHARE_BUNDLE_INVALID_TEST,
            "민감 변수의 값은 이 경로로 받지 않습니다. 가져온 뒤 비밀 값 관리에서 채우세요.",
            names=offending,
        )


def _root_of(repo: ProjectRepository | None) -> str | None:
    return str(repo.paths.root) if repo is not None else None


def _differs(before: planner.SharePlan, after: planner.SharePlan) -> bool:
    """예고와 지금이 다른가. **만들어질 것**만 본다 — 시각·계획 ID 는 언제나 다르다.

    **대상 프로젝트가 바뀐 경우는 이 함수가 보지 않는다.** 배치 모양이 우연히 같을 수 있기
    때문이다(양쪽 다 그 접두어에 테스트가 없는 경우). 호출부가 `target_root` 를 따로
    비교한다 — 미리보기를 본 뒤 다른 프로젝트를 열었다면 그것은 「같은 계획」이 아니다.
    """
    def shape(plan: planner.SharePlan) -> object:
        return (
            [(t.source_id, t.target_id, t.status) for t in plan.tests],
            [(g.source_prefix, g.target_prefix, g.action) for g in plan.groups],
            plan.target_project_name,
        )

    return shape(before) != shape(after)


def _report_view(
    report: applier.ShareReport, repo: ProjectRepository | None
) -> ShareReportView:
    return ShareReportView(
        project_root=report.project_root,
        project_name=report.project_name,
        project_renamed_from=report.project_renamed_from,
        created_tests=[
            CreatedTestView(
                target_id=t.target_id,
                source_id=t.source_id,
                name=t.name,
                group_prefix=t.group_prefix,
            )
            for t in report.created_tests
        ],
        renumbered=[
            RenumberedView(from_id=r.from_id, to_id=r.to_id) for r in report.renumbered
        ],
        created_groups=[GroupRefView(prefix=g.prefix, name=g.name) for g in report.created_groups],
        skipped=[SkippedView(source_id=s.source_id, reason=s.reason) for s in report.skipped],
        required_values=_fill_secret_state(report.required_values, repo),
        repaired_variables=[_repaired_view(r) for r in report.repaired_variables],
        notices=[_notice_view(n) for n in report.notices],
    )
