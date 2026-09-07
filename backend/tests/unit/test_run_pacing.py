"""실행 속도 대응표. 004 FR-101·FR-102, SC-004.

**대응표가 한 곳에만 있는지**를 지키는 테스트다. 러너와 화면이 각자 숫자를 들고 있으면
화면이 "1.5초 쉽니다" 라고 말하는 동안 러너가 0.5초를 쉬는 상태가 만들어진다.
"""

from __future__ import annotations

import pytest

from itb.domain.run_pacing import (
    DEFAULT_PACING,
    MIN_PERCEPTIBLE_DELAY_MS,
    RunPacing,
    auto_pause,
    delay_ms,
    label,
)


def test_four_levels_exist() -> None:
    """FR-102 — 선택지는 최소 네 가지다."""
    assert len(list(RunPacing)) >= 4
    assert {p.value for p in RunPacing} >= {"fast", "normal", "slow", "step"}


@pytest.mark.parametrize(
    ("pacing", "expected_delay", "expected_auto_pause"),
    [
        (RunPacing.FAST, 0, False),
        (RunPacing.NORMAL, 500, False),
        (RunPacing.SLOW, 1500, False),
        (RunPacing.STEP, 0, True),
    ],
)
def test_delay_table(
    pacing: RunPacing, expected_delay: int, expected_auto_pause: bool
) -> None:
    assert delay_ms(pacing) == expected_delay
    assert auto_pause(pacing) is expected_auto_pause


def test_fast_is_the_pre_004_behaviour() -> None:
    """`빠름` 은 간격이 없다 — 004 이전과 같은 동작이어야 한다 (spec 엣지 케이스)."""
    assert delay_ms(RunPacing.FAST) == 0
    assert auto_pause(RunPacing.FAST) is False


def test_slow_is_perceptible() -> None:
    """SC-004 — `느림` 은 사람이 화면 변화를 확인할 수 있는 간격이어야 한다.

    이 단언이 `_DELAY_MS[SLOW]` 를 함부로 줄이는 변경을 막는다.
    """
    assert delay_ms(RunPacing.SLOW) >= MIN_PERCEPTIBLE_DELAY_MS


def test_only_step_auto_pauses() -> None:
    """자동 일시정지는 `한 스텝씩` 하나뿐이다.

    다른 속도가 일시정지에 들어가면 사용자는 멈춘 이유를 알 수 없다.
    """
    pausing = [p for p in RunPacing if auto_pause(p)]
    assert pausing == [RunPacing.STEP]


def test_default_is_not_fast() -> None:
    """기본값이 004 이전 동작이면 이 기능이 있어도 아무것도 달라지지 않는다 (research R8)."""
    assert DEFAULT_PACING is RunPacing.NORMAL
    assert DEFAULT_PACING is not RunPacing.FAST


def test_every_pacing_has_a_label() -> None:
    """화면 표기 누락을 막는다 — 값이 늘면 이름도 함께 늘어야 한다."""
    for pacing in RunPacing:
        assert label(pacing)


def test_unknown_value_is_rejected() -> None:
    """열거형 밖 값은 받지 않는다. 임의의 밀리초 입력을 허용하지 않는다."""
    with pytest.raises(ValueError, match="turtle"):
        RunPacing("turtle")


def test_table_covers_every_member() -> None:
    """값을 추가하고 대응표에 넣지 않으면 여기서 걸린다."""
    for pacing in RunPacing:
        assert isinstance(delay_ms(pacing), int)
        assert isinstance(auto_pause(pacing), bool)
