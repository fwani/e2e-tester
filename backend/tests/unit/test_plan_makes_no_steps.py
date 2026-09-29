"""헌법 원칙 I — 계획은 Step 을 만들지 않는다 (025 T079a · FR-037).

## 왜 따로 못 박는가

025 는 모델에게 도구를 둘 더 준다 (`mark_item`·`find_by_text`). 둘 다 Step 을 만들지
않지만, **그 사실을 확인하는 것이 없으면 다음 변경에서 조용히 깨진다.**

깨지는 모양은 이렇다 — 누군가 「항목을 완료로 표시할 때 그 항목에 해당하는 Step 도
만들어 주자」로 바꾼다. 편리해 보이고, 화면에서는 잘 돌아 보인다. 그러나 그 순간
Step 을 만드는 주체가 둘이 되고, 헌법 원칙 I 이 요구하는 단일 Step 모델이 깨진다.

## 원칙 I 이 요구하는 것

> Human browser actions and AI Agent browser actions MUST be recorded into one and the
> same Test Step DSL.

Step 은 **브라우저를 실제로 조작했을 때**만 만들어진다. 계획의 상태, 수행 기록, 관찰의
발견 경로 — 어느 것도 Step 의 존재나 모양을 바꾸지 않는다.
"""

from __future__ import annotations

import inspect

from itb.authoring import fold, journal, plan, refine, summary

MODULES = (plan, journal, fold, refine, summary)
"""025 가 더한 모듈 전부. **이 목록이 곧 검사 범위다** — 새 모듈이 생기면 여기 더한다."""

STEP_MAKING_NAMES = ("ClickStep", "FillStep", "SelectStep", "NavigateStep", "AssertionStep")
"""Step 을 만드는 이름들. 025 의 모듈이 이것들을 부르면 안 된다."""


def test_new_modules_do_not_construct_steps() -> None:
    """**025 의 어느 모듈도 Step 을 만들지 않는다** (FR-037 · 헌법 원칙 I).

    소스를 읽어 확인한다 — 실행 경로를 타면 「그 경로를 지나지 않았을 뿐」일 수 있고,
    그러면 검사가 아무것도 말하지 않는다.
    """
    offenders: list[str] = []
    for module in MODULES:
        source = inspect.getsource(module)
        for name in STEP_MAKING_NAMES:
            if f"{name}(" in source:
                offenders.append(f"{module.__name__} — {name}")

    assert offenders == [], (
        f"025 의 모듈이 Step 을 만들고 있다: {offenders}. "
        "Step 을 만드는 것은 브라우저를 조작하는 도구뿐이다 (헌법 원칙 I)."
    )


def test_marking_an_item_does_not_touch_steps() -> None:
    """항목 상태를 바꾸는 것이 Step 목록과 무관하다.

    `WorkPlan` 은 Step 을 참조하지 않으므로(`test_work_plan.py` 가 구조로 고정한다)
    구조상 만질 수 없다. 여기서는 **동작으로** 다시 확인한다 — 구조가 바뀌어도 이 성질이
    깨졌음을 알 수 있어야 한다.
    """
    work = plan.WorkPlan(items=[plan.PlanItem("i1", 1, "로그인한다")])

    item = work.mark("i1", plan.ItemStatus.DONE)

    assert item.status is plan.ItemStatus.DONE
    # 계획이 들고 있는 것은 항목뿐이다. Step 이 끼어들 자리가 없다.
    assert set(plan.WorkPlan.__slots__) == {"items", "constraints", "source"}


def test_authoring_modules_do_not_import_execution() -> None:
    """025 의 모듈이 실행 계층을 끌어오지 않는다.

    `.importlinter` 는 **반대 방향**을 막는다 (`itb.execution` 이 `itb.authoring` 에
    닿지 못하게). 이쪽 방향은 계약이 없으므로 여기서 본다 — 작성이 실행을 끌어오면
    Step 을 만들 수단이 생기고, 그것이 위 검사가 막으려는 것의 앞 단계다.

    `tools.py` 는 예외다 — 그것은 실제로 브라우저를 조작하는 도구이고, Step 을 만드는
    유일한 주체다.
    """
    offenders: list[str] = []
    for module in MODULES:
        source = inspect.getsource(module)
        if "from itb.execution" in source or "import itb.execution" in source:
            offenders.append(module.__name__)

    assert offenders == [], (
        f"작성 모듈이 실행 계층을 끌어왔다: {offenders}. Step 을 만드는 수단이 "
        "생기는 자리다 (헌법 원칙 I)."
    )
