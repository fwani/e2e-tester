/**
 * AI 작성 국면의 실패 표시. DR-016·DR-020 · SC-104·SC-105.
 *
 * **이것이 이 라운드에서 가장 중요한 프런트엔드 회귀 테스트다.**
 *
 * 사용자가 겪은 것: "AI로 만들기를 눌러도 아무 일도 일어나지 않는다."
 * 실체는 이랬다 (research R2) — 서버는 `ai_error` 를 제대로 발행했고 화면은 그것을
 * 상태에 담기까지 했는데, 그 값을 그리는 유일한 컴포넌트가
 *
 *     const isAiSession = ["ai_running","ai_blocked"].includes(view.state) || messages.length > 0
 *
 * 뒤에 숨어 있었다. 실패 직후 세션이 `paused` 로 가고 진행 메시지가 하나도 없으면
 * 조건이 거짓이 되어 **실패 사유가 화면에 도달하지 못했다.**
 *
 * 그래서 여기서 확인하는 것은 "실패가 보인다" 가 아니라
 * **"세션 상태·메시지 유무와 무관하게 보인다"** 다.
 *
 * **007 이행 4** — `AiRecord` 화면이 사라지고 AI 작성 국면이 통합 화면의 한 상태가 됐다.
 * 지시문 작성(세션 이전)은 `AiCompose` 가 맡는다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { ErrorInfo } from "../src/components/ErrorNotice";

import { AiCompose } from "../src/pages/AiCompose";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

/** 003 에서 오류 prop 이 문자열에서 ErrorInfo 로 바뀌었다 — 다음 행동을 함께 나르기 위해서다. */
const failure = (message: string): ErrorInfo => ({
  message,
  // 001 FR-067 — 실패해도 그때까지의 Step 은 보존된다. 그 사실이 다음 행동에 실려 온다.
  nextAction: "다시 시도하거나 직접 이어받으세요. 기록된 Step은 남아 있습니다.",
  category: "blocked",
  code: "UNKNOWN",
});

function ai(overrides: Record<string, unknown> = {}, state = "ai_running") {
  return sessionProps({
    view: sessionView({
      state: state as never,
      authoring_mode: "ai",
      test_id: null,
      steps: [],
    }),
    aiInstruction: "로그인한 다음 프로젝트를 만들어",
    outcomeOf: () => "recorded",
    ...overrides,
  });
}

const REASON =
  "언어모델 자격 증명을 찾을 수 없습니다. `ANTHROPIC_API_KEY` 를 환경 변수로 주세요.";

afterEach(cleanup);

describe("AI 작성 국면 — 실패는 언제나 보인다 (DR-020)", () => {
  it("진행 메시지가 하나도 없어도 실패 사유를 그린다", () => {
    // 001 이 못 그리던 바로 그 조합이다: 메시지 0건 + AI 가 이미 멈춘 세션.
    render(<SessionWorkbench {...ai({ aiError: failure(REASON), aiMessages: [] })} />);
    expect(screen.getByText(REASON)).toBeTruthy();
  });

  it("세션 상태가 무엇이든 실패 사유를 그린다 (research R2 의 뿌리)", () => {
    // AI 가 실패하면 세션이 검토를 위해 `paused` 로 옮겨간다. 그때 사유가 사라지던
    // 것이 001·003 AP-032 였다.
    render(<SessionWorkbench {...ai({ aiError: failure(REASON) }, "paused")} />);
    expect(screen.getByText(REASON)).toBeTruthy();
  });

  it("실패해도 그때까지의 Step 이 보존됨을 알린다 (001 FR-067)", () => {
    render(<SessionWorkbench {...ai({ aiError: failure(REASON) })} />);
    expect(screen.getByText(/기록된 Step은 남아 있습니다/)).toBeTruthy();
  });

  it("오류는 alert 역할로 노출된다 — 조용히 지나가지 않는다", () => {
    render(<SessionWorkbench {...ai({ aiError: failure(REASON) })} />);
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  it("실패가 없으면 실패 영역을 그리지 않는다", () => {
    render(<SessionWorkbench {...ai({ aiError: null })} />);
    expect(document.querySelector("[data-always-visible-failure]")).toBeNull();
  });
});

describe("AI 작성 국면 — 상태 표시 (DR-016)", () => {
  it("수행 중이면 국면 표시가 그렇게 말한다", () => {
    render(<SessionWorkbench {...ai()} />);
    expect(document.querySelector("[data-phase-pill]")?.textContent).toBe("AI 작성 중");
  });

  it("지시문이 화면에 남는다 — 무엇을 시켰는지 잃지 않는다 (UX U-07)", () => {
    render(<SessionWorkbench {...ai()} />);
    expect(screen.getByText("로그인한 다음 프로젝트를 만들어")).toBeTruthy();
  });
});

describe("AI 작성 국면 — 저장 (001 FR-028·FR-029·FR-064)", () => {
  it("Step 이 없으면 저장할 수 없고 이유가 붙는다", () => {
    render(<SessionWorkbench {...ai({ saveName: "이름" })} />);
    const save = document.querySelector('button[data-action="save"]') as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    expect(screen.getByText("Step 이 없으면 저장할 수 없습니다.")).toBeTruthy();
  });
});

describe("지시문 작성 (AiCompose)", () => {
  it("지시문을 쓰는 자리가 있다", () => {
    render(<AiCompose startUrl="http://t/" onCancel={() => undefined} onStarted={() => undefined} />);
    expect(screen.getByText("지시문 작성")).toBeTruthy();
    expect(screen.getByLabelText("자연어 지시")).toBeTruthy();
  });

  it("지시문이 저장되지 않는다는 것을 알린다 (FR-064)", () => {
    render(<AiCompose startUrl="http://t/" onCancel={() => undefined} onStarted={() => undefined} />);
    expect(screen.getByText(/지시문은 테스트로 저장되지 않습니다/)).toBeTruthy();
  });

  it("지시문이 비면 실행할 수 없다", () => {
    render(<AiCompose startUrl="http://t/" onCancel={() => undefined} onStarted={() => undefined} />);
    expect((screen.getByRole("button", { name: "AI 실행 →" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
