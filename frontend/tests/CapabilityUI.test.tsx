/**
 * 007 T065 — **감춰진 조작 0건** (SC-004 · FR-234·FR-247).
 *
 * 이 파일이 재는 것은 하나다. `contracts/ui-contract.md` §3 의 표에서 `–`(해당 없음)가
 * **아닌** 칸은 전부 그 국면 화면에 **있어야 한다.** 있고 없고를 국면마다 눈으로 세는
 * 대신 표를 읽어 센다 — 눈으로 세면 한 국면을 빠뜨리고, 빠진 자리가 감춰진 조작이 된다.
 *
 * `CapabilityCoverage` 와 무엇이 다른가: 그것은 **표 자체**가 온전한지 본다(빠진 칸·근거
 * 없는 `–`·화면에 없는 해소 방법). 이 파일은 **화면이 표를 따르는지** 본다. 표가 옳아도
 * 화면이 그리지 않으면 사용자에게는 없는 조작이다.
 *
 * ## 조작의 집 (ui-contract §4-1)
 *
 * 조작마다 자리가 하나다. 그래서 검사는 `[data-action="<id>"]` 하나를 찾는다 — 버튼이든
 * 입력칸이든 상관하지 않는다. 자리가 둘이면 라벨이 둘이 되고, 그것은 `LabelUniqueness`
 * 와 이 파일의 「한 조작에 한 자리」가 함께 잡는다.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ACTION_IDS, type ActionId } from "../src/lib/actions";
import { rawCell } from "../src/lib/capabilities";
import { PHASES, type Phase } from "../src/lib/phase";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { ResultView } from "../src/pages/ResultView";
import { EditView } from "../src/pages/EditView";
import { sessionProps } from "./helpers/session";
import { definitionView, runResult, sessionView } from "./helpers/workbench";
import type { SessionState } from "../src/api/client";

/**
 * 그 국면에서 **화면에 있어야 하는** 조작.
 *
 * `–` 인 칸만 없어도 된다 — 그 근거(N1·N2·N3)는 `CapabilityCoverage` 가 이미 센다.
 */
function required(phase: Phase): ActionId[] {
  return ACTION_IDS.filter((a) => rawCell(phase, a).t !== "na");
}

/**
 * 조작이 그 자리를 갖지 않아도 되는 예외 — **없다.**
 *
 * 자리를 옮긴 조작이 있으면 그 자리에 `data-action` 을 달아야지, 여기 이름을 더해서는
 * 안 된다. 예외 목록이 자라는 것이 곧 감춰진 조작이 자라는 것이다.
 */
const EXEMPT: ActionId[] = [];

function present(): Set<string> {
  const found = new Set<string>();
  for (const el of document.querySelectorAll("[data-action]")) {
    const id = el.getAttribute("data-action");
    if (id) found.add(id);
  }
  return found;
}

/** 그 국면에서 빠진 조작. 비어 있어야 한다. */
function missing(phase: Phase): ActionId[] {
  const found = present();
  return required(phase).filter((a) => !found.has(a) && !EXEMPT.includes(a));
}

/** 비활성인데 이유가 없는 조작. 비어 있어야 한다 (FR-234). */
function silentlyDisabled(): string[] {
  const out: string[] = [];
  for (const el of document.querySelectorAll("[data-action]")) {
    const id = el.getAttribute("data-action");
    if (id === null) continue;
    const disabled =
      (el as HTMLButtonElement | HTMLInputElement).disabled === true ||
      el.getAttribute("aria-disabled") === "true";
    if (!disabled) continue;
    if (document.querySelector(`[data-disabled-reason="${id}"]`) === null) out.push(id);
  }
  return out;
}

/** 한 조작이 두 자리를 갖지 않는다 (FR-235). */
function duplicated(): string[] {
  const counts = new Map<string, number>();
  for (const el of document.querySelectorAll("[data-action]")) {
    const id = el.getAttribute("data-action");
    if (id === null) continue;
    counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  return [...counts.entries()].filter(([, n]) => n > 1).map(([id, n]) => `${id} ×${n}`);
}

const SESSION_STATE: Record<string, { state: SessionState; mode: "record" | "ai" }> = {
  recording: { state: "recording", mode: "record" },
  ai_authoring: { state: "ai_running", mode: "ai" },
  takeover: { state: "takeover_recording", mode: "ai" },
  running: { state: "replaying", mode: "record" },
  paused: { state: "paused", mode: "record" },
};

/**
 * 국면 하나를 **실제 어댑터로** 그린다.
 *
 * Step 상세를 함께 연다 — `step.update`·`step.markSensitive`·`step.repick` 의 집이
 * 거기이기 때문이다 (§4-1). 닫힌 상태만 재면 그 셋이 늘 빠진 것으로 세어진다.
 */
async function renderPhase(phase: Phase) {
  if (phase === "result") {
    stubResult();
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
    await waitFor(() => expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull());
    return;
  }
  if (phase === "editing") {
    stubDefinition();
    render(<EditView testId="TC-001" focusStepId="st-1" onBack={() => undefined} onRun={() => undefined} onOpenBrowserAt={() => undefined} onOpenSession={() => undefined} />);
    await waitFor(() => expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull());
    return;
  }
  const fixture = SESSION_STATE[phase];
  render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state: fixture!.state, authoring_mode: fixture!.mode }),
        focusedStepId: "st-1",
        detailOpen: true,
        aiInstruction: "로그인한 다음 프로젝트를 만들어",
        aiBlocked: { attempted: null, reason: "막혔습니다", choices: ["takeover"] },
      })}
    />,
  );
}

function stubResult() {
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

function stubDefinition() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(JSON.stringify(definitionView()), { status: 200 });
      }
      // 결과가 있는 테스트다 — 「결과 자세히 보기」가 조건 C13 으로 열린다.
      return new Response(JSON.stringify(runResult()), { status: 200 });
    }),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("감춰진 조작 0건 (SC-004 · FR-234)", () => {
  it.each(PHASES)("%s — 표가 `–` 로 두지 않은 조작이 전부 화면에 있다", async (phase) => {
    await renderPhase(phase);
    const gone = missing(phase);
    expect(
      gone,
      `${phase} 에서 ${gone.length}개가 화면에 없다: ${gone.join(", ")}\n` +
        "표가 `–` 로 두지 않았으면 화면에 있어야 한다 (FR-234·FR-247).",
    ).toEqual([]);
  });

  it.each(PHASES)("%s — 비활성 조작이 전부 이유를 갖는다", async (phase) => {
    await renderPhase(phase);
    const silent = silentlyDisabled();
    expect(
      silent,
      `${phase} 에서 이유 없이 잠긴 조작: ${silent.join(", ")}`,
    ).toEqual([]);
  });

  it.each(PHASES)("%s — 한 조작이 두 자리를 갖지 않는다 (FR-235)", async (phase) => {
    await renderPhase(phase);
    const dup = duplicated();
    expect(dup, `${phase} 에서 자리가 둘인 조작: ${dup.join(", ")}`).toEqual([]);
  });
});

describe("예외 목록은 비어 있어야 한다", () => {
  it("조작을 화면에서 빼는 예외가 없다", () => {
    // 자리를 옮겼으면 그 자리에 `data-action` 을 달아야지, 예외로 넘겨서는 안 된다.
    expect(EXEMPT).toEqual([]);
  });

  it("Step 지목은 일곱 국면 전부에서 같은 방식이다 (FR-227)", async () => {
    for (const phase of PHASES) {
      await renderPhase(phase);
      expect(document.querySelector("[data-step-row]"), phase).not.toBeNull();
      cleanup();
    }
  });

  it("검사가 실제로 무언가를 세고 있다", () => {
    // 표를 못 읽은 채 초록이 되는 상태를 막는다.
    expect(required("running").length).toBeGreaterThan(10);
    expect(required("editing").length).toBeGreaterThan(10);
  });
});

describe("결말 요약은 화면에 하나뿐이다 (T063 · FR-218d)", () => {
  it.each(PHASES)("%s — `data-run-summary` 가 최대 하나다", async (phase) => {
    await renderPhase(phase);
    expect(document.querySelectorAll("[data-run-summary]").length).toBeLessThanOrEqual(1);
  });
});

describe("국면 표시도 하나뿐이다 (FR-219)", () => {
  it.each(PHASES)("%s — `data-phase-pill` 이 정확히 하나다", async (phase) => {
    await renderPhase(phase);
    expect(document.querySelectorAll("[data-phase-pill]").length).toBe(1);
    expect(screen.getAllByText(/./).length).toBeGreaterThan(0);
  });
});
