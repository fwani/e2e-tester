"""엑셀 통로 엔드포인트 (기능 014 · contracts/rest-api.md).

내보내기는 여기, 가져오기도 여기. 초안 조회·삭제는 :mod:`itb.api.routes.drafts` 가 맡는다.
"""

from __future__ import annotations

import datetime as dt
import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, bad_request, not_found
from itb.api.state import AppState, get_state
from itb.domain.run_result import Outcome
from itb.portability import exporter
from itb.portability.limits import XLSX_MEDIA_TYPE
from itb.portability.sheet_name import SheetRename
from itb.portability.workbook import WorkbookError, write_workbook
from itb.storage.repository import ProjectRepository, slugify

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
