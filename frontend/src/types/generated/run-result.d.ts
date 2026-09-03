/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type ConsoleLog = string | null;
export type FailureScreenshot = string | null;
export type NetworkLog = string | null;
export type Trace = null;
export type Browser = string;
export type FailedStepIndex = number | null;
export type FinishedAt = string;
export type Outcome = "pass" | "fail";
export type PassedCount = number;
export type SessionLost = boolean;
export type StartedAt = string;
export type CandidateDisagreement = string[];
export type DurationMs = number;
export type ErrorMessage = string | null;
export type Index = number;
export type Label = string;
export type Candidate = string;
export type Expression = string;
export type MatchCount = number;
export type Matched = boolean;
export type WaitedMs = number;
export type LocatorAttempts = LocatorAttempt[];
export type StepOutcome = "pass" | "fail" | "skipped" | "not_run";
export type ResolvedCandidate = string | null;
export type StepId = string;
export type Tab = number;
export type TabWaitMs = number;
export type Steps = StepResult[];
export type TestId = string;
export type TotalCount = number;
export type TotalMs = number;

export interface RunResult {
  artifacts: Artifacts;
  browser: Browser;
  failed_step_index: FailedStepIndex;
  finished_at: FinishedAt;
  outcome: Outcome;
  passed_count: PassedCount;
  session_lost: SessionLost;
  started_at: StartedAt;
  steps: Steps;
  test_id: TestId;
  total_count: TotalCount;
  total_ms: TotalMs;
}
export interface Artifacts {
  console_log: ConsoleLog;
  failure_screenshot: FailureScreenshot;
  network_log: NetworkLog;
  trace: Trace;
}
export interface StepResult {
  candidate_disagreement: CandidateDisagreement;
  duration_ms: DurationMs;
  error_message: ErrorMessage;
  index: Index;
  label: Label;
  locator_attempts: LocatorAttempts;
  outcome: StepOutcome;
  resolved_candidate: ResolvedCandidate;
  step_id: StepId;
  tab: Tab;
  tab_wait_ms: TabWaitMs;
}
/**
 * 요소 탐색 시도 하나. RunResult 화면의 "시도한 LOCATOR (우선순위 순)" 에 대응한다.
 */
export interface LocatorAttempt {
  candidate: Candidate;
  expression: Expression;
  match_count: MatchCount;
  matched: Matched;
  waited_ms: WaitedMs;
}
