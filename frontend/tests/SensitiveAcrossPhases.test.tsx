/**
 * 007 T068 — **민감 값은 일곱 국면 전부에서 참조로만 보인다** (FR-252 · 006 FR-212·FR-215).
 *
 * 006 이 이것을 편집 화면 하나에서 세웠다. 007 은 화면을 합치면서 그 성질이 **국면을
 * 넘어서도** 유지되는지 물어야 한다 — 합치는 과정에서 어느 국면 하나가 평문 경로를
 * 되살리면, 그 국면에서만 값이 새고 그것은 화면을 열어 봐야만 보인다.
 *
 * 성질은 둘이다.
 *
 * 1. 값을 참조로 담은 Step 은 어느 국면에서나 `{{NAME}}` 로만 보인다
 * 2. 평문이 화면에 없다 — 실제 값은 봉인되어 비밀 파일에 있고 화면에 올 경로가 없다
 *
 * **경로를 만들지 않는 것이 방법이다** (006 research). 마스킹으로 가리면 마스킹을
 * 잊는 코드 경로가 언젠가 생긴다.
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PHASES, type Phase } from "../src/lib/phase";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { ResultView } from "../src/pages/ResultView";
import { EditView } from "../src/pages/EditView";
import { ComposeView } from "../src/pages/ComposeView";
import { sessionProps } from "./helpers/session";
import { definitionView, fillStep, runResult, sessionView, test as testFixture } from "./helpers/workbench";
import type { SessionState } from "../src/api/client";
import type { Step } from "../src/types/generated/step";

/** 봉인된 실제 값. **어느 국면에서도 화면에 나와서는 안 된다.** */
const PLAINTEXT = "hunter2-super-secret";
const REFERENCE = "{{LOGIN_PASSWORD}}";

/** 민감 변수를 참조하는 Step. 정의에는 참조만 남는다 (006 FR-082). */
function secretStep(): Step {
  return fillStep({ id: "st-2", label: "비밀번호 입력", value: REFERENCE });
}

const SESSION_STATE: Record<string, { state: SessionState; mode: "record" | "ai" }> = {
  recording: { state: "recording", mode: "record" },
  ai_authoring: { state: "ai_running", mode: "ai" },
  takeover: { state: "takeover_recording", mode: "ai" },
  running: { state: "replaying", mode: "record" },
  paused: { state: "paused", mode: "record" },
  /** 2026-09-09 에 갈라진 둘 (`phase.ts`). 민감 값 규칙은 국면과 무관하게 같다 */
  review: { state: "review", mode: "record" },
  finished: { state: "completed", mode: "record" },
};

function stub(kind: "result" | "definition") {
  const test = testFixture({
    steps: [secretStep()],
    variables: [{ name: "LOGIN_PASSWORD", sensitive: true }],
  } as never);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(JSON.stringify(definitionView({ test })), { status: 200 });
      }
      if (url.includes("/result")) {
        if (kind === "definition") return new Response(JSON.stringify(runResult()), { status: 200 });
        return new Response(
          JSON.stringify(
            runResult({
              steps: [
                {
                  step_id: "st-2",
                  index: 0,
                  label: "비밀번호 입력",
                  outcome: "pass",
                  duration_ms: 90,
                  element_wait_ms: 0,
                  tab: 0,
                  tab_wait_ms: 0,
                  error_code: null,
                  error_message: null,
                  locator_attempts: [],
                  resolved_candidate: null,
                  candidate_disagreement: [],
                },
              ],
            }),
          ),
          { status: 200 },
        );
      }
      return new Response("본문", { status: 200 });
    }),
  );
}

async function renderPhase(phase: Phase) {
  /*
    2회차 — 만들기 국면 (FR-217b). **Step 이 0개이므로 민감 값이 있을 수 없다.**
    그래도 훑는 대상에서 빼지 않는다 — 「이 국면에는 원래 없다」는 판단이 언젠가
    틀리면(예: 초안을 이어 만드는 기능이 생기면) 아무것도 세지 않는 상태가 된다.
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
    stub("result");
    render(
      <ResultView
        testId="TC-001"
        focusStepId="st-2"
        onRunAll={() => undefined}
        onRunFrom={() => undefined}
        onBack={() => undefined}
      />,
    );
    await waitFor(() =>
      expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
    );
    return;
  }
  if (phase === "editing") {
    stub("definition");
    render(<EditView testId="TC-001" focusStepId="st-2" onBack={() => undefined} />);
    await waitFor(() =>
      expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
    );
    return;
  }
  const fixture = SESSION_STATE[phase]!;
  render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({
          state: fixture.state,
          authoring_mode: fixture.mode,
          steps: [secretStep()],
        }),
        focusedStepId: "st-2",
        detailOpen: true,
      })}
    />,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("민감 값 (T068 · FR-252)", () => {
  it.each(PHASES)("%s — 평문이 화면에 없다", async (phase) => {
    await renderPhase(phase);
    const text = document.body.textContent ?? "";
    expect(text, `${phase} 에서 평문이 화면에 나왔다`).not.toContain(PLAINTEXT);
    // 입력칸의 **값**도 본다. 텍스트로는 보이지 않지만 화면에 들어와 있는 것이다.
    for (const el of document.querySelectorAll("input, textarea")) {
      expect(
        (el as HTMLInputElement).value,
        `${phase} 의 입력칸에 평문이 들어와 있다`,
      ).not.toContain(PLAINTEXT);
    }
  });

  /**
   * 이 검사는 「참조가 **없어지지 않았는가**」를 센다 — 값이 있다는 사실 자체가
   * 사라지면 사용자는 그 Step 이 무엇을 넣는지 모른다.
   *
   * 만들기 국면은 Step 이 0개이므로 **보여 줄 참조가 애초에 없다.** 위의 두 검사
   * (평문이 없다 · 참조 칸을 고칠 수 없다)는 그 국면에서도 그대로 돈다 — 「있어서는
   * 안 되는 것」을 세는 검사는 대상이 없어도 뜻이 있다.
   */
  it.each(PHASES.filter((p) => p !== "composing"))("%s — 참조 형태로만 보인다", async (phase) => {
    await renderPhase(phase);
    const shownAsText = (document.body.textContent ?? "").includes(REFERENCE);
    const shownAsValue = [...document.querySelectorAll("input, textarea")].some((el) =>
      (el as HTMLInputElement).value.includes(REFERENCE),
    );
    expect(
      shownAsText || shownAsValue,
      `${phase} 에서 민감 참조가 화면에 없다 — 값이 있다는 사실 자체가 사라졌다`,
    ).toBe(true);
  });

  it.each(PHASES)("%s — 참조 값 칸은 고칠 수 없다 (006 FR-213)", async (phase) => {
    await renderPhase(phase);
    const field = document.querySelector("#detail-value") as HTMLInputElement | null;
    if (field === null) return; // 그 국면에 값 칸이 없으면 볼 것이 없다
    if (!field.value.includes(REFERENCE)) return;
    // 평문이 이 화면에 들어올 자리를 만들지 않는다 — 그것이 마스킹보다 강한 보장이다.
    expect(field.disabled, `${phase} 의 참조 값 칸이 열려 있다`).toBe(true);
  });
});
