/**
 * 삭제 결과를 **사실대로** 말한다 (2026-09-10 · 003 AS-046 · EC-007).
 *
 * ## 무엇이 깨져 있었나
 *
 * 두 창에서 같은 테스트를 지우면 두 번째 창의 삭제는 **옮길 것이 없다.** 서버는 그것을
 * 오류로 만들지 않고 `trashed_to: null` 로 알린다 (013 FR-436 — 사용자가 원한 결과는
 * 이미 이루어져 있다). 화면이 그 값을 읽지 않아 두 가지가 겹쳐 있었다.
 *
 * 1. **한 개 삭제는 아무것도 그리지 않았다.** `act()` 가 `await fn()` 의 값을 버려
 *    `.then((res) => …)` 의 `res` 가 언제나 `undefined` 였다 — 「한 개와 여러 개의
 *    결과가 같다」(SC-632)가 조용히 깨져 있었다.
 * 2. 여러 개 삭제는 옮기지 않은 것까지 **「휴지통으로 옮겼습니다」**로 말하고, 옮긴
 *    자리 칸에 빈 값을 그렸다.
 *
 * 둘이 합쳐져 「조용한 성공」이 됐다. 이 파일이 그 자리를 지킨다.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";

function stub(routes: Record<string, unknown>) {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push(`${init?.method ?? "GET"} ${url}`);
      const key = Object.keys(routes)
        .filter((k) => url.startsWith(k))
        .sort((a, b) => b.length - a.length)[0];
      const body = key === undefined ? undefined : routes[key];
      const status = body === undefined ? 404 : 200;
      const text = body === undefined ? "" : JSON.stringify(body);
      return Promise.resolve({
        ok: status < 400,
        status,
        text: () => Promise.resolve(text),
        clone: () => ({ text: () => Promise.resolve(text) }),
      } as unknown as Response);
    }),
  );
  return calls;
}

const listing = (names: string[]) => ({
  counts: { total: names.length, pass: 0, fail: 0 },
  groups: [],
  tests: names.map((name, i) => ({
    id: `TC-00${i + 1}`,
    name,
    step_count: 1,
    authoring_mode: "record",
    outcome: null,
    last_run_at: null,
    failure_summary: null,
    group_prefix: "TC",
  })),
  problems: [],
});

function mount() {
  render(
    <TestList
      projectName="삭제"
      onCreate={() => {}}
      onRun={() => {}}
      pendingRunId={null}
      onOpenResult={() => {}}
      activeSessions={[]}
    />,
  );
}

/** 행 메뉴 → 삭제 → 확인. 확인 버튼의 이름도 「삭제」다. */
async function deleteFirstRow(name: string) {
  fireEvent.click(await screen.findByRole("button", { name: `${name} 추가 동작` }));
  fireEvent.click(screen.getByRole("button", { name: "삭제" }));
  fireEvent.click(screen.getByRole("button", { name: "삭제" }));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("한 개 삭제도 결과를 그린다 (SC-632)", () => {
  it("옮겨진 자리가 화면에 남는다 — 그 값이 되돌리는 방법 전부다", async () => {
    stub({
      "/api/tests/TC-001": { id: "TC-001", name: "하나", trashed_to: "/trash/20260910-TC-001" },
      "/api/tests": listing(["하나"]),
      "/api/groups": { groups: [] },
    });
    mount();

    await deleteFirstRow("하나");

    await waitFor(() =>
      expect(document.querySelector("[data-trashed-notice]")).not.toBeNull(),
    );
    expect(screen.getByText("/trash/20260910-TC-001")).toBeTruthy();
  });
});

describe("이미 없던 것을 옮겼다고 말하지 않는다 (AS-046)", () => {
  it("한 개 — 옮긴 표시 대신 이미 지워져 있었다고 알린다", async () => {
    stub({
      "/api/tests/TC-001": { id: "TC-001", name: "하나", trashed_to: null },
      "/api/tests": listing(["하나"]),
      "/api/groups": { groups: [] },
    });
    mount();

    await deleteFirstRow("하나");

    await waitFor(() =>
      expect(document.querySelector("[data-error-notice]")).not.toBeNull(),
    );
    expect(document.querySelector("[data-trashed-notice]")).toBeNull();
    expect(screen.getByText(/이미 지워져 있어 옮기지 않았습니다/)).toBeTruthy();
    // 다음 행동이 비어 있으면 안내가 아니다 (003 EC-004).
    expect(
      document.querySelector("[data-error-next-action]")!.textContent!.trim().length,
    ).toBeGreaterThan(0);
  });

  it("깨진 것이 아니라 **막힌 것**이다 — 사용자가 할 수 있는 일이 있다", async () => {
    stub({
      "/api/tests/TC-001": { id: "TC-001", name: "하나", trashed_to: null },
      "/api/tests": listing(["하나"]),
      "/api/groups": { groups: [] },
    });
    mount();

    await deleteFirstRow("하나");

    await waitFor(() =>
      expect(document.querySelector("[data-error-notice]")).not.toBeNull(),
    );
    expect(
      document.querySelector("[data-error-notice]")!.getAttribute("data-category"),
    ).toBe("blocked");
  });

  it("섞여 있으면 둘 다 말한다 — 옮긴 자리도, 이미 없던 것도", async () => {
    stub({
      "/api/tests:delete": {
        deleted: [
          { id: "TC-001", name: "하나", trashed_to: "/trash/20260910-TC-001" },
          { id: "TC-002", name: "둘", trashed_to: null },
        ],
      },
      "/api/tests": listing(["하나", "둘"]),
      "/api/groups": { groups: [] },
    });
    mount();
    await screen.findByText("하나");

    fireEvent.click(screen.getByRole("checkbox", { name: "하나 선택" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "둘 선택" }));
    fireEvent.click(document.querySelector("[data-test-bulk-delete]") as HTMLButtonElement);
    fireEvent.click(
      document.querySelector("[data-test-bulk-confirm-run]") as HTMLButtonElement,
    );

    await waitFor(() =>
      expect(document.querySelector("[data-trashed-notice]")).not.toBeNull(),
    );
    expect(document.querySelector("[data-error-notice]")).not.toBeNull();
    expect(screen.getByText("/trash/20260910-TC-001")).toBeTruthy();
  });
});
