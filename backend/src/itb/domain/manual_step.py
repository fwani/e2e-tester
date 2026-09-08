"""사람이 **손으로** 만들 수 있는 Step 의 서술 (009 FR-285·FR-286).

## 이 모듈이 있는 이유

Step 을 추가하는 길이 셋뿐이었고 셋 다 「살아 있는 브라우저 + 일시정지」를 요구했다.
그 요구의 근거는 하나다 — **요소 후보는 살아 있는 페이지에서만 수집·검증된다**
(헌법 원칙 IV). 그런데 요소를 지목하지 않는 Step 종류가 넷 있고, 그것까지 같은 잠금에
걸려 있었다 (009 관찰 M-11).

이 모듈은 그 넷을 **명시적인 목록**으로 만든다. 목록이 있으면 「일부는 손으로 만들 수
있다」를 표현할 수 있고, 없으면 전부 못 만드는 쪽으로 정리된다 — 006 이 그랬다.

## 왜 domain 인가

「무엇이 요소 지목을 요구하는가」는 **Step 모델의 성질**이다. ``NavigateStep`` 은 ``url``
을 갖고 ``ClickStep`` 은 ``TargetLocator`` 를 갖는다 — 그 판단의 근거가 ``step.py`` 에
있으므로 목록도 그 옆에 있어야 한다.

또 헌법의 **Cross-language schema duty** 가 스키마를 한 곳에 두라고 요구한다. 여기 두면
``itb.schema.export`` 가 JSON Schema 로 내보내고 프론트엔드는 생성 타입으로 받는다 —
손으로 유지하는 목록이 두 벌이 되지 않는다 (009 research R1).

## 원칙 IV 를 **타입으로** 지킨다

``ManualStepSpec`` 은 판별 유니온이며 ``click``·``fill``·``select``·``hover``·``drag``
가 **성립하지 않는다.** 런타임 ``if`` 로 막으면 그 검사를 지나가는 경로가 언젠가 생기지만,
요청 모델에 그 종류가 없으면 그런 경로를 쓸 수 없다.

**``target`` 을 받는 필드가 하나도 없다.** 손으로 넣은 후보는 검증 상태를 얻을 수 없고,
그것을 ``verified`` 로 적으면 거짓이며 아니면 조용히 무효인 정의가 된다 (006 FR-187 제외
결정과 같은 근거).

## 새 Step 종류를 만들지 않는다

``build_step`` 이 만드는 것은 기존 ``NavigateStep``·``CloseTabStep``·``AssertionStep``
이다 (원칙 I). 그래서 실행·생성기·내보내기를 고칠 것이 없다 — 생성기는 이미 이 셋을
다룬다 (원칙 V).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.step import (
    AssertionStep,
    Author,
    CloseTabStep,
    NavigateStep,
    Step,
)

LABEL_MAX = 200
"""표시 이름의 길이 한도. ``_StepBase.label`` 과 같은 값이어야 한다.

여기 상수로 두는 이유: 파생 라벨을 자를 때 쓴다. ``step.py`` 의 필드 제약을 넘기면
저장 시점이 아니라 **만드는 순간** 검증이 터지고, 그때 사용자는 자기가 넣은 주소가 길다는
것 말고는 알 수 없다.
"""


class InsertableKind(StrEnum):
    """손으로 만들 수 있는 Step 종류. **이 목록이 정본이다** (FR-286).

    Step 종류가 늘 때 고치는 곳은 여기와 아래 ``ManualStepSpec`` 뿐이다. 프론트엔드는
    생성 타입으로 받으므로 자동으로 따라온다.

    **여기 없는 종류는 이 경로로 만들 수 없다** (FR-287) — ``click``·``fill``·
    ``select``·``hover``·``drag``, 그리고 ``assertion`` 의 ``visible``·``hidden``(대상
    필수)과 대상이 있는 ``text``. 감추지 않고 화면이 이유를 밝힌다.
    """

    NAVIGATE = "navigate"
    """주소로 이동. 주소만 있으면 성립한다."""

    CLOSE_TAB = "close_tab"
    """탭 닫기. 대상은 공통 ``tab`` 필드가 가리킨다."""

    ASSERT_URL = "assert_url"
    """현재 주소 검증. ``Assertion`` 검증기가 ``url`` 에 ``target`` 두는 것을 이미 거절한다."""

    ASSERT_TEXT = "assert_text"
    """화면 **전체** 텍스트 검증. ``target`` 이 없으면 화면 전체를 본다 (``assertion.py``)."""


class _SpecBase(BaseModel):
    """모든 서술이 공유하는 필드.

    ``id`` 를 받지 않는다 — 서버가 ``allocate_step_id`` 로 만든다. 그 함수는 「이미 쓰인
    번호를 피한다」를 갖고 있고, 그 규칙을 화면이 복제하면 리코더가 매긴 번호와 충돌한다.

    ``author`` 도 받지 않는다. 손으로 넣은 것은 ``human`` 이며 서버가 정한다. ``author``
    는 실행 방식을 바꾸지 않는다 (원칙 I).
    """

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    label: str | None = Field(default=None, min_length=1, max_length=LABEL_MAX)
    """생략하면 서술에서 파생한다 (``derive_label``)."""

    tab: int = Field(default=0, ge=0)
    timeout_ms: int | None = Field(default=None, ge=1, le=60_000)
    """생략하면 Step 의 기본값을 쓴다."""


class NavigateSpec(_SpecBase):
    kind: Literal[InsertableKind.NAVIGATE] = InsertableKind.NAVIGATE
    url: str = Field(min_length=1, max_length=2000)


class CloseTabSpec(_SpecBase):
    kind: Literal[InsertableKind.CLOSE_TAB] = InsertableKind.CLOSE_TAB


class AssertUrlSpec(_SpecBase):
    kind: Literal[InsertableKind.ASSERT_URL] = InsertableKind.ASSERT_URL
    url: str = Field(min_length=1, max_length=2000)
    """기대하는 주소. ``match`` 가 ``contains`` 면 일부만 적어도 된다."""

    match: MatchMode = MatchMode.EQUALS


class AssertTextSpec(_SpecBase):
    kind: Literal[InsertableKind.ASSERT_TEXT] = InsertableKind.ASSERT_TEXT
    value: str = Field(min_length=1, max_length=4000)
    """기대 텍스트. ``{{변수명}}`` 참조를 쓸 수 있다.

    **평문 민감 값을 여기 넣지 않는다.** 실제 값은 비밀 값 엔드포인트가 다루고 정의에는
    참조만 남는다 (FR-082·FR-212).
    """

    match: MatchMode = MatchMode.CONTAINS
    """화면 전체 텍스트에는 ``contains`` 가 기본이다 — 전체 일치는 실무에서 거의 쓰이지 않는다."""


ManualStepSpec = Annotated[
    NavigateSpec | CloseTabSpec | AssertUrlSpec | AssertTextSpec,
    Field(discriminator="kind"),
]
"""손으로 넣을 Step 의 서술. **판별자는 ``kind``** 다.

``Step`` 의 판별자가 ``type`` 인 것과 갈리는 것은 의도다 — 이것은 Step 이 아니라 Step 을
만드는 **입력**이고, 종류 집합도 다르다(넷 대 여덟). 같은 이름을 쓰면 둘이 교환 가능한
것처럼 읽힌다.
"""


def _clip(text: str, room: int) -> str:
    """라벨에 들어갈 값을 자른다. 자랐으면 자랐다고 표시한다."""
    if len(text) <= room:
        return text
    return text[: max(room - 1, 0)] + "…"


def derive_label(spec: ManualStepSpec) -> str:
    """서술에서 표시 이름을 만든다 (009 research R6).

    **화면이 만들지 않는다.** 화면이 만들면 같은 종류의 Step 이 만든 경로에 따라 다른
    이름을 갖는다 — 리코더가 만든 것, AI 가 만든 것, 손으로 넣은 것이 목록에서 서로
    다르게 보인다.
    """
    if isinstance(spec, NavigateSpec):
        prefix = "주소로 이동 — "
        return prefix + _clip(spec.url, LABEL_MAX - len(prefix))
    if isinstance(spec, CloseTabSpec):
        return f"탭 {spec.tab} 닫기"
    if isinstance(spec, AssertUrlSpec):
        prefix = "주소 검증 — "
        return prefix + _clip(spec.url, LABEL_MAX - len(prefix))
    prefix = "화면 텍스트 검증 — "
    return prefix + _clip(spec.value, LABEL_MAX - len(prefix))


def build_step(spec: ManualStepSpec, step_id: str) -> Step:
    """서술과 id 로 도메인 Step 을 만든다. **순수 함수다.**

    ``author`` 는 항상 ``human`` 이다. 만드는 종류는 기존 셋이며 **새 Step 종류를 만들지
    않는다** (원칙 I·V).
    """
    label = spec.label or derive_label(spec)
    common: dict[str, object] = {"id": step_id, "label": label, "author": Author.HUMAN}
    # 생략된 타임아웃은 **넘기지 않는다** — Step 이 자기 기본값을 갖는다 (DEFAULT_TIMEOUT_MS).
    if spec.timeout_ms is not None:
        common["timeout_ms"] = spec.timeout_ms

    if isinstance(spec, NavigateSpec):
        # navigate 는 탭을 옮기지 않는다. 공통 tab 은 그대로 실린다.
        return NavigateStep(**common, tab=spec.tab, url=spec.url)  # type: ignore[arg-type]
    if isinstance(spec, CloseTabSpec):
        return CloseTabStep(**common, tab=spec.tab)  # type: ignore[arg-type]
    if isinstance(spec, AssertUrlSpec):
        return AssertionStep(
            **common,  # type: ignore[arg-type]
            tab=spec.tab,
            assertion=Assertion(kind=AssertionKind.URL, match=spec.match, value=spec.url),
        )
    return AssertionStep(
        **common,  # type: ignore[arg-type]
        tab=spec.tab,
        # target 을 두지 않는다 — 화면 전체 텍스트를 본다 (assertion.py 의 규칙).
        assertion=Assertion(kind=AssertionKind.TEXT, match=spec.match, value=spec.value),
    )
