/**
 * 실행 트리거 (005 T016·T017 · FR-127·FR-129·FR-130).
 *
 * 리포트의 실측을 그대로 고정한다.
 *
 * - 「처음부터 실행」을 52 ms 안에 5회 클릭했더니 `POST /api/sessions` **5건**이 나가고
 *   그중 2건이 201 이었다 — 실제 브라우저 창 두 개가 떴다 (U-06)
 * - 클릭 후 0.2초에 화면이 **완전히 그대로**였다. 버튼 상태도, 진행 표시도, 문구도
 *   없었다 (U-11) — 그래서 사용자가 다시 눌렀고 위 결함으로 직결됐다
 * - 결과가 FAIL 인 행은 「실행」이 「결과 보기」로 **바뀌어** 목록에서 재실행할 수
 *   없었다 (U-12). 통과한 실행은 결과를 열 길이 없었다 (U-13)
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RunResult } from "../src/pages/RunResult";
import { TestList } from "../src/pages/TestList";
import type { RunResult as RunResultData } from "../src/types/generated/run-result";

const noop = () => undefined;

function failedResult(): RunResultData {
  return {
    test_id: "TC-002",
    outcome: "fail",
    started_at: "2026-09-07T00:00:00Z",
    finished_at: "2026-09-07T00:00:03Z",
    total_ms: 3210,
    passed_count: 5,
    total_count: 7,
    attempted_count: 7,
    scope: "full",
    start_index: 0,
    stopped_step_index: null,
    failed_step_index: 5,
    browser: "Playwright · Chromium",
    session_lost: false,
    artifacts: { failure_screenshot: null, console_log: null, network_log: null, trace: null },
    steps: Array.from({ length: 7 }, (_, i) => ({
      step_id: `step-${String(i + 1).padStart(2, "0")}`,
      index: i,
      label: `Step ${i + 1}`,
      outcome: i < 5 ? ("pass" as const) : i === 5 ? ("fail" as const) : ("not_run" as const),
      duration_ms: 90,
      tab: 0,
      tab_wait_ms: 0,
      element_wait_ms: 0,
      error_code: i === 5 ? ("ELEMENT_NOT_FOUND" as const) : null,
      resolved_candidate: null,
      locator_attempts: [],
      error_message: i === 5 ? "요소를 찾을 수 없습니다" : null,
      candidate_disagreement: [],
    })),
  };
}

function mockResultFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/result")) {
      return new Response(JSON.stringify(failedResult()), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("결과 화면의 실행 버튼 (US1)", () => {
  it("실패 지점부터 실행 라벨에 시작 Step 번호가 있다 (FR-149·U-02)", async () => {
    vi.stubGlobal("fetch", mockResultFetch());
    render(<RunResult testId="TC-002" onRunAll={noop} onRunFrom={noop} onBack={noop} />);

    // 실패 인덱스 5 → 사용자에게는 Step 06.
    const button = await screen.findByRole("button", { name: /Step 06부터 실행/ });
    expect(button).toBeTruthy();
    // 어디서 시작하는지 말하지 않던 옛 라벨은 없다.
    expect(screen.queryByRole("button", { name: "실패한 Step부터 실행" })).toBeNull();
  });

  it("누르기 전에 건너뛰는 구간과 선행 상태를 알린다 (FR-150·U-02)", async () => {
    vi.stubGlobal("fetch", mockResultFetch());
    render(<RunResult testId="TC-002" onRunAll={noop} onRunFrom={noop} onBack={noop} />);

    await screen.findByRole("button", { name: /Step 06부터 실행/ });
    expect(screen.getByText(/01~05 는 건너뜁니다/)).toBeTruthy();
    expect(screen.getByText(/처음부터 실행」을 쓰세요/)).toBeTruthy();
  });

  it("실행 요청 중에는 두 버튼이 비활성이고 준비 문구를 말한다 (FR-127·FR-129·SC-214)", async () => {
    vi.stubGlobal("fetch", mockResultFetch());
    render(
      <RunResult testId="TC-002" onRunAll={noop} onRunFrom={noop} onBack={noop} runPending />,
    );

    await waitFor(() => {
      const buttons = screen.getAllByRole("button", { name: /실행을 준비하는 중/ });
      // 「처음부터 실행」과 「Step 06부터 실행」 둘 다 잠긴다.
      expect(buttons.length).toBe(2);
      for (const b of buttons) expect((b as HTMLButtonElement).disabled).toBe(true);
    });
  });

  it("연타해도 실행 요청은 한 번만 나간다 (FR-127·SC-213·U-06)", async () => {
    vi.stubGlobal("fetch", mockResultFetch());
    const onRunAll = vi.fn();
    // 부모(App)의 in-flight 가드를 흉내 낸다 — 첫 호출 뒤 runPending 이 참이 된다.
    const { rerender } = render(
      <RunResult testId="TC-002" onRunAll={onRunAll} onRunFrom={noop} onBack={noop} />,
    );
    const button = await screen.findByRole("button", { name: "처음부터 실행" });

    await userEvent.click(button);
    rerender(
      <RunResult testId="TC-002" onRunAll={onRunAll} onRunFrom={noop} onBack={noop} runPending />,
    );
    const locked = screen.getAllByRole("button", { name: /실행을 준비하는 중/ })[0];
    await userEvent.click(locked).catch(() => undefined);
    await userEvent.click(locked).catch(() => undefined);

    expect(onRunAll).toHaveBeenCalledTimes(1);
  });
});

describe("목록 행의 실행·결과 도달 (US1 · FR-130)", () => {
  function listFetch(rows: unknown[]) {
    return vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/tests") && !url.includes("/result")) {
        return new Response(JSON.stringify({ tests: rows, problems: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
    });
  }

  const baseRow = {
    id: "TC-002",
    name: "실패한 테스트",
    step_count: 7,
    authoring_mode: "record",
    updated_at: "2026-09-07T00:00:00Z",
    last_run_at: "2026-09-07T00:00:03Z",
    failure_summary: null,
  };

  it("실패한 행에서도 「실행」에 도달한다 (U-12)", async () => {
    vi.stubGlobal("fetch", listFetch([{ ...baseRow, outcome: "fail" }]));
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);

    await screen.findByText("실패한 테스트");
    expect(screen.getByRole("button", { name: /실행/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: "결과 보기" })).toBeTruthy();
  });

  it("통과한 행에서도 「결과 보기」에 도달한다 (U-13)", async () => {
    vi.stubGlobal("fetch", listFetch([{ ...baseRow, id: "TC-003", outcome: "pass" }]));
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);

    await screen.findByText("실패한 테스트");
    expect(screen.getByRole("button", { name: "결과 보기" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /실행/ })).toBeTruthy();
  });

  it("중지·부분 성공 결말에서도 두 경로가 모두 있다 (FR-130)", async () => {
    for (const outcome of ["stopped", "partial_pass"] as const) {
      vi.stubGlobal("fetch", listFetch([{ ...baseRow, outcome }]));
      const view = render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
      await screen.findByText("실패한 테스트");
      expect(screen.getByRole("button", { name: "결과 보기" })).toBeTruthy();
      expect(screen.getByRole("button", { name: /실행/ })).toBeTruthy();
      view.unmount();
    }
  });

  it("한 번도 실행하지 않은 행에는 결과 보기를 두지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      listFetch([{ ...baseRow, outcome: null, last_run_at: null }]),
    );
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);

    await screen.findByText("실패한 테스트");
    expect(screen.queryByRole("button", { name: "결과 보기" })).toBeNull();
  });

  it("실행 요청 중인 행은 「준비 중…」으로 잠긴다 (FR-129·U-11)", async () => {
    vi.stubGlobal("fetch", listFetch([{ ...baseRow, outcome: "fail" }]));
    render(
      <TestList onCreate={noop} onOpenResult={noop} onRun={noop} pendingRunId="TC-002" />,
    );

    await screen.findByText("실패한 테스트");
    const button = screen.getByRole("button", { name: "준비 중…" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
});
