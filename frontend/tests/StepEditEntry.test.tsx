import { revealTool } from "./helpers/toolPanel";
/**
 * 026 US4 — 편집 화면의 **두 AI 입구가 갈리는가** (FR-031·FR-032·FR-003).
 *
 * ## 이 파일이 재는 것
 *
 * 1. **두 조작이 나란히 있고 결과를 말한다** — 「고른 Step 을 버림」과 「남김」
 * 2. **잠금 사유가 서로 다르다** — 선택 조건이 다르므로 같은 문장이면 사용자는 어느
 *    쪽을 만족시켜야 하는지 알 수 없다
 * 3. **고른 개수별 상태가 표대로다** — 0개 / 1개 / 2개 연속 / 2개 불연속
 *
 * 이것이 이 기능의 주요 UX 위험이다. 백엔드가 동작해도 두 입구가 닮아 보이면 사용자는
 * 누를 때마다 차이를 확인하느라 멈춘다 (011 FR-235 가 막으려는 상태).
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditView } from "../src/pages/EditView";
import { clickStep, definitionView, runResult, test as makeTest } from "./helpers/workbench";

const FOUR = [
  clickStep({ id: "st-1" }),
  clickStep({ id: "st-2" }),
  clickStep({ id: "st-3" }),
  clickStep({ id: "st-4" }),
] as const satisfies readonly [unknown, ...unknown[]];

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(
          JSON.stringify(
            definitionView({
              test: makeTest({
                steps: [...FOUR] as NonNullable<Parameters<typeof makeTest>[0]>["steps"],
              }),
            }),
          ),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify(runResult()), { status: 200 });
    }),
  );
}

async function renderEdit(overrides: Partial<Parameters<typeof EditView>[0]> = {}) {
  stubFetch();
  render(
    <EditView
      testId="TC-001"
      focusStepId={null}
      onBack={() => undefined}
      onRun={() => undefined}
      onOpenBrowserAt={() => undefined}
      onOpenSession={() => undefined}
      {...overrides}
    />,
  );
  await waitFor(() =>
    expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
  );
}

/**
 * Step 을 **지목한다** — 목록에서 이름을 누른다 (`step.select`).
 *
 * 체크 칸(`check`)과 **다른 일이다.** 2026-09-30 사용자 보고로 갈렸다:
 *
 * > 「편집 화면에서는 AI 에게 고쳐 달라기 버튼이 전혀 눌리지 않는다」
 *
 * 026 은 체크 칸을 대상 지정에 썼고, 그래서 Step 을 눌러 고른 사용자에게도 버튼이
 * 잠긴 채 「고르세요」라고 말했다. 「이 Step 하나를 고쳐 달라」는 지목이다.
 */
async function pick(stepId: string) {
  const row = document.querySelector(`[data-step-row="${stepId}"]`);
  const nameButton = row?.querySelector("button") as HTMLButtonElement | null;
  expect(nameButton, `${stepId} 의 이름 버튼이 없다`).not.toBeNull();
  await userEvent.click(nameButton as HTMLButtonElement);
}

async function check(stepId: string) {
  const row = document.querySelector(`[data-step-row="${stepId}"]`);
  const box = row?.querySelector("input[type=checkbox]") as HTMLInputElement | null;
  expect(box, `${stepId} 의 체크 칸이 없다`).not.toBeNull();
  await userEvent.click(box as HTMLInputElement);
}

const btn = (action: string) =>
  document.querySelector(`button[data-action="${action}"]`) as HTMLButtonElement | null;

const rerecordBtn = () => btn("ai.rerecord");
const stepEditBtn = () => btn("ai.stepEdit");

/**
 * 잠금 사유는 버튼 옆의 사유 자리에 실린다 (`data-disabled-reason` · ui-contract §7).
 *
 * 버튼 본문이 아니라 **별도 자리**인 것이 017 이후의 구조다. 사유 전문은
 * `aria-describedby` 로 버튼에 묶인다.
 */
function reasonOf(action: string): string {
  const el = document.querySelector(`[data-disabled-reason="${action}"]`);
  return el?.textContent ?? "";
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("어느 패널에서 찾는가 (2026-09-30 사용자 보고)", () => {
  /*
    > 「계속 편집하는 스텝을 선택하라고 하는데 그런 것도 없음」

    조작은 등록돼 있었고 표도 화면도 온전했는데 **「Step 추가」 패널을 열어야** 보였다.
    Step 을 고치려는 사람이 「추가」를 열 이유가 없다.

    기존 검사가 이것을 못 잡은 이유: `revealTool()` 이 **어느 패널이든** 열어 주므로
    「있다」만 확인하고 「찾을 수 있다」는 확인하지 않았다. 자리를 검사로 고정한다.
  */
  it("**「Step 편집 도구」 안에 있다** — 「Step 추가」가 아니다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });

    const host = stepEditBtn()?.closest("[data-tool-name]");
    expect(host?.getAttribute("data-tool-name")).toBe("Step 편집 도구");
  });

  it("같은 패널에 **다른 Step 편집 조작들과 함께** 있다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });

    const host = stepEditBtn()?.closest("[data-tool-name]");
    // 고른 Step 에 대해 하는 일들이 한 자리에 모여야 사용자가 찾을 곳을 안다.
    expect(host?.querySelector('[data-action="step.delete"]')).not.toBeNull();
    expect(host?.querySelector('[data-action="step.moveUp"]')).not.toBeNull();
  });
});

describe("두 입구가 나란히 있다 (FR-031)", () => {
  it("편집 화면에 **둘 다** 있다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });
    expect(rerecordBtn(), "「AI 로 다시 만들기」가 없다").not.toBeNull();
    expect(stepEditBtn(), "「AI 에게 고쳐 달라기」가 없다").not.toBeNull();
  });

  it("**고른 Step 이 남는가**를 이름이 말한다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });
    // 둘 다 「AI 로 무언가 한다」이므로 이름만으로는 갈리지 않는다. 결과를 말해야 한다.
    expect(rerecordBtn()?.textContent).toContain("버림");
    expect(stepEditBtn()?.textContent).toContain("남김");
  });

  it("**브라우저가 열린다는 사실**을 둘 다 미리 말한다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });
    expect(rerecordBtn()?.textContent).toContain("브라우저");
    expect(stepEditBtn()?.textContent).toContain("브라우저");
  });
});

describe("잠금 사유가 서로 다르다 (FR-032)", () => {
  it("아무것도 고르지 않았을 때 — **다른 문장**이다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });

    const rerecord = reasonOf("ai.rerecord");
    const stepEdit = reasonOf("ai.stepEdit");

    expect(rerecord).toContain("다시 만들 Step");
    // **「목록에서 누르세요」** — 체크 칸이 아니라 지목을 요구한다는 것이 문구에 있어야
    // 한다. 「고르세요」만 말하면 사용자는 체크를 켜 놓고도 왜 안 풀리는지 모른다.
    expect(stepEdit).toContain("목록에서 누르세요");
    expect(rerecord).not.toBe(stepEdit);
  });

  it("**체크만 해서는 고치기가 풀리지 않는다** — 둘은 다른 고르기다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });

    await check("st-2");
    await check("st-3");

    // 체크는 **구간**을 정한다 — 재녹화의 것이다.
    expect(rerecordBtn()?.disabled).toBe(false);
    // 고치기는 지목을 본다. 체크를 몇 개 켜든 지목이 없으면 잠긴 채다.
    expect(stepEditBtn()?.disabled).toBe(true);
    expect(reasonOf("ai.stepEdit")).toContain("목록에서 누르세요");
  });

  it("불연속으로 체크했을 때 — 재녹화가 **이어진 Step** 을 요구한다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });

    await check("st-1");
    await check("st-3");

    expect(reasonOf("ai.rerecord")).toContain("이어진 Step");
  });
});

describe("고른 개수별 상태 (FR-003)", () => {
  it("**Step 을 누르면 고치기가 풀린다** (2026-09-30 사용자 보고)", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });

    expect(stepEditBtn()?.disabled, "누르기 전에는 잠겨 있다").toBe(true);

    await pick("st-2");

    expect(stepEditBtn()?.disabled, "Step 을 눌렀는데도 잠겨 있다").toBe(false);
  });

  it("지목한 Step 으로 시작한다 — **그 id 하나로**", async () => {
    const onStepEdit = vi.fn();
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit });

    await pick("st-3");
    await revealTool(stepEditBtn() as HTMLButtonElement);
    await userEvent.click(stepEditBtn() as HTMLButtonElement);

    expect(onStepEdit).toHaveBeenCalledWith("TC-001", "st-3");
  });

  it("체크와 지목이 다르면 **지목한 것**으로 시작한다", async () => {
    const onStepEdit = vi.fn();
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit });

    await check("st-1"); // 체크는 재녹화의 것
    await pick("st-3"); // 지목이 고치기의 것
    await revealTool(stepEditBtn() as HTMLButtonElement);
    await userEvent.click(stepEditBtn() as HTMLButtonElement);

    expect(onStepEdit).toHaveBeenCalledWith("TC-001", "st-3");
  });

  it("**잠긴 채로도 자리는 보인다** — 감추면 기능이 있다는 사실을 알 수 없다", async () => {
    await renderEdit({ onRerecordRange: vi.fn(), onStepEdit: vi.fn() });
    // 아무것도 고르지 않은 상태에서도 버튼이 화면에 남아 있다 (FR-234 · REASON_VISIBILITY)
    expect(stepEditBtn()).not.toBeNull();
    expect(stepEditBtn()?.disabled).toBe(true);
  });
});
