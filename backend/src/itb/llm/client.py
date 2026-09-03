"""언어모델 경계. **제품 전체에서 `anthropic` SDK 를 아는 유일한 모듈이다** (research R5).

이 파일이 존재하는 이유는 헌법 원칙 II(NON-NEGOTIABLE)다. SDK 접점을 한 곳에 모으고
`itb.execution` 이 이 패키지를 임포트할 수 없게 `.importlinter` 계약으로 막는다 —
저장된 테스트의 실행 경로에서 언어모델 호출이 **코드 구조상 도달 불가능**해야 한다.

**키를 코드에 넣지 않는다** (FR-084). 인자 없는 생성자를 쓰면 SDK 가
`ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → `ant auth login` 프로필 순으로 해석한다.

**Opus 5 에서 쓰지 않는 것** (research R5 실측): `budget_tokens`·`temperature`·`top_p`·
`top_k`·어시스턴트 프리필. 모두 400 을 낸다. 사고 깊이는 `thinking` 파라미터가 아니라
`output_config={"effort": ...}` 로 조절한다 — Opus 5 는 adaptive thinking 이 기본이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - 타입 검사 전용
    from anthropic import AsyncAnthropic

MODEL = "claude-opus-5"
"""브라우저 에이전트는 화면을 보고 다음 동작을 정하는 장기 도구 사용 작업이고,
SC-002(자연어 변환 성공률 70% 이상)가 직접 모델 성능에 걸린다."""

EFFORT = "xhigh"
"""장기 도구 사용 작업이므로 기본을 높게 둔다. 비용을 낮출 때는 모델을 내리기 전에
이 값을 먼저 조정한다 (research R5)."""

MAX_TOKENS = 8192

FALLBACK_BETA = "server-side-fallback-2026-07-01"
"""거부(`stop_reason: "refusal"`) 시 서버측 폴백. `fallbacks="default"` 와 함께 쓴다."""


class LlmUnavailableError(Exception):
    """언어모델을 쓸 수 없다.

    자격 증명이 없거나 SDK 를 만들 수 없는 경우다. **그때까지 만든 Step 은 보존한다**
    (FR-067) — 호출자가 이 예외를 받아 `ai_error` 를 발행하고 세션을 유지한다.
    """


class RefusalError(Exception):
    """모델이 거부했다 (`stop_reason: "refusal"`).

    `content` 를 읽기 전에 `stop_reason` 을 확인해야 한다 (research R5). 거부 응답의
    `content` 를 도구 호출로 해석하려 들면 무엇이 일어났는지 알 수 없는 실패가 된다.
    """


@dataclass(slots=True)
class LlmConfig:
    """호출 파라미터. 테스트가 갈아 끼울 수 있게 값으로 둔다."""

    model: str = MODEL
    max_tokens: int = MAX_TOKENS
    effort: str = EFFORT
    betas: list[str] = field(default_factory=lambda: [FALLBACK_BETA])
    fallbacks: str = "default"

    def request_kwargs(self) -> dict[str, Any]:
        """`tool_runner` 에 그대로 넘길 인자.

        `output_config`·`betas`·`fallbacks` 를 **직접 받는다** — `extra_body` 로 우회할
        필요가 없다 (T008 실측).
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "output_config": {"effort": self.effort},
            "betas": list(self.betas),
            "fallbacks": self.fallbacks,
        }


def create_client() -> AsyncAnthropic:
    """`AsyncAnthropic` 을 만든다. **인자를 주지 않는다** (FR-084).

    SDK 가 없거나 자격 증명을 해석하지 못하면 `LlmUnavailableError` 로 바꾼다 — 원래
    예외를 그대로 올리면 호출자가 SDK 예외 타입을 알아야 하고, 그러면 경계가 새어 나간다.
    """
    try:
        from anthropic import AsyncAnthropic  # noqa: PLC0415 - 경계를 이 함수 안에 둔다
    except ImportError as exc:  # pragma: no cover - 의존성은 설치되어 있다
        msg = "anthropic SDK 를 불러올 수 없습니다."
        raise LlmUnavailableError(msg) from exc

    try:
        return AsyncAnthropic()
    except Exception as exc:  # noqa: BLE001 - 자격 증명 오류 종류가 SDK 내부 사정이다
        msg = (
            "언어모델 자격 증명을 찾을 수 없습니다. "
            "`ANTHROPIC_API_KEY` 를 환경 변수로 주거나 `ant auth login` 으로 로그인하세요. "
            "그때까지 기록된 Step 은 보존됩니다."
        )
        raise LlmUnavailableError(msg) from exc


def check_stop_reason(stop_reason: str | None) -> None:
    """`content` 를 읽기 전에 확인한다 (research R5)."""
    if stop_reason == "refusal":
        msg = (
            "언어모델이 이 지시를 거부했습니다. 지시문을 바꿔 다시 시도하거나 "
            "직접 녹화로 만드세요. 그때까지 기록된 Step 은 보존됩니다."
        )
        raise RefusalError(msg)
