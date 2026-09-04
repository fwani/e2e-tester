"""Step 편집 엔드포인트. FR-035~FR-037·FR-040a~d·FR-020·FR-082b (T097·T139).

contracts/rest-api.md §일시정지 중 편집.

**모두 `PAUSED` 게이트다** (FR-035a). 다른 상태에서 오면 `409 NOT_PAUSED` 로 거절하고
현재 상태를 알린다.

**이미 실행된 Step 편집에 대한 계약** (FR-040a~d): 요청은 **성공한다.** 응답에 경고를 실어
보낸다. 서버는 브라우저에 어떤 명령도 보내지 않는다 — 화면 정상화는 사용자 몫이다.

편집 연산 자체는 `itb.execution.step_edits` 가 한다. 이 라우터가 하는 일은 세 가지다:
요청 검증, 결과를 세션에 반영, 이벤트 발행. 연산을 여기 두면 브라우저 객체가 손에 닿는
곳에서 편집이 일어나고, "여기서 한 번만 되돌리면" 이 언제든 들어올 수 있다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from itb.api.errors import ErrorCode, bad_request, conflict, not_found
from itb.api.routes.sessions import SessionWork, require_paused, work_of
from itb.api.state import AppState, get_state
from itb.domain.assertion import AssertionKind, MatchMode
from itb.domain.locator import TargetLocator
from itb.domain.step import Author, Step
from itb.domain.test_case import (
    fallback_variable_name,
    make_variable_name,
    variable_reference,
)
from itb.execution.assertion_builder import (
    AssertionTargetError,
    build_assertion,
    build_step,
)
from itb.execution.element_probe import collect_by_selector
from itb.execution.step_edits import (
    EditResult,
    ReorderMismatchError,
    StepNotFoundError,
    ValueNotSupportedError,
    allocate_step_id,
    delete_step,
    find_index,
    insert_step,
    reorder_steps,
    update_step,
)
from itb.recording.repick import PendingRepick, RepickSlot, apply_repick
from itb.secrets.keys import KeyMissingError, load_public
from itb.secrets.store import SecretStore

router = APIRouter(prefix="/api/sessions", tags=["steps"])

State = Annotated[AppState, Depends(get_state)]
STEP_ADAPTER: TypeAdapter[Step] = TypeAdapter(Step)


class StepsResponse(BaseModel):
    """FR-040b — 편집 결과와 함께 경고를 돌려준다."""

    model_config = ConfigDict(extra="forbid")

    steps: list[Step]
    edit_warnings: list[str]
    current_step_index: int


class InsertStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: dict[str, object]
    at: int | None = Field(default=None, ge=0)
    """생략하면 일시정지 위치에 삽입한다."""


class PatchStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=200)
    value: str | None = Field(default=None, max_length=4000)
    timeout_ms: int | None = Field(default=None, ge=1, le=60_000)
    sensitive: bool | None = None
    """FR-082b — 민감 여부를 사용자가 지정한다.

    `true` 로 바꾸면 지금 정의에 남아 있는 평문 값을 변수 참조로 옮기고 공개키로
    봉인한다. 응답에는 값이 실리지 않는다.
    """


class ReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: list[str] = Field(min_length=1)


class AddAssertionRequest(BaseModel):
    """검증 Step 추가 (FR-037).

    **후보 묶음을 클라이언트가 만들지 않는다.** 대상은 셀렉터 하나로 지정하고, 후보
    수집·검증은 제품이 한다 (원칙 IV).
    """

    model_config = ConfigDict(extra="forbid")

    kind: AssertionKind
    target_selector: str | None = Field(default=None, min_length=1, max_length=1000)
    value: str | None = Field(default=None, max_length=4000)
    match: MatchMode = MatchMode.EQUALS
    label: str | None = Field(default=None, min_length=1, max_length=200)
    at: int | None = Field(default=None, ge=0)
    tab: int | None = Field(default=None, ge=0)
    """생략하면 지금 미러가 보고 있는 탭이다."""


class RepickRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: RepickSlot = RepickSlot.TARGET
    """`drag` 는 대상이 둘이므로 어느 쪽을 다시 집는지 지정한다 (T166)."""

    selector: str | None = Field(default=None, min_length=1, max_length=1000)
    """주면 즉시 그 요소로 갱신한다. 생략하면 브라우저에서 클릭할 때까지 대기한다."""


class RepickResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    waiting: bool
    """True 면 브라우저에서 요소를 클릭할 때까지 대기 중이다 (FR-020)."""

    slot: RepickSlot
    steps: list[Step]
    edit_warnings: list[str]
    current_step_index: int
    message: str


# ─── 공통 ───────────────────────────────────────────────────────────────────


def _apply_edit(w: SessionWork, result: EditResult) -> None:
    """편집 결과를 세션에 반영한다. **브라우저에는 아무 명령도 보내지 않는다.**"""
    w.steps = result.steps
    w.current_step_index = result.current_step_index
    for message in result.warnings:
        w.session.add_edit_warning(message)
    if w.runner is not None:
        # 총 개수만 알려 준다. 위치는 편집 연산이 이미 옮겼고 세션이 소유한다 —
        # 여기서 다시 쓰면 실행 중 러너의 전진과 겹쳐 같은 Step 이 두 번 돈다.
        w.runner.retarget(len(w.steps))


async def _response(w: SessionWork) -> StepsResponse:
    """편집 결과 응답. 경고가 있으면 이벤트로도 알린다 (FR-040b)."""
    await w.session.publish_edit_warnings()
    return StepsResponse(
        steps=w.steps,
        edit_warnings=list(w.session.edit_warnings),
        current_step_index=w.current_step_index,
    )


def _index_or_404(w: SessionWork, step_id: str) -> int:
    try:
        return find_index(w.steps, step_id)
    except StepNotFoundError as exc:
        raise not_found(ErrorCode.DEFINITION_INVALID, str(exc)) from exc


def _next_step_id(w: SessionWork) -> str:
    """다음 Step id. 리코더와 같은 할당기를 쓴다 — 번호가 충돌하면 저장이 거절된다."""
    return allocate_step_id(w.steps)


# ─── 삽입·수정·삭제·순서 ───────────────────────────────────────────────────


def _missing_fields(exc: Exception) -> list[str]:
    """검증 실패의 **위치만** 뽑는다. 값은 뽑지 않는다.

    pydantic 오류에는 넘어온 값이 통째로 들어 있다. 그것을 사용자 대면 오류에 실으면
    비밀 값이 화면·로그·저장된 결과로 샌다 (003 EC-005).
    """
    errors = getattr(exc, "errors", None)
    if not callable(errors):
        return []
    out: list[str] = []
    for err in errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if not isinstance(p, int))
        if loc:
            out.append(loc)
    return sorted(set(out))


@router.post("/{session_id}/steps")
async def insert(session_id: str, body: InsertStepRequest) -> StepsResponse:
    w = work_of(session_id)
    require_paused(w)
    try:
        step = STEP_ADAPTER.validate_python(body.step)
    except Exception as exc:  # noqa: BLE001 - 검증 실패 사유를 그대로 전달한다
        # 예외 원문을 그대로 싣지 않는다. pydantic 은 `input_value=...` 에 **넘어온 값을
        # 통째로** 담는데, `fill` Step 이면 그 자리에 사용자가 입력한 비밀번호가 들어간다
        # (003 EC-005·SC-209). 무엇이 잘못됐는지는 필드 이름으로 충분히 알린다.
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            "Step 형식이 올바르지 않습니다.",
            next_action="Step 종류와 필수 항목을 확인한 뒤 다시 시도하세요.",
            fields=_missing_fields(exc),
        ) from exc

    result = insert_step(w.steps, w.current_step_index, step, body.at)
    _apply_edit(w, result)
    await w.session.emit(
        "step_added", step=step.model_dump(mode="json"), at_index=result.at_index
    )
    return await _response(w)


@router.patch("/{session_id}/steps/{step_id}")
async def patch(
    session_id: str, step_id: str, body: PatchStepRequest, state: State
) -> StepsResponse:
    """표시 이름·입력값·타임아웃·민감 여부를 고친다 (FR-035·FR-082b)."""
    w = work_of(session_id)
    require_paused(w)
    _index_or_404(w, step_id)

    try:
        result = update_step(
            w.steps,
            w.current_step_index,
            step_id,
            label=body.label,
            value=body.value,
            timeout_ms=body.timeout_ms,
        )
    except ValueNotSupportedError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    _apply_edit(w, result)

    if body.sensitive:
        _promote_to_sensitive(w, step_id, state)

    updated = w.steps[_index_or_404(w, step_id)]
    await w.session.emit("step_updated", step=updated.model_dump(mode="json"))
    return await _response(w)


def _promote_to_sensitive(w: SessionWork, step_id: str, state: AppState) -> None:
    """FR-082b — 평문 값을 변수 참조로 옮기고 공개키로 봉인한다 (T140).

    **정의에 평문을 남기지 않는다.** 옮긴 뒤의 Step 값은 참조뿐이고, 실제 값은 비밀
    파일의 암호문에 있다. 공개키가 없으면 값을 잃지 않기 위해 **거절**한다 — 참조만
    남기고 값을 버리면 그 Step 은 재실행 불가가 되고 사용자는 값을 다시 알 수 없다.
    """
    index = _index_or_404(w, step_id)
    step = w.steps[index]
    raw = getattr(step, "value", None)
    if not isinstance(raw, str):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"{step.type} Step 은 입력값이 없어 민감으로 지정할 수 없습니다.",
        )
    if raw.startswith("{{") and raw.endswith("}}"):
        return  # 이미 참조다. 다시 옮기지 않는다.

    target = getattr(step, "target", None)
    basis = _name_basis(target)
    name = make_variable_name(basis) or fallback_variable_name(
        len(w.recorder.sensitive_captures) + 1
    )

    repo = state.require_repository()
    try:
        public = load_public(state.key_paths)
    except KeyMissingError as exc:
        raise conflict(
            ErrorCode.KEY_MISSING,
            "공개키가 없어 민감 값을 보관할 수 없습니다. 먼저 키를 만드세요. "
            "값을 잃지 않기 위해 지정을 적용하지 않았습니다.",
        ) from exc

    SecretStore(repo.paths.secrets_file).put(name, raw, public)
    from itb.recording.recorder import SensitiveCapture

    if all(c.variable_name != name for c in w.recorder.sensitive_captures):
        w.recorder.sensitive_captures.append(
            SensitiveCapture(variable_name=name, sealed=True)
        )
    w.steps[index] = step.model_copy(update={"value": variable_reference(name)})


def _name_basis(target: TargetLocator | None) -> str | None:
    """변수 이름의 근거. 요소를 알 수 있는 것 중 가장 안정적인 것부터 본다."""
    if target is None:
        return None
    for value in (
        target.test_id.value if target.test_id else None,
        target.stable_attr.value if target.stable_attr else None,
        target.label.value if target.label else None,
        target.accessible_name,
    ):
        if isinstance(value, str) and value.strip():
            return value
    return None


@router.delete("/{session_id}/steps/{step_id}")
async def remove(session_id: str, step_id: str) -> StepsResponse:
    """FR-035 — Step 삭제.

    `RunnerPaused` 디자인의 대표 흐름이 **이미 실행 완료된 Step 03 을 삭제**하는 것이다
    (quickstart §5 4단계). 따라서 실행된 Step 삭제를 막지 않는다. 경고만 세운다 (FR-040a).
    """
    w = work_of(session_id)
    require_paused(w)
    _index_or_404(w, step_id)
    result = delete_step(w.steps, w.current_step_index, step_id)
    _apply_edit(w, result)
    await w.session.emit("step_removed", step_id=step_id)
    return await _response(w)


@router.post("/{session_id}/steps:reorder")
async def reorder(session_id: str, body: ReorderRequest) -> StepsResponse:
    w = work_of(session_id)
    require_paused(w)
    try:
        result = reorder_steps(w.steps, w.current_step_index, body.order)
    except ReorderMismatchError as exc:
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            str(exc),
            expected=exc.expected,
            received=exc.received,
        ) from exc
    _apply_edit(w, result)
    await w.session.emit("steps_reordered", order=body.order)
    return await _response(w)


# ─── 검증 Step 추가 (FR-037) ───────────────────────────────────────────────


@router.post("/{session_id}/assertions")
async def add_assertion(session_id: str, body: AddAssertionRequest) -> StepsResponse:
    """FR-013a 의 4종 중 하나를 골라 검증 Step 을 추가한다.

    대상 요소를 지정하면 **그 자리에서 후보를 수집·검증한다** (FR-013a·FR-019b).
    찾지 못하면 Step 을 만들지 않는다 — 재실행에서 반드시 실패할 Step 을 만들어 두는
    것이 사용자에게 더 나쁘다.
    """
    w = work_of(session_id)
    require_paused(w)

    tab_index = body.tab if body.tab is not None else w.session.mirrored_tab_index
    handle = w.session.find_tab(tab_index)
    if handle is None or handle.closed:
        raise bad_request(
            ErrorCode.TAB_NOT_FOUND,
            f"탭 {tab_index} 이 열려 있지 않아 대상을 확인할 수 없습니다.",
        )

    try:
        assertion = await build_assertion(
            handle.page,
            body.kind,
            target_selector=body.target_selector,
            value=body.value,
            match=body.match,
            test_id_attribute=w.recorder.test_id_attribute,
        )
    except AssertionTargetError as exc:
        raise bad_request(ErrorCode.DEFINITION_INVALID, str(exc)) from exc
    except ValueError as exc:
        raise bad_request(
            ErrorCode.DEFINITION_INVALID, f"검증 조건이 올바르지 않습니다: {exc}"
        ) from exc

    step = build_step(
        assertion,
        _next_step_id(w),
        label=body.label,
        tab=tab_index,
        author=Author.HUMAN,
    )
    result = insert_step(w.steps, w.current_step_index, step, body.at)
    _apply_edit(w, result)
    await w.session.emit(
        "step_added", step=step.model_dump(mode="json"), at_index=result.at_index
    )
    return await _response(w)


# ─── 다시 집기 (FR-020) ────────────────────────────────────────────────────


@router.post("/{session_id}/steps/{step_id}/repick")
async def repick(session_id: str, step_id: str, body: RepickRequest) -> RepickResponse:
    """"다시 집기" — 대상 요소를 재지정해 후보를 갱신한다 (FR-020, T138·T139).

    `selector` 를 주면 즉시 갱신한다. 생략하면 **브라우저에서 요소를 클릭할 때까지
    대기**하며, 그 클릭은 Step 이 되지 않는다.
    """
    w = work_of(session_id)
    require_paused(w)
    index = _index_or_404(w, step_id)
    step = w.steps[index]
    if not hasattr(step, body.slot.value):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"{step.type} Step 에는 '{body.slot.value}' 대상이 없어 다시 집을 수 없습니다.",
        )

    if body.selector is None:
        w.recorder.repick.sink = _repick_sink(session_id)
        w.recorder.repick.arm(step_id, body.slot)
        await w.session.bring_tab_to_front(w.session.active_tab_index)
        return RepickResponse(
            waiting=True,
            slot=body.slot,
            steps=w.steps,
            edit_warnings=list(w.session.edit_warnings),
            current_step_index=w.current_step_index,
            message="브라우저 창에서 대상 요소를 클릭하세요. 그 클릭은 Step 으로 "
            "기록되지 않습니다.",
        )

    handle = w.session.find_tab(step.tab)
    if handle is None or handle.closed:
        raise bad_request(
            ErrorCode.TAB_NOT_FOUND,
            f"탭 {step.tab} 이 열려 있지 않아 대상을 다시 집을 수 없습니다.",
        )
    target = await collect_by_selector(
        handle.page, body.selector, w.recorder.test_id_attribute
    )
    if target is None:
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            f"대상 요소를 찾지 못해 Step 을 갱신하지 않았습니다: {body.selector}",
        )
    await _replace_target(session_id, PendingRepick(step_id, body.slot), target)
    w = work_of(session_id)
    return RepickResponse(
        waiting=False,
        slot=body.slot,
        steps=w.steps,
        edit_warnings=list(w.session.edit_warnings),
        current_step_index=w.current_step_index,
        message="후보를 다시 수집했습니다.",
    )


def _repick_sink(session_id: str):  # noqa: ANN201 - RepickSink 를 만든다
    async def sink(pending: PendingRepick, target: TargetLocator) -> None:
        await _replace_target(session_id, pending, target)

    return sink


async def _replace_target(
    session_id: str, pending: PendingRepick, target: TargetLocator
) -> None:
    """Step 의 대상 후보를 갈아 끼우고 `step_updated` 를 발행한다.

    **경고를 세우지 않는다.** 다시 집기는 정의를 고치는 것이지 화면에 무언가를 하는 것이
    아니고, 이미 실행된 Step 의 후보를 고치는 것은 다음 실행을 위한 준비다.
    """
    from itb.api.routes.sessions import _WORK

    w = _WORK.get(session_id)
    if w is None:
        return
    try:
        index = find_index(w.steps, pending.step_id)
    except StepNotFoundError:
        return
    updated = apply_repick(w.steps[index], pending.slot, target)
    w.steps[index] = updated  # type: ignore[assignment]
    await w.session.emit("step_updated", step=updated.model_dump(mode="json"))  # type: ignore[attr-defined]
