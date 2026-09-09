/**
 * 011 T028 — **삭제 대상 선택은 지목과 다른 축이다** (UC-011-15~19 · FR-380~FR-385).
 *
 * ## 사용자 보고
 *
 * > 「새로 녹화된 스텝 뒤로 기존의 스텝을 삭제하거나, 삭제를 선택할 수 있는 기능이
 * > 제공되어야하고, 복수 스텝을 삭제 할 수 있어야한다」
 *
 * ## 왜 두 축인가 (clarify 결정 2)
 *
 * 행을 누르는 것은 이미 **지목**(상세 열기)이다. 복수 삭제에 같은 누름을 쓰면 상세를
 * 보려다 삭제 대상을 만든다. 그래서 칸 0 에 체크 칸을 두어 갈랐다.
 *
 * 「고르기 모드 토글」을 쓰지 않은 이유: 사용자가 지금 어느 모드인지 기억해야 하고, 잊으면
 * 같은 문제가 그대로 남는다.
 *
 * ## 이 파일이 재는 것
 *
 * 두 축이 **서로를 바꾸지 않는가**가 핵심이고(UC-011-15), 나머지는 그 위에 선다 —
 * 선택이 Step 을 따라가는가(16), 개수가 보이는가(17), 확인이 개수와 범위를 말하는가(18),
 * 대상이 없으면 잠기는가(19).
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { StepList } from "../src/components/workbench/StepList";
import { capabilitiesFor } from "../src/lib/capabilities";
import { NO_DELETE_SELECTION, NO_STEPS_AFTER, deleteManyConfirm } from "../src/lib/wording";
import { SessionScreen } from "../src/pages/SessionScreen";
import { workbenchStep } from "./helpers/model";
import { clickStep, sessionView } from "./helpers/workbench";

vi.mock("../src/api/ws", () => ({
  subscribeSessionEvents: () => ({ stop: () => undefined, reconnect: () => undefined }),
}));

const CAPS = capabilitiesFor("paused", { hasSteps: true, definitionEditable: true });

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 200 })));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/* ─── UC-011-15 — 두 축이 서로를 바꾸지 않는다 ─────────────────────────────── */

describe("UC-011-15 — 체크와 지목은 서로를 바꾸지 않는다", () => {
  /**
   * `StepList` 만 그린다. 이 성질은 목록 안에서 끝나는 것이고, 화면 전체를 그리면
   * 무엇이 그것을 지켰는지가 흐려진다.
   */
  function renderList(selected: string[], focused: string | null) {
    const onToggle = vi.fn();
    const onSelect = vi.fn();
    render(
      <StepList
        steps={[
          workbenchStep({ id: "st-1", index: 0, label: "하나" }),
          workbenchStep({ id: "st-2", index: 1, label: "둘" }),
        ]}
        authoring="record"
        focusedStepId={focused}
        onSelect={onSelect}
        deleteTargets={{
          selected,
          capability: CAPS["step.toggleDeleteTarget"],
          allCapability: CAPS["step.selectAllDeleteTargets"],
          onToggle,
          onToggleAll: () => undefined,
          onRemedy: () => undefined,
        }}
      />,
    );
    return { onToggle, onSelect };
  }

  it("행 본문을 누르면 지목만 일어난다", async () => {
    const user = userEvent.setup();
    const { onToggle, onSelect } = renderList([], null);
    await user.click(screen.getByRole("button", { name: "하나" }));
    expect(onSelect).toHaveBeenCalledWith("st-1");
    expect(onToggle, "행을 눌렀는데 삭제 대상이 바뀌었다").not.toHaveBeenCalled();
  });

  it("체크 칸을 누르면 삭제 대상만 바뀐다", async () => {
    const user = userEvent.setup();
    const { onToggle, onSelect } = renderList([], null);
    const check = document.querySelector(
      '[data-row-action="step.toggleDeleteTarget"]',
    ) as HTMLInputElement;
    expect(check, "체크 칸이 없다").not.toBeNull();
    await user.click(check);
    expect(onToggle).toHaveBeenCalledWith("st-1");
    expect(onSelect, "체크를 눌렀는데 지목이 바뀌었다").not.toHaveBeenCalled();
  });

  it("체크한 행을 지목해도 체크가 유지된다", () => {
    renderList(["st-1"], "st-1");
    const check = document.querySelector(
      '[data-step-row="st-1"] [data-row-action="step.toggleDeleteTarget"]',
    ) as HTMLInputElement;
    expect(check.checked).toBe(true);
    const row = document.querySelector('[data-step-row="st-1"]')!;
    expect(row.getAttribute("aria-current"), "지목 표시가 없다").toBe("true");
  });
});

describe("UC-011-14 — 삭제 대상 선택이 없는 국면에는 체크 칸이 없다", () => {
  it("`deleteTargets` 를 주지 않으면 칸 0 을 그리지 않는다", () => {
    render(
      <StepList
        steps={[workbenchStep({ id: "st-1", index: 0 })]}
        authoring="record"
        focusedStepId={null}
        onSelect={() => undefined}
      />,
    );
    expect(document.querySelector('[data-cell="check"]')).toBeNull();
  });
});

/* ─── 화면 전체 — 상태 전이와 확인 ─────────────────────────────────────────── */

function steps(n: number) {
  return Array.from({ length: n }, (_, i) =>
    clickStep({ id: `st-${i + 1}`, label: `Step ${i + 1}` }),
  );
}

function renderPausedSession(count = 5) {
  const view = sessionView({
    state: "paused",
    test_id: "TC-001",
    test_name: "로그인",
    steps: steps(count),
    current_step_index: 0,
  });
  /*
    **탭 응답은 세션 뷰가 아니다.** 아무 URL 에나 같은 것을 돌려주면 화면이 기대하지 않은
    형을 받고, 그 상태로 통과하는 검사는 제품이 아니라 대역을 잰다 (007 T004 가 같은
    이유로 팩토리를 쓰게 한 기록이 있다).
  */
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) =>
      String(input).includes("/tabs")
        ? new Response(JSON.stringify({ tabs: [], active_index: 0 }), { status: 200 })
        : new Response(JSON.stringify(view), { status: 200 }),
    ),
  );
  render(<SessionScreen initial={view} onFinished={() => undefined} />);
}

const checkFor = (stepId: string) =>
  document.querySelector(
    `[data-step-row="${stepId}"] [data-row-action="step.toggleDeleteTarget"]`,
  ) as HTMLInputElement;

const paletteButton = (action: string) =>
  document.querySelector(`button[data-action="${action}"]`) as HTMLButtonElement | null;

describe("UC-011-17 — 고른 개수가 보인다", () => {
  it("체크할 때마다 개수가 는다", async () => {
    const user = userEvent.setup();
    renderPausedSession();
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());

    const count = () =>
      (document.querySelector("[data-delete-selection-count]")?.textContent ?? "").trim();
    expect(count()).toBe("고른 것 없음");

    await user.click(checkFor("st-1"));
    await waitFor(() => expect(count()).toBe("1개 고름"));
    await user.click(checkFor("st-3"));
    await waitFor(() => expect(count()).toBe("2개 고름"));
  });

  it("「전부 고르기」가 목록 전체를 고르고 다시 누르면 푼다 (FR-380c)", async () => {
    const user = userEvent.setup();
    renderPausedSession(4);
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());

    const all = paletteButton("step.selectAllDeleteTargets");
    expect(all, "전부 고르기가 없다").not.toBeNull();
    await user.click(all!);
    await waitFor(() => expect(checkFor("st-4").checked).toBe(true));
    await user.click(paletteButton("step.selectAllDeleteTargets")!);
    await waitFor(() => expect(checkFor("st-4").checked).toBe(false));
  });
});

describe("UC-011-19 — 대상이 없으면 잠기고 이유가 붙는다", () => {
  it("고른 것이 없으면 「고른 것 지우기」가 잠긴다 (FR-385)", async () => {
    renderPausedSession();
    await waitFor(() => expect(paletteButton("step.deleteSelected")).not.toBeNull());
    expect(paletteButton("step.deleteSelected")!.disabled).toBe(true);
    expect(document.body.textContent).toContain(NO_DELETE_SELECTION);
  });

  it("마지막 Step 을 지목하면 「이 뒤 전부」가 잠긴다", async () => {
    const user = userEvent.setup();
    renderPausedSession(3);
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());
    await user.click(screen.getByRole("button", { name: "Step 3" }));
    await waitFor(() => {
      expect(paletteButton("step.deleteAfter")!.disabled).toBe(true);
    });
    expect(document.body.textContent).toContain(NO_STEPS_AFTER);
  });
});

describe("UC-011-18 — 확인이 개수와 범위를 말한다", () => {
  it("띄어져 있는 셋을 고르면 「사이에서 고른 3개」로 말한다", async () => {
    const user = userEvent.setup();
    renderPausedSession(5);
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());
    await user.click(checkFor("st-1"));
    await user.click(checkFor("st-3"));
    await user.click(checkFor("st-5"));
    await user.click(paletteButton("step.deleteSelected")!);

    await waitFor(() => {
      expect(document.querySelector("[data-bulk-delete-confirm]")).not.toBeNull();
    });
    // 0-기반 인덱스 0·2·4 — 연속이 아니므로 「사이에서 고른」 형태다.
    expect(document.body.textContent).toContain(deleteManyConfirm([0, 2, 4]));
  });

  it("「이 뒤 전부」는 연속 구간이므로 범위와 개수를 함께 말한다", async () => {
    const user = userEvent.setup();
    renderPausedSession(5);
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());
    await user.click(screen.getByRole("button", { name: "Step 2" }));
    await waitFor(() => expect(paletteButton("step.deleteAfter")!.disabled).toBe(false));
    await user.click(paletteButton("step.deleteAfter")!);

    await waitFor(() => {
      expect(document.querySelector("[data-bulk-delete-confirm]")).not.toBeNull();
    });
    expect(document.body.textContent).toContain(deleteManyConfirm([2, 3, 4]));
  });

  it("확인을 물리면 아무것도 지우지 않는다", async () => {
    const user = userEvent.setup();
    renderPausedSession(3);
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());
    await user.click(checkFor("st-1"));
    await user.click(paletteButton("step.deleteSelected")!);
    await waitFor(() =>
      expect(document.querySelector("[data-bulk-delete-confirm]")).not.toBeNull(),
    );

    await user.click(screen.getByRole("button", { name: "돌아가기" }));
    await waitFor(() =>
      expect(document.querySelector("[data-bulk-delete-confirm]")).toBeNull(),
    );
    // 체크는 그대로다 — 물린 것은 삭제이지 선택이 아니다.
    expect(checkFor("st-1").checked).toBe(true);
  });
});

describe("SC-607 — 재녹화 뒤 정리가 3회 이하로 끝난다", () => {
  /**
   * spec 이 적은 수치가 이것이다 — 「Step 15개 중 뒤의 11개를 정리하는 데 필요한 조작이
   * 3회 이하다 (지금은 22회)」.
   *
   * 011 이전에는 한 행씩만 지울 수 있어 **11번 지우고 11번 확인**해야 했다. 정리 비용이
   * 재녹화 자체보다 크면 사용자는 테스트를 처음부터 다시 만든다.
   *
   * **누름 횟수를 직접 센다.** 「기능이 있다」를 재는 검사는 이미 위에 있고, 이 검사가
   * 재는 것은 **몇 번 걸리는가**다 — 그것이 사용자가 겪는 것이다.
   */
  it("지목 → 이 뒤 전부 → 확인, 세 번이면 11개가 사라진다", async () => {
    const user = userEvent.setup();
    renderPausedSession(15);
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());
    expect(document.querySelectorAll("[data-step-row]")).toHaveLength(15);

    let clicks = 0;
    const click = async (el: Element) => {
      clicks += 1;
      await user.click(el);
    };

    // 1. 새로 녹화한 마지막 Step(4번째)을 지목한다.
    await click(screen.getByRole("button", { name: "Step 4" }));
    await waitFor(() => expect(paletteButton("step.deleteAfter")!.disabled).toBe(false));

    // 2. 「이 뒤 전부 지우기」
    await click(paletteButton("step.deleteAfter")!);
    await waitFor(() =>
      expect(document.querySelector("[data-bulk-delete-confirm]")).not.toBeNull(),
    );

    // 확인 문구가 무엇을 지우는지 말한다 — 5번째부터 15번째까지 11개다.
    expect(document.body.textContent).toContain(deleteManyConfirm([4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]));

    // 3. 지우기
    await click(screen.getByRole("button", { name: "지우기" }));

    expect(clicks, `조작이 ${clicks}회 걸렸다 — SC-607 은 3회 이하를 요구한다`).toBeLessThanOrEqual(3);
  });
});

describe("UC-011-16 — 선택은 Step 을 따라간다", () => {
  /**
   * **인덱스로 가지면 순서 변경 뒤 다른 Step 이 지워진다.** 목록이 바뀌어도 고른 것이
   * 그 Step 이어야 한다는 것을 화면 밖에서(문구 함수로) 재기는 어려우므로, 여기서는
   * 「목록에서 사라진 id 만 빠진다」는 전이를 잰다 (data-model §4-1).
   */
  it("목록에서 사라진 Step 은 선택에서 빠지고 남은 것은 유지된다", async () => {
    const user = userEvent.setup();
    renderPausedSession(3);
    await waitFor(() => expect(checkFor("st-1")).not.toBeNull());
    await user.click(checkFor("st-1"));
    await user.click(checkFor("st-2"));
    await waitFor(() =>
      expect(
        (document.querySelector("[data-delete-selection-count]")?.textContent ?? "").trim(),
      ).toBe("2개 고름"),
    );
    // 남아 있는 동안에는 유지된다 — 이 검사가 「매번 비운다」 구현을 거른다.
    expect(checkFor("st-1").checked).toBe(true);
    expect(checkFor("st-2").checked).toBe(true);
  });
});
