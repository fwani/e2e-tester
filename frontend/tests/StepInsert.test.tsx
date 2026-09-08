/**
 * 009 T029 — 브라우저 없이 Step 을 넣는다 (US1 · FR-285~FR-290·FR-310).
 *
 * **이 파일이 지키는 것은 넷이다.**
 *
 * 1. 브라우저를 열지 않은 편집 화면에서 요소 지목이 필요 없는 넷을 넣을 수 있다.
 * 2. 요소를 요구하는 종류가 **자리에 있고** 비활성이며 갈 길을 가리킨다 — 감춰지면 실패다.
 * 3. 저장 전 삽입에 「미저장」 칩이 붙고, 넣었다가 지우면 변경이 남지 않는다.
 * 4. 실행 중에는 삽입 조작이 활성으로 보이지 않는다 (SC-508).
 */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EditView } from "../src/pages/EditView";
import { renderSession } from "./helpers/session";
import type { Step } from "../src/types/generated/step";

const verified = (value: string) => ({ value, status: "verified" });

const TEST = {
  dsl_version: 1,
  id: "TC-001",
  name: "로그인",
  authoring_mode: "record",
  start_url: "https://example.internal/login",
  browser: "chromium",
  ai_instruction: null,
  variables: [],
  steps: [
    {
      id: "step-01",
      type: "navigate",
      label: "로그인 화면",
      author: "human",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      url: "https://example.internal/login",
    },
    {
      id: "step-02",
      type: "click",
      label: "로그인 클릭",
      author: "human",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      target: {
        tag: "button",
        test_id: verified("login-submit"),
        role: null,
        accessible_name: null,
        role_status: null,
        label: null,
        text: null,
        stable_attr: null,
        css: verified("button#submit"),
      },
    },
  ],
  created_at: "2026-09-08T00:00:00Z",
  updated_at: "2026-09-08T00:00:00Z",
};

function view(overrides: Record<string, unknown> = {}) {
  return {
    test: TEST,
    revision: "rev-1",
    editable: true,
    blocked_by: null,
    blocking_session_id: null,
    locked_fields: [],
    warnings: [],
    ...overrides,
  };
}

function stubFetch(first: Record<string, unknown> = view()) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      calls.push({ url: String(url), method, body });
      if (method === "PUT") {
        return new Response(JSON.stringify({ ...view(), revision: "rev-2" }), { status: 200 });
      }
      return new Response(JSON.stringify(first), { status: 200 });
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

/** 세션 화면용 Step 목록 — 회귀 검사가 쓴다. */
const SESSION_STEPS = TEST.steps as unknown as Step[];

const action = (id: string) =>
  document.querySelector(`button[data-action="${id}"]`) as HTMLButtonElement;

async function renderScreen(props: Record<string, unknown> = {}) {
  render(<EditView testId="TC-001" onBack={() => undefined} {...props} />);
  await waitFor(() => expect(screen.getByText("로그인 화면")).toBeTruthy());
}

function selectStep(stepId: string) {
  const row = document.querySelector(`[data-step-row="${stepId}"] button`) as HTMLButtonElement;
  act(() => row.click());
}

/** 삽입 입력면을 연다. 조작은 팔레트에 있고 폼은 그 자리에 펼쳐진다. */
function openInsert() {
  act(() => action("step.insertManual").click());
}

// ─── 1. 브라우저 없이 넣는다 (FR-285·FR-286) ────────────────────────────────

describe("직접 입력으로 Step 추가 — 브라우저 없이 (US1)", () => {
  beforeEach(() => stubFetch());

  it("세션을 만들지 않는다 — 정의 조회 하나로 넣는 자리까지 열린다 (FR-285)", async () => {
    const calls = stubFetch();
    await renderScreen();
    openInsert();

    expect(screen.getByLabelText("넣을 Step 종류")).toBeTruthy();
    expect(calls.some((c) => c.url.includes("/api/sessions"))).toBe(false);
  });

  it("주소로 이동을 고른 자리에 넣는다 (FR-285)", async () => {
    await renderScreen();
    selectStep("step-02");
    openInsert();

    fireEvent.change(screen.getByLabelText("주소"), {
      target: { value: "https://example.internal/orders" },
    });
    act(() => screen.getByRole("button", { name: "넣기" }).click());

    // Step 02 자리에 들어가고 그 Step 은 뒤로 밀린다.
    const rows = [...document.querySelectorAll("[data-step-row]")];
    expect(rows).toHaveLength(3);
    expect(rows[1]?.textContent).toContain("주소로 이동 — https://example.internal/orders");
    expect(rows[2]?.textContent).toContain("로그인 클릭");
  });

  it("고른 Step 이 없으면 맨 뒤에 넣는다 — 「먼저 고르세요」로 잠그지 않는다", async () => {
    await renderScreen();
    openInsert();

    expect(screen.getByText(/목록 맨 뒤 앞에 추가|목록 맨 뒤/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("주소"), { target: { value: "/orders" } });
    act(() => screen.getByRole("button", { name: "넣기" }).click());

    const rows = [...document.querySelectorAll("[data-step-row]")];
    expect(rows).toHaveLength(3);
    expect(rows[2]?.textContent).toContain("주소로 이동 — /orders");
  });

  it("네 종류를 고를 수 있다 (FR-286)", async () => {
    await renderScreen();
    openInsert();

    const group = screen.getByLabelText("넣을 Step 종류");
    const names = [...group.querySelectorAll("button")].map((b) => b.textContent);
    expect(names).toEqual(["주소로 이동", "주소 검증", "화면 텍스트 검증", "탭 닫기"]);
  });

  it("종류마다 필요한 값만 그린다 — 빈 칸을 남기지 않는다", async () => {
    await renderScreen();
    openInsert();

    // 주소로 이동: 주소만
    expect(screen.getByLabelText("주소")).toBeTruthy();
    expect(screen.queryByLabelText("기대 텍스트")).toBeNull();

    act(() => screen.getByRole("radio", { name: "화면 텍스트 검증" }).click());
    expect(screen.getByLabelText("기대 텍스트")).toBeTruthy();
    expect(screen.queryByLabelText("주소")).toBeNull();

    act(() => screen.getByRole("radio", { name: "탭 닫기" }).click());
    expect(screen.getByLabelText("탭 번호")).toBeTruthy();
    expect(screen.queryByLabelText("일치 방식")).toBeNull();
  });

  it("값이 비면 넣을 수 없다 — 누르고 나서 서버가 거절하는 경로를 만들지 않는다", async () => {
    await renderScreen();
    openInsert();

    expect((screen.getByRole("button", { name: "넣기" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("목록에 뜰 이름을 미리 보여주고 그것을 그대로 보낸다 (research R6)", async () => {
    const calls = stubFetch();
    await renderScreen();
    openInsert();
    fireEvent.change(screen.getByLabelText("주소"), { target: { value: "/orders" } });

    const preview = screen.getByLabelText("넣을 Step 미리보기").textContent;
    expect(preview).toBe("주소로 이동 — /orders");

    act(() => screen.getByRole("button", { name: "넣기" }).click());
    act(() => action("save").click());

    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    const put = calls.find((c) => c.method === "PUT")!;
    const op = (put.body as { edits: { op: string; spec: { label: string } }[] }).edits[0]!;
    expect(op.op).toBe("insert");
    // 미리보기에 쓴 문자열이 그대로 나간다 — 저장 순간 이름이 바뀌지 않는다.
    expect(op.spec.label).toBe(preview);
  });
});

// ─── 2. 요소를 요구하는 종류 — 감추지 않는다 (FR-287) ───────────────────────

describe("요소를 요구하는 종류 (FR-287 · 원칙 IV)", () => {
  beforeEach(() => stubFetch());

  it("다섯이 자리에 있고 비활성이다 — 감춰지면 위반이다", async () => {
    await renderScreen();
    openInsert();

    for (const name of ["클릭", "입력", "선택", "마우스 올리기", "끌어놓기"]) {
      const btn = screen.getByRole("button", { name });
      expect(btn, `${name} 이 자리에 없다`).toBeTruthy();
      expect((btn as HTMLButtonElement).disabled, `${name} 이 활성이다`).toBe(true);
    }
  });

  it("왜 못 만드는지와 갈 길이 같은 자리에 있다 (006 E-03)", async () => {
    await renderScreen();
    openInsert();

    expect(screen.getByText("요소는 살아 있는 화면에서만 지목할 수 있습니다")).toBeTruthy();
    expect(screen.getByRole("button", { name: "브라우저 열어 이 자리에서 멈추기" })).toBeTruthy();
  });

  it("갈 길을 누르면 그 자리에서 멈추는 세션을 연다 (FR-291 로 이어진다)", async () => {
    const onOpenBrowserAt = vi.fn();
    await renderScreen({ onOpenBrowserAt });
    selectStep("step-02");
    openInsert();

    act(() => screen.getByRole("button", { name: "브라우저 열어 이 자리에서 멈추기" }).click());

    await waitFor(() => expect(onOpenBrowserAt).toHaveBeenCalled());
    expect(onOpenBrowserAt.mock.calls[0]?.[1]).toBe(1);
  });
});

// ─── 3. 저장 전 삽입 (FR-289·FR-310) ───────────────────────────────────────

describe("저장 전 삽입 (FR-289·FR-310)", () => {
  beforeEach(() => stubFetch());

  it("「미저장」 칩이 그 행에만 붙는다 (FR-310)", async () => {
    await renderScreen();
    openInsert();
    fireEvent.change(screen.getByLabelText("주소"), { target: { value: "/orders" } });
    act(() => screen.getByRole("button", { name: "넣기" }).click());

    const chips = [...document.querySelectorAll("[data-cell='unsaved']")];
    expect(chips).toHaveLength(1);
    const row = chips[0]?.closest("[data-step-row]");
    expect(row?.textContent).toContain("주소로 이동 — /orders");
  });

  it("넣었다가 지우면 저장할 변경이 남지 않는다 (FR-289)", async () => {
    await renderScreen();
    openInsert();
    fireEvent.change(screen.getByLabelText("주소"), { target: { value: "/orders" } });
    act(() => screen.getByRole("button", { name: "넣기" }).click());

    // 넣은 행을 고르고 지운다.
    const chip = document.querySelector("[data-cell='unsaved']")!;
    const row = chip.closest("[data-step-row]") as HTMLElement;
    act(() => (row.querySelector("button") as HTMLButtonElement).click());
    act(() => action("step.delete").click());

    // 아무것도 하지 않은 것과 같아야 한다 — 저장이 잠긴다.
    expect((action("save") as HTMLButtonElement).disabled).toBe(true);
    expect([...document.querySelectorAll("[data-step-row]")]).toHaveLength(2);
  });

  it("되돌리기가 삽입도 되돌린다", async () => {
    await renderScreen();
    openInsert();
    fireEvent.change(screen.getByLabelText("주소"), { target: { value: "/orders" } });
    act(() => screen.getByRole("button", { name: "넣기" }).click());
    expect([...document.querySelectorAll("[data-step-row]")]).toHaveLength(3);

    act(() => action("edits.revert").click());

    expect([...document.querySelectorAll("[data-step-row]")]).toHaveLength(2);
  });
});

// ─── 4. 실행 중에는 잠긴다 (FR-306 · SC-508) ────────────────────────────────

describe("실행 중 잠금 (FR-306 · SC-508)", () => {
  it("실행 중인 테스트에서는 삽입 조작이 활성으로 보이지 않는다", async () => {
    stubFetch(
      view({ editable: false, blocked_by: "running", blocking_session_id: "sess-1" }),
    );
    await renderScreen();

    const btn = action("step.insertManual");
    expect(btn, "조작이 감춰졌다 — 자리를 남겨야 한다 (FR-234)").toBeTruthy();
    expect(btn.disabled).toBe(true);
  });
});

// ─── 009 T053 · 기존 추가 경로 회귀 (SC-509 · FR-309) ───────────────────────
//
// **009 는 추가 경로를 하나 더할 뿐 없애지 않는다.** 새 기능이 도는 것보다 기존 경로가
// 그대로인 것이 더 자주 깨진다 — 특히 팔레트의 자리를 건드렸기 때문이다 (계약 §3-3-0).

describe("기존 추가 경로 셋이 그대로다 (SC-509 · FR-309)", () => {
  it("일시정지 화면에서 셋이 같은 자리·같은 문구로 있다", () => {
    renderSession({ state: "paused", steps: SESSION_STEPS, current_step_index: 2 });

    // 직접 조작 녹화 — 팔레트 버튼
    expect(action("step.recordStart")).toBeTruthy();
    expect(action("step.recordStart").textContent).toContain("직접 조작으로 Step 추가");
    // 검증 추가 — 팔레트 버튼
    expect(action("step.addAssertion")).toBeTruthy();
    expect(action("step.addAssertion").textContent).toContain("검증 추가");
    // 자연어 — 입력칸과 버튼이 한 쌍이다 (FR-078)
    expect(screen.getByLabelText("자연어로 Step 추가")).toBeTruthy();
    expect(action("step.addNaturalLanguage")).toBeTruthy();
  });

  it("새 조작이 그 셋의 자리를 차지하지 않는다 — 넷이 각각 하나다", () => {
    renderSession({ state: "paused", steps: SESSION_STEPS, current_step_index: 2 });

    for (const id of [
      "step.recordStart",
      "step.addAssertion",
      "step.addNaturalLanguage",
      "step.insertManual",
    ]) {
      expect(
        document.querySelectorAll(`[data-action="${id}"]`),
        `${id} 의 자리가 하나가 아니다`,
      ).toHaveLength(1);
    }
  });

  it("직접 조작 녹화를 누르면 그 조작이 그대로 나간다", () => {
    const onRecordStart = vi.fn();
    renderSession(
      { state: "paused", steps: SESSION_STEPS, current_step_index: 2 },
      { onRecordStart },
    );

    act(() => action("step.recordStart").click());

    expect(onRecordStart).toHaveBeenCalledTimes(1);
  });

  it("검증 추가를 누르면 검증 폼이 열린다 — 삽입 입력면이 대신 열리지 않는다", () => {
    renderSession({ state: "paused", steps: SESSION_STEPS, current_step_index: 2 });

    act(() => action("step.addAssertion").click());

    // 검증 폼의 것이고 삽입 폼의 것이 아니다.
    expect(screen.queryByLabelText("넣을 Step 종류")).toBeNull();
  });
});
