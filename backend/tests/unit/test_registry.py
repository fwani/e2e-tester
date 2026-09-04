"""프로젝트 레지스트리. DR-002·DR-003·DR-004·DR-007·DR-009.

첫 화면 목록의 근거다. 이것이 없어서 사용자가 절대 경로를 타이핑해야 했다 (research R4).
"""

from __future__ import annotations

import json
import pathlib

import pytest

from itb.storage import registry
from itb.storage.registry import ProjectEntry, forget, list_projects, load, remember, scan_workspace


def make_project(root: pathlib.Path, name: str = "샘플") -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "itb-project.yaml").write_text(
        f"name: {name}\ndefault_start_url: https://x.test/\n", encoding="utf-8"
    )
    return root


@pytest.fixture
def reg(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "registry.json"


# ─── 읽기·쓰기 ──────────────────────────────────────────────────────────────


def test_missing_file_is_not_an_error(reg: pathlib.Path) -> None:
    """첫 실행에는 파일이 없다. 그것이 오류면 아무도 도구를 못 연다."""
    assert load(reg) == ([], None)


def test_remember_then_load(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    root = make_project(tmp_path / "p")
    remember(root, "데이터 플랫폼", "managed", reg)

    entries, warning = load(reg)
    assert warning is None
    assert [(e.name, e.origin) for e in entries] == [("데이터 플랫폼", "managed")]
    assert entries[0].last_opened_at.endswith("Z")


def test_remember_is_idempotent_on_root(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    """같은 프로젝트를 두 번 열어도 항목은 하나다. `root` 가 유일 키다."""
    root = make_project(tmp_path / "p")
    remember(root, "첫 이름", "managed", reg)
    remember(root, "바뀐 이름", "external", reg)

    entries, _ = load(reg)
    assert len(entries) == 1
    assert entries[0].name == "바뀐 이름"
    assert entries[0].origin == "external"


def test_stored_form_omits_derived_fields(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    """`accessible` 은 조회 시 계산한다. 저장하면 즉시 낡는다 (data-model.md §1)."""
    remember(make_project(tmp_path / "p"), "x", "managed", reg)

    raw = json.loads(reg.read_text(encoding="utf-8"))
    assert set(raw["projects"][0]) == {"root", "name", "last_opened_at", "origin"}


def test_unknown_version_is_not_overwritten(reg: pathlib.Path, tmp_path: pathlib.Path) -> None:
    """앞으로 형식이 바뀌었을 때 옛 도구가 사용자 기록을 날리면 안 된다."""
    original = json.dumps({"version": 99, "projects": [{"root": "/x", "name": "미래"}]})
    reg.write_text(original, encoding="utf-8")

    entries, warning = load(reg)
    assert entries == []
    assert warning is not None and "형식을 알 수 없습니다" in warning

    remember(make_project(tmp_path / "p"), "새것", "managed", reg)
    assert reg.read_text(encoding="utf-8") == original, "모르는 형식을 덮어썼다"


def test_corrupt_file_warns_and_does_not_crash(reg: pathlib.Path) -> None:
    reg.write_text("{ not json", encoding="utf-8")

    entries, warning = load(reg)
    assert entries == []
    assert warning is not None


def test_entries_without_root_are_skipped(reg: pathlib.Path) -> None:
    reg.write_text(
        json.dumps({"version": 1, "projects": [{"name": "root 없음"}, {"root": "/ok"}]}),
        encoding="utf-8",
    )
    entries, _ = load(reg)
    assert [e.root for e in entries] == ["/ok"]


# ─── 목록에서 치우기 (DR-009) ───────────────────────────────────────────────


def test_forget_removes_entry_but_not_the_project(
    tmp_path: pathlib.Path, reg: pathlib.Path
) -> None:
    """목록 정리와 자산 삭제는 다른 조작이다. 되돌릴 수 없는 쪽을 조용히 하지 않는다."""
    root = make_project(tmp_path / "p")
    remember(root, "x", "external", reg)

    assert forget(root, reg) is True
    assert load(reg)[0] == []
    assert (root / "itb-project.yaml").exists(), "디스크의 프로젝트를 지웠다"


def test_forget_unknown_root_is_noop(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    assert forget(tmp_path / "nope", reg) is False


# ─── 관리 위치 스캔 (DR-002) ────────────────────────────────────────────────


def test_scan_finds_projects_without_registry(tmp_path: pathlib.Path) -> None:
    """레지스트리가 지워져도 관리 위치의 프로젝트는 보여야 한다."""
    make_project(tmp_path / "a", "가")
    make_project(tmp_path / "b", "나")
    (tmp_path / "not-a-project").mkdir()

    found = scan_workspace(tmp_path)
    assert {e.name for e in found} == {"가", "나"}
    assert all(e.origin == "managed" for e in found)


def test_scan_reads_display_name_from_project_file(tmp_path: pathlib.Path) -> None:
    make_project(tmp_path / "slug-name", "사람이 읽는 이름")
    assert scan_workspace(tmp_path)[0].name == "사람이 읽는 이름"


def test_scan_missing_workspace_is_empty(tmp_path: pathlib.Path) -> None:
    assert scan_workspace(tmp_path / "nope") == []


# ─── 합집합 목록 (DR-002 + DR-004 + DR-007) ─────────────────────────────────


def test_list_merges_scan_and_registry(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    """스캔만 보면 외부 경로가 안 보이고, 레지스트리만 보면 관리 위치가 사라진다."""
    ws = tmp_path / "ws"
    managed = make_project(ws / "managed", "관리")
    external = make_project(tmp_path / "elsewhere" / "ext", "외부")
    remember(external, "외부", "external", reg)

    entries, _ = list_projects(reg, ws)
    assert {e.name for e in entries} == {"관리", "외부"}
    assert managed.exists()


def test_list_deduplicates_by_root(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    ws = tmp_path / "ws"
    root = make_project(ws / "p", "하나")
    remember(root, "하나", "managed", reg)

    entries, _ = list_projects(reg, ws)
    assert len(entries) == 1


def test_list_sorts_by_last_opened_descending(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    """DR-004 — 최근 연 순."""
    ws = tmp_path / "ws"
    for name in ("먼저", "나중"):
        remember(make_project(ws / name, name), name, "managed", reg)

    entries, _ = list_projects(reg, ws)
    stamps = [e.last_opened_at for e in entries]
    assert stamps == sorted(stamps, reverse=True)


def test_list_marks_inaccessible_with_reason(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    """DR-009 — 사라진 프로젝트를 조용히 빼지 않는다. 왜 못 여는지 알려준다."""
    gone = tmp_path / "gone"
    make_project(gone, "사라질 것")
    remember(gone, "사라질 것", "external", reg)
    (gone / "itb-project.yaml").unlink()
    gone.rmdir()

    entries, _ = list_projects(reg, tmp_path / "ws")
    assert len(entries) == 1
    assert entries[0].accessible is False
    assert entries[0].unavailable_reason


def test_list_marks_directory_without_marker(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    root = make_project(tmp_path / "p", "표식 삭제")
    remember(root, "표식 삭제", "external", reg)
    (root / "itb-project.yaml").unlink()

    entries, _ = list_projects(reg, tmp_path / "ws")
    assert entries[0].accessible is False
    assert "itb-project.yaml" in (entries[0].unavailable_reason or "")


def test_list_survives_unreadable_project_file(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    """프로젝트 파일 하나가 깨져도 목록 전체가 실패하면 안 된다."""
    ws = tmp_path / "ws"
    broken = ws / "broken"
    broken.mkdir(parents=True)
    (broken / "itb-project.yaml").write_text("{{{ not yaml", encoding="utf-8")

    entries, _ = list_projects(reg, ws)
    assert [e.name for e in entries] == ["broken"], "디렉터리 이름으로 대신하지 않았다"


def test_list_propagates_registry_warning(tmp_path: pathlib.Path, reg: pathlib.Path) -> None:
    reg.write_text("garbage", encoding="utf-8")
    _, warning = list_projects(reg, tmp_path / "ws")
    assert warning is not None


def test_default_paths_are_used_when_omitted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """인자를 생략하면 XDG 경로를 쓴다 — 실제 서버가 도는 방식이다."""
    monkeypatch.setattr(registry, "registry_file", lambda: tmp_path / "r.json")
    monkeypatch.setattr(registry, "workspace_dir", lambda: tmp_path / "ws")
    make_project(tmp_path / "ws" / "p", "기본 경로")

    entries, _ = list_projects()
    assert [e.name for e in entries] == ["기본 경로"]


def test_entry_equality_ignores_nothing_surprising() -> None:
    a = ProjectEntry(root="/x", name="n", last_opened_at="t", origin="managed")
    assert a.stored()["origin"] == "managed"
