/**
 * 목록의 결말 필터와 정렬 (008 T022 · FR-272 · V-07).
 *
 * 확정 디자인 `TestList.dc.html` 은 검색 옆에 결말 필터 넷(전체·통과·실패·미실행)과
 * 정렬(「최근 실행 순」)을 그린다. 코드에는 **개수만** 있었고 거르지도 정렬하지도 못했다 —
 * 디자인에 있는 것을 뺀 형태이며 DC-007 위반이다.
 *
 * 둘 다 화면 안에서 계산한다. 백엔드 `list_tests` 는 `q` 만 받고(research R7) 응답 행이
 * 이미 `outcome`·`last_run_at` 을 담는다. 이 검사는 **그 계산이 실제로 목록을 바꾸는지**
 * 를 본다 — 조작이 있는데 아무 일도 하지 않으면 없는 것보다 나쁘다.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";
import type { TestListRow } from "../src/api/client";

const noop = () => undefined;

function row(over: Partial<TestListRow> & { id: string }): TestListRow {
  return {
    name: `이름 ${over.id}`,
    step_count: 3,
    authoring_mode: "record",
    outcome: null,
    last_run_at: null,
    failure_summary: null,
    ...over,
  } as TestListRow;
}

/** 통과 2 · 실패 1 · 미실행 1. 마지막 실행 시각은 서로 다르게 둔다. */
const ROWS: TestListRow[] = [
  row({ id: "TC-001", outcome: "pass", last_run_at: "2026-09-07T00:00:01Z" }),
  row({ id: "TC-002", outcome: "fail", last_run_at: "2026-09-07T00:00:09Z" }),
  row({ id: "TC-003", outcome: "pass", last_run_at: "2026-09-07T00:00:05Z" }),
  row({ id: "TC-004", outcome: null }),
];

function listFetch(rows: TestListRow[]) {
  return vi.fn(
    async () =>
      new Response(
        JSON.stringify({
          tests: rows,
          counts: { total: rows.length, pass: 0, fail: 0 },
          problems: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
  );
}

async function renderList() {
  vi.stubGlobal("fetch", listFetch(ROWS));
  render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
  await screen.findByText("이름 TC-001");
}

/** 화면에 남은 행의 ID 를 나온 순서대로. */
function visibleIds(): string[] {
  return Array.from(document.querySelectorAll("[data-test-row]")).map(
    (el) => (el as HTMLElement).dataset.testRow as string,
  );
}

describe("결말 필터 (FR-272 · DC-007)", () => {
  it("확정 디자인이 정의한 넷이 있고 그 이상 늘리지 않는다", async () => {
    await renderList();
    const group = screen.getByRole("group", { name: "결말로 거르기" });
    const labels = Array.from(group.querySelectorAll("button")).map((b) =>
      (b.textContent ?? "").replace(/\d+$/, "").trim(),
    );
    expect(labels).toEqual(["전체", "통과", "실패", "미실행"]);
  });

  it("고른 결말만 남는다", async () => {
    await renderList();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /^통과/ }));
    expect(visibleIds().sort()).toEqual(["TC-001", "TC-003"]);

    await user.click(screen.getByRole("button", { name: /^실패/ }));
    expect(visibleIds()).toEqual(["TC-002"]);

    await user.click(screen.getByRole("button", { name: /^미실행/ }));
    expect(visibleIds()).toEqual(["TC-004"]);

    await user.click(screen.getByRole("button", { name: /^전체/ }));
    expect(visibleIds()).toHaveLength(4);
  });

  it("개수는 **거르기 전 전체**를 센다 — 필터가 자기 자신을 0으로 만들지 않는다", async () => {
    // 거른 뒤의 수를 세면 「실패」를 고른 순간 「통과 0」이 되어 돌아갈 길이 사라진다.
    await renderList();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^실패/ }));

    expect(screen.getByRole("button", { name: "통과 2" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "실패 1" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "미실행 1" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "전체 4" })).toBeTruthy();
  });

  it("고른 결말이 하나도 없으면 그 사실을 말한다", async () => {
    vi.stubGlobal("fetch", listFetch([row({ id: "TC-100", outcome: "pass" })]));
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("이름 TC-100");

    await userEvent.setup().click(screen.getByRole("button", { name: /^실패/ }));
    expect(screen.getByText("실패인 테스트가 없습니다.")).toBeTruthy();
  });
});

describe("정렬 (FR-272)", () => {
  it("최근 실행 순이 기본이고, 돌린 적 없는 것은 뒤로 간다", async () => {
    await renderList();
    // TC-002(00:09) → TC-003(00:05) → TC-001(00:01) → TC-004(없음)
    expect(visibleIds()).toEqual(["TC-002", "TC-003", "TC-001", "TC-004"]);
  });

  it("끄면 저장된 순으로 돌아간다 — 정렬이 실제로 순서를 바꾼다", async () => {
    await renderList();
    await userEvent.setup().click(screen.getByRole("button", { name: "최근 실행 순" }));
    expect(visibleIds()).toEqual(["TC-001", "TC-002", "TC-003", "TC-004"]);
  });
});

describe("백엔드를 건드리지 않는다 (research R7)", () => {
  it("거르기·정렬에 다시 조회하지 않는다 — 검색만 서버를 부른다", async () => {
    const fetchMock = listFetch(ROWS);
    vi.stubGlobal("fetch", fetchMock);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByText("이름 TC-001");

    const before = fetchMock.mock.calls.length;
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /^실패/ }));
    await user.click(screen.getByRole("button", { name: "최근 실행 순" }));

    expect(fetchMock.mock.calls.length, "필터·정렬이 서버를 다시 불렀다").toBe(before);
  });
});
