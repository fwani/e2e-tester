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
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, bad_request, not_found
from itb.api.routes._download import content_disposition
from itb.api.state import AppState, get_state
from itb.domain.test_case import Project, Test
from itb.sharing import builder
from itb.sharing.bundle import RequiredValue
from itb.sharing.limits import BUNDLE_MEDIA_TYPE, BUNDLE_SUFFIX
from itb.storage.repository import ProjectError, ProjectRepository, slugify

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
        start_urls=[StartUrlView(**vars(u)) for u in review.start_urls],
        plaintext_values=[PlaintextValueView(**vars(v)) for v in review.plaintext_values],
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
