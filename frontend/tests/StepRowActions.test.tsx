/**
 * 009 T051 — 행에서 바로 옮기고 지운다 (US3 · FR-298~FR-304 · SC-503·SC-504·SC-505·SC-507).
 *
 * **이 파일이 재는 것은 조작 횟수다.** 기능이 되는지는 서버 계약이 이미 보고 있다.
 * 여기서 보는 것은 「몇 번 누르는가」와 「어디를 누르는가」다 — 그것이 009 가 고치려는 것의
 * 전부이기 때문이다 (관찰 M-05·M-06·M-07).
 */
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EditView } from "../src/pages/EditView";
import { renderSession } from "./helpers/session";
import type { Step } from "../src/types/generated/step";

function step(n: number): Record<string, unknown> {
  return {
    id: `step-0${n}`,
    type: "navigate",
    label: `Step ${n} 이동`,
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    url: `/p${n}`,
  };
}

const SIX = [1, 2, 3, 4, 5, 6].map(step);

const TEST = {
  dsl_version: 1,
  id: "TC-001",
  name: "이동",
  authoring_mode: "record",
  start_url: "/p1",
  browser: "chromium",
  ai_instruction: null,
  variables: [],
  steps: SIX,
  created_at: "2026-09-08T00:00:00Z",
  updated_at: "2026-09-08T00:00:00Z",
};

function stubFetch() {
  const calls: { url: string; method: string; body: unknown }[] = [];
  const view = {
    test: TEST,
    revision: "rev-1",
    editable: true,
    blocked_by: null,
    blocking_session_id: null,
    locked_fields: [],
    warnings: [],
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      calls.push({
        url: String(url),
        method,
        body: init?.body ? JSON.parse(String(init.body)) : null,
      });
      if (method === "PUT") {
        return new Response(JSON.stringify({ ...view, revision: "rev-2" }), { status: 200 });
      }
      return new Response(JSON.stringify(view), { status: 200 });
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

/** 그 행의 그 조작. **행에서 집는다** — 화면 아래로 내려가지 않는다. */
function rowOp(stepId: string, action: string): HTMLButtonElement {
  const el = document.querySelector(
    `[data-step-row="${stepId}"] [data-row-action="${action}"]`,
  );
  expect(el, `${stepId} 행에 ${action} 이 없다`).not.toBeNull();
  return el as HTMLButtonElement;
}

function labels(): string[] {
  return [...document.querySelectorAll("[data-step-row]")].map(
    (r) => r.getAttribute("data-step-row") ?? "",
  );
}

async function renderEdit() {
  stubFetch();
  render(<EditView testId="TC-001" onBack={() => undefined} />);
  await waitFor(() => expect(screen.getByText("Step 1 이동")).toBeTruthy());
}

// ─── 1. 조작 횟수 (SC-503) ──────────────────────────────────────────────────

describe("세 칸 아래로 (SC-503 · FR-299)", () => {
  it("편집 화면 — 「아래로」 3회로 끝난다. 다른 Step 을 고르지 않는다", async () => {
    await renderEdit();
    let clicks = 0;

    for (let i = 0; i < 3; i += 1) {
      act(() => rowOp("step-02", "step.moveDown").click());
      clicks += 1;
    }

    expect(clicks).toBe(3);
    /*
      2번(자리 1)이 자리 4 로 갔다 — 세 번 눌러 세 칸 내려간다.

      **다른 Step 을 고르는 조작이 하나도 없다.** 이전에는 아래 Step 셋을 각각 고르고
      각각 올려야 해서 여섯 번이었다 (관찰 M-05).
    */
    expect(labels()).toEqual([
      "step-01",
      "step-03",
      "step-04",
      "step-05",
      "step-02",
      "step-06",
    ]);
  });

  it("일시정지 화면 — 별도 패널을 열지 않고 행에서 옮긴다", () => {
    const onApplyReorder = vi.fn();
    renderSession(
      { state: "paused", steps: SIX as unknown as Step[], current_step_index: 6 },
      { onApplyReorder },
    );

    act(() => rowOp("step-02", "step.moveDown").click());

    expect(onApplyReorder).toHaveBeenCalledTimes(1);
    expect(onApplyReorder.mock.calls[0]?.[0]).toEqual([
      "step-01",
      "step-03",
      "step-02",
      "step-04",
      "step-05",
      "step-06",
    ]);
  });
});

// ─── 2. 끝단 (FR-300) ───────────────────────────────────────────────────────

describe("갈 곳이 없는 방향 (FR-300)", () => {
  it("첫 행의 「위로」와 마지막 행의 「아래로」가 자리를 남기고 비활성이다", async () => {
    await renderEdit();

    const firstUp = rowOp("step-01", "step.moveUp");
    const lastDown = rowOp("step-06", "step.moveDown");
    expect(firstUp.disabled).toBe(true);
    expect(lastDown.disabled).toBe(true);
    // 이유가 붙는다 — 조용히 잠기지 않는다 (FR-234).
    expect(firstUp.getAttribute("aria-label")).toContain("맨 위입니다");
    expect(lastDown.getAttribute("aria-label")).toContain("맨 아래입니다");
  });

  it("그 방향의 반대는 열려 있다", async () => {
    await renderEdit();

    expect(rowOp("step-01", "step.moveDown").disabled).toBe(false);
    expect(rowOp("step-06", "step.moveUp").disabled).toBe(false);
  });
});

// ─── 3. 목록이 하나다 (SC-505 · FR-301) ─────────────────────────────────────

describe("순서 변경에 별도 패널을 쓰지 않는다 (SC-505 · FR-301)", () => {
  it("일시정지 화면에 Step 패널이 하나만 있다", () => {
    renderSession({ state: "paused", steps: SIX as unknown as Step[], current_step_index: 6 });

    expect(document.querySelectorAll("[data-workbench-step-panel]")).toHaveLength(1);
    // 「순서 변경」이라는 이름의 패널이 열릴 길이 없다.
    expect(screen.queryByText("순서 변경")).toBeNull();
  });
});

// ─── 4. 지우기 확인 (SC-504 · FR-302) ───────────────────────────────────────

describe("지우기는 확인을 거친다 (FR-302)", () => {
  it("확인 전에는 지워지지 않는다", async () => {
    await renderEdit();

    act(() => rowOp("step-02", "step.delete").click());

    expect(labels()).toHaveLength(6);
    expect(screen.getByText("지울까요?")).toBeTruthy();
  });

  it("확인하면 그때 지워진다 — 조작이 **행 안에서** 끝난다 (SC-504)", async () => {
    await renderEdit();

    act(() => rowOp("step-02", "step.delete").click());
    act(() => rowOp("step-02", "step.delete.confirm").click());

    expect(labels()).toEqual(["step-01", "step-03", "step-04", "step-05", "step-06"]);
  });

  it("취소하면 그대로 남는다", async () => {
    await renderEdit();

    act(() => rowOp("step-02", "step.delete").click());
    act(() => rowOp("step-02", "step.delete.cancel").click());

    expect(labels()).toHaveLength(6);
    expect(screen.queryByText("지울까요?")).toBeNull();
  });
});

// ─── 5. 「이 앞에 추가」가 그 행 앞을 가리킨다 (FR-298) ─────────────────────

describe("행의 「이 앞에 추가」 (FR-298)", () => {
  it("그 행을 고른 상태로 입력면이 열린다", async () => {
    await renderEdit();

    act(() => rowOp("step-03", "step.insertManual").click());

    expect(screen.getByLabelText("넣을 Step 종류")).toBeTruthy();
    expect(screen.getByText(/Step 03 앞에 추가/)).toBeTruthy();
  });
});

// ─── 6. 키보드만으로 (SC-507 · FR-303) ──────────────────────────────────────

describe("키보드 경로 (SC-507 · FR-303)", () => {
  it("모든 행 조작이 이름을 갖고 순서가 화면 순서와 같다", async () => {
    await renderEdit();

    const ops = [...document.querySelectorAll("[data-step-row] [data-row-action]")];
    /*
      **2026-09-10 (011) — 행마다 조작이 다섯이 됐다.**

      칸 0 에 삭제 대상 체크가 붙었다 (UC-011-12). 6행 × 5조작 = 30 이다.

      **버튼 단언을 조작별로 갈랐다.** 체크는 `input[type=checkbox]` 다 — 누르면 즉시
      일어나는 행 조작 넷과 달리 **상태를 켜고 끄는** 것이라, 눌린 상태를 접근성 트리에
      전달하는 요소여야 한다. 버튼으로 만들면 `aria-pressed` 를 손으로 붙여야 하고 그것을
      빠뜨리면 체크 여부가 키보드 사용자에게 전달되지 않는다.

      **이름 규칙은 그대로다** — 다섯 다 「〈Step 이름〉 〈조작〉」 형태여야 한다 (FR-303).
    */
    expect(ops).toHaveLength(30);
    for (const op of ops) {
      expect(op.getAttribute("aria-label"), "이름 없는 조작이 있다").toBeTruthy();
      const action = op.getAttribute("data-row-action");
      if (action === "step.toggleDeleteTarget") {
        expect(op.tagName).toBe("INPUT");
        expect((op as HTMLInputElement).type).toBe("checkbox");
      } else {
        expect(op.tagName).toBe("BUTTON");
      }
    }

    // 첫 행의 이름 형태 — 「〈이름〉 위로 옮기기」
    expect(rowOp("step-02", "step.moveUp").getAttribute("aria-label")).toBe(
      "Step 2 이동 위로 옮기기",
    );
    expect(rowOp("step-02", "step.moveDown").getAttribute("aria-label")).toBe(
      "Step 2 이동 아래로 옮기기",
    );
  });
});

// ─── 7. 잠긴 국면 (SC-508 · FR-306·FR-308) ──────────────────────────────────

describe("잠긴 국면 (SC-508 · FR-306·FR-308)", () => {
  it("실행 중에는 행 조작이 활성으로 보이지 않는다", () => {
    renderSession({ state: "replaying", steps: SIX as unknown as Step[] });

    const ops = [...document.querySelectorAll("[data-step-row] [data-row-action]")];
    expect(ops.length).toBeGreaterThan(0);
    for (const op of ops) {
      expect((op as HTMLButtonElement).disabled, `${op.getAttribute("data-row-action")}`).toBe(
        true,
      );
    }
  });
});

// ─── 009 T059 · 팔레트 경로도 표대로 동작한다 (계약 §3-3-0 · 005 U-01) ──────
//
// **조작의 자리는 팔레트가 선언하고 행은 사례다.** 자리가 선언되어 있으면 그 경로도
// 동작해야 한다 — 활성인데 아무 일도 하지 않는 조작이 005 U-01 의 형태였다.

describe("팔레트 경로 (계약 §3-3-0)", () => {
  const paletteAction = (id: string) =>
    document.querySelector(`button[data-action="${id}"]`) as HTMLButtonElement;

  it("고른 Step 이 없으면 팔레트 이동이 비활성이고 이유가 붙는다", () => {
    renderSession({ state: "paused", steps: SIX as unknown as Step[], current_step_index: 6 });

    for (const id of ["step.moveUp", "step.moveDown"]) {
      const btn = paletteAction(id);
      expect(btn, `${id} 이 팔레트에 없다`).toBeTruthy();
      expect(btn.disabled, `${id} 이 활성이다 — 누르면 아무 일도 안 한다`).toBe(true);
    }
    expect(screen.getAllByText("먼저 Step 을 고르세요").length).toBeGreaterThan(0);
  });

  it("고른 Step 이 있으면 팔레트 이동이 실제로 옮긴다", () => {
    const onApplyReorder = vi.fn();
    renderSession(
      {
        state: "paused",
        steps: SIX as unknown as Step[],
        current_step_index: 6,
      },
      { onApplyReorder, focusedStepId: "step-02" },
    );

    act(() => paletteAction("step.moveDown").click());

    expect(onApplyReorder).toHaveBeenCalledTimes(1);
    expect(onApplyReorder.mock.calls[0]?.[0]).toEqual([
      "step-01",
      "step-03",
      "step-02",
      "step-04",
      "step-05",
      "step-06",
    ]);
  });
});
