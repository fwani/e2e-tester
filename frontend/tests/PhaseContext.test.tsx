/**
 * 007 T075 — **국면을 넘어도 보던 Step 을 잃지 않는다** (SC-005·SC-006 · US3).
 *
 * 사용자가 겪는 한 바퀴는 이렇다 — 결과에서 실패한 Step 을 지목하고, 고치러 편집으로
 * 가고, 브라우저를 열어 세션에서 확인하고, 다시 결과로 돌아온다. 007 이전에는 그
 * 구간마다 지목이 끊겼다: `onShowResult` 가 테스트 식별자만 날랐고(S-10), 편집으로
 * 가는 길만 Step 을 실었다.
 *
 * 그래서 사용자는 매 국면에서 **그 Step 을 다시 찾았다.** 200개 목록에서 그것은
 * 스크롤과 눈으로 하는 일이다.
 *
 * 여기서 재는 것은 둘이다.
 *
 * 1. **왕복 전 구간에서 지목이 이어진다** (SC-005) — 주소가 그것을 나른다
 * 2. **새로 고침이 그 위치를 되찾는다** (SC-006) — 10번 중 10번
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  initialLocation,
  locationToSearch,
  searchToLocation,
  type WorkbenchLocation,
} from "../src/hooks/useScreenUrl";
import { ResultView } from "../src/pages/ResultView";
import { EditView } from "../src/pages/EditView";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { definitionView, runResult, sessionView } from "./helpers/workbench";

const STEP = "st-2";

function stubApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(JSON.stringify(definitionView()), { status: 200 });
      }
      if (url.includes("/result")) {
        return new Response(JSON.stringify(runResult()), { status: 200 });
      }
      return new Response("본문", { status: 200 });
    }),
  );
}

/** 그 Step 이 **지목된 상태로** 화면에 있는가. */
function focused(stepId: string): boolean {
  const row = document.querySelector(`[data-step-row="${stepId}"]`);
  if (row === null) return false;
  const pressed = row.querySelector('[aria-pressed="true"]');
  const detail = document.querySelector("[data-workbench-step-detail]");
  return pressed !== null || detail !== null;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("왕복 전 구간에서 지목이 이어진다 (SC-005 · FR-239)", () => {
  it("결과 국면 — 지목해 들어오면 그 Step 이 펼쳐져 있다", async () => {
    stubApi();
    render(
      <ResultView
        testId="TC-001"
        focusStepId={STEP}
        onRunAll={() => undefined}
        onRunFrom={() => undefined}
        onBack={() => undefined}
      />,
    );
    await waitFor(() => expect(document.querySelector("[data-step-row]")).not.toBeNull());
    expect(focused(STEP), "결과 국면이 지목을 잃었다").toBe(true);
  });

  it("편집 국면 — 같은 Step 이 이어진다", async () => {
    stubApi();
    render(<EditView testId="TC-001" focusStepId={STEP} onBack={() => undefined} />);
    await waitFor(() => expect(document.querySelector("[data-step-row]")).not.toBeNull());
    expect(focused(STEP), "편집 국면이 지목을 잃었다").toBe(true);
  });

  it("세션 국면 — 같은 Step 이 이어진다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({ view: sessionView({ state: "paused" }), focusedStepId: STEP })}
      />,
    );
    expect(focused(STEP), "세션 국면이 지목을 잃었다").toBe(true);
  });

  it("한 바퀴를 도는 동안 Step 을 다시 찾는 조작이 0회다", async () => {
    // 각 국면이 **받은 지목을 그대로 쓰는지**만 본다. 하나라도 흘리면 그 국면에서
    // 사용자가 다시 찾아야 하고, 그것이 SC-005 가 세는 값이다.
    stubApi();
    const seen: boolean[] = [];

    render(
      <ResultView
        testId="TC-001"
        focusStepId={STEP}
        onRunAll={() => undefined}
        onRunFrom={() => undefined}
        onBack={() => undefined}
      />,
    );
    await waitFor(() => expect(document.querySelector("[data-step-row]")).not.toBeNull());
    seen.push(focused(STEP));
    cleanup();

    render(<EditView testId="TC-001" focusStepId={STEP} onBack={() => undefined} />);
    await waitFor(() => expect(document.querySelector("[data-step-row]")).not.toBeNull());
    seen.push(focused(STEP));
    cleanup();

    render(
      <SessionWorkbench
        {...sessionProps({ view: sessionView({ state: "paused" }), focusedStepId: STEP })}
      />,
    );
    seen.push(focused(STEP));

    expect(seen.filter((v) => !v).length, "지목을 흘린 국면이 있다").toBe(0);
  });
});

describe("지목한 Step 이 사라졌을 때 (FR-243)", () => {
  it("사실을 밝히고 목록은 정상으로 보여 준다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "paused" }),
          focusedStepId: "지워진-step",
        })}
      />,
    );
    // 조용히 첫 Step 을 고르면 사용자는 그것이 보던 것이라고 믿는다.
    expect(document.querySelector("[data-focus-missing]")).not.toBeNull();
    // 목록은 그대로다 — 빈 화면을 주면 목록을 잃는다.
    expect(document.querySelectorAll("[data-step-row]").length).toBe(2);
  });
});

describe("새로 고침이 위치를 되찾는다 (SC-006 · FR-240)", () => {
  const ROUND_TRIP: WorkbenchLocation[] = [
    { name: "result", testId: "TC-001", sessionId: null, stepId: STEP },
    { name: "definition", testId: "TC-001", sessionId: null, stepId: STEP },
    { name: "result", testId: "TC-001", sessionId: null, stepId: null },
    { name: "definition", testId: "TC-002", sessionId: null, stepId: "st-9" },
    { name: "runner", testId: null, sessionId: "s-1", stepId: null },
  ];

  it("10번 중 10번 되찾는다 — 국면·테스트·Step 이 그대로다", () => {
    let restored = 0;
    for (let i = 0; i < 10; i += 1) {
      const at = ROUND_TRIP[i % ROUND_TRIP.length]!;
      const back = searchToLocation(locationToSearch(at));
      if (
        back.name === at.name &&
        (back.testId ?? null) === (at.testId ?? null) &&
        (back.sessionId ?? null) === (at.sessionId ?? null) &&
        (back.stepId ?? null) === (at.stepId ?? null)
      ) {
        restored += 1;
      }
    }
    expect(restored, "새로 고침이 위치를 잃었다").toBe(10);
  });

  it("결과 국면의 지목도 주소에 실린다 — 007 이 넓힌 자리다", () => {
    expect(locationToSearch({ name: "result", testId: "TC-001", stepId: STEP })).toBe(
      `?screen=result&test=TC-001&step=${STEP}`,
    );
  });

  it("최초 로드가 주소의 위치를 읽는다", () => {
    const url = `${window.location.pathname}?screen=result&test=TC-001&step=${STEP}`;
    window.history.replaceState({}, "", url);
    expect(initialLocation()).toEqual({
      name: "result",
      testId: "TC-001",
      sessionId: null,
      stepId: STEP,
    });
    window.history.replaceState({}, "", window.location.pathname);
  });
});
