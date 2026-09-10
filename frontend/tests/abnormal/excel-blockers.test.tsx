/**
 * 엑셀 통로의 막힘 (014 T047 · 003 오류 계약).
 *
 * **막혔을 때 사유와 다음 행동이 화면에 있어야 한다.** 조용히 실패하거나 "요청이
 * 실패했습니다" 로만 끝나면 사용자는 파일을 고쳐야 하는지, 프로젝트를 나눠야 하는지,
 * 다시 시도하면 되는지 알 수 없다.
 *
 * 서버는 `next_action` 을 늘 채워 보낸다 (`domain/error.py` 의 전수 대응표). 이 파일은
 * 화면이 그것을 **버리지 않는지** 본다.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ImportPlanView } from "../../src/api/client";
import { ImportFilePicker, ImportPreview } from "../../src/pages/ImportPreview";

function errorBody(code: string, message: string, nextAction: string, detail: object = {}) {
  return {
    error: { code, category: "blocked", message, next_action: nextAction, detail },
  };
}

function stubFailure(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: false,
        status,
        headers: new Headers(),
        text: () => Promise.resolve(JSON.stringify(body)),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response),
    ),
  );
}

const PLAN: ImportPlanView = {
  plan_id: "pl_test",
  file_name: "설계서.xlsx",
  expires_at: "2026-09-10T10:00:00Z",
  draft_count: 1,
  group_count: 1,
  sheets: [
    {
      sheet_name: "회원",
      prefix: "USER",
      prefix_source: "from_rows",
      needs_prefix: false,
      group_name: "회원",
      existing_group_name: null,
      name_differs: false,
      row_count: 1,
      renumbered: [],
    },
  ],
  skipped: [],
  capacity: { needed: 1, available: 900, ok: true },
  warnings: [],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("파일이 거절될 때", () => {
  const pickFile = () => {
    const errors: { message: string; nextAction?: string }[] = [];
    const { container } = render(
      <ImportFilePicker
        label="엑셀에서 가져오기"
        onPlan={() => {}}
        onError={(e) => errors.push({ message: e.message, nextAction: e.nextAction })}
      />,
    );
    const input = container.querySelector("[data-import-file]") as HTMLInputElement;
    const file = new File(["nope"], "설계서.xlsx");
    fireEvent.change(input, { target: { files: [file] } });
    return errors;
  };

  it("스프레드시트가 아니면 사유가 전달된다", async () => {
    stubFailure(
      400,
      errorBody(
        "IMPORT_FILE_REJECTED",
        "스프레드시트 파일(.xlsx)이 아닙니다.",
        "더 작은 파일을 고르거나, 스프레드시트 형식(.xlsx)인지 확인한 뒤 다시 시도하세요.",
        { kind: "not_xlsx" },
      ),
    );
    const errors = pickFile();
    await waitFor(() => expect(errors.length).toBe(1));
    expect(errors[0]?.message).toContain("스프레드시트 파일");
  });

  it("다음 행동이 함께 전달된다", async () => {
    stubFailure(
      400,
      errorBody(
        "IMPORT_FILE_REJECTED",
        "시트가 상한(200개)을 넘습니다.",
        "더 작은 파일을 고르세요.",
        { kind: "sheet_count", limit: 200, actual: 300 },
      ),
    );
    const errors = pickFile();
    await waitFor(() => expect(errors.length).toBe(1));
    expect(errors[0]?.nextAction).toContain("더 작은 파일");
  });

  it("같은 파일을 다시 고를 수 있다", async () => {
    // input 의 값을 비우지 않으면 change 가 다시 일어나지 않아 재시도가 막힌다.
    stubFailure(400, errorBody("IMPORT_FILE_REJECTED", "거절", "다시"));
    const errors: unknown[] = [];
    const { container } = render(
      <ImportFilePicker label="가져오기" onPlan={() => {}} onError={(e) => errors.push(e)} />,
    );
    const input = container.querySelector("[data-import-file]") as HTMLInputElement;
    const file = new File(["x"], "a.xlsx");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(errors.length).toBe(1));
    expect(input.value).toBe("");
  });

  it("xlsx 만 고르도록 안내한다", () => {
    stubFailure(400, errorBody("IMPORT_FILE_REJECTED", "거절", "다시"));
    const { container } = render(
      <ImportFilePicker label="가져오기" onPlan={() => {}} onError={() => {}} />,
    );
    const input = container.querySelector("[data-import-file]") as HTMLInputElement;
    expect(input.accept).toBe(".xlsx");
  });
});

describe("확정이 막힐 때", () => {
  const confirm = () => {
    render(<ImportPreview plan={PLAN} onCancel={() => {}} onDone={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
  };

  it("계획이 만료되면 파일을 다시 고르라고 말한다", async () => {
    stubFailure(
      400,
      errorBody(
        "IMPORT_PLAN_NOT_FOUND",
        "미리보기가 만료됐거나 없습니다.",
        "미리보기가 만료됐습니다. 파일을 다시 고르세요.",
      ),
    );
    confirm();
    expect(await screen.findByText(/미리보기가 만료됐거나 없습니다/)).toBeTruthy();
    expect(screen.getByText(/파일을 다시 고르세요/)).toBeTruthy();
  });

  it("수용량이 넘치면 무엇을 하면 되는지 말한다", async () => {
    stubFailure(
      400,
      errorBody(
        "IMPORT_CAPACITY_EXCEEDED",
        "만들려는 초안이 50건인데 이 프로젝트에 남은 번호는 10개입니다.",
        "프로젝트를 나누거나, 가져올 행을 줄인 뒤 다시 시도하세요.",
        { needed: 50, available: 10 },
      ),
    );
    confirm();
    expect(await screen.findByText(/남은 번호는 10개입니다/)).toBeTruthy();
    expect(screen.getByText(/프로젝트를 나누거나/)).toBeTruthy();
  });

  it("되돌린 실패와 되돌리지 못한 실패를 다르게 말한다", async () => {
    stubFailure(
      500,
      errorBody(
        "IMPORT_FAILED",
        "가져오기가 실패했습니다.",
        "아무것도 만들어지지 않았습니다. 원인을 고친 뒤 다시 시도하세요.",
      ),
    );
    confirm();
    // 「아무것도 만들어지지 않았다」가 전달되어야 사용자가 다시 시도할 수 있다.
    expect(await screen.findByText(/아무것도 만들어지지 않았습니다/)).toBeTruthy();
  });

  it("계약 형태가 아닌 응답도 화면을 멈추지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 502,
          headers: new Headers(),
          text: () => Promise.resolve("<html>Bad Gateway</html>"),
          clone: () => ({ text: () => Promise.resolve("") }),
        } as unknown as Response),
      ),
    );
    confirm();
    // 사유를 모르더라도 무엇을 하면 되는지는 말한다.
    expect(await screen.findByText(/화면을 새로 고쳐/)).toBeTruthy();
  });

  it("실패한 뒤에도 취소로 나갈 수 있다", async () => {
    stubFailure(500, errorBody("IMPORT_FAILED", "실패", "다시 시도하세요."));
    const onCancel = vi.fn();
    render(<ImportPreview plan={PLAN} onCancel={onCancel} onDone={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await screen.findByText(/실패/);
    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(onCancel).toHaveBeenCalled();
  });
});
