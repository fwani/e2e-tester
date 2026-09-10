"""엑셀 통로 엔드포인트 (기능 014 · contracts/rest-api.md).

내보내기는 여기, 가져오기도 여기. 초안 조회·삭제는 :mod:`itb.api.routes.drafts` 가 맡는다.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from itb.api.errors import ApiError, ErrorCode, bad_request, conflict, not_found
from itb.api.state import AppState, get_state
from itb.domain.draft import Draft, DraftSource
from itb.domain.run_result import Outcome
from itb.domain.test_case import MAX_TEST_NUMBER, RESERVED_PREFIX, Project, TestGroup
from itb.portability import exporter
from itb.portability.importer import (
    ImportPlan,
    PrefixSource,
    RowPlan,
    SheetPlan,
    build_plan,
    validate_prefix,
)
from itb.portability.limits import MAX_UPLOAD_BYTES, XLSX_MEDIA_TYPE
from itb.portability.sheet_name import SheetRename
from itb.portability.workbook import (
    ArchiveRejected,
    ParsedWorkbook,
    WorkbookError,
    read_sheets,
    write_workbook,
)
from itb.storage import registry, trash
from itb.storage.paths import allocate_workspace_path
from itb.storage.repository import ProjectError, ProjectRepository, slugify
from itb.storage.session_files import sanitize_display_name
from itb.storage.test_moves import AllOrNothingError, PartialFailureError, run_all

router = APIRouter(prefix="/api", tags=["excel"])
"""**`/api/project` 아래에 두지 않는다.**

프로젝트 대조 가드(`api/app.py` 의 `_project_guard`, `client.ts` 의 `isProjectPath`)는
`/api/project` 로 시작하는 경로를 **제외한다** — 프로젝트를 바꾸는 조작 자체를 막으면
프로젝트를 옮길 수 없기 때문이다. 내보내기를 그 아래 두면 가드가 걸리지 않아, 화면이
프로젝트 A 를 보여 주는데 서버가 B 를 연 상태에서 조용히 B 를 내보낸다.
"""

State = Annotated[AppState, Depends(get_state)]


def _repo(state: AppState) -> ProjectRepository:
    if state.repository is None:
        raise not_found(
            ErrorCode.PROJECT_NOT_OPEN,
            "열린 프로젝트가 없습니다. 프로젝트를 만들거나 여세요.",
        )
    return state.repository


# ─── 내보내기 (US1) ────────────────────────────────────────────────────────


class SheetRenameView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_name: str
    sheet_name: str
    reason: str


class TruncationView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: str
    column: str
    kept_lines: int
    dropped_lines: int


class ExportWarningsView(BaseModel):
    """내보내기에서 무엇이 바뀌는가. 파일을 만들지 않고 미리 본다 (FR-008·FR-010)."""

    model_config = ConfigDict(extra="forbid")
    sheet_renames: list[SheetRenameView] = Field(default_factory=list)
    truncations: list[TruncationView] = Field(default_factory=list)
    unreadable: list[str] = Field(default_factory=list)
    test_count: int = 0
    sheet_count: int = 0


def _collect(repo: ProjectRepository) -> tuple[list, exporter.ExportReport]:
    """프로젝트를 읽어 시트와 보고를 만든다.

    **읽을 수 없는 정의가 있어도 실패하지 않는다.** 그 테스트는 빠지고 경고에 잡힌다 —
    `GET /api/tests` 가 ``problems`` 로 같은 일을 한다. 깨진 파일 하나 때문에 프로젝트
    전체를 내보내지 못하면, 사용자는 그것을 찾아 고치기 전에는 아무것도 할 수 없다.
    """
    project = repo.read_project()
    tests, problems = repo.list_tests()

    outcomes: dict[str, Outcome | None] = {}
    for test in tests:
        result, _problem = repo.try_read_result(test.id)
        outcomes[test.id] = result.outcome if result else None

    return exporter.build_sheets(project, tests, outcomes, unreadable=problems)


def _content_disposition(filename: str) -> str:
    """ASCII 대체 이름과 RFC 5987 이름을 함께 싣는다 (research R9).

    HTTP 헤더는 ASCII 로 제한되는데 프로젝트 이름은 한글일 수 있다. 이 저장소는 같은 함정을
    `X-ITB-Project-Root` 에서 이미 겪었다. 두 이름을 함께 보내면 ``filename*`` 을 이해하는
    브라우저는 한글 이름을, 아닌 쪽은 ASCII 이름을 쓴다.
    """
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "itb-export.xlsx"
    quoted = urllib.parse.quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quoted}"


@router.get("/export")
async def export_project(state: State) -> Response:
    """프로젝트 전체를 워크북 하나로 내보낸다 (FR-001).

    **프로젝트의 어떤 파일도 바꾸지 않는다** (FR-012).
    """
    repo = _repo(state)
    try:
        specs, report = _collect(repo)
        data = write_workbook(specs)
    except WorkbookError as exc:
        # 반쯤 만들어진 파일을 주지 않는다 (FR-013). 워크북은 메모리에서 완성된 뒤에야
        # 응답 본문이 되므로, 실패는 언제나 "파일이 없다" 이지 "파일이 이상하다" 가 아니다.
        raise bad_request(ErrorCode.EXPORT_FAILED, str(exc)) from exc

    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    filename = f"{slugify(repo.read_project().name)}-{stamp}.xlsx"

    headers = {"Content-Disposition": _content_disposition(filename)}
    if report.warning_count:
        headers["X-ITB-Export-Warnings"] = str(report.warning_count)

    return Response(content=data, media_type=XLSX_MEDIA_TYPE, headers=headers)


@router.get("/export/warnings")
async def export_warnings(state: State) -> ExportWarningsView:
    """내보내면 무엇이 바뀌는지 미리 본다. 파일을 만들지 않는다."""
    repo = _repo(state)
    _specs, report = _collect(repo)
    return ExportWarningsView(
        sheet_renames=[_rename_view(r) for r in report.sheet_renames],
        truncations=[
            TruncationView(
                test_id=t.test_id,
                column=t.column,
                kept_lines=t.kept_lines,
                dropped_lines=t.dropped_lines,
            )
            for t in report.truncations
        ],
        unreadable=report.unreadable,
        test_count=report.test_count,
        sheet_count=report.sheet_count,
    )


def _rename_view(rename: SheetRename) -> SheetRenameView:
    return SheetRenameView(
        group_name=rename.group_name,
        sheet_name=rename.sheet_name,
        reason=rename.reason,
    )


# ─── 가져오기 (US2) ────────────────────────────────────────────────────────


class RenumberedView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row: int
    from_id: str = Field(serialization_alias="from")
    to_id: str = Field(serialization_alias="to")


class SkippedRowView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_name: str
    row: int
    reason: str


class SheetPlanView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_name: str
    prefix: str | None
    prefix_source: str | None
    needs_prefix: bool
    group_name: str | None
    existing_group_name: str | None
    name_differs: bool
    row_count: int
    renumbered: list[RenumberedView] = Field(default_factory=list)


class CapacityView(BaseModel):
    """만들 수 있는가 (FR-036a·b).

    파일을 **읽는** 상한과 프로젝트가 **수용하는** 양은 다른 것이다. 이 값이 없으면
    초안을 만들다가 번호가 바닥나 반쯤 만들어진 상태로 끝난다.
    """

    model_config = ConfigDict(extra="forbid")
    needed: int
    available: int
    ok: bool


class ImportPlanView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str
    file_name: str
    expires_at: datetime
    draft_count: int
    group_count: int
    sheets: list[SheetPlanView]
    skipped: list[SkippedRowView]
    capacity: CapacityView
    warnings: list[str]


class CommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(min_length=1, max_length=64)
    prefixes: dict[str, str] = Field(default_factory=dict)
    """`needs_prefix` 인 시트에 대한 답 (FR-022a).

    시트를 빼거나 빈 문자열을 주면 **그 시트를 건너뛴다** (FR-022b).
    """


class CreateProjectImportRequest(CommitRequest):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    default_start_url: str = Field(pattern=r"^https?://", max_length=2000)
    test_id_attribute: str = Field(default="data-testid", min_length=1, max_length=100)


class GroupRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prefix: str
    name: str


class DraftRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_id: str
    name: str
    group_prefix: str
    desired_test_id: str | None


class SkippedSheetView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_name: str
    reason: str


class ImportResultView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    created_groups: list[GroupRef] = Field(default_factory=list)
    reused_groups: list[GroupRef] = Field(default_factory=list)
    drafts: list[DraftRef] = Field(default_factory=list)
    skipped: list[SkippedRowView] = Field(default_factory=list)
    skipped_sheets: list[SkippedSheetView] = Field(default_factory=list)
    renumbered: list[RenumberedView] = Field(default_factory=list)


class CreateProjectImportResult(ImportResultView):
    project: dict[str, object]


def _plan_view(state: AppState, plan: ImportPlan, repo: ProjectRepository | None) -> ImportPlanView:
    """계획을 화면이 읽을 형태로 만든다. **아무것도 만들지 않는다.**"""
    used = _used_ids(repo)
    available = MAX_TEST_NUMBER - len(used)
    needed = plan.draft_count

    sheets: list[SheetPlanView] = []
    renumbered_all: list[RenumberedView] = []
    for sheet in plan.sheets:
        renumbered = [
            RenumberedView(row=r.row, from_id=r.renumbered_from, to_id=r.desired_test_id or "")
            for r in sheet.rows
            if r.renumbered_from is not None
        ]
        renumbered_all.extend(renumbered)
        sheets.append(
            SheetPlanView(
                sheet_name=sheet.sheet_name,
                prefix=sheet.prefix,
                prefix_source=sheet.prefix_source.value if sheet.prefix_source else None,
                needs_prefix=sheet.needs_prefix,
                group_name=sheet.group_name,
                existing_group_name=sheet.existing_group_name,
                name_differs=sheet.name_differs,
                row_count=len(sheet.rows),
                renumbered=renumbered,
            )
        )

    return ImportPlanView(
        plan_id=plan.plan_id,
        file_name=plan.file_name,
        expires_at=state.import_plans.expires_at(plan),
        draft_count=needed,
        group_count=sum(1 for s in plan.sheets if _makes_group(s)),
        sheets=sheets,
        skipped=[
            SkippedRowView(sheet_name=s.sheet_name, row=s.row, reason=s.reason.value)
            for s in plan.skipped
        ],
        capacity=CapacityView(needed=needed, available=available, ok=needed <= available),
        warnings=plan.warnings,
    )


def _makes_group(sheet: SheetPlan) -> bool:
    """이 시트가 그룹을 뜻하는가. 그룹 없음과 접두어 미정은 아니다."""
    return sheet.prefix is not None and sheet.prefix != RESERVED_PREFIX


def _used_ids(repo: ProjectRepository | None) -> set[str]:
    if repo is None:
        return set()
    tests, _problems = repo.list_tests()
    return {t.id for t in tests}


@router.post("/import/preview")
async def preview_import(
    state: State, file: Annotated[UploadFile, File()]
) -> ImportPlanView:
    """파일을 해석해 **계획**을 만든다. 프로젝트에는 아무것도 만들지 않는다 (FR-016).

    열린 프로젝트가 있으면 그것에 비추어 계획한다(기존 그룹·수용량). 없으면 새 프로젝트를
    만들며 가져오는 경우다.
    """
    data = await _read_upload(file)
    repo = state.repository
    project = repo.read_project() if repo else None

    parsed = _parse(data)
    plan = build_plan(
        parsed,
        sanitize_display_name(file.filename),
        project=project,
        taken_ids=_used_ids(repo),
    )
    state.import_plans.put(plan)
    return _plan_view(state, plan, repo)


async def _read_upload(file: UploadFile) -> bytes:
    """업로드를 상한 안에서 읽는다 (FR-036).

    **상한 + 1 바이트만 읽어 초과를 판정한다.** 전체를 메모리에 올린 뒤 재는 것은 상한이
    없는 것과 같다 — `session_files.py` 가 쓰는 수법과 같다.
    """
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise bad_request(
            ErrorCode.IMPORT_FILE_REJECTED,
            f"파일이 상한({MAX_UPLOAD_BYTES // (1024 * 1024)}MB)을 넘습니다.",
            kind="file_bytes",
            limit=MAX_UPLOAD_BYTES,
            actual=len(data),
        )
    return data


def _parse(data: bytes) -> ParsedWorkbook:
    try:
        return read_sheets(data)
    except ArchiveRejected as exc:
        detail: dict[str, object] = {"kind": exc.kind}
        if exc.limit is not None:
            detail["limit"] = exc.limit
        if exc.actual is not None:
            detail["actual"] = exc.actual
        raise bad_request(ErrorCode.IMPORT_FILE_REJECTED, str(exc), **detail) from exc
    except WorkbookError as exc:
        raise bad_request(
            ErrorCode.IMPORT_FILE_REJECTED, str(exc), kind="corrupt"
        ) from exc


# ─── 확정 ──────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class _Materialized:
    """확정이 만든 것들. 되돌릴 때도 이 목록을 쓴다."""

    created_groups: list[GroupRef] = field(default_factory=list)
    reused_groups: list[GroupRef] = field(default_factory=list)
    drafts: list[DraftRef] = field(default_factory=list)
    skipped_sheets: list[SkippedSheetView] = field(default_factory=list)
    renumbered: list[RenumberedView] = field(default_factory=list)


def _resolve_plan(state: AppState, plan_id: str) -> ImportPlan:
    plan = state.import_plans.get(plan_id)
    if plan is None:
        raise bad_request(
            ErrorCode.IMPORT_PLAN_NOT_FOUND,
            "미리보기가 만료됐거나 없습니다.",
        )
    return plan


def _apply_prefixes(plan: ImportPlan, prefixes: dict[str, str]) -> None:
    """사용자가 준 접두어를 계획에 반영한다 (FR-022a·c).

    형식에 맞지 않으면 **확정 전에** 거절한다. 만들다가 거절하면 되돌릴 것이 생긴다.
    """
    for sheet in plan.sheets:
        if not sheet.needs_prefix:
            continue
        given = (prefixes.get(sheet.sheet_name) or "").strip()
        if not given:
            continue  # 비워두면 건너뛴다 (FR-022b)
        problem = validate_prefix(given)
        if problem is not None:
            code = (
                ErrorCode.GROUP_PREFIX_RESERVED
                if given.upper() == RESERVED_PREFIX
                else ErrorCode.DEFINITION_INVALID
            )
            raise bad_request(code, problem, sheet_name=sheet.sheet_name)
        sheet.prefix = given.upper()
        sheet.prefix_source = PrefixSource.USER_SUPPLIED


def _check_capacity(plan: ImportPlan, repo: ProjectRepository) -> None:
    """만들 수 있는지 **아무것도 만들기 전에** 본다 (FR-036b).

    이 검사가 없으면 초안을 만들다가 번호가 바닥나 반쯤 만들어진 상태로 끝난다.
    """
    used = _used_ids(repo)
    needed = sum(len(s.rows) for s in plan.sheets if s.prefix is not None)
    available = MAX_TEST_NUMBER - len(used)
    if needed > available:
        raise bad_request(
            ErrorCode.IMPORT_CAPACITY_EXCEEDED,
            f"만들려는 초안이 {needed}건인데 이 프로젝트에 남은 번호는 {available}개입니다.",
            needed=needed,
            available=available,
        )


def _materialize(plan: ImportPlan, repo: ProjectRepository) -> _Materialized:
    """그룹과 초안을 만든다. **전부 아니면 전무다** (FR-025).

    **순서가 계약이다** (data-model §8):

    1. 그룹을 먼저 쓴다 — 초안이 가리키는 접두어의 그룹이 없으면 목록 화면이 그 초안을
       어디에도 놓지 못한다
    2. 초안을 ``run_all`` 로 만든다 — 기존 삭제·이동과 같은 전부-아니면-전무 규약
    3. 초안이 실패하면 그룹 쓰기도 되돌린다

    "눈에 보이지 않는 흔적이 눈에 보이는 손실보다 낫다" (013 research R5).
    """
    made = _Materialized()

    project = repo.read_project()
    before_groups = list(project.groups)
    known = {g.prefix for g in project.groups}

    new_groups: list[TestGroup] = []
    for sheet in plan.sheets:
        if sheet.prefix is None:
            made.skipped_sheets.append(
                SkippedSheetView(sheet_name=sheet.sheet_name, reason="no_prefix")
            )
            continue
        if not _makes_group(sheet):
            continue
        if sheet.prefix in known:
            # 이미 있는 그룹은 **이름을 그대로 둔다** (FR-024a). 가져오기는 더하는
            # 일이지 고치는 일이 아니다.
            existing = next(g for g in project.groups if g.prefix == sheet.prefix)
            made.reused_groups.append(GroupRef(prefix=existing.prefix, name=existing.name))
            continue
        name = _unique_group_name(sheet.group_name, project.groups, new_groups)
        new_groups.append(TestGroup(prefix=sheet.prefix, name=name))
        known.add(sheet.prefix)
        made.created_groups.append(GroupRef(prefix=sheet.prefix, name=name))

    if new_groups:
        project.groups = [*project.groups, *new_groups]
        repo.write_project(project)

    # ── 초안 (전부 아니면 전무) ──────────────────────────────────────────
    targets: list[tuple[SheetPlan, RowPlan, str]] = []
    reserved: set[str] = set()
    for sheet in plan.sheets:
        if sheet.prefix is None:
            continue
        for row in sheet.rows:
            draft_id = repo.drafts.allocate_id(taken=reserved)
            reserved.add(draft_id)
            targets.append((sheet, row, draft_id))

    def write_one(target: tuple[SheetPlan, RowPlan, str]) -> Draft:
        sheet, row, draft_id = target
        draft = Draft(
            draft_id=draft_id,
            name=row.name,
            description=row.description,
            actor=row.actor,
            procedure=row.procedure,
            expectation=row.expectation,
            desired_test_id=row.desired_test_id,
            group_prefix=sheet.prefix or RESERVED_PREFIX,
            source=DraftSource(
                file_name=plan.file_name, sheet_name=sheet.sheet_name, row=row.row
            ),
        )
        repo.drafts.write(draft)
        return draft

    def undo_one(target: tuple[SheetPlan, RowPlan, str], _made: Draft) -> None:
        repo.drafts.delete(target[2])

    def rollback_groups() -> None:
        if not new_groups:
            return
        current = repo.read_project()
        current.groups = before_groups
        repo.write_project(current)

    try:
        written = run_all(targets, validate=lambda _t: None, do=write_one, undo=undo_one)
    except AllOrNothingError as exc:
        rollback_groups()
        raise ApiError(500, ErrorCode.IMPORT_FAILED, str(exc.reason)) from exc
    except PartialFailureError as exc:
        rollback_groups()
        raise ApiError(
            500,
            ErrorCode.IMPORT_PARTIAL,
            str(exc.reason),
            stranded=[{"target": s.target, "where": s.where} for s in exc.stranded],
        ) from exc

    made.drafts = [
        DraftRef(
            draft_id=d.draft_id,
            name=d.name,
            group_prefix=d.group_prefix,
            desired_test_id=d.desired_test_id,
        )
        for d in written
    ]
    made.renumbered = [
        RenumberedView(row=r.row, from_id=r.renumbered_from, to_id=r.desired_test_id or "")
        for s in plan.sheets
        for r in s.rows
        if r.renumbered_from is not None
    ]
    return made


def _unique_group_name(
    wanted: str, existing: list[TestGroup], pending: list[TestGroup]
) -> str:
    """그룹 이름이 겹치지 않게 한다.

    `Project._check_groups` 가 이름 중복을 거절하므로, 다른 접두어가 같은 이름을 쓰려 하면
    저장 자체가 실패한다. 그때 가져오기 전체를 막는 대신 뒤엣것에 접미를 붙인다 — 사용자가
    나중에 고칠 수 있고, 행을 잃지 않는다.
    """
    taken = {g.name for g in existing} | {g.name for g in pending}
    if wanted not in taken:
        return wanted
    suffix = 2
    while f"{wanted} ({suffix})" in taken:
        suffix += 1
    return f"{wanted} ({suffix})"


def _result_view(plan: ImportPlan, made: _Materialized) -> ImportResultView:
    return ImportResultView(
        created_groups=made.created_groups,
        reused_groups=made.reused_groups,
        drafts=made.drafts,
        skipped=[
            SkippedRowView(sheet_name=s.sheet_name, row=s.row, reason=s.reason.value)
            for s in plan.skipped
        ],
        skipped_sheets=made.skipped_sheets,
        renumbered=made.renumbered,
    )


@router.post("/import/commit", status_code=201)
async def commit_import(body: CommitRequest, state: State) -> ImportResultView:
    """열린 프로젝트로 가져온다. 전부 아니면 전무다 (FR-025)."""
    repo = _repo(state)
    plan = _resolve_plan(state, body.plan_id)

    _apply_prefixes(plan, body.prefixes)
    _check_capacity(plan, repo)

    made = _materialize(plan, repo)
    state.import_plans.drop(plan.plan_id)
    return _result_view(plan, made)


@router.post("/import/create-project", status_code=201)
async def create_project_from_import(
    body: CreateProjectImportRequest, state: State
) -> CreateProjectImportResult:
    """파일에서 **새 프로젝트를 만들며** 가져온다 (FR-014a·b·c).

    **만들다 만 프로젝트를 남기지 않는다.** 가져오기가 실패하면 방금 만든 프로젝트를
    휴지통으로 옮기고 레지스트리에서 지운다 — 지우지 않고 휴지통으로 보내는 것은 013 이
    삭제를 휴지통 이동으로 정한 결정을 그대로 쓰는 것이다.
    """
    plan = _resolve_plan(state, body.plan_id)
    _apply_prefixes(plan, body.prefixes)

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
            f"프로젝트를 만들 수 없습니다: {exc.strerror or exc}.",
        ) from exc

    try:
        _check_capacity(plan, repo)
        made = _materialize(plan, repo)
    except Exception:
        _discard_project(repo)
        raise

    registry.remember(repo.paths.root, project.name, "managed")
    state.repository = repo
    state.import_plans.drop(plan.plan_id)

    base = _result_view(plan, made)
    return CreateProjectImportResult(
        **base.model_dump(),
        project={
            "root": str(repo.paths.root),
            "name": project.name,
            "default_start_url": project.default_start_url,
            "browser": project.browser.value,
            "test_id_attribute": project.test_id_attribute,
            "max_tabs": project.max_tabs,
        },
    )


def _discard_project(repo: ProjectRepository) -> None:
    """만들다 만 프로젝트를 치운다 (FR-014c).

    실패해도 삼킨다 — 여기서 또 예외를 내면 **원래 실패 사유가 가려진다**. 사용자가
    알아야 하는 것은 가져오기가 왜 실패했는가이지, 정리가 왜 실패했는가가 아니다.
    """
    with contextlib.suppress(OSError, ProjectError):
        trash.move_to_trash(repo.paths.root)
    with contextlib.suppress(OSError):
        registry.forget(repo.paths.root)
