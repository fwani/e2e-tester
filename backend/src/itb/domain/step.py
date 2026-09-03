"""Step 모델. 헌법 원칙 I (Unified Step Model, NON-NEGOTIABLE).

**사람이 만든 Step 과 AI 가 만든 Step 은 같은 타입이다.** ``author`` 는 부가 정보이며
실행 방식을 바꾸지 않는다 (FR-014). 컴포넌트별 별도 표현을 두지 않는다.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from itb.domain.assertion import Assertion
from itb.domain.locator import TargetLocator

STEP_ID_PATTERN = r"^step-\d{2,}$"
DEFAULT_TIMEOUT_MS = 5000
"""디자인 RunResult 의 `timeout 5000 ms` 표기와 research R8 을 따른다."""


class Author(StrEnum):
    HUMAN = "human"
    AI = "ai"


class StepType(StrEnum):
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    NAVIGATE = "navigate"
    ASSERTION = "assertion"
    CLOSE_TAB = "close_tab"


class _StepBase(BaseModel):
    """모든 Step 이 공유하는 필드."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=STEP_ID_PATTERN)
    label: str = Field(min_length=1, max_length=200)
    """사람이 읽는 표시 이름. 목록·결과 화면에 나온다."""

    author: Author = Author.HUMAN
    """작성 주체. **실행 방식을 바꾸지 않는다** (FR-014)."""

    tab: int = Field(default=0, ge=0)
    """탭 참조. 열린 순서이며 최초 탭이 0이다 (FR-030a). 번호는 재사용하지 않는다."""

    timeout_ms: int = Field(default=DEFAULT_TIMEOUT_MS, ge=1, le=60_000)
    frame_url: str | None = Field(default=None, max_length=2000)
    """하위 프레임에서 기록된 경우. MVP 실행은 main frame 만 대상으로 한다."""


class ClickStep(_StepBase):
    type: Literal[StepType.CLICK] = StepType.CLICK
    target: TargetLocator


class FillStep(_StepBase):
    type: Literal[StepType.FILL] = StepType.FILL
    target: TargetLocator
    value: str = Field(max_length=4000)
    """``{{변수명}}`` 참조를 쓸 수 있다. 민감 값은 반드시 참조로만 저장한다 (FR-082)."""


class SelectStep(_StepBase):
    type: Literal[StepType.SELECT] = StepType.SELECT
    target: TargetLocator
    value: str = Field(max_length=2000)


class NavigateStep(_StepBase):
    type: Literal[StepType.NAVIGATE] = StepType.NAVIGATE
    url: str = Field(min_length=1, max_length=2000)


class AssertionStep(_StepBase):
    type: Literal[StepType.ASSERTION] = StepType.ASSERTION
    assertion: Assertion


class CloseTabStep(_StepBase):
    """탭 닫기 (FR-030c). 대상은 공통 ``tab`` 필드가 가리킨다."""

    type: Literal[StepType.CLOSE_TAB] = StepType.CLOSE_TAB


Step = Annotated[
    ClickStep | FillStep | SelectStep | NavigateStep | AssertionStep | CloseTabStep,
    Field(discriminator="type"),
]
"""판별 유니온. 이 하나가 제품 전체의 유일한 테스트 표현이다 (원칙 I)."""


def target_of(step: object) -> TargetLocator | None:
    """Step 의 대상 요소를 꺼낸다. 대상이 없는 종류면 None.

    호출자가 ``isinstance`` 분기를 반복하지 않게 하는 편의 함수다.
    """
    tgt = getattr(step, "target", None)
    if tgt is not None:
        return tgt
    assertion = getattr(step, "assertion", None)
    if assertion is not None:
        return assertion.target
    return None
