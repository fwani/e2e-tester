"""검증 조건. FR-013a 의 4종만 지원한다.

요소 갯수 검증과 입력 필드 현재값 검증은 MVP 범위가 아니다 (FR-013c).
"""

from __future__ import annotations

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


class MatchMode(StrEnum):
    EQUALS = "equals"
    CONTAINS = "contains"


class Assertion(BaseModel):
    """검증 Step 의 조건."""

    model_config = ConfigDict(extra="forbid")

    kind: AssertionKind
    target: TargetLocator | None = None
    match: MatchMode = MatchMode.EQUALS
    value: str | None = Field(default=None, max_length=4000)
    """비교 값. ``{{변수명}}`` 참조를 쓸 수 있다 (FR-013b)."""

    @model_validator(mode="after")
    def _check_shape(self) -> Self:
        if self.kind in (AssertionKind.VISIBLE, AssertionKind.HIDDEN):
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
        elif self.kind is AssertionKind.TEXT and not self.value:
            msg = "text 검증은 비교 값이 필요하다"
            raise ValueError(msg)
        return self
