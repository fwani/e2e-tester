"""원자적 파일 쓰기. 003 AP-042 · AS-049 · AS-050.

저장이 도중에 끊겨도 **자산 파일이 일부만 쓰인 상태로 남아서는 안 된다.** 곧바로 덮어쓰는
방식은 그것을 보장할 수 없다 — 쓰기가 중간에 끊기면 원본 자리에 반쪽짜리 파일이 남고,
사용자는 앞서 만든 테스트 정의나 봉인한 비밀 값을 잃는다.

이 방식은 이미 `registry.py` 안에 있었다. 거기서만 쓰이고 있었을 뿐이다 — 테스트 정의를
쓰는 `yaml_io.dump_model()` 도, 비밀 값 저장소도 곧바로 덮어쓰고 있었다. 같은 규칙을
서로 다른 파일이 각자 지키게 두면 한 곳이 빠지고, 빠진 곳은 사고가 나야 드러난다.

**임시 파일은 같은 디렉터리에 만든다.** 다른 파일 시스템에 만들면 `replace` 가 원자적이지
않다. 실패하면 임시 파일을 치우고 원래 예외를 그대로 올린다 — 호출자가 무엇이 일어났는지
알아야 한다.
"""

from __future__ import annotations

import contextlib
import os
import pathlib

SUFFIX = ".itbtmp"
"""임시 파일 표시. 원본 확장자를 유지하지 않는다 — 목록 훑기가 반쪽 파일을 정식 자산으로
읽는 일이 없어야 한다."""


class StorageWriteError(OSError):
    """파일을 안전하게 쓰지 못했다.

    `OSError` 를 상속한다 — 호출부가 이미 `OSError` 를 다루고 있으면 그대로 걸린다.
    """


def write_text(
    path: pathlib.Path,
    text: str,
    *,
    encoding: str = "utf-8",
    mode: int | None = None,
) -> None:
    """텍스트를 원자적으로 쓴다.

    쓰기가 도중에 끊기면 **원본은 그대로 남는다.** 반쪽 내용은 임시 파일에만 있고, 그
    임시 파일도 치운다.

    `mode` 를 주면 바꿔치기 **전에** 권한을 건다 — 뒤에 걸면 그 사이에 파일이 넓은
    권한으로 존재하는 순간이 생긴다.
    """
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}{SUFFIX}")

    try:
        with tmp.open("w", encoding=encoding) as fh:
            fh.write(text)
            fh.flush()
            # 내용이 디스크에 닿기 전에 바꿔치기하면, 이름은 새 파일인데 내용은 비어
            # 있는 상태가 정전 뒤에 남을 수 있다.
            os.fsync(fh.fileno())
        if mode is not None:
            tmp.chmod(mode)
        tmp.replace(path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def write_bytes(path: pathlib.Path, data: bytes, *, mode: int | None = None) -> None:
    """바이트를 원자적으로 쓴다. 규칙은 :func:`write_text` 와 같다."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}{SUFFIX}")

    try:
        with tmp.open("wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if mode is not None:
            tmp.chmod(mode)
        tmp.replace(path)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
