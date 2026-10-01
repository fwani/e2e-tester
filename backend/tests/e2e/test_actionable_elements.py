"""사람이 가리킨 것을 AI 가 찾는다 (025 US3 · T018~T021·T079b).

## 이 파일이 확인하는 것

사람은 브라우저에 **보이는 것**을 기준으로 말한다 — 「메뉴관리를 클릭한다」. AI 가 받는
목록은 태그와 속성으로 판정한 요소뿐이었고, React·Vue 는 `onclick` 속성을 DOM 에 남기지
않으므로 현대 웹 앱에서 클릭되는 `div`·`span`·`li`·`td` 가 **아예 없었다.**

`fixtures/sample-app/view-only-clickables.html` 이 그 상황을 그대로 만든다 — 이벤트 위임만
쓰고 `onclick` 속성을 하나도 두지 않는다.

## 가장 중요한 검증은 T019 다

`cursor` 는 **상속되는 속성**이다. 조상과 자손이 모두 `pointer` 로 계산되므로, 그것을
걸러 내지 않으면 목록이 몇 배로 부풀고 모델은 어느 것을 눌러야 할지 알 수 없게 된다.
기능이 동작하는 것처럼 보이면서 쓸모가 없어지는 실패이고, 그래서 따로 못 박는다.
"""

from __future__ import annotations

import pathlib

import pytest
from playwright.async_api import async_playwright

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "itb"
    / "recording"
    / "injected"
    / "recorder.js"
)
PAGE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "fixtures"
    / "sample-app"
    / "view-only-clickables.html"
)

pytestmark = pytest.mark.browser


async def _observe(limit: int = 200) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.add_init_script(SCRIPT.read_text())
        await page.goto(PAGE.as_uri())
        raw = await page.evaluate(
            "(l) => window.__itbObserve ? window.__itbObserve(l) : null", limit
        )
        await browser.close()
    assert isinstance(raw, dict), "관찰 스크립트가 주입되지 않았다"
    return raw


async def _find(text: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.add_init_script(SCRIPT.read_text())
        await page.goto(PAGE.as_uri())
        raw = await page.evaluate(
            "([w, l]) => window.__itbFindByText ? window.__itbFindByText(w, l) : null",
            [text, 10],
        )
        await browser.close()
    assert isinstance(raw, dict), "찾기 스크립트가 주입되지 않았다"
    return raw


async def test_clickable_non_semantic_elements_are_observed() -> None:
    """**클릭되는 `div`·`tr` 이 목록에 있다** (FR-039·FR-040).

    이것이 없으면 사람이 화면에서 가리킨 것을 AI 가 찾지 못한다.
    """
    raw = await _observe()
    names = {(e.get("name") or "").strip(): e for e in raw["elements"]}

    assert "메뉴관리" in names, (
        "클릭되는 div 가 관찰 목록에 없다. INTERACTIVE 선택자는 onclick 속성을 보는데, "
        "React·Vue 는 그 속성을 남기지 않는다 — 025 US3 이 고치려는 바로 그 상태다."
    )
    assert names["메뉴관리"]["actionability"] == "cursor"
    assert names["메뉴관리"]["tag"] == "div"

    rows = [e for e in raw["elements"] if e["tag"] == "tr"]
    assert rows, "클릭되는 표의 행이 목록에 없다"


async def test_semantic_elements_keep_their_higher_certainty() -> None:
    """태그로 확실한 것은 `cursor` 로 강등되지 않는다.

    모델이 「확실한 것」과 「짐작한 것」을 구별할 수 있어야, 조작이 실패했을 때 무엇을
    의심할지 안다.
    """
    raw = await _observe()
    links = [e for e in raw["elements"] if e["tag"] == "a"]

    assert links, "링크가 목록에 없다"
    assert all(e["actionability"] in {"semantic", "role"} for e in links)


async def test_cursor_inheritance_does_not_duplicate_ancestors_and_children() -> None:
    """**`cursor` 는 상속된다** — 가장 바깥만 실린다 (research R13 의 함정).

    `<div style="cursor:pointer"><span>메뉴관리</span></div>` 에서 `span` 의 computed
    cursor 도 `pointer` 다. 걸러 내지 않으면 둘 다 실리고, 목록이 몇 배로 부풀면서
    모델은 어느 것을 눌러야 할지 알 수 없게 된다.
    """
    raw = await _observe()
    cursor_els = [e for e in raw["elements"] if e["actionability"] == "cursor"]
    tags = [e["tag"] for e in cursor_els]

    assert "span" not in tags or tags.count("span") == 1, (
        f"조상과 자손이 함께 실렸다: {[(e['tag'], e.get('name')) for e in cursor_els]}"
    )
    # 트리 항목 셋은 각각 하나씩만 잡혀야 한다 — div 와 그 안의 span 이 둘 다면 여섯이다.
    tree = [e for e in cursor_els if (e.get("name") or "") in {"메뉴관리", "사용자관리"}]
    assert len(tree) == 2, f"트리 항목이 중복으로 실렸다: {tree}"


async def test_decorative_text_is_not_collected() -> None:
    """커서를 바꾸지 않는 설명 문구는 잡히지 않는다.

    이것이 잡히면 목록이 본문 전체가 되고, 상한이 의미를 잃는다.
    """
    raw = await _observe()
    names = [(e.get("name") or "") for e in raw["elements"]]

    assert not any("아래 항목은" in n for n in names)


async def test_find_by_text_separates_the_text_from_what_reacts() -> None:
    """글자를 담은 요소와 **반응하는 요소**가 갈라져 온다 (FR-042).

    텍스트는 `<span>` 에 있고 핸들러는 조상 `<div>` 에 붙은 것이 흔하다. 하나로 합쳐
    주면 모델은 어느 쪽을 받았는지 모른 채 조작하고, 잘못된 쪽이면 아무 일도 일어나지
    않은 채 Step 만 남는다.
    """
    raw = await _find("메뉴관리")
    assert raw["matches"], "화면에 있는 글자를 찾지 못했다"

    match = raw["matches"][0]
    assert match["text_element"]["tag"] == "span"
    assert match["actionable"] is not None
    assert match["actionable"]["tag"] == "div", (
        "반응하는 요소가 글자 요소 자신으로 나왔다. cursor 상속 때문에 첫 pointer 에서 "
        "멈춘 것이다 — 가장 바깥까지 올라가야 한다."
    )


async def test_find_by_text_says_when_nothing_reacts() -> None:
    """누를 수 없는 글자면 `actionable` 이 `null` 이다.

    「화면에 있지만 누를 수 있는 것이 아니다」도 모델이 알아야 할 사실이다 — 그때
    짐작으로 다른 것을 누르는 대신 알릴 수 있다 (FR-043).
    """
    raw = await _find("아래 항목은")

    assert raw["matches"], "화면에 있는 글자를 찾지 못했다"
    assert raw["matches"][0]["actionable"] is None


async def test_observation_marks_truncation() -> None:
    """상한에 걸려 잘리면 **그 사실이 실린다** (FR-044).

    말하지 않으면 모델은 목록이 전부라고 믿고, 화면에 있는 것을 「없다」고 판단한다.
    """
    full = await _observe(limit=200)
    cut = await _observe(limit=2)

    assert full["truncated"] is False
    assert cut["truncated"] is True
    assert len(cut["elements"]) == 2


async def test_uniqueness_refusal_still_applies_to_cursor_elements() -> None:
    """**헌법 원칙 IV 는 그대로다** (025 T079b · FR-046).

    관찰 범위를 넓혔다고 조작 거절 규칙이 약해지면 안 된다. `cursor` 로 발견된 요소도
    같은 `unique` 판정을 지나고, 거짓이면 `_act_on_element` 가 지금과 같이 거절한다.

    여기서 확인하는 것은 **판정이 붙는다**는 사실이다 — 거절 자체는
    `tests/integration` 의 기존 검증이 덮는다.
    """
    raw = await _observe()
    cursor_els = [e for e in raw["elements"] if e["actionability"] == "cursor"]

    assert cursor_els, "커서로 발견된 요소가 없다 — 이 검증이 아무것도 보지 않는다"
    # 관찰 스크립트는 **모든 요소에** 유일성 판정을 싣는다. 참일 때 결과에서 빼는 것은
    # `BrowserToolbox.observe_page` 이고(대부분 참이라 같은 칸이 200줄 붙는 것을 막는다),
    # 판정 자체는 여기서 이미 끝나 있다.
    #
    # 확인하는 것은 **커서로 발견된 요소도 그 판정을 지난다**는 사실이다. 지나지 않으면
    # 조작 단계에서 유일성을 확인할 근거가 없고, 헌법 원칙 IV 가 이 경로에서만 느슨해진다.
    for element in cursor_els:
        assert "unique" in element, f"유일성 판정이 없는 요소: {element.get('name')}"
        assert isinstance(element["unique"], bool)
    assert all(e.get("css") for e in cursor_els), (
        "커서로 발견된 요소에 경로가 없다 — 그러면 조작 단계에서 다시 찾을 수 없다"
    )


async def test_find_by_text_carries_what_a_reference_needs() -> None:
    """찾은 `actionable` 이 **참조를 부여받을 수 있는 상태로** 온다 (025 FR-047).

    `find_by_text` 는 `observe_page` 가 상한에 걸려 잘린 화면에서 요소에 닿는 유일한
    길이다. 그 길이 뚫려 있으려면 여기서 받은 것으로 Python 이 참조를 만들 수 있어야
    하고, 그러려면 `ObservedElement` 가 요구하는 사실이 다 실려 와야 한다.

    특히 `unique` 다. 빠지면 기본값 `True` 로 참조가 만들어져, 가리키는 경로가 하나로
    좁혀지지 않는 요소를 `_act_on_element` 가 **거절하지 못한다** (FR-046). 관찰
    경로에서는 막히는 조작이 이 경로에서만 조용히 통과하게 되고, 그 어긋남은 잘못된
    요소가 조작된 뒤에야 드러난다.
    """
    raw = await _find("메뉴관리")
    assert raw["matches"], "화면에 있는 글자를 찾지 못했다"

    actionable = raw["matches"][0]["actionable"]
    assert actionable is not None

    for key in ("css", "tag", "role", "name", "visible", "disabled", "unique"):
        assert key in actionable, (
            f"`{key}` 가 실리지 않았다 — Python 이 참조를 만들 때 기본값으로 메우게 되고, "
            "그 기본값은 조작 거절 규칙을 느슨하게 만든다"
        )
    assert isinstance(actionable["unique"], bool)
    assert actionable["visible"] is True


async def test_svg_icon_that_is_itself_the_target_is_observed() -> None:
    """**`<svg>` 자신이 클릭 대상인 아이콘이 목록에 있다** (2026-10-01 사용자 보고).

    `<svg class="icons svg-icon"><use href="…#star-outline"></use></svg>` 를 AI 가 누르지
    못해 작성이 멈췄다. 관찰은 「글자도 이미지도 없는 것」을 빼는데, 이미지 판정을
    **자손**에서만 했다 — `svg` 자신은 자손이 `<use>` 뿐이고 `innerText` 도 없어서
    빠졌다. 사람에게는 커서가 손가락으로 바뀌는 별 아이콘인데 AI 에게는 없는 요소였다.

    이름도 함께 본다. 목록에 떠도 이름이 없으면 모델은 「별 아이콘」을 지목할 근거가
    없다 — 스프라이트 조각 이름(`star-outline`)이 그 근거다.
    """
    raw = await _observe()
    icons = [e for e in raw["elements"] if e["tag"] == "svg"]

    assert len(icons) == 1, (
        f"클릭되는 svg 아이콘이 관찰 목록에 없거나 스프라이트 정의까지 실렸다: {icons}"
    )
    icon = icons[0]
    assert icon["actionability"] == "cursor"
    assert icon["visible"] is True
    assert icon["unique"] is True
    assert "star-outline" in (icon.get("name") or ""), (
        f"아이콘 이름이 비어 있다 — 모델이 지목할 근거가 없다: {icon}"
    )


async def test_observed_svg_icon_path_reaches_the_icon() -> None:
    """관찰이 준 경로로 **실제로 그 아이콘을 누를 수 있다.**

    목록에 뜨는 것과 조작되는 것은 다른 일이다. SVG 는 태그 대소문자와 네임스페이스가
    HTML 과 달라 경로가 어긋나기 쉽고, 어긋나면 Step 만 남고 화면은 그대로다.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.add_init_script(SCRIPT.read_text())
        await page.goto(PAGE.as_uri())
        raw = await page.evaluate("(l) => window.__itbObserve(l)", 200)
        icon = next(e for e in raw["elements"] if e["tag"] == "svg")
        await page.click(icon["css"])
        status = await page.text_content("#status")
        await browser.close()

    assert status == "즐겨찾기에 추가했습니다."
