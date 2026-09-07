"""Step 편집 연산. FR-035·FR-040a~d (T096). 헌법 원칙 III 불변식 3.

**이 모듈은 브라우저를 알지 못한다.** Playwright 를 임포트하지 않고, 세션도 받지 않는다.
받는 것은 Step 목록과 실행 위치뿐이고, 돌려주는 것은 새 목록·새 위치·경고 목록이다.

그 제약이 곧 요구사항이다. 편집은 **테스트 정의만 바꾸고 브라우저에 아무 명령도 보내지
않는다** (FR-040a, data-model §8 불변식 3). 편집 로직이 `Page` 를 손에 들고 있으면 "여기서
한 번만 되돌리면 편할 텐데" 가 언제든 들어올 수 있다. 손에 들지 않게 해 두면 그 유혹이
구조적으로 없다.

경고는 **판정 결과를 문장으로 만든 것**이다 (FR-040b). 편집 지점이 이미 실행된 구간에
있으면, 정의는 바뀌었지만 화면은 그대로라는 사실을 사용자가 알아야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from itb.domain.step import Step


class StepNotFoundError(Exception):
    """편집 대상 Step 이 목록에 없다."""

    def __init__(self, step_id: str) -> None:
        self.step_id = step_id
        super().__init__(f"Step 을 찾을 수 없습니다: {step_id}")


class ReorderMismatchError(Exception):
    """순서 목록이 현재 Step 집합과 다르다.

    부분 적용하지 않는다 — 절반만 옮긴 목록은 사용자가 의도한 어떤 상태도 아니다.
    """

    def __init__(self, expected: list[str], received: list[str]) -> None:
        self.expected = expected
        self.received = received
        super().__init__(
            "순서 목록이 현재 Step 집합과 다릅니다. "
            "모든 Step id 를 정확히 한 번씩 넣으세요."
        )


class ValueNotSupportedError(Exception):
    """입력값을 갖지 않는 Step 종류에 값을 지정했다."""

    def __init__(self, step_type: str) -> None:
        self.step_type = step_type
        super().__init__(f"{step_type} Step 은 입력값을 갖지 않습니다.")


class FieldNotSupportedError(Exception):
    """그 Step 종류가 갖지 않는 필드를 고치려 했다 (006 FR-183).

    `ValueNotSupportedError` 와 갈라 두지 않고 하나로 합칠 수도 있었지만, 기존 예외의
    메시지("입력값을 갖지 않습니다")가 이미 세션 편집 계약에 나가 있다. 그것을 일반화하면
    이미 나간 문구가 바뀐다.
    """

    def __init__(self, step_type: str, field: str) -> None:
        self.step_type = step_type
        self.field = field
        super().__init__(f"{step_type} Step 은 {field} 를 갖지 않습니다.")


@dataclass(slots=True)
class EditResult:
    """편집 결과. 원본을 바꾸지 않고 새 상태를 돌려준다.

    호출자(라우터)가 세션에 반영하고 이벤트를 발행한다 — 이벤트 발행을 이 모듈에 두면
    다시 세션을 알아야 하고, 그러면 브라우저와의 거리가 좁아진다.
    """

    steps: list[Step]
    current_step_index: int
    warnings: list[str] = field(default_factory=list)
    at_index: int = 0
    """삽입·수정이 일어난 위치. 이벤트 페이로드의 `at_index` 가 된다."""


def allocate_step_id(steps: list[Step]) -> str:
    """다음 Step id 를 만든다. **이미 쓰인 번호를 피한다.**

    개수만 세면 충돌한다. 리코더가 매긴 번호와 편집으로 추가한 번호가 같은 목록에 섞이고,
    목록 중간이 삭제되면 번호가 촘촘하지 않게 된다 — `step-01, step-02, step-05` 상태에서
    개수+1 은 `step-04` 를 만들지만 그다음 호출은 다시 `step-04` 를 만든다.

    Step id 중복은 저장 시점에 `Test` 검증이 잡지만, 그때는 사용자가 이미 작업을 끝낸
    뒤다. 만드는 순간에 피하는 것이 맞다.
    """
    used = {s.id for s in steps}
    number = len(steps) + 1
    while f"step-{number:02d}" in used:
        number += 1
    return f"step-{number:02d}"


def already_executed_warning(index: int) -> str:
    """FR-040b 의 경고 문장. 한 곳에서만 만든다.

    문장이 여러 곳에서 만들어지면 같은 상황에 다른 안내가 나가고, 사용자는 두 상황이
    다른 것이라고 읽는다.
    """
    return (
        f"step {index + 1:02d} 은 이미 실행된 Step입니다. "
        "이 편집은 현재 브라우저 화면에 적용되지 않았습니다. "
        "화면을 원하는 상태로 만든 뒤 이어서 실행하세요."
    )


def _clamp(at: int | None, current: int, size: int) -> int:
    """삽입 위치를 목록 범위 안으로 맞춘다. 생략하면 일시정지 위치다."""
    target = current if at is None else at
    return max(0, min(target, size))


def insert_step(
    steps: list[Step], current_step_index: int, step: Step, at: int | None = None
) -> EditResult:
    """Step 을 삽입한다 (FR-035).

    `at` 을 생략하면 **일시정지 위치**에 넣는다 — 사용자가 지금 보고 있는 지점이다
    (FR-036·FR-079 가 같은 규칙을 쓴다).
    """
    index = _clamp(at, current_step_index, len(steps))
    warnings = [already_executed_warning(index)] if index < current_step_index else []
    new_steps = [*steps[:index], step, *steps[index:]]
    # 실행 위치는 "다음에 실행할 Step" 이다. 일시정지 위치에 넣은 Step 은 **아직 수행되지
    # 않은 정의**이므로 그것이 다음에 실행될 것이 되어야 한다 — 위치를 밀면 사용자가 방금
    # 넣은 Step 이 조용히 건너뛰어진다. 앞쪽에 넣은 경우만 인덱스가 밀린다.
    #
    # 직접 동작 추가(FR-036)로 기록된 Step 은 **이미 수행된** 것이므로 규칙이 다르다.
    # 그 경로는 리코더 sink 가 실행 위치를 따로 전진시킨다.
    new_index = current_step_index + 1 if index < current_step_index else current_step_index
    return EditResult(new_steps, new_index, warnings, at_index=index)


def find_index(steps: list[Step], step_id: str) -> int:
    for i, s in enumerate(steps):
        if s.id == step_id:
            return i
    raise StepNotFoundError(step_id)


def update_step(
    steps: list[Step],
    current_step_index: int,
    step_id: str,
    *,
    label: str | None = None,
    value: str | None = None,
    timeout_ms: int | None = None,
    tab: int | None = None,
    url: str | None = None,
    assertion_value: str | None = None,
) -> EditResult:
    """표시 이름·입력값·타임아웃·탭·주소·기대값을 고친다 (FR-035·FR-082b·006 FR-183).

    Step 종류를 바꾸지 않는다. 종류가 바뀌면 대상 요소의 의미도 바뀌므로 그것은 삭제와
    삽입이며, 편집으로 위장하면 후보 묶음이 엉뚱한 종류에 남는다.

    **006 이 인자를 늘렸다** — `tab`·`url`·`assertion_value`. 정의 편집(세션 없는 편집)이
    이 세 가지를 요구하는데(006 FR-183), 그것을 위한 두 번째 편집 함수를 만들면 규칙이 두
    벌이 된다. 편집 핵심은 한 곳이므로 인자를 여기 더한다 (006 research R2·R3).

    **`target` 을 받지 않는 것은 의도다.** 요소 후보는 살아 있는 페이지에서만 수집·검증되며
    (헌법 원칙 IV), 손으로 넣은 후보는 검증 상태를 얻을 수 없다. 다시 집기는
    `itb.recording.repick` 이 담당한다 (006 FR-187 제외 결정).
    """
    index = find_index(steps, step_id)
    current = steps[index]

    update: dict[str, object] = {}
    if label is not None:
        update["label"] = label
    if timeout_ms is not None:
        update["timeout_ms"] = timeout_ms
    if tab is not None:
        update["tab"] = tab
    if value is not None:
        if not hasattr(current, "value"):
            raise ValueNotSupportedError(str(current.type))
        update["value"] = value
    if url is not None:
        if not hasattr(current, "url"):
            raise FieldNotSupportedError(str(current.type), "url")
        update["url"] = url
    if assertion_value is not None:
        assertion = getattr(current, "assertion", None)
        if assertion is None:
            raise FieldNotSupportedError(str(current.type), "assertion_value")
        update["assertion"] = assertion.model_copy(update={"value": assertion_value})

    updated = current.model_copy(update=update)
    new_steps = [*steps]
    new_steps[index] = updated
    warnings = [already_executed_warning(index)] if index < current_step_index else []
    return EditResult(new_steps, current_step_index, warnings, at_index=index)


def delete_step(
    steps: list[Step], current_step_index: int, step_id: str
) -> EditResult:
    """Step 을 삭제한다 (FR-035).

    **이미 실행된 Step 도 삭제할 수 있다.** `RunnerPaused` 디자인의 대표 흐름이 실행이
    끝난 Step 03 을 지우는 것이다 (quickstart §5 4단계). 막지 않고 경고만 세운다.
    """
    index = find_index(steps, step_id)
    warnings = [already_executed_warning(index)] if index < current_step_index else []
    new_steps = [*steps[:index], *steps[index + 1 :]]
    new_index = current_step_index - 1 if index < current_step_index else current_step_index
    return EditResult(new_steps, max(0, new_index), warnings, at_index=index)


def reorder_steps(
    steps: list[Step], current_step_index: int, order: list[str]
) -> EditResult:
    """Step 순서를 바꾼다 (FR-035).

    **경고 판정은 "이미 실행된 구간이 달라졌는가" 다.** 실행 위치 앞의 순서가 그대로면
    화면 상태와 정의가 여전히 맞고, 달라졌으면 맞지 않는다. 개별 Step 이 얼마나 움직였는지
    세는 것보다 이 판정이 사용자가 알아야 하는 것에 정확히 대응한다.
    """
    by_id = {s.id: s for s in steps}
    if sorted(order) != sorted(by_id):
        raise ReorderMismatchError(sorted(by_id), list(order))

    executed_before = [s.id for s in steps[:current_step_index]]
    executed_after = order[:current_step_index]
    warnings: list[str] = []
    if executed_before != executed_after:
        first_change = next(
            (
                i
                for i, (a, b) in enumerate(zip(executed_before, executed_after, strict=False))
                if a != b
            ),
            0,
        )
        warnings.append(already_executed_warning(first_change))

    return EditResult([by_id[i] for i in order], current_step_index, warnings)
