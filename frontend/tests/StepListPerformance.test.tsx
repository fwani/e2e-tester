/**
 * Step 목록 렌더 성능 (T151·T101). research R8.
 *
 * **002 에서 대상을 실제 렌더 경로로 옮겼다.** 전사 이후 어느 페이지도
 * `components/StepList.tsx` 를 임포트하지 않는데 이 가드는 그것을 재고 있었다 —
 * 통과하지만 아무것도 지키지 않는 상태였다 (converge 1회차가 잡았다).
 * 이제 페이지가 실제로 쓰는 `StepList` 를 200개 그려 잰다 (007 이행 3 — 단일 구현).
 *
 * 테스트당 Step 200개까지가 설계 상한이다 (plan.md Scale/Scope). 그 규모에서 목록이
 * 느려지면 일시정지 중 편집이 실용적이지 않게 된다 — 사용자는 Step 을 고르고 지우고
 * 옮기는 동안 이 목록을 계속 본다.
 *
 * **절대 시간을 재는 테스트는 환경에 따라 흔들린다.** 그래서 상한을 넉넉히 두고, 잡으려는
 * 것을 명확히 한다: 항목 수에 대해 **선형보다 나쁜** 렌더(예: 항목마다 전체 목록을 다시
 * 훑는 구현)를 잡는다. 미세한 성능 회귀는 이 테스트의 목표가 아니다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StepList } from "../src/components/workbench/StepList";
import type { WorkbenchStep } from "../src/components/workbench/model";
import type { Step } from "../src/types/generated/step";

/** 일곱 국면이 쓰는 **그 목록**을 그대로 그린다. */
function StepPanel({
  steps,
  pausedIndex = null,
}: {
  steps: Step[];
  pausedIndex?: number | null;
}) {
  const items: WorkbenchStep[] = steps.map((step, index) => ({
    id: step.id,
    index,
    step,
    label: step.label,
    outcome: "pending",
    durationMs: null,
    isPausedHere: index === pausedIndex,
  }));
  return (
    <StepList
      steps={items}
      authoring="record"
      focusedStepId={null}
      onSelect={() => undefined}
    />
  );
}

/** 200개 목록 한 번을 그리는 데 허용하는 시간. 넉넉하다 — 잡으려는 것은 배 이상 느린 구현이다. */
const BUDGET_MS = 2000;

function makeSteps(count: number): Step[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `step-${String(i + 1).padStart(2, "0")}`,
    type: "click",
    label: `${i + 1}번째 클릭`,
    author: i % 3 === 0 ? "ai" : "human",
    tab: i % 7 === 0 ? 1 : 0,
    timeout_ms: 5000,
    frame_url: null,
    target: {
      tag: "button",
      test_id: { value: `btn-${i}`, status: "verified" },
      role: null,
      accessible_name: null,
      role_status: null,
      label: null,
      text: null,
      stable_attr: null,
      css: { value: `button:nth-of-type(${i + 1})`, status: "verified" },
    },
  })) as unknown as Step[];
}

afterEach(cleanup);

describe("Step 패널 — 200개 규모 (실제 렌더 경로)", () => {
  it("설계 상한(200개)을 예산 안에 그린다", () => {
    const steps = makeSteps(200);
    const started = performance.now();
    render(<StepPanel steps={steps} pausedIndex={100} />);
    const elapsed = performance.now() - started;

    expect(screen.getByText("200번째 클릭")).toBeTruthy();
    expect(elapsed).toBeLessThan(BUDGET_MS);
  });

  it("항목 수에 대해 선형 근처로 늘어난다", () => {
    // 50 → 200 은 4배다. 4배 이상 느려지면 항목마다 전체를 훑는 구현일 가능성이 높다.
    const small = performance.now();
    render(<StepPanel steps={makeSteps(50)} />);
    const smallElapsed = Math.max(performance.now() - small, 1);
    cleanup();

    const large = performance.now();
    render(<StepPanel steps={makeSteps(200)} />);
    const largeElapsed = performance.now() - large;

    expect(largeElapsed).toBeLessThan(smallElapsed * 12);
  });

  it("일시정지 위치를 한 곳만 구분한다 (FR-034)", () => {
    const { container } = render(<StepPanel steps={makeSteps(200)} pausedIndex={100} />);
    // 구분은 목록에서 정확히 한 곳이다 — 여러 개면 어디서 멈췄는지 알 수 없다.
    // 패널 자체도 왼쪽 테두리를 갖는다(460px 경계)므로 **행 안에서만** 센다.
    expect(container.querySelectorAll('[data-step-row][style*="border-left"]')).toHaveLength(1);
  });
});
