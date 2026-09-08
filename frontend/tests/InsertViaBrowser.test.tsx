/**
 * 009 T040 — 「이 앞에 추가」 한 조작 (US2 · FR-291~FR-297).
 *
 * **이 파일이 지키는 것은 셋이다.**
 *
 * 1. 조작 하나로 「저장 → 세션 생성(목표 지정)」이 일어난다 — 사용자가 조립하지 않는다.
 * 2. 재생 중 **목표와 현재를 함께** 말하고, 도달하지 못한 실패를 도달과 구별한다.
 * 3. 결과 화면의 「고치기」가 그 Step 을 고른 상태로 편집 화면을 넘긴다.
 */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditView } from "../src/pages/EditView";
import { renderSession } from "./helpers/session";
import type { Step } from "../src/types/generated/step";

const verified = (value: string) => ({ value, status: "verified" });

const STEPS = [
  {
    id: "step-01",
    type: "navigate",
    label: "로그인 화면",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    url: "/login",
  },
  {
    id: "step-02",
    type: "click",
    label: "로그인 클릭",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    target: {
      tag: "button",
      test_id: verified("login-submit"),
      role: null,
      accessible_name: null,
      role_status: null,
      label: null,
      text: null,
      stable_attr: null,
      css: verified("button#submit"),
    },
  },
  {
    id: "step-03",
    type: "assertion",
    label: "환영 문구",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    assertion: { kind: "text", target: null, match: "contains", value: "환영" },
  },
];

const TEST = {
  dsl_version: 1,
  id: "TC-001",
  name: "로그인",
  authoring_mode: "record",
  start_url: "/login",
  browser: "chromium",
  ai_instruction: null,
  variables: [],
  steps: STEPS,
  created_at: "2026-09-08T00:00:00Z",
  updated_at: "2026-09-08T00:00:00Z",
};

function definitionView(overrides: Record<string, unknown> = {}) {
  return {
    test: TEST,
    revision: "rev-1",
    editable: true,
    blocked_by: null,
    blocking_session_id: null,
    locked_fields: [],
    warnings: [],
    ...overrides,
  };
}

function stubFetch() {
  const calls: { url: string; method: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      calls.push({ url: String(url), method, body });
      if (method === "PUT") {
        return new Response(JSON.stringify({ ...definitionView(), revision: "rev-2" }), {
          status: 200,
        });
      }
      if (String(url).includes("/api/sessions") && method === "POST") {
        return new Response(JSON.stringify({ session_id: "sess-9" }), { status: 201 });
      }
      return new Response(JSON.stringify(definitionView()), { status: 200 });
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

const action = (id: string) =>
  document.querySelector(`button[data-action="${id}"]`) as HTMLButtonElement;

function selectStep(stepId: string) {
  const row = document.querySelector(`[data-step-row="${stepId}"] button`) as HTMLButtonElement;
  act(() => row.click());
}

// ─── 1. 한 조작으로 저장하고 목표를 지정해 세션을 연다 (FR-291·FR-292) ──────

describe("「이 앞에 추가」 한 조작 (FR-291)", () => {
  it("고친 것이 없으면 곧바로 그 자리를 목표로 세션을 연다", async () => {
    stubFetch();
    const onOpenBrowserAt = vi.fn();
    render(
      <EditView testId="TC-001" onBack={() => undefined} onOpenBrowserAt={onOpenBrowserAt} />,
    );
    await waitFor(() => expect(screen.getByText("로그인 화면")).toBeTruthy());

    selectStep("step-03");
    act(() => action("browser.openAt").click());

    await waitFor(() => expect(onOpenBrowserAt).toHaveBeenCalled());
    const [testId, stepIndex, stepId] = onOpenBrowserAt.mock.calls[0]!;
    expect(testId).toBe("TC-001");
    // 그 Step **앞에서** 멈춘다 — 인덱스가 곧 목표다.
    expect(stepIndex).toBe(2);
    expect(stepId).toBe("step-03");
  });

  it("미저장 변경이 있으면 **먼저 저장한다는 사실이 누르기 전에** 보인다 (FR-292)", async () => {
    stubFetch();
    render(
      <EditView testId="TC-001" onBack={() => undefined} onOpenBrowserAt={() => undefined} />,
    );
    await waitFor(() => expect(screen.getByText("로그인 화면")).toBeTruthy());

    // 이름을 바꿔 미저장 변경을 만든다.
    fireEvent.change(screen.getByLabelText("테스트 이름"), { target: { value: "고친 이름" } });

    expect(
      screen.getByText(/저장한 뒤 브라우저를 엽니다|먼저 저장/),
      "저장이 먼저 일어난다는 사실이 누르기 전에 보이지 않는다",
    ).toBeTruthy();
  });

  it("미저장 변경이 있으면 저장이 **먼저** 나가고 그다음 세션이 열린다 (FR-292)", async () => {
    const calls = stubFetch();
    const onOpenBrowserAt = vi.fn();
    render(
      <EditView testId="TC-001" onBack={() => undefined} onOpenBrowserAt={onOpenBrowserAt} />,
    );
    await waitFor(() => expect(screen.getByText("로그인 화면")).toBeTruthy());

    fireEvent.change(screen.getByLabelText("테스트 이름"), { target: { value: "고친 이름" } });
    selectStep("step-02");
    act(() => action("browser.openAt").click());

    await waitFor(() => expect(onOpenBrowserAt).toHaveBeenCalled());
    // 저장이 먼저다 — 두 경로가 다른 목록을 들고 있는 상태를 만들지 않는다 (006 FR-203).
    expect(calls.some((c) => c.method === "PUT")).toBe(true);
  });
});

// ─── 2. 진행과 도달 전 실패 (FR-293·FR-294) ─────────────────────────────────

describe("목표 지점 표시 (FR-293·FR-294)", () => {
  it("재생 중 목표와 현재를 함께 말한다", () => {
    renderSession({
      steps: STEPS as unknown as Step[],
      current_step_index: 1,
      pause_before_index: 2,
    });

    expect(screen.getByText(/Step 03 앞에서 멈춥니다/)).toBeTruthy();
    expect(screen.getByText(/지금 Step 02/)).toBeTruthy();
  });

  it("목표가 없으면 보통 진행 표시를 쓴다 — 없는 목표를 지어내지 않는다", () => {
    renderSession({ steps: STEPS as unknown as Step[], current_step_index: 1 });

    expect(screen.queryByText(/앞에서 멈춥니다/)).toBeNull();
  });

  it("도달하기 전에 실패하면 도달과 구별해 말한다 (FR-294)", () => {
    renderSession(
      {
        state: "paused",
        steps: STEPS as unknown as Step[],
        current_step_index: 1,
        pause_before_index: 2,
      },
      // 실패한 Step 을 화면이 아는 방법은 결말이다 — 두 번째가 실패다.
      { outcomeOf: (_s: Step, index: number) => (index === 1 ? "fail" : "pass") },
    );

    expect(screen.getByText(/Step 03 에 도달하기 전에 Step 02 에서 실패했습니다/)).toBeTruthy();
  });

  it("도달했으면 목표가 비고 일시정지 문구가 그대로다", () => {
    renderSession({
      state: "paused",
      steps: STEPS as unknown as Step[],
      current_step_index: 2,
    });

    expect(screen.queryByText(/도달하기 전에/)).toBeNull();
    expect(screen.queryByText(/앞에서 멈춥니다/)).toBeNull();
  });
});

// ─── 3. 결과 화면의 「고치기」 (FR-297) ─────────────────────────────────────

describe("결과 화면에서 그 자리로 (FR-297)", () => {
  it("편집 화면이 넘겨받은 Step 을 고른 상태로 열린다", async () => {
    stubFetch();
    render(
      <EditView testId="TC-001" focusStepId="step-03" onBack={() => undefined} />,
    );
    await waitFor(() => expect(screen.getByText("로그인 화면")).toBeTruthy());

    // 그 행이 골라진 상태다 — 「먼저 Step 을 고르세요」를 다시 하지 않는다.
    const row = document.querySelector('[data-step-row="step-03"] button');
    expect(row?.getAttribute("aria-pressed")).toBe("true");
  });
});

// ─── 009 T063 · 다른 세션이 잡고 있을 때 (US2/AC5 · FR-234) ─────────────────
//
// 이 조작은 그 테스트로 **세션을 만든다.** 이미 잡혀 있으면 만들 수 없고 서버가 409 로
// 거절한다. 활성으로 그리면 누른 뒤 거절되고, 그것이 005 U-01 의 형태다.

describe("다른 세션이 그 테스트를 잡고 있을 때 (US2/AC5)", () => {
  function stubBlocked() {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify(
            definitionView({
              editable: false,
              blocked_by: "running",
              blocking_session_id: "sess-1",
            }),
          ),
          { status: 200 },
        ),
      ),
    );
  }

  it("비활성이고 그 세션으로 가는 방법을 가리킨다", async () => {
    stubBlocked();
    render(
      <EditView testId="TC-001" onBack={() => undefined} onOpenBrowserAt={() => undefined} />,
    );
    await waitFor(() => expect(screen.getByText("로그인 화면")).toBeTruthy());

    const btn = action("browser.openAt");
    expect(btn, "조작이 감춰졌다 — 자리를 남겨야 한다 (FR-234)").toBeTruthy();
    expect(btn.disabled, "활성이다 — 누르면 서버가 409 로 거절한다").toBe(true);
    // 「실행 중인 세션 보기」가 그 방법이다.
    expect(action("session.open")).toBeTruthy();
    expect(action("session.open").disabled).toBe(false);
  });

  it("누를 수 없으므로 세션을 만들지 않는다", async () => {
    stubBlocked();
    const onOpenBrowserAt = vi.fn();
    render(
      <EditView testId="TC-001" onBack={() => undefined} onOpenBrowserAt={onOpenBrowserAt} />,
    );
    await waitFor(() => expect(screen.getByText("로그인 화면")).toBeTruthy());

    act(() => action("browser.openAt").click());

    expect(onOpenBrowserAt).not.toHaveBeenCalled();
  });
});
