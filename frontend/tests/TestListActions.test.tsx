/**
 * 목록의 이름 변경·삭제 (T167). FR-007.
 *
 * **삭제 확인이 이 테스트의 요점이다.** 확인 없이 지우면 사용자가 만든 자산이 한 번의
 * 오클릭으로 사라진다 — 되돌릴 수 없는 조작이므로 확인은 기능이 아니라 요구사항이다.
 */
import { act, render, screen, waitFor } from "@testing-library/react";
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

let calls: { url: string; method: string }[] = [];

beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url: String(url), method: init?.method ?? "GET" });
      if (init?.method === "DELETE") return new Response(null, { status: 204 });
      if (init?.method === "PATCH") return new Response("{}", { status: 200 });
      return new Response(JSON.stringify(LISTING), { status: 200 });
    }),
  );
});

afterEach(() => vi.unstubAllGlobals());

const noop = () => undefined;

async function renderList() {
  render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
  await waitFor(() => expect(screen.getByText("로그인")).toBeTruthy());
}

describe("TestList — 이름 변경·삭제 (FR-007)", () => {
  it("삭제는 확인을 거친다. 확인 전에는 요청하지 않는다", async () => {
    await renderList();

    act(() => screen.getByText("삭제").click());
    // 확인 창이 떴을 뿐 아직 지우지 않았다.
    expect(screen.getByText(/되돌릴 수 없습니다/)).toBeTruthy();
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
  });

  it("취소하면 지우지 않는다", async () => {
    await renderList();
    act(() => screen.getByText("삭제").click());
    act(() => screen.getByText("취소").click());

    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    expect(screen.queryByText(/되돌릴 수 없습니다/)).toBeNull();
  });

  it("확인하면 그때 삭제를 요청한다", async () => {
    await renderList();
    act(() => screen.getByText("삭제").click());

    // 확인 창 안의 삭제 버튼(두 번째 '삭제')을 누른다.
    const buttons = screen.getAllByText("삭제");
    const confirmButton = buttons[buttons.length - 1];
    expect(confirmButton).toBeTruthy();
    act(() => confirmButton?.click());

    await waitFor(() =>
      expect(calls.some((c) => c.method === "DELETE" && c.url.includes("TC-001"))).toBe(
        true,
      ),
    );
  });

  it("이름 변경은 PATCH 로 보낸다", async () => {
    await renderList();
    // 목록 헤더에도 "이름" 이 있으므로 버튼으로 좁힌다.
    act(() => screen.getByRole("button", { name: "이름" }).click());

    const input = screen.getByLabelText("새 이름") as HTMLInputElement;
    expect(input.value).toBe("로그인");

    act(() => screen.getByText("저장").click());
    await waitFor(() =>
      expect(calls.some((c) => c.method === "PATCH" && c.url.includes("TC-001"))).toBe(
        true,
      ),
    );
  });

  it("정의 보기는 핸들러가 있을 때만 그린다 (FR-016)", async () => {
    await renderList();
    expect(screen.queryByText("정의 보기")).toBeNull();

    const onOpenDefinition = vi.fn();
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        onOpenDefinition={onOpenDefinition}
      />,
    );
    await waitFor(() => expect(screen.getAllByText("정의 보기").length).toBe(1));
    act(() => screen.getByText("정의 보기").click());
    expect(onOpenDefinition).toHaveBeenCalledWith("TC-001");
  });
});
