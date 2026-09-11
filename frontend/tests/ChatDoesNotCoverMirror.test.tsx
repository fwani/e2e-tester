/**
 * **대화가 미리보기를 덮지 않는다** (2026-09-11 사용자 보고 · 016).
 *
 * ## 보고된 것
 *
 * > 「ai 대화가 미리보기 화면을 덮쳐서 아무것도 보이지 않는다」
 *
 * 화면에는 대상 앱(미러)이 위에 있고 대화 패널이 아래에 있었는데, 대화 차례가 쌓이자
 * 미러가 브라우저 껍데기 두 줄만 남고 사라졌다.
 *
 * ## 왜 그랬나 — **S-12 와 같은 형태다**
 *
 * 016 이 대화 패널을 좌측 열의 셋째 자리로 걸면서(`Workbench` 의 `leftExtra`) **배분을
 * 아무도 정하지 않았다.** 선언이 없는 flex 자식은 `0 1 auto` 이고 그 최소 높이는 「내용
 * 전체」다. 위의 대상 앱 슬롯은 `flex-1`(basis 0)이라 더 줄일 것이 없으므로, 대화가
 * 길어질 때 생기는 음의 여백을 **미러가 전부 먹는다.**
 *
 * `lib/layout.ts` 가 존재하는 이유가 정확히 그 결함이었다 (spec S-12) — 자리가 둘에서
 * 셋으로 늘어날 때 배분표만 보고는 셋째가 빠진 것을 볼 수 없었다.
 *
 * ## 이 파일이 재는 것
 *
 * 높이는 브라우저의 레이아웃 결과이고 jsdom 은 그것을 계산하지 않는다. 그래서
 * `WorkbenchHeight.test.tsx` 와 같은 방식으로 **결과가 아니라 구조**를 잰다 — 상한을
 * 주는 선언과 줄어들 수 있다는 선언, 그리고 스크롤 영역이 제자리에 있는가. 셋이 있으면
 * 실제 브라우저에서 미러가 자리를 지킨다.
 *
 * 상한의 **값**은 구조가 아니라 산수이므로 따로 센다 (마지막 describe) — 세 자리의
 * 상한 합이 100% 를 넘으면 구조가 옳아도 미러가 눌린다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { CHAT_SLOT_CLASS, CONTENT_MAX_HEIGHT } from "../src/lib/layout";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import type { ChatTurn } from "../src/api/client";

import { canShrink, minHeightIsZero, scrolls } from "./helpers/style";

afterEach(cleanup);

/** 「높이 상한이 있는가」 — 없으면 이 자리가 내용만큼 늘어난다. */
function hasMaxHeight(el: HTMLElement): boolean {
  return el.style.maxHeight !== "" || /\bmax-h-/.test(el.className);
}

/** 대화가 길어진 상태를 만든다 — 그것이 보고된 조건이다. */
function manyTurns(count: number): ChatTurn[] {
  return Array.from({ length: count }, (_, i) => ({
    role: i % 2 === 0 ? ("user" as const) : ("assistant" as const),
    text: `${i + 1}번째 차례 — `.repeat(8),
    at: `2026-09-11T00:${String(i).padStart(2, "0")}:00Z`,
  }));
}

function renderWithChat(turns: ChatTurn[]) {
  return render(
    <SessionWorkbench
      {...sessionProps({ view: sessionView(), chatTurns: turns })}
    />,
  );
}

/** 대화 패널이 들어앉은 자리. `Workbench` 가 배분을 내려 주는 껍데기다. */
function chatSlot(): HTMLElement {
  const el = document.querySelector<HTMLElement>("[data-workbench-left-extra]");
  // 자리를 못 찾은 채 통과하면 이 파일이 재는 것이 하나도 없다
  expect(el, "대화 자리를 찾지 못했다 — 표식이 없어졌거나 자리가 사라졌다").not.toBeNull();
  return el!;
}

/** 대상 앱 슬롯. 미러가 사는 자리다. */
function targetSlot(): HTMLElement {
  const el = document.querySelector<HTMLElement>("[data-workbench-target]");
  expect(el, "대상 앱 슬롯을 찾지 못했다").not.toBeNull();
  return el!;
}

describe("대화 자리에 배분이 있다 (사용자 보고 2026-09-11)", () => {
  it("**대화가 길어도 자리에 높이 상한이 있다**", () => {
    renderWithChat(manyTurns(40));
    expect(
      hasMaxHeight(chatSlot()),
      "대화 자리에 높이 상한이 없다 — 차례가 쌓일수록 미러를 밀어낸다",
    ).toBe(true);
  });

  it("대화가 적을 때와 많을 때의 **선언이 같다**", () => {
    /*
      「내용이 늘면 늘어난다」가 결함이었으므로, 재는 것은 **내용과 무관하게 같은가**다.
      값이 같으면 그 자리는 대화 차례 수를 모른다.
    */
    const { unmount } = renderWithChat(manyTurns(1));
    const few = chatSlot().className;
    unmount();

    renderWithChat(manyTurns(60));
    expect(chatSlot().className).toBe(few);
  });

  it("자리는 **남는 높이를 가져가지 않는다** — 주 자리는 미러다", () => {
    /*
      세션이 있는 국면의 주 자리는 모두 미러다 (`PRIMARY_SLOT`). 대화 자리가 함께
      늘어나면 선언한 주 자리와 실제 배분이 어긋나고, 그것이 S-12 의 형태다.
    */
    renderWithChat(manyTurns(40));
    expect(
      /\bflex-1\b|\bflex-auto\b|\bgrow\b/.test(chatSlot().className),
      "대화 자리가 남는 높이를 가져간다 — 미러와 경쟁한다",
    ).toBe(false);
  });

  it("미러 자리가 **여전히 남는 높이를 갖는다**", () => {
    renderWithChat(manyTurns(40));
    const target = targetSlot();
    expect(/\bflex-1\b/.test(target.className), "대상 앱 슬롯이 남는 높이를 잃었다").toBe(true);
    expect(minHeightIsZero(target), "대상 앱 슬롯의 min-height 0 이 없어졌다").toBe(true);
  });

  it("자리의 **순서는 그대로다** — 미러 · 작업 영역 · 대화 (FR-218c)", () => {
    renderWithChat(manyTurns(3));
    const column = document.querySelector<HTMLElement>("[data-workbench-left-column]");
    expect(column, "좌측 열을 찾지 못했다").not.toBeNull();

    const slots = [...column!.children];
    expect(slots.indexOf(targetSlot())).toBe(0);
    expect(slots.indexOf(chatSlot())).toBe(slots.length - 1);
  });
});

describe("넘치는 것은 대화 기록이 자기 안에서 처리한다", () => {
  it("**패널이 자기 내용보다 작아질 수 있다** (min-height 0)", () => {
    /*
      상한만 있고 이 선언이 없으면 패널의 최소 높이가 대화 내용 전체로 남는다 —
      상한을 넘어 흘러나오고, 그때 흘러나온 부분이 아래의 것을 덮는다.
    */
    renderWithChat(manyTurns(40));
    const panel = screen.getByLabelText("AI 와 대화");
    expect(
      minHeightIsZero(panel as HTMLElement),
      "대화 패널이 자기 내용보다 작아질 수 없다 — 상한을 넘어 흘러나온다",
    ).toBe(true);
  });

  it("**대화 기록이 스크롤 영역이고, 자기 높이를 0 으로 줄일 수 있다**", () => {
    renderWithChat(manyTurns(40));
    const log = screen.getByLabelText("대화 기록") as HTMLElement;
    expect(scrolls(log), "대화 기록이 스크롤 영역이 아니다").toBe(true);
    expect(
      minHeightIsZero(log),
      "`min-height: 0` 이 없으면 스크롤 영역을 두고도 스크롤할 것이 남지 않는다",
    ).toBe(true);
  });

  it("**입력칸은 줄지 않는다** — 답이 길어져도 쓸 자리가 남는다", () => {
    /*
      줄어드는 자리가 기록 하나여야 한다. 입력칸까지 줄면 대화가 길어질수록 쓸 칸이
      납작해지고, 그 상태에서 사용자는 지시를 쓸 수 없다.
    */
    renderWithChat(manyTurns(40));
    const box = screen.getByLabelText("AI 에게 할 말");
    const form = box.closest("form");
    expect(form, "입력 폼을 찾지 못했다").not.toBeNull();
    expect(canShrink(form as HTMLElement), "입력 폼이 줄어든다 — 쓸 칸이 납작해진다").toBe(
      false,
    );
  });
});

describe("상한의 값 — 세 자리가 100% 를 넘지 않는다", () => {
  /** `max-h-[33%]` · `"45%"` 에서 백분율을 읽는다. */
  function percent(source: string): number {
    const m = /(\d+(?:\.\d+)?)%/.exec(source);
    expect(m, `백분율을 읽지 못했다: ${source}`).not.toBeNull();
    return Number.parseFloat(m![1] as string);
  }

  it("대화(③-c) + 작업 영역(③-b)의 상한 합이 100% 미만이다", () => {
    /*
      구조가 옳아도 값이 100% 를 넘으면 미러가 남는 높이를 못 받는다. `content` 의 45%
      는 ③-b 하나가 미러와 나눠 쓸 때의 값이었으므로, 자리가 셋이 된 지금은 합을 센다.
    */
    const sum = percent(CHAT_SLOT_CLASS) + percent(CONTENT_MAX_HEIGHT);
    expect(sum, "두 상한의 합이 100% 이상이다 — 미러에 남는 높이가 없다").toBeLessThan(100);
  });

  it("대화 자리가 **작업 영역보다 크지 않다** — 주 자리가 미러이기 때문이다", () => {
    expect(percent(CHAT_SLOT_CLASS)).toBeLessThanOrEqual(percent(CONTENT_MAX_HEIGHT));
  });
});
