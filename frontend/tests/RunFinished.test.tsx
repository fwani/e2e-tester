/**
 * 실행이 끝난 화면이 **이유와 다음 행동**을 준다 (UX U-02).
 *
 * 사용자가 겪은 것: `FAIL · 3 / 5 통과` 와 Step 04 의 빨간 ✕ 만 있었다. 이유는 한 글자도
 * 없고, 결과 화면으로 가는 링크도 다시 실행하는 버튼도 없었다. 그 자리에서 할 수 있는 것이
 * 없으니 새로고침을 누르게 되고, 그러면 목록으로 튕긴다.
 *
 * **007 이행 1** — 결말 요약은 국면 띠가 하나만 갖고(FR-218d), 사유는 알림이, 다음 행동은
 * 헤더·국면 띠의 조작이 맡는다. 옛 `Runner` 의 「실행 종료 바」가 세 자리로 나뉜 것이다.
 * 조작은 **감추지 않는다** — 쓸 수 없으면 비활성으로 남고 이유가 붙는다 (FR-234).
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import type { Step } from "../src/types/generated/step";

const steps = [
  { id: "s1", type: "click", label: "로그인", author: "human", tab: 0, timeout_ms: 5000,
    frame_url: null, target: { test_id: { value: "login", status: "verified" } } },
] as unknown as Step[];

function props(overrides: Record<string, unknown> = {}) {
  return sessionProps({
    view: sessionView({ state: "replaying", steps, current_step_index: 0 }),
    outcomeOf: () => "fail",
    durationOf: () => 120,
    ...overrides,
  });
}

const button = (name: string) => screen.getByRole("button", { name }) as HTMLButtonElement;

afterEach(cleanup);

describe("실행 종료 표시", () => {
  it("실행 중에는 결과로 가는 길이 아직 열리지 않는다", () => {
    render(<SessionWorkbench {...props()} />);
    // 감추지 않고 **비활성으로 남긴다** — 감추면 사용자는 그런 길이 없는 줄 안다.
    expect(button("결과 자세히 보기").disabled).toBe(true);
    expect(document.querySelector("[data-disabled-reason='result.show']")).not.toBeNull();
  });

  it("실패 사유와 갈 곳을 한 화면에 준다", () => {
    const onShowResult = vi.fn();
    const onRerunFrom = vi.fn();
    const onShowList = vi.fn();
    render(
      <SessionWorkbench
        {...props({
          view: sessionView({ state: "failed", steps, current_step_index: 0 }),
          summary: "실패 · Step 01 에서 실패 · 3 / 5 통과 · 0.23 s",
          failure: { index: 0, message: "PASSWORD: 민감 변수를 복호화할 수 없습니다." },
          onShowResult,
          onRerunFrom,
          onShowList,
        })}
      />,
    );

    // 결말 요약은 **화면에 하나뿐이다** (FR-218d · 005 FR-140 · U-19).
    const summary = document.querySelectorAll("[data-run-summary]");
    expect(summary).toHaveLength(1);
    expect(summary[0]?.textContent).toContain("실패 · Step 01 에서 실패 · 3 / 5 통과");
    // 이유가 있어야 한다 — 빨간 ✕ 만으로는 "1분 안에 원인 파악" 이 성립하지 않는다.
    expect(screen.getByText(/민감 변수를 복호화할 수 없습니다/)).toBeTruthy();

    fireEvent.click(button("결과 자세히 보기"));
    fireEvent.click(button("Step 01부터 실행"));
    fireEvent.click(button("목록으로"));
    expect(onShowResult).toHaveBeenCalledTimes(1);
    expect(onRerunFrom).toHaveBeenCalledWith(0);
    expect(onShowList).toHaveBeenCalledTimes(1);
  });

  it("통과했으면 실패 사유를 지어내지 않는다", () => {
    render(
      <SessionWorkbench
        {...props({
          view: sessionView({ state: "completed", steps, current_step_index: 0 }),
          outcomeOf: () => "pass",
          summary: "통과 · 5 / 5 통과 · 1.02 s",
          failure: null,
          onRerunAll: () => undefined,
        })}
      />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
    // 끝난 세션에서는 재실행이 열린다 (C1).
    expect(button("처음부터 실행").disabled).toBe(false);
    // 지목한 Step 이 없으면 「Step nn부터 실행」은 무엇부터인지 모른다 — 이유를 붙여 잠근다.
    expect(button("Step 01부터 실행").disabled).toBe(true);
  });

  it("끝난 실행의 「닫기」는 강조를 뺀다 (005 FR-147 · U-08)", () => {
    render(
      <SessionWorkbench
        {...props({
          view: sessionView({ state: "completed", steps, current_step_index: 0 }),
          outcomeOf: () => "pass",
        })}
      />,
    );
    const close = button("닫기");
    expect(close.style.boxShadow).toBe("none");
    expect(screen.queryByRole("button", { name: "중지" })).toBeNull();
  });
});
