"""Step 수정 트랜잭션. 026 FR-013·FR-020~FR-022·FR-029 (data-model §1).

이 파일이 고정하는 핵심은 **불변식 B** 다 — 버리면 목록이 시작 전과 id·순서·내용까지
같아진다. 016 은 그것을 「스냅샷 없이」 성립시켰고(research R7), 이 기능은 그 전제를
깨므로 **원본을 보관해서** 성립시킨다. 016 과 갈리는 자리를 함께 확인한다.
"""

from __future__ import annotations

import pytest

from itb.authoring.step_edit import StepEditTransaction, TransactionSettledError
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


def snapshot(steps: list[Step]) -> list[tuple[str, str]]:
    """id 와 내용을 함께 본다. id 만 비교하면 내용이 바뀐 것을 놓친다."""
    return [(s.id, s.model_dump_json()) for s in steps]


def opened(steps: list[Step], target_id: str = "step-03") -> StepEditTransaction:
    index = next(i for i, s in enumerate(steps) if s.id == target_id)
    return StepEditTransaction(
        target_id=target_id,
        origin=steps[index],
        arrival_index=index,
        baseline_ids=frozenset(s.id for s in steps),
    )


# ─── 불변식 A — 권한 범위 (FR-013) ──────────────────────────────────────────


def test_the_chosen_step_is_editable() -> None:
    steps = steps_of(5)
    tx = opened(steps)
    assert tx.owns("step-03", steps) is True


def test_a_step_made_this_session_is_editable() -> None:
    steps = steps_of(5)
    tx = opened(steps)
    steps.append(ClickStep(id="step-06", label="새것", target=target("new")))
    assert tx.owns("step-06", steps) is True


def test_every_other_step_is_out_of_scope() -> None:
    steps = steps_of(5)
    tx = opened(steps)
    for sid in ("step-01", "step-02", "step-04", "step-05"):
        assert tx.owns(sid, steps) is False


def test_an_id_that_is_not_in_the_list_is_out_of_scope() -> None:
    """지워진 Step 을 고치라는 요청은 범위 문제가 아니라 대상 부재다."""
    steps = steps_of(5)
    tx = opened(steps)
    assert tx.owns("step-99", steps) is False


def test_the_chosen_step_stays_editable_even_after_it_was_deleted_and_remade() -> None:
    """대상 id 는 범위의 **정의**다. 목록에 없으면 거짓이지만 돌아오면 참이다."""
    steps = steps_of(5)
    tx = opened(steps)
    removed = [s for s in steps if s.id != "step-03"]
    assert tx.owns("step-03", removed) is False
    assert tx.owns("step-03", steps) is True


# ─── 확정 — 016 과 정반대다 (research R5) ───────────────────────────────────


def test_commit_deletes_nothing() -> None:
    steps = steps_of(5)
    tx = opened(steps)
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))
    held = snapshot(steps)

    result = tx.commit(steps, current_step_index=0)

    assert snapshot(result.steps) == held


def test_commit_is_allowed_even_when_nothing_was_made() -> None:
    """**016 과 갈리는 자리.** 016 은 만든 것이 없으면 확정을 잠근다 (빈 구간 교체는
    조용한 삭제이므로). 여기서는 교체하지 않으므로 그 위험이 없고, 같은 규칙을 베끼면
    「AI 에게 물어만 보고 그만두기」가 막힌다."""
    steps = steps_of(5)
    tx = opened(steps)
    assert tx.can_commit(steps) is True
    tx.commit(steps, current_step_index=0)


# ─── 불변식 B — 버리면 시작 전과 같다 (FR-022·FR-029) ───────────────────────


def test_discard_restores_the_modified_step() -> None:
    steps = steps_of(5)
    before = snapshot(steps)
    tx = opened(steps)
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))

    result = tx.discard(steps, current_step_index=0)

    assert snapshot(result.steps) == before


def test_discard_also_removes_what_was_made_this_session() -> None:
    steps = steps_of(5)
    before = snapshot(steps)
    tx = opened(steps)
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))
    steps.insert(2, ClickStep(id="step-06", label="새것", target=target("new")))

    result = tx.discard(steps, current_step_index=0)

    assert snapshot(result.steps) == before


def test_discard_puts_back_a_step_the_agent_deleted() -> None:
    steps = steps_of(5)
    before = snapshot(steps)
    tx = opened(steps)
    steps = [s for s in steps if s.id != "step-03"]

    result = tx.discard(steps, current_step_index=0)

    assert snapshot(result.steps) == before


def test_discard_is_one_result_not_two_applications() -> None:
    """**부분 적용이 남지 않는다** (research R7). 삭제와 복원이 한 결과로 나온다."""
    steps = steps_of(5)
    before = snapshot(steps)
    tx = opened(steps)
    steps[2] = ClickStep(id="step-03", label="바뀐 이름", target=target("other"))
    steps.append(ClickStep(id="step-06", label="새것", target=target("new")))

    result = tx.discard(steps, current_step_index=0)

    # 결과 하나가 시작 전 상태다 — 중간 상태를 호출자가 볼 일이 없다.
    assert snapshot(result.steps) == before


def test_discard_is_fine_when_nothing_changed() -> None:
    steps = steps_of(5)
    before = snapshot(steps)
    tx = opened(steps)

    result = tx.discard(steps, current_step_index=0)

    assert snapshot(result.steps) == before


# ─── 불변식 C — 끝난 트랜잭션 ───────────────────────────────────────────────


def test_settling_twice_is_refused() -> None:
    """연타 방지. 되맞춤이 도는 중에 한 번 더 눌리면 실행이 겹친다."""
    steps = steps_of(5)
    tx = opened(steps)
    tx.commit(steps, current_step_index=0)
    tx.close()

    with pytest.raises(TransactionSettledError):
        tx.commit(steps, current_step_index=0)
    with pytest.raises(TransactionSettledError):
        tx.discard(steps, current_step_index=0)


def test_a_settled_transaction_cannot_commit() -> None:
    steps = steps_of(5)
    tx = opened(steps)
    tx.close()
    assert tx.can_commit(steps) is False


# ─── 불변식 D — 원본은 바뀌지 않는다 ───────────────────────────────────────


def test_the_origin_does_not_change_no_matter_how_often_the_target_is_edited() -> None:
    steps = steps_of(5)
    tx = opened(steps)
    held = tx.origin.model_dump_json()

    steps[2] = ClickStep(id="step-03", label="한 번", target=target("x"))
    steps[2] = ClickStep(id="step-03", label="두 번", target=target("y"))

    assert tx.origin.model_dump_json() == held


def test_created_is_derived_not_recorded() -> None:
    """만든 것을 기록하지 않고 **도출한다** — 생성 경로가 늘어도 자동으로 덮인다."""
    steps = steps_of(5)
    tx = opened(steps)
    steps.append(ClickStep(id="step-06", label="새것", target=target("new")))
    steps.insert(0, ClickStep(id="step-07", label="또 하나", target=target("new2")))

    assert tx.created(steps) == ["step-07", "step-06"]
