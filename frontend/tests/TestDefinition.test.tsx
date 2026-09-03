/**
 * 정의 보기 화면 (T169). FR-016·FR-019.
 *
 * **실행하지 않고 볼 수 있는가**가 이 화면의 존재 이유이므로, 세션을 만들지 않고
 * `GET /api/tests/{id}` 하나로 그려지는지를 본다.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TestDefinition } from "../src/pages/TestDefinition";

const verified = (value: string) => ({ value, status: "verified" });

const DEFINITION = {
  dsl_version: 1,
  id: "TC-001",
  name: "로그인",
  authoring_mode: "ai",
  start_url: "https://example.internal/login",
  browser: "chromium",
  ai_instruction: "로그인해서 프로젝트 화면으로 가",
  variables: [{ name: "LOGIN_PASSWORD", value: null, sensitive: true }],
  steps: [
    {
      id: "step-01",
      type: "fill",
      label: "비밀번호 입력",
      author: "ai",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      value: "{{LOGIN_PASSWORD}}",
      target: {
        tag: "input",
        test_id: null,
        role: null,
        accessible_name: null,
        role_status: null,
        label: verified("비밀번호"),
        text: null,
        stable_attr: null,
        css: verified("input#password"),
      },
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
  ],
  created_at: "2026-09-03T00:00:00Z",
  updated_at: "2026-09-03T00:00:00Z",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(DEFINITION), { status: 200 })),
  );
});

afterEach(() => vi.unstubAllGlobals());

describe("TestDefinition", () => {
  it("세션을 만들지 않고 정의를 그린다 (FR-016)", async () => {
    render(<TestDefinition testId="TC-001" onBack={() => undefined} />);

    await waitFor(() => expect(screen.getByText("로그인")).toBeTruthy());
    expect(screen.getByText("비밀번호 입력")).toBeTruthy();
    expect(screen.getByText("로그인 클릭")).toBeTruthy();

    // 세션 엔드포인트를 부르지 않았다 — 실행 없이 볼 수 있어야 한다.
    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    expect(calls.every(([url]) => !String(url).includes("/api/sessions"))).toBe(true);
  });

  it("민감 값을 표시하지 않고 참조만 보여 준다 (FR-082)", async () => {
    render(<TestDefinition testId="TC-001" onBack={() => undefined} />);
    await waitFor(() => expect(screen.getByText("비밀번호 입력")).toBeTruthy());

    expect(screen.getByText("{{LOGIN_PASSWORD}}")).toBeTruthy();
    expect(screen.getByText(/값은 표시되지 않습니다/)).toBeTruthy();
  });

  it("지시문을 '실행 대상이 아님' 과 함께 보여 준다 (FR-063·FR-064)", async () => {
    render(<TestDefinition testId="TC-001" onBack={() => undefined} />);
    await waitFor(() =>
      expect(screen.getByText("로그인해서 프로젝트 화면으로 가")).toBeTruthy(),
    );
    expect(screen.getByText(/실행 대상이 아닙니다/)).toBeTruthy();
  });

  it("Step 을 고르면 후보 우선순위 표를 보여 준다 (FR-019)", async () => {
    render(<TestDefinition testId="TC-001" onBack={() => undefined} />);
    await waitFor(() => expect(screen.getByText("로그인 클릭")).toBeTruthy());

    // 상태 갱신을 act 로 감싼다 — 감싸지 않으면 React 가 경고하고, 그 경고는 실제
    // 사용자가 보는 동작과 테스트가 어긋날 수 있다는 신호다.
    act(() => screen.getByText("로그인 클릭").click());
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());
    expect(screen.getByText("사용 중")).toBeTruthy();
  });

  it("결과 화면에서 지목한 Step 을 처음부터 펼친다 (FR-056)", async () => {
    render(
      <TestDefinition testId="TC-001" focusStepId="step-02" onBack={() => undefined} />,
    );
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());
  });

  it("다시 집기는 여기서 제공하지 않고 그 이유를 알린다 (FR-020)", async () => {
    render(
      <TestDefinition testId="TC-001" focusStepId="step-02" onBack={() => undefined} />,
    );
    await waitFor(() => expect(screen.getByText("login-submit")).toBeTruthy());

    expect(screen.queryByText("다시 집기")).toBeNull();
    expect(screen.getByText(/살아 있는 브라우저가 필요합니다/)).toBeTruthy();
  });
});
