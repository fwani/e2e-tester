"""검증 조건 구성. FR-037·FR-013a·FR-013b (T100).

4종(`visible`·`hidden`·`text`·`url`) 중 하나를 만든다. **요소를 대상으로 하는 검증에서는
제품이 후보를 수집·검증한다** — 클라이언트가 `TargetLocator` 를 손으로 만들어 보내게 하면
녹화가 만드는 후보와 검증 Step 의 후보가 갈리고, 원칙 IV 의 단일 지점이 무너진다.

클라이언트가 주는 것은 **어느 요소인가**(CSS 셀렉터 하나)와 조건뿐이다.

`{{변수명}}` 참조를 비교 값에 쓸 수 있다 (FR-013b). 이 모듈은 참조를 풀지 않는다 —
해석은 실행 시점에 `VariableResolver` 가 한다. 여기서 풀면 정의 파일에 값이 박힌다.
"""

from __future__ import annotations

from playwright.async_api import Page

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.step import AssertionStep, Author
from itb.execution.element_probe import collect_by_selector


class AssertionTargetError(Exception):
    """대상 요소를 찾지 못했다.

    **Step 을 만들지 않는다.** 후보 없는 검증 Step 은 재실행에서 반드시 실패하므로,
    만들어 두는 것이 사용자에게 더 나쁘다 (FR-081 과 같은 판정).
    """


ELEMENT_KINDS = frozenset({AssertionKind.VISIBLE, AssertionKind.HIDDEN})
"""대상 요소가 반드시 필요한 종류 (data-model §5)."""


async def build_assertion(
    page: Page,
    kind: AssertionKind,
    *,
    target_selector: str | None = None,
    value: str | None = None,
    match: MatchMode = MatchMode.EQUALS,
    test_id_attribute: str = "data-testid",
) -> Assertion:
    """조건 하나를 만든다.

    - `url` — 요소를 보지 않는다. 셀렉터를 주면 무시하지 않고 거절한다: 조용히 버리면
      사용자는 대상이 반영됐다고 오해한다.
    - `text` — 셀렉터가 있으면 그 요소, 없으면 화면 전체가 대상이다.
    - `visible`·`hidden` — 셀렉터가 필수다.
    """
    if kind is AssertionKind.URL:
        if target_selector is not None:
            msg = "주소 검증은 대상 요소를 갖지 않습니다. 셀렉터를 비우세요."
            raise AssertionTargetError(msg)
        return Assertion(kind=kind, target=None, match=match, value=value)

    if kind in ELEMENT_KINDS and not target_selector:
        msg = f"{kind.value} 검증은 대상 요소가 필요합니다."
        raise AssertionTargetError(msg)

    target = None
    if target_selector:
        target = await collect_by_selector(page, target_selector, test_id_attribute)
        if target is None:
            msg = (
                f"대상 요소를 찾지 못해 검증 Step 을 만들지 않았습니다: {target_selector}. "
                "화면에 그 요소가 있는지 확인한 뒤 다시 지정하세요."
            )
            raise AssertionTargetError(msg)

    return Assertion(kind=kind, target=target, match=match, value=value)


def default_label(assertion: Assertion) -> str:
    """조건에서 표시 이름을 만든다. 사용자가 이름을 주면 그것을 쓴다."""
    value = assertion.value
    match assertion.kind:
        case AssertionKind.VISIBLE:
            return f"{value or '요소'} 표시 확인"
        case AssertionKind.HIDDEN:
            return f"{value or '요소'} 사라짐 확인"
        case AssertionKind.TEXT:
            return f"텍스트 {value!r} 확인"
        case AssertionKind.URL:
            return f"주소 {value!r} 확인"
    return "검증"  # pragma: no cover - enum 이 4종을 덮는다


def build_step(
    assertion: Assertion,
    step_id: str,
    *,
    label: str | None = None,
    tab: int = 0,
    author: Author = Author.HUMAN,
    timeout_ms: int | None = None,
) -> AssertionStep:
    """검증 Step 을 만든다.

    `author` 를 인자로 받는 이유는 **자연어로 추가한 검증(FR-078)도 같은 함수를 쓰기**
    때문이다. 작성 주체가 다를 뿐 만들어지는 Step 은 같다 (원칙 I).
    """
    kwargs: dict[str, object] = {
        "id": step_id,
        "label": label or default_label(assertion),
        "author": author,
        "tab": tab,
        "assertion": assertion,
    }
    if timeout_ms is not None:
        kwargs["timeout_ms"] = timeout_ms
    return AssertionStep.model_validate(kwargs)
