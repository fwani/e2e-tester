"""Step 6종 실행. FR-013a·FR-015·FR-045·FR-057.

**작성 주체를 보지 않는다.** 사람이 만든 Step 과 AI 가 만든 Step 이 같은 코드를 지난다 —
헌법 원칙 I 이 실행 계층에서 지켜지는 지점이다. `author` 는 여기서 읽히지 않는다.

**언어모델을 호출하지 않는다.** 이 모듈이 아는 것은 저장된 정의뿐이다 (FR-044·FR-045).
임포트 계약(`execution-no-llm`)이 이를 구조로 강제한다.

**아무것도 발행하지 않는다** (024 T055 · research R5). 실행 기록을 **값으로 돌려줄 뿐**
이벤트를 내지 않는다. 024 가 요소의 화면상 자리를 여기서 읽게 되면서 그 성질이 처음으로
시험대에 올랐다 — 자리를 알리는 통로(`on_element_resolved` 같은 콜백)를 여기 달았다면,
재생 배선에서 그것을 잇는 **한 줄**로 헌법 원칙 II 가 깨진다. 재생도 이 실행기를 쓰기
때문이다.

값을 돌려주는 쪽을 택한 이유가 그것이다. 재생 쪽이 `ai_focus` 를 내려면 코드를 새로
써야 한다 — **실수로는 생기지 않는다.** 발행은 AI 작성 전용 모듈(`authoring/tools.py`)
안에만 있다.

**대기 시간 상한은 Step 하나 전체에 대한 예산이다** (FR-057). 탭을 기다린 시간과 요소를
찾은 시간이 각각 상한을 갖게 두면 한 Step 이 상한의 두 배 이상 걸릴 수 있다.
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.error import ErrorCode
from itb.domain.run_result import LocatorAttempt
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    CloseTabStep,
    DragStep,
    FillStep,
    HoverStep,
    NavigateStep,
    PressStep,
    SelectStep,
    Step,
    UploadStep,
    mime_type_of,
)
from itb.execution import pointer
from itb.execution.frame_resolver import (
    FrameNotFoundError,
    SearchRoot,
    resolve_frame,
)
from itb.execution.locator_runtime import (
    MIN_ACTION_TIMEOUT_MS,
    ElementNotFoundError,
    Resolution,
    resolve,
)
from itb.execution.session import BrowserSession, TabNotFoundError
from itb.execution.tab_resolver import describe_tab_failure, resolve_tab
from itb.secrets.resolver import VariableResolutionError, VariableResolver

__all__ = [
    "MIN_ACTION_TIMEOUT_MS",
    "ElementRect",
    "StepExecution",
    "StepExecutor",
    "StepFailure",
    "settle",
]
"""`MIN_ACTION_TIMEOUT_MS` 는 `locator_runtime` 이 정의한다 — 요소 탐색이 언제 포기하고
채택할지와 동작에 얼마를 남길지가 **같은 값**이어야 하기 때문이다 (004). 여기서 다시
내보내는 것은 기존 임포트 경로를 깨지 않기 위해서다.
"""


@dataclass(frozen=True, slots=True)
class ElementRect:
    """요소가 대상 화면에서 차지하는 자리 (024 FR-001 · data-model §2).

    **좌표계는 미러 프레임과 같다** — 주 프레임 뷰포트 기준 CSS 픽셀. iframe 안의
    요소여도 그렇다 (024 research R3 실측: 하위 프레임 요소의 경계 상자가 주 프레임
    기준으로 나왔다).

    **음수 좌표는 유효하다.** 스크롤 위에 있는 요소가 그렇다 — 실측에서 뷰포트 높이 800
    인 화면의 요소가 `y=2008` 로 나왔다. 자리가 없는 것이 아니라 보이지 않는 것이며,
    그릴지 말지는 **화면이 판정한다** (024 FR-019). 여기서 화면 안으로 밀어 넣지 않는다.

    크기가 0 이하이거나 수치가 아니면 **자리가 없는 것**이다 — `of` 가 `None` 을 준다.
    """

    x: float
    y: float
    width: float
    height: float

    @classmethod
    def of(cls, box: dict[str, Any] | None) -> ElementRect | None:
        """Playwright 의 경계 상자를 자리로 바꾼다. 자리가 아니면 `None`.

        **`None` 을 돌려주는 것이 정상 경로다.** 보이지 않는 요소는 경계 상자가 없고,
        크기가 0 인 요소는 그릴 자리가 없다. 둘 다 「그리지 않는다」로 귀결되므로
        구별하지 않는다.
        """
        if not isinstance(box, dict):
            return None
        try:
            x, y = float(box["x"]), float(box["y"])
            width, height = float(box["width"]), float(box["height"])
        except (KeyError, TypeError, ValueError):
            return None
        # `NaN` 은 모든 비교를 거짓으로 만들어 아래 검사를 그대로 통과한다 — 좌표가
        # 수치가 아니면 화면이 그린 자리가 사라지거나 화면 전체를 덮는다.
        if not all(math.isfinite(v) for v in (x, y, width, height)):
            return None
        if width <= 0 or height <= 0:
            return None
        return cls(x=x, y=y, width=width, height=height)

    def as_payload(self) -> dict[str, float]:
        """이벤트에 싣는 모양 (024 contracts/ai-focus.md §2)."""
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


class StepFailure(Exception):
    """Step 실행 실패. 진단에 필요한 것을 함께 들고 있다 (FR-021·FR-054).

    **분류를 함께 든다** (003 AP-033). 실패 문장만으로는 "대상 사이트가 응답하지 않은
    것"과 "제품이 깨진 것"을 받는 쪽이 구별할 수 없다. 문구를 해석하지 않고도 판별되어야
    한다는 것이 US1 의 요구다.
    """

    def __init__(
        self,
        message: str,
        attempts: list[LocatorAttempt] | None = None,
        tab_wait_ms: int = 0,
        *,
        code: ErrorCode = ErrorCode.STEP_FAILED,
        element_wait_ms: int = 0,
        rect: ElementRect | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts or []
        self.tab_wait_ms = tab_wait_ms
        self.code = code
        self.element_wait_ms = element_wait_ms
        """요소를 기다린 시간 (004 FR-121). 실패 사유가 "얼마나 기다렸는지" 를 담아야
        사용자가 예산을 늘릴지 정의를 고칠지 판단할 수 있다."""
        self.rect = rect
        """실패한 요소의 자리 (024 FR-008 · data-model §4).

        **요소는 찾았는데 동작이 실패한 경우에만 있다** — 가려짐·비활성·시간 초과가
        그렇다. 024 US2 가 겨냥하는 것이 정확히 그 경우다. 요소 자체를 찾지 못한 실패에는
        잴 것이 없으므로 `None` 이고, 그때는 아무것도 표시되지 않는다 (FR-010).
        """


@dataclass(slots=True)
class StepExecution:
    """Step 하나를 실행한 기록. 성공 경로에서도 진단 정보를 남긴다."""

    resolved_candidate: str | None = None
    attempts: list[LocatorAttempt] = field(default_factory=list)
    disagreement: list[str] = field(default_factory=list)
    tab_wait_ms: int = 0
    element_wait_ms: int = 0
    """요소가 나타나기를 기다린 시간 (004 FR-114). 성공 경로에서도 남긴다.

    **하위 프레임을 기다린 시간도 여기 들어간다.** 프레임을 찾는 것은 요소를 찾는 일의
    일부이고, 사용자가 이 값으로 하는 일(예산을 얼마로 잡을지)은 둘을 나눠 봐도 달라지지
    않는다. 그래서 프레임 대기로 **씨앗을 놓고** 이후 지점이 모두 더한다 — 대입으로 두면
    나중에 요소 대기가 프레임 대기를 지운다.
    """

    tab: int = 0

    rect: ElementRect | None = None
    """이 Step 이 조작한 요소의 화면상 자리 (024 FR-001).

    **실행기가 실제로 채택한 요소에서 읽은 값이다.** 후보 수집이 쓴 CSS 경로가 아니라
    우선순위 전략(testId→role→…)이 고른 그 요소다 — 둘은 다를 수 있고, 다르면 표시된
    자리와 조작된 요소가 갈린다 (024 research R1).

    **`None` 이 정상 값이다.** 요소를 대상으로 하지 않는 Step(이동·탭 닫기), 보이지 않아
    경계 상자가 없는 요소, 측정이 실패한 경우가 그렇다. 「자리를 모른다」와 「자리가
    없다」를 구별하지 않는 이유는 둘 다 「그리지 않는다」로 귀결되기 때문이다.

    **이 값을 여기서 어디로도 보내지 않는다.** 모듈 머리말을 보라 — 발행하는 순간 재생
    경로가 원칙 II 를 어기는 자리가 된다.
    """


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
        if isinstance(step, CloseTabStep):
            # 탭 닫기는 대상 탭이 **없는 상태**를 목표로 한다. 다른 종류와 달리
            # 대상이 없는 것이 실패가 아니므로 엄격한 탭 해석을 지나지 않는다.
            return await self._close_tab(step)

        deadline = time.monotonic() + step.timeout_ms / 1000

        try:
            tab = await resolve_tab(self._session, step.tab, step.timeout_ms)
        except TabNotFoundError as exc:
            raise StepFailure(
                describe_tab_failure(exc, step.tab),
                tab_wait_ms=step.timeout_ms,
                code=ErrorCode.TAB_NOT_FOUND,
            ) from exc

        record = StepExecution(tab_wait_ms=tab.waited_ms, tab=step.tab)

        # **앞선 Step 이 일으킨 화면 전환을 여기서 기다린다.**
        #
        # 2026-09-30 사용자 보고 — 「빠름으로 하면 앞선 스텝이 이루어져야 하는데 그냥
        # 지나가버려서 작성한 테스트가 중간에 실패한다」. 실행 속도(004)는 Step 사이에
        # 쉬는 시간일 뿐 아무것도 확인하지 않으므로(`run_pacing`), `NORMAL` 의 500ms 가
        # 우연히 메워 주던 틈이 `FAST` 에서 그대로 드러난 것이다. 속도를 고른 것이 테스트의
        # 성패를 가르면 그 설정은 쓸 수 없다.
        #
        # **`goto` 는 이미 기다린다.** Playwright 의 기본값이 `wait_until="load"` 이므로
        # 빠져 있던 것은 화면 이동 Step 이 아니라 **클릭·submit 이 일으킨 전환**이었다.
        # 그 대가는 전환을 일으킨 Step 이 아니라 **그 다음 Step** 이 치른다 — 그래서
        # 고칠 자리가 여기다.
        #
        # **`domcontentloaded` 다 — `networkidle` 이 아니다.** 대상 화면이 WebSocket 이나
        # 폴링을 쓰면 idle 은 영영 오지 않고, 그러면 모든 Step 이 예산을 통째로 버린다.
        # SPA 의 부분 렌더는 이것으로 덮이지 않는다. 그 자리는 검증 Step 이 맡는다 —
        # 여기서 화면이 「준비됐는지」를 판정하려 들면 원칙 II 가 요구하는 결정성이
        # 시간 감각으로 바뀐다.
        record.tab_wait_ms += await self._settle_transition(tab.page, deadline)

        # 하위 프레임에서 기록된 Step 은 **그 프레임 안에서** 찾아야 한다. main frame 만
        # 뒤지면 프레임 안에서 측정된 후보는 0개를 매칭하고, 사용자는 예산을 다 쓴 "요소를
        # 찾을 수 없습니다" 만 본다 (001 research 의 iframe 항목).
        try:
            frame = await resolve_frame(tab.page, step.frame_url, step.timeout_ms)
        except FrameNotFoundError as exc:
            # 프레임을 기다린 시간은 요소 대기에 넣는다 — 프레임을 찾는 것은 요소를 찾는
            # 일의 일부이며, 사용자가 예산을 정할 때 보는 값도 그것이다.
            record.element_wait_ms = exc.waited_ms
            raise StepFailure(
                str(exc),
                record.attempts,
                record.tab_wait_ms,
                code=(
                    ErrorCode.ELEMENT_AMBIGUOUS
                    if exc.ambiguous
                    else ErrorCode.ELEMENT_NOT_READY
                ),
                element_wait_ms=exc.waited_ms,
            ) from exc

        record.element_wait_ms = frame.waited_ms
        if frame.relaxed:
            record.disagreement = [
                *record.disagreement,
                f"프레임을 쿼리·프래그먼트를 뗀 주소로 맞췄습니다: {step.frame_url}",
            ]

        try:
            await self._dispatch(step, tab.page, frame.root, deadline, record)
        except StepFailure:
            raise
        except ElementNotFoundError as exc:
            record.element_wait_ms += exc.waited_ms
            raise StepFailure(
                str(exc),
                exc.attempts,
                record.tab_wait_ms,
                code=_classify_lookup(exc),
                element_wait_ms=record.element_wait_ms,
            ) from exc
        except VariableResolutionError as exc:
            # FR-089f — 값을 구하지 못하면 빈 값으로 진행하지 않고 사유를 밝히며 멈춘다.
            raise StepFailure(str(exc), record.attempts, record.tab_wait_ms) from exc
        except PlaywrightError as exc:
            # **여기가 024 US2 가 겨냥하는 실패다** — 요소는 찾았는데 동작이 안 된 경우
            # (가려짐·비활성·시간 초과). `record.rect` 에 그 요소의 자리가 이미 들어 있다.
            #
            # 위의 `ElementNotFoundError` 경로에는 싣지 않는다 — 요소를 못 찾았으므로
            # 잴 것이 없었고, 자리를 모르면서 그리면 거짓말이 된다 (FR-010).
            raise StepFailure(
                _humanize(exc, step),
                record.attempts,
                record.tab_wait_ms,
                code=_classify(exc, step),
                rect=record.rect,
            ) from exc
        return record

    # ─── 종류별 실행 ────────────────────────────────────────────────────────

    async def _dispatch(
        self,
        step: Step,
        page: Page,
        root: SearchRoot,
        deadline: float,
        record: StepExecution,
    ) -> None:
        """종류별 실행. **남은 예산을 매 단계에서 다시 계산한다.**

        요소를 찾는 데 쓴 시간과 동작에 쓴 시간이 각각 상한을 갖게 두면 한 Step 이 상한의
        두 배 이상 걸린다 — FR-057 이 막으려는 것이 정확히 그것이다.

        **`page` 와 `root` 를 나눠 받는다.** `root` 는 요소를 찾을 문서이며 하위 프레임일
        수 있다. `page` 는 탭 자체를 뜻하며 화면 이동과 주소 검증이 쓴다 — iframe 안의
        Step 이라도 "현재 주소" 는 주소창의 주소여야 한다.
        """
        match step:
            case NavigateStep():
                url = self._resolver.substitute(step.url)
                await page.goto(url, timeout=self._left(deadline))
            case ClickStep():
                located = await self._locate(root, step, deadline, record)
                await self._click(page, located.locator, deadline)
            case FillStep():
                located = await self._locate(root, step, deadline, record)
                value = self._resolver.substitute(step.value)
                await located.locator.fill(value, timeout=self._left(deadline))
            case SelectStep():
                located = await self._locate(root, step, deadline, record)
                value = self._resolver.substitute(step.value)
                await located.locator.select_option(value, timeout=self._left(deadline))
            case HoverStep():
                located = await self._locate(root, step, deadline, record)
                await located.locator.hover(timeout=self._left(deadline))
            case UploadStep():
                located = await self._locate(root, step, deadline, record)
                await self._upload(located.locator, step, deadline)
            case PressStep():
                # **대상 요소에** 키를 보낸다 (023 FR-051). `page.keyboard.press` 는
                # 지금 포커스된 곳에 보내므로, 앞 Step 의 부작용에 결과가 좌우된다 —
                # 원칙 II 가 요구하는 「같은 화면이면 같은 결과」가 성립하지 않는다.
                # `locator.press` 는 포커스를 먼저 주고 누르므로 정의가 곧 사실이다.
                #
                # 결과를 판정하지 않는다. 키를 눌렀는데 화면이 안 바뀌어도 성공이다 —
                # 「눌렀더니 태그가 생겼다」는 검증 Step 이 따로 맡는다.
                located = await self._locate(root, step, deadline, record)
                await located.locator.press(step.key.value, timeout=self._left(deadline))
            case DragStep():
                await self._drag(step, root, deadline, record)
            case AssertionStep():
                await self._assert(step.assertion, page, root, deadline, record)
            case _:  # pragma: no cover - 판별 유니온이 모든 종류를 덮는다
                msg = f"실행할 수 없는 Step 종류입니다: {type(step).__name__}"
                raise StepFailure(msg, record.attempts, record.tab_wait_ms)

    async def _click(self, page: Page, locator: Any, deadline: float) -> None:
        """클릭한다. **가려져 있으면 포인터를 먼저 비운다** (2026-09-09 사용자 보고).

        ## 무엇이 문제였나

        보고 문장: 「step9번으로 클릭한 다음에 메뉴에 마우스가 그대로 있어서 확장된
        형태라서 메뉴 뒤에 가려진 원천데이터를 클릭하지 못한다. 측정은 잘되었으나, 재실행시
        클릭한 위치에 마우스가 가게되면서 발생한 문제로 보인다.」

        진단이 맞다. Playwright 의 `click()` 은 포인터를 요소 위로 **옮기고 그대로 둔다.**
        녹화 때는 사람이 곧 다른 곳으로 마우스를 움직이므로 hover 로 열린 메뉴가 접히지만,
        재생 때는 포인터가 그 자리에 머문다.

        그리고 그것이 **교착이 된다.** Playwright 는 클릭 전에 히트 검사를 하는데, 그
        검사는 포인터를 옮기기 **전에** 한다. 그래서 「메뉴가 덮고 있다 → 검사 실패 →
        재시도 → 포인터는 그대로 → 메뉴도 그대로」가 예산이 끝날 때까지 돈다.

        ## 첫 판은 실패한 뒤에 고치려 했다 — 그것으로는 안 됐다

        처음에는 클릭이 실패하면 포인터를 비우고 한 번 더 시도했다. 사용자가 「안 됨」이라고
        답했고, 이유는 둘이다.

        1. **재시도에 남는 예산이 250ms 뿐이다.** 첫 시도가 Step 예산을 통째로 쓰고 실패
           하므로 `_left` 가 하한(`MIN_ACTION_TIMEOUT_MS`)을 돌려준다. 메뉴가 접히는
           전환 시간까지 있으면 그 안에 끝나지 않는다.
        2. **막힌 Step 마다 예산을 통째로 버린다.** 고쳐도 재실행이 Step 당 10초씩 느려진다.

        그래서 **실패를 기다리지 않는다.** 클릭 지점이 가려졌는지 먼저 물어보고
        (`pointer.is_occluded` — 평가 한 번), 가려졌을 때만 포인터를 비운다.

        ## 왜 「항상 비우기」가 아닌가

        모든 클릭 앞에서 포인터를 옮기면 **반대 방향의 흐름이 깨진다**: hover 로 열려
        포인터가 안에 있어야 유지되는 메뉴는 옮기는 순간 접히고, 그 안을 누르려던 클릭이
        실패한다. 가림을 실제로 확인하면 그 흐름은 건드리지 않는다 — 그 경우 대상은
        가려져 있지 않다(메뉴 **안**에 있다).

        재시도는 그대로 남긴다. 가림 확인이 놓치는 경우(전환 중, 확인 자체가 실패)에도
        마지막 한 번의 기회가 있어야 한다.

        가림 판정과 포인터 이동은 `itb.execution.pointer` 가 갖는다 — 그 모듈의 머리말에
        왜 여기 있지 않은지 적어 두었다.
        """
        if await pointer.is_occluded(locator):
            await pointer.park(page)

        try:
            await locator.click(timeout=self._left(deadline))
            return
        except PlaywrightError:
            # 가림 확인이 놓친 경우의 마지막 기회. 이미 실패한 클릭이므로 더 나빠질 것이 없다.
            await pointer.park(page)
            await locator.click(timeout=self._left(deadline))

    async def _upload(self, locator: Any, step: UploadStep, deadline: float) -> None:
        """파일을 올린다 (2026-09-09 사용자 보고).

        ## 무엇을 올리는가 — **같은 이름의 빈 파일**

        정의에 남는 것은 파일 이름뿐이다 (`UploadStep` 의 주석). 그래서 재실행은 그 이름을
        가진 빈 파일을 올린다 — 이름이 같으면 **확장자도 같고**, 사용자가 요구한 것이
        그것이다 (「실제 서비스에서는 확장자를 보는경우가 있기 때문」).

        **디스크에 쓰지 않는다.** Playwright 가 이름·MIME·바이트를 그대로 받으므로
        (``FilePayload``) 임시 파일을 만들 이유가 없다. 처음에는 ``tempfile`` 로 만들었는데,
        그러면 언제 지울지가 문제가 된다 — 실행 중에 지우면 브라우저가 아직 읽는 중일 수
        있고, 안 지우면 남는다. 만들지 않으면 그 문제가 없다.

        ## 한계를 적어 둔다

        내용은 비어 있다. 확장자·이름·MIME 을 보는 검증은 통과하고, **내용을 파싱하는
        검증은 통과하지 못한다** (예: 서버가 xlsx 를 실제로 열어 보는 경우). 그때 실패는
        업로드가 아니라 그 다음 Step 에서 나며, 사용자는 이유를 알기 어렵다.

        그 경우까지 덮으려면 정의가 실제 파일을 가리켜야 하고(경로 또는 첨부), 그것은
        「테스트 정의가 옮겨 다닐 수 있는가」를 건드리는 결정이다 — 지금 요구에 없으므로
        하지 않는다. 대신 이 한계가 어디에 적혀 있는지 남긴다.
        """
        await locator.set_input_files(
            {
                "name": step.file_name,
                "mimeType": mime_type_of(step.file_name),
                "buffer": b"",
            },
            timeout=self._left(deadline),
        )

    async def _close_tab(self, step: CloseTabStep) -> StepExecution:
        """탭 닫기 (FR-030c).

        **이미 닫혀 있거나 열리지 않았으면 통과한다.** 이 Step 의 목표는 대상 탭이 열려
        있지 않은 상태이며, 그 상태는 이미 충족돼 있다. `hidden` 검증이 "처음부터 없던
        경우도 통과" 하는 것과 같은 판정이다 (spec 엣지 케이스).

        이 관용이 필요한 실제 흐름: 녹화 때 사용자가 "닫기" 버튼을 눌러 탭이 닫히면 클릭
        Step 과 닫기 Step 이 함께 남을 수 있다. 재실행에서 클릭이 이미 탭을 닫으므로 닫기
        Step 은 할 일이 없다 — 그것을 실패로 보면 정상 흐름이 실패한다.
        """
        record = StepExecution(tab=step.tab)
        handle = self._session.find_tab(step.tab)

        if handle is None:
            # 아직 열리지 않았을 수 있다. 예산만큼 기다려 보고, 없으면 목표 달성으로 본다.
            started = time.monotonic()
            try:
                handle = await self._session.wait_for_tab(step.tab, step.timeout_ms)
            except TabNotFoundError:
                record.tab_wait_ms = int((time.monotonic() - started) * 1000)
                return record
            record.tab_wait_ms = int((time.monotonic() - started) * 1000)

        if handle.closed:
            return record

        try:
            await handle.page.close()
        except PlaywrightError as exc:
            raise StepFailure(_humanize(exc, step), tab_wait_ms=record.tab_wait_ms) from exc
        return record

    async def _drag(
        self, step: DragStep, root: SearchRoot, deadline: float, record: StepExecution
    ) -> None:
        """끄는 대상과 놓는 위치를 각각 해석해 끌어다 놓는다 (FR-023c).

        `drag_to` 는 실제 마우스 이동(누르기 → 이동 → 놓기)을 수행하므로 HTML5 끌어놓기
        핸들러와 포인터 기반 핸들러 양쪽에서 동작한다.

        **놓는 위치를 못 찾은 것도 실패다.** 끄는 대상만 찾고 진행하면 요소가 엉뚱한 곳에
        떨어지거나 원위치로 돌아가는데, 그 결과는 통과로 보일 수 있다 — 실패보다 나쁘다.
        """
        source = await self._locate(root, step, deadline, record)
        try:
            destination = await resolve(root, step.drop_target, self._left(deadline))
        except ElementNotFoundError as exc:
            # 시도 내역을 합쳐 둔다. 어느 쪽을 못 찾았는지 결과 화면에서 보여야 한다.
            record.attempts = [*record.attempts, *exc.attempts]
            record.element_wait_ms += exc.waited_ms
            msg = f"놓을 위치를 찾을 수 없습니다. {exc}"
            raise StepFailure(
                msg,
                record.attempts,
                record.tab_wait_ms,
                code=_classify_lookup(exc),
                element_wait_ms=record.element_wait_ms,
            ) from exc

        record.attempts = [*record.attempts, *destination.attempts]
        record.disagreement = [*record.disagreement, *destination.disagreement]
        # 두 요소를 각각 기다렸으므로 더한다 — 이 Step 이 실제로 대기에 쓴 시간이다.
        record.element_wait_ms += destination.waited_ms
        await source.locator.drag_to(destination.locator, timeout=self._left(deadline))

    async def _locate(
        self, root: SearchRoot, step: Step, deadline: float, record: StepExecution
    ) -> Resolution:
        """요소를 찾고 시도 내역을 기록에 남긴다."""
        target = getattr(step, "target", None)
        if target is None:  # pragma: no cover - 호출자가 대상 있는 종류만 넘긴다
            msg = "이 Step 에는 대상 요소가 없습니다."
            raise StepFailure(msg, record.attempts, record.tab_wait_ms)
        try:
            located = await resolve(root, target, self._left(deadline))
        except ElementNotFoundError as exc:
            record.attempts = exc.attempts
            record.element_wait_ms += exc.waited_ms
            raise
        record.attempts = located.attempts
        record.disagreement = [*record.disagreement, *located.disagreement]
        record.resolved_candidate = located.strategy.kind.value
        record.element_wait_ms += located.waited_ms
        record.rect = await _measure(located)
        return located

    # ─── 검증 6종 (001 FR-013a + 021) ──────────────────────────────────────

    async def _assert(
        self,
        assertion: Assertion,
        page: Page,
        root: SearchRoot,
        deadline: float,
        record: StepExecution,
    ) -> None:
        match assertion.kind:
            case AssertionKind.URL:
                # 주소 검증만 `page` 를 쓴다 — iframe 안의 Step 이라도 사용자가 뜻한
                # "현재 주소" 는 주소창의 주소다.
                await self._assert_url(assertion, page, deadline)
            case AssertionKind.HIDDEN:
                await self._assert_hidden(assertion, root, deadline, record)
            case AssertionKind.VISIBLE:
                located = await self._locate_target(assertion, root, deadline, record)
                await located.locator.wait_for(
                    state="visible", timeout=self._left(deadline)
                )
            case AssertionKind.TEXT:
                await self._assert_text(assertion, root, deadline, record)
            case AssertionKind.VALUE:
                await self._assert_value(assertion, root, deadline, record)
            case AssertionKind.ENABLED | AssertionKind.DISABLED:
                await self._assert_state(assertion, root, deadline, record)

    async def _assert_url(
        self, assertion: Assertion, page: Page, deadline: float
    ) -> None:
        expected = self._resolver.substitute(assertion.value or "")

        async def observe() -> str:
            return page.url

        ok, actual = await _watch(assertion, observe, expected, deadline)
        if ok:
            return
        msg = f"현재 주소가 {_expectation(expected, assertion.match)}. 실제: {actual!r}"
        raise StepFailure(msg)

    async def _assert_hidden(
        self,
        assertion: Assertion,
        root: SearchRoot,
        deadline: float,
        record: StepExecution,
    ) -> None:
        """`hidden` 은 **처음부터 없던 경우도 통과한다** (spec 엣지 케이스).

        요소를 찾지 못한 것이 곧 조건 충족이므로, 탐색 실패를 실패로 옮기지 않는다.
        """
        try:
            located = await self._locate_target(assertion, root, deadline, record)
        except (ElementNotFoundError, StepFailure):
            return
        await located.locator.wait_for(state="hidden", timeout=self._left(deadline))

    async def _assert_text(
        self,
        assertion: Assertion,
        root: SearchRoot,
        deadline: float,
        record: StepExecution,
    ) -> None:
        """**021 이전에는 기다리지 않았다.** 한 번 읽고 판정했다.

        긍정형에서는 그 차이가 「가끔 실패한다」로 보이지만 부정형에서는 「항상
        통과한다」가 된다 — 부정 조건의 기본 상태가 참이기 때문이다. 그래서 021 은
        부정형을 더하면서 대기 규칙을 `settle` 하나로 합쳤다 (FR-003).

        **대상 요소는 한 번만 찾는다.** 탐색 자체가 이미 기다리고, 매 폴마다 다시
        찾으면 요소가 교체되는 화면에서 어느 요소를 본 것인지 알 수 없어진다.
        """
        expected = self._resolver.substitute(assertion.value or "")
        if assertion.target is None:
            scope = "화면"

            async def observe() -> str:
                return await root.inner_text("body", timeout=self._left(deadline))
        else:
            # 대상을 찾지 못하면 여기서 실패한다 — 긍정·부정 모두 그렇다 (FR-006).
            # 부정형을 통과시키면 「요소가 사라져서 통과」와 「텍스트가 달라서 통과」를
            # 결과에서 구별할 수 없다. 요소가 없을 수도 있는 상황은 `hidden` 이 맡는다.
            located = await self._locate_target(assertion, root, deadline, record)
            scope = "요소"

            async def observe() -> str:
                return await located.locator.inner_text(timeout=self._left(deadline))

        ok, actual = await _watch(assertion, observe, expected, deadline)
        if ok:
            return
        msg = (
            f"{scope}의 텍스트가 {_expectation(expected, assertion.match)}. "
            f"실제: {_clip(actual)!r}"
        )
        raise StepFailure(msg, record.attempts, record.tab_wait_ms)

    async def _assert_value(
        self,
        assertion: Assertion,
        root: SearchRoot,
        deadline: float,
        record: StepExecution,
    ) -> None:
        """입력 칸에 담긴 값을 본다 (023 FR-001).

        ## `_assert_text` 와 무엇이 다른가 — 관찰 함수 하나뿐이다

        대기(`_watch`)·비교(`_matches`)·실패 설명 조립(`_EXPECTATION_VERBS`)을 그대로
        재사용한다. 021 이 관찰 함수를 인자로 받는 구조를 만들어 둔 덕분이며, **이 종류만의
        대기 규칙을 새로 만들지 않는 것**이 명세 FR-005 의 요구다.

        ## 왜 텍스트로는 안 되는가

        ``<input>`` 의 값은 자식 텍스트 노드가 아니라 요소의 값 속성이다. 브라우저는 그것을
        자기만의 내부 구조에 그리는데 `inner_text` 는 거기 닿지 못한다 — 칸이 가득 차 있어도
        **언제나 빈 문자열**이 관찰된다. 023 이 이 종류를 만든 이유가 그것이다.

        ## 대상은 언제나 있다

        ``text`` 검증과 달리 「화면 전체」 경우가 없다 (FR-002). 그래서 분기가 없고, 대상을
        찾지 못하면 긍정·부정 모두 실패한다 (FR-006).
        """
        expected = self._resolver.substitute(assertion.value or "")
        located = await self._locate_target(assertion, root, deadline, record)

        async def observe() -> str:
            return str(await located.locator.input_value(timeout=self._left(deadline)))

        ok, actual = await _watch(assertion, observe, expected, deadline)
        if ok:
            return

        # 023 FR-016 — **비밀번호 칸의 관찰값은 스크러버와 무관하게 가린다.**
        #
        # 스크러버는 그 실행에서 **복호화된** 민감 값만 안다. 검증이 실패했다는 것은
        # 관찰값이 기대값과 다르다는 뜻이고, 다르다는 것은 그 목록에 없다는 뜻이다 —
        # 그래서 **검증이 실패할 때만 새는 구조**였다 (023 research R2).
        #
        # 판정은 이미 실제 값으로 끝났다. 여기서 바뀌는 것은 설명 문자열뿐이므로 원칙 II
        # 의 결정성에 예외가 생기지 않는다.
        shown = _MASKED if await self._is_secret_field(located.locator) else _clip(actual)
        msg = f"입력값이 {_expectation(expected, assertion.match)}. 실제: {shown!r}"
        raise StepFailure(msg, record.attempts, record.tab_wait_ms)

    async def _is_secret_field(self, locator: Any) -> bool:
        """이 대상이 비밀번호 칸인가 (023 FR-016).

        **녹화와 같은 규칙을 쓴다** — ``type`` 속성이 ``password`` 인가. 판별 규칙을 새로
        만들지 않는 이유는, 두 곳이 다르게 판단하면 입력 Step 에서는 가려지고 검증 Step
        에서는 새는 상태가 생기기 때문이다.

        **살아 있는 요소에서 읽는다.** 저장된 정의에 「이것은 비밀번호 칸이다」를 적지
        않는다 — 화면이 바뀌면 옛 판단이 남는다 (023 research R1).

        읽지 못하면 **가리는 쪽으로 판단한다.** 가릴 것을 안 가리는 쪽이 안 가려도 될 것을
        가리는 쪽보다 나쁘다.
        """
        try:
            kind = await locator.get_attribute("type", timeout=_ATTRIBUTE_READ_MS)
        except Exception:  # noqa: BLE001 - 요소가 사라지는 중이면 읽을 수 없다
            return True
        return (kind or "").strip().lower() == "password"

    async def _assert_state(
        self,
        assertion: Assertion,
        root: SearchRoot,
        deadline: float,
        record: StepExecution,
    ) -> None:
        """요소를 조작할 수 있는가 (021 FR-010~FR-014).

        ## `hidden` 과 갈리는 지점 — 대상을 찾지 못하면 **실패한다**

        `_assert_hidden` 은 탐색 실패를 조건 충족으로 옮기지만 여기서는 그러지 않는다.
        「없다」와 「있는데 잠겼다」는 다른 사실이고, 한 검증이 둘을 함께 통과시키면
        결과를 보고 어느 쪽이었는지 알 수 없다 (FR-012). 요소가 없을 수도 있는 상황을
        표현하려는 것이라면 `hidden` 이 그 자리다.

        ## `expect()` 를 쓰지 않는 이유

        `expect(locator).to_be_disabled()` 는 자기 형식의 오류 메시지를 만든다. 020 이
        실행기의 실패 설명을 그대로 `mismatch.observed` 에 싣기 때문에, 문체가 갈리면
        화면의 문구와 저장된 기록이 서로 다른 말을 한다.

        ## 비폼 요소의 한계 — 판정을 바꾸지 않는다

        브라우저는 `<div>` 같은 요소에 대해 「조작할 수 있다」를 참으로 준다. 태그를
        보고 판정을 뒤집으면 원칙 II 의 결정성(같은 화면이면 같은 결과)에 예외가
        생기므로, **실행은 브라우저가 주는 값을 그대로 쓰고 작성 시점에 알린다**
        (`assertion_builder.warn_if_stateless`).
        """
        located = await self._locate_target(assertion, root, deadline, record)
        want_enabled = assertion.kind is AssertionKind.ENABLED

        async def observe() -> str:
            enabled = await located.locator.is_enabled(timeout=self._left(deadline))
            return "enabled" if enabled else "disabled"

        ok, actual = await settle(
            observe, lambda v: (v == "enabled") is want_enabled, deadline
        )
        if ok:
            return
        expectation = "있어야" if want_enabled else "없어야"
        happened = "있었습니다" if actual == "enabled" else "없었습니다"
        msg = f"대상을 조작할 수 {expectation} 하는데 조작할 수 {happened}."
        raise StepFailure(msg, record.attempts, record.tab_wait_ms)

    async def _locate_target(
        self,
        assertion: Assertion,
        root: SearchRoot,
        deadline: float,
        record: StepExecution,
    ) -> Resolution:
        if assertion.target is None:  # pragma: no cover - 스키마가 막는다
            msg = "이 검증에는 대상 요소가 필요합니다."
            raise StepFailure(msg, record.attempts, record.tab_wait_ms)
        located = await resolve(root, assertion.target, self._left(deadline))
        record.attempts = located.attempts
        record.disagreement = [*record.disagreement, *located.disagreement]
        record.resolved_candidate = located.strategy.kind.value
        record.element_wait_ms += located.waited_ms
        # 검증도 요소를 지목한다 — 그 자리를 알리지 않을 이유가 없다 (024 FR-001).
        # 「화면 전체」를 보는 검증은 여기 오지 않으므로 대상 없는 경우가 섞이지 않는다.
        record.rect = await _measure(located)
        return located

    # ─── 시간 예산 ─────────────────────────────────────────────────────────

    async def _settle_transition(self, page: Page, deadline: float) -> int:
        """진행 중인 문서 전환이 끝나기를 기다린다. 기다린 시간(ms)을 돌려준다.

        **실패시키지 않는다.** 전환이 상한 안에 끝나지 않았다는 것은 그 자체로는 판정이
        아니다 — 화면이 아직 아니라면 이어지는 요소 탐색이 남은 예산으로 같은 사실을
        훨씬 정확한 문장으로 알린다(「무엇을 못 찾았는가」). 여기서 던지면 사용자는
        원인을 가리키지 않는 새 실패 유형을 하나 더 읽게 된다.

        **Step 예산을 통째로 쓰지 않는다** (`_TRANSITION_WAIT_MS`). 이 대기는 보조이고,
        판정은 뒤에 온다. 여기서 예산을 다 쓰면 정작 요소를 찾을 시간이 남지 않는다.

        기다린 시간은 `tab_wait_ms` 에 더한다 — 전환이 끝나기를 기다리는 것은 **탭이
        준비되기를 기다리는 일의 일부**이며, 프레임 대기를 `element_wait_ms` 에 넣은
        것과 같은 판단이다. 새 칸을 만들면 읽는 쪽이 셋을 더해야 Step 이 얼마나 기다렸는지
        알게 된다.
        """
        budget = min(self._left(deadline), _TRANSITION_WAIT_MS)
        started = time.monotonic()
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=budget)
        except PlaywrightError:
            # 시간 초과도, 전환 중 페이지가 닫힌 경우도 여기로 온다. 둘 다 이 대기가
            # 판정할 일이 아니다.
            pass
        return int((time.monotonic() - started) * 1000)

    @staticmethod
    def _left(deadline: float) -> int:
        """이 Step 에 남은 시간(ms).

        `MIN_ACTION_TIMEOUT_MS` 아래로 내려가지 않는다 — 0 을 Playwright 에 넘기면
        "무한 대기"로 해석되어 상한이 사라진다 (FR-057).
        """
        return max(int((deadline - time.monotonic()) * 1000), MIN_ACTION_TIMEOUT_MS)


async def _measure(located: Resolution) -> ElementRect | None:
    """채택된 요소의 자리를 잰다 (024 T007·T008).

    **채택된 그 요소에서 읽는다.** 후보 수집이 쓴 CSS 경로로 다시 찾지 않는다 — 우선순위
    전략이 고른 것과 CSS 가 가리키는 것은 다를 수 있고, 다르면 표시된 자리와 조작된
    요소가 갈린다 (024 research R1).

    **무슨 일이 있어도 실행을 멈추지 않는다** (FR-006). 표시는 곁가지이고, 그것 때문에
    테스트가 실패하면 안 된다 — `BrowserToolbox._announce` 가 같은 규칙으로 되어 있다.
    측정이 안 되면 자리가 없는 것으로 본다.

    **여기서 기다리지 않는다.** 요소는 이미 채택됐고, 자리를 재느라 Step 의 시간 예산을
    더 쓰면 표시가 실행을 느리게 만든다 (FR-057 의 취지).
    """
    try:
        return ElementRect.of(await located.locator.bounding_box(timeout=_RECT_READ_MS))
    except Exception:  # noqa: BLE001 - 요소가 사라지는 중일 수 있다. 자리만 잃는다
        return None


async def settle(
    observe: Callable[[], Awaitable[str]],
    holds: Callable[[str], bool],
    deadline: float,
    poll_ms: int = 50,
) -> tuple[bool, str]:
    """조건이 참이 될 때까지 다시 보고, 참이면 즉시 끝낸다 (021 FR-003·FR-004).

    값 비교 검증과 상태 검증이 **모두 이것을 쓴다.** 021 이전에는 주소 검증만 기다리고
    텍스트 검증은 한 번 읽고 판정했는데, 그 위에 부정형을 얹으면 화면이 준비되기 전에
    평가해 조용히 통과하는 검증이 대량으로 만들어진다.

    돌려주는 것은 `(참이 되었는가, 마지막 관찰값)` 이다. **마지막 값이 필요한 이유**는
    실패 설명에 「실제로는 무엇이었는가」가 들어가야 하고, 020 이 그 문자열을 그대로
    어긋남 기록에 싣기 때문이다.

    제한 시간이 이미 지났어도 **한 번은 본다.** 앞선 Step 이 예산을 다 쓴 경우에
    그런데, 한 번도 보지 않으면 적을 관찰값이 없어 어긋남 기록이 빈 문자열을 받는다 —
    그것은 「화면이 비어 있었다」로 읽히는 거짓 기록이다.

    **부정 조건에는 이것을 쓰지 않는다.** `hold` 가 그 자리다 — 아래를 보라.
    """
    observed = await observe()
    if holds(observed):
        return True, observed
    while time.monotonic() < deadline:
        await asyncio.sleep(poll_ms / 1000)
        observed = await observe()
        if holds(observed):
            return True, observed
    return False, observed


async def hold(
    observe: Callable[[], Awaitable[str]],
    holds: Callable[[str], bool],
    deadline: float,
    poll_ms: int = 50,
) -> tuple[bool, str]:
    """조건이 제한 시간 **동안 유지되는지** 지켜본다 (021 FR-003a).

    ## 왜 부정 조건은 `settle` 과 달라야 하는가

    「`오류` 가 없다」는 **기본 상태가 참**이다. 클릭 직후 화면이 비어 있는 찰나에
    평가하면 통과한다 — 그리고 0.8초 뒤에 오류가 떠도 아무도 모른다. 결과 화면에는
    초록색이 찍히지만 그 통과는 아무것도 검증하지 않았다.

    긍정과 부정은 **시간에 대해 비대칭**이다.

    | | 「X 가 나타난다」 | 「X 가 없다」 |
    |---|---|---|
    | 한 번 참이면 | 끝이다 — 나타났다는 사실은 변하지 않는다 | **아무것도 말하지 않는다** — 다음 순간 나타날 수 있다 |
    | 제한 시간의 뜻 | 얼마나 기다려 줄까 (상한) | **언제까지 없어야 하나** (관찰 기간) |

    그래서 부정 검증은 제한 시간을 **항상 소모한다.** 이것은 비효율이 아니라 그
    검증이 묻는 질문의 성질이다 — 「지금 없다」를 묻는 검증은 쓸모가 없고, 사용자가
    뜻한 것은 언제나 「이 동안 없다」다.

    거짓이 되는 **즉시** 끝낸다. 그때의 관찰값이 실패 설명에 들어간다.
    """
    observed = await observe()
    if not holds(observed):
        return False, observed
    while time.monotonic() < deadline:
        await asyncio.sleep(poll_ms / 1000)
        observed = await observe()
        if not holds(observed):
            return False, observed
    return True, observed


async def _watch(
    assertion: Assertion,
    observe: Callable[[], Awaitable[str]],
    expected: str,
    deadline: float,
) -> tuple[bool, str]:
    """값 비교 검증의 대기. **긍정이면 기다리고, 부정이면 지켜본다.**

    고르는 판단을 한곳에 둔다 — 주소 검증과 텍스트 검증이 각자 고르면 둘이 갈릴 자리가
    생기고, 그때 「부정 검증이 왜 주소에서만 즉시 통과하는가」를 설명할 말이 없다.
    """
    watcher = hold if assertion.negated else settle
    return await watcher(observe, lambda v: _matches(v, expected, assertion.match), deadline)


def _matches(actual: str, expected: str, mode: MatchMode) -> bool:
    """비교 판정. **부정형은 긍정형의 부정으로 정의한다** (021).

    따로 쓰면 두 갈래가 갈린다 — 예컨대 `equals` 만 양끝 공백을 다듬고 `not_equals` 는
    다듬지 않는 식의 어긋남이 생기고, 그때 어느 쪽이 맞는지 판단할 근거가 없다.
    """
    if mode is MatchMode.CONTAINS:
        return expected in actual
    if mode is MatchMode.NOT_CONTAINS:
        return expected not in actual
    if mode is MatchMode.NOT_EQUALS:
        return actual.strip() != expected.strip()
    return actual.strip() == expected.strip()


_EXPECTATION_VERBS = {
    MatchMode.EQUALS: "와 같아야 하는데 다릅니다",
    MatchMode.CONTAINS: "를 포함해야 하는데 없습니다",
    MatchMode.NOT_EQUALS: "와 달라야 하는데 같습니다",
    MatchMode.NOT_CONTAINS: "를 포함하지 않아야 하는데 포함했습니다",
}
"""실패 설명의 뒷부분. **기대와 실제가 모두 읽혀야 한다** (021 FR-005).

020 이 이 문자열을 그대로 어긋남 기록에 싣는다 — 긍정형과 부정형의 문체가 갈리면
화면의 문구와 저장된 기록이 서로 다른 말을 하게 된다.
"""


def _expectation(expected: str, mode: MatchMode) -> str:
    return f"{expected!r}{_EXPECTATION_VERBS[mode]}"


_MASKED = "********"
"""민감한 칸의 관찰값 자리에 넣는 문구 (023 FR-016).

길이를 드러내지 않는 고정 길이다 — 실제 길이를 보이면 그 자체가 정보다.
"""

_TRANSITION_WAIT_MS = 5_000
"""앞선 Step 이 일으킨 화면 전환을 기다려 주는 상한.

Step 예산(기본 10초)보다 **짧다.** 전환이 5초 안에 끝나지 않는 화면이라면 기다림이
부족한 것이 아니라 그 화면이 느린 것이고, 그때 사용자에게 필요한 것은 조용한 대기가
아니라 「무엇을 못 찾았는가」다. 남은 예산은 그 판정에 쓴다.
"""

_RECT_READ_MS = 1_000
"""요소의 자리를 읽는 데 주는 시간 (024). `_ATTRIBUTE_READ_MS` 와 같은 판단으로 짧다 —
이것은 표시를 위한 것이고, 여기서 오래 매달리면 실행이 느려질 뿐이다.
"""

_ATTRIBUTE_READ_MS = 1_000
"""대상 성질을 읽는 데 주는 시간. 짧게 잡는다 — 판정은 이미 끝났고 이것은 설명을 만드는
중이다. 여기서 오래 매달리면 실패 보고가 느려질 뿐이다.
"""


def _clip(text: str, limit: int = 200) -> str:
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "…"


def _classify_lookup(exc: ElementNotFoundError) -> ErrorCode:
    """요소 탐색 실패의 세 갈래 (004 FR-120·FR-123).

    **문구가 아니라 예외가 든 사실로 가른다.** 화면이 메시지를 파싱해 분류하게 두면
    문구를 다듬는 순간 분류가 깨진다.

    | 상황 | 코드 | 사용자가 할 일 |
    |---|---|---|
    | 시도할 후보가 없다 | `STEP_FAILED` | 정의를 고친다. 기다려도 달라지지 않는다 |
    | 예산 안에 아무도 하나를 못 가리켰다 | `ELEMENT_NOT_READY` | 예산을 늘리거나 화면을 확인한다 |
    | 예산 안에 여러 개만 매칭됐다 | `ELEMENT_AMBIGUOUS` | 대상을 다시 집는다 |
    """
    if exc.ambiguous:
        return ErrorCode.ELEMENT_AMBIGUOUS
    if exc.timed_out:
        return ErrorCode.ELEMENT_NOT_READY
    return ErrorCode.STEP_FAILED


def _classify(exc: PlaywrightError, step: Step) -> ErrorCode:
    """실패의 출처를 가른다 (003 AP-031·AP-033).

    페이지를 여는 도중 난 실패는 **대상 쪽 사정**이다. 그것을 요소 탐색 실패와 같은
    코드로 내보내면 사용자는 자기 테스트 정의를 고치려 들고, 고칠 것이 없어 헤맨다.
    """
    if isinstance(step, NavigateStep) or "navigating to" in str(exc.message):
        return ErrorCode.TARGET_UNREACHABLE
    return ErrorCode.STEP_FAILED


_INTERCEPT_MARK = "intercepts pointer events"
"""Playwright 가 "다른 요소가 포인터를 가로막았다" 고 말할 때 쓰는 문구."""

_OPEN_TAG = re.compile(r"<[a-zA-Z][^>]{0,120}>")


def _blocker(full: str) -> str | None:
    """포인터를 가로막은 요소의 여는 태그. 알아보지 못하면 None.

    Playwright 의 호출 기록은 두 형태로 말한다.

        <blocker> intercepts pointer events
        <blocker> from <ancestor>…</ancestor> subtree intercepts pointer events

    어느 쪽이든 **그 항목의 첫 여는 태그**가 가로막은 요소다. 뒤의 `<ancestor>` 를 잡으면
    사용자에게 엉뚱한 것을 지목해 보여 준다.

    **원문 전체를 받아야 한다.** 사용자에게 붙이는 원문은 길이를 자르는데, 실측(TC-007)에서
    그 절단이 `subtree` 를 `su` 로 끊어 이 문구 자체를 잘라 냈다. 잘린 문자열에서 찾으면
    정작 이 판정이 필요한 실패에서 판정이 되지 않는다.
    """
    at = full.find(_INTERCEPT_MARK)
    if at < 0:
        return None
    item = full[:at].rsplit(" - ", 1)[-1]
    found = _OPEN_TAG.search(item)
    return found.group(0) if found else None


def _humanize(exc: PlaywrightError, step: Step) -> str:
    """Playwright 오류를 사용자 문장으로 바꾼다 (FR-054).

    원문을 버리지 않는다 — 사람이 읽을 문장을 앞에 두고 원인을 뒤에 붙인다.

    **페이지 이동 실패를 요소 탐색 실패와 같은 문장으로 말하지 않는다** (003 AP-031).
    "대상 요소가 나타나지 않았다" 는 대상 사이트가 응답을 끝내지 않은 상황을 잘못
    설명하고, 사용자를 없는 문제로 보낸다.
    """
    full = " ".join(str(exc.message).split())
    # 사용자에게 붙이는 원문만 자른다. **판정은 전체 문장으로 한다** — 절단이 판정에
    # 필요한 문구를 잘라 내면, 잘릴 만큼 긴 실패에서만 판정이 실패한다.
    raw = full[:400]
    timed_out = "Timeout" in full or "timeout" in full
    if _classify(exc, step) is ErrorCode.TARGET_UNREACHABLE:
        what = (
            f"{step.timeout_ms}ms 안에 응답을 끝내지 않았습니다"
            if timed_out
            else "페이지를 열 수 없었습니다"
        )
        return f"{step.label}: 대상 사이트가 {what}. ({raw})"
    if _INTERCEPT_MARK in full:
        # **요소를 못 찾은 것과 갈라 말한다.** 여기서는 요소를 찾았고, 다른 요소가 그 위를
        # 덮고 있어 포인터가 닿지 않았을 뿐이다. 한 문장으로 뭉뚱그리면 사용자는 있지도
        # 않은 "요소가 안 나타나는 문제" 를 찾아 헤맨다 — 실측(TC-007)에서 후보는 1개를
        # 정확히 매칭했는데(`matched: true`) 메시지는 "나타나지 않았거나" 라고 말했다.
        covered = _blocker(full) or "다른 요소"
        return (
            f"{step.label}: 대상 요소는 찾았지만 {covered} 이(가) 위를 덮고 있어 "
            f"{step.timeout_ms}ms 동안 동작할 수 없었습니다. 로딩 표시나 모달이 걷히기를 "
            f"기다리는 검증을 앞에 두거나, 그 Step 이 필요한지 다시 보세요. ({raw})"
        )
    if timed_out:
        return (
            f"{step.label} 이(가) {step.timeout_ms}ms 안에 끝나지 않았습니다. "
            f"대상 요소가 나타나지 않았거나 동작이 막혔습니다. ({raw})"
        )
    return f"{step.label} 실행에 실패했습니다. ({raw})"
