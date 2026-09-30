/**
 * **표가 「할 수 있다」고 말한 조작이 실제로 이어져 있는가.** 027 FR-014~FR-016.
 *
 * ## 이 검사가 존재하는 이유
 *
 * 026 에서 「AI 에게 고쳐 달라기」가 한 화면에만 붙었고, **검사는 전부 통과했으며**,
 * 사용자가 찾지 못해서 알게 됐다. 조작표도 화면도 온전했다 — 없던 것은 「이 조작이 어느
 * 화면에 이어져 있는가」를 말해 주는 자리였다.
 *
 * ## `CapabilityUI` 와 무엇이 다른가
 *
 * | | 재는 것 |
 * |---|---|
 * | `CapabilityUI` | 조작이 화면에 **있는가** (`data-action`) |
 * | 이 파일 | 그 조작이 **이어져 있는가** (`data-wired-actions`) |
 *
 * 버튼이 있는데 눌러도 아무 일이 없는 상태를 앞의 것은 잡지 못한다.
 *
 * ## 판정 기준은 「해당 없음이 아닌 것」이다
 *
 * **「활성(enabled)」으로 잡으면 절반만 잡는다.** `cond(...)`·`off(...)` 인 조작도
 * 조건이 풀리거나 사유가 해소되면 눌리고, 그때 아무 일도 일어나지 않으면 그것이 바로
 * 이 기능이 막으려는 결함이다.
 *
 * 「해당 없음(`na`)」만이 「이을 필요가 없다」다 — 그 국면에 그 일이 아예 없다는 뜻이다.
 *
 * ## 목록을 손으로 적지 않는다
 *
 * 「어느 조작이 어느 화면에 있어야 하는가」를 여기 적으면 그것이 **세 번째 진실**이
 * 되고, 기능이 늘 때마다 고쳐야 하며, 고치지 않으면 거짓으로 통과한다. 화면을 그려서
 * 조작표와 대조하므로 목록이 필요 없다 (research R2).
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ACTION_IDS, type ActionId } from "../src/lib/actions";
import { rawCell } from "../src/lib/capabilities";
import { WIRED_ACTION_IDS } from "../src/lib/actionWiring";
import { PHASES, type Phase } from "../src/lib/phase";
import { EditView } from "../src/pages/EditView";
import { ResultView } from "../src/pages/ResultView";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { clickStep, definitionView, runResult, sessionView, test as makeTest } from "./helpers/workbench";
import type { SessionState } from "../src/api/client";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const STEPS = [clickStep({ id: "st-1" }), clickStep({ id: "st-2" }), clickStep({ id: "st-3" })];

/**
 * 그 국면에서 **이어져 있어야 하는** 조작.
 *
 * 「해당 없음」이 아니고, 이 배선 모듈이 다루는 조작인 것. 배선이 아직 다루지 않는
 * 조작(AI 대화 등)은 어댑터 고유의 것이므로 세지 않는다.
 */
function mustBeWired(phase: Phase): ActionId[] {
  return ACTION_IDS.filter(
    (id) => WIRED_ACTION_IDS.includes(id) && rawCell(phase, id).t !== "na",
  );
}

/** 화면이 내보낸 「이어 둔 조작」. 화면이 손으로 적은 것이 아니다 */
function wiredOnScreen(): Set<string> {
  const found = new Set<string>();
  for (const el of document.querySelectorAll("[data-wired-actions]")) {
    for (const id of (el.getAttribute("data-wired-actions") ?? "").split(",")) {
      if (id) found.add(id);
    }
  }
  return found;
}

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
        return new Response(
          JSON.stringify(
            definitionView({
              test: makeTest({
                steps: [...STEPS] as NonNullable<Parameters<typeof makeTest>[0]>["steps"],
              }),
            }),
          ),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify(runResult()), { status: 200 });
    }),
  );
}

/** 국면 하나를 실제 어댑터로 그린다 */
async function renderPhase(phase: Phase): Promise<boolean> {
  if (phase === "composing") return false; // 만들기 국면에는 Step 도 세션도 없다
  stubFetch();

  if (phase === "editing") {
    render(
      <EditView
        testId="TC-001"
        focusStepId={null}
        onBack={() => undefined}
        onRun={() => undefined}
        onOpenBrowserAt={() => undefined}
        onOpenSession={() => undefined}
      />,
    );
    await waitFor(() =>
      expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
    );
    return true;
  }

  if (phase === "result") {
    render(
      <ResultView
        testId="TC-001"
        focusStepId="st-1"
        onBack={() => undefined}
        onEditStep={() => undefined}
        onRun={() => undefined}
      />,
    );
    await waitFor(() =>
      expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
    );
    return true;
  }

  const setup = SESSION_STATE[phase];
  if (setup === undefined) return false;
  render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state: setup.state, steps: STEPS, authoring_mode: setup.mode }),
      })}
    />,
  );
  return true;
}

describe("표가 말한 조작이 이어져 있다 (FR-014 · SC-002)", () => {
  it.each(PHASES)("%s — 「해당 없음」이 아닌 조작이 전부 이어져 있다", async (phase) => {
    const drawn = await renderPhase(phase);
    if (!drawn) return; // 그릴 수 없는 국면은 이 검사의 대상이 아니다

    const wired = wiredOnScreen();
    const missing = mustBeWired(phase).filter((id) => !wired.has(id));

    expect(
      missing,
      `${phase} 에서 ${missing.length}개 조작이 이어져 있지 않다: ${missing.join(", ")}\n` +
        "조작표가 「해당 없음」으로 두지 않았으면 그 화면에서 눌릴 수 있고, 눌렸을 때\n" +
        "아무 일도 일어나지 않으면 사용자는 제품이 고장 났다고 읽는다.\n" +
        "→ 그 화면의 능력 묶음(`ScreenCapabilities`)에 해당 능력을 더하세요.",
    ).toEqual([]);
  });
});

describe("배선 목록 자체의 성질", () => {
  it("화면이 내보낸 목록에 **표에 없는 조작**이 들어 있지 않다", async () => {
    await renderPhase("editing");
    const stray = [...wiredOnScreen()].filter(
      (id) => !ACTION_IDS.includes(id as ActionId),
    );
    expect(stray, `조작 식별자가 아닌 것이 섞였다: ${stray.join(", ")}`).toEqual([]);
  });

  it("**목록을 이 파일이 들지 않는다** (FR-016 · research R2)", async () => {
    // 이 검사가 「어느 조작이 어디에 있어야 하는가」를 적어 두면 그것이 곧 낡는다.
    // 판정은 전부 `rawCell`(조작표)과 `data-wired-actions`(렌더 결과)에서 나온다.
    const drawn = await renderPhase("editing");
    expect(drawn).toBe(true);
    expect(mustBeWired("editing").length).toBeGreaterThan(0);
  });
});
