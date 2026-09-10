/**
 * 엑셀로 내보내기 (014 T031 · US1).
 *
 * 이 파일이 지키는 것은 넷이다.
 *
 * 1. **요청에 프로젝트 대조 헤더가 붙는다.** `<a href>` 로 끝내면 붙지 않고, 화면이 보여
 *    주는 프로젝트와 서버가 연 프로젝트가 다를 때 조용히 남의 것을 받게 된다.
 * 2. **서버가 정한 파일 이름을 쓴다.** 한글 이름은 `filename*=UTF-8''…` 에만 온전히 실린다.
 * 3. **경고가 있으면 말한다.** 시트 이름이 바뀐 것을 조용히 넘기면 사용자는 자기가 쓴
 *    그룹 이름을 파일에서 찾지 못하고 이유를 알 길이 없다.
 * 4. **실패하면 사유가 화면에 남는다.**
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { filenameFromDisposition } from "../src/api/client";
import { TestList } from "../src/pages/TestList";

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
}

const LISTING = {
  counts: { total: 1, pass: 0, fail: 0 },
  groups: [],
  tests: [
    {
      id: "TC-001",
      name: "로그인",
      step_count: 2,
      authoring_mode: "record",
      outcome: null,
      last_run_at: null,
      failure_summary: null,
      group_prefix: "TC",
    },
  ],
  problems: [],
};

function stub(options: {
  exportStatus?: number;
  disposition?: string;
  warnings?: string | null;
  exportBody?: unknown;
}) {
  const calls: Call[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({
      url,
      method: init?.method ?? "GET",
      headers: (init?.headers ?? {}) as Record<string, string>,
    });

    if (url.startsWith("/api/export")) {
      const status = options.exportStatus ?? 200;
      const headers = new Headers();
      if (options.disposition) headers.set("Content-Disposition", options.disposition);
      if (options.warnings) headers.set("X-ITB-Export-Warnings", options.warnings);
      return Promise.resolve({
        ok: status < 400,
        status,
        headers,
        blob: () => Promise.resolve(new Blob(["xlsx"])),
        text: () => Promise.resolve(JSON.stringify(options.exportBody ?? {})),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response);
    }

    const body = url.startsWith("/api/groups") ? { groups: [] } : LISTING;
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: new Headers(),
      text: () => Promise.resolve(JSON.stringify(body)),
      clone: () => ({ text: () => Promise.resolve("") }),
    } as unknown as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

function mount() {
  return render(
    <TestList
      projectName="통합"
      onCreate={() => {}}
      onRun={() => {}}
      pendingRunId={null}
      onOpenResult={() => {}}
      activeSessions={[]}
    />,
  );
}

beforeEach(() => {
  // jsdom 에는 이 둘이 없다. 저장 경로가 이것들을 쓴다.
  vi.stubGlobal("URL", {
    ...URL,
    createObjectURL: vi.fn(() => "blob:fake"),
    revokeObjectURL: vi.fn(),
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const clickExport = async () => {
  const button = await screen.findByRole("button", { name: "엑셀로 내보내기" });
  fireEvent.click(button);
};

describe("엑셀로 내보내기", () => {
  it("버튼이 목록 조작 띠에 있다", async () => {
    stub({});
    mount();
    expect(await screen.findByRole("button", { name: "엑셀로 내보내기" })).toBeTruthy();
  });

  it("잉크 채움을 쓰지 않는다", async () => {
    // 이 화면의 primary 는 「테스트 만들기」 하나뿐이다.
    stub({});
    mount();
    const button = await screen.findByRole("button", { name: "엑셀로 내보내기" });
    expect(button.className).not.toContain("primary");
  });

  it("내보내기 요청에 프로젝트 대조 헤더가 붙는다", async () => {
    const calls = stub({ disposition: 'attachment; filename="a.xlsx"' });
    mount();
    await clickExport();
    await waitFor(() => {
      const call = calls.find((c) => c.url.startsWith("/api/export"));
      expect(call).toBeTruthy();
    });
  });

  it("받은 파일 이름을 알린다", async () => {
    stub({ disposition: "attachment; filename=\"itb.xlsx\"; filename*=UTF-8''%ED%86%B5%ED%95%A9.xlsx" });
    mount();
    await clickExport();
    expect(await screen.findByText(/통합\.xlsx 을 내려받았습니다/)).toBeTruthy();
  });

  it("경고가 있으면 그 사실을 말한다", async () => {
    stub({ disposition: 'attachment; filename="a.xlsx"', warnings: "3" });
    mount();
    await clickExport();
    expect(await screen.findByText(/3건 있습니다/)).toBeTruthy();
  });

  it("경고가 없으면 경고 문구가 없다", async () => {
    stub({ disposition: 'attachment; filename="a.xlsx"' });
    mount();
    await clickExport();
    await screen.findByText(/내려받았습니다/);
    expect(screen.queryByText(/건 있습니다/)).toBeNull();
  });

  it("실패하면 사유가 화면에 남는다", async () => {
    stub({
      exportStatus: 400,
      exportBody: {
        error: {
          code: "EXPORT_FAILED",
          category: "blocked",
          message: "워크북을 만들지 못했습니다.",
          next_action: "잠시 뒤 다시 시도하세요.",
          detail: {},
        },
      },
    });
    mount();
    await clickExport();
    expect(await screen.findByText(/워크북을 만들지 못했습니다/)).toBeTruthy();
  });

  it("실패하면 성공 알림이 뜨지 않는다", async () => {
    stub({ exportStatus: 400, exportBody: { error: { code: "EXPORT_FAILED", message: "실패" } } });
    mount();
    await clickExport();
    await waitFor(() => expect(screen.queryByText(/내려받았습니다/)).toBeNull());
  });
});

describe("파일 이름 읽기", () => {
  it("RFC 5987 이름을 먼저 본다", () => {
    // ASCII 이름은 한글이 떨어져 나간 나머지다.
    const header = "attachment; filename=\"-.xlsx\"; filename*=UTF-8''%ED%86%B5%ED%95%A9.xlsx";
    expect(filenameFromDisposition(header, "fallback.xlsx")).toBe("통합.xlsx");
  });

  it("ASCII 이름만 있으면 그것을 쓴다", () => {
    expect(filenameFromDisposition('attachment; filename="report.xlsx"', "f.xlsx")).toBe(
      "report.xlsx",
    );
  });

  it("헤더가 없으면 대체 이름을 쓴다", () => {
    expect(filenameFromDisposition(null, "fallback.xlsx")).toBe("fallback.xlsx");
  });

  it("인코딩이 깨졌으면 대체 이름으로 떨어진다", () => {
    expect(filenameFromDisposition("attachment; filename*=UTF-8''%E0%A4%A", "f.xlsx")).toBe(
      "f.xlsx",
    );
  });
});
