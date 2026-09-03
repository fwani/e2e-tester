"""후보 수집과 기록 시점 검증. 헌법 원칙 IV (FR-017·FR-019b).

주입된 JS 가 보낸 원시 후보를 `TargetLocator` 로 만들고, **그 후보가 방금 조작한 그 요소를
실제로 가리키는지 즉시 확인**해 상태를 부여한다.

기록 시점 검증이 이 설계에서 가장 값어치가 큰 결정이다. 검증이 없으면 `StepInspector` 의
`사용 중`/`대체 N` 표시가 추측이 되고, SC-008 을 나중에 실행이 깨져서야 알게 된다.
검증하면 **기록 시점에** 측정할 수 있다.

실측(research R4)에서 `text`·`css` 후보가 각각 2·3개 요소를 매칭하는 경우가 나왔다.
그래서 상태에 `ambiguous` 가 있다 — 이를 확보된 후보로 세면 SC-008 이 부풀려진다.
"""

from __future__ import annotations

from typing import Any, Protocol

from itb.domain.locator import Candidate, CandidateStatus, StableAttr, TargetLocator
from itb.locator.strategy import PRIORITY, LocatorStrategy, StrategyKind

STABLE_ATTR_NAMES: tuple[str, ...] = (
    "name",
    "data-name",
    "data-id",
    "data-qa",
    "data-role",
    "aria-label",
)
"""안정적 속성 후보로 볼 속성 이름. 자동 생성 클래스나 난수 id 는 제외한다."""

MAX_TEXT_LENGTH = 200
"""너무 긴 텍스트는 후보로 쓸 수 없다 — 화면 문구가 조금만 바뀌어도 깨진다."""


class RawCandidates(Protocol):
    """주입된 JS 가 보내는 원시 후보 페이로드의 모양."""

    def get(self, key: str, default: Any = None) -> Any: ...


def _clean(value: Any) -> str | None:
    """후보 값으로 쓸 수 있게 다듬는다. 쓸 수 없으면 None."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > MAX_TEXT_LENGTH:
        return None
    return text


def build_unverified(raw: dict[str, Any], test_id_attribute: str = "data-testid") -> TargetLocator:
    """원시 후보를 검증 전 `TargetLocator` 로 만든다.

    이 단계에서는 모든 후보가 `UNVERIFIED` 다. `verify` 가 실제 상태를 채운다.
    CSS 는 항상 있어야 한다 — 없으면 `TargetLocator` 불변식이 거절한다.
    """
    attrs: dict[str, Any] = raw.get("attributes") or {}

    test_id_value = _clean(attrs.get(test_id_attribute))
    label_value = _clean(raw.get("label"))
    text_value = _clean(raw.get("text"))
    css_value = _clean(raw.get("css"))
    role = _clean(raw.get("role"))
    name = _clean(raw.get("accessibleName"))

    stable: StableAttr | None = None
    for attr_name in STABLE_ATTR_NAMES:
        if attr_name == test_id_attribute:
            continue
        attr_value = _clean(attrs.get(attr_name))
        if attr_value is not None:
            stable = StableAttr(
                name=attr_name, value=attr_value, status=CandidateStatus.UNVERIFIED
            )
            break

    def cand(value: str | None) -> Candidate | None:
        if value is None:
            return None
        return Candidate(value=value, status=CandidateStatus.UNVERIFIED)

    return TargetLocator(
        tag=_clean(raw.get("tag")),
        test_id=cand(test_id_value),
        role=role,
        accessible_name=name,
        role_status=(
            CandidateStatus.UNVERIFIED if role is not None and name is not None else None
        ),
        label=cand(label_value),
        text=cand(text_value),
        stable_attr=stable,
        css=cand(css_value),
    )


def classify(match_count: int, same_element: bool) -> CandidateStatus:
    """검증 결과를 상태로 바꾼다.

    | 조건 | 상태 |
    |------|------|
    | 매칭 0개 | `NOT_COLLECTED` — 값은 있으나 지금 화면에서 찾지 못한다 |
    | 매칭 2개 이상 | `AMBIGUOUS` — 어느 것을 잡을지 결정할 수 없다 (FR-019b) |
    | 매칭 1개, 동일 요소 | `VERIFIED` — 사용 가능한 유일한 상태 |
    | 매칭 1개, 다른 요소 | `UNVERIFIED` |
    """
    if match_count == 0:
        return CandidateStatus.NOT_COLLECTED
    if match_count > 1:
        return CandidateStatus.AMBIGUOUS
    return CandidateStatus.VERIFIED if same_element else CandidateStatus.UNVERIFIED


def apply_statuses(
    target: TargetLocator, statuses: dict[StrategyKind, CandidateStatus]
) -> TargetLocator:
    """검증 결과를 반영한 새 `TargetLocator` 를 만든다. 원본을 바꾸지 않는다."""
    data = target.model_dump()

    def put(key: str, kind: StrategyKind) -> None:
        entry = data.get(key)
        if isinstance(entry, dict) and kind in statuses:
            entry["status"] = statuses[kind].value

    put("test_id", StrategyKind.TEST_ID)
    put("label", StrategyKind.LABEL)
    put("text", StrategyKind.TEXT)
    put("stable_attr", StrategyKind.STABLE_ATTR)
    put("css", StrategyKind.CSS)
    if data.get("role_status") is not None and StrategyKind.ROLE in statuses:
        data["role_status"] = statuses[StrategyKind.ROLE].value

    return TargetLocator.model_validate(data)


def candidate_strategies(target: TargetLocator) -> list[tuple[StrategyKind, LocatorStrategy]]:
    """검증 대상 전략 목록.

    `ordered_strategies` 는 확보된 후보만 돌려주므로 검증 단계에서는 쓸 수 없다 —
    아직 아무것도 `VERIFIED` 가 아니기 때문이다. 여기서는 **값이 있는 모든 후보**를
    임시로 `VERIFIED` 로 간주해 전략을 만든다.
    """
    probe = apply_statuses(target, dict.fromkeys(PRIORITY, CandidateStatus.VERIFIED))
    from itb.locator.strategy import ordered_strategies

    return [(s.kind, s) for s in ordered_strategies(probe)]


def summarize_verification(target: TargetLocator) -> dict[str, object]:
    """SC-008 측정용 요약. 기록 시점에 후보 품질을 알 수 있다."""
    usable = target.usable_candidate_count()
    return {
        "usable_candidates": usable,
        "meets_sc008": usable >= 2,
        "statuses": {
            kind.value: _status_of(target, kind) for kind in PRIORITY
        },
    }


def _status_of(target: TargetLocator, kind: StrategyKind) -> str | None:
    match kind:
        case StrategyKind.TEST_ID:
            return target.test_id.status.value if target.test_id else None
        case StrategyKind.ROLE:
            return target.role_status.value if target.role_status else None
        case StrategyKind.LABEL:
            return target.label.status.value if target.label else None
        case StrategyKind.TEXT:
            return target.text.status.value if target.text else None
        case StrategyKind.STABLE_ATTR:
            return target.stable_attr.status.value if target.stable_attr else None
        case StrategyKind.CSS:
            return target.css.status.value if target.css else None
