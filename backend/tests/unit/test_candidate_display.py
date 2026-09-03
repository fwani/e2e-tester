"""후보 표시 상태 파생 규칙. FR-019a (T134).

**표시 상태는 저장되지 않는다.** 저장된 것은 후보별 검증 상태 4종
(`verified`/`ambiguous`/`unverified`/`not_collected`)뿐이고, 화면 표기는 그 상태와
우선순위에서 파생된다 (data-model §6).

이 테스트가 고정하는 것은 파생 규칙 자체다. 규칙이 바뀌면 `StepInspector` 의 표기가
바뀌므로, 바뀌었다는 사실이 여기서 드러나야 한다.
"""

from __future__ import annotations

import pytest

from itb.domain.locator import Candidate, CandidateStatus, StableAttr, TargetLocator
from itb.locator.display import DisplayState, display_states
from itb.locator.strategy import PRIORITY, StrategyKind


def cand(value: str, status: CandidateStatus = CandidateStatus.VERIFIED) -> Candidate:
    return Candidate(value=value, status=status)


def test_display_state_is_not_a_stored_field() -> None:
    """**표시 상태를 저장하지 않는다.**

    `TargetLocator` 에 표시용 필드가 생기면 후보를 다시 수집했을 때 표기가 옛것을 가리킨다.
    스키마에 그런 필드가 없다는 것을 고정한다.
    """
    fields = set(TargetLocator.model_fields)
    for forbidden in ("display", "display_state", "display_states", "in_use"):
        assert forbidden not in fields, f"표시 상태가 저장 스키마에 들어갔다: {forbidden}"


def test_first_verified_candidate_is_in_use() -> None:
    """우선순위가 가장 높은 `verified` 후보가 `사용 중` 이다 (FR-018·FR-019a)."""
    target = TargetLocator(
        test_id=cand("save"),
        label=cand("저장"),
        css=cand("button.save"),
    )
    states = display_states(target)
    assert states[StrategyKind.TEST_ID] == DisplayState.IN_USE
    assert states[StrategyKind.LABEL] == f"{DisplayState.FALLBACK} 1"
    assert states[StrategyKind.CSS] == DisplayState.LAST_RESORT


def test_css_is_marked_last_resort_even_when_it_is_the_only_candidate() -> None:
    """CSS 만 있으면 그것이 `사용 중` 이다.

    "최후" 는 **다른 후보가 있을 때의 순위 표기**다. 유일한 후보를 최후로 적으면 사용자는
    쓰이지 않는다고 읽는다.
    """
    states = display_states(TargetLocator(css=cand(".only")))
    assert states[StrategyKind.CSS] == DisplayState.IN_USE


def test_ambiguous_is_distinguished_from_not_collected() -> None:
    """FR-019b — `모호` 와 `수집되지 않음` 은 다르다.

    모호한 후보는 **값이 있다.** 수집되지 않은 것처럼 보이면 사용자는 그 값을 고칠 수
    있다는 사실을 모른다.
    """
    target = TargetLocator(
        text=cand("삭제", CandidateStatus.AMBIGUOUS),
        css=cand("button.delete"),
    )
    states = display_states(target)
    assert states[StrategyKind.TEXT] == DisplayState.AMBIGUOUS
    assert states[StrategyKind.LABEL] == DisplayState.NOT_COLLECTED
    # 모호한 후보는 사용 가능 후보로 세지 않는다 — CSS 가 `사용 중` 이 된다.
    assert states[StrategyKind.CSS] == DisplayState.IN_USE


def test_unverified_is_distinguished_too() -> None:
    """`검증 실패` 는 "찾긴 했는데 다른 요소" 다. 값이 틀렸다는 신호다."""
    target = TargetLocator(
        test_id=cand("stale", CandidateStatus.UNVERIFIED),
        css=cand(".x"),
    )
    states = display_states(target)
    assert states[StrategyKind.TEST_ID] == DisplayState.UNVERIFIED
    assert states[StrategyKind.CSS] == DisplayState.IN_USE


def test_role_pair_requires_both_role_and_name() -> None:
    """role 후보는 role 과 접근 이름이 **짝**일 때만 성립한다.

    한쪽만 있으면 `get_by_role` 을 만들 수 없으므로 수집되지 않은 것과 같다.
    """
    only_role = TargetLocator(role="button", css=cand(".x"))
    assert display_states(only_role)[StrategyKind.ROLE] == DisplayState.NOT_COLLECTED

    paired = TargetLocator(
        role="button",
        accessible_name="저장",
        role_status=CandidateStatus.VERIFIED,
        css=cand(".x"),
    )
    assert display_states(paired)[StrategyKind.ROLE] == DisplayState.IN_USE


def test_stable_attr_is_reported_like_other_candidates() -> None:
    target = TargetLocator(
        stable_attr=StableAttr(
            name="data-qa", value="save", status=CandidateStatus.VERIFIED
        ),
        css=cand(".x"),
    )
    states = display_states(target)
    assert states[StrategyKind.STABLE_ATTR] == DisplayState.IN_USE
    assert states[StrategyKind.CSS] == DisplayState.LAST_RESORT


def test_every_priority_kind_gets_a_state() -> None:
    """6단 전부에 표기가 있다. 빠진 칸이 있으면 화면에 구멍이 난다."""
    states = display_states(TargetLocator(css=cand(".x")))
    assert set(states) == set(PRIORITY)
    assert len(PRIORITY) == 6


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (CandidateStatus.VERIFIED, DisplayState.IN_USE),
        (CandidateStatus.AMBIGUOUS, DisplayState.AMBIGUOUS),
        (CandidateStatus.UNVERIFIED, DisplayState.UNVERIFIED),
        (CandidateStatus.NOT_COLLECTED, DisplayState.NOT_COLLECTED),
    ],
)
def test_each_stored_status_maps_to_one_display_state(
    status: CandidateStatus, expected: str
) -> None:
    """저장 상태 4종이 각각 어떤 표기가 되는지 전수로 고정한다."""
    target = TargetLocator(test_id=cand("x", status), css=cand(".y"))
    assert display_states(target)[StrategyKind.TEST_ID] == expected
