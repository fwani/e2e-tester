"""이름만으로 구별되지 않는 요소를 **구별되지 않는다고 말한다** (2026-09-11 사용자 보고).

## 보고된 것

> 「ai 에게 시킬때 검색 input 이 한화면에 두개가 있을때, 명확한 위치를 선택하지 못하고
> 다른 input 에 입력을 하는 문제가 있다」

## 왜 그랬나

`observe_page` 가 에이전트에게 주던 줄은 `tag·role·name·visible·disabled·type` 여섯
칸이었다. 같은 placeholder 를 가진 검색 칸 둘은 **여섯 칸이 모두 같다** — 에이전트가 알
수 있는 차이가 목록 순서뿐이므로 앞의 것을 고를 수밖에 없었다.

시스템 프롬프트에는 「추측으로 다른 요소를 누르지 마세요」가 있었지만, 그것은 지킬 수
없는 규칙이었다. 에이전트는 자기가 추측하고 있다는 사실을 알 방법이 없었다.

## 이 파일이 재는 것

`mark_duplicates` 는 브라우저를 쓰지 않는 순수 함수다 — 묶음 기준과 자기 제외, 그리고
**고르지 않는다**는 성질을 여기서 전수로 센다. 실제 화면에서 정보가 실제로 갈리는지는
`tests/integration/test_twin_search.py` 가 살아 있는 브라우저로 본다.
"""

from __future__ import annotations

from typing import Any

from itb.authoring.tools import (
    DISTINGUISHING_FIELDS,
    DUPLICATE_KEY_FIELDS,
    mark_duplicates,
)


def row(ref: str, **over: Any) -> dict[str, Any]:
    """관찰 결과 한 줄. 기본값은 **검색 칸**이다 — 보고된 화면의 그 요소다."""
    base: dict[str, Any] = {
        "element_ref": ref,
        "tag": "input",
        "role": "textbox",
        "name": "이름 또는 아이디를 검색하세요.",
        "visible": True,
        "disabled": False,
        "type": "text",
    }
    base.update(over)
    return base


def test_two_identical_search_inputs_are_marked_on_both_sides() -> None:
    """보고된 화면 그대로 — 검색 칸 둘이 서로를 가리킨다."""
    elements = [row("e1", id="user-search"), row("e2", id="org-search")]
    mark_duplicates(elements)

    assert elements[0]["duplicate_with"] == ["e2"]
    assert elements[1]["duplicate_with"] == ["e1"]


def test_self_is_excluded() -> None:
    """「나 말고 이것들이 나와 같아 보인다」가 읽을 말이다."""
    elements = [row("e1"), row("e2"), row("e3")]
    mark_duplicates(elements)

    for element in elements:
        assert element["element_ref"] not in element["duplicate_with"]
        assert len(element["duplicate_with"]) == 2


def test_a_single_element_is_not_marked() -> None:
    """겹치지 않으면 아무 표식도 붙지 않는다 — 읽을 것을 늘리지 않는다."""
    elements = [row("e1"), row("e2", name="검색", tag="button", role="button", type=None)]
    mark_duplicates(elements)

    assert "duplicate_with" not in elements[0]
    assert "duplicate_with" not in elements[1]


def test_each_key_field_alone_separates_the_group() -> None:
    """묶음 기준 네 칸이 **전부** 판정에 쓰인다.

    한 칸이라도 빠지면 그 칸만 다른 두 요소가 「같아 보인다」로 잘못 표시된다 —
    에이전트는 구별할 수 있는데 물어보게 된다.
    """
    for field in DUPLICATE_KEY_FIELDS:
        elements = [row("e1"), row("e2", **{field: "다른값"})]
        mark_duplicates(elements)
        assert "duplicate_with" not in elements[0], f"{field} 이 묶음 기준에서 빠졌다"
        assert "duplicate_with" not in elements[1], f"{field} 이 묶음 기준에서 빠졌다"


def test_invisible_elements_count_too() -> None:
    """보이지 않는 것도 센다.

    `visible` 로 걸러 세면 hover 로 열리는 메뉴 안의 같은 이름 항목이 묶음에서 빠지고,
    남은 하나가 「유일하다」로 보인다. 관찰이 보이지 않는 요소를 목록에서 빼지 않는
    것과 같은 판단이다.
    """
    elements = [row("e1"), row("e2", visible=False)]
    mark_duplicates(elements)

    assert elements[0]["duplicate_with"] == ["e2"]
    assert elements[1]["duplicate_with"] == ["e1"]


def test_marking_does_not_choose_or_drop_anything() -> None:
    """**고르지 않는다.**

    제품이 하나를 골라 주면 그것도 추측이고, 틀렸을 때 조용히 통과한다 (004 가 `.first`
    폴백을 지운 근거와 같다). 이 함수는 줄을 지우지도, 순서를 바꾸지도, `duplicate_with`
    말고 다른 칸을 건드리지도 않는다.
    """
    elements = [row("e1", id="user-search"), row("e2", id="org-search")]
    before = [dict(element) for element in elements]

    mark_duplicates(elements)

    assert [e["element_ref"] for e in elements] == ["e1", "e2"]
    for after, original in zip(elements, before, strict=True):
        assert {k: v for k, v in after.items() if k != "duplicate_with"} == original


def test_distinguishing_fields_are_the_four_the_prompt_names() -> None:
    """프롬프트가 이름으로 부르는 넷과 같아야 한다.

    프롬프트는 「`id`·`placeholder`·`label`·`context` 를 보고 고르세요」라고 말한다.
    관찰 결과가 그중 하나를 싣지 않으면 그 문장은 없는 것을 가리키게 된다.
    """
    from itb.authoring.agent import SYSTEM_PROMPT

    assert DISTINGUISHING_FIELDS == ("id", "placeholder", "label", "context")
    for field in DISTINGUISHING_FIELDS:
        assert f"`{field}`" in SYSTEM_PROMPT, f"프롬프트가 {field} 를 말하지 않는다"
    assert "duplicate_with" in SYSTEM_PROMPT
