"""테스트 목록·조회·이름 변경·삭제·결과. FR-002~FR-007·FR-016·FR-050~FR-058."""

from __future__ import annotations

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
from itb.domain.run_result import Outcome, RunResult, RunScope
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
    delete_step,
    reorder_steps,
    update_step,
)
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

    # 결과 파일의 경로는 프로젝트 루트 기준 상대 경로다. 루트 밖을 가리키면 — 결과 파일이
    # 손으로 고쳐졐 경우다 — 서빙하지 않는다 (FR-085 의 경계와 같은 이유).
    root = repo.paths.root.resolve()
    file = (root / path).resolve() if not pathlib.Path(path).is_absolute() else pathlib.Path(path)
    if root not in file.parents:
        raise bad_request(ErrorCode.INVALID_PATH, f"{kind} 산출물 경로가 프로젝트 밖을 가리킵니다.")
    if not file.is_file():
        raise not_found(
            ErrorCode.TEST_NOT_FOUND,
            f"{kind} 산출물 파일이 없습니다: {path}",
            next_action="실행 산출물(.runs/)이 지워졌을 수 있습니다. 다시 실행하면 새로 남습니다.",
        )
    return FileResponse(file, media_type=_ARTIFACT_MEDIA_TYPE[kind])


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

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if all(
            getattr(self, f) is None
            for f in ("label", "value", "timeout_ms", "tab", "url", "assertion_value")
        ):
            msg = "update 연산은 고칠 필드를 최소 하나 지정해야 합니다."
            raise ValueError(msg)
        return self


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
    UpdateStepOp | DeleteStepOp | ReorderOp | SetNameOp | SetStartUrlOp,
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
            return (
                "주소 이동 Step 이 뒤로 밀렸습니다. 로그인 같은 선행 상태가 필요한 Step 이 "
                "앞으로 왔을 수 있습니다 — 저장 후 「처음부터 실행」으로 확인하세요."
            )
    return None


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
            if isinstance(op, UpdateStepOp):
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
