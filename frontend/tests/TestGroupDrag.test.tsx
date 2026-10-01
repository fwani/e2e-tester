/**
 * 028 — 목록에서 끌어 그룹에 넣기. spec US2·US3·US4 · contracts/ui-contract.md UC-028-01~07.
 *
 * 사용자가 「그룹 지정이 어렵다, 목록에서 되면 좋겠다」고 했다. 실제로 목록에는
 * 「그룹으로 옮기기」가 있었지만 **그룹이 하나 이상 있어야만 보였고**, 접두어 규칙에
 * 막혀 그룹을 못 만든 사용자에게는 그 칸이 존재하지 않았다.
 *
 * 이 파일이 지키는 것 중 가장 중요한 하나는 **013 SC-627** 이다: 끌지 않는 사용자의
 * 목록은 028 이전과 같아야 한다. 새 기능이 안 쓰는 사람에게 비용을 지우면 그것은
 * 개선이 아니다.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";
import type { GroupSummary, TestListRow } from "../src/api/client";

const noop = () => undefined;

function row(over: Partial<TestListRow> & { id: string; name: string }): TestListRow {
  return {
    step_count: 3,
    authoring_mode: "record",
    outcome: null,
    last_run_at: null,
    failure_summary: null,
    // 028: 접두어는 **마지막 하이픈 앞**이다. `IT-PM-001` 의 소속은 `IT` 가 아니다.
    group_prefix: over.id.slice(0, over.id.lastIndexOf("-")),
    ...over,
  } as TestListRow;
}

interface Call {
  url: string;
  method: string;
  body: unknown;
}

function stub(rows: TestListRow[], groups: GroupSummary[]) {
  const calls: Call[] = [];
  const defined = groups
    .filter((g) => g.name !== null)
    .map((g) => ({ prefix: g.prefix, name: g.name as string, count: g.count }));
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({
        url,
        method: init?.method ?? "GET",
        body: init?.body === undefined ? undefined : JSON.parse(String(init.body)),
      });
      if (url.includes("/api/groups")) {
        return new Response(JSON.stringify({ groups: defined }), {
          status: init?.method === "POST" ? 201 : 200,
          headers: { "content-type": "application/json" },
        });
      }
      if (url.includes(":move")) {
        return new Response(JSON.stringify({ moved: [] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(
        JSON.stringify({
          tests: rows,
          groups,
          counts: { total: rows.length, pass: 0, fail: 0 },
          problems: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    }),
  );
  return calls;
}

const GROUPED_ROWS = [
  row({ id: "IT-PM-001", name: "프로젝트 등록" }),
  row({ id: "IT-PM-002", name: "프로젝트 수정" }),
  row({ id: "TC-003", name: "그룹 없는 것" }),
];
const GROUPS: GroupSummary[] = [
  { prefix: "TC", name: null, count: 1 },
  { prefix: "IT-PM", name: "프로젝트 관리", count: 2 },
  { prefix: "IT-DM", name: "데이터 관리", count: 0 },
];

const dropBar = () => document.querySelector("[data-group-drop-bar]");
const targetFor = (prefix: string) =>
  document.querySelector(`[data-drop-target="${prefix}"]`) as HTMLElement | null;

/** 브라우저가 실어 나르는 것을 jsdom 에서 흉내 낸다. */
function dataTransfer() {
  const store: Record<string, string> = {};
  return {
    effectAllowed: "",
    dropEffect: "",
    setData: (k: string, v: string) => {
      store[k] = v;
    },
    getData: (k: string) => store[k] ?? "",
  };
}

async function startDragging(testId: string) {
  const handle = document.querySelector(`[data-test-row="${testId}"]`) as HTMLElement;
  fireEvent.dragStart(handle, { dataTransfer: dataTransfer() });
  await waitFor(() => expect(dropBar()).not.toBeNull());
  return handle;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ─── UC-028-01 · 끌지 않을 때는 아무것도 늘지 않는다 ───────────────────────

describe("끌기 전의 목록 (FR-014 · SC-005 · 013 SC-627)", () => {
  it("표적 띠가 없다", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");

    expect(dropBar()).toBeNull();
  });

  it("그룹이 하나도 없는 프로젝트에서도 없다", async () => {
    stub([row({ id: "TC-001", name: "하나" })], [{ prefix: "TC", name: null, count: 1 }]);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("하나");

    expect(dropBar()).toBeNull();
  });
});

// ─── UC-028-02 · 끌기 중의 표적 ────────────────────────────────────────────

describe("끌기를 시작하면", () => {
  it("표적 띠가 나타나고 끝나면 사라진다 (FR-014 · FR-018)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");

    const handle = await startDragging("IT-PM-001");
    fireEvent.dragEnd(handle);
    await waitFor(() => expect(dropBar()).toBeNull());
  });

  it("테스트가 0개인 그룹도 표적이 된다 (FR-015)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");
    await startDragging("IT-PM-001");

    // 「데이터 관리」는 테스트가 0개다. 옮길 곳이 되지 못하면 빈 그룹은 영영 빈다.
    expect(targetFor("IT-DM")).not.toBeNull();
    expect(targetFor("IT-PM")).not.toBeNull();
    expect(targetFor("TC")).not.toBeNull();
  });

  it("올라와 있는 표적이 구분된다 (FR-016)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");
    await startDragging("IT-PM-001");

    const target = targetFor("IT-DM")!;
    expect(target.hasAttribute("data-drop-over")).toBe(false);
    fireEvent.dragEnter(target, { dataTransfer: dataTransfer() });
    await waitFor(() => expect(target.hasAttribute("data-drop-over")).toBe(true));
    fireEvent.dragLeave(target);
    await waitFor(() => expect(target.hasAttribute("data-drop-over")).toBe(false));
  });

  it("표적은 탭 순서에 끼지 않는다 (FR-028 · UC-028-07)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");
    await startDragging("IT-PM-001");

    for (const el of Array.from(document.querySelectorAll("[data-drop-target]"))) {
      expect((el as HTMLElement).tabIndex).toBe(-1);
    }
  });
});

// ─── UC-028-03 · 무엇이 끌리는가 ───────────────────────────────────────────

describe("끌어서 놓으면", () => {
  async function dropOn(prefix: string) {
    const target = targetFor(prefix)!;
    fireEvent.dragOver(target, { dataTransfer: dataTransfer() });
    fireEvent.drop(target, { dataTransfer: dataTransfer() });
  }

  it("끈 행 하나가 옮겨진다 (FR-017)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");
    await startDragging("IT-PM-001");
    await dropOn("IT-DM");

    await waitFor(() => {
      const move = calls.find((c) => c.url.includes(":move"));
      expect(move?.body).toEqual({ test_ids: ["IT-PM-001"], to_prefix: "IT-DM" });
    });
  });

  it("고른 것 중 하나를 끌면 고른 전부가 간다 (FR-017)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");

    const user = userEvent.setup();
    await user.click(screen.getByRole("checkbox", { name: "프로젝트 등록 선택" }));
    await user.click(screen.getByRole("checkbox", { name: "프로젝트 수정 선택" }));

    await startDragging("IT-PM-001");
    await dropOn("IT-DM");

    await waitFor(() => {
      const move = calls.find((c) => c.url.includes(":move"));
      expect((move?.body as { test_ids: string[] }).test_ids.sort()).toEqual([
        "IT-PM-001",
        "IT-PM-002",
      ]);
    });
  });

  it("고르지 않은 행을 끌면 그 행만 가고 고른 것은 그대로다 (UC-028-03)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");

    const user = userEvent.setup();
    await user.click(screen.getByRole("checkbox", { name: "프로젝트 등록 선택" }));

    await startDragging("TC-003");
    await dropOn("IT-DM");

    await waitFor(() => {
      const move = calls.find((c) => c.url.includes(":move"));
      expect(move?.body).toEqual({ test_ids: ["TC-003"], to_prefix: "IT-DM" });
    });
    // 끌기가 선택을 지우면 사용자가 고르던 일이 날아간다.
    expect(
      (screen.getByRole("checkbox", { name: "프로젝트 등록 선택" }) as HTMLInputElement).checked,
    ).toBe(true);
  });

  it("「그룹에서 빼기」는 TC 로 돌린다 (FR-015)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");
    await startDragging("IT-PM-001");
    await dropOn("TC");

    await waitFor(() => {
      const move = calls.find((c) => c.url.includes(":move"));
      expect((move?.body as { to_prefix: string }).to_prefix).toBe("TC");
    });
  });

  it("무엇이 어디로 갔는지 알린다 (FR-019)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");
    await startDragging("IT-PM-001");
    await dropOn("IT-DM");

    const notice = await screen.findByText(/「데이터 관리」\(으\)로 옮겼습니다/);
    expect(notice).not.toBeNull();
  });

  it("표적 밖에서 끝내면 아무것도 보내지 않는다 (FR-018)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");
    const handle = await startDragging("IT-PM-001");
    fireEvent.dragEnd(handle);

    await waitFor(() => expect(dropBar()).toBeNull());
    expect(calls.some((c) => c.url.includes(":move"))).toBe(false);
  });
});

// ─── UC-028-04·05 · 그룹이 하나도 없어도 길이 있다 ─────────────────────────

const EMPTY_GROUPS: GroupSummary[] = [{ prefix: "TC", name: null, count: 2 }];
const UNGROUPED_ROWS = [
  row({ id: "TC-001", name: "하나" }),
  row({ id: "TC-002", name: "둘" }),
];

describe("그룹이 0개인 프로젝트 (US3)", () => {
  it("체크하면 선택 띠에 그룹 지정 수단이 있다 (FR-023 · UC-028-04)", async () => {
    stub(UNGROUPED_ROWS, EMPTY_GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("하나");

    await userEvent.setup().click(screen.getByRole("checkbox", { name: "하나 선택" }));

    // 028 이전에는 여기에 **아무것도 없었다.** 그것이 「그룹 지정이 안 된다」였다.
    const select = await screen.findByRole("combobox", { name: "그룹으로 옮기기" });
    expect(
      within(select).getByRole("option", { name: "+ 새 그룹 만들어 옮기기" }),
    ).toBeTruthy();
  });

  it("끌면 「새 그룹으로」 표적이 나온다 (FR-024)", async () => {
    stub(UNGROUPED_ROWS, EMPTY_GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("하나");
    await startDragging("TC-001");

    expect(targetFor("__new__")).not.toBeNull();
    // 그룹이 없으니 「빼기」는 할 일이 없다.
    expect(targetFor("TC")).toBeNull();
  });

  it("놓으면 그룹을 만들고 이어서 옮긴다 (FR-025 · api-contract §2)", async () => {
    const calls = stub(UNGROUPED_ROWS, EMPTY_GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("하나");
    await startDragging("TC-001");

    const target = targetFor("__new__")!;
    fireEvent.dragOver(target, { dataTransfer: dataTransfer() });
    fireEvent.drop(target, { dataTransfer: dataTransfer() });

    const user = userEvent.setup();
    await user.type(await screen.findByRole("textbox", { name: "그룹 이름" }), "프로젝트 관리");
    await user.type(screen.getByRole("textbox", { name: "그룹 접두어" }), "IT-PM");
    await user.click(screen.getByRole("button", { name: "만들기" }));

    await waitFor(() => {
      const create = calls.find((c) => c.url.includes("/api/groups") && c.method === "POST");
      expect(create?.body).toEqual({ prefix: "IT-PM", name: "프로젝트 관리" });
    });
    await waitFor(() => {
      const move = calls.find((c) => c.url.includes(":move"));
      expect(move?.body).toEqual({ test_ids: ["TC-001"], to_prefix: "IT-PM" });
    });
  });

  it("취소하면 그룹도 안 만들고 옮기지도 않는다 (FR-025)", async () => {
    const calls = stub(UNGROUPED_ROWS, EMPTY_GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("하나");
    await startDragging("TC-001");

    const target = targetFor("__new__")!;
    fireEvent.drop(target, { dataTransfer: dataTransfer() });

    await userEvent.setup().click(await screen.findByRole("button", { name: "취소" }));

    await waitFor(() =>
      expect(document.querySelector("[data-new-group-drop]")).toBeNull(),
    );
    expect(calls.some((c) => c.url.includes("/api/groups") && c.method === "POST")).toBe(false);
    expect(calls.some((c) => c.url.includes(":move"))).toBe(false);
  });
});

// ─── UC-028-07 · 포인터 없이 (US4) ─────────────────────────────────────────

describe("선택칸 경로 (FR-027 · SC-006)", () => {
  it("끌지 않고도 같은 이동을 한다", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");

    const user = userEvent.setup();
    await user.click(screen.getByRole("checkbox", { name: "프로젝트 등록 선택" }));
    await user.selectOptions(
      await screen.findByRole("combobox", { name: "그룹으로 옮기기" }),
      "IT-DM",
    );

    await waitFor(() => {
      const move = calls.find((c) => c.url.includes(":move"));
      expect(move?.body).toEqual({ test_ids: ["IT-PM-001"], to_prefix: "IT-DM" });
    });
    // 끌어 놓기와 같은 완료 표시를 쓴다 — 두 길의 결과가 달라 보이면 안 된다.
    expect(await screen.findByText(/「데이터 관리」\(으\)로 옮겼습니다/)).not.toBeNull();
  });

  it("새 그룹 만들어 옮기기도 선택칸으로 된다 (FR-027)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("프로젝트 등록");

    const user = userEvent.setup();
    await user.click(screen.getByRole("checkbox", { name: "프로젝트 등록 선택" }));
    await user.selectOptions(
      await screen.findByRole("combobox", { name: "그룹으로 옮기기" }),
      "__new__",
    );

    expect(await screen.findByRole("textbox", { name: "그룹 접두어" })).not.toBeNull();
  });
});
