"""테스트 목록·조회·이름 변경·삭제·결과. FR-002~FR-007·FR-016·FR-050~FR-058."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from itb.api.errors import ErrorCode, bad_request, not_found, not_implemented
from itb.api.state import AppState, get_state
from itb.domain.run_result import Outcome, RunResult
from itb.domain.test_case import AuthoringMode, Test
from itb.storage.repository import ProjectError, ResultUnreadableError
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


@router.delete("/{test_id}", status_code=204)
async def delete_test(test_id: str, state: State) -> None:
    repo = state.require_repository()
    try:
        removed = repo.delete_test(test_id)
    except ProjectError as exc:
        raise bad_request(ErrorCode.TEST_NOT_FOUND, str(exc)) from exc
    if not removed:
        raise not_found(ErrorCode.TEST_NOT_FOUND, f"테스트를 찾을 수 없습니다: {test_id}")


@router.get("/{test_id}/result")
async def get_result(test_id: str, state: State) -> RunResult:
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
    return result


@router.get("/{test_id}/result/artifacts/{kind}")
async def get_artifact(
    test_id: str,
    kind: Literal["screenshot", "console", "network", "trace"],
    state: State,
) -> dict[str, str]:
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
    return {"kind": kind, "path": path}
