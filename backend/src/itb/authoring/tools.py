"""에이전트 도구 표면. FR-061·FR-062·FR-066·FR-086 (T111, research R5).

**도구는 Step 종류와 1:1이다.** 이것이 원칙 I 을 에이전트 쪽에서 지키는 방법이다.
에이전트가 할 수 있는 모든 일이 표현 가능한 Step 이므로, "AI 결과를 결정적 Step 으로
컴파일"(FR-061)이 별도의 변환 작업이 아니라 **기록의 부산물**이 된다 — 컴파일 단계에서
표현 불가능한 동작을 만나 실패하는 경우가 원리적으로 없다.

| 도구 | Step |
|------|------|
| `click`·`fill`·`select`·`navigate`·`hover`·`drag`·`close_tab` | 같은 이름의 Step |
| `assert_condition` | `assertion` |
| `list_tabs`·`observe_page` | 없음 (읽기 전용) |
| `report_blocked` | 없음 (FR-069 실패 경로) |

`hover`·`drag` 는 Step 종류가 8종이 된 뒤 1:1 을 회복하기 위해 더했다 (T163).

**`execute_javascript` 도구를 두지 않는다.** 표현할 수 있는 Step 이 없고 FR-086(브라우저
조작 범위를 넘는 동작 금지)에도 걸린다. 이 부재를 테스트로 고정한다 (T106).

**에이전트가 CSS 셀렉터를 짜지 않는다.** `observe_page` 가 요소마다 `element_ref` 를
부여하고, 도구 실행 시 그 요소에서 후보를 수집·검증하는 것은 **제품**이다. 셀렉터를 짜게
하면 원칙 IV 의 후보 수집을 건너뛰어 생성된 테스트가 취약해진다.
"""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from itb.domain.assertion import Assertion, AssertionKind, MatchMode
from itb.domain.step import (
    AssertionStep,
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
from itb.execution.element_probe import collect_by_selector, describe_element
from itb.execution.session import BrowserSession, TabNotFoundError
from itb.execution.step_edits import (
    EditResult,
    FieldNotSupportedError,
    StepNotFoundError,
    ValueNotSupportedError,
    delete_step,
    find_index,
    reorder_steps,
    update_step,
)
from itb.execution.step_executor import StepExecutor, StepFailure
from itb.secrets.capture import SensitiveCapturer

MAX_TOOL_CALLS = 40
"""도구 호출 총 상한 (FR-066).

**하드 루프 카운터가 1차 방어선이다** (research R5). 모델에게 페이스 조절을 맡기는 장치
(task budget)는 권고적이며 이것을 대체하지 못한다.
"""

MAX_CONSECUTIVE_ELEMENT_FAILURES = 3
"""같은 요소를 연달아 실패한 횟수 상한 (FR-066).

같은 버튼을 40번 누르게 두지 않는다. 세 번 실패했으면 그 경로는 막힌 것이고, 사용자에게
넘기는 것이 맞다 (FR-069).
"""

OBSERVE_ELEMENT_LIMIT = 120
"""한 번에 보여 줄 요소 수 상한. 화면이 크면 컨텍스트를 다 먹는다."""


@dataclass(slots=True)
class AttemptLimits:
    """시도 횟수 추적. **제품 코드가 센다** (research R5).

    **상한 도달을 예외로 알리지 않는다.** SDK 의 tool runner 는 도구가 던진 예외를 모두
    잡아 `is_error` 도구 결과로 바꿔 모델에게 돌려준다 — 예외로는 루프를 끊을 수 없고,
    모델이 같은 도구를 계속 부르면 같은 예외가 반복될 뿐이다.

    그래서 상한 도달은 **상태로 남긴다.** 도구는 그 뒤 아무 조작도 하지 않고 "상한에
    도달했으니 더 시도하지 말라" 를 결과로 돌려주며, 우리가 소유한 `async for` 본문이
    그 상태를 보고 루프를 끊는다 (`AuthoringAgent._drive`).
    """

    max_calls: int = MAX_TOOL_CALLS
    max_element_failures: int = MAX_CONSECUTIVE_ELEMENT_FAILURES
    calls: int = 0
    failures_by_element: dict[str, int] = field(default_factory=dict)
    last_failed_element: str | None = None
    exceeded_reason: str | None = None
    """상한에 도달한 사유. None 이 아니면 루프를 끊어야 한다."""

    @property
    def exceeded(self) -> bool:
        return self.exceeded_reason is not None

    def record_call(self) -> bool:
        """도구 호출 하나를 센다. 계속 진행해도 되면 True.

        False 를 돌려준 뒤에는 어떤 조작도 하지 않는다 — 상한을 넘긴 호출이 화면을
        바꾸면 사용자가 보는 상태와 기록된 Step 이 어긋난다.
        """
        if self.exceeded:
            return False
        if self.calls >= self.max_calls:
            # **거절된 호출은 세지 않는다.** 카운터는 실제로 진행한 호출 수여야 하고,
            # 그것이 `ai_finished`·진단에 실려 나가는 값이다.
            self.exceeded_reason = (
                f"도구 호출이 상한({self.max_calls}회)에 도달해 중단했습니다. "
                "지시가 너무 크거나 화면에서 길을 찾지 못하고 있습니다. "
                "그때까지 성공한 동작은 Step 으로 남아 있습니다."
            )
            return False
        self.calls += 1
        return True

    def record_failure(self, element: str) -> None:
        """요소 하나에 대한 실패를 센다. **연속 실패만 센다.**

        서로 다른 요소를 각각 한 번 실패한 것은 막힌 것이 아니라 화면을 탐색하는 중이다.
        """
        if self.last_failed_element != element:
            self.failures_by_element[element] = 0
        self.last_failed_element = element
        count = self.failures_by_element.get(element, 0) + 1
        self.failures_by_element[element] = count
        if count >= self.max_element_failures and not self.exceeded:
            self.exceeded_reason = (
                f"같은 요소에 {count}회 연속 실패해 중단했습니다: {element}. "
                "그때까지 성공한 동작은 Step 으로 남아 있습니다."
            )

    def record_success(self, element: str | None = None) -> None:
        """성공하면 연속 실패 기록을 지운다."""
        if element is not None:
            self.failures_by_element.pop(element, None)
        self.last_failed_element = None

    def reset(self) -> None:
        """재시도·건너뛰기 때 예산을 새로 준다 (FR-072·FR-073).

        앞선 시도가 쓴 호출까지 상한에 포함하면 사용자가 "다시" 를 누르는 순간 이미
        상한에 닿아 있을 수 있다.
        """
        self.calls = 0
        self.failures_by_element.clear()
        self.last_failed_element = None
        self.exceeded_reason = None


STOP_NOTICE = {
    "stop": True,
    "message": (
        "시도 상한에 도달했습니다. 더 이상 도구를 부르지 마세요. "
        "무엇이 막았는지 한 줄로 정리하고 끝내세요."
    ),
}
"""상한 도달 후 모든 도구가 돌려주는 결과.

조용히 실패를 반복하지 않고 **모델에게도 멈추라고 말한다.** 우리가 루프를 끊긴 하지만,
모델이 그 사이에 같은 시도를 더 하는 것을 줄이는 것이 낫다.
"""


@dataclass(frozen=True, slots=True)
class ObservedElement:
    """`observe_page` 가 부여한 요소 참조.

    `ref` 는 이 세션 안에서만 뜻이 있다. 에이전트가 다음 도구 호출에서 지목할 이름이며,
    실제 요소 식별은 `css` 를 통해 제품이 한다.
    """

    ref: str
    css: str
    tag: str
    role: str | None
    name: str | None
    visible: bool
    disabled: bool


StepSink = Callable[[Step], Awaitable[None]]
"""성공한 동작을 Step 으로 확정하는 통로. `compiler` 가 구현한다."""

ProgressSink = Callable[[str], Awaitable[None]]
"""`ai_progress` 발행 통로 (FR-060)."""


EditSink = Callable[["EditResult"], Awaitable[None]]
"""편집 결과를 받는 통로 (016 US3).

`StepSink` 와 대칭이다 — 그쪽은 「새 Step 하나」를, 이쪽은 「바뀐 목록 전체」를 나른다.
편집 연산(`step_edits`)이 새 목록을 돌려주므로 모양이 그렇게 갈린다.
"""


@dataclass(slots=True)
class BrowserToolbox:
    """에이전트가 브라우저에 할 수 있는 일 전부.

    **SDK 를 알지 못한다.** 도구 데코레이터를 붙이는 것은 `build_tools` 가 하고, 이
    클래스는 순수한 async 메서드만 갖는다 — 그래서 자격 증명 없이 테스트할 수 있고,
    도구 표면과 Step 종류의 1:1 대응을 단위 테스트로 고정할 수 있다 (T106).
    """

    session: BrowserSession
    executor: StepExecutor
    allocate_step_id: Callable[[], str]
    on_step: StepSink
    on_progress: ProgressSink | None = None
    capturer: SensitiveCapturer | None = None
    on_variable: Callable[[str], None] | None = None
    """민감 변수가 새로 생겼음을 알리는 통로.

    저장 전 세션에는 `Test.variables` 가 없으므로, 등록하지 않으면 방금 만든 참조를
    실행기가 "정의되지 않은 변수" 로 거절한다.
    """

    # ─── 편집 도구가 쓰는 통로 (016 US3) ─────────────────────────────────
    #
    # **목록을 소유하지 않는다.** 만드는 도구가 `on_step` 으로 넘기는 것과 같은
    # 구조다 — 소유하면 실패 경로에서 Step 이 사라질 자리가 하나 더 생긴다 (FR-067).
    steps_source: Callable[[], list[Step]] | None = None
    """지금 작업 중 목록을 읽는 통로. 없으면 편집 도구가 「준비되지 않았다」를 돌려준다."""

    on_edit: EditSink | None = None
    """편집 결과를 세션에 반영하고 이벤트를 발행하는 통로.

    **사람의 편집과 같은 이벤트로 나가야 한다** (FR-039). 그래서 발행을 여기서 하지
    않고 호출자에게 맡긴다 — 두 곳에서 발행하면 화면이 같은 변경을 두 번 받는다.
    """

    in_scope: Callable[[str], bool] | None = None
    """이 Step 을 고칠 수 있는가 (FR-037 · 불변식 8).

    없으면 **아무것도 고칠 수 없다.** 기본값이 「전부 허용」이면, 배선을 빠뜨린 경로에서
    AI 가 사용자의 멀쩡한 Step 을 건드린다 — 모르는 것을 참으로 보지 않는다.
    """

    test_id_attribute: str = "data-testid"
    limits: AttemptLimits = field(default_factory=AttemptLimits)
    author: Author = Author.AI

    refs: dict[str, ObservedElement] = field(default_factory=dict)
    _ref_seq: int = 0
    blocked_reason: str | None = None
    blocked_question: str | None = None
    """막힌 김에 **사람에게 물을 것** (2026-09-10 사용자 결정).

    `blocked_reason` 과 갈라 둔다. 사유는 「왜 못 했는가」이고 질문은 「무엇을 알려 주면
    되는가」다 — 뭉치면 화면이 답 칸을 무엇에 대해 여는지 말할 수 없다.
    """

    # ─── 읽기 전용 도구 ────────────────────────────────────────────────────

    async def list_tabs(self) -> dict[str, Any]:
        """열린 탭 목록. 조작하지 않는다."""
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        tabs = []
        for handle in self.session.tabs:
            tabs.append(
                {
                    "tab": handle.tab_index,
                    "url": handle.url,
                    "title": await handle.title(),
                    "closed": handle.closed,
                }
            )
        return {"tabs": tabs, "active_tab": self.session.active_tab_index}

    async def observe_page(self, tab: int = 0) -> dict[str, Any]:
        """지정 탭의 상호작용 가능한 요소 목록과 화면 텍스트. 조작하지 않는다.

        **여기서 부여한 `element_ref` 만 다른 도구에 넘길 수 있다.** 에이전트가 셀렉터를
        만들어 넘기면 후보 수집을 건너뛰게 되므로 받지 않는다.
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        # 관찰은 Step 을 만들지 않지만 **시간이 든다.** 알리지 않으면 그 동안 화면이
        # 조용하고, 사용자는 AI 가 멈춘 줄 안다.
        await self._announce("화면을 살펴보는 중" + (f" (탭 {tab})" if tab else ""))
        handle = self._tab(tab)
        try:
            raw = await handle.page.evaluate(
                "(limit) => (typeof window.__itbObserve === 'function'"
                " ? window.__itbObserve(limit) : null)",
                OBSERVE_ELEMENT_LIMIT,
            )
        except Exception as exc:  # noqa: BLE001 - 문서 교체 중일 수 있다
            return {"error": f"화면을 읽을 수 없습니다: {type(exc).__name__}"}
        if not isinstance(raw, dict):
            return {"error": "화면 관찰 스크립트가 주입되지 않았습니다."}

        elements: list[dict[str, Any]] = []
        for entry in raw.get("elements") or []:
            css = entry.get("css")
            if not isinstance(css, str) or not css:
                continue
            self._ref_seq += 1
            ref = f"e{self._ref_seq}"
            observed = ObservedElement(
                ref=ref,
                css=css,
                tag=str(entry.get("tag") or ""),
                role=entry.get("role"),
                name=entry.get("name"),
                visible=bool(entry.get("visible")),
                disabled=bool(entry.get("disabled")),
            )
            self.refs[ref] = observed
            elements.append(
                {
                    "element_ref": ref,
                    "tag": observed.tag,
                    "role": observed.role,
                    "name": observed.name,
                    "visible": observed.visible,
                    "disabled": observed.disabled,
                    "type": entry.get("type"),
                }
            )
        return {
            "tab": tab,
            "url": raw.get("url"),
            "title": raw.get("title"),
            "text": raw.get("text"),
            "elements": elements,
        }

    # ─── 조작 도구 — Step 과 1:1 ───────────────────────────────────────────

    async def click(self, element_ref: str) -> dict[str, Any]:
        return await self._act_on_element(
            element_ref, lambda step_id, target, tab: ClickStep(
                id=step_id, label=self._label(element_ref, "클릭"), author=self.author,
                tab=tab, target=target,
            )
        )

    async def hover(self, element_ref: str) -> dict[str, Any]:
        return await self._act_on_element(
            element_ref, lambda step_id, target, tab: HoverStep(
                id=step_id, label=self._label(element_ref, "에 마우스 올리기"),
                author=self.author, tab=tab, target=target,
            )
        )

    async def fill(self, element_ref: str, value: str) -> dict[str, Any]:
        """입력. **비밀번호 유형 필드의 값은 변수 참조로 바꿔 저장한다** (FR-082a).

        AI 가 넣은 값도 사람이 넣은 값과 같은 규칙을 지나야 한다 — 경로에 따라 한쪽만
        평문이 남으면 그 사실은 그 경로를 지나는 테스트가 없을 때 드러나지 않는다.
        """
        observed = self.refs.get(element_ref)
        stored = value
        if observed is not None and await self._is_password(observed):
            if self.capturer is None:
                return {
                    "error": (
                        "비밀번호 필드에 값을 넣으려면 민감 값 보관이 필요합니다. "
                        "이 세션에서는 지원되지 않습니다."
                    )
                }
            stored = self.capturer.to_reference(
                value,
                cache_key=observed.css,
                name_basis=(observed.name, observed.css),
            )
            if self.on_variable is not None and stored.startswith("{{"):
                self.on_variable(stored[2:-2])

        return await self._act_on_element(
            element_ref,
            lambda step_id, target, tab: FillStep(
                id=step_id, label=self._label(element_ref, "입력"), author=self.author,
                tab=tab, target=target, value=stored,
            ),
        )

    async def select(self, element_ref: str, value: str) -> dict[str, Any]:
        return await self._act_on_element(
            element_ref,
            lambda step_id, target, tab: SelectStep(
                id=step_id, label=self._label(element_ref, "선택"), author=self.author,
                tab=tab, target=target, value=value,
            ),
        )

    async def upload(self, element_ref: str, file_name: str) -> dict[str, Any]:
        """파일 입력에 파일을 넣는다 (2026-09-09 · `upload` Step).

        **AI 도 이 Step 을 만들 수 있어야 한다.** 도구 표면과 Step 종류는 1:1 이고
        (T163 · `test_agent_tools`), 그 불변식이 지키는 것은 「사람은 만들 수 있는데 AI 는
        만들 수 없는 Step 종류」가 생기지 않는 것이다. 새 종류를 더하면서 도구를 빼면
        AI 작성은 그 자리에서 조용히 막힌다.

        **파일 내용은 다루지 않는다.** 정의에 남는 것은 이름뿐이고(`UploadStep`) 실행은
        같은 이름의 빈 파일을 올린다 — 사람이 녹화한 경우와 같은 동작이다. AI 가 실제
        파일을 만들거나 고르는 경로는 없다 (FR-086 — 브라우저 조작 범위를 넘지 않는다).
        """
        name = file_name.strip()
        if not name:
            return {
                "error": (
                    "올릴 파일 이름이 비어 있습니다. 확장자를 포함한 이름을 주세요 "
                    "(예: 보고서.xlsx)."
                )
            }
        return await self._act_on_element(
            element_ref,
            lambda step_id, target, tab: UploadStep(
                id=step_id,
                label=f"{self._label(element_ref, '에 파일 올리기')} ({name})",
                author=self.author,
                tab=tab,
                target=target,
                file_name=name,
            ),
        )

    async def drag(self, element_ref: str, drop_ref: str) -> dict[str, Any]:
        """끌어다 놓기. **양 끝을 모두 요구한다** (contracts/step-dsl §hover 와 drag)."""
        drop = self.refs.get(drop_ref)
        if drop is None:
            return {
                "error": (
                    f"놓는 위치 참조를 찾을 수 없습니다: {drop_ref}. "
                    "observe_page 를 다시 부르세요."
                )
            }
        tab = self._tab_of_ref(drop_ref)
        drop_target = await collect_by_selector(
            self._tab(tab).page, drop.css, self.test_id_attribute
        )
        if drop_target is None:
            return {"error": f"놓는 위치의 식별 정보를 수집하지 못했습니다: {drop_ref}"}

        return await self._act_on_element(
            element_ref,
            lambda step_id, target, tab_index: DragStep(
                id=step_id,
                label=self._label(element_ref, f"을 {drop.name or drop_ref} 으로 끌어다 놓기"),
                author=self.author,
                tab=tab_index,
                target=target,
                drop_target=drop_target,
            ),
        )

    async def navigate(self, url: str) -> dict[str, Any]:
        """화면 이동. 요소를 지목하지 않는 유일한 조작 도구다."""
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        if not url.startswith(("http://", "https://")):
            return {"error": "http 또는 https 주소만 이동할 수 있습니다 (FR-085)."}
        step = NavigateStep(
            id=self.allocate_step_id(),
            label=f"화면 이동 {url}",
            author=self.author,
            tab=self.session.active_tab_index,
            url=url,
        )
        return await self._execute(step, element=url)

    async def close_tab(self, tab: int) -> dict[str, Any]:
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        step = CloseTabStep(
            id=self.allocate_step_id(),
            label=f"탭 {tab} 닫기",
            author=self.author,
            tab=tab,
        )
        return await self._execute(step, element=f"tab:{tab}")

    async def assert_condition(
        self,
        kind: str,
        element_ref: str | None = None,
        value: str | None = None,
        match: str = "equals",
    ) -> dict[str, Any]:
        """검증 Step 을 만들고 **즉시 확인한다** (FR-013a 의 4종만).

        확인하지 않고 기록하면 통과하지 않는 검증이 정의에 들어간다. 성공한 동작만
        Step 으로 남긴다는 규칙(FR-061)이 검증에도 적용된다.
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        try:
            assertion_kind = AssertionKind(kind)
            match_mode = MatchMode(match)
        except ValueError:
            return {
                "error": (
                    f"지원하지 않는 검증 종류입니다: {kind}. "
                    "visible / hidden / text / url 중 하나여야 합니다."
                )
            }

        tab = self.session.active_tab_index
        target = None
        if element_ref is not None:
            observed = self.refs.get(element_ref)
            if observed is None:
                return {"error": f"요소 참조를 찾을 수 없습니다: {element_ref}."}
            tab = self._tab_of_ref(element_ref)
            target = await collect_by_selector(
                self._tab(tab).page, observed.css, self.test_id_attribute
            )
            if target is None:
                return {"error": f"검증 대상의 식별 정보를 수집하지 못했습니다: {element_ref}"}

        try:
            assertion = Assertion(
                kind=assertion_kind, target=target, match=match_mode, value=value
            )
        except ValueError as exc:
            return {"error": f"검증 조건이 올바르지 않습니다: {exc}"}

        step = AssertionStep(
            id=self.allocate_step_id(),
            label=self._assertion_label(assertion),
            author=self.author,
            tab=tab,
            assertion=assertion,
        )
        return await self._execute(step, element=element_ref or f"assert:{kind}")

    async def report_blocked(
        self, reason: str, question: str | None = None
    ) -> dict[str, Any]:
        """수행 불가 선언 (FR-069). 루프를 끊고 사용자 선택으로 넘긴다.

        `question` 은 **사람에게 물을 한 문장**이다 (2026-09-10 사용자 결정). 새 도구를
        만들지 않고 여기에 붙이는 이유는 도구 표면이 계약이기 때문이다 (`TOOL_NAMES`) —
        늘리면 Step 종류와의 1:1 이 깨진다. 물을 것이 있다는 사실은 **막힘의 성질**이지
        별개의 동작이 아니다.
        """
        self.limits.record_call()
        # **예외를 던지지 않는다.** SDK 가 도구 예외를 잡아 모델에게 돌려주므로 예외로는
        # 루프를 끊을 수 없다. 상태로 남기고 우리가 소유한 루프 본문이 끊는다.
        self.blocked_reason = reason
        self.blocked_question = (question or "").strip() or None
        return {
            "acknowledged": True,
            "message": "수행 불가를 접수했습니다. 사용자가 이어서 처리합니다. 끝내세요.",
        }

    # ─── 내부 ───────────────────────────────────────────────────────────────

    def _tab(self, tab: int) -> Any:
        handle = self.session.find_tab(tab)
        if handle is None or handle.closed:
            msg = f"탭 {tab} 이 열려 있지 않습니다."
            raise TabNotFoundError(msg)
        return handle

    def _tab_of_ref(self, _ref: str) -> int:
        """참조가 어느 탭의 것인지.

        `observe_page` 가 탭 단위로 도는데 참조에 탭을 새기지 않는 이유는, 같은 화면을
        여러 번 관찰할 때 참조가 계속 늘어나기 때문이다. 지금 활성 탭을 쓴다 — 관찰과
        조작 사이에 탭이 바뀌면 실행이 실패하고 그 사실이 도구 결과로 돌아간다.
        """
        return self.session.active_tab_index

    def _label(self, element_ref: str, suffix: str) -> str:
        observed = self.refs.get(element_ref)
        name = (observed.name if observed else None) or (
            observed.tag if observed else element_ref
        )
        return f"{name} {suffix}".strip()

    @staticmethod
    def _assertion_label(assertion: Assertion) -> str:
        from itb.execution.assertion_builder import default_label

        return default_label(assertion)

    async def _is_password(self, observed: ObservedElement) -> bool:
        """비밀번호 유형 필드인가 (FR-082a).

        요소 설명을 다시 읽어 판정한다 — 관찰 시점의 `type` 만 믿으면 화면이 바뀐 뒤
        엉뚱한 요소를 비밀번호로 취급할 수 있다.
        """
        handle = self.session.find_tab(self.session.active_tab_index)
        if handle is None or handle.closed:
            return False
        element = await describe_element(handle.page, observed.css)
        if element is None:
            return False
        attrs = element.get("attributes") or {}
        return str(attrs.get("type") or "").lower() == "password"

    # ─── 편집 도구 (016 US3 · contracts/agent-tools.md §2) ────────────────
    #
    # **넷 다 사람의 편집과 같은 순수 함수를 지난다** (`itb.execution.step_edits`).
    # 원칙 I 이 문서의 약속이 아니라 코드의 성질이 되는 지점이다 — 같은 함수를 지나면
    # 다를 수가 없다.
    #
    # **거절은 예외가 아니라 반환값이다** (FR-038). SDK 는 도구가 던진 예외를 잡아
    # 모델에게 돌려주므로 예외로는 루프를 끊을 수 없고, 무엇보다 이 거절들은 오류가
    # 아니라 **정상적인 답**이다 — 「그건 내 권한 밖입니다」.

    def _editable(self, step_id: str) -> tuple[list[Step], None] | tuple[None, dict[str, Any]]:
        """편집 준비가 됐고 그 Step 이 권한 범위 안인지 본다 (불변식 8).

        성공하면 지금 목록을, 실패하면 에이전트에게 돌려줄 거절을 반환한다.
        """
        if self.steps_source is None or self.on_edit is None:
            return None, {
                "error": "이 세션에서는 Step 을 고칠 수 없습니다.",
            }
        steps = self.steps_source()
        if self.in_scope is None or not self.in_scope(step_id):
            return None, {
                "error": (
                    f"{step_id} 은 이번에 당신이 만든 Step 이 아니므로 고칠 수 없습니다. "
                    "사람에게 말하세요 — 사람은 편집 화면에서 고칠 수 있습니다."
                )
            }
        try:
            find_index(steps, step_id)
        except StepNotFoundError as exc:
            return None, {"error": str(exc)}
        return steps, None

    def _current_index(self) -> int:
        """편집 연산에 넘길 실행 위치.

        재녹화 세션은 일시정지 상태이고 위치는 세션이 소유한다. 도구는 그 값을 알지
        못하므로 **0 을 넘긴다** — 편집 연산이 이 값으로 하는 일은 「실행된 구간을
        건드렸는가」 경고뿐이고, 그 판정은 반영 시점에 호출자가 다시 한다.
        """
        return 0

    async def update_step(self, step_id: str, field: str, value: str) -> dict[str, Any]:
        """Step 의 편집 가능한 속성을 고친다 (FR-032).

        **고칠 수 있는 필드 목록을 여기 복제하지 않는다.** `step_edits.update_step` 이
        `FieldNotSupportedError` 로 판정하고, 그 사유를 그대로 돌려준다 — 복제하면
        사람이 고칠 수 있는 것과 AI 가 고칠 수 있는 것이 갈린다 (원칙 I).
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        steps, refusal = self._editable(step_id)
        if steps is None:
            return refusal  # type: ignore[return-value]

        await self._announce(f"{step_id} 의 {field} 를 고치는 중")

        kwargs: dict[str, Any] = {field: value}
        try:
            result = update_step(steps, self._current_index(), step_id, **kwargs)
        except TypeError:
            return {
                "error": (
                    f"고칠 수 없는 필드입니다: {field}. "
                    "표시 이름(label)·입력값(value)·제한 시간(timeout_ms) 등을 쓸 수 있습니다."
                )
            }
        except (FieldNotSupportedError, ValueNotSupportedError) as exc:
            return {"error": str(exc)}
        except ValueError as exc:
            return {"error": f"값이 올바르지 않습니다: {exc}"}

        await self.on_edit(result)  # type: ignore[misc]
        changed = next(st for st in result.steps if st.id == step_id)
        return {"ok": True, "step_id": step_id, "field": field, "label": changed.label}

    async def delete_step(self, step_id: str) -> dict[str, Any]:
        """Step 을 지운다 (FR-033).

        **복수 삭제 도구는 만들지 않는다.** 에이전트가 하나씩 부르면 되고, 전부-또는-전무
        보장이 필요한 것은 확정·버리기이지 에이전트의 정리가 아니다.
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        steps, refusal = self._editable(step_id)
        if steps is None:
            return refusal  # type: ignore[return-value]

        await self._announce(f"{step_id} 을 지우는 중")

        result = delete_step(steps, self._current_index(), step_id)
        await self.on_edit(result)  # type: ignore[misc]
        return {"ok": True, "deleted": step_id, "remaining": len(result.steps)}

    async def move_step(self, step_id: str, direction: str) -> dict[str, Any]:
        """Step 을 한 칸 옮긴다 (FR-034).

        **방향만 받는다. 절대 순번을 받지 않는다.** 사람의 조작(`step.moveUp`·
        `step.moveDown`)과 같은 모양이며, 절대 순번을 받으면 에이전트가 목록을 다시
        관찰하지 않고 낡은 순번을 넘길 수 있다.

        **옮길 자리도 권한 범위 안이어야 한다.** 옛 구간 위로 올라가려 하면 거절한다 —
        허용하면 확정이 지울 구간과 남길 것의 경계가 흐려진다.
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        if direction not in ("up", "down"):
            return {"error": f"방향은 up 또는 down 이어야 합니다: {direction}"}
        steps, refusal = self._editable(step_id)
        if steps is None:
            return refusal  # type: ignore[return-value]

        await self._announce(
            f"{step_id} 을 {'위로' if direction == 'up' else '아래로'} 옮기는 중"
        )
        index = find_index(steps, step_id)
        target = index - 1 if direction == "up" else index + 1
        if target < 0 or target >= len(steps):
            return {"error": f"{step_id} 은 이미 {'처음' if direction == 'up' else '끝'}입니다."}
        if self.in_scope is None or not self.in_scope(steps[target].id):
            return {
                "error": (
                    f"그 자리({steps[target].id})는 이번에 당신이 만든 구간 밖입니다. "
                    "만든 Step 들 사이에서만 옮길 수 있습니다."
                )
            }

        order = [st.id for st in steps]
        order[index], order[target] = order[target], order[index]
        result = reorder_steps(steps, self._current_index(), order)
        await self.on_edit(result)  # type: ignore[misc]
        return {"ok": True, "step_id": step_id, "index": target}

    async def repick_target(
        self, step_id: str, element_ref: str, slot: str = "target"
    ) -> dict[str, Any]:
        """Step 의 대상 요소를 다시 지정한다 (FR-035).

        **`element_ref` 만 받는다. 셀렉터를 받지 않는다** (헌법 원칙 IV). 후보 묶음은
        `collect_by_selector` 가 **살아 있는 페이지에서** 새로 수집한다 — 저장되는 것은
        단일 셀렉터가 아니라 후보 묶음이다.

        **`RepickController` 를 쓰지 않는다.** 그것은 「사람의 다음 클릭 한 번을 대상
        지정으로 쓴다」는 대기 상태 기계이고, AI 는 기다릴 것이 없다 — 이미 참조를 갖고
        있다. 같은 이름의 두 기제를 합치면, 사람이 다시 집기를 걸어 둔 상태에서 AI 가
        대상을 바꾸는 경우에 어느 쪽이 이기는지가 정의되지 않는다.
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        if slot not in ("target", "drop_target"):
            return {"error": f"slot 은 target 또는 drop_target 이어야 합니다: {slot}"}
        steps, refusal = self._editable(step_id)
        if steps is None:
            return refusal  # type: ignore[return-value]

        await self._announce(f"{step_id} 의 대상을 다시 지목하는 중")
        observed = self.refs.get(element_ref)
        if observed is None:
            return {
                "error": (
                    f"요소 참조를 찾을 수 없습니다: {element_ref}. "
                    "observe_page 를 먼저 불러 참조를 받으세요."
                )
            }

        step = steps[find_index(steps, step_id)]
        if not hasattr(step, slot):
            return {
                "error": (
                    f"{step.type.value} Step 은 {slot} 을 갖지 않습니다. "
                    "대상을 지목하는 Step 에만 쓸 수 있습니다."
                )
            }

        tab = self._tab_of_ref(element_ref)
        try:
            page = self._tab(tab).page
        except TabNotFoundError as exc:
            return {"error": str(exc)}

        target = await collect_by_selector(page, observed.css, self.test_id_attribute)
        if target is None:
            return {
                "error": (
                    f"요소를 찾지 못했습니다: {observed.name or element_ref}. "
                    "화면이 바뀌었을 수 있습니다. observe_page 로 다시 확인하세요."
                )
            }

        # **모델을 통째로 바꾼다.** 필드만 갈아 끼우면 pydantic 검증을 지나지 않아,
        # 후보가 하나도 없는 `TargetLocator` 같은 상태가 조용히 저장될 수 있다.
        replaced = step.model_copy(update={slot: target, "label": self._label(element_ref, "지목")})
        new_steps = [replaced if st.id == step_id else st for st in steps]
        await self.on_edit(EditResult(new_steps, self._current_index(), []))  # type: ignore[misc]
        return {
            "ok": True,
            "step_id": step_id,
            "label": replaced.label,
            "candidates": sum(
                1
                for c in (target.test_id, target.label, target.text, target.stable_attr, target.css)
                if c is not None
            ),
        }

    async def _announce(self, text: str) -> None:
        """지금 무엇을 하는 중인지 알린다 (FR-060 · 2026-09-11 사용자 요청).

        ## 왜 **하기 전에** 알리는가

        이전에는 `_execute` 가 **성공한 뒤에** Step 이름 하나를 보냈다. 그래서:

        - 요소를 기다리는 동안(최대 `timeout_ms`) 화면이 조용하다 — 사용자에게는
          「멈춘 것」과 「기다리는 것」이 같아 보인다
        - **실패하면 아무것도 보고되지 않는다.** 무엇을 하다 실패했는지 남지 않는다
        - 관찰·편집처럼 Step 을 만들지 않는 도구는 아예 흔적이 없다

        사용자가 읽는 것은 「AI 가 지금 무엇을 하는 중인지」이고, 그것은 **시도**의
        기록이지 성공의 기록이 아니다.

        보고에 실패해도 도구를 멈추지 않는다 — 진행 표시는 곁가지이고, 그것 때문에
        작성이 끊기면 안 된다.
        """
        if self.on_progress is None:
            return
        with contextlib.suppress(Exception):
            await self.on_progress(text)

    async def _act_on_element(
        self,
        element_ref: str,
        make_step: Callable[[str, Any, int], Step],
    ) -> dict[str, Any]:
        """요소를 지목하는 조작의 공통 경로.

        **후보 수집·검증은 여기서 제품이 한다** — 에이전트가 준 것은 참조 하나뿐이다.
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        observed = self.refs.get(element_ref)
        if observed is None:
            return {
                "error": (
                    f"요소 참조를 찾을 수 없습니다: {element_ref}. "
                    "observe_page 를 먼저 불러 참조를 받으세요."
                )
            }

        tab = self._tab_of_ref(element_ref)
        try:
            page = self._tab(tab).page
        except TabNotFoundError as exc:
            self.limits.record_failure(element_ref)
            return {"error": str(exc)}

        target = await collect_by_selector(page, observed.css, self.test_id_attribute)
        if target is None:
            self.limits.record_failure(element_ref)
            return {
                "error": (
                    f"요소를 찾지 못했습니다: {observed.name or element_ref}. "
                    "화면이 바뀌었을 수 있습니다. observe_page 로 다시 확인하세요."
                )
            }

        step = make_step(self.allocate_step_id(), target, tab)
        return await self._execute(step, element=element_ref)

    async def _execute(self, step: Step, element: str) -> dict[str, Any]:
        """Step 을 실행하고 **성공한 경우에만** 기록한다 (FR-061).

        실행에 쓰는 것은 재실행과 **같은 `StepExecutor`** 다. 그래서 "AI 로 만든 테스트가
        재실행에서 통과한다" 가 별도의 보장이 아니라 같은 코드를 지난 결과가 된다.
        """
        tabs_before = len(self.session.tabs)
        # **하기 전에 알린다.** 요소를 기다리는 동안 화면이 조용하면 사용자는 멈춘
        # 것과 기다리는 것을 구별할 수 없다 (`_announce` 머리말).
        await self._announce(f"{step.label} — 수행 중")
        try:
            await self.executor.execute(step)
        except StepFailure as exc:
            self.limits.record_failure(element)
            await self._announce(f"{step.label} — 실패: {exc}")
            return {"error": str(exc)}
        except TabNotFoundError as exc:
            self.limits.record_failure(element)
            await self._announce(f"{step.label} — 실패: {exc}")
            return {"error": str(exc)}

        self.limits.record_success(element)
        await self.on_step(step)
        await self._announce(f"{step.label} — 완료")

        result: dict[str, Any] = {"ok": True, "step": step.label}
        # 새 탭 열림을 도구 결과에 덧붙인다 — 에이전트가 탭 전환을 스스로 판단하려면
        # 열림을 관측할 수 있어야 한다 (research R5).
        opened = self.session.tabs[tabs_before:]
        if opened:
            result["opened_tabs"] = [t.tab_index for t in opened]
            result["note"] = (
                f"새 탭 {', '.join(str(t.tab_index) for t in opened)} 이 열렸습니다. "
                "그 탭을 조작하려면 observe_page(tab) 로 먼저 관찰하세요."
            )
        return result


# ─── SDK 도구 정의 ──────────────────────────────────────────────────────────

READ_ONLY_TOOLS: tuple[str, ...] = (
    "list_tabs",
    "observe_page",
)
"""화면을 읽기만 하는 도구. 조작하지 않으므로 Step 을 만들지 않는다."""

CONTROL_TOOLS: tuple[str, ...] = ("report_blocked",)
"""루프의 흐름을 바꾸는 도구. Step 을 만들지 않고 **에이전트를 멈춘다** (FR-069).

016 이전에는 분류가 없었다. 「`TOOL_NAMES` 는 계약이다」라는 문장이 정확히는
`STEP_PRODUCING_TOOLS` 에 대한 것이었는데, 그 사실을 적을 자리가 없어서 `report_blocked`
와 `observe_page` 가 계약 밖에 떠 있었다 (baseline.md T002).
"""

STEP_EDITING_TOOLS: tuple[str, ...] = (
    "update_step",
    "delete_step",
    "move_step",
    "repick_target",
)
"""Step 을 **고치는** 도구 (016 US3).

**새 Step 종류를 만들지 않는다** — 그래서 `STEP_PRODUCING_TOOLS` ↔ Step 종류의 1:1 이
그대로다 (FR-040). 넷 다 사람의 편집과 **같은 순수 함수**(`itb.execution.step_edits`)를
지나므로, 결과가 다를 수가 없다 (원칙 I · FR-036).

권한은 **이번 세션이 만든 Step** 으로 한정된다 (FR-037 · 불변식 8). 그 한정이 되돌리기를
스냅샷 없이 성립시킨다 (research R7).
"""

TOOL_NAMES: tuple[str, ...] = (
    *READ_ONLY_TOOLS,
    *(
        "click",
        "fill",
        "select",
        "navigate",
        "hover",
        "drag",
        "upload",
        "assert_condition",
        "close_tab",
    ),
    *STEP_EDITING_TOOLS,
    *CONTROL_TOOLS,
)
"""도구 표면 전체 (16종). **네 분류의 합집합이며, 그것이 계약이다.**

016 이 12 → 16 으로 넓혔다. 넓히는 것이 아니라 **정확히 적는 것**이었다 — 「늘리면 Step
종류와의 1:1 이 깨진다」는 옛 문장은 실제로는 `STEP_PRODUCING_TOOLS` 에 대한 것이고,
`observe_page`·`report_blocked` 는 이미 Step 을 만들지 않으면서 이 목록에 있었다.

검사(`test_tool_surface.py`)가 네 분류의 합집합이 이 목록과 같고 교집합이 없음을
고정한다. 분류에서 빠진 도구도, 두 분류에 든 도구도 생기지 않는다.
"""

STEP_PRODUCING_TOOLS: tuple[str, ...] = (
    "click",
    "fill",
    "select",
    "navigate",
    "hover",
    "drag",
    "upload",
    "assert_condition",
    "close_tab",
)
"""Step 을 만드는 도구. **Step 종류와 정확히 대응한다** (T163).

2026-09-09 에 `upload` 가 들어와 9종이 됐다 (사용자 보고 — 파일 업로드 녹화). 검사가
그것을 요구했다: 종류를 더하고 도구를 빼면 「사람은 만들 수 있는데 AI 는 만들 수 없는
Step 종류」가 생긴다.
"""


def build_tools(toolbox: BrowserToolbox) -> list[Any]:
    """SDK 에 넘길 도구 목록을 만든다.

    `@beta_async_tool` 를 여기서만 쓴다 — `BrowserToolbox` 가 SDK 를 모르게 두어야
    자격 증명 없이 도구 동작을 테스트할 수 있다.
    """
    from anthropic import beta_async_tool  # noqa: PLC0415 - SDK 경계를 함수 안에 둔다

    @beta_async_tool
    async def list_tabs() -> dict[str, Any]:
        """열린 탭 목록과 활성 탭을 돌려준다. 화면을 조작하지 않는다."""
        return await toolbox.list_tabs()

    @beta_async_tool
    async def observe_page(tab: int = 0) -> dict[str, Any]:
        """지정 탭의 상호작용 가능한 요소 목록과 화면 텍스트를 돌려준다.

        각 요소에 `element_ref` 가 붙는다. 다른 도구에는 **이 참조만** 넘길 수 있다.
        CSS 셀렉터를 직접 만들어 넘기지 않는다.
        """
        return await toolbox.observe_page(tab)

    @beta_async_tool
    async def click(element_ref: str) -> dict[str, Any]:
        """요소를 클릭한다. 성공하면 클릭 Step 으로 기록된다."""
        return await toolbox.click(element_ref)

    @beta_async_tool
    async def fill(element_ref: str, value: str) -> dict[str, Any]:
        """입력 필드에 값을 넣는다. 성공하면 입력 Step 으로 기록된다."""
        return await toolbox.fill(element_ref, value)

    @beta_async_tool
    async def select(element_ref: str, value: str) -> dict[str, Any]:
        """셀렉트 박스에서 값을 고른다. 성공하면 선택 Step 으로 기록된다."""
        return await toolbox.select(element_ref, value)

    @beta_async_tool
    async def navigate(url: str) -> dict[str, Any]:
        """주소로 이동한다. http·https 만 허용된다."""
        return await toolbox.navigate(url)

    @beta_async_tool
    async def hover(element_ref: str) -> dict[str, Any]:
        """요소에 마우스를 올린다. hover 로만 열리는 메뉴에 쓴다."""
        return await toolbox.hover(element_ref)

    @beta_async_tool
    async def drag(element_ref: str, drop_ref: str) -> dict[str, Any]:
        """요소를 다른 요소 위로 끌어다 놓는다. 양 끝 참조가 모두 필요하다."""
        return await toolbox.drag(element_ref, drop_ref)

    @beta_async_tool
    async def upload(element_ref: str, file_name: str) -> dict[str, Any]:
        """파일 입력에 파일을 넣는다.

        확장자를 포함한 이름을 주면 그 이름으로 기록된다 (예: ``보고서.xlsx``). 내용은
        비어 있으므로, 서버가 파일 내용을 읽는 화면에는 쓸 수 없다.
        """
        return await toolbox.upload(element_ref, file_name)

    @beta_async_tool
    async def assert_condition(
        kind: str,
        element_ref: str | None = None,
        value: str | None = None,
        match: str = "equals",
    ) -> dict[str, Any]:
        """화면 상태를 검증한다.

        `kind` 는 visible / hidden / text / url 중 하나다. `visible`·`hidden` 은
        `element_ref` 가 필요하고 `url` 은 요소를 보지 않는다.
        """
        return await toolbox.assert_condition(kind, element_ref, value, match)

    @beta_async_tool
    async def close_tab(tab: int) -> dict[str, Any]:
        """탭을 닫는다. 성공하면 탭 닫기 Step 으로 기록된다."""
        return await toolbox.close_tab(tab)

    # ─── 편집 도구 (016 US3) ─────────────────────────────────────────────

    @beta_async_tool
    async def update_step(step_id: str, field: str, value: str) -> dict[str, Any]:
        """이번에 만든 Step 의 속성 하나를 고친다.

        field 에는 label(표시 이름)·value(입력값)·timeout_ms(제한 시간) 등을 쓴다.
        다른 Step 은 고칠 수 없다 — 사람에게 말하세요.
        """
        return await toolbox.update_step(step_id, field, value)

    @beta_async_tool
    async def delete_step(step_id: str) -> dict[str, Any]:
        """이번에 만든 Step 하나를 지운다. 다른 Step 은 지울 수 없다."""
        return await toolbox.delete_step(step_id)

    @beta_async_tool
    async def move_step(step_id: str, direction: str) -> dict[str, Any]:
        """이번에 만든 Step 을 한 칸 옮긴다. direction 은 up 또는 down 이다."""
        return await toolbox.move_step(step_id, direction)

    @beta_async_tool
    async def repick_target(
        step_id: str, element_ref: str, slot: str = "target"
    ) -> dict[str, Any]:
        """이번에 만든 Step 의 대상 요소를 다시 지정한다.

        element_ref 는 observe_page 가 준 참조여야 한다. CSS 셀렉터를 직접 만들지 마라.
        slot 은 drag Step 에서만 drop_target 이 될 수 있다.
        """
        return await toolbox.repick_target(step_id, element_ref, slot)

    @beta_async_tool
    async def report_blocked(reason: str, question: str = "") -> dict[str, Any]:
        """지시를 수행할 수 없음을 알린다. 무엇이 막았는지 구체적으로 적는다.

        사람이 알려 주면 풀릴 일이면 `question` 에 물어볼 한 문장을 함께 적는다.
        """
        return await toolbox.report_blocked(reason, question or None)

    return [
        list_tabs,
        observe_page,
        click,
        fill,
        select,
        navigate,
        hover,
        drag,
        upload,
        assert_condition,
        close_tab,
        update_step,
        delete_step,
        move_step,
        repick_target,
        report_blocked,
    ]


# ─── 개발용 Claude Code 드라이버의 도구 표면 (ITB_AI_DRIVER=claude-code) ────────
# `build_tools` 와 **같은 `BrowserToolbox` 메서드**를 부른다. 도구 표면이 둘로 갈라지면
# 개발 중에 본 동작이 제품 동작과 달라지므로, 감싸는 방식만 다르고 부르는 것은 같다.

MCP_SERVER_NAME = "itb"
"""in-process MCP 서버 이름. 도구는 `mcp__itb__<이름>` 으로 노출된다."""

_REF = {"type": "string", "description": "observe_page 가 준 element_ref"}

TOOL_SCHEMAS: dict[str, tuple[str, dict[str, Any]]] = {
    "list_tabs": (
        "열린 탭 목록과 활성 탭을 돌려준다. 화면을 조작하지 않는다.",
        {"type": "object", "properties": {}, "required": []},
    ),
    "observe_page": (
        "지정 탭의 상호작용 가능한 요소 목록과 화면 텍스트를 돌려준다. "
        "각 요소에 element_ref 가 붙는다. 다른 도구에는 이 참조만 넘길 수 있다.",
        {
            "type": "object",
            "properties": {"tab": {"type": "integer", "minimum": 0, "default": 0}},
            "required": [],
        },
    ),
    "click": (
        "요소를 클릭한다. 성공하면 클릭 Step 으로 기록된다.",
        {"type": "object", "properties": {"element_ref": _REF}, "required": ["element_ref"]},
    ),
    "fill": (
        "입력 필드에 값을 넣는다. 성공하면 입력 Step 으로 기록된다.",
        {
            "type": "object",
            "properties": {"element_ref": _REF, "value": {"type": "string"}},
            "required": ["element_ref", "value"],
        },
    ),
    "select": (
        "셀렉트 박스에서 값을 고른다. 성공하면 선택 Step 으로 기록된다.",
        {
            "type": "object",
            "properties": {"element_ref": _REF, "value": {"type": "string"}},
            "required": ["element_ref", "value"],
        },
    ),
    "navigate": (
        "주소로 이동한다. http·https 만 허용된다.",
        {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    ),
    "hover": (
        "요소에 마우스를 올린다. hover 로만 열리는 메뉴에 쓴다.",
        {"type": "object", "properties": {"element_ref": _REF}, "required": ["element_ref"]},
    ),
    "upload": (
        "파일 입력에 파일을 넣는다. 확장자를 포함한 이름을 주면 그 이름으로 기록된다 "
        "(내용은 비어 있다).",
        {
            "type": "object",
            "properties": {"element_ref": _REF, "file_name": {"type": "string"}},
            "required": ["element_ref", "file_name"],
        },
    ),
    "drag": (
        "요소를 다른 요소 위로 끌어다 놓는다. 양 끝 참조가 모두 필요하다.",
        {
            "type": "object",
            "properties": {"element_ref": _REF, "drop_ref": _REF},
            "required": ["element_ref", "drop_ref"],
        },
    ),
    "assert_condition": (
        "화면 상태를 검증한다. kind 는 visible / hidden / text / url 중 하나다. "
        "visible·hidden 은 element_ref 가 필요하고 url 은 요소를 보지 않는다.",
        {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["visible", "hidden", "text", "url"]},
                "element_ref": _REF,
                "value": {"type": "string"},
                "match": {"type": "string", "default": "equals"},
            },
            "required": ["kind"],
        },
    ),
    "close_tab": (
        "탭을 닫는다. 성공하면 탭 닫기 Step 으로 기록된다.",
        {
            "type": "object",
            "properties": {"tab": {"type": "integer", "minimum": 0}},
            "required": ["tab"],
        },
    ),
    "update_step": (
        "이번에 만든 Step 의 속성 하나를 고친다. field 에는 label·value·timeout_ms 등을 "
        "쓴다. 다른 Step 은 고칠 수 없다 — 사람에게 말하라.",
        {
            "type": "object",
            "properties": {
                "step_id": {"type": "string"},
                "field": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["step_id", "field", "value"],
        },
    ),
    "delete_step": (
        "이번에 만든 Step 하나를 지운다. 다른 Step 은 지울 수 없다.",
        {
            "type": "object",
            "properties": {"step_id": {"type": "string"}},
            "required": ["step_id"],
        },
    ),
    "move_step": (
        "이번에 만든 Step 을 한 칸 옮긴다. direction 은 up 또는 down 이다.",
        {
            "type": "object",
            "properties": {
                "step_id": {"type": "string"},
                "direction": {"type": "string", "enum": ["up", "down"]},
            },
            "required": ["step_id", "direction"],
        },
    ),
    "repick_target": (
        "이번에 만든 Step 의 대상 요소를 다시 지정한다. element_ref 는 observe_page 가 "
        "준 참조여야 한다 — CSS 셀렉터를 직접 만들지 마라.",
        {
            "type": "object",
            "properties": {
                "step_id": {"type": "string"},
                "element_ref": {"type": "string"},
                "slot": {"type": "string", "enum": ["target", "drop_target"]},
            },
            "required": ["step_id", "element_ref"],
        },
    ),
    "report_blocked": (
        "지시를 수행할 수 없음을 알린다. 무엇이 막았는지 구체적으로 적는다. "
        "사람이 알려 주면 풀릴 일이면 question 에 물어볼 한 문장을 함께 적는다.",
        {
            "type": "object",
            "properties": {"reason": {"type": "string"}, "question": {"type": "string"}},
            "required": ["reason"],
        },
    ),
}
"""도구 이름 → (설명, 입력 스키마). `build_tools` 의 도구 16종과 같은 목록이다.

**이 목록이 곧 허용 목록이다.** 개발용 드라이버는 여기 없는 도구를 전부 거부한다 —
Claude Code 가 기본으로 주는 파일 읽기·쓰기·Bash 가 그 대상이다 (FR-086).
"""

QUALIFIED_TOOL_NAMES = [f"mcp__{MCP_SERVER_NAME}__{name}" for name in TOOL_SCHEMAS]
"""Claude Code 가 부르는 이름. 권한 게이트가 이 목록만 허용한다."""


def build_mcp_tools(toolbox: BrowserToolbox) -> list[Any]:
    """개발용 Claude Code 드라이버에 넘길 in-process MCP 도구 목록 (`ITB_AI_DRIVER`).

    `claude_agent_sdk` 를 여기서만 쓴다 — `BrowserToolbox` 는 어느 SDK 도 모른다.
    **선택 의존성이므로 미설치 환경에서는 `ImportError` 가 난다.** 기본 경로(Messages
    API)는 이 함수를 부르지 않으므로 영향받지 않는다.
    """
    import json  # noqa: PLC0415 - 이 경로 전용

    from claude_agent_sdk import tool  # noqa: PLC0415 - SDK 경계를 함수 안에 둔다

    handlers: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
        "list_tabs": toolbox.list_tabs,
        "observe_page": toolbox.observe_page,
        "click": toolbox.click,
        "fill": toolbox.fill,
        "select": toolbox.select,
        "navigate": toolbox.navigate,
        "hover": toolbox.hover,
        "drag": toolbox.drag,
        "upload": toolbox.upload,
        "assert_condition": toolbox.assert_condition,
        "close_tab": toolbox.close_tab,
        "report_blocked": toolbox.report_blocked,
    }

    def wrap(name: str) -> Any:
        description, schema = TOOL_SCHEMAS[name]
        handler = handlers[name]

        @tool(name, description, schema)
        async def run(args: dict[str, Any]) -> dict[str, Any]:
            # MCP 는 결과를 텍스트로 실어 보낸다. 도구가 돌려준 dict 를 그대로 JSON 으로
            # 넘긴다 — 요약하면 모델이 element_ref 를 잃는다.
            result = await handler(**args)
            payload = json.dumps(result, ensure_ascii=False)
            return {"content": [{"type": "text", "text": payload}]}

        return run

    return [wrap(name) for name in TOOL_SCHEMAS]
