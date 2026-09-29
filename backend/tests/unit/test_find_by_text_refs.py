"""낱말로 찾은 것을 **거기서 바로 조작할 수 있다** (025 FR-047·FR-048).

## 보고된 것 (2026-09-29)

> 「못 찾는다고, 재시도 해도 안되는 경우가 있으면 테스트 생성이 어렵다. 브라우저로
> 볼때는 명확하게 보이는데, 못찾으면 안된다」

## 왜 그랬나 — 순환이었다

`observe_page` 가 상한에 걸려 잘린 화면에서 모델이 갈 곳은 `find_by_text` 뿐이다.
그런데 그 도구는 **참조를 주지 않고** 「조작하려면 `observe_page` 로 참조를 받으세요」로
돌려보냈다. 돌아간 그 목록에는 **바로 그 요소가 잘려 나가 있다.**

    observe_page(잘림) → find_by_text(찾음, 참조 없음) → observe_page(잘림) → …

모델은 이 고리를 돌며 도구 예산을 태우고, 사용자에게는 「화면에 분명히 보이는 것을 AI
가 못 찾는다」로 보인다. 근거였던 「후보 수집과 유일성 검증이 `observe_page` 경로에만
있다」는 사실이 아니다 — 둘 다 조작 시점의 `_act_on_element` 에 있다.

## 두 번째 원인 — 제품이 모르는 절단

Claude Code 드라이버는 MCP 응답에 자체 토큰 상한을 둔다. 넘으면 **CLI 가** 잘라 파일로
떨구고, 모델은 그 파일을 읽으려다 `Read` 차단(FR-086)에 걸려 **턴이 통째로 끊긴다.**
그 사이 제품의 `truncated` 는 거짓이므로 FR-044 의 안내도 붙지 않는다.

## 이 파일이 재는 것

브라우저를 쓰지 않는다. 참조가 실제로 부여되고 조작 도구가 그것을 받아들이는가,
그리고 예산 초과가 잘림으로 표현되는가 — 둘 다 순수한 자료 흐름이다. 살아 있는
화면에서 `actionable` 이 제대로 갈리는지는 `tests/e2e/test_actionable_elements.py` 가 본다.
"""

from __future__ import annotations

from typing import Any

import pytest

from itb.authoring.tools import (
    OBSERVE_RESPONSE_CHAR_BUDGET,
    BrowserToolbox,
    _fit_to_budget,
)


class _Page:
    """`evaluate` 하나만 있으면 된다 — 도구는 주입 스크립트의 결과만 읽는다."""

    def __init__(self, raw: Any) -> None:
        self._raw = raw

    async def evaluate(self, _script: str, _arg: Any = None) -> Any:
        return self._raw


class _Handle:
    def __init__(self, page: _Page) -> None:
        self.page = page
        self.tab_index = 0
        self.closed = False


class _Session:
    def __init__(self, page: _Page) -> None:
        self._handle = _Handle(page)
        self.active_tab_index = 0
        self.tabs = [self._handle]

    def find_tab(self, tab: int) -> _Handle | None:
        return self._handle if tab == 0 else None


def _toolbox(raw: Any) -> BrowserToolbox:
    return BrowserToolbox(
        session=_Session(_Page(raw)),  # type: ignore[arg-type]
        executor=object(),  # type: ignore[arg-type]
        allocate_step_id=lambda: "step-1",
        on_step=lambda _step: None,  # type: ignore[arg-type]
    )


def _match(**over: Any) -> dict[str, Any]:
    """`__itbFindByText` 가 주는 한 건. 기본값은 **누를 수 있는 것**이다."""
    actionable: dict[str, Any] | None = {
        "tag": "div",
        "role": None,
        "name": "메뉴관리",
        "css": "#sidebar > div:nth-child(3)",
        "actionability": "cursor",
        "visible": True,
        "disabled": False,
        "unique": True,
    }
    if "actionable" in over:
        given = over.pop("actionable")
        # `None` 은 「누를 수 있는 것이 없다」이지 「기본값을 쓰라」가 아니다 (FR-043).
        actionable = None if given is None else {**actionable, **given}
    base: dict[str, Any] = {
        "text_element": {"tag": "span", "name": "메뉴관리", "css": "#sidebar span"},
        "actionable": actionable,
        "context": "사이드바",
    }
    base.update(over)
    return base


# ─── 순환이 끊겼는가 (FR-047) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_found_element_carries_a_usable_reference() -> None:
    """찾은 것에 **참조가 붙는다.** 이것이 없으면 갈 곳이 없다."""
    box = _toolbox({"matches": [_match()]})

    result = await box.find_by_text("메뉴관리")

    ref = result["matches"][0]["actionable"]["element_ref"]
    assert ref, "찾았는데 조작할 방법이 없다 — 보고된 그 막다른 길이다"
    assert ref in box.refs


@pytest.mark.asyncio
async def test_the_reference_resolves_to_what_reacts_not_the_text() -> None:
    """참조가 가리키는 것은 **반응하는 요소**다 (FR-042).

    글자 요소에 참조를 주면 `<span>` 을 클릭하게 되고, 핸들러가 조상에 붙어 있으면
    **아무 일도 일어나지 않은 채 Step 만 남는다.** 가장 나쁜 실패다.
    """
    box = _toolbox({"matches": [_match()]})

    result = await box.find_by_text("메뉴관리")

    ref = result["matches"][0]["actionable"]["element_ref"]
    assert box.refs[ref].css == "#sidebar > div:nth-child(3)"
    assert "element_ref" not in result["matches"][0]["text_element"]


@pytest.mark.asyncio
async def test_reference_keeps_the_facts_the_refusal_rule_needs() -> None:
    """`unique` 가 **같이 실린다** (FR-046).

    싣지 않으면 `ObservedElement` 의 기본값 `True` 로 통과해, 가리키는 경로가 하나로
    좁혀지지 않는 요소를 `_act_on_element` 가 거절하지 못한다. 관찰 경로에서는 막히는
    조작이 이 경로에서만 조용히 통과하는 상태가 되고, 그 어긋남은 **잘못된 요소가
    조작된 뒤에야** 드러난다.
    """
    box = _toolbox({"matches": [_match(actionable={"unique": False})]})

    result = await box.find_by_text("메뉴관리")

    ref = result["matches"][0]["actionable"]["element_ref"]
    assert box.refs[ref].unique is False


@pytest.mark.asyncio
async def test_no_reference_when_nothing_reacts() -> None:
    """누를 수 없는 글자에는 참조를 주지 않는다 (FR-043).

    주면 모델이 그것을 조작하려 들고, 그것은 짐작이다. 알릴 것은 「있지만 누를 수
    없다」이다.
    """
    box = _toolbox({"matches": [_match(actionable=None)]})

    result = await box.find_by_text("아래 항목은")

    assert result["matches"][0]["actionable"] is None
    assert not box.refs
    assert "report_blocked" in result["note"]


@pytest.mark.asyncio
async def test_note_no_longer_sends_the_model_back_to_observe_page() -> None:
    """안내가 **순환을 만들지 않는다.**

    「observe_page 로 참조를 받으세요」가 남아 있으면 참조를 줘도 모델은 돌아간다 —
    도구가 주는 말이 도구가 하는 일보다 강하다.
    """
    box = _toolbox({"matches": [_match()]})

    note = (await box.find_by_text("메뉴관리"))["note"]

    assert "observe_page" not in note
    assert "element_ref" in note


@pytest.mark.asyncio
async def test_references_do_not_collide_with_observation() -> None:
    """두 경로가 **같은 번호를 두 요소에 주지 않는다.**

    참조 발번을 한 자리(`_register`)로 모은 이유다. 갈라 두면 `find_by_text` 가 준
    `e3` 을 뒤이은 `observe_page` 가 다른 요소에 덮어쓰고, 모델이 쥔 참조가 조용히
    다른 것을 가리키게 된다.
    """
    box = _toolbox({"matches": [_match(), _match(actionable={"css": "#other"})]})

    result = await box.find_by_text("메뉴관리")

    refs = [m["actionable"]["element_ref"] for m in result["matches"]]
    assert len(set(refs)) == 2
    assert len(box.refs) == 2


# ─── 제품이 먼저 자르는가 (FR-048) ───────────────────────────────────────────


def test_small_observation_is_left_alone() -> None:
    """예산 안이면 아무것도 버리지 않는다."""
    elements = [{"element_ref": f"e{i}", "name": "확인"} for i in range(10)]

    kept, over = _fit_to_budget(elements)

    assert kept == elements
    assert over is False


def test_oversized_observation_is_cut_and_says_so() -> None:
    """예산을 넘으면 **버리고, 버렸다고 말한다** (FR-044).

    말하지 않으면 모델은 목록이 전부라고 믿고 화면에 있는 것을 「없다」고 판단한다.
    """
    fat = {"element_ref": "e", "name": "가" * 500}
    elements = [dict(fat, element_ref=f"e{i}") for i in range(200)]

    kept, over = _fit_to_budget(elements)

    assert over is True
    assert 0 < len(kept) < len(elements)


def test_cut_result_fits_the_budget() -> None:
    """남긴 것이 **실제로 예산 안에 든다.**

    이것이 참이 아니면 CLI 가 다시 자르고, 그 절단은 제품이 모르는 절단이다 — 모델이
    파일을 읽으려다 턴이 끊기는 바로 그 상태로 돌아간다.
    """
    import json

    elements = [
        {"element_ref": f"e{i}", "name": "가" * 500, "context": "나" * 200}
        for i in range(200)
    ]

    kept, _ = _fit_to_budget(elements)

    size = sum(len(json.dumps(e, ensure_ascii=False)) for e in kept)
    assert size <= OBSERVE_RESPONSE_CHAR_BUDGET


def test_korean_is_measured_as_written_not_escaped() -> None:
    """한글을 **보내는 모양 그대로** 잰다.

    `ensure_ascii=True` 로 재면 한글 한 자가 `\\uXXXX` 6자로 세어져 예산을 세 배 넘게
    깎는다. 그러면 멀쩡한 화면에서도 목록이 3분의 1로 잘리고, 「AI 가 화면의 요소를 못
    본다」가 **이번 수정 때문에** 다시 생긴다.
    """
    korean = [{"element_ref": f"e{i}", "name": "가" * 100} for i in range(30)]
    ascii_same_length = [{"element_ref": f"e{i}", "name": "a" * 100} for i in range(30)]

    assert _fit_to_budget(korean)[1] is False
    assert len(_fit_to_budget(korean)[0]) == len(_fit_to_budget(ascii_same_length)[0])


def test_uncertain_elements_are_dropped_first() -> None:
    """잘려야 한다면 **짐작으로 잡은 쪽이 먼저** 잘린다.

    관찰 스크립트가 확실한 것(태그·속성)을 앞에, `cursor` 로 잡은 것을 뒤에 싣는다.
    앞에서부터 버리면 그 순서가 뜻을 잃는다.
    """
    # 확실한 것만으로 이미 예산을 넘긴다 — 그러면 짐작 쪽은 한 줄도 남으면 안 된다.
    certain = [
        {"element_ref": f"c{i}", "name": "가" * 400, "actionability": "semantic"}
        for i in range(60)
    ]
    guessed = [
        {"element_ref": f"g{i}", "name": "가" * 400, "actionability": "cursor"}
        for i in range(10)
    ]
    given = [*certain, *guessed]

    kept, over = _fit_to_budget(given)

    assert over is True
    assert all(e["actionability"] == "semantic" for e in kept)
    # 남긴 것이 **앞에서부터 이어지는 조각**이다. 중간을 건너뛰며 고르면 모델이 보는
    # 순서가 화면의 순서와 달라진다.
    assert kept == given[: len(kept)]


# ─── 말이 도구를 되돌려보내지 않는가 ────────────────────────────────────────


def test_system_prompt_does_not_route_back_to_observe_page() -> None:
    """프롬프트가 **순환을 지시하지 않는다.**

    도구가 참조를 주게 고쳐도, 모델이 읽는 말이 「조작하려면 observe_page 로 참조를
    받으세요」로 남아 있으면 모델은 그대로 돌아간다 — **말이 코드보다 강하다.** 025
    최초 구현에서 실제로 이 문장이 순환의 절반이었다.
    """
    from itb.authoring.agent import SYSTEM_PROMPT

    where = SYSTEM_PROMPT.index("find_by_text")
    guidance = SYSTEM_PROMPT[where : where + 400]

    assert "element_ref" in guidance, "찾은 것을 어떻게 쓰는지 말하지 않는다"
    assert "observe_page 로 참조를 받아야" not in guidance


def test_tool_description_tells_the_model_to_use_the_reference() -> None:
    """모델이 읽는 **도구 설명문**도 같은 말을 한다.

    프롬프트와 설명문은 다른 자리이고, 한쪽만 고치면 모델은 둘 중 구체적인 쪽(설명문)을
    따른다. 여기서 보는 것은 `BrowserToolbox` 의 docstring 이 아니라 **드라이버가 실제로
    모델에게 보내는 설명문**이다 — 둘은 다른 문자열이고, 모델이 받는 것은 후자다.
    """
    from itb.authoring.tools import TOOL_SCHEMAS

    # **원천을 본다.** 두 드라이버가 모두 여기서 설명문을 가져가므로, 여기가 맞으면
    # 경로마다 다른 말을 하는 일이 없다. 선택 의존성(`claude_agent_sdk`)도 필요 없다.
    doc, _schema = TOOL_SCHEMAS["find_by_text"]

    assert "element_ref" in doc, "찾은 것을 어떻게 쓰는지 말하지 않는다"
    assert "observe_page" not in doc
