"""작업 계획의 불변 조건과 상태 전이 (025 T032·T058).

## 이 파일이 지키는 성질

계획은 **두 주체가 함께 만지는 값**이다 — 모델이 완료를 표시하고 사람이 되돌린다. 그
둘이 같은 규칙을 지나야 「했다」가 뜻을 갖는다.

가장 중요한 것은 **모델이 되돌릴 수 없다**는 것이다 (data-model §2). 모델이 자기 표시를
취소할 수 있으면 했다가 안 했다가 하는 값이 되고, 그것은 진척이 아니다.
"""

from __future__ import annotations

import pytest

from itb.authoring.plan import (
    MAX_PLAN_ITEMS,
    Constraint,
    ConstraintScope,
    ItemStatus,
    PlanError,
    PlanItem,
    PlanSource,
    WorkPlan,
)


def _plan() -> WorkPlan:
    return WorkPlan(
        items=[
            PlanItem("i1", 1, "로그인한다"),
            PlanItem("i2", 2, "메뉴관리로 이동한다"),
            PlanItem("i3", 3, "새 메뉴를 등록한다"),
        ],
        constraints=[Constraint("기존 데이터는 검증에 쓰지 않는다")],
    )


def test_empty_plan_behaves_like_no_plan() -> None:
    """**빈 계획은 계획이 없는 것과 같다** (FR-012).

    정제에 실패했거나 사용자가 거절한 세션이 그렇다. 그때 016 이전과 같이 동작해야
    하고, 그 판정이 한 곳(`empty`)에 있어야 두 갈래가 갈리지 않는다.
    """
    assert WorkPlan().empty is True
    assert _plan().empty is False


def test_next_item_is_the_first_pending() -> None:
    """**다음 할 일을 제품이 지목한다** (contracts/agent-context.md §1 의 `▶`).

    목록만 주면 모델이 어디서 이어야 하는지를 스스로 판정해야 하고, 그 판정이 「되풀이」와
    「건너뜀」이 생기는 자리다.
    """
    plan = _plan()
    assert plan.next_item is not None
    assert plan.next_item.id == "i1"

    plan.mark("i1", ItemStatus.DONE)
    assert plan.next_item is not None
    assert plan.next_item.id == "i2"


def test_skipped_items_do_not_become_next() -> None:
    """건너뛴 것은 다음 할 일이 아니다 — 그것은 이미 결론이 난 항목이다."""
    plan = _plan()
    plan.mark("i1", ItemStatus.SKIPPED, "제품에 그 기능이 없다")

    assert plan.next_item is not None
    assert plan.next_item.id == "i2"


def test_model_cannot_undo_its_own_mark() -> None:
    """**모델은 되돌릴 수 없다** (data-model §2).

    자기 표시를 취소할 수 있으면 「했다」가 무엇을 뜻하는지 알 수 없다.
    """
    plan = _plan()
    plan.mark("i1", ItemStatus.DONE)

    with pytest.raises(PlanError, match="사용자만"):
        plan.mark("i1", ItemStatus.PENDING)

    assert plan.find("i1") is not None
    assert plan.find("i1").status is ItemStatus.DONE  # type: ignore[union-attr]


def test_user_can_revert() -> None:
    """사용자는 되돌릴 수 있다. 사유도 함께 지워진다."""
    plan = _plan()
    plan.mark("i1", ItemStatus.SKIPPED, "제품에 그 기능이 없다")

    reverted = plan.revert("i1")

    assert reverted.status is ItemStatus.PENDING
    assert reverted.skip_reason is None


def test_skipping_requires_a_reason() -> None:
    """**사유 없는 건너뜀은 거절한다** (FR-027).

    사유가 없으면 「건너뛰었다」와 「하지 않았다」가 구별되지 않고, 그러면 완료 보고가
    남은 일을 덮는다.
    """
    plan = _plan()

    with pytest.raises(PlanError, match="이유"):
        plan.mark("i1", ItemStatus.SKIPPED)
    with pytest.raises(PlanError, match="이유"):
        plan.mark("i1", ItemStatus.SKIPPED, "   ")

    assert plan.find("i1").status is ItemStatus.PENDING  # type: ignore[union-attr]


def test_marking_twice_is_harmless() -> None:
    """같은 항목을 여러 번 표시해도 한 번만 바뀐다 (research R9).

    모델이 성실히 표시하다 중복하는 것이 **해로우면 안 된다.** 거절하면 모델이
    「무언가 잘못됐다」로 읽고 다른 일을 하려 든다.
    """
    plan = _plan()
    plan.mark("i1", ItemStatus.DONE)
    plan.mark("i1", ItemStatus.DONE)

    assert [i.status for i in plan.items].count(ItemStatus.DONE) == 1


def test_unknown_item_is_refused_with_a_usable_reason() -> None:
    """없는 항목을 지목하면 거절하고, **왜인지 모델에게 말한다.**"""
    plan = _plan()

    with pytest.raises(PlanError, match="그런 항목이 없습니다"):
        plan.mark("nope", ItemStatus.DONE)


def test_appending_keeps_numbering_contiguous() -> None:
    """대화로 온 새 지시가 항목이 된다 (FR-029). 순번은 끊기지 않는다.

    **사용자가 보는 번호와 모델에게 가는 번호가 같아야 한다** — 어긋나면 사용자가
    「3번을 다시」라고 말했을 때 모델이 다른 것을 집는다.
    """
    plan = _plan()
    added = plan.append("삭제 확인창에서 취소를 누른다")

    assert added.order == 4
    assert [i.order for i in plan.items] == [1, 2, 3, 4]


def test_renumber_after_removal() -> None:
    """항목을 지우면 번호를 다시 매긴다."""
    plan = _plan()
    plan.items.pop(1)
    plan.renumber()

    assert [i.order for i in plan.items] == [1, 2]


def test_append_stops_at_the_limit() -> None:
    """상한을 넘기지 않는다 — 매 턴 주입되는 값이기 때문이다."""
    plan = WorkPlan(items=[PlanItem(f"i{n}", n, f"할 일 {n}") for n in range(1, MAX_PLAN_ITEMS + 1)])

    with pytest.raises(PlanError, match="너무 많습니다"):
        plan.append("하나 더")


def test_remaining_reports_what_is_left() -> None:
    """남은 것이 무엇인지 — `ai_finished` 가 이것을 싣는다 (FR-028)."""
    plan = _plan()
    plan.mark("i1", ItemStatus.DONE)
    plan.mark("i2", ItemStatus.SKIPPED, "해당 없음")

    assert [i.id for i in plan.remaining] == ["i3"]


def test_constraints_for_item_includes_globals() -> None:
    """전역 제약은 **모든 항목에** 걸린다.

    「기존 데이터는 검증에 쓰지 않는다」가 첫 구획 앞에 한 번 적혀 있어도 네 구획 전부에
    걸려야 한다 — 그것이 정제가 하는 일이다.
    """
    plan = _plan()
    plan.constraints.append(
        Constraint("연결 주소는 {{url_a}} 를 쓴다", ConstraintScope.ITEM, "i3")
    )

    for_i3 = plan.constraints_for("i3")
    for_i1 = plan.constraints_for("i1")

    assert len(for_i3) == 2
    assert len(for_i1) == 1


def test_plan_does_not_reference_steps() -> None:
    """**계획은 Step 을 참조하지 않는다** (data-model §1 · 헌법 원칙 I).

    항목과 Step 은 1:N 도 1:1 도 아니다 — 검증만 하는 항목은 Step 을 만들지 않고, 한
    항목이 여러 Step 이 되기도 한다. 참조를 두면 그 어긋남을 누군가 메워야 하고, 메우는
    쪽은 반드시 짐작한다.

    이 검증은 **구조**를 고정한다. 누군가 `step_ids` 를 더하면 여기서 실패하고, 그때
    「왜 필요한가」를 먼저 답해야 한다.
    """
    fields = set(PlanItem.__slots__) | set(WorkPlan.__slots__)

    assert not any("step" in name for name in fields), (
        f"계획이 Step 을 참조하고 있다: {sorted(f for f in fields if 'step' in f)}"
    )


def test_source_distinguishes_refined_from_edited() -> None:
    """사용자가 손댄 계획은 정제 결과와 갈라 둔다.

    손댄 계획을 다시 정제하면 그 손댐이 지워진다 — 그것을 막으려면 어느 쪽인지 알아야
    한다.
    """
    assert WorkPlan().source is PlanSource.REFINED
    assert WorkPlan(source=PlanSource.MANUAL).source is PlanSource.MANUAL
