/**
 * REST 클라이언트. contracts/rest-api.md.
 *
 * **명령은 REST, 관찰은 WebSocket.** 이 파일은 명령만 담당한다.
 *
 * 타입은 backend/schema 에서 생성된 것만 쓴다 — 손으로 정의하면 원칙 I 의
 * Cross-language schema duty 를 위반한다.
 */
import type { RunResult } from "../types/generated/run-result";
import type { Step } from "../types/generated/step";
import type { Test } from "../types/generated/step-dsl";

export type ErrorCode =
  | "PROJECT_NOT_OPEN"
  | "PROJECT_ALREADY_EXISTS"
  | "PROJECT_NOT_FOUND"
  | "INVALID_PATH"
  | "TEST_NOT_FOUND"
  | "STEP_LIST_EMPTY"
  | "DEFINITION_INVALID"
  | "SESSION_NOT_FOUND"
  | "SESSION_ALREADY_ACTIVE"
  | "SESSION_LOST"
  | "NOT_PAUSED"
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
  | "NOT_SUPPORTED";

/** 서버가 계약 형태로 보낸 오류. 메시지를 그대로 사용자에게 보여줄 수 있다. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: ErrorCode | "UNKNOWN",
    message: string,
    readonly detail: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });

  if (resp.status === 204) return undefined as T;

  const text = await resp.text();
  const body: unknown = text ? JSON.parse(text) : null;

  if (!resp.ok) {
    const err = (body as { error?: { code?: ErrorCode; message?: string; detail?: Record<string, unknown> } })?.error;
    throw new ApiError(
      resp.status,
      err?.code ?? "UNKNOWN",
      err?.message ?? `요청이 실패했습니다 (${resp.status}).`,
      err?.detail ?? {},
    );
  }
  return body as T;
}

const get = <T,>(p: string) => request<T>(p);
const post = <T,>(p: string, body?: unknown) =>
  request<T>(p, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
const patch = <T,>(p: string, body: unknown) =>
  request<T>(p, { method: "PATCH", body: JSON.stringify(body) });
const del = <T,>(p: string) => request<T>(p, { method: "DELETE" });

// ─── 프로젝트 ───────────────────────────────────────────────────────────────

export interface ProjectView {
  root: string;
  name: string;
  default_start_url: string;
  browser: "chromium";
  test_id_attribute: string;
  max_tabs: number;
  gitignore_present: boolean;
  secrets_file_present: boolean;
}

export const project = {
  current: () => get<ProjectView>("/api/project"),
  create: (body: {
    path: string;
    name: string;
    default_start_url: string;
    test_id_attribute?: string;
  }) => post<ProjectView>("/api/project/create", body),
  open: (path: string) => post<ProjectView>("/api/project/open", { path }),
};

// ─── 테스트 ─────────────────────────────────────────────────────────────────

export interface FailureSummary {
  step_index: number;
  message: string;
}

export interface TestListRow {
  id: string;
  name: string;
  step_count: number;
  authoring_mode: "record" | "ai";
  outcome: "pass" | "fail" | null;
  last_run_at: string | null;
  failure_summary: FailureSummary | null;
}

export interface TestListResponse {
  counts: { total: number; pass: number; fail: number };
  tests: TestListRow[];
  problems: string[];
}

/** 산출물 종류. `trace` 는 서버가 `501` 을 돌려준다 (spec 디자인 차이 1). */
export type ArtifactKind = "screenshot" | "trace" | "console" | "network";

export const tests = {
  list: (q?: string) =>
    get<TestListResponse>(`/api/tests${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  get: (id: string) => get<Test>(`/api/tests/${id}`),
  rename: (id: string, name: string) => patch<Test>(`/api/tests/${id}`, { name }),
  remove: (id: string) => del<void>(`/api/tests/${id}`),
  /** 최근 실행 결과. 테스트당 1건만 보관된다 (FR-050~FR-054). */
  result: (id: string) => get<RunResult>(`/api/tests/${id}/result`),
  artifact: (id: string, kind: ArtifactKind) =>
    get<{ kind: string; path: string }>(`/api/tests/${id}/result/artifacts/${kind}`),
};

// ─── 세션 ───────────────────────────────────────────────────────────────────

export type SessionState =
  | "starting"
  | "recording"
  | "replaying"
  | "ai_running"
  | "ai_blocked"
  | "takeover_recording"
  | "paused"
  | "completed"
  | "failed"
  | "stopped"
  | "lost";

export interface SessionView {
  session_id: string;
  state: SessionState;
  state_label: string;
  test_id: string | null;
  current_step_index: number;
  steps: Step[];
  tabs_open: number;
  active_tab_index: number;
  mirrored_tab_index: number;
  edit_warnings: string[];
  recorder_warnings: string[];
  allowed_commands: string[];
  /** 저장하지 않은 편집이 있는가. 중지 확인의 근거다 (FR-042). */
  has_unsaved_changes: boolean;
}

export interface TabView {
  tab_index: number;
  url: string;
  title: string;
  closed: boolean;
}

export interface TabsResponse {
  tabs: TabView[];
  active_tab_index: number;
  mirrored_tab_index: number;
  max_tabs: number;
}

export interface StepsResponse {
  steps: Step[];
  edit_warnings: string[];
  current_step_index: number;
}

/** 검증 조건 4종 (FR-013a). 요소 갯수·입력값 검증은 범위 외 (FR-013c). */
export type AssertionKind = "visible" | "hidden" | "text" | "url";
export type MatchMode = "equals" | "contains";

export interface AddAssertionBody {
  kind: AssertionKind;
  /** 대상 요소. **후보 수집은 제품이 한다** — 클라이언트는 셀렉터만 준다 (원칙 IV). */
  target_selector?: string | null;
  value?: string | null;
  match?: MatchMode;
  label?: string | null;
  at?: number | null;
  tab?: number | null;
}

/** 다시 집을 대상. `drag` 만 두 번째 값을 쓴다 (T166). */
export type RepickSlot = "target" | "drop_target";

export interface RepickResponse extends StepsResponse {
  waiting: boolean;
  slot: RepickSlot;
  message: string;
}

export const sessions = {
  create: (body: {
    mode: "record" | "replay" | "ai";
    test_id?: string | null;
    start_url?: string | null;
    ai_instruction?: string | null;
  }) => post<SessionView>("/api/sessions", body),
  get: (id: string) => get<SessionView>(`/api/sessions/${id}`),
  pause: (id: string) => post<SessionView>(`/api/sessions/${id}/pause`),
  resume: (id: string) => post<SessionView>(`/api/sessions/${id}/resume`),
  runFrom: (id: string, stepIndex: number) =>
    post<SessionView>(`/api/sessions/${id}/run-from`, { step_index: stepIndex }),
  recordActionsStart: (id: string) =>
    post<SessionView>(`/api/sessions/${id}/record-actions:start`),
  recordActionsStop: (id: string) =>
    post<SessionView>(`/api/sessions/${id}/record-actions:stop`),
  stop: (id: string) => post<SessionView>(`/api/sessions/${id}/stop`),
  save: (id: string, name: string) => post<Test>(`/api/sessions/${id}/save`, { name }),
  tabs: (id: string) => get<TabsResponse>(`/api/sessions/${id}/tabs`),
  setMirrorTab: (id: string, tabIndex: number) =>
    post<TabsResponse>(`/api/sessions/${id}/mirror-tab`, { tab_index: tabIndex }),
  deleteStep: (id: string, stepId: string) =>
    del<StepsResponse>(`/api/sessions/${id}/steps/${stepId}`),
  reorderSteps: (id: string, order: string[]) =>
    post<StepsResponse>(`/api/sessions/${id}/steps:reorder`, { order }),
  /** Step 삽입. `at` 을 생략하면 일시정지 위치다 (FR-035). */
  insertStep: (id: string, step: unknown, at?: number) =>
    post<StepsResponse>(`/api/sessions/${id}/steps`, { step, at: at ?? null }),
  /** 표시 이름·입력값·타임아웃·민감 여부 수정 (FR-035·FR-082b). */
  patchStep: (
    id: string,
    stepId: string,
    body: {
      label?: string;
      value?: string;
      timeout_ms?: number;
      sensitive?: boolean;
    },
  ) => patch<StepsResponse>(`/api/sessions/${id}/steps/${stepId}`, body),
  /** 검증 Step 추가 (FR-037·FR-013a). */
  addAssertion: (id: string, body: AddAssertionBody) =>
    post<StepsResponse>(`/api/sessions/${id}/assertions`, body),
  /**
   * "다시 집기" (FR-020). `selector` 를 생략하면 브라우저에서 클릭할 때까지 대기한다 —
   * 그 클릭은 Step 으로 기록되지 않는다.
   */
  repick: (id: string, stepId: string, body: { slot?: RepickSlot; selector?: string }) =>
    post<RepickResponse>(`/api/sessions/${id}/steps/${stepId}/repick`, {
      slot: body.slot ?? "target",
      selector: body.selector ?? null,
    }),
};

// ─── 비밀 값·키 ─────────────────────────────────────────────────────────────

export interface KeyStatus {
  private_key_present: boolean;
  public_key_present: boolean;
  passphrase_protected: boolean;
  public_key_fingerprint: string | null;
  permission_warning: string | null;
}

export interface SecretsResponse {
  public_key_fingerprint: string | null;
  fingerprint_matches_key: boolean;
  names: { name: string; present: boolean }[];
}

export const secrets = {
  keyStatus: () => get<KeyStatus>("/api/keys/status"),
  generateKey: (passphrase?: string) =>
    post<KeyStatus>("/api/keys/generate", { passphrase: passphrase ?? null }),
  list: () => get<SecretsResponse>("/api/secrets"),
  /** 값은 응답에 없다. 공개키만으로 봉인한다 (FR-089b). */
  put: (name: string, value: string) =>
    request<void>(`/api/secrets/${name}`, { method: "PUT", body: JSON.stringify({ value }) }),
  remove: (name: string) => del<void>(`/api/secrets/${name}`),
};

export const health = () =>
  get<{ status: string; bind: string; project_open: boolean; active_sessions: number }>(
    "/api/health",
  );
