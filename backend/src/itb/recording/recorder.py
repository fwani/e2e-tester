"""Recorder. FR-024~FR-030·FR-082a·FR-083 (T054·T055·T056·T057·T058·T157).

`add_init_script` 와 `expose_binding` 을 **`Page` 가 아니라 `BrowserContext` 에** 등록한다.
그래서 이후 열리는 모든 탭에 리코더와 콜백 채널이 자동으로 주입된다 — 멀티 탭이 사실상
공짜로 따라오는 이유다 (research R2, T004 로 확인).

**T157 (analyze C2) — 파이프라인 순서가 보안 요건이다.**

    수집 → 검증 → **민감 값 치환** → Step 생성 → 이벤트 발행

민감 값 치환이 이벤트 발행보다 **반드시 먼저** 일어나야 한다. 순서가 뒤바뀌면 비밀번호
평문이 프론트에 도달한다. `_build_step` 이 치환을 끝낸 Step 만 돌려주고, 이벤트는 그 Step
으로만 만들어진다 — 평문이 이벤트 페이로드에 들어갈 경로가 구조적으로 없다.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import pathlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from nacl.public import PublicKey
from playwright.async_api import Frame, Page

from itb.domain.locator import TargetLocator
from itb.domain.step import (
    Author,
    ClickStep,
    CloseTabStep,
    DragStep,
    FillStep,
    HoverStep,
    NavigateStep,
    SelectStep,
    Step,
    UploadStep,
)
from itb.execution.element_probe import collect_and_verify
from itb.execution.frame_resolver import SearchRoot
from itb.execution.session import BrowserSession, TabLimitReachedError
from itb.locator.strategy import StrategyKind, ordered_strategies
from itb.recording.repick import RepickController
from itb.secrets.capture import SensitiveCapture, SensitiveCapturer
from itb.secrets.store import SecretStore

INJECTED_SCRIPT = pathlib.Path(__file__).parent / "injected" / "recorder.js"
BINDING_NAME = "__itbRecord"
NAV_DEDUPE_MS = 3000
"""클릭이 유발한 네비게이션을 별도 Step 으로 만들지 않는 시간창.

클릭 Step 이 재실행 시 같은 이동을 다시 만들므로, 이동을 별도 Step 으로 두면 같은 사건이
두 번 표현된다 (FR-030b, research R2).

**시간창만으로는 판정이 타이밍에 따라 흔들린다.** 그래서 탭별 인과 플래그와 함께 쓴다.

플래그는 세 조건을 모두 만족할 때만 억제한다.

1. 그 탭에서 클릭이 있었다
2. 그 클릭 이후 **다른 Step 이 기록되지 않았다** — 다른 Step 이 기록됐다면 페이지가
   그대로 살아 있었다는 뜻이므로 그 클릭은 이동을 유발하지 않았다
3. 시간창 안이다

조건 2가 핵심이다. 없으면 "이동을 유발하지 않은 클릭 → 다른 동작 → 뒤로 가기" 흐름에서
정당한 이동이 잘못 억제된다.
"""

HOVER_DEDUPE_MS = 1500
"""같은 요소의 hover 를 한 번으로 접는 시간창.

메뉴를 열었다 닫았다 하는 동안 같은 Step 이 쌓이는 것을 막는다. 클릭보다 길게 잡은
이유는, hover 는 의도적으로 반복되는 동작이 아니기 때문이다.
"""

CLICK_DEDUPE_MS = 700
"""같은 요소의 클릭을 한 번으로 접는 시간창.

`pointerdown` 과 `click` 이 같은 클릭에 대해 둘 다 온다. 사람이 같은 버튼을 의도적으로
두 번 누르는 간격보다는 짧고, 한 클릭의 두 이벤트 간격보다는 넉넉하게 잡았다.
"""

@dataclass(frozen=True, slots=True)
class Origin:
    """동작이 일어난 자리. **탭과 문서를 함께 든다.**

    주입 스크립트는 모든 프레임에서 돌기 때문에, 같은 탭 안에서도 동작이 어느 문서에서
    일어났는지가 갈린다. 그것을 구별하지 않으면 두 가지가 동시에 깨진다.

    1. **후보 검증이 엉뚱한 문서에서 일어난다.** iframe 안의 클릭을 main frame 기준으로
       검증하면 `role`·`text` 후보가 전부 미수집으로 깎이고, 주입 스크립트가 프레임 안에서
       잰 CSS 만 `verified` 로 남는다. 그 Step 은 실행이 main frame 을 뒤지므로 반드시
       실패하는데 녹화 화면에는 아무 이상이 보이지 않는다.
    2. **중복 제거 키가 프레임을 넘어 섞인다.** `main#app-main > div` 같은 범용 경로는
       프레임마다 따로 존재하므로, 탭만으로 키를 만들면 서로 다른 문서의 요소가 같은
       Step 으로 접힌다.
    """

    page: Page
    """탭 자체. 화면 이동과 주소는 언제나 이쪽이다."""

    root: SearchRoot
    """후보를 수집·검증할 문서. main frame 이면 `page` 와 같다."""

    tab: int
    frame_url: str | None
    """하위 프레임에서 온 동작이면 그 프레임의 주소, main frame 이면 None.

    None 이 main frame 을 뜻하므로 기존 정의는 그대로 남는다 — 실행도 이 값이 없으면
    프레임 해석을 아예 지나지 않는다.
    """

    def key(self, css: str) -> tuple[int, str]:
        """중복 제거·후보 재사용 키. **프레임을 포함한다.**

        main frame 에서는 프레임 부분이 비므로 기존 키와 같은 값이 나온다.
        """
        return (self.tab, css if self.frame_url is None else f"{self.frame_url}|{css}")


StepSink = Callable[[Step, int], Awaitable[None]]
"""(step, insert_index) 를 받아 Step 목록에 넣고 이벤트를 발행한다."""


@dataclass(slots=True)
class Recorder:
    """한 세션의 녹화기.

    Step 목록을 직접 소유하지 않는다 — `sink` 를 통해 세션의 작업 중 목록에 넣는다.
    그래야 일시정지 중 삽입 위치를 세션이 정할 수 있다 (FR-036).
    """

    session: BrowserSession
    sink: StepSink
    test_id_attribute: str = "data-testid"
    store: SecretStore | None = None
    public_key: PublicKey | None = None
    key_source: Callable[[], PublicKey | None] | None = None
    """봉인 시점의 공개키를 구한다. 포착기에 그대로 넘긴다 (`SensitiveCapturer.key_source`)."""

    id_allocator: Callable[[], str] | None = None
    """Step id 할당기. 주면 그것을 쓴다.

    리코더는 Step 목록을 소유하지 않으므로(sink 로 넘긴다) 이미 쓰인 번호를 알 수 없다.
    목록을 가진 쪽이 할당기를 주면 편집으로 추가된 Step 과 번호가 충돌하지 않는다.
    """

    repick: RepickController = field(default_factory=RepickController)
    """다시 집기 대기 (FR-020).

    **녹화가 꺼져 있어도 동작한다.** 다시 집기는 일시정지 중에 쓰는 기능이고, 그때
    리코더는 멈춰 있다. `active` 게이트 앞에서 처리하는 이유가 이것이다.
    """

    active: bool = False
    author: Author = Author.HUMAN
    insert_at: int | None = None
    """None 이면 목록 끝에 붙인다. 일시정지 중이면 그 위치에 삽입한다."""

    _step_seq: int = 0
    _last_click_ms: float = 0.0
    _last_fill_key: tuple[int, str] | None = None
    _last_step_id: str | None = None
    _last_step_label: str | None = None
    _fill_step_ids: dict[tuple[int, str], str] = field(default_factory=dict)
    """(탭, CSS) → 그 요소의 최근 fill Step id. 중복 제거의 근거다."""

    _fill_values: dict[tuple[int, str], str] = field(default_factory=dict)
    _fill_targets: dict[tuple[int, str], TargetLocator] = field(default_factory=dict)
    """(탭, CSS) → 그 요소에 대해 **가장 잘 검증된** 후보 묶음.

    같은 요소의 확정 이벤트가 화면 이동과 겹치면 재수집 결과가 전부 미수집으로 나온다.
    그때 새 결과로 덮어쓰면 이미 확보한 후보를 잃는다 — 그래서 더 나은 쪽을 남긴다.
    """

    _hover_seen: dict[tuple[int, str], float] = field(default_factory=dict)
    """(탭, CSS) → 그 요소의 hover 를 기록한 시각(ms). 반복 hover 를 접는 데 쓴다."""

    _last_click_key: tuple[int, str] | None = None
    """직전에 기록한 클릭 Step 의 키. 없으면 직전 Step 이 클릭이 아니다.

    **클릭한 요소의 hover 는 Step 이 아니어야 한다.** `click()` 이 이미 포인터를 그 자리로
    옮기므로 뒤따르는 hover Step 은 같은 이동을 두 번 표현한다. 그리고 그 hover 는 사람이
    의도한 것이 아니라 **클릭이 만든 화면 변화를 hover 효과로 오인한 결과**다.

    실측(TC-011 step-14): 레이블을 클릭하면 목록이 다시 그려지는데, 그때 포인터는 투명한
    `<input>` 위에 있다. 그 DOM 변화가 input 의 hover 효과로 판정돼 Step 이 됐고, 재실행은
    `<button class="accordion-head">` 에 덮인 그 input 을 hover 하려다 10초를 쓰고 실패했다.

    `_last_hover` 와 대칭이다 — 순서가 `hover → click` 이면 클릭이 hover 를 갈아 끼우고,
    `click → hover` 면 hover 를 만들지 않는다. 어느 순서든 **한 번의 조작은 Step 하나**다.
    """

    _last_hover: tuple[tuple[int, str], str] | None = None
    """직전에 기록한 hover Step 의 (키, id). 없으면 직전 Step 이 hover 가 아니다.

    **클릭이 뒤따르면 그 hover 는 Step 이 아니어야 한다** (아래 `_record_click` 참고).
    `_emit` 이 모든 Step 이 지나는 단일 지점이므로 거기서 지운다 — 다른 Step 이 하나라도
    들어오면 그 hover 는 더 이상 "직전" 이 아니다.
    """

    _select_step_ids: dict[tuple[int, str], str] = field(default_factory=dict)
    """(탭, CSS) → 그 `<select>` 의 최근 select Step id.

    `change` 와 `blur` 가 같은 선택에 대해 둘 다 도착한다 — 입력과 같은 상황이다
    (FR-025). 접지 않으면 한 번의 선택이 Step 두 개가 되고, 재실행이 같은 값을 두 번
    고른다. SC-008 측정이 이 중복을 드러냈다.
    """

    _select_values: dict[tuple[int, str], str] = field(default_factory=dict)

    _click_seen: dict[tuple[int, str], float] = field(default_factory=dict)
    """(탭, CSS) → 그 요소의 클릭을 기록한 시각(ms). `pointerdown`·`click` 중복 제거용."""

    _nav_suppress: dict[int, float] = field(default_factory=dict)
    """탭 → 그 탭에서 클릭이 일어난 시각(ms). 클릭이 유발한 **이동 사슬**을 억제한다.

    **하나만 억제하면 안 된다** (TC-010 실측). 로그인 한 번이 리다이렉트 사슬을 만들어
    이동이 다섯 번 일어났고, 첫 하나만 억제한 결과 나머지 넷이 Step 으로 남았다. 그
    정의를 재실행하면 로그인 클릭 뒤에 `goto /portal-auth/login` 이 실행되어 **로그인
    화면으로 되돌아간다** — 우연히 마지막 주소가 같아서 통과했을 뿐이다.

    그래서 플래그를 소비하지 않고, 억제 조건이 유지되는 동안 오는 이동을 모두 억제한다.
    조건이 풀리는 지점은 두 곳이다 — 시간창을 넘기거나, 다른 Step 이 기록되는 것
    (`NAV_DEDUPE_MS` 문서의 조건 2: 다른 Step 이 기록됐다면 페이지가 살아 있었다는 뜻이므로
    그 클릭은 이동을 유발하지 않았다).
    """

    _last_nav_url: dict[int, str] = field(default_factory=dict)
    """탭 → 그 탭에 마지막으로 기록한 이동 주소. **연속 중복을 접는 근거다.**

    SPA 는 같은 주소로 `pushState`·`replaceState` 를 여러 번 부른다 (TC-010 에서 상세
    화면 주소가 3번 연달아 왔다). 주소가 같은 이동을 연달아 기록하면 재실행이 같은 곳으로
    `goto` 를 반복한다.

    한계: 사용자가 **일부러 같은 주소를 다시 여는 것**(새로 고침)도 함께 접힌다. 주소만
    보고 둘을 가를 방법이 없고, 접지 않으면 훨씬 흔한 SPA 중복이 그대로 남는다.
    """

    capturer: SensitiveCapturer | None = None
    """민감 값 포착기. 없으면 `install()` 에서 만든다.

    **AI 작성 경로와 같은 객체를 공유할 수 있어야 한다** — 사람이 이어받아 입력한 값과
    AI 가 입력한 값이 같은 변수 이름 공간을 쓰지 않으면 정의와 비밀 파일이 어긋난다.
    """

    warnings: list[str] = field(default_factory=list)
    _installed: bool = False
    _watched: set[int] = field(default_factory=set)
    """감시를 붙인 `Page` 의 id. 같은 탭에 핸들러를 두 번 붙이지 않기 위한 것이다."""

    # ─── 설치 ───────────────────────────────────────────────────────────────

    async def install(self) -> None:
        """컨텍스트 단위로 리코더와 콜백 채널을 등록한다.

        네비게이션 이전에 등록해야 한다. 한 번만 설치한다.
        """
        if self._installed:
            return
        if self.capturer is None:
            self.capturer = SensitiveCapturer(
                store=self.store, public_key=self.public_key, key_source=self.key_source
            )
        context = self.session.context

        # 바운드 메서드를 그대로 넘기지 않는다. Playwright 가 핸들러의 `__self__` 에
        # 래퍼를 캐시하려 하는데 `Recorder` 는 slots 를 쓰므로 `__dict__` 가 없어 실패한다.
        async def on_record(source: dict[str, Any], payload: dict[str, Any]) -> None:
            await self._on_record(source, payload)

        await context.expose_binding(BINDING_NAME, on_record)
        script = self._script()
        await context.add_init_script(script=script)
        # 이미 열려 있는 탭에는 init script 가 적용되지 않았으므로 직접 평가한다.
        #
        # **프레임마다 넣는다.** 세션은 `install()` 보다 먼저 시작 주소를 열기 때문에, 첫
        # 화면의 문서는 main frame 과 iframe 모두 이미 로드된 상태다. `page.evaluate` 는
        # main frame 에서만 도므로 예전에는 그 화면의 iframe 이 리코더 없이 남았고, 거기서
        # 한 조작은 **아무 Step 도 만들지 않았다** — 사용자에게는 "녹화가 안 된다" 로만
        # 보였다. 이후에 붙는 프레임은 `add_init_script` 가 덮는다.
        for tab in self.session.open_tabs():
            for frame in tab.page.frames:
                with contextlib.suppress(Exception):
                    await frame.evaluate(script)
        for tab in self.session.open_tabs():
            self.watch_page(tab.page)
        # 이후 열리는 탭은 세션이 알려 준다. 이 등록이 없으면 새 탭의 화면 이동과
        # 탭 닫힘이 기록되지 않는다 (FR-024·FR-030c).
        self.session.attach_page_observer(self.watch_page)
        self._installed = True

    def _script(self) -> str:
        """주입할 스크립트. 앞에 설정을 붙인다.

        `testId` 속성명은 대상 앱마다 다르므로(research R4) 스크립트가 알아야 한다 —
        동작 시점 후보 검증을 페이지 안에서 하기 때문이다. 값은 프로젝트 설정에서 온
        속성명이며 JSON 으로 직렬화해 넣는다: 문자열을 그대로 이어 붙이면 따옴표가 들어간
        값에서 스크립트가 깨진다 (헌법 보안 요건 — 생성 코드를 문자열 접합으로 만들지
        않는다).
        """
        config = json.dumps({"testIdAttribute": self.test_id_attribute})
        return f"window.__itbConfig = {config};\n" + INJECTED_SCRIPT.read_text(
            encoding="utf-8"
        )

    def _watch_navigation(self, page: Page) -> None:
        """main frame 네비게이션을 Python 측에서 듣는다.

        JS `beforeunload` 로 잡으면 페이지가 사라지는 중에 바인딩 호출이 유실될 수 있다.
        """
        page.on("framenavigated", lambda frame: self._on_navigated(page, frame))

    def watch_page(self, page: Page) -> None:
        """탭 하나에 네비게이션·닫힘 감시를 붙인다.

        `BrowserSession.notify_page` 가 새 탭마다 호출한다. 이미 붙은 탭에 두 번
        붙지 않도록 `_watched` 로 걸러 낸다 — 핸들러가 중복되면 Step 도 중복된다.
        """
        key = id(page)
        if key in self._watched:
            return
        self._watched.add(key)
        self._watch_navigation(page)
        page.on("close", lambda _p=page: self._on_tab_closed(_p))

    def _on_tab_closed(self, page: Page) -> None:
        """탭 닫힘 → `close_tab` Step (FR-030c).

        **녹화 중일 때만 기록한다.** 재실행 중 `close_tab` Step 이 탭을 닫으면 이 핸들러가
        다시 불리는데, 그때 Step 을 만들면 실행이 정의를 늘린다.

        **그 탭의 클릭이 닫음을 유발한 경우는 기록하지 않는다.** 페이지 안의 "닫기" 버튼을
        누른 것은 이미 클릭 Step 으로 남아 있고, 재실행 때 그 클릭이 같은 닫힘을 다시
        만든다. 두 Step 을 모두 남기면 한 사건이 두 번 표현된다 — 클릭이 유발한 화면 이동을
        억제하는 것(FR-030b)과 같은 판정이며, 같은 인과 플래그를 쓴다.
        """
        if not self.active:
            return
        handle = self.session.tab_of(page)
        if handle is None:
            return

        clicked_at = self._nav_suppress.pop(handle.tab_index, None)
        if clicked_at is not None and (time.monotonic() * 1000) - clicked_at < NAV_DEDUPE_MS:
            return

        asyncio.create_task(  # noqa: RUF006 - 이벤트 핸들러에서 대기할 수 없다
            self._emit(self.record_tab_close(handle.tab_index))
        )

    # ─── 녹화 제어 ─────────────────────────────────────────────────────────

    def start(self, author: Author = Author.HUMAN, insert_at: int | None = None) -> None:
        self.active = True
        self.author = author
        self.insert_at = insert_at
        self._last_fill_key = None
        self._last_step_id = None
        self._fill_step_ids.clear()
        self._fill_values.clear()

    def stop(self) -> None:
        self.active = False
        self._last_fill_key = None
        self._last_step_id = None

    def _next_step_id(self) -> str:
        if self.id_allocator is not None:
            return self.id_allocator()
        self._step_seq += 1
        return f"step-{self._step_seq:02d}"

    def seed_step_seq(self, existing: int) -> None:
        """이미 있는 Step 개수에 맞춰 번호를 이어 붙인다."""
        self._step_seq = max(self._step_seq, existing)

    # ─── 콜백 (주입 JS → Python) ───────────────────────────────────────────

    async def _on_record(self, source: dict[str, Any], payload: dict[str, Any]) -> None:
        """주입 JS 의 `window.__itbRecord` 호출을 받는다.

        `source["page"]` 로 발신 탭을 식별한다 (T004 로 확인). 페이지별 바인딩 이름을
        만들 필요가 없다.
        """
        page: Page = source["page"]
        # **`source["frame"]` 을 버리면 안 된다.** 주입 스크립트는 모든 프레임에서 돌므로
        # 이 값이 동작이 일어난 문서를 가리킨다. 예전에는 `page` 만 써서 iframe 안의
        # 동작을 main frame 기준으로 검증했고, 그 Step 은 실행에서 반드시 실패했다.
        frame: Frame = source["frame"]
        if self.repick.armed:
            # 다시 집기 대기 중이면 이 클릭은 **대상 지정**이며 Step 이 되지 않는다.
            if payload.get("kind") == "click":
                await self._deliver_repick(page, frame, payload.get("element") or {})
            return
        if not self.active:
            return
        tab = self.session.tab_of(page)
        if tab is None:
            # on("page") 가 아직 처리되지 않은 탭. 상한을 넘겼으면 등록이 거절된다.
            try:
                tab = self.session.register_tab(page)
            except TabLimitReachedError as exc:
                self._warn(str(exc))
                return

        kind = payload.get("kind")
        element = payload.get("element") or {}
        origin = self._origin(page, frame, tab.tab_index)

        if kind == "hover":
            await self._prewarm(origin, element)
        elif kind == "hover_action":
            await self._record_hover(origin, element)
        elif kind == "drag":
            await self._record_drag(origin, element, payload)
        elif kind == "click":
            await self._record_click(origin, element)
        elif kind == "fill":
            await self._record_fill(origin, element, payload)
        elif kind == "select":
            await self._record_select(origin, element, payload)
        elif kind == "file_input":
            await self._record_upload(origin, element, payload)

    @staticmethod
    def _basis(element: dict[str, Any]) -> str:
        """중복 제거·후보 재사용의 기준 문자열.

        주입 스크립트가 준 묶음 이름(`group`)을 쓰고, 없으면 CSS 경로로 떨어진다.

        **왜 CSS 가 아닌 별도 기준이 필요한가**: `<label>` 을 누르면 브라우저가 연결된
        컨트롤에 클릭을 한 번 더 합성해 보낸다. 두 이벤트의 대상이 다르므로 CSS 로 접으면
        한 번의 클릭이 Step 두 개가 되고, 재실행이 체크박스를 켰다가 다시 끈다 (TC-009
        실측). 묶음 이름은 레이블과 컨트롤 양쪽에서 같은 값이 나오므로 둘이 접힌다.

        컨트롤 자신에 대해서는 묶음 이름이 자기 CSS 와 같으므로 기존 키가 그대로다.
        """
        return str(element.get("group") or element.get("css") or "")

    def _origin(self, page: Page, frame: Frame, tab: int) -> Origin:
        """동작이 일어난 자리를 만든다. 하위 프레임이면 그 사실을 사용자에게 알린다.

        **알리는 이유**: 프레임은 재실행 사이에 유지되는 식별자가 없어 주소로 찾는다.
        캐시 무효화 토큰이 붙는 iframe 처럼 주소가 매번 달라지는 화면은 그 Step 이
        실패하는데, 원인이 프레임이라는 것은 실패 메시지를 봐야 알 수 있다. 녹화 시점에
        말해 두면 저장하기 전에 판단할 수 있다.
        """
        if frame == page.main_frame:
            return Origin(page=page, root=page, tab=tab, frame_url=None)
        url = frame.url
        self._warn(
            "하위 프레임(iframe) 안의 동작을 기록했습니다. 재실행 시 프레임을 주소로 "
            f"찾습니다: {url or '(주소 없음)'}. 주소가 매번 달라지는 프레임이면 그 Step "
            "은 재실행에서 실패할 수 있습니다."
        )
        return Origin(page=page, root=frame, tab=tab, frame_url=url or None)

    async def _deliver_repick(
        self, page: Page, frame: Frame, element: dict[str, Any]
    ) -> None:
        """다시 집기 대상을 재수집해 전달한다 (FR-020).

        수집에 실패하면 **대기를 유지한다.** 사용자가 빈 영역이나 식별 불가한 요소를
        눌렀을 뿐이므로, 대기를 풀면 다시 버튼을 눌러야 한다.
        """
        origin = self._origin(page, frame, -1)
        target = await self._collect_target(origin, element)
        if target is None:
            return
        await self.repick.deliver(target, origin.frame_url)

    @property
    def last_step_label(self) -> str | None:
        """마지막으로 기록한 Step 의 표시 이름. 인수 요약에 쓴다 (FR-076)."""
        return self._last_step_label

    @property
    def sensitive_captures(self) -> list[SensitiveCapture]:
        """포착한 민감 값 목록. 저장 시 변수 정의를 만드는 근거다 (FR-082)."""
        return self.capturer.captures if self.capturer is not None else []

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    # ─── 후보 수집 + 기록 시점 검증 (원칙 IV) ─────────────────────────────

    async def _collect_target(
        self, origin: Origin, element: dict[str, Any], warn_on_failure: bool = True
    ) -> TargetLocator | None:
        """후보를 수집하고 **즉시 검증**해 상태를 채운다.

        수집·검증 자체는 `itb.execution.element_probe` 가 한다 — 편집·다시 집기·AI 도구가
        같은 코드를 지나야 녹화된 Step 과 편집으로 만든 Step 의 후보가 갈리지 않는다
        (원칙 IV). 리코더가 여기서 더하는 것은 **사용자에게 알릴 경고** 하나다.

        `warn_on_failure=False` 는 사전 수집(hover) 경로용이다 — 지나가는 요소마다 경고를
        쌓으면 정작 Step 이 만들어지지 않은 경고가 묻힌다.
        """
        target = await collect_and_verify(origin.root, element, self.test_id_attribute)
        if target is None and warn_on_failure:
            self._warn(
                "대상 요소를 식별할 정보를 전혀 수집하지 못해 Step 을 만들지 못했습니다."
            )
        return target

    # ─── Step 기록 ─────────────────────────────────────────────────────────

    async def _emit(self, step: Step) -> None:
        # 어떤 Step 이든 하나 들어오면 앞선 hover·클릭은 "직전" 이 아니게 된다. 각자
        # `_record_hover`·`_record_click` 이 이 호출 **뒤에** 다시 세운다.
        self._last_hover = None
        self._last_click_key = None
        index = self.insert_at if self.insert_at is not None else -1
        self._last_step_id = step.id
        self._last_step_label = step.label
        await self.sink(step, index)
        if self.insert_at is not None:
            self.insert_at += 1

    async def _prewarm(self, origin: Origin, element: dict[str, Any]) -> None:
        """포인터가 올라간 요소의 후보를 미리 수집·검증해 둔다. Step 은 만들지 않는다.

        클릭 시점 수집이 화면 이동과 경쟁하는 문제의 해법이다 (US2 재실행에서 드러났다).
        여기서 확보한 결과는 `_best_target` 을 통해 클릭 Step 에 쓰인다.
        """
        basis = self._basis(element)
        if not basis:
            return
        target = await self._collect_target(origin, element, warn_on_failure=False)
        if target is not None:
            self._best_target(origin.key(basis), target)

    async def _record_click(self, origin: Origin, element: dict[str, Any]) -> None:
        """클릭을 기록한다.

        `pointerdown` 과 `click` 이 같은 클릭에 대해 둘 다 도착한다. 먼저 온 쪽만 남긴다 —
        먼저 온 쪽이 화면 이동을 앞질러 후보를 검증했을 가능성이 높다.

        **레이블 활성화도 같은 클릭이다.** `<label>` 을 누르면 브라우저가 연결된 컨트롤에
        클릭을 한 번 더 합성해 보낸다. `_basis` 가 두 이벤트에 같은 키를 주므로 여기서
        함께 접히고, **포인터가 실제로 닿은 쪽**이 남는다.
        """
        if _is_container_gap(element):
            # 껍데기의 여백을 누른 것이다 — 아무 일도 일어나지 않았고, 어느 요소를
            # 뜻하는지도 알 수 없다 (아래 참고).
            self._warn(
                "조작 대상이 아닌 껍데기(목록·카드 등)의 여백을 누른 클릭은 Step 으로 "
                "만들지 않았습니다. 그 클릭은 화면에 아무 일도 하지 않고, 어느 요소를 "
                "누르려던 것인지 알 수 없습니다. 의도한 대상이 있으면 그 요소를 직접 "
                "누르세요."
            )
            return
        now_ms = time.monotonic() * 1000
        key = origin.key(self._basis(element))
        last = self._click_seen.get(key)
        if last is not None and now_ms - last < CLICK_DEDUPE_MS:
            return
        self._click_seen[key] = now_ms
        self._last_click_ms = now_ms
        # ★ 수집을 기다리기 **전에** 억제 플래그를 세운다. 수집이 화면 이동과 겹치면
        # 이동 이벤트가 먼저 처리되는데, 그때 플래그가 없으면 클릭이 유발한 이동이
        # 별도 navigate Step 으로 남아 재실행 때 같은 이동을 두 번 하게 된다 (FR-030b).
        self._nav_suppress[origin.tab] = now_ms

        fresh = await self._collect_target(origin, element)
        if fresh is None:
            self._click_seen.pop(key, None)
            return
        # 마우스가 올라간 시점에 확보해 둔 후보가 더 나으면 그것을 쓴다.
        target = self._best_target(key, fresh)
        self._last_fill_key = None
        label = element.get("accessibleName") or element.get("text") or element.get("tag")

        # **같은 요소의 직전 hover 는 이 클릭이 대신한다.**
        #
        # `click()` 은 그 자체가 포인터를 옮기고(hover) 누르고 떼는 동작이다. 앞에 hover
        # Step 을 따로 두면 같은 이동을 두 번 표현하는 것이고, 정의를 읽는 사람은 그 hover
        # 에 별도의 뜻이 있다고 오해한다. 실측(TC-010)에서 37 Step 중 6쌍이 이 형태였다.
        #
        # **hover 를 아예 기록하지 않을 수는 없다.** 포인터가 올라간 시점에는 클릭이 뒤따를지
        # 알 수 없고, 클릭이 없으면 그 hover 자체가 동작이다(메뉴가 열린다). 그래서 일단
        # 기록하고, 클릭이 오면 **그 자리에서 갈아 끼운다** — 새 Step 을 뒤에 붙이지 않으므로
        # 순서와 번호가 그대로 유지된다.
        absorbed = self._last_hover is not None and self._last_hover[0] == key
        step_id = self._last_hover[1] if absorbed else self._next_step_id()
        click = ClickStep(
            id=step_id,
            label=f"{label} 클릭",
            author=self.author,
            tab=origin.tab,
            frame_url=origin.frame_url,
            target=target,
        )
        if absorbed:
            self._last_hover = None
            self._hover_seen.pop(key, None)
            self._last_step_id = step_id
            self._last_step_label = click.label
            await self.sink(click, -2)  # -2 = 기존 Step 갈아 끼우기
        else:
            await self._emit(click)
        # 이 클릭 뒤에 같은 요소의 hover 가 오면 그것은 클릭이 만든 변화다.
        self._last_click_key = key

    async def _record_fill(
        self, origin: Origin, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        """입력을 기록한다.

        **중복 제거**: `change` 와 `blur` 가 모두 발생하므로 같은 요소에 대한 연속 입력은
        최종 값 하나로 접는다 (FR-025, research R2 실측).

        **T157**: 민감 값 치환이 이벤트 발행보다 먼저 일어난다.
        """
        target = await self._collect_target(origin, element)
        if target is None:
            return

        key = origin.key(target.css.value if target.css else "")
        target = self._best_target(key, target)
        raw_value = payload.get("value") or ""
        sensitive = bool(payload.get("sensitive"))

        # ★ 치환을 이벤트 발행보다 먼저 한다 (T157). 이 순서가 뒤바뀌면 평문이 프론트에 간다.
        stored_value = self._to_variable_reference(raw_value, sensitive, element, key)

        # 이 탭에서 입력이 기록됐다 → 페이지가 살아 있으므로 앞선 클릭은 이동을 만들지
        # 않았다. 억제 플래그를 지운다 (NAV_DEDUPE_MS 문서의 조건 2).
        self._nav_suppress.pop(origin.tab, None)

        # 중복 제거 (FR-025). "직전 이벤트" 기준으로는 부족하다 — 다른 요소를 클릭하면
        # 그 클릭이 이 필드의 blur 를 유발하므로, 클릭 Step 이 사이에 끼어 같은 입력이
        # 두 Step 이 된다. 그래서 **같은 요소의 최근 fill Step 을 되짚어** 판단한다.
        existing_id = self._find_recent_fill(key, stored_value)
        if existing_id is not None:
            await self.sink(
                FillStep(
                    id=existing_id,
                    label=self._fill_label(element, sensitive),
                    author=self.author,
                    tab=origin.tab,
                    frame_url=origin.frame_url,
                    target=target,
                    value=stored_value,
                ),
                -2,  # -2 = 기존 Step 갱신
            )
            self._last_fill_key = key
            self._last_step_id = existing_id
            self._fill_values[key] = stored_value
            return

        self._last_fill_key = key
        self._fill_values[key] = stored_value
        new_id = self._next_step_id()
        self._fill_step_ids[key] = new_id
        await self._emit(
            FillStep(
                id=new_id,
                label=self._fill_label(element, sensitive),
                author=self.author,
                tab=origin.tab,
                frame_url=origin.frame_url,
                target=target,
                value=stored_value,
            )
        )

    def _best_target(self, key: tuple[int, str], fresh: TargetLocator) -> TargetLocator:
        """이번 수집 결과와 이전 결과 중 **더 잘 검증된** 쪽을 쓴다.

        확정 이벤트(`change`/`blur`)가 화면 이동과 겹치면 재수집이 전부 미수집으로 돌아온다.
        그때 새 결과로 덮어쓰면 이미 확보한 후보를 잃고, 저장된 테스트가 재실행 불가가 된다.
        """
        previous = self._fill_targets.get(key)
        if previous is not None and _usable_count(previous) > _usable_count(fresh):
            return previous
        self._fill_targets[key] = fresh
        return fresh

    def _find_recent_fill(self, key: tuple[int, str], new_value: str) -> str | None:
        """같은 요소의 기존 fill Step 을 찾는다. 갱신 대상이면 그 id, 아니면 None.

        갱신 대상 판정:

        - **직전 이벤트가 같은 요소였다** → 연속 입력이다 (FR-025).
        - **값이 같다** → `change` 와 `blur` 가 같은 입력을 두 번 보고한 것이다.
          다른 요소를 클릭해 blur 가 유발된 경우가 여기 해당한다.

        값이 다르고 직전도 아니면 새 Step 을 만든다 — 필드 A 입력 → 다른 동작 →
        필드 A 를 **다른 값으로** 다시 입력한 것은 별개의 동작이다.
        """
        step_id = self._fill_step_ids.get(key)
        if step_id is None:
            return None
        if self._last_fill_key == key:
            return step_id
        if self._fill_values.get(key) == new_value:
            return step_id
        return None

    def _element_key(self, element: dict[str, Any]) -> tuple[int, str]:
        """탭 정보 없이 요소를 구분하는 키. 호출자가 키를 주지 않을 때만 쓴다.

        CSS 가 있으면 그것이 가장 좁은 식별자다. 없으면 이름·라벨로 떨어진다 — 서로 다른
        필드가 같은 변수를 공유하는 일을 막는 것이 목적이다.
        """
        attrs = element.get("attributes") or {}
        basis = (
            element.get("css")
            or attrs.get("name")
            or attrs.get(self.test_id_attribute)
            or element.get("label")
            or element.get("accessibleName")
            or ""
        )
        return (-1, str(basis))

    @staticmethod
    def _fill_label(element: dict[str, Any], sensitive: bool) -> str:
        name = element.get("label") or element.get("accessibleName") or "입력"
        return f"{name} 입력" if not sensitive else f"{name} 입력 (민감)"

    def _to_variable_reference(
        self,
        raw_value: str,
        sensitive: bool,
        element: dict[str, Any],
        key: tuple[int, str] | None = None,
    ) -> str:
        """민감 값을 변수 참조로 바꾸고 공개키로 봉인한다 (FR-082·FR-082a·FR-089b).

        **평문을 돌려주지 않는다.** 이 함수의 반환값만 Step 에 들어가고, Step 만 이벤트로
        나가므로 평문이 프론트에 도달할 경로가 없다 (T157).

        포착 자체는 `SensitiveCapturer` 가 한다 — AI 작성 경로(FR-061)도 같은 객체를 써야
        변수 이름 공간이 갈라지지 않는다.
        """
        if not sensitive or not raw_value:
            return raw_value
        if self.capturer is None:  # pragma: no cover - install() 이 먼저 돈다
            self.capturer = SensitiveCapturer(
                store=self.store, public_key=self.public_key, key_source=self.key_source
            )

        cache_key = key if key is not None else self._element_key(element)
        attrs = element.get("attributes") or {}
        stored = self.capturer.to_reference(
            raw_value,
            cache_key=repr(cache_key),
            name_basis=(
                attrs.get("name"),
                attrs.get(self.test_id_attribute),
                element.get("label"),
            ),
        )
        for message in self.capturer.warnings:
            self._warn(message)
        return stored

    async def _record_hover(self, origin: Origin, element: dict[str, Any]) -> None:
        """화면을 바꾼 hover 를 Step 으로 기록한다 (FR-023c).

        판정은 주입 스크립트가 한다 — hover 직후 문서 변화가 있었는지는 페이지 안에서만
        관측할 수 있다. 여기서는 이미 걸러진 것을 받아 Step 으로 만든다.

        같은 요소의 hover 가 연달아 오면 하나로 접는다. 메뉴를 열었다 닫았다 하는 동안
        같은 Step 이 여러 개 쌓이면 재실행이 무의미하게 길어진다.

        **여기서 만든 Step 은 같은 요소의 클릭이 뒤따르면 그 클릭으로 갈아 끼워진다**
        (`_record_click`). 포인터가 올라간 시점에는 클릭이 뒤따를지 알 수 없으므로 일단
        만들어 두는 것이다.
        """
        basis = self._basis(element)
        if not basis:
            return
        key = origin.key(basis)
        if self._last_click_key == key:
            # 직전에 이 요소를 클릭했다 → 지금 관측된 화면 변화는 그 클릭의 결과다.
            # 클릭은 이미 포인터를 여기로 옮기므로 hover Step 이 더할 것이 없다.
            return
        last = self._hover_seen.get(key)
        now_ms = time.monotonic() * 1000
        if last is not None and now_ms - last < HOVER_DEDUPE_MS:
            return
        self._hover_seen[key] = now_ms

        fresh = await self._collect_target(origin, element)
        if fresh is None:
            return
        target = self._best_target(key, fresh)
        if not _has_identity(target):
            # 위치 경로 하나로만 지목되는 요소는 hover Step 으로 만들지 않는다 (아래 참고).
            self._hover_seen.pop(key, None)
            self._warn(
                "이름·텍스트로 지목할 수 없는 요소에 마우스가 올라간 것은 Step 으로 "
                "만들지 않았습니다. 로딩 덮개처럼 잠깐 나타나는 요소가 화면을 바꾼 것을 "
                "hover 로 오인하는 것을 막기 위한 것입니다. 필요한 hover 가 빠졌다면 "
                "일시정지 중 직접 동작 추가로 넣으세요."
            )
            return
        self._last_fill_key = None
        label = element.get("accessibleName") or element.get("text") or element.get("tag")
        step_id = self._next_step_id()
        await self._emit(
            HoverStep(
                id=step_id,
                label=f"{label} 에 마우스 올리기",
                author=self.author,
                tab=origin.tab,
                frame_url=origin.frame_url,
                target=target,
            )
        )
        # 이 hover 에 곧 클릭이 뒤따르면 클릭이 이 Step 을 대신한다.
        self._last_hover = (key, step_id)
        # hover 가 기록됐다 → 페이지가 살아 있으므로 앞선 클릭은 이동을 만들지 않았다
        # (`NAV_DEDUPE_MS` 문서의 조건 2).
        self._nav_suppress.pop(origin.tab, None)

    async def _record_drag(
        self, origin: Origin, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        """끌어다 놓기를 Step 하나로 기록한다 (FR-023c).

        **끄는 대상과 놓는 위치를 모두 확보해야 기록한다.** 한쪽만 있는 Step 은 재실행할
        수 없으므로, 절반만 남기지 않고 사유를 경고로 남긴다.
        """
        drop_element = payload.get("dropElement") or {}
        source = await self._collect_target(origin, element)
        destination = await self._collect_target(origin, drop_element)
        if source is None or destination is None:
            self._warn(
                "끌어다 놓기에서 끄는 대상 또는 놓는 위치를 식별하지 못해 Step 을 "
                "만들지 못했습니다. 일시정지 중 직접 동작 추가로 보완하세요."
            )
            return

        self._last_fill_key = None
        # 끌어다 놓기가 기록됐다 → 페이지가 살아 있었다 (조건 2).
        self._nav_suppress.pop(origin.tab, None)
        source_label = element.get("accessibleName") or element.get("text") or element.get("tag")
        drop_label = (
            drop_element.get("accessibleName")
            or drop_element.get("text")
            or drop_element.get("tag")
        )
        await self._emit(
            DragStep(
                id=self._next_step_id(),
                label=f"{source_label} 을 {drop_label} 으로 끌어다 놓기",
                author=self.author,
                tab=origin.tab,
                frame_url=origin.frame_url,
                target=source,
                drop_target=destination,
            )
        )

    async def _record_select(
        self, origin: Origin, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        """선택을 기록한다.

        **중복 제거**: `change` 와 `blur` 가 같은 선택에 대해 둘 다 도착하므로, 같은
        요소에 같은 값이면 기존 Step 을 갱신한다 (FR-025 와 같은 판정). 값이 다르면 새
        Step 이다 — 같은 셀렉트를 다시 다른 값으로 고른 것은 별개의 동작이다.
        """
        target = await self._collect_target(origin, element)
        if target is None:
            return
        key = origin.key(target.css.value if target.css else "")
        target = self._best_target(key, target)
        value = str(payload.get("value") or "")

        self._last_fill_key = None
        # 선택이 기록됐다 → 페이지가 살아 있으므로 앞선 클릭은 이동을 만들지 않았다.
        self._nav_suppress.pop(origin.tab, None)
        name = element.get("label") or element.get("accessibleName") or "선택"

        existing_id = self._select_step_ids.get(key)
        if existing_id is not None and self._select_values.get(key) == value:
            await self.sink(
                SelectStep(
                    id=existing_id,
                    label=f"{name} 선택",
                    author=self.author,
                    tab=origin.tab,
                    frame_url=origin.frame_url,
                    target=target,
                    value=value,
                ),
                -2,  # -2 = 기존 Step 갱신
            )
            self._last_step_id = existing_id
            return

        new_id = self._next_step_id()
        self._select_step_ids[key] = new_id
        self._select_values[key] = value
        await self._emit(
            SelectStep(
                id=new_id,
                label=f"{name} 선택",
                author=self.author,
                tab=origin.tab,
                frame_url=origin.frame_url,
                target=target,
                value=value,
            )
        )

    async def _record_upload(
        self, origin: Any, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        """파일 입력 → upload Step (2026-09-09 사용자 보고).

        ## 이전에는 경고 하나였다

        같은 자리에 이런 문구가 있었다 — 「파일 입력이 감지됐습니다. 운영체제 파일 선택
        대화상자는 기록할 수 없으므로, Step 편집에서 파일 경로를 직접 지정해야 합니다.」

        **두 번 틀렸다.** 첫째, 기록할 수 없다는 것이 사실이 아니다 — 브라우저는 고른
        파일의 이름을 준다(``File.name``). 운영체제 대화상자를 기록할 수 없는 것과 그
        결과를 기록할 수 없는 것은 다른 이야기다. 둘째, 안내한 「Step 편집에서 파일 경로를
        직접 지정」이 **제품에 없었다** — 그런 칸도 Step 종류도 없었으므로 사용자는 안내를
        따를 수 없었다 (006 E-03 과 같은 형태의 결함).

        ## 무엇을 기록하는가

        파일 이름 하나다. 확장자가 그 안에 있고, 사용자가 요구한 것이 확장자다 — 「실제
        서비스에서는 확장자를 보는경우가 있기 때문」.

        **여러 개를 고른 경우 첫 번째만 쓴다.** 다중 업로드(``multiple``)는 Step 하나가
        여러 파일을 갖는 형태를 요구하는데, 그것은 이 Step 의 모양을 바꾸는 일이고 지금
        요구에 없다. 첫 번째를 기록하고 나머지는 경고로 알린다 — 조용히 버리면 사용자는
        재실행이 왜 다르게 도는지 알 수 없다.

        **비우는 것(취소)은 Step 이 아니다.** 파일을 고르지 않고 대화상자를 닫으면
        ``change`` 가 빈 목록으로 올 수 있다. 그때 만들 Step 이 없다.
        """
        raw = payload.get("files")
        names = [str(n) for n in raw if str(n).strip()] if isinstance(raw, list) else []
        if not names:
            return

        if len(names) > 1:
            self._warn(
                f"파일 {len(names)}개를 골랐습니다. 첫 번째({names[0]})만 기록합니다 — "
                "재실행도 한 개만 올립니다."
            )

        target = await self._collect_target(origin, element)
        if target is None:
            return
        key = origin.key(target.css.value if target.css else "")
        target = self._best_target(key, target)

        self._last_fill_key = None
        # 파일 선택이 기록됐다 → 페이지가 살아 있으므로 앞선 클릭은 이동을 만들지 않았다.
        self._nav_suppress.pop(origin.tab, None)

        file_name = names[0]
        label = element.get("label") or element.get("accessibleName") or "파일"
        await self._emit(
            UploadStep(
                id=self._next_step_id(),
                # 라벨에 **파일 이름을 넣는다.** 목록에서 어느 파일을 올린 Step 인지
                # 행을 열지 않고 알 수 있어야 한다 (확장자가 요구의 핵심이다).
                label=f"{label} 에 {file_name} 올리기",
                author=self.author,
                tab=origin.tab,
                frame_url=origin.frame_url,
                target=target,
                file_name=file_name,
            )
        )

    def _on_navigated(self, page: Page, frame: Frame) -> None:
        """main frame 네비게이션 → navigate Step.

        클릭 직후 짧은 시간창 안의 네비게이션은 중복으로 보고 건너뛴다.
        """
        if not self.active or frame != page.main_frame:
            return
        tab = self.session.tab_of(page)
        if tab is None:
            return

        # 클릭이 있었고(플래그) 그 직후(시간창)면 이 이동은 클릭이 유발한 것으로 본다.
        # **플래그를 소비하지 않는다** — 한 클릭이 이동을 여러 번 만들기 때문이다.
        clicked_at = self._nav_suppress.get(tab.tab_index)
        if clicked_at is not None:
            if (time.monotonic() * 1000) - clicked_at < NAV_DEDUPE_MS:
                return
            self._nav_suppress.pop(tab.tab_index, None)  # 시간창을 넘겼다
        url = frame.url
        if not url or url == "about:blank":
            return
        # 같은 주소로 연달아 온 이동은 한 번의 이동이다.
        if self._last_nav_url.get(tab.tab_index) == url:
            return
        # **여기서 세운다.** 이 핸들러는 동기이고 Step 생성은 작업으로 넘기므로, 작업 안에서
        # 세우면 빠르게 연달아 온 이동이 둘 다 검사를 통과한다.
        self._last_nav_url[tab.tab_index] = url
        self._last_fill_key = None
        asyncio.create_task(  # noqa: RUF006 - 이벤트 핸들러에서 대기할 수 없다
            self._emit(
                NavigateStep(
                    id=self._next_step_id(),
                    label=f"화면 이동 {url}",
                    author=self.author,
                    tab=tab.tab_index,
                    url=url,
                )
            )
        )

    def record_tab_close(self, tab_index: int) -> CloseTabStep:
        """탭 닫기를 Step 으로 만든다 (FR-030c)."""
        self._last_fill_key = None
        return CloseTabStep(
            id=self._next_step_id(),
            label=f"탭 {tab_index} 닫기",
            author=self.author,
            tab=tab_index,
        )



def _is_container_gap(element: dict[str, Any]) -> bool:
    """껍데기의 **여백**을 누른 클릭인가.

    실측(TC-013)에서 이런 Step 이 셋 나왔다.

    | 기록된 요소 | 표시 이름 |
    |---|---|
    | `ul:nth-of-type(2)` | `앱 관리온톨로지 관리데이터 관리프로젝트 관리` |
    | `div > div > ul` | `가이드온톨로지규칙온톨로지유콩온톨로지인공지능온톨로지` |
    | `div#__nuxt > div > div` | `로그인 Graphio v2.2.0 아이디 지우기 비밀번…` |

    이름이 **자식 텍스트를 전부 이어붙인 형태**인 것이 껍데기라는 신호다. 항목 사이 여백을
    누른 것이고, 화면에는 아무 일도 일어나지 않는다.

    **버튼으로 바꿔 주지 않는다.** 여백은 어느 요소를 뜻하는지 알 수 없다 — 실측한 화면의
    껍데기는 버튼 두 개를 품고 있었다. 추측해서 하나를 고르면 사용자가 누르지 않은 것을
    누르는 정의가 된다. 그래서 **기록하지 않는다.**

    두 사실이 함께 성립할 때만 그렇게 본다.

    1. **그 요소 자체가 조작 대상이 아니다** — `actionTarget` 이 조상까지 올라가 봤는데도
       버튼·링크·`[role]`·`[onclick]` 어느 것도 찾지 못했다.
    2. **조작 대상을 품고 있다** — 목록·카드처럼 컨트롤을 감싸는 껍데기다.

    조건 2가 필요한 이유: `addEventListener` 로만 클릭을 처리하는 `div` 버튼은 우리 눈에
    조작 대상으로 보이지 않는다. 그런 요소는 컨트롤을 품고 있지 않으므로 조건 2에서
    걸러지고, 클릭이 그대로 기록된다.

    남는 한계: 목록 껍데기에 위임 핸들러를 달고 **껍데기 자신의 클릭까지** 처리하는 구현은
    놓친다. 그 경우는 일시정지 중 직접 동작 추가(FR-036)로 넣는다.
    """
    if element.get("actionable", True):
        return False
    return bool(element.get("wrapsControls"))


def _has_identity(target: TargetLocator) -> bool:
    """위치가 아니라 **무엇인가**로 지목되는가. CSS 말고 쓸 수 있는 후보가 있는가.

    **hover Step 에만 적용한다.** 클릭·입력은 사용자가 실제로 한 동작이므로 이름이 없어도
    기록해야 한다 (003 AS-016 이 그 경우를 위한 픽스처다). hover 는 다르다 — 그것이
    "의미 있는 hover 였는가" 는 사람이 말해 준 것이 아니라 **주입 스크립트의 추론**이다
    (FR-023c: 화면이 바뀌었는가). 추론이므로 오탐의 대가를 따로 재야 한다.

    실측(TC-007)에서 드러난 오탐: 화면 이동 직후 로딩 덮개(`div.overlay`)가 포인터 밑에
    있는 동안 로딩이 끝나 화면이 바뀌었고, 그 변화가 hover 의 효과로 판정됐다. 만들어진
    Step 은 이름이 없어 표시가 "div 에 마우스 올리기" 였고, 후보는 위치 경로
    (`main#app-main > div > div:nth-of-type(1)`) 하나뿐이었다. 재실행에서 그 경로는 다시
    덮개를 가리켰고, 덮개 위의 로딩 표시가 포인터를 가로막아 **10초를 쓰고 실패**했다.

    이름이 없으면 두 가지가 함께 무너진다.

    1. **의도를 표현할 수 없다.** "div 에 마우스 올리기" 는 사람이 다시 읽어도 무엇을
       하려던 Step 인지 알 수 없다.
    2. **위치 경로 하나만 남는다.** 그 경로는 "그 자리에 있는 무엇" 을 가리키므로, 화면
       상태가 달라지면 다른 요소를 잡는다.

    빠뜨리는 쪽의 대가는 작다. 아이콘만 있는 hover 메뉴처럼 정말 필요한 경우는 일시정지
    중 직접 동작 추가(FR-036)로 넣을 수 있고, 그것은 이미 이 추론의 알려진 보완 경로다.
    """
    return any(s.kind is not StrategyKind.CSS for s in ordered_strategies(target))


def _usable_count(target: TargetLocator) -> int:
    """실행에 쓸 수 있는 후보 수. `verified` 만 센다 (원칙 IV).

    후보 판정은 `itb.locator.strategy` 한 곳에만 둔다 — 여기서 상태를 다시 해석하면
    Runner·Generator 와 갈라진다.
    """
    return len(ordered_strategies(target))
