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
)
from itb.execution.element_probe import collect_and_verify
from itb.execution.session import BrowserSession, TabLimitReachedError
from itb.locator.strategy import ordered_strategies
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
    """탭 → 그 탭에서 클릭이 일어난 시각(ms). 다음 이동 하나를 억제하는 데 쓴다."""

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
                store=self.store, public_key=self.public_key
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
        for tab in self.session.open_tabs():
            with contextlib.suppress(Exception):
                await tab.page.evaluate(script)
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
        if self.repick.armed:
            # 다시 집기 대기 중이면 이 클릭은 **대상 지정**이며 Step 이 되지 않는다.
            if payload.get("kind") == "click":
                await self._deliver_repick(page, payload.get("element") or {})
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

        if kind == "hover":
            await self._prewarm(page, tab.tab_index, element)
        elif kind == "hover_action":
            await self._record_hover(page, tab.tab_index, element)
        elif kind == "drag":
            await self._record_drag(page, tab.tab_index, element, payload)
        elif kind == "click":
            await self._record_click(page, tab.tab_index, element)
        elif kind == "fill":
            await self._record_fill(page, tab.tab_index, element, payload)
        elif kind == "select":
            await self._record_select(page, tab.tab_index, element, payload)
        elif kind == "file_input":
            self._warn(
                "파일 입력이 감지됐습니다. 운영체제 파일 선택 대화상자는 기록할 수 없으므로, "
                "Step 편집에서 파일 경로를 직접 지정해야 합니다."
            )

    async def _deliver_repick(self, page: Page, element: dict[str, Any]) -> None:
        """다시 집기 대상을 재수집해 전달한다 (FR-020).

        수집에 실패하면 **대기를 유지한다.** 사용자가 빈 영역이나 식별 불가한 요소를
        눌렀을 뿐이므로, 대기를 풀면 다시 버튼을 눌러야 한다.
        """
        target = await self._collect_target(page, element)
        if target is None:
            return
        await self.repick.deliver(target)

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
        self, page: Page, element: dict[str, Any], warn_on_failure: bool = True
    ) -> TargetLocator | None:
        """후보를 수집하고 **즉시 검증**해 상태를 채운다.

        수집·검증 자체는 `itb.execution.element_probe` 가 한다 — 편집·다시 집기·AI 도구가
        같은 코드를 지나야 녹화된 Step 과 편집으로 만든 Step 의 후보가 갈리지 않는다
        (원칙 IV). 리코더가 여기서 더하는 것은 **사용자에게 알릴 경고** 하나다.

        `warn_on_failure=False` 는 사전 수집(hover) 경로용이다 — 지나가는 요소마다 경고를
        쌓으면 정작 Step 이 만들어지지 않은 경고가 묻힌다.
        """
        target = await collect_and_verify(page, element, self.test_id_attribute)
        if target is None and warn_on_failure:
            self._warn(
                "대상 요소를 식별할 정보를 전혀 수집하지 못해 Step 을 만들지 못했습니다."
            )
        return target

    # ─── Step 기록 ─────────────────────────────────────────────────────────

    async def _emit(self, step: Step) -> None:
        index = self.insert_at if self.insert_at is not None else -1
        self._last_step_id = step.id
        self._last_step_label = step.label
        await self.sink(step, index)
        if self.insert_at is not None:
            self.insert_at += 1

    async def _prewarm(self, page: Page, tab: int, element: dict[str, Any]) -> None:
        """포인터가 올라간 요소의 후보를 미리 수집·검증해 둔다. Step 은 만들지 않는다.

        클릭 시점 수집이 화면 이동과 경쟁하는 문제의 해법이다 (US2 재실행에서 드러났다).
        여기서 확보한 결과는 `_best_target` 을 통해 클릭 Step 에 쓰인다.
        """
        key = (tab, str(element.get("css") or ""))
        if not key[1]:
            return
        target = await self._collect_target(page, element, warn_on_failure=False)
        if target is not None:
            self._best_target(key, target)

    async def _record_click(
        self, page: Page, tab: int, element: dict[str, Any]
    ) -> None:
        """클릭을 기록한다.

        `pointerdown` 과 `click` 이 같은 클릭에 대해 둘 다 도착한다. 먼저 온 쪽만 남긴다 —
        먼저 온 쪽이 화면 이동을 앞질러 후보를 검증했을 가능성이 높다.
        """
        now_ms = time.monotonic() * 1000
        key = (tab, str(element.get("css") or ""))
        last = self._click_seen.get(key)
        if last is not None and now_ms - last < CLICK_DEDUPE_MS:
            return
        self._click_seen[key] = now_ms
        self._last_click_ms = now_ms
        # ★ 수집을 기다리기 **전에** 억제 플래그를 세운다. 수집이 화면 이동과 겹치면
        # 이동 이벤트가 먼저 처리되는데, 그때 플래그가 없으면 클릭이 유발한 이동이
        # 별도 navigate Step 으로 남아 재실행 때 같은 이동을 두 번 하게 된다 (FR-030b).
        self._nav_suppress[tab] = now_ms

        fresh = await self._collect_target(page, element)
        if fresh is None:
            self._click_seen.pop(key, None)
            return
        # 마우스가 올라간 시점에 확보해 둔 후보가 더 나으면 그것을 쓴다.
        target = self._best_target(key, fresh)
        self._last_fill_key = None
        label = element.get("accessibleName") or element.get("text") or element.get("tag")
        await self._emit(
            ClickStep(
                id=self._next_step_id(),
                label=f"{label} 클릭",
                author=self.author,
                tab=tab,
                target=target,
            )
        )

    async def _record_fill(
        self, page: Page, tab: int, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        """입력을 기록한다.

        **중복 제거**: `change` 와 `blur` 가 모두 발생하므로 같은 요소에 대한 연속 입력은
        최종 값 하나로 접는다 (FR-025, research R2 실측).

        **T157**: 민감 값 치환이 이벤트 발행보다 먼저 일어난다.
        """
        target = await self._collect_target(page, element)
        if target is None:
            return

        css = target.css.value if target.css else ""
        key = (tab, css)
        target = self._best_target(key, target)
        raw_value = payload.get("value") or ""
        sensitive = bool(payload.get("sensitive"))

        # ★ 치환을 이벤트 발행보다 먼저 한다 (T157). 이 순서가 뒤바뀌면 평문이 프론트에 간다.
        stored_value = self._to_variable_reference(raw_value, sensitive, element, key)

        # 이 탭에서 입력이 기록됐다 → 페이지가 살아 있으므로 앞선 클릭은 이동을 만들지
        # 않았다. 억제 플래그를 지운다 (NAV_DEDUPE_MS 문서의 조건 2).
        self._nav_suppress.pop(tab, None)

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
                    tab=tab,
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
                tab=tab,
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
                store=self.store, public_key=self.public_key
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

    async def _record_hover(
        self, page: Page, tab: int, element: dict[str, Any]
    ) -> None:
        """화면을 바꾼 hover 를 Step 으로 기록한다 (FR-023c).

        판정은 주입 스크립트가 한다 — hover 직후 문서 변화가 있었는지는 페이지 안에서만
        관측할 수 있다. 여기서는 이미 걸러진 것을 받아 Step 으로 만든다.

        같은 요소의 hover 가 연달아 오면 하나로 접는다. 메뉴를 열었다 닫았다 하는 동안
        같은 Step 이 여러 개 쌓이면 재실행이 무의미하게 길어진다.
        """
        key = (tab, str(element.get("css") or ""))
        if not key[1]:
            return
        last = self._hover_seen.get(key)
        now_ms = time.monotonic() * 1000
        if last is not None and now_ms - last < HOVER_DEDUPE_MS:
            return
        self._hover_seen[key] = now_ms

        fresh = await self._collect_target(page, element)
        if fresh is None:
            return
        target = self._best_target(key, fresh)
        self._last_fill_key = None
        label = element.get("accessibleName") or element.get("text") or element.get("tag")
        await self._emit(
            HoverStep(
                id=self._next_step_id(),
                label=f"{label} 에 마우스 올리기",
                author=self.author,
                tab=tab,
                target=target,
            )
        )

    async def _record_drag(
        self, page: Page, tab: int, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        """끌어다 놓기를 Step 하나로 기록한다 (FR-023c).

        **끄는 대상과 놓는 위치를 모두 확보해야 기록한다.** 한쪽만 있는 Step 은 재실행할
        수 없으므로, 절반만 남기지 않고 사유를 경고로 남긴다.
        """
        drop_element = payload.get("dropElement") or {}
        source = await self._collect_target(page, element)
        destination = await self._collect_target(page, drop_element)
        if source is None or destination is None:
            self._warn(
                "끌어다 놓기에서 끄는 대상 또는 놓는 위치를 식별하지 못해 Step 을 "
                "만들지 못했습니다. 일시정지 중 직접 동작 추가로 보완하세요."
            )
            return

        self._last_fill_key = None
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
                tab=tab,
                target=source,
                drop_target=destination,
            )
        )

    async def _record_select(
        self, page: Page, tab: int, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        """선택을 기록한다.

        **중복 제거**: `change` 와 `blur` 가 같은 선택에 대해 둘 다 도착하므로, 같은
        요소에 같은 값이면 기존 Step 을 갱신한다 (FR-025 와 같은 판정). 값이 다르면 새
        Step 이다 — 같은 셀렉트를 다시 다른 값으로 고른 것은 별개의 동작이다.
        """
        target = await self._collect_target(page, element)
        if target is None:
            return
        css = target.css.value if target.css else ""
        key = (tab, css)
        target = self._best_target(key, target)
        value = str(payload.get("value") or "")

        self._last_fill_key = None
        # 선택이 기록됐다 → 페이지가 살아 있으므로 앞선 클릭은 이동을 만들지 않았다.
        self._nav_suppress.pop(tab, None)
        name = element.get("label") or element.get("accessibleName") or "선택"

        existing_id = self._select_step_ids.get(key)
        if existing_id is not None and self._select_values.get(key) == value:
            await self.sink(
                SelectStep(
                    id=existing_id,
                    label=f"{name} 선택",
                    author=self.author,
                    tab=tab,
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
                tab=tab,
                target=target,
                value=value,
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
        clicked_at = self._nav_suppress.pop(tab.tab_index, None)
        if clicked_at is not None and (time.monotonic() * 1000) - clicked_at < NAV_DEDUPE_MS:
            return
        url = frame.url
        if not url or url == "about:blank":
            return
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



def _usable_count(target: TargetLocator) -> int:
    """실행에 쓸 수 있는 후보 수. `verified` 만 센다 (원칙 IV).

    후보 판정은 `itb.locator.strategy` 한 곳에만 둔다 — 여기서 상태를 다시 해석하면
    Runner·Generator 와 갈라진다.
    """
    return len(ordered_strategies(target))
