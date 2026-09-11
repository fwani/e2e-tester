/**
 * 행의 `⋮` 메뉴는 잘리지 않는다 (사용자 보고 · 2026-09-09).
 *
 * ## 보고된 것
 *
 * > 메뉴 누르면 선택지가 아래로 생기는데, z 값이 낮아서 안보임
 *
 * ## 왜 그랬나 — z 값이 아니라 **잘림**이었다
 *
 * 메뉴는 행 안에 `position: absolute; z-index: 5` 로 있었다. 그 위로 조상 **셋**이 잘라
 * 낸다 — 목록 스크롤 상자(`overflow: auto`), 그것을 감싼 `.pane`(`overflow: hidden`),
 * 바깥 아트보드다. `overflow` 가 `visible` 이 아닌 조상은 자식을 잘라 내고, **`z-index`
 * 를 아무리 올려도 거기서 빠져나갈 수 없다.** 값을 올리는 수정이었다면 아무 일도 일어나지
 * 않았을 것이다.
 *
 * 실측(Chromium 1440×900 · 40행 · 목록을 끝까지 내린 상태):
 *
 * | | 마지막 행 메뉴 | 그 자리에 실제로 잡히는 것 |
 * |---|---|---|
 * | 고치기 전 | `top=844 bottom=942`, 스크롤 상자가 845 에서 자름 | 바닥 띠의 「Playwright 로 내보내기」 |
 * | 고친 뒤 | `top=710 bottom=808` (위로 열림) | 메뉴의 「편집」 |
 *
 * ## 이 파일이 재는 것
 *
 * 잘림도 겹침도 브라우저의 레이아웃 결과이고 jsdom 은 그것을 계산하지 않는다. 그래서
 * `WorkbenchHeight.test.tsx` 와 같은 방식으로 **결과가 아니라 구조**를 잰다 — 메뉴가
 * 잘라 내는 조상 **밖**에 있는가. 밖에 있으면 잘릴 수 없다.
 */
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";

const LISTING = {
  counts: { total: 1, pass: 1, fail: 0 },
  problems: [],
  tests: [
    {
      id: "TC-001",
      name: "로그인",
      step_count: 3,
      authoring_mode: "record",
      outcome: "pass",
      last_run_at: null,
      failure_summary: null,
    },
  ],
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(LISTING), { status: 200 })),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

const noop = () => undefined;

async function openRowMenu() {
  render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} onOpenDefinition={noop} />);
  await waitFor(() => expect(screen.getByText("로그인")).toBeTruthy());
  act(() => screen.getByRole("button", { name: "로그인 추가 동작" }).click());
  const menu = document.querySelector<HTMLElement>("[data-row-menu]");
  expect(menu, "메뉴가 열리지 않았다").not.toBeNull();
  return menu as HTMLElement;
}

describe("행 메뉴는 잘라 내는 조상 밖에 있다", () => {
  it("메뉴는 행 안이 아니라 문서 바닥에 붙는다", async () => {
    const menu = await openRowMenu();
    // 행 안에 있으면 목록 스크롤 상자와 `.pane` 이 잘라 낸다 — 그것이 보고된 결함이다.
    expect(menu.closest("[data-test-row]")).toBeNull();
    expect(menu.parentElement).toBe(document.body);
  });

  it("자리는 창 기준이다 — 스크롤 상자 안의 자리로 잡으면 다시 잘린다", async () => {
    const menu = await openRowMenu();
    expect(menu.style.position).toBe("fixed");
  });

  it("메뉴 항목은 그대로 있다 — 자리를 옮긴 것이지 없앤 것이 아니다", async () => {
    const menu = await openRowMenu();
    // 015 — `.navlink` 가 유틸리티로 해체돼 셀렉터로 찾을 수 없다. 자리 표식을 붙였다.
    // 자리를 찾는 일에 모양을 쓰는 것이 애초에 약한 결합이었다.
    const labels = [...menu.querySelectorAll("[data-row-menu-item]")].map((b) => b.textContent);
    expect(labels).toEqual(["편집", "이름", "삭제"]);
  });

  it("닫으면 문서에서 사라진다 — 떠 있는 채로 남지 않는다", async () => {
    await openRowMenu();
    act(() => screen.getByRole("button", { name: "로그인 추가 동작" }).click());
    expect(document.querySelector("[data-row-menu]")).toBeNull();
  });
});
