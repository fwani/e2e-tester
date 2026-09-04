"""민감 값 포착. FR-082·FR-082a·FR-083·FR-089b (T058 에서 옮겨 온 단일 지점).

**평문을 돌려주지 않는다.** 이 모듈을 지난 값은 `{{변수명}}` 참조뿐이고, 실제 값은 공개키로
봉인되어 비밀 파일에 있다. 그래서 이벤트·API 응답·정의 파일에 평문이 도달할 경로가 없다.

리코더(사람 녹화)와 AI 도구(자연어 작성)가 **같은 코드**를 지나야 한다. 갈라지면 한쪽
경로에서만 평문이 새고, 그 사실은 그 경로를 지나는 테스트가 없을 때 드러나지 않는다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from nacl.public import PublicKey

from itb.domain.test_case import (
    fallback_variable_name,
    make_variable_name,
    variable_reference,
)
from itb.secrets.store import SecretStore


@dataclass(slots=True)
class SensitiveCapture:
    """민감 값 하나를 변수로 옮긴 기록."""

    variable_name: str
    sealed: bool
    """공개키로 봉인해 비밀 파일에 저장했는가. 공개키가 없으면 False."""


@dataclass(slots=True)
class SensitiveCapturer:
    """한 세션에서 포착한 민감 값들.

    같은 필드가 이벤트를 여러 번 내도 변수는 하나여야 한다. 없으면 한 번의 입력이
    `SECRET_VALUE_1`, `SECRET_VALUE_2` … 로 늘어나 정의와 비밀 파일이 어긋난다.
    """

    store: SecretStore | None = None
    public_key: PublicKey | None = None
    key_source: Callable[[], PublicKey | None] | None = None
    """봉인하는 **그 순간의** 공개키를 구한다. 주면 `public_key` 스냅숏보다 우선한다.

    세션 시작 시점에 키를 붙잡아 두면, 그 사이 키 관리 화면에서 키를 만들거나 바꿔도
    그 세션은 없어진 키로 계속 봉인하려 든다. 사용자에게는 "키를 만들었는데도 민감
    값이 저장되지 않는다" 로 보인다.
    """

    captures: list[SensitiveCapture] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _names: dict[str, str] = field(default_factory=dict)
    """포착 키 → 변수 이름. 키는 호출자가 정한다 (보통 탭+CSS)."""

    def to_reference(
        self, raw_value: str, cache_key: str, name_basis: tuple[str | None, ...] = ()
    ) -> str:
        """민감 값을 변수 참조로 바꾸고 공개키로 봉인한다.

        공개키가 없으면 **경고를 남기고 참조만 만든다.** 값을 잃는 것이 맞다 — 평문을
        정의에 남기는 것은 FR-082 위반이고, 사용자는 값을 다시 입력하거나 환경 변수로
        공급할 수 있다 (FR-089g).
        """
        variable = self._names.get(cache_key)
        if variable is None:
            variable = self._allocate_name(name_basis)
            self._names[cache_key] = variable

        sealed = False
        public = self._public()
        if self.store is None or public is None:
            self._warn(
                f"민감 값을 보관할 공개키가 없어 {variable} 의 값을 저장하지 못했습니다. "
                "키를 만든 뒤 값을 다시 입력하거나 환경 변수로 공급하세요."
            )
        else:
            try:
                self.store.put(variable, raw_value, public)
                sealed = True
            except Exception as exc:  # noqa: BLE001 - 사유를 그대로 경고로 옮긴다
                # 예전에는 사유를 버리고 "공개키가 없다" 로만 알렸다. 지문 불일치처럼
                # 조치가 전혀 다른 실패가 같은 문장으로 보여 원인을 찾을 수 없었다.
                self._warn(f"민감 값 {variable} 을 보관하지 못했습니다: {exc}")

        existing = next(
            (c for c in self.captures if c.variable_name == variable), None
        )
        if existing is None:
            self.captures.append(SensitiveCapture(variable_name=variable, sealed=sealed))
        elif sealed:
            existing.sealed = True
        return variable_reference(variable)

    def _public(self) -> PublicKey | None:
        return self.key_source() if self.key_source is not None else self.public_key

    def _allocate_name(self, basis: tuple[str | None, ...]) -> str:
        for candidate in basis:
            name = make_variable_name(candidate)
            if name is not None and name not in self._names.values():
                return name
        return fallback_variable_name(len(self.captures) + 1)

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def variable_names(self) -> set[str]:
        return {c.variable_name for c in self.captures}
