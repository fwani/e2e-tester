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

import os
import pathlib
import re
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
