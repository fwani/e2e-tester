"""프로젝트·테스트·변수.

테스트 정의는 사용자가 버전 관리에 넣는 자산이다 (FR-088b). 민감 값이 이 안에 들어가지
않도록 스키마 수준에서 막는다 (FR-082).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from itb.domain.step import Step

DSL_VERSION = 1
TEST_ID_PATTERN = r"^TC-\d{3}$"
VARIABLE_NAME_PATTERN = r"^[A-Z][A-Z0-9_]*$"
URL_PATTERN = r"^https?://"
MAX_TABS_DEFAULT = 10
"""동시에 열린 탭 상한 (FR-030g)."""


SENSITIVE_VARIABLE_PREFIX = "SECRET_"
"""민감 값을 옮길 변수 이름의 접두사."""


def make_variable_name(
    basis: str | None, prefix: str = SENSITIVE_VARIABLE_PREFIX
) -> str | None:
    """이름 후보에서 변수 이름을 만든다. 쓸 수 없는 근거면 None.

    반드시 `[A-Z][A-Z0-9_]*` 를 지켜야 한다. **`str.isalnum()` 을 쓸 수 없다** — 한글도
    참이므로 "비밀번호" 같은 라벨이 그대로 통과해 변수 이름 패턴을 위반하고, 저장
    시점에야 테스트 검증이 실패한다. ASCII 영숫자만 남기며, 남는 것이 없으면 None 이다.

    **실패를 None 으로 알린다.** 여기서 순번 이름으로 대체하면 호출자가 "근거에서 만든
    이름" 과 "순번 이름" 을 구분할 수 없다 — 호출자마다 순번의 근거가 다르다.

    이 규칙이 도메인에 있는 이유는 **녹화(FR-082a)와 나중 민감 지정(FR-082b)이 같은
    이름을 만들어야** 하기 때문이다. 두 곳에서 따로 만들면 같은 필드가 경로에 따라 다른
    변수 이름을 얻고, 정의 파일과 비밀 파일이 어긋난다.
    """
    if not isinstance(basis, str):
        return None
    slug = "".join(
        ch if ("a" <= ch.lower() <= "z" or ch.isdigit()) else "_" for ch in basis
    ).upper()
    slug = "_".join(part for part in slug.split("_") if part)
    if not slug or slug[0].isdigit():
        return None
    return f"{prefix}{slug}"[:60]


def fallback_variable_name(index: int, prefix: str = SENSITIVE_VARIABLE_PREFIX) -> str:
    """근거에서 이름을 만들 수 없을 때 쓰는 순번 이름 (한글 전용 라벨 등)."""
    return f"{prefix}VALUE_{index}"


def variable_reference(name: str) -> str:
    """`{{이름}}` 참조 문자열. 형식을 한 곳에서만 만든다."""
    return f"{{{{{name}}}}}"


class AuthoringMode(StrEnum):
    """작성 방식. **테스트를 시작한 방식**으로 결정하며 이후 바뀌지 않는다 (FR-002a)."""

    RECORD = "record"
    AI = "ai"


class BrowserKind(StrEnum):
    CHROMIUM = "chromium"


class Variable(BaseModel):
    """테스트 안에서 값을 대신하는 이름."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    name: str = Field(pattern=VARIABLE_NAME_PATTERN, max_length=100)
    value: str | None = Field(default=None, max_length=4000)
    sensitive: bool = False

    @model_validator(mode="after")
    def _no_plaintext_secret(self) -> Self:
        """민감 변수는 정의 파일에 값을 갖지 않는다.

        이 불변식이 민감 값의 정의 파일 유입을 스키마 수준에서 차단한다 (FR-082).
        실제 값은 별도 비밀 파일의 암호문에 있다 (FR-089c).
        """
        if self.sensitive and self.value is not None:
            msg = (
                f"민감 변수 {self.name} 은 value 를 가질 수 없다. "
                "실제 값은 비밀 파일에 암호문으로 보관한다 (FR-082, FR-089c)"
            )
            raise ValueError(msg)
        return self


class Project(BaseModel):
    """테스트를 담는 최상위 단위. 프로젝트 하나 = 디렉터리 하나."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    name: str = Field(min_length=1, max_length=100)
    default_start_url: str = Field(pattern=URL_PATTERN, max_length=2000)
    browser: BrowserKind = BrowserKind.CHROMIUM
    test_id_attribute: str = Field(default="data-testid", min_length=1, max_length=100)
    """대상 앱이 쓰는 testId 속성명. `data-test`, `data-cy` 등을 쓰는 앱이 흔하다."""

    next_test_number: int = Field(default=1, ge=1, le=999)
    max_tabs: int = Field(default=MAX_TABS_DEFAULT, ge=1, le=50)


class Test(BaseModel):
    """하나의 테스트 시나리오. `tests/` 아래 YAML 파일 하나에 대응한다."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    dsl_version: int = DSL_VERSION
    id: str = Field(pattern=TEST_ID_PATTERN)
    name: str = Field(min_length=1, max_length=200)
    authoring_mode: AuthoringMode
    start_url: str = Field(pattern=URL_PATTERN, max_length=2000)
    browser: BrowserKind = BrowserKind.CHROMIUM
    variables: list[Variable] = Field(default_factory=list)
    steps: list[Step] = Field(min_length=1)
    """**1개 이상** — Step 이 없는 테스트는 저장할 수 없다 (FR-029)."""

    ai_instruction: str | None = Field(default=None, max_length=8000)
    """자연어 지시문 원문. **실행 대상이 아니다** (FR-063). 작성 의도의 기록일 뿐이다."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _check_refs(self) -> Self:
        seen_step_ids: set[str] = set()
        for st in self.steps:
            if st.id in seen_step_ids:
                msg = f"Step id 가 중복됐다: {st.id}"
                raise ValueError(msg)
            seen_step_ids.add(st.id)

        names = [v.name for v in self.variables]
        if len(names) != len(set(names)):
            msg = "변수 이름이 중복됐다"
            raise ValueError(msg)

        declared = set(names)
        for ref in self.referenced_variables():
            if ref not in declared:
                msg = f"정의되지 않은 변수를 참조한다: {{{{{ref}}}}}"
                raise ValueError(msg)

        if self.dsl_version != DSL_VERSION:
            msg = (
                f"지원하지 않는 dsl_version: {self.dsl_version} "
                f"(이 버전은 {DSL_VERSION} 만 읽는다)"
            )
            raise ValueError(msg)
        return self

    def referenced_variables(self) -> set[str]:
        """Step 값과 검증 조건에서 참조하는 ``{{변수명}}`` 이름 집합."""
        import re

        pat = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
        found: set[str] = set()
        for st in self.steps:
            for text in (
                getattr(st, "value", None),
                getattr(getattr(st, "assertion", None), "value", None),
                getattr(st, "url", None),
            ):
                if isinstance(text, str):
                    found.update(pat.findall(text))
        return found

    def sensitive_variable_names(self) -> set[str]:
        return {v.name for v in self.variables if v.sensitive}
