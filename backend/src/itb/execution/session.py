"""브라우저 세션 관리. 헌법 원칙 III (research R1).

**핵심 통찰: 일시정지는 브라우저에 대한 조작이 아니다.** 장수명 `BrowserContext` 를 유지한 채
"명령 전송을 멈추는 것"만으로 인증 상태·화면 위치·입력 내용·페이지 내 JS 상태가 그대로 남는다.
따라서 FR-032(세션 종료 금지)와 FR-038(재시작 없이 이어서 실행)은 상태 저장·복원 로직이 아니라
**태스크 일시 중단**으로 달성된다. 실측(T003)으로 확인했다.

**제약**: Playwright 객체는 생성된 이벤트 루프에 묶인다. 모든 호출은 FastAPI 메인 루프에서
일어나야 한다. `run_in_threadpool` 로 감싸면 안 된다.

멀티 탭(FR-030)은 `BrowserContext` 하나에 여러 `Page` 를 두어 지원한다. `add_init_script` 와
`expose_binding` 을 **컨텍스트 단위로** 등록했기 때문에 새 탭에 리코더가 자동 주입된다 —
멀티 탭이 사실상 공짜로 따라오는 이유다 (research R2, T004 로 확인).
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from playwright.async_api import Browser, BrowserContext, Page, Playwright

from itb.domain.test_case import MAX_TABS_DEFAULT
from itb.execution.state_machine import (
    Command,
    SessionState,
    next_state,
)


class SessionError(Exception):
    """세션 관련 오류."""


class TabLimitReachedError(SessionError):
    """동시 탭 상한 초과 (FR-030g)."""


class TabNotFoundError(SessionError):
    """Step 이 참조하는 탭이 없다 (FR-030d)."""


@dataclass(slots=True)
class TabHandle:
    """탭 하나. **`tab_index` 는 재사용하지 않는다** (data-model §8 불변식).

    닫힌 탭도 목록에서 제거하지 않는다 — 번호가 밀리면 저장된 Step 의 `tab` 참조가
    다른 탭을 가리키게 된다.
    """

    tab_index: int
    page: Page
    opened_at: datetime
    closed: bool = False

    @property
    def url(self) -> str:
        with contextlib.suppress(Exception):
            return self.page.url
        return ""

    async def title(self) -> str:
        if self.closed:
            return ""
        try:
            return await self.page.title()
        except Exception:  # noqa: BLE001 - 닫히는 중이면 제목을 못 읽는다
            return ""


EventSink = Callable[[str, dict[str, object]], Awaitable[None]]
"""세션이 이벤트를 내보내는 통로. (type, payload) 를 받는다."""

PageObserver = Callable[[Page], None]
"""새 탭을 관찰할 대상. 리코더가 네비게이션·탭 닫힘 감시를 붙이는 데 쓴다."""


@dataclass(slots=True)
class BrowserSession:
    """세션 하나 = Browser 1 + BrowserContext 1 + Page 여러 개."""

    session_id: str
    browser: Browser
    context: BrowserContext
    state: SessionState
    tabs: list[TabHandle] = field(default_factory=list)
    active_tab_index: int = 0
    mirrored_tab_index: int = 0
    test_id: str | None = None
    current_step_index: int = 0
    """다음에 실행할 Step 위치.

    **세션이 소유한다.** 상태 전이 이벤트가 이 값을 함께 실어 보내야 하므로
    (contracts/websocket.md `state_changed`), API 계층에 사본을 두면 두 값이 어긋난다.
    """

    max_tabs: int = MAX_TABS_DEFAULT
    edit_warnings: list[str] = field(default_factory=list)
    _resume: asyncio.Event = field(default_factory=asyncio.Event)
    _next_tab_index: int = 0
    _sink: EventSink | None = None
    _tab_opened: asyncio.Event = field(default_factory=asyncio.Event)
    _page_observer: PageObserver | None = None
    """새 탭이 열렸을 때 알려 줄 대상. 리코더가 등록한다.

    세션이 리코더를 직접 임포트하지 않는 이유는 방향이다 — 리코더가 세션을 임포트하므로
    반대 방향을 두면 고리가 생긴다. 훅 하나로 방향을 유지한다.
    """

    # ─── 이벤트 ─────────────────────────────────────────────────────────────

    def attach_sink(self, sink: EventSink | None) -> None:
        self._sink = sink

    async def emit(self, event_type: str, **payload: object) -> None:
        """이벤트를 내보낸다. 통로가 없거나 실패해도 실행에 영향을 주지 않는다.

        미러 프레임이 끊겨도 `step_*` 이벤트가 계속 흐르는 것과 같은 이유다 (FR-047b).
        """
        if self._sink is None:
            return
        with contextlib.suppress(Exception):
            await self._sink(event_type, payload)

    # ─── 상태 전이 ──────────────────────────────────────────────────────────

    async def apply(self, command: Command) -> SessionState:
        """명령을 적용한다. 정의되지 않은 조합이면 `InvalidTransitionError` (FR-043a)."""
        new_state = next_state(self.state, command)
        if new_state is self.state and command is not Command.EDIT_STEPS:
            return self.state
        self.state = new_state
        if command is Command.PAUSE:
            self._resume.clear()
        elif command in (Command.RESUME, Command.RUN_FROM):
            self._resume.set()
        await self.emit(
            "state_changed",
            state=new_state.value,
            current_step_index=self.current_step_index,
            active_tab=self.active_tab_index,
        )
        return new_state

    # ─── 일시정지 / 이어서 실행 (원칙 III) ─────────────────────────────────

    async def wait_until_resumed(self) -> None:
        """일시정지 해제를 기다린다.

        **브라우저에 아무 명령도 보내지 않는다.** 이것이 원칙 III 의 전부다.
        """
        await self._resume.wait()

    @property
    def is_paused(self) -> bool:
        return not self._resume.is_set()

    def mark_running(self) -> None:
        self._resume.set()

    # ─── 탭 (FR-030) ───────────────────────────────────────────────────────

    def register_tab(self, page: Page) -> TabHandle:
        """새 탭에 번호를 부여한다. 열린 순서이며 재사용하지 않는다 (FR-030a·FR-030b)."""
        open_count = sum(1 for t in self.tabs if not t.closed)
        if open_count >= self.max_tabs:
            msg = (
                f"동시에 열린 탭이 상한({self.max_tabs})에 도달했습니다. "
                "기록을 중단합니다."
            )
            raise TabLimitReachedError(msg)

        handle = TabHandle(
            tab_index=self._next_tab_index,
            page=page,
            opened_at=datetime.now(UTC),
        )
        self._next_tab_index += 1
        self.tabs.append(handle)
        self._tab_opened.set()
        self._tab_opened = asyncio.Event()
        return handle

    def attach_page_observer(self, observer: PageObserver | None) -> None:
        """새 탭 통보 대상을 등록한다. 리코더가 `install()` 에서 부른다."""
        self._page_observer = observer

    def notify_page(self, page: Page) -> None:
        """새 탭이 열렸음을 관찰자에게 알린다. 실패해도 탭 등록에 영향을 주지 않는다."""
        if self._page_observer is None:
            return
        with contextlib.suppress(Exception):
            self._page_observer(page)

    def tab_of(self, page: Page) -> TabHandle | None:
        """페이지가 어느 탭인지. `expose_binding` 의 source 를 tab_index 로 바꿀 때 쓴다."""
        for t in self.tabs:
            if t.page is page:
                return t
        return None

    def find_tab(self, tab_index: int) -> TabHandle | None:
        for t in self.tabs:
            if t.tab_index == tab_index:
                return t
        return None

    def mark_closed(self, page: Page) -> TabHandle | None:
        handle = self.tab_of(page)
        if handle is not None:
            handle.closed = True
        return handle

    def open_tabs(self) -> list[TabHandle]:
        return [t for t in self.tabs if not t.closed]

    async def wait_for_tab(self, tab_index: int, timeout_ms: int) -> TabHandle:
        """대상 탭이 열리기를 기다린다 (FR-030d).

        상한을 넘기면 **어느 탭을 기다렸는지** 명시해 실패시킨다.
        """
        deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
        while True:
            handle = self.find_tab(tab_index)
            if handle is not None:
                if handle.closed:
                    msg = (
                        f"탭 {tab_index} 은 이미 닫혀 있습니다. "
                        "녹화 때와 다른 순서로 탭이 열렸거나 닫혔을 수 있습니다."
                    )
                    raise TabNotFoundError(msg)
                return handle
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                msg = (
                    f"탭 {tab_index} 이 열리기를 {timeout_ms}ms 기다렸으나 열리지 "
                    "않았습니다. 대상 앱이 탭을 녹화 때와 다른 순서로 열었을 수 있습니다."
                )
                raise TabNotFoundError(msg)
            waiter = self._tab_opened
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(waiter.wait(), timeout=remaining)

    async def bring_tab_to_front(self, tab_index: int) -> None:
        """조작 국면에서 대상 탭을 앞으로 가져온다 (FR-023a·FR-030e)."""
        handle = self.find_tab(tab_index)
        if handle is None or handle.closed:
            return
        self.active_tab_index = tab_index
        with contextlib.suppress(Exception):
            await handle.page.bring_to_front()

    # ─── 편집 경고 (FR-040b) ───────────────────────────────────────────────

    def add_edit_warning(self, message: str) -> None:
        if message not in self.edit_warnings:
            self.edit_warnings.append(message)

    async def publish_edit_warnings(self) -> None:
        """쌓인 편집 경고를 이벤트로 내보낸다 (FR-040b, contracts/websocket.md).

        REST 응답에도 같은 목록이 실린다. 이벤트가 별도로 필요한 이유는, 편집을 요청한
        클라이언트가 아닌 화면(다른 탭에서 같은 세션을 보고 있는 경우)도 경고를 알아야
        하기 때문이다.
        """
        if not self.edit_warnings:
            return
        await self.emit("edit_warning", messages=list(self.edit_warnings))

    def take_edit_warnings(self) -> list[str]:
        out = list(self.edit_warnings)
        self.edit_warnings.clear()
        return out


class SessionManager:
    """세션 소유자. **브라우저 수명을 HTTP 요청 수명에서 분리한다** (research R1).

    `async_playwright().start()` 를 FastAPI lifespan 에서 1회 호출하고 앱 종료 시 `stop()`
    한다. `async with` 컨텍스트 매니저는 쓰지 않는다 — 블록을 벗어날 때 드라이버가 닫힌다.
    """

    def __init__(self, playwright: Playwright) -> None:
        self._pw = playwright
        self._sessions: dict[str, BrowserSession] = {}
        self._by_test: dict[str, str] = {}

    # ─── 조회 ───────────────────────────────────────────────────────────────

    def get(self, session_id: str) -> BrowserSession | None:
        return self._sessions.get(session_id)

    def require(self, session_id: str) -> BrowserSession:
        s = self._sessions.get(session_id)
        if s is None:
            msg = f"세션을 찾을 수 없습니다: {session_id}"
            raise SessionError(msg)
        return s

    def active_session_for_test(self, test_id: str) -> str | None:
        """FR-043 — 테스트당 동시 실행 1건."""
        return self._by_test.get(test_id)

    def all_sessions(self) -> list[BrowserSession]:
        return list(self._sessions.values())

    # ─── 생성·종료 ─────────────────────────────────────────────────────────

    async def create(
        self,
        start_url: str,
        test_id: str | None = None,
        headless: bool = False,
        max_tabs: int = MAX_TABS_DEFAULT,
        test_id_attribute: str = "data-testid",
    ) -> BrowserSession:
        """세션을 만든다.

        `headless=False` 가 기본이다 — 조작 국면은 실제 창을 요구하고(clarify 결정 3),
        스크린캐스트는 headed 에서도 동작한다(T006 실측). 모드를 하나로 유지한다.
        """
        if test_id is not None and test_id in self._by_test:
            msg = f"이미 실행 중인 세션이 있습니다: {test_id}"
            raise SessionError(msg)

        # testId 속성명은 대상 앱마다 다르다 (research R4).
        with contextlib.suppress(Exception):
            self._pw.selectors.set_test_id_attribute(test_id_attribute)

        browser = await self._pw.chromium.launch(headless=headless)
        context = await browser.new_context()

        session = BrowserSession(
            session_id=uuid.uuid4().hex,
            browser=browser,
            context=context,
            state=SessionState.STARTING,
            test_id=test_id,
            max_tabs=max_tabs,
        )

        # 새 탭 감지 — target=_blank 와 window.open 양쪽 모두에서 발생한다 (T005 실측).
        def on_page(page: Page) -> None:
            try:
                handle = session.register_tab(page)
            except TabLimitReachedError as exc:
                asyncio.create_task(  # noqa: RUF006 - 이벤트 통보는 대기하지 않는다
                    session.emit("tab_limit_reached", limit=session.max_tabs, message=str(exc))
                )
                return
            page.on("close", lambda _p=page: self._on_tab_closed(session, _p))
            # 리코더에게 새 탭을 알린다 — 네비게이션·탭 닫힘 감시가 여기서 붙는다.
            session.notify_page(page)
            asyncio.create_task(  # noqa: RUF006
                self._announce_tab(session, handle)
            )

        context.on("page", on_page)

        page = await context.new_page()
        if session.tab_of(page) is None:  # on_page 가 먼저 돌지 않은 경우 대비
            session.register_tab(page)
        await page.goto(start_url)

        self._sessions[session.session_id] = session
        if test_id is not None:
            self._by_test[test_id] = session.session_id
        return session

    @staticmethod
    async def _announce_tab(session: BrowserSession, handle: TabHandle) -> None:
        """`tab_opened` 를 계약 형태로 발행한다 (contracts/websocket.md).

        제목은 await 가 필요하므로 태스크에서 읽는다. 막 열린 탭은 제목이 비어 있을 수
        있다 — 빈 문자열을 그대로 보낸다. 없는 값을 채워 넣지 않는다.
        """
        await session.emit(
            "tab_opened",
            tab=handle.tab_index,
            url=handle.url,
            title=await handle.title(),
        )

    def _on_tab_closed(self, session: BrowserSession, page: Page) -> None:
        handle = session.mark_closed(page)
        if handle is not None:
            asyncio.create_task(  # noqa: RUF006
                session.emit("tab_closed", tab=handle.tab_index)
            )

    async def close(self, session_id: str) -> None:
        """세션을 종료한다.

        **`PAUSED`·`AI_BLOCKED` 에서 이 함수를 호출하는 것은 불변식 1 위반이다.**
        호출자가 먼저 `STOP` 명령을 적용해야 한다.
        """
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        if session.test_id is not None:
            self._by_test.pop(session.test_id, None)
        with contextlib.suppress(Exception):
            await session.context.close()
        with contextlib.suppress(Exception):
            await session.browser.close()

    async def close_all(self) -> None:
        for sid in list(self._sessions):
            await self.close(sid)
