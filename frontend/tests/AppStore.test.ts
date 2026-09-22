/**
 * 018 §3.1·§3.2 — 앱 저장소.
 *
 * 가장 중요한 것은 **프로젝트 조회가 한 번이고, 끝나는 순간 모든 요청이 그 프로젝트를 말한다**는 것이다.
 * 옛 `App.tsx` 의 `openProject` 가 「효과로 미루지 않고 곧바로 세운다」고 적은 판단(2026-09-10 사용자
 * 보고 1번)을 저장소가 이어받는다. 헤더 대조 자체는 `ProjectRootGuard.test.ts` 가 본다.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { setExpectedProjectRoot, tests, type ImportPlanView, type ProjectView } from "../src/api/client";
import { createAppStore } from "../src/app/appStore";

const PROJECT = { name: "P", root: "/tmp/p", default_start_url: "http://t/" } as ProjectView;
const HEADER = "X-ITB-Project-Root";

interface Call {
  url: string;
  headers: Record<string, string>;
}

function stub(project: { status: number; body: unknown }) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, headers: (init?.headers ?? {}) as Record<string, string> });
      const body = url === "/api/project" ? project : { status: 200, body: { tests: [], problems: [] } };
      return new Response(JSON.stringify(body.body), { status: body.status });
    }),
  );
  return calls;
}

const NOT_OPEN = {
  status: 404,
  body: {
    error: {
      code: "PROJECT_NOT_OPEN",
      category: "blocked",
      message: "열린 프로젝트가 없습니다",
      next_action: "프로젝트를 여세요",
      detail: {},
    },
  },
};

afterEach(() => {
  setExpectedProjectRoot(null);
  vi.unstubAllGlobals();
});

describe("열린 프로젝트 (018 §3.2)", () => {
  it("처음에는 모른다 — `undefined` 다", () => {
    expect(createAppStore().getState().project).toBeUndefined();
  });

  it("동시에 여러 번 물어도 조회는 한 번이다 — 미들웨어는 이동마다 돈다", async () => {
    const calls = stub({ status: 200, body: PROJECT });
    const store = createAppStore();
    const [a, b] = await Promise.all([store.ensureProject(), store.ensureProject()]);
    await store.ensureProject();
    expect(a?.root).toBe("/tmp/p");
    expect(b?.root).toBe("/tmp/p");
    expect(calls.filter((c) => c.url === "/api/project")).toHaveLength(1);
  });

  it("조회가 끝나면 다음 요청부터 그 프로젝트를 말한다", async () => {
    const calls = stub({ status: 200, body: PROJECT });
    await createAppStore().ensureProject();
    await tests.list();
    const listCall = calls.find((c) => c.url.startsWith("/api/tests"));
    expect(listCall?.headers[HEADER]).toBe(encodeURIComponent("/tmp/p"));
  });

  it("조회에 실패하면 열린 프로젝트가 없다 — `null` 이다", async () => {
    stub(NOT_OPEN);
    const store = createAppStore();
    await expect(store.ensureProject()).resolves.toBeNull();
    expect(store.getState().project).toBeNull();
  });

  it("사용자가 먼저 연 프로젝트를 늦게 온 조회가 덮지 않는다", async () => {
    let release: (r: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((resolve) => (release = resolve))),
    );
    const store = createAppStore();
    const pending = store.ensureProject();
    const mine = { ...PROJECT, root: "/tmp/mine", name: "mine" };
    store.openProject(mine);
    release(new Response(JSON.stringify(PROJECT), { status: 200 }));
    await expect(pending).resolves.toEqual(mine);
    expect(store.getState().project).toEqual(mine);
  });

  it("이름 바꾸기는 같은 경로일 때만 반영된다 (012 FR-405)", () => {
    const store = createAppStore();
    store.openProject(PROJECT);
    store.renameProject("/tmp/other", "남의 것");
    expect(store.getState().project?.name).toBe("P");
    store.renameProject("/tmp/p", "새 이름");
    expect(store.getState().project?.name).toBe("새 이름");
  });

  it("프로젝트를 닫으면 요청이 더는 프로젝트를 말하지 않는다 (012 FR-416)", async () => {
    const calls = stub({ status: 200, body: PROJECT });
    const store = createAppStore();
    store.openProject(PROJECT);
    store.openProject(null);
    await tests.list();
    expect(calls.at(-1)?.headers[HEADER]).toBeUndefined();
  });
});

describe("구독 (018 §3.1)", () => {
  it("상태가 바뀔 때마다 알리고, 끊으면 더 알리지 않는다", () => {
    const store = createAppStore();
    const listener = vi.fn();
    const off = store.subscribe(listener);
    store.setError({ message: "m", nextAction: "n", category: "blocked", code: "X" });
    store.setImportDone(null);
    expect(listener).toHaveBeenCalledTimes(2);
    off();
    store.setError(null);
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("바뀌지 않은 필드는 같은 객체다 — 선택 함수가 헛돌지 않는다", () => {
    const store = createAppStore();
    store.openProject(PROJECT);
    const before = store.getState().project;
    store.setError(null);
    expect(store.getState().project).toBe(before);
  });
});

describe("가져오기 계획 (018 §3.4)", () => {
  const plan = { plan_id: "p-1", file_name: "a.xlsx" } as ImportPlanView;

  it("맡긴 계획을 돌려주고, 버리면 없다", () => {
    const store = createAppStore();
    expect(store.importPlan("p-1")).toBeNull();
    store.keepImportPlan(plan);
    expect(store.importPlan("p-1")).toBe(plan);
    store.dropImportPlan("p-1");
    expect(store.importPlan("p-1")).toBeNull();
  });

  it("저장소마다 따로다 — 새로 고친 앱은 계획을 모른다", () => {
    createAppStore().keepImportPlan(plan);
    expect(createAppStore().importPlan("p-1")).toBeNull();
  });
});
