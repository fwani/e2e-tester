/**
 * 공유용 내보내기 (019 T030 · US1·US4).
 *
 * 이 파일이 지키는 것은 넷이다.
 *
 * 1. **확인 없이 내려받을 수 없다.** 내보내기는 되돌릴 수 없고, 나가기 전에 보이는 것이
 *    유일한 방어선이다 (US4).
 * 2. **평문 값을 가리지 않는다.** 가려 놓으면 사번이나 사내 계정이 섞여 있어도 발견할 수
 *    없다 (research R11).
 * 3. **고른 것이 있으면 그것만 보낸다.** 선택이 없으면 프로젝트 전체다.
 * 4. **요청에 프로젝트 대조 헤더가 붙는다.** `<a href>` 로 끝내면 붙지 않고, 화면이 보여
 *    주는 프로젝트와 서버가 연 프로젝트가 다를 때 조용히 남의 것을 받게 된다.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { setExpectedProjectRoot } from "../src/api/client";
import { ShareExport } from "../src/pages/ShareExport";

interface Call {
  url: string;
  method: string;
  headers: Record<string, string>;
}

const PREVIEW = {
  project_name: "통합",
  test_count: 2,
  group_count: 1,
  start_urls: [{ scope: "project", test_id: null, url: "https://example.internal" }],
  plaintext_values: [
    {
      test_id: "TC-001",
      step_id: "step-01",
      step_label: "아이디 입력",
      field: "value",
      value: "platform-user",
      truncated: false,
    },
  ],
  required_values: [
    {
      name: "SECRET_LOGIN_PW",
      sensitive: true,
      declared: true,
      usages: [
        { test_id: "TC-001", step_id: "step-02", step_label: "비밀번호 입력", field: "value" },
      ],
    },
  ],
  unreadable: [],
};

function stub(options: { preview?: unknown; exportStatus?: number } = {}) {
  const calls: Call[] = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({
      url,
      method: init?.method ?? "GET",
      headers: (init?.headers ?? {}) as Record<string, string>,
    });

    if (url.startsWith("/api/share/export/preview")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers(),
        text: () => Promise.resolve(JSON.stringify(options.preview ?? PREVIEW)),
        clone: () => ({ text: () => Promise.resolve("") }),
      } as unknown as Response);
    }

    const status = options.exportStatus ?? 200;
    const headers = new Headers();
    headers.set(
      "Content-Disposition",
      "attachment; filename=\"share.itbshare.yaml\"; filename*=UTF-8''%ED%86%B5%ED%95%A9.itbshare.yaml",
    );
    headers.set("X-ITB-Share-Test-Count", "2");
    return Promise.resolve({
      ok: status < 400,
      status,
      headers,
      blob: () => Promise.resolve(new Blob(["bundle"])),
      text: () =>
        Promise.resolve(
          JSON.stringify({
            error: { code: "SHARE_EXPORT_EMPTY", message: "내보낼 테스트가 없습니다." },
          }),
        ),
      clone: () => ({ text: () => Promise.resolve("") }),
    } as unknown as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
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
  setExpectedProjectRoot(null);
});

const acknowledge = async () => {
  fireEvent.click(await screen.findByTestId("share-export-ack"));
};

const download = () => screen.getByRole("button", { name: /파일 내려받기/ });

describe("공유용 내보내기", () => {
  it("확인하기 전에는 내려받을 수 없다", async () => {
    stub();
    render(<ShareExport />);
    await screen.findByTestId("share-export-summary");
    expect((download() as HTMLButtonElement).disabled).toBe(true);
  });

  it("확인하면 내려받기가 열린다", async () => {
    stub();
    render(<ShareExport />);
    await acknowledge();
    expect((download() as HTMLButtonElement).disabled).toBe(false);
  });

  it("파일에 들어가는 평문 값을 가리지 않고 보여 준다", async () => {
    stub();
    render(<ShareExport />);
    await screen.findByTestId("share-export-plaintext");
    // 가렸다면 이 단언이 실패한다 — 그것이 이 검증의 목적이다.
    expect(screen.getByText("platform-user")).toBeTruthy();
  });

  it("민감 값이 파일에 들어가지 않는다는 사실을 보내는 사람에게 알린다", async () => {
    stub();
    render(<ShareExport />);
    const notice = await screen.findByTestId("share-export-secret-notice");
    expect(notice.textContent).toContain("민감 값은 파일에 들어가지 않습니다");
    expect(notice.textContent).toContain("SECRET_LOGIN_PW");
  });

  it("선택이 없으면 전체를 보낸다", async () => {
    const calls = stub();
    render(<ShareExport />);
    await acknowledge();
    fireEvent.click(download());
    await waitFor(() => {
      const post = calls.find((c) => c.method === "POST");
      expect(post).toBeTruthy();
    });
    const preview = calls.find((c) => c.url.startsWith("/api/share/export/preview"));
    expect(preview?.url).toBe("/api/share/export/preview");
  });

  it("고른 테스트만 보낸다", async () => {
    const calls = stub();
    render(<ShareExport testIds={["TC-001", "TC-003"]} />);
    await screen.findByTestId("share-export-summary");
    const preview = calls.find((c) => c.url.startsWith("/api/share/export/preview"));
    expect(preview?.url).toContain("TC-001%2CTC-003");
  });

  it("내려받기 요청에 프로젝트 대조 헤더가 붙는다", async () => {
    setExpectedProjectRoot("/tmp/projects/통합");
    const calls = stub();
    render(<ShareExport />);
    await acknowledge();
    fireEvent.click(download());
    await waitFor(() => {
      const post = calls.find((c) => c.method === "POST");
      expect(post?.headers["X-ITB-Project-Root"]).toBeTruthy();
    });
  });

  it("끝나면 무엇을 받았는지 말한다", async () => {
    stub();
    render(<ShareExport />);
    await acknowledge();
    fireEvent.click(download());
    const done = await screen.findByTestId("share-export-done");
    expect(done.textContent).toContain("통합.itbshare.yaml");
    expect(done.textContent).toContain("2건");
  });

  it("실패하면 사유가 화면에 남는다", async () => {
    stub({ exportStatus: 400 });
    render(<ShareExport />);
    await acknowledge();
    fireEvent.click(download());
    await waitFor(() => {
      expect(screen.getByText(/내보낼 테스트가 없습니다/)).toBeTruthy();
    });
  });
});
