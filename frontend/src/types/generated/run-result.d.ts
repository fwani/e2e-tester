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
export type AttemptedCount = number;
export type Browser = string;
export type FailedStepIndex = number | null;
export type FinishedAt = string;
/**
 * 실행이 어떻게 끝났는가 (005 FR-131·FR-137).
 *
 * **네 값이 필요한 이유는 두 값이 서로 다른 것을 뭉갰기 때문이다.** 사용자가 누른 중지가
 * `FAIL` 로 기록되어 사고처럼 보이고(U-03), 실패 Step 을 건너뛴 실행이 통과처럼 보였다
 * (U-05).
 *
 * 판정 우선순위는 `decide_outcome()` 이 갖는다. 여기서 값을 늘리기만 하고 판정을 여러
 * 곳에 흩으면 화면과 저장된 결과가 다시 어긋난다.
 */
export type Outcome = "pass" | "fail" | "stopped" | "partial_pass";
export type PassedCount = number;
/**
 * 이 실행이 전체였는가 부분이었는가 (005 FR-152).
 *
 * 결말과 **다른 축**이다. Step 06~07 만 돌아 전부 통과하면 결말은 `PASS` 이고 범위가
 * `PARTIAL` 이다. 한 값에 섞으면 "부분 구간을 전부 통과한 실행" 을 부를 이름이 없어진다.
 */
export type RunScope = "full" | "partial";
export type SessionLost = boolean;
export type StartIndex = number;
export type StartedAt = string;
export type CandidateDisagreement = string[];
export type DurationMs = number;
export type ElementWaitMs = number;
export type ErrorCode =
  | "PROJECT_NOT_OPEN"
  | "PROJECT_ALREADY_EXISTS"
  | "PROJECT_NOT_FOUND"
  | "INVALID_PATH"
  | "PROJECT_IN_USE"
  | "PROJECT_MISMATCH"
  | "PROJECT_DELETE_FAILED"
  | "GROUP_NOT_FOUND"
  | "GROUP_ALREADY_EXISTS"
  | "GROUP_PREFIX_RESERVED"
  | "TEST_NOT_FOUND"
  | "TEST_IN_USE"
  | "TEST_DELETE_FAILED"
  | "TEST_DELETE_PARTIAL"
  | "TEST_MOVE_FAILED"
  | "TEST_MOVE_PARTIAL"
  | "STEP_LIST_EMPTY"
  | "DEFINITION_INVALID"
  | "DEFINITION_STALE"
  | "SESSION_NOT_FOUND"
  | "SESSION_ALREADY_ACTIVE"
  | "SESSION_LOST"
  | "NOT_PAUSED"
  | "CANNOT_RESUME_PAST_FAILURE"
  | "INVALID_TRANSITION"
  | "TAB_NOT_FOUND"
  | "TAB_LIMIT_REACHED"
  | "KEY_MISSING"
  | "KEY_ALREADY_EXISTS"
  | "PASSPHRASE_REQUIRED"
  | "PASSPHRASE_INVALID"
  | "DECRYPT_FAILED"
  | "FINGERPRINT_MISMATCH"
  | "SECRET_NOT_FOUND"
  | "STEP_FAILED"
  | "TARGET_UNREACHABLE"
  | "ELEMENT_NOT_READY"
  | "ELEMENT_AMBIGUOUS"
  | "AI_FAILED"
  | "STORAGE_WRITE_FAILED"
  | "PROMPT_NOT_FOUND"
  | "UPLOAD_REJECTED"
  | "UPLOAD_NOT_FOUND"
  | "NOT_SUPPORTED"
  | "INTERNAL_ERROR";
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
export type Screenshot = string | null;
export type ScreenshotNote = string | null;
export type StepId = string;
export type Tab = number;
export type TabWaitMs = number;
export type Steps = StepResult[];
export type StoppedStepIndex = number | null;
export type TestId = string;
export type TotalCount = number;
export type TotalMs = number;

export interface RunResult {
  artifacts: Artifacts;
  attempted_count: AttemptedCount;
  browser: Browser;
  failed_step_index: FailedStepIndex;
  finished_at: FinishedAt;
  outcome: Outcome;
  passed_count: PassedCount;
  scope: RunScope;
  session_lost: SessionLost;
  start_index: StartIndex;
  started_at: StartedAt;
  steps: Steps;
  stopped_step_index: StoppedStepIndex;
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
  element_wait_ms: ElementWaitMs;
  error_code: ErrorCode | null;
  error_message: ErrorMessage;
  index: Index;
  label: Label;
  locator_attempts: LocatorAttempts;
  outcome: StepOutcome;
  resolved_candidate: ResolvedCandidate;
  screenshot: Screenshot;
  screenshot_note: ScreenshotNote;
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
