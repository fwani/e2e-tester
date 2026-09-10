/**
 * 프로젝트 목록 줄의 조작. 012 FR-399~FR-425 · contracts/ui-contract.md.
 *
 * **프로젝트만 이름을 못 고치고 못 지웠다.** 테스트에는 둘 다 있는데 프로젝트에는
 * 없어서, 잘못 지은 이름은 영구히 남고 쓰지 않는 프로젝트는 첫 화면에 계속 쌓였다.
 *
 * 이 파일이 지키는 것은 두 가지다.
 *
 * 1. **줄의 상태가 조작 집합을 정한다** (data-model §3). 줄마다 따로 판단하지 않는다.
 * 2. **되돌릴 수 없는 쪽을 조용히 하지 않는다.** 확인 전에는 요청이 나가지 않고,
 *    끝난 뒤에는 되돌리는 방법이 화면에 남는다.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ProjectListItem } from "../src/api/client";
import { ProjectSetup } from "../src/pages/ProjectSetup";

const managed: ProjectListItem = {
  root: "/home/me/.local/share/itb/projects/결제",
  name: "결제",
  last_opened_at: "2026-09-04T02:11:00Z",
  origin: "managed",
  accessible: true,
  unavailable_reason: null,
};

const external: ProjectListItem = {
  root: "/home/me/work/외부-프로젝트",
  name: "외부 프로젝트",
  last_opened_at: "2026-09-03T00:00:00Z",
  origin: "external",
  accessible: true,
  unavailable_reason: null,
};

const gone: ProjectListItem = {
  root: "/home/me/elsewhere/moved",
  name: "옮겨진 것",
  last_opened_at: "2026-09-01T00:00:00Z",
  origin: "external",
  accessible: false,
  unavailable_reason: "디렉터리가 없습니다. 옮겨졌거나 삭제된 것으로 보입니다.",
};

interface Call {
  url: string;
  method: string;
  body: unknown;
}

/**
 * 요청을 모두 기록하는 가짜 fetch. **무엇이 나갔는지가 이 파일의 주된 단언이다** —
 * "확인 전에는 아무것도 옮기지 않는다" 는 화면 표시가 아니라 요청의 부재로만 셀 수 있다.
 */
function stub(routes: Record<string, { status?: number; body: unknown }>) {
  const calls: Call[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({
      url,
      method,
      body: init?.body === undefined ? undefined : JSON.parse(String(init.body)),
    });
    const key = Object.keys(routes)
      .filter((k) => url.startsWith(k))
      .sort((a, b) => b.length - a.length)[0];
    const route = key === undefined ? undefined : routes[key];
    const status = route?.status ?? (route === undefined ? 404 : 200);
    return Promise.resolve({
      ok: status < 400,
      status,
      text: () => Promise.resolve(route === undefined ? "" : JSON.stringify(route.body)),
    } as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

const listing = (projects: ProjectListItem[]) => ({ body: { projects, warning: null } });

const summaryOf = (item: ProjectListItem, count = 3) => ({
  body: { root: item.root, name: item.name, test_count: count, origin: item.origin },
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

// ─── UC-012-01 · 줄의 상태가 조작을 정한다 ─────────────────────────────────

describe("줄 상태 × 조작 (data-model §3)", () => {
  it("접근 가능한 줄에는 열기·이름 바꾸기·삭제·목록에서 치우기가 모두 있다", async () => {
    stub({ "/api/project/list": listing([managed]) });
    render(<ProjectSetup onOpened={() => {}} />);

    await screen.findByText("결제");
    expect(screen.getByRole("button", { name: "열기" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "이름 바꾸기" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "삭제" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "목록에서 치우기" })).toBeTruthy();
  });

  it("열 수 없는 줄에는 삭제가 없고 목록에서 치우기만 있다 (FR-418)", async () => {
    stub({ "/api/project/list": listing([gone]) });
    render(<ProjectSetup onOpened={() => {}} />);

    await screen.findByText("옮겨진 것");
    expect(screen.queryByRole("button", { name: "삭제" })).toBeNull();
    expect(screen.queryByRole("button", { name: "이름 바꾸기" })).toBeNull();
    expect(screen.getByRole("button", { name: "목록에서 치우기" })).toBeTruthy();
  });

  it("열 수 없는 줄은 왜 조작이 없는지 말한다 (FR-406)", async () => {
    stub({ "/api/project/list": listing([gone]) });
    render(<ProjectSetup onOpened={() => {}} />);

    await screen.findByText(/열 수 없는 상태여서 이름 변경과 삭제를 할 수 없습니다/);
  });

  it("두 조작의 설명이 디스크의 파일이 어떻게 되는지 각각 말한다 (FR-423 · SC-620)", async () => {
    stub({ "/api/project/list": listing([managed]) });
    render(<ProjectSetup onOpened={() => {}} />);

    await screen.findByText("결제");
    expect(screen.getByRole("button", { name: "삭제" }).getAttribute("title")).toContain(
      "휴지통으로 옮깁니다",
    );
    expect(
      screen.getByRole("button", { name: "목록에서 치우기" }).getAttribute("title"),
    ).toContain("디스크의 파일은 지우지 않습니다");
  });
});

// ─── UC-012-02 · 이름 인라인 편집 ──────────────────────────────────────────

describe("이름 인라인 편집 (US1)", () => {
  it("확인 창 없이 두 조작으로 끝난다 (SC-614)", async () => {
    const calls = stub({
      "/api/project/list": listing([managed]),
      "/api/project/name": { body: { ...managed, name: "결제 회귀" } },
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "이름 바꾸기" }));
    const input = screen.getByLabelText("프로젝트 이름") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "결제 회귀" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await screen.findByText("결제 회귀");
    const patch = calls.find((c) => c.method === "PATCH");
    expect(patch?.url).toContain("/api/project/name");
    expect(patch?.body).toEqual({ root: managed.root, name: "결제 회귀" });
  });

  it("빈 이름은 요청을 만들지 않고 그 자리에서 사유를 말한다 (FR-403)", async () => {
    const calls = stub({ "/api/project/list": listing([managed]) });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "이름 바꾸기" }));
    const input = screen.getByLabelText("프로젝트 이름");
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.keyDown(input, { key: "Enter" });

    await screen.findByText("프로젝트 이름은 비워 둘 수 없습니다.");
    expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(0);
    // 입력 칸이 열린 채로 남는다 — 사용자가 그 자리에서 고칠 수 있어야 한다.
    expect(screen.getByLabelText("프로젝트 이름")).toBeTruthy();
  });

  it("Esc 는 원래 이름으로 되돌리고 요청하지 않는다", async () => {
    const calls = stub({ "/api/project/list": listing([managed]) });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "이름 바꾸기" }));
    const input = screen.getByLabelText("프로젝트 이름");
    fireEvent.change(input, { target: { value: "버릴 이름" } });
    fireEvent.keyDown(input, { key: "Escape" });

    await screen.findByText("결제");
    expect(calls.filter((c) => c.method === "PATCH")).toHaveLength(0);
  });
});

// ─── UC-012-03·04 · 삭제 확인과 완료 표시 ──────────────────────────────────

describe("삭제 = 휴지통 이동 (US2)", () => {
  it("확인 전에는 어떤 삭제 요청도 나가지 않는다 (FR-412 · SC-617)", async () => {
    const calls = stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed),
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));

    await screen.findByText(/휴지통으로 옮길까요/);
    expect(calls.filter((c) => c.url.includes("/api/project/trash"))).toHaveLength(0);
  });

  it("확인 단계가 무엇이 사라지는지와 되돌릴 수 있다는 사실을 말한다 (FR-411)", async () => {
    stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed, 7),
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));

    await screen.findByText(/저장된 테스트 7개가 함께 옮겨집니다/);
    expect(screen.getAllByText(managed.root).length).toBeGreaterThan(0);
    await screen.findByText(/지우지 않고 휴지통으로 옮깁니다/);
  });

  it("외부 위치 프로젝트는 그 사실을 확인 단계에 표시한다 (FR-424)", async () => {
    stub({
      "/api/project/list": listing([external]),
      "/api/project/summary": summaryOf(external),
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));

    await screen.findByText(/도구 바깥에서 만들어진 위치입니다/);
  });

  it("취소하면 아무것도 바뀌지 않는다 (FR-412)", async () => {
    const calls = stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed),
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));
    fireEvent.click(await screen.findByRole("button", { name: "취소" }));

    await screen.findByRole("button", { name: "삭제" });
    expect(calls.filter((c) => c.url.includes("/api/project/trash"))).toHaveLength(0);
  });

  it("완료되면 옮겨진 위치를 그대로 보여주고 되돌리는 방법을 말한다 (FR-410·FR-425)", async () => {
    const destination = "/home/me/.local/share/itb/trash/20260910-071530-결제";
    stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed),
      "/api/project/trash": {
        body: { root: managed.root, name: "결제", trashed_to: destination, was_open: false },
      },
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));
    fireEvent.click(await screen.findByRole("button", { name: "휴지통으로 옮기기" }));

    await screen.findByText(destination);
    await screen.findByText(/되돌리려면 이 폴더를 원래 자리로 옮기세요/);
  });

  it("이미 없던 프로젝트는 「목록에서 뺐습니다」로 말한다 (FR-420)", async () => {
    stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed),
      "/api/project/trash": {
        body: { root: managed.root, name: "결제", trashed_to: null, was_open: false },
      },
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));
    fireEvent.click(await screen.findByRole("button", { name: "휴지통으로 옮기기" }));

    await screen.findByText(/목록에서 뺐습니다/);
  });

  it("열려 있던 프로젝트를 지우면 열린 상태를 비우라고 알린다 (FR-416)", async () => {
    stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed),
      "/api/project/trash": {
        body: { root: managed.root, name: "결제", trashed_to: "/t/1", was_open: true },
      },
    });
    const closed = vi.fn();
    render(<ProjectSetup onOpened={() => {}} onProjectClosed={closed} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));
    fireEvent.click(await screen.findByRole("button", { name: "휴지통으로 옮기기" }));

    await waitFor(() => expect(closed).toHaveBeenCalledTimes(1));
  });
});

// ─── UC-012-06 · 거절과 실패는 그 줄에 붙는다 ──────────────────────────────

describe("거절·실패 표시", () => {
  it("실행 중이면 사유와 다음 행동이 그 줄에 뜬다 (FR-417)", async () => {
    stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed),
      "/api/project/trash": {
        status: 409,
        body: {
          error: {
            code: "PROJECT_IN_USE",
            category: "blocked",
            message: "실행 중인 브라우저가 있어 이 프로젝트를 삭제할 수 없습니다.",
            next_action: "실행 중인 브라우저를 먼저 중지한 뒤 다시 삭제하세요.",
            detail: {},
          },
        },
      },
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));
    fireEvent.click(await screen.findByRole("button", { name: "휴지통으로 옮기기" }));

    await screen.findByText(/실행 중인 브라우저가 있어/);
    await screen.findByText(/먼저 중지한 뒤 다시 삭제하세요/);
  });

  it("옮기기에 실패하면 「그대로 있습니다」가 화면에 나온다 (FR-414 · SC-618)", async () => {
    stub({
      "/api/project/list": listing([managed]),
      "/api/project/summary": summaryOf(managed),
      "/api/project/trash": {
        status: 500,
        body: {
          error: {
            code: "PROJECT_DELETE_FAILED",
            category: "blocked",
            message: "프로젝트를 휴지통으로 옮기지 못했습니다: Permission denied",
            next_action:
              "프로젝트는 그대로 남아 있습니다. 저장 위치의 권한과 남은 공간을 확인하세요.",
            detail: {},
          },
        },
      },
    });
    render(<ProjectSetup onOpened={() => {}} />);

    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));
    fireEvent.click(await screen.findByRole("button", { name: "휴지통으로 옮기기" }));

    // 실패 후 사용자가 가장 먼저 묻는 것에 답한다 — "내 테스트는 어떻게 됐나".
    await screen.findByText(/그대로 남아 있습니다/);
  });
});
