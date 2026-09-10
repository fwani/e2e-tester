"""휴지통 이동. 012 FR-409·FR-414·FR-415·FR-420·FR-421.

**삭제가 파괴가 아니라 이동이라는 것이 이 모듈의 전부다.** `tests/*.yaml` 은 사용자가
버전 관리에 넣도록 만든 평문 자산이고(헌법 원칙 V), 실수로 지운 것을 되찾을 수 없으면
이 기능은 사용자에게 손해다.
"""

from __future__ import annotations

import datetime as dt
import pathlib

import pytest

from itb.storage import registry
from itb.storage.trash import TrashError, move_to_trash


@pytest.fixture
def store(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """`XDG` 를 임시 디렉터리로 돌린다. 실제 홈을 건드리지 않는다."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return tmp_path


def make_project(root: pathlib.Path, name: str = "샘플") -> pathlib.Path:
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "itb-project.yaml").write_text(
        f"name: {name}\ndefault_start_url: https://x.test/\n", encoding="utf-8"
    )
    (root / "tests" / "TC-001-로그인.yaml").write_text("id: TC-001\n", encoding="utf-8")
    return root


def workspace(store: pathlib.Path) -> pathlib.Path:
    return store / "data" / "itb" / "projects"


def trash(store: pathlib.Path) -> pathlib.Path:
    return store / "data" / "itb" / "trash"


# ─── 옮기기 ────────────────────────────────────────────────────────────────


def test_the_whole_directory_moves_with_its_contents(store: pathlib.Path) -> None:
    root = make_project(workspace(store) / "결제")

    destination = move_to_trash(root)

    assert destination is not None
    assert not root.exists()
    assert (destination / "itb-project.yaml").exists()
    moved = destination / "tests" / "TC-001-로그인.yaml"
    assert moved.read_text(encoding="utf-8") == "id: TC-001\n"


def test_the_destination_records_when_and_what(store: pathlib.Path) -> None:
    """자리 이름만으로 "언제 지운 어느 프로젝트" 가 읽혀야 한다 (012 research R3)."""
    root = make_project(workspace(store) / "결제")

    destination = move_to_trash(root)

    assert destination is not None
    assert destination.parent == trash(store)
    assert destination.name.endswith("-결제")
    # 접두사가 그날의 시각이다.
    stamp = destination.name.split("-결제")[0]
    assert dt.datetime.strptime(stamp, "%Y%m%d-%H%M%S")  # noqa: DTZ007 — 형식만 본다


def test_deleting_the_same_name_twice_keeps_both(store: pathlib.Path) -> None:
    """FR-415 · SC-619 — **덮어쓰지 않는다.**

    시각 접두사만으로는 부족하다. 같은 초에 두 번 지우는 일이 실제로 가능하고, 그때
    덮어쓰면 먼저 지운 사람의 테스트 정의가 사라진다.
    """
    first = make_project(workspace(store) / "같은이름", name="첫 번째")
    first_dest = move_to_trash(first)
    second = make_project(workspace(store) / "같은이름", name="두 번째")

    second_dest = move_to_trash(second)

    assert first_dest is not None
    assert second_dest is not None
    assert first_dest != second_dest
    assert "첫 번째" in (first_dest / "itb-project.yaml").read_text(encoding="utf-8")
    assert "두 번째" in (second_dest / "itb-project.yaml").read_text(encoding="utf-8")


def test_an_already_missing_directory_is_not_a_failure(store: pathlib.Path) -> None:
    """FR-420 — 사용자가 원한 결과가 이미 이루어져 있다. 실패로 보고하지 않는다."""
    assert move_to_trash(workspace(store) / "없는-것") is None


# ─── 실패 ──────────────────────────────────────────────────────────────────


def test_a_failed_move_leaves_the_original_where_it_was(
    store: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-414 · SC-618 — 이 성질이 이 모듈 계약의 핵심이다.

    목록에서는 사라졌는데 자산은 원래 자리에 남는 상태가 가장 나쁘다 — 사용자는 자기
    테스트가 어디 있는지 알 방법을 잃는다. 그것을 막는 전제가 "실패하면 원본이 그대로"
    이고, 호출부는 그 위에서 "성공 뒤에 레지스트리" 순서를 지킨다.
    """
    root = make_project(workspace(store) / "결제")

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("itb.storage.trash.shutil.move", boom)

    with pytest.raises(TrashError):
        move_to_trash(root)

    assert (root / "tests" / "TC-001-로그인.yaml").exists()


def test_a_failed_move_does_not_leave_half_a_copy_in_the_trash(
    store: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """다른 볼륨에서는 복사 도중 실패할 수 있다. 반쪽을 남기지 않는다 (012 research R4)."""
    root = make_project(workspace(store) / "결제")

    def half_then_boom(src: str, dst: str) -> None:
        pathlib.Path(dst).mkdir(parents=True)
        (pathlib.Path(dst) / "itb-project.yaml").write_text("반쪽", encoding="utf-8")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("itb.storage.trash.shutil.move", half_then_boom)

    with pytest.raises(TrashError):
        move_to_trash(root)

    assert list(trash(store).iterdir()) == []


# ─── 목록과의 관계 ──────────────────────────────────────────────────────────


def test_a_trashed_project_does_not_come_back_in_the_listing(store: pathlib.Path) -> None:
    """FR-421 — 휴지통은 `projects/` 의 **형제**라 스캔에 걸리지 않는다.

    `projects/.trash/` 안에 두었다면 스캔·목록·경로 검증 세 곳이 각자 제외 규칙을
    지켜야 하고, 한 곳이 빠지면 지운 프로젝트가 목록에 돌아온다.
    """
    root = make_project(workspace(store) / "결제")
    registry.remember(root, "결제", "managed")

    move_to_trash(root)
    registry.forget(root)

    entries, _warning = registry.list_projects()
    assert entries == []
