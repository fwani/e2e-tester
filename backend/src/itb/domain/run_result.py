"""실행 결과. `.runs/<테스트ID>/result.json` 에 저장한다. 테스트당 최근 1건만 보관한다."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Outcome(StrEnum):
    # ruff S105 는 PASS 라는 이름을 비밀번호로 오인한다. 테스트 통과 여부다.
    PASS = "pass"  # noqa: S105
    FAIL = "fail"


class StepOutcome(StrEnum):
    PASS = "pass"  # noqa: S105
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
