/**
 * RunResult 화면 테스트 (T089).
 *
 * 요약 3항목·Step 결과·실패 상세·재실행 두 갈래·`TRACE` 비활성을 고정한다
 * (FR-050~FR-058, spec 디자인 차이 1).
 *
 * `fetch` 를 대신 세워 REST 계약 형태만 흉내 낸다 — 화면이 무엇을 읽고 어떻게 그리는지가
 * 검증 대상이고, 서버 동작은 백엔드 계약 테스트가 본다.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RunResult } from "../src/pages/RunResult";
import type { RunResult as RunResultData } from "../src/types/generated/run-result";

function failedResult(): RunResultData {
  return {
    test_id: "TC-003",
    outcome: "fail",
    started_at: "2026-09-03T00:00:00Z",
    finished_at: "2026-09-03T00:00:06Z",
    total_ms: 6410,
    passed_count: 4,
    total_count: 5,
    failed_step_index: 4,
    browser: "Playwright · Chromium",
    session_lost: false,
    artifacts: {
      failure_screenshot: ".runs/TC-003/failure.png",
      console_log: ".runs/TC-003/console.log",
      network_log: ".runs/TC-003/network.log",
      trace: null,
    },
    steps: [
      step(0, "로그인", "pass", 421),
      step(1, "데이터 메뉴 이동", "pass", 302),
      step(2, "파일 선택", "pass", 581),
      step(3, "업로드 이름 입력", "pass", 103),
      {
        ...step(4, "저장", "fail", 5000),
        error_message: '"저장" 버튼을 찾을 수 없습니다.',
        locator_attempts: [
          attempt("test_id", "testId=save-dataset", 5000),
          attempt("role", 'role=button name="저장"', 0),
          attempt("text", 'text="저장"', 0),
        ],
      },
    ],
  };
}

function step(
  index: number,
  label: string,
  outcome: "pass" | "fail",
  durationMs: number,
): RunResultData["steps"][number] {
  return {
    step_id: `step-0${index + 1}`,
    index,
    label,
    outcome,
    duration_ms: durationMs,
    tab: 0,
    tab_wait_ms: 0,
    resolved_candidate: outcome === "pass" ? "test_id" : null,
    locator_attempts: [],
    error_message: null,
    candidate_disagreement: [],
  };
}

function attempt(candidate: string, expression: string, waitedMs: number) {
  return { candidate, expression, matched: false, match_count: 0, waited_ms: waitedMs };
}

function stubFetch(result: RunResultData) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/result")) {
      return Promise.resolve(
        new Response(JSON.stringify(result), { status: 200 }),
      );
    }
    if (url.includes("/artifacts/trace")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            error: { code: "NOT_SUPPORTED", message: "지원하지 않습니다.", detail: {} },
          }),
          { status: 501 },
        ),
      );
    }
    if (url.includes("/artifacts/")) {
      // 서버는 산출물 **본문**을 돌려준다 — 경로 JSON 이 아니다 (UX U-03).
      const kind = url.split("/artifacts/")[1];
      return Promise.resolve(new Response(`${kind} 기록 첫 줄`, { status: 200 }));
    }
    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

const noop = () => undefined;

afterEach(() => {
  vi.restoreAllMocks();
});

describe("RunResult", () => {
  it("요약 3항목을 보여준다 (FR-050)", async () => {
    vi.stubGlobal("fetch", stubFetch(failedResult()));
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );

    expect(await screen.findByText("6.41 s")).toBeDefined();
    expect(screen.getByText("4 / 5")).toBeDefined();
    // "05" 는 Step 목록의 행 번호에도 나온다. 요약 칸 안에서만 찾는다.
    const stoppedCell = screen.getByText("멈춘 STEP").parentElement;
    expect(stoppedCell?.textContent).toContain("05");
  });

  it("실행한 브라우저를 표시한다 (FR-058)", async () => {
    vi.stubGlobal("fetch", stubFetch(failedResult()));
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );
    expect(await screen.findByText("Playwright · Chromium")).toBeDefined();
  });

  it("Step별 결과와 소요 시간을 보여준다 (FR-051)", async () => {
    vi.stubGlobal("fetch", stubFetch(failedResult()));
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );
    expect(await screen.findByText("로그인")).toBeDefined();
    expect(screen.getByText("421 ms")).toBeDefined();
    expect(screen.getByText("5000 ms")).toBeDefined();
  });

  it("실패 이유와 시도한 후보를 우선순위 순으로 보여준다 (FR-054·FR-021)", async () => {
    vi.stubGlobal("fetch", stubFetch(failedResult()));
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );

    expect(await screen.findByText('"저장" 버튼을 찾을 수 없습니다.')).toBeDefined();
    expect(screen.getByText("시도한 LOCATOR (우선순위 순)")).toBeDefined();
    expect(screen.getByText("testId=save-dataset")).toBeDefined();
    expect(screen.getByText('role=button name="저장"')).toBeDefined();
    expect(screen.getByText("timeout 5000 ms")).toBeDefined();
  });

  it("TRACE 탭은 비활성이다 (spec 디자인 차이 1)", async () => {
    vi.stubGlobal("fetch", stubFetch(failedResult()));
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );

    const trace = (await screen.findByText("TRACE")).closest("button");
    expect(trace).not.toBeNull();
    expect((trace as HTMLButtonElement).disabled).toBe(true);
  });

  it("실패한 Step부터 / 처음부터 두 갈래로 재실행한다 (FR-055)", async () => {
    vi.stubGlobal("fetch", stubFetch(failedResult()));
    const onRunFrom = vi.fn();
    const onRunAll = vi.fn();
    render(
      <RunResult
        testId="TC-003"
        onRunAll={onRunAll}
        onRunFrom={onRunFrom}
        onBack={noop}
      />,
    );

    await userEvent.click(await screen.findByText("실패한 Step부터 실행"));
    expect(onRunFrom).toHaveBeenCalledWith("TC-003", 4);

    await userEvent.click(screen.getByText("처음부터 실행"));
    expect(onRunAll).toHaveBeenCalledWith("TC-003");
  });

  it("실패한 Step 상세로 이동할 수 있다 (FR-056)", async () => {
    vi.stubGlobal("fetch", stubFetch(failedResult()));
    const onEditStep = vi.fn();
    render(
      <RunResult
        testId="TC-003"
        onRunAll={noop}
        onRunFrom={noop}
        onEditStep={onEditStep}
        onBack={noop}
      />,
    );

    await userEvent.click(await screen.findByText("Step 05 고치기"));
    expect(onEditStep).toHaveBeenCalledWith("TC-003", "step-05");
  });

  it("통과한 실행에는 '실패한 Step부터 실행' 이 없다", async () => {
    const passed: RunResultData = {
      ...failedResult(),
      outcome: "pass",
      failed_step_index: null,
      passed_count: 5,
      steps: failedResult().steps.map((s) => ({ ...s, outcome: "pass" as const })),
    };
    vi.stubGlobal("fetch", stubFetch(passed));
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );

    await screen.findByText("처음부터 실행");
    expect(screen.queryByText("실패한 Step부터 실행")).toBeNull();
  });

  it("세션 유실로 끝난 실행은 이어서 실행이 불가함을 알린다 (FR-041c)", async () => {
    vi.stubGlobal("fetch", stubFetch({ ...failedResult(), session_lost: true }));
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );
    expect(
      await screen.findByText(/처음부터 다시 실행해야 합니다/),
    ).toBeDefined();
  });

  it("산출물 탭을 바꾸면 그 종류를 요청한다 (FR-052·FR-053)", async () => {
    const fetchStub = stubFetch(failedResult());
    vi.stubGlobal("fetch", fetchStub);
    render(
      <RunResult testId="TC-003" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );

    await userEvent.click(await screen.findByText("CONSOLE"));
    await waitFor(() => {
      const requested = fetchStub.mock.calls.map((c) => String(c[0]));
      expect(requested.some((u) => u.endsWith("/artifacts/console"))).toBe(true);
    });
  });
});
