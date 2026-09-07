/**
 * 한 화면에 결말 어휘가 하나만 있다 (005 T033 · FR-140·FR-141·SC-222).
 *
 * U-20 의 실측 — 같은 결말을 화면마다 다른 말로 불렀다.
 *
 * | 자리 | 통과 | 실패 |
 * |---|---|---|
 * | 실행 화면 배지 | 「완료」 | 「실패」 |
 * | 실행 화면 요약 바 | `PASS` | `FAIL` |
 * | 목록 칩 | `PASS` | `FAIL` |
 * | 목록 배너 | 「완료」 | 「실패」 |
 *
 * U-19 는 같은 뿌리의 다른 증상이다 — 결말 요약이 **한 화면에 두 번** 나왔다. 얇은 회색
 * 띠와 결말 바에 같은 문장이 동시에 있어서, 사용자는 둘이 다른 것인지 확인하느라 멈췄다.
 *
 * 어휘를 사전 한 곳에 모은 것(`wording.ts`)이 수정이고, 이 파일은 **다시 흩어지지 않는지**
 * 를 본다. 화면 하나를 고치는 테스트가 아니라 규칙을 지키는 테스트다.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RunResult } from "../src/pages/RunResult";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import { outcomeChip, outcomeLabel, runSummary } from "../src/lib/wording";
import type { Outcome, RunResult as RunResultData } from "../src/types/generated/run-result";

const noop = () => undefined;
const ALL_OUTCOMES: Outcome[] = ["pass", "fail", "stopped", "partial_pass"];

function resultWith(outcome: Outcome): RunResultData {
  return {
    test_id: "TC-002",
    outcome,
    started_at: "2026-09-07T00:00:00Z",
    finished_at: "2026-09-07T00:00:03Z",
    total_ms: 3210,
    passed_count: outcome === "pass" ? 7 : 5,
    total_count: 7,
    attempted_count: 7,
    scope: "full",
    start_index: 0,
    stopped_step_index: outcome === "stopped" ? 5 : null,
    failed_step_index: outcome === "fail" || outcome === "partial_pass" ? 5 : null,
    browser: "Playwright · Chromium",
    session_lost: false,
    artifacts: { failure_screenshot: null, console_log: null, network_log: null, trace: null },
    steps: Array.from({ length: 7 }, (_, i) => ({
      step_id: `step-${String(i + 1).padStart(2, "0")}`,
      index: i,
      label: `Step ${i + 1}`,
      outcome: (i < 5 ? "pass" : i === 5 ? "fail" : "not_run") as
        | "pass"
        | "fail"
        | "not_run",
      duration_ms: 90,
      tab: 0,
      tab_wait_ms: 0,
      element_wait_ms: 0,
      error_code: null,
      resolved_candidate: null,
      locator_attempts: [],
      error_message: null,
      candidate_disagreement: [],
    })),
  };
}

/** 주석을 뺀 실제 코드. 주석 안의 "이전에는 `PASS`/`FAIL` 이었다" 설명까지 잡지 않는다. */
function code(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
}

function jsonFetch(body: unknown) {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "content-type": "application/json" },
    }),
  );
}

// ─── 사전이 값마다 하나씩만 준다 ────────────────────────────────────────────

describe("결말 하나에 문장 하나·칩 하나 (FR-141)", () => {
  it("네 결말이 서로 다른 문장을 갖는다 — 두 값이 같은 말을 쓰면 구분이 사라진다", () => {
    const labels = ALL_OUTCOMES.map(outcomeLabel);
    expect(new Set(labels).size).toBe(ALL_OUTCOMES.length);
  });

  it("네 결말이 서로 다른 칩을 갖는다", () => {
    const chips = ALL_OUTCOMES.map(outcomeChip);
    expect(new Set(chips).size).toBe(ALL_OUTCOMES.length);
  });

  it("중지는 어디서도 FAIL 로 불리지 않는다 (FR-131·U-03)", () => {
    expect(outcomeChip("stopped")).not.toBe("FAIL");
    expect(outcomeLabel("stopped")).not.toBe("실패");
    const summary = runSummary({
      outcome: "stopped",
      passedCount: 5,
      attemptedCount: 6,
      totalCount: 7,
      stoppedStepIndex: 5,
    });
    expect(summary).not.toContain("실패");
    expect(summary.startsWith("중지")).toBe(true);
  });

  it("부분 성공도 실패로 불리지 않는다 (U-05)", () => {
    const summary = runSummary({
      outcome: "partial_pass",
      passedCount: 6,
      attemptedCount: 6,
      totalCount: 7,
      failedStepIndex: 5,
    });
    expect(summary.startsWith("부분 성공")).toBe(true);
  });
});

// ─── 한 화면에 요약이 한 번 ─────────────────────────────────────────────────

describe("결말 요약은 한 화면에 한 번만 나온다 (FR-140·U-19)", () => {
  it.each(ALL_OUTCOMES)("결과 화면 — %s", async (outcome) => {
    vi.stubGlobal("fetch", jsonFetch(resultWith(outcome)));
    const view = render(
      <RunResult testId="TC-002" onRunAll={noop} onRunFrom={noop} onBack={noop} />,
    );

    const chip = outcomeChip(outcome);
    await screen.findAllByText(chip);

    // 결말 요약 자리가 **정확히 하나**다. `<= 1` 로 두면 자리가 아예 없을 때도
    // 통과해 버려 U-19 의 재발을 잡지 못한다.
    const summaries = view.container.querySelectorAll("[data-run-summary]");
    expect(summaries.length).toBe(1);
    expect(summaries[0]?.textContent).toContain(outcomeLabel(outcome));

    vi.restoreAllMocks();
    view.unmount();
  });

  /**
   * T123 — **세션 국면도 같은 규칙을 지킨다.**
   *
   * 007 이전에는 결말 요약을 그릴 수 있는 자리가 둘이었다 — 정보 배너와, 페이지가
   * 스스로 그리는 결말 표시(`Runner` 의 결말 바 / `RunnerPaused` 의 결말 블록). 배너의
   * 조건이 `!isDone` 하나였고 **멈추기 전에 실행이 끝난 세션은 `paused`** 이므로
   * `isDone` 이 거짓이다. 그래서 배너와 결말 블록이 같은 문장을 나란히 그렸다.
   *
   * 통합 뒤에는 요약을 그릴 수 있는 자리가 **구조적으로 하나뿐이다** — 국면 띠의
   * `data-run-summary` (FR-218d). 조건을 원문에서 확인하는 대신 **세어서** 본다.
   */
  it.each([
    ["끝난 실행", "completed"],
    ["멈추기 전에 끝난 실행", "paused"],
    ["중지 후 검토", "review"],
  ] as const)("세션 국면 — %s 에서도 결말 요약은 하나다 (T123)", (_name, state) => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state }),
          summary: "실패 · Step 06 에서 실패 · 5 / 7 통과",
          failure: { index: 5, message: "요소를 찾을 수 없습니다" },
        })}
      />,
    );
    expect(document.querySelectorAll("[data-run-summary]")).toHaveLength(1);
  });
});

// ─── 어휘가 다시 흩어지지 않는다 ────────────────────────────────────────────

const SOURCES = import.meta.glob("../src/**/*.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

describe("결말 어휘는 사전에서만 나온다 (FR-141·SC-222)", () => {
  it("화면이 결말 칩 문자열을 직접 쓰지 않는다", () => {
    const offenders = Object.entries(SOURCES)
      .filter(([, src]) => /"(PASS|FAIL|STOPPED|PARTIAL)"/.test(code(src)))
      .map(([path]) => path);

    expect(
      offenders,
      `결말 칩을 직접 적은 파일: ${offenders.join(", ")} — wording.ts 의 outcomeChip() 을 쓴다`,
    ).toEqual([]);
  });

  it("화면이 결말을 두 값으로 가르지 않는다", () => {
    // `outcome === "pass" ? … : …` 는 나머지 셋을 한 덩어리로 뭉갠다. 그것이 중지를
    // 실패로 보이게 한 형태다 (U-03).
    const offenders = Object.entries(SOURCES)
      .filter(([, src]) => /\boutcome\s*===\s*"pass"\s*\?/.test(code(src)))
      .map(([path]) => path);

    expect(
      offenders,
      `결말을 이분법으로 가른 파일: ${offenders.join(", ")} — 네 값을 모두 다뤄야 한다`,
    ).toEqual([]);
  });

  it("`outcomeLabel`·`outcomeChip`·`outcomeTone` 은 `wording.ts` 에만 정의된다", () => {
    const LIB = import.meta.glob("../src/lib/*.ts", {
      query: "?raw",
      import: "default",
      eager: true,
    }) as Record<string, string>;

    for (const fn of ["outcomeLabel", "outcomeChip", "outcomeTone"]) {
      const definers = Object.entries({ ...SOURCES, ...LIB })
        .filter(([, src]) => new RegExp(`export function ${fn}\\b`).test(src))
        .map(([path]) => path);
      expect(definers.length, `${fn} 정의가 ${definers.length} 곳이다`).toBe(1);
      expect(definers[0]).toContain("wording.ts");
    }
  });
});
