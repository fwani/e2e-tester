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
  key_dir: "/tmp/itb-test/keys",
  sealed_projects: [],
  // 암호구가 걸려 있지 않은 키는 열 것이 없다 — 항상 열린 상태로 취급한다.
  unlocked: true,
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

const WITH_KEYS = {
  ...NO_KEYS,
  private_key_present: true,
  public_key_present: true,
  public_key_fingerprint: "SHA256:aaaa",
};

const LOCKED = { ...WITH_KEYS, passphrase_protected: true, unlocked: false };
const UNLOCKED = { ...WITH_KEYS, passphrase_protected: true, unlocked: true };

describe("KeyManagement — 잠금 해제 (FR-089e-3)", () => {
  it("잠겨 있으면 **이 화면에서** 암호구를 받아 해제한다", async () => {
    // 사용자가 겪은 것: 키 관리 화면에서 암호구를 입력해 키를 만들었는데, 실행하면
    // "환경 변수 ITB_KEY_PASSPHRASE 로 공급하라" 고 나온다. 화면이 이미 받은 것을
    // 화면이 쓰지 못한 것이다 (UX U-26). 해제 조작이 여기 있어야 한다.
    vi.stubGlobal("fetch", stub({ "GET /api/keys/status": { status: 200, body: LOCKED } }));
    render(<KeyManagement />);

    expect(await screen.findByText(/비밀키가 잠겨 있습니다/)).toBeTruthy();
    expect(screen.getByLabelText("암호구")).toBeTruthy();
    expect(screen.getByRole("button", { name: "잠금 해제" })).toBeTruthy();
  });

  it("암호구가 8자 미만이면 제출을 막는다 — 서버 제약과 같은 값이다", async () => {
    vi.stubGlobal("fetch", stub({ "GET /api/keys/status": { status: 200, body: LOCKED } }));
    render(<KeyManagement />);
    const input = await screen.findByLabelText("암호구");

    fireEvent.change(input, { target: { value: "short" } });

    const submit = screen.getByRole("button", { name: "잠금 해제" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    expect(screen.getByText(/8자 이상입니다/)).toBeTruthy();
  });

  it("해제하면 잠금 해제 경로를 부르고 열린 상태로 바뀐다", async () => {
    const fetchMock = stub({
      "GET /api/keys/status": { status: 200, body: LOCKED },
      "POST /api/keys/unlock": { status: 200, body: UNLOCKED },
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<KeyManagement />);

    fireEvent.change(await screen.findByLabelText("암호구"), {
      target: { value: "correct-horse" },
    });
    fireEvent.click(screen.getByRole("button", { name: "잠금 해제" }));

    await waitFor(() => expect(screen.getByText(/잠금을 해제했습니다/)).toBeTruthy());
    expect(screen.queryByText(/비밀키가 잠겨 있습니다/)).toBeNull();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).includes("/api/keys/unlock") &&
          (init as RequestInit | undefined)?.method === "POST",
      ),
    ).toBe(true);
  });

  it("틀린 암호구는 그 사유를 그대로 보여준다 — 복호화 실패와 구분된다", async () => {
    vi.stubGlobal(
      "fetch",
      stub({
        "GET /api/keys/status": { status: 200, body: LOCKED },
        "POST /api/keys/unlock": {
          status: 400,
          body: {
            error: {
              code: "PASSPHRASE_INVALID",
              message: "암호구가 올바르지 않습니다.",
              next_action: "암호구를 다시 확인해 입력하세요.",
            },
          },
        },
      }),
    );
    render(<KeyManagement />);

    fireEvent.change(await screen.findByLabelText("암호구"), {
      target: { value: "wrong-passphrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "잠금 해제" }));

    await waitFor(() => expect(screen.getByText(/암호구가 올바르지 않습니다/)).toBeTruthy());
    // 여전히 잠겨 있다 — 틀린 암호구가 조용히 들어앉지 않는다.
    expect(screen.getByText(/비밀키가 잠겨 있습니다/)).toBeTruthy();
  });

  it("열려 있으면 그 사실과 다시 잠그는 방법을 알린다", async () => {
    vi.stubGlobal("fetch", stub({ "GET /api/keys/status": { status: 200, body: UNLOCKED } }));
    render(<KeyManagement />);

    expect(await screen.findByText(/비밀키가 열려 있습니다/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "다시 잠그기" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "잠금 해제" })).toBeNull();
  });

  it("암호구가 없는 키에는 잠금 이야기를 꺼내지 않는다", async () => {
    vi.stubGlobal("fetch", stub({ "GET /api/keys/status": { status: 200, body: WITH_KEYS } }));
    render(<KeyManagement />);

    await screen.findByText("키 교체·삭제");
    expect(screen.queryByText(/비밀키가 잠겨 있습니다/)).toBeNull();
    expect(screen.queryByText(/비밀키가 열려 있습니다/)).toBeNull();
  });
});

describe("KeyManagement — 교체·삭제 (DR-031)", () => {
  const withKeys = (extra: Record<string, { status: number; body: unknown }> = {}) =>
    stub({ "GET /api/keys/status": { status: 200, body: WITH_KEYS }, ...extra });

  const button = (name: string) => screen.getByRole("button", { name }) as HTMLButtonElement;

  it("확인 문구 전에는 두 버튼 모두 잠겨 있다", async () => {
    vi.stubGlobal("fetch", withKeys());
    render(<KeyManagement />);
    await screen.findByText("키 교체·삭제");

    expect(button("키 교체").disabled).toBe(true);
    expect(button("키 삭제").disabled).toBe(true);
  });

  it("틀린 확인 문구는 열어 주지 않는다", async () => {
    vi.stubGlobal("fetch", withKeys());
    render(<KeyManagement />);
    const input = await screen.findByLabelText(/확인 문구/);

    fireEvent.change(input, { target: { value: "delete" } });

    expect(button("키 교체").disabled).toBe(true);
    expect(button("키 삭제").disabled).toBe(true);
  });

  it("정확한 확인 문구를 넣으면 열린다", async () => {
    vi.stubGlobal("fetch", withKeys());
    render(<KeyManagement />);
    const input = await screen.findByLabelText(/확인 문구/);

    fireEvent.change(input, { target: { value: "DELETE" } });

    expect(button("키 교체").disabled).toBe(false);
    expect(button("키 삭제").disabled).toBe(false);
  });

  it("교체하면 함께 비운 값의 개수를 알린다", async () => {
    vi.stubGlobal(
      "fetch",
      withKeys({
        "POST /api/keys/regenerate": {
          status: 201,
          body: {
            status: { ...WITH_KEYS, public_key_fingerprint: "SHA256:bbbb" },
            purged_secret_count: 2,
            project_open: true,
          },
        },
      }),
    );
    render(<KeyManagement />);
    fireEvent.change(await screen.findByLabelText(/확인 문구/), {
      target: { value: "DELETE" },
    });

    fireEvent.click(button("키 교체"));

    await waitFor(() => expect(screen.getByText(/봉인된 값 2개를 함께 비웠습니다/)).toBeTruthy());
    expect(screen.getByText("SHA256:bbbb")).toBeTruthy();
  });

  it("삭제하면 상태가 '없음' 으로 돌아가고 위험 구역이 사라진다", async () => {
    vi.stubGlobal(
      "fetch",
      withKeys({
        "DELETE /api/keys": {
          status: 200,
          body: { status: NO_KEYS, purged_secret_count: 1, project_open: true },
        },
      }),
    );
    render(<KeyManagement />);
    fireEvent.change(await screen.findByLabelText(/확인 문구/), {
      target: { value: "DELETE" },
    });

    fireEvent.click(button("키 삭제"));

    await waitFor(() => expect(screen.getByText(/키를 지웠습니다/)).toBeTruthy());
    expect(screen.queryByText("키 교체·삭제")).toBeNull();
    expect(screen.getByRole("button", { name: "키 쌍 만들기" })).toBeTruthy();
  });

  it("교체 실패는 계약 메시지를 그대로 보여주고 키 상태를 바꾸지 않는다", async () => {
    const message = "새 키를 저장할 수 없습니다: Permission denied.";
    vi.stubGlobal(
      "fetch",
      withKeys({
        "POST /api/keys/regenerate": {
          status: 400,
          body: { error: { code: "INVALID_PATH", message } },
        },
      }),
    );
    render(<KeyManagement />);
    fireEvent.change(await screen.findByLabelText(/확인 문구/), {
      target: { value: "DELETE" },
    });

    fireEvent.click(button("키 교체"));

    expect(await screen.findByText(message)).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/요청이 실패했습니다 \(\d{3}\)/);
  });

  it("짧은 새 암호구로는 교체를 막는다 — 서버 왕복 없이 사유를 말한다", async () => {
    vi.stubGlobal("fetch", withKeys());
    render(<KeyManagement />);
    fireEvent.change(await screen.findByLabelText(/확인 문구/), {
      target: { value: "DELETE" },
    });
    fireEvent.change(screen.getByLabelText(/새 암호구/), { target: { value: "short" } });

    expect(screen.getByText(/8자 이상이어야 합니다/)).toBeTruthy();
    expect(button("키 교체").disabled).toBe(true);
    // 삭제는 새 암호구와 무관하다.
    expect(button("키 삭제").disabled).toBe(false);
  });
});
