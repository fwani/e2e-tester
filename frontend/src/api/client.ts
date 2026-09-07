/**
 * REST 클라이언트. contracts/rest-api.md.
 *
 * **명령은 REST, 관찰은 WebSocket.** 이 파일은 명령만 담당한다.
 *
 * 타입은 backend/schema 에서 생성된 것만 쓴다 — 손으로 정의하면 원칙 I 의
 * Cross-language schema duty 를 위반한다.
 */
import type { Category, ErrorBody, ErrorCode } from "../types/generated/error-response";
import type { RunResult } from "../types/generated/run-result";
import type { Step } from "../types/generated/step";
import type { Test } from "../types/generated/step-dsl";

// ErrorCode·Category 는 backend/src/itb/domain/error.py 에서 생성된다. 손으로 쓰지 않는다.
export type { Category, ErrorBody, ErrorCode } from "../types/generated/error-response";

/**
 * 서버가 계약 형태로 보낸 오류. 메시지를 그대로 사용자에게 보여줄 수 있다.
 *
 * `category` 는 이 오류가 **막은 것**(사용자가 고칠 수 있다)인지 **깨진 것**(할 수 있는
 * 일이 없다)인지를 말한다. 상태 코드로 유추하지 않는다 — 둘은 일대일이 아니다 (003 EC-002).
 * 계약 형태가 아닌 응답(연결 실패 등)은 `code: "UNKNOWN"` 에 `category: "broken"` 이다.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: ErrorCode | "UNKNOWN",
    message: string,
    readonly detail: Record<string, unknown> = {},
    readonly category: Category = "broken",
    readonly nextAction: string = "",
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
  if (!resp.ok) throw apiErrorFromBody(resp.status, text);
  return (text ? JSON.parse(text) : null) as T;
}

/** 실패 응답 본문을 `ApiError` 로 바꾼다. 계약 형태가 아니어도 던질 수 있는 것을 만든다. */
function apiErrorFromBody(status: number, text: string): ApiError {
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null; // 계약 형태가 아닌 본문(HTML 오류 페이지 등)
  }
  const err = (body as { error?: Partial<ErrorBody> } | null)?.error;
  return new ApiError(
    status,
    err?.code ?? "UNKNOWN",
    err?.message ?? `요청이 실패했습니다 (${status}).`,
    (err?.detail ?? {}) as Record<string, unknown>,
    // 계약 형태가 아니면 제품이 스스로를 설명하지 못한 것이므로 "깨진 것" 이다.
    err?.category ?? "broken",
    err?.next_action ?? "화면을 새로 고쳐 다시 시도하세요. 계속 발생하면 서버 로그를 확인하세요.",
  );
}

const get = <T,>(p: string) => request<T>(p);
const post = <T,>(p: string, body?: unknown) =>
  request<T>(p, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
const patch = <T,>(p: string, body: unknown) =>
  request<T>(p, { method: "PATCH", body: JSON.stringify(body) });
const put = <T,>(p: string, body: unknown) =>
  request<T>(p, { method: "PUT", body: JSON.stringify(body) });
// DELETE 에 본문을 실을 수 있게 한다 — 프로젝트를 목록에서 치울 때 `root` 를 보낸다.
const del = <T,>(p: string, body?: unknown) =>
  request<T>(p, {
    method: "DELETE",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

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

/** 도구가 알고 있는 프로젝트 하나. 첫 화면 목록의 항목이다 (DR-002·DR-003). */
export interface ProjectListItem {
  root: string;
  name: string;
  last_opened_at: string;
  origin: "managed" | "external";
  /** 지금 열 수 있는가. 조회 시점에 계산된다 — 파일 시스템은 도구 밖에서 바뀐다. */
  accessible: boolean;
  unavailable_reason: string | null;
}

export interface ProjectListResponse {
  projects: ProjectListItem[];
  /** 레지스트리를 읽지 못했을 때의 사유. 목록 조회 자체는 실패하지 않는다. */
  warning: string | null;
}

export const project = {
  current: () => get<ProjectView>("/api/project"),
  /** 첫 화면 목록. 관리 위치 스캔 ∪ 레지스트리를 최근 연 순으로 준다. */
  list: () => get<ProjectListResponse>("/api/project/list"),
  /**
   * 새 프로젝트. **`path` 를 보내지 않는다** (DR-001) — 사용자는 서버의 실행 경로를
   * 알 수 없다. 도구가 위치를 정하고 응답의 `root` 로 알려 준다.
   */
  create: (body: { name: string; default_start_url: string; test_id_attribute?: string }) =>
    post<ProjectView>("/api/project/create", body),
  /** 사용자가 폴더 선택기로 고른 경로를 연다. 위치를 지정하는 유일한 경로다 (DR-005). */
  open: (path: string) => post<ProjectView>("/api/project/open", { path }),
  /** 목록에서만 치운다. **디스크의 프로젝트는 지우지 않는다** (DR-009). */
  forget: (root: string) => del<void>("/api/project/registry", { root }),
};

// ─── 디렉터리 탐색 (DR-005) ─────────────────────────────────────────────────
//
// 브라우저는 임의 절대 경로를 줄 수 없다. 서버가 홈 하위 디렉터리 목록을 그린다.
// **디렉터리만 온다 — 파일 이름은 오지 않는다.**

export interface DirectoryEntry {
  name: string;
  path: string;
  /** 유효한 프로젝트 구조인가. 사용자가 어디를 골라야 하는지 알려 준다. */
  is_project: boolean;
}

export interface BrowseResponse {
  path: string;
  /** 홈 최상위에서는 `null`. 경계 밖으로 올라갈 수 없다. */
  parent: string | null;
  entries: DirectoryEntry[];
}

export const fs = {
  browse: (path?: string) =>
    get<BrowseResponse>(
      path === undefined ? "/api/fs/browse" : `/api/fs/browse?path=${encodeURIComponent(path)}`,
    ),
};

// ─── AI 사용 가능 여부 (DR-021) ─────────────────────────────────────────────
//
// **작성 경로 전용이다.** 재실행 경로는 이것을 읽지 않는다 (원칙 II).
// 자격 증명의 조각은 오지 않는다 — 가능 여부와 안내 문구뿐이다.

export interface AiAvailability {
  available: boolean;
  /** 쓸 수 없을 때 무엇이 준비되지 않았고 무엇을 하면 되는지. */
  reason: string | null;
}

export const ai = {
  availability: () => get<AiAvailability>("/api/ai/availability"),
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
  /**
   * 산출물 주소. 서버가 **바이트**를 돌려주므로 스크린샷은 `<img src>` 에 그대로 넣는다.
   * 예전에는 `{kind, path}` JSON 을 받아 그 상대 경로를 `src` 에 넣었고, 화면에는 깨진
   * 이미지와 경로 문자열만 남았다 (UX U-03).
   */
  artifactUrl: (id: string, kind: ArtifactKind) => `/api/tests/${id}/result/artifacts/${kind}`,
  /** 로그 산출물 본문. 실패는 계약 형태 오류로 온다. */
  artifactText: async (id: string, kind: ArtifactKind): Promise<string> => {
    const resp = await fetch(`/api/tests/${id}/result/artifacts/${kind}`);
    const text = await resp.text();
    if (!resp.ok) throw apiErrorFromBody(resp.status, text);
    return text;
  },
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
  /** 중지 후 검토. **종료 상태가 아니다** — 편집·저장을 받는다 (DR-010). */
  | "review"
  | "stopped"
  | "lost";

/**
 * 실행 속도 (004 FR-102). 값과 간격의 대응표는 **서버가 갖는다** —
 * `pacing_changed` 이벤트가 `delay_ms` 와 `auto_pause` 를 함께 실어 보낸다.
 * 화면이 대응표를 복제하면 서버와 갈린다.
 */
export type RunPacing = "fast" | "normal" | "slow" | "step";

/** 화면 표기. 값 → 이름은 표기일 뿐이라 여기 둬도 서버와 갈리지 않는다. */
export const PACING_LABEL: Record<RunPacing, string> = {
  fast: "빠름",
  normal: "보통",
  slow: "느림",
  step: "한 스텝씩",
};

export const PACING_ORDER: RunPacing[] = ["fast", "normal", "slow", "step"];

export interface PreferencesView {
  run_pacing: RunPacing;
  /** 설정을 읽지 못한 사유. **조회 자체는 실패하지 않는다.** */
  warning: string | null;
}

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
  /**
   * 어떻게 만드는 세션인가. **세션의 불변 속성이다.**
   *
   * 화면이 AI 세션 여부를 `state` 로 판정하면 AI 가 실패해 `paused` 로 바뀌는 순간
   * 실패 사유가 사라진다 — 001 의 "AI 로 만들기 무반응" 이 그것이다 (research R2).
   */
  authoring_mode: "record" | "ai";
  /**
   * 이 세션의 실행 속도 (004).
   *
   * `paused` 의 **문구를 가르는 유일한 근거**다. 자동 일시정지(`한 스텝씩`)와 사용자가
   * 직접 누른 일시정지는 상태가 같고 의미가 다르다 — 상태로는 구별할 수 없다.
   */
  pacing: RunPacing;
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

/** AI 실패 시 4선택지 (FR-071~FR-074). */
export type AiChoice = "takeover" | "retry" | "skip" | "abort";

export interface AiStepResponse {
  created: boolean;
  message: string;
  step_id: string | null;
  steps: Step[];
  current_step_index: number;
  state: SessionState;
}

/** 다시 집을 대상. `drag` 만 두 번째 값을 쓴다 (T166). */
export type RepickSlot = "target" | "drop_target";

export interface RepickResponse extends StepsResponse {
  waiting: boolean;
  slot: RepickSlot;
  message: string;
}

export interface SessionListResponse {
  sessions: SessionView[];
}

export const sessions = {
  /** 살아 있는 세션 전부. 새로고침으로 놓친 세션을 되찾는 길이다 (UX U-05). */
  list: () => get<SessionListResponse>("/api/sessions"),
  create: (body: {
    mode: "record" | "replay" | "ai";
    test_id?: string | null;
    start_url?: string | null;
    ai_instruction?: string | null;
    /** 생략하면 저장된 취향, 그것도 없으면 서버 기본값 (FR-109). */
    pacing?: RunPacing;
  }) => post<SessionView>("/api/sessions", body),
  get: (id: string) => get<SessionView>(`/api/sessions/${id}`),
  /**
   * 실행 속도 변경 (FR-103). **실행 중에도 부를 수 있다** — 진행 중인 Step 을 끊지
   * 않고 다음 Step 경계부터 적용된다.
   */
  setPacing: (id: string, pacing: RunPacing) =>
    post<SessionView>(`/api/sessions/${id}/pacing`, { pacing }),
  pause: (id: string) => post<SessionView>(`/api/sessions/${id}/pause`),
  resume: (id: string) => post<SessionView>(`/api/sessions/${id}/resume`),
  runFrom: (id: string, stepIndex: number) =>
    post<SessionView>(`/api/sessions/${id}/run-from`, { step_index: stepIndex }),
  recordActionsStart: (id: string) =>
    post<SessionView>(`/api/sessions/${id}/record-actions:start`),
  recordActionsStop: (id: string) =>
    post<SessionView>(`/api/sessions/${id}/record-actions:stop`),
  /**
   * 중지 — **브라우저만 정리한다.** 세션은 `review` 로 남아 Step 을 계속 보고 저장할
   * 수 있다 (DR-010·DR-013). 001 은 여기서 세션을 파괴해 이후 저장이 불가능했다.
   */
  stop: (id: string) => post<SessionView>(`/api/sessions/${id}/stop`),
  /** 검토 중인 초안을 버린다. **여기서 비로소 세션이 파괴된다** (DR-014). */
  discard: (id: string) => post<void>(`/api/sessions/${id}/discard`),
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
  /** AI 실패 시 선택 (FR-071~FR-074). `AI_BLOCKED` 에서만 받는다. */
  aiChoice: (id: string, choice: AiChoice) =>
    post<SessionView>(`/api/sessions/${id}/ai-choice`, { choice }),
  /**
   * 일시정지 중 자연어로 Step 하나 추가 (FR-078).
   *
   * 대상을 찾지 못하면 `created: false` 와 사유가 온다 — 실패해도 일시정지 상태가
   * 유지된다 (FR-081).
   */
  aiStep: (id: string, instruction: string) =>
    post<AiStepResponse>(`/api/sessions/${id}/ai-step`, { instruction }),
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
  /** 키가 실제로 놓인 곳. 화면은 고정 문구 대신 이것을 찍는다 (UX U-09). */
  key_dir: string;
  /** 지금 키로 봉인된 값을 가진 프로젝트 이름들 — 키 교체·삭제의 실제 영향 범위. */
  sealed_projects: string[];
}

export interface SecretsResponse {
  public_key_fingerprint: string | null;
  fingerprint_matches_key: boolean;
  names: { name: string; present: boolean }[];
}

/** 되돌릴 수 없는 키 조작의 확인 문구. 서버의 `DESTROY_CONFIRM` 과 같은 값이다. */
export const DESTROY_CONFIRM = "DELETE";

export interface DestroyKeyResult {
  status: KeyStatus;
  purged_secret_count: number;
  project_open: boolean;
}

export const secrets = {
  keyStatus: () => get<KeyStatus>("/api/keys/status"),
  generateKey: (passphrase?: string) =>
    post<KeyStatus>("/api/keys/generate", { passphrase: passphrase ?? null }),
  /** 키를 지운다. 봉인된 값도 함께 사라진다 — 호출 전에 사용자 확인을 받는다. */
  destroyKey: () =>
    del<DestroyKeyResult>("/api/keys", { confirm: DESTROY_CONFIRM, passphrase: null }),
  /** 지우고 다시 만드는 것을 한 번의 확인으로 묶는다. */
  regenerateKey: (passphrase?: string) =>
    post<DestroyKeyResult>("/api/keys/regenerate", {
      confirm: DESTROY_CONFIRM,
      passphrase: passphrase ?? null,
    }),
  list: () => get<SecretsResponse>("/api/secrets"),
  /** 값은 응답에 없다. 공개키만으로 봉인한다 (FR-089b). */
  put: (name: string, value: string) =>
    request<void>(`/api/secrets/${name}`, { method: "PUT", body: JSON.stringify({ value }) }),
  remove: (name: string) => del<void>(`/api/secrets/${name}`),
};

// ─── 사용자 취향 (004) ──────────────────────────────────────────────────────

export const preferences = {
  get: () => get<PreferencesView>("/api/preferences"),
  put: (runPacing: RunPacing) =>
    put<PreferencesView>("/api/preferences", { run_pacing: runPacing }),
};

export const health = () =>
  get<{ status: string; bind: string; project_open: boolean; active_sessions: number }>(
    "/api/health",
  );
