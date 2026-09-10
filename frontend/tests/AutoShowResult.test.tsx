/**
 * 실행이 끝나면 **결과 국면으로 스스로 넘어간다** (2026-09-10 사용자 결정).
 *
 * 「실행이 완료되면 결과화면으로 자동 이전(변화)되면 좋겠다. 결과 상세보기나, 실행 후
 * 결과를 보는 것이나 사실은 같은 건데 결과를 상세보기 하는 화면을 버튼을 눌러 가는 게
 * UX 적으로 불편하다」.
 *
 * 이 파일이 지키는 것은 넷이다.
 *
 * 1. 끝난 실행은 **묻지 않고** 결과로 간다.
 * 2. 실패했으면 그 Step 을 **지목해서** 간다 — 다음에 하는 일이 그것을 고치는 것이다.
 * 3. **중지·유실은 아니다.** 실행이 완료된 것이 아니며, 그 순간 화면에 있던 것을 뺏는다.
 * 4. **편집에서 출발한 세션은 예외다** — 돌아갈 곳이 편집 화면이다 (006 FR-204).
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SessionScreen } from "../src/pages/SessionScreen";
import { sessionView } from "./helpers/workbench";
import type { SessionState } from "../src/api/client";

vi.mock("../src/api/ws", () => ({
  subscribeSessionEvents: () => ({ stop: () => undefined, reconnect: () => undefined }),
}));

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 200 })));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function mount(state: SessionState, extra: Record<string, unknown> = {}) {
  const onShowResult = vi.fn();
  render(
    <SessionScreen
      initial={sessionView({ state, test_id: "TC-001" })}
      onFinished={() => {}}
      onShowResult={onShowResult}
      {...extra}
    />,
  );
  return onShowResult;
}

describe("실행 완료 → 결과 (2026-09-10)", () => {
  it.each(["completed", "failed"] as SessionState[])(
    "%s 이면 버튼을 누르지 않아도 결과로 간다",
    async (state) => {
      const onShowResult = mount(state);
      await waitFor(() => expect(onShowResult).toHaveBeenCalledWith("TC-001", null));
    },
  );

  it.each(["stopped", "lost"] as SessionState[])(
    "%s 은 실행이 완료된 것이 아니므로 화면을 뺏지 않는다",
    async (state) => {
      const onShowResult = mount(state);
      await new Promise((r) => setTimeout(r, 50));
      expect(onShowResult).not.toHaveBeenCalled();
    },
  );

  it("편집에서 출발한 세션은 결과로 튀지 않는다 — 돌아갈 곳이 편집 화면이다", async () => {
    const onShowResult = mount("completed", { autoShowResult: false });
    await new Promise((r) => setTimeout(r, 50));
    expect(onShowResult).not.toHaveBeenCalled();
  });

  it("저장되지 않은 초안은 결과 화면이 읽을 대상이 없다", async () => {
    const onShowResult = vi.fn();
    render(
      <SessionScreen
        initial={sessionView({ state: "completed", test_id: null })}
        onFinished={() => {}}
        onShowResult={onShowResult}
      />,
    );
    await new Promise((r) => setTimeout(r, 50));
    expect(onShowResult).not.toHaveBeenCalled();
  });
});
