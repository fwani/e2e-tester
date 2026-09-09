/**
 * 2026-09-09 사용자 보고 — **다시 실행하는 Step 의 상태 표기가 갱신되지 않았다.**
 *
 * 보고 문장: 「테스트를 다시 실행하는 스텝이면, 상태 표기가 업데이트 되어야함」.
 *
 * ## 왜 갱신되지 않았나
 *
 * 결말은 두 곳에서 온다 — 화면이 이벤트로 모은 것(`progress`)과 서버가 준 지난 실행의
 * 기록(`view.step_results`). 세션 안에서 다시 실행하면(「이 Step 부터 이어 실행」·
 * 「계속하기」) 화면이 다시 마운트되지 않으므로 둘 다 지난 값을 그대로 들고 있었다.
 *
 * 그리고 `outcomeOf` 의 판정 순서가 `progress` → 서버 기록 → `running` 이었다. 다시 도는
 * Step 은 앞의 둘에 지난 결말을 갖고 있으므로 **「실행 중」에 닿지 못했다.**
 *
 * 이 파일이 재는 것은 그 순서와 무효화다 — 「지금 돌고 있다」는 관측된 사실이고 지난
 * 결말은 기록이며, 사실이 기록을 이겨야 한다.
 */
import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionScreen } from "../src/pages/SessionScreen";
import { clickStep, fillStep, sessionView } from "./helpers/workbench";
import type { SessionEvent } from "../src/api/ws";

/** 구독을 가로채 이벤트를 손으로 밀어 넣는다. */
let push: (event: SessionEvent) => void = () => undefined;

vi.mock("../src/api/ws", () => ({
  subscribeSessionEvents: (
    _sessionId: string,
    handlers: { onEvent: (e: SessionEvent) => void },
  ) => {
    push = handlers.onEvent;
    return { stop: () => undefined, reconnect: () => undefined };
  },
}));

const STEPS = [clickStep({ id: "st-1" }), fillStep({ id: "st-2" })];

/**
 * 지난 실행의 기록을 가진 세션 — Step 01 통과(120ms) · Step 02 실패.
 *
 * 이것이 이 결함이 나는 조건이다: **결과가 이미 있는데 다시 돈다.**
 */
function view() {
  return sessionView({
    state: "replaying",
    test_id: "TC-001",
    steps: STEPS,
    current_step_index: 0,
    saved_at: "2026-09-09T00:00:00Z",
    /*
      **지난 실행의 기록** (`StepProgress` — step_id · outcome · duration_ms 셋뿐이다).
      이것이 이 결함이 나는 조건이다: 결과가 이미 있는데 다시 돈다.
    */
    step_results: [
      { step_id: "st-1", outcome: "pass", duration_ms: 120 },
      { step_id: "st-2", outcome: "fail", duration_ms: 900 },
    ],
  });
}

function row(stepId: string): HTMLElement {
  const el = document.querySelector(`[data-step-row="${stepId}"]`);
  expect(el, `Step 행 ${stepId} 이 없다`).not.toBeNull();
  return el as HTMLElement;
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(view()), { status: 200 })),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function mount() {
  render(<SessionScreen initial={view()} onFinished={() => undefined} />);
}

describe("다시 실행하면 Step 의 상태 표기가 갱신된다 (2026-09-09)", () => {
  it("지난 실행의 결말이 「실행 중」을 가리지 않는다", () => {
    mount();
    // 시작 상태: 서버 기록대로 Step 01 은 통과로 보인다.
    expect(row("st-1").textContent).toContain("120");

    act(() => {
      push({ type: "step_started", step_id: "st-1", index: 0, tab: 0 } as SessionEvent);
    });

    /*
      다시 도는 중이다. 지난 실행의 소요 시간이 남아 있으면 사용자는 이번 실행이 이미
      끝난 것으로 읽는다 — 그것이 보고된 증상이다.
    */
    expect(row("st-1").textContent).not.toContain("120");
  });

  it("아직 닿지 않은 Step 의 지난 결과도 걷는다", () => {
    mount();
    expect(row("st-2").textContent).toContain("900");

    act(() => {
      push({ type: "step_started", step_id: "st-1", index: 0, tab: 0 } as SessionEvent);
    });

    /*
      Step 02 는 이번 실행에서 **아직 돌지 않았다.** 지난 실행의 실패가 남아 있으면
      사용자는 이번에도 실패한 줄 안다 — 실제로는 아직 도착하지 않았다.
    */
    expect(row("st-2").textContent).not.toContain("900");
  });

  it("이번 실행의 결말은 도착하는 대로 반영된다", () => {
    mount();
    act(() => {
      push({ type: "step_started", step_id: "st-1", index: 0, tab: 0 } as SessionEvent);
      push({
        type: "step_finished",
        step_id: "st-1",
        index: 0,
        outcome: "pass",
        duration_ms: 55,
      } as SessionEvent);
    });
    expect(row("st-1").textContent).toContain("55");
    // 지난 값으로 되돌아가지 않는다.
    expect(row("st-1").textContent).not.toContain("120");
  });

  it("중간부터 이어 실행하면 그 앞의 결말은 남는다", () => {
    mount();
    act(() => {
      push({ type: "step_started", step_id: "st-2", index: 1, tab: 0 } as SessionEvent);
    });
    /*
      **앞은 걷지 않는다.** Step 01 은 이번 실행에서 돌지 않았지만 그 결과는 지난 실행의
      사실이고, 「이 Step 부터 이어 실행」은 그 앞을 그대로 둔다는 뜻이다. 전부 걷으면
      사용자는 앞이 실패했는지 통과했는지 알 수 없게 된다.
    */
    expect(row("st-1").textContent).toContain("120");
    expect(row("st-2").textContent).not.toContain("900");
  });
});
