"""프로젝트 레지스트리. DR-002·DR-003·DR-004·DR-007·DR-009.

**첫 화면 목록의 근거다.** 이전에는 열린 프로젝트가 `AppState.repository` — 프로세스
메모리 — 에만 있었다. 서버를 재시작하면 사라지고, 사용자는 자기가 전에 만든 프로젝트가
어디 있는지 알 방법이 없어 절대 경로를 타이핑해야 했다. 그것이 이번 라운드 최상위
결함이다 (research R4).

**목록은 두 출처의 합집합이다.**

- 관리 위치(`~/.local/share/itb/projects/`) 스캔
- 레지스트리 파일(`~/.config/itb/registry.json`)

어느 한쪽만으로는 부족하다. 스캔만 보면 "기존 프로젝트 열기" 로 연 외부 경로가 안
보이고(DR-007 위반), 레지스트리만 보면 파일이 사라졌을 때 관리 위치의 프로젝트가 통째로
사라진다.

`accessible` 은 **저장하지 않고 조회 시 계산한다.** 파일 시스템은 도구 바깥에서 바뀌므로
저장하면 즉시 낡는다 (data-model.md §1).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import pathlib
from dataclasses import dataclass
from typing import Any, Literal

from itb.storage import atomic
from itb.storage.paths import registry_file, workspace_dir
from itb.storage.repository import PROJECT_FILE

FORMAT_VERSION = 1

Origin = Literal["managed", "external"]


def _now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ProjectEntry:
    """도구가 알고 있는 프로젝트 하나."""

    root: str
    name: str
    last_opened_at: str
    origin: Origin

    # 아래 둘은 조회 시 계산한다. 저장하지 않는다.
    accessible: bool = True
    unavailable_reason: str | None = None

    def stored(self) -> dict[str, Any]:
        """파일에 쓸 형태. 파생 필드는 뺀다."""
        return {
            "root": self.root,
            "name": self.name,
            "last_opened_at": self.last_opened_at,
            "origin": self.origin,
        }


class RegistryError(Exception):
    """레지스트리를 읽을 수 없다. 사용자에게 알릴 수 있는 사유를 담는다."""


# ─── 접근 가능 여부 (조회 시 계산) ──────────────────────────────────────────


def _probe(root: pathlib.Path) -> tuple[bool, str | None]:
    """프로젝트가 지금 열 수 있는 상태인가 (DR-009).

    열어 보지 않고 존재와 권한만 본다 — 목록을 그리려고 프로젝트 N개를 파싱할 이유가 없다.
    """
    if not root.exists():
        return False, "디렉터리가 없습니다. 옮겨졌거나 삭제된 것으로 보입니다."
    if not root.is_dir():
        return False, "디렉터리가 아닙니다."
    marker = root / PROJECT_FILE
    if not marker.exists():
        return False, f"{PROJECT_FILE} 이 없어 프로젝트로 열 수 없습니다."
    try:
        marker.open("rb").close()
    except OSError:
        return False, "읽기 권한이 없습니다."
    return True, None


def _name_from_disk(root: pathlib.Path, fallback: str) -> str:
    """프로젝트 파일에서 표시 이름을 읽는다. 실패하면 디렉터리 이름을 쓴다.

    목록을 그리는 일이 프로젝트 파일 하나 때문에 통째로 실패하면 안 된다.
    """
    with contextlib.suppress(Exception):
        import yaml  # noqa: PLC0415 — 목록 조회 경로에서만 필요하다

        data = yaml.safe_load((root / PROJECT_FILE).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            return str(data["name"])
    return fallback


# ─── 파일 입출력 ────────────────────────────────────────────────────────────


def load(path: pathlib.Path | None = None) -> tuple[list[ProjectEntry], str | None]:
    """레지스트리를 읽는다. `(항목, 경고)` 를 돌려준다.

    **읽지 못해도 예외를 던지지 않는다.** 첫 화면이 레지스트리 하나 때문에 열리지 않으면
    사용자는 아무것도 할 수 없다. 대신 경고를 함께 돌려 화면이 알릴 수 있게 한다.

    **모르는 형식을 덮어쓰지 않는다.** 앞으로 형식이 바뀌었을 때 옛 도구가 사용자의
    기록을 조용히 날리는 것을 막는다.
    """
    file = path or registry_file()
    if not file.exists():
        return [], None

    try:
        raw = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], f"프로젝트 목록 파일을 읽을 수 없습니다: {file}. 새 항목만 표시합니다."

    if not isinstance(raw, dict) or raw.get("version") != FORMAT_VERSION:
        return [], (
            f"프로젝트 목록 파일의 형식을 알 수 없습니다: {file}. "
            "덮어쓰지 않았습니다. 최신 버전으로 만든 파일일 수 있습니다."
        )

    entries: list[ProjectEntry] = []
    for item in raw.get("projects", []):
        if not isinstance(item, dict) or not isinstance(item.get("root"), str):
            continue
        entries.append(
            ProjectEntry(
                root=item["root"],
                name=str(item.get("name") or pathlib.Path(item["root"]).name),
                last_opened_at=str(item.get("last_opened_at") or ""),
                origin="external" if item.get("origin") == "external" else "managed",
            )
        )
    return entries, None


def _save(entries: list[ProjectEntry], path: pathlib.Path | None = None) -> None:
    file = path or registry_file()
    body = {"version": FORMAT_VERSION, "projects": [e.stored() for e in entries]}
    # 쓰다 만 파일을 남기지 않는다. 이 방식은 여기서 시작해 `storage/atomic.py` 로
    # 옮겨졌다 — 자산을 쓰는 모든 경로가 같은 것을 지난다 (003 AP-042).
    atomic.write_text(file, json.dumps(body, ensure_ascii=False, indent=2))


# ─── 갱신 ──────────────────────────────────────────────────────────────────


def remember(
    root: pathlib.Path, name: str, origin: Origin, path: pathlib.Path | None = None
) -> None:
    """프로젝트를 목록에 넣거나 마지막 연 시각을 갱신한다 (DR-007).

    형식을 읽지 못한 경우에는 **쓰지 않는다.** 알 수 없는 형식을 우리 형식으로 덮으면
    사용자의 기록이 사라진다.
    """
    file = path or registry_file()
    entries, warning = load(file)
    if warning is not None and file.exists():
        return

    resolved = str(pathlib.Path(root).expanduser().resolve())
    kept = [e for e in entries if e.root != resolved]
    kept.append(ProjectEntry(root=resolved, name=name, last_opened_at=_now(), origin=origin))
    _save(kept, file)


def forget(root: pathlib.Path, path: pathlib.Path | None = None) -> bool:
    """목록에서 항목을 지운다 (DR-009).

    **디스크의 프로젝트는 지우지 않는다.** 목록 정리와 자산 삭제는 다른 조작이고,
    되돌릴 수 없는 쪽을 조용히 하지 않는다.

    관리 위치에 실재하는 프로젝트는 스캔에 다시 걸려 목록에 남는다. 정상이다 —
    `list_projects` 가 스캔 ∪ 레지스트리이기 때문이다.
    """
    file = path or registry_file()
    entries, _ = load(file)
    resolved = str(pathlib.Path(root).expanduser().resolve())
    kept = [e for e in entries if e.root != resolved]
    if len(kept) == len(entries):
        return False
    _save(kept, file)
    return True


# ─── 조회 ──────────────────────────────────────────────────────────────────


def scan_workspace(root: pathlib.Path | None = None) -> list[ProjectEntry]:
    """관리 위치에서 프로젝트를 찾는다 (DR-002).

    레지스트리가 없거나 지워져도 여기서 만든 프로젝트는 보인다.
    """
    base = (root or workspace_dir()).expanduser()
    if not base.is_dir():
        return []

    found: list[ProjectEntry] = []
    for child in sorted(base.iterdir()):
        if not (child / PROJECT_FILE).exists():
            continue
        # 레지스트리에 없는 항목의 정렬 기준. 실제로 연 시각은 아니다.
        stamp = dt.datetime.fromtimestamp(child.stat().st_mtime, dt.UTC)
        found.append(
            ProjectEntry(
                root=str(child.resolve()),
                name=_name_from_disk(child, child.name),
                last_opened_at=stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                origin="managed",
            )
        )
    return found


def list_projects(
    registry_path: pathlib.Path | None = None, workspace: pathlib.Path | None = None
) -> tuple[list[ProjectEntry], str | None]:
    """첫 화면에 그릴 목록. `(항목, 경고)`.

    스캔 ∪ 레지스트리를 `root` 로 중복 제거하고 최근 연 순으로 정렬한다
    (DR-002·DR-004·DR-007). 레지스트리 쪽 항목을 우선한다 — 실제로 연 시각을 알기
    때문이다.
    """
    stored, warning = load(registry_path)
    merged: dict[str, ProjectEntry] = {e.root: e for e in scan_workspace(workspace)}
    for entry in stored:  # 레지스트리가 스캔을 덮는다
        merged[entry.root] = entry

    resolved: list[ProjectEntry] = []
    for entry in merged.values():
        ok, reason = _probe(pathlib.Path(entry.root))
        name = _name_from_disk(pathlib.Path(entry.root), entry.name) if ok else entry.name
        resolved.append(
            ProjectEntry(
                root=entry.root,
                name=name,
                last_opened_at=entry.last_opened_at,
                origin=entry.origin,
                accessible=ok,
                unavailable_reason=reason,
            )
        )

    resolved.sort(key=lambda e: e.last_opened_at, reverse=True)
    return resolved, warning
