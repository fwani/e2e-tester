/**
 * 국면별 픽스처 팩토리 (007 T004).
 *
 * **왜 필요한가.** 007 은 일곱 국면을 하나의 화면으로 합친다. 그 화면을 검사하려면 같은
 * 테스트 안에서 일곱 국면을 만들어야 하는데, 지금 테스트들은 국면마다 `SessionView` 를
 * 손으로 조립한다. 손으로 조립하면 필드가 빠지고, 빠진 필드는 **테스트가 통과하는 채로**
 * 런타임 오류를 낸다.
 *
 * 실제로 그랬다 — 기준선(`design-conformance/baseline.md`)의 미처리 오류 2건이
 * `tests/EditEntryPoints.test.tsx` 의 픽스처에 `recorder_warnings` 가 없어서 났다.
 * 353개 테스트가 전부 통과하는 상태에서 `view.recorder_warnings.map` 이 터졌다.
 *
 * 그래서 이 파일의 규칙은 하나다 — **팩토리는 항상 온전한 객체를 만든다.** 필요한 것만
 * `overrides` 로 덮는다.
 */

import type {
  DefinitionView,
  RunResultView,
  SessionState,
  SessionView,
} from "../../src/api/client";
import type { Step, TargetLocator } from "../../src/types/generated/step";
import type { StepResult } from "../../src/types/generated/run-result";
import type { Test } from "../../src/types/generated/step-dsl";

/** `verified` 후보 하나를 가진 최소 유효 `TargetLocator`. */
export function target(overrides: Partial<TargetLocator> = {}): TargetLocator {
  return {
    accessible_name: "로그인",
    css: { status: "verified", value: "button.login" },
    label: null,
    role: "button",
    role_status: "verified",
    stable_attr: null,
    tag: "button",
    test_id: null,
    text: null,
    ...overrides,
  };
}

/** `click` Step 하나. 다른 종류가 필요하면 `overrides` 로 `type` 을 바꾼다. */
export function clickStep(overrides: Partial<Step> = {}): Step {
  return {
    type: "click",
    id: "st-1",
    label: "로그인 버튼 클릭",
    author: "human",
    frame_url: null,
    tab: 0,
    timeout_ms: 5000,
    target: target(),
    ...overrides,
  } as Step;
}

/** `fill` Step 하나. 값을 가진 행의 칸 자리를 검사할 때 쓴다. */
export function fillStep(overrides: Partial<Step> = {}): Step {
  return {
    type: "fill",
    id: "st-2",
    label: "아이디 입력",
    author: "human",
    frame_url: null,
    tab: 0,
    timeout_ms: 5000,
    target: target({ accessible_name: "아이디", role: "textbox" }),
    value: "tester",
    ...overrides,
  } as Step;
}

/** 두 개짜리 기본 Step 목록. */
export function steps(): Step[] {
  return [clickStep({ id: "st-1" }), fillStep({ id: "st-2" })];
}

/**
 * 온전한 `SessionView`.
 *
 * **선택 필드까지 채운다.** `step_results` · `pause_settled` · `run_scope` 는 타입이
 * 선택이지만 서버는 항상 보낸다. 픽스처가 빼면 화면의 복원 경로(005 FR-171)가 테스트에서
 * 한 번도 걸리지 않는다.
 */
export function sessionView(overrides: Partial<SessionView> = {}): SessionView {
  return {
    session_id: "s-1",
    state: "replaying",
    state_label: "실행 중",
    test_id: "TC-001",
    test_name: "로그인",
    current_step_index: 0,
    steps: steps(),
    tabs_open: 1,
    active_tab_index: 0,
    mirrored_tab_index: 0,
    edit_warnings: [],
    recorder_warnings: [],
    allowed_commands: ["PAUSE", "STOP"],
    has_unsaved_changes: false,
    authoring_mode: "record",
    pacing: "normal",
    step_results: [],
    pause_settled: true,
    run_scope: "full",
    run_start_index: 0,
    saved_at: null,
    ...overrides,
  } as SessionView;
}

/**
 * 국면 약칭 → 그 국면을 만드는 `SessionView`.
 *
 * `contracts/ui-contract.md` §3 의 국면 약칭을 그대로 쓴다. 세션이 없는 국면
 * (`RES`·`EDT`)은 세션으로 만들 수 없으므로 여기 없다 — `definitionView`·`runResult` 가
 * 그 둘을 맡는다.
 */
export const SESSION_PHASES: Record<
  "REC" | "AI" | "TKO" | "RUN" | "PAU",
  { state: SessionState; authoring_mode: "record" | "ai" }
> = {
  REC: { state: "recording", authoring_mode: "record" },
  AI: { state: "ai_running", authoring_mode: "ai" },
  TKO: { state: "takeover_recording", authoring_mode: "ai" },
  RUN: { state: "replaying", authoring_mode: "record" },
  PAU: { state: "paused", authoring_mode: "record" },
};

/** 국면 약칭으로 세션을 만든다. */
export function sessionInPhase(
  phase: keyof typeof SESSION_PHASES,
  overrides: Partial<SessionView> = {},
): SessionView {
  const { state, authoring_mode } = SESSION_PHASES[phase];
  return sessionView({ state, authoring_mode, ...overrides });
}

/** 저장된 테스트 정의. */
export function test(overrides: Partial<Test> = {}): Test {
  return {
    id: "TC-001",
    name: "로그인",
    start_url: "http://t/login.html",
    authoring_mode: "record",
    ai_instruction: null,
    steps: steps(),
    variables: [],
    ...overrides,
  } as unknown as Test;
}

/** 온전한 `DefinitionView` — 편집 국면의 입력이다. */
export function definitionView(overrides: Partial<DefinitionView> = {}): DefinitionView {
  return {
    test: test(),
    revision: "rev-1",
    editable: true,
    blocked_by: null,
    blocking_session_id: null,
    locked_fields: [],
    warnings: [],
    ...overrides,
  };
}

/** 결과의 Step 행 하나. **Step DSL 을 갖지 않는다** — research R3 이 확인한 사실이다. */
export function stepResult(overrides: Partial<StepResult> = {}): StepResult {
  return {
    step_id: "st-1",
    index: 0,
    label: "로그인 버튼 클릭",
    outcome: "pass",
    duration_ms: 120,
    element_wait_ms: 0,
    tab: 0,
    tab_wait_ms: 0,
    /* 011 — 서버는 이 둘을 **항상** 싣는다 (`error_code` 와 같은 규칙). 없음은 `null` 이다 */
    screenshot: null,
    screenshot_note: null,
    error_code: null,
    error_message: null,
    locator_attempts: [],
    resolved_candidate: "role=button \"로그인\"",
    candidate_disagreement: [],
    ...overrides,
  };
}

/** 온전한 `RunResultView` — 결과 국면의 입력이다. */
export function runResult(overrides: Partial<RunResultView> = {}): RunResultView {
  return {
    test_id: "TC-001",
    outcome: "pass",
    scope: "full",
    start_index: 0,
    passed_count: 2,
    attempted_count: 2,
    total_count: 2,
    total_ms: 240,
    failed_step_index: null,
    stopped_step_index: null,
    session_lost: false,
    browser: "chromium",
    started_at: "2026-09-08T00:00:00Z",
    finished_at: "2026-09-08T00:00:00Z",
    steps: [stepResult({ step_id: "st-1", index: 0 }), stepResult({ step_id: "st-2", index: 1 })],
    artifacts: {
      console_log: null,
      failure_screenshot: null,
      network_log: null,
      trace: null,
    },
    ...overrides,
  } as RunResultView;
}
