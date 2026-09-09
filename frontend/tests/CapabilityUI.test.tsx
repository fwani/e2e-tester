/**
 * 007 T065 — **감춰진 조작 0건** (SC-004 · FR-234·FR-247).
 *
 * ## 2026-09-09 — 재는 것이 좁아졌다 (사용자 결정)
 *
 * 이전에 이 파일이 잰 것은 「표에서 `–` 가 아닌 칸은 전부 화면에 있다」였다. 그 규칙이
 * 지켜지는 채로 사용자가 보고한 것: 검토 국면의 조작 자리 24개 중 14개가 비활성이고,
 * 「처음부터 실행」이 버튼 하나 + 해소 링크 둘로 한 띠에 세 번 나왔다.
 *
 * 그래서 비활성을 둘로 갈랐다 (`capabilities.ts` 의 `REASON_VISIBILITY`). 이 파일이
 * 재는 것도 함께 갈린다.
 *
 * - **`keep`** — 사용자가 이 화면에서 곧바로 해소할 수 있는 전제(이름 미입력·Step
 *   미선택·요청 진행 중). 그 자리는 **여전히 반드시 있어야 한다** (`alwaysPresent`).
 * - **`hide`** — 「이 상태의 조작이 아니다」. 접히는 것이 맞고, 접혔는지는 세지 않는다.
 *   대신 **접혀야 할 사유가 화면에 새지 않았는지**를 센다 (아래 「사유가 새지 않는다」).
 *
 * 두 번째가 이 개정의 이빨이다. 조작을 접는 결정을 내리면 「접혔어야 할 것이 남는」
 * 실수가 조용해지는데, `ActionButton` 을 지나지 않는 자리(실행 속도·미러·탭 줄)가 실제로
 * 그랬다 — 속도 선택 넷이 검토 국면에 「실행이 이미 끝났습니다」를 달고 남아 있었다.
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
import { alwaysPresent, reasonVisibility } from "../src/lib/capabilities";
import { AT_BOTTOM, AT_TOP } from "../src/components/workbench/StepRowOps";
import {
  DISABLED_REASON,
  RUN_NEEDS_SAVE,
  SAVE_NEEDS_NAME,
  SENSITIVE_NO_VALUE,
  type DisabledReasonKey,
} from "../src/lib/wording";
import { PHASES, type Phase } from "../src/lib/phase";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { ResultView } from "../src/pages/ResultView";
import { EditView } from "../src/pages/EditView";
import { ComposeView } from "../src/pages/ComposeView";
import { sessionProps } from "./helpers/session";
import { definitionView, runResult, sessionView } from "./helpers/workbench";
import type { SessionState } from "../src/api/client";

/**
 * 그 국면에서 **화면에 있어야 하는** 조작.
 *
 * 판정은 `capabilities.ts` 의 `alwaysPresent` 가 한다 — 검사가 사본을 들면 표와 갈린다.
 */
function required(phase: Phase): ActionId[] {
  return ACTION_IDS.filter((a) => alwaysPresent(phase, a));
}

/**
 * 화면에 **나타나도 되는** 비활성 사유의 전부.
 *
 * 표의 `keep` 사유 + 화면이 좁혀 붙이는 사유들이다. 이 목록에 없는 문구가 화면에
 * 나타나면 접혀야 할 조작이 접히지 않은 것이다.
 */
const ALLOWED_REASONS: Set<string> = new Set<string>([
  ...(Object.keys(DISABLED_REASON) as DisabledReasonKey[])
    .filter((k) => reasonVisibility(k) === "keep")
    .map((k) => DISABLED_REASON[k]),
  // 화면이 아는 사실로 좁힌 것들 — 표에 담을 수 없고 전부 `keep` 이다.
  SAVE_NEEDS_NAME,
  RUN_NEEDS_SAVE,
  "먼저 Step 을 고르세요",
  AT_TOP,
  AT_BOTTOM,
  SENSITIVE_NO_VALUE,
]);

/**
 * 접히는 규칙 밖에 있는 조작 — **자리가 버튼이 아닌 것들**.
 *
 * - `mirror.control` — `ALWAYS_KEEP` 이다 (`capabilities.ts`). 자리가 미러 화면 전체이고
 *   사용자가 그 위를 클릭해 보므로, 어떤 사유로든 화면 위에 남아야 한다 (010 SC-516).
 * - `ai.compose` — `ALWAYS_KEEP` 이다. 자리가 지시문 칸이고 그 **내용이 정보다** —
 *   접으면 무엇을 시켰는지 잃는다 (001 FR-063 · UX U-07).
 * - `artifact.select` — 자리가 **탭 줄**이고 탭마다 자기 사유를 갖는다 (FR-246). 조작
 *   전체가 접히는지와 개별 탭이 지원되지 않는지는 다른 축이다.
 */
const EXEMPT_FROM_FOLDING = new Set<string>([
  "mirror.control",
  "ai.compose",
  "artifact.select",
]);

/** 접혀야 할 사유가 화면에 남았는가. */
function leakedReasons(): string[] {
  const out: string[] = [];
  for (const el of document.querySelectorAll("[data-disabled-reason]")) {
    const id = el.getAttribute("data-disabled-reason");
    if (id === null || EXEMPT_FROM_FOLDING.has(id)) continue;
    const text = (el.textContent ?? "").trim();
    // 해소 방법 버튼의 라벨이 같은 요소에 붙는다 — 사유로 시작하는지만 본다.
    if ([...ALLOWED_REASONS].some((r) => text.startsWith(r))) continue;
    out.push(`${id}: "${text}"`);
  }
  return out;
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
  /** 2026-09-09 에 갈라진 둘 (`phase.ts`) */
  review: { state: "review", mode: "record" },
  finished: { state: "completed", mode: "record" },
};

/**
 * 국면 하나를 **실제 어댑터로** 그린다.
 *
 * Step 상세를 함께 연다 — `step.update`·`step.markSensitive`·`step.repick` 의 집이
 * 거기이기 때문이다 (§4-1). 닫힌 상태만 재면 그 셋이 늘 빠진 것으로 세어진다.
 */
async function renderPhase(phase: Phase) {
  /*
    2회차 — 만들기 국면 (FR-217b). 세션도 저장된 테스트도 Step 도 없으므로 다른
    국면과 다른 어댑터를 쓴다. **국면을 더하면 이 함수가 그것을 몰라 터진다** — 그것이
    「빠뜨릴 수 없게 한다」의 실제 동작이다.
  */
  if (phase === "composing") {
    render(
      <ComposeView
        project={null}
        onCancel={() => undefined}
        onRecord={() => undefined}
        onStartAi={() => undefined}
      />,
    );
    await waitFor(() =>
      expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
    );
    return;
  }
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

  it.each(PHASES)("%s — 접혀야 할 사유가 화면에 새지 않는다", async (phase) => {
    await renderPhase(phase);
    const leaked = leakedReasons();
    expect(
      leaked,
      `${phase} 에서 「이 상태의 조작이 아니다」인 사유가 화면에 남았다:\n  ${leaked.join("\n  ")}\n` +
        "그 자리는 접혀야 한다 (`capabilities.ts` 의 REASON_VISIBILITY).",
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

  /**
   * FR-227 은 **지목하는 방식**이 같아야 한다는 것이다. Step 행이 없는 국면에서 행을
   * 요구하는 것이 아니다 — 만들기 국면은 Step 이 0개다 (FR-260).
   *
   * 그래서 둘을 나눠 센다: 모든 국면에서 **Step 패널의 자리**가 있고, Step 이 있는
   * 국면에서는 그 행이 같은 방식으로 지목된다.
   */
  it("Step 목록의 자리는 모든 국면에 있다 (FR-260 · S-15)", async () => {
    for (const phase of PHASES) {
      await renderPhase(phase);
      expect(document.querySelector("[data-workbench-step-panel]"), phase).not.toBeNull();
      cleanup();
    }
  });

  it("Step 이 있는 국면 전부에서 지목 방식이 같다 (FR-227)", async () => {
    for (const phase of PHASES) {
      if (phase === "composing") continue; // Step 이 0개다 — 아래 검사가 그것을 센다
      await renderPhase(phase);
      expect(document.querySelector("[data-step-row]"), phase).not.toBeNull();
      cleanup();
    }
  });

  it("만들기 국면은 목록이 비었음과 어디에 쌓이는지를 그 자리에서 말한다 (FR-260)", async () => {
    await renderPhase("composing");
    expect(document.querySelector("[data-step-row]")).toBeNull();
    // 자리를 감추면 「조작이 어디에 쌓이는지」를 시작 전에 보여 줄 수 없다 (S-15)
    expect(screen.getByText(/시작하면 조작 하나가 행 하나로 여기 쌓입니다/)).toBeTruthy();
  });

  it("검사가 실제로 무언가를 세고 있다", () => {
    /*
      표를 못 읽은 채 초록이 되는 상태를 막는다.

      **기준이 낮아졌다** (2026-09-09). 이전에는 국면마다 10개를 넘게 요구했는데, 그 수는
      「`–` 가 아닌 칸」의 수였고 지금 세는 것은 「반드시 자리에 있어야 하는 칸」이다 —
      접히는 것이 정상인 칸이 빠졌으므로 국면별 수가 준다 (실행 중 국면은 6개다).

      그래서 두 가지로 센다: **어느 국면도 통째로 비지 않는다**(화면이 아무 조작도 갖지
      않는 국면은 없다)와 **합계가 유의미하다**. 둘 중 하나만으로는 한 국면이 0 이 되는
      실수나 표를 통째로 못 읽는 실수를 놓친다.
    */
    for (const phase of PHASES) {
      expect(required(phase).length, `${phase} 에 반드시 있어야 하는 조작이 없다`).toBeGreaterThan(
        2,
      );
    }
    const total = PHASES.reduce((n, p) => n + required(p).length, 0);
    expect(total).toBeGreaterThan(40);
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
