"""검증 조건 구성. FR-037·FR-013a·FR-013b (T100) · 021.

6종(`visible`·`hidden`·`enabled`·`disabled`·`text`·`url`) 중 하나를 만든다. **요소를 대상으로 하는 검증에서는
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


ELEMENT_KINDS = frozenset(
    {
        AssertionKind.VISIBLE,
        AssertionKind.HIDDEN,
        AssertionKind.ENABLED,
        AssertionKind.DISABLED,
    }
)
"""대상 요소가 반드시 필요한 종류 (data-model §5 · 021).

`enabled`·`disabled` 가 여기 있는 이유는 **대상 없이는 물을 수 없는 질문**이기
때문이다. `hidden` 과 갈리는 지점이기도 하다 — `hidden` 은 대상이 없어도 통과하지만
이 둘은 실패한다 (021 FR-012).
"""


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
    - `visible`·`hidden`·`enabled`·`disabled` — 셀렉터가 필수다.
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


STATEFUL_TAGS = frozenset(
    {"button", "input", "select", "textarea", "option", "optgroup", "fieldset"}
)
"""조작 가능 여부를 실제로 가질 수 있는 태그 (021 FR-014).

HTML 의 `disabled` 속성이 의미를 갖는 요소들이다. `a` 는 일부러 뺐다 — 링크에는
`disabled` 가 없고, 브라우저는 언제나 「조작할 수 있다」로 답한다.
"""


def stateless_target_warning(assertion: Assertion) -> str | None:
    """상태 검증의 대상이 조작 가능 여부를 가질 수 없으면 경고 문구를 돌려준다.

    ## 왜 막지 않고 알리는가

    막으면 `contenteditable` 이나 ARIA 로 잠금을 표현하는 정당한 위젯까지 막힌다.
    그런 화면에서 사용자가 할 수 있는 일이 없어진다.

    ## 왜 실행 판정을 바꾸지 않는가

    브라우저는 이런 요소에 「조작할 수 있다」를 참으로 준다. 태그를 보고 판정을
    뒤집으면 원칙 II 의 결정성(같은 화면이면 같은 결과)에 예외가 생긴다. 실행은
    브라우저가 주는 값을 그대로 쓰고, **작성 시점에 사람에게 말한다.**

    ## 왜 경고가 필요한가 — 방향이 비대칭이다

    | 검증 | 이런 대상에서 | 위험 |
    |---|---|---|
    | 「조작할 수 없다」 | 항상 실패 | 낮다 — 사람이 알아차린다 |
    | 「조작할 수 있다」 | 항상 통과 | **높다 — 아무것도 검증하지 않은 초록색** |
    """
    if assertion.kind not in (AssertionKind.ENABLED, AssertionKind.DISABLED):
        return None
    tag = (assertion.target.tag or "").lower() if assertion.target else ""
    if not tag or tag in STATEFUL_TAGS:
        return None
    return (
        f"<{tag}> 는 조작 가능 여부를 갖지 않는 요소라 브라우저가 언제나 "
        "「조작할 수 있다」로 답합니다. 이 검증은 늘 같은 결과를 내므로 "
        "버튼·입력처럼 실제로 잠길 수 있는 요소를 대상으로 삼으세요."
    )


MATCH_PHRASES = {
    MatchMode.EQUALS: "와 같음",
    MatchMode.CONTAINS: "를 포함",
    MatchMode.NOT_EQUALS: "와 다름",
    MatchMode.NOT_CONTAINS: "를 포함하지 않음",
}
"""표시 이름에 들어갈 비교 방식 (021 FR-023).

**긍정과 부정이 이름에서 갈려야 한다.** 021 이전 이름은 비교 방식을 담지 않아서,
「`오류` 가 있어야 한다」와 「`오류` 가 없어야 한다」가 목록에서 똑같이 보였다 — 정반대
뜻의 두 Step 을 구별할 수 없는 것은 표시 문제가 아니라 결함이다.
"""


def default_label(assertion: Assertion) -> str:
    """조건에서 표시 이름을 만든다. 사용자가 이름을 주면 그것을 쓴다."""
    value = assertion.value
    match assertion.kind:
        case AssertionKind.VISIBLE:
            return f"{value or '요소'} 표시 확인"
        case AssertionKind.HIDDEN:
            return f"{value or '요소'} 사라짐 확인"
        case AssertionKind.ENABLED:
            return "요소를 조작할 수 있음 확인"
        case AssertionKind.DISABLED:
            return "요소를 조작할 수 없음 확인"
        case AssertionKind.TEXT:
            return f"텍스트가 {value!r}{MATCH_PHRASES[assertion.match]} 확인"
        case AssertionKind.URL:
            return f"주소가 {value!r}{MATCH_PHRASES[assertion.match]} 확인"
    return "검증"  # pragma: no cover - enum 이 6종을 덮는다


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
