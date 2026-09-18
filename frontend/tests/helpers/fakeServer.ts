/**
 * 앱 전체를 그리는 검사의 가짜 서버 (018 — `EditEntryPoints.test.tsx` 에서 옮겼다).
 *
 * 006 이 「이 라운드가 부르는 모든 경로를 아는 가짜 서버」로 만든 것을 라우팅 검사도 쓴다. 옮기며
 * 더한 것은 옵션뿐이다 — 열린 프로젝트가 없는 경우, 프로젝트 조회가 늦는 경우, 세션의 모습, 초안.
 * 요청마다 **헤더도** 적는다 — 프로젝트 조회보다 먼저 나간 요청은 프로젝트 헤더가 없다 (018 §3.2).
 */
import { vi } from "vitest";

import type { SessionView } from "../../src/api/client";
import { sessionView } from "./workbench";

export const PROJECT = { name: "P", root: "/tmp/p", default_start_url: "http://t/" };

const verified = (value: string) => ({ value, status: "verified" });

export const STEP_01 = {
  id: "step-01",
  type: "navigate",
  label: "로그인 화면",
  author: "human",
  tab: 0,
  timeout_ms: 5000,
  frame_url: null,
  url: "http://t/login.html",
};

export const STEP_02 = {
  id: "step-02",
  type: "click",
  label: "대시보드 열기",
  author: "human",
  tab: 0,
  timeout_ms: 20000,
  frame_url: null,
  target: {
    tag: "button",
    test_id: verified("dashboard-open"),
    role: null,
    accessible_name: null,
    role_status: null,
    label: null,
    text: null,
    stable_attr: null,
    css: verified("#open"),
  },
};

export const TEST = {
  dsl_version: 1,
  id: "TC-001",
  name: "로그인",
  authoring_mode: "record",
  start_url: "http://t/login.html",
  browser: "chromium",
  ai_instruction: null,
  variables: [],
  steps: [STEP_01, STEP_02],
  created_at: "2026-09-07T00:00:00Z",
  updated_at: "2026-09-07T00:00:00Z",
};

export const LIST = {
  counts: { total: 1, pass: 0, fail: 1 },
  tests: [
    {
      id: "TC-001",
      name: "로그인",
      step_count: 2,
      authoring_mode: "record",
      outcome: "fail",
      last_run_at: "2026-09-07T00:00:00Z",
      failure_summary: { step_index: 1, message: "요소를 찾을 수 없습니다" },
    },
  ],
  problems: [],
};

export const RESULT = {
  test_id: "TC-001",
  outcome: "fail",
  scope: "full",
  started_at: "2026-09-07T00:00:00Z",
  finished_at: "2026-09-07T00:00:02Z",
  duration_ms: 2000,
  total_steps: 2,
  passed_steps: 1,
  failed_step_index: 1,
  stopped_step_index: null,
  start_index: 0,
  steps: [
    {
      step_id: "step-01",
      index: 0,
      outcome: "pass",
      duration_ms: 500,
      error: null,
      locator_attempts: [],
    },
    {
      step_id: "step-02",
      index: 1,
      outcome: "fail",
      duration_ms: 1500,
      locator_attempts: [],
      error: {
        code: "ELEMENT_NOT_READY",
        category: "blocked",
        message: "기다렸지만 요소가 나타나지 않았습니다.",
        next_action: "대기 시간을 늘리세요.",
        detail: {},
      },
    },
  ],
  artifacts: [],
  last_full_run: null,
};

export const DEFINITION_VIEW = {
  test: TEST,
  revision: "rev-1",
  editable: true,
  blocked_by: null,
  blocking_session_id: null,
  locked_fields: [
    { field: "steps[].target", reason: "live_browser_required" },
    { field: "steps[].type", reason: "delete_and_insert_instead" },
  ],
  warnings: [],
};

const NO_KEYS = {
  private_key_present: false,
  public_key_present: false,
  passphrase_protected: false,
  public_key_fingerprint: null,
  permission_warning: null,
  key_dir: "/tmp/itb-test/keys",
  sealed_projects: [],
  unlocked: true,
};

export interface FakeServerOptions {
  /** `null` 이면 열린 프로젝트가 없다 — `GET /api/project` 가 404 다. */
  project?: typeof PROJECT | null;
  /** 프로젝트 조회 응답을 이만큼 늦춘다 (ms). */
  projectDelayMs?: number;
  /** `GET /api/sessions/{id}` 와 세션 하위 경로가 돌려줄 세션에 덮어쓸 값. */
  session?: Partial<SessionView>;
  /** `GET /api/drafts/{id}` 의 응답. 여기 없는 식별자는 404 다. */
  drafts?: Record<string, unknown>;
  /** 이미 끝나 서버가 모르는 세션. `GET /api/sessions/{id}` 가 404 다. */
  missingSessions?: string[];
}

export interface FakeCall {
  url: string;
  method: string;
  body: unknown;
  headers: Record<string, string>;
}

const notFound = (code: string) => ({
  error: { code, category: "blocked", message: "찾을 수 없습니다", next_action: "목록에서 다시 고르세요", detail: {} },
});

/** 이 라운드가 부르는 모든 경로를 아는 가짜 서버. 요청을 기록해 돌려준다. */
export function stubServer(options: FakeServerOptions = {}): FakeCall[] {
  const calls: FakeCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url);
      const method = init?.method ?? "GET";
      calls.push({
        url: u,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : null,
        headers: (init?.headers ?? {}) as Record<string, string>,
      });
      const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

      if (u === "/api/project") {
        if (options.projectDelayMs) await new Promise((r) => setTimeout(r, options.projectDelayMs));
        return options.project === null
          ? json(notFound("PROJECT_NOT_OPEN"), 404)
          : json(options.project ?? PROJECT);
      }
      if (u === "/api/project/list") return json({ projects: [], warning: null });
      if (u === "/api/keys/status") return json(NO_KEYS);
      if (u === "/api/secrets") {
        return json({ public_key_fingerprint: null, fingerprint_matches_key: true, names: [] });
      }
      if (u.startsWith("/api/drafts/")) {
        const id = decodeURIComponent(u.slice("/api/drafts/".length));
        const draft = options.drafts?.[id];
        return draft === undefined ? json(notFound("DRAFT_NOT_FOUND"), 404) : json(draft);
      }
      /* ── 여기부터 EditEntryPoints 의 원래 분기 그대로 ── */
      if (u.startsWith("/api/tests/TC-001/definition")) return json(DEFINITION_VIEW);
      if (u.startsWith("/api/tests/TC-001/result")) return json(RESULT);
      if (u.startsWith("/api/tests")) return json(LIST);
      if (u === "/api/sessions") {
        if (method === "POST") {
          // 007 T004 — 손으로 조립하지 않고 팩토리를 쓴다. 이전에는 여기서
          // `recorder_warnings` 등이 빠져 `SessionScreen` 이 렌더 중에 터졌고, 그
          // 오류가 **테스트가 통과하는 채로** 콘솔로만 흘러나왔다
          // (design-conformance/baseline.md 의 미처리 오류 2건).
          return json(
            sessionView({
              session_id: "s-new",
              state: "paused",
              state_label: "일시정지",
              test_id: "TC-001",
              authoring_mode: "record",
              steps: [STEP_01, STEP_02] as unknown as SessionView["steps"],
              current_step_index: 1,
            }),
            201,
          );
        }
        return json({ sessions: [] });
      }
      const sessionId = u.startsWith("/api/sessions/") ? u.slice("/api/sessions/".length).split("/")[0]! : null;
      if (sessionId !== null && options.missingSessions?.includes(sessionId)) {
        return json(notFound("SESSION_NOT_FOUND"), 404);
      }
      // 007 T004 — 세션 하위 경로도 세션 뷰를 돌려준다. 이전에는 `run-from` 이
      // 아래 `{ ok: true }` 로 떨어져 `SessionScreen` 이 세션 아닌 것을 받았고,
      // 그것이 baseline.md 의 미처리 오류 나머지 1건이었다.
      if (u.startsWith("/api/sessions/")) {
        return json(
          sessionView({
            session_id: "s-new",
            state: "replaying",
            state_label: "실행 중",
            test_id: "TC-001",
            steps: [STEP_01, STEP_02] as unknown as SessionView["steps"],
            current_step_index: 1,
            run_scope: "partial",
            run_start_index: 1,
            // 018 — 라우팅 검사가 세션의 모습을 정한다.
            ...options.session,
          }),
        );
      }
      if (u.startsWith("/api/preferences")) return json({ run_pacing: "normal" });
      return json({ ok: true });
    }),
  );
  return calls;
}
