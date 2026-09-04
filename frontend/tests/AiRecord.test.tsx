/**
 * AI 작성 화면의 실패 표시. DR-016·DR-020 · SC-104·SC-105.
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
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { ErrorInfo } from "../src/components/ErrorNotice";

import { AiRecord } from "../src/pages/AiRecord";

/** 003 에서 오류 prop 이 문자열에서 ErrorInfo 로 바뀌었다 — 다음 행동을 함께 나르기 위해서다. */
const failure = (message: string): ErrorInfo => ({
  message,
  nextAction: "다시 시도하거나 직접 이어받으세요.",
  category: "blocked",
  code: "UNKNOWN",
});

const base = {
  instruction: "로그인한 다음 프로젝트를 만들어",
  running: false,
  steps: [],
  messages: [] as string[],
  error: null as ErrorInfo | null,
  blocked: null,
  saveName: "",
  onSaveNameChange: () => undefined,
  onSave: () => undefined,
};

const REASON =
  "언어모델 자격 증명을 찾을 수 없습니다. `ANTHROPIC_API_KEY` 를 환경 변수로 주세요.";

afterEach(cleanup);

describe("AiRecord — 실패는 언제나 보인다 (DR-020)", () => {
  it("진행 메시지가 하나도 없어도 실패 사유를 그린다", () => {
    // 001 이 못 그리던 바로 그 조합이다: 메시지 0건 + 세션이 이미 paused.
    render(<AiRecord {...base} error={failure(REASON)} />);

    expect(screen.getByText(REASON)).toBeTruthy();
    // 헤더 알약과 실패 영역 제목 둘 다 같은 문구를 쓴다.
    expect(screen.getAllByText("AI 수행 실패").length).toBe(2);
  });

  it("running 이 아니어도 실패 사유를 그린다", () => {
    render(<AiRecord {...base} running={false} error={failure(REASON)} />);
    expect(screen.getByText(REASON)).toBeTruthy();
  });

  it("실패해도 그때까지의 Step 이 보존됨을 알린다 (001 FR-067)", () => {
    render(<AiRecord {...base} error={failure(REASON)} steps={[]} />);
    expect(screen.getByText(/보존됐습니다/)).toBeTruthy();
  });

  it("오류는 alert 역할로 노출된다 — 조용히 지나가지 않는다", () => {
    render(<AiRecord {...base} error={failure(REASON)} />);
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  it("실패가 없으면 실패 영역을 그리지 않는다", () => {
    render(<AiRecord {...base} error={null} />);
    expect(screen.queryByText("AI 수행 실패")).toBeNull();
  });
});

describe("AiRecord — 상태 표시 (DR-016)", () => {
  it("실패하면 상태 알약이 실패를 말한다", () => {
    render(<AiRecord {...base} error={failure(REASON)} />);
    // 헤더의 알약과 실패 영역 제목 둘 다 "AI 수행 실패" 를 쓴다.
    expect(screen.getAllByText("AI 수행 실패").length).toBe(2);
  });

  it("수행 중이면 그렇게 말한다", () => {
    render(<AiRecord {...base} running />);
    expect(screen.getByText("AI 수행 중")).toBeTruthy();
  });

  it("지시문 작성 중이면 그렇게 말한다", () => {
    render(<AiRecord {...base} composing onInstructionChange={() => undefined} />);
    expect(screen.getByText("지시문 작성")).toBeTruthy();
    expect(screen.getByLabelText("자연어 지시")).toBeTruthy();
  });
});

describe("AiRecord — 저장 (001 FR-028·FR-029·FR-064)", () => {
  it("Step 이 없으면 저장할 수 없다", () => {
    render(<AiRecord {...base} saveName="이름" steps={[]} />);

    expect((screen.getByText("테스트로 저장") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Step 이 없으면 저장할 수 없습니다.")).toBeTruthy();
  });

  it("지시문이 저장되지 않는다는 것을 알린다 (FR-064)", () => {
    render(<AiRecord {...base} />);
    expect(screen.getByText(/지시문은 테스트로 저장되지 않습니다/)).toBeTruthy();
  });
});
