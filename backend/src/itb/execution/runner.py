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

from itb.domain.error import ErrorCode, error_body, error_payload
from itb.domain.run_pacing import auto_pause, delay_ms
from itb.domain.run_result import (
    scope_of,
    decide_outcome,
    attempted_of,
    RunScope,
    Artifacts,
    Outcome,
    RunResult,
    StepOutcome,
    StepResult,
)
from itb.domain.step import Step
from itb.domain.test_case import Test
from itb.execution.artifacts import ArtifactCollector, ArtifactPaths
from itb.execution.session import BrowserSession
from itb.execution.state_machine import Command, InvalidTransitionError, SessionState
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
        self._task: asyncio.Task[None] | None = None
        self._finished = asyncio.Event()
        self._boundary = asyncio.Event()
        self._on_finished = on_finished
        # **실행 위치는 세션이 소유한다.** 여기에 사본을 두면 편집이 한쪽을 고치는 동안
        # 러너가 다른 쪽을 올려, 같은 Step 이 두 번 실행된다 (T093 이 잡은 결함).
        session.current_step_index = max(0, min(start_index, total_steps))

    # ─── 진행 상태 ─────────────────────────────────────────────────────────

    @property
    def current_index(self) -> int:
        """다음에 실행할 Step 위치. 편집 경고 판정의 기준이다 (FR-040b)."""
        return self._session.current_step_index

    @property
    def total_steps(self) -> int:
        return self._total

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def at_boundary(self) -> bool:
        """Step 하나가 끝나고 다음 Step 을 시작하지 않은 상태인가.

        편집은 이 지점에서만 안전하다. Step 이 도는 중에 목록을 고치면 방금 실행한
        Step 이 어느 위치였는지에 대한 판단이 편집과 엇갈린다.
        """
        return self._boundary.is_set() or self._finished.is_set()

    async def wait_for_boundary(self, timeout_s: float) -> bool:
        """Step 경계에 도달할 때까지 기다린다. 도달했으면 True.

        일시정지 요청이 Step 중간에 도착하면 그 Step 은 끝까지 돈다 — 중간에 끊으면
        브라우저가 반쯤 조작된 상태로 남고, 그것은 "화면 상태를 그대로 유지한다"(FR-032)
        와 다른 결과다. 그래서 끊지 않고 **끝나기를 기다린다.**

        기다림에 상한을 두는 이유는 Step 하나가 최대 60초까지 걸릴 수 있기 때문이다.
        상한을 넘기면 False 를 돌려주고, 호출자가 그 사실을 사용자에게 알린다 —
        멈춘 것처럼 보여 주고 실제로는 아직 도는 상태를 만들지 않는다.
        """
        if self.at_boundary:
            return True
        tasks = [
            asyncio.create_task(self._boundary.wait()),
            asyncio.create_task(self._finished.wait()),
        ]
        try:
            done, pending = await asyncio.wait(
                tasks, timeout=timeout_s, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        return bool(done)

    def retarget(self, total_steps: int) -> None:
        """편집 후 총 Step 수를 다시 잡는다.

        **위치는 건드리지 않는다.** 위치는 편집 연산(`step_edits`)이 이미 옮겼고, 세션이
        그것을 소유한다. 여기서 다시 쓰면 두 판단이 겹친다. 브라우저는 어느 쪽도 건드리지
        않는다 (FR-040a).
        """
        self._total = total_steps
        self._session.current_step_index = max(
            0, min(self._session.current_step_index, total_steps)
        )

    # ─── 실행 ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.running:
            msg = "이미 실행 중입니다."
            raise RuntimeError(msg)
        self._finished.clear()
        self._boundary.clear()
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
                    "run_error",
                    **error_payload(
                        ErrorCode.INTERNAL_ERROR,
                        "실행 중 예상하지 못한 오류가 발생했습니다.",
                        next_action="Step 목록은 그대로 있습니다. 다시 실행하고, 계속 "
                        "발생하면 서버 로그와 함께 알려주세요.",
                        kind=type(exc).__name__,
                    ),
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
                        **error_payload(
                            ErrorCode.INTERNAL_ERROR,
                            "실행은 끝났지만 결과를 정리하지 못했습니다.",
                            next_action="결과 화면이 비어 있을 수 있습니다. 다시 실행하세요.",
                            kind=type(exc).__name__,
                        ),
                    )

            await self._settle(passed)
        finally:
            self._finished.set()
            self._boundary.set()

    async def _advance(self) -> bool:
        """Step 을 순차로 실행한다. 전체 통과 여부를 돌려준다.

        **종료 상태로 옮기지 않는다.** 그 일은 결과 기록이 끝난 뒤 `_settle` 이 한다.
        """
        while True:
            # 일시정지 지점 — 브라우저에 아무 명령도 보내지 않는다.
            if self._session.is_paused:
                # 여기가 Step 경계다. 편집은 이 상태에서만 안전하다.
                self._boundary.set()
                await self._session.wait_until_resumed()
                self._boundary.clear()

            index = self._session.current_step_index
            if index >= self._total:
                break

            should_continue = await self._run_step(self._session, index)
            # **상대 전진.** 실행 중에 편집이 들어와 위치가 밀렸어도 "방금 실행한 Step
            # 다음" 으로 간다. 절대값을 다시 쓰면 밀린 편집이 되돌려져 같은 Step 이 두 번
            # 돈다 (T093 이 잡은 결함).
            self._session.current_step_index += 1
            if not should_continue:
                return False

            await self._pace(self._session.current_step_index)
        return True

    async def _pace(self, next_index: int) -> None:
        """Step 하나를 마친 뒤 사람이 따라올 시간을 준다 (004 FR-101·FR-105·FR-106).

        **다음 Step 이 있을 때만 쉰다.** 마지막 Step 뒤에 쉬면 실행이 끝났는데도 끝나지
        않은 것처럼 보인다 (spec 엣지 케이스).

        **저장된 Step 을 실행하는 구간에만 적용한다** (FR-045 구간). AI 가 다음 동작을
        판단하는 시간은 Step 실행이 아니며, 거기에 간격을 더하면 이미 느린 것을 더 느리게
        만들 뿐 사람이 볼 것이 늘지 않는다 (spec 엣지 케이스).

        **속도는 매 경계에서 다시 읽는다.** 실행 중 변경이 다음 Step 부터 반영되는 것이
        FR-103 의 요구이며, 값을 루프 시작 때 잡아 두면 그 요구가 깨진다.

        간격은 Step 의 대기 예산 **밖**이다 (FR-105). 여기서 잔 시간은 어느 Step 의
        `duration_ms` 에도 들어가지 않는다 — 이 함수가 Step 실행 사이에 있기 때문이다.
        """
        if next_index >= self._total or self._session.is_paused:
            return
        if self._session.state is not SessionState.REPLAYING:
            return

        pacing = self._session.pacing
        if auto_pause(pacing):
            # 새 상태를 만들지 않는다. 기존 `PAUSED` 에 들어가므로 편집·조작 허용 규칙이
            # 이미 검증된 경로를 그대로 쓴다 (research R7, FR-108).
            #
            # **좁게 삼킨다.** 이 경계에 도달하는 사이 상태가 옮겨졌다면(중지·유실) PAUSE 는
            # 유효하지 않은 전이이고, 그때는 멈출 이유도 사라진 것이므로 그냥 넘어가면 된다.
            # `Exception` 을 통째로 삼키면 그 밖의 결함이 조용히 묻힌다.
            with contextlib.suppress(InvalidTransitionError):
                await self._session.apply(Command.PAUSE)
            return

        delay_s = delay_ms(pacing) / 1000
        if delay_s <= 0:
            return
        # 일시정지가 요청되면 즉시 깨어난다. 간격이 끝나기를 기다리지 않는다 (FR-106).
        # 중지는 태스크 취소이고 `wait_for` 는 취소 가능하므로 역시 즉시 반영된다.
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                self._session.wait_pause_requested(), timeout=delay_s
            )

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

    start_index: int = 0
    """이 실행이 시작한 Step (005 FR-152). `reset()` 이 갱신한다."""

    stop_requested: bool = False
    """사용자가 중지를 요청했는가 (005 FR-131).

    **엔진이 이것을 들고 있는 이유**는 결말 판정의 입력이기 때문이다. 중지 경로가
    `finalize()` 인자로만 넘기면, 유실 감지와 러너 종료가 각자 `finalize()` 를 부르는
    경로에서 한쪽이 이 사실을 모른 채 실패로 확정한다 — 그것이 U-03 이었다.
    """

    skipped_failures: bool = False
    """사용자가 「실패한 Step 건너뛰고 계속」을 골랐는가 (005 FR-137)."""

    stopped_index: int | None = None
    """중지 시점의 Step (005 FR-131)."""

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
        # 005 FR-152 — 이 실행의 범위를 결과에 남기기 위해 시작 지점을 기억한다.
        self.start_index = max(0, start_index)
        self.stop_requested = False
        self.skipped_failures = False
        self.stopped_index = None
        self.skip_before(start_index)

    def rebase(self, steps: list[Step]) -> None:
        """편집된 Step 목록을 실행 대상으로 삼는다 (FR-035·FR-038, T101).

        **이미 실행된 Step 의 결과를 보존한다.** 일시정지 중 편집한 뒤 이어서 실행하면
        앞선 Step 들은 다시 돌지 않으므로(원칙 III), 그 결과를 버리면 최종 결과에서
        통과 수가 0 으로 떨어지고 "무엇이 돌았는지" 를 알 수 없게 된다.

        보존 기준은 **Step id** 다. 순서가 바뀌어도 같은 Step 의 결과는 따라간다.
        새로 삽입된 Step 은 `not_run` 으로 시작한다 — 아직 돌지 않았다는 사실 그대로다.

        `test` 를 갈아 끼우는 이유는 실행 대상이 **세션의 작업 중 목록** 이어야 하기
        때문이다. 디스크의 정의를 계속 보면 편집이 실행에 반영되지 않아, 사용자는 고친
        테스트가 아니라 고치기 전 테스트가 이어서 도는 것을 본다.
        """
        previous = {r.step_id: r for r in self.results}
        self.test = self.test.model_copy(update={"steps": list(steps)})
        rebuilt: list[StepResult] = []
        for index, step in enumerate(self.test.steps):
            old = previous.get(step.id)
            if old is None:
                rebuilt.append(
                    StepResult(
                        step_id=step.id,
                        index=index,
                        label=step.label,
                        outcome=StepOutcome.NOT_RUN,
                        tab=step.tab,
                    )
                )
                continue
            rebuilt.append(old.model_copy(update={"index": index, "label": step.label}))
        self.results = rebuilt

    def note_stop_requested(self, step_index: int | None = None) -> None:
        """사용자가 중지를 요청했다 (005 FR-131).

        **결말 판정 전에 불러야 한다.** 이 사실을 모르는 판정은 중지를 실패로 적고, 그것이
        U-03 의 마지막 조각이었다.
        """
        self.stop_requested = True
        if step_index is not None:
            self.stopped_index = step_index

    def note_skipped_failures(self) -> None:
        """사용자가 「실패한 Step 건너뛰고 계속」을 골랐다 (005 FR-137)."""
        self.skipped_failures = True

    def has_failed_step(self) -> bool:
        """지금까지의 결과에 실패한 Step 이 있는가 (005 FR-136).

        재개를 거절할지 판단하는 근거다. 실패를 조용히 지나가면 화면은 「완료」라고
        말하고 저장된 결과는 실패인 상태가 된다(U-05).
        """
        return any(r.outcome is StepOutcome.FAIL for r in self.results)

    def first_failed_index(self) -> int | None:
        """가장 앞선 실패 Step 의 인덱스 (005 FR-136 의 안내에 쓴다)."""
        return next((r.index for r in self.results if r.outcome is StepOutcome.FAIL), None)

    def clear_failed_steps(self) -> None:
        """실패 Step 을 건너뜀으로 바꾼다 (005 FR-137).

        「실패한 Step 건너뛰고 계속」의 의미가 이것이다 — 실패를 **지우지 않고** 건너뛴
        것으로 남긴다. 지우면 결과에서 그 Step 이 왜 안 돌았는지 알 수 없다.
        """
        for result in self.results:
            if result.outcome is StepOutcome.FAIL:
                result.outcome = StepOutcome.SKIPPED
        self.failed_index = None

    def skip_before(self, start_index: int) -> None:
        """`start_index` 앞의 **아직 돌지 않은** Step 을 건너뛴 것으로 표시한다 (FR-055).

        "실패한 Step부터 실행" 은 앞선 Step 을 **실행하지 않는다**. 그것을 `pass` 로 적으면
        통과 수가 부풀고, `not_run` 으로 적으면 왜 안 돌았는지 알 수 없다.

        **이미 결과가 있는 Step 은 건드리지 않는다.** 일시정지 후 이어서 실행할 때도 이
        함수를 지나는데, 그때 앞선 Step 들은 이 실행에서 실제로 통과한 것이다. 덮어쓰면
        같은 실행의 통과 기록이 사라진다.
        """
        for result in self.results[: min(start_index, len(self.results))]:
            if result.outcome is StepOutcome.NOT_RUN:
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
            result.element_wait_ms = exc.element_wait_ms
            result.error_code = exc.code
            result.locator_attempts = exc.attempts
            result.error_message = self._scrubber().scrub(str(exc))
            self.failed_index = index
            self._failure_tab = step.tab

            await session.emit(
                "step_failed",
                step_id=step.id,
                index=index,
                # `error_message` 는 001·002 의 화면과 검증이 읽는 이름이라 그대로 둔다.
                # `error` 는 003 이 더한 것으로, **분류와 다음 행동**을 함께 싣는다 —
                # 문구를 해석하지 않고도 "대상 쪽 사정" 과 "제품이 깨진 것" 이 갈린다
                # (EC-008·AP-033).
                error_message=result.error_message,
                locator_attempts=[a.model_dump(mode="json") for a in exc.attempts],
                tab_wait_ms=exc.tab_wait_ms,
                element_wait_ms=exc.element_wait_ms,
                error=error_body(exc.code, result.error_message),
            )
            await session.emit(
                "step_finished",
                step_id=step.id,
                index=index,
                outcome=StepOutcome.FAIL.value,
                duration_ms=result.duration_ms,
                element_wait_ms=exc.element_wait_ms,
                resolved_candidate=None,
            )
            return False

        result.outcome = StepOutcome.PASS
        result.duration_ms = int((time.monotonic() - started) * 1000)
        result.tab_wait_ms = record.tab_wait_ms
        result.element_wait_ms = record.element_wait_ms
        result.locator_attempts = record.attempts
        result.resolved_candidate = record.resolved_candidate
        result.candidate_disagreement = record.disagreement

        await session.emit(
            "step_finished",
            step_id=step.id,
            index=index,
            outcome=StepOutcome.PASS.value,
            duration_ms=result.duration_ms,
            element_wait_ms=record.element_wait_ms,
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
                **error_payload(
                    ErrorCode.INTERNAL_ERROR,
                    "실행 결과를 저장하지 못했습니다.",
                    next_action="이 실행의 결과는 남지 않았습니다. 다시 실행하세요.",
                    kind=type(exc).__name__,
                ),
            )

        await self.session.emit(
            "run_finished",
            outcome=result.outcome.value,
            total_ms=result.total_ms,
            passed_count=result.passed_count,
            total_count=result.total_count,
            attempted_count=result.attempted_count,
            scope=result.scope.value,
            start_index=result.start_index,
            stopped_step_index=result.stopped_step_index,
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
        # 005 T036b — 결말은 순수 함수가 정한다. `passed` 를 그대로 쓰지 않는 이유는
        # 호출자마다 그것을 다르게 계산했고, 그래서 사용자가 누른 중지가 실패가 됐다(U-03).
        outcome = decide_outcome(
            self.results,
            session_lost=session_lost,
            stop_requested=self.stop_requested,
            skipped_failures=self.skipped_failures,
        )
        # `passed=False` 인데 실패 Step 이 없는 경우가 있다 — 러너가 중단된 경로다.
        # 그때 결말을 통과로 적으면 실행이 성공한 것처럼 보인다.
        if outcome is Outcome.PASS and not passed:
            outcome = Outcome.FAIL
        return RunResult(
            test_id=self.test.id,
            outcome=outcome,
            started_at=self.started_at,
            finished_at=finished_at,
            total_ms=int((finished_at - self.started_at).total_seconds() * 1000),
            passed_count=passed_count,
            total_count=len(self.results),
            attempted_count=attempted_of(self.results),
            start_index=self.start_index,
            scope=scope_of(self.start_index),
            stopped_step_index=self.stopped_index if outcome is Outcome.STOPPED else None,
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
