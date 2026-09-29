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
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from itb.domain.assertion import (
    MAX_OBSERVED_CHARS,
    Assertion,
    AssertionKind,
    AuthoringMismatch,
    MatchMode,
)
from itb.domain.step import (
    AssertionStep,
    Author,
    ClickStep,
    CloseTabStep,
    DragStep,
    FillStep,
    HoverStep,
    NavigateStep,
    PressKey,
    PressStep,
    SelectStep,
    Step,
    UploadStep,
    press_label,
)
from itb.execution.assertion_builder import value_target_refusal
from itb.execution.element_probe import collect_by_selector, describe_element, probe_by_selector
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
from itb.execution.step_executor import ElementRect, StepExecutor, StepFailure
from itb.secrets.capture import SensitiveCapturer
from itb.secrets.scrubber import Scrubber

# ─── 막힘의 종류 (020 FR-023) ────────────────────────────────────────────────
#
# **`blocked.py` 가 아니라 여기에 있다.** 그쪽이 자연스러운 자리로 보이지만
# (`AiChoice` 옆), 임포트 방향이 그것을 막는다 — `blocked` → `agent` → `tools` 이므로
# `tools` 가 `blocked` 를 가져오면 순환이 된다.
#
# 값이 **만들어지는 곳**이 여기라는 점에서 이 자리도 맞다. `report_blocked` 가 종류를
# 정하고, `blocked.py` 는 그것을 화면으로 나르기만 한다.


class BlockedKind(StrEnum):
    """막힘이 **무엇 때문인가** (020 FR-023).

    `AiChoice` 와 다른 축이다 — 그쪽은 「사람이 무엇을 할 수 있는가」이고 이것은
    「왜 막혔는가」다.

    **도구를 늘리지 않고 `report_blocked` 의 인자로 표현한다.** 전례가 그대로 있다 —
    `question` 도 같은 판단으로 추가됐다: 「물을 것이 있다는 사실은 **막힘의 성질**이지
    별개의 동작이 아니다」(`tools.report_blocked`). 막힘의 원인 종류도 같은 성질이다.
    """

    NEEDS_INPUT = "needs_input"
    """사람이 알려 주면 풀린다 — 어느 계정인지, 어느 버튼인지, 어떤 값인지.

    **기본값이며 020 이전의 모든 막힘이 여기다.** 그래서 기존 동작이 변하지 않는다
    (FR-025).
    """

    PRODUCT_MISMATCH = "product_mismatch"
    """제품이 지시문과 다르게 동작해 진행할 수 없다 (020 US4).

    **사람에게 물을 것이 없는 막힘이다.** 지금까지 이 상황은 「요소를 찾지 못했다」로
    보고됐고, 사용자는 힌트를 주며 시간을 쓴 뒤에야 제품 문제였음을 알았다.

    이 종류에는 질문이 붙지 않는다 (FR-024). **도구 쪽에서 버린다** — 지침에만 적어
    두면 모델이 규칙을 어겼을 때 막을 것이 없고, 그러면 답할 수 없는 질문에 답변 칸이
    열린다.
    """

    BUDGET_EXHAUSTED = "budget_exhausted"
    """예산이 떨어져 멈췄다 (022 FR-001).

    **`PRODUCT_MISMATCH` 와 묶지 않는다.** 둘 다 「사람이 알려 줄 것이 없다」지만
    **이어가기의 의미가 정반대**다.

    | | `product_mismatch` | `budget_exhausted` |
    |---|---|---|
    | 이어가면 | **같은 결과** — 제품이 여전히 잘못 동작한다 | **진행된다** — 예산이 새로 생겼다 |

    한 값으로 묶으면 화면이 「이어가도 소용없다」와 「이어가면 된다」를 같은 말로 하게
    된다. 그것은 `product_mismatch` 가 만들어진 이유(사용자가 헛되이 힌트를 주며 시간을
    쓰는 것을 없앤다)를 정확히 뒤집는다.

    **판정은 제품이 센 값으로만 한다** (022 FR-003). 모델이 「예산이 없다」고 말하는 것은
    근거가 아니다 — 모델의 말이 판정에 끼어들면, 그 한마디로 사용자가 다른 화면을 본다.
    """


DEFAULT_BLOCKED_KIND = BlockedKind.NEEDS_INPUT
"""인식하지 못한 값이 떨어지는 곳.

오타가 조용히 답변 칸을 막으면 사용자는 이유를 모른 채 이어갈 방법을 잃는다. 반대
방향의 오작동(질문이 필요 없는데 칸이 열림)이 덜 해롭다.
"""


MAX_TOOL_CALLS = 40
"""도구 호출 총 상한 (FR-066).

**하드 루프 카운터가 1차 방어선이다** (research R5). 모델에게 페이스 조절을 맡기는 장치
(task budget)는 권고적이며 이것을 대체하지 못한다.
"""

MAX_DRIVER_TURNS = MAX_TOOL_CALLS * 3
"""드라이버에 넘기는 **대화 turn** 상한. `MAX_TOOL_CALLS` 와 **단위가 다르다.**

`MAX_TOOL_CALLS` 는 `record_call()` 을 지난 도구 호출만 센다. turn 은 「user 메시지 +
assistant 응답」 한 쌍이고 **도구를 부르지 않은 턴도 센다** — 모델이 말만 한 턴, 권한
콜백이 `interrupt=True` 로 되돌린 시도, 생각만 한 턴이 모두 여기 들어간다.

**두 값을 같게 두면 turn 쪽이 먼저 찬다** (2026-09-28 사용자 보고). 이전 코드는
`max_turns=MAX_TOOL_CALLS` 로 넘겼고, 그래서 1차 방어선이 끊기 전에 드라이버가 먼저
끝냈다. `MAX_TOOL_CALLS` 에 적힌 40 은 도달하지 않는 숫자가 되고, 사용자는 상한을
올려도 같은 지점에서 다시 멈추는 것을 본다 — 낭비되는 턴의 비율이 그대로이기 때문이다.

**3배는 여유이지 목표가 아니다.** 실제로 끊는 것은 언제나 1차 방어선이어야 한다. 이
값은 모델이 도구를 전혀 부르지 않고 말만 계속하는 경우를 막는 최후 안전망이며,
`_sdk_driver` 의 `max_iterations` 와 같은 자리다.
"""


class DriverTurnLimitError(Exception):
    """드라이버가 turn 상한에서 멈췄다 — **실패가 아니라 상한 도달이다.**

    `AttemptLimits.exceeded_reason` 과 **같은 뜻이고 세는 주체만 다르다.** 그래서 결말도
    같아야 한다 — 막힘(`BLOCKED`)으로 보고되고, 세션은 살아 있고, 사용자가 이어갈지
    고른다 (FR-066·FR-069).

    이 예외가 없던 동안 turn 상한은 `RuntimeError` 로 올라가 「AI 수행 중 예상하지 못한
    오류」로 표시됐다. 정상적인 상한 도달이 버그처럼 보였고, **막힘에만 열리는 이어가기
    칸이 열리지 않아** 사용자는 그때까지 만든 Step 을 두고 처음부터 다시 해야 했다.
    """


MAX_CONSECUTIVE_ELEMENT_FAILURES = 3
"""같은 요소를 연달아 실패한 횟수 상한 (FR-066).

같은 버튼을 40번 누르게 두지 않는다. 세 번 실패했으면 그 경로는 막힌 것이고, 사용자에게
넘기는 것이 맞다 (FR-069).
"""

OBSERVE_ELEMENT_LIMIT = 200
"""한 번에 보여 줄 요소 수 상한. 화면이 크면 컨텍스트를 다 먹는다."""

DISTINGUISHING_FIELDS = ("id", "placeholder", "label", "context")
"""이름이 같은 요소를 **구별하는 사실들** (2026-09-11 사용자 보고).

관찰 스크립트가 실어 보내는 값이며 이 순서대로 결과에 실린다. 넷 다 이미 문서에 있던
것이고 새로 만든 표식이 아니다 — 사용자가 지시문에 `id="text-input-example-11"` 처럼
적어 주는 것이 바로 이 값들이다.
"""

DUPLICATE_KEY_FIELDS = ("tag", "role", "name", "type")
"""이 넷이 모두 같으면 **에이전트가 구별할 수 없다** — `mark_duplicates` 의 묶음 기준."""


def mark_duplicates(elements: list[dict[str, Any]]) -> None:
    """이름만으로는 구별되지 않는 요소들에 `duplicate_with` 를 붙인다. 제자리에서 고친다.

    ## 무엇이 문제였나 (2026-09-11 사용자 보고)

    > 「ai 에게 시킬때 검색 input 이 한화면에 두개가 있을때, 명확한 위치를 선택하지 못하고
    > 다른 input 에 입력을 하는 문제가 있다」

    `observe_page` 가 주는 줄이 `tag=input · role=textbox · name=<placeholder> · type=text`
    일 때, 같은 placeholder 를 가진 검색 칸 둘은 **한 칸도 다르지 않다.** 에이전트는 목록
    순서상 앞의 것을 고를 수밖에 없고, 그것이 사용자가 본 「다른 input 에 입력」이다.

    시스템 프롬프트는 「추측으로 다른 요소를 누르지 마세요」라고 적고 있었지만, 그 규칙은
    **지킬 수 없는 규칙**이었다 — 에이전트는 자기가 추측하고 있다는 사실조차 알 수 없었다.

    ## 왜 여기서 대신 고르지 않는가

    제품이 하나를 골라 주면 그것도 추측이다. 004 가 `.first` 폴백을 지운 근거와 같다 —
    자동으로 하나를 고르면 **틀렸을 때 조용히 통과한다**. 그래서 이 함수는 고르지 않고
    「둘이 구별되지 않는다」는 사실만 싣는다. 고르는 것은 지시문을 읽는 쪽의 일이고,
    지시문이 말해 주지 않으면 물어야 한다 (`SYSTEM_PROMPT` · FR-069).

    ## 보이지 않는 요소도 센다

    화면에 없는 것과 이름이 겹쳐도 사람은 그것을 구별로 쓰지 않는다. 반대로 `visible` 로
    걸러 세면, hover 로 열리는 메뉴 안의 같은 이름 항목이 묶음에서 빠져 「하나뿐」으로
    보인다 — 관찰이 보이지 않는 요소를 목록에서 빼지 않는 것과 같은 판단이다.
    """
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in elements:
        groups.setdefault(tuple(row.get(f) for f in DUPLICATE_KEY_FIELDS), []).append(row)
    for members in groups.values():
        if len(members) < 2:
            continue
        refs = [str(m["element_ref"]) for m in members]
        for row in members:
            # 자기 자신은 빼고 적는다 — 「나 말고 이것들이 나와 같아 보인다」가 읽을 말이다.
            row["duplicate_with"] = [r for r in refs if r != row["element_ref"]]


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
    """**이번 시도**의 호출 수. 예산을 새로 줄 때 0 이 된다."""

    total_calls: int = 0
    """이 지시에 쓴 **누적** 호출 수 (022 FR-017·FR-018). 예산을 새로 줘도 남는다.

    **`calls` 와 같은 자리에서 센다.** `record_call()` 이 도구 호출의 유일한 통과 지점
    이므로, 두 계수를 여기 두면 어긋날 수 없다 — 세는 주체가 둘이면 어긋난다는 판단은
    이 저장소에 이미 두 번 적혀 있다 (`AuthoringAgent._count`·`MAX_INSTRUCTION_CHARS`).
    """

    steps_at_attempt_start: int | None = None
    """이번 시도를 시작할 때의 Step 수 (022 FR-020).

    **`None` 은 「진전이 없다」가 아니라 「비교할 것이 아직 없다」**이다. 첫 시도에는
    직전 값이 없으므로 진전을 판정하지 않는다 — 둘을 묶으면 첫 시도에서 상한에 닿은
    사용자가 근거 없는 경고를 본다.

    `AttemptLimits` 는 Step 을 세지 않는다. 아는 쪽(`reset_attempt` 의 호출부)이 넘긴다.
    """
    failures_by_element: dict[str, int] = field(default_factory=dict)
    last_failed_element: str | None = None
    exceeded_reason: str | None = None
    """상한에 도달한 사유. None 이 아니면 루프를 끊어야 한다."""

    exceeded_is_budget: bool = False
    """멈춘 이유가 **예산 소진인가** (022 FR-001·FR-002).

    `exceeded_reason` 하나로는 갈라낼 수 없다 — 총 호출 상한과 같은 요소 연속 실패가
    **같은 필드**를 쓰기 때문이다. 문구를 뒤져 판정하면 문구를 고치는 날 조용히 깨진다.

    연속 실패는 **예산 소진이 아니다.** 그 경로가 막힌 것이므로 사람이 알려 줄 것이
    있고, 이어가기의 의미도 다르다 (FR-069).
    """

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
            # 022 FR-001 — 예산이 떨어진 것이지 길을 잃은 것이 아니다.
            self.exceeded_is_budget = True
            return False
        self.calls += 1
        self.total_calls += 1
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
            # **`exceeded_is_budget` 을 세우지 않는다** (022 FR-002). 예산은 남아 있고,
            # 그 경로가 막힌 것이다 — 사람이 알려 주면 풀릴 수 있다.
            self.exceeded_reason = (
                f"같은 요소에 {count}회 연속 실패해 중단했습니다: {element}. "
                "그때까지 성공한 동작은 Step 으로 남아 있습니다."
            )

    def record_mismatch(self, element: str) -> None:
        """검증이 기대와 달랐다 — **성공도 실패도 아니다** (020 FR-009).

        연속 실패 계수와 `last_failed_element` 를 **둘 다 건드리지 않는다.** 어긋남은
        상한에 대해 중립이어야 한다.

        ## 왜 아무것도 부르지 않는 것으로는 부족한가

        그러면 앞선 실패의 `last_failed_element` 가 남아, 그 다음 실패가 **연속**으로
        세어진다. 명시적 메서드를 두면 「어긋남은 세지 않는다」가 코드에 적힌다.

        ## 왜 `record_success` 를 부르지 않는가

        그것은 연속 실패를 **초기화**한다. 어긋남이 다른 요소의 실패 흐름을 지우면
        상한이 약해진다.

        ## 총 호출 상한은 그대로 걸린다

        `assert_condition` 진입 시 `record_call()` 이 먼저 돌기 때문이다. 모델이 같은
        검증을 무한히 시도해도 총 상한에서 멈춘다 (FR-009 후반부).

        `element` 를 받지만 쓰지 않는다 — 호출부가 무엇에 대한 어긋남인지 적게 하려는
        것이고, 그 기록이 필요해지면 여기가 받을 자리다.
        """

    def record_success(self, element: str | None = None) -> None:
        """성공하면 연속 실패 기록을 지운다."""
        if element is not None:
            self.failures_by_element.pop(element, None)
        self.last_failed_element = None

    def reset_attempt(self, step_count: int | None = None) -> None:
        """**이번 시도의 예산만** 되돌린다 (FR-072·FR-073 · 022 FR-008).

        앞선 시도가 쓴 호출까지 상한에 포함하면 사용자가 "다시" 를 누르는 순간 이미
        상한에 닿아 있을 수 있다.

        **`total_calls` 는 지우지 않는다** (022 FR-018). 하는 일이 「전부 되돌린다」에서
        「이번 시도의 예산만 되돌린다」로 좁아졌고, 이름이 그 사실을 말한다 — 예전 이름
        `reset` 은 누적까지 지우는 것으로 읽혔다.

        `step_count` 를 받으면 진전 판정의 기준점으로 삼는다. 넘기지 않으면 기준점이
        갱신되지 않으므로, **이어가기 경로는 반드시 넘긴다.**
        """
        self.calls = 0
        self.failures_by_element.clear()
        self.last_failed_element = None
        self.exceeded_reason = None
        self.exceeded_is_budget = False
        if step_count is not None:
            self.steps_at_attempt_start = step_count


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

    unique: bool = True
    """`css` 가 **이 요소 하나만** 가리키는가 (2026-09-11 사용자 보고).

    도구는 이 `css` 로 요소를 다시 찾는다. 둘 이상을 가리키면 문서 순서상 첫 번째가
    잡히고, 에이전트가 무엇을 골랐든 조작은 다른 요소에 간다. 그래서 거짓이면
    `_act_on_element` 가 **거절한다** — 조용히 다른 요소를 조작하지 않는다.

    기본값이 참인 것은 낡은 주입 스크립트가 이 사실을 싣지 않는 경우뿐이며, 그때는
    지금까지와 같이 동작한다.
    """


StepSink = Callable[[Step], Awaitable[None]]
"""성공한 동작을 Step 으로 확정하는 통로. `compiler` 가 구현한다."""

ProgressSink = Callable[[str], Awaitable[None]]
"""`ai_progress` 발행 통로 (FR-060)."""


@dataclass(frozen=True, slots=True)
class FocusNotice:
    """AI 가 방금 다룬 요소의 **자리** (024 FR-001 · data-model §6).

    미러 위에 테두리를 그릴 근거다. 좌표계는 미러 프레임과 같다 — 주 프레임 뷰포트 기준
    CSS 픽셀.
    """

    tab: int
    """어느 탭의 자리인가 (FR-004). 없으면 화면이 어느 그림 위에 그릴지 판정할 수 없다."""

    rect: ElementRect
    """**필수다.** 자리를 모르면 이 알림 자체를 만들지 않는다 (FR-010)."""

    status: str
    """`"done"` 또는 `"failed"` (FR-008). 「수행 중」은 없다 — 자리는 요소가 확정된
    뒤에야 알 수 있고, 그것을 표시하려면 추측한 자리를 써야 한다 (024 research R2)."""

    label: str
    """Step 의 이름표와 **같은 값** (FR-009). 화면이 진행 문구와 짝지어 읽는다."""


FocusSink = Callable[[FocusNotice], Awaitable[None]]
"""`ai_focus` 발행 통로 (024 FR-001).

## 왜 `ProgressSink` 와 나누는가

`_announce` 는 **자리를 모르는 자리에서도 불린다** — 화면 살펴보기, Step 편집, 막힘
신고. 한 통로로 묶으면 그 호출마다 「자리 없음」을 넘기게 되고, 「자리를 모른다」와
「자리가 없다」가 같은 모양이 된다.

두 알림은 성질도 다르다. 진행 문구는 **쌓이는 이력**이고 자리는 **지금 하나뿐인
상태**다 — 한 이벤트로 묶으면 화면이 매 건마다 「지난 표시를 지울 것인가」를 판단하게
된다 (FR-005 · 024 research R4).
"""


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
    on_focus: FocusSink | None = None
    """자리 알림 통로 (024 FR-001). 없으면 알리지 않고 나머지는 지금과 같이 동작한다.

    **재생에는 이 통로가 없다.** 발행 지점이 이 모듈 안에만 있고, 이 모듈은 AI 작성
    전용이다 — 원칙 II 경계가 규칙이 아니라 구조로 지켜지는 자리다 (024 research R5).
    """
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

    current_index: Callable[[], int] | None = None
    """지금 실행 위치를 읽는 통로 (2026-09-11 사용자 보고).

    편집 연산(`step_edits`)은 실행 위치를 받아 **그 값을 고쳐 돌려준다** — 앞에서 지운
    Step 만큼 위치를 당기는 식이다. 그 결과가 세션에 그대로 반영되므로(`_apply_rerecord_edit`),
    여기서 넘기는 값이 곧 세션의 다음 실행 위치가 된다.

    없으면 0 을 넘긴다. 그것이 실측에서 사고를 냈다 — AI 가 Step 대상을 다시 지목하자
    실행 위치가 23 에서 0 으로 돌아갔고, 화면은 「Step 01 에서 중지」로 바뀌었다.
    그 상태로 「계속하기」를 누르면 이미 지나온 로그인부터 다시 실행한다 (SC-007 위반).
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

    blocked_kind: BlockedKind = BlockedKind.NEEDS_INPUT
    """막힘이 **무엇 때문인가** (020 FR-023).

    사유·질문과 또 다른 축이다 — 사유는 「왜 못 했는가」, 질문은 「무엇을 알려 주면
    되는가」, 이것은 「사람이 알려 줄 수 있는 종류의 문제인가」다.
    """

    scrubber_source: Callable[[], Scrubber] | None = None
    """지금까지 복호화된 민감 값으로 스크러버를 만들어 주는 것 (020 FR-015).

    **값이 아니라 함수다.** 작성 도중 새 민감 변수가 해석될 수 있으므로, 값으로 들고
    있으면 나중에 복호화된 값이 마스킹되지 않는다 (`Runner._scrubber` 와 같은 판단).

    어긋남 기록(`AuthoringMismatch.observed`)은 화면에서 읽은 텍스트를 **디스크에
    남긴다.** 진행 알림과 달리 흘러가 버리지 않으므로, 여기가 거르는 유일한 자리다.

    없으면 거르지 않는다 — 016 이전 경로와 검증이 이 통로 없이도 돌아야 한다.
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
                # 관찰 스크립트가 싣지 않으면(낡은 주입) 지금까지와 같이 동작한다.
                unique=bool(entry.get("unique", True)),
            )
            self.refs[ref] = observed
            row: dict[str, Any] = {
                "element_ref": ref,
                "tag": observed.tag,
                "role": observed.role,
                "name": observed.name,
                "visible": observed.visible,
                "disabled": observed.disabled,
                "type": entry.get("type"),
            }
            # 이름이 같은 요소를 구별하는 사실들 (2026-09-11 사용자 보고 · `mark_duplicates`).
            # **없는 것은 싣지 않는다** — `null` 칸이 120줄 쌓이면 읽을 것이 늘어날 뿐이다.
            for key in DISTINGUISHING_FIELDS:
                value = entry.get(key)
                if isinstance(value, str) and value:
                    row[key] = value
            # **조작할 수 없는 요소는 미리 말한다** (2026-09-11 실측).
            #
            # 경로가 이 요소 하나를 가리키지 못하면 `_act_on_element` 가 거절한다. 그
            # 사실을 관찰 단계에서 알려 주면 에이전트가 헛되이 시도하고 실패 예산을
            # 깎는 대신 다른 요소를 찾거나 사람에게 물을 수 있다.
            #
            # **참일 때는 싣지 않는다** — 대부분 참이므로 120줄에 같은 칸이 붙으면 읽을
            # 것만 는다 (`DISTINGUISHING_FIELDS` 와 같은 판단).
            if not observed.unique:
                row["unique"] = False
            elements.append(row)
        mark_duplicates(elements)
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

    async def press(self, element_ref: str, key: str) -> dict[str, Any]:
        """대상 요소에 키를 누른다 (023 · `press` Step).

        ## 이 도구가 없어서 작성이 중단됐다

        「태그를 입력한 뒤 Enter 또는 Space를 눌러 추가하세요」 같은 칸에서는 키가 확정
        동작이다. 값을 넣는 것만으로는 태그가 만들어지지 않고, 태그가 없으면 저장이
        거절되고, 저장이 안 되면 그 뒤의 시나리오가 통째로 성립하지 않는다.

        우회로도 없다 — 그런 칸 옆에는 「추가」 버튼이 없다.

        ## 범위 밖 키는 지원 목록과 함께 거절한다

        「지원하지 않습니다」로 끝내면 모델은 **다른 키를 또 시도한다.** 도구 호출 횟수를
        소모하면서 같은 벽에 부딪히므로, 거절 문구는 **다음에 무엇을 할 수 있는지**를
        담아야 한다.
        """
        try:
            press_key = PressKey(key.strip())
        except ValueError:
            supported = " / ".join(k.value for k in PressKey)
            return {
                "error": (
                    f"지원하지 않는 키입니다: {key!r}. "
                    f"누를 수 있는 키는 {supported} 뿐입니다. "
                    "글자를 입력하려면 fill 을 쓰세요."
                )
            }
        return await self._act_on_element(
            element_ref,
            lambda step_id, target, tab: PressStep(
                id=step_id,
                # **녹화 경로와 같은 함수를 쓴다** (023 FR-059). 각자 만들면 같은 동작이
                # 목록에서 다르게 불리고, 사용자는 두 Step 이 다른 일을 한다고 읽는다.
                label=press_label(press_key),
                author=self.author,
                tab=tab,
                target=target,
                key=press_key,
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
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        """검증 Step 을 만들고 **즉시 확인한다** (FR-013a 의 4종만).

        ## 확인 결과가 Step 의 운명을 정하지 않는다 (020 FR-005)

        001 은 「성공한 동작만 Step 으로 남긴다」(FR-061)를 검증에도 적용했다. 동작
        Step 에는 맞지만 **검증에는 정반대다** — 실패하는 검증이야말로 결함을 잡는
        테스트이며, 그것을 버리면 저장된 정의는 작성 시점 제품 동작의 사본이 된다.
        사본은 원본과 같으므로 처음 돌리면 반드시 통과하고, 그 통과는 정보를 담고
        있지 않다.

        그래서 검증은 `keep_on_failure` 로 실행한다. 어긋나도 Step 은 남고, 어긋났다는
        사실이 `mismatch` 에 함께 적힌다.

        ## 어긋남과 대상 없음은 다르다 (FR-007)

        아래 참조 해석 단계는 **그대로 둔다.** 참조를 찾지 못하거나 식별 정보를 모으지
        못한 것은 「무엇을 관찰했는지 적을 수 없는 상태」이고, 그것을 어긋남으로
        기록하면 관찰값이 빈 거짓 기록이 만들어진다.

        가르는 기준은 **언제 실패했는가**가 아니라 **무엇이 실패했는가**다 —
        참조 해석 실패는 대상 없음, 검증 판정 실패는 어긋남이다.
        """
        if not self.limits.record_call():
            return dict(STOP_NOTICE)
        try:
            assertion_kind = AssertionKind(kind)
            match_mode = MatchMode(match)
        except ValueError:
            kinds = " / ".join(k.value for k in AssertionKind)
            matches = " / ".join(m.value for m in MatchMode)
            return {
                "error": (
                    f"지원하지 않는 검증 종류 또는 비교 방식입니다: {kind} / {match}. "
                    f"종류는 {kinds}, 비교는 {matches} 중 하나여야 합니다."
                )
            }

        tab = self.session.active_tab_index
        target = None
        if element_ref is not None:
            observed = self.refs.get(element_ref)
            if observed is None:
                return {"error": f"요소 참조를 찾을 수 없습니다: {element_ref}."}
            tab = self._tab_of_ref(element_ref)
            probed = await probe_by_selector(
                self._tab(tab).page, observed.css, self.test_id_attribute
            )
            if probed is None:
                return {"error": f"검증 대상의 식별 정보를 수집하지 못했습니다: {element_ref}"}
            target = probed.locator

            # 023 — **대상 성질 판정을 화면 폼 경로와 같은 함수로 한다.**
            #
            # 이 경로는 `build_assertion` 을 지나지 않는다. 그래서 021 의
            # `stateless_target_warning` 이 여기 닿지 않고 있다(research R3) — 같은
            # 구조로 만들면 AI 가 만드는 검증만 새 규칙 밖에 남는다.
            refusal = value_target_refusal(assertion_kind, probed, value)
            if refusal is not None:
                return {"error": refusal}

        try:
            assertion = Assertion(
                kind=assertion_kind, target=target, match=match_mode, value=value
            )
        except ValueError as exc:
            return {"error": f"검증 조건이 올바르지 않습니다: {exc}"}

        # 제한 시간을 생략하면 Step 이 자기 기본값을 쓴다. **부정 검증에서 이 값은
        # 상한이 아니라 관찰 기간이다** (021 FR-003a) — 그 동안 조건이 유지되는지
        # 지켜보므로 항상 소모된다. 짧게 주는 것이 합리적인 경우가 많다.
        extra: dict[str, Any] = {} if timeout_ms is None else {"timeout_ms": timeout_ms}
        try:
            step = AssertionStep(
                id=self.allocate_step_id(),
                label=self._assertion_label(assertion),
                author=self.author,
                tab=tab,
                assertion=assertion,
                **extra,
            )
        except ValueError as exc:
            return {"error": f"검증 Step 을 만들 수 없습니다: {exc}"}
        return await self._execute(
            step, element=element_ref or f"assert:{kind}", keep_on_failure=True
        )

    async def report_blocked(
        self, reason: str, question: str | None = None, kind: str | None = None
    ) -> dict[str, Any]:
        """수행 불가 선언 (FR-069). 루프를 끊고 사용자 선택으로 넘긴다.

        `question` 은 **사람에게 물을 한 문장**이다 (2026-09-10 사용자 결정). 새 도구를
        만들지 않고 여기에 붙이는 이유는 도구 표면이 계약이기 때문이다 (`TOOL_NAMES`) —
        늘리면 Step 종류와의 1:1 이 깨진다. 물을 것이 있다는 사실은 **막힘의 성질**이지
        별개의 동작이 아니다.

        `kind` 도 **같은 판단으로** 붙는다 (020 FR-023). 막힘의 원인 종류 역시 막힘의
        성질이며, 별개의 도구가 아니다.

        ## 질문은 종류가 정한다 (FR-024)

        `product_mismatch` 이면 `question` 을 **버린다.** 제품이 지시문과 다르게 동작해
        막힌 것에는 사람이 알려 줄 것이 없고, 그런데도 답변 칸이 열리면 사용자는 답할
        수 없는 질문 앞에서 시간을 쓴다.

        **지침이 아니라 여기서 버린다.** 지침에만 적어 두면 모델이 규칙을 어겼을 때
        막을 것이 없다.

        ## 모르는 값은 기본으로 떨어진다

        오타가 조용히 답변 칸을 막으면 사용자는 이유를 모른 채 이어갈 방법을 잃는다.
        반대 방향의 오작동(질문이 필요 없는데 칸이 열림)이 덜 해롭다.
        """
        self.limits.record_call()
        # **예외를 던지지 않는다.** SDK 가 도구 예외를 잡아 모델에게 돌려주므로 예외로는
        # 루프를 끊을 수 없다. 상태로 남기고 우리가 소유한 루프 본문이 끊는다.
        self.blocked_reason = reason
        try:
            self.blocked_kind = BlockedKind(str(kind or "").strip())
        except ValueError:
            self.blocked_kind = DEFAULT_BLOCKED_KIND
        if self.blocked_kind is BlockedKind.PRODUCT_MISMATCH:
            self.blocked_question = None
        else:
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
        """편집 연산에 넘길 실행 위치 (2026-09-11 사용자 보고).

        **세션이 소유한 값을 읽어 온다.** 이전 판은 여기서 0 을 넘기며 「편집 연산이 이
        값으로 하는 일은 경고뿐」이라고 적었는데, 그것이 틀렸다 — `step_edits` 는 경고만
        내는 것이 아니라 **위치 자체를 계산해 돌려주고**, 그 값이 `_apply_rerecord_edit`
        을 지나 세션의 실행 위치가 된다.

        그래서 AI 가 Step 하나를 고치면 실행 위치가 0 으로 되돌아갔다. 화면은 「Step 01
        에서 중지」로 바뀌고, 「계속하기」는 이미 지나온 로그인부터 다시 실행한다.

        통로가 없으면 0 이다 — 편집 도구를 쓰지 않는 세션에서는 이 값이 쓰이지 않는다.
        """
        return self.current_index() if self.current_index is not None else 0

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

    async def _focus(
        self, rect: ElementRect | None, tab: int, status: str, label: str
    ) -> None:
        """방금 다룬 요소의 자리를 알린다 (024 FR-001·FR-006·FR-010).

        **자리를 모르면 아무것도 보내지 않는다.** 「자리 없음」을 나타내는 값을 두지
        않는다 — 그것을 보내면 화면이 그 알림을 받고 「지난 표시를 지울 것인가」를
        판단해야 하고, 그 판단은 표시의 수명이 이미 하고 있다 (024 research R6).

        요소를 못 찾은 실패, 가리키는 자리가 하나로 좁혀지지 않아 거절한 조작이 그
        경우다. 어느 것인지 **제품도 모르는** 상태에서 하나를 골라 그리면 거짓말이 된다.

        **알리는 데 실패해도 도구를 멈추지 않는다** — `_announce` 와 같은 규칙이다.
        표시는 곁가지이고, 그것 때문에 작성이 끊기면 안 된다.
        """
        if self.on_focus is None or rect is None:
            return
        with contextlib.suppress(Exception):
            await self.on_focus(
                FocusNotice(tab=tab, rect=rect, status=status, label=label)
            )

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

        # **가리키는 것이 하나가 아니면 조작하지 않는다** (2026-09-11 사용자 보고).
        #
        # 아래 `collect_by_selector` 는 이 `css` 로 요소를 **다시 찾는다.** 경로가 둘
        # 이상을 가리키면 `querySelector` 가 문서 순서상 첫 번째를 주고, 에이전트가 무엇을
        # 지목했든 조작은 다른 요소에 간다. 실측에서 목록의 이름 검색 칸을 정확히 지목한
        # 입력이 헤더의 전역 검색 칸에 들어갔고, 화면은 아무 일도 없는 것처럼 보였다.
        #
        # **여기서 대신 고르지 않는다.** 하나를 골라 주면 그것도 추측이고, 틀렸을 때
        # 조용히 통과한다 (004 가 `.first` 폴백을 지운 근거 · `mark_duplicates` 머리말).
        # 에이전트에게 돌려주고 사람에게 묻게 한다 (FR-069).
        if not observed.unique:
            self.limits.record_failure(element_ref)
            return {
                "error": (
                    f"이 요소를 가리키는 경로가 화면에서 유일하지 않습니다: "
                    f"{observed.name or element_ref}. 같은 자리를 가리키는 요소가 둘 "
                    "이상이어서 어느 것을 조작할지 제품이 정할 수 없습니다. "
                    "다른 요소로 같은 일을 할 수 있는지 observe_page 로 확인하고, "
                    "없으면 report_blocked 로 사람에게 물으세요."
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

    async def _execute(
        self, step: Step, element: str, *, keep_on_failure: bool = False
    ) -> dict[str, Any]:
        """Step 을 실행하고 기록한다. **실패 처리는 두 갈래다.**

        실행에 쓰는 것은 재실행과 **같은 `StepExecutor`** 다. 그래서 "AI 로 만든 테스트가
        재실행에서 통과한다" 가 별도의 보장이 아니라 같은 코드를 지난 결과가 된다.

        ## `keep_on_failure` — 동작 Step 과 검증 Step 은 실패의 뜻이 다르다 (020)

        | | 꺼짐 (기본 · 동작 Step 8종) | 켜짐 (`assert_condition` 하나) |
        |---|---|---|
        | 실패의 뜻 | **진행 불가** | **제품 결함 후보** |
        | Step 기록 | 안 한다 (001 FR-061) | **한다** (020 FR-005) |
        | 연속 실패 계수 | +1 | 건드리지 않는다 (FR-009) |
        | 반환 | `{"error": ...}` | `{"ok": true, "assertion_failed": true, ...}` |

        **왜 인자 하나로 가르는가**: `assert_condition` 이 이 함수를 쓰지 않고 자기
        경로를 가지면 실행·진행 알림·새 탭 감지·상한 기록이 복제된다. 복제된 순간 두
        경로가 조용히 갈라지고, 갈라진 것을 검사가 잡지 못한다 (research R3).

        **도구 표면은 그대로다.** `TOOL_NAMES` 16종, `STEP_PRODUCING_TOOLS` 9종,
        Step 종류와의 1:1 대응이 변하지 않는다 — 바뀌는 것은 도구 하나의 실패 처리다.
        """
        tabs_before = len(self.session.tabs)
        # **하기 전에 알린다.** 요소를 기다리는 동안 화면이 조용하면 사용자는 멈춘
        # 것과 기다리는 것을 구별할 수 없다 (`_announce` 머리말).
        #
        # **자리는 여기서 알리지 못한다** (024 research R2). 요소가 아직 확정되지 않았고,
        # 확정 전의 자리는 추측이다. 기다리는 동안의 공백은 이 문구가 메운다 — 문구는
        # 기다림을 말하고, 테두리는 결과의 자리를 말한다.
        await self._announce(f"{step.label} — 수행 중")
        try:
            record = await self.executor.execute(step)
        except StepFailure as exc:
            if keep_on_failure:
                return await self._keep_mismatch(step, element, str(exc))
            self.limits.record_failure(element)
            # **요소는 찾았는데 동작이 안 된 경우에만 자리가 있다** (024 US2). 요소를
            # 못 찾은 실패에는 `rect` 가 없고, 그러면 `_focus` 가 조용히 지나간다.
            await self._focus(exc.rect, step.tab, "failed", step.label)
            await self._announce(f"{step.label} — 실패: {exc}")
            return {"error": str(exc)}
        except TabNotFoundError as exc:
            # **탭이 없는 것은 어긋남이 아니다.** 검증이 기대와 달랐다는 것과, 검증할
            # 화면 자체가 사라졌다는 것은 다른 사실이다. 후자를 어긋남으로 기록하면
            # 「그때 화면이 이랬다」가 거짓이 된다 (FR-007 과 같은 경계).
            self.limits.record_failure(element)
            await self._announce(f"{step.label} — 실패: {exc}")
            return {"error": str(exc)}

        self.limits.record_success(element)
        await self.on_step(step)
        await self._focus(record.rect, step.tab, "done", step.label)
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

    async def _keep_mismatch(
        self, step: Step, element: str, failure: str
    ) -> dict[str, Any]:
        """검증이 기대와 달랐다 — **Step 을 남기고 그 사실을 함께 적는다** (020 FR-005).

        ## 무엇을 관찰값으로 적는가

        실행기가 만든 실패 설명을 그대로 쓴다. 새 관찰 로직을 만들면 **같은 상황을 두
        곳이 서로 다르게 설명**하게 되고, 화면의 문구와 실행 결과의 문구가 갈린다
        (research R2).

        **거르는 것은 여기 한 번뿐이다** (FR-015). 이 문장은 디스크에 남으므로 진행
        알림과 달리 흘러가지 않는다. 화면이 다시 거르지 않는다 — 거르는 곳이 둘이면
        어느 쪽이 기준인지 말할 수 없다.

        ## 모델에게 무엇을 돌려주는가

        `ok` 와 `assertion_failed` 를 **함께** 싣는다. 도구 호출로서는 성공했고(Step 이
        기록됐다), 검증 결과로서는 어긋났다 — 두 축을 한 값으로 뭉치면 모델이
        「실패했으니 다시」로 읽는다. 이 기능 전체가 그 오독을 없애는 것이다 (FR-010).
        """
        scrubber = self.scrubber_source() if self.scrubber_source is not None else None
        observed = scrubber.scrub(failure) if scrubber is not None else failure
        truncated = len(observed) > MAX_OBSERVED_CHARS
        recorded = step.model_copy(
            update={
                "mismatch": AuthoringMismatch(
                    observed=observed[:MAX_OBSERVED_CHARS],
                    truncated=truncated,
                    recorded_at=datetime.now(UTC),
                )
            }
        )

        # **성공도 실패도 아니다.** 연속 실패 상한에 대해 중립이어야 기대값 고수가
        # 처벌받지 않는다 (FR-009). 총 호출 상한은 진입 시 이미 세었다.
        self.limits.record_mismatch(element)
        await self.on_step(recorded)
        await self._announce(f"{step.label} — 기대와 다름: {observed}")
        return {
            "ok": True,
            "assertion_failed": True,
            "step": step.label,
            "observed": observed[:MAX_OBSERVED_CHARS],
            "note": (
                "검증이 기대와 다릅니다. 값을 바꾸어 다시 시도하지 마세요 — "
                "이 Step 은 결함 후보로 이미 기록되었습니다. "
                "남은 지시를 계속 수행하세요."
            ),
        }


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
        "press",
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
    "press",
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
    async def press(element_ref: str, key: str) -> dict[str, Any]:
        """대상 요소에 키를 누른다.

        **입력 후 키로 확정하는 칸에 쓴다.** 「태그를 입력한 뒤 Enter 또는 Space를 눌러
        추가하세요」 같은 칸은 `fill` 만으로는 아무 일도 일어나지 않는다 — 값을 넣은 뒤
        이 도구로 확정해야 태그가 만들어진다.

        `key` 는 Enter / Space / Tab / Escape 중 하나다. 글자를 입력하려면 `fill` 을 쓴다.

        `element_ref` 가 **필요하다** — 포커스된 곳이 아니라 그 요소에 키를 보낸다.
        """
        return await toolbox.press(element_ref, key)

    @beta_async_tool
    async def assert_condition(
        kind: str,
        element_ref: str | None = None,
        value: str | None = None,
        match: str = "equals",
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        """화면 상태를 검증한다.

        `kind` 는 visible / hidden / enabled / disabled / text / url / value 중 하나다.
        `visible`·`hidden`·`enabled`·`disabled`·`value` 는 `element_ref` 가 필요하고
        `url` 은 요소를 보지 않는다.

        **입력 칸·선택 목록에 담긴 값을 볼 때는 `text` 가 아니라 `value` 다.** 입력 칸을
        `text` 로 보면 칸이 가득 차 있어도 언제나 빈 문자열이 관찰된다.

        `match` 는 equals / contains / not_equals / not_contains 중 하나이며 **텍스트와
        주소 검증에만** 쓴다. `not_` 로 시작하는 비교에서 `timeout_ms` 는 상한이 아니라
        **그 동안 조건이 유지되는지 지켜보는 기간**이다.

        **기대와 달라도 Step 으로 기록된다.** 그때는 결함 후보로 표시되며, 값을 바꾸거나
        조건을 뒤집어 다시 시도하면 안 된다.
        """
        return await toolbox.assert_condition(kind, element_ref, value, match, timeout_ms)

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
    async def report_blocked(
        reason: str, question: str = "", kind: str = "needs_input"
    ) -> dict[str, Any]:
        """지시를 수행할 수 없음을 알린다. 무엇이 막았는지 구체적으로 적는다.

        사람이 알려 주면 풀릴 일이면 `question` 에 물어볼 한 문장을 함께 적고
        `kind` 는 `needs_input` 으로 둔다.

        **제품이 지시문과 다르게 동작해서 막힌 것이면** `kind` 에 `product_mismatch` 를
        적는다. 그때는 사람에게 물을 것이 없으므로 `question` 은 무시된다.
        """
        return await toolbox.report_blocked(reason, question or None, kind)

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
        press,
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
    "press": (
        "대상 요소에 키를 누른다. **입력 후 키로 확정하는 칸에 쓴다** — "
        "「태그를 입력한 뒤 Enter 또는 Space를 눌러 추가하세요」 같은 칸은 fill 만으로는 "
        "아무 일도 일어나지 않는다. key 는 Enter / Space / Tab / Escape 중 하나이며, "
        "글자를 입력하려면 fill 을 쓴다.",
        {
            "type": "object",
            "properties": {
                "element_ref": _REF,
                "key": {"type": "string", "enum": [k.value for k in PressKey]},
            },
            "required": ["element_ref", "key"],
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
        "화면 상태를 검증한다. kind 는 visible / hidden / enabled / disabled / text / url "
        "중 하나다. visible·hidden·enabled·disabled 는 element_ref 가 필요하고 url 은 "
        "요소를 보지 않는다. enabled·disabled 는 value 를 쓰지 않는다. "
        "match 는 텍스트·주소 검증에만 쓰며 not_equals·not_contains 로 부정할 수 있다. "
        "부정 비교에서 timeout_ms 는 그 동안 조건이 유지되는지 지켜보는 기간이다. "
        "기대와 달라도 Step 으로 기록되며 결함 후보로 표시된다 — "
        "값을 바꾸거나 조건을 뒤집어 다시 시도하지 마라.",
        {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": [k.value for k in AssertionKind],
                },
                "element_ref": _REF,
                "value": {"type": "string"},
                "match": {
                    "type": "string",
                    "enum": [m.value for m in MatchMode],
                    "default": "equals",
                },
                "timeout_ms": {"type": "integer", "minimum": 1, "maximum": 60000},
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
        "사람이 알려 주면 풀릴 일이면 question 에 물어볼 한 문장을 함께 적는다. "
        "제품이 지시문과 다르게 동작해서 막힌 것이면 kind 에 product_mismatch 를 "
        "적는다 — 그때는 사람에게 물을 것이 없다.",
        {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "question": {"type": "string"},
                "kind": {
                    "type": "string",
                    "enum": ["needs_input", "product_mismatch"],
                    "default": "needs_input",
                },
            },
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

    # 도구 이름 = `BrowserToolbox` 메서드 이름이다. 목록을 여기 한 번 더 적으면
    # `TOOL_SCHEMAS` 가 늘어날 때 한쪽만 갱신되어 `KeyError` 가 난다 — 016 의
    # `STEP_EDITING_TOOLS` 넷이 실제로 그렇게 빠졌다. 이름으로 찾아 쓴다.
    handlers: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
        name: getattr(toolbox, name) for name in TOOL_SCHEMAS
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
