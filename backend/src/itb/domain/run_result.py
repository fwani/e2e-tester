"""실행 결과. `.runs/<테스트ID>/result.json` 에 저장한다. 테스트당 최근 1건만 보관한다."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Outcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class StepOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    NOT_RUN = "not_run"


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

    locator_attempts: list[LocatorAttempt] = Field(default_factory=list)
    error_message: str | None = None
    candidate_disagreement: list[str] = Field(default_factory=list)
    """후보들이 서로 다른 요소를 가리킨 경우의 기록."""


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
