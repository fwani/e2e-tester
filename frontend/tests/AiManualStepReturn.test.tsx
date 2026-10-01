/**
 * **AI 세션에서 직접 조작으로 Step 을 추가하고 돌아온다** (2026-09-30 사용자 보고).
 *
 * > 「ai 생성중 → 직접 조작으로 스텝을 추가하다가 → 다시 ai 로 갈 방법이 없다」
 *
 * `Phase.test.ts` 가 같은 길을 **판정과 표**로 잰다. 이 파일은 그것이 **화면에 실제로
 * 그려지는가**를 잰다. 둘을 가르는 이유는 실측이다 — 표가 `●` 여도 그 조작을 그리는
 * 컴포넌트가 그 국면에 걸려 있지 않으면 화면에는 없다. 「조작할 수 있다」와 「조작이
 * 보인다」는 다른 질문이고, 이 결함의 절반이 두 번째 쪽이었다.
 *
 * 그래서 여기서 쓰는 단언은 전부 **화면에서 찾을 수 있는가**다. 능력 객체를 다시 묻지
 * 않는다 — 그러면 `Phase.test.ts` 를 한 번 더 쓰는 것이고, 배선이 끊겨도 통과한다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

afterEach(cleanup);

const INSTRUCTION = "로그인하고 연결 정보를 등록해";

/** AI 세션 하나를 그 상태로 그린다. 지시문을 주는 이유는 그것이 대화의 첫 차례이기 때문이다. */
function renderAi(state: "ai_running" | "paused" | "recording") {
  return render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state, authoring_mode: "ai" }),
        aiInstruction: INSTRUCTION,
      })}
    />,
  );
}

/** AI 작성 현황이 **옆자리로** 서 있는가. `null` 이면 이 세션에 그 자리가 없다. */
function sidebar(): HTMLElement | null {
  return document.getElementById("ai-authoring-sidebar");
}

describe("AI 세션에서 직접 조작으로 Step 을 추가하고 돌아온다 (2026-09-30 사용자 보고)", () => {
  /*
    ── 길의 세 지점 ────────────────────────────────────────────────────────
    AI 작성 중 → (일시정지) → 직접 조작 녹화 → (기록 멈추기) → 일시정지 → AI 에게 말하기.
    가운데 두 지점이 막혀 있었다.
  */

  it("AI 가 도는 중에는 작성 현황이 옆에 있다 — 고치기 전에도 그랬다", () => {
    renderAi("ai_running");
    expect(sidebar()).not.toBeNull();
  });

  /**
   * **직접 조작에는 반드시 `paused` 를 지난다** (`state_machine.py`:
   * `PAUSED → RECORD_ACTIONS_START`). 그 길목에서 자리가 사라지면, 사용자는 방금까지
   * AI 와 주고받던 화면이 없어진 자리에서 돌아갈 곳을 찾아야 한다.
   */
  it("일시정지해도 작성 현황이 남는다 — 돌아갈 자리가 사라지지 않는다", () => {
    renderAi("paused");
    expect(sidebar(), "일시정지에서 AI 작성 현황이 사라졌다").not.toBeNull();
  });

  it("직접 조작 녹화 중에도 작성 현황이 남는다", () => {
    renderAi("recording");
    expect(sidebar(), "녹화 중에 AI 작성 현황이 사라졌다").not.toBeNull();
  });

  /**
   * 지시문은 **대화의 첫 차례**다 (`AiAuthoringPanel`). 그것이 보인다는 것은 패널이
   * 껍데기만 선 것이 아니라 이 세션의 이력을 들고 있다는 뜻이다 — 자리만 남고 내용이
   * 비면 사용자에게는 여전히 「없어진 것」이다.
   */
  it("일시정지에서도 처음 시킨 말이 그대로 보인다", () => {
    renderAi("paused");
    expect(screen.getAllByText(INSTRUCTION).length).toBeGreaterThan(0);
  });

  /**
   * **켠 것을 끄는 버튼이 화면에 있다.** 이것이 없어서 길이 끊겼다 — 녹화를 켜 놓고
   * 끌 수단이 없으면 사용자는 「일시정지」가 그 일을 한다는 것을 추측해야 한다.
   */
  it("녹화 중에는 「기록 멈추기」가 화면에 있다", () => {
    renderAi("recording");
    const stop = document.querySelector('[data-action="step.recordStop"]');
    expect(stop, "녹화를 끄는 조작이 화면에 없다").not.toBeNull();
  });

  /**
   * 되돌아온 자리에 **쓸 칸이 실제로 있는가.** 잠긴 자리는 보이기만 하므로
   * (`ChatPanel` 의 「자리는 보이되 잠긴다」), 잠기지 않았음을 함께 본다.
   */
  it("일시정지에서 AI 에게 쓸 칸이 열려 있다 — 돌아가는 길이 이어진다", () => {
    renderAi("paused");
    const box = document.querySelector('[data-action="ai.chat"]');
    expect(box, "AI 에게 말하는 자리가 화면에 없다").not.toBeNull();
    expect((box as HTMLTextAreaElement | HTMLButtonElement).disabled).toBe(false);
  });
});
