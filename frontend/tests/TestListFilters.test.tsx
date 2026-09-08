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

describe("표 머리와 행이 같은 격자를 쓴다 (FR-273 · V-08)", () => {
  /*
    008 이 고친 결함 하나가 이것이었다 — 표 머리는 flex 로 `92 108 1fr 74 118 130 196`,
    행도 flex 로 같은 폭을 **따로** 적었고 확정 디자인의 grid `96 82 1fr 64 92 150 168` 과는
    열 폭 7개 중 6개가 달랐다. 값이 두 곳에 있으니 한쪽만 고쳐도 아무도 몰랐다.

    지금은 `GRID` 상수 하나를 둘이 함께 쓴다. 그러나 **상수를 쓰는 것과 같은 값이 나오는
    것은 다르다** — 누가 한쪽에 인라인을 덧대면 상수는 그대로인 채 화면이 어긋난다.
    렌더한 결과에서 직접 잰다.
  */
  it("렌더한 표 머리와 모든 행의 gridTemplateColumns 가 한 값이다", async () => {
    await renderList();

    const head = document.querySelector<HTMLElement>(".thead");
    const rows = Array.from(document.querySelectorAll<HTMLElement>("[data-test-row]"));
    expect(head, "표 머리를 찾지 못했다 — 선택자가 낡았다면 이 검사는 아무것도 세지 않는다").not.toBeNull();
    expect(rows.length, "행이 없으면 대조가 성립하지 않는다").toBeGreaterThan(0);

    const shapes = new Set([
      head!.style.gridTemplateColumns,
      ...rows.map((r) => r.style.gridTemplateColumns),
    ]);
    expect(
      [...shapes],
      `표 머리와 행의 격자가 갈렸다: ${[...shapes].join(" | ")}`,
    ).toHaveLength(1);

    // 빈 값 하나로 "일치" 가 되지 않게 한다 — 002 가 CSS 를 빈 값으로 바꿔 단언이
    // 빈 문자열을 상대로 통과하던 것과 같은 함정이다. 그리고 그 한 값은 확정 디자인의
    // 열 폭이어야 한다 (TestList.dc.html 의 행·표 머리가 쓰는 값).
    expect([...shapes][0]).toBe("96px 82px 1fr 64px 92px 150px 168px");
  });
});
