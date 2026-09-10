/**
 * 테스트 목록의 그룹. 013 FR-438~FR-451 · contracts/ui-contract.md UC-013-06·08.
 *
 * **한 프로젝트 안에서 테스트를 묶을 방법이 없었다.** 목록이 한 덩어리라 「사용자관리」와
 * 「데이터 관리」를 눈으로 갈라야 했다.
 *
 * 이 파일이 지키는 것 중 가장 중요한 하나는 **SC-627** 이다: 그룹을 쓰지 않는 사용자의
 * 목록은 이 기능 이전과 같은 모습이어야 한다. 새 기능이 안 쓰는 사람에게 비용을 지우면
 * 그것은 개선이 아니다.
 */
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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
    group_prefix: over.id.split("-")[0]!,
    ...over,
  } as TestListRow;
}

interface Call {
  url: string;
  method: string;
  body: unknown;
}

/** 그룹 질의를 실제로 보내는지 보려면 URL 을 기록해야 한다. */
function stub(
  rows: TestListRow[],
  groups: GroupSummary[],
  defined: { prefix: string; name: string; count: number }[] = groups
    .filter((g) => g.name !== null)
    .map((g) => ({ prefix: g.prefix, name: g.name as string, count: g.count })),
) {
  const calls: Call[] = [];
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
        // 정의된 그룹 전부 — **테스트가 0개인 것도 포함한다** (013 converge T061).
        return new Response(JSON.stringify({ groups: defined }), {
          status: init?.method === "POST" ? 201 : 200,
          headers: { "content-type": "application/json" },
        });
      }
      const wanted = new URL(url, "http://x").searchParams.get("group");
      const kept = wanted === null ? rows : rows.filter((r) => r.group_prefix === wanted);
      return new Response(
        JSON.stringify({
          tests: kept,
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
  row({ id: "USER-001", name: "로그인" }),
  row({ id: "USER-002", name: "회원가입" }),
  row({ id: "TC-003", name: "그룹 없는 것" }),
];
const GROUPS: GroupSummary[] = [
  { prefix: "TC", name: null, count: 1 },
  { prefix: "USER", name: "사용자관리 테스트", count: 2 },
];

const bar = () => document.querySelector("[data-test-group-bar]");
const headings = () =>
  Array.from(document.querySelectorAll("[data-group-heading]")).map(
    (el) => (el as HTMLElement).dataset.groupHeading,
  );

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ─── SC-627 · 안 쓰는 사람에게 비용을 지우지 않는다 ────────────────────────

describe("그룹이 없는 프로젝트", () => {
  it("그룹 띠를 그리지 않는다 (SC-627)", async () => {
    stub([row({ id: "TC-001", name: "로그인" })], []);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");

    expect(bar()).toBeNull();
  });

  it("소제목으로 묶지 않는다 — 이전과 같은 모습이다 (SC-627)", async () => {
    stub([row({ id: "TC-001", name: "로그인" })], []);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");

    expect(headings()).toEqual([]);
  });

  it("그래도 그룹을 만들 길은 있다", async () => {
    stub([row({ id: "TC-001", name: "로그인" })], []);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");

    expect(screen.getByRole("button", { name: "+ 그룹" })).toBeTruthy();
  });
});

// ─── UC-013-06 · 묶어 보기·걸러 보기 ──────────────────────────────────────

describe("그룹이 있는 프로젝트", () => {
  it("그룹별로 묶이고 「그룹 없음」이 마지막에 온다 (FR-440)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");

    // 이름이 있는 묶음을 먼저 보여주는 것이 목록을 훑는 순서에 맞는다.
    await waitFor(() => expect(headings()).toEqual(["USER", "TC"]));
  });

  it("칩이 그룹만 남긴다 (FR-441)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(
      within(bar() as HTMLElement).getByRole("button", { name: /사용자관리 테스트/ }),
    );

    await waitFor(() => expect(screen.queryByText("그룹 없는 것")).toBeNull());
    // **서버에서 거른다** — 화면에서 거르면 그룹 개수와 목록이 갈린다.
    expect(calls.some((c) => c.url.includes("group=USER"))).toBe(true);
  });

  it("한 그룹만 볼 때는 소제목으로 묶지 않는다", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(
      within(bar() as HTMLElement).getByRole("button", { name: /사용자관리 테스트/ }),
    );

    // 소제목이 하나뿐이면 자리만 차지한다.
    await waitFor(() => expect(headings()).toEqual([]));
  });

  it("걸러 본 상태에서도 다른 그룹의 개수가 보인다", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(
      within(bar() as HTMLElement).getByRole("button", { name: /사용자관리 테스트/ }),
    );

    // 개수는 걸러 보기 **전** 값이다 — 그래야 그리로 갈 수 있다.
    await waitFor(() =>
      expect(within(bar() as HTMLElement).getByRole("button", { name: /그룹 없음/ })).toBeTruthy(),
    );
  });

  it("그룹 없는 테스트도 목록에 남는다 (FR-439)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);

    // 그룹을 만들지 않아도 도구를 쓸 수 있어야 한다.
    await screen.findByText("그룹 없는 것");
  });

  it("정의가 없는 접두어는 이름을 지어내지 않는다", async () => {
    stub(
      [row({ id: "GHOST-001", name: "정의 없는 그룹의 테스트" })],
      [{ prefix: "GHOST", name: null, count: 1 }],
    );
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("정의 없는 그룹의 테스트");

    // 목록을 막지 않고 접두어를 그대로 쓴다.
    await waitFor(() =>
      expect(within(bar() as HTMLElement).getByRole("button", { name: /GHOST/ })).toBeTruthy(),
    );
  });
});

// ─── UC-013-08 · 그룹 만들기 ──────────────────────────────────────────────

describe("그룹 만들기", () => {
  it("이름과 접두어를 따로 받고 접두어가 왜 필요한지 말한다 (FR-444d)", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "+ 그룹" }));

    expect(screen.getByLabelText("그룹 이름")).toBeTruthy();
    expect(screen.getByLabelText("그룹 접두어")).toBeTruthy();
    // 말하지 않으면 사용자는 이름을 두 번 적는 칸으로 읽는다.
    await screen.findByText(/테스트 식별자에 들어갑니다/);
  });

  it("TC 를 접두어로 쓰면 요청 전에 막고 사유를 말한다 (FR-445a)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "+ 그룹" }));
    await user.type(screen.getByLabelText("그룹 이름"), "가로채기");
    await user.type(screen.getByLabelText("그룹 접두어"), "TC");

    await screen.findByText(/TC 는 그룹 없는 테스트가 씁니다/);
    expect(
      (screen.getByRole("button", { name: "만들기" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(calls.filter((c) => c.method === "POST")).toHaveLength(0);
  });

  it("소문자를 넣어도 대문자로 보낸다 — 식별자가 파일 이름이 되기 때문이다", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "+ 그룹" }));
    await user.type(screen.getByLabelText("그룹 이름"), "결제 테스트");
    await user.type(screen.getByLabelText("그룹 접두어"), "pay");
    await user.click(screen.getByRole("button", { name: "만들기" }));

    await waitFor(() => {
      const post = calls.find((c) => c.method === "POST" && c.url.includes("/api/groups"));
      expect(post?.body).toEqual({ prefix: "PAY", name: "결제 테스트" });
    });
  });
});

// ─── UC-013-08 · 그룹 정리 (US3) ──────────────────────────────────────────

describe("그룹 정리", () => {
  const pickUser = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(
      within(bar() as HTMLElement).getByRole("button", { name: /사용자관리 테스트/ }),
    );
  };

  it("조작은 그 그룹을 고른 상태에서만 나온다", async () => {
    stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    // 칩마다 조작을 달면 띠가 빽빽해지고 어느 그룹을 건드리는지 흐려진다.
    expect(screen.queryByRole("button", { name: "그룹 없애기" })).toBeNull();

    await pickUser(user);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "그룹 없애기" })).toBeTruthy(),
    );
    expect(screen.getByRole("button", { name: "이름 바꾸기" })).toBeTruthy();
  });

  it("이름 변경에는 확인이 없다 — 되돌리면 그만이다", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await pickUser(user);
    await user.click(await screen.findByRole("button", { name: "이름 바꾸기" }));
    const input = screen.getByLabelText("그룹 이름 바꾸기");
    await user.clear(input);
    await user.type(input, "새 이름{Enter}");

    await waitFor(() => {
      const patch = calls.find((c) => c.method === "PATCH");
      expect(patch?.body).toEqual({ name: "새 이름" });
    });
  });

  it("없애기에는 확인이 있고 **「지워지지 않습니다」를 말한다** (FR-451)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await pickUser(user);
    await user.click(await screen.findByRole("button", { name: "그룹 없애기" }));

    // 「없애기」라는 말을 듣고 사용자가 가장 먼저 걱정하는 것이 그것이다.
    const box = await waitFor(
      () => document.querySelector("[data-group-disband-confirm]") as HTMLElement,
    );
    expect(box.textContent).toContain("지워지지 않습니다");
    expect(box.textContent).toContain("TC-###");
    expect(calls.filter((c) => c.method === "DELETE")).toHaveLength(0);
  });

  it("확인 전에는 없애지 않는다", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await pickUser(user);
    await user.click(await screen.findByRole("button", { name: "그룹 없애기" }));
    await waitFor(() =>
      expect(document.querySelector("[data-group-disband-confirm]")).not.toBeNull(),
    );
    await user.click(screen.getByRole("button", { name: "돌아가기" }));

    await waitFor(() =>
      expect(document.querySelector("[data-group-disband-confirm]")).toBeNull(),
    );
    expect(calls.filter((c) => c.method === "DELETE")).toHaveLength(0);
  });

  it("복수 이동이 이미 있는 선택을 쓴다 (FR-448)", async () => {
    const calls = stub(GROUPED_ROWS, GROUPS);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("그룹 없는 것 선택"));
    const select = await screen.findByLabelText("그룹으로 옮기기");
    await user.selectOptions(select, "USER");

    await waitFor(() => {
      const move = calls.find((c) => c.url.includes("/api/tests:move"));
      expect(move?.body).toEqual({ test_ids: ["TC-003"], to_prefix: "USER" });
    });
  });

  it("그룹이 없으면 「그룹으로 옮기기」를 그리지 않는다 (SC-627)", async () => {
    stub([row({ id: "TC-001", name: "로그인" })], []);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("로그인");
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("로그인 선택"));

    await waitFor(() =>
      expect(document.querySelector("[data-test-selection-bar]")).not.toBeNull(),
    );
    expect(screen.queryByLabelText("그룹으로 옮기기")).toBeNull();
  });
});

// ─── converge 2회차 · 빈 그룹을 없앨 수 있는가 (T061) ─────────────────────

describe("테스트가 0개인 그룹", () => {
  it("띠에서 사라지지 않는다 — 없앨 방법이 화면에 있어야 한다", async () => {
    // 목록 응답은 빈 그룹을 뺀다 (FR-450 — 소제목이 목록을 어지럽히지 않는다).
    // 띠까지 그것을 근거로 삼으면 **테스트를 전부 옮긴 그룹을 고를 수도, 없앨 수도
    // 없다** — 012 에서 사용자가 지적한 「없앨 방법이 없는 줄」과 같은 형태다.
    stub(
      [row({ id: "TC-001", name: "그룹 없는 것" })],
      [{ prefix: "TC", name: null, count: 1 }],
      [{ prefix: "EMPTY", name: "비어 있는 그룹", count: 0 }],
    );
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("그룹 없는 것");

    await waitFor(() =>
      expect(
        within(bar() as HTMLElement).getByRole("button", { name: /비어 있는 그룹/ }),
      ).toBeTruthy(),
    );
  });

  it("골라서 없앨 수 있다", async () => {
    const calls = stub(
      [row({ id: "TC-001", name: "그룹 없는 것" })],
      [{ prefix: "TC", name: null, count: 1 }],
      [{ prefix: "EMPTY", name: "비어 있는 그룹", count: 0 }],
    );
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("그룹 없는 것");
    const user = userEvent.setup();

    await screen.findByRole("button", { name: /비어 있는 그룹/ });
    await user.click(screen.getByRole("button", { name: /비어 있는 그룹/ }));
    // 클릭 뒤 목록이 다시 오고 띠가 다시 그려진다 — 그 뒤에 조작이 나타난다.
    await waitFor(() =>
      expect(
        Array.from(document.querySelectorAll("button")).map((b) => b.textContent),
      ).toContain("그룹 없애기"),
    );
    await user.click(screen.getByRole("button", { name: "그룹 없애기" }));
    await user.click(await screen.findByRole("button", { name: "없애기" }));

    await waitFor(() =>
      expect(calls.some((c) => c.method === "DELETE" && c.url.includes("/api/groups/EMPTY"))).toBe(
        true,
      ),
    );
  });

  it("골랐는데 0건이어도 「빈 프로젝트」 화면이 되지 않는다", async () => {
    /*
      converge 2회차에서 실제로 걸린 결함이다. `isEmptyProject` 가 검색어는 이미
      고려했는데(`query.trim() === ""`) 그룹 걸러 보기는 빠져 있었다. 그래서 테스트가
      0개인 그룹을 고르는 순간 화면이 **첫 사용자 안내로 바뀌고 그룹 띠까지 사라져**,
      사용자가 돌아올 길을 잃었다.
    */
    stub(
      [row({ id: "TC-001", name: "그룹 없는 것" })],
      [{ prefix: "TC", name: null, count: 1 }],
      [{ prefix: "EMPTY", name: "비어 있는 그룹", count: 0 }],
    );
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("그룹 없는 것");
    const user = userEvent.setup();

    await screen.findByRole("button", { name: /비어 있는 그룹/ });
    await user.click(screen.getByRole("button", { name: /비어 있는 그룹/ }));

    // 띠가 남아 있어야 돌아올 수 있다.
    await waitFor(() => expect(bar()).not.toBeNull());
    expect(
      within(bar() as HTMLElement).getByRole("button", { name: /^전체/ }),
    ).toBeTruthy();
  });
});
