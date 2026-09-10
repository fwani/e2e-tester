"""여러 자산을 옮길 때의 「전부 되거나 전부 안 되거나」. 013 FR-432·FR-444b.

**이 규약이 왜 성립하는지**가 이 파일이 지키는 것이다. 파일 시스템에는 여러 경로에 걸친
원자적 연산이 없다. 삭제를 **휴지통 이동**으로 정한 결정 덕에 되돌릴 수 있고, 되돌릴 수
있으므로 「전부 되거나 전부 안 되거나」를 흉내 낼 수 있다 (013 research R4).
"""

from __future__ import annotations

import pathlib

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


# ─── 그룹 이동 (013 FR-444a·FR-444b · research R5) ─────────────────────────


def _repo(tmp_path: pathlib.Path):  # noqa: ANN202
    from itb.domain.test_case import Project
    from itb.storage.repository import ProjectRepository

    return ProjectRepository.create(
        tmp_path / "프로젝트",
        Project(name="프로젝트", default_start_url="https://x.test/"),
    )


def _add(repo, test_id: str, name: str) -> None:  # noqa: ANN001
    from itb.domain.step import NavigateStep
    from itb.domain.test_case import AuthoringMode, Test

    repo.write_test(
        Test(
            id=test_id,
            name=name,
            authoring_mode=AuthoringMode.RECORD,
            start_url="https://x.test/",
            steps=[NavigateStep(id="step-01", label="열기", url="https://x.test/")],
        )
    )


def _add_result(repo, test_id: str):  # noqa: ANN001, ANN202
    runs = repo.paths.run_dir(test_id)
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "result.json").write_text('{"결과": true}', encoding="utf-8")
    return runs


def test_the_number_survives_the_move(tmp_path: pathlib.Path) -> None:
    """**접두어만 바뀐다** (013 research R3).

    번호가 프로젝트 전체에서 고유하므로 새 자리가 언제나 비어 있다 — FR-444c 를 규칙이
    아니라 구조로 만족시킨다.
    """
    from itb.storage.test_moves import move_test_to_group

    repo = _repo(tmp_path)
    _add(repo, "TC-003", "로그인")

    moved = move_test_to_group(repo, "TC-003", "USER")

    assert moved.to_id == "USER-003"
    assert repo.find_test_path("USER-003") is not None
    assert repo.find_test_path("TC-003") is None


def test_the_result_follows_the_test(tmp_path: pathlib.Path) -> None:
    """SC-628 — 옮긴 뒤에도 결과가 그대로여야 한다."""
    from itb.storage.test_moves import move_test_to_group

    repo = _repo(tmp_path)
    _add(repo, "TC-001", "로그인")
    old_runs = _add_result(repo, "TC-001")

    move_test_to_group(repo, "TC-001", "USER")

    assert not old_runs.exists()
    assert (repo.paths.run_dir("USER-001") / "result.json").read_text(
        encoding="utf-8"
    ) == '{"결과": true}'


def test_the_steps_are_untouched(tmp_path: pathlib.Path) -> None:
    """그룹을 바꾸는 것이 테스트 내용을 건드리지 않는다 (FR-447)."""
    from itb.storage.test_moves import move_test_to_group

    repo = _repo(tmp_path)
    _add(repo, "TC-001", "로그인")
    before = repo.read_test("TC-001")

    move_test_to_group(repo, "TC-001", "USER")
    after = repo.read_test("USER-001")

    assert after.name == before.name
    assert [s.id for s in after.steps] == [s.id for s in before.steps]
    assert after.id == "USER-001"


def test_a_taken_number_gets_a_new_one(tmp_path: pathlib.Path) -> None:
    """번호가 차 있으면 **새 번호를 뽑아 옮긴다** (014 3차 요청).

    013 은 번호를 프로젝트 전체에서 고유하게 두어 이 상황 자체를 없앴었다. 그룹마다
    번호를 세게 되면서 자리가 차 있는 일이 흔해졌고, 그때 거절하면 **그룹 이동이 평범한
    경우에 실패한다.**

    FR-444c(식별자 고유)는 여전히 지켜진다 — 거절이 아니라 **부여**로 지킨다.
    """
    from itb.storage.test_moves import move_test_to_group

    repo = _repo(tmp_path)
    _add(repo, "TC-001", "옮길 것")
    _add(repo, "USER-001", "이미 있는 것")

    moved = move_test_to_group(repo, "TC-001", "USER")

    assert moved.to_id == "USER-002"
    assert repo.find_test_path("TC-001") is None
    assert repo.find_test_path("USER-001") is not None
    assert repo.find_test_path("USER-002") is not None


def test_a_free_number_is_kept_on_move(tmp_path: pathlib.Path) -> None:
    """자리가 비어 있으면 **번호를 그대로 지킨다**.

    사용자의 문서·CI 가 그 번호를 가리키고 있다. 비어 있는데도 새 번호를 주면 이유 없이
    자산의 이름을 바꾸는 일이 된다.
    """
    from itb.storage.test_moves import move_test_to_group

    repo = _repo(tmp_path)
    _add(repo, "TC-003", "옮길 것")

    assert move_test_to_group(repo, "TC-003", "USER").to_id == "USER-003"


def test_rename_still_refuses_a_taken_identifier(tmp_path: pathlib.Path) -> None:
    """낮은 층의 가드는 그대로다 — 이미 쓰는 식별자로는 이름을 바꿀 수 없다."""
    from itb.storage.test_moves import MoveError, rename_test_id

    repo = _repo(tmp_path)
    _add(repo, "TC-001", "옛 것")
    _add(repo, "USER-001", "이미 있는 것")

    with pytest.raises(MoveError, match="이미 쓰는"):
        rename_test_id(repo, "TC-001", "USER-001")

    assert repo.find_test_path("TC-001") is not None


def test_a_failed_definition_write_puts_the_artifacts_back(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-628a — **정의와 결과가 갈라진 상태를 만들지 않는다.**

    산출물을 먼저 옮기는 순서가 이 되돌림을 가능하게 한다 (013 research R5).
    """
    from itb.storage import test_moves as mod
    from itb.storage.test_moves import MoveError, move_test_to_group

    repo = _repo(tmp_path)
    _add(repo, "TC-001", "로그인")
    old_runs = _add_result(repo, "TC-001")

    def boom(_self, _test):  # noqa: ANN001, ANN202
        msg = "쓸 수 없습니다"
        raise OSError(13, msg)

    monkeypatch.setattr(type(repo), "write_test", boom)

    with pytest.raises(MoveError):
        move_test_to_group(repo, "TC-001", "USER")

    monkeypatch.undo()
    assert repo.find_test_path("TC-001") is not None, "정의가 원래 자리에 없다"
    assert (old_runs / "result.json").exists(), "산출물이 되돌려지지 않았다"
    assert not repo.paths.run_dir("USER-001").exists(), "새 자리에 흔적이 남았다"
    assert mod is not None


def test_moving_back_restores_the_original_identifier(
    tmp_path: pathlib.Path,
) -> None:
    """복수 이동의 되돌림이 이것에 기댄다 (`run_all` 의 3번 걸음)."""
    from itb.storage.test_moves import move_test_back, move_test_to_group

    repo = _repo(tmp_path)
    _add(repo, "TC-001", "로그인")
    _add_result(repo, "TC-001")

    moved = move_test_to_group(repo, "TC-001", "USER")
    move_test_back(repo, moved)

    assert repo.find_test_path("TC-001") is not None
    assert repo.find_test_path("USER-001") is None
    assert (repo.paths.run_dir("TC-001") / "result.json").exists()
