"""T028 — Locator 우선순위 해석 단위 테스트 (헌법 원칙 IV, FR-018·FR-019a·FR-019b)."""

from __future__ import annotations

import pytest

from itb.domain.locator import Candidate, CandidateStatus, StableAttr, TargetLocator
from itb.locator.strategy import (
    PRIORITY,
    DisplayState,
    StrategyKind,
    choose_strategy,
    display_states,
    ordered_strategies,
)

V = CandidateStatus.VERIFIED
AMB = CandidateStatus.AMBIGUOUS
UNV = CandidateStatus.UNVERIFIED
NC = CandidateStatus.NOT_COLLECTED


def cand(value: str, status: CandidateStatus = V) -> Candidate:
    return Candidate(value=value, status=status)


def full_target(**overrides: object) -> TargetLocator:
    """모든 후보가 확보된 요소."""
    base: dict[str, object] = {
        "tag": "button",
        "test_id": cand("create-project"),
        "role": "button",
        "accessible_name": "프로젝트 생성",
        "role_status": V,
        "label": cand("프로젝트명"),
        "text": cand("프로젝트 생성"),
        "stable_attr": StableAttr(name="data-role", value="create", status=V),
        "css": cand(".card button"),
    }
    base.update(overrides)
    return TargetLocator(**base)  # type: ignore[arg-type]


# ─── 우선순위 (FR-018) ──────────────────────────────────────────────────────


def test_priority_order_matches_fr018() -> None:
    assert PRIORITY == (
        StrategyKind.TEST_ID,
        StrategyKind.ROLE,
        StrategyKind.LABEL,
        StrategyKind.TEXT,
        StrategyKind.STABLE_ATTR,
        StrategyKind.CSS,
    )


def test_test_id_wins_when_available() -> None:
    s = choose_strategy(full_target())
    assert s is not None
    assert s.kind is StrategyKind.TEST_ID


@pytest.mark.parametrize(
    ("drop", "expected"),
    [
        (["test_id"], StrategyKind.ROLE),
        (["test_id", "role"], StrategyKind.LABEL),
        (["test_id", "role", "label"], StrategyKind.TEXT),
        (["test_id", "role", "label", "text"], StrategyKind.STABLE_ATTR),
        (["test_id", "role", "label", "text", "stable_attr"], StrategyKind.CSS),
    ],
)
def test_falls_through_priority(drop: list[str], expected: StrategyKind) -> None:
    kw: dict[str, object] = {}
    for name in drop:
        if name == "role":
            kw["role"] = None
            kw["accessible_name"] = None
            kw["role_status"] = None
        else:
            kw[name] = None
    s = choose_strategy(full_target(**kw))
    assert s is not None
    assert s.kind is expected


def test_returns_none_when_no_usable_candidate() -> None:
    """모든 후보가 모호·검증 실패면 None. 조용히 CSS 로 떨어지지 않는다."""
    t = TargetLocator(
        test_id=cand("x", AMB),
        text=cand("저장", AMB),
        css=cand(".btn", UNV),
    )
    assert choose_strategy(t) is None
    assert ordered_strategies(t) == []


# ─── ambiguous 는 건너뛴다 (FR-019b) ────────────────────────────────────────


def test_ambiguous_candidate_is_skipped() -> None:
    """가장 높은 우선순위 후보가 모호하면 다음 후보로 넘어간다."""
    s = choose_strategy(full_target(test_id=cand("dup", AMB)))
    assert s is not None
    assert s.kind is StrategyKind.ROLE


def test_unverified_candidate_is_skipped() -> None:
    s = choose_strategy(full_target(test_id=cand("wrong", UNV)))
    assert s is not None
    assert s.kind is StrategyKind.ROLE


def test_ordered_strategies_excludes_unusable() -> None:
    t = full_target(text=cand("프로젝트 생성", AMB), label=cand("프로젝트명", NC))
    kinds = [s.kind for s in ordered_strategies(t)]
    assert StrategyKind.TEXT not in kinds
    assert StrategyKind.LABEL not in kinds
    assert kinds == [
        StrategyKind.TEST_ID,
        StrategyKind.ROLE,
        StrategyKind.STABLE_ATTR,
        StrategyKind.CSS,
    ]


# ─── exact=True (FR-018a, research R4 실측) ─────────────────────────────────


def test_all_strategies_are_exact() -> None:
    """부분 일치를 허용하면 대체 후보가 다른 요소를 잡는다 — 실패보다 나쁘다."""
    for s in ordered_strategies(full_target()):
        assert s.exact is True


# ─── role 후보는 role 과 name 이 모두 있어야 한다 ──────────────────────────


def test_role_without_name_is_not_usable() -> None:
    s = choose_strategy(full_target(test_id=None, accessible_name=None))
    assert s is not None
    assert s.kind is StrategyKind.LABEL


def test_role_without_status_is_not_usable() -> None:
    s = choose_strategy(full_target(test_id=None, role_status=None))
    assert s is not None
    assert s.kind is StrategyKind.LABEL


# ─── describe() — 실패 상세 표기 (FR-021) ──────────────────────────────────


def test_describe_covers_every_kind() -> None:
    described = {s.kind: s.describe() for s in ordered_strategies(full_target())}
    assert described[StrategyKind.TEST_ID] == "testId=create-project"
    assert "role=button" in described[StrategyKind.ROLE]
    assert described[StrategyKind.STABLE_ATTR] == '[data-role="create"]'
    assert described[StrategyKind.CSS] == "css=.card button"
    assert set(described) == set(PRIORITY)


# ─── 표시 상태 파생 (FR-019a) ──────────────────────────────────────────────


def test_display_states_full_target() -> None:
    st = display_states(full_target())
    assert st[StrategyKind.TEST_ID] == DisplayState.IN_USE
    assert st[StrategyKind.ROLE] == f"{DisplayState.FALLBACK} 1"
    assert st[StrategyKind.LABEL] == f"{DisplayState.FALLBACK} 2"
    assert st[StrategyKind.TEXT] == f"{DisplayState.FALLBACK} 3"
    assert st[StrategyKind.STABLE_ATTR] == f"{DisplayState.FALLBACK} 4"
    assert st[StrategyKind.CSS] == DisplayState.LAST_RESORT


def test_display_states_mixed() -> None:
    """디자인 StepInspector 의 실제 표기 조합을 재현한다."""
    t = TargetLocator(
        tag="button",
        test_id=cand("create-project"),
        role="button",
        accessible_name="프로젝트 생성",
        role_status=V,
        text=cand("프로젝트 생성"),
        css=cand(".project-header button:nth-child(2)"),
    )
    st = display_states(t)
    assert st[StrategyKind.TEST_ID] == DisplayState.IN_USE
    assert st[StrategyKind.ROLE] == f"{DisplayState.FALLBACK} 1"
    assert st[StrategyKind.LABEL] == DisplayState.NOT_COLLECTED
    assert st[StrategyKind.TEXT] == f"{DisplayState.FALLBACK} 2"
    assert st[StrategyKind.STABLE_ATTR] == DisplayState.NOT_COLLECTED
    assert st[StrategyKind.CSS] == DisplayState.LAST_RESORT


def test_display_states_distinguishes_ambiguous_from_not_collected() -> None:
    """모호와 미수집을 구분해야 사용자가 왜 안 쓰이는지 알 수 있다."""
    t = TargetLocator(text=cand("저장", AMB), css=cand(".btn"), label=None)
    st = display_states(t)
    assert st[StrategyKind.TEXT] == DisplayState.AMBIGUOUS
    assert st[StrategyKind.LABEL] == DisplayState.NOT_COLLECTED
    assert st[StrategyKind.CSS] == DisplayState.IN_USE


def test_display_states_marks_unverified() -> None:
    t = TargetLocator(test_id=cand("wrong", UNV), css=cand(".btn"))
    st = display_states(t)
    assert st[StrategyKind.TEST_ID] == DisplayState.UNVERIFIED


def test_display_states_covers_all_kinds() -> None:
    assert set(display_states(TargetLocator(css=cand(".x")))) == set(PRIORITY)


def test_css_only_target_shows_in_use_not_last_resort() -> None:
    """CSS 하나만 확보된 경우, 실제로 쓰이므로 `사용 중` 이다."""
    st = display_states(TargetLocator(css=cand(".only")))
    assert st[StrategyKind.CSS] == DisplayState.IN_USE
