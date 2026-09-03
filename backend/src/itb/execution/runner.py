"""러너 태스크. 헌법 원칙 III.

세션마다 하나의 `asyncio.Task` 가 Step 을 순차 실행한다. HTTP 요청은 명령을 적용하고 즉시
반환하며, 실제 실행은 이 태스크가 담당한다 — 그래야 브라우저 수명이 요청 수명과 분리된다.

**Pause 는 태스크가 `asyncio.Event` 를 await 하는 것이다.** 브라우저에는 아무 명령도 보내지
않는다. 이 파일에 상태 저장·복원 로직이 없는 이유다 (research R1, T003 으로 실측 확인).
"""

from __future__ import annotations

import asyncio
import contextlib
import pathlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from playwright.async_api import Page

from itb.domain.run_result import (
    Artifacts,
    Outcome,
    RunResult,
    StepOutcome,
    StepResult,
)
from itb.domain.test_case import Test
from itb.execution.artifacts import ArtifactCollector, ArtifactPaths
from itb.execution.session import BrowserSession
from itb.execution.state_machine import Command, SessionState
from itb.execution.step_executor import StepExecutor, StepFailure
from itb.secrets.resolver import VariableResolver
from itb.secrets.scrubber import Scrubber

StepRunner = Callable[[BrowserSession, int], Awaitable[bool]]
"""Step 하나를 실행한다. (session, step_index) → 계속 진행할지 여부."""

ResultWriter = Callable[[RunResult], object]
"""실행 결과를 보관한다. 저장 계층을 주입받아 엔진이 파일 경로를 몰라도 되게 한다."""

RunCompletion = Callable[[bool], Awaitable[None]]
"""실행이 끝났을 때 한 번 호출된다. 인자는 전체 통과 여부.

**취소된 경우에는 호출되지 않는다.** 취소는 사용자가 중지한 것이고, 중지된 실행의 결과를
"실패한 실행"으로 기록하면 목록 화면에 없던 실패가 생긴다.
"""


class RunnerTask:
    """세션 하나의 실행 태스크.

    Step 실행 자체는 주입받은 `StepRunner` 가 담당한다 — 이 클래스는 **진행·일시정지·취소**만
    책임진다. 그래서 브라우저 없이 테스트할 수 있다.
    """

    def __init__(
        self,
        session: BrowserSession,
        step_runner: StepRunner,
        total_steps: int,
        start_index: int = 0,
        on_finished: RunCompletion | None = None,
    ) -> None:
        self._session = session
        self._run_step = step_runner
        self._total = total_steps
        self._index = start_index
        self._task: asyncio.Task[None] | None = None
        self._finished = asyncio.Event()
        self._on_finished = on_finished

    # ─── 진행 상태 ─────────────────────────────────────────────────────────

    @property
    def current_index(self) -> int:
        """다음에 실행할 Step 위치. 편집 경고 판정의 기준이다 (FR-040b)."""
        return self._index

    @property
    def total_steps(self) -> int:
        return self._total

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def retarget(self, start_index: int, total_steps: int) -> None:
        """편집 후 실행 위치를 다시 잡는다.

        Step 이 삽입·삭제되면 인덱스가 밀린다. 브라우저는 건드리지 않는다 (FR-040a).
        """
        self._index = max(0, min(start_index, total_steps))
        self._total = total_steps

    # ─── 실행 ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.running:
            msg = "이미 실행 중입니다."
            raise RuntimeError(msg)
        self._finished.clear()
        self._session.mark_running()
        self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        """실행 태스크 본체.

        **순서가 요구사항이다.** Step 실행 → 완료 통보(결과 기록) → 종료 상태 전이.

        종료 상태를 먼저 올리면, 그것을 본 화면이 결과를 읽으러 오는데 결과가 아직 없다.
        중지 요청이 그 틈에 들어오면 결과를 쓰던 태스크가 취소되어 실행 기록이 사라진다.
        상태가 `완료`·`실패` 로 보이는 시점에는 결과가 이미 디스크에 있어야 한다.

        완료 통보를 `finally` 에 두지 않는 이유는 따로 있다. `finally` 안에서 await 하면
        취소 도중에도 실행되어, 사용자가 중지한 실행이 실패로 기록된다.
        """
        passed = False
        try:
            try:
                passed = await self._advance()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - 예상 못한 실패도 결과로 남겨야 한다
                passed = False
                await self._session.emit(
                    "run_error", reason=f"실행 중 예상하지 못한 오류: {type(exc).__name__}"
                )

            if self._on_finished is not None:
                try:
                    await self._on_finished(passed)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    # 결과를 남기지 못했다는 사실을 조용히 넘기지 않는다.
                    await self._session.emit(
                        "run_error",
                        reason=f"실행 결과를 정리하지 못했습니다: {type(exc).__name__}: {exc}",
                    )

            await self._settle(passed)
        finally:
            self._finished.set()

    async def _advance(self) -> bool:
        """Step 을 순차로 실행한다. 전체 통과 여부를 돌려준다.

        **종료 상태로 옮기지 않는다.** 그 일은 결과 기록이 끝난 뒤 `_settle` 이 한다.
        """
        while self._index < self._total:
            # 일시정지 지점 — 브라우저에 아무 명령도 보내지 않는다.
            if self._session.is_paused:
                await self._session.wait_until_resumed()
                # 재개 시점에 편집으로 총 개수가 바뀌었을 수 있다.
                if self._index >= self._total:
                    break

            should_continue = await self._run_step(self._session, self._index)
            self._index += 1
            if not should_continue:
                return False
        return True

    async def _settle(self, passed: bool) -> None:
        """실행을 종료 상태로 옮긴다. 결과가 이미 기록된 뒤에만 호출된다."""
        if self._session.state not in (SessionState.REPLAYING, SessionState.AI_RUNNING):
            # 일시정지·유실·중지로 이미 다른 상태에 있다. 덮어쓰지 않는다.
            return
        with contextlib.suppress(Exception):
            await self._session.apply(
                Command.FINISH_PASS if passed else Command.FINISH_FAIL
            )

    async def wait(self) -> None:
        await self._finished.wait()

    async def cancel(self) -> None:
        """태스크를 취소한다. 브라우저는 호출자가 정리한다."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._finished.set()


# ─── 재실행 엔진 (US2) ──────────────────────────────────────────────────────


@dataclass(slots=True)
class ReplayEngine:
    """저장된 테스트 하나를 실행하며 결과를 모은다. FR-045~FR-058.

    `RunnerTask` 가 **언제** Step 을 돌릴지 정하고, 이 클래스가 **무엇이 일어났는지**를
    기록한다. 둘을 나눠 둔 덕에 일시정지·취소 로직과 결과 집계가 서로를 오염시키지 않는다.

    **언어모델을 부르지 않는다.** 실행에 필요한 모든 것이 `test` 안에 있다 (FR-044·FR-045).
    """

    session: BrowserSession
    test: Test
    executor: StepExecutor
    resolver: VariableResolver
    collector: ArtifactCollector
    run_dir: pathlib.Path
    project_root: pathlib.Path
    write_result: ResultWriter
    browser_label: str = "Chromium"

    results: list[StepResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    failed_index: int | None = None
    finalized: bool = False
    _failure_tab: int = 0

    def __post_init__(self) -> None:
        self.results = [
            StepResult(
                step_id=step.id,
                index=index,
                label=step.label,
                outcome=StepOutcome.NOT_RUN,
                tab=step.tab,
            )
            for index, step in enumerate(self.test.steps)
        ]

    # ─── 실행 위치 ─────────────────────────────────────────────────────────

    def reset(self, start_index: int = 0) -> None:
        """실행 위치를 옮기며 결과를 초기화한다 (FR-055).

        "실패한 Step부터 실행" 은 **새 실행**이다. 앞선 실행의 실패 기록을 남겨 두면 통과한
        실행이 실패로 보이거나 멈춘 Step 번호가 옛것을 가리킨다.
        """
        self.__post_init__()
        self.started_at = datetime.now(UTC)
        self.failed_index = None
        self.finalized = False
        self._failure_tab = 0
        self.skip_before(start_index)

    def skip_before(self, start_index: int) -> None:
        """`start_index` 앞의 Step 을 건너뛴 것으로 표시한다 (FR-055).

        "실패한 Step부터 실행" 은 앞선 Step 을 **실행하지 않는다**. 그것을 `pass` 로 적으면
        통과 수가 부풀고, `not_run` 으로 적으면 왜 안 돌았는지 알 수 없다.
        """
        for result in self.results[: min(start_index, len(self.results))]:
            result.outcome = StepOutcome.SKIPPED

    # ─── Step 하나 ─────────────────────────────────────────────────────────

    async def run_step(self, session: BrowserSession, index: int) -> bool:
        """Step 하나를 실행한다. 계속 진행할지 여부를 돌려준다 (FR-049)."""
        if index >= len(self.test.steps):  # pragma: no cover - 러너가 범위를 지킨다
            return True

        step = self.test.steps[index]
        result = self.results[index]
        await session.emit("step_started", step_id=step.id, index=index, tab=step.tab)

        started = time.monotonic()
        try:
            record = await self.executor.execute(step)
        except StepFailure as exc:
            result.outcome = StepOutcome.FAIL
            result.duration_ms = int((time.monotonic() - started) * 1000)
            result.tab_wait_ms = exc.tab_wait_ms
            result.locator_attempts = exc.attempts
            result.error_message = self._scrubber().scrub(str(exc))
            self.failed_index = index
            self._failure_tab = step.tab

            await session.emit(
                "step_failed",
                step_id=step.id,
                index=index,
                error_message=result.error_message,
                locator_attempts=[a.model_dump(mode="json") for a in exc.attempts],
                tab_wait_ms=exc.tab_wait_ms,
            )
            await session.emit(
                "step_finished",
                step_id=step.id,
                index=index,
                outcome=StepOutcome.FAIL.value,
                duration_ms=result.duration_ms,
                resolved_candidate=None,
            )
            return False

        result.outcome = StepOutcome.PASS
        result.duration_ms = int((time.monotonic() - started) * 1000)
        result.tab_wait_ms = record.tab_wait_ms
        result.locator_attempts = record.attempts
        result.resolved_candidate = record.resolved_candidate
        result.candidate_disagreement = record.disagreement

        await session.emit(
            "step_finished",
            step_id=step.id,
            index=index,
            outcome=StepOutcome.PASS.value,
            duration_ms=result.duration_ms,
            resolved_candidate=record.resolved_candidate,
        )
        return True

    # ─── 마무리 ────────────────────────────────────────────────────────────

    async def finalize(self, passed: bool, session_lost: bool = False) -> RunResult:
        """결과를 집계해 저장하고 `run_finished` 를 발행한다 (FR-048·FR-050).

        두 번 호출해도 한 번만 기록한다 — 유실 감지와 러너 종료가 겹칠 수 있다.
        """
        if self.finalized:
            return self._build(passed, session_lost)
        self.finalized = True

        scrubber = self._scrubber()
        artifacts = await self.collector.write(
            self.run_dir,
            self.project_root,
            scrubber,
            failure_page=self._failure_page() if not passed else None,
        )

        result = self._build(passed, session_lost, artifacts)
        try:
            self.write_result(result)
        except Exception as exc:  # noqa: BLE001 - 기록 실패를 조용히 넘기지 않는다
            # 결과를 못 남기면 사용자는 실행이 아예 없었던 것처럼 본다. 화면에 알린다.
            await self.session.emit(
                "run_error",
                reason=f"실행 결과를 저장하지 못했습니다: {type(exc).__name__}: {exc}",
            )

        await self.session.emit(
            "run_finished",
            outcome=result.outcome.value,
            total_ms=result.total_ms,
            passed_count=result.passed_count,
            total_count=result.total_count,
            failed_step_index=result.failed_step_index,
        )
        for note in artifacts.notes:
            await self.session.emit("artifact_note", message=note)
        return result

    def _build(
        self,
        passed: bool,
        session_lost: bool,
        artifacts: ArtifactPaths | None = None,
    ) -> RunResult:
        finished_at = datetime.now(UTC)
        passed_count = sum(1 for r in self.results if r.outcome is StepOutcome.PASS)
        return RunResult(
            test_id=self.test.id,
            outcome=Outcome.PASS if passed and not session_lost else Outcome.FAIL,
            started_at=self.started_at,
            finished_at=finished_at,
            total_ms=int((finished_at - self.started_at).total_seconds() * 1000),
            passed_count=passed_count,
            total_count=len(self.results),
            failed_step_index=self.failed_index,
            browser=self.browser_label,
            steps=self.results,
            artifacts=Artifacts(
                failure_screenshot=artifacts.failure_screenshot if artifacts else None,
                console_log=artifacts.console_log if artifacts else None,
                network_log=artifacts.network_log if artifacts else None,
            ),
            session_lost=session_lost,
        )

    def _failure_page(self) -> Page | None:
        """실패 시점 스크린샷을 찍을 화면 (FR-052).

        실패한 Step 의 탭을 우선한다. 그 탭이 닫혔다면 남아 있는 탭 중 하나라도 찍는다 —
        아무것도 안 찍는 것보다 화면 하나라도 남기는 것이 진단에 낫다.
        """
        handle = self.session.find_tab(self._failure_tab)
        if handle is not None and not handle.closed:
            return handle.page
        open_tabs = self.session.open_tabs()
        return open_tabs[-1].page if open_tabs else None

    def _scrubber(self) -> Scrubber:
        """지금까지 복호화된 민감 값으로 스크러버를 만든다.

        실행 도중 새 민감 변수가 해석될 수 있으므로 **호출 시점마다 다시 만든다.**
        한 번 만들어 재사용하면 나중에 복호화된 값이 마스킹되지 않는다.
        """
        return Scrubber(self.resolver.resolved_sensitive_values())
