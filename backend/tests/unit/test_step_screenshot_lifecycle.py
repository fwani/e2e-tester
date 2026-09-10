"""Step 화면의 생애 — 실행 시작에 비우고, 실패 Step 은 파일을 나눠 쓴다.

011 FR-394·FR-396a · data-model.md §4-2.

## 왜 브라우저 없이 재는가

여기서 재는 셋은 **브라우저를 지나지 않는다.**

- 실행 시작에 `steps/` 를 비우는 것은 엔진이 만들어질 때 일어난다
- 실패 Step 이 `failure.png` 를 가리키는 것은 결과를 조립할 때 일어난다
- 실행하지 않은 Step 이 경로도 사유도 갖지 않는 것은 초기값이다

실제 재생은 브라우저 계층(`-m browser`)이 돈다. 이 파일은 그 계층이 확인할 수 없는 것 —
**파일이 언제 사라지는가** — 을 맡는다.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep
from itb.domain.test_case import Test
from itb.execution.artifacts import STEP_SHOTS_DIR, ArtifactCollector, ArtifactPaths
from itb.execution.runner import ReplayEngine

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16


def _target() -> TargetLocator:
    return TargetLocator(css=Candidate(value="#a", status=CandidateStatus.VERIFIED))


def _test(n: int) -> Test:
    return Test(
        id="TC-001",
        name="로그인",
        authoring_mode="record",
        start_url="http://127.0.0.1:1/",
        steps=[
            ClickStep(id=f"step-{i + 1:02d}", label=f"Step {i + 1}", target=_target())
            for i in range(n)
        ],
    )


class _FakeSession:
    session_id = "s-1"

    def find_tab(self, _index: int) -> None:
        return None

    def open_tabs(self) -> list[object]:
        return []


class _FakeContext:
    def on(self, *_a: Any, **_k: Any) -> None:
        return None


def _engine(run_dir: pathlib.Path, root: pathlib.Path, steps: int = 3) -> ReplayEngine:
    class _FakeResolver:
        def resolved_sensitive_values(self) -> list[str]:
            return []

    return ReplayEngine(
        session=_FakeSession(),  # type: ignore[arg-type]
        test=_test(steps),
        executor=None,  # type: ignore[arg-type]
        resolver=_FakeResolver(),  # type: ignore[arg-type]
        collector=ArtifactCollector(_FakeContext()),  # type: ignore[arg-type]
        run_dir=run_dir,
        project_root=root,
        write_result=lambda _r: None,
    )


# ─── 실행 시작에 비운다 (FR-396a) ───────────────────────────────────────────


def test_engine_clears_previous_run_shots(tmp_path: pathlib.Path) -> None:
    """**엔진이 만들어질 때가 실행의 시작이다.**

    `run_step` 안에서 「첫 번째인가」를 따로 들고 비우면 이어서 실행(`start_index > 0`)에서
    그 판정이 틀린다 — 그때 비우면 이미 통과한 Step 의 화면이 사라진다.
    """
    run_dir = tmp_path / ".runs" / "TC-001"
    shots = run_dir / STEP_SHOTS_DIR
    shots.mkdir(parents=True)
    for i in range(5):
        (shots / f"{i}.png").write_bytes(PNG)

    _engine(run_dir, tmp_path)
    assert not shots.exists(), "이전 실행의 화면이 남았다"


def test_shrinking_a_test_leaves_no_orphan_shots(tmp_path: pathlib.Path) -> None:
    """Step 을 줄여 다시 돌리면 높은 인덱스 파일이 남으면 안 된다.

    **덮어쓰기로는 부족하다는 것이 이 검사의 뜻이다.** 5개짜리 실행 뒤 2개짜리로 돌리면
    `3.png`·`4.png` 가 남아, 사용자는 지금 실행에 없는 화면을 보게 된다.
    """
    run_dir = tmp_path / ".runs" / "TC-001"
    shots = run_dir / STEP_SHOTS_DIR
    shots.mkdir(parents=True)
    for i in range(5):
        (shots / f"{i}.png").write_bytes(PNG)

    _engine(run_dir, tmp_path, steps=2)
    assert not shots.exists()


def test_clear_failure_becomes_an_artifact_note(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """비우지 못해도 **엔진은 만들어진다** (FR-396c). 사유는 산출물 기록으로 간다."""
    run_dir = tmp_path / ".runs" / "TC-001"
    (run_dir / STEP_SHOTS_DIR).mkdir(parents=True)

    def boom(*_a: Any, **_k: Any) -> None:
        raise OSError("읽기 전용")

    monkeypatch.setattr("itb.execution.artifacts.shutil.rmtree", boom)
    engine = _engine(run_dir, tmp_path)
    assert engine.collector.startup_notes, "사유가 조용히 사라졌다"


# ─── 실행하지 않은 Step (FR-393) ────────────────────────────────────────────


def test_unrun_steps_have_neither_path_nor_reason(tmp_path: pathlib.Path) -> None:
    """찍지 못한 것이 아니라 **찍을 일이 없었다.** 사유를 남기면 결함으로 읽힌다."""
    engine = _engine(tmp_path / ".runs" / "TC-001", tmp_path)
    for result in engine.results:
        assert result.screenshot is None
        assert result.screenshot_note is None


# ─── 실패 Step 은 파일을 나눠 쓴다 (FR-394) ─────────────────────────────────


def test_failed_step_points_at_the_failure_shot(tmp_path: pathlib.Path) -> None:
    """같은 화면을 두 벌 저장하지 않는다.

    실패 시점 스크린샷은 011 이전부터 있었고, Step 별 화면을 더하면서 실패한 Step 만 두 번
    찍힐 수 있게 됐다. 경로를 나눠 쓰면 파일은 한 벌이다.
    """
    engine = _engine(tmp_path / ".runs" / "TC-001", tmp_path)
    engine.failed_index = 1
    artifacts = ArtifactPaths(failure_screenshot=".runs/TC-001/failure.png")

    engine._share_failure_screenshot(artifacts)

    assert engine.results[1].screenshot == ".runs/TC-001/failure.png"
    assert engine.results[1].screenshot_note is None
    # 다른 Step 은 건드리지 않는다.
    assert engine.results[0].screenshot is None


def test_step_shot_wins_when_it_exists(tmp_path: pathlib.Path) -> None:
    """Step 촬영이 이미 성공했으면 그것을 그대로 둔다 — 그 화면이 그 Step 의 것이다."""
    engine = _engine(tmp_path / ".runs" / "TC-001", tmp_path)
    engine.failed_index = 1
    engine.results[1].screenshot = ".runs/TC-001/steps/1.png"

    engine._share_failure_screenshot(ArtifactPaths(failure_screenshot=".runs/TC-001/failure.png"))
    assert engine.results[1].screenshot == ".runs/TC-001/steps/1.png"


def test_nothing_to_share_when_the_run_passed(tmp_path: pathlib.Path) -> None:
    """통과한 실행에는 실패 시점 스크린샷이 없다."""
    engine = _engine(tmp_path / ".runs" / "TC-001", tmp_path)
    engine._share_failure_screenshot(ArtifactPaths())
    assert all(r.screenshot is None for r in engine.results)
