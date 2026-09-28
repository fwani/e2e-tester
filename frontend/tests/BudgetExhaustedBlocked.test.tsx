/**
 * 예산이 떨어져 멈추면 화면이 그 상황의 말을 한다 (022 US2·US3).
 *
 * ## 무엇이 문제였나 (2026-09-28 사용자 보고)
 *
 * 상한에 닿은 화면이 「AI 가 막혔습니다 · 알려 주세요」라고 말했다. 예산이 떨어진
 * 것은 막힌 것이 아니고 알려 줄 것도 없는데, 사용자는 이어가려고 의미 없는 문장을
 * 지어내야 하는 것으로 읽었다.
 *
 * **기존 막힘 화면은 한 글자도 바뀌지 않아야 한다** (FR-016 · SC-005). 020·011 이
 * 쌓은 것이 이 변경으로 무너지면 얻는 것보다 잃는 것이 크다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

const base = {
  attempted: null,
  reason: "도구 호출이 상한(40회)에 도달해 중단했습니다.",
  choices: ["takeover", "answer", "retry", "skip", "abort"],
  question: null,
};

function mount(over: Record<string, unknown> = {}) {
  return render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
        aiBlocked: { ...base, kind: "budget_exhausted", ...over },
      })}
    />,
  );
}

const answerBox = () => document.querySelector("#blocked-answer");
const note = () => document.querySelector("[data-blocked-budget-exhausted]");
const usage = () => document.querySelector("[data-blocked-usage]");
const stalled = () => document.querySelector("[data-blocked-stalled]");
const buttons = () =>
  Array.from(
    document.querySelectorAll('[data-action="ai.chooseBlocked"] button'),
  ).map((b) => b.textContent?.trim() ?? "");

afterEach(cleanup);

describe("예산 소진은 막힘과 다르게 보인다 (FR-012·FR-013)", () => {
  it("제목이 「막혔습니다」가 아니다", () => {
    mount();
    expect(screen.queryByText("AI 가 막혔습니다")).toBeNull();
    expect(screen.getByText("여기까지 했습니다")).toBeTruthy();
  });

  it("알려 주기 칸이 열리지 않는다 — 알려 줄 것이 없다", () => {
    mount();
    expect(answerBox()).toBeNull();
  });

  it("이어가면 된다고 말한다 — 「이어가도 소용없다」와 정반대다", () => {
    mount();
    expect(note()).not.toBeNull();
    expect(note()!.textContent).toContain("이어서 계속할 수 있습니다");
  });

  it("사유는 그대로 보인다", () => {
    mount();
    expect(screen.getByText(base.reason)).toBeTruthy();
  });
});

describe("선택지가 그 상황의 말이다 (FR-014·FR-015)", () => {
  it("이어가기가 「다시」가 아니라 「이어서」로 읽힌다", () => {
    mount();
    expect(buttons()).toContain("이어서 계속");
    expect(buttons()).not.toContain("AI 에게 다시");
  });

  it("끝내기가 「여기까지」로 읽힌다", () => {
    mount();
    expect(buttons()).toContain("여기까지");
  });

  it("건너뛰기가 보이지 않는다 — 건너뛸 특정 동작이 없다", () => {
    mount();
    expect(buttons()).not.toContain("이 동작 건너뛰기");
  });

  it("이어받는 길은 남는다 — 막다른 길로 만들지 않는다", () => {
    mount();
    expect(buttons()).toContain("직접 조작해 이어가기");
  });
});

describe("판단 근거가 보인다 (FR-017·FR-019·FR-020·FR-021)", () => {
  it("누적 동작 수와 Step 수를 한 줄로 말한다", () => {
    mount({ totalToolCalls: 87, stepCount: 12 });
    expect(usage()).not.toBeNull();
    expect(usage()!.textContent).toContain("87");
    expect(usage()!.textContent).toContain("12");
  });

  it("수치를 모르면 그 줄을 그리지 않는다 — 022 이전 서버와 섞여도 깨지지 않는다", () => {
    mount({ totalToolCalls: null, stepCount: null });
    expect(usage()).toBeNull();
  });

  it("진전이 없었으면 그 사실을 알린다", () => {
    mount({ totalToolCalls: 87, stepCount: 12, madeProgress: false });
    expect(stalled()).not.toBeNull();
    expect(stalled()!.textContent).toContain("맴돌고");
  });

  it("진전이 있었으면 아무 말도 하지 않는다 — 정상 진행에 잡음을 더하지 않는다", () => {
    mount({ totalToolCalls: 87, stepCount: 12, madeProgress: true });
    expect(stalled()).toBeNull();
  });

  it("판정할 수 없으면(첫 시도) 경고하지 않는다 — null 과 false 는 다르다", () => {
    mount({ totalToolCalls: 40, stepCount: 5, madeProgress: null });
    expect(stalled()).toBeNull();
  });

  it("진전 없음이 이어가기를 막지 않는다 (FR-021)", () => {
    mount({ totalToolCalls: 87, stepCount: 12, madeProgress: false });
    const go = Array.from(
      document.querySelectorAll('[data-action="ai.chooseBlocked"] button'),
    ).find((b) => b.textContent?.trim() === "이어서 계속");
    expect(go).toBeDefined();
    expect((go as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("기존 막힘은 바뀌지 않는다 (FR-016 · SC-005)", () => {
  it("알려 주면 풀리는 막힘에는 답 칸과 다섯 선택지가 그대로다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
          aiBlocked: { ...base, kind: "needs_input", question: "어느 계정입니까?" },
        })}
      />,
    );
    expect(answerBox()).not.toBeNull();
    expect(note()).toBeNull();
    expect(usage()).toBeNull();
    expect(buttons()).toEqual([
      "직접 조작해 이어가기",
      "AI 에게 다시",
      "이 동작 건너뛰기",
      "AI 작성 끝내기",
    ]);
  });

  it("제품 동작 불일치도 그대로다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
          aiBlocked: { ...base, kind: "product_mismatch" },
        })}
      />,
    );
    expect(answerBox()).toBeNull();
    expect(document.querySelector("[data-blocked-product-mismatch]")).not.toBeNull();
    expect(note()).toBeNull();
    expect(buttons()).toContain("이 동작 건너뛰기");
  });
});
