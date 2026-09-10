"""삭제된 프로젝트를 옮겨 두는 곳. 012 FR-409·FR-414·FR-415·FR-420.

**삭제는 파괴가 아니라 이동이다.** `tests/*.yaml` 은 사용자가 버전 관리에 넣도록 만든
평문 자산이고(헌법 원칙 V), 그것을 도구가 되돌릴 수 없게 지우는 경로를 만들지 않는다.
목록에서 사라지되 되찾을 수 있어야 한다.

`ProjectRepository` 에 넣지 않은 이유는 그 객체가 **열린 프로젝트 하나의 안쪽**을 다루기
때문이다. 프로젝트 디렉터리 자체를 옮기는 일은 그 바깥이며, `paths.py`·`atomic.py` 와
같은 층이다 (plan.md Structure Decision).
"""

from __future__ import annotations

import contextlib
import pathlib
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

from itb.storage.paths import allocate_trash_path

if TYPE_CHECKING:  # pragma: no cover — 순환 임포트를 피한다
    from itb.storage.repository import ProjectRepository


class TrashError(OSError):
    """휴지통으로 옮기지 못했다.

    `OSError` 를 상속한다 — 호출부가 이미 `OSError` 를 다루고 있으면 그대로 걸린다.
    `atomic.StorageWriteError` 와 같은 관례다.
    """


def move_to_trash(root: pathlib.Path) -> pathlib.Path | None:
    """프로젝트 디렉터리를 통째로 휴지통으로 옮기고, 옮겨진 자리를 돌려준다.

    **이미 없으면 `None` 이다** (FR-420). 지우려는 순간 디렉터리가 없는 것은 실패가
    아니다 — 사용자가 원한 결과가 이미 이루어져 있다. 호출부는 목록에서 빼는 것으로
    끝내면 된다.

    **실패하면 원본이 그대로 남는다** (FR-414). 이 성질이 이 함수의 계약에서 가장 중요한
    부분이다. 목록에서는 사라졌는데 자산은 원래 자리에 남는 상태를 만들지 않으려면
    호출부가 "옮기기 성공 뒤에 레지스트리" 순서를 지켜야 하고, 그 전제가 여기서 선다.

    `shutil.move` 를 쓰는 이유는 **다른 볼륨**이다 (research R4). 외부 위치 프로젝트는
    다른 디스크에 있을 수 있고, 그때 `os.rename` 은 `EXDEV` 로 실패한다. `shutil.move`
    는 같은 볼륨이면 `os.rename`(원자적), 다르면 복사 후 원본 삭제로 분기한다.

    다른 볼륨에서 복사 도중 실패하면 **목적지에 반쪽이 남는다.** 원본이 남는 것이 더
    중요하므로 그 실패 모드는 받아들이고, 목적지의 반쪽만 치운다. 치우기가 또 실패해도
    원래 예외를 덮지 않는다 — `atomic.write_text` 가 임시 파일에 대해 하는 것과 같다.
    """
    root = pathlib.Path(root)
    if not root.exists():
        return None

    destination = allocate_trash_path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.move(str(root), str(destination))
    except OSError as exc:
        # 반쪽 결과를 남기지 않는다. 원본은 건드리지 않는다.
        with contextlib.suppress(OSError):
            if destination.is_dir():
                shutil.rmtree(destination)
            elif destination.exists():
                destination.unlink()
        msg = f"프로젝트를 휴지통으로 옮기지 못했습니다: {exc.strerror or exc}"
        raise TrashError(msg) from exc

    return destination


# ─── 테스트 하나 (013 FR-437) ───────────────────────────────────────────────

TRASHED_DEFINITION_DIR = "runs"
"""휴지통 항목 안에서 실행 산출물이 앉는 자리. **이름이 고정이어야** 되돌리는 사람이
어디로 보낼지 안다."""


@dataclass(frozen=True, slots=True)
class TrashedTest:
    """휴지통으로 간 테스트 하나 (013 data-model §4)."""

    test_id: str
    entry: pathlib.Path
    """항목 디렉터리. **사용자에게 알리는 값이 이것이다** — 되돌리는 방법 전부다."""

    definition: pathlib.Path
    """항목 안의 정의 파일. **원래 파일명 그대로다.**"""


def move_test_to_trash(repo: ProjectRepository, test_id: str) -> TrashedTest:
    """테스트 하나를 휴지통으로 옮긴다 (013 FR-437).

        <trash_dir>/<시각>-<ID>-<이름>/
        ├── <ID>-<이름>.yaml    ← 원래 파일명 그대로
        └── runs/               ← .runs/<ID>/ 의 내용 (있을 때만)

    **원래 파일명을 그대로 두는 것이 요점이다.** 되돌리기가 「이 `.yaml` 을 프로젝트의
    `tests/` 로 옮긴다」한 걸음이 된다. 이름을 바꿔 두면 사용자가 원래 이름을 알아내야
    한다 (013 research R6).

    정의 파일이 없으면 :class:`TrashError` 다 — 호출자가 먼저 검증했어야 한다.
    """
    definition = repo.find_test_path(test_id)
    if definition is None:
        msg = f"테스트 정의를 찾을 수 없습니다: {test_id}"
        raise TrashError(msg)

    entry = allocate_trash_path(pathlib.Path(test_id))
    entry.mkdir(parents=True, exist_ok=True)

    moved_definition = entry / definition.name
    runs = repo.paths.run_dir(test_id)
    moved_runs = entry / TRASHED_DEFINITION_DIR

    try:
        # 산출물이 먼저다. 정의가 먼저 옮겨진 뒤 산출물이 실패하면, 되돌렸을 때
        # 「테스트는 돌아왔는데 결과가 사라진」 상태가 잠깐이라도 생긴다.
        if runs.is_dir():
            shutil.move(str(runs), str(moved_runs))
        shutil.move(str(definition), str(moved_definition))
    except OSError as exc:
        with contextlib.suppress(OSError):
            if moved_runs.is_dir():
                shutil.move(str(moved_runs), str(runs))
            if entry.is_dir() and not any(entry.iterdir()):
                entry.rmdir()
        msg = f"테스트를 휴지통으로 옮기지 못했습니다: {exc.strerror or exc}"
        raise TrashError(msg) from exc

    return TrashedTest(test_id=test_id, entry=entry, definition=moved_definition)


def restore_test(repo: ProjectRepository, trashed: TrashedTest) -> None:
    """휴지통 항목을 원래 자리로 되돌린다 (013 T016).

    **사용자용 복구 조작이 아니다.** 복수 삭제가 도중에 실패했을 때 이미 옮긴 것을
    되돌리는 용도다 (`storage/test_moves.py` 의 3번 걸음). 사용자는 파일 탐색기로
    되돌린다 — 도구는 휴지통을 읽지 않는다.

    되돌리는 순서는 옮기는 순서의 **역순**이다: 정의가 먼저 제자리로 가야, 도중에 실패해도
    「정의는 있는데 결과가 휴지통에」가 되고 그 반대가 되지 않는다.
    """
    repo.paths.tests_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(trashed.definition), str(repo.paths.tests_dir / trashed.definition.name))

    moved_runs = trashed.entry / TRASHED_DEFINITION_DIR
    if moved_runs.is_dir():
        runs = repo.paths.run_dir(trashed.test_id)
        runs.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(moved_runs), str(runs))

    with contextlib.suppress(OSError):
        if not any(trashed.entry.iterdir()):
            trashed.entry.rmdir()
