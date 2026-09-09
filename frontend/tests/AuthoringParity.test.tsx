/**
 * 011 T037 — **녹화와 지시문이 대등하다** (UC-011-23·24·25 · FR-374~FR-379).
 *
 * ## 사용자 보고
 *
 * > 「스텝을 새로 녹화하는것처럼, ai 지시문으로도 스텝을 추가할 수 있어야한다」
 *
 * ## 무엇이 틀렸었나
 *
 * **조작은 이미 있었다.** 편집 국면 권한표에서 둘 다 이렇게 잠겨 있었을 뿐이다.
 *
 * ```
 * "step.recordStart":       off("NEEDS_BROWSER", "browser.openAt")
 * "step.addNaturalLanguage": off("NEEDS_BROWSER", "browser.openAt")
 * ```
 *
 * 해소 방법도 맞았다. 문제는 사용자가 **두 걸음**을 걸어야 했다는 것이고 — 브라우저를
 * 열고, 그다음에 지시문을 쓰고 — 그래서 「녹화처럼 되지 않는다」로 겪었다. 게다가 자연어
 * 입력칸은 버튼 줄 **위**에 따로 있고 녹화 시작은 버튼 줄 **안**에 다른 조작과 섞여 있어,
 * 두 길이 같은 무게로 보이지도 않았다.
 *
 * 009 가 `browser.openAt` 을 다섯 걸음에서 한 걸음으로 만든 것과 같은 종류의 수정이다.
 *
 * ## 이 파일이 재는 것
 *
 * 대등성은 **셋이 함께** 성립해야 한다.
 *
 * 1. 둘 다 브라우저 없이 눌린다 (UC-011-23)
 * 2. 둘 다 같은 묶음에 있다 — 자리와 무게
 * 3. 저장하지 않은 변경이 있으면 **기존** 확인이 걸린다. 새 확인을 만들지 않는다 (24)
 *
 * 그리고 실패 경로 하나 — 열기가 실패하면 시작한 것처럼 보이지 않는다 (25).
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { capabilityOf } from "../src/lib/capabilities";
import { DISABLED_REASON, SAVE_BEFORE_OPEN_BROWSER } from "../src/lib/wording";
import { EditView } from "../src/pages/EditView";
import { definitionView, runResult } from "./helpers/workbench";

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/definition")) {
        return new Response(JSON.stringify(definitionView()), { status: 200 });
      }
      return new Response(JSON.stringify(runResult()), { status: 200 });
    }),
  );
}

async function renderEdit(
  overrides: Partial<Parameters<typeof EditView>[0]> = {},
) {
  stubFetch();
  render(
    <EditView
      testId="TC-001"
      focusStepId="st-1"
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

const btn = (action: string) =>
  document.querySelector(`button[data-action="${action}"]`) as HTMLButtonElement | null;

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/* ─── 1. 권한표 — 브라우저를 요구하지 않는다 ───────────────────────────────── */

describe("UC-011-23 — 편집 국면에서 두 조작이 브라우저를 요구하지 않는다", () => {
  const FACTS = { hasSteps: true, definitionEditable: true };

  it.each(["step.recordStart", "step.addNaturalLanguage"] as const)(
    "%s 가 활성이다",
    (action) => {
      expect(capabilityOf("editing", action, FACTS).kind).toBe("enabled");
    },
  );

  it("`step.addAssertion` 은 그대로 잠긴다 — 요소 지목은 사용자가 해야 한다", () => {
    const state = capabilityOf("editing", "step.addAssertion", FACTS);
    expect(state.kind).toBe("disabled");
    if (state.kind === "disabled") {
      expect(state.reason).toBe(DISABLED_REASON.NEEDS_BROWSER);
      expect(state.remedy?.action).toBe("browser.openAt");
    }
  });

  it("다른 세션이 그 테스트를 잡고 있으면 둘 다 잠긴다", () => {
    const blocked = { ...FACTS, definitionEditable: false };
    const open = capabilityOf("editing", "browser.openAt", blocked);
    for (const action of ["step.recordStart", "step.addNaturalLanguage"] as const) {
      expect(capabilityOf("editing", action, blocked).kind).toBe(open.kind);
    }
  });
});

/* ─── 2. 자리와 무게 ───────────────────────────────────────────────────────── */

describe("FR-374 — 두 길이 같은 묶음에 같은 무게로 있다", () => {
  it("녹화 버튼과 지시문 입력칸이 같은 묶음 안에 있다", async () => {
    await renderEdit();
    const record = btn("step.recordStart");
    const nlInput = screen.getByLabelText("자연어로 Step 추가");
    expect(record, "녹화 조작이 없다").not.toBeNull();

    /*
      같은 부모 묶음을 공유하는지 본다. 좌표가 아니라 구조로 재는 이유는
      `PhaseBarWidth`·`WorkbenchHeight` 와 같다 — jsdom 은 배치를 계산하지 않는다.
    */
    const group = record!.closest("div")?.parentElement;
    expect(group?.contains(nlInput), "두 길이 다른 묶음에 있다").toBe(true);
  });

  it("둘 다 같은 형의 조작 버튼이다 — 하나가 더 무겁지 않다", async () => {
    await renderEdit();
    const record = btn("step.recordStart")!;
    const submit = btn("step.addNaturalLanguage")!;
    expect(record.className).toBe(submit.className);
  });
});

/* ─── 3. 저장하지 않은 변경 (UC-011-24) ────────────────────────────────────── */

describe("UC-011-24 — 기존 「저장하고 열기」가 그대로 걸린다", () => {
  it("저장하지 않은 변경이 있으면 그 사실을 미리 말한다", async () => {
    const user = userEvent.setup();
    await renderEdit();

    // 이름을 고쳐 저장하지 않은 변경을 만든다.
    const name = document.querySelector('[data-action="test.rename"]') as HTMLInputElement;
    await user.type(name, "!");

    await waitFor(() => {
      expect(document.body.textContent).toContain(SAVE_BEFORE_OPEN_BROWSER);
    });
  });

  it("새 확인 대화상자를 만들지 않는다", async () => {
    const user = userEvent.setup();
    await renderEdit();
    const name = document.querySelector('[data-action="test.rename"]') as HTMLInputElement;
    await user.type(name, "!");
    await user.click(btn("step.recordStart")!);
    /*
      기존 경로는 **먼저 저장한 뒤** 연다 (006 FR-203). 확인을 겹침 대화상자로 다시 묻지
      않는다 — 011 이 조작을 하나 더 만들면서 확인도 하나 더 만들면 사용자가 배운 흐름이
      갈린다.

      **「확인」 대화상자만 센다.** `role="dialog"` 로 세면 이미 열려 있는 Step 상세가
      걸린다 — 그것은 확인이 아니라 이 국면의 주 작업면이다.
    */
    const confirms = [...document.querySelectorAll('[role="dialog"]')].filter((d) =>
      (d.getAttribute("aria-label") ?? "").includes("확인"),
    );
    expect(confirms, "011 이 새 확인 대화상자를 만들었다").toHaveLength(0);
  });
});

/* ─── 5. 되돌릴 수 있는 경로 (FR-386) ──────────────────────────────────────── */

describe("FR-386 — 편집의 복수 삭제는 되돌릴 수 있다", () => {
  /**
   * 세션과 **성질이 다르다.** 편집은 연산을 쌓았다가 저장할 때 보내므로 「변경 전부
   * 되돌리기」로 되돌아간다 — 그래서 확인에 「되돌릴 수 없습니다」를 붙이지 않는다.
   *
   * 같은 확인 컴포넌트를 두 경로가 쓰므로, 한쪽만 재면 다른 쪽이 조용히 갈린다.
   */
  it("확인에 「되돌릴 수 없습니다」가 붙지 않는다", async () => {
    const user = userEvent.setup();
    await renderEdit();

    const check = document.querySelector(
      '[data-row-action="step.toggleDeleteTarget"]',
    ) as HTMLInputElement | null;
    expect(check, "편집 국면에 체크 칸이 없다").not.toBeNull();
    await user.click(check!);

    const del = document.querySelector(
      'button[data-action="step.deleteSelected"]',
    ) as HTMLButtonElement;
    await waitFor(() => expect(del.disabled).toBe(false));
    await user.click(del);

    await waitFor(() =>
      expect(document.querySelector("[data-bulk-delete-confirm]")).not.toBeNull(),
    );
    expect(
      document.querySelector("[data-bulk-delete-irreversible]"),
      "편집인데 되돌릴 수 없다고 말한다 — edits.revert 로 되돌아간다",
    ).toBeNull();
  });
});

/* ─── 4. 지시문이 실려 나간다 (FR-375) ─────────────────────────────────────── */

describe("FR-374a·FR-375 — 지시문이 목표 자리와 함께 실려 나간다", () => {
  it("지시문으로 더하기를 누르면 지목한 자리와 지시문이 함께 나간다", async () => {
    const user = userEvent.setup();
    const onOpenBrowserAt = vi.fn();
    await renderEdit({ onOpenBrowserAt });

    const nlInput = screen.getByLabelText("자연어로 Step 추가");
    await user.type(nlInput, "장바구니에 담아");
    await user.click(btn("step.addNaturalLanguage")!);

    await waitFor(() => expect(onOpenBrowserAt).toHaveBeenCalled());
    const [testId, , , instruction] = onOpenBrowserAt.mock.calls[0]!;
    expect(testId).toBe("TC-001");
    expect(instruction, "지시문이 실리지 않았다").toBe("장바구니에 담아");
  });

  /**
   * FR-377 — **명령과 기록은 다른 것이다.**
   *
   * `instructionOnArrival` 은 「도착하면 이것을 수행하라」이고 한 번 쓰이면 끝난다.
   * `aiInstruction` 은 「무엇을 시켰는가」라는 기록이며 화면에 계속 남아야 한다 —
   * 보이지 않으면 사용자는 자기가 무엇을 시켰는지 잃는다 (001 FR-063 · UX U-07).
   *
   * 수렴 1회차가 잡은 것이 이것이었다: 명령만 싣고 기록을 빠뜨렸다.
   */
  it("지시문이 세션의 기록으로도 실린다", async () => {
    const user = userEvent.setup();
    const onOpenBrowserAt = vi.fn();
    await renderEdit({ onOpenBrowserAt });

    await user.type(screen.getByLabelText("자연어로 Step 추가"), "장바구니에 담아");
    await user.click(btn("step.addNaturalLanguage")!);

    await waitFor(() => expect(onOpenBrowserAt).toHaveBeenCalled());
    /*
      `EditView` 는 네 번째 인자로 문장을 넘기고, `App` 이 그것을 **둘로** 나눠 싣는다
      (`instructionOnArrival` + `aiInstruction`). 여기서는 화면 경계까지만 재고, 둘로
      나뉘는지는 `App` 의 그 줄이 갖는다 — 이 검사가 재는 것은 문장이 실려 나간다는 것이다.
    */
    const [, , , instruction] = onOpenBrowserAt.mock.calls[0]!;
    expect(instruction).toBe("장바구니에 담아");
  });

  it("녹화로 더하기는 지시문 없이 나간다 — 도착하면 기록이 켜진다", async () => {
    const user = userEvent.setup();
    const onOpenBrowserAt = vi.fn();
    await renderEdit({ onOpenBrowserAt });

    await user.click(btn("step.recordStart")!);
    await waitFor(() => expect(onOpenBrowserAt).toHaveBeenCalled());
    const [, , , instruction] = onOpenBrowserAt.mock.calls[0]!;
    expect(instruction ?? null).toBeNull();
  });

  /**
   * UC-011-25 · FR-374c — **열기가 실패하면 시작하지 않는다.**
   *
   * 저장하지 않은 변경이 있으면 먼저 저장한 뒤 여는데(006 FR-203), 그 저장이 실패하면
   * 세션이 열리지 않아야 한다. 시작한 것처럼 보이면 사용자는 무엇이 남았는지 알 수 없다.
   */
  it("저장이 실패하면 브라우저를 열지 않고 사유를 남긴다", async () => {
    const user = userEvent.setup();
    const onOpenBrowserAt = vi.fn();

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/definition") && (init?.method ?? "GET") === "PUT") {
          return new Response(
            JSON.stringify({
              error: { code: "DEFINITION_INVALID", category: "blocked", message: "저장 실패" },
            }),
            { status: 400 },
          );
        }
        if (url.includes("/definition")) {
          return new Response(JSON.stringify(definitionView()), { status: 200 });
        }
        return new Response(JSON.stringify(runResult()), { status: 200 });
      }),
    );
    render(
      <EditView
        testId="TC-001"
        focusStepId="st-1"
        onBack={() => undefined}
        onRun={() => undefined}
        onOpenBrowserAt={onOpenBrowserAt}
        onOpenSession={() => undefined}
      />,
    );
    await waitFor(() =>
      expect(document.querySelector("[data-workbench-step-panel]")).not.toBeNull(),
    );

    // 저장하지 않은 변경을 만든 뒤 지시문으로 더하기를 누른다.
    const name = document.querySelector('[data-action="test.rename"]') as HTMLInputElement;
    await user.type(name, "!");
    const nlInput = screen.getByLabelText("자연어로 Step 추가");
    await user.type(nlInput, "장바구니에 담아");
    await user.click(btn("step.addNaturalLanguage")!);

    await waitFor(() => expect(document.body.textContent).toContain("저장 실패"));
    expect(onOpenBrowserAt, "저장이 실패했는데 세션을 열었다").not.toHaveBeenCalled();
  });

  it("빈 지시문으로는 나가지 않는다", async () => {
    const user = userEvent.setup();
    const onOpenBrowserAt = vi.fn();
    await renderEdit({ onOpenBrowserAt });

    await user.click(btn("step.addNaturalLanguage")!);
    expect(onOpenBrowserAt, "빈 지시문으로 브라우저를 열었다").not.toHaveBeenCalled();
  });
});
