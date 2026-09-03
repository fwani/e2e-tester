"""후보 표시 상태 파생. FR-019·FR-019a (T137).

**표시 상태를 저장하지 않는다** (data-model §6). 저장된 것은 후보별 검증 상태 4종뿐이고,
`사용 중`/`대체 N`/`최후` 같은 표기는 그 상태와 우선순위에서 **파생**된다. 저장하면 후보를
다시 수집했을 때(FR-020 다시 집기) 표기가 옛것을 가리킨다.

`strategy.py` 에서 분리한 이유는 역할이 다르기 때문이다. `strategy` 는 **실행이 어느 후보를
쓸지** 정하는 단일 지점이고(원칙 IV), 이 모듈은 **사람에게 무엇을 보여줄지** 정한다.
실행에는 쓰이지 않으므로 여기가 바뀌어도 재실행 결과가 달라지지 않는다.

화면(`LocatorPriorityTable.tsx`)에도 같은 규칙의 사본이 있다. 두 곳의 판정이 갈리지
않도록 같은 사례를 양쪽 단위 테스트가 각각 고정한다.
"""

from __future__ import annotations

from enum import StrEnum

from itb.domain.locator import CandidateStatus, TargetLocator
from itb.locator.strategy import PRIORITY, StrategyKind


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
