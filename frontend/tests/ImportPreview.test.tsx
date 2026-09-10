/**
 * 가져오기 미리보기 (014 T046 · US2).
 *
 * 이 화면이 지켜야 하는 것은 넷이다.
 *
 * 1. **확정 전에는 아무 요청도 나가지 않는다** (FR-016). 취소가 프로젝트를 건드리지
 *    않는다는 것은 취소해 봐야 확인된다.
 * 2. **접두어 입력 칸은 물어야 하는 시트에만 나온다** (FR-022a).
 * 3. **바뀌는 것을 미리 말한다** — 번호 변경, 기존 그룹 이름 유지 (FR-023b·FR-024a).
 * 4. **빠지는 것을 위치와 함께 말한다** (FR-018).
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ImportPlanView, SheetPlanView } from "../src/api/client";
import { ImportPreview } from "../src/pages/ImportPreview";

interface Call {
  url: string;
  method: string;
  body: unknown;
}

function stub(commitStatus = 201, commitBody: unknown = { drafts: [] }) {
  const calls: Call[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({
      url,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? JSON.parse(init.body) : null,
    });
    return Promise.resolve({
      ok: commitStatus < 400,
      status: commitStatus,
      headers: new Headers(),
      text: () => Promise.resolve(JSON.stringify(commitBody)),
      clone: () => ({ text: () => Promise.resolve("") }),
    } as unknown as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

const sheet = (over: Partial<SheetPlanView> = {}): SheetPlanView => ({
  sheet_name: "회원",
  prefix: "USER",
  prefix_source: "from_rows",
  needs_prefix: false,
  group_name: "회원",
  existing_group_name: null,
  name_differs: false,
  row_count: 2,
  renumbered: [],
  ...over,
});

const plan = (over: Partial<ImportPlanView> = {}): ImportPlanView => ({
  plan_id: "pl_test",
  file_name: "설계서.xlsx",
  expires_at: "2026-09-10T10:00:00Z",
  draft_count: 2,
  group_count: 1,
  sheets: [sheet()],
  skipped: [],
  capacity: { needed: 2, available: 900, ok: true },
  warnings: [],
  ...over,
});

function mount(p: ImportPlanView, onCancel = () => {}, onDone = () => {}) {
  return render(<ImportPreview plan={p} onCancel={onCancel} onDone={onDone} />);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("무엇이 만들어지는가", () => {
  it("그룹 수와 초안 수를 말한다", () => {
    stub();
    mount(plan());
    expect(screen.getByText(/그룹 1개, 테스트 초안 2건을 만듭니다/)).toBeTruthy();
  });

  it("초안이 테스트가 아니라는 것을 말한다", () => {
    stub();
    mount(plan());
    expect(screen.getByText(/초안은 아직 테스트가 아닙니다/)).toBeTruthy();
  });

  it("파일 이름을 보여준다", () => {
    stub();
    mount(plan());
    expect(screen.getByText("설계서.xlsx")).toBeTruthy();
  });

  it("시트 수를 보여준다", () => {
    stub();
    mount(plan({ sheets: [sheet(), sheet({ sheet_name: "데이터", prefix: "DATA" })] }));
    expect(screen.getByText("시트 2개")).toBeTruthy();
  });
});

describe("확정 전에는 아무것도 만들지 않는다", () => {
  it("화면을 그리는 것만으로 요청이 나가지 않는다", () => {
    const calls = stub();
    mount(plan());
    expect(calls).toEqual([]);
  });

  it("취소는 요청을 내지 않는다", () => {
    const calls = stub();
    const onCancel = vi.fn();
    mount(plan(), onCancel);
    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(onCancel).toHaveBeenCalled();
    expect(calls).toEqual([]);
  });

  it("가져오기를 눌러야 확정 요청이 나간다", async () => {
    const calls = stub();
    mount(plan());
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => {
      expect(calls.map((c) => c.url)).toContain("/api/import/commit");
    });
  });

  it("확정 요청이 계획 식별자를 싣는다", async () => {
    const calls = stub();
    mount(plan());
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => {
      const commit = calls.find((c) => c.url === "/api/import/commit");
      expect((commit?.body as { plan_id: string }).plan_id).toBe("pl_test");
    });
  });
});

describe("접두어를 물어야 하는 시트", () => {
  it("물어야 하는 시트에만 입력 칸이 나온다", () => {
    stub();
    mount(
      plan({
        sheets: [
          sheet(),
          sheet({ sheet_name: "데이터관리", prefix: null, needs_prefix: true }),
        ],
      }),
    );
    expect(screen.queryByLabelText("회원 그룹 접두어")).toBeNull();
    expect(screen.getByLabelText("데이터관리 그룹 접두어")).toBeTruthy();
  });

  it("접두어를 아는 시트는 값을 보여준다", () => {
    stub();
    mount(plan());
    expect(screen.getByText("USER")).toBeTruthy();
  });

  it("비우면 건너뛴다고 말한다", () => {
    stub();
    mount(plan({ sheets: [sheet({ prefix: null, needs_prefix: true })] }));
    const input = screen.getByLabelText("회원 그룹 접두어") as HTMLInputElement;
    expect(input.placeholder).toContain("건너뜀");
  });

  it("입력한 접두어가 확정 요청에 실린다", async () => {
    const calls = stub();
    mount(plan({ sheets: [sheet({ sheet_name: "데이터관리", prefix: null, needs_prefix: true })] }));
    fireEvent.change(screen.getByLabelText("데이터관리 그룹 접두어"), {
      target: { value: "data" },
    });
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => {
      const commit = calls.find((c) => c.url === "/api/import/commit");
      expect((commit?.body as { prefixes: Record<string, string> }).prefixes).toEqual({
        데이터관리: "DATA",
      });
    });
  });

  it("몇 개를 답했는지 말한다", () => {
    stub();
    mount(
      plan({
        sheets: [
          sheet({ sheet_name: "가", prefix: null, needs_prefix: true }),
          sheet({ sheet_name: "나", prefix: null, needs_prefix: true }),
        ],
      }),
    );
    expect(screen.getByText(/시트 2개 중 0개 답했습니다/)).toBeTruthy();
  });

  it("접두어를 답하면 만들 초안 수가 는다", () => {
    stub();
    mount(
      plan({
        draft_count: 0,
        group_count: 0,
        sheets: [sheet({ sheet_name: "데이터관리", prefix: null, needs_prefix: true, row_count: 6 })],
      }),
    );
    expect(screen.getByText(/초안 0건을 만듭니다/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("데이터관리 그룹 접두어"), {
      target: { value: "DATA" },
    });
    expect(screen.getByText(/초안 6건을 만듭니다/)).toBeTruthy();
  });
});

describe("무엇이 바뀌는가", () => {
  it("번호가 바뀐 행을 원래 값과 함께 보여준다", () => {
    stub();
    mount(
      plan({
        sheets: [sheet({ renumbered: [{ row: 7, from: "USER-003", to: "USER-014" }] })],
      }),
    );
    expect(screen.getByText(/번호가 바뀐 행 1건/)).toBeTruthy();
    expect(screen.getByText(/7행: USER-003 → USER-014/)).toBeTruthy();
  });

  it("기존 그룹 이름을 유지한다고 말한다", () => {
    // 가져오기는 더하는 일이지 고치는 일이 아니다 (FR-024a).
    stub();
    mount(
      plan({
        sheets: [sheet({ existing_group_name: "사용자관리", name_differs: true })],
      }),
    );
    expect(screen.getByText(/이미 있는 그룹 「사용자관리」을 씁니다/)).toBeTruthy();
  });

  it("이름이 같으면 그 말을 하지 않는다", () => {
    stub();
    mount(plan({ sheets: [sheet({ existing_group_name: "회원", name_differs: false })] }));
    expect(screen.queryByText(/이미 있는 그룹/)).toBeNull();
  });

  it("경고를 보여준다", () => {
    stub();
    mount(plan({ warnings: ["「혼재」 시트에 접두어가 섞여 있습니다."] }));
    expect(screen.getByText(/접두어가 섞여 있습니다/)).toBeTruthy();
  });
});

describe("무엇이 빠지는가", () => {
  it("건너뛸 행을 시트와 행 번호로 말한다", () => {
    stub();
    mount(plan({ skipped: [{ sheet_name: "회원", row: 9, reason: "no_title" }] }));
    expect(screen.getByText(/건너뛸 행 1건/)).toBeTruthy();
    expect(screen.getByText(/회원 9행 — 「대상기능」 칸이 비어 있음/)).toBeTruthy();
  });

  it("이유를 사람이 읽는 말로 바꾼다", () => {
    stub();
    mount(plan({ skipped: [{ sheet_name: "메모", row: 1, reason: "no_columns" }] }));
    expect(screen.getByText(/필수 컬럼\(TC ID·대상기능\)이 없음/)).toBeTruthy();
  });

  it("건너뛸 행이 없으면 그 자리를 그리지 않는다", () => {
    stub();
    mount(plan());
    expect(screen.queryByText(/건너뛸 행/)).toBeNull();
  });
});

describe("수용량", () => {
  it("남은 번호보다 많으면 확정을 막는다", () => {
    stub();
    mount(plan({ draft_count: 50, capacity: { needed: 50, available: 10, ok: false } }));
    const button = screen.getByRole("button", { name: "가져오기" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });

  it("남은 수를 말한다", () => {
    stub();
    mount(plan({ draft_count: 50, capacity: { needed: 50, available: 10, ok: false } }));
    expect(screen.getByText(/남은 번호는 10개입니다/)).toBeTruthy();
  });

  it("들어가면 막지 않는다", () => {
    stub();
    mount(plan());
    const button = screen.getByRole("button", { name: "가져오기" }) as HTMLButtonElement;
    expect(button.disabled).toBe(false);
  });
});

describe("실패", () => {
  it("확정이 실패하면 사유가 화면에 남는다", async () => {
    stub(400, {
      error: {
        code: "IMPORT_CAPACITY_EXCEEDED",
        category: "blocked",
        message: "남은 번호가 부족합니다.",
        next_action: "프로젝트를 나누세요.",
        detail: {},
      },
    });
    mount(plan());
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    expect(await screen.findByText(/남은 번호가 부족합니다/)).toBeTruthy();
  });

  it("실패하면 완료로 넘어가지 않는다", async () => {
    stub(400, { error: { code: "IMPORT_FAILED", message: "실패" } });
    const onDone = vi.fn();
    mount(plan(), () => {}, onDone);
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => expect(onDone).not.toHaveBeenCalled());
  });

  it("성공하면 완료를 알린다", async () => {
    stub(201, { created_groups: [], drafts: [{ draft_id: "D-0001" }] });
    const onDone = vi.fn();
    mount(plan(), () => {}, onDone);
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
  });
});
