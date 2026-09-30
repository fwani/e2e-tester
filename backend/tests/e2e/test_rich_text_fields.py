"""`input` 이 아닌 입력 칸을 AI 가 찾는다 (025 FR-049·FR-050).

## 보고된 것 (2026-09-29)

리치 텍스트 편집기와 태그 입력 칸을 가리키며 「이걸 인식못하는데?」.

## 왜 그랬나 — 셀렉터가 두 벌이었다

| 목록 | `contenteditable` | 쓰는 곳 |
|---|---|---|
| `ACTIONABLE` | 있었다 | 사람이 직접 녹화 |
| `INTERACTIVE` | **없었다** | `observe_page`·`find_by_text` |

그래서 **사람이 녹화하면 잡히는데 AI 는 못 찾는** 상태였다. 같은 화면을 두 목록이
다르게 보고 있었고, 그 차이는 AI 로 만들어 볼 때까지 드러나지 않는다.

## 목록에 띄우는 것만으로는 부족했다

띄우고 나니 이름이 `null` 이었다. 글 쓰는 칸은 비어 있고, `<label for>` 는 `<div>` 를
연결하지 못하며(labelable 요소가 아니다), 실제 제품의 `for` 값은 존재하지 않는 id 를
가리키고 있었다. 이름 없는 익명 `div` 는 목록에 있어도 모델이 지목할 수 없다.

## 이 파일이 재는 것

`fixtures/sample-app/rich-text-fields.html` 은 제품에서 받은 DOM 구조 그대로다.
**이름을 얻는 세 경로**를 각각 못 박는다 — 하나만 살아 있어도 나머지 화면은 막힌다.
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
    / "rich-text-fields.html"
)

pytestmark = pytest.mark.browser

EDITOR = ".toastui-editor-ww-container .ProseMirror"
TAG_INPUT = ".field-tag-input"


async def _observe() -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.add_init_script(SCRIPT.read_text())
        await page.goto(PAGE.as_uri())
        raw = await page.evaluate(
            "(l) => window.__itbObserve ? window.__itbObserve(l) : null", 200
        )
        await browser.close()
    assert isinstance(raw, dict), "관찰 스크립트가 주입되지 않았다"
    return raw


def _named(raw: dict, name: str) -> list[dict]:
    return [e for e in raw["elements"] if (e.get("name") or "").strip() == name]


async def test_rich_text_editor_is_observed() -> None:
    """**편집 영역이 목록에 있다** (FR-049).

    이것이 없으면 「공지사항 내용에 입력한다」를 수행할 방법이 없다. 사람이 녹화하면
    잡히던 요소이므로, 없다는 것은 두 셀렉터 목록이 갈라졌다는 뜻이다.
    """
    raw = await _observe()
    editors = [
        e
        for e in raw["elements"]
        if e.get("tag") == "div" and (e.get("name") or "").startswith("공지사항 내용")
    ]

    assert editors, (
        "contenteditable 편집 영역이 관찰 목록에 없다 — "
        "INTERACTIVE 와 ACTIONABLE 이 갈라졌는지 보라"
    )
    assert any(e.get("visible") for e in editors), "보이는 편집 영역이 하나도 없다"


async def test_editor_name_comes_from_the_label_beside_it() -> None:
    """이름을 **바로 앞에 놓인 라벨**에서 얻는다 (FR-050).

    이 편집기는 `aria-label` 도 `placeholder` 도 없고, `<label for>` 는 실재하지 않는
    id 를 가리키며 `<div>` 는 그것으로 연결되지도 않는다. 남은 단서는 문서 순서뿐이다.

    라벨까지 **열 겹**이라는 것이 이 검증의 핵심이다 — 거리 상한이 짧으면 조용히
    실패하고, 그 실패는 이름이 `null` 인 익명 요소로만 드러난다.
    """
    raw = await _observe()

    assert _named(raw, "공지사항 내용 *"), (
        "편집 영역이 옆 라벨에서 이름을 얻지 못했다. "
        "NEARBY_MAX_HOPS 가 짧거나, 라벨이 조작 요소로 오인되어 버려졌을 수 있다"
    )


async def test_tag_input_name_comes_from_data_placeholder() -> None:
    """태그 칸은 **`data-placeholder`** 로 이름을 얻는다 (FR-050).

    표준은 아니지만 리치 입력 위젯이 실제로 쓰는 관례다. 이 경로가 없으면 태그 칸은
    라벨이 `<div class="form-label">` 이라 `el.labels` 로도 닿지 않아 이름이 없다.
    """
    raw = await _observe()
    tags = [
        e
        for e in raw["elements"]
        if e.get("tag") == "span" and (e.get("name") or "").startswith("태그를 입력한")
    ]

    assert tags, "태그 입력 칸이 data-placeholder 에서 이름을 얻지 못했다"
    assert tags[0].get("visible") is True


async def test_typed_content_does_not_become_the_name() -> None:
    """**쓴 글이 이름을 밀어내지 않는다** (FR-050).

    `contenteditable` 의 `textContent` 는 사용자가 방금 쓴 본문이다. 그것이 이름이 되면
    입력할 때마다 이름이 달라지고, 다음 관찰에서 모델은 같은 칸을 알아보지 못한다 —
    수정 시나리오(값을 바꾸고 다시 관찰)가 정확히 그 경로다.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.add_init_script(SCRIPT.read_text())
        await page.goto(PAGE.as_uri())
        await page.fill(EDITOR, "이 문장이 이름이 되면 안 된다")
        raw = await page.evaluate("(l) => window.__itbObserve(l)", 200)
        await browser.close()

    names = [(e.get("name") or "") for e in raw["elements"]]
    assert not any("이 문장이 이름이 되면 안 된다" in n for n in names), (
        "쓴 본문이 요소 이름이 되었다 — 다음 관찰에서 같은 칸을 지목할 수 없게 된다"
    )
    assert _named(raw, "공지사항 내용 *"), "입력 후 라벨 이름이 사라졌다"


async def test_both_fields_accept_input() -> None:
    """찾은 뒤 **실제로 채워진다.**

    관찰이 고쳐져도 조작이 안 되면 의미가 없다. 둘은 다른 계층이므로 함께 못 박는다.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(PAGE.as_uri())
        await page.fill(EDITOR, "공지 본문")
        await page.fill(TAG_INPUT, "공지")
        assert "공지 본문" in await page.inner_text(EDITOR)
        assert "공지" in await page.inner_text(TAG_INPUT)
        await browser.close()


async def test_label_is_not_borrowed_across_fields() -> None:
    """**옆 칸의 라벨을 빌려 오지 않는다.**

    라벨을 멀리까지 찾으러 가는 규칙은 느슨해지기 쉽다. 「공지사항 이름」은 자기
    `<input>` 의 것이지 편집기의 것이 아니다 — 하나의 라벨이 두 칸에 붙으면 모델은
    둘을 구별할 수 없고, 그것은 이 수정이 없애려던 상황과 같다.
    """
    raw = await _observe()
    borrowed = [
        e
        for e in _named(raw, "공지사항 이름 *")
        if e.get("tag") not in ("input", "label")
    ]

    assert not borrowed, f"이름 라벨이 다른 칸까지 번졌다: {borrowed}"


# ─── 재실행에서 다시 찾을 수 있는가 (025 FR-051) ────────────────────────────


async def _describe(selector: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.add_init_script(SCRIPT.read_text())
        await page.goto(PAGE.as_uri())
        raw = await page.evaluate("(s) => window.__itbDescribe(s)", selector)
        await browser.close()
    assert isinstance(raw, dict), f"요소를 설명하지 못했다: {selector}"
    return raw


async def test_generated_id_stays_out_of_the_css_path() -> None:
    """**매번 바뀌는 id 는 경로에 넣지 않는다** (2026-09-30 사용자 보고).

    Toast UI 는 마운트할 때마다 `notice-content-editor-<무작위>` 로 id 를 짓는다. 그것이
    경로에 들어가면 재실행이 **반드시** 실패한다 — 화면은 그대로인데 id 만 달라지기
    때문이다. 저장된 테스트에서 같은 편집기가 `…-aysr6yz` 와 `…-e6ct2lx` 두 값으로
    남아 있었고, 녹화하는 동안 이미 달라진 것이었다.

    실패가 저장 시점이 아니라 **재실행 시점에** 드러나는 것이 이 결함의 성질이다.
    녹화 화면에서는 아무 이상이 보이지 않는다.
    """
    described = await _describe(EDITOR)

    assert "notice-content-editor-" not in described["css"], (
        f"난수 id 가 경로에 들어갔다: {described['css']}"
    )


async def test_stable_id_is_still_used() -> None:
    """**사람이 지은 id 는 계속 쓴다.**

    난수 판정이 느슨해지면 멀쩡한 id 까지 버리게 되고, 그러면 모든 경로가 위치 기반이
    되어 형제 하나만 끼어들어도 깨진다. 판정이 좁게 유지되는지 반대편에서 못 박는다.
    """
    described = await _describe("#notice-name")

    assert "#notice-name" in described["css"], (
        f"안정적인 id 를 쓰지 않았다: {described['css']}"
    )


async def test_borrowed_label_is_not_stored_as_the_accessible_name() -> None:
    """빌려 온 이름은 **후보로 저장되지 않는다** (FR-051).

    옆 라벨에서 얻은 이름은 목록에서 지목하는 데 쓰는 값이다. 그것이 후보로 저장되면
    재실행이 `getByRole(…, name)` 으로 찾으려 하는데 **그 요소의 실제 접근 이름은 비어
    있다.** 저장하는 순간 재실행 불가가 되고, 화면에는 아무 이상이 보이지 않는다.

    관찰 목록에는 이름이 **있어야 하고**(FR-050) 후보에는 **없어야 한다** — 한 값이
    두 곳에서 반대로 쓰인다는 것이 이 검증의 요점이다.
    """
    described = await _describe(EDITOR)
    raw = await _observe()

    assert described["accessibleName"] is None, (
        f"빌려 온 이름이 후보로 저장됐다: {described['accessibleName']!r}"
    )
    assert _named(raw, "공지사항 내용 *"), "관찰 목록에서는 이름이 사라지면 안 된다"
