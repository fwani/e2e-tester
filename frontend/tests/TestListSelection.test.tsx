/**
 * 테스트 목록의 선택과 복수 삭제. 013 FR-426~FR-437 · contracts/ui-contract.md.
 *
 * **Step 에는 011 이 복수 삭제를 만들었는데 테스트에는 없었다.** 11개를 정리하려면 확인을
 * 11번 거쳐야 했다.
 *
 * 이 파일이 지키는 것은 셋이다.
 *
 * 1. **보이지 않는 것은 지워지지 않는다** (SC-625). 걸러 본 뒤 지우면 화면에 있던 것만
 *    사라져야 한다 — 그러지 않으면 무엇을 지웠는지 볼 수 없는 삭제가 된다.
 * 2. **확인 전에는 아무 요청도 나가지 않는다** (FR-431).
 * 3. **거절 뒤 선택이 남는다** (UC-013-07). 다시 고르게 만들면 멈추고 돌아온 뜻이 없어진다.
 */
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";
import type { TestListRow } from "../src/api/client";

const noop = () => undefined;

function row(over: Partial<TestListRow> & { id: string; name: string }): TestListRow {
  return {
    step_count: 3,
    authoring_mode: "record",
    outcome: null,
    last_run_at: null,
    failure_summary: null,
    ...over,
  } as TestListRow;
}

const ROWS: TestListRow[] = [
  row({ id: "TC-001", name: "로그인" }),
  row({ id: "TC-002", name: "회원가입" }),
  row({ id: "TC-003", name: "결제" }),
];

interface Call {
  url: string;
  method: string;
  body: unknown;
}

/** 요청을 전부 기록한다 — **무엇이 나갔는지가 이 파일의 주된 단언이다.** */
function stub(deleteResponse?: { status: number; body: unknown }) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({
        url,
        method,
        body: init?.body === undefined ? undefined : JSON.parse(String(init.body)),
      });
      if (url.includes("/api/tests:delete")) {
        const r = deleteResponse ?? {
          status: 200,
          body: {
            deleted: [
              { id: "TC-001", name: "로그인", trashed_to: "/휴지통/20260910-1-TC-001-로그인" },
            ],
          },
        };
        return new Response(JSON.stringify(r.body), {
          status: r.status,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(
        JSON.stringify({
          tests: ROWS,
          counts: { total: ROWS.length, pass: 0, fail: 0 },
          problems: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }),
  );
  return calls;
}

async function renderList() {
  render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
  await screen.findByText("로그인");
}

const bar = () => document.querySelector("[data-test-selection-bar]");
const confirm = () => document.querySelector("[data-test-bulk-confirm]");
const deleteCalls = (calls: Call[]) => calls.filter((c) => c.url.includes("/api/tests:delete"));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ─── UC-013-02 · 선택 띠 ───────────────────────────────────────────────────

describe("선택 띠", () => {
  it("고른 것이 없으면 그리지 않는다 (SC-627)", async () => {
    stub();
    await renderList();

    // 그룹도 복수 삭제도 쓰지 않는 사용자에게 자리를 뺏지 않는다.
    expect(bar()).toBeNull();
  });

  it("고르면 나타나고 개수를 말한다 (FR-427)", async () => {
    stub();
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));

    await waitFor(() => expect(bar()).not.toBeNull());
    expect(within(bar() as HTMLElement).getByText("1개 선택됨")).toBeTruthy();
  });

  it("체크 칸은 행 열기와 갈라져 있다 (FR-426 · UC-013-01)", async () => {
    stub();
    const onOpenResult = vi.fn();
    render(<TestList onCreate={noop} onOpenResult={onOpenResult} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));

    // 열려던 사용자가 삭제 대상을 고르는 일이 없어야 한다 — 그 반대도 마찬가지다.
    expect(onOpenResult).not.toHaveBeenCalled();
  });
});

// ─── UC-013-03 · 보이는 것만 ───────────────────────────────────────────────

describe("걸러 보기와 선택 (SC-625)", () => {
  it("화면에서 사라진 행은 선택에서도 빠진다 (FR-429)", async () => {
    stub();
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));
    await user.click(screen.getByLabelText("회원가입 선택"));
    await waitFor(() =>
      expect(within(bar() as HTMLElement).getByText("2개 선택됨")).toBeTruthy(),
    );

    // 「미실행」으로 걸러도 셋 다 미실행이라 남는다. 대신 「통과」로 거르면 0개가 된다.
    await user.click(screen.getByRole("button", { name: /^통과/ }));

    await waitFor(() => expect(bar()).toBeNull(), { timeout: 2000 });
  });

  it("「보이는 것 전부 선택」의 대상은 보이는 것뿐이다 (FR-428)", async () => {
    const calls = stub();
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /^미실행/ }));
    await user.click(screen.getByLabelText("보이는 테스트 전부 선택"));
    await waitFor(() => expect(bar()).not.toBeNull());

    await user.click(within(bar() as HTMLElement).getByText("선택한 항목 삭제"));
    await user.click(screen.getByText("지우기"));

    await waitFor(() => expect(deleteCalls(calls)).toHaveLength(1));
    expect((deleteCalls(calls)[0]!.body as { test_ids: string[] }).test_ids).toEqual([
      "TC-001",
      "TC-002",
      "TC-003",
    ]);
  });
});

// ─── UC-013-04·05 · 확인과 완료 ────────────────────────────────────────────

describe("확인과 완료", () => {
  it("확인 전에는 삭제 요청이 나가지 않는다 (FR-431)", async () => {
    const calls = stub();
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));
    await waitFor(() => expect(bar()).not.toBeNull());
    await user.click(within(bar() as HTMLElement).getByText("선택한 항목 삭제"));

    await waitFor(() => expect(confirm()).not.toBeNull());
    expect(deleteCalls(calls)).toHaveLength(0);
  });

  it("확인 문구가 개수와 이름을 함께 말한다 (FR-430)", async () => {
    stub();
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));
    await user.click(screen.getByLabelText("회원가입 선택"));
    await waitFor(() => expect(bar()).not.toBeNull());
    await user.click(within(bar() as HTMLElement).getByText("선택한 항목 삭제"));

    const box = await waitFor(() => confirm() as HTMLElement);
    // 개수만 있으면 「2개」가 어느 둘인지 알 수 없다.
    expect(box.textContent).toContain("로그인");
    expect(box.textContent).toContain("회원가입");
    expect(box.textContent).toContain("2개");
    // 되돌릴 수 있다는 사실을 확인 시점에 말한다 (FR-437b).
    expect(box.textContent).toContain("되돌릴 수 있습니다");
  });

  it("돌아가면 아무것도 지워지지 않는다", async () => {
    const calls = stub();
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));
    await waitFor(() => expect(bar()).not.toBeNull());
    await user.click(within(bar() as HTMLElement).getByText("선택한 항목 삭제"));
    await waitFor(() => expect(confirm()).not.toBeNull());
    await user.click(screen.getByText("돌아가기"));

    await waitFor(() => expect(confirm()).toBeNull());
    expect(deleteCalls(calls)).toHaveLength(0);
  });

  it("완료되면 옮겨진 자리와 되돌리는 방법을 남긴다 (FR-437a·FR-437b)", async () => {
    stub();
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));
    await waitFor(() => expect(bar()).not.toBeNull());
    await user.click(within(bar() as HTMLElement).getByText("선택한 항목 삭제"));
    await waitFor(() => expect(confirm()).not.toBeNull());
    await user.click(screen.getByText("지우기"));

    const notice = await waitFor(() => {
      const el = document.querySelector("[data-trashed-notice]");
      expect(el).not.toBeNull();
      return el as HTMLElement;
    });
    expect(notice.textContent).toContain("/휴지통/20260910-1-TC-001-로그인");
    expect(notice.textContent).toContain("되돌리려면");
  });
});

// ─── UC-013-07 · 거절 ──────────────────────────────────────────────────────

describe("거절 뒤의 상태", () => {
  it("실행 중이면 사유가 뜨고 **선택이 남는다**", async () => {
    stub({
      status: 409,
      body: {
        error: {
          code: "TEST_IN_USE",
          category: "blocked",
          message: "실행 중인 브라우저가 있어 정리할 수 없습니다.",
          next_action: "실행 중인 브라우저를 먼저 중지한 뒤 다시 시도하세요.",
          detail: {},
        },
      },
    });
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));
    await waitFor(() => expect(bar()).not.toBeNull());
    await user.click(within(bar() as HTMLElement).getByText("선택한 항목 삭제"));
    await waitFor(() => expect(confirm()).not.toBeNull());
    await user.click(screen.getByText("지우기"));

    await screen.findByText(/실행 중인 브라우저가 있어/);
    // 다시 고르게 만들면 멈추고 돌아온 뜻이 없어진다.
    await waitFor(() => expect(bar()).not.toBeNull());
    expect(within(bar() as HTMLElement).getByText("1개 선택됨")).toBeTruthy();
  });

  it("옮기기에 실패하면 「원래 자리」가 화면에 나온다 (SC-618 과 같은 규칙)", async () => {
    stub({
      status: 500,
      body: {
        error: {
          code: "TEST_DELETE_FAILED",
          category: "blocked",
          message: "휴지통으로 옮기지 못했습니다.",
          next_action:
            "테스트는 전부 원래 자리에 있습니다. 저장 위치의 권한과 남은 공간을 확인하세요.",
          detail: {},
        },
      },
    });
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));
    await waitFor(() => expect(bar()).not.toBeNull());
    await user.click(within(bar() as HTMLElement).getByText("선택한 항목 삭제"));
    await waitFor(() => expect(confirm()).not.toBeNull());
    await user.click(screen.getByText("지우기"));

    // 실패 후 사용자가 가장 먼저 묻는 것에 답한다 — "내 테스트는 어떻게 됐나".
    await screen.findByText(/원래 자리에 있습니다/);
  });
});
