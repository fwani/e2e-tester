/**
 * 018 — 주소가 화면을 고르고, 화면을 넘어 사는 상태가 이동을 견딘다 (design §2·§3·§5·§6 · §7.1).
 *
 * 005 R8 의 `useScreenUrl` 이 지키던 것(새로고침 복원 FR-166 · 뒤로가기 FR-167 · 지목 유지 FR-181·FR-239)을
 * 라우터 위에서 다시 고정하고, 018 이 새로 약속한 것(모든 화면 딥링크 · 일회성 명령 · 옛 주소 · 프로젝트
 * 조회 순서)을 더한다. 앱 전체를 메모리 라우터로 그려 **주소 → 화면**을 실제로 걷는다.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ImportPlanView } from "../src/api/client";
import { renderApp } from "./helpers/app";
import { stubServer } from "./helpers/fakeServer";

afterEach(() => {
  vi.unstubAllGlobals();
});

const action = (id: string) => document.querySelector<HTMLButtonElement>(`button[data-action="${id}"]`);

describe("주소마다 그 화면이 뜬다 (§2)", () => {
  it("/ — 테스트 목록", async () => {
    stubServer();
    renderApp("/");
    expect(await screen.findByText("로그인")).toBeTruthy();
  });

  it("/tests/TC-001/result — 결과 화면", async () => {
    stubServer();
    renderApp("/tests/TC-001/result");
    expect(await screen.findByText("Step 02 고치기")).toBeTruthy();
  });

  it("/tests/TC-001/edit — 편집 화면", async () => {
    stubServer();
    renderApp("/tests/TC-001/edit");
    expect(await screen.findByText("변경 저장")).toBeTruthy();
  });

  it("/tests/TC-001/edit?step=step-02 — 지목한 Step 이 펼쳐진다 (006 FR-181)", async () => {
    stubServer();
    renderApp("/tests/TC-001/edit?step=step-02");
    expect(await screen.findByText("dashboard-open")).toBeTruthy();
  });

  it("/tests/new — 만들기", async () => {
    stubServer();
    renderApp("/tests/new");
    expect(await screen.findByLabelText("시작 URL")).toBeTruthy();
  });

  it("/tests/new?draft= — 초안의 지시문이 미리 채워진다 (014 FR-031)", async () => {
    stubServer({
      drafts: { "D-0001": { draft_id: "D-0001", name: "초안", group_prefix: "TC", suggested_instruction: "로그인한다" } },
    });
    renderApp("/tests/new?draft=D-0001");
    await waitFor(() =>
      expect((screen.getByLabelText("자연어 지시") as HTMLTextAreaElement).value).toBe("로그인한다"),
    );
  });

  it("/keys — 키 관리", async () => {
    stubServer();
    renderApp("/keys");
    expect(await screen.findByRole("heading", { name: "키 관리" })).toBeTruthy();
  });

  it("/secrets — 비밀 값", async () => {
    stubServer();
    renderApp("/secrets");
    expect(await screen.findByRole("heading", { name: "비밀 값" })).toBeTruthy();
  });

  it("/projects — 프로젝트 선택", async () => {
    stubServer();
    renderApp("/projects");
    expect(await screen.findByRole("button", { name: /새 프로젝트 만들기/ })).toBeTruthy();
  });

  it("/sessions/:id — 실행 화면을 주소만으로 되찾는다", async () => {
    const calls = stubServer();
    renderApp("/sessions/s-new");
    await waitFor(() => expect(document.querySelector("[data-phase-pill]")).not.toBeNull());
    expect(calls.some((c) => c.method === "GET" && c.url === "/api/sessions/s-new")).toBe(true);
    expect(screen.queryByText("로그인")).toBeNull();
  });

  it("없는 경로는 목록으로 교체된다", async () => {
    stubServer();
    const { router } = renderApp("/없는/곳");
    expect(await screen.findByText("로그인")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("옛 주소 (§6)", () => {
  it("`?screen=` 주소는 새 주소로 **교체**된다 — 뒤로가기 기록에 남지 않는다", async () => {
    stubServer();
    const { router } = renderApp("/?screen=definition&test=TC-001&step=step-02");
    expect(await screen.findByText("dashboard-open")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/tests/TC-001/edit");
    expect(router.state.location.search).toBe("?step=step-02");
    expect(router.state.historyAction).toBe("REPLACE");
  });
});

describe("열린 프로젝트 (§3.2)", () => {
  it("열린 프로젝트가 없으면 어느 주소든 프로젝트 선택으로 간다", async () => {
    stubServer({ project: null });
    const { router } = renderApp("/tests/TC-001/result");
    await waitFor(() => expect(router.state.location.pathname).toBe("/projects"));
    expect(await screen.findByRole("button", { name: /새 프로젝트 만들기/ })).toBeTruthy();
  });

  it("세션 조회는 프로젝트를 확인한 **뒤에** 나간다 — 옛 뒤바뀜(2026-09-10 보고 1번)을 막는다", async () => {
    const calls = stubServer({ projectDelayMs: 30 });
    renderApp("/sessions/s-new");
    await waitFor(() => expect(calls.some((c) => c.url === "/api/sessions/s-new")).toBe(true));
    const first = calls.find((c) => c.url === "/api/sessions/s-new")!;
    expect(first.headers["X-ITB-Project-Root"]).toBe(encodeURIComponent("/tmp/p"));
  });
});

describe("실행 화면의 도착 정보 (§3.3)", () => {
  it("일회성 명령은 도착에 한 번 쓰이고 **기록에서 지워진다** — 새로 고쳐도 되살아나지 않는다", async () => {
    const calls = stubServer({ session: { state: "paused", pause_before_index: null } });
    const { router } = renderApp("/sessions/s-new?from=edit&step=step-02", {
      state: { aiInstruction: null, recordOnArrival: true, instructionOnArrival: null },
    });
    // 명령이 지워지기 전에 소비됐다 — 도착하자 기록이 켜졌다 (009 FR-291).
    await waitFor(() =>
      expect(
        calls.some((c) => c.method === "POST" && c.url === "/api/sessions/s-new/record-actions:start"),
      ).toBe(true),
    );
    // 기록에는 명령이 없다. 돌아갈 곳(주소)은 그대로다.
    await waitFor(() =>
      expect(router.state.location.state).toEqual({
        aiInstruction: null,
        recordOnArrival: false,
        instructionOnArrival: null,
      }),
    );
    expect(router.state.location.search).toBe("?from=edit&step=step-02");
  });

  it("명령 없이 들어오면 기록을 켜지 않는다", async () => {
    const calls = stubServer({ session: { state: "paused", pause_before_index: null } });
    renderApp("/sessions/s-new");
    await waitFor(() => expect(document.querySelector("[data-phase-pill]")).not.toBeNull());
    await new Promise((r) => setTimeout(r, 50));
    expect(calls.some((c) => c.url.includes("record-actions:start"))).toBe(false);
  });

  it("편집에서 온 세션은 끝나면 편집으로 돌아간다 — 새로 고친 뒤에도 (006 FR-204)", async () => {
    stubServer({ session: { state: "paused", pause_before_index: null } });
    const { router } = renderApp("/sessions/s-new?from=edit&step=step-02");
    await waitFor(() => expect(action("nav.back")).not.toBeNull());
    act(() => action("nav.back")!.click());
    await waitFor(() => expect(router.state.location.pathname).toBe("/tests/TC-001/edit"));
    expect(router.state.location.search).toBe("?step=step-02");
  });

  it("그 밖의 세션은 끝나면 목록으로 간다", async () => {
    stubServer({ session: { state: "paused", pause_before_index: null } });
    const { router } = renderApp("/sessions/s-new");
    await waitFor(() => expect(action("nav.back")).not.toBeNull());
    act(() => action("nav.back")!.click());
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });

  it("실행이 끝나면 결과로 넘어간다 — 편집에서 온 세션은 예외다 (2026-09-10 결정)", async () => {
    stubServer({ session: { state: "completed" } });
    const auto = renderApp("/sessions/s-new");
    await waitFor(() => expect(auto.router.state.location.pathname).toBe("/tests/TC-001/result"));
    auto.unmount();

    const fromEdit = renderApp("/sessions/s-new?from=edit");
    await waitFor(() => expect(document.querySelector("[data-phase-pill]")).not.toBeNull());
    await new Promise((r) => setTimeout(r, 50));
    expect(fromEdit.router.state.location.pathname).toBe("/sessions/s-new");
  });

  it("결과로 자동 이동한 뒤 뒤로 가면 목록으로 간다 — 세션으로 되튕기지 않는다", async () => {
    stubServer({ session: { state: "completed" } });
    const { router } = renderApp("/");
    expect(await screen.findByText("로그인")).toBeTruthy();
    await act(() => router.navigate("/sessions/s-new"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/tests/TC-001/result"));
    // 자동 이동은 세션 기록을 **교체**한다 — 밀어 넣으면 뒤로가기가 세션 주소로 돌아가고,
    // loader 가 세션을 다시 읽어 자동 이동이 또 일어나 뒤로가기가 통째로 막힌다.
    expect(router.state.historyAction).toBe("REPLACE");
    await act(() => router.navigate(-1));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });

  it("세션을 찾지 못하면 오류 없이 목록으로 교체된다 (옛 `openSession` 의 실패와 같다)", async () => {
    stubServer({ missingSessions: ["s-gone"] });
    const { router } = renderApp("/sessions/s-gone");
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(await screen.findByText("로그인")).toBeTruthy();
    expect(document.querySelector("[data-app-notice]")).toBeNull();
  });
});

describe("만들기의 초안 (§3.4 · §5)", () => {
  it("초안을 읽지 못하면 오류를 알리고 목록에 남는다 — 빈 지시문으로 들어가지 않는다 (014 US3)", async () => {
    stubServer();
    const { router } = renderApp("/tests/new?draft=D-없음");
    expect(await screen.findByText("찾을 수 없습니다")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/");
    expect(screen.queryByLabelText("시작 URL")).toBeNull();
  });
});

describe("가져오기 미리보기 (§3.4)", () => {
  const plan = {
    plan_id: "p-1",
    file_name: "설계서.xlsx",
    expires_at: "2026-09-17T01:00:00Z",
    draft_count: 0,
    group_count: 0,
    sheets: [],
    skipped: [],
    capacity: { needed: 0, available: 999, ok: true, groups: [] },
    warnings: [],
  } as ImportPlanView;

  it("맡긴 계획이 있으면 미리보기를 그린다", async () => {
    stubServer();
    renderApp("/import/p-1", { prepare: (store) => store.keepImportPlan(plan) });
    expect(await screen.findByText("설계서.xlsx")).toBeTruthy();
  });

  it("계획이 없으면(새로 고침) 사라졌다고 알리고 목록으로 교체된다 — 백엔드는 그대로다", async () => {
    stubServer();
    const { router } = renderApp("/import/p-1");
    expect(await screen.findByText("가져오기 미리보기가 사라졌습니다.")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("뒤로가기·앞으로가기 (005 FR-167 · 007 FR-241)", () => {
  it("결과에서 뒤로 가면 목록, 앞으로 가면 지목까지 그대로인 결과다", async () => {
    stubServer();
    const { router } = renderApp("/");
    expect(await screen.findByText("로그인")).toBeTruthy();
    await act(() => router.navigate("/tests/TC-001/result?step=step-02"));
    expect(await screen.findByText("Step 02 고치기")).toBeTruthy();
    // 숫자 이동은 기록만 옮기고 곧바로 돌아온다 — 위치는 기다려서 본다.
    await act(() => router.navigate(-1));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    await act(() => router.navigate(1));
    await waitFor(() => expect(router.state.location.pathname).toBe("/tests/TC-001/result"));
    expect(router.state.location.search).toBe("?step=step-02");
  });
});

describe("실행 경로 (005 T021 · U-06)", () => {
  it("실행을 연달아 눌러도 세션은 하나이고, 실행 화면으로 간다", async () => {
    const calls = stubServer();
    const { router } = renderApp("/tests/TC-001/result");
    await waitFor(() => expect(action("run.all")).not.toBeNull());
    act(() => action("run.all")!.click());
    act(() => action("run.all")?.click());
    await waitFor(() => expect(router.state.location.pathname).toBe("/sessions/s-new"));
    expect(calls.filter((c) => c.url === "/api/sessions" && c.method === "POST")).toHaveLength(1);
  });
});
