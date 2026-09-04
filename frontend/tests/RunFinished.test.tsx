/**
 * 실행이 끝난 화면이 **이유와 다음 행동**을 준다 (UX U-02).
 *
 * 사용자가 겪은 것: `FAIL · 3 / 5 통과` 와 Step 04 의 빨간 ✕ 만 있었다. 이유는 한 글자도
 * 없고, 결과 화면으로 가는 링크도 다시 실행하는 버튼도 없었다. 그 자리에서 할 수 있는 것이
 * 없으니 새로고침을 누르게 되고, 그러면 목록으로 튕긴다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Runner } from "../src/pages/Runner";
import type { Step } from "../src/types/generated/step";

const steps = [
  { id: "s1", type: "click", label: "로그인", author: "human", tab: 0, timeout_ms: 5000,
    target: { test_id: { value: "login", status: "verified" } } },
] as unknown as Step[];

const base = {
  title: "TC-001",
  testId: "TC-001",
  progressLabel: "step 01 / 01",
  statusLabel: "FAILED",
  authoring: "record" as const,
  currentUrl: "https://x.test/",
  steps,
  outcomeOf: () => "fail" as const,
  durationOf: () => 120,
  busy: false,
  canPause: false,
  onPause: () => undefined,
  onStop: () => undefined,
  mirror: <div />,
};

afterEach(cleanup);

describe("실행 종료 바", () => {
  it("실행 중에는 나오지 않는다", () => {
    render(<Runner {...base} />);
    expect(screen.queryByText("결과 자세히 보기")).toBeNull();
  });

  it("실패 사유와 갈 곳을 한 화면에 준다", () => {
    const onShowResult = vi.fn();
    const onRerunFromFailure = vi.fn();
    const onBack = vi.fn();
    render(
      <Runner
        {...base}
        finished={{
          summary: "FAIL · 3 / 5 통과 · 0.23 s",
          failureReason: "PASSWORD: 민감 변수를 복호화할 수 없습니다.",
          onShowResult,
          onRerunFromFailure,
          onBack,
        }}
      />,
    );

    const bar = screen.getByRole("status");
    expect(bar.textContent).toContain("FAIL · 3 / 5 통과");
    // 이유가 있어야 한다 — 빨간 ✕ 만으로는 "1분 안에 원인 파악"(SC-009)이 성립하지 않는다.
    expect(bar.textContent).toContain("민감 변수를 복호화할 수 없습니다");

    fireEvent.click(screen.getByRole("button", { name: "결과 자세히 보기" }));
    fireEvent.click(screen.getByRole("button", { name: "실패한 Step부터 다시 실행" }));
    fireEvent.click(screen.getByRole("button", { name: "목록으로" }));
    expect(onShowResult).toHaveBeenCalledTimes(1);
    expect(onRerunFromFailure).toHaveBeenCalledTimes(1);
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("통과했으면 실패 전용 행동을 내놓지 않는다", () => {
    render(
      <Runner
        {...base}
        finished={{
          summary: "PASS · 5 / 5 통과 · 1.02 s",
          failureReason: null,
          onRerunFromFailure: () => undefined,
          onRerunAll: () => undefined,
          onBack: () => undefined,
        }}
      />,
    );
    expect(screen.queryByText("실패한 Step부터 다시 실행")).toBeNull();
    expect(screen.getByRole("button", { name: "처음부터 다시 실행" })).toBeTruthy();
  });
});
