/**
 * 세 화면이 같은 Step 번호를 말한다 (005 T032 · FR-138·SC-216).
 *
 * U-07 의 실측은 이랬다 — 목록 행은 `step 05 실패`, 결과 화면은 `Step 06 실패`. **같은
 * 실행, 같은 Step, 다른 번호.** 사용자는 어느 쪽이 맞는지 알 수 없고, 06 을 고치면 될
 * 것을 05 를 들여다본다.
 *
 * 원인은 한 곳의 오타가 아니라 **8곳이 각자 `index + 1` 을 하고 있던 것**이었다. 한 줄을
 * 고치면 증상은 사라지지만 아홉 번째 자리가 생기면 같은 일이 다시 난다.
 *
 * 그래서 이 파일은 두 층에서 본다.
 *
 * 1. **표시** — 세 화면이 같은 0-기반 인덱스에서 같은 문자열을 낸다
 * 2. **구조** — 그 변환을 하는 곳이 `wording.ts` 하나뿐이다
 *
 * 2번이 없으면 1번은 오늘만 참이다.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ResultView } from "../src/pages/ResultView";
import { TestList } from "../src/pages/TestList";
import { stepLabel } from "../src/lib/wording";
import type { RunResult as RunResultData } from "../src/types/generated/run-result";

/** 실패한 Step 의 0-기반 인덱스. 사용자에게는 `Step 06` 이다. */
const FAILED_INDEX = 5;
const EXPECTED = "Step 06";

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
    failed_step_index: FAILED_INDEX,
    browser: "Playwright · Chromium",
    session_lost: false,
    artifacts: { failure_screenshot: null, console_log: null, network_log: null, trace: null },
    steps: Array.from({ length: 7 }, (_, i) => ({
      step_id: `step-${String(i + 1).padStart(2, "0")}`,
      index: i,
      label: `Step ${i + 1}`,
      outcome:
        i < FAILED_INDEX
          ? ("pass" as const)
          : i === FAILED_INDEX
            ? ("fail" as const)
            : ("not_run" as const),
      duration_ms: 90,
      tab: 0,
      tab_wait_ms: 0,
      element_wait_ms: 0,
      screenshot: null,
      screenshot_note: null,
      error_code: i === FAILED_INDEX ? ("ELEMENT_NOT_READY" as const) : null,
      resolved_candidate: null,
      locator_attempts: [],
      error_message: i === FAILED_INDEX ? "요소를 찾을 수 없습니다" : null,
      candidate_disagreement: [],
    })),
  };
}

function jsonFetch(routes: Record<string, unknown>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const key = Object.keys(routes).find((part) => url.includes(part));
    return new Response(JSON.stringify(key ? routes[key] : {}), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  });
}

// ─── 1. 표시 ───────────────────────────────────────────────────────────────

describe("같은 실패가 세 곳에서 같은 번호로 보인다 (SC-216)", () => {
  it("사전이 0-기반 5 를 Step 06 으로 바꾼다", () => {
    expect(stepLabel(FAILED_INDEX)).toBe(EXPECTED);
  });

  it("결과 화면이 Step 06 이라고 말한다", async () => {
    vi.stubGlobal("fetch", jsonFetch({ "/result": failedResult() }));
    render(<ResultView testId="TC-002" onRunAll={noop} onRunFrom={noop} onBack={noop} />);

    const shown = await screen.findAllByText(new RegExp(EXPECTED));
    expect(shown.length).toBeGreaterThan(0);
    // 옛 증상 — 1 작은 번호가 어디에도 없다.
    expect(screen.queryByText(/Step 05 실패/)).toBeNull();
    vi.restoreAllMocks();
  });

  it("목록 행이 같은 Step 06 이라고 말한다 (U-07)", async () => {
    vi.stubGlobal(
      "fetch",
      jsonFetch({
        "/api/tests": {
          tests: [
            {
              id: "TC-002",
              name: "실패한 테스트",
              step_count: 7,
              authoring_mode: "record",
              updated_at: "2026-09-07T00:00:00Z",
              last_run_at: "2026-09-07T00:00:03Z",
              outcome: "fail",
              failure_summary: { step_index: FAILED_INDEX, message: "요소를 찾을 수 없습니다" },
            },
          ],
          problems: [],
        },
      }),
    );
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);

    await screen.findByText("실패한 테스트");
    expect(screen.getByText(new RegExp(EXPECTED))).toBeTruthy();
    // U-07 그 자체 — 목록만 1 작았다.
    expect(screen.queryByText(/[Ss]tep 05/)).toBeNull();
    vi.restoreAllMocks();
  });
});

// ─── 2. 구조 ───────────────────────────────────────────────────────────────

// `?raw` 로 원문을 읽는다 (error-notice.test.tsx·DesignTokens.test.tsx 와 같은 방식).
const SOURCES = import.meta.glob("../src/**/*.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const LIB_SOURCES = import.meta.glob("../src/lib/*.ts", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** 주석과 문자열 안의 예시를 빼고 실제 코드만 남긴다. */
function code(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

describe("Step 번호 변환은 한 곳에서만 일어난다 (FR-138)", () => {
  it("`wording.ts` 밖에서 Step **번호**를 손으로 만들지 않는다", () => {
    // 잡으려는 것은 `Step ${index + 1}` 처럼 **0-기반을 표시로 바꾸는** 조립이다.
    // `Step ${steps.length}개` 같은 **개수** 표기는 변환이 아니므로 대상이 아니다 —
    // 그것까지 막으면 규칙이 실제 결함과 무관해지고 곧 무시된다.
    const patterns = [
      /[Ss]tep\s*\$\{[^}]*\+\s*1/, // `Step ${i + 1}`
      /\bstep\w*[Ii]ndex\s*\+\s*1/, // `stepIndex + 1`, `failedStepIndex + 1`
    ];
    const offenders = Object.entries(SOURCES)
      .filter(([, src]) => patterns.some((re) => re.test(code(src))))
      .map(([path]) => path);

    expect(offenders, `Step 번호를 직접 조립하는 파일: ${offenders.join(", ")}`).toEqual([]);
  });

  it("`stepLabel` 과 `stepNumber` 는 `wording.ts` 에만 정의된다", () => {
    const definers = Object.entries({ ...SOURCES, ...LIB_SOURCES })
      .filter(([, src]) => /export function step(Label|Number)\b/.test(src))
      .map(([path]) => path);

    expect(definers.length).toBe(1);
    expect(definers[0]).toContain("wording.ts");
  });

  it("`padStart(2, \"0\")` 로 번호를 맞추는 곳이 사전 말고는 없다", () => {
    const offenders = Object.entries(SOURCES)
      .filter(([, src]) => /padStart\(\s*2\s*,/.test(code(src)))
      .map(([path]) => path);

    expect(offenders, `번호 자릿수를 직접 맞추는 파일: ${offenders.join(", ")}`).toEqual([]);
  });
});
