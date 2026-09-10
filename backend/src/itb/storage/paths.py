"""도구가 관리하는 저장 위치. DR-002·DR-006.

사용자가 프로젝트 디렉터리 경로를 타이핑하게 만든 것이 이번 라운드 최상위 결함의
원인이다 — 서버가 어느 경로에서 실행 중인지 사용자는 알 방법이 없다. 도구가 정해진
위치를 알고 있어야 한다.

**설정과 사용자 자산을 나눈다.**

- ``~/.config/itb/`` — 도구 설정. 키(기존)와 레지스트리(신규)
- ``~/.local/share/itb/projects/`` — 사용자 자산. 테스트 정의 YAML

프로젝트를 설정 디렉터리에 두지 않는 이유는 001 FR-011 과 헌법 원칙 V 다. 테스트 정의는
**사용자가 버전 관리에 넣는 평문**이다. 설정 디렉터리에 두면 사용자가 그것을 자기 것으로
인식하지 못한다 (research R4).

``~/.config/itb/keys`` 라는 선례가 이미 `itb.secrets.keys` 에 있다. 같은 관례를 잇는다.
"""

from __future__ import annotations

import datetime as dt
import os
import pathlib
import re
import tempfile
import unicodedata

CONFIG_DIRNAME = "itb"

# 경로를 매번 계산한다. 모듈 상수로 굳히면 테스트가 HOME 을 바꿔도 따라오지 않는다.


def config_dir() -> pathlib.Path:
    """도구 설정 디렉터리. ``XDG_CONFIG_HOME`` 을 존중한다."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = pathlib.Path(base) if base else pathlib.Path.home() / ".config"
    return root / CONFIG_DIRNAME


def data_dir() -> pathlib.Path:
    """사용자 자산 디렉터리. ``XDG_DATA_HOME`` 을 존중한다."""
    base = os.environ.get("XDG_DATA_HOME")
    root = pathlib.Path(base) if base else pathlib.Path.home() / ".local" / "share"
    return root / CONFIG_DIRNAME


def workspace_dir() -> pathlib.Path:
    """관리 프로젝트가 모여 있는 곳. 첫 화면 목록의 스캔 대상이다 (DR-002)."""
    return data_dir() / "projects"


def trash_dir() -> pathlib.Path:
    """삭제된 프로젝트가 옮겨져 있는 곳 (012 FR-409·FR-421).

    **``workspace_dir()`` 의 형제다.** 목록 스캔 대상은 ``data_dir()/projects`` 뿐이므로
    이 자리에 있는 한 삭제한 프로젝트가 목록에 다시 나타날 수 없다. ``projects/.trash/``
    안에 두면 스캔·목록·경로 검증 세 곳이 각자 제외 규칙을 지켜야 하고, 한 곳이 빠지면
    지운 프로젝트가 목록에 돌아온다 (012 research R3).

    도구는 이곳을 **읽지도 비우지도 않는다.** 정리는 사용자가 한다 — 사용자 자산을
    도구가 예고 없이 파괴하는 경로를 만들지 않는다 (헌법 원칙 V).
    """
    return data_dir() / "trash"


def registry_file() -> pathlib.Path:
    """프로젝트 레지스트리. 설정이지 자산이 아니다 (data-model.md §1)."""
    return config_dir() / "registry.json"


def home_root() -> pathlib.Path:
    """디렉터리 탐색의 경계. 이 아래만 탐색을 허용한다 (DR-005 보안 경계)."""
    return pathlib.Path.home().resolve()


# ─── 경계 검증 ──────────────────────────────────────────────────────────────


class PathOutsideHomeError(ValueError):
    """사용자 홈 밖을 가리키는 경로. 탐색기가 임의 파일 시스템 브라우저가 되면 안 된다."""


def resolve_within_home(raw: str | pathlib.Path) -> pathlib.Path:
    """경로를 정규화하고 홈 하위인지 확인한다. 아니면 거부한다.

    **``resolve()`` 를 먼저 한다.** 문자열 검사만 하면 ``~/../etc`` 나 심볼릭 링크로
    경계를 넘을 수 있다. 정규화는 심볼릭 링크도 따라가므로, 링크가 가리키는 **실제**
    위치로 판정한다 (research R4 보안 경계).

    서버가 로컬에 있으므로(001 FR-088) 디렉터리를 읽는 것 자체는 정당하다. 다만 읽어 줄
    범위를 사용자 홈으로 좁힌다 — 그 밖을 열어 줄 이유가 없다.
    """
    path = pathlib.Path(raw).expanduser()
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as exc:  # 순환 심볼릭 링크 등
        msg = f"경로를 해석할 수 없습니다: {raw}"
        raise PathOutsideHomeError(msg) from exc

    home = home_root()
    if resolved != home and home not in resolved.parents:
        msg = "사용자 홈 디렉터리 아래의 경로만 열 수 있습니다."
        raise PathOutsideHomeError(msg)
    return resolved


# ─── 슬러그 ────────────────────────────────────────────────────────────────

_UNSAFE = re.compile(r"[^0-9A-Za-z가-힣._-]+")


def session_files_dir(session_id: str) -> pathlib.Path:
    """세션이 사용자에게 받은 파일이 머무는 곳 (010 T063 · FR-337b·FR-337c).

    **설정도 사용자 자산도 아니다.** 테스트 정의는 사용자가 버전 관리에 넣는 평문이지만
    (원칙 V), 여기 들어오는 파일은 **그 세션의 조작을 위해서만 쓰이고 세션과 함께
    사라진다.** 자산 디렉터리에 두면 사용자는 그것을 자기 것으로 인식하고, 지워지면
    잃어버린 것으로 읽는다.

    그래서 임시 위치에 둔다. 프로세스가 비정상 종료해도 운영체제가 언젠가 정리하고,
    제품은 세션 종료 시점에 명시적으로 지운다 (FR-337b).

    `session_id` 는 서버가 만든 UUID 이므로 경로 조각으로 안전하다 — 사용자가 보낸 값이
    아니다. 그래도 한 겹 더 좁히는 이유는, 이 함수가 나중에 다른 식별자로 불릴 때
    조용히 위험해지지 않게 하기 위해서다.
    """
    safe = _UNSAFE.sub("-", session_id).strip("-.") or "session"
    return session_files_root() / safe[:64]


def session_files_root() -> pathlib.Path:
    """세션 파일 저장소의 뿌리. 검증이 여기를 갈아 끼운다."""
    base = os.environ.get("ITB_SESSION_FILES_DIR")
    if base:
        return pathlib.Path(base)
    return pathlib.Path(tempfile.gettempdir()) / "itb-session-files"


def slugify(name: str) -> str:
    """프로젝트 이름을 디렉터리 이름으로 바꾼다.

    **이름이 경로가 되는 지점이므로 경계 검증이 필요하다** (헌법 보안 요구). 경로
    구분자·상위 이동·제어 문자를 없앤다. 한글은 남긴다 — 사용자가 자기 프로젝트를
    파일 탐색기에서 알아볼 수 있어야 한다.
    """
    normalized = unicodedata.normalize("NFC", name).strip()
    # 제어 문자 제거. 파일 이름에 들어가면 도구마다 다르게 깨진다.
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch)[0] != "C")
    slug = _UNSAFE.sub("-", normalized).strip("-.")

    # "." 과 ".." 는 디렉터리 이름으로 쓸 수 없다. 위 치환을 통과할 수 있어 따로 막는다.
    if slug in {"", ".", ".."}:
        return "project"
    return slug[:80]


def allocate_workspace_path(name: str, root: pathlib.Path | None = None) -> pathlib.Path:
    """관리 위치에서 아직 쓰이지 않은 디렉터리를 고른다.

    이름이 겹치면 ``-2``·``-3`` 을 붙인다. **``PROJECT_ALREADY_EXISTS`` 를 내지 않는다** —
    사용자가 위치를 모르는데 위치 충돌로 실패시킬 수 없다 (contracts/rest-api-delta.md §2).
    """
    base = (root or workspace_dir()).expanduser()
    slug = slugify(name)

    candidate = base / slug
    suffix = 2
    while candidate.exists():
        candidate = base / f"{slug}-{suffix}"
        suffix += 1
    return candidate


def allocate_trash_path(
    root: pathlib.Path, *, when: dt.datetime | None = None, base: pathlib.Path | None = None
) -> pathlib.Path:
    """휴지통에서 아직 쓰이지 않은 자리를 고른다 (012 FR-415).

        <trash_dir>/<YYYYMMDD-HHMMSS>-<원래 디렉터리 이름>

    **시각 접두사가 충돌 회피와 기록을 동시에 한다.** 사용자가 휴지통을 열었을 때 언제
    지운 어느 프로젝트인지가 디렉터리 이름만으로 읽힌다. 그래도 같은 초에 두 번 지우는
    일이 가능하므로 ``-2``·``-3`` 을 붙여 피한다 — ``allocate_workspace_path`` 와 같은
    규칙이다. **덮어쓰지 않는 것이 요점이다**: 먼저 지운 사람의 테스트 정의가 나중 삭제에
    사라지면 이 기능이 지키려던 것이 무너진다.

    표시 이름이 아니라 **원래 디렉터리 이름**을 쓴다. 표시 이름에는 경로 구분자가 들어갈
    수 있고, 그것을 파일명에 넣으면 경로가 갈라진다. 디렉터리 이름은 이미 :func:`slugify`
    를 지난 값이다.
    """
    stamp = (when or dt.datetime.now(dt.UTC)).strftime("%Y%m%d-%H%M%S")
    parent = (base or trash_dir()).expanduser()
    label = f"{stamp}-{root.name}" if root.name else stamp

    candidate = parent / label
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{label}-{suffix}"
        suffix += 1
    return candidate
