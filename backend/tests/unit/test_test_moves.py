"""여러 자산을 옮길 때의 「전부 되거나 전부 안 되거나」. 013 FR-432·FR-444b.

**이 규약이 왜 성립하는지**가 이 파일이 지키는 것이다. 파일 시스템에는 여러 경로에 걸친
원자적 연산이 없다. 삭제를 **휴지통 이동**으로 정한 결정 덕에 되돌릴 수 있고, 되돌릴 수
있으므로 「전부 되거나 전부 안 되거나」를 흉내 낼 수 있다 (013 research R4).
"""

from __future__ import annotations

import pytest

from itb.storage.test_moves import (
    AllOrNothingError,
    PartialFailureError,
    run_all,
)


def test_a_validation_failure_touches_nothing() -> None:
    """FR-432 — 실패의 대부분이 여기서 걸린다. 걸리면 **아무것도 하지 않는다.**"""
    done: list[str] = []

    def validate(t: str) -> None:
        if t == "나쁜 것":
            msg = "실행 중입니다"
            raise ValueError(msg)

    with pytest.raises(ValueError, match="실행 중입니다"):
        run_all(
            ["좋은 것", "나쁜 것"],
            validate=validate,
            do=lambda t: done.append(t) or t,  # type: ignore[func-returns-value]
            undo=lambda _t, _r: None,
        )

    assert done == [], "검증 단계에서 걸렸는데 무언가 실행됐다"


def test_every_target_is_validated_before_any_runs() -> None:
    """**전부** 검증하고 **그다음** 실행한다. 섞으면 첫 번째가 이미 옮겨진 뒤 두 번째가 걸린다."""
    order: list[str] = []

    run_all(
        ["a", "b"],
        validate=lambda t: order.append(f"검증:{t}"),
        do=lambda t: order.append(f"실행:{t}") or t,  # type: ignore[func-returns-value]
        undo=lambda _t, _r: None,
    )

    assert order == ["검증:a", "검증:b", "실행:a", "실행:b"]


def test_a_midway_failure_rolls_back_what_was_done() -> None:
    """FR-432 · SC-624 — 「셋 중 둘만」을 만들지 않는다."""
    moved: list[str] = []

    def do(t: str) -> str:
        if t == "c":
            msg = "옮기지 못했습니다"
            raise OSError(msg)
        moved.append(t)
        return f"휴지통/{t}"

    with pytest.raises(AllOrNothingError, match="옮기지 못했습니다"):
        run_all(
            ["a", "b", "c"],
            validate=lambda _t: None,
            do=do,
            undo=lambda t, _r: moved.remove(t),
        )

    assert moved == [], "되돌린 뒤에도 옮겨진 것이 남았다"


def test_rollback_runs_in_reverse_order() -> None:
    """나중에 한 것이 앞의 것에 기대고 있을 수 있다."""
    undone: list[str] = []

    def do(t: str) -> str:
        if t == "c":
            msg = "실패"
            raise OSError(msg)
        return t

    with pytest.raises(AllOrNothingError):
        run_all(
            ["a", "b", "c"],
            validate=lambda _t: None,
            do=do,
            undo=lambda t, _r: undone.append(t),
        )

    assert undone == ["b", "a"]


def test_a_failed_rollback_is_reported_separately() -> None:
    """**삼키지 않는다.**

    되돌렸으면 요청 전과 같으니 다시 시도하면 되고, 되돌리지 못했으면 어디에 무엇이 있는지
    확인해야 한다 — 사용자가 할 일이 다르므로 예외를 가른다.
    """

    def do(t: str) -> str:
        if t == "c":
            msg = "옮기지 못했습니다"
            raise OSError(msg)
        return f"휴지통/{t}"

    def undo(t: str, _r: str) -> None:
        if t == "a":
            msg = "되돌리지도 못했습니다"
            raise OSError(msg)

    with pytest.raises(PartialFailureError) as caught:
        run_all(["a", "b", "c"], validate=lambda _t: None, do=do, undo=undo)

    assert [s.target for s in caught.value.stranded] == ["a"]
    assert caught.value.stranded[0].where == "휴지통/a"


def test_rollback_does_not_stop_at_the_first_failure() -> None:
    """하나가 막혔다고 나머지를 포기하면 되돌릴 수 있었던 것까지 새 자리에 남는다."""
    undone: list[str] = []

    def undo(t: str, _r: str) -> None:
        if t == "b":
            msg = "이것만 막혔다"
            raise OSError(msg)
        undone.append(t)

    def do(t: str) -> str:
        if t == "c":
            msg = "실패"
            raise OSError(msg)
        return t

    with pytest.raises(PartialFailureError) as caught:
        run_all(["a", "b", "c"], validate=lambda _t: None, do=do, undo=undo)

    assert undone == ["a"], "막힌 것 뒤의 되돌리기가 멈췄다"
    assert [s.target for s in caught.value.stranded] == ["b"]


def test_success_returns_what_each_step_produced() -> None:
    """호출자가 옮겨진 자리를 사용자에게 알려야 한다 (FR-437a)."""
    assert run_all(
        ["a", "b"],
        validate=lambda _t: None,
        do=lambda t: f"휴지통/{t}",
        undo=lambda _t, _r: None,
    ) == ["휴지통/a", "휴지통/b"]
