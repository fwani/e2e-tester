"""권한 경계. 026 FR-013~FR-017 · SC-005·SC-006 (US3).

이 파일이 고정하는 것은 **넓힌 자리와 넓히지 않은 자리 둘 다**이다. 앞만 보면 016 이
조용히 깨진 것을 놓치고, 뒤만 보면 이 기능이 동작하지 않는 것을 놓친다.

권한 판정식은 `itb.api.routes.sessions` 의 `in_scope` 람다에 있다. 여기서는 그 식을
**같은 모양으로 재현해** 두 트랜잭션의 조합을 전부 확인한다 — 브라우저 없이 돌 수 있고,
조합이 늘어도 값이 싸다. 실제 배선이 이 식을 쓰는지는 `tests/us_step_edit/` 의 통합
검사가 본다.
"""

from __future__ import annotations

import pytest

from itb.authoring.rerecord import RerecordTransaction, validate_range
from itb.authoring.step_edit import StepEditTransaction
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep, Step


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


def in_scope(
    step_id: str,
    steps: list[Step],
    rerecord: RerecordTransaction | None = None,
    step_edit: StepEditTransaction | None = None,
) -> bool:
    """`sessions.py` 의 판정식과 **같은 모양**이다 (026 research R1).

    항이 둘이고 둘째가 026 이 더한 것이다. 첫째 항만 남기면 016 의 판정과 글자 그대로
    같아야 하며, 그것이 FR-014 다.
    """
    return (
        rerecord is not None and not rerecord.settled and rerecord.owns(step_id, steps)
    ) or (
        step_edit is not None and not step_edit.settled and step_edit.owns(step_id, steps)
    )


def open_edit(steps: list[Step], target_id: str) -> StepEditTransaction:
    index = next(i for i, s in enumerate(steps) if s.id == target_id)
    return StepEditTransaction(
        target_id=target_id,
        origin=steps[index],
        arrival_index=index,
        baseline_ids=frozenset(s.id for s in steps),
    )


def open_rerecord(steps: list[Step], ids: list[str]) -> RerecordTransaction:
    rng = validate_range(steps, ids)
    return RerecordTransaction(
        range=rng,
        arrival_index=next(i for i, s in enumerate(steps) if s.id == rng.first),
        baseline_ids=frozenset(s.id for s in steps),
    )


# ─── 넓힌 자리 (FR-013 · SC-005) ────────────────────────────────────────────


def test_the_chosen_step_is_in_scope() -> None:
    steps = steps_of(5)
    tx = open_edit(steps, "step-03")
    assert in_scope("step-03", steps, step_edit=tx) is True


def test_a_step_made_this_session_is_in_scope() -> None:
    steps = steps_of(5)
    tx = open_edit(steps, "step-03")
    steps.append(ClickStep(id="step-06", label="새것", target=target("new")))
    assert in_scope("step-06", steps, step_edit=tx) is True


@pytest.mark.parametrize("sid", ["step-01", "step-02", "step-04", "step-05"])
def test_everything_else_is_refused(sid: str) -> None:
    """**100% 거절이다** (SC-005). 「고른 것만」이 경계다."""
    steps = steps_of(5)
    tx = open_edit(steps, "step-03")
    assert in_scope(sid, steps, step_edit=tx) is False


def test_a_settled_edit_grants_nothing() -> None:
    """끝난 뒤에는 대상조차 고칠 수 없다 (불변식 C)."""
    steps = steps_of(5)
    tx = open_edit(steps, "step-03")
    tx.close()
    assert in_scope("step-03", steps, step_edit=tx) is False


def test_the_scope_is_fixed_when_the_session_starts() -> None:
    """**대화로 범위가 넓어지지 않는다** (FR-017).

    `target_id` 는 트랜잭션이 만들어질 때 정해지고 그것을 바꾸는 연산이 없다. 대화로
    넓힐 수 있으면 사용자는 「지금 AI 가 무엇을 고칠 수 있는가」를 대화 이력을 되짚어야
    알 수 있고, 되돌리기 대상도 흐려진다.
    """
    steps = steps_of(5)
    tx = open_edit(steps, "step-03")
    mutators = [
        name
        for name in dir(tx)
        if not name.startswith("_") and callable(getattr(tx, name))
    ]
    assert set(mutators) == {"created", "can_commit", "owns", "commit", "discard", "close"}, (
        "범위를 바꾸는 연산이 새로 생겼는지 본다 — 생겼다면 FR-017 을 다시 판단해야 한다"
    )


# ─── 넓히지 않은 자리 — FR-014 회귀 (SC-006) ────────────────────────────────


def test_a_session_without_a_chosen_step_behaves_exactly_like_016() -> None:
    """**고른 Step 이 없으면 판정이 016 과 글자 그대로 같다.**

    기존 AI 작성·자연어 Step 추가 경로가 여기 해당한다 — 트랜잭션이 둘 다 없으므로
    아무것도 고칠 수 없다. 「모르는 것을 참으로 보지 않는다」가 기본값이다.
    """
    steps = steps_of(5)
    for s in steps:
        assert in_scope(s.id, steps) is False


def test_a_rerecord_session_is_unchanged() -> None:
    """재녹화 세션에서 026 이 권한을 넓히지 않았다 (FR-014 · FR-030).

    구간 밖은 물론 **교체 대상인 옛 구간도** 여전히 권한 밖이다.
    """
    steps = steps_of(5)
    tx = open_rerecord(steps, ["step-03", "step-04"])

    for sid in ("step-01", "step-02", "step-03", "step-04", "step-05"):
        assert in_scope(sid, steps, rerecord=tx) is False, (
            f"{sid} 이 재녹화에서 고칠 수 있게 됐다 — 016 이 깨졌다"
        )

    steps.append(ClickStep(id="step-06", label="새것", target=target("new")))
    assert in_scope("step-06", steps, rerecord=tx) is True


def test_the_two_transactions_do_not_leak_into_each_other() -> None:
    """한쪽의 권한이 다른 쪽으로 새지 않는다.

    구조적으로 동시에 차지 않지만(세션 모드가 하나다), 판정식이 `or` 이므로 한쪽이
    남아 있을 때 다른 쪽 대상이 열리는지 확인해 둔다.
    """
    steps = steps_of(5)
    edit = open_edit(steps, "step-03")
    rerec = open_rerecord(steps, ["step-01"])

    assert in_scope("step-01", steps, rerecord=rerec) is False
    assert in_scope("step-01", steps, step_edit=edit) is False
    assert in_scope("step-03", steps, rerecord=rerec) is False
    assert in_scope("step-03", steps, step_edit=edit) is True


# ─── 거절문 (FR-015·FR-016) ─────────────────────────────────────────────────


def hint_for(
    rerecord: RerecordTransaction | None = None,
    step_edit: StepEditTransaction | None = None,
) -> str:
    """`sessions.py` 의 `_scope_hint` 와 **같은 모양**이다."""
    if step_edit is not None and not step_edit.settled:
        return (
            f"지금 고칠 수 있는 것은 {step_edit.target_id} (사용자가 고쳐 달라고 "
            "지목한 Step) 과 이번에 당신이 만든 Step 입니다."
        )
    if rerecord is not None and not rerecord.settled:
        return "지금 고칠 수 있는 것은 이번에 당신이 만든 Step 뿐입니다."
    return "지금은 어떤 Step 도 고칠 수 없습니다."


def test_the_hint_names_what_is_allowed() -> None:
    """거절만 받으면 모델은 같은 요청을 반복한다 (FR-016).

    **허용 대상의 식별자가 문장에 들어 있어야** 모델이 그 자리에서 방향을 바꾼다.
    """
    steps = steps_of(5)
    tx = open_edit(steps, "step-03")
    assert "step-03" in hint_for(step_edit=tx)


def test_the_hint_is_honest_when_nothing_is_editable() -> None:
    assert "어떤 Step 도" in hint_for()


def test_the_hint_does_not_promise_the_chosen_step_after_settling() -> None:
    """끝난 뒤에도 대상을 약속하면 모델은 「된다고 했는데 거절당하는」 상태를 만난다."""
    steps = steps_of(5)
    tx = open_edit(steps, "step-03")
    tx.close()
    assert "step-03" not in hint_for(step_edit=tx)
