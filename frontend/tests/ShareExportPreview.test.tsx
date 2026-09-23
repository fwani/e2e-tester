/**
 * 내보내기 확인 화면 (019 T079 · US4).
 *
 * **되돌릴 수 없는 조작 앞의 유일한 방어선이다.** 확인하지 않으면 내려받을 수 없고,
 * 취소하면 아무것도 만들어지지 않는다.
 *
 * 평문 값을 **가리지 않는다**는 것이 이 파일의 중심이다 — 가려 놓으면 사번이나 사내 계정이
 * 섞여 있어도 발견할 수 없고, 그러면 이 화면이 있으나 마나다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ShareExport } from "../src/pages/ShareExport";

const PREVIEW = {
  project_name: "통합",
  test_count: 2,
  group_count: 1,
  start_urls: [
    { scope: "project", test_id: null, url: "https://internal.example" },
    { scope: "test", test_id: "TC-002", url: "https://internal.example/admin" },
  ],
  plaintext_values: [
    {
      test_id: "TC-001",
      step_id: "step-01",
      step_label: "사번 입력",
      field: "value",
      value: "2019-0421",
      truncated: false,
    },
  ],
  required_values: [],
  unreadable: ["TC-004: 정의를 읽을 수 없습니다"],
};

function stub() {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push(`${init?.method ?? "GET"} ${url}`);
      if (url.startsWith("/api/share/export/preview")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers(),
          text: () => Promise.resolve(JSON.stringify(PREVIEW)),
          clone: () => ({ text: () => Promise.resolve("") }),
        } as unknown as Response);
      }
      const headers = new Headers();
      headers.set("Content-Disposition", 'attachment; filename="s.itbshare.yaml"');
      headers.set("X-ITB-Share-Test-Count", "2");
      return Promise.resolve({
        ok: true,
        status: 200,
        headers,
        blob: () => Promise.resolve(new Blob(["b"])),
        text: () => Promise.resolve("{}"),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response);
    }),
  );
  return calls;
}

beforeEach(() => {
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

describe("내보내기 확인", () => {
  it("확인 전에는 파일을 만들지 않는다", async () => {
    const calls = stub();
    render(<ShareExport />);
    await screen.findByTestId("share-export-plaintext");
    // 미리보기만 부르고 내보내기는 부르지 않았다.
    expect(calls.some((c) => c === "POST /api/share/export")).toBe(false);
  });

  it("평문 값을 가리지 않고 보여 준다", async () => {
    stub();
    render(<ShareExport />);
    await screen.findByTestId("share-export-plaintext");
    // 사번이 그대로 보여야 발견할 수 있다.
    expect(screen.getByText("2019-0421")).toBeTruthy();
    expect(screen.getByText("사번 입력")).toBeTruthy();
  });

  it("시작 주소를 함께 나가는 정보로 보여 준다", async () => {
    stub();
    render(<ShareExport />);
    const urls = await screen.findByTestId("share-export-urls");
    expect(urls.textContent).toContain("https://internal.example");
    expect(urls.textContent).toContain("TC-002");
  });

  it("빠지는 테스트가 있으면 알린다", async () => {
    stub();
    render(<ShareExport />);
    const notice = await screen.findByTestId("share-export-unreadable");
    expect(notice.textContent).toContain("1건");
  });

  it("취소하면 아무것도 만들어지지 않는다", async () => {
    const calls = stub();
    const onClose = vi.fn();
    render(<ShareExport onClose={onClose} />);
    await screen.findByTestId("share-export-plaintext");
    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(onClose).toHaveBeenCalled();
    expect(calls.some((c) => c === "POST /api/share/export")).toBe(false);
  });

  it("확인한 뒤에만 파일이 만들어진다", async () => {
    const calls = stub();
    render(<ShareExport />);
    await screen.findByTestId("share-export-plaintext");
    fireEvent.click(screen.getByTestId("share-export-ack"));
    fireEvent.click(screen.getByRole("button", { name: /파일 내려받기/ }));
    await screen.findByTestId("share-export-done");
    expect(calls.filter((c) => c === "POST /api/share/export")).toHaveLength(1);
  });
});
