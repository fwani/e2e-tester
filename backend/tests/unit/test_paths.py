"""도구가 관리하는 저장 위치와 경계 검증. DR-002·DR-005·DR-006.

경계 검증은 **보안 요구**다 (헌법 "모든 외부 입력은 경계에서 검증"). 탐색기가 임의
파일 시스템 브라우저가 되면 안 된다.
"""

from __future__ import annotations

import pathlib

import pytest

from itb.storage.paths import (
    PathOutsideHomeError,
    allocate_workspace_path,
    config_dir,
    data_dir,
    registry_file,
    resolve_within_home,
    slugify,
    workspace_dir,
)

# ─── 경로 결정 ──────────────────────────────────────────────────────────────


def test_defaults_follow_xdg_convention(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: pathlib.Path("/h")))

    assert config_dir() == pathlib.Path("/h/.config/itb")
    assert data_dir() == pathlib.Path("/h/.local/share/itb")
    assert workspace_dir() == pathlib.Path("/h/.local/share/itb/projects")
    assert registry_file() == pathlib.Path("/h/.config/itb/registry.json")


def test_xdg_overrides_are_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/cfg")
    monkeypatch.setenv("XDG_DATA_HOME", "/dat")

    assert config_dir() == pathlib.Path("/cfg/itb")
    assert workspace_dir() == pathlib.Path("/dat/itb/projects")


def test_paths_follow_home_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    """경로를 모듈 상수로 굳히면 HOME 변경을 따라오지 못한다 — 테스트가 사용자 홈을 건드린다."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: pathlib.Path("/a")))
    first = config_dir()
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: pathlib.Path("/b")))

    assert first != config_dir()


def test_config_and_data_are_separate(monkeypatch: pytest.MonkeyPatch) -> None:
    """사용자 자산을 설정 디렉터리에 두지 않는다 — 001 FR-011·헌법 원칙 V (research R4)."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: pathlib.Path("/h")))

    assert config_dir() not in workspace_dir().parents


# ─── 경계 검증 (보안) ───────────────────────────────────────────────────────


def test_path_inside_home_is_accepted(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    target = tmp_path / "work" / "proj"
    target.mkdir(parents=True)

    assert resolve_within_home(target) == target.resolve()


def test_home_itself_is_accepted(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))

    assert resolve_within_home(tmp_path) == tmp_path.resolve()


def test_path_outside_home_is_rejected(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    (tmp_path / "home").mkdir()

    with pytest.raises(PathOutsideHomeError):
        resolve_within_home("/etc")


def test_dotdot_escape_is_rejected(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """문자열 검사만 하면 통과한다. 정규화 후에 판정해야 막힌다."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: home))

    with pytest.raises(PathOutsideHomeError):
        resolve_within_home(str(home / ".." / ".." / "etc"))


def test_symlink_out_of_home_is_rejected(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """심볼릭 링크는 따라간 뒤 **실제 위치로** 판정한다."""
    home = tmp_path / "home"
    home.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (home / "escape").symlink_to(outside)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: home))

    with pytest.raises(PathOutsideHomeError):
        resolve_within_home(home / "escape")


# ─── 슬러그 ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("데이터 플랫폼", "데이터-플랫폼"),
        ("My Project", "My-Project"),
        ("a/b/c", "a-b-c"),  # 경로 구분자가 디렉터리를 가르면 안 된다
        ("../../etc", "etc"),  # 상위 이동
        ("...", "project"),  # 남는 것이 없으면 기본 이름
        ("", "project"),
        ("   ", "project"),
        (".", "project"),
        ("..", "project"),
        ("ok_name-1.2", "ok_name-1.2"),
    ],
)
def test_slugify(name: str, expected: str) -> None:
    assert slugify(name) == expected


def test_slugify_strips_control_characters() -> None:
    assert "\n" not in slugify("a\nb")
    assert "\x00" not in slugify("a\x00b")


def test_slugify_bounds_length() -> None:
    assert len(slugify("x" * 500)) <= 80


def test_slug_never_escapes_workspace(tmp_path: pathlib.Path) -> None:
    """어떤 이름을 줘도 관리 위치를 벗어나지 않는다 — 이름이 경로가 되는 지점이다."""
    for hostile in ["../../etc/passwd", "/absolute", "..", "a/../../b"]:
        allocated = allocate_workspace_path(hostile, root=tmp_path)
        assert tmp_path in allocated.parents, f"{hostile} → {allocated}"


def test_allocate_avoids_collision_instead_of_failing(tmp_path: pathlib.Path) -> None:
    """위치 충돌로 실패시키지 않는다 — 사용자는 위치를 모른다 (contracts §2)."""
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj-2").mkdir()

    assert allocate_workspace_path("proj", root=tmp_path) == tmp_path / "proj-3"
