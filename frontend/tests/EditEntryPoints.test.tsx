/**
 * 006 T047·T048·T053·T057 — 편집 진입점 (US2 · FR-176·FR-178·FR-180 · SC-304).
 *
 * **이 파일이 지키는 것은 이름과 도착지의 일치다.** 006 이 고친 가장 아픈 것이 그것이었다 —
 * 결과 화면의 「Step 06 고치기」가 **읽기 전용 화면**으로 데려갔다 (E-04). 이름이 「고치기」인
 * 컨트롤이 고칠 수 없는 곳으로 가는 것은 단순한 불편이 아니라 거짓 안내다.
 *
 * 화면 하나를 렌더해 문구를 보는 것으로는 이것을 잡을 수 없다. 그래서 `App` 을 통째로
 * 렌더해 **진입점 → 도착 화면**을 실제로 걷는다.
 */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../src/App";

const PROJECT = { name: "P", root: "/tmp/p", default_start_url: "http://t/" };

const verified = (value: string) => ({ value, status: "verified" });

const STEP_01 = {
  id: "step-01",
  type: "navigate",
  label: "로그인 화면",
  author: "human",
  tab: 0,
  timeout_ms: 5000,
  frame_url: null,
  url: "http://t/login.html",
};

const STEP_02 = {
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

const TEST = {
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

const LIST = {
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

const RESULT = {
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

const DEFINITION_VIEW = {
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

/** 이 라운드가 부르는 모든 경로를 아는 가짜 서버. 세션 생성 요청을 기록한다. */
function stubServer() {
  const calls: { url: string; method: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url);
      const method = init?.method ?? "GET";
      calls.push({
        url: u,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : null,
      });
      const json = (body: unknown, status = 200) =>
        new Response(JSON.stringify(body), { status });

      if (u === "/api/project") return json(PROJECT);
      if (u.startsWith("/api/tests/TC-001/definition")) return json(DEFINITION_VIEW);
      if (u.startsWith("/api/tests/TC-001/result")) return json(RESULT);
      if (u.startsWith("/api/tests")) return json(LIST);
      if (u === "/api/sessions") {
        if (method === "POST") {
          return json(
            {
              session_id: "s-new",
              state: "paused",
              state_label: "일시정지",
              test_id: "TC-001",
              authoring_mode: "record",
              start_url: "http://t/login.html",
              steps: [STEP_01, STEP_02],
              current_step_index: 1,
              pacing: "normal",
              edit_warnings: [],
              saved_at: null,
              has_unsaved_changes: false,
            },
            201,
          );
        }
        return json({ sessions: [] });
      }
      if (u.startsWith("/api/preferences")) return json({ run_pacing: "normal" });
      return json({ ok: true });
    }),
  );
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("편집 진입점 — 이름과 도착지가 일치한다 (SC-304)", () => {
  it("목록 행 메뉴의 「편집」이 편집 가능한 화면으로 데려간다 (FR-175·FR-178)", async () => {
    stubServer();
    render(<App />);
    await waitFor(() => expect(screen.getByText("로그인")).toBeTruthy());

    act(() => screen.getByLabelText("로그인 추가 동작").click());
    act(() => screen.getByText("편집").click());

    // 도착한 화면에서 실제로 고칠 수 있다 — 저장 컨트롤이 있다.
    await waitFor(() => expect(screen.getByText("변경 저장")).toBeTruthy());
    expect(screen.getByLabelText("테스트 이름")).toBeTruthy();
  });

  it("결과 화면의 「Step 02 고치기」가 그 Step 이 펼쳐진 편집 화면으로 간다 (FR-176·FR-180)", async () => {
    stubServer();
    window.history.replaceState({}, "", "/?screen=result&test=TC-001");
    render(<App />);

    await waitFor(() => expect(screen.getByText("Step 02 고치기")).toBeTruthy());
    act(() => screen.getByText("Step 02 고치기").click());

    // 편집 가능한 화면이고, Step 02 가 지목·펼쳐져 있다.
    await waitFor(() => expect(screen.getByText("변경 저장")).toBeTruthy());
    expect(screen.getByText("dashboard-open")).toBeTruthy();
    expect(screen.getByLabelText("Step 대기 시간 (ms)")).toBeTruthy();
  });

  it("편집 화면에 「정의 보기」 같은 읽기 전용 도착지가 없다 (FR-177)", async () => {
    stubServer();
    render(<App />);
    await waitFor(() => expect(screen.getByText("로그인")).toBeTruthy());

    act(() => screen.getByLabelText("로그인 추가 동작").click());
    expect(screen.queryByText("정의 보기")).toBeNull();
  });
});

describe("편집 → 저장 → 재실행 한 바퀴 (US2 · SC-303)", () => {
  it("고쳐 저장한 뒤 그 자리에서 「Step 02부터 실행」을 건다", async () => {
    const calls = stubServer();
    window.history.replaceState({}, "", "/?screen=result&test=TC-001");
    render(<App />);

    await waitFor(() => expect(screen.getByText("Step 02 고치기")).toBeTruthy());
    act(() => screen.getByText("Step 02 고치기").click());
    await waitFor(() => expect(screen.getByLabelText("Step 대기 시간 (ms)")).toBeTruthy());

    fireEvent.change(screen.getByLabelText("Step 대기 시간 (ms)"), {
      target: { value: "5000" },
    });
    await waitFor(() => expect(screen.getByText("변경 저장 (1건)")).toBeTruthy());
    act(() => screen.getByText("변경 저장 (1건)").click());
    await waitFor(() => expect(screen.getByText(/저장했습니다/)).toBeTruthy());

    act(() => screen.getByText("Step 02부터 실행").click());

    // 005 가 만든 단일 실행 경로를 지난다 — 세션 생성 1건 + run-from.
    await waitFor(() => {
      const posts = calls.filter((c) => c.url === "/api/sessions" && c.method === "POST");
      expect(posts).toHaveLength(1);
      expect(posts[0]?.body).toEqual({ mode: "replay", test_id: "TC-001" });
      expect(
        calls.some((c) => c.url.includes("/run-from")),
      ).toBe(true);
    });
  });
});

describe("브라우저 편집 세션 (US3 · FR-200·FR-201 · SC-305)", () => {
  it("「브라우저 열어 Step 02 에서 멈추기」가 pause_before_index 로 세션을 만든다", async () => {
    const calls = stubServer();
    window.history.replaceState({}, "", "/?screen=definition&test=TC-001&step=step-02");
    render(<App />);

    await waitFor(() =>
      expect(screen.getByText("브라우저 열어 Step 02 에서 멈추기")).toBeTruthy(),
    );
    act(() => screen.getByText("브라우저 열어 Step 02 에서 멈추기").click());

    await waitFor(() => {
      const posts = calls.filter((c) => c.url === "/api/sessions" && c.method === "POST");
      expect(posts).toHaveLength(1);
      // 사용자가 「일시정지」를 누른 적이 없다 — 서버가 그 지점에서 멈춰 준다.
      expect(posts[0]?.body).toEqual({
        mode: "replay",
        test_id: "TC-001",
        pause_before_index: 1,
      });
    });
    expect(calls.some((c) => c.url.includes("/pause"))).toBe(false);
  });

  it("주소가 지목한 Step 을 새로고침 뒤에도 펼친다 (FR-181)", async () => {
    stubServer();
    window.history.replaceState({}, "", "/?screen=definition&test=TC-001&step=step-02");
    render(<App />);

    await waitFor(() => expect(screen.getByText("dashboard-open")).toBeTruthy());
  });
});
