"""테스트 목록·조회·이름 변경·삭제·결과. FR-002~FR-007·FR-016·FR-050~FR-058."""

from __future__ import annotations

import contextlib
import pathlib
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from itb.api.errors import (
    ApiError,
    ErrorCode,
    bad_request,
    conflict,
    not_found,
    not_implemented,
)
from itb.api.state import AppState, get_state
from itb.domain.manual_step import (
    CloseTabSpec,
    ManualStepSpec,
    NavigateSpec,
    build_step,
)
from itb.domain.run_result import Outcome, RunResult, RunScope
from itb.domain.step import Step
from itb.domain.test_case import (
    AuthoringMode,
    Test,
    Variable,
    derive_variables,
    undefined_variable_references,
    variable_reference,
)
from itb.execution.step_edits import (
    FieldNotSupportedError,
    ReorderMismatchError,
    StepNotFoundError,
    ValueNotSupportedError,
    allocate_step_id,
    delete_step,
    insert_step,
    reorder_steps,
    update_step,
)
from itb.storage import test_moves, trash
from itb.storage.repository import (
    ProjectError,
    ProjectRepository,
    ResultUnreadableError,
)
from itb.storage.yaml_io import DefinitionError

router = APIRouter(prefix="/api/tests", tags=["tests"])

State = Annotated[AppState, Depends(get_state)]


class FailureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_index: int
    message: str


class TestListRow(BaseModel):
    """`TestList` 화면 한 행 (FR-002·FR-005)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    step_count: int
    authoring_mode: AuthoringMode
    outcome: Outcome | None = None
    last_run_at: str | None = None
    failure_summary: FailureSummary | None = None


class TestCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    passed: int = Field(serialization_alias="pass")
    failed: int = Field(serialization_alias="fail")


class TestListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    counts: TestCounts
    tests: list[TestListRow]
    problems: list[str] = Field(default_factory=list)
    """읽을 수 없는 정의 파일의 사유. 깨진 파일 하나가 목록을 막지 않는다."""


class RenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class DeleteTestsRequest(BaseModel):
    """복수 삭제 (013 FR-426·FR-432 · contracts/api-contract.md §3).

    **`DELETE` 에 본문을 싣지 않는다.** 프록시·클라이언트에 따라 벗겨지고, 쿼리에 실으면
    목록이 길 때 URL 길이에 걸리며 삭제 대상이 접근 로그에 남는다. `POST …:delete` 는
    011 이 Step 복수 삭제에서 정한 형태이고 이 저장소가 이미 쓴다.
    """

    model_config = ConfigDict(extra="forbid")

    test_ids: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(min_length=1)


class TrashedTestView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    trashed_to: str
    """옮겨진 자리. **이 값이 되돌리는 방법 전부다** (FR-437a)."""


class DeleteTestsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted: list[TrashedTestView]


@router.get("")
async def list_tests(
    state: State,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> TestListResponse:
    repo = state.require_repository()
    tests, problems = repo.list_tests()

    rows: list[TestListRow] = []
    passed = failed = 0
    for t in tests:
        # 목록에서는 깨진 결과 파일 하나가 전체를 막지 않게 사유만 모은다 (FR-087).
        result, problem = repo.try_read_result(t.id)
        if problem is not None:
            problems.append(problem)
        outcome = result.outcome if result else None
        if outcome is Outcome.PASS:
            passed += 1
        elif outcome is Outcome.FAIL:
            failed += 1

        summary: FailureSummary | None = None
        if result and result.outcome is Outcome.FAIL and result.failed_step_index is not None:
            failing = next(
                (s for s in result.steps if s.index == result.failed_step_index), None
            )
            summary = FailureSummary(
                step_index=result.failed_step_index,
                message=(failing.error_message if failing and failing.error_message else "실패"),
            )

        rows.append(
            TestListRow(
                id=t.id,
                name=t.name,
                step_count=len(t.steps),
                authoring_mode=t.authoring_mode,
                outcome=outcome,
                last_run_at=result.finished_at.isoformat() if result else None,
                failure_summary=summary,
            )
        )

    if q:
        needle = q.strip().lower()
        rows = [r for r in rows if needle in r.name.lower() or needle in r.id.lower()]

    return TestListResponse(
        counts=TestCounts(total=len(tests), passed=passed, failed=failed),
        tests=rows,
        problems=problems,
    )


@router.get("/{test_id}")
async def get_test(test_id: str, state: State) -> Test:
    repo = state.require_repository()
    try:
        return repo.read_test(test_id)
    except ProjectError as exc:
        raise not_found(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc
    except DefinitionError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc


@router.patch("/{test_id}")
async def rename_test(test_id: str, body: RenameRequest, state: State) -> Test:
    repo = state.require_repository()
    try:
        test = repo.read_test(test_id)
    except ProjectError as exc:
        raise not_found(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc
    updated = test.model_copy(update={"name": body.name})
    repo.write_test(updated)
    return updated


@router.delete("/{test_id}")
async def delete_test(test_id: str, state: State) -> TrashedTestView:
    """테스트 하나를 **휴지통으로 옮긴다** (013 FR-437 · contracts/api-contract.md §2).

    **204 를 버린 것이 이 계약의 핵심 변경이다.** 옮겨진 위치를 돌려주지 않으면 사용자는
    되돌릴 수 없고, 그러면 「파괴하지 않는다」는 결정이 사용자에게는 삭제와 구별되지 않는다.

    **복수 삭제와 뜻이 같아야 한다** (SC-632). 같은 이름의 조작이 개수에 따라 결과가
    달라지면 사용자는 「삭제」 하나를 두 가지로 배워야 한다.
    """
    repo = state.require_repository()
    _require_test_exists(repo, test_id)
    _require_not_running(state, test_id)

    try:
        trashed = trash.move_test_to_trash(repo, test_id)
    except OSError as exc:
        raise ApiError(500, ErrorCode.TEST_DELETE_FAILED, str(exc)) from exc

    return TrashedTestView(
        id=test_id, name=_name_of(repo, test_id, trashed), trashed_to=str(trashed.entry)
    )


@router.post(":delete")
async def delete_tests(body: DeleteTestsRequest, state: State) -> DeleteTestsResponse:
    """여러 테스트를 한 번에 휴지통으로 옮긴다 (013 FR-432 · api-contract §3).

    **전부 되거나 전부 안 되거나.** 순서 규약은 `storage/test_moves.py` 가 갖는다 —
    삭제와 그룹 이동이 그것을 공유하므로, 여기에 두면 두 벌이 되고 한쪽만 고치면 다른
    쪽에서 되돌림이 빠진다.

    실패를 **두 코드로 가른다**: `TEST_DELETE_FAILED` 는 되돌렸으므로 요청 전과 같고,
    `TEST_DELETE_PARTIAL` 은 되돌리지 못해 일부가 휴지통에 남아 있다. 사용자가 할 일이
    다르다 — 앞은 다시 시도하면 되고 뒤는 자리를 확인해야 한다.
    """
    repo = state.require_repository()
    if len(set(body.test_ids)) != len(body.test_ids):
        raise bad_request(ErrorCode.DEFINITION_INVALID, "같은 테스트가 두 번 들어 있습니다.")

    names = {tid: _name_of(repo, tid, None) for tid in body.test_ids}

    def validate(test_id: str) -> None:
        _require_test_exists(repo, test_id)
        _require_not_running(state, test_id)

    try:
        moved = test_moves.run_all(
            body.test_ids,
            validate=validate,
            do=lambda tid: trash.move_test_to_trash(repo, tid),
            undo=lambda _tid, trashed: trash.restore_test(repo, trashed),
        )
    except test_moves.PartialFailureError as exc:
        raise ApiError(
            500,
            ErrorCode.TEST_DELETE_PARTIAL,
            exc.reason,
            {"stranded": [{"test": s.target, "where": s.where} for s in exc.stranded]},
        ) from exc
    except test_moves.AllOrNothingError as exc:
        raise ApiError(500, ErrorCode.TEST_DELETE_FAILED, exc.reason) from exc

    return DeleteTestsResponse(
        deleted=[
            TrashedTestView(id=t.test_id, name=names[t.test_id], trashed_to=str(t.entry))
            for t in moved
        ]
    )


# ─── 013 공용 도우미 ────────────────────────────────────────────────────────


def _require_test_exists(repo: ProjectRepository, test_id: str) -> None:
    try:
        found = repo.find_test_path(test_id)
    except ProjectError as exc:
        raise not_found(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc
    if found is None:
        raise not_found(ErrorCode.TEST_NOT_FOUND, f"테스트를 찾을 수 없습니다: {test_id}")


def _require_not_running(state: AppState, test_id: str) -> None:
    """살아 있는 세션이 있으면 거절한다 (013 FR-433).

    **거절은 요청을 받지 않은 것과 같아야 한다** — 브라우저를 닫지 않는다 (헌법 원칙 III).
    판정은 이미 있는 `active_session_for_test` 를 쓴다. 새 목록을 만들면 상태가 늘 때
    한쪽이 빠진다.
    """
    if state.sessions.active_session_for_test(test_id) is not None:
        raise ApiError(
            409,
            ErrorCode.TEST_IN_USE,
            f"실행 중인 브라우저가 있어 「{test_id}」을(를) 정리할 수 없습니다.",
        )


def _name_of(repo: ProjectRepository, test_id: str, trashed: object) -> str:
    """표시 이름. **읽지 못해도 실패하지 않는다.**

    이름 하나를 못 읽는다고 삭제를 막으면 깨진 테스트일수록 지울 수 없어진다.
    """
    with contextlib.suppress(Exception):
        return repo.read_test(test_id).name
    return test_id


class RunResultView(RunResult):
    """실행 결과 + 보조 문맥 (005 FR-152).

    `RunResult` 를 그대로 확장하므로 기존 클라이언트가 읽던 필드는 모두 그대로다.
    """

    last_full_run: RunResult | None = None
    """최근 **전체** 실행 (005 FR-152).

    부분 실행 결과 화면이 "최근 전체 실행: 5 / 7 통과" 를 함께 보여주기 위한 것이다.
    이전에는 부분 실행이 전체 실행 결과를 덮어써서, 사용자는 `5 / 7` → `0 / 7` 을 보고
    "고치다 더 망가뜨렸다" 고 읽었다 (U-02).

    이번 실행이 전체이면 `None` 이다 — 같은 것을 두 번 보여줄 이유가 없다.
    """


@router.get("/{test_id}/result")
async def get_result(test_id: str, state: State) -> RunResultView:
    """최근 실행 결과.

    **"결과 없음" 과 "결과를 읽을 수 없음" 을 구분한다.** 손상된 파일을 없는 것처럼
    보고하면 사용자는 방금 한 실행이 사라진 줄 안다 (FR-087, 헌법 §보안).
    """
    repo = state.require_repository()
    try:
        result = repo.read_result(test_id)
    except ResultUnreadableError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    if result is None:
        raise not_found(
            ErrorCode.TEST_NOT_FOUND,
            f"{test_id} 의 실행 결과가 없습니다. 먼저 실행하세요.",
        )
    # 005 FR-152 — 부분 실행일 때만 최근 전체 실행을 함께 준다.
    #
    # 보조 표시가 없어도 주 결과는 온다. `read_full_result` 는 읽기 실패를 예외로 만들지
    # 않는다 — 보조 때문에 결과를 못 보게 하면 고치려던 것보다 나쁘다.
    full = repo.read_full_result(test_id) if result.scope is RunScope.PARTIAL else None
    return RunResultView(**result.model_dump(), last_full_run=full)


_ARTIFACT_MEDIA_TYPE = {
    "screenshot": "image/png",
    "console": "text/plain; charset=utf-8",
    "network": "text/plain; charset=utf-8",
}


@router.get("/{test_id}/result/artifacts/{kind}")
async def get_artifact(
    test_id: str,
    kind: Literal["screenshot", "console", "network", "trace"],
    state: State,
) -> FileResponse:
    """산출물 **내용**을 돌려준다 — 경로가 아니다 (UX U-03).

    예전에는 ``{"kind", "path"}`` JSON 을 돌려줬다. 화면은 그 경로를 ``<img src>`` 에
    넣어 깨진 이미지를 그렸고, 로그 탭은 ``.runs/TC-001/console.log`` 라는 상대 경로 한
    줄만 보여줬다. 결과 화면의 나머지는 다 살아 있는데 눈으로 확인하는 증거만 전부
    죽어 있었다. 사용자는 프로젝트 폴더 절대 경로를 따로 기억해 파인더로 찾아야 했다.
    """
    repo = state.require_repository()
    if kind == "trace":
        # MVP 미지원. `TRACE` 탭은 비활성으로 표시한다 (spec 디자인 차이 1).
        raise not_implemented(
            ErrorCode.NOT_SUPPORTED,
            "실행 추적(Trace)은 이번 범위에 없습니다. TRACE 탭은 비활성입니다.",
        )
    try:
        result = repo.read_result(test_id)
    except ResultUnreadableError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    if result is None:
        raise not_found(ErrorCode.TEST_NOT_FOUND, f"{test_id} 의 실행 결과가 없습니다.")
    mapping = {
        "screenshot": result.artifacts.failure_screenshot,
        "console": result.artifacts.console_log,
        "network": result.artifacts.network_log,
    }
    path = mapping[kind]
    if path is None:
        raise not_found(ErrorCode.TEST_NOT_FOUND, f"{kind} 산출물이 없습니다.")

    file = _artifact_file(repo.paths.root, path, kind)
    return FileResponse(file, media_type=_ARTIFACT_MEDIA_TYPE[kind])


def _artifact_file(root: pathlib.Path, path: str, what: str) -> pathlib.Path:
    """상대 경로를 실제 파일로 바꾸되 **프로젝트 밖은 거절한다**.

    결과 파일의 경로는 프로젝트 루트 기준 상대 경로다. 루트 밖을 가리키면 — 결과 파일이
    손으로 고쳐진 경우다 — 서빙하지 않는다 (FR-085 의 경계와 같은 이유).

    **011 이 함수로 뽑았다.** Step 별 화면 서빙이 같은 검사를 필요로 했고, 복제하면 한쪽만
    고쳐지는 날이 온다 — 그날 프로젝트 밖 파일이 나간다 (api-contract §3).
    """
    resolved = root.resolve()
    file = (
        (resolved / path).resolve()
        if not pathlib.Path(path).is_absolute()
        else pathlib.Path(path)
    )
    if resolved not in file.parents:
        raise bad_request(ErrorCode.INVALID_PATH, f"{what} 산출물 경로가 프로젝트 밖을 가리킵니다.")
    if not file.is_file():
        raise not_found(
            ErrorCode.TEST_NOT_FOUND,
            f"{what} 산출물 파일이 없습니다: {path}",
            next_action="실행 산출물(.runs/)이 지워졌을 수 있습니다. 다시 실행하면 새로 남습니다.",
        )
    return file


@router.get("/{test_id}/result/steps/{index}/screenshot")
async def get_step_screenshot(test_id: str, index: int, state: State) -> FileResponse:
    """그 Step 이 끝난 시점의 화면 (011 FR-390 · api-contract §3).

    **`kind` 를 늘리지 않았다.** `GET …/result/artifacts/{kind}` 는 실행 전체에 하나씩인
    산출물을 위한 것이고 `kind` 별 media type 표가 그 전제 위에 있다. Step 별은 인덱스를
    갖는 다른 성질이라, `kind` 에 넣으면 인덱스를 실을 자리가 없다.

    **없음의 사유를 실어 보낸다** (FR-391·FR-396b). 「없습니다」만 돌려주면 화면은 민감 값
    때문에 남기지 않은 것과 촬영이 실패한 것을 구분할 수 없다.
    """
    repo = state.require_repository()
    if index < 0:
        raise bad_request(ErrorCode.DEFINITION_INVALID, "Step 번호는 0 이상이어야 합니다.")
    try:
        result = repo.read_result(test_id)
    except ResultUnreadableError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    if result is None:
        raise not_found(
            ErrorCode.TEST_NOT_FOUND,
            f"{test_id} 의 실행 결과가 없습니다. 먼저 실행하세요.",
        )
    if index >= len(result.steps):
        raise not_found(
            ErrorCode.TEST_NOT_FOUND,
            f"이 실행에는 Step 이 {len(result.steps)}개뿐입니다.",
        )

    step = result.steps[index]
    if step.screenshot is None:
        raise not_found(
            ErrorCode.TEST_NOT_FOUND,
            step.screenshot_note or "이 Step 의 화면이 남아 있지 않습니다.",
            next_action="다시 실행하면 이 실행의 화면이 새로 남습니다.",
        )
    file = _artifact_file(repo.paths.root, step.screenshot, "화면")
    return FileResponse(file, media_type="image/png")


# ─── 정의 편집 (006) ────────────────────────────────────────────────────────
#
# **왜 여기 있는가**: 저장된 테스트를 고치는 길이 세션에만 있었다. Step 을 바꾸는 API 가
# 전부 `/api/sessions/{id}/steps*` 이어서, 오탈자 하나를 고치려고 브라우저를 띄우고 대상
# 앱에 접속해야 했다 (006 E-08·E-09).
#
# **편집 규칙을 여기서 다시 만들지 않는다.** 연산은 `itb.execution.step_edits` 가 하고
# (그 모듈은 Playwright 를 임포트하지 않는다), 변수 파생은
# `itb.domain.test_case.derive_variables()` 가 한다. 세션 편집과 **같은 함수**다 —
# 두 벌이면 한쪽에서 규칙이 어긋난다 (006 research R2·R3·R5).
#
# **요청은 편집 결과가 아니라 편집 연산 목록이다.** 결과를 받으면 "어느 Step 종류가 값을
# 갖는가" 같은 판정이 화면으로 넘어가고, 그것이 두 번째 구현이 된다 (research R3).
#
# **언어모델을 부르지 않는다** (헌법 원칙 II, FR-210). 이 절의 어떤 경로도 작성(authoring)
# 계층에 닿지 않는다.


class UpdateStepOp(BaseModel):
    """Step 하나의 편집 가능한 필드를 고친다 (FR-183).

    **locator 관련 필드가 없는 것은 의도다.** 요소 후보는 살아 있는 페이지에서만 수집·검증
    되고(헌법 원칙 IV), 손으로 넣은 후보는 검증 상태를 얻을 수 없다. 그것을 `verified` 로
    적으면 거짓말이고, 아니면 조용히 무효인 편집이 된다 (FR-187 제외 결정, research R6).
    다시 집기는 살아 있는 세션의 `/steps/{id}/repick` 이 담당한다.

    **평문 민감 값을 받는 필드도 없다.** `value` 에는 참조(`{{NAME}}`)가 들어올 수 있을
    뿐이고, 실제 값은 비밀 값 엔드포인트가 다룬다 (FR-212·FR-215, research R10).
    """

    model_config = ConfigDict(extra="forbid")

    op: Literal["update"]
    step_id: str = Field(min_length=1, max_length=100)
    label: str | None = Field(default=None, min_length=1, max_length=200)
    value: str | None = Field(default=None, max_length=4000)
    timeout_ms: int | None = Field(default=None, ge=1, le=60_000)
    tab: int | None = Field(default=None, ge=0)
    url: str | None = Field(default=None, min_length=1, max_length=2000)
    assertion_value: str | None = Field(default=None, max_length=4000)
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    """올릴 파일의 이름 (2026-09-09 · `upload` Step).

    세션 편집(`PATCH /sessions/{id}/steps/{step_id}`)과 **같은 칸을 갖는다.** 한쪽에만
    두면 「세션에서는 고칠 수 있는데 편집 화면에서는 못 고치는」 필드가 생기고, 006 이
    두 편집 경로를 하나의 `update_step` 으로 모은 이유가 무너진다.
    """

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if all(
            getattr(self, f) is None
            for f in (
                "label",
                "value",
                "timeout_ms",
                "tab",
                "url",
                "assertion_value",
                "file_name",
            )
        ):
            msg = "update 연산은 고칠 필드를 최소 하나 지정해야 합니다."
            raise ValueError(msg)
        return self


class InsertStepOp(BaseModel):
    """Step 을 목록의 임의 위치에 넣는다 (009 FR-285 · 계약 §4-1).

    **세션 없는 편집에 삽입이 없던 것이 비대칭이었다.** 같은 화면에서 삭제와 순서 변경은
    되는데 추가만 안 됐다 (009 관찰 M-02). 006 이 그것을 뺀 근거는 원칙 IV 였고 그 판단은
    옳았다 — 다만 요소를 요구하지 **않는** 종류까지 함께 빠졌다 (M-11).

    ``spec`` 이 판별 유니온이므로 요소를 요구하는 종류는 **여기 도달하지 못한다.** 런타임
    검사가 아니라 타입이 막는다 (``itb.domain.manual_step``).

    ``at`` 은 **그 위치 앞**이다. 범위를 벗어나면 거절한다 — `insert_step` 은 클램프하지만
    (일시정지 위치를 기준으로 쓰이는 함수라서) 정의 편집에서 조용히 다른 자리에 넣는 것은
    사용자가 의도한 어떤 상태도 아니다.
    """

    model_config = ConfigDict(extra="forbid")

    op: Literal["insert"]
    at: int = Field(ge=0)
    spec: ManualStepSpec


class DeleteStepOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["delete"]
    step_id: str = Field(min_length=1, max_length=100)


class ReorderOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["reorder"]
    order: list[str] = Field(min_length=1)


class SetNameOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["set_name"]
    name: str = Field(min_length=1, max_length=200)


class SetStartUrlOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: Literal["set_start_url"]
    url: str = Field(min_length=1, max_length=2000)


EditOp = Annotated[
    InsertStepOp | UpdateStepOp | DeleteStepOp | ReorderOp | SetNameOp | SetStartUrlOp,
    Field(discriminator="op"),
]


class SaveDefinitionRequest(BaseModel):
    """편집 저장 요청 (FR-193·FR-209).

    `revision` 은 `GET /definition` 이 준 값이다. 되돌려 보내지 않으면 저장할 수 없다 —
    바탕이 바뀐 것을 모르고 덮어쓰는 경로를 만들지 않는다. "강제" 플래그는 두지 않는다:
    플래그는 습관이 되고, 습관이 되면 감지가 무의미해진다.
    """

    model_config = ConfigDict(extra="forbid")

    revision: str = Field(min_length=1, max_length=64)
    edits: list[EditOp] = Field(min_length=1)


class LockedField(BaseModel):
    """이 화면에서 고칠 수 없는 항목과 그 이유 (FR-191).

    `reason` 은 **문구 키**다. 문장은 화면이 만든다 — 서버가 UI 문구를 정하면 어휘 사전을
    한 곳에 모아 둔 규칙이 깨진다.
    """

    model_config = ConfigDict(extra="forbid")

    field: str
    reason: Literal[
        "live_browser_required", "delete_and_insert_instead", "record_only"
    ]


LOCKED_FIELDS: tuple[LockedField, ...] = (
    LockedField(field="steps[].target", reason="live_browser_required"),
    LockedField(field="steps[].drop_target", reason="live_browser_required"),
    LockedField(field="steps[].assertion.target", reason="live_browser_required"),
    LockedField(field="steps[].type", reason="delete_and_insert_instead"),
    LockedField(field="steps[].author", reason="record_only"),
    LockedField(field="ai_instruction", reason="record_only"),
)
"""편집 불가 항목의 **유일한 근거** (data-model §1 의 편집 가능 표).

화면이 이 목록을 따로 갖지 않게 서버가 준다. 두 곳에 두면 표가 갈리고, 갈린 표는
"눌러도 아무 일이 없는 칸" 을 만든다.
"""


class DefinitionView(BaseModel):
    """편집을 위한 정의 조회 응답 (FR-182·FR-206).

    `revision` 을 `Test` 안에 넣지 않는 이유: `Test` 는 저장되는 DSL 모델이고 파일 해시는
    파일의 성질이다. 넣으면 저장할 때 자기 해시를 자기 안에 적는 순환이 된다.
    """

    model_config = ConfigDict(extra="forbid")

    test: Test
    revision: str
    editable: bool
    blocked_by: Literal["running"] | None = None
    blocking_session_id: str | None = None
    """화면이 「실행 중인 세션 보기」 버튼을 만들기 위한 것.

    사용자에게 보이는 문장에는 세션 식별자를 넣지 않는다 (005 FR-135).
    """

    locked_fields: list[LockedField] = Field(default_factory=lambda: list(LOCKED_FIELDS))
    warnings: list[str] = Field(default_factory=list)
    """저장을 막지 않는 것들 (FR-216 · 순서 변경 경고). 막는 것은 오류로 낸다."""


def _view_of(
    test: Test, revision: str, blocking_session_id: str | None, warnings: list[str]
) -> DefinitionView:
    return DefinitionView(
        test=test,
        revision=revision,
        editable=blocking_session_id is None,
        blocked_by="running" if blocking_session_id is not None else None,
        blocking_session_id=blocking_session_id,
        locked_fields=list(LOCKED_FIELDS),
        warnings=warnings,
    )


def _read_for_edit(test_id: str, state: AppState) -> tuple[Test, str]:
    """정의와 지문을 함께 읽는다. **브라우저를 만들지 않는다** (FR-182)."""
    repo = state.require_repository()
    try:
        test = repo.read_test(test_id)
        revision = repo.definition_revision(test_id)
    except ProjectError as exc:
        raise not_found(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc
    except DefinitionError as exc:
        # 깨진 파일을 반쯤 읽어 저장해 더 망가뜨리지 않는다 (FR-196).
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    return test, revision


@router.get("/{test_id}/definition")
async def get_definition(test_id: str, state: State) -> DefinitionView:
    """편집을 위한 정의 조회 (FR-182).

    **실행 중이어도 200 이다.** 화면은 열리고 읽기 전용으로 그려진다 (FR-206) — 못 열게
    하면 사용자는 무엇이 실행 중인지도 볼 수 없다.
    """
    test, revision = _read_for_edit(test_id, state)
    return _view_of(test, revision, state.sessions.reservation_for_test(test_id), [])


def _sensitive_names(test: Test) -> set[str]:
    return {v.name for v in test.variables if v.sensitive}


def _value_before(test: Test, step_id: str) -> str | None:
    for step in test.steps:
        if step.id == step_id:
            return getattr(step, "value", None)
    return None


def _reject_plaintext_over_secret(test: Test, op: UpdateStepOp) -> None:
    """민감 참조를 평문 리터럴로 바꾸는 편집을 거절한다 (FR-213 · data-model V6).

    **판정 기준**: 편집 *전* 값이 `{{NAME}}` 이고 그 `NAME` 이 민감 변수인 경우만 본다.
    비민감 변수 참조를 평문으로 바꾸는 것은 정상 편집이므로 막지 않는다.
    """
    if op.value is None:
        return
    before = _value_before(test, op.step_id)
    if before is None:
        return
    sensitive = _sensitive_names(test)
    was_secret_ref = any(before == variable_reference(name) for name in sensitive)
    if not was_secret_ref:
        return
    if any(op.value == variable_reference(name) for name in sensitive):
        return  # 다른 민감 변수 참조로 바꾸는 것은 허용한다
    raise bad_request(
        ErrorCode.DEFINITION_INVALID,
        "민감 값은 정의 파일에 평문으로 넣을 수 없습니다.",
        next_action="값 자체는 「비밀 값」 화면에서 바꾸세요. 여기서는 참조만 다룹니다.",
        step_id=op.step_id,
    )


def _reorder_warning(before: list[str], after: list[str], test: Test) -> str | None:
    """순서 변경이 선행 상태를 깰 수 있다는 경고 (명세 Edge Case · research Q1).

    **막지 않는다.** 순서 변경 자체는 정상 편집이고, 무엇이 선행 상태인지는 대상 앱마다
    다르므로 제품이 단정할 수 없다. 규칙은 얕게 시작한다 — `navigate` Step 이 뒤로
    밀렸는지만 본다. 규칙이 늘어나면 별도 결정으로 다룬다.
    """
    kinds = {s.id: str(s.type) for s in test.steps}
    for step_id, kind in kinds.items():
        if kind != "navigate":
            continue
        if before.index(step_id) < after.index(step_id):
            return NAVIGATE_MOVED_BACK
    return None


NAVIGATE_MOVED_BACK = (
    "주소 이동 Step 이 뒤로 밀렸습니다. 로그인 같은 선행 상태가 필요한 Step 이 "
    "앞으로 왔을 수 있습니다 — 저장 후 「처음부터 실행」으로 확인하세요."
)
"""순서가 바뀌어 선행 상태가 깨질 수 있다는 경고. **한 곳에서만 만든다.**

순서 변경(`_reorder_warning`)과 삽입(`_insert_warnings`)이 같은 상황을 만들 수 있으므로
문장을 공유한다. 두 곳에서 만들면 같은 상황에 다른 안내가 나가고, 사용자는 두 상황이 다른
것이라고 읽는다.
"""


def _insert_warnings(steps: list[Step], op: InsertStepOp) -> list[str]:
    """삽입이 남기는 경고 (009 FR-312). **저장을 막지 않는다.**

    막지 않는 이유는 `_reorder_warning` 과 같다 — 무엇이 선행 상태인지는 대상 앱마다
    다르므로 제품이 단정할 수 없다. 규칙은 얕게 시작한다.

    `close_tab` 의 탭 번호를 저장 시점에 막지 않는 이유: 번호의 유효성이 **실행 흐름**에
    달려 있다. 앞선 Step 이 새 탭을 열면 유효해지고, 그 판단은 정의만 봐서는 못 한다.
    """
    notes: list[str] = []
    if isinstance(op.spec, CloseTabSpec) and op.spec.tab > 0:
        opened = {s.tab for s in steps[: op.at]}
        if op.spec.tab not in opened:
            notes.append(
                f"탭 {op.spec.tab} 은 이 자리까지의 Step 에 나오지 않습니다. "
                "실행할 때 그 탭이 없으면 이 Step 에서 실패합니다 — "
                "저장 후 「처음부터 실행」으로 확인하세요."
            )
    if isinstance(op.spec, NavigateSpec) and 0 < op.at < len(steps):
        notes.append(NAVIGATE_MOVED_BACK)
    return notes


def _apply_edits(test: Test, edits: list[EditOp]) -> tuple[Test, list[str]]:
    """편집 연산을 정의에 적용한다 (V4 · research R3).

    **연산은 `itb.execution.step_edits` 가 한다.** 이 함수가 하는 일은 연산을 그 모듈에
    넘기고 결과를 모으는 것뿐이다.

    `current_step_index=0` 으로 부른다 — 정의 편집에는 실행 위치가 없으므로 "이미 실행된
    구간을 고쳤다" 경고가 하나도 생기지 않는다. 그래서 그 모듈을 고치지 않고 쓸 수 있다.

    **전부 또는 전무다.** 하나라도 실패하면 예외가 올라가고 호출자는 파일을 쓰지 않는다 —
    절반 적용된 정의는 사용자가 의도한 어떤 상태도 아니다.
    """
    steps = list(test.steps)
    name = test.name
    start_url = test.start_url
    warnings: list[str] = []

    for op in edits:
        try:
            if isinstance(op, InsertStepOp):
                if op.at > len(steps):
                    raise bad_request(
                        ErrorCode.DEFINITION_INVALID,
                        f"넣을 위치가 범위를 벗어났습니다: {op.at} (Step {len(steps)}개)",
                        next_action="목록에서 넣을 자리를 다시 고른 뒤 저장하세요.",
                    )
                for note in _insert_warnings(steps, op):
                    if note not in warnings:
                        warnings.append(note)
                # id 는 서버가 매긴다 — 쓰인 번호를 피하는 규칙이 한 곳에 있다 (research R6).
                step = build_step(op.spec, allocate_step_id(steps))
                # `current_step_index=0` 은 다른 연산과 같다. 정의 편집에는 실행 위치가 없다.
                steps = insert_step(steps, 0, step, op.at).steps
            elif isinstance(op, UpdateStepOp):
                _reject_plaintext_over_secret(test, op)
                steps = update_step(
                    steps,
                    0,
                    op.step_id,
                    label=op.label,
                    value=op.value,
                    timeout_ms=op.timeout_ms,
                    tab=op.tab,
                    url=op.url,
                    assertion_value=op.assertion_value,
                    file_name=op.file_name,
                ).steps
            elif isinstance(op, DeleteStepOp):
                steps = delete_step(steps, 0, op.step_id).steps
            elif isinstance(op, ReorderOp):
                before = [s.id for s in steps]
                steps = reorder_steps(steps, 0, op.order).steps
                note = _reorder_warning(before, [s.id for s in steps], test)
                if note is not None and note not in warnings:
                    warnings.append(note)
            elif isinstance(op, SetNameOp):
                name = op.name
            else:
                start_url = op.url
        except StepNotFoundError as exc:
            raise bad_request(
                ErrorCode.DEFINITION_INVALID, str(exc), step_id=exc.step_id
            ) from exc
        except (ValueNotSupportedError, FieldNotSupportedError) as exc:
            raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
        except ReorderMismatchError as exc:
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                str(exc),
                expected=exc.expected,
                received=exc.received,
            ) from exc

    if not steps:
        raise bad_request(
            ErrorCode.STEP_LIST_EMPTY,
            "Step 이 없는 테스트는 저장할 수 없습니다.",
            next_action="삭제를 되돌리거나 Step 을 추가한 뒤 다시 저장하세요.",
        )

    variables = derive_variables(
        steps,
        base_variables=test.variables,
        sealed_names={v.name for v in test.variables if v.sensitive},
    )
    try:
        updated = test.model_copy(
            update={
                "name": name,
                "start_url": start_url,
                "steps": steps,
                "variables": [Variable.model_validate(v) for v in variables],
                "updated_at": datetime.now(UTC),
            }
        )
        # `model_copy` 는 검증을 다시 돌리지 않는다. 저장 전에 한 번 더 통과시킨다 (V7).
        updated = Test.model_validate(updated.model_dump(mode="json"))
    except ValidationError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc

    undefined = undefined_variable_references(updated.steps, updated.variables)
    for missing in undefined:
        warnings.append(
            f"{variable_reference(missing)} 을 참조하지만 그 변수의 값이 정의되지 "
            "않았습니다. 실행하면 빈 값이 채워집니다."
        )
    return updated, warnings


@router.put("/{test_id}/definition")
async def save_definition(
    test_id: str, body: SaveDefinitionRequest, state: State
) -> DefinitionView:
    """편집 저장 (FR-193). 검증 순서는 data-model §4 표 그대로다.

    V1 요청 형태(모델이 이미 했다) → V2 `revision` → V3 실행 중 → V4 연산 적용 →
    V5 Step 1개 이상 → V6 민감 참조 → V7 `Test` 검증 → V8 변수 파생 → V9 경고.
    """
    repo = state.require_repository()
    test, revision = _read_for_edit(test_id, state)

    # V2 — 읽은 뒤에 파일이 밖에서 바뀌었는가 (FR-209).
    if body.revision != revision:
        raise conflict(
            ErrorCode.DEFINITION_STALE,
            "이 테스트의 정의 파일이 편집을 시작한 뒤에 바뀌었습니다.",
            test_id=test_id,
            revision=revision,
            test=test.model_dump(mode="json"),
        )

    # V3 — 실행 중인 정의를 밑에서 바꾸지 않는다 (FR-207). 판정 근거는 005 의 예약 하나다.
    held = state.sessions.reservation_for_test(test_id)
    if held:
        raise conflict(
            ErrorCode.SESSION_ALREADY_ACTIVE,
            f"{test_id} 가 지금 실행 중입니다.",
            next_action="실행이 끝난 뒤에 저장하세요.",
            test_id=test_id,
            session_id=held,
        )

    updated, warnings = _apply_edits(test, body.edits)

    try:
        repo.write_test(updated)
    except ProjectError as exc:
        # 조용히 넘기지 않는다 (FR-198).
        raise bad_request(ErrorCode.STORAGE_WRITE_FAILED, str(exc)) from exc
    except OSError as exc:
        raise ApiError(
            status_code=500,
            code=ErrorCode.STORAGE_WRITE_FAILED,
            message=f"정의 파일을 저장하지 못했습니다: {exc}",
        ) from exc

    return _view_of(updated, repo.definition_revision(test_id), None, warnings)
