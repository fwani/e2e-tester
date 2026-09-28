/**
 * **AI 작성 현황은 하나의 대화다** (2026-09-28 사용자 요청).
 *
 * > 「ai 테스트 생성시, 작성현황에서 사람이 입력한 최초 프롬프트 부터 시작해서, ai 의
 * > 답변, 사람이 재입력한 내용등 대화형태처럼 확인하면 좋겠다」
 *
 * 그 전에는 한 흐름이 세 곳으로 갈려 있었다 — 최초 지시문은 **어디에도 없었고**, AI 의
 * 답과 사람의 재입력은 아래 대화 칸에, 수행 자취는 위 목록에 쌓였다.
 *
 * 이 파일이 재는 것은 넷이다.
 *
 * 1. 최초 지시문이 **첫 차례로** 선다 — 없으면 무엇을 시켜서 시작됐는지 알 수 없다.
 * 2. 사람·AI·사람이 **받은 순서 그대로** 한 자리에 선다.
 * 3. 같은 말이 **두 번 보이지 않는다** — 아래 대화 칸은 쓰는 자리로만 남는다.
 * 4. 자취는 대화에 **딸려** 있고 끌 수 있다.
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import type { AuthoringEntry } from "../src/components/workbench/AiAuthoringPanel";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

afterEach(cleanup);

const INSTRUCTION = "로그인하고 릴리즈 노트를 등록해";

/** 사람 → 자취 → AI → 사람 → 자취. 실제 한 턴의 모양이다. */
function log(): AuthoringEntry[] {
  return [
    { kind: "progress", text: "로그인 화면을 연다", at: "2026-09-28T00:00:01Z" },
    { kind: "progress", text: "계정을 입력한다", at: "2026-09-28T00:00:02Z" },
    { kind: "assistant", text: "로그인까지 Step 3개를 만들었습니다.", at: "2026-09-28T00:00:03Z" },
    { kind: "user", text: "릴리즈 노트 등록도 이어서 해줘", at: "2026-09-28T00:00:04Z" },
    { kind: "progress", text: "운영 관리로 이동한다", at: "2026-09-28T00:00:05Z" },
  ];
}

function renderAuthoring(entries: AuthoringEntry[] = log()) {
  return render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state: "ai_running", authoring_mode: "ai" }),
        aiInstruction: INSTRUCTION,
        authoringLog: entries,
      })}
    />,
  );
}

/** 작성 현황의 대화 자리. 못 찾으면 이 파일이 재는 것이 없다. */
function timeline(): HTMLElement {
  const el = document.getElementById("ai-authoring-log");
  expect(el, "작성 현황의 대화 기록 자리를 찾지 못했다").not.toBeNull();
  return el as HTMLElement;
}

describe("작성 현황이 한 줄기 대화로 보인다 (2026-09-28 사용자 요청)", () => {
  it("**최초 지시문이 첫 차례로 선다**", () => {
    renderAuthoring();
    const first = within(timeline()).getAllByRole("listitem")[0]!;
    expect(first.textContent, "첫 차례가 최초 지시문이 아니다").toContain(INSTRUCTION);
    expect(
      first.textContent,
      "최초 지시문임을 알 수 있는 표시가 없다 — 대화 도중의 말과 구별되지 않는다",
    ).toContain("처음 지시");
  });

  it("사람·AI·사람이 **받은 순서 그대로** 한 자리에 선다", () => {
    renderAuthoring();
    const text = timeline().textContent ?? "";
    const order = [
      INSTRUCTION,
      "로그인까지 Step 3개를 만들었습니다.",
      "릴리즈 노트 등록도 이어서 해줘",
    ].map((t) => text.indexOf(t));
    expect(order.every((i) => i >= 0), "대화 차례 가운데 보이지 않는 것이 있다").toBe(true);
    expect(
      [...order].sort((a, b) => a - b),
      "화면에 선 순서가 받은 순서와 다르다",
    ).toEqual(order);
  });

  it("같은 말이 **두 번 보이지 않는다** — 아래 대화 칸은 쓰는 자리다", () => {
    renderAuthoring();
    /*
      사이드바에서 대화 기록은 타임라인 하나다. 아래 칸이 같은 차례를 또 쌓으면 한
      화면에 같은 말이 두 번 보이고, 사용자는 둘이 다른 것인지 확인하느라 멈춘다.
    */
    expect(screen.queryByRole("log", { name: "대화 기록" })).toBeNull();
    expect(
      screen.getAllByText("릴리즈 노트 등록도 이어서 해줘"),
      "사람이 쓴 말이 두 자리에 보인다",
    ).toHaveLength(1);
    // 쓰는 자리는 그대로 있다 — 기록만 옮겼지 입구를 없앤 것이 아니다.
    expect(screen.getByLabelText("AI 에게 할 말")).toBeTruthy();
  });

  it("자취는 **대화에 딸려** 있고, 꺼서 대화만 볼 수 있다", async () => {
    const user = userEvent.setup();
    renderAuthoring();
    expect(timeline().textContent, "수행 자취가 보이지 않는다").toContain("운영 관리로 이동한다");

    await user.click(screen.getByRole("button", { name: "자취 숨기기" }));
    const after = timeline().textContent ?? "";
    expect(after, "자취를 껐는데 남아 있다").not.toContain("운영 관리로 이동한다");
    expect(after, "자취를 껐더니 대화까지 사라졌다").toContain(INSTRUCTION);
  });

  it("지시문이 없는 세션은 **없는 차례를 지어내지 않는다**", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_running", authoring_mode: "ai" }),
          aiInstruction: null,
          authoringLog: [{ kind: "assistant", text: "무엇을 만들까요?", at: "2026-09-28T00:00:00Z" }],
        })}
      />,
    );
    const items = within(timeline()).getAllByRole("listitem");
    expect(items).toHaveLength(1);
    expect(items[0]!.textContent).toContain("무엇을 만들까요?");
  });
});
