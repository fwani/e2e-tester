"""`restore_step` — 대상 하나를 시작 시점 모습으로 되돌린다. 026 FR-020·FR-022.

이 함수가 있어야 하는 진짜 이유는 **AI 가 대상 Step 을 지울 수 있기 때문**이다
(026 research R3). 지워진 Step 은 「교체」로 돌아오지 않는다. 두 경우를 한 함수가 다루지
않으면 되돌리기 규칙이 라우터에 살게 되고, 그것이 헌법 원칙 I 이 금지하는 두 번째
구현이다.
"""

from __future__ import annotations

from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep, Step
from itb.execution.step_edits import restore_step


def target(name: str) -> TargetLocator:
    return TargetLocator(
        role="button",
        accessible_name=name,
        css=Candidate(value=f"button.{name}", status=CandidateStatus.VERIFIED),
    )


def steps_of(n: int) -> list[Step]:
    return [
        ClickStep(id=f"step-{i + 1:02d}", label=f"동작 {i + 1}", target=target(f"b{i + 1}"))
        for i in range(n)
    ]


def snapshot(steps: list[Step]) -> list[tuple[str, str]]:
    return [(s.id, s.model_dump_json()) for s in steps]


# ─── 경우 1: 대상이 목록에 있다 (고쳐졌다) ──────────────────────────────────


def test_a_modified_step_is_replaced_in_place() -> None:
    steps = steps_of(5)
    origin = steps[2]
    before = snapshot(steps)

    # AI 가 라벨과 대상을 고쳤다.
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))

    result = restore_step(steps, current_step_index=0, origin=origin, at_index=2)

    assert snapshot(result.steps) == before
    assert result.at_index == 2


def test_restoring_keeps_the_step_identifier() -> None:
    """식별자가 유지된다 (FR-029). 고치는 것이지 갈아 끼우는 것이 아니다."""
    steps = steps_of(5)
    origin = steps[2]
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))

    result = restore_step(steps, current_step_index=0, origin=origin, at_index=2)

    assert [s.id for s in result.steps] == [f"step-0{i}" for i in range(1, 6)]


def test_restoring_does_not_touch_other_steps() -> None:
    steps = steps_of(5)
    origin = steps[2]
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))

    result = restore_step(steps, current_step_index=0, origin=origin, at_index=2)

    assert snapshot(result.steps[:2]) == snapshot(steps_of(5)[:2])
    assert snapshot(result.steps[3:]) == snapshot(steps_of(5)[3:])


# ─── 경우 2: 대상이 목록에 없다 (AI 가 지웠다) ──────────────────────────────


def test_a_deleted_step_is_put_back_at_its_place() -> None:
    """**이 경우가 이 함수의 존재 이유다.** 교체로는 돌아오지 않는다."""
    full = steps_of(5)
    origin = full[2]
    steps = [s for s in full if s.id != "step-03"]

    result = restore_step(steps, current_step_index=0, origin=origin, at_index=2)

    assert snapshot(result.steps) == snapshot(full)


def test_putting_back_clamps_when_the_list_got_shorter() -> None:
    """그 사이 뒤쪽이 지워져 자리가 없어졌으면 목록 끝에 놓는다."""
    full = steps_of(5)
    origin = full[4]
    steps = full[:2]

    result = restore_step(steps, current_step_index=0, origin=origin, at_index=4)

    assert [s.id for s in result.steps] == ["step-01", "step-02", "step-05"]


# ─── 공통 성질 ──────────────────────────────────────────────────────────────


def test_the_original_list_is_not_mutated() -> None:
    """`EditResult` 는 새 상태를 돌려준다 — 원본을 바꾸지 않는다."""
    steps = steps_of(5)
    origin = steps[2]
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))
    held = snapshot(steps)

    restore_step(steps, current_step_index=0, origin=origin, at_index=2)

    assert snapshot(steps) == held


def test_restoring_an_executed_step_warns() -> None:
    """이미 지나온 자리를 되돌리면 정의와 화면이 어긋난다 — 기존 규칙 그대로."""
    steps = steps_of(5)
    origin = steps[1]
    steps[1] = ClickStep(id="step-02", label="바뀐 이름", target=target("other"))

    result = restore_step(steps, current_step_index=3, origin=origin, at_index=1)

    assert result.warnings
