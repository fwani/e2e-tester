/**
 * 키 관리. DR-028~DR-031 · SC-107.
 *
 * 사용자가 겪은 것: "키 쌍 만들기를 하면 422 에러가 나옴."
 *
 * 실체는 두 겹이었다 (research R3).
 * 1. 암호구 최소 길이(8자) 제약이 화면에 안내되지 않았다.
 * 2. `RequestValidationError` 핸들러가 없어 앱의 **모든** 422 가 원인을 알 수 없는
 *    "요청이 실패했습니다 (422)." 한 문장이 됐다.
 *
 * 2번은 `backend/tests/contract/test_validation_errors.py` 가 본다.
 * 여기서는 1번과, 실패가 사용자에게 어떻게 보이는지를 본다.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KeyManagement } from "../src/pages/KeyManagement";

const NO_KEYS = {
  private_key_present: false,
  public_key_present: false,
  passphrase_protected: false,
  public_key_fingerprint: null,
  permission_warning: null,
};

function stub(routes: Record<string, { status: number; body: unknown }>) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const key = `${method} ${Object.keys(routes).find((k) => url.includes(k.split(" ")[1] ?? "")) ?? ""}`;
    const match = routes[`${method} ${url.replace(/^.*\/api/, "/api")}`] ?? routes[key];
    const chosen = match ?? { status: 200, body: NO_KEYS };
    return Promise.resolve({
      ok: chosen.status < 400,
      status: chosen.status,
      text: () => Promise.resolve(JSON.stringify(chosen.body)),
    } as Response);
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", stub({ "GET /api/keys/status": { status: 200, body: NO_KEYS } }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("KeyManagement — 제약을 제출 전에 알린다 (DR-029)", () => {
  it("암호구 규칙을 처음부터 보여준다", async () => {
    render(<KeyManagement />);

    // 「키 쌍 만들기」는 구역 제목이자 버튼 이름이다. 역할로 좁힌다.
    expect(await screen.findByText(/8자 이상 200자 이하/)).toBeTruthy();
  });

  it("8자 미만이면 사유를 말하고 제출을 막는다", async () => {
    render(<KeyManagement />);
    const input = await screen.findByLabelText("암호구 (선택)");

    fireEvent.change(input, { target: { value: "short" } });

    expect(screen.getByText(/8자 이상이어야 합니다/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "키 쌍 만들기" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("비어 있으면 막지 않는다 — 암호구는 선택이다", async () => {
    render(<KeyManagement />);
    await screen.findByLabelText("암호구 (선택)");

    expect((screen.getByRole("button", { name: "키 쌍 만들기" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("8자 이상이면 다시 열린다", async () => {
    render(<KeyManagement />);
    const input = await screen.findByLabelText("암호구 (선택)");

    fireEvent.change(input, { target: { value: "long-enough-pass" } });

    expect(screen.queryByText(/8자 이상이어야 합니다/)).toBeNull();
    expect((screen.getByRole("button", { name: "키 쌍 만들기" }) as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("KeyManagement — 실패 표시 (DR-030·SC-107)", () => {
  it("서버의 계약 메시지를 그대로 보여준다", async () => {
    const message = "이미 키가 있습니다. 새로 만들면 기존 암호문을 읽을 수 없습니다.";
    vi.stubGlobal(
      "fetch",
      stub({
        "GET /api/keys/status": { status: 200, body: NO_KEYS },
        "POST /api/keys/generate": {
          status: 409,
          body: { error: { code: "KEY_ALREADY_EXISTS", message } },
        },
      }),
    );
    render(<KeyManagement />);

    fireEvent.click(await screen.findByRole("button", { name: "키 쌍 만들기" }));

    expect(await screen.findByText(message)).toBeTruthy();
  });

  it("원시 HTTP 상태 코드를 화면에 노출하지 않는다", async () => {
    vi.stubGlobal(
      "fetch",
      stub({
        "GET /api/keys/status": { status: 200, body: NO_KEYS },
        "POST /api/keys/generate": {
          status: 400,
          body: {
            error: { code: "INVALID_PATH", message: "키를 저장할 권한이 없습니다." },
          },
        },
      }),
    );
    render(<KeyManagement />);

    fireEvent.click(await screen.findByRole("button", { name: "키 쌍 만들기" }));
    await screen.findByText("키를 저장할 권한이 없습니다.");

    expect(document.body.textContent).not.toMatch(/요청이 실패했습니다 \(\d{3}\)/);
    expect(document.body.textContent).not.toContain("400");
  });
});

describe("KeyManagement — 성공 (DR-031)", () => {
  it("만들고 나면 키 상태가 갱신된다", async () => {
    const created = { ...NO_KEYS, private_key_present: true, public_key_present: true };
    vi.stubGlobal(
      "fetch",
      stub({
        "GET /api/keys/status": { status: 200, body: NO_KEYS },
        "POST /api/keys/generate": { status: 201, body: created },
      }),
    );
    render(<KeyManagement />);

    fireEvent.click(await screen.findByRole("button", { name: "키 쌍 만들기" }));

    await waitFor(() => expect(screen.getByText(/키 쌍을 만들었습니다/)).toBeTruthy());
  });
});
