/**
 * 005 T127 — `resume` 요청이 계약대로 나간다 (FR-137 · contracts/rest-api.md §3-b).
 *
 * **이 자리가 N-04 가 드러낸 이음매다.** 계약(rest-api.md §3-b)에 `skip_failed` 가 있고
 * 백엔드(`sessions.py:resume`)가 그것을 읽고 결말을 `partial_pass` 로 만들고, 그 경로의
 * 통합 테스트(`backend/tests/integration/test_resume_with_failed_step.py`)까지 있었다.
 * 없던 것은 **그 필드를 보내는 전선** 하나였고, 양쪽 끝을 보는 테스트는 둘 다 통과했다.
 *
 * 화면 테스트는 "버튼을 누르면 콜백이 불린다" 까지만 본다. 콜백이 무엇을 보내는지는
 * 보지 않으므로, 클라이언트가 필드 이름을 틀리거나(`skipFailed` 로 보내거나) 본문을
 * 아예 빠뜨려도 그 테스트는 초록이다. 여기서 **나가는 요청 자체**를 본다.
 */

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import { sessions } from "../src/api/client";

const SID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

interface Sent {
  url: string;
  method: string;
  body: string | null;
}

let sent: Sent[] = [];

function stubFetch() {
  sent = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      sent.push({
        url: String(input),
        method: init?.method ?? "GET",
        body: typeof init?.body === "string" ? init.body : null,
      });
      // 세션 뷰의 내용은 이 테스트의 대상이 아니다 — 나가는 요청만 본다.
      return new Response("{}", {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }),
  );
}

beforeEach(stubFetch);
afterEach(() => vi.unstubAllGlobals());

describe("resume 요청 본문 (FR-137 · rest-api.md §3-b)", () => {
  it("건너뛰기를 고르면 `skip_failed: true` 를 싣는다", async () => {
    await sessions.resume(SID, true);

    expect(sent).toHaveLength(1);
    expect(sent[0]?.url).toBe(`/api/sessions/${SID}/resume`);
    expect(sent[0]?.method).toBe("POST");
    expect(sent[0]?.body).not.toBeNull();
    // **필드 이름을 문자열로 단정한다.** 계약은 snake_case 이고, 프론트의 카멜케이스가
    // 그대로 나가면 서버는 조용히 `false` 로 읽는다 — 실패 Step 이 있는 재개는 409 로
    // 거절되고, 사용자에게는 버튼이 아무 일도 하지 않는 것으로 보인다.
    expect(JSON.parse(sent[0]?.body ?? "{}")).toEqual({ skip_failed: true });
  });

  it("보통의 재개는 본문을 **보내지 않는다** — 기존 동작을 유지한다", async () => {
    await sessions.resume(SID);

    expect(sent).toHaveLength(1);
    expect(sent[0]?.method).toBe("POST");
    // 계약: "본문을 보내지 않으면 `{\"skip_failed\": false}` 와 같다." 항상 실으면
    // 계약상 같은 요청이지만 요청 로그가 달라져 회귀를 읽기 어려워진다.
    expect(sent[0]?.body).toBeNull();
  });

  it("명시적으로 건너뛰지 않겠다고 해도 본문을 보내지 않는다", async () => {
    await sessions.resume(SID, false);
    expect(sent[0]?.body).toBeNull();
  });

  it("건너뛰기가 다른 세션의 재개에 새지 않는다", async () => {
    await sessions.resume(SID, true);
    await sessions.resume(SID);

    expect(JSON.parse(sent[0]?.body ?? "{}")).toEqual({ skip_failed: true });
    expect(sent[1]?.body).toBeNull();
  });
});
