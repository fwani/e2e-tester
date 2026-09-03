"""Step 6종 실행. FR-013a·FR-015·FR-045·FR-057.

**작성 주체를 보지 않는다.** 사람이 만든 Step 과 AI 가 만든 Step 이 같은 코드를 지난다 —
헌법 원칙 I 이 실행 계층에서 지켜지는 지점이다. `author` 는 여기서 읽히지 않는다.

**언어모델을 호출하지 않는다.** 이 모듈이 아는 것은 저장된 정의뿐이다 (FR-044·FR-045).
임포트 계약(`execution-no-llm`)이 이를 구조로 강제한다.

**대기 시간 상한은 Step 하나 전체에 대한 예산이다** (FR-057). 탭을 기다린 시간과 요소를
찾은 시간이 각각 상한을 갖게 두면 한 Step 이 상한의 두 배 이상 걸릴 수 있다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.run_result import LocatorAttempt
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    CloseTabStep,
    FillStep,
    NavigateStep,
    SelectStep,
    Step,
)
from itb.execution.locator_runtime import ElementNotFoundError, Resolution, resolve
from itb.execution.session import BrowserSession, TabNotFoundError
from itb.execution.tab_resolver import describe_tab_failure, resolve_tab
from itb.secrets.resolver import VariableResolutionError, VariableResolver

MIN_ACTION_TIMEOUT_MS = 250
"""탭 대기에 예산을 거의 다 쓴 경우에도 동작 자체에 남겨 두는 최소 시간.

0 을 넘기면 Playwright 가 "무한 대기"로 해석한다 — 상한이 사라져 FR-057 이 깨진다.
"""


class StepFailure(Exception):
    """Step 실행 실패. 진단에 필요한 것을 함께 들고 있다 (FR-021·FR-054)."""

    def __init__(
        self,
        message: str,
        attempts: list[LocatorAttempt] | None = None,
        tab_wait_ms: int = 0,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts or []
        self.tab_wait_ms = tab_wait_ms


@dataclass(slots=True)
class StepExecution:
    """Step 하나를 실행한 기록. 성공 경로에서도 진단 정보를 남긴다."""

    resolved_candidate: str | None = None
    attempts: list[LocatorAttempt] = field(default_factory=list)
    disagreement: list[str] = field(default_factory=list)
    tab_wait_ms: int = 0
    tab: int = 0


class StepExecutor:
    """한 실행 동안 Step 을 하나씩 수행한다.

    변수 해석기를 들고 있다 — 복호화된 값은 이 객체와 Playwright 호출 사이에만 존재하며
    어디에도 기록되지 않는다 (FR-089d).
    """

    def __init__(self, session: BrowserSession, resolver: VariableResolver) -> None:
        self._session = session
        self._resolver = resolver

    async def execute(self, step: Step) -> StepExecution:
        """Step 을 실행한다. 실패하면 `StepFailure` 를 던진다."""
        deadline = time.monotonic() + step.timeout_ms / 1000

        try:
            tab = await resolve_tab(self._session, step.tab, step.timeout_ms)
        except TabNotFoundError as exc:
            raise StepFailure(
                describe_tab_failure(exc, step.tab), tab_wait_ms=step.timeout_ms
            ) from exc

        record = StepExecution(tab_wait_ms=tab.waited_ms, tab=step.tab)

        try:
            await self._dispatch(step, tab.page, deadline, record)
        except StepFailure:
            raise
        except ElementNotFoundError as exc:
            raise StepFailure(str(exc), exc.attempts, record.tab_wait_ms) from exc
        except VariableResolutionError as exc:
            # FR-089f — 값을 구하지 못하면 빈 값으로 진행하지 않고 사유를 밝히며 멈춘다.
            raise StepFailure(str(exc), record.attempts, record.tab_wait_ms) from exc
        except PlaywrightError as exc:
            raise StepFailure(
                _humanize(exc, step), record.attempts, record.tab_wait_ms
            ) from exc
        return record

    # ─── 종류별 실행 ────────────────────────────────────────────────────────

    async def _dispatch(
        self, step: Step, page: Page, deadline: float, record: StepExecution
    ) -> None:
        """종류별 실행. **남은 예산을 매 단계에서 다시 계산한다.**

        요소를 찾는 데 쓴 시간과 동작에 쓴 시간이 각각 상한을 갖게 두면 한 Step 이 상한의
        두 배 이상 걸린다 — FR-057 이 막으려는 것이 정확히 그것이다.
        """
        match step:
            case NavigateStep():
                url = self._resolver.substitute(step.url)
                await page.goto(url, timeout=self._left(deadline))
            case CloseTabStep():
                await page.close()
            case ClickStep():
                located = await self._locate(page, step, deadline, record)
                await located.locator.click(timeout=self._left(deadline))
            case FillStep():
                located = await self._locate(page, step, deadline, record)
                value = self._resolver.substitute(step.value)
                await located.locator.fill(value, timeout=self._left(deadline))
            case SelectStep():
                located = await self._locate(page, step, deadline, record)
                value = self._resolver.substitute(step.value)
                await located.locator.select_option(value, timeout=self._left(deadline))
            case AssertionStep():
                await self._assert(step.assertion, page, deadline, record)
            case _:  # pragma: no cover - 판별 유니온이 모든 종류를 덮는다
                msg = f"실행할 수 없는 Step 종류입니다: {type(step).__name__}"
                raise StepFailure(msg, record.attempts, record.tab_wait_ms)

    async def _locate(
        self, page: Page, step: Step, deadline: float, record: StepExecution
    ) -> Resolution:
        """요소를 찾고 시도 내역을 기록에 남긴다."""
        target = getattr(step, "target", None)
        if target is None:  # pragma: no cover - 호출자가 대상 있는 종류만 넘긴다
            msg = "이 Step 에는 대상 요소가 없습니다."
            raise StepFailure(msg, record.attempts, record.tab_wait_ms)
        try:
            located = await resolve(page, target, self._left(deadline))
        except ElementNotFoundError as exc:
            record.attempts = exc.attempts
            raise
        record.attempts = located.attempts
        record.disagreement = located.disagreement
        record.resolved_candidate = located.strategy.kind.value
        return located

    # ─── 검증 4종 (FR-013a) ────────────────────────────────────────────────

    async def _assert(
        self,
        assertion: Assertion,
        page: Page,
        deadline: float,
        record: StepExecution,
    ) -> None:
        match assertion.kind:
            case AssertionKind.URL:
                await self._assert_url(assertion, page, deadline)
            case AssertionKind.HIDDEN:
                await self._assert_hidden(assertion, page, deadline, record)
            case AssertionKind.VISIBLE:
                located = await self._locate_target(assertion, page, deadline, record)
                await located.locator.wait_for(
                    state="visible", timeout=self._left(deadline)
                )
            case AssertionKind.TEXT:
                await self._assert_text(assertion, page, deadline, record)

    async def _assert_url(
        self, assertion: Assertion, page: Page, deadline: float
    ) -> None:
        expected = self._resolver.substitute(assertion.value or "")
        actual = page.url
        while time.monotonic() < deadline:
            actual = page.url
            if _matches(actual, expected, assertion.match):
                return
            await page.wait_for_timeout(50)
        if _matches(page.url, expected, assertion.match):
            return
        verb = "와 같지" if assertion.match is MatchMode.EQUALS else "를 포함하지"
        msg = (
            f"현재 주소가 기대한 값{verb} 않습니다. "
            f"기대: {expected!r}, 실제: {actual!r}"
        )
        raise StepFailure(msg)

    async def _assert_hidden(
        self,
        assertion: Assertion,
        page: Page,
        deadline: float,
        record: StepExecution,
    ) -> None:
        """`hidden` 은 **처음부터 없던 경우도 통과한다** (spec 엣지 케이스).

        요소를 찾지 못한 것이 곧 조건 충족이므로, 탐색 실패를 실패로 옮기지 않는다.
        """
        try:
            located = await self._locate_target(assertion, page, deadline, record)
        except (ElementNotFoundError, StepFailure):
            return
        await located.locator.wait_for(state="hidden", timeout=self._left(deadline))

    async def _assert_text(
        self,
        assertion: Assertion,
        page: Page,
        deadline: float,
        record: StepExecution,
    ) -> None:
        expected = self._resolver.substitute(assertion.value or "")
        if assertion.target is None:
            actual = await page.inner_text("body", timeout=self._left(deadline))
            scope = "화면"
        else:
            located = await self._locate_target(assertion, page, deadline, record)
            actual = await located.locator.inner_text(timeout=self._left(deadline))
            scope = "요소"
        if _matches(actual, expected, assertion.match):
            return
        verb = "와 같지" if assertion.match is MatchMode.EQUALS else "를 포함하지"
        msg = (
            f"{scope}의 텍스트가 기대한 값{verb} 않습니다. "
            f"기대: {expected!r}, 실제: {_clip(actual)!r}"
        )
        raise StepFailure(msg, record.attempts, record.tab_wait_ms)

    async def _locate_target(
        self,
        assertion: Assertion,
        page: Page,
        deadline: float,
        record: StepExecution,
    ) -> Resolution:
        if assertion.target is None:  # pragma: no cover - 스키마가 막는다
            msg = "이 검증에는 대상 요소가 필요합니다."
            raise StepFailure(msg, record.attempts, record.tab_wait_ms)
        located = await resolve(page, assertion.target, self._left(deadline))
        record.attempts = located.attempts
        record.disagreement = located.disagreement
        record.resolved_candidate = located.strategy.kind.value
        return located

    # ─── 시간 예산 ─────────────────────────────────────────────────────────

    @staticmethod
    def _left(deadline: float) -> int:
        """이 Step 에 남은 시간(ms).

        `MIN_ACTION_TIMEOUT_MS` 아래로 내려가지 않는다 — 0 을 Playwright 에 넘기면
        "무한 대기"로 해석되어 상한이 사라진다 (FR-057).
        """
        return max(int((deadline - time.monotonic()) * 1000), MIN_ACTION_TIMEOUT_MS)


def _matches(actual: str, expected: str, mode: MatchMode) -> bool:
    if mode is MatchMode.CONTAINS:
        return expected in actual
    return actual.strip() == expected.strip()


def _clip(text: str, limit: int = 200) -> str:
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "…"


def _humanize(exc: PlaywrightError, step: Step) -> str:
    """Playwright 오류를 사용자 문장으로 바꾼다 (FR-054).

    원문을 버리지 않는다 — 사람이 읽을 문장을 앞에 두고 원인을 뒤에 붙인다.
    """
    raw = " ".join(str(exc.message).split())[:400]
    if "Timeout" in raw or "timeout" in raw:
        return (
            f"{step.label} 이(가) {step.timeout_ms}ms 안에 끝나지 않았습니다. "
            f"대상 요소가 나타나지 않았거나 동작이 막혔습니다. ({raw})"
        )
    return f"{step.label} 실행에 실패했습니다. ({raw})"
