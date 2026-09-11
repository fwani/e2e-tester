"""구간 교체 트랜잭션. 016 FR-015·FR-016·FR-026~FR-030 (T007, research R7).

이 파일이 고정하는 핵심은 **불변식 9** 다 — 버리면 목록이 시작 전과 id·순서·내용까지
같아진다. 그것이 성립하는 이유는 스냅샷이 있어서가 아니라 **불변식 8**(AI 는 자기가 만든
것만 고친다) 때문이며, 두 불변식의 관계를 여기서 함께 확인한다.
"""

from __future__ import annotations

import pytest

from itb.authoring.rerecord import (
    EmptyRangeError,
    NothingCreatedError,
    RangeNotContiguousError,
    RerecordTransaction,
    TransactionSettledError,
    validate_range,
)
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep, Step
from itb.execution.step_edits import StepNotFoundError


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


# ─── 구간 검증 (FR-015·FR-016) ──────────────────────────────────────────────


def test_a_contiguous_range_is_accepted() -> None:
    steps = steps_of(10)
    rng = validate_range(steps, ["step-04", "step-05", "step-06"])
    assert rng.step_ids == ("step-04", "step-05", "step-06")
    assert rng.first == "step-04"
    assert len(rng) == 3


def test_the_order_the_user_clicked_does_not_matter() -> None:
    """화면의 체크 순서는 사용자가 누른 순서다. 목록 순서로 정규화한다."""
    steps = steps_of(10)
    rng = validate_range(steps, ["step-06", "step-04", "step-05"])
    assert rng.step_ids == ("step-04", "step-05", "step-06")


def test_a_gap_is_rejected() -> None:
    """사이가 비면 거절한다 (FR-016).

    도착점이 하나여야 하기 때문이다 — 3번과 7번을 고르면 화면을 어디로 되돌릴지 정할 수
    없고, 사이에 낀 4~6 을 새 Step 과 어떻게 이을지도 정의되지 않는다.
    """
    steps = steps_of(10)
    with pytest.raises(RangeNotContiguousError):
        validate_range(steps, ["step-03", "step-07"])


def test_a_single_step_is_a_valid_range() -> None:
    """한 개짜리 구간도 연속이다. Step 하나만 다시 만드는 것은 흔한 일이다."""
    assert len(validate_range(steps_of(5), ["step-03"])) == 1


def test_the_whole_list_is_a_valid_range() -> None:
    steps = steps_of(4)
    assert len(validate_range(steps, [s.id for s in steps])) == 4


def test_an_empty_range_is_rejected() -> None:
    with pytest.raises(EmptyRangeError):
        validate_range(steps_of(5), [])


def test_a_duplicate_is_rejected() -> None:
    """같은 Step 을 두 번 고른 것도 거절한다. `delete_steps` 와 같은 규칙이다."""
    with pytest.raises(RangeNotContiguousError):
        validate_range(steps_of(5), ["step-02", "step-02"])


def test_an_unknown_id_is_rejected_by_the_existing_rule() -> None:
    """존재 검증은 `find_index` 에 맡긴다 — 규칙을 두 곳에 두지 않는다."""
    with pytest.raises(StepNotFoundError):
        validate_range(steps_of(5), ["step-99"])


# ─── 확정 (FR-026·FR-028·불변식 10) ─────────────────────────────────────────


def tx(steps: list[Step], ids: list[str], arrival: int) -> RerecordTransaction:
    """트랜잭션을 만든다. **시작 시점 id 집합을 함께 굳힌다.**

    그것이 「이번 세션이 만든 것」의 정의다 — 생성 지점마다 기록하지 않고 도출한다
    (`baseline_ids` 주석: 생성 경로가 둘이고 하나를 놓치면 조용히 깨진다).
    """
    return RerecordTransaction(
        range=validate_range(steps, ids),
        arrival_index=arrival,
        baseline_ids=frozenset(s.id for s in steps),
    )


def test_commit_removes_the_old_range_in_one_go() -> None:
    """옛 구간이 한 번에 사라지고 앞뒤가 이어진다 (FR-026)."""
    steps = steps_of(8)
    t = tx(steps, ["step-04", "step-05"], arrival=3)

    # 새 Step 두 개가 4번 자리에 들어왔다고 본다.
    new_a = ClickStep(id="step-09", label="새 1", target=target("n1"))
    new_b = ClickStep(id="step-10", label="새 2", target=target("n2"))
    working = [*steps[:3], new_a, new_b, *steps[3:]]

    result = t.commit(working, current_step_index=3)
    ids = [s.id for s in result.steps]

    assert ids == [
        "step-01",
        "step-02",
        "step-03",
        "step-09",
        "step-10",
        "step-06",
        "step-07",
        "step-08",
    ]


def test_commit_is_refused_when_nothing_was_created() -> None:
    """빈 것으로 교체하는 것은 구간 삭제이지 재녹화가 아니다 (FR-028 · 불변식 10)."""
    steps = steps_of(6)
    t = tx(steps, ["step-03"], arrival=2)
    assert t.can_commit(steps) is False
    with pytest.raises(NothingCreatedError):
        t.commit(steps, current_step_index=2)


def test_can_commit_turns_true_once_something_is_made() -> None:
    steps = steps_of(6)
    t = tx(steps, ["step-03"], arrival=2)
    assert t.can_commit(steps) is False

    working = [*steps, ClickStep(id="step-07", label="새", target=target("n"))]
    assert t.can_commit(working) is True


# ─── 버리기 (FR-027 · 불변식 9) ─────────────────────────────────────────────


def test_discard_restores_the_list_exactly() -> None:
    """**불변식 9** — 버리면 시작 전과 id·순서·내용까지 같다 (SC-004)."""
    steps = steps_of(8)
    before = snapshot(steps)
    t = tx(steps, ["step-04", "step-05"], arrival=3)

    made = [
        ClickStep(id="step-09", label="새 1", target=target("n1")),
        ClickStep(id="step-10", label="새 2", target=target("n2")),
        ClickStep(id="step-11", label="새 3", target=target("n3")),
    ]
    working = [*steps[:3], *made, *steps[3:]]

    result = t.discard(working, current_step_index=3)
    assert snapshot(result.steps) == before


@pytest.mark.parametrize("round_no", range(20))
def test_discard_restores_exactly_every_time(round_no: int) -> None:
    """20회 반복해도 매번 같다 (SC-004).

    반복 검사인 이유는 이것이 **신뢰의 기반**이기 때문이다. 스무 번 중 한 번이라도
    목록이 달라지면 사용자는 버리기를 누르지 못하고, 누르지 못하면 시행착오 루프가
    성립하지 않는다 — 이 기능의 값 전체가 거기 걸려 있다.
    """
    steps = steps_of(6 + (round_no % 5))
    before = snapshot(steps)
    t = tx(steps, ["step-03", "step-04"], arrival=2)

    made = [
        ClickStep(id=f"step-{90 + i}", label=f"새 {i}", target=target(f"n{i}"))
        for i in range(1 + round_no % 4)
    ]
    working = [*steps[:2], *made, *steps[2:]]

    result = t.discard(working, current_step_index=2)
    assert snapshot(result.steps) == before


def test_discard_with_nothing_created_is_allowed() -> None:
    """아무것도 만들지 않은 채 그만두는 것은 정상이다. 확정과 다른 점이다."""
    steps = steps_of(5)
    before = snapshot(steps)
    t = tx(steps, ["step-02"], arrival=1)
    result = t.discard(steps, current_step_index=1)
    assert snapshot(result.steps) == before


def test_a_step_the_ai_deleted_simply_stops_existing() -> None:
    """AI 가 자기가 만든 Step 을 지워도 되돌리기가 깨지지 않는다.

    **기록 방식이었다면 문제가 됐다** — 지워진 id 가 목록에 남아 버리기가 없는 것을
    지우려 들고, `delete_steps` 가 전부-또는-전무로 거절해 되돌리기 자체가 실패한다.

    도출 방식에는 그 문제가 **없다.** 「지금 목록에 있는데 시작 시점에 없던 것」이므로,
    지워진 Step 은 애초에 세어지지 않는다. 설계를 바꾸면서 결함 한 종류가 사라졌다.
    """
    steps = steps_of(5)
    t = tx(steps, ["step-02"], arrival=1)
    made = ClickStep(id="step-09", label="새", target=target("n"))
    working = [steps[0], made, *steps[1:]]
    assert t.created(working) == ["step-09"]

    after_ai_delete = [s for s in working if s.id != made.id]
    assert t.created(after_ai_delete) == [], "지워진 것은 세지 않는다"

    result = t.discard(after_ai_delete, current_step_index=1)
    assert snapshot(result.steps) == snapshot(steps)


# ─── 권한 범위 (FR-037 · 불변식 8) ──────────────────────────────────────────


def test_the_scope_is_what_this_session_made() -> None:
    """**불변식 8 이 불변식 9 를 성립시킨다.**

    AI 가 고칠 수 있는 것이 자기가 만든 것뿐이므로 옛 구간과 구간 밖은 바뀌지 않고,
    바뀌지 않으므로 스냅샷 없이 되돌릴 수 있다 (R7).
    """
    steps = steps_of(6)
    t = tx(steps, ["step-03", "step-04"], arrival=2)
    working = [*steps, ClickStep(id="step-07", label="새", target=target("n"))]

    assert t.owns("step-07", working) is True
    assert t.owns("step-03", working) is False, "교체 대상은 AI 가 못 건드린다"
    assert t.owns("step-01", working) is False, "구간 밖도 마찬가지다"
    assert t.owns("step-99", working) is False, "목록에 없는 id 는 대상 부재다"


def test_created_follows_the_list_order() -> None:
    """만든 것의 순서는 **목록 순서**다 — 화면이 그 순서로 센다."""
    steps = steps_of(4)
    t = tx(steps, ["step-02"], arrival=1)
    a = ClickStep(id="step-20", label="나중", target=target("a"))
    b = ClickStep(id="step-10", label="먼저", target=target("b"))
    working = [steps[0], b, a, *steps[1:]]
    assert t.created(working) == ["step-10", "step-20"]


def test_any_creation_path_is_covered() -> None:
    """**어느 길로 만들어졌든 세어진다** (baseline_ids 주석의 근거).

    초안은 생성 지점마다 `record()` 를 부르는 방식이었고, 손 삽입 경로를 놓쳐 확정이
    「만든 것이 없다」로 거절됐다. 도출 방식은 길을 세지 않는다.
    """
    steps = steps_of(3)
    t = tx(steps, ["step-02"], arrival=1)
    # 리코더가 넣었든 손으로 넣었든 AI 가 만들었든 목록에 있으면 같다.
    working = [
        *steps,
        ClickStep(id="step-50", label="어떤 길로든", target=target("x")),
    ]
    assert t.created(working) == ["step-50"]
    assert t.can_commit(working) is True


# ─── 연타 방지 ──────────────────────────────────────────────────────────────


def test_a_settled_transaction_refuses_both_endings() -> None:
    """끝난 트랜잭션에 확정·버리기를 다시 걸 수 없다.

    버리기의 되맞춤 실행이 도는 중에 한 번 더 눌리면 실행이 겹친다.
    """
    steps = steps_of(5)
    t = tx(steps, ["step-02"], arrival=1)
    working = [*steps, ClickStep(id="step-09", label="새", target=target("n"))]
    t.close()

    with pytest.raises(TransactionSettledError):
        t.commit(working, current_step_index=1)
    with pytest.raises(TransactionSettledError):
        t.discard(working, current_step_index=1)
    assert t.can_commit(working) is False


def test_commit_does_not_close_by_itself() -> None:
    """트랜잭션을 닫는 것은 **호출자가 결과를 반영한 뒤**다.

    여기서 먼저 닫으면 삭제가 실패했을 때 되돌릴 수도 다시 시도할 수도 없는 상태가
    남는다.
    """
    steps = steps_of(5)
    t = tx(steps, ["step-02"], arrival=1)
    made = ClickStep(id="step-09", label="새", target=target("n"))
    working = [steps[0], made, *steps[1:]]

    t.commit(working, current_step_index=1)
    assert t.settled is False


# ─── 도착점 (FR-031) ────────────────────────────────────────────────────────


def test_the_arrival_index_is_frozen_at_the_start() -> None:
    """도착점은 **시작 시점** 값이며 삽입으로 밀리지 않는다.

    버리기 시점에 다시 계산하면 그 사이 삽입된 Step 때문에 값이 밀려 엉뚱한 곳에 멈춘다
    — 화면과 정의가 어긋나고, 그것이 FR-031 이 막으려는 상태다.
    """
    steps = steps_of(8)
    t = tx(steps, ["step-04"], arrival=3)
    grown = [
        *steps,
        *(
            ClickStep(id=f"step-{90 + i}", label=f"새 {i}", target=target(f"n{i}"))
            for i in range(5)
        ),
    ]
    assert len(t.created(grown)) == 5
    assert t.arrival_index == 3
