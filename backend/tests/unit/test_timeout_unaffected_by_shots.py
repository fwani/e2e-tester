"""촬영이 Step 실행 시간에 들어가지 않는다. 011 FR-395 · SC-611.

## 왜 이 검사가 필요한가

Step 별 화면 촬영은 수백 ms 가 걸릴 수 있다. 그것이 `duration_ms` 에 들어가면 **시간 초과
판정이 바뀐다** — 011 이전에 통과하던 테스트가 느려졌다는 이유로 실패한다. 기능을 하나
더하면서 기존 결말을 흔드는 것이 이 기능에서 가장 비싼 실패다.

## 무엇으로 고정하는가

성질을 지키는 것은 **호출 순서 하나**다 — 촬영은 `result.duration_ms = …` 아래에서 불린다.
순서는 다음 사람이 줄을 옮기면 조용히 깨지므로, 「촬영이 오래 걸려도 `duration_ms` 가
늘지 않는다」를 직접 잰다.

시간을 재는 검사이므로 `timing` 계층이다 (`tests/tiers.py`) — 프로세스 8개가 CPU 를 나눠
쓰면 재는 값이 제품의 성질이 아니라 그 순간의 부하가 된다.
"""

from __future__ import annotations

import asyncio
import pathlib
import re
from typing import Any

import pytest

from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import ClickStep
from itb.domain.test_case import Test
from itb.execution.artifacts import ArtifactCollector
from itb.execution.runner import ReplayEngine

SHOT_DELAY = 0.25
"""촬영이 걸리는 시간. `duration_ms` 에 들어가면 250ms 가 더해진다 — 눈에 띄는 크기다."""


def _target() -> TargetLocator:
    return TargetLocator(css=Candidate(value="#a", status=CandidateStatus.VERIFIED))


class _SlowPage:
    """촬영이 **느린** 화면. 이 지연이 어디로 가는지가 이 검사의 대상이다."""

    async def screenshot(self, **_kwargs: Any) -> bytes:
        await asyncio.sleep(SHOT_DELAY)
        return b"\x89PNG\r\n\x1a\n" + b"0" * 16


class _Tab:
    closed = False

    def __init__(self) -> None:
        self.page = _SlowPage()


class _Session:
    session_id = "s-1"

    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict[str, Any]]] = []

    def find_tab(self, _index: int) -> _Tab:
        return _Tab()

    def open_tabs(self) -> list[_Tab]:
        return [_Tab()]

    async def emit(self, event_type: str, **payload: Any) -> None:
        self.emitted.append((event_type, payload))


class _Executor:
    """즉시 끝나는 실행기. Step 자체는 빠르고 **촬영만 느리다.**"""

    async def execute(self, _step: Any) -> Any:
        class _Record:
            tab_wait_ms = 0
            element_wait_ms = 0
            attempts: list[Any] = []
            resolved_candidate = "css"
            disagreement: list[str] = []

        return _Record()


class _Resolver:
    def resolved_sensitive_values(self) -> list[str]:
        return []


class _Context:
    def on(self, *_a: Any, **_k: Any) -> None:
        return None


@pytest.mark.timing
@pytest.mark.anyio
async def test_screenshot_time_stays_out_of_duration(tmp_path: pathlib.Path) -> None:
    """촬영이 250ms 걸려도 `duration_ms` 는 그것을 담지 않는다.

    **여유를 크게 두지 않는다.** 지연의 절반(125ms)만 넘어도 실패하게 하면, 촬영이
    `duration_ms` 안으로 들어간 순간 잡힌다.
    """
    session = _Session()
    engine = ReplayEngine(
        session=session,  # type: ignore[arg-type]
        test=Test(
            id="TC-001",
            name="로그인",
            authoring_mode="record",
            start_url="http://127.0.0.1:1/",
            steps=[ClickStep(id="step-01", label="하나", target=_target())],
        ),
        executor=_Executor(),  # type: ignore[arg-type]
        resolver=_Resolver(),  # type: ignore[arg-type]
        collector=ArtifactCollector(_Context()),  # type: ignore[arg-type]
        run_dir=tmp_path / ".runs" / "TC-001",
        project_root=tmp_path,
        write_result=lambda _r: None,
    )

    assert await engine.run_step(session, 0) is True  # type: ignore[arg-type]

    result = engine.results[0]
    # 촬영은 실제로 일어났다 — 아무것도 안 찍고 통과한 것이 아니다.
    assert result.screenshot is not None, "촬영이 일어나지 않아 이 검사가 무의미하다"
    assert result.duration_ms < SHOT_DELAY * 1000 / 2, (
        f"촬영 시간이 duration_ms 에 들어갔다: {result.duration_ms}ms "
        f"(촬영 {int(SHOT_DELAY * 1000)}ms)"
    )


@pytest.mark.timing
@pytest.mark.anyio
async def test_emitted_duration_matches_the_result(tmp_path: pathlib.Path) -> None:
    """이벤트로 나가는 값도 같다 — 화면이 결과 파일과 다른 시간을 보면 안 된다."""
    session = _Session()
    engine = ReplayEngine(
        session=session,  # type: ignore[arg-type]
        test=Test(
            id="TC-001",
            name="로그인",
            authoring_mode="record",
            start_url="http://127.0.0.1:1/",
            steps=[ClickStep(id="step-01", label="하나", target=_target())],
        ),
        executor=_Executor(),  # type: ignore[arg-type]
        resolver=_Resolver(),  # type: ignore[arg-type]
        collector=ArtifactCollector(_Context()),  # type: ignore[arg-type]
        run_dir=tmp_path / ".runs" / "TC-001",
        project_root=tmp_path,
        write_result=lambda _r: None,
    )
    await engine.run_step(session, 0)  # type: ignore[arg-type]

    finished = [p for t, p in session.emitted if t == "step_finished"]
    assert len(finished) == 1
    assert finished[0]["duration_ms"] == engine.results[0].duration_ms


def test_this_module_is_in_the_timing_tier() -> None:
    """시간을 재는 검사는 순차 계층에 있어야 한다 (`tests/tiers.py` 의 `TIMING_MODULES`).

    병렬로 돌면 재는 값이 그 순간의 부하가 되고, 이 검사는 조용히 흔들린다.
    """
    tiers = (pathlib.Path(__file__).parent.parent / "tiers.py").read_text(encoding="utf-8")
    assert re.search(r"test_timeout_unaffected_by_shots", tiers), (
        "이 모듈을 tests/tiers.py 의 TIMING_MODULES 에 등록하라"
    )
