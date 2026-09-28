"""실행 결과. `.runs/<테스트ID>/result.json` 에 저장한다. 테스트당 최근 1건만 보관한다."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from itb.domain.error import ErrorCode


class Outcome(StrEnum):
    """실행이 어떻게 끝났는가 (005 FR-131·FR-137).

    **네 값이 필요한 이유는 두 값이 서로 다른 것을 뭉갰기 때문이다.** 사용자가 누른 중지가
    `FAIL` 로 기록되어 사고처럼 보이고(U-03), 실패 Step 을 건너뛴 실행이 통과처럼 보였다
    (U-05).

    판정 우선순위는 `decide_outcome()` 이 갖는다. 여기서 값을 늘리기만 하고 판정을 여러
    곳에 흩으면 화면과 저장된 결과가 다시 어긋난다.
    """

    PASS = "pass"
    FAIL = "fail"

    STOPPED = "stopped"
    """사용자가 중지를 요청해 끝났다. **실패 집계에 넣지 않는다** (FR-131).

    세션 유실은 여기가 아니라 `FAIL` 이다 — 사고이며 사용자가 요청한 중단이 아니다.
    """

    PARTIAL_PASS = "partial_pass"
    """실패 Step 을 명시적으로 건너뛰고 나머지를 마쳤다 (FR-137).

    이름이 `partial` 이 아닌 이유는 `RunScope.PARTIAL`(부분 실행 = 실행 범위)과 구별하기
    위해서다. 같은 리터럴로 두 뜻을 표현하면 판정 코드에서 섞이고, 섞인 것을 테스트로
    잡기 어렵다.
    """


class RunScope(StrEnum):
    """이 실행이 전체였는가 부분이었는가 (005 FR-152).

    결말과 **다른 축**이다. Step 06~07 만 돌아 전부 통과하면 결말은 `PASS` 이고 범위가
    `PARTIAL` 이다. 한 값에 섞으면 "부분 구간을 전부 통과한 실행" 을 부를 이름이 없어진다.
    """

    FULL = "full"
    PARTIAL = "partial"


class StepOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"


class AssertionClass(StrEnum):
    """검증 Step 하나가 이번 실행에서 갖는 분류 (020 FR-018).

    **결말(`Outcome`)과 다른 축이다.** 결말은 실행 전체가 어떻게 끝났는가이고, 이것은
    검증 하나가 「원래 알던 것」인지 「오늘 깨진 것」인지다. 한 축에 섞으면 둘을 함께
    말할 수 없다 — `Outcome` 에 값을 더하지 않는 이유다 (FR-021).

    판정은 정의의 `AssertionStep.mismatch` 와 이번 실행의 `StepOutcome` **둘 다**를 봐야
    나온다. `classify_assertion()` 이 그 판정을 소유한다.
    """

    KNOWN_DEFECT = "known_defect"
    """작성 시점에도 실패했고 지금도 실패한다. **이미 아는 결함이다.**"""

    REGRESSION = "regression"
    """작성 시점에는 통과했는데 지금 실패한다. **오늘 깨진 것이며 먼저 봐야 한다.**"""

    RESOLVED = "resolved"
    """작성 시점에 어긋났는데 이번에는 통과했다 (FR-022).

    사용자에게 「표시를 걷어낼 수 있습니다」를 알리는 신호다. **제품이 스스로 걷어내지
    않는다** (FR-028) — 결함이 고쳐졌는지의 판단은 사람의 것이다.
    """


class LocatorAttempt(BaseModel):
    """요소 탐색 시도 하나. RunResult 화면의 "시도한 LOCATOR (우선순위 순)" 에 대응한다."""

    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    candidate: str
    """후보 종류 이름. `test_id`, `role`, `label`, `text`, `stable_attr`, `css`."""

    expression: str
    """사람이 읽는 표현. 예: `testId=save-dataset`."""

    matched: bool
    match_count: int = Field(default=0, ge=0)
    waited_ms: int = Field(default=0, ge=0)


class StepResult(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    step_id: str
    index: int = Field(ge=0)
    label: str
    outcome: StepOutcome
    duration_ms: int = Field(default=0, ge=0)
    tab: int = Field(default=0, ge=0)
    tab_wait_ms: int = Field(default=0, ge=0)
    """대상 탭이 열리기를 기다린 시간 (FR-030d)."""

    error_code: ErrorCode | None = None
    """실패의 분류 (004 FR-123).

    **결과 화면이 문구를 해석하지 않고 분기할 수 있어야 한다.** 003 이 실시간 이벤트에
    `error` 본문을 실었지만 저장된 결과에는 코드가 남지 않았다 — 그래서 결과 화면은
    "요소를 찾을 수 없습니다" 라는 문장을 읽는 것 말고 할 수 있는 일이 없었다.

    문구는 다듬을 수 있어야 하고, 다듬는 순간 분류가 깨지면 안 된다.
    """

    element_wait_ms: int = Field(default=0, ge=0)
    """요소가 나타나기를 폴링하며 기다린 시간 (004 FR-114).

    **성공한 Step 에도 기록한다.** 실패했을 때만 남기면 "왜 이 Step 만 느린가" 를 볼 수
    없고, 예산을 얼마로 잡아야 하는지 판단할 근거가 사라진다.

    `tab_wait_ms` 와 함께 `duration_ms` 를 나눠 쓴다 — 셋의 관계는
    `tab_wait_ms + element_wait_ms <= duration_ms` 다. **Step 간 간격은 포함되지 않는다**
    (FR-105). 간격은 Step 실행 밖의 시간이며 시간 초과 판정에 들어가지 않는다.
    """

    resolved_candidate: str | None = None
    """어느 후보로 요소를 찾았는지."""

    screenshot: str | None = None
    """이 Step 이 **끝난 시점**의 화면 (011 FR-389 · FR-397).

    **프로젝트 루트 기준 상대 경로다.** 절대 경로를 넣으면 결과 파일이 장비에 묶이고
    사용자 홈 경로가 노출된다 (`Artifacts` 의 경로들과 같은 규칙).

    없을 수 있는 경우가 셋이다.

    - 실행 대상이 아니었다 (`skipped`·`not_run`) — `screenshot_note` 도 비운다. 찍지
      못한 것이 아니라 찍을 일이 없었다 (FR-393).
    - 민감 값이 화면에 있어 남기지 않았다 — 사유를 남긴다 (FR-392).
    - 촬영이 실패했다 — 사유를 남긴다 (FR-391).

    실패한 Step 은 `Artifacts.failure_screenshot` 과 **같은 경로**를 가리킨다. 파일을 두 벌
    만들지 않는다 (FR-394).

    **선택 필드다** — 011 이전에 저장된 결과 파일이 그대로 읽힌다 (SC-613).
    """

    screenshot_note: str | None = None
    """화면을 남기지 못한 사유 (011 FR-391). `screenshot` 이 `None` 일 때만 뜻이 있다.

    **없다는 사실만으로는 부족하다.** 민감 값 때문에 남기지 않은 것과 촬영이 실패한 것은
    사용자에게 서로 다른 뜻이다 — 첫째는 의도된 보호이며, 실패로 읽히면 사용자가 없는
    결함을 찾는다.
    """

    locator_attempts: list[LocatorAttempt] = Field(default_factory=list)
    error_message: str | None = None
    candidate_disagreement: list[str] = Field(default_factory=list)
    """후보들이 서로 다른 요소를 가리킨 경우의 기록."""

    assertion_class: AssertionClass | None = None
    """검증 Step 이라면 이번 실행에서의 분류 (020 FR-018).

    **저장한다.** 분류는 정의의 `mismatch` 와 이번 결과를 함께 봐야 나오는데, 결과 파일만
    들고 화면을 그리는 자리가 있고 정의는 그 뒤에 바뀔 수 있다. 저장하지 않으면 어제
    실행한 결과의 분류가 오늘 정의를 고친 것 때문에 달라진다 — **결과는 그때의
    사실이어야 한다.**

    **선택 필드다** — 020 이전에 저장된 결과 파일이 그대로 읽힌다 (`screenshot` 이
    011 에서 같은 판단으로 들어온 것과 같다).

    건수 요약은 여기 없다. `counts_by_class()` 로 그때그때 센다 — 파생값을 저장하면
    원본과 어긋날 자리가 생긴다 (`attempted_of` 와 같은 판단).
    """


class Artifacts(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    failure_screenshot: str | None = None
    console_log: str | None = None
    network_log: str | None = None
    trace: None = None
    """MVP 미지원. `TRACE` 탭은 비활성으로 표시한다 (spec 디자인 차이 1)."""


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)

    test_id: str
    outcome: Outcome
    started_at: datetime
    finished_at: datetime
    total_ms: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    failed_step_index: int | None = Field(default=None, ge=0)
    browser: str
    steps: list[StepResult] = Field(default_factory=list)
    artifacts: Artifacts = Field(default_factory=Artifacts)
    session_lost: bool = False
    """세션 유실로 종료된 실행인지 (FR-041a)."""

    start_index: int = Field(default=0, ge=0)
    """이 실행이 시작한 Step (005 FR-152). 0 이면 처음부터 돌았다."""

    scope: RunScope = RunScope.FULL
    """전체 실행인가 부분 실행인가 (005 FR-152).

    `start_index > 0` 에서 파생되지만 **저장한다.** 읽는 쪽이 매번 해석하면 같은 규칙이
    여러 곳에 복제되고, 한 곳이 빠뜨린다.
    """

    attempted_count: int = Field(default=0, ge=0)
    """실제 실행 대상이던 Step 수 = 전체 − 건너뜀 (005 FR-152).

    **요약 문장의 분모는 이것이다.** `total_count` 를 분모로 쓰면 5개를 건너뛴 부분 실행이
    `0 / 7` 로 보여, 사용자는 직전 전체 실행(5/7)보다 나빠진 줄 안다 (U-02).
    """

    stopped_step_index: int | None = Field(default=None, ge=0)
    """사용자가 중지한 시점의 Step (005 FR-131). `STOPPED` 일 때만 채운다."""


# ─── 결말 판정 (005 T036a·T036b) ─────────────────────────────────────────────


def decide_outcome(
    steps: list[StepResult],
    *,
    session_lost: bool = False,
    stop_requested: bool = False,
    skipped_failures: bool = False,
) -> Outcome:
    """실행 결말을 정한다. **순수 함수다** (005 FR-131·FR-137).

    판정을 여기 한 곳에 두는 이유는 이전 구현이
    `Outcome.PASS if passed and not session_lost else Outcome.FAIL` 한 줄로 모든 결말을
    만들었고, 그 `passed` 불리언을 호출자마다 다르게 계산했기 때문이다. 그래서 사용자가
    누른 중지가 실패가 됐고(U-03), 실패 Step 을 건너뛴 실행이 완료로 보였다(U-05).

    우선순위는 위에서부터 먼저 걸리는 것이 이긴다 (data-model.md §1):

    1. 세션 유실 → `FAIL`. **사고이며 사용자가 요청한 중단이 아니다.** 중지보다 먼저
       보는 이유는, 유실 뒤에 도착한 중지 요청이 사고를 정상 중단으로 바꿔 적지 않게
       하려는 것이다.
    2. 중지 요청 → `STOPPED`
    3. 실패 Step 을 명시적으로 건너뛰고 계속함 → `PARTIAL_PASS`
       — **단, 건너뛰지 않은 실패가 남아 있으면 이 규칙을 건너뛴다** (020 FR-039)
    4. 실패 Step 이 남아 있음 → `FAIL`
    5. 그 외 → `PASS`

    `skipped_failures` 는 **사용자가 「실패한 Step 건너뛰고 계속」을 골랐는지**다.
    `StepOutcome.SKIPPED` 가 결과에 있는 것만으로는 알 수 없다 — 부분 실행도 앞선 Step 을
    건너뜀으로 적기 때문이다. 그 둘을 구분하지 않으면 부분 실행이 전부 `PARTIAL_PASS` 가
    된다.

    ## 3번이 조건을 갖게 된 이유 (020 FR-039)

    **순서는 바뀌지 않았다. 3번이 걸리는 조건만 좁혔다.**

    020 이전에는 실패가 곧 중단이었으므로 결과에 `FAIL` 이 하나뿐이었고, 그 하나가 곧
    사용자가 건너뛰기로 고른 것이었다. 020 FR-033 이 그 전제를 깬다 — 검증 실패는 실행을
    멈추지 않으므로 `FAIL` 이 여럿 쌓인 채 뒤쪽 동작 Step 에서 멈출 수 있다. 그때
    사용자가 건너뛰기를 고르면, 조건이 없는 3번은 **아무도 건너뛰지 않은 회귀까지 부분
    성공으로 덮는다.**

    `PARTIAL_PASS` 의 뜻은 「실패한 것들을 사용자가 알고 건너뛰었다」이지 「실패가
    있었다」가 아니다. 조건을 좁히는 것이 그 뜻을 되찾는 일이다.

    건너뛰기는 실패를 `SKIPPED` 로 바꾸므로(`Runner.skip_blocking_failure`), 여기 남아
    있는 `FAIL` 은 정의상 **건너뛰지 않은 것**이다.
    """
    if session_lost:
        return Outcome.FAIL
    if stop_requested:
        return Outcome.STOPPED
    unskipped_failure = any(r.outcome is StepOutcome.FAIL for r in steps)
    if skipped_failures and not unskipped_failure:
        return Outcome.PARTIAL_PASS
    if unskipped_failure:
        return Outcome.FAIL
    return Outcome.PASS


def counts_as_failure(outcome: Outcome) -> bool:
    """실패로 집계하는 결말인가 (005 FR-131).

    화면과 목록이 각자 `outcome == FAIL` 을 쓰면 결말이 늘 때마다 한 곳이 빠뜨린다.
    """
    return outcome is Outcome.FAIL


def attempted_of(steps: list[StepResult]) -> int:
    """실행 대상이던 Step 수 = 전체 − 건너뜀 (005 FR-152).

    `NOT_RUN` 은 **뺀다** — 실행 대상이었지만 앞선 실패로 도달하지 못한 것이므로 분모에
    남아야 한다. 그것을 빼면 실패한 실행이 `5 / 5` 로 보인다.
    """
    return sum(1 for r in steps if r.outcome is not StepOutcome.SKIPPED)


def scope_of(start_index: int) -> RunScope:
    """시작 지점에서 실행 범위를 정한다 (005 FR-152)."""
    return RunScope.FULL if start_index <= 0 else RunScope.PARTIAL


# ─── 검증 실패의 분류 (020 T035 · FR-018~FR-022) ──────────────────────────────


def classify_assertion(step: object, result: StepResult) -> AssertionClass | None:
    """검증 Step 하나가 이번 실행에서 갖는 분류. **순수 함수다** (020 FR-018).

    판정을 여기 한 곳에 두는 이유는 `decide_outcome` 과 같다 — 여러 곳이 각자 판정하면
    화면과 저장된 결과가 어긋난다 (005 가 그것으로 U-03·U-05 를 겪었다).

    **`step` 을 `object` 로 받는다.** `itb.domain.run_result` 가 `itb.domain.step` 을
    임포트하면 `step` → `assertion` → … 로 도메인 안에 방향 있는 의존이 하나 더 생긴다.
    이 함수에 필요한 것은 「검증 Step 인가」와 「`mismatch` 가 있는가」 둘뿐이고, 둘 다
    속성으로 물을 수 있다.

    판정표 (data-model.md §3):

    | 검증 Step | `mismatch` | `outcome` | 분류 |
    |---|---|---|---|
    | 예 | 있음 | `FAIL` | `KNOWN_DEFECT` |
    | 예 | 없음 | `FAIL` | `REGRESSION` |
    | 예 | 있음 | `PASS` | `RESOLVED` |
    | 예 | 없음 | `PASS` | `None` — 말할 것이 없다 |
    | 예 | — | `SKIPPED`·`NOT_RUN` | `None` — 실행되지 않았다 |
    | 아니오 | — | — | `None` |
    """
    if getattr(step, "type", None) != "assertion":
        return None
    had_mismatch = getattr(step, "mismatch", None) is not None
    if result.outcome is StepOutcome.FAIL:
        return AssertionClass.KNOWN_DEFECT if had_mismatch else AssertionClass.REGRESSION
    if result.outcome is StepOutcome.PASS and had_mismatch:
        return AssertionClass.RESOLVED
    return None


def counts_by_class(results: list[StepResult]) -> dict[AssertionClass, int]:
    """분류별 건수. **저장하지 않고 그때그때 센다** (020 FR-019).

    파생값을 저장하면 원본과 어긋날 자리가 생긴다 (`attempted_of` 와 같은 판단).

    **0건인 분류는 열쇠 자체가 없다.** 화면이 「없는 것을 0으로 표시할지」를 다시
    판단하지 않게 하려는 것이다 — 0건 분류를 싣지 않는 규칙(FR-019)이 여기서 한 번
    정해지고, 읽는 쪽 셋이 그것을 공유한다.
    """
    counts: dict[AssertionClass, int] = {}
    for result in results:
        if result.assertion_class is not None:
            counts[result.assertion_class] = counts.get(result.assertion_class, 0) + 1
    return counts
