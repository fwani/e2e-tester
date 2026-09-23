"""실행할 수 있는 상태인가 (기능 019 · FR-044 · research R10).

**값을 읽지 않는다. 있는지만 본다.** 판정하려고 복호화하면 잠긴 키에서 실패하고, 「잠겨
있다」와 「값이 없다」는 다른 사실이다 — 사용자가 할 일이 다르다.

**`VariableResolver` 와 같은 해석 순서를 따른다.** 환경 변수가 1순위이므로, 환경 변수에
값이 있으면 봉인 저장소가 비어 있어도 막지 않는다. 순서가 갈리면 화면은 「값이 필요합니다」
라고 하는데 실행은 성공하거나, 그 반대가 된다.

이 모듈이 `itb.secrets` 에 있는 이유는 **한 규칙을 두 곳이 봐야** 하기 때문이다 — 목록이
누르기 전에 보여 주는 상태(`GET /api/tests/{id}/readiness`)와 세션 생성 직전의 차단
(`POST /api/sessions`)이 다른 답을 주면, 사용자는 눌러도 되는 버튼을 눌러 막힌다.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from itb.domain.test_case import Test, undefined_variable_references
from itb.secrets.store import SecretStore


@dataclass(frozen=True, slots=True)
class Readiness:
    """저장된 테스트를 지금 실행할 수 있는가."""

    missing_secrets: list[str] = field(default_factory=list)
    """값이 없는 **민감** 변수. 비어 있지 않으면 실행이 막힌다 (FR-044)."""

    empty_variables: list[str] = field(default_factory=list)
    """값이 빈 **비민감** 변수. **막지 않는다** — 빈 문자열이 유효한 입력일 수 있고,
    이것은 제품이 이미 쓰는 판정이다 (`undefined_variable_references`).
    """

    key_available: bool = False
    """이 설치에 키가 있는가 (FR-045). 없으면 민감 값을 채울 수 없다."""

    @property
    def runnable(self) -> bool:
        return not self.missing_secrets


def assess(
    test: Test,
    store: SecretStore | None,
    *,
    key_available: bool,
    env: Mapping[str, str] | None = None,
) -> Readiness:
    """실행 준비 상태를 판정한다.

    민감 변수 하나가 「값이 있다」로 판정되는 조건은 둘 중 하나다.

    1. 같은 이름의 **환경 변수**가 있다 (해석 순서 1순위, FR-089g)
    2. 비밀 파일에 같은 이름의 **암호문**이 있다

    ``store`` 가 ``None`` 이면 비밀 파일이 없는 것으로 본다 — 열린 프로젝트가 없거나
    아직 아무 값도 봉인하지 않은 상태다.
    """
    environ = os.environ if env is None else env

    missing = [
        name
        for name in sorted(test.sensitive_variable_names())
        if environ.get(name) is None and not (store is not None and store.has(name))
    ]

    # 비민감·빈 값은 기존 판정을 그대로 쓴다 — 두 벌을 만들지 않는다.
    empty = [
        name
        for name in undefined_variable_references(test.steps, test.variables)
        if environ.get(name) is None
    ]

    return Readiness(
        missing_secrets=missing,
        empty_variables=empty,
        key_available=key_available,
    )
