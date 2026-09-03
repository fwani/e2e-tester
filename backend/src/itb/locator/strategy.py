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


class DisplayState(StrEnum):
    """Step 상세 화면 표기. FR-019a 의 파생 규칙 결과다. **저장하지 않는다.**"""

    IN_USE = "사용 중"
    FALLBACK = "대체"
    LAST_RESORT = "최후"
    AMBIGUOUS = "모호(사용 불가)"
    UNVERIFIED = "검증 실패"
    NOT_COLLECTED = "수집되지 않음"


def _raw_status(kind: StrategyKind, target: TargetLocator) -> CandidateStatus | None:
    """후보의 저장 상태. 값 자체가 없으면 None."""
    match kind:
        case StrategyKind.TEST_ID:
            return target.test_id.status if target.test_id else None
        case StrategyKind.ROLE:
            if target.role is None or target.accessible_name is None:
                return None
            return target.role_status or CandidateStatus.NOT_COLLECTED
        case StrategyKind.LABEL:
            return target.label.status if target.label else None
        case StrategyKind.TEXT:
            return target.text.status if target.text else None
        case StrategyKind.STABLE_ATTR:
            return target.stable_attr.status if target.stable_attr else None
        case StrategyKind.CSS:
            return target.css.status if target.css else None


def display_states(target: TargetLocator) -> dict[StrategyKind, str]:
    """후보별 표시 상태를 우선순위 순으로 파생한다 (FR-019a).

    표시 상태는 저장 데이터에서 계산되며 별도로 저장하지 않는다.
    """
    usable_seen = 0
    out: dict[StrategyKind, str] = {}
    for kind in PRIORITY:
        status = _raw_status(kind, target)
        if status is None or status is CandidateStatus.NOT_COLLECTED:
            out[kind] = DisplayState.NOT_COLLECTED
            continue
        if status is CandidateStatus.AMBIGUOUS:
            out[kind] = DisplayState.AMBIGUOUS
            continue
        if status is CandidateStatus.UNVERIFIED:
            out[kind] = DisplayState.UNVERIFIED
            continue
        # verified
        if usable_seen == 0:
            out[kind] = DisplayState.IN_USE
        elif kind is StrategyKind.CSS:
            out[kind] = DisplayState.LAST_RESORT
        else:
            out[kind] = f"{DisplayState.FALLBACK} {usable_seen}"
        usable_seen += 1
    return out
