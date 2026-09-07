"""Locator 우선순위 해석의 **단일 지점**. 헌법 원칙 IV.

이 모듈은 순수하다 — Playwright 도, FastAPI 도 임포트하지 않는다. 그래야 Runner 와
Generator 가 같은 판단을 공유할 수 있다 (FR-022). `.importlinter` 의
`locator-strategy-is-pure` 계약이 이를 강제한다.

    choose_strategy(target) -> LocatorStrategy      의도의 표현
           ├─ Runner    → Playwright Locator 로 변환   (itb.execution)
           └─ Generator → Playwright 코드 문자열로 변환 (itb.generator)

**실측 반영 (research R4)**: 이름·텍스트 매칭은 반드시 완전 일치여야 한다.
`get_by_role(name=...)` 의 기본은 부분 일치이며, 부분 일치를 허용하면 대체 후보가
조용히 다른 요소를 잡아 테스트가 잘못된 대상에 대해 통과할 수 있다 — 실패보다 나쁘다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from itb.domain.locator import CandidateStatus, TargetLocator


class StrategyKind(StrEnum):
    """후보 종류. 값이 곧 우선순위 이름이며 결과 화면 표기에 쓰인다."""

    TEST_ID = "test_id"
    ROLE = "role"
    LABEL = "label"
    TEXT = "text"
    STABLE_ATTR = "stable_attr"
    CSS = "css"


PRIORITY: tuple[StrategyKind, ...] = (
    StrategyKind.TEST_ID,
    StrategyKind.ROLE,
    StrategyKind.LABEL,
    StrategyKind.TEXT,
    StrategyKind.STABLE_ATTR,
    StrategyKind.CSS,
)
"""FR-018 의 우선순위. 이 순서가 제품 내 실행과 생성 코드 양쪽의 유일한 기준이다."""


# ─── 대기 정책 (004 FR-111·FR-116·FR-118) ──────────────────────────────────
#
# **여기 두는 이유**: 이 모듈이 이미 우선순위 판단의 유일한 지점이고 순수하다. 대기 정책도
# Runner 와 Generator 가 같은 값을 봐야 하므로 같은 자리에 둔다 (헌법 원칙 IV 후단).
#
# **정책 요약** — 구현은 `itb.execution.locator_runtime.resolve()` 에 있다.
#
# 1. 후보 전체를 대기 없이 한 번 확인한다. `count()==1` 인 것이 있으면 우선순위 순으로
#    채택하고 즉시 반환한다. 요소가 이미 있는 정상 경로는 여기서 끝난다 (FR-113).
# 2. 아무도 맞지 않으면 `POLL_INTERVAL_MS` 주기로 **후보 전체를 다시 확인한다.**
#    최상위 후보 하나에만 예산을 거는 것은 004 이전의 결함이었다 — 하위 후보로만 늦게
#    나타나는 요소가 한 번도 다시 확인되지 않았다 (research R1: 5004ms 실패).
# 3. 채택은 **보이는 것을 먼저** 본다. 로딩 중 숨겨진 자리표시자를 잡지 않기 위해서다.
#    다만 보이지 않는 것이 정상인 대상(`hidden` 검증, 화면 밖 입력란)이 있으므로,
#    예산이 거의 끝나면 보이지 않는 매칭도 채택한다 (FR-119).
# 4. 여러 개를 매칭하는 후보는 **채택하지 않는다.** 자동으로 첫 번째를 고르면 잘못된
#    요소에 대해 통과할 수 있고, 그것은 실패보다 나쁘다 (research R2).
#
# **생성기와의 차이 (알려진 한계)**: 내보낸 Playwright 코드는 폴링하지 않는다. 생성기는
# `ordered_strategies()[0]` 하나로 코드를 만들기 때문이다. 예산(`step.timeout_ms`)은
# 양쪽이 공유하므로 지연 로딩 화면에서 같은 시간을 기다린다. 다후보 대기의 표준
# Playwright 표현은 내보내기 구현 시점의 과제다 (004 plan Complexity Tracking).

POLL_INTERVAL_MS = 100
"""요소가 나타났는지 다시 확인하는 주기 (research R4 실측).

**100ms 인 근거**: 오버슈트가 89ms 로 측정됐다 — 요소가 나타난 뒤 다음 동작까지의 추가
지연이 사람이 느낄 수준을 넘지 않는다 (FR-116). 후보 5종을 한 라운드 확인하는 비용이
14.8ms 이므로 대기 중 점유율은 15% 수준이고, 정상 경로는 1라운드에서 반환하므로 이
비용이 발생하지 않는다.

지수 백오프를 쓰지 않은 이유: 최대 주기가 400ms 가 되면 오버슈트가 FR-116 을 위협한다.
라운드당 15ms 를 아끼자고 치를 대가가 아니다.
"""


@dataclass(frozen=True, slots=True)
class LocatorStrategy:
    """요소를 찾는 **의도**의 표현. 실행 가능한 객체가 아니다."""

    kind: StrategyKind
    args: dict[str, str]
    exact: bool = True
    """이름·텍스트 매칭을 완전 일치로 한다 (FR-018a, research R4 실측)."""

    def describe(self) -> str:
        """사람이 읽는 표현. 실패 상세의 "시도한 LOCATOR" 표기에 쓴다."""
        match self.kind:
            case StrategyKind.TEST_ID:
                return f"testId={self.args['test_id']}"
            case StrategyKind.ROLE:
                return f"role={self.args['role']} name={self.args['name']!r}"
            case StrategyKind.LABEL:
                return f"label={self.args['label']!r}"
            case StrategyKind.TEXT:
                return f"text={self.args['text']!r}"
            case StrategyKind.STABLE_ATTR:
                return f'[{self.args["name"]}="{self.args["value"]}"]'
            case StrategyKind.CSS:
                return f"css={self.args['css']}"


def _strategy_for(kind: StrategyKind, target: TargetLocator) -> LocatorStrategy | None:
    """후보 하나를 전략으로 바꾼다. 확보되지 않은 후보면 None.

    `AMBIGUOUS` 후보는 건너뛴다 — 실행 시 어느 요소를 잡을지 결정할 수 없다 (FR-019b).
    """
    match kind:
        case StrategyKind.TEST_ID:
            c = target.test_id
            if c is not None and c.usable:
                return LocatorStrategy(kind, {"test_id": c.value})
        case StrategyKind.ROLE:
            if (
                target.role is not None
                and target.accessible_name is not None
                and target.role_status is CandidateStatus.VERIFIED
            ):
                return LocatorStrategy(
                    kind, {"role": target.role, "name": target.accessible_name}
                )
        case StrategyKind.LABEL:
            c = target.label
            if c is not None and c.usable:
                return LocatorStrategy(kind, {"label": c.value})
        case StrategyKind.TEXT:
            c = target.text
            if c is not None and c.usable:
                return LocatorStrategy(kind, {"text": c.value})
        case StrategyKind.STABLE_ATTR:
            sa = target.stable_attr
            if sa is not None and sa.usable:
                return LocatorStrategy(kind, {"name": sa.name, "value": sa.value})
        case StrategyKind.CSS:
            c = target.css
            if c is not None and c.usable:
                return LocatorStrategy(kind, {"css": c.value})
    return None


def ordered_strategies(target: TargetLocator) -> list[LocatorStrategy]:
    """확보된 후보를 우선순위 순으로 모두 돌려준다.

    Runner 는 이 목록을 순회하고, Generator 는 첫 항목으로 코드를 만든다.
    실패 상세의 "시도한 LOCATOR (우선순위 순)" 도 이 목록이 근거다 (FR-021).
    """
    out: list[LocatorStrategy] = []
    for kind in PRIORITY:
        s = _strategy_for(kind, target)
        if s is not None:
            out.append(s)
    return out


def choose_strategy(target: TargetLocator) -> LocatorStrategy | None:
    """우선순위가 가장 높은 확보된 후보. 없으면 None.

    확보된 후보가 하나도 없다는 것은 모든 후보가 미수집·모호·검증 실패라는 뜻이다.
    호출자는 이 경우를 실패로 다뤄야 한다 — 조용히 CSS 로 떨어지지 않는다.
    """
    strategies = ordered_strategies(target)
    return strategies[0] if strategies else None
