/**
 * 011 T046 — **결과보기에서 Step 별로 화면을 본다** (UC-011-20·21·22 · FR-390·FR-391·FR-393).
 *
 * ## 사용자 보고
 *
 * > 「각 스텝의 스크린샷 기록이 있어야한다. 결과보기에서는 스크린샷을 스텝별로
 * > 볼수있어야한다」
 *
 * 011 이전에 남는 것은 **실행당 1장**(실패 시점)뿐이었다. 통과한 Step 이 의도한 화면을
 * 만들었는지 확인할 방법이 없었고, 실패 원인이 몇 단계 앞에서 생긴 경우 그 앞을 볼 수
 * 없었다.
 *
 * ## 이 파일이 재는 것
 *
 * **없음의 네 상황이 서로 다른 말을 하는가**가 절반이다 (UC-011-21). 「없습니다」 하나로
 * 뭉개면 사용자는 제품이 못 찍은 것인지 자기가 못 볼 이유가 있는 것인지 알 수 없고,
 * 민감 값 보호가 결함으로 읽힌다.
 *
 * 나머지 절반은 자리다 — 새 영역을 만들지 않고 Step 상세 안에 있으며(20), 기존 표시를
 * 밀어내지 않는다(22).
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MISSING_SHOT_REASON } from "../src/lib/wording";
import { ResultView } from "../src/pages/ResultView";
import { definitionView, runResult, stepResult } from "./helpers/workbench";
import type { StepResult } from "../src/types/generated/run-result";

function stub(steps: StepResult[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(JSON.stringify(definitionView()), { status: 200 });
      }
      if (url.includes("/result")) {
        return new Response(
          JSON.stringify(runResult({ steps, total_count: steps.length })),
          { status: 200 },
        );
      }
      return new Response("본문", { status: 200 });
    }),
  );
}

async function renderResult(steps: StepResult[], focusStepId: string | null = "st-1") {
  stub(steps);
  render(
    <ResultView
      testId="TC-001"
      focusStepId={focusStepId}
      onRunAll={() => undefined}
      onRunFrom={() => undefined}
      onEditStep={() => undefined}
      onBack={() => undefined}
    />,
  );
  await waitFor(() =>
    expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
  );
}

const pane = () => document.querySelector("[data-step-shot]");
const image = () => document.querySelector("[data-step-shot-image]") as HTMLImageElement | null;
const missing = () => document.querySelector("[data-step-shot-missing]");

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/* ─── UC-011-20 — 지목한 Step 의 화면이 상세에 있다 ────────────────────────── */

describe("UC-011-20 — Step 을 고르면 그 Step 의 화면이 보인다", () => {
  it("화면이 있으면 그 Step 의 주소로 그린다", async () => {
    await renderResult([
      stepResult({ step_id: "st-1", index: 0, screenshot: ".runs/TC-001/steps/0.png" }),
    ]);
    expect(pane(), "화면 판이 없다").not.toBeNull();
    expect(image()?.src).toContain("/api/tests/TC-001/result/steps/0/screenshot");
  });

  it("자리는 Step 상세 안이다 — 새 영역을 만들지 않는다", async () => {
    await renderResult([
      stepResult({ step_id: "st-1", index: 0, screenshot: ".runs/TC-001/steps/0.png" }),
    ]);
    const detail = document.querySelector("[data-workbench-detail-layer]");
    expect(detail, "상세가 열리지 않았다").not.toBeNull();
    expect(detail!.contains(pane()!), "화면 판이 상세 밖에 있다").toBe(true);
  });

  it("다른 Step 을 고르면 그 Step 의 화면으로 바뀐다", async () => {
    const user = userEvent.setup();
    await renderResult([
      stepResult({ step_id: "st-1", index: 0, screenshot: ".runs/TC-001/steps/0.png" }),
      stepResult({
        step_id: "st-2",
        index: 1,
        label: "두 번째",
        screenshot: ".runs/TC-001/steps/1.png",
      }),
    ]);
    expect(image()?.src).toContain("/steps/0/screenshot");

    await user.click(screen.getByRole("button", { name: "두 번째" }));
    await waitFor(() => expect(image()?.src).toContain("/steps/1/screenshot"));
  });

  it("접근 가능한 이름이 몇 번째 Step 인지 말한다", async () => {
    await renderResult([
      stepResult({ step_id: "st-1", index: 0, screenshot: ".runs/TC-001/steps/0.png" }),
    ]);
    // 표시 번호는 1-기반이다 (FR-138). 저장·API 인덱스는 0-기반 그대로다.
    expect(image()?.alt).toContain("01");
  });
});

/* ─── UC-011-21 — 없음의 네 상황이 서로 다른 말을 한다 ─────────────────────── */

describe("UC-011-21 — 없으면 사유를 말한다", () => {
  it("서버가 준 사유를 그대로 보여 준다 (민감 값 보호)", async () => {
    await renderResult([
      stepResult({
        step_id: "st-1",
        index: 0,
        screenshot: null,
        screenshot_note: "민감 값이 화면에 있어 남기지 않았습니다",
      }),
    ]);
    expect(missing()?.textContent).toContain("민감 값");
  });

  it("사유가 없으면 분류 문구로 메운다 — 빈 자리를 남기지 않는다", async () => {
    await renderResult([
      stepResult({ step_id: "st-1", index: 0, screenshot: null, screenshot_note: null }),
    ]);
    expect(missing()?.textContent).toBe(MISSING_SHOT_REASON.capture_failed);
  });

  it.each(["skipped", "not_run"] as const)(
    "%s Step 은 판 자체를 그리지 않는다 — 「없다」가 아니라 「해당 없다」다 (FR-393)",
    async (outcome) => {
      await renderResult([
        stepResult({ step_id: "st-1", index: 0, outcome, screenshot: null, screenshot_note: null }),
      ]);
      expect(pane(), `${outcome} 인데 화면 판이 있다`).toBeNull();
    },
  );

  it("실패한 Step 도 화면을 갖는다 — 실패 시점 산출물과 같은 파일이다 (FR-394)", async () => {
    await renderResult([
      stepResult({
        step_id: "st-1",
        index: 0,
        outcome: "fail",
        screenshot: ".runs/TC-001/failure.png",
      }),
    ]);
    expect(image()).not.toBeNull();
  });
});

/* ─── UC-011-22 — 다른 표시를 밀어내지 않는다 ──────────────────────────────── */

describe("UC-011-22 — 기존 표시가 그대로 남는다", () => {
  it("시도한 locator 표와 실패 사유가 함께 보인다", async () => {
    await renderResult([
      stepResult({
        step_id: "st-1",
        index: 0,
        outcome: "fail",
        screenshot: ".runs/TC-001/failure.png",
        error_message: "요소를 찾을 수 없습니다",
        locator_attempts: [
          {
            candidate: "css",
            expression: "#go",
            matched: false,
            match_count: 0,
            waited_ms: 20,
          },
        ],
      }),
    ]);
    expect(image(), "화면이 없다").not.toBeNull();
    expect(document.body.textContent).toContain("시도한 LOCATOR");
    expect(document.body.textContent).toContain("요소를 찾을 수 없습니다");
  });

  it("결말과 소요 시간은 목록 행에 그대로 있다", async () => {
    await renderResult([
      stepResult({
        step_id: "st-1",
        index: 0,
        duration_ms: 120,
        screenshot: ".runs/TC-001/steps/0.png",
      }),
    ]);
    const row = document.querySelector('[data-step-row="st-1"]')!;
    expect(row.textContent).toContain("120");
    expect(row.querySelector('[data-outcome="pass"]')).not.toBeNull();
  });
});
