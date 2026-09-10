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

from itb.storage.paths import allocate_trash_path


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
