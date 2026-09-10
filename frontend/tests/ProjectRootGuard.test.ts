/**
 * 화면이 보는 프로젝트와 서버가 연 프로젝트가 갈라지지 않게 한다 (2026-09-10 사용자 보고 1번).
 *
 * 「a 프로젝트에서 새 테스트 만들기를 할 때 시작 URL = bbbb 로 했더니 b 프로젝트의 테스트
 * 리스트로 추가가 되었다」.
 *
 * 원인은 시작 URL 이 아니다. 서버는 열린 프로젝트를 **하나만** 들고 있고
 * (`AppState.repository`), `POST /api/project/create` 는 만드는 즉시 그리로 옮겨 간다.
 * 화면에서 「계속」 대신 「돌아가기」를 누르면 화면은 이전 프로젝트에 남고, 그 뒤의 저장은
 * 전부 새 프로젝트로 간다.
 *
 * 이 파일이 지키는 것은 셋이다.
 *
 * 1. 모든 요청이 **자기가 믿는 프로젝트**를 함께 말한다.
 * 2. 서버가 다르다고 하면 **그 프로젝트를 다시 열고 같은 요청을 이어서** 보낸다 —
 *    거절된 요청은 실행되지 않았으므로 다시 보내는 것이 안전하다.
 * 3. 경로는 **퍼센트 인코딩**된다. HTTP 헤더는 ISO-8859-1 이고 프로젝트 이름은 한글일
 *    수 있어, 그대로 넣으면 브라우저가 `fetch` 자체를 거절한다 (실측으로 확인했다).
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { setExpectedProjectRoot, tests } from "../src/api/client";

const HEADER = "X-ITB-Project-Root";
const KOREAN_ROOT = "/home/me/.local/share/itb/projects/결제";

interface Call {
  url: string;
  headers: Record<string, string>;
}

function stub(responses: { status: number; body: unknown }[]) {
  const calls: Call[] = [];
  let i = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({
        url: String(input),
        headers: (init?.headers ?? {}) as Record<string, string>,
      });
      const r = responses[Math.min(i++, responses.length - 1)]!;
      const text = JSON.stringify(r.body);
      return Promise.resolve({
        ok: r.status < 400,
        status: r.status,
        text: () => Promise.resolve(text),
        clone: () => ({ text: () => Promise.resolve(text) }),
      } as unknown as Response);
    }),
  );
  return calls;
}

const ok = { status: 200, body: { counts: { total: 0, pass: 0, fail: 0 }, tests: [] } };
const mismatch = {
  status: 409,
  body: {
    error: {
      code: "PROJECT_MISMATCH",
      category: "blocked",
      message: "다릅니다",
      next_action: "다시 여세요",
      detail: {},
    },
  },
};

afterEach(() => {
  setExpectedProjectRoot(null);
  vi.unstubAllGlobals();
});

describe("프로젝트 대조 헤더", () => {
  it("한글 경로도 헤더에 실린다 — 인코딩하지 않으면 요청이 나가지도 않는다", async () => {
    const calls = stub([ok]);
    setExpectedProjectRoot(KOREAN_ROOT);

    await tests.list();

    expect(calls[0]!.headers[HEADER]).toBe(encodeURIComponent(KOREAN_ROOT));
    // 헤더 값이 실제로 헤더에 실릴 수 있는 문자만 갖는가 (ISO-8859-1).
    expect(/^[\x20-\x7e]*$/.test(calls[0]!.headers[HEADER]!)).toBe(true);
  });

  it("프로젝트를 바꾸는 조작에는 걸지 않는다 — 걸면 프로젝트를 옮길 수 없다", async () => {
    const calls = stub([{ status: 200, body: { root: KOREAN_ROOT } }]);
    setExpectedProjectRoot(KOREAN_ROOT);

    await fetchProjectOpen();

    expect(calls[0]!.headers[HEADER]).toBeUndefined();
  });

  it("서버가 다른 프로젝트를 열고 있으면 되돌린 뒤 같은 요청을 잇는다", async () => {
    const calls = stub([mismatch, { status: 200, body: { root: KOREAN_ROOT } }, ok]);
    setExpectedProjectRoot(KOREAN_ROOT);

    const result = await tests.list();

    expect(calls.map((c) => c.url)).toEqual([
      "/api/tests",
      "/api/project/open",
      "/api/tests",
    ]);
    expect(result.tests).toEqual([]);
  });

  it("믿는 프로젝트가 없으면 헤더도 없다 — 첫 화면은 대조할 것이 없다", async () => {
    const calls = stub([ok]);

    await tests.list();

    expect(calls[0]!.headers[HEADER]).toBeUndefined();
  });
});

/** `project.open` 은 화면 흐름을 타므로 여기서는 경로만 확인한다. */
async function fetchProjectOpen(): Promise<void> {
  const { project } = await import("../src/api/client");
  await project.open(KOREAN_ROOT);
}
