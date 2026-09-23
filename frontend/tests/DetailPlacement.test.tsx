/**
 * Step details keep the list available: inline in editing, temporary inspector for live/results.
 * The shared detail implementation remains reachable without changing the browser column width.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

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
    expect(document.querySelector(phase === "composing" ? "[data-compose-start]" : "[data-workbench-step-panel]")).not.toBeNull(),
  );
}

const detailLayer = () =>
  document.querySelector("[data-workbench-detail-layer]") as HTMLElement | null;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/**
 * 상세 층의 자리 — **인라인과 클래스 두 표기를 모두 읽는다.**
 *
 * 015 가 배치를 클래스로 옮기는 중이라 전환된 화면과 아직인 화면이 공존한다.
 * 두 표기를 같은 이름으로 환산해 비교하므로, 이 검사가 묻는 것(「자리가 모든 국면에서
 * 같은가」)은 전환 중에도 그대로 성립한다.
 */
function placement(el: HTMLElement): { position: string; right: string; top: string; bottom: string } {
  const cls = el.className;
  const pick = (side: "right" | "top" | "bottom"): string => {
    const inline = el.style[side];
    if (inline !== "") return inline;
    const m = new RegExp(`\\b${side}-(\\[[^\\]]+\\]|[a-z0-9-]+)`).exec(cls);
    return m?.[1] ?? "";
  };
  const position =
    el.style.position !== ""
      ? el.style.position
      : /\babsolute\b/.test(cls)
        ? "absolute"
        : /\bfixed\b/.test(cls)
          ? "fixed"
          : "";
  return { position, right: pick("right"), top: pick("top"), bottom: pick("bottom") };
}

describe("Step 상세는 작업 목적에 맞게 배치하고 목록을 가리지 않는다", () => {
  it.each(PHASES)("%s — 편집은 본문에, 실행과 결과는 검사 창에 표시한다", async (phase) => {
    await renderPhaseWithDetail(phase);
    const layer = detailLayer();
    if (phase === "composing") {
      expect(layer).toBeNull();
      return;
    }
    expect(layer, `${phase} 상세가 열리지 않았다`).not.toBeNull();
    const panel = document.querySelector("[data-workbench-step-panel]")!;
    expect(panel.contains(layer)).toBe(false);
    expect(layer!.contains(panel)).toBe(false);
    if (phase === "editing") {
      expect(layer!.hasAttribute("data-edit-detail-inline")).toBe(true);
      expect(document.querySelector("[data-workbench-left-column]")!.contains(layer)).toBe(true);
      expect(layer!.closest('[data-slot="scrim"]')).toBeNull();
      expect(placement(layer!).position).not.toBe("absolute");
    } else if (phase === "ai_authoring" || phase === "takeover") {
      expect(layer!.tagName).toBe("ASIDE");
      expect(layer!.closest('[data-slot="scrim"]')).toBeNull();
      expect(placement(layer!).position).not.toBe("absolute");
      expect(document.querySelector<HTMLElement>("#ai-authoring-sidebar")!.hidden).toBe(true);
    } else {
      expect(layer!.getAttribute("data-slot")).toBe("scrim");
      expect(placement(layer!).position).toBe("absolute");
      expect(placement(layer!).right).toBe("0");
      expect(layer!.className).toContain("left-steps");
    }
  });
});

describe("FR-370 — 지목을 바꿔도 자리와 크기가 같다", () => {
  /**
   * 「상세 대상만 바뀐다」의 **뒤 절반**이다. 앞 절반(내용이 그 Step 으로 바뀐다)은
   * `StepScreenshot` 이 센다.
   *
   * 지금은 자리가 상수라 저절로 지켜진다. 그래도 재는 이유: 다음 사람이 「이 Step 은
   * 길어서 더 넓게」 같은 분기를 넣으면 조용히 깨지고, 사용자에게는 고를 때마다 판이
   * 움직이는 것으로 보인다.
   */
  it("다른 행을 골라도 상세 층의 자리 선언이 그대로다", async () => {
    const user = userEvent.setup();
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "paused" }),
          focusedStepId: "st-1",
          detailOpen: true,
        })}
      />,
    );
    await waitFor(() => expect(detailLayer()).not.toBeNull());

    const snapshot = (el: HTMLElement) =>
      [el.style.position, el.style.top, el.style.right, el.style.bottom, el.style.left].join("|");
    const before = snapshot(detailLayer()!);

    await user.click(screen.getByRole("button", { name: "아이디 입력" }));
    await waitFor(() => expect(detailLayer()).not.toBeNull());

    expect(snapshot(detailLayer()!), "지목이 바뀌면서 상세의 자리가 움직였다").toBe(before);
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
