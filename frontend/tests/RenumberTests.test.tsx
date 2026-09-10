/**
 * 테스트 번호 정리 (2026-09-10 사용자 결정).
 *
 * 「테스트 번호가 sequencial 하게 증가하는 것은 맞다. 001, 002, 003, 004 순서로 생성 후,
 * 번호를 일괄적으로 맞추거나 재조정하는 방법이 있으면 좋겠다」.
 *
 * 이 파일이 지키는 것은 셋이다.
 *
 * 1. **확인 전에는 요청이 나가지 않는다.** 식별자는 사용자가 git 에 커밋해 보관하는
 *    자산의 이름이고 (헌법 원칙 V), 되돌리는 조작이 없다 — 삭제와 같은 무게다.
 * 2. **어느 식별자가 어디로 갔는지 화면에 남는다.** 사용자가 자기 저장소·문서·CI 에서
 *    고쳐야 하는 정보이므로 토스트로 흘려 보내면 그 일을 할 수 없다.
 * 3. **아무것도 안 바뀐 것과 이미 정리되어 있던 것을 구별해 말한다.**
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";

interface Call {
  url: string;
  method: string;
}

function stub(routes: Record<string, unknown>) {
  const calls: Call[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, method: init?.method ?? "GET" });
    const key = Object.keys(routes)
      .filter((k) => url.startsWith(k))
      .sort((a, b) => b.length - a.length)[0];
    const body = key === undefined ? undefined : routes[key];
    const status = body === undefined ? 404 : 200;
    return Promise.resolve({
      ok: status < 400,
      status,
      text: () => Promise.resolve(body === undefined ? "" : JSON.stringify(body)),
      clone: () => ({ text: () => Promise.resolve("") }),
    } as unknown as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

const row = (id: string, name: string) => ({
  id,
  name,
  step_count: 1,
  authoring_mode: "record",
  outcome: null,
  last_run_at: null,
  failure_summary: null,
  group_prefix: id.split("-")[0],
});

const listing = (ids: [string, string][]) => ({
  counts: { total: ids.length, pass: 0, fail: 0 },
  groups: [],
  tests: ids.map(([id, name]) => row(id, name)),
  problems: [],
});

function mount() {
  return render(
    <TestList
      projectName="번호"
      onCreate={() => {}}
      onRun={() => {}}
      pendingRunId={null}
      onOpenResult={() => {}}
      activeSessions={[]}
    />,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("번호 정리", () => {
  it("확인하기 전에는 아무 요청도 나가지 않는다", async () => {
    const calls = stub({
      "/api/tests": listing([["TC-001", "하나"], ["TC-005", "둘"]]),
      "/api/groups": { groups: [] },
    });
    mount();
    await screen.findByText("하나");

    fireEvent.click(screen.getByRole("button", { name: "번호 정리" }));

    expect(document.querySelector("[data-renumber-confirm]")).not.toBeNull();
    expect(calls.some((c) => c.url.includes(":renumber"))).toBe(false);
  });

  it("돌아가기를 누르면 확인이 걷히고 요청도 없다", async () => {
    const calls = stub({
      "/api/tests": listing([["TC-001", "하나"]]),
      "/api/groups": { groups: [] },
    });
    mount();
    await screen.findByText("하나");
    fireEvent.click(screen.getByRole("button", { name: "번호 정리" }));

    fireEvent.click(screen.getByRole("button", { name: "돌아가기" }));

    expect(document.querySelector("[data-renumber-confirm]")).toBeNull();
    expect(calls.some((c) => c.url.includes(":renumber"))).toBe(false);
  });

  it("확인하면 바뀐 식별자가 화면에 남는다", async () => {
    const calls = stub({
      "/api/tests:renumber": {
        renumbered: [{ from_id: "TC-005", to_id: "TC-002", name: "둘" }],
        unchanged: 1,
      },
      "/api/tests": listing([["TC-001", "하나"], ["TC-002", "둘"]]),
      "/api/groups": { groups: [] },
    });
    mount();
    await screen.findByText("하나");
    fireEvent.click(screen.getByRole("button", { name: "번호 정리" }));

    fireEvent.click(
      document.querySelector("[data-renumber-confirm-run]") as HTMLButtonElement,
    );

    await waitFor(() =>
      expect(document.querySelector("[data-renumbered-notice]")).not.toBeNull(),
    );
    expect(calls.some((c) => c.url.includes(":renumber") && c.method === "POST")).toBe(true);
    expect(screen.getByText(/TC-005 → TC-002/)).toBeTruthy();
  });

  it("이미 정리되어 있었으면 그렇게 말한다 — 아무 일도 없던 것처럼 두지 않는다", async () => {
    stub({
      "/api/tests:renumber": { renumbered: [], unchanged: 2 },
      "/api/tests": listing([["TC-001", "하나"], ["TC-002", "둘"]]),
      "/api/groups": { groups: [] },
    });
    mount();
    await screen.findByText("하나");
    fireEvent.click(screen.getByRole("button", { name: "번호 정리" }));
    fireEvent.click(
      document.querySelector("[data-renumber-confirm-run]") as HTMLButtonElement,
    );

    await waitFor(() =>
      expect(screen.getByText(/이미 정리되어 있었습니다/)).toBeTruthy(),
    );
  });
});
