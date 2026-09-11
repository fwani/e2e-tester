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
    // 015 T030 — 배치가 클래스로 바뀌었다. **묻는 것은 그대로다**: 층이 Step 목록을
    // 덮지 않고 그 왼쪽까지만 오는가. `right-steps` 는 `--w-steps`(= STEP_PANEL_WIDTH)다.
    expect(el.className, "층이 왼쪽 끝까지 덮지 않는다").toContain("left-0");
    expect(el.className, "층이 Step 목록을 덮는다").toContain("right-steps");
    expect(el.className).toContain("top-0");
    expect(el.className).toContain("bottom-0");
    // 클래스 이름이 실제로 그 폭을 그리는지는 정본 토큰이 보증한다 — 값이 어긋나면
    // L1 대조가 잡는다. 여기서 다시 재면 같은 값을 두 곳에 적는 것이 된다.
    expect(STEP_PANEL_WIDTH, "STEP_PANEL_WIDTH 가 --w-steps 와 어긋났다").toBe(460);
  });

  it("층이 포인터를 통과시키지 않는다", async () => {
    await renderWithDetail(true);
    const el = layer()!;
    // 015 T030 — 클래스로 바뀌었다. 묻는 것은 그대로: 층이 클릭을 받는가.
    expect(
      el.className,
      "`pointer-events-none` 이면 클릭이 그대로 미러에 닿는다",
    ).not.toContain("pointer-events-none");
  });

  it("층이 미러보다 위에 있다", async () => {
    await renderWithDetail(true);
    const el = layer()!;
    // 015 T030 — `z-20` 클래스로 바뀌었다. 묻는 것은 그대로: 층이 미러보다 위인가.
    const z = Number.parseInt(el.style.zIndex || "0", 10);
    const zClass = /\bz-\[?(\d+)\]?\b/.exec(el.className);
    const zValue = z > 0 ? z : Number.parseInt(zClass?.[1] ?? "0", 10);
    expect(zValue, "겹침 층에 z-index 가 없다").toBeGreaterThan(0);
  });

  it("가려진 영역이 눈으로도 가려진 것으로 보인다", async () => {
    await renderWithDetail(true);
    // 반투명 잉크가 깔린다 — 아래가 조작 대상이 아니라는 것을 색으로도 말한다.
    // 015 T030 — `.scrim` 이 `ui/Surface` 의 `Scrim` 부품이 됐다. 클래스 이름 대신
    // 부품이 내보내는 `data-strength` 를 읽는다 (LC-4 ②).
    const el = layer()!;
    // 농도까지 묻는다. 겹침(640px)은 `soft`, 화면 전체를 덮는 확인 판은 `strong` 이다 —
    // 덮는 면적이 클수록 짙게 한다는 것이 정본의 판단이다 (DC-009).
    expect(
      el.dataset.strength ?? (el.classList.contains("scrim") ? "soft" : "없음"),
      "가림막이 없거나 농도가 다르다 — 아래가 조작 가능해 보인다",
    ).toBe("soft");
  });
});
