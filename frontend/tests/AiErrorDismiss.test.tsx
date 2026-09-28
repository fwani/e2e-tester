/**
 * **지나간 실패는 치울 수 있다** (2026-09-28 사용자 보고).
 *
 * > 「ai 대화 현황에서, 확인이 필요합니다 부분은, 한번 뜨면 제거가 안됨.
 * > x 표시로 제거가능하게 해줘」
 *
 * `aiError` 를 `null` 로 되돌리는 길이 **하나도 없었다.** 설정은 두 곳에서 하는데
 * (`ai_error`·`rerecord_realign_failed`) 해제가 없어, 한 번 뜨면 세션이 끝날 때까지
 * 남았다 — AI 작성 중 실패는 세션을 끝내지 않으므로(FR-067) 그 뒤로도 작성이
 * 이어지는데, 다음 턴이 성공해도 붉은 문장이 그대로였다.
 *
 * ## 무엇을 재는가
 *
 * 닫는 수단이 **있는가**, 눌렀을 때 소유자에게 **닿는가**, 그리고 닫을 수 없어야 하는
 * 것(막힘)이 **여전히 닫히지 않는가**. 셋째가 요점이다 — 막힘은 선택지를 고르기 전까지
 * 세션이 서 있는 상태이고, 닫으면 고를 곳이 사라진다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import type { ErrorInfo } from "../src/components/ErrorNotice";
import type { AiBlockedState } from "../src/components/workbench/model";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

afterEach(cleanup);

const AI_ERROR: ErrorInfo = {
  message: "요소를 찾지 못했습니다.",
  nextAction: "다시 시도하거나, 직접 이어받아 Step을 만들 수 있습니다.",
  category: "blocked",
  code: "AI_FAILED",
};

const BLOCKED: AiBlockedState = {
  reason: "어느 계정으로 로그인할지 모르겠습니다.",
  attempted: "로그인 버튼 클릭",
  question: "어느 계정을 쓸까요?",
  kind: "needs_input",
  choices: ["retry", "skip", "takeover", "abort", "answer"],
};

function renderAi(overrides: Parameters<typeof sessionProps>[0] = {}) {
  return render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state: "ai_running", authoring_mode: "ai" }),
        aiInstruction: "로그인해",
        ...overrides,
      })}
    />,
  );
}

describe("AI 실패 배너를 닫을 수 있다 (2026-09-28 사용자 보고)", () => {
  it("**닫는 수단이 있다** — 실패가 떠 있으면 X 가 함께 선다", () => {
    renderAi({ aiError: AI_ERROR, onDismissAiError: () => undefined });
    expect(screen.getByText("확인이 필요합니다"), "실패 배너가 뜨지 않았다").toBeTruthy();
    expect(
      screen.getByRole("button", { name: "이 알림 닫기" }),
      "닫는 수단이 없다 — 한 번 뜨면 치울 수 없다",
    ).toBeTruthy();
  });

  it("누르면 **소유자에게 닿는다** — 배너를 들고 있는 쪽이 지운다", async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();
    renderAi({ aiError: AI_ERROR, onDismissAiError: onDismiss });

    await user.click(screen.getByRole("button", { name: "이 알림 닫기" }));
    expect(onDismiss, "닫기를 눌렀는데 소유자에게 닿지 않았다").toHaveBeenCalledTimes(1);
  });

  it("치울 길을 **주지 않으면 X 가 서지 않는다**", () => {
    /*
      조작의 결과를 그 자리에서 말하는 알림은 닫히면 안 된다. 그래서 닫기는 기본이
      아니라 **준 자리에만** 선다 — `onDismissNotice` 와 같은 규율이다.
    */
    renderAi({ aiError: AI_ERROR });
    expect(screen.queryByRole("button", { name: "이 알림 닫기" })).toBeNull();
  });

  it("**막힘은 닫히지 않는다** — 선택지를 고르기 전까지 세션이 서 있다", () => {
    renderAi({ aiBlocked: BLOCKED, onDismissAiError: () => undefined });
    expect(screen.getByText("AI 가 막혔습니다"), "막힘이 뜨지 않았다").toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "이 알림 닫기" }),
      "막힘에 닫기가 생겼다 — 닫으면 선택지를 고를 곳이 사라진다",
    ).toBeNull();
  });
});
