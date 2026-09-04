"""디렉터리 탐색. DR-005. contracts/rest-api-delta.md §4.

**왜 서버가 탐색기를 그리는가**: 브라우저는 임의 절대 경로를 줄 수 없다.
`<input type="file" webkitdirectory>` 는 상대 경로만 주고, File System Access API 는
핸들만 주며 서버가 읽을 경로가 되지 않는다. 서버가 로컬에 있으므로(001 FR-088) 서버가
디렉터리를 읽어 목록을 주는 것이 유일하게 성립하는 방법이다 (research R4).

**이 엔드포인트는 이번 라운드가 여는 유일한 새 공격면이다.** 그래서 좁게 만든다.

- 사용자 홈 아래로 한정. `resolve()` 후 판정하므로 `..` 와 심볼릭 링크로 넘을 수 없다
- **디렉터리 이름만 반환한다.** 파일 이름조차 주지 않는다 — 탐색기가 파일 유출 통로가
  되면 안 된다
- 숨김 디렉터리 제외 — `.ssh` 노출과 목록 소음을 함께 막는다
- 읽기 권한이 없으면 사유와 함께 거절. 조용한 빈 목록은 진단할 수 없다
"""

from __future__ import annotations

import pathlib
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from itb.api.errors import ErrorCode, bad_request
from itb.storage.paths import PathOutsideHomeError, home_root, resolve_within_home
from itb.storage.repository import PROJECT_FILE

router = APIRouter(prefix="/api/fs", tags=["fs"])


class DirectoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    is_project: bool
    """유효한 프로젝트 구조인가. 사용자가 어디를 골라야 하는지 알려 준다."""


class BrowseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    parent: str | None
    """홈 최상위에서는 `null`. 경계 밖으로 올라가는 조작을 화면에서부터 막는다."""

    entries: list[DirectoryEntry]


@router.get("/browse")
async def browse(
    path: Annotated[str | None, Query(max_length=4096)] = None,
) -> BrowseResponse:
    """홈 하위 디렉터리 목록. 경로를 생략하면 사용자 홈."""
    home = home_root()
    target = home if path is None else _checked(path)

    if not target.is_dir():
        raise bad_request(
            ErrorCode.INVALID_PATH, f"디렉터리가 아닙니다: {target.name}"
        )

    try:
        children = sorted(target.iterdir(), key=lambda p: p.name.lower())
    except PermissionError as exc:
        raise bad_request(
            ErrorCode.INVALID_PATH,
            f"'{target.name}' 을 읽을 권한이 없습니다. 다른 위치를 고르세요.",
        ) from exc
    except OSError as exc:
        raise bad_request(
            ErrorCode.INVALID_PATH, f"'{target.name}' 을 열 수 없습니다."
        ) from exc

    entries: list[DirectoryEntry] = []
    for child in children:
        # 파일은 목록에 넣지 않는다. 이름조차 주지 않는다.
        if child.name.startswith(".") or not _is_visible_dir(child):
            continue
        entries.append(
            DirectoryEntry(
                name=child.name,
                path=str(child),
                is_project=(child / PROJECT_FILE).exists(),
            )
        )

    return BrowseResponse(
        path=str(target),
        parent=str(target.parent) if target != home else None,
        entries=entries,
    )


def _checked(raw: str) -> pathlib.Path:
    try:
        return resolve_within_home(raw)
    except PathOutsideHomeError as exc:
        raise bad_request(ErrorCode.INVALID_PATH, str(exc)) from exc


def _is_visible_dir(child: pathlib.Path) -> bool:
    """디렉터리인가. 심볼릭 링크가 홈 밖을 가리키면 목록에 넣지 않는다.

    `is_dir()` 은 링크를 따라가므로 그것만으로는 경계를 지키지 못한다. 목록에 넣어 두면
    사용자가 그것을 눌러 경계 밖을 열려 시도하게 되고, 그 요청은 거절되지만 애초에
    보여주지 않는 편이 낫다.
    """
    try:
        if not child.is_dir():
            return False
        if child.is_symlink():
            resolve_within_home(child)
    except PathOutsideHomeError:
        return False
    except OSError:
        return False
    return True
