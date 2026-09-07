/**
 * 응답을 붙잡아 두는 테스트 도구 (005 T003 · FR-129·FR-142 검증의 전제).
 *
 * 리포트가 잡은 결함 둘은 **응답 전 화면**에 있었다.
 *
 * - 실행 버튼을 누르고 0.2초 뒤 화면이 완전히 그대로였다. 그래서 사용자가 다시 눌렀고,
 *   52 ms 안의 5회 클릭이 브라우저 창 두 개를 띄웠다 (U-11 → U-06)
 * - 「일시정지」를 누르면 즉시 「일시정지됨」이 되는데 실제로는 19초를 더 돌았다 (U-04)
 *
 * 응답이 끝난 뒤의 화면만 단정하면 둘 다 통과한다. 결함이 사는 구간이 **요청과 응답
 * 사이**이기 때문이다. 그래서 그 구간을 열어 두고 멈춰 세울 수단이 필요하다.
 *
 * ```ts
 * const api = pendingFetch({ "/api/sessions": sessionView });
 * vi.stubGlobal("fetch", api.fetch);
 * await userEvent.click(runButton);
 * expect(screen.getByText(/실행을 준비하는 중/)).toBeTruthy(); // 응답 전
 * await api.settle("/api/sessions");
 * ```
 */

/** 밖에서 결말을 정할 수 있는 Promise. */
export interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason?: unknown) => void;
}

export function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export interface PendingFetch {
  /** `vi.stubGlobal("fetch", …)` 에 그대로 넣는다. */
  fetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
  /** 붙잡아 둔 요청을 풀어 준다. 그 URL 조각의 요청이 아직 없으면 던진다. */
  settle: (urlPart: string, body?: unknown, status?: number) => Promise<void>;
  /** 붙잡아 둔 요청을 실패로 끝낸다 (거절 응답 검증용). */
  fail: (urlPart: string, body: unknown, status: number) => Promise<void>;
  /** 지금까지 요청이 간 URL 전부. 연타가 몇 건을 냈는지 세는 데 쓴다. */
  urls: string[];
  /** 그 URL 조각으로 나간 요청 수. */
  countOf: (urlPart: string) => number;
  /** 그 URL 조각의 요청이 도착할 때까지 기다린다. */
  waitFor: (urlPart: string, timeoutMs?: number) => Promise<void>;
}

/**
 * URL 조각별로 응답을 정하는 `fetch` 스텁.
 *
 * `held` 에 적힌 조각은 **응답을 붙잡아 둔다** — `settle()` 을 부르기 전까지 Promise 가
 * 풀리지 않는다. 나머지는 `routes` 의 본문으로 즉시 답한다.
 */
export function pendingFetch(
  routes: Record<string, unknown> = {},
  options: { held?: string[] } = {},
): PendingFetch {
  const held = options.held ?? Object.keys(routes);
  const urls: string[] = [];
  const waiting = new Map<string, Deferred<Response>[]>();

  const matchHeld = (url: string): string | null =>
    held.find((part) => url.includes(part)) ?? null;

  const api: PendingFetch = {
    urls,
    fetch: (input) => {
      const url = String(input);
      urls.push(url);

      const part = matchHeld(url);
      if (part !== null) {
        const d = deferred<Response>();
        const queue = waiting.get(part) ?? [];
        queue.push(d);
        waiting.set(part, queue);
        return d.promise;
      }

      const route = Object.keys(routes).find((part2) => url.includes(part2));
      return Promise.resolve(jsonResponse(route ? routes[route] : {}));
    },
    countOf: (urlPart) => urls.filter((u) => u.includes(urlPart)).length,
    waitFor: async (urlPart, timeoutMs = 1000) => {
      const deadline = Date.now() + timeoutMs;
      while (!(waiting.get(urlPart)?.length ?? 0)) {
        if (Date.now() > deadline) {
          throw new Error(
            `${urlPart} 요청이 ${timeoutMs} ms 안에 오지 않았다. 나간 요청: ${urls.join(", ") || "없음"}`,
          );
        }
        await new Promise((r) => setTimeout(r, 5));
      }
    },
    settle: async (urlPart, body = routes[urlPart] ?? {}, status = 200) => {
      await api.waitFor(urlPart);
      const queue = waiting.get(urlPart) ?? [];
      for (const d of queue.splice(0)) d.resolve(jsonResponse(body, status));
      // 응답 처리(then 체인)가 돌 기회를 준다.
      await Promise.resolve();
    },
    fail: async (urlPart, body, status) => {
      await api.settle(urlPart, body, status);
    },
  };

  return api;
}
