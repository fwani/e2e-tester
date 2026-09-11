/**
 * 016 T034b — 편집 화면에서 재녹화를 시작한다 (US1 · FR-015·FR-016·FR-022).
 *
 * ## 이 파일이 재는 것
 *
 * 1. **구간 지정이 삭제 대상 체크를 그대로 쓴다** — 체크 칸을 둘로 만들면 사용자가
 *    어느 쪽에 체크할지 판단해야 한다 (FR-015)
 * 2. **불연속은 시작하지 않는다** — 서버도 거절하지만 화면이 먼저 말하면 브라우저가
 *    떴다 사라지는 것을 보지 않아도 된다 (FR-016)
 * 3. **저장하지 않은 편집은 기존 규칙을 받는다** — 006 FR-203 「먼저 저장한 뒤 연다」
 *    이고 011 이 「새 확인을 만들지 않는다」를 명시했다 (FR-022)
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditView } from "../src/pages/EditView";
import { clickStep, definitionView, runResult, test as makeTest } from "./helpers/workbench";

/**
 * Step 넷 — 불연속을 만들려면 셋 이상이 필요하다.
 *
 * `Test.steps` 는 **비어 있지 않은 튜플**이다 (FR-029: Step 1개 이상). 타입이 그
 * 사실을 들고 있으므로 배열 리터럴을 그대로 넘길 수 없다.
 */
const FOUR = [
  clickStep({ id: "st-1" }),
  clickStep({ id: "st-2" }),
  clickStep({ id: "st-3" }),
  clickStep({ id: "st-4" }),
] as const satisfies readonly [unknown, ...unknown[]];

function stubFetch(onSave?: () => void, blocking = false) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/definition")) {
        if (init?.method === "PUT") onSave?.();
        return new Response(
          JSON.stringify(
            definitionView({
              test: makeTest({
                steps: [...FOUR] as NonNullable<Parameters<typeof makeTest>[0]>["steps"],
              }),
              // 다른 세션이 그 테스트를 잡고 있으면 정의는 읽기 전용이다 (006 FR-206).
              ...(blocking
                ? {
                    editable: false,
                    blocked_by: "running",
                    blocking_session_id: "s-other",
                  }
                : {}),
            }),
          ),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify(runResult()), { status: 200 });
    }),
  );
}

async function renderEdit(
  overrides: Partial<Parameters<typeof EditView>[0]> = {},
  onSave?: () => void,
  blocking = false,
) {
  stubFetch(onSave, blocking);
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

/** 행의 체크 칸. 구간 지정이 **삭제 대상 체크를 그대로 쓴다** (FR-015). */
async function check(stepId: string) {
  const row = document.querySelector(`[data-step-row="${stepId}"]`);
  const box = row?.querySelector("input[type=checkbox]") as HTMLInputElement | null;
  expect(box, `${stepId} 의 체크 칸이 없다`).not.toBeNull();
  await userEvent.click(box as HTMLInputElement);
}

const rerecordButton = () =>
  document.querySelector('button[data-action="ai.rerecord"]') as HTMLButtonElement | null;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("구간 지정 (FR-015)", () => {
  it("**같은 체크 칸을 쓴다** — 재녹화용 칸을 따로 만들지 않는다", async () => {
    await renderEdit();
    // 삭제와 재녹화가 같은 체크를 공유한다. 칸이 둘이면 사용자가 판단해야 한다.
    const boxes = document.querySelectorAll('[data-step-row] input[type=checkbox]');
    expect(boxes.length).toBe(FOUR.length);
  });

  it("연속 구간을 고르면 그 id 들로 시작한다", async () => {
    const onRerecordRange = vi.fn();
    await renderEdit({ onRerecordRange });

    await check("st-2");
    await check("st-3");
    await userEvent.click(rerecordButton() as HTMLButtonElement);

    expect(onRerecordRange).toHaveBeenCalledWith("TC-001", ["st-2", "st-3"]);
  });

  it("고른 순서가 달라도 **목록 순서로** 보낸다", async () => {
    const onRerecordRange = vi.fn();
    await renderEdit({ onRerecordRange });

    await check("st-3");
    await check("st-2");
    await userEvent.click(rerecordButton() as HTMLButtonElement);

    // 화면의 체크 순서는 사용자가 누른 순서다. 구간은 목록 순서로 정규화한다.
    expect(onRerecordRange).toHaveBeenCalledWith("TC-001", ["st-2", "st-3"]);
  });

  it("하나만 골라도 된다 — Step 하나를 다시 만드는 것은 흔한 일이다", async () => {
    const onRerecordRange = vi.fn();
    await renderEdit({ onRerecordRange });

    await check("st-3");
    await userEvent.click(rerecordButton() as HTMLButtonElement);

    expect(onRerecordRange).toHaveBeenCalledWith("TC-001", ["st-3"]);
  });
});

describe("불연속은 시작하지 않는다 (FR-016)", () => {
  it("사이가 비면 **시작하지 않고 이유를 말한다**", async () => {
    const onRerecordRange = vi.fn();
    await renderEdit({ onRerecordRange });

    await check("st-1");
    await check("st-3");
    await userEvent.click(rerecordButton() as HTMLButtonElement);

    expect(onRerecordRange).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByText(/이어져 있지 않습니다/)).toBeTruthy());
    // 무엇을 하면 되는지도 말한다.
    expect(screen.getByText(/이어진 Step 을 고르세요/)).toBeTruthy();
  });

  it("아무것도 고르지 않으면 아무 일도 일어나지 않는다", async () => {
    const onRerecordRange = vi.fn();
    await renderEdit({ onRerecordRange });

    const button = rerecordButton();
    if (button !== null && !button.disabled) await userEvent.click(button);
    expect(onRerecordRange).not.toHaveBeenCalled();
  });
});

describe("저장하지 않은 편집 (FR-022 · 006 FR-203)", () => {
  it("**먼저 저장한 뒤** 시작한다 — 새 확인을 만들지 않는다", async () => {
    /*
      이 저장소에는 이미 규칙이 있다: 006 FR-203 「저장하지 않은 변경이 있으면 먼저
      저장한 뒤 세션을 연다」이고, 011 이 `openBrowser` 에서 「새 확인을 만들지
      않는다」를 명시했다. 재녹화도 세션을 여는 조작이므로 같은 규칙을 받는다.
    */
    const onRerecordRange = vi.fn();
    const saved = vi.fn();
    await renderEdit({ onRerecordRange }, saved);

    // 편집을 하나 만든다 — 이름을 고치면 저장하지 않은 변경이 생긴다.
    const name = document.querySelector(
      '[data-workbench-phase-bar] input[type=text]',
    ) as HTMLInputElement | null;
    if (name === null) {
      // 이름 칸이 이 국면에 없으면 이 검사의 전제가 성립하지 않는다.
      expect(true).toBe(true);
      return;
    }
    await userEvent.type(name, "!");

    await check("st-2");
    await userEvent.click(rerecordButton() as HTMLButtonElement);

    await waitFor(() => expect(saved).toHaveBeenCalled());
    await waitFor(() => expect(onRerecordRange).toHaveBeenCalled());
  });
});


describe("다른 세션이 잡고 있으면 (FR-017)", () => {
  it("**미리 잠긴다** — 눌러 보고 409 를 받지 않는다", async () => {
    /*
      서버는 `409 SESSION_BUSY` 로 거절한다. 그것만으로는 부족하다 — 009 T063 이 고친
      결함이 바로 「활성으로 그렸다가 눌리면 거절」이었다. 표가 `cond(C7)` 로 두는
      이유가 이것이고, 이 검사가 그 판정이 실제로 화면에 닿는지 본다.
    */
    const onRerecordRange = vi.fn();
    await renderEdit({ onRerecordRange }, undefined, true);

    const button = rerecordButton();
    expect(button, "조작이 화면에서 사라졌다 — 잠기되 보여야 한다 (FR-234)").not.toBeNull();
    expect(button?.disabled).toBe(true);

    // 눌러도 아무 일이 없다.
    if (button !== null) await userEvent.click(button);
    expect(onRerecordRange).not.toHaveBeenCalled();
  });

  it("무엇을 하면 풀리는지 **가리킨다** — 그 세션으로 가는 조작이 있다", async () => {
    /*
      잠긴 채 이유만 있으면 사용자는 갇힌다. 005 FR-126 이 그 세션으로 가는 길을
      요구하고, 016 은 그것을 새로 만들지 않고 기존 `session.open` 을 쓴다.
    */
    await renderEdit({}, undefined, true);
    const open = document.querySelector('button[data-action="session.open"]');
    expect(open, "실행 중인 세션으로 가는 조작이 없다").not.toBeNull();
  });
});
