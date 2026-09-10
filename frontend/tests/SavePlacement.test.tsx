/**
 * 011 T008 — **저장·되돌리기·이름의 집은 국면 띠다** (UC-011-1·2·3 · FR-360~FR-361).
 *
 * ## 무엇을 재는가
 *
 * `CapabilityUI` 는 「표가 `–` 로 두지 않은 조작이 화면에 **있는가**」를 센다. 자리가
 * 어디인지는 보지 않는다 — 그래서 저장이 팔레트 바닥에 있어도 그 검사는 통과했고,
 * 실제로 통과하는 채로 사용자가 보고했다:
 *
 * > 「테스트를 저장하는 버튼과 이름을 지정하는게 오른쪽 아래에 존재하는데, ux 적으로
 * > 매우 불편함」
 *
 * 이 파일이 재는 것은 **자리**다. 「있는가」가 아니라 「어디에 있는가」이며, 그것이
 * FR-235(같은 조작은 어느 국면에서나 같은 자리)의 나머지 절반이다.
 *
 * ## 왜 조상 요소로 재는가
 *
 * `data-workbench-phase-bar` 는 국면 띠가 이미 갖고 있는 표식이고,
 * `data-workbench-step-panel`·`data-workbench-step-footer` 는 Step 패널과 그 바닥
 * (팔레트)이 갖고 있다. 좌표나 CSS 로 재면 값이 바뀔 때마다 검사를 고쳐야 하지만,
 * 「어느 영역 안에 있는가」는 배치가 바뀌어도 같은 질문이다.
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ActionId } from "../src/lib/actions";
import { alwaysPresent } from "../src/lib/capabilities";
import { PHASES, type Phase } from "../src/lib/phase";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { ResultView } from "../src/pages/ResultView";
import { EditView } from "../src/pages/EditView";
import { ComposeView } from "../src/pages/ComposeView";
import { sessionProps } from "./helpers/session";
import { definitionView, runResult, sessionView } from "./helpers/workbench";
import type { SessionState } from "../src/api/client";

/** 011 이 국면 띠로 옮긴 셋 (011 계약 §1 · 007 계약 §2-7). */
const MOVED_TO_PHASE_BAR: ActionId[] = ["save", "edits.revert", "test.rename"];

/**
 * 팔레트에 **남는** 둘 (research R1).
 *
 * 국면 띠에 표시되지 않는 값이므로 「보이는 곳에서 고친다」 논리가 성립하지 않고,
 * 48px 한 줄은 긴 URL 을 담을 수 없다. 함께 옮기지 않았다는 것을 검사로 고정한다 —
 * 다음 사람이 「저장 옆에 있어야 자연스럽다」로 옮기면 띠가 창 밖으로 밀려난다.
 */
const STAYS_IN_PALETTE: ActionId[] = ["test.setStartUrl", "ai.compose"];

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

/** 국면 하나를 실제 어댑터로 그린다. `CapabilityUI` 와 같은 방식이다. */
async function renderPhase(phase: Phase) {
  if (phase === "composing") {
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
          aiInstruction: "로그인한 다음 프로젝트를 만들어",
        })}
      />,
    );
  }
  await waitFor(() =>
    expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
  );
}

function elementsFor(action: ActionId): Element[] {
  return [...document.querySelectorAll(`[data-action="${action}"]`)];
}

function isInside(el: Element, marker: string): boolean {
  return el.closest(`[${marker}]`) !== null;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("UC-011-1 — 저장·되돌리기·이름은 국면 띠에 있다", () => {
  it.each(PHASES)("%s — 그 국면에 있어야 하는 것은 국면 띠 안에 있다", async (phase) => {
    await renderPhase(phase);
    for (const action of MOVED_TO_PHASE_BAR) {
      if (!alwaysPresent(phase, action)) continue;
      const els = elementsFor(action);
      expect(els.length, `${phase} × ${action} 이 화면에 없다`).toBeGreaterThan(0);
      for (const el of els) {
        expect(
          isInside(el, "data-workbench-phase-bar"),
          `${phase} × ${action} 이 국면 띠 밖에 있다 (011 UC-011-1)`,
        ).toBe(true);
      }
    }
  });

  it.each(PHASES)("%s — Step 패널 안에는 없다", async (phase) => {
    await renderPhase(phase);
    for (const action of MOVED_TO_PHASE_BAR) {
      for (const el of elementsFor(action)) {
        expect(
          isInside(el, "data-workbench-step-panel"),
          `${phase} × ${action} 이 아직 Step 패널 안에 있다 — 011 이 옮긴 자리가 아니다`,
        ).toBe(false);
      }
    }
  });

  it.each(PHASES)("%s — 시작 주소·지시문은 팔레트에 남는다 (research R1)", async (phase) => {
    await renderPhase(phase);
    for (const action of STAYS_IN_PALETTE) {
      for (const el of elementsFor(action)) {
        expect(
          isInside(el, "data-workbench-phase-bar"),
          `${phase} × ${action} 이 국면 띠로 갔다 — 48px 한 줄은 긴 값을 담을 수 없다`,
        ).toBe(false);
      }
    }
  });
});

describe("UC-011-2 — 이름을 표시하는 자리와 고치는 자리가 하나다", () => {
  /**
   * 국면 띠는 011 이전에도 테스트 이름을 그렸다 (`PhaseBar` 의 `.phase-name`). 팔레트에도
   * 이름 입력칸이 있었으므로 **같은 값에 자리가 둘**이었다. 011 은 그 둘을 하나로 합친다.
   *
   * `data-action="test.rename"` 이 하나뿐인 것은 `CapabilityUI` 의 「한 조작에 한 자리」가
   * 이미 센다. 이 검사가 더하는 것은 **그 하나가 이름을 보여주는 자리와 같은지**다.
   */
  it.each(PHASES)("%s — 이름 표시 자리가 곧 `test.rename` 의 자리다", async (phase) => {
    await renderPhase(phase);
    const rename = elementsFor("test.rename");
    if (rename.length === 0) return; // 그 국면에 없는 조작이면 잴 것이 없다
    expect(rename.length, `${phase} 에서 test.rename 자리가 ${rename.length}개다`).toBe(1);
    const nameSlot = document.querySelector("[data-phase-test-name]");
    expect(nameSlot, `${phase} — 국면 띠의 이름 자리 표식이 없다`).not.toBeNull();
    expect(
      nameSlot!.contains(rename[0]!) || nameSlot === rename[0],
      `${phase} — 이름을 보여주는 자리와 고치는 자리가 다르다 (UC-011-2)`,
    ).toBe(true);
  });
});

describe("UC-011-3 — 국면 띠는 조작이 늘어도 줄어들 수 있다", () => {
  /**
   * 국면 띠의 조작 묶음은 `flex: 0 1 auto`·`minWidth: 0` 이어야 한다. `0 0 auto` 였을 때
   * 여러 조작이 동시에 잠겨 이유 문구가 나란히 붙으면 묶음이 제 내용 폭을 끝까지 요구해
   * **띠가 창 밖으로 밀려났다** (`PhaseBar.tsx` 주석의 기록).
   *
   * 011 이 그 묶음에 조작을 셋 더하므로 같은 위험이 커진다. 이름 입력칸에도 같은 규칙을
   * 요구한다 — 200자를 받는 칸이 제 내용 폭을 요구하면 조작이 밀려난다.
   */
  it("이름 자리가 줄어들 수 있다", async () => {
    await renderPhase("paused");
    const nameSlot = document.querySelector("[data-phase-test-name]") as HTMLElement | null;
    expect(nameSlot).not.toBeNull();
    // 브라우저·jsdom 이 `0` 과 `0px` 을 다르게 정규화한다 — 값으로 잰다.
    expect(
      parseFloat(nameSlot!.style.minWidth || "NaN"),
      "이름 자리에 minWidth: 0 이 없다",
    ).toBe(0);
  });
});
