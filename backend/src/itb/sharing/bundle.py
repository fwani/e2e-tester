"""공유 묶음의 모양 (기능 019 · data-model §2).

묶음은 **봉투**이지 테스트의 두 번째 표현이 아니다. 안에 실리는 것은
:class:`itb.domain.test_case.Test` **그대로**이며, 이 모듈은 그것을 감싸는 매니페스트만
정의한다. 테스트를 별도 모델로 다시 정의하면 두 모양이 갈리고, 갈린 순간 헌법 원칙 I 이
깨진다 — 같은 테스트가 어디를 거쳤느냐에 따라 다르게 실행된다.

**민감 값이 들어갈 자리가 없다.** :class:`itb.domain.test_case.Variable` 이
``sensitive=True`` 인 변수의 ``value`` 를 스키마 수준에서 거부하므로, `Test` 를 그대로
직렬화하는 한 값이 실릴 곳이 없다. 이 모듈이 `itb.secrets` 를 임포트하지 못하는 것은
`.importlinter` 가 강제한다 (research R3).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from itb.domain.test_case import (
    URL_PATTERN,
    VARIABLE_NAME_PATTERN,
    VARIABLE_REFERENCE_PATTERN,
    VARIABLE_VALUE_FIELDS,
    BrowserKind,
    Test,
    TestGroup,
    step_field_text,
)
from itb.sharing.limits import (
    BUNDLE_VERSION,
    MAX_BUNDLE_GROUPS,
    MAX_BUNDLE_TESTS,
)

_MODEL_CONFIG = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)


class ValueUsage(BaseModel):
    """어떤 변수가 **어디서** 쓰이는지 (FR-040).

    이름만 보여 주면 받는 사람은 무엇을 넣을지 모른다. 「TC-001 의 '비밀번호 입력' 스텝」
    까지 보여야 자기 계정의 어떤 값인지 판단할 수 있다.
    """

    model_config = _MODEL_CONFIG

    test_id: str
    step_id: str
    step_label: str | None = None
    field: str
    """:data:`itb.domain.test_case.VARIABLE_VALUE_FIELDS` 중 하나."""


class RequiredValue(BaseModel):
    """받는 사람이 **채워야 실행되는 것** 하나 (FR-040 · data-model §2.3).

    민감한 것과 그렇지 않은 것을 한 모델에 둔다. 받는 사람에게는 둘 다 "비어 있어서 채워야
    하는 것" 이고, 다른 것은 저장 위치뿐이다 — 민감한 것은 봉인 저장소로, 그렇지 않은 것은
    테스트 정의로 간다 (FR-048).
    """

    model_config = _MODEL_CONFIG

    name: str = Field(pattern=VARIABLE_NAME_PATTERN, max_length=100)
    sensitive: bool
    declared: bool = True
    """묶음에 변수 선언이 있었는가. 거짓이면 참조만 있어 **보충한 것**이다 (FR-047)."""

    usages: list[ValueUsage] = Field(min_length=1)


class BundleProject(BaseModel):
    """묶음이 나르는 프로젝트 설정 (data-model §2.2).

    :class:`itb.domain.test_case.Project` 에서 ``next_test_number`` 를 뺀 것이다. 그 필드는
    이미 쓰이지 않는 하위 호환 잔재이며(도메인 주석), 묶음에 실으면 새 형식이 옛 잔재를
    물려받는다.
    """

    model_config = _MODEL_CONFIG

    name: str = Field(min_length=1, max_length=100)
    default_start_url: str = Field(pattern=URL_PATTERN, max_length=2000)
    browser: BrowserKind = BrowserKind.CHROMIUM
    test_id_attribute: str = Field(default="data-testid", min_length=1, max_length=100)
    max_tabs: int = Field(default=10, ge=1, le=50)
    groups: list[TestGroup] = Field(default_factory=list, max_length=MAX_BUNDLE_GROUPS)


class ShareBundle(BaseModel):
    """전달 가능한 파일 하나의 내용 전체."""

    model_config = _MODEL_CONFIG

    bundle_version: int = BUNDLE_VERSION
    """**테스트 정의의 ``dsl_version`` 과 별개다** (research R2).

    봉투가 바뀌는 주기와 스텝 모델이 바뀌는 주기가 다르다. 한 숫자로 묶으면 봉투를 고칠
    때마다 모든 테스트 파일의 버전을 올려야 한다.

    여기서 값을 검증하지 않는다 — 읽을 수 있는지 판정하는 것은 :mod:`itb.sharing.reader`
    의 일이고, 거기서 사용자에게 보여 줄 사유와 함께 거절한다.
    """

    generator: str = Field(default="itb", min_length=1, max_length=100)
    """만든 도구 이름·버전. 표시·진단용이며 **판정에 쓰지 않는다.**"""

    created_at: dt.datetime
    project: BundleProject
    required_values: list[RequiredValue] = Field(default_factory=list)
    """**참고용 요약이며 정본이 아니다** (research R7).

    가져오는 쪽은 이 목록을 믿지 않고 테스트 정의에서 다시 계산한다 — 파일이 손으로
    편집될 수 있기 때문이다.
    """

    tests: list[Test] = Field(min_length=1, max_length=MAX_BUNDLE_TESTS)


# ─── 필요 값 산출 (FR-040 · research R7) ────────────────────────────────────


def _usages_by_name(tests: list[Test]) -> dict[str, list[ValueUsage]]:
    """테스트 목록에서 변수 이름 → 쓰이는 자리 목록.

    :data:`itb.domain.test_case.VARIABLE_VALUE_FIELDS` 를 돈다 — 참조하는 *이름*을 찾는
    `referenced_variable_names` 와 **같은 자리**를 봐야 한다.
    """
    found: dict[str, list[ValueUsage]] = {}
    for test in tests:
        for step in test.steps:
            for field in VARIABLE_VALUE_FIELDS:
                text = step_field_text(step, field)
                if text is None:
                    continue
                for name in VARIABLE_REFERENCE_PATTERN.findall(text):
                    found.setdefault(name, []).append(
                        ValueUsage(
                            test_id=test.id,
                            step_id=step.id,
                            step_label=step.label,
                            field=field,
                        )
                    )
    return found


def collect_required_values(tests: list[Test]) -> list[RequiredValue]:
    """받는 사람이 채워야 할 것의 목록 (FR-040).

    담는 기준이 두 가지로 갈린다.

    - **민감 변수는 전부** 담는다. 정의에 값을 가질 수 없으므로(`_no_plaintext_secret`)
      언제나 비어 있고, 받는 쪽은 언제나 채워야 한다.
    - **비민감 변수는 값이 빈 것만** 담는다. 값이 있으면 채울 것이 없다.

    쓰이는 자리가 하나도 없는 변수는 담지 않는다 — 선언만 남고 참조가 사라진 경우이며,
    채워도 아무 데도 쓰이지 않는다. 그런 항목을 목록에 올리면 사용자가 「이건 왜 필요하지」
    에 답할 수 없다.

    이름 순으로 정렬해 돌려준다. 순서가 실행마다 달라지면 묶음 파일이 매번 다르게 나오고,
    두 묶음을 비교하는 일이 무의미해진다.
    """
    usages = _usages_by_name(tests)
    out: list[RequiredValue] = []
    seen: set[str] = set()

    for test in tests:
        for var in test.variables:
            if var.name in seen:
                continue
            if not var.sensitive and var.value:
                continue
            places = usages.get(var.name)
            if not places:
                continue
            seen.add(var.name)
            out.append(
                RequiredValue(
                    name=var.name,
                    sensitive=var.sensitive,
                    declared=True,
                    usages=places,
                )
            )

    return sorted(out, key=lambda v: v.name)
