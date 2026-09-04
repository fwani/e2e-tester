"""변수 값 해석. FR-015·FR-089f·FR-089g.

해석 순서 (data-model §7):

    1. 동일 이름 환경 변수가 있으면 → 그 값
    2. secrets.local.yaml 에 암호문이 있으면 → 비밀키로 복호화
    3. Variable.value 가 있으면 → 그 값 (민감하지 않은 변수)
    4. 없으면 → 해당 Step 실패, 사유 명시. **빈 값으로 진행하지 않는다.**

환경 변수를 1순위로 두면 비밀값을 장비에 보관하지 않는 운용이 가능해진다 (FR-089g).
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable

from nacl.public import PrivateKey

from itb.domain.test_case import Test
from itb.secrets.keys import KeyStoreError
from itb.secrets.store import SecretStore

VARIABLE_REF = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


class VariableResolutionError(Exception):
    """변수 값을 구할 수 없다. 사유를 그대로 사용자에게 보여준다 (FR-089f)."""


class VariableResolver:
    """한 실행 동안의 변수 값 해석기.

    비밀키는 **민감 변수를 실제로 요구할 때만** 필요하다. 민감 변수가 없는 테스트는
    비밀키 없이 실행된다. 그래서 조립부는 비밀키를 미리 열지 않고 `key_source` 만
    넘기고, 실제로 필요한 순간에 연다. 못 열면 그 사유를 그대로 보여준다.

    **키를 세션 시작 시점에 붙잡지 않는 것이 요점이다.** 붙잡아 두면 키 관리 화면에서
    키를 만들거나 바꿔도 열려 있던 세션은 계속 옛 상태로 실패한다.
    """

    def __init__(
        self,
        test: Test,
        store: SecretStore | None = None,
        private_key: PrivateKey | None = None,
        env: object = None,
        key_unavailable_reason: str | None = None,
        key_source: Callable[[], tuple[PrivateKey | None, str | None]] | None = None,
    ) -> None:
        self._test = test
        self._store = store
        self._private = private_key
        self._key_reason = key_unavailable_reason
        self._key_source = key_source
        self._env = os.environ if env is None else env
        self._declared = {v.name: v for v in test.variables}
        self._cache: dict[str, str] = {}

    def declare(self, name: str, sensitive: bool = True) -> None:
        """실행 중 새로 포착된 변수를 등록한다 (AI 작성 경로, FR-082a).

        AI 가 비밀번호 필드에 값을 넣으면 그 자리에서 변수가 생긴다. 저장 전이므로
        `Test.variables` 에는 아직 없고, 그 상태로 Step 을 실행하면 "정의되지 않은 변수"
        로 실패한다. 등록해 두면 봉인된 암호문에서 값을 찾는다.

        **평문을 받지 않는다.** 값은 이미 비밀 파일에 봉인돼 있고 이 객체는 이름만 안다.
        """
        from itb.domain.test_case import Variable

        self._declared[name] = Variable(name=name, value=None, sensitive=sensitive)

    def resolve(self, name: str) -> str:
        if name in self._cache:
            return self._cache[name]

        var = self._declared.get(name)
        if var is None:
            msg = f"정의되지 않은 변수를 참조합니다: {{{{{name}}}}}"
            raise VariableResolutionError(msg)

        # 1. 환경 변수 우선 (FR-089g) — 민감 여부와 무관하게 적용한다
        env_value = self._env.get(name)  # type: ignore[union-attr]
        if env_value is not None:
            self._cache[name] = env_value
            return env_value

        # 2. 민감 변수 → 암호문 복호화
        if var.sensitive:
            value = self._resolve_sensitive(name)
            self._cache[name] = value
            return value

        # 3. 정의 파일의 값
        if var.value is not None:
            self._cache[name] = var.value
            return var.value

        msg = (
            f"변수 {name} 의 값을 구할 수 없습니다. "
            f"환경 변수 {name} 을 설정하거나 정의 파일에 값을 넣으세요."
        )
        raise VariableResolutionError(msg)

    def _resolve_sensitive(self, name: str) -> str:
        if self._store is None or not self._store.has(name):
            msg = (
                f"민감 변수 {name} 의 값이 보관되어 있지 않습니다. "
                f"비밀 값을 입력하거나 환경 변수 {name} 을 설정하세요."
            )
            raise VariableResolutionError(msg)
        if self._private is None and self._key_source is not None:
            # 실행 중 한 번만 연다 — 한 번의 실행 도중 키가 바뀌는 것은 오히려 사고다.
            self._private, self._key_reason = self._key_source()

        if self._private is None:
            # 사유가 있으면 그것을 쓴다 — "없는 키"와 "암호구로 잠긴 키"는 조치가 다르다.
            reason = self._key_reason or "비밀키가 없습니다."
            msg = (
                f"민감 변수 {name} 을 복호화할 수 없습니다. {reason} "
                f"또는 환경 변수 {name} 으로 값을 공급하세요 (FR-089f)."
            )
            raise VariableResolutionError(msg)
        try:
            return self._store.get(name, self._private)
        except KeyStoreError as exc:
            raise VariableResolutionError(str(exc)) from exc

    def substitute(self, text: str) -> str:
        """문자열의 모든 ``{{변수명}}`` 을 치환한다."""

        def one(m: re.Match[str]) -> str:
            return self.resolve(m.group(1))

        return VARIABLE_REF.sub(one, text)

    def resolved_sensitive_values(self) -> list[str]:
        """지금까지 복호화된 민감 값 목록. **스크러버 구성에만 쓴다.**"""
        return [
            v
            for name, v in self._cache.items()
            if (var := self._declared.get(name)) is not None and var.sensitive
        ]
