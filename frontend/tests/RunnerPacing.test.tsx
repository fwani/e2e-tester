/**
 * 실행 중 화면이 어디까지 왔는지 보여준다 (004 FR-107).
 *
 * **Step 간 간격이 이 요구의 이유다.** 간격 동안 화면이 아무것도 말하지 않으면, 속도를
 * 낮춘 사용자는 멈춘 것인지 쉬는 것인지 구별할 수 없다.
 *
 * 간격 중에는 `step_started` 가 발행되지 않는다. 그래서 마지막으로 온 `step_finished`
 * 상태가 그대로 남아 **방금 끝난 Step 과 그 결과**가 보인다. 그것이 성립의 근거인데,
 * 지금까지 암묵적이었다 — 누군가 간격 중 이벤트를 추가하면 조용히 깨진다. 여기서 고정한다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PacingControl } from "../src/components/PacingControl";
import { Runner } from "../src/pages/Runner";
import type { Step } from "../src/types/generated/step";

const steps = [
  {
    id: "s1", type: "click", label: "로그인", author: "human", tab: 0,
    timeout_ms: 10000,
    target: { test_id: { value: "login", status: "verified" } },
  },
  {
    id: "s2", type: "click", label: "데이터 메뉴", author: "human", tab: 0,
    timeout_ms: 10000,
    target: { test_id: { value: "data", status: "verified" } },
  },
  {
    id: "s3", type: "click", label: "업로드", author: "human", tab: 0,
    timeout_ms: 10000,
    target: { test_id: { value: "upload", status: "verified" } },
  },
] as unknown as Step[];

/** Step 02 를 막 끝낸 상태 — 곧 03 이 시작되기 전, 즉 **간격 중**이다. */
const inTheGap = {
  title: "TC-001",
  testId: "TC-001",
  progressLabel: "step 02 / 03",
  statusLabel: "RUNNING",
  authoring: "record" as const,
  currentUrl: "https://x.test/",
  steps,
  // 간격 중에는 `step_started` 가 없으므로 03 은 `running` 이 아니라 `pending` 이다 —
  // 그것이 "아직 시작하지 않았다" 를 화면에 말하는 방식이다.
  outcomeOf: (_s: Step, index: number) =>
    index <= 1 ? ("pass" as const) : ("pending" as const),
  durationOf: (s: Step) => (s.id === "s2" ? 342 : undefined),
  busy: false,
  canPause: true,
  onPause: () => undefined,
  onStop: () => undefined,
  mirror: <div />,
};

afterEach(cleanup);

describe("간격 중 진행 표시 (FR-107)", () => {
  it("어디까지 왔는지 보여준다", () => {
    render(<Runner {...inTheGap} />);
    expect(screen.getByText("step 02 / 03")).toBeDefined();
  });

  it("방금 끝난 Step 과 그 결과가 보인다", () => {
    render(<Runner {...inTheGap} />);
    // 사용자가 간격 동안 읽는 것: 무엇이 끝났고 얼마나 걸렸는가.
    expect(screen.getByText("데이터 메뉴")).toBeDefined();
    expect(screen.getByText("342 ms")).toBeDefined();
  });

  it("아직 시작하지 않은 Step 을 끝난 것으로 보이게 하지 않는다", () => {
    render(<Runner {...inTheGap} />);
    // 03 이 이미 통과한 것처럼 보이면, 간격 중 화면은 거짓을 말하는 것이다.
    expect(screen.getByText("업로드")).toBeDefined();
    expect(screen.queryByText("342 ms")).not.toBeNull();
    // 소요 시간이 붙은 Step 은 실제로 끝난 것 하나뿐이다.
    expect(screen.queryAllByText(/\d+ ms/)).toHaveLength(1);
  });

  it("실행 중에도 속도를 바꿀 수 있다 (FR-103)", () => {
    const onChange = vi.fn();
    render(
      <Runner
        {...inTheGap}
        pacing={<PacingControl value="slow" onChange={onChange} />}
      />,
    );
    fireEvent.click(screen.getByTestId("pacing-fast"));
    expect(onChange).toHaveBeenCalledWith("fast");
  });

  it("실행이 끝나면 속도를 바꿀 수 없되 무엇을 골랐는지는 남는다", () => {
    const onChange = vi.fn();
    render(
      <Runner
        {...inTheGap}
        statusLabel="COMPLETED"
        canPause={false}
        pacing={<PacingControl value="slow" onChange={onChange} disabled />}
      />,
    );
    const slow = screen.getByTestId("pacing-slow") as HTMLButtonElement;
    expect(slow.disabled).toBe(true);
    expect(slow.getAttribute("aria-pressed")).toBe("true");
  });
});
