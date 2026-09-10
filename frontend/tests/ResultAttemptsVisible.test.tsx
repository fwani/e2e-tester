/**
 * 결과 국면의 「왜 멈췄나」가 자리를 갖는다 (007 T132 · SC-012 · FR-262 · quickstart §1-8).
 *
 * ## 이 검사가 세는 것은 「보이는가」가 아니다
 *
 * 2회차 명세는 처음에 S-13 을 「시도한 locator 가 겹침 상세에만 있다」로 적었다.
 * **그 관찰이 틀렸다** — `PhaseAside`(현 `WorkArea`)가 1회차부터 `step.locator_attempts`
 * 를 조건 없이 그려 왔고, 주석까지 「Step 상세를 열지 않아도 보여야 한다」로 달려 있었다.
 *
 * 실제 결함은 **자리의 크기**였다. 그 영역이 `minHeight: 42` · `maxHeight: 45%` 였고,
 * 실패 사유와 시도한 locator 표가 그 안에서 스크롤에 갇혔다. 답이 화면에 있는데도 한눈에
 * 들어오지 않았다 — S-12(편집 국면의 역전)와 같은 뿌리다.
 *
 * 그래서 이 검사는 **자리가 충분한가**를 센다. 「보이는가」만 세면 1회차 구현도 통과하고,
 * 그러면 아무것도 지키지 못한다.
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResultView } from "../src/pages/ResultView";
import { RESULT_WORK_PX, flexOf, splitFor } from "../src/lib/layout";
import { definitionView, runResult, stepResult } from "./helpers/workbench";

const el = (selector: string) => document.querySelector<HTMLElement>(selector);

/** 시도한 네 후보 — 하나도 맞지 않았다. */
const ATTEMPTS = [
  { candidate: "testId", expression: "(없음)", match_count: 0, waited_ms: 0, matched: false },
  {
    candidate: "role",
    expression: 'role=button "저장"',
    match_count: 0,
    waited_ms: 5_000,
    matched: false,
  },
  { candidate: "text", expression: 'text="저장"', match_count: 0, waited_ms: 0, matched: false },
  { candidate: "css", expression: "button.save", match_count: 0, waited_ms: 0, matched: false },
];

const REASON = "5000 ms 안에 요소를 찾지 못했습니다";

/** 실패한 Step 하나. `stepResult` 를 지나 온전한 모양을 갖는다 */
const FAILED_STEP = stepResult({
  step_id: "st-1",
  index: 0,
  label: "저장 버튼 클릭",
  outcome: "fail",
  duration_ms: 5_000,
  element_wait_ms: 5_000,
  error_message: REASON,
  // 실제 코드 목록의 값이다 — 004 FR-122 의 진단이 `code` 로 분기하므로 아무 값이나 쓰면
  // 진단 문구가 달라지고 이 검사가 무엇을 재는지 흐려진다
  error_code: "ELEMENT_NOT_READY",
  locator_attempts: ATTEMPTS,
});

/** `CapabilityUI.test.tsx` 의 `stubResult` 와 같은 방식이다. */
function stubFailingResult(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(JSON.stringify(definitionView()), { status: 200 });
      }
      if (url.includes("/result")) {
        return new Response(
          JSON.stringify(
            runResult({
              outcome: "fail",
              failed_step_index: 0,
              steps: [FAILED_STEP],
              passed_count: 0,
              attempted_count: 1,
              total_count: 1,
            }),
          ),
          { status: 200 },
        );
      }
      return new Response("본문", { status: 200 });
    }),
  );
}

async function showResult() {
  stubFailingResult();
  const view = render(
    <ResultView
      testId="TC-001"
      focusStepId={null}
      onRunAll={vi.fn()}
      onRunFrom={vi.fn()}
      onBack={vi.fn()}
    />,
  );
  await waitFor(() => expect(el("[data-workbench-step-panel]")).not.toBeNull());
  return view;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("결과 국면 ③-b 가 스크롤 없이 담을 자리를 갖는다 (SC-012 · FR-262)", () => {
  it("배분이 정해진 높이다 — 내용 높이도, 남는 높이도 아니다", () => {
    const { workArea } = splitFor("result");
    expect(workArea.kind).toBe("fixed");
    if (workArea.kind === "fixed") expect(workArea.px).toBe(RESULT_WORK_PX);
  });

  /**
   * **이것이 1회차와 갈리는 지점이다.** `content` 배분에는 상한(45%)이 붙고, 그 상한이
   * 실패 사유와 locator 표를 스크롤에 갇히게 했다. `fixed` 에는 상한이 붙지 않는다.
   */
  it("높이 상한이 붙지 않는다 — 상한이 내용을 스크롤에 갇히게 했다 (S-13)", () => {
    const style = flexOf(splitFor("result").workArea);
    expect(style.maxHeight).toBeUndefined();
    expect(style.minHeight).toBe(RESULT_WORK_PX);
  });

  it("실패 사유 2줄 + LOCATOR 4행 + 경고 1개가 들어가는 높이다", () => {
    // 사유 블록 ≈96 + 표 머리 36 + 4행 ×34 + 경고 ≈64 + 여백 ≈92 = 424
    expect(RESULT_WORK_PX).toBeGreaterThanOrEqual(400);
  });

  it("작업 영역이 그 배분으로 실제로 그려진다", async () => {
    const view = await showResult();
    const work = el("[data-workbench-work]")!;
    expect(work.dataset.slotSize).toBe("fixed");
    // 015 T029 — 배분이 클래스로 바뀌었다. 묻는 것은 그대로다: 결과 국면의 작업
    // 영역이 424px 로 고정되고 **상한이 붙지 않는가**. 상한(`max-h-[45%]`)이 붙으면
    // 실패 사유와 LOCATOR 4행이 스크롤 뒤로 숨는다 (FR-262).
    expect(work.className).toContain(`flex-[0_0_${RESULT_WORK_PX}px]`);
    expect(work.className, "고정 높이에 상한이 붙었다 — 내용이 잘린다").not.toContain("max-h-");
    view.unmount();
  });
});

describe("겹침 상세를 열지 않은 상태에서 답이 다 있다 (FR-262)", () => {
  it("실패 사유가 작업 영역에 있다", async () => {
    const view = await showResult();
    // 겹침 상세가 닫힌 상태임을 먼저 확인한다 — 열려 있으면 이 검사는 아무것도 세지 않는다
    expect(el("[data-workbench-step-detail]")).toBeNull();
    expect(el("[data-workbench-work]")!.textContent).toContain(REASON);
    view.unmount();
  });

  it("시도한 LOCATOR 네 후보가 작업 영역에 있다", async () => {
    const view = await showResult();
    expect(el("[data-workbench-step-detail]")).toBeNull();
    const text = el("[data-workbench-work]")!.textContent ?? "";
    for (const attempt of ATTEMPTS) {
      expect(text, `${attempt.candidate} 가 없다`).toContain(attempt.expression);
    }
    view.unmount();
  });

  /**
   * 겹침 상세의 표는 **지목한** Step 의 것이고, 작업 영역의 것은 **실패한** Step 고정이다.
   * 둘은 다른 질문에 답하므로 한쪽이 다른 쪽을 대체하지 않는다 — 같은 값을 두 곳에 두는
   * 것과 다르다 (`WorkArea` 도 `StepDetail` 도 `step.locator_attempts` 를 읽는다).
   */
  it("시도 기록을 별도 필드로 나르지 않는다 — 같은 값을 두 곳에 두지 않는다", () => {
    // `WorkAreaView.failure_detail` 이 `attempts` 를 갖지 않는다.
    // 구현 중 그 필드를 만들다 S-13 의 관찰이 틀렸음을 발견했다.
    const work: import("../src/components/workbench/model").WorkAreaView = {
      kind: "failure_detail",
      step: FAILED_STEP,
      diagnosis: null,
    };
    expect(Object.keys(work).sort()).toEqual(["diagnosis", "kind", "step"]);
  });
});
