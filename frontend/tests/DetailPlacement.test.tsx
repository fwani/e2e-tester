/**
 * 011 T017 — **Step 상세는 Step 목록 왼쪽에서 겹친다** (UC-011-7·8·10 · FR-368~FR-373).
 *
 * ## 사용자 보고
 *
 * > 「STEP 상세 는 오버레이로 오른쪽으로 뜨고있는데 스텝리스트 왼쪽으로 수정한다」
 *
 * ## 무엇이 문제였나
 *
 * 상세는 우측에서 겹쳤고 **Step 목록도 우측에 있다.** 그래서 상세가 목록을 덮었다 —
 * 방금 고른 행을 보면서 상세를 읽을 수 없고, 무엇을 골랐는지 확인하려면 상세를 닫아야
 * 했다.
 *
 * ## 011 이 고른 답 (clarify 결정 1)
 *
 * **겹침은 유지하고 자리만 옮긴다.** 대상 앱을 밀어 나란히 놓으면 최소 기준 폭에서
 * 미러가 **상시로** 좁아지는데, 상세가 닫혀 있는 시간이 열려 있는 시간보다 길다. 볼 때만
 * 가리는 쪽이 총비용이 작다.
 *
 * 그래서 이 파일이 재는 것은 셋이다 — 자리가 목록 왼쪽인가, 목록을 덮지 않는가, 대상 앱의
 * **폭을 바꾸지 않는가**. 마지막이 겹침의 정의다: 밀어내면 폭이 변한다.
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { STEP_PANEL_WIDTH } from "../src/components/workbench/StepList";
import { PHASES, type Phase } from "../src/lib/phase";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { ResultView } from "../src/pages/ResultView";
import { EditView } from "../src/pages/EditView";
import { ComposeView } from "../src/pages/ComposeView";
import { sessionProps } from "./helpers/session";
import { definitionView, runResult, sessionView } from "./helpers/workbench";
import type { SessionState } from "../src/api/client";

const SESSION_STATE: Record<string, { state: SessionState; mode: "record" | "ai" }> = {
  recording: { state: "recording", mode: "record" },
  ai_authoring: { state: "ai_running", mode: "ai" },
  takeover: { state: "takeover_recording", mode: "ai" },
  running: { state: "replaying", mode: "record" },
  paused: { state: "paused", mode: "record" },
  review: { state: "review", mode: "record" },
  finished: { state: "completed", mode: "record" },
};

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(JSON.stringify(definitionView()), { status: 200 });
      }
      if (url.includes("/result")) {
        return new Response(JSON.stringify(runResult({ outcome: "fail", failed_step_index: 0 })), {
          status: 200,
        });
      }
      return new Response("본문", { status: 200 });
    }),
  );
}

/** 상세를 **연 채로** 그 국면을 그린다. 자리를 재려면 열려 있어야 한다. */
async function renderPhaseWithDetail(phase: Phase) {
  if (phase === "composing") {
    // 만들기 국면에는 Step 이 구조적으로 0개다 — 상세가 열릴 수 없다.
    render(
      <ComposeView
        project={null}
        onCancel={() => undefined}
        onRecord={() => undefined}
        onStartAi={() => undefined}
      />,
    );
  } else if (phase === "result") {
    stubFetch();
    render(
      <ResultView
        testId="TC-001"
        focusStepId="st-1"
        onRunAll={() => undefined}
        onRunFrom={() => undefined}
        onEditStep={() => undefined}
        onBack={() => undefined}
      />,
    );
  } else if (phase === "editing") {
    stubFetch();
    render(
      <EditView
        testId="TC-001"
        focusStepId="st-1"
        onBack={() => undefined}
        onRun={() => undefined}
        onOpenBrowserAt={() => undefined}
        onOpenSession={() => undefined}
      />,
    );
  } else {
    const fixture = SESSION_STATE[phase]!;
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: fixture.state, authoring_mode: fixture.mode }),
          focusedStepId: "st-1",
          detailOpen: true,
        })}
      />,
    );
  }
  await waitFor(() =>
    expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
  );
}

const detailLayer = () =>
  document.querySelector("[data-workbench-detail-layer]") as HTMLElement | null;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("UC-011-7 — 상세의 자리는 Step 목록 왼쪽이고 국면마다 같다", () => {
  it.each(PHASES)("%s — 상세가 열리면 목록 왼쪽에 붙는다", async (phase) => {
    await renderPhaseWithDetail(phase);
    const layer = detailLayer();
    if (layer === null) return; // 그 국면에서 상세가 열리지 않으면 잴 것이 없다

    /*
      **`right` 가 Step 패널 폭이다.** 0 이면 목록을 덮는다 (011 이전 상태).
      좌표를 직접 적지 않고 정본 상수와 대조한다 — 패널 폭이 바뀌면 함께 바뀌어야 한다.
    */
    expect(layer.style.right, `${phase} — 상세가 아직 목록을 덮는 자리에 있다`).toBe(
      `${STEP_PANEL_WIDTH}px`,
    );
    expect(layer.style.position).toBe("absolute");
  });

  it("자리가 모든 국면에서 같다 (FR-369)", async () => {
    const seen = new Map<string, Phase[]>();
    for (const phase of PHASES) {
      await renderPhaseWithDetail(phase);
      const layer = detailLayer();
      if (layer !== null) {
        const key = `${layer.style.position}|${layer.style.right}|${layer.style.top}|${layer.style.bottom}`;
        seen.set(key, [...(seen.get(key) ?? []), phase]);
      }
      cleanup();
      vi.unstubAllGlobals();
    }
    expect(seen.size, `자리가 ${seen.size}가지다: ${[...seen.keys()].join(" / ")}`).toBe(1);
  });
});

describe("UC-011-7 — Step 목록을 가리지 않는다", () => {
  it("상세 층과 Step 패널이 겹치지 않는다", async () => {
    await renderPhaseWithDetail("paused");
    const layer = detailLayer();
    const panel = document.querySelector("[data-workbench-step-panel]");
    expect(layer, "상세가 열리지 않았다").not.toBeNull();
    expect(panel).not.toBeNull();
    // 상세 층이 Step 패널을 담고 있으면(또는 그 반대면) 덮는 배치다.
    expect(layer!.contains(panel!), "상세가 Step 패널을 품고 있다").toBe(false);
    expect(panel!.contains(layer!), "Step 패널이 상세를 품고 있다").toBe(false);
  });
});

describe("UC-011-8 — 상세는 대상 앱의 폭을 바꾸지 않는다", () => {
  /**
   * **겹침의 정의다.** 밀어내는 배치라면 상세가 열릴 때 좌측 열의 폭 선언이 바뀐다.
   * jsdom 은 실제 폭을 계산하지 않으므로 `WorkbenchHeight` 와 같은 방식으로 **구조를**
   * 잰다 — 좌측 열의 flex 선언이 상세 유무에 관계없이 같은가.
   */
  it("상세를 열어도 좌측 열의 배분 선언이 같다", async () => {
    const leftColumnFlex = async (detailOpen: boolean) => {
      render(
        <SessionWorkbench
          {...sessionProps({
            view: sessionView({ state: "paused" }),
            focusedStepId: "st-1",
            detailOpen,
          })}
        />,
      );
      await waitFor(() =>
        expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
      );
      const left = document.querySelector("[data-workbench-left-column]") as HTMLElement | null;
      expect(left, "좌측 열 표식이 없다").not.toBeNull();
      const value = left!.style.flex;
      cleanup();
      return value;
    };

    const closed = await leftColumnFlex(false);
    const open = await leftColumnFlex(true);
    expect(open, "상세가 열리면서 좌측 열의 폭 선언이 바뀌었다 — 겹침이 아니라 밀어내기다").toBe(
      closed,
    );
  });
});

describe("UC-011-10 — 닫는 조작은 상세 안에 있다", () => {
  it.each(PHASES)("%s — 상세가 열리면 그 안에 닫는 조작이 있다", async (phase) => {
    await renderPhaseWithDetail(phase);
    const layer = detailLayer();
    if (layer === null) return;
    const close = layer.querySelector("[data-detail-close]");
    expect(close, `${phase} — 상세 안에 닫는 조작이 없다`).not.toBeNull();
  });
});
