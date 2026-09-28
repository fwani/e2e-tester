"""검증 조건 구성. FR-037·FR-013a·FR-013b (T100) · 021.

7종(`visible`·`hidden`·`enabled`·`disabled`·`text`·`value`·`url`) 중 하나를 만든다.
**요소를 대상으로 하는 검증에서는 제품이 후보를 수집·검증한다** — 클라이언트가
`TargetLocator` 를 손으로 만들어 보내게 하면 녹화가 만드는 후보와 검증 Step 의 후보가
갈리고, 원칙 IV 의 단일 지점이 무너진다.

클라이언트가 주는 것은 **어느 요소인가**(CSS 셀렉터 하나)와 조건뿐이다.

`{{변수명}}` 참조를 비교 값에 쓸 수 있다 (FR-013b). 이 모듈은 참조를 풀지 않는다 —
해석은 실행 시점에 `VariableResolver` 가 한다. 여기서 풀면 정의 파일에 값이 박힌다.
"""

from __future__ import annotations

from typing import NamedTuple

from playwright.async_api import Page

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.step import AssertionStep, Author
from itb.domain.test_case import SENSITIVE_VARIABLE_PREFIX
from itb.execution.element_probe import ProbedTarget, probe_by_selector
from itb.secrets.resolver import VARIABLE_REF


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
        AssertionKind.VALUE,
    }
)
"""대상 요소가 반드시 필요한 종류 (data-model §5 · 021 · 023).

`enabled`·`disabled` 가 여기 있는 이유는 **대상 없이는 물을 수 없는 질문**이기
때문이다. `hidden` 과 갈리는 지점이기도 하다 — `hidden` 은 대상이 없어도 통과하지만
이 둘은 실패한다 (021 FR-012).

`value` 는 023 이 더했고, **이 집합과 `VALUE_COMPARING_KINDS` 양쪽에 드는 첫 종류다.**
지금까지 둘은 겹치지 않았다 — `text` 는 대상이 선택이었고, 대상이 필수인 넷은 값을
비교하지 않았다. 두 집합이 배타적이라는 전제가 원래 없었으므로 값 추가만으로 성립한다.
"""


class BuiltAssertion(NamedTuple):
    """만들어진 조건과 **함께 보여 줄 안내** (023).

    거절은 여기 없다 — 거절은 예외로 나가고 Step 이 만들어지지 않는다. 여기 담기는 것은
    **만들되 알려 줘야 하는 것**뿐이다 (선택 목록의 내부 식별자 · 입력 칸의 텍스트 검증).

    `build_assertion` 이 조건만 돌려주던 시절에는 이 정보가 갈 곳이 없어 호출자가 요소를
    다시 읽어야 했다. 다시 읽으면 그 사이에 화면이 바뀔 수 있고, 무엇보다 **같은 판정을
    두 번 하는 코드**가 생긴다.
    """

    assertion: Assertion
    notes: list[str]


async def build_assertion_with_notes(
    page: Page,
    kind: AssertionKind,
    *,
    target_selector: str | None = None,
    value: str | None = None,
    match: MatchMode = MatchMode.EQUALS,
    test_id_attribute: str = "data-testid",
) -> BuiltAssertion:
    """조건 하나를 만들고 안내를 함께 돌려준다.

    - `url` — 요소를 보지 않는다. 셀렉터를 주면 무시하지 않고 거절한다: 조용히 버리면
      사용자는 대상이 반영됐다고 오해한다.
    - `text` — 셀렉터가 있으면 그 요소, 없으면 화면 전체가 대상이다.
    - `visible`·`hidden`·`enabled`·`disabled` — 셀렉터가 필수다.
    """
    if kind is AssertionKind.URL:
        if target_selector is not None:
            msg = "주소 검증은 대상 요소를 갖지 않습니다. 셀렉터를 비우세요."
            raise AssertionTargetError(msg)
        # **여기도 `BuiltAssertion` 이어야 한다.** 주소 검증은 요소를 보지 않으므로 안내가
        # 붙을 일이 없지만, 반환 형태가 갈리면 호출자가 두 모양을 다 다뤄야 한다 —
        # 그리고 실제로 그것을 잊어 e2e 가 깨졌다 (023 구현 중).
        return BuiltAssertion(
            assertion=Assertion(kind=kind, target=None, match=match, value=value),
            notes=[],
        )

    if kind in ELEMENT_KINDS and not target_selector:
        msg = f"{kind.value} 검증은 대상 요소가 필요합니다."
        raise AssertionTargetError(msg)

    target = None
    probed: ProbedTarget | None = None
    if target_selector:
        probed = await probe_by_selector(page, target_selector, test_id_attribute)
        if probed is None:
            msg = (
                f"대상 요소를 찾지 못해 검증 Step 을 만들지 않았습니다: {target_selector}. "
                "화면에 그 요소가 있는지 확인한 뒤 다시 지정하세요."
            )
            raise AssertionTargetError(msg)
        target = probed.locator

    # 023 — 입력값 검증은 대상의 성질을 본다. **두 작성 경로가 같은 함수를 부른다.**
    refusal = value_target_refusal(kind, probed, value)
    if refusal is not None:
        raise AssertionTargetError(refusal)

    assertion = Assertion(kind=kind, target=target, match=match, value=value)
    notes = [
        note
        for note in (select_value_note(kind, probed), text_on_input_note(kind, probed))
        if note is not None
    ]
    return BuiltAssertion(assertion=assertion, notes=notes)


async def build_assertion(
    page: Page,
    kind: AssertionKind,
    *,
    target_selector: str | None = None,
    value: str | None = None,
    match: MatchMode = MatchMode.EQUALS,
    test_id_attribute: str = "data-testid",
) -> Assertion:
    """조건만 필요한 호출자를 위한 짝 (안내를 버린다).

    기존 호출자와 검증이 이 이름을 쓰고 있어 남겨 둔다. **새로 쓰는 쪽은 안내가 있는
    짝을 쓴다** — 버리는 것이 기본값이 되면 023 이 만든 안내가 조용히 사라진다.
    """
    built = await build_assertion_with_notes(
        page,
        kind,
        target_selector=target_selector,
        value=value,
        match=match,
        test_id_attribute=test_id_attribute,
    )
    return built.assertion


VALUE_BEARING_TAGS = frozenset({"input", "textarea", "select"})
"""값을 읽을 수 있는 태그 (023 · 실측 확인, research R8a).

그 밖의 요소에 값 읽기를 걸면 **실행이 오류로 끝난다** — 값이 없다는 뜻이다.
"""

VALUELESS_INPUT_TYPES = frozenset({"checkbox", "radio"})
"""값을 갖지만 그 값이 **아무것도 말해 주지 않는** 입력 종류 (023 FR-032).

실측: 체크하든 말든 `'on'` 이 나온다. 체크 상태와 무관한 고정 문자열이므로, 이 대상에
입력값 검증을 걸면 **늘 같은 결과를 내는 검증**이 된다 — 021 FR-014 가 막으려던 것과
같은 종류의 무의미다.
"""


def value_target_refusal(
    kind: AssertionKind, probed: ProbedTarget | None, value: str | None
) -> str | None:
    """입력값 검증을 만들 수 없는 이유. 만들 수 있으면 ``None`` (023 FR-031·FR-032·FR-015).

    ## 왜 경고가 아니라 거절인가 — 021 과 갈리는 지점

    | | 021 상태 검증의 판정 불가 대상 | 023 입력값 검증의 값 없는 대상 |
    |---|---|---|
    | 실행하면 | 「조작할 수 있다」로 **통과**한다 | **오류**로 끝난다 |
    | 정당한 쓸모 | 있다 — ARIA 로 잠금을 표현하는 위젯 | 없다 |
    | 그래서 | 막으면 정당한 경우까지 막힌다 → 경고 | 반드시 실패할 Step 이 남는다 → **거절** |

    제품에 이미 같은 판단이 있다 — 후보를 수집하지 못한 대상에 대해 「재실행에서 반드시
    실패하므로, 만들어 두는 것이 사용자에게 더 나쁘다」.

    ## 문구는 대안을 담는다

    「지원하지 않습니다」로 끝내면 사용자도 모델도 다음에 무엇을 할지 모른다. 특히 **값
    없는 대상에서 텍스트 검증을 가리키는 것**이 중요하다 — 이 기능이 고치려는 실수의
    반대 방향이라, 안 가리키면 두 종류 사이를 오가며 헤맨다.

    ## 판정하지 못하면 거절하지 않는다

    태그를 읽지 못한 경우다. 판정 실패를 거절로 바꾸면 정당한 대상이 막힌다 — 그때는
    실행 시점 오류로 드러난다.
    """
    if kind is not AssertionKind.VALUE or probed is None:
        return None

    tag = probed.tag
    if not tag:
        return None  # 판정하지 못한 것을 거절로 바꾸지 않는다

    if tag not in VALUE_BEARING_TAGS:
        return (
            f"<{tag}> 에는 입력값이 없어 입력값 검증을 만들 수 없습니다. "
            "화면에 보이는 글자를 확인하려면 텍스트 검증을 쓰세요."
        )

    if tag == "input" and probed.input_type in VALUELESS_INPUT_TYPES:
        return (
            f"{probed.input_type} 의 값은 체크 여부와 무관한 고정 문자열이라, "
            "이 검증은 체크하든 말든 같은 결과를 냅니다. "
            "체크 상태 검증은 아직 제공하지 않습니다 — "
            "체크로 화면이 바뀐다면 그 변화를 검증하세요."
        )

    if tag == "input" and probed.input_type == "password":
        return _secret_value_refusal(value)

    return None


def _secret_value_refusal(value: str | None) -> str | None:
    """비밀번호 칸의 비교 값이 정의 파일에 평문을 남기는가 (023 FR-015).

    ## 참조라는 형식이 아니라 **민감한지**가 기준이다

    민감하지 않은 변수는 정의 파일에 값을 갖는다 (`Variable._no_plaintext_secret` 이 막는
    것은 민감 변수의 평문이다). 그러므로 비밀번호 칸의 값을 그것으로 비교하면 **평문을
    적은 것과 결과가 같다.**

    ## 왜 여기서 막아야 하는가

    녹화는 비밀번호 칸에 넣은 값을 민감 변수 참조로 바꾸고, 정의는 민감 변수의 평문을
    거절하고, 공유는 민감 값에 닿는 경로가 차단돼 있다. **검증 Step 의 비교 값만 그
    방어선 밖이었다** — 입력 Step 이 아니므로 위의 어느 규칙도 걸리지 않는다.
    """
    text = (value or "").strip()
    names = VARIABLE_REF.findall(text)
    stripped = VARIABLE_REF.sub("", text).strip()
    if names and not stripped and all(n.startswith(SENSITIVE_VARIABLE_PREFIX) for n in names):
        return None
    return (
        "비밀번호 칸의 값은 정의 파일에 평문으로 남길 수 없습니다. "
        f"{SENSITIVE_VARIABLE_PREFIX} 로 시작하는 민감 변수 참조로만 비교하세요 "
        "(예: {{SECRET_PW}})."
    )


def select_value_note(kind: AssertionKind, probed: ProbedTarget | None) -> str | None:
    """선택 목록을 대상으로 한 입력값 검증에 붙는 안내 (023 FR-033).

    **경고가 아니라 조언이다.** 잘못된 것이 아니라 알아야 할 것이다 — 021 의 관찰 기간
    안내와 같은 성격이며, 021 의 `stateless_target_warning` 과는 성격이 다르다.

    실측: 화면에 `분석` 이 보여도 값은 `analysis` 다 (research R8a).
    """
    if kind is not AssertionKind.VALUE or probed is None or probed.tag != "select":
        return None
    return (
        "선택 목록은 화면에 보이는 항목 이름이 아니라 그 항목의 내부 식별자를 비교합니다. "
        "예를 들어 화면에 「분석」이 보여도 값은 analysis 일 수 있습니다."
    )


def text_on_input_note(kind: AssertionKind, probed: ProbedTarget | None) -> str | None:
    """입력 칸에 텍스트 검증을 고른 사람에게 (023 FR-030).

    **막지 않는다.** 이미 저장된 정의에 그런 조합이 있고, 거절로 바꾸면 그 테스트가
    열리지 않는다 (FR-040 과 충돌한다). 알리기만 한다.

    `select` 는 제외한다 — 자식 `option` 의 글자를 텍스트로 가지므로 관찰값이 비지 않는다.
    """
    if kind is not AssertionKind.TEXT or probed is None:
        return None
    if probed.tag not in {"input", "textarea"}:
        return None
    return (
        "입력 칸은 텍스트로 관찰하면 값이 들어 있어도 언제나 빈 문자열입니다. "
        "칸에 담긴 값을 보려면 「입력값」 검증을 쓰세요."
    )


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
        case AssertionKind.VALUE:
            # **주어가 `입력값` 인 것이 목록에서 두 종류를 가르는 단서다** (023 FR-035).
            # 「텍스트」와 「입력값」은 서로 다른 것을 보며, 그 차이가 이 기능의 출발점이다.
            return f"입력값이 {value!r}{MATCH_PHRASES[assertion.match]} 확인"
        case AssertionKind.URL:
            return f"주소가 {value!r}{MATCH_PHRASES[assertion.match]} 확인"
    return "검증"  # pragma: no cover - enum 이 7종을 덮는다


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
