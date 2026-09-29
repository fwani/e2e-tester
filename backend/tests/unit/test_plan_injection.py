"""계획 주입 문자열 — 모델이 매 턴 받는 것 (025 T033~T035).

## 이 파일이 지키는 성질

016 이 「지금 테스트」 하나를 정했고, 025 가 「요구받은 것」을 더한다. 더한 쪽이
지켜야 하는 것은 셋이다.

1. **순서** — 제약이 맨 앞. 가장 자주 어겨지고 앞머리가 가장 잘 읽힌다
2. **예산** — 016 의 16KB 를 늘리지 않고 나눈다. 넘으면 생략을 명시하며 줄인다
3. **없어도 돈다** — 계획이 없는 세션이 016 이전과 정확히 같이 동작한다 (FR-012)

셋째가 이 기능의 회귀 방어선이다. 기존 작성 경로가 하나라도 막히면 이 기능은 값이
아니라 비용이다.
"""

from __future__ import annotations

from itb.authoring.plan import (
    Constraint,
    ConstraintScope,
    ItemStatus,
    PlanItem,
    WorkPlan,
)
from itb.authoring.summary import (
    DEFAULT_SUMMARY_BUDGET,
    MARK_DONE,
    MARK_NEXT,
    MARK_SKIPPED,
    PLAN_BUDGET,
    STEPS_BUDGET_WITH_PLAN,
    build_plan_summary,
)


def _plan() -> WorkPlan:
    return WorkPlan(
        items=[
            PlanItem("i1", 1, "관리자 계정으로 로그인한다", ItemStatus.DONE),
            PlanItem("i2", 2, "메뉴관리로 이동한다", ItemStatus.DONE),
            PlanItem("i3", 3, "새 메뉴 추가 버튼을 클릭한다"),
            PlanItem("i4", 4, "각 필드에 값을 입력한다"),
            PlanItem("i5", 5, "사용 여부를 전환한다", ItemStatus.SKIPPED, "제품에 없다"),
        ],
        constraints=[
            Constraint("기존 등록된 데이터는 검증에 사용하지 않는다"),
            Constraint("연결 주소는 {{url_a}} 를 쓴다", ConstraintScope.ITEM, "i4"),
        ],
    )


def test_constraints_come_first() -> None:
    """**제약이 맨 앞이다** (contracts/agent-context.md §1).

    지시문이 준 값을 바꾸고 금지한 것을 하는 어긋남이 이 기능이 고치려는 것이고, 그것을
    막는 문장이 가장 잘 읽히는 자리에 있어야 한다.
    """
    out = build_plan_summary(_plan())

    assert out.index("[반드시 지킬 것]") < out.index("[할 일]")
    assert "기존 등록된 데이터는 검증에 사용하지 않는다" in out


def test_next_item_is_pointed_at() -> None:
    """가장 앞선 미완료에 `▶` 가 붙는다.

    목록만 주면 모델이 어디서 이어야 하는지를 스스로 판정해야 한다.
    """
    out = build_plan_summary(_plan())
    marked = [line for line in out.splitlines() if MARK_NEXT in line]

    assert len(marked) == 1
    assert "새 메뉴 추가 버튼" in marked[0]


def test_done_and_skipped_are_distinguishable() -> None:
    """했음·건너뜀·아직이 서로 다르게 보인다. 건너뜀에는 사유가 붙는다."""
    out = build_plan_summary(_plan())

    assert out.count(MARK_DONE) == 2
    assert MARK_SKIPPED in out
    assert "(건너뜀: 제품에 없다)" in out


def test_no_plan_adds_nothing() -> None:
    """**계획이 없으면 빈 문자열이다** (FR-012).

    이것이 이 기능의 회귀 방어선이다. 016 이전 경로(지시문 하나·자연어 Step 추가·구간
    재녹화)가 그대로 돌아야 한다.
    """
    assert build_plan_summary(None) == ""
    assert build_plan_summary(WorkPlan()) == ""


def test_budget_is_split_not_grown() -> None:
    """**016 의 총량을 늘리지 않는다** (research R6).

    016 은 16KB 를 정하면서 "그보다 더 키우지 않는다 — 매 턴 붙기 때문이다" 라고 적었다.
    그 판단을 뒤집지 않는다.
    """
    assert PLAN_BUDGET + STEPS_BUDGET_WITH_PLAN == DEFAULT_SUMMARY_BUDGET


def test_step_budget_is_untouched_without_a_plan() -> None:
    """**계획이 없으면 Step 이 16KB 를 그대로 쓴다.**

    무조건 10KB 로 줄이면 025 와 아무 상관 없는 경로(계획 없는 세션·자연어 Step 추가·
    구간 재녹화)에서도 Step 100개 근처에서 축약이 걸린다 — 016 이 실측으로 피하려던
    상황이 되살아난다. 좁히는 것은 계획이 실제로 붙을 때뿐이다.
    """
    import inspect

    from itb.authoring.summary import build_definition_summary

    default = inspect.signature(build_definition_summary).parameters["budget"].default

    assert default == DEFAULT_SUMMARY_BUDGET, (
        "정의 요약의 기본 예산이 좁아졌다. 계획이 없는 세션까지 016 이전보다 나빠진다."
    )


def test_long_plan_is_shortened_with_an_explicit_note() -> None:
    """예산을 넘으면 **완료된 것부터 접고 생략을 명시한다** (FR-013).

    조용히 사라지면 모델은 그 항목들을 다시 하려 든다 — 016 이 정의 요약에 대해 내린
    판단과 같다.
    """
    long_text = "이것은 아주 긴 할 일 설명이며 실제 지시문에서 흔한 길이다. " * 3
    plan = WorkPlan(
        items=[
            PlanItem(
                f"i{n}",
                n,
                f"{n}번 {long_text}",
                ItemStatus.DONE if n <= 40 else ItemStatus.PENDING,
            )
            for n in range(1, 61)
        ]
    )

    out = build_plan_summary(plan)

    assert len(out.encode()) <= PLAN_BUDGET
    assert "생략" in out, "잘렸는데 그 사실을 말하지 않았다"
    # 남은 일이 먼저다 — 마지막 항목은 살아 있어야 한다.
    assert "60번" in out


def test_constraints_survive_shortening() -> None:
    """**제약은 접지 않는다.**

    그것을 잃으면 이 기능이 고치려는 문제(값을 바꾸고 금지를 어긴다)가 그대로 돌아온다.
    """
    long_text = "긴 할 일 설명이 이어진다. " * 5
    plan = WorkPlan(
        items=[PlanItem(f"i{n}", n, f"{n}번 {long_text}") for n in range(1, 81)],
        constraints=[Constraint("절대로 기존 데이터를 지우지 않는다")],
    )

    out = build_plan_summary(plan)

    assert "절대로 기존 데이터를 지우지 않는다" in out


def test_values_are_carried_as_references_not_secrets() -> None:
    """자격 증명은 **정제 단계에서 이미 참조로 바뀐다** (FR-010 · research R10).

    이 모듈은 다시 거르지 않는다 — 거르는 곳이 둘이면 어느 쪽이 기준인지 말할 수 없다.
    여기서 확인하는 것은 **참조 표기가 그대로 실린다**는 것이다. 참조를 값으로 오해해
    가공하면 모델이 쓸 수 없는 문자열이 된다.
    """
    plan = WorkPlan(
        items=[PlanItem("i1", 1, "로그인한다")],
        constraints=[Constraint("비밀번호는 {{admin_password}} 를 쓴다")],
    )

    out = build_plan_summary(plan)

    assert "{{admin_password}}" in out
