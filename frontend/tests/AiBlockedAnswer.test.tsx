/**
 * 2026-09-10 UI/UX 점검 — **AI 에게 답해서 이어 가는 칸이 실제로 쓸 만한가.**
 *
 * 답 칸 자체는 이미 있고 `AiFailureVisible.test.tsx` 가 그 존재와 전송을 지킨다. 여기서
 * 지키는 것은 **그 칸에 손과 눈이 닿는가**다.
 *
 * 1. **초점이 온다.** 막힘은 세션이 멈춘 상태다. 초점을 옮기지 않으면 키보드로 도는
 *    사용자는 화면 어딘가에 새로 생긴 칸을 Tab 으로 찾아야 한다.
 * 2. **질문을 읽을 수 있는 형태로 그린다.** 질문이 `.lbl`(11px 대문자 모노)에 들어가
 *    있었다 — 한 문장을 읽는 형태가 아니다.
 * 3. **손을 옮기지 않고 보낼 수 있다.** `Enter` 는 줄바꿈이어야 하므로(여러 줄로
 *    설명하는 것이 정상) `Cmd`/`Ctrl` + `Enter` 를 받고, **화면이 그 사실을 말한다.**
 * 4. **글자를 치는 순간 줄이 사라지지 않는다.** 힌트가 조건부로 그려지면 첫 글자에
 *    아래가 위로 튄다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

const base = {
  attempted: 'click role=button "저장"',
  reason: "AI 가 더 진행하지 못했습니다.",
  choices: ["takeover", "answer", "retry"],
};

function mount(over: { question?: string | null } = {}, onChooseBlocked?: (c: string, a?: string) => void) {
  return render(
    <SessionWorkbench
      {...sessionProps({
        view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
        aiBlocked: { ...base, question: over.question ?? null },
        ...(onChooseBlocked ? { onChooseBlocked } : {}),
      })}
    />,
  );
}

const box = () => document.querySelector("#blocked-answer") as HTMLTextAreaElement;
const send = () => document.querySelector("[data-blocked-answer-send]") as HTMLButtonElement;

afterEach(cleanup);

describe("초점", () => {
  it("막히면 답 칸에 초점이 온다 — 멈춘 화면에서 초점을 빼앗을 다른 일이 없다", () => {
    mount({ question: "어느 프로젝트로 로그인합니까?" });
    expect(document.activeElement).toBe(box());
  });

  it("질문이 없어도 초점은 온다 — 물을 것을 특정하지 못한 채 막히는 경우가 있다", () => {
    mount();
    expect(document.activeElement).toBe(box());
  });
});

describe("질문을 읽을 수 있는가", () => {
  it("질문은 이름표가 아니라 본문이다", () => {
    mount({ question: "어느 프로젝트로 로그인합니까?" });
    const q = document.querySelector("[data-blocked-question]") as HTMLElement;
    expect(q).not.toBeNull();
    expect(q.textContent).toBe("어느 프로젝트로 로그인합니까?");
    // 015 — `.answer-q` 가 유틸리티로 해체됐다. **묻는 것은 그대로다**: 질문이
    // 이름표(`.lbl`, 11px 대문자 모노)가 아니라 본문 형태인가. 라벨 형태로 한 문장을
    // 읽게 하면 읽히지 않는다는 것이 정본의 판단이다.
    expect(q.className, "질문이 이름표 형태다 — 한 문장을 읽는 형태가 아니다").not.toContain("uppercase");
    expect(q.className, "질문이 본문 크기가 아니다").toContain("text-[13px]");
    // 이름표에 문장을 담지 않는다 — `.lbl` 은 짧은 이름만 갖는다.
    const label = document.querySelector('label[for="blocked-answer"]') as HTMLElement;
    expect(label.textContent).toBe("AI 의 질문");
  });

  it("질문이 없으면 본문 자리를 만들지 않고 이름표만 바뀐다", () => {
    mount();
    expect(document.querySelector("[data-blocked-question]")).toBeNull();
    expect(
      (document.querySelector('label[for="blocked-answer"]') as HTMLElement).textContent,
    ).toBe("AI 에게 알려 주기");
  });
});

describe("보내는 길", () => {
  it("`Cmd` + `Enter` 로 보낸다", () => {
    const chosen: [string, string | undefined][] = [];
    mount({}, (choice, answer) => chosen.push([choice, answer]));
    fireEvent.change(box(), { target: { value: "TEST 프로젝트입니다." } });
    fireEvent.keyDown(box(), { key: "Enter", metaKey: true });
    expect(chosen).toEqual([["answer", "TEST 프로젝트입니다."]]);
  });

  it("`Ctrl` + `Enter` 도 같다 — 도구는 두 운영체제에서 돈다", () => {
    const chosen: [string, string | undefined][] = [];
    mount({}, (choice, answer) => chosen.push([choice, answer]));
    fireEvent.change(box(), { target: { value: "등록 버튼입니다." } });
    fireEvent.keyDown(box(), { key: "Enter", ctrlKey: true });
    expect(chosen).toEqual([["answer", "등록 버튼입니다."]]);
  });

  it("맨 `Enter` 는 보내지 않는다 — 여러 줄로 설명하는 것이 정상이다", () => {
    const chosen: string[] = [];
    mount({}, (choice) => chosen.push(choice));
    fireEvent.change(box(), { target: { value: "첫 줄" } });
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(chosen).toEqual([]);
  });

  it("빈 칸에서는 단축키도 보내지 않는다", () => {
    const chosen: string[] = [];
    mount({}, (choice) => chosen.push(choice));
    fireEvent.keyDown(box(), { key: "Enter", metaKey: true });
    expect(chosen).toEqual([]);
    expect(send().disabled).toBe(true);
  });

  it("단축키가 있다는 것을 화면이 말한다 — 말하지 않는 단축키는 없는 것과 같다", () => {
    mount();
    fireEvent.change(box(), { target: { value: "등록 버튼입니다." } });
    expect(screen.getByText(/Cmd\/Ctrl \+ Enter/)).toBeTruthy();
  });
});

describe("자리가 흔들리지 않는가", () => {
  it("힌트 줄은 글자를 쳐도 사라지지 않는다", () => {
    mount();
    const before = document.querySelectorAll("[data-blocked-answer] [data-hint-line]").length;
    expect(before).toBe(1);
    fireEvent.change(box(), { target: { value: "한 글자" } });
    expect(document.querySelectorAll("[data-blocked-answer] [data-hint-line]").length).toBe(1);
  });

  it("여러 줄을 적을 자리를 준다", () => {
    mount();
    expect(box().rows).toBeGreaterThanOrEqual(3);
  });
});

describe("선택지", () => {
  it("`answer` 는 버튼으로 중복되지 않는다 — 같은 조작이 두 자리를 갖지 않는다", () => {
    mount();
    expect(screen.queryByRole("button", { name: "답하고 AI 에게 돌려주기" })).toBeNull();
    expect(send()).not.toBeNull();
  });

  it("답을 보낸 뒤 칸이 비워진다 — 다음 질문에 앞의 답이 남아 있으면 잘못 보낸다", () => {
    const chosen: unknown[] = [];
    mount({}, (...args) => chosen.push(args));
    fireEvent.change(box(), { target: { value: "답" } });
    fireEvent.click(send());
    expect(box().value).toBe("");
  });
});

describe("`answer` 가 선택지에 없으면", () => {
  it("칸을 그리지 않는다 — 서버가 받지 않는 길을 열지 않는다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({
          view: sessionView({ state: "ai_blocked", authoring_mode: "ai" }),
          aiBlocked: { ...base, question: null, choices: ["takeover", "retry"] },
        })}
      />,
    );
    expect(document.querySelector("[data-blocked-answer]")).toBeNull();
    // 선택지 버튼 쪽에도 나타나지 않는다 — 목록에서 걸러지는 것이 아니라 애초에 없다.
    expect(screen.queryByRole("button", { name: "답하고 AI 에게 돌려주기" })).toBeNull();
  });
});
