/**
 * Step 안에서 비밀 값 넣기. DR-023 ~ DR-027 · SC-106.
 *
 * **화면 이동 0회**가 요점이다. 이전에는 별도 화면으로 나갔다 와야 했고, 로그인은 가장
 * 흔한 사전 Step 이라 그 끊김이 테스트 생성 시간에 그대로 얹혔다.
 *
 * 보안 쪽에서 확인하는 것:
 * - 값이 전송 후 화면·상태에 남지 않는다
 * - Step 에 들어가는 것은 `{{변수명}}` 참조뿐이다 (FR-082·FR-084)
 * - 값을 돌려주는 요청을 하지 않는다
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InlineSecretInput, referenceName } from "../src/components/InlineSecretInput";

const KEY_PRESENT = {
  private_key_present: true,
  public_key_present: true,
  passphrase_protected: false,
  public_key_fingerprint: "SHA256:x",
  permission_warning: null,
};
const KEY_ABSENT = { ...KEY_PRESENT, private_key_present: false, public_key_present: false };

let calls: { url: string; method: string; body: string | null }[] = [];

function stub(keyStatus: unknown, names: { name: string; present: boolean }[] = []) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({
      url,
      method: init?.method ?? "GET",
      body: typeof init?.body === "string" ? init.body : null,
    });
    const body = url.includes("/api/keys/status")
      ? keyStatus
      : url.includes("/api/keys/generate")
        ? KEY_PRESENT
        : url.includes("/api/secrets")
          ? { public_key_fingerprint: "SHA256:x", fingerprint_matches_key: true, names }
          : {};
    return Promise.resolve({
      ok: true,
      status: init?.method === "PUT" ? 204 : 200,
      text: () => Promise.resolve(init?.method === "PUT" ? "" : JSON.stringify(body)),
    } as Response);
  });
}

beforeEach(() => {
  calls = [];
  vi.stubGlobal("fetch", stub(KEY_PRESENT));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("InlineSecretInput — 그 자리에서 넣는다 (DR-023·SC-106)", () => {
  it("이름과 값을 넣고 봉인하면 참조를 돌려준다", async () => {
    const onLinked = vi.fn();
    render(<InlineSecretInput onLinked={onLinked} />);
    await screen.findByLabelText("변수 이름");

    fireEvent.change(screen.getByLabelText("변수 이름"), {
      target: { value: "LOGIN_PASSWORD" },
    });
    fireEvent.change(screen.getByLabelText("값"), { target: { value: "s3cr3t" } });
    fireEvent.click(screen.getByText("봉인하고 연결"));

    await waitFor(() => expect(onLinked).toHaveBeenCalledWith("{{LOGIN_PASSWORD}}"));
  });

  it("봉인 후 값이 화면에 남지 않는다 (FR-083)", async () => {
    render(<InlineSecretInput onLinked={() => undefined} />);
    await screen.findByLabelText("변수 이름");

    fireEvent.change(screen.getByLabelText("변수 이름"), { target: { value: "PW" } });
    fireEvent.change(screen.getByLabelText("값"), { target: { value: "s3cr3t" } });
    fireEvent.click(screen.getByText("봉인하고 연결"));

    await waitFor(() =>
      expect((screen.getByLabelText("값") as HTMLInputElement).value).toBe(""),
    );
    expect(document.body.textContent).not.toContain("s3cr3t");
  });

  it("값 입력칸은 가려진다", async () => {
    render(<InlineSecretInput onLinked={() => undefined} />);
    const input = (await screen.findByLabelText("값")) as HTMLInputElement;

    expect(input.type).toBe("password");
  });

  it("값을 돌려받는 요청을 하지 않는다", async () => {
    render(<InlineSecretInput onLinked={() => undefined} />);
    await screen.findByLabelText("변수 이름");

    fireEvent.change(screen.getByLabelText("변수 이름"), { target: { value: "PW" } });
    fireEvent.change(screen.getByLabelText("값"), { target: { value: "x" } });
    fireEvent.click(screen.getByText("봉인하고 연결"));

    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    // 값이 나가는 것은 PUT 하나뿐이고, 되받는 GET 은 이름 목록이다.
    const gets = calls.filter((c) => c.method === "GET" && c.url.includes("/api/secrets"));
    expect(gets.every((c) => c.body === null)).toBe(true);
  });
});

describe("InlineSecretInput — 공개키가 없을 때 (DR-025)", () => {
  it("그 자리에서 키를 만들 수 있다", async () => {
    vi.stubGlobal("fetch", stub(KEY_ABSENT));
    render(<InlineSecretInput onLinked={() => undefined} />);

    expect(await screen.findByText(/공개키가 없어/)).toBeTruthy();
    fireEvent.click(screen.getByText("키 쌍 만들기"));

    await waitFor(() => expect(screen.getByText(/키 쌍을 만들었습니다/)).toBeTruthy());
  });

  it("키가 없으면 봉인 버튼이 잠긴다", async () => {
    vi.stubGlobal("fetch", stub(KEY_ABSENT));
    render(<InlineSecretInput onLinked={() => undefined} />);
    await screen.findByLabelText("변수 이름");

    fireEvent.change(screen.getByLabelText("변수 이름"), { target: { value: "PW" } });
    fireEvent.change(screen.getByLabelText("값"), { target: { value: "x" } });

    expect((screen.getByText("봉인하고 연결") as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("InlineSecretInput — 기존 변수 (DR-026)", () => {
  it("등록된 이름 중에서 고를 수 있다", async () => {
    vi.stubGlobal("fetch", stub(KEY_PRESENT, [{ name: "LOGIN_PASSWORD", present: true }]));
    const onLinked = vi.fn();
    render(<InlineSecretInput onLinked={onLinked} />);

    const select = await screen.findByLabelText("등록된 변수");
    fireEvent.change(select, { target: { value: "LOGIN_PASSWORD" } });

    expect(onLinked).toHaveBeenCalledWith("{{LOGIN_PASSWORD}}");
  });

  it("등록된 변수가 없으면 선택 칸을 그리지 않는다", async () => {
    render(<InlineSecretInput onLinked={() => undefined} />);
    await screen.findByLabelText("변수 이름");

    expect(screen.queryByLabelText("등록된 변수")).toBeNull();
  });
});

describe("InlineSecretInput — 이름 규칙", () => {
  it("규칙에 맞지 않으면 사유를 말하고 막는다", async () => {
    render(<InlineSecretInput onLinked={() => undefined} />);
    await screen.findByLabelText("변수 이름");

    fireEvent.change(screen.getByLabelText("변수 이름"), { target: { value: "_BAD" } });
    fireEvent.change(screen.getByLabelText("값"), { target: { value: "x" } });

    expect(screen.getByText(/대문자로 시작하고/)).toBeTruthy();
    expect((screen.getByText("봉인하고 연결") as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("referenceName", () => {
  it("참조에서 이름을 뽑는다", () => {
    expect(referenceName("{{LOGIN_PASSWORD}}")).toBe("LOGIN_PASSWORD");
  });

  it("참조가 아니면 null 이다", () => {
    expect(referenceName("plain")).toBeNull();
    expect(referenceName("{{lower}}")).toBeNull();
  });
});
