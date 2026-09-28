"""검증 조건. 7종을 지원한다 (001 FR-013a + 021 + 023).

## 023 이 001 FR-013c 의 판단 하나를 뒤집었다

001 은 **입력 필드 현재값 검증**을 범위 밖에 두었고 021 이 그 판단을 유지했다. 023 이
그것을 되돌린다 — 범위를 넓히고 싶어서가 아니라, **그 빈칸이 다른 검증을 망가뜨리고
있었기 때문이다.**

입력 칸에는 값을 묻는 수단이 없었으므로 사용자와 AI 는 텍스트 검증을 골랐다. 그런데
``<input>`` 의 값은 자식 텍스트 노드가 아니라 요소의 값 속성이라, 텍스트로 관찰하면
**칸이 가득 차 있어도 언제나 빈 문자열**이다. 그 검증은 구조적으로 100% 실패했고,
021 이 부정 비교를 더한 뒤에는 더 나빠졌다 — 「`오류` 를 포함하지 않는다」가 아무것도
검증하지 않은 채 통과한다.

**표현 수단이 없으면 사람은 가장 가까운 것을 고른다.** 어휘의 빈칸이 옆 어휘를 오염시킨
것이고, 그래서 이것은 확장이 아니라 수정이다.

## 아직 범위 밖인 것

요소 갯수 검증은 여전히 범위가 아니다 (001 FR-013c). 체크 상태와 읽기 전용도 범위
밖이다 (021) — 조작 가능 여부로 대부분 대체되고, 필요해지면 같은 축에 값을 더하는
형태가 된다. **입력값 검증으로 체크 상태를 대신할 수 없다**는 점은 023 이 분명히 했다:
체크박스의 값은 체크 여부와 무관한 고정 문자열이라(실측 확인), 그 대상에 이 검증을 걸면
늘 같은 결과를 내는 검증이 된다.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from itb.domain.locator import TargetLocator


class AssertionKind(StrEnum):
    VISIBLE = "visible"
    """요소가 화면에 보인다."""

    HIDDEN = "hidden"
    """요소가 없거나 보이지 않는다. 처음부터 없던 경우와 사라진 경우 모두 통과한다."""

    TEXT = "text"
    """텍스트 일치 또는 포함. target 이 있으면 그 요소, 없으면 화면 전체."""

    URL = "url"
    """현재 화면 주소 일치 또는 포함. 요소 탐색을 하지 않는다."""

    VALUE = "value"
    """입력 칸에 **담긴 값** (023).

    ``TEXT`` 와 다르다 — 「화면에 보이는 글자」와 「칸에 담긴 값」은 서로 다른 사실이고,
    그 구별이 저장된 정의에 남아야 한다. ``<input>``·``<textarea>``·``<select>`` 가
    대상이며, 그 밖의 요소에는 값이 없어 작성 시점에 거절된다.

    **텍스트 검증에 「값으로 읽기」 옵션을 붙이지 않은 이유**는 하나의 종류가 설정에 따라
    다른 것을 보게 되기 때문이다. 정의만 보고는 무엇을 비교하는지 알 수 없고, 대상의
    성질이 저장되지 않으므로 생성기는 판단할 근거조차 없다 — 제품 안 실행과 내보낸
    코드가 갈린다 (023 research R1).
    """

    ENABLED = "enabled"
    """요소를 조작할 수 있다 (021).

    ``VISIBLE`` 과 다르다 — 보이는 것과 누를 수 있는 것은 별개다. `disabled` 가 붙은
    버튼은 보이면서 눌리지 않고, 그 상태를 기존 네 종류로는 표현할 수 없었다.
    """

    DISABLED = "disabled"
    """요소를 조작할 수 없다 (021).

    **``HIDDEN`` 과 갈리는 지점은 대상이 없을 때다.** ``HIDDEN`` 은 없어도 통과하지만
    이 검증은 **실패한다.** 「없다」와 「있는데 잠겼다」는 다른 사실이고, 한 검증이 둘을
    함께 통과시키면 결과를 보고 어느 쪽이었는지 알 수 없다 (021 FR-012).
    """


class MatchMode(StrEnum):
    EQUALS = "equals"
    CONTAINS = "contains"

    NOT_EQUALS = "not_equals"
    """같지 않다 (021)."""

    NOT_CONTAINS = "not_contains"
    """포함하지 않는다 (021).

    ## 부정을 종류가 아니라 비교 방식에 둔 이유 (021 research R1)

    ``kind`` 는 「무엇을 보는가」이고 ``match`` 는 「어떻게 비교하는가」다. 부정은 비교
    방법이지 관찰 대상이 아니다. ``value`` 와 ``match`` 를 쓰는 종류는 ``TEXT``·``URL``
    둘뿐이고 부정형이 필요한 것도 정확히 그 둘이라, 새 값이 이미 있는 축에 그대로 얹힌다.

    ``negate`` 플래그를 두지 않은 이유는 ``equals`` + negate 와 ``not_equals`` 가 같은
    뜻이 되기 때문이다 — 저장된 정의에 두 표현이 공존하면 두 정의가 같은지 비교할 수
    없다 (`UploadStep` 이 확장자를 별도 필드로 두지 않은 것과 같은 판단).
    """


NEGATED_MATCHES = frozenset({MatchMode.NOT_EQUALS, MatchMode.NOT_CONTAINS})
"""부정 비교. **값을 비교하는 종류에서만 쓸 수 있다** (021 FR-002)."""

VALUE_COMPARING_KINDS = frozenset(
    {AssertionKind.TEXT, AssertionKind.URL, AssertionKind.VALUE}
)
"""비교 값을 갖는 종류. 부정 비교가 허용되는 것도 이것들뿐이다.

``VALUE`` 를 여기 더하는 것만으로 부정 비교가 열린다 — ``_check_negation`` 은 이 집합을
읽을 뿐이므로 고치지 않았다 (023).
"""

STATE_KINDS = frozenset({AssertionKind.ENABLED, AssertionKind.DISABLED})
"""요소의 조작 가능 여부를 보는 종류 (021). 대상이 필수이고 비교 값을 갖지 않는다.

``VALUE`` 는 여기 들지 않는다 — 대상이 필수인 것은 같지만 **값을 비교하기** 때문이다.
023 의 ``VALUE`` 가 「대상 필수」와 「값 비교」 양쪽 성질을 함께 갖는 첫 종류이며, 두
성질이 배타적이라는 전제가 원래 없었으므로 규칙 추가만으로 성립한다.
"""


class Assertion(BaseModel):
    """검증 Step 의 조건."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    kind: AssertionKind
    target: TargetLocator | None = None
    match: MatchMode = MatchMode.EQUALS
    value: str | None = Field(default=None, max_length=4000)
    """비교 값. ``{{변수명}}`` 참조를 쓸 수 있다 (FR-013b)."""

    @model_validator(mode="after")
    def _check_shape(self) -> Self:
        """형태 규칙. **021 data-model.md §2 의 표가 권위다.**

        ## 기존 두 비교 방식의 허용 범위를 넓히지도 좁히지도 않는다

        ``visible`` + ``contains`` 처럼 뜻이 없는 조합이 이미 저장된 정의에 있을 수 있다
        (지금 무시된다). 여기서 거절하면 예전 정의가 열리지 않으므로, **검사 대상은 021
        이 새로 더한 부정 비교뿐이다.** 하위 호환은 이 경계가 만든다.
        """
        self._check_negation()
        if self.kind in STATE_KINDS:
            if self.target is None:
                msg = f"{self.kind} 검증은 target 이 필요하다"
                raise ValueError(msg)
            if self.value is not None:
                # 새 종류는 처음부터 닫는다. `visible`·`hidden` 이 value 를 열어 둔 것은
                # 표시 이름 생성이 실제로 그것을 읽기 때문이고, 나중에 닫을 수는 없다.
                msg = f"{self.kind} 검증은 비교 값을 갖지 않는다"
                raise ValueError(msg)
        elif self.kind in (AssertionKind.VISIBLE, AssertionKind.HIDDEN):
            if self.target is None:
                msg = f"{self.kind} 검증은 target 이 필요하다"
                raise ValueError(msg)
        elif self.kind is AssertionKind.URL:
            if self.target is not None:
                msg = "url 검증은 요소 탐색을 하지 않는다. target 을 두지 않는다"
                raise ValueError(msg)
            if not self.value:
                msg = "url 검증은 비교 값이 필요하다"
                raise ValueError(msg)
        elif self.kind is AssertionKind.VALUE:
            # 023 — **대상 필수 + 값 필수.** `text` 와 달리 「화면 전체」 경우가 없다:
            # 대상 없는 입력값 검증은 물을 수 있는 질문이 아니다.
            if self.target is None:
                msg = "value 검증은 어느 칸인지 가리키는 target 이 필요하다"
                raise ValueError(msg)
            if not self.value:
                msg = "value 검증은 비교 값이 필요하다"
                raise ValueError(msg)
        elif self.kind is AssertionKind.TEXT and not self.value:
            msg = "text 검증은 비교 값이 필요하다"
            raise ValueError(msg)
        return self

    def _check_negation(self) -> None:
        """부정 비교는 값을 비교하는 종류에서만, 그리고 값이 있어야 쓸 수 있다 (021)."""
        if self.match not in NEGATED_MATCHES:
            return
        if self.kind not in VALUE_COMPARING_KINDS:
            # 조용히 무시하면 사용자의 오해가 정의 파일에 남는다. 요소가 보이지 않음을
            # 뜻하려던 것이라면 `hidden` 이 그 자리다.
            msg = (
                f"{self.kind} 검증은 값을 비교하지 않으므로 {self.match} 를 쓸 수 없다. "
                "요소가 없거나 보이지 않음은 hidden 검증이다"
            )
            raise ValueError(msg)
        if not self.value:
            # 빈 문자열을 포함하지 않는 화면은 없다 — 통과할 수 없는 검증이 된다.
            msg = f"{self.match} 비교는 비어 있지 않은 값이 필요하다"
            raise ValueError(msg)

    @property
    def negated(self) -> bool:
        """이 조건이 부정형인가. 화면 문구와 실패 설명이 함께 읽는다."""
        return self.match in NEGATED_MATCHES


MAX_OBSERVED_CHARS = 4000
"""작성 시점 관찰값의 길이 상한 (020 FR-008).

``Assertion.value`` 의 상한과 **같은 값이다.** 기대값보다 관찰값이 더 길게 남을 이유가
없고, 두 상한이 다르면 어느 쪽이 기준인지 설명할 말이 없다.
"""


class AuthoringMismatch(BaseModel):
    """작성 시점에 이 검증이 통과하지 않았다는 기록 (020 FR-005·FR-008).

    ## 이것이 있는 이유 — 정의는 제품 동작의 사본이 아니다

    지시문이 「저장하면 `저장되었습니다` 가 뜬다」를 요구했는데 제품이 `처리 완료` 를
    띄우면, 지금까지의 제품은 **검증 Step 을 만들지 않았다.** 성공한 것만 기록하는
    규칙(001 FR-061)이 검증에도 걸려 있었기 때문이다. 모델에게는 통과하는 값을 찾는
    것 외에 선택지가 없었고, 그래서 버그값이 정답으로 굳었다.

    이 모델이 그 자리를 채운다. **기대와 달랐다는 사실을 기록하고 Step 은 남긴다.**

    ## 기대값은 여기에 없다

    기대값의 유일한 출처는 ``AssertionStep.assertion.value`` 다. 여기에 복제해 두면
    Step 편집으로 조건을 고쳤을 때 둘이 갈리고, 그때 어느 쪽이 맞는지 아무도 모른다
    (`UploadStep` 이 확장자를 별도 필드로 두지 않는 것과 같은 판단).

    ## 결함이라고 판정하지 않는다

    이름이 「결함」이 아니라 「어긋남」인 이유다. 기대와 관찰이 달랐다는 것은 사실이고,
    그것이 제품 결함인지 지시문 오류인지는 **사람이 판단한다.**
    """

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    observed: str = Field(min_length=1, max_length=MAX_OBSERVED_CHARS)
    """작성 시점에 화면이 어땠는지. 실행기가 만든 실패 설명을 스크러빙한 것이다.

    **비어 있을 수 없다.** 빈 문자열은 「화면이 비어 있었다」로 읽힌다 — 적을 것이 없는
    상황은 어긋남이 아니라 **대상 없음**이고, 그때는 Step 자체가 만들어지지 않는다
    (FR-007).

    새 관찰 로직을 만들지 않고 실행기의 설명을 쓰는 이유는, 같은 상황을 두 곳이 서로
    다르게 설명하면 화면의 문구와 실행 결과의 문구가 갈리기 때문이다.
    """

    truncated: bool = False
    """``observed`` 가 상한에서 잘렸는가 (FR-008).

    잘렸다는 사실이 드러나지 않으면 사람이 그 문장을 화면 전체로 읽는다.
    """

    recorded_at: datetime
    """언제 기록됐는가.

    「얼마나 오래된 결함 후보인가」를 사람이 판단할 근거다. 반년 전에 기록된 어긋남과
    어제 것은 같은 무게가 아니다.
    """
