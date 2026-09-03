"""Step 편집 엔드포인트. FR-035~FR-037·FR-040a~d. contracts/rest-api.md §일시정지 중 편집.

**모두 `PAUSED` 게이트다** (FR-035a). 다른 상태에서 오면 `409 NOT_PAUSED` 로 거절하고
현재 상태를 알린다.

**이미 실행된 Step 편집에 대한 계약** (FR-040a~d): 요청은 **성공한다.** 응답에 경고를 실어
보낸다. 서버는 브라우저에 어떤 명령도 보내지 않는다 — 화면 정상화는 사용자 몫이다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from itb.api.errors import ErrorCode, bad_request, not_found
from itb.api.routes.sessions import SessionWork, require_paused, work_of
from itb.api.state import AppState, get_state
from itb.domain.assertion import Assertion
from itb.domain.step import AssertionStep, Author, Step

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
    """FR-082b — 민감 여부를 사용자가 지정한다."""


class ReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: list[str] = Field(min_length=1)


class AddAssertionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assertion: dict[str, object]
    label: str | None = Field(default=None, min_length=1, max_length=200)
    at: int | None = Field(default=None, ge=0)
    tab: int = Field(default=0, ge=0)


def _warn_if_already_executed(w: SessionWork, index: int) -> None:
    """FR-040b — 편집 지점이 현재 실행 위치보다 이전이면 경고를 세운다.

    브라우저에 어떤 명령도 보내지 않는다. 되돌리지 않는다는 사실을 사용자에게 알리는 것이
    이 함수의 전부다.
    """
    if index < w.current_step_index:
        step_no = index + 1
        w.session.add_edit_warning(
            f"step {step_no:02d} 은 이미 실행된 Step입니다. "
            "이 편집은 현재 브라우저 화면에 적용되지 않았습니다. "
            "화면을 원하는 상태로 만든 뒤 이어서 실행하세요."
        )


async def _response(w: SessionWork) -> StepsResponse:
    """편집 결과 응답. 경고가 있으면 이벤트로도 알린다 (FR-040b)."""
    await w.session.publish_edit_warnings()
    return StepsResponse(
        steps=w.steps,
        edit_warnings=list(w.session.edit_warnings),
        current_step_index=w.current_step_index,
    )


def _find_index(w: SessionWork, step_id: str) -> int:
    for i, s in enumerate(w.steps):
        if s.id == step_id:
            return i
    raise not_found(ErrorCode.DEFINITION_INVALID, f"Step 을 찾을 수 없습니다: {step_id}")


@router.post("/{session_id}/steps")
async def insert_step(
    session_id: str, body: InsertStepRequest
) -> StepsResponse:
    w = work_of(session_id)
    require_paused(w)
    try:
        step = STEP_ADAPTER.validate_python(body.step)
    except Exception as exc:  # noqa: BLE001 - 검증 실패 사유를 그대로 전달한다
        raise bad_request(
            ErrorCode.DEFINITION_INVALID, f"Step 형식이 올바르지 않습니다: {exc}"
        ) from exc

    at = body.at if body.at is not None else w.current_step_index
    at = max(0, min(at, len(w.steps)))
    _warn_if_already_executed(w, at)
    w.steps.insert(at, step)
    if at <= w.current_step_index:
        w.current_step_index += 1
    await w.session.emit("step_added", step=step.model_dump(mode="json"), at_index=at)
    return await _response(w)


@router.patch("/{session_id}/steps/{step_id}")
async def patch_step(
    session_id: str, step_id: str, body: PatchStepRequest
) -> StepsResponse:
    w = work_of(session_id)
    require_paused(w)
    index = _find_index(w, step_id)
    _warn_if_already_executed(w, index)

    current = w.steps[index]
    update: dict[str, object] = {}
    if body.label is not None:
        update["label"] = body.label
    if body.timeout_ms is not None:
        update["timeout_ms"] = body.timeout_ms
    if body.value is not None:
        if not hasattr(current, "value"):
            raise bad_request(
                ErrorCode.DEFINITION_INVALID,
                f"{current.type} Step 은 입력값을 갖지 않습니다.",
            )
        update["value"] = body.value

    updated = current.model_copy(update=update)
    w.steps[index] = updated
    await w.session.emit("step_updated", step=updated.model_dump(mode="json"))
    return await _response(w)


@router.delete("/{session_id}/steps/{step_id}")
async def delete_step(session_id: str, step_id: str) -> StepsResponse:
    """FR-035 — Step 삭제.

    `RunnerPaused` 디자인의 대표 흐름이 **이미 실행 완료된 Step 03 을 삭제**하는 것이다.
    따라서 실행된 Step 삭제를 막지 않는다. 경고만 세운다 (FR-040a).
    """
    w = work_of(session_id)
    require_paused(w)
    index = _find_index(w, step_id)
    _warn_if_already_executed(w, index)
    w.steps.pop(index)
    if index < w.current_step_index:
        w.current_step_index -= 1
    await w.session.emit("step_removed", step_id=step_id)
    return await _response(w)


@router.post("/{session_id}/steps:reorder")
async def reorder_steps(session_id: str, body: ReorderRequest) -> StepsResponse:
    w = work_of(session_id)
    require_paused(w)

    by_id = {s.id: s for s in w.steps}
    if set(body.order) != set(by_id):
        raise bad_request(
            ErrorCode.DEFINITION_INVALID,
            "순서 목록이 현재 Step 집합과 다릅니다. 모든 Step id 를 정확히 한 번씩 넣으세요.",
            expected=sorted(by_id),
            received=body.order,
        )

    # 현재 위치보다 앞으로 옮겨진 Step 이 있으면 경고한다 (FR-040b).
    old_index = {s.id: i for i, s in enumerate(w.steps)}
    for new_i, step_id in enumerate(body.order):
        if old_index[step_id] >= w.current_step_index > new_i:
            _warn_if_already_executed(w, new_i)

    w.steps = [by_id[i] for i in body.order]
    await w.session.emit("steps_reordered", order=body.order)
    return await _response(w)


@router.post("/{session_id}/assertions")
async def add_assertion(
    session_id: str, body: AddAssertionRequest
) -> StepsResponse:
    """FR-037 — FR-013a 의 4종 중 하나를 골라 검증 Step 을 추가한다."""
    w = work_of(session_id)
    require_paused(w)
    try:
        assertion = Assertion.model_validate(body.assertion)
    except Exception as exc:  # noqa: BLE001
        raise bad_request(
            ErrorCode.DEFINITION_INVALID, f"검증 조건이 올바르지 않습니다: {exc}"
        ) from exc

    at = body.at if body.at is not None else w.current_step_index
    at = max(0, min(at, len(w.steps)))
    w.recorder.seed_step_seq(len(w.steps))
    label = body.label or _assertion_label(assertion)
    step = AssertionStep(
        id=f"step-{len(w.steps) + 1:02d}",
        label=label,
        author=Author.HUMAN,
        tab=body.tab,
        assertion=assertion,
    )
    _warn_if_already_executed(w, at)
    w.steps.insert(at, step)
    if at <= w.current_step_index:
        w.current_step_index += 1
    await w.session.emit("step_added", step=step.model_dump(mode="json"), at_index=at)
    return await _response(w)


def _assertion_label(assertion: Assertion) -> str:
    match assertion.kind:
        case "visible":
            return f"{assertion.value or '요소'} 표시 확인"
        case "hidden":
            return f"{assertion.value or '요소'} 사라짐 확인"
        case "text":
            return f"텍스트 {assertion.value!r} 확인"
        case "url":
            return f"주소 {assertion.value!r} 확인"
    return "검증"
