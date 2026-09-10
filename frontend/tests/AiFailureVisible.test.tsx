/**
 * 007 T044 — **AI 실패와 차단은 국면·세션 상태와 무관하게 보인다** (FR-218f · FR-253).
 *
 * 001 research R2 가 규명한 결함이 정확히 이것이었다 — `ai_error` 를 렌더하는 유일한
 * 컴포넌트가 `isAiSession` 조건 뒤에 숨어, 실패가 상태에 담겨도 화면에 도달하지 못했다.
 * 002 가 그것을 고쳤지만 구멍이 옮겨졌을 뿐이다: AI 수행이 실패하면 세션이 검토를 위해
 * `paused` 로 가고, 그러면 조건이 다시 거짓이 됐다 (003 AP-032).
 *
 * 통합 화면에서 그 결함이 되살아날 수 있는 자리는 **국면 판정** 하나다. 그래서 여기서는
 * 일곱 국면 중 세션으로 만들 수 있는 다섯을 전부 돌며 같은 사실을 확인한다 —
 * "이 국면에서는 안 보인다" 는 예외가 하나라도 생기면 그것이 그 결함이다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ErrorInfo } from "../src/components/ErrorNotice";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import type { SessionState } from "../src/api/client";
import { phaseOfSession } from "../src/lib/phase";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

const REASON = "저장 버튼을 찾지 못했습니다";

const aiError: ErrorInfo = {
  message: REASON,
  nextAction: "다시 시도하거나, 직접 이어받아 Step을 만들 수 있습니다.",
  category: "blocked",
  code: "UNKNOWN",
};

const blocked = {
  attempted: 'click role=button "저장"',
  reason: "AI 가 더 진행하지 못했습니다.",
  question: null,
  choices: ["takeover", "answer", "retry"],
};

/**
 * 선택지의 표시 문구 (2026-09-10).
 *
 * 이전에는 서버가 준 값(`takeover`)이 그대로 버튼 글자였고 이 검사도 그 값으로 찾았다.
 * **검사가 영어 식별자를 화면 문구로 굳히고 있었던 것이다** — 사전이 생겼으므로 검사도
 * 사전을 지난다.
 */
const CHOICE_LABEL: Record<string, string> = {
  takeover: "직접 조작해 이어가기",
  retry: "AI 에게 다시",
};

/**
 * 세션으로 만들 수 있는 다섯 국면. `authoring_mode` 는 전부 `ai` 다 — AI 세션이
 * 국면을 옮겨 다니는 것이 이 결함의 조건이었기 때문이다.
 */
const STATES: SessionState[] = [
  "ai_running",
  "ai_blocked",
  "takeover_recording",
  "paused",
  "review",
];

afterEach(cleanup);

describe("AI 실패 사유 (FR-253 · 001 R2 · 003 AP-032)", () => {
  it.each(STATES)("%s 상태에서도 사유가 화면에 있다", (state) => {
    const view = sessionView({ state, authoring_mode: "ai" });
    render(<SessionWorkbench {...sessionProps({ view, aiError })} />);
    expect(
      screen.getByText(REASON),
      `${state}(국면 ${phaseOfSession(view)})에서 사유가 사라졌다`,
    ).toBeTruthy();
  });

  it.each(STATES)("%s 상태에서 사유가 alert 로 전달된다", (state) => {
    render(
      <SessionWorkbench
        {...sessionProps({ view: sessionView({ state, authoring_mode: "ai" }), aiError })}
      />,
    );
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });

  it("실행 중 국면처럼 AI 와 무관해 보이는 자리에서도 사라지지 않는다", () => {
    // `authoring_mode` 가 `ai` 인 세션이 `replaying` 으로 갈 일은 흔치 않지만, 국면
    // 판정이 바뀌어도 사유가 남는지가 이 파일의 질문이다.
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "replaying", authoring_mode: "ai" }),
          aiError,
        })}
      />,
    );
    expect(screen.getByText(REASON)).toBeTruthy();
  });

  it("사유가 없으면 지어내지 않는다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({ view: sessionView({ state: "ai_running", authoring_mode: "ai" }) })}
      />,
    );
    expect(screen.queryByText(REASON)).toBeNull();
  });
});

describe("AI 차단 선택지 (FR-069·FR-070 · FR-218f)", () => {
  it.each(["ai_running", "ai_blocked", "takeover_recording"] as SessionState[])(
    "%s 상태에서 차단 사유와 선택지가 조건 없이 보인다",
    (state) => {
      render(
        <SessionWorkbench
          {...sessionProps({
            view: sessionView({ state, authoring_mode: "ai" }),
            aiBlocked: blocked,
          })}
        />,
      );
      expect(document.querySelector("[data-always-visible-failure]")).not.toBeNull();
      expect(screen.getByText("AI 가 더 진행하지 못했습니다.")).toBeTruthy();
      for (const [choice, label] of Object.entries(CHOICE_LABEL)) {
        expect(blocked.choices).toContain(choice);
        expect(screen.getByRole("button", { name: label })).toBeTruthy();
      }
      /*
        2026-09-10 — `answer` 는 **버튼이 아니라 답 칸**이다. 같은 조작을 두 자리에 두면
        사용자는 둘이 다른 것인지 확인하느라 멈춘다 (FR-235).
      */
      expect(document.querySelector("[data-blocked-answer]")).not.toBeNull();
      expect(screen.queryByRole("button", { name: "answer" })).toBeNull();
    },
  );
});

describe("AI 에게 답해서 이어 가기 (2026-09-10 사용자 결정)", () => {
  it("질문이 있으면 답 칸이 그 질문을 걸고 열린다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
          aiBlocked: { ...blocked, question: "어느 프로젝트를 삭제할까요?" },
        })}
      />,
    );
    expect(screen.getByText(/어느 프로젝트를 삭제할까요\?/)).toBeTruthy();
  });

  it("답을 적어야 보낼 수 있다 — 빈 답은 AI 를 헛돌게 한다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
          aiBlocked: blocked,
        })}
      />,
    );
    const send = document.querySelector("[data-blocked-answer-send]") as HTMLButtonElement;
    expect(send.disabled).toBe(true);
  });

  it("적은 답이 `answer` 선택과 함께 나간다", async () => {
    const chosen: [string, string | undefined][] = [];
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
          aiBlocked: blocked,
          onChooseBlocked: (choice: string, answer?: string) => chosen.push([choice, answer]),
        })}
      />,
    );
    const box = document.querySelector("#blocked-answer") as HTMLTextAreaElement;
    fireEvent.change(box, { target: { value: "TEST 프로젝트입니다." } });
    fireEvent.click(document.querySelector("[data-blocked-answer-send]")!);

    expect(chosen).toEqual([["answer", "TEST 프로젝트입니다."]]);
  });
});

describe("작성 국면의 Step 결말 (T045 · FR-225 · S-08·S-09)", () => {
  it("AI 가 만든 Step 은 「통과」가 아니라 「기록됨」이다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_running", authoring_mode: "ai" }),
          outcomeOf: () => "recorded",
        })}
      />,
    );
    // 확정 결말이 아닌데 체크 표식을 그리던 것이 S-09 였다.
    expect(document.querySelectorAll("[data-outcome='recorded']").length).toBeGreaterThan(0);
    expect(document.querySelector("[data-outcome='pass']")).toBeNull();
    expect(screen.getAllByLabelText("기록됨").length).toBeGreaterThan(0);
  });

  it("AI 작성 국면에도 Step 번호가 있다 (S-08 · FR-224)", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_running", authoring_mode: "ai" }),
          outcomeOf: () => "recorded",
        })}
      />,
    );
    const numbers = [...document.querySelectorAll("[data-cell='number']")].map(
      (n) => n.textContent,
    );
    expect(numbers).toEqual(["01", "02"]);
  });
});
