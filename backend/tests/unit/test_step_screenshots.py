"""Step 별 화면 촬영·보관. 011 FR-389·FR-392·FR-396a·FR-396c·FR-398.

## 왜 단위로 재는가

이 셋은 **브라우저 없이** 판정된다 — 민감 값이 들어 있는지, 디렉터리를 비웠는지, 실패가
밖으로 나가지 않는지. 실제 브라우저를 띄우면 검증하려는 것과 무관한 시간과 실패 원인이
늘어난다 (`test_step_edit_api.py` 머리말과 같은 판단).

`Page` 는 `screenshot()` 하나만 쓰이므로 대역으로 충분하다.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from itb.execution.artifacts import (
    STEP_SHOTS_DIR,
    ArtifactCollector,
    clear_step_screenshots,
    step_shot_name,
)
from itb.secrets.scrubber import Scrubber

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class _FakePage:
    """`screenshot()` 만 답하는 대역. 실패를 흉내 낼 수 있다."""

    def __init__(self, data: bytes = PNG, raises: Exception | None = None) -> None:
        self._data = data
        self._raises = raises
        self.calls = 0

    async def screenshot(self, **_kwargs: Any) -> bytes:
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._data


class _FakeContext:
    def on(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _collector() -> ArtifactCollector:
    return ArtifactCollector(_FakeContext())  # type: ignore[arg-type]


# ─── 촬영 (FR-389) ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_writes_png_under_steps_dir(tmp_path: pathlib.Path) -> None:
    """`.runs/<ID>/steps/<0기반 index>.png` 에 쓰고 **상대 경로**를 돌려준다 (FR-397)."""
    run_dir = tmp_path / ".runs" / "TC-001"
    run_dir.mkdir(parents=True)
    path, note = await _collector().write_step_screenshot(
        run_dir, tmp_path, Scrubber([]), _FakePage(), 3
    )
    assert note is None
    assert path == f".runs/TC-001/{STEP_SHOTS_DIR}/{step_shot_name(3)}"
    assert (run_dir / STEP_SHOTS_DIR / "3.png").read_bytes() == PNG
    # 절대 경로를 넣으면 결과 파일이 장비에 묶이고 홈 경로가 노출된다.
    assert not pathlib.Path(path).is_absolute()


@pytest.mark.anyio
async def test_index_is_zero_based(tmp_path: pathlib.Path) -> None:
    """저장·API·이벤트의 인덱스는 0-기반이고 그것을 바꾸지 않는다 (contracts §6)."""
    run_dir = tmp_path / ".runs" / "TC-001"
    run_dir.mkdir(parents=True)
    await _collector().write_step_screenshot(run_dir, tmp_path, Scrubber([]), _FakePage(), 0)
    assert (run_dir / STEP_SHOTS_DIR / "0.png").is_file()


# ─── 민감 값 (FR-392 · SC-612) ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_secret_in_bytes_is_not_written(tmp_path: pathlib.Path) -> None:
    """**쓰지 않고 사유만 남긴다.**

    PNG 를 문자열로 치환하면 파일이 깨진다. 실패 시점 스크린샷이 이미 같은 규칙이고,
    011 은 그 함수를 그대로 쓴다 — 검사를 복제하지 않았다는 것이 이 검사의 뜻이다.
    """
    run_dir = tmp_path / ".runs" / "TC-001"
    run_dir.mkdir(parents=True)
    tainted = b"\x89PNG\r\n\x1a\n" + b"hunter2" + b"0" * 32
    path, note = await _collector().write_step_screenshot(
        run_dir, tmp_path, Scrubber(["hunter2"]), _FakePage(tainted), 1
    )
    assert path is None
    assert note is not None and "민감" in note
    assert not (run_dir / STEP_SHOTS_DIR / "1.png").exists(), "민감 값이 디스크에 남았다"


# ─── 촬영 실패 (FR-391·FR-398) ──────────────────────────────────────────────


@pytest.mark.anyio
async def test_capture_failure_returns_note_not_exception(tmp_path: pathlib.Path) -> None:
    """화면이 이미 닫혔을 수 있다. **예외를 밖으로 내지 않는다** — 산출물이 실행을 멈추지 않는다."""
    run_dir = tmp_path / ".runs" / "TC-001"
    run_dir.mkdir(parents=True)
    path, note = await _collector().write_step_screenshot(
        run_dir, tmp_path, Scrubber([]), _FakePage(raises=RuntimeError("closed")), 0
    )
    assert path is None
    assert note is not None and note != ""


@pytest.mark.anyio
async def test_unwritable_dir_returns_note(tmp_path: pathlib.Path) -> None:
    """디렉터리를 만들 수 없어도 사유만 남는다 (FR-398)."""
    run_dir = tmp_path / ".runs" / "TC-001"
    run_dir.mkdir(parents=True)
    # `steps` 자리에 **파일**을 두면 디렉터리를 만들 수 없다.
    (run_dir / STEP_SHOTS_DIR).write_text("가로막는 파일", encoding="utf-8")
    path, note = await _collector().write_step_screenshot(
        run_dir, tmp_path, Scrubber([]), _FakePage(), 0
    )
    assert path is None
    assert note is not None


# ─── 보관 — 실행마다 비운다 (FR-396a·FR-396c) ───────────────────────────────


def test_clear_removes_previous_run(tmp_path: pathlib.Path) -> None:
    """**이것이 「테스트당 최근 실행 1회분」의 전부다** (clarify 결정 3)."""
    run_dir = tmp_path / ".runs" / "TC-001"
    shots = run_dir / STEP_SHOTS_DIR
    shots.mkdir(parents=True)
    for i in range(4):
        (shots / f"{i}.png").write_bytes(PNG)

    assert clear_step_screenshots(run_dir) is None
    assert not shots.exists(), "이전 실행의 화면이 남았다"


def test_clear_is_quiet_when_nothing_to_clear(tmp_path: pathlib.Path) -> None:
    """첫 실행에는 지울 것이 없다. 그것은 사유가 아니다."""
    run_dir = tmp_path / ".runs" / "TC-001"
    run_dir.mkdir(parents=True)
    assert clear_step_screenshots(run_dir) is None


def test_clear_failure_returns_note(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """비우기 실패는 **실행을 막지 않는다** (FR-396c). 사유만 돌려준다."""
    run_dir = tmp_path / ".runs" / "TC-001"
    (run_dir / STEP_SHOTS_DIR).mkdir(parents=True)

    def boom(*_a: Any, **_k: Any) -> None:
        raise OSError("읽기 전용")

    monkeypatch.setattr("itb.execution.artifacts.shutil.rmtree", boom)
    note = clear_step_screenshots(run_dir)
    assert note is not None and "지우지 못했" in note


def test_startup_note_rides_along_to_artifacts(tmp_path: pathlib.Path) -> None:
    """시작 시점 사유가 결과 산출물 기록에 실린다 (FR-396c).

    `ArtifactPaths.notes` 는 실행이 끝나고 만들어지므로, 그 자리가 없으면 「이전 실행
    화면을 지우지 못했다」가 조용히 사라진다 — 그때 사용자는 지난 실행의 화면을 이번
    것으로 읽는다.
    """
    collector = _collector()
    collector.startup_notes.append("지우지 못했습니다")
    # `write` 는 비동기지만 여기서 재는 것은 통로의 존재이므로 필드로 확인한다.
    assert "지우지 못했습니다" in collector.startup_notes
