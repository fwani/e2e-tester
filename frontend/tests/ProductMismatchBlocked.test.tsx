/**
 * 제품 동작 불일치로 막히면 답 칸을 열지 않는다 (020 T040 · FR-024·FR-025·FR-026).
 *
 * ## 무엇이 문제였나
 *
 * 제품 결함으로 화면이 지시문과 달라져 AI 가 진행할 수 없을 때, 지금까지 그것은
 * 「요소를 찾지 못했다」로 보고됐다. 사용자는 힌트를 주며 시간을 쓴 뒤에야 제품
 * 문제였음을 알았다.
 *
 * 답 칸을 닫는 것이 그 시간을 없앤다. **막다른 길로 만들지는 않는다** — 사람이
 * 이어받는 길은 여전히 열려 있어야 한다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

const base = {
  attempted: 'click role=link "항목 목록"',
  reason: "저장 후 목록으로 돌아가지 않아 방금 만든 항목을 찾을 수 없습니다.",
  choices: ["takeover", "answer", "retry", "skip", "abort"],
};

function mount(kind: "needs_input" | "product_mismatch", question: string | null = null) {
  return render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
        aiBlocked: { ...base, kind, question },
      })}
    />,
  );
}

const answerBox = () => document.querySelector("#blocked-answer");
const note = () => document.querySelector("[data-blocked-product-mismatch]");

afterEach(cleanup);

describe("제품 동작 불일치 (FR-024)", () => {
  it("답 칸이 열리지 않는다", () => {
    mount("product_mismatch");
    expect(answerBox()).toBeNull();
  });

  it("모델이 규칙을 어겨 질문을 실어 보내도 칸이 열리지 않는다", () => {
    // 서버가 이미 질문을 버리지만(도구 쪽 방어), 화면도 종류를 보고 판단한다.
    // 겹은 둘이어야 한 겹이 새도 사용자가 답할 수 없는 질문 앞에 서지 않는다.
    mount("product_mismatch", "어느 목록을 말하는 건가요?");
    expect(answerBox()).toBeNull();
  });

  it("왜 답할 수 없는지를 화면이 말한다", () => {
    mount("product_mismatch");
    expect(note()).not.toBeNull();
    expect(note()!.textContent).toContain("제품이 지시문과 다르게 동작");
  });

  it("사유는 그대로 보인다 — 무엇이 막았는지는 여전히 필요하다", () => {
    mount("product_mismatch");
    expect(screen.getByText(base.reason)).toBeTruthy();
  });

  it("나머지 선택지는 그대로다 (FR-026)", () => {
    // 답변만 빠진다. 직접 수행·다시·건너뛰기·종료로 이어가는 길은 열려 있어야 한다 —
    // 막다른 길이 되면 사용자에게 남는 것은 세션을 버리는 것뿐이다.
    mount("product_mismatch");
    const actions = document.querySelector('[data-action="ai.chooseBlocked"]');
    expect(actions).not.toBeNull();
    expect(actions!.querySelectorAll("button").length).toBe(4);
  });
});

describe("기존 막힘은 바뀌지 않는다 (FR-025)", () => {
  it("알려 주면 풀리는 막힘에는 답 칸이 그대로 열린다", () => {
    mount("needs_input", "어느 계정으로 로그인합니까?");
    expect(answerBox()).not.toBeNull();
    expect(note()).toBeNull();
  });

  it("질문이 없어도 답 칸은 열린다 — 질문이 답변의 전제는 아니다", () => {
    mount("needs_input");
    expect(answerBox()).not.toBeNull();
  });
});
