/**
 * 011 T019 — **상세가 덮은 자리로 조작이 새지 않는다** (UC-011-9 · FR-373b).
 *
 * ## 왜 011 이 이 위험을 만들었나
 *
 * 010 이 미러 조작을 만들었다 — 미러 이미지가 포인터 이벤트를 받아 대상 브라우저로
 * 보낸다. 011 이 Step 상세를 **그 미러 위로** 옮겼다 (clarify 결정 1).
 *
 * 겹치는 판이 클릭을 삼키지 않으면, 사용자는 상세를 읽는 중에 그 아래 보이지 않는 곳을
 * 조작하게 된다. 대상 앱에서는 실제로 무언가 눌리고, 화면에는 그 결과가 보이지 않는다.
 *
 * ## 왜 구조를 재는가
 *
 * 이 성질은 브라우저의 히트 테스트 결과이고 jsdom 은 그것을 계산하지 않는다. 그래서
 * `PhaseBarWidth`·`WorkbenchHeight` 와 같은 방식으로 **결과가 아니라 구조**를 잰다 —
 * 가로막는 층이 실제로 그 영역을 덮고 있는가, 포인터를 통과시키지 않는가.
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { STEP_PANEL_WIDTH } from "../src/components/workbench/StepList";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

afterEach(cleanup);

async function renderWithDetail(detailOpen: boolean) {
  render(
    <SessionWorkbench
      {...sessionProps({
        // 미러가 살아 있는 국면이어야 이 위험이 성립한다.
        view: sessionView({ state: "recording", authoring_mode: "record" }),
        focusedStepId: "st-1",
        detailOpen,
      })}
    />,
  );
  await waitFor(() =>
    expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
  );
}

const layer = () => document.querySelector("[data-workbench-detail-layer]") as HTMLElement | null;

describe("UC-011-9 — 상세 층이 그 아래 미러를 가로막는다", () => {
  it("상세가 열리면 가로막는 층이 생긴다", async () => {
    await renderWithDetail(true);
    expect(layer(), "상세가 열렸는데 층이 없다").not.toBeNull();
  });

  it("상세가 닫혀 있으면 층이 없다 — 닫으면 미러가 그대로 살아난다", async () => {
    await renderWithDetail(false);
    expect(layer(), "상세가 닫혔는데 가로막는 층이 남아 있다").toBeNull();
  });

  it("층이 대상 앱 영역 전체를 덮는다 (Step 패널 폭만 남긴다)", async () => {
    await renderWithDetail(true);
    const el = layer()!;
    /*
      **`left` 가 있어야 한다.** 없으면 절대 배치 상자가 내용 폭으로 줄어들고, 판 옆의
      빈 자리에서 클릭이 미러에 닿는다 — 보이지 않는 곳을 조작하게 된다.
    */
    expect(el.style.left, "층이 왼쪽 끝까지 덮지 않는다").toBe("0px");
    expect(el.style.right).toBe(`${STEP_PANEL_WIDTH}px`);
    expect(el.style.top).toBe("0px");
    expect(el.style.bottom).toBe("0px");
  });

  it("층이 포인터를 통과시키지 않는다", async () => {
    await renderWithDetail(true);
    const el = layer()!;
    expect(
      el.style.pointerEvents,
      "`pointerEvents: none` 이면 클릭이 그대로 미러에 닿는다",
    ).not.toBe("none");
  });

  it("층이 미러보다 위에 있다", async () => {
    await renderWithDetail(true);
    const el = layer()!;
    const z = Number.parseInt(el.style.zIndex || "0", 10);
    expect(z, "겹침 층에 z-index 가 없다").toBeGreaterThan(0);
  });

  it("가려진 영역이 눈으로도 가려진 것으로 보인다", async () => {
    await renderWithDetail(true);
    // `.scrim` 이 반투명 잉크를 깐다 — 아래가 조작 대상이 아니라는 것을 색으로도 말한다.
    expect(layer()!.classList.contains("scrim")).toBe(true);
  });
});
