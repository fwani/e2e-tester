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

import contextlib
import pathlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from nacl.public import PublicKey
from playwright.async_api import Frame, Page

from itb.domain.locator import CandidateStatus, TargetLocator
from itb.domain.step import (
    Author,
    ClickStep,
    CloseTabStep,
    FillStep,
    NavigateStep,
    SelectStep,
    Step,
)
from itb.execution.session import BrowserSession, TabLimitReachedError
from itb.locator.collector import (
    apply_statuses,
    build_unverified,
    candidate_strategies,
)
from itb.locator.strategy import StrategyKind, ordered_strategies
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

CLICK_DEDUPE_MS = 700
"""같은 요소의 클릭을 한 번으로 접는 시간창.

`pointerdown` 과 `click` 이 같은 클릭에 대해 둘 다 온다. 사람이 같은 버튼을 의도적으로
두 번 누르는 간격보다는 짧고, 한 클릭의 두 이벤트 간격보다는 넉넉하게 잡았다.
"""

SENSITIVE_VARIABLE_PREFIX = "SECRET_"

StepSink = Callable[[Step, int], Awaitable[None]]
"""(step, insert_index) 를 받아 Step 목록에 넣고 이벤트를 발행한다."""


@dataclass(slots=True)
class SensitiveCapture:
    """민감 값 하나를 변수로 옮긴 기록."""

    variable_name: str
    sealed: bool
    """공개키로 봉인해 비밀 파일에 저장했는가. 공개키가 없으면 False."""


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

    active: bool = False
    author: Author = Author.HUMAN
    insert_at: int | None = None
    """None 이면 목록 끝에 붙인다. 일시정지 중이면 그 위치에 삽입한다."""

    _step_seq: int = 0
    _last_click_ms: float = 0.0
    _last_fill_key: tuple[int, str] | None = None
    _last_step_id: str | None = None
    _fill_step_ids: dict[tuple[int, str], str] = field(default_factory=dict)
    """(탭, CSS) → 그 요소의 최근 fill Step id. 중복 제거의 근거다."""

    _fill_values: dict[tuple[int, str], str] = field(default_factory=dict)
    _fill_targets: dict[tuple[int, str], TargetLocator] = field(default_factory=dict)
    """(탭, CSS) → 그 요소에 대해 **가장 잘 검증된** 후보 묶음.

    같은 요소의 확정 이벤트가 화면 이동과 겹치면 재수집 결과가 전부 미수집으로 나온다.
    그때 새 결과로 덮어쓰면 이미 확보한 후보를 잃는다 — 그래서 더 나은 쪽을 남긴다.
    """

    _click_seen: dict[tuple[int, str], float] = field(default_factory=dict)
    """(탭, CSS) → 그 요소의 클릭을 기록한 시각(ms). `pointerdown`·`click` 중복 제거용."""

    _secret_names: dict[tuple[int, str], str] = field(default_factory=dict)
    """(탭, CSS) → 그 요소에 부여한 민감 변수 이름.

    같은 필드가 이벤트를 여러 번 내도 변수는 하나여야 한다. 없으면 한 번의 입력이
    `SECRET_VALUE_1`, `SECRET_VALUE_2` … 로 늘어나 정의와 비밀 파일이 어긋난다.
    """

    _nav_suppress: dict[int, float] = field(default_factory=dict)
    """탭 → 그 탭에서 클릭이 일어난 시각(ms). 다음 이동 하나를 억제하는 데 쓴다."""
    sensitive_captures: list[SensitiveCapture] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _installed: bool = False

    # ─── 설치 ───────────────────────────────────────────────────────────────

    async def install(self) -> None:
        """컨텍스트 단위로 리코더와 콜백 채널을 등록한다.

        네비게이션 이전에 등록해야 한다. 한 번만 설치한다.
        """
        if self._installed:
            return
        context = self.session.context

        # 바운드 메서드를 그대로 넘기지 않는다. Playwright 가 핸들러의 `__self__` 에
        # 래퍼를 캐시하려 하는데 `Recorder` 는 slots 를 쓰므로 `__dict__` 가 없어 실패한다.
        async def on_record(source: dict[str, Any], payload: dict[str, Any]) -> None:
            await self._on_record(source, payload)

        await context.expose_binding(BINDING_NAME, on_record)
        await context.add_init_script(
            script=INJECTED_SCRIPT.read_text(encoding="utf-8")
        )
        # 이미 열려 있는 탭에는 init script 가 적용되지 않았으므로 직접 평가한다.
        for tab in self.session.open_tabs():
            with contextlib.suppress(Exception):
                await tab.page.evaluate(INJECTED_SCRIPT.read_text(encoding="utf-8"))
        for tab in self.session.open_tabs():
            self._watch_navigation(tab.page)
        self._installed = True

    def _watch_navigation(self, page: Page) -> None:
        """main frame 네비게이션을 Python 측에서 듣는다.

        JS `beforeunload` 로 잡으면 페이지가 사라지는 중에 바인딩 호출이 유실될 수 있다.
        """
        page.on("framenavigated", lambda frame: self._on_navigated(page, frame))

    def watch_new_tab(self, page: Page) -> None:
        """새 탭에도 네비게이션 감시를 붙인다. `context.on("page")` 에서 호출한다."""
        self._watch_navigation(page)

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
        if not self.active:
            return
        page: Page = source["page"]
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

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    # ─── 후보 수집 + 기록 시점 검증 (원칙 IV) ─────────────────────────────

    async def _collect_target(
        self, page: Page, element: dict[str, Any], warn_on_failure: bool = True
    ) -> TargetLocator | None:
        """후보를 수집하고 **즉시 검증**해 상태를 채운다.

        검증이 없으면 `StepInspector` 표시가 추측이 되고 SC-008 을 기록 시점에 측정할 수
        없다 (research R4).

        `warn_on_failure=False` 는 사전 수집(hover) 경로용이다 — 지나가는 요소마다 경고를
        쌓으면 정작 Step 이 만들어지지 않은 경고가 묻힌다.
        """
        try:
            target = build_unverified(element, self.test_id_attribute)
        except ValueError:
            # CSS 조차 없는 경우. 기록할 수 없다.
            if warn_on_failure:
                self._warn(
                    "대상 요소를 식별할 정보를 전혀 수집하지 못해 Step 을 만들지 못했습니다."
                )
            return None

        css = target.css.value if target.css else None
        anchor = None
        if css:
            with contextlib.suppress(Exception):
                anchor = await page.query_selector(css)

        statuses: dict[StrategyKind, CandidateStatus] = {}
        for kind, strategy in candidate_strategies(target):
            statuses[kind] = await self._verify(page, strategy, anchor)
        return apply_statuses(target, statuses)

    async def _verify(
        self, page: Page, strategy: Any, anchor: Any
    ) -> CandidateStatus:
        """후보 하나를 실제로 찾아 상태를 판정한다."""
        from itb.execution.locator_runtime import to_locator

        try:
            locator = to_locator(page, strategy)
            count = await locator.count()
        except Exception:  # noqa: BLE001 - 잘못된 셀렉터는 미수집으로 본다
            return CandidateStatus.NOT_COLLECTED

        if count == 0:
            return CandidateStatus.NOT_COLLECTED
        if count > 1:
            # 실측에서 text·css 후보가 각각 2·3개를 매칭했다 (FR-019b).
            return CandidateStatus.AMBIGUOUS
        if anchor is None:
            return CandidateStatus.UNVERIFIED
        try:
            other = await locator.element_handle()
            same = await page.evaluate("([a, b]) => a === b", [anchor, other])
        except Exception:  # noqa: BLE001
            return CandidateStatus.UNVERIFIED
        return CandidateStatus.VERIFIED if same else CandidateStatus.UNVERIFIED

    # ─── Step 기록 ─────────────────────────────────────────────────────────

    async def _emit(self, step: Step) -> None:
        index = self.insert_at if self.insert_at is not None else -1
        self._last_step_id = step.id
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
        import time

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

    def _sensitive_variable_name(self, element: dict[str, Any]) -> str:
        """민감 변수 이름을 만든다. 반드시 `[A-Z][A-Z0-9_]*` 를 지켜야 한다.

        `isalnum()` 은 한글도 참이므로 쓸 수 없다 — 한글 라벨("비밀번호")을 그대로 쓰면
        변수 이름 패턴을 위반해 **저장 시 테스트 검증이 실패한다.** 그래서 ASCII 영숫자만
        남기고, 남는 것이 없으면(한글 전용 라벨) 순번을 쓴다.
        """
        candidates = (
            element.get("attributes", {}).get("name"),
            element.get("attributes", {}).get(self.test_id_attribute),
            element.get("label"),
        )
        for base in candidates:
            if not isinstance(base, str):
                continue
            slug = "".join(
                ch if ("a" <= ch.lower() <= "z" or ch.isdigit()) else "_" for ch in base
            ).upper()
            slug = "_".join(part for part in slug.split("_") if part)
            if slug and not slug[0].isdigit():
                return f"{SENSITIVE_VARIABLE_PREFIX}{slug}"[:60]

        # ASCII 로 쓸 수 있는 근거가 없다. 순번으로 유일성을 확보한다.
        return f"{SENSITIVE_VARIABLE_PREFIX}VALUE_{len(self.sensitive_captures) + 1}"

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
        """
        if not sensitive or not raw_value:
            return raw_value

        # 같은 필드는 이벤트를 여러 번 내도 변수 하나를 쓴다. 이름을 매번 새로 만들면
        # 입력 한 번이 `SECRET_VALUE_1`, `SECRET_VALUE_2` … 로 늘어난다.
        cache_key = key if key is not None else self._element_key(element)
        variable = self._secret_names.get(cache_key)
        if variable is None:
            variable = self._sensitive_variable_name(element)
            self._secret_names[cache_key] = variable

        sealed = False
        if self.store is not None and self.public_key is not None:
            with contextlib.suppress(Exception):
                self.store.put(variable, raw_value, self.public_key)
                sealed = True
        if not sealed:
            self._warn(
                f"민감 값을 보관할 공개키가 없어 {variable} 의 값을 저장하지 못했습니다. "
                "키를 만든 뒤 값을 다시 입력하거나 환경 변수로 공급하세요."
            )
        existing = next(
            (c for c in self.sensitive_captures if c.variable_name == variable), None
        )
        if existing is None:
            self.sensitive_captures.append(
                SensitiveCapture(variable_name=variable, sealed=sealed)
            )
        elif sealed:
            existing.sealed = True
        return f"{{{{{variable}}}}}"

    async def _record_select(
        self, page: Page, tab: int, element: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        target = await self._collect_target(page, element)
        if target is None:
            return
        self._last_fill_key = None
        # 선택이 기록됐다 → 페이지가 살아 있으므로 앞선 클릭은 이동을 만들지 않았다.
        self._nav_suppress.pop(tab, None)
        name = element.get("label") or element.get("accessibleName") or "선택"
        await self._emit(
            SelectStep(
                id=self._next_step_id(),
                label=f"{name} 선택",
                author=self.author,
                tab=tab,
                target=target,
                value=str(payload.get("value") or ""),
            )
        )

    def _on_navigated(self, page: Page, frame: Frame) -> None:
        """main frame 네비게이션 → navigate Step.

        클릭 직후 짧은 시간창 안의 네비게이션은 중복으로 보고 건너뛴다.
        """
        if not self.active or frame != page.main_frame:
            return
        import asyncio
        import time

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
