"""`mark_item` 이 **모델이 볼 수 있는 것**으로 항목을 지목하는가 (2026-09-30 사용자 보고).

## 무엇이 문제였나

보고 문장: 「`mark_item` 은 id 형식(`1`, `item-01`, `todo-01`, `checklist-1` 등)이 모두
거부되어 할 일 진행 표시를 남기지 못했습니다.」 — 매 세션 반복해서 나왔다.

**모델은 id 를 알 방법이 없었다.** 주입되는 목록은 `  1. ▶ 로그인한다` 처럼 `order` 만
적고 `id` 는 싣지 않는데, `WorkPlan.find` 는 `id` 정확 일치만 봤다. 실제 값은
`i1`(정제) 또는 `i5-3847`(대화로 추가, 해시가 붙는다)이라 추측할 수 있는 형태가 아니다.

거절 문면도 도움이 되지 않았다 — 「목록의 번호와 id 를 다시 확인하세요」라고 했지만
목록에 id 가 없으므로 확인할 것이 없었고, 모델은 같은 추측을 반복했다.

## 이 파일이 재는 것

**주입되는 것과 받는 것이 같은 낱말인가.** 둘이 갈라지면 모델은 지목할 수단이 없다.
그래서 `build_plan_summary` 가 실제로 뱉은 줄에서 번호를 읽어 그것으로 표시한다 —
한쪽만 고치면 여기서 실패한다.
"""

from __future__ import annotations

import re

import pytest

from itb.authoring.plan import ItemStatus, PlanError, PlanItem, WorkPlan
from itb.authoring.summary import build_plan_summary
from itb.authoring.tools import TOOL_SCHEMAS


def _plan() -> WorkPlan:
    return WorkPlan(
        items=[
            PlanItem("i1", 1, "로그인한다"),
            PlanItem("i2", 2, "메뉴관리로 이동한다"),
            PlanItem("i3", 3, "새 메뉴를 등록한다"),
        ],
    )


# ─── 1. 주입된 목록으로 실제로 지목할 수 있다 ────────────────────────────────


def test_the_number_the_model_sees_is_the_number_it_can_mark() -> None:
    """**이것이 이 파일의 핵심이다.** 주입된 줄에서 번호를 읽어 그대로 표시한다.

    모델이 하는 일을 그대로 한다 — 목록을 받고, 거기 보이는 번호를 쓴다.
    """
    plan = _plan()
    summary = build_plan_summary(plan)

    # 주입문에서 「2번 항목」의 번호를 읽는다. 모델이 보는 것이 이것뿐이다.
    line = next(ln for ln in summary.splitlines() if "메뉴관리로 이동한다" in ln)
    number = (re.match(r"\s*(\d+)\.", line) or pytest.fail(f"번호를 못 읽었다: {line!r}")).group(1)

    marked = plan.mark(number, ItemStatus.DONE)
    assert marked.text == "메뉴관리로 이동한다"


def test_the_injected_list_still_carries_no_id() -> None:
    """**검사가 헛돌지 않는다.**

    나중에 누가 목록에 id 를 적으면 위 검사는 번호 없이도 통과할 수 있다. 그때는 이
    파일의 전제가 바뀐 것이므로 여기서 알린다 — 번호로 지목하는 길을 낸 이유가
    「id 가 보이지 않아서」이기 때문이다.
    """
    summary = build_plan_summary(_plan())

    assert "i1" not in summary
    assert "i2" not in summary


@pytest.mark.parametrize("given", ["1", " 2 ", "3"])
def test_the_visible_number_is_accepted(given: str) -> None:
    """공백이 섞여도 받는다 — 모델이 어떻게 적든 뜻은 같다."""
    assert _plan().mark(given, ItemStatus.DONE).order == int(given.strip())


def test_the_internal_id_still_works() -> None:
    """**프론트의 되돌리기 경로가 바뀌지 않는다.** 그쪽은 진짜 id 를 갖고 있다."""
    assert _plan().mark("i2", ItemStatus.DONE).text == "메뉴관리로 이동한다"


def test_an_id_shaped_like_a_number_is_not_confused() -> None:
    """id 를 먼저 본다 — 둘이 겹치는 계획에서도 id 가 이긴다.

    실제 id 는 `i1` 형태라 이런 계획은 생기지 않지만, 우선순위가 뒤집히면 **id 를 가진
    호출자가 다른 항목을 집는다.** 그 순간을 여기서 잡는다.
    """
    plan = WorkPlan(items=[PlanItem("2", 1, "첫째"), PlanItem("i2", 2, "둘째")])

    assert plan.mark("2", ItemStatus.DONE).text == "첫째"


# ─── 2. 거절당했을 때 다음에 무엇을 할지 알 수 있다 ──────────────────────────


def test_the_refusal_names_the_numbers_that_exist() -> None:
    """거절만 받으면 모델은 같은 추측을 반복한다 — 실제로 그랬다."""
    with pytest.raises(PlanError) as caught:
        _plan().mark("todo-01", ItemStatus.DONE)

    message = str(caught.value)
    assert "1~3" in message, f"쓸 수 있는 번호를 말하지 않는다: {message}"


def test_an_out_of_range_number_is_still_refused() -> None:
    """번호를 받는다고 아무 번호나 받는 것이 아니다."""
    with pytest.raises(PlanError):
        _plan().mark("9", ItemStatus.DONE)


# ─── 3. 모델이 실제로 받는 설명문이 같은 말을 한다 ───────────────────────────


def test_the_tool_description_tells_the_model_what_to_pass() -> None:
    """`plan.py` 만 고치면 모델은 여전히 이름을 지어낸다.

    모델이 실제로 받는 것은 `TOOL_SCHEMAS` 다 (`test_tool_descriptions_scope` 머리말).
    """
    description, schema = TOOL_SCHEMAS["mark_item"]

    assert "번호" in description, "무엇을 넣어야 하는지 말하지 않는다"
    item_id = schema["properties"]["item_id"]
    assert "description" in item_id, "item_id 가 형식을 말하지 않는다"
    assert "번호" in item_id["description"]
