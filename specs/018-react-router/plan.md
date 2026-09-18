# 018 React Router 도입 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 화면 전환을 `App.tsx` 의 `screen` 상태에서 React Router(Data 모드)로 옮겨, 경로형 주소 · 모든 화면의 새로고침/딥링크 · 링크 기반 이동을 얻는다.

**Architecture:** 라우트 표(`app/router.tsx`)가 URL 을 기존 페이지 prop 으로 옮기는 얇은 어댑터(`app/routes/*`)를 그린다. 화면을 넘어 사는 상태(열린 프로젝트 · 오류 · 가져오기)는 라우터마다 하나인 바깥 저장소(`app/appStore.ts`)에 두어 loader 와 화면이 함께 쓴다. 루트 미들웨어가 프로젝트 조회를 loader 보다 먼저 끝낸다.

**Tech Stack:** React 19.2 · TypeScript 5.7 · Vite 6 · `react-router@^8.4.0` · `@base-ui/react` 1.8 · Vitest 2 + jsdom 25 · Playwright(Python, 실브라우저 검증)

**Spec:** [`specs/018-react-router/design.md`](./design.md) — 구현자는 이 계획과 함께 읽는다.

## Global Constraints

- 의존성: `react-router@^8.4.0` 하나만 더한다. `react-router-dom` 은 쓰지 않는다 (v8 에서 지워졌다).
- 가져오기: `RouterProvider` 는 `react-router/dom` 에서, 나머지는 전부 `react-router` 에서.
- 화면(`src/pages/*`, `src/components/*`)은 `react-router` 를 가져오지 않는다 — 검사 19개 파일이 `TestList` 를 라우터 없이 그린다. 화면은 지금처럼 콜백 prop 을 받고, 주소 문자열은 `src/lib/paths.ts`(순수 함수)에서 얻는다.
- 화면 파일에 원시 `<button>`·`<input>`·`<select>`·`<textarea>` 를 쓰지 않는다 (`tests/RawElements.test.ts`). 링크도 `ui/` 부품(`ButtonLink`·`MenuLinkItem`)을 지난다.
- `ui/` 부품은 `className` 을 받지 않는다 — `layout` 은 배치만. 새 모양 값을 만들지 않고 `buttonVariants`·`plainButtonVariants`·`menuItemVariants` 를 재사용한다.
- 주석은 한국어로, 이 저장소 관용대로 **왜**를 적고 근거(`018 §n`, 옛 FR 번호)를 붙인다. 옛 `App.tsx` 에서 옮기는 판단 주석은 뜻을 잃지 않게 함께 옮긴다.
- 커밋 메시지: `feat(018): …` / `test(018): …` / `docs(018): …` 형식, 끝에 빈 줄 + `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- 프론트 검증 명령: `cd frontend && npx tsc --noEmit && npx vitest run`
- **알려진 실패 2건**: `src/` 가 바뀌는 순간(Task 1 부터) `tests/BeforeAfterParity.test.ts` 와 `tests/ScreenSweep.test.ts` 의 「보고서가 낡지 않았다」가 실패한다. 두 보고서는 Task 7 에서 다시 뜬다. **그 둘 외의 실패는 0 이어야 한다.**
- **기존 간헐 실패 1건**: `tests/EditEntryPoints.test.tsx` 「Step 02 고치기가 그 Step 이 펼쳐진 편집 화면으로 간다」는 전체 실행 부하에서만 가끔 실패한다(단독 3/3 통과). Task 5 에서 그 줄을 `findByText` 로 고친다. 그 전에 이것만 실패하면 단독으로 다시 돌려 확인한다.

## 파일 지도

| 파일 | 상태 | 책임 |
|------|------|------|
| `frontend/src/lib/paths.ts` | 새로 | 경로 모양(`PATTERNS`) · 주소 빌더(`paths`) · 옛 `?screen=` 변환(`legacyPath`) |
| `frontend/src/ui/Button.tsx` | 고침 | `ButtonLink` · `isPlainClick` 추가, 모양 고르기를 `shapeOf` 로 분리 |
| `frontend/src/ui/DropdownMenu.tsx` | 고침 | `MenuLinkItem` 추가 |
| `frontend/src/app/appStore.ts` | 새로 | 바깥 저장소 · `AppStoreContext` · `useAppStore` · `useAppState` |
| `frontend/src/app/arrival.ts` | 새로 | 실행 화면의 도착 정보(기록 · 일회성 명령) 읽기/지우기 |
| `frontend/src/app/actions.tsx` | 새로 | 세션을 여는 유일한 경로 · `pendingRun` · 만들기 잠금 |
| `frontend/src/app/AppShell.tsx` | 새로 | 레이아웃 라우트 — 알림 층 · 오류 토스트 · `<Outlet />` |
| `frontend/src/app/RouteStatus.tsx` | 새로 | 첫 로딩 화면 · 루트 오류 화면 |
| `frontend/src/app/routes/*.tsx` | 새로 | 라우트별 어댑터 9개 |
| `frontend/src/app/router.tsx` | 새로 | `createRoutes(store)` — 라우트 표 · loader · 미들웨어 |
| `frontend/src/app/AppRoot.tsx` | 새로 | `AppRoot`(저장소 + `RouterProvider`) · `createBrowserApp()` |
| `frontend/src/main.tsx` | 고침 | `createBrowserApp()` 로 시작 |
| `frontend/src/App.tsx` | **삭제** | Task 5 |
| `frontend/src/hooks/useScreenUrl.ts` | **삭제** | Task 5 |
| `frontend/tests/setup/dom.ts` | 고침 | jsdom `AbortSignal` ↔ Node `Request` 잇기 |
| `frontend/tests/helpers/fakeServer.ts` | 새로 | `EditEntryPoints` 의 가짜 서버를 옮겨 옵션을 더한 것 |
| `frontend/tests/helpers/app.tsx` | 새로 | `renderApp(url, { state?, prepare? })` — 메모리 라우터로 앱 전체를 그린다 |
| `frontend/tests/paths.test.ts` · `ButtonLink.test.tsx` · `AppStore.test.ts` · `Routing.test.tsx` | 새로 | 이 계획의 검사 |
| `frontend/tests/ScreenUrl.test.ts` | **삭제** | Task 5 — `paths.test.ts` · `Routing.test.tsx` 가 물려받는다 |
| `frontend/src/pages/TestList.tsx` · `SecretValues.tsx` · `KeyManagement.tsx` | 고침 | Task 6 — 순수 이동을 링크로 |
| `backend/tests/abnormal/ui_context.py` · `drivers/ui_drivers.py` · `test_ui_surface_restore.py` | 고침 | Task 6·7 |
| `scripts/screen_sweep.py` · `scripts/design_compare_ba.py` | 고침 | Task 6·7 |
| `README.md` · `specs/005-ux-walkthrough-repair/research.md` · `specs/018-react-router/design.md` | 고침 | 문서 |

---

### Task 1: 라우터 의존성 · 검사 환경 · 주소 모양

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json` (npm 이 쓴다)
- Modify: `frontend/tests/setup/dom.ts` (파일 끝에 덧붙인다)
- Create: `frontend/src/lib/paths.ts`
- Test: `frontend/tests/paths.test.ts`
- Modify: `specs/018-react-router/design.md` (§2 파일 배치)

**Interfaces:**
- Produces:
  - `PATTERNS: { list; projects; compose; edit; result; session; importPreview; keys; secrets }` — 라우트 경로 문자열 (`"/tests/:testId/edit"` 등)
  - `paths.list(): string` · `paths.projects()` · `paths.compose(draftId?: string | null)` · `paths.edit(testId: string, stepId?: string | null)` · `paths.result(testId: string, stepId?: string | null)` · `paths.session(sessionId: string, back?: { stepId: string | null } | null)` · `paths.importPreview(planId: string)` · `paths.keys()` · `paths.secrets()`
  - `legacyPath(search: string): string | null` — `?screen=` 이 없으면 `null`

- [ ] **Step 0: 실브라우저 기준선을 적어 둔다**

코드를 바꾸기 **전에** 실브라우저 검사를 한 번 돌려, 이미 실패하는 것을 적어 둔다. Task 6·7 에서 「새로 깨진 것」과 「원래 깨져 있던 것」을 가르는 근거다.

```bash
cd backend && uv sync && uv run playwright install chromium \
  && uv run pytest -m "browser and not timing" -q -n 2 2>&1 | tail -40 | tee ../.018-browser-baseline.txt
```

Expected: 끝줄에 `N passed` (실패가 있으면 그 이름이 파일에 남는다). `.018-browser-baseline.txt` 는 커밋하지 않는다 — Task 7 마지막에 지운다.

- [ ] **Step 1: 의존성을 더한다**

```bash
cd frontend && npm install react-router@^8.4.0
```

Expected: `package.json` 의 `dependencies` 에 `"react-router": "^8.4.0"` 이 생긴다. `react-router-dom` 은 생기지 않는다.

- [ ] **Step 2: jsdom 환경의 신호 불일치를 잇는다**

사전 조사에서 실측한 것: vitest 의 jsdom 환경은 `AbortController` 를 jsdom 것으로 바꾸고 `Request` 는 Node(undici) 것을 남긴다. Data 라우터가 `new Request(url, { signal })` 를 만드는 순간 `TypeError: RequestInit: Expected signal ("AbortSignal {}") to be an instance of AbortSignal.` 로 죽는다. `frontend/tests/setup/dom.ts` 의 **파일 끝**(마지막 `}` 뒤)에 덧붙인다:

```ts
/*
  ## Data 라우터의 요청 신호 — jsdom 과 Node 의 `AbortSignal` 이 다르다 (018 · 사전 실측)

  vitest 의 jsdom 환경은 `AbortController` 를 jsdom 것으로 바꾸지만 `Request` 는 Node(undici) 것을 남긴다.
  React Router 의 Data 라우터는 이동마다 `new Request(url, { signal })` 를 만들고, undici 는 jsdom 의 신호를
  받지 않는다 — `RequestInit: Expected signal … to be an instance of AbortSignal` 로 라우터가 첫 이동에서 죽는다.

  **흉내가 아니라 잇기다.** jsdom 신호가 끊기면 Node 신호도 같은 이유로 끊긴다. 라우터는 요청의 신호로
  「중간에 버려진 이동」을 판정하므로 신호를 떼어 버리면 안 된다. Node 의 컨트롤러는 전역이 덮였으므로
  `node:util` 의 `transferableAbortController()`(Node 컨트롤러를 돌려준다)로 얻는다.
*/
import { transferableAbortController } from "node:util";

if (typeof globalThis.Request !== "undefined") {
  const NodeRequest = globalThis.Request;
  class BridgedRequest extends NodeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      const signal = init?.signal;
      if (signal) {
        const bridge = transferableAbortController();
        if (signal.aborted) bridge.abort(signal.reason);
        else signal.addEventListener("abort", () => bridge.abort(signal.reason), { once: true });
        init = { ...init, signal: bridge.signal };
      }
      super(input, init);
    }
  }
  globalThis.Request = BridgedRequest as typeof Request;
}
```

`import` 문이 파일 끝에 오는 것은 ES 모듈에서 허용된다(호이스팅). 파일 머리의 표(「jsdom 에 없는 API」)에 한 줄을 더한다:

```
 * | `Request` 의 `signal` | React Router Data 라우터의 모든 이동 | 첫 이동에서 `RequestInit: Expected signal` 예외 — 파일 끝 절 |
```

- [ ] **Step 3: 실패하는 검사를 쓴다**

`frontend/tests/paths.test.ts`:

```ts
/**
 * 018 — 주소 모양과 옛 주소 변환 (design §2 · §6).
 *
 * `ScreenUrl.test.ts`(005·006·007) 가 지키던 것을 물려받는다: 기본 화면은 주소에 아무것도 남기지 않고,
 * 지목한 Step 은 주소에 실리며, 옛 주소(`?screen=` · 1회차의 `create`·`ai-compose`)로 들어와도 같은
 * 화면에 닿는다. 왕복은 라우트 표가 실제로 쓰는 `matchPath` 로 확인한다.
 */
import { matchPath } from "react-router";
import { describe, expect, it } from "vitest";

import { PATTERNS, legacyPath, paths } from "../src/lib/paths";

describe("주소 빌더 (018 §2)", () => {
  it("목록은 `/` 다 — 기본 화면에 파라미터를 남기지 않는다 (005 FR-166)", () => {
    expect(paths.list()).toBe("/");
  });

  it("결과·편집은 테스트를 경로에, 지목한 Step 을 질의에 싣는다 (006 FR-181 · 007 FR-239)", () => {
    expect(paths.result("TC-001")).toBe("/tests/TC-001/result");
    expect(paths.result("TC-001", "st-2")).toBe("/tests/TC-001/result?step=st-2");
    expect(paths.edit("TC-001", null)).toBe("/tests/TC-001/edit");
    expect(paths.edit("TC-001", "st-2")).toBe("/tests/TC-001/edit?step=st-2");
  });

  it("만들기는 초안이 있을 때만 질의를 싣는다 (014 US3)", () => {
    expect(paths.compose()).toBe("/tests/new");
    expect(paths.compose("D-0001")).toBe("/tests/new?draft=D-0001");
  });

  it("실행 화면은 편집에서 왔을 때만 돌아갈 곳을 싣는다 (006 FR-204)", () => {
    expect(paths.session("s-1")).toBe("/sessions/s-1");
    expect(paths.session("s-1", { stepId: "st-2" })).toBe("/sessions/s-1?from=edit&step=st-2");
    expect(paths.session("s-1", { stepId: null })).toBe("/sessions/s-1?from=edit");
  });

  it("나머지 화면", () => {
    expect(paths.projects()).toBe("/projects");
    expect(paths.importPreview("p-1")).toBe("/import/p-1");
    expect(paths.keys()).toBe("/keys");
    expect(paths.secrets()).toBe("/secrets");
  });

  it("식별자는 경로 조각으로 인코딩된다 — 슬래시가 경로를 쪼개지 않는다", () => {
    expect(paths.result("A/B")).toBe("/tests/A%2FB/result");
  });

  it("왕복이 값을 잃지 않는다 — 라우트 표의 모양으로 되읽는다 (007 FR-240)", () => {
    const cases: [string, string, Record<string, string>][] = [
      [PATTERNS.result, paths.result("TC-001", "st-2"), { testId: "TC-001" }],
      [PATTERNS.edit, paths.edit("TC-002"), { testId: "TC-002" }],
      [PATTERNS.session, paths.session("s-9", { stepId: "st-1" }), { sessionId: "s-9" }],
      [PATTERNS.importPreview, paths.importPreview("p-1"), { planId: "p-1" }],
    ];
    for (const [pattern, url, params] of cases) {
      const pathname = url.split("?")[0]!;
      expect(matchPath(pattern, pathname)?.params, url).toEqual(params);
    }
  });
});

describe("옛 주소 → 새 주소 (018 §6 · 열어 둔 탭과 북마크를 끊지 않는다)", () => {
  it.each([
    ["?screen=result&test=TC-001", "/tests/TC-001/result"],
    ["?screen=result&test=TC-001&step=st-2", "/tests/TC-001/result?step=st-2"],
    ["?screen=definition&test=TC-001&step=st-2", "/tests/TC-001/edit?step=st-2"],
    ["?screen=keys", "/keys"],
    ["?screen=secrets", "/secrets"],
    ["?screen=compose", "/tests/new"],
    ["?screen=create", "/tests/new"],
    ["?screen=ai-compose", "/tests/new"],
    ["?screen=runner&session=s-1", "/sessions/s-1"],
    ["?screen=list", "/"],
    ["?screen=result", "/"],
    ["?screen=runner", "/"],
    ["?screen=없는-화면", "/"],
  ])("%s → %s", (search, expected) => {
    expect(legacyPath(search)).toBe(expected);
  });

  it("`screen` 이 없으면 옮기지 않는다", () => {
    expect(legacyPath("")).toBeNull();
    expect(legacyPath("?step=st-2")).toBeNull();
  });
});
```

- [ ] **Step 4: 실패를 확인한다**

Run: `cd frontend && npx vitest run tests/paths.test.ts`
Expected: FAIL — `Failed to resolve import "../src/lib/paths"`

- [ ] **Step 5: 구현한다**

`frontend/src/lib/paths.ts`:

```ts
/**
 * 화면 주소 — 경로 모양 · 주소 빌더 · 옛 주소 변환 (018 design §2 · §6).
 *
 * **`react-router` 를 가져오지 않는다.** 라우트 표(`app/router.tsx`)와 화면(`pages/*`)이 같은 모양을
 * 써야 하는데, 화면은 라우터 없이도 그려져야 한다 — 검사 19개 파일이 `TestList` 를 단독으로 그린다.
 * 그래서 주소는 순수 함수로 여기서 만들고, 화면은 이것으로 링크의 `href` 를 얻는다.
 *
 * 005 R8 은 `?screen=result&test=TC-001` 질의 문자열을 썼다. 018 이 경로형으로 바꾸며 **옛 주소를
 * 끊지 않는다** — `useScreenUrl.ts` 의 규율(열어 둔 탭과 북마크를 끊지 않는다)을 `legacyPath` 가 잇는다.
 */

/** 라우트 표가 쓰는 경로 모양. 바꾸면 `legacyPath` 와 `paths` 도 함께 본다. */
export const PATTERNS = {
  list: "/",
  projects: "/projects",
  compose: "/tests/new",
  edit: "/tests/:testId/edit",
  result: "/tests/:testId/result",
  session: "/sessions/:sessionId",
  importPreview: "/import/:planId",
  keys: "/keys",
  secrets: "/secrets",
} as const;

const segment = (value: string) => encodeURIComponent(value);

/** 값이 있는 것만 질의에 싣는다 — 빈 파라미터로 주소를 더럽히지 않는다 (005 FR-166). */
function withQuery(path: string, query: Record<string, string | null | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value) params.set(key, value);
  }
  const search = params.toString();
  return search ? `${path}?${search}` : path;
}

export const paths = {
  list: () => PATTERNS.list,
  projects: () => PATTERNS.projects,
  /** 초안에서 출발하면 초안 식별자를 싣는다 — loader 가 그것으로 지시문을 채운다 (014 FR-031). */
  compose: (draftId?: string | null) => withQuery(PATTERNS.compose, { draft: draftId }),
  /** 지목한 Step 은 질의에 — 새로 고쳐도 고치러 온 Step 을 잃지 않는다 (006 FR-181). */
  edit: (testId: string, stepId?: string | null) =>
    withQuery(`/tests/${segment(testId)}/edit`, { step: stepId }),
  /** 결과 국면도 지목을 싣는다 (007 FR-239). */
  result: (testId: string, stepId?: string | null) =>
    withQuery(`/tests/${segment(testId)}/result`, { step: stepId }),
  /**
   * 실행 화면. `back` 이 있으면 끝났을 때 편집으로 돌아간다 (006 FR-204).
   *
   * 돌아갈 곳을 **주소에** 싣는 이유: 새로 고쳐도 끝나면 편집으로 가야 한다. 테스트는 세션 응답의
   * `test_id` 가 알려 주므로 싣지 않는다 (018 §3.3).
   */
  session: (sessionId: string, back?: { stepId: string | null } | null) =>
    withQuery(`/sessions/${segment(sessionId)}`, back ? { from: "edit", step: back.stepId } : {}),
  importPreview: (planId: string) => `/import/${segment(planId)}`,
  keys: () => PATTERNS.keys,
  secrets: () => PATTERNS.secrets,
};

/** 1회차 이름 → 2회차 이름 (007 research R12). 만들기가 화면 둘에서 국면 하나로 합쳐졌다. */
const RENAMED: Record<string, string> = {
  create: "compose",
  "ai-compose": "compose",
};

/**
 * 옛 `?screen=` 주소가 가리키던 새 주소. `screen` 이 없으면 `null` — 옮기지 않는다.
 *
 * 필수 값이 빠졌거나 모르는 이름이면 목록이다. 005 의 `searchToLocation` 이 「알 수 없는 값은 목록으로
 * 떨어뜨린다」고 한 것과 같다 — 앱을 이탈시키지 않는다.
 */
export function legacyPath(search: string): string | null {
  const params = new URLSearchParams(search);
  const raw = params.get("screen");
  if (raw === null) return null;
  const name = RENAMED[raw] ?? raw;
  const test = params.get("test");
  const step = params.get("step");
  const session = params.get("session");
  switch (name) {
    case "result":
      return test ? paths.result(test, step) : paths.list();
    case "definition":
      return test ? paths.edit(test, step) : paths.list();
    case "keys":
      return paths.keys();
    case "secrets":
      return paths.secrets();
    case "compose":
      return paths.compose();
    case "runner":
      return session ? paths.session(session) : paths.list();
    default:
      return paths.list();
  }
}
```

- [ ] **Step 6: 통과를 확인한다**

Run: `cd frontend && npx vitest run tests/paths.test.ts`
Expected: PASS (21 tests)

- [ ] **Step 7: 설계 문서의 파일 배치를 고친다**

`specs/018-react-router/design.md` §2 「새로 만든다」 표에서 `paths.ts` 줄을 지우고, 표 바로 아래에 다음 문단을 더한다:

```markdown
**`paths.ts` 는 `src/lib/` 에 둔다** (구현 중 결정). 화면(`pages/*`)이 링크의 `href` 를 이것으로 얻는데,
화면이 `app/` 을 가져오면 `app → pages → app` 으로 층이 거꾸로 선다. `react-router` 도 가져오지 않는
순수 함수라 `lib/` 이 맞는 자리다.
```

- [ ] **Step 8: 전체 검사**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 타입 오류 0. 실패는 Global Constraints 의 **알려진 2건**(두 보고서 digest)뿐.

- [ ] **Step 9: 커밋**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tests/setup/dom.ts \
  frontend/src/lib/paths.ts frontend/tests/paths.test.ts specs/018-react-router/design.md
git commit -m "$(cat <<'EOF'
feat(018): 라우터 의존성과 주소 모양을 들인다 (T001)

react-router 8.4 를 더하고, 경로 빌더와 옛 ?screen= 변환을 순수 함수로 둔다.
jsdom 의 AbortSignal 과 Node Request 가 달라 Data 라우터가 죽는 것을 검사 환경에서 잇는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---
### Task 2: 링크 부품 — `ButtonLink` · `MenuLinkItem`

**Files:**
- Modify: `frontend/src/ui/Button.tsx`
- Modify: `frontend/src/ui/DropdownMenu.tsx`
- Test: `frontend/tests/ButtonLink.test.tsx`
- Modify: `specs/018-react-router/design.md` (§4)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `isPlainClick(event: Pick<MouseEvent, "button" | "metaKey" | "ctrlKey" | "shiftKey" | "altKey">): boolean` (`src/ui/Button.tsx`)
  - `ButtonLink(props: { href: string; onNavigate?: () => void; variant?: ButtonVariant; size?: ButtonSize; layout?: string; children?; …<a> props except className })` (`src/ui/Button.tsx`)
  - `MenuLinkItem(props: { href: string; onNavigate: () => void; layout?: string; children?; …Base UI LinkItem props except className })` (`src/ui/DropdownMenu.tsx`)

**왜 react-router 의 `<Link>` 가 아닌가:** `<Link>` 는 라우터 문맥 밖에서 예외를 던진다. 화면은 라우터 없이 그려져야 하므로(Global Constraints), 부품은 **진짜 `<a href>`** 를 그리고 보통 클릭만 가로채 콜백(`onNavigate`)을 부른다. 콜백은 라우트 어댑터가 `navigate()` 로 채운다. Cmd/Ctrl/Shift/Alt 클릭과 가운데 클릭(`auxclick`)은 브라우저 기본 동작(새 탭·새 창)이 된다.

- [ ] **Step 1: 실패하는 검사를 쓴다**

`frontend/tests/ButtonLink.test.tsx`:

```tsx
/**
 * 018 §4 — 링크 부품. 모습은 버튼 그대로, 요소는 `<a href>`.
 *
 * 순수 이동을 버튼으로 두면 Cmd·가운데 클릭으로 새 탭을 열 수 없고 링크 주소를 복사할 수도 없다.
 * 그렇다고 문서를 새로 열면 앱 상태가 날아간다. 그래서 **보통 클릭만** 앱 안에서 옮기고 나머지는
 * 브라우저에 맡긴다. 이 파일이 그 경계를 고정한다.
 *
 * 브라우저에 맡기는 경우는 `href="#…"` 를 쓴다 — jsdom 은 해시 이동만 구현하고, 그 밖의 주소로
 * 기본 동작이 일어나면 「Not implemented: navigation」을 콘솔에 남긴다.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button, ButtonLink } from "../src/ui/Button";
import { Menu, MenuContent, MenuLinkItem, MenuTrigger } from "../src/ui/DropdownMenu";

const click = (el: Element, init: MouseEventInit = {}) => {
  const event = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0, ...init });
  el.dispatchEvent(event);
  return event;
};

describe("ButtonLink — 모양은 버튼, 요소는 링크 (018 §4)", () => {
  it("href 를 가진 a 요소이고 변종 표의 모양을 그대로 쓴다", () => {
    render(
      <ButtonLink href="/keys" onNavigate={() => undefined} variant="nav">
        키 관리
      </ButtonLink>,
    );
    const link = screen.getByRole("link", { name: "키 관리" });
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe("/keys");
    expect(link.getAttribute("data-variant")).toBe("nav");
    // 정본 `.navlink` 의 높이 — `plainButtonVariants` 에서 온 것이다.
    expect(link.className).toContain("h-[28px]");
  });

  it("상자 변종은 border-box 다 — a 의 기본값(content-box)이면 테두리만큼 높아진다", () => {
    render(
      <ButtonLink href="/tests/new" onNavigate={() => undefined} variant="primary">
        테스트 만들기
      </ButtonLink>,
    );
    const link = screen.getByRole("link", { name: "테스트 만들기" });
    expect(link.className).toContain("box-border");
    expect(link.className).toContain("h-control");
  });

  it("같은 변종의 버튼과 모양 클래스가 같다 — 모양의 정의는 하나다 (017 FR-003)", () => {
    render(
      <>
        <Button variant="nav">버튼</Button>
        <ButtonLink href="#x" variant="nav">
          링크
        </ButtonLink>
      </>,
    );
    const button = screen.getByRole("button", { name: "버튼" }).className;
    const link = screen.getByRole("link", { name: "링크" }).className;
    expect(link).toBe(`${button} box-border`);
  });

  it("보통 클릭은 앱 안에서 옮긴다 — 문서를 새로 열지 않는다", () => {
    const onNavigate = vi.fn();
    render(
      <ButtonLink href="/keys" onNavigate={onNavigate}>
        키 관리
      </ButtonLink>,
    );
    const event = click(screen.getByRole("link"));
    expect(onNavigate).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });

  it.each(["metaKey", "ctrlKey", "shiftKey", "altKey"] as const)(
    "%s 를 누른 클릭은 브라우저에 맡긴다 — 새 탭·새 창",
    (key) => {
      const onNavigate = vi.fn();
      render(
        <ButtonLink href="#keys" onNavigate={onNavigate}>
          키 관리
        </ButtonLink>,
      );
      const event = click(screen.getByRole("link"), { [key]: true });
      expect(onNavigate).not.toHaveBeenCalled();
      expect(event.defaultPrevented).toBe(false);
    },
  );

  it("주 단추가 아닌 클릭은 브라우저에 맡긴다", () => {
    const onNavigate = vi.fn();
    render(
      <ButtonLink href="#keys" onNavigate={onNavigate}>
        키 관리
      </ButtonLink>,
    );
    click(screen.getByRole("link"), { button: 1 });
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("호출부의 onClick 이 막으면 옮기지 않는다", () => {
    const onNavigate = vi.fn();
    render(
      <ButtonLink href="#keys" onNavigate={onNavigate} onClick={(e) => e.preventDefault()}>
        키 관리
      </ButtonLink>,
    );
    click(screen.getByRole("link"));
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("onNavigate 가 없으면 평범한 링크다", () => {
    render(<ButtonLink href="#list">목록으로</ButtonLink>);
    const event = click(screen.getByRole("link"));
    expect(event.defaultPrevented).toBe(false);
  });
});

describe("MenuLinkItem — 메뉴 항목인 링크 (018 §4)", () => {
  it("메뉴 항목 역할의 a 요소이고, 누르면 옮긴다", async () => {
    const onNavigate = vi.fn();
    render(
      <Menu>
        <MenuTrigger>
          <Button size="icon" aria-label="추가 동작">
            ⋯
          </Button>
        </MenuTrigger>
        <MenuContent>
          <MenuLinkItem href="/tests/TC-001/edit" onNavigate={onNavigate}>
            편집
          </MenuLinkItem>
        </MenuContent>
      </Menu>,
    );
    await userEvent.setup().click(screen.getByLabelText("추가 동작"));
    const item = await screen.findByRole("menuitem", { name: "편집" });
    expect(item.tagName).toBe("A");
    expect(item.getAttribute("href")).toBe("/tests/TC-001/edit");
    const event = click(item);
    expect(onNavigate).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run tests/ButtonLink.test.tsx`
Expected: FAIL — `ButtonLink` / `MenuLinkItem` 이 export 되지 않았다 (`is not a function` 또는 `does not provide an export`).

- [ ] **Step 3: `Button.tsx` 를 고친다**

(a) 가져오기 줄을 바꾼다:

```ts
import type { ComponentPropsWithRef, MouseEvent, ReactNode } from "react";
```

(b) `const PLAIN …` 줄 바로 아래에 모양 고르기 함수를 둔다:

```ts
/**
 * 변종 이름으로 표를 고른다. `Button` 과 `ButtonLink` 가 **같은 모양**을 얻는 유일한 통로다 (018 §4).
 *
 * 클래스 이름을 조립하지 않는다 — 표에서 완성된 문자열을 꺼낼 뿐이다.
 * Tailwind 는 소스를 텍스트로 스캔하므로 `bg-${x}` 같은 것을 찾지 못한다 (가드 G-B).
 */
function shapeOf(variant: ButtonVariant, size: ButtonSize): string {
  return PLAIN.has(variant)
    ? plainButtonVariants({ variant: variant as PlainVariant })
    : buttonVariants({ variant: variant as BoxVariant, size });
}
```

(c) `Button` 본문의 첫 부분을 바꾼다. 지금:

```ts
  // 클래스 이름을 조립하지 않는다 — 표에서 완성된 문자열을 꺼내 이어 붙일 뿐이다.
  // Tailwind 는 소스를 텍스트로 스캔하므로 `bg-${x}` 같은 것을 찾지 못한다 (가드 G-B).
  const shape = PLAIN.has(variant)
    ? plainButtonVariants({ variant: variant as PlainVariant })
    : buttonVariants({ variant: variant as BoxVariant, size });
  const cls = cn(shape, layout);
```

바꾼 뒤:

```ts
  const cls = cn(shapeOf(variant, size), layout);
```

(d) 파일 끝에 덧붙인다:

```tsx
/**
 * 새 탭·새 창·다른 단추가 아닌 **보통 클릭**인가 (018 §4).
 *
 * 링크 부품은 이때만 앱 안에서 옮긴다. 나머지는 브라우저가 한다 — 사용자가 Cmd 를 누르고 눌렀다면
 * 원하는 것은 새 탭이다. 가운데 클릭은 `click` 이 아니라 `auxclick` 으로 오므로 여기까지 오지 않는다.
 */
export function isPlainClick(
  event: Pick<MouseEvent, "button" | "metaKey" | "ctrlKey" | "shiftKey" | "altKey">,
): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

export interface ButtonLinkProps extends Omit<ComponentPropsWithRef<"a">, "className" | "href"> {
  readonly href: string;
  /**
   * 보통 클릭일 때 부른다 — 라우트 어댑터가 `navigate()` 로 채운다.
   *
   * **없으면 평범한 링크다.** 루트 오류 화면처럼 앱 상태를 믿을 수 없는 자리는 문서를 새로 여는 것이 맞다.
   */
  readonly onNavigate?: () => void;
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  /** `Button` 과 같다 — 배치만. */
  readonly layout?: string;
  readonly children?: ReactNode;
}

/**
 * 버튼 모양의 링크 (018 §4).
 *
 * **순수 이동만** 이것으로 그린다 — 누르면 다른 화면으로 가고 그 밖의 일은 하지 않는 조작. 실행·녹화처럼
 * 부수효과가 있거나, 이동 전에 확인을 거치는 조작은 `Button` 이다. 링크는 비활성이 없으므로
 * 비활성 사유를 보여야 하는 조작에도 쓰지 않는다 (FR-014).
 *
 * `react-router` 의 `<Link>` 를 쓰지 않는다 — 라우터 밖에서 예외를 던지고, 화면은 라우터 없이도 그려진다.
 *
 * `box-border`: 전역 `button{}` 규칙과 브라우저 기본값이 버튼에는 `border-box` 를 주지만 `<a>` 는
 * `content-box` 다. 빠뜨리면 32px 상자가 테두리만큼 34px 가 된다. 모양 값이 아니라 상자 계산 방식이다.
 */
export function ButtonLink({
  href,
  onNavigate,
  onClick,
  variant = "default",
  size = "md",
  layout,
  children,
  ...rest
}: ButtonLinkProps) {
  return (
    <a
      href={href}
      className={cn(shapeOf(variant, size), "box-border", layout)}
      data-slot="button-link"
      data-variant={variant}
      data-size={size}
      onClick={(event) => {
        onClick?.(event);
        if (onNavigate === undefined || event.defaultPrevented || !isPlainClick(event)) return;
        event.preventDefault();
        onNavigate();
      }}
      {...rest}
    >
      {children}
    </a>
  );
}
```

- [ ] **Step 4: `DropdownMenu.tsx` 를 고친다**

(a) `import { cn } from "./cn";` 아래에 더한다:

```ts
import { isPlainClick } from "./Button";
```

(b) `MenuItem` 함수 바로 아래에 더한다:

```tsx
/**
 * 링크인 메뉴 항목 (018 §4) — Base UI `Menu.LinkItem` 이 `<a role="menuitem">` 을 그린다.
 *
 * 모습은 `MenuItem` 의 기본 변종 그대로다. 행 메뉴의 「편집」처럼 **다른 화면으로 가기만 하는** 항목에
 * 쓴다 — 가운데 클릭으로 새 탭에서 열 수 있다. 보통 클릭은 `ButtonLink` 와 같은 규칙으로 가로챈다.
 *
 * `closeOnClick`: 링크 항목의 기본값은 「닫지 않는다」다. 앱 안에서 옮기면 메뉴가 그 자리에 남아
 * 다음 화면을 덮을 수 있으므로 닫는다.
 */
export function MenuLinkItem({
  href,
  onNavigate,
  onClick,
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof MenuPrimitive.LinkItem>, "className" | "href"> &
  LayoutProps & { href: string; onNavigate: () => void }) {
  return (
    <MenuPrimitive.LinkItem
      href={href}
      closeOnClick
      className={cn(menuItemVariants({ variant: "default" }), layout)}
      data-slot="menu-item"
      data-variant="default"
      onClick={(event) => {
        onClick?.(event);
        if (!isPlainClick(event)) return;
        event.preventDefault();
        onNavigate();
      }}
      {...rest}
    >
      {children}
    </MenuPrimitive.LinkItem>
  );
}
```

`ButtonLink` 와 달리 `event.defaultPrevented` 를 보지 않는다 — 메뉴 부품이 안에서 기본 동작을 막아도 이동은 우리가 정한다.

- [ ] **Step 5: 통과를 확인한다**

Run: `cd frontend && npx vitest run tests/ButtonLink.test.tsx`
Expected: PASS (12 tests)

Base UI 의 `onClick` 인자 타입이 `isPlainClick` 과 맞지 않아 `tsc` 가 불평하면(Base UI 가 이벤트를 감싼 타입을 줄 때), 인자를 `event as unknown as MouseEvent` 로 바꾸지 말고 `isPlainClick` 의 매개변수 타입(`Pick<…>`)이 받는지 먼저 본다 — `Pick` 이므로 감싼 이벤트도 그 다섯 속성을 가지면 통과한다.

- [ ] **Step 6: 부품 가드와 전체 검사**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 타입 오류 0. 실패는 알려진 2건뿐. 특히 `UiSkin` · `ClassExistence` · `DesignTokens` · `FocusRing` 가 통과해야 한다 — 새 클래스는 `box-border` 하나이고 정적 유틸리티다.

- [ ] **Step 7: 설계 문서 §4 를 고친다**

`specs/018-react-router/design.md` §4 의 첫 항목(「`ui/ButtonLink.tsx` 를 새로 둔다 …」)을 다음으로 바꾼다:

```markdown
- **`ButtonLink`(`ui/Button.tsx`) 와 `MenuLinkItem`(`ui/DropdownMenu.tsx`)** 을 둔다. 둘 다 진짜 `<a href>` 를
  그리고, **보통 클릭만** 가로채 `onNavigate` 콜백을 부른다. Cmd/Ctrl/Shift/Alt·가운데 클릭은 브라우저가
  새 탭·새 창으로 연다. 모양은 `Button`·`MenuItem` 의 변종 표를 그대로 쓴다.
  - **`react-router` 의 `<Link>` 를 쓰지 않는다** (구현 중 결정). `<Link>` 는 라우터 밖에서 예외를 던지는데,
    검사 19개 파일이 `TestList` 를 라우터 없이 그린다. 화면은 지금처럼 콜백 prop 을 받고, `href` 는
    `lib/paths.ts` 에서 얻는다. 콜백을 `navigate()` 로 채우는 것은 라우트 어댑터다.
```

같은 절의 「링크로 바꾸는 것」 목록을 다음으로 바꾼다 (초안 「녹화」는 `DraftList` 안의 조작이라 이번에 두지 않는다):

```markdown
- **링크로 바꾸는 것: 부수효과가 없는 순수 이동만.**
  - 목록 머리띠의 「바꾸기」(프로젝트) · 「비밀 값」 · 「키 관리」 · 「테스트 만들기」
  - 목록 행의 「결과 보기」, 행 메뉴의 「편집」(`MenuLinkItem`)
  - 비밀 값의 「키 관리」 · 「닫기」, 키 관리의 「닫기」
```

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/ui/Button.tsx frontend/src/ui/DropdownMenu.tsx \
  frontend/tests/ButtonLink.test.tsx specs/018-react-router/design.md
git commit -m "$(cat <<'EOF'
feat(018): 버튼 모양의 링크 부품을 둔다 (T002)

ButtonLink·MenuLinkItem 은 진짜 <a href> 를 그리고 보통 클릭만 앱 안에서 옮긴다.
라우터 문맥이 필요 없어 화면을 단독으로 그리는 검사가 그대로 선다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---
### Task 3: 앱 저장소 — `app/appStore.ts`

**Files:**
- Create: `frontend/src/app/appStore.ts`
- Test: `frontend/tests/AppStore.test.ts`
- Modify: `specs/018-react-router/design.md` (§3.1 · §5)

**Interfaces:**
- Consumes: `project.current()` · `setExpectedProjectRoot()` (`src/api/client.ts`), `ErrorInfo` (`src/components/ErrorNotice.tsx`)
- Produces (`src/app/appStore.ts`):
  - `interface AppState { readonly project: ProjectView | null | undefined; readonly error: ErrorInfo | null; readonly importDone: ImportResultView | null }` — `project` 가 `undefined` 면 아직 모른다
  - `interface AppStore { getState(): AppState; subscribe(listener: () => void): () => void; ensureProject(): Promise<ProjectView | null>; openProject(p: ProjectView | null): void; renameProject(root: string, name: string): void; setError(error: ErrorInfo | null): void; setImportDone(result: ImportResultView | null): void; keepImportPlan(plan: ImportPlanView): void; importPlan(planId: string): ImportPlanView | null; dropImportPlan(planId: string): void }`
  - `createAppStore(): AppStore`
  - `AppStoreContext: React.Context<AppStore | null>` · `useAppStore(): AppStore` · `useAppState<T>(select: (s: AppState) => T): T`

**왜 React 상태가 아닌가:** loader 는 React 밖에서 돈다. 초안 조회에 실패한 loader 는 오류를 알려야 하고(§5), 프로젝트 조회는 loader 보다 먼저 끝나야 한다(§3.2). 둘 다 컴포넌트 상태로는 닿지 않는다. 라우터마다 하나를 만든다 — 모듈 전역이면 검사끼리 상태가 샌다.

- [ ] **Step 1: 실패하는 검사를 쓴다**

`frontend/tests/AppStore.test.ts`:

```ts
/**
 * 018 §3.1·§3.2 — 앱 저장소.
 *
 * 가장 중요한 것은 **프로젝트 조회가 한 번이고, 끝나는 순간 모든 요청이 그 프로젝트를 말한다**는 것이다.
 * 옛 `App.tsx` 의 `openProject` 가 「효과로 미루지 않고 곧바로 세운다」고 적은 판단(2026-09-10 사용자
 * 보고 1번)을 저장소가 이어받는다. 헤더 대조 자체는 `ProjectRootGuard.test.ts` 가 본다.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { setExpectedProjectRoot, tests, type ImportPlanView, type ProjectView } from "../src/api/client";
import { createAppStore } from "../src/app/appStore";

const PROJECT = { name: "P", root: "/tmp/p", default_start_url: "http://t/" } as ProjectView;
const HEADER = "X-ITB-Project-Root";

interface Call {
  url: string;
  headers: Record<string, string>;
}

function stub(project: { status: number; body: unknown }) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push({ url, headers: (init?.headers ?? {}) as Record<string, string> });
      const body = url === "/api/project" ? project : { status: 200, body: { tests: [], problems: [] } };
      return new Response(JSON.stringify(body.body), { status: body.status });
    }),
  );
  return calls;
}

const NOT_OPEN = {
  status: 404,
  body: {
    error: {
      code: "PROJECT_NOT_OPEN",
      category: "blocked",
      message: "열린 프로젝트가 없습니다",
      next_action: "프로젝트를 여세요",
      detail: {},
    },
  },
};

afterEach(() => {
  setExpectedProjectRoot(null);
  vi.unstubAllGlobals();
});

describe("열린 프로젝트 (018 §3.2)", () => {
  it("처음에는 모른다 — `undefined` 다", () => {
    expect(createAppStore().getState().project).toBeUndefined();
  });

  it("동시에 여러 번 물어도 조회는 한 번이다 — 미들웨어는 이동마다 돈다", async () => {
    const calls = stub({ status: 200, body: PROJECT });
    const store = createAppStore();
    const [a, b] = await Promise.all([store.ensureProject(), store.ensureProject()]);
    await store.ensureProject();
    expect(a?.root).toBe("/tmp/p");
    expect(b?.root).toBe("/tmp/p");
    expect(calls.filter((c) => c.url === "/api/project")).toHaveLength(1);
  });

  it("조회가 끝나면 다음 요청부터 그 프로젝트를 말한다", async () => {
    const calls = stub({ status: 200, body: PROJECT });
    await createAppStore().ensureProject();
    await tests.list();
    const listCall = calls.find((c) => c.url.startsWith("/api/tests"));
    expect(listCall?.headers[HEADER]).toBe(encodeURIComponent("/tmp/p"));
  });

  it("조회에 실패하면 열린 프로젝트가 없다 — `null` 이다", async () => {
    stub(NOT_OPEN);
    const store = createAppStore();
    await expect(store.ensureProject()).resolves.toBeNull();
    expect(store.getState().project).toBeNull();
  });

  it("사용자가 먼저 연 프로젝트를 늦게 온 조회가 덮지 않는다", async () => {
    let release: (r: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((resolve) => (release = resolve))),
    );
    const store = createAppStore();
    const pending = store.ensureProject();
    const mine = { ...PROJECT, root: "/tmp/mine", name: "mine" };
    store.openProject(mine);
    release(new Response(JSON.stringify(PROJECT), { status: 200 }));
    await expect(pending).resolves.toEqual(mine);
    expect(store.getState().project).toEqual(mine);
  });

  it("이름 바꾸기는 같은 경로일 때만 반영된다 (012 FR-405)", () => {
    const store = createAppStore();
    store.openProject(PROJECT);
    store.renameProject("/tmp/other", "남의 것");
    expect(store.getState().project?.name).toBe("P");
    store.renameProject("/tmp/p", "새 이름");
    expect(store.getState().project?.name).toBe("새 이름");
  });

  it("프로젝트를 닫으면 요청이 더는 프로젝트를 말하지 않는다 (012 FR-416)", async () => {
    const calls = stub({ status: 200, body: PROJECT });
    const store = createAppStore();
    store.openProject(PROJECT);
    store.openProject(null);
    await tests.list();
    expect(calls.at(-1)?.headers[HEADER]).toBeUndefined();
  });
});

describe("구독 (018 §3.1)", () => {
  it("상태가 바뀔 때마다 알리고, 끊으면 더 알리지 않는다", () => {
    const store = createAppStore();
    const listener = vi.fn();
    const off = store.subscribe(listener);
    store.setError({ message: "m", nextAction: "n", category: "blocked", code: "X" });
    store.setImportDone(null);
    expect(listener).toHaveBeenCalledTimes(2);
    off();
    store.setError(null);
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("바뀌지 않은 필드는 같은 객체다 — 선택 함수가 헛돌지 않는다", () => {
    const store = createAppStore();
    store.openProject(PROJECT);
    const before = store.getState().project;
    store.setError(null);
    expect(store.getState().project).toBe(before);
  });
});

describe("가져오기 계획 (018 §3.4)", () => {
  const plan = { plan_id: "p-1", file_name: "a.xlsx" } as ImportPlanView;

  it("맡긴 계획을 돌려주고, 버리면 없다", () => {
    const store = createAppStore();
    expect(store.importPlan("p-1")).toBeNull();
    store.keepImportPlan(plan);
    expect(store.importPlan("p-1")).toBe(plan);
    store.dropImportPlan("p-1");
    expect(store.importPlan("p-1")).toBeNull();
  });

  it("저장소마다 따로다 — 새로 고친 앱은 계획을 모른다", () => {
    createAppStore().keepImportPlan(plan);
    expect(createAppStore().importPlan("p-1")).toBeNull();
  });
});
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run tests/AppStore.test.ts`
Expected: FAIL — `Failed to resolve import "../src/app/appStore"`

- [ ] **Step 3: 구현한다**

`frontend/src/app/appStore.ts`:

```ts
/**
 * 앱 저장소 — 화면을 넘어 사는 상태 (018 design §3.1).
 *
 * 옛 `App.tsx` 가 `useState` 로 쥐던 것 중 **loader 도 닿아야 하는 것**을 여기로 옮겼다.
 *
 * - 열린 프로젝트 — 루트 미들웨어가 loader 보다 먼저 채운다 (§3.2)
 * - 오류 — 초안 조회에 실패한 loader 가 알린다 (§5). 문자열이 아니라 `ErrorInfo` 다 (003 EC-004)
 * - 가져오기 결과·계획 — 미리보기에서 만들어지고 목록에서 확인한다 (014 FR-018a · §3.4)
 *
 * **React 상태가 아니라 바깥 저장소다.** loader 는 React 밖에서 돈다. 화면은 `useAppState` 로 구독한다.
 * **라우터마다 하나다** (`createAppStore`) — 모듈 전역이면 검사끼리 상태가 새고, 새로 고친 앱이 옛
 * 가져오기 계획을 기억하는 것처럼 보이게 된다.
 */
import { createContext, useContext, useSyncExternalStore } from "react";

import {
  project as projectApi,
  setExpectedProjectRoot,
  type ImportPlanView,
  type ImportResultView,
  type ProjectView,
} from "../api/client";
import type { ErrorInfo } from "../components/ErrorNotice";

export interface AppState {
  /** `undefined` = 아직 모른다. `null` = 열린 프로젝트가 없다. */
  readonly project: ProjectView | null | undefined;
  readonly error: ErrorInfo | null;
  /** 방금 끝난 가져오기의 결과. 목록 위에 한 번 보이고 사용자가 닫는다 (014 FR-018a). */
  readonly importDone: ImportResultView | null;
}

export interface AppStore {
  getState(): AppState;
  subscribe(listener: () => void): () => void;
  /** 열린 프로젝트를 한 번만 조회한다. 이미 알면 묻지 않는다. 실패는 「없다」(`null`)다. */
  ensureProject(): Promise<ProjectView | null>;
  openProject(p: ProjectView | null): void;
  renameProject(root: string, name: string): void;
  setError(error: ErrorInfo | null): void;
  setImportDone(result: ImportResultView | null): void;
  keepImportPlan(plan: ImportPlanView): void;
  importPlan(planId: string): ImportPlanView | null;
  dropImportPlan(planId: string): void;
}

export function createAppStore(): AppStore {
  let state: AppState = { project: undefined, error: null, importDone: null };
  const listeners = new Set<() => void>();
  /**
   * 가져오기 계획 (§3.4). **구독 대상이 아니다** — 화면은 이것을 그리지 않고 loader 만 읽는다.
   * `location.state` 에 두지 않는 이유: 그것은 새로 고쳐도 남아 만료된 계획을 그린다.
   */
  const plans = new Map<string, ImportPlanView>();
  let pending: Promise<ProjectView | null> | null = null;

  const update = (patch: Partial<AppState>) => {
    state = { ...state, ...patch };
    for (const listener of listeners) listener();
  };

  /*
    2026-09-10 사용자 보고 1번 — **화면이 보고 있는 프로젝트를 모든 요청이 함께 말한다.**

    **효과로 미루지 않고 여기서 곧바로 세운다.** 효과는 렌더 뒤에 돌고, 자식의 효과가 부모보다 먼저
    돈다 — 프로젝트를 바꾼 직후 새로 붙는 목록 화면의 첫 조회가 옛 프로젝트의 경로를 달고 나가게 된다
    (옛 `App.tsx` 의 `openProject` 주석).
  */
  const openProject = (p: ProjectView | null) => {
    setExpectedProjectRoot(p?.root ?? null);
    update({ project: p });
  };

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    ensureProject() {
      if (state.project !== undefined) return Promise.resolve(state.project);
      pending ??= projectApi
        .current()
        .then(
          (p) => p,
          // 열린 프로젝트가 없으면 선택 화면부터다 — 그 화면이 기존 프로젝트를 불러 보여준다 (DR-002).
          () => null,
        )
        .then((p) => {
          pending = null;
          // 기다리는 사이 사용자가 연 프로젝트가 있으면 그것이 이긴다.
          if (state.project === undefined) openProject(p);
          return state.project ?? null;
        });
      return pending;
    },
    openProject,
    renameProject(root, name) {
      /*
        **경로가 같을 때만 갈아 끼운다** (012 FR-405). 목록의 어느 줄에서나 이름을 고칠 수 있으므로,
        지금 열려 있는 것과 다른 프로젝트를 고쳤는데 열린 것의 이름을 바꾸면 안 된다.
      */
      const p = state.project;
      if (p && p.root === root) update({ project: { ...p, name } });
    },
    setError(error) {
      update({ error });
    },
    setImportDone(importDone) {
      update({ importDone });
    },
    keepImportPlan(plan) {
      plans.set(plan.plan_id, plan);
    },
    importPlan(planId) {
      return plans.get(planId) ?? null;
    },
    dropImportPlan(planId) {
      plans.delete(planId);
    },
  };
}

export const AppStoreContext = createContext<AppStore | null>(null);

export function useAppStore(): AppStore {
  const store = useContext(AppStoreContext);
  if (store === null) throw new Error("AppStoreContext 가 없습니다 — AppRoot 안에서만 쓸 수 있습니다.");
  return store;
}

/**
 * 저장소의 한 조각을 구독한다.
 *
 * **선택 함수는 필드를 그대로 돌려줘야 한다.** 새 객체를 만들면 매번 다른 값이 되어 무한히 다시 그린다.
 * 저장소는 바뀌지 않은 필드를 같은 객체로 두므로 필드를 꺼내는 것은 안전하다.
 */
export function useAppState<T>(select: (s: AppState) => T): T {
  const store = useAppStore();
  return useSyncExternalStore(store.subscribe, () => select(store.getState()));
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run tests/AppStore.test.ts`
Expected: PASS (11 tests)

「사용자가 먼저 연 프로젝트를 …」가 실패하면 `release` 가 불리기 전에 `fetch` 가 호출되지 않은 것이다 — `projectApi.current()` 는 동기적으로 `fetch` 를 부르므로 `ensureProject()` 직후 `release` 가 채워져 있어야 한다. `get()` 이 `await` 뒤에 `fetch` 를 부르도록 바뀌어 있다면 `release(...)` 앞에 `await Promise.resolve()` 를 한 줄 넣는다.

- [ ] **Step 5: 설계 문서를 고친다**

`specs/018-react-router/design.md` §3.1 의 표 바로 위에 다음 문단을 넣는다:

```markdown
**자리는 바깥 저장소(`app/appStore.ts`)다** (구현 중 결정). 셸의 React 상태로 두면 loader 가 닿지 못한다 —
초안 조회에 실패한 loader 가 오류를 알릴 수 없고, 프로젝트 조회를 loader 보다 먼저 끝낼 수도 없다.
저장소는 라우터마다 하나이며 화면은 `useAppState` 로 구독한다. 아래 표의 「셸」은 이 저장소를 뜻한다
(`pendingRun` · 만들기 잠금만 `actions.tsx` 의 React 상태다 — 버튼만 그것을 본다).
```

§5 표의 세 줄(`/sessions/:id` 두 줄, `/tests/new?draft=` 줄)을 다음으로 바꾼다:

```markdown
| `/sessions/:id` 조회 실패 (이미 끝난 세션 포함) | loader 가 오류 없이 `/` 로 **교체 이동** (지금 `openSession` 의 실패와 같다) |
| `/tests/new?draft=` 조회 실패 | loader 가 저장소에 오류를 남기고 `/` 로 교체 이동 — 목록에서 출발했다면 목록이 그대로 남는다 |
```

그리고 표 아래 문단(「라우트 `errorElement` 는 …」)을 다음으로 바꾼다:

```markdown
라우트별 `errorElement` 는 두지 않는다 (구현 중 결정). loader 의 실패는 loader 가 저장소에 알리고
`replace()` 로 옮기면 끝난다 — 오류 화면을 한 번 그렸다가 다시 옮기는 깜빡임이 없고, 기록에 죽은 주소가
남지 않는다. `errorElement` 는 렌더 예외를 받는 루트 하나뿐이다.
```

- [ ] **Step 6: 전체 검사**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 타입 오류 0. 실패는 알려진 2건뿐.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/app/appStore.ts frontend/tests/AppStore.test.ts specs/018-react-router/design.md
git commit -m "$(cat <<'EOF'
feat(018): 화면을 넘어 사는 상태를 바깥 저장소로 둔다 (T003)

열린 프로젝트·오류·가져오기를 loader 와 화면이 함께 쓴다. 프로젝트 조회는 한 번이고,
끝나는 순간 요청이 그 프로젝트를 말한다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---
### Task 4: 라우트 표와 셸 — 아직 `main.tsx` 에 잇지 않는다

이 작업은 새 뿌리(`AppRoot`)를 **완성하고 검사로 증명**하되, 제품의 시작점(`main.tsx`)은 옛 `App` 그대로 둔다. 잇는 것은 Task 5 다 — 리뷰어가 「새 라우팅이 옛 동작을 옮겼는가」와 「옛 것을 치웠는가」를 따로 볼 수 있게 한다.

**Files:**
- Create: `frontend/src/app/arrival.ts`
- Create: `frontend/src/app/actions.tsx`
- Create: `frontend/src/app/AppShell.tsx`
- Create: `frontend/src/app/RouteStatus.tsx`
- Create: `frontend/src/app/routes/ListRoute.tsx` · `ComposeRoute.tsx` · `EditRoute.tsx` · `ResultRoute.tsx` · `SessionRoute.tsx` · `ImportRoute.tsx` · `KeysRoute.tsx` · `SecretsRoute.tsx` · `ProjectsRoute.tsx`
- Create: `frontend/src/app/router.tsx`
- Create: `frontend/src/app/AppRoot.tsx`
- Create: `frontend/tests/helpers/fakeServer.ts`
- Create: `frontend/tests/helpers/app.tsx`
- Modify: `frontend/tests/EditEntryPoints.test.tsx` (가짜 서버를 도우미로 옮긴다 — 동작 변화 없음)
- Test: `frontend/tests/Routing.test.tsx`

**Interfaces:**
- Consumes: `paths` · `PATTERNS` · `legacyPath` (Task 1), `ButtonLink` (Task 2), `AppStore` · `createAppStore` · `AppStoreContext` · `useAppStore` · `useAppState` (Task 3)
- Produces:
  - `src/app/arrival.ts`: `interface SessionArrival { readonly aiInstruction: string | null; readonly recordOnArrival: boolean; readonly instructionOnArrival: string | null }` · `arrivalState(a: Partial<SessionArrival>): SessionArrival` · `readArrival(state: unknown): SessionArrival` · `hasCommands(state: unknown): boolean` · `withoutCommands(state: unknown): SessionArrival`
  - `src/app/actions.tsx`: `interface AppActions { readonly pendingRun: string | null; startRun(testId: string, fromStepIndex?: number): void; openBrowserAt(testId: string, stepIndex: number, stepId: string | null, instruction: string | null): void; openRerecord(testId: string, stepIds: string[]): void; openSession(sessionId: string): void; readonly composeBusy: boolean; lockCompose(): boolean; unlockCompose(): void }` · `AppActionsProvider` · `useAppActions(): AppActions`
  - `src/app/routes/ComposeRoute.tsx`: `interface ComposeDraft { draft_id: string; name: string; group_prefix: string; instruction: string }` · `ComposeRoute`
  - `src/app/router.tsx`: `createRoutes(store: AppStore): RouteObject[]`
  - `src/app/AppRoot.tsx`: `interface AppParts { readonly store: AppStore; readonly router: DataRouter }` · `createBrowserApp(): AppParts` · `AppRoot(props: AppParts)`
  - `tests/helpers/fakeServer.ts`: `stubServer(options?: FakeServerOptions): FakeCall[]` 와 픽스처 `PROJECT` · `STEP_01` · `STEP_02` · `TEST` · `LIST` · `RESULT` · `DEFINITION_VIEW`
  - `tests/helpers/app.tsx`: `renderApp(url: string, options?: { state?: unknown; prepare?: (store: AppStore) => void }): RenderResult & { store: AppStore; router: DataRouter }`

- [ ] **Step 1: 가짜 서버를 도우미로 옮긴다**

`frontend/tests/EditEntryPoints.test.tsx` 의 19~201행(`const PROJECT` 부터 `function stubServer() { … }` 끝까지)을 **잘라 내** 아래 파일로 옮기고 옵션을 더한다. `frontend/tests/helpers/fakeServer.ts`:

```ts
/**
 * 앱 전체를 그리는 검사의 가짜 서버 (018 — `EditEntryPoints.test.tsx` 에서 옮겼다).
 *
 * 006 이 「이 라운드가 부르는 모든 경로를 아는 가짜 서버」로 만든 것을 라우팅 검사도 쓴다. 옮기며
 * 더한 것은 옵션뿐이다 — 열린 프로젝트가 없는 경우, 프로젝트 조회가 늦는 경우, 세션의 모습, 초안.
 * 요청마다 **헤더도** 적는다 — 프로젝트 조회보다 먼저 나간 요청은 프로젝트 헤더가 없다 (018 §3.2).
 */
import { vi } from "vitest";

import type { SessionView } from "../../src/api/client";
import { sessionView } from "./workbench";

// ↓ EditEntryPoints.test.tsx 19~136행(`PROJECT` · `verified` · `STEP_01` · `STEP_02` · `TEST` · `LIST` · `RESULT` ·
//   `DEFINITION_VIEW`)을 **한 글자도 바꾸지 않고** 여기 붙인다. `verified` 를 뺀 일곱 `const` 앞에 `export` 를 붙인다.

const NO_KEYS = {
  private_key_present: false,
  public_key_present: false,
  passphrase_protected: false,
  public_key_fingerprint: null,
  permission_warning: null,
  key_dir: "/tmp/itb-test/keys",
  sealed_projects: [],
  unlocked: true,
};

export interface FakeServerOptions {
  /** `null` 이면 열린 프로젝트가 없다 — `GET /api/project` 가 404 다. */
  project?: typeof PROJECT | null;
  /** 프로젝트 조회 응답을 이만큼 늦춘다 (ms). */
  projectDelayMs?: number;
  /** `GET /api/sessions/{id}` 와 세션 하위 경로가 돌려줄 세션에 덮어쓸 값. */
  session?: Partial<SessionView>;
  /** `GET /api/drafts/{id}` 의 응답. 여기 없는 식별자는 404 다. */
  drafts?: Record<string, unknown>;
  /** 이미 끝나 서버가 모르는 세션. `GET /api/sessions/{id}` 가 404 다. */
  missingSessions?: string[];
}

export interface FakeCall {
  url: string;
  method: string;
  body: unknown;
  headers: Record<string, string>;
}

const notFound = (code: string) => ({
  error: { code, category: "blocked", message: "찾을 수 없습니다", next_action: "목록에서 다시 고르세요", detail: {} },
});

/** 이 라운드가 부르는 모든 경로를 아는 가짜 서버. 요청을 기록해 돌려준다. */
export function stubServer(options: FakeServerOptions = {}): FakeCall[] {
  const calls: FakeCall[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url);
      const method = init?.method ?? "GET";
      calls.push({
        url: u,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : null,
        headers: (init?.headers ?? {}) as Record<string, string>,
      });
      const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

      if (u === "/api/project") {
        if (options.projectDelayMs) await new Promise((r) => setTimeout(r, options.projectDelayMs));
        return options.project === null
          ? json(notFound("PROJECT_NOT_OPEN"), 404)
          : json(options.project ?? PROJECT);
      }
      if (u === "/api/project/list") return json({ projects: [], warning: null });
      if (u === "/api/keys/status") return json(NO_KEYS);
      if (u === "/api/secrets") {
        return json({ public_key_fingerprint: null, fingerprint_matches_key: true, names: [] });
      }
      if (u.startsWith("/api/drafts/")) {
        const id = decodeURIComponent(u.slice("/api/drafts/".length));
        const draft = options.drafts?.[id];
        return draft === undefined ? json(notFound("DRAFT_NOT_FOUND"), 404) : json(draft);
      }
      /* ── 여기부터 EditEntryPoints 의 원래 분기 그대로 ── */
      if (u.startsWith("/api/tests/TC-001/definition")) return json(DEFINITION_VIEW);
      if (u.startsWith("/api/tests/TC-001/result")) return json(RESULT);
      if (u.startsWith("/api/tests")) return json(LIST);
      if (u === "/api/sessions") {
        if (method === "POST") {
          /* 원래 주석 그대로 */
          return json(
            sessionView({
              session_id: "s-new",
              state: "paused",
              state_label: "일시정지",
              test_id: "TC-001",
              authoring_mode: "record",
              steps: [STEP_01, STEP_02] as unknown as SessionView["steps"],
              current_step_index: 1,
            }),
            201,
          );
        }
        return json({ sessions: [] });
      }
      const sessionId = u.startsWith("/api/sessions/") ? u.slice("/api/sessions/".length).split("/")[0]! : null;
      if (sessionId !== null && options.missingSessions?.includes(sessionId)) {
        return json(notFound("SESSION_NOT_FOUND"), 404);
      }
      /* 원래 주석 그대로 */
      if (u.startsWith("/api/sessions/")) {
        return json(
          sessionView({
            session_id: "s-new",
            state: "replaying",
            state_label: "실행 중",
            test_id: "TC-001",
            steps: [STEP_01, STEP_02] as unknown as SessionView["steps"],
            current_step_index: 1,
            run_scope: "partial",
            run_start_index: 1,
            // 018 — 라우팅 검사가 세션의 모습을 정한다.
            ...options.session,
          }),
        );
      }
      if (u.startsWith("/api/preferences")) return json({ run_pacing: "normal" });
      return json({ ok: true });
    }),
  );
  return calls;
}
```

`/* 원래 주석 그대로 */` 두 자리에는 원문 `stubServer` 의 같은 자리 주석(「007 T004 — 손으로 조립하지 않고 …」 · 「007 T004 — 세션 하위 경로도 …」)을 그대로 붙인다. `project` 옵션의 타입이 `typeof PROJECT` 이므로 `PROJECT` 는 이 파일 위쪽에 있어야 한다.

`EditEntryPoints.test.tsx` 에는 잘라 낸 자리에 다음 가져오기를 둔다 (파일 머리의 `import { sessionView } …` 와 `import type { SessionView } …` 줄은 더 쓰이지 않으면 지운다 — `tsc` 의 `noUnusedLocals` 가 알려 준다):

```ts
import { stubServer } from "./helpers/fakeServer";
```

Run: `cd frontend && npx vitest run tests/EditEntryPoints.test.tsx`
Expected: PASS (6 tests) — 옮기기만 했으므로 결과가 같다.

- [ ] **Step 2: 앱 전체를 그리는 도우미를 쓴다**

`frontend/tests/helpers/app.tsx`:

```tsx
/**
 * 앱 전체를 **메모리 라우터**로 그린다 (018).
 *
 * 제품은 브라우저 라우터를 쓰지만 검사는 주소를 직접 쥐어야 한다 — 시작 주소, `history.state`, 이동 뒤의
 * 위치를 `router.state` 로 읽는다. 라우트 표와 저장소는 제품과 **같은 함수**(`createRoutes` ·
 * `createAppStore`)로 만든다.
 *
 * 검사가 끝나면 라우터를 버린다 — 남겨 두면 진행 중이던 loader 가 다음 검사의 가짜 서버를 부른다.
 * 저장소가 세운 프로젝트 경로도 되돌린다 (`client.ts` 의 모듈 값이다).
 */
import { render } from "@testing-library/react";
import { createMemoryRouter, type DataRouter } from "react-router";
import { afterEach } from "vitest";

import { setExpectedProjectRoot } from "../../src/api/client";
import { AppRoot } from "../../src/app/AppRoot";
import { createAppStore, type AppStore } from "../../src/app/appStore";
import { createRoutes } from "../../src/app/router";

const live: DataRouter[] = [];

afterEach(() => {
  for (const router of live.splice(0)) router.dispose();
  setExpectedProjectRoot(null);
});

export function renderApp(
  url: string,
  options: { state?: unknown; prepare?: (store: AppStore) => void } = {},
) {
  const store = createAppStore();
  options.prepare?.(store);
  const at = new URL(url, "http://localhost");
  const router = createMemoryRouter(createRoutes(store), {
    initialEntries: [{ pathname: at.pathname, search: at.search, state: options.state ?? null }],
  });
  live.push(router);
  return { ...render(<AppRoot store={store} router={router} />), store, router };
}
```

- [ ] **Step 3: 실패하는 라우팅 검사를 쓴다**

`frontend/tests/Routing.test.tsx`:

```tsx
/**
 * 018 — 주소가 화면을 고르고, 화면을 넘어 사는 상태가 이동을 견딘다 (design §2·§3·§5·§6 · §7.1).
 *
 * 005 R8 의 `useScreenUrl` 이 지키던 것(새로고침 복원 FR-166 · 뒤로가기 FR-167 · 지목 유지 FR-181·FR-239)을
 * 라우터 위에서 다시 고정하고, 018 이 새로 약속한 것(모든 화면 딥링크 · 일회성 명령 · 옛 주소 · 프로젝트
 * 조회 순서)을 더한다. 앱 전체를 메모리 라우터로 그려 **주소 → 화면**을 실제로 걷는다.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ImportPlanView } from "../src/api/client";
import { renderApp } from "./helpers/app";
import { stubServer } from "./helpers/fakeServer";

afterEach(() => {
  vi.unstubAllGlobals();
});

const action = (id: string) => document.querySelector<HTMLButtonElement>(`button[data-action="${id}"]`);

describe("주소마다 그 화면이 뜬다 (§2)", () => {
  it("/ — 테스트 목록", async () => {
    stubServer();
    renderApp("/");
    expect(await screen.findByText("로그인")).toBeTruthy();
  });

  it("/tests/TC-001/result — 결과 화면", async () => {
    stubServer();
    renderApp("/tests/TC-001/result");
    expect(await screen.findByText("Step 02 고치기")).toBeTruthy();
  });

  it("/tests/TC-001/edit — 편집 화면", async () => {
    stubServer();
    renderApp("/tests/TC-001/edit");
    expect(await screen.findByText("변경 저장")).toBeTruthy();
  });

  it("/tests/TC-001/edit?step=step-02 — 지목한 Step 이 펼쳐진다 (006 FR-181)", async () => {
    stubServer();
    renderApp("/tests/TC-001/edit?step=step-02");
    expect(await screen.findByText("dashboard-open")).toBeTruthy();
  });

  it("/tests/new — 만들기", async () => {
    stubServer();
    renderApp("/tests/new");
    expect(await screen.findByLabelText("시작 URL")).toBeTruthy();
  });

  it("/tests/new?draft= — 초안의 지시문이 미리 채워진다 (014 FR-031)", async () => {
    stubServer({
      drafts: { "D-0001": { draft_id: "D-0001", name: "초안", group_prefix: "TC", suggested_instruction: "로그인한다" } },
    });
    renderApp("/tests/new?draft=D-0001");
    await waitFor(() =>
      expect((screen.getByLabelText("자연어 지시") as HTMLTextAreaElement).value).toBe("로그인한다"),
    );
  });

  it("/keys — 키 관리", async () => {
    stubServer();
    renderApp("/keys");
    expect(await screen.findByRole("heading", { name: "키 관리" })).toBeTruthy();
  });

  it("/secrets — 비밀 값", async () => {
    stubServer();
    renderApp("/secrets");
    expect(await screen.findByRole("heading", { name: "비밀 값" })).toBeTruthy();
  });

  it("/projects — 프로젝트 선택", async () => {
    stubServer();
    renderApp("/projects");
    expect(await screen.findByRole("button", { name: /새 프로젝트 만들기/ })).toBeTruthy();
  });

  it("/sessions/:id — 실행 화면을 주소만으로 되찾는다", async () => {
    const calls = stubServer();
    renderApp("/sessions/s-new");
    await waitFor(() => expect(document.querySelector("[data-phase-pill]")).not.toBeNull());
    expect(calls.some((c) => c.method === "GET" && c.url === "/api/sessions/s-new")).toBe(true);
    expect(screen.queryByText("로그인")).toBeNull();
  });

  it("없는 경로는 목록으로 교체된다", async () => {
    stubServer();
    const { router } = renderApp("/없는/곳");
    expect(await screen.findByText("로그인")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("옛 주소 (§6)", () => {
  it("`?screen=` 주소는 새 주소로 **교체**된다 — 뒤로가기 기록에 남지 않는다", async () => {
    stubServer();
    const { router } = renderApp("/?screen=definition&test=TC-001&step=step-02");
    expect(await screen.findByText("dashboard-open")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/tests/TC-001/edit");
    expect(router.state.location.search).toBe("?step=step-02");
    expect(router.state.historyAction).toBe("REPLACE");
  });
});

describe("열린 프로젝트 (§3.2)", () => {
  it("열린 프로젝트가 없으면 어느 주소든 프로젝트 선택으로 간다", async () => {
    stubServer({ project: null });
    const { router } = renderApp("/tests/TC-001/result");
    await waitFor(() => expect(router.state.location.pathname).toBe("/projects"));
    expect(await screen.findByRole("button", { name: /새 프로젝트 만들기/ })).toBeTruthy();
  });

  it("세션 조회는 프로젝트를 확인한 **뒤에** 나간다 — 옛 뒤바뀜(2026-09-10 보고 1번)을 막는다", async () => {
    const calls = stubServer({ projectDelayMs: 30 });
    renderApp("/sessions/s-new");
    await waitFor(() => expect(calls.some((c) => c.url === "/api/sessions/s-new")).toBe(true));
    const first = calls.find((c) => c.url === "/api/sessions/s-new")!;
    expect(first.headers["X-ITB-Project-Root"]).toBe(encodeURIComponent("/tmp/p"));
  });
});

describe("실행 화면의 도착 정보 (§3.3)", () => {
  it("일회성 명령은 도착에 한 번 쓰이고 **기록에서 지워진다** — 새로 고쳐도 되살아나지 않는다", async () => {
    const calls = stubServer({ session: { state: "paused", pause_before_index: null } });
    const { router } = renderApp("/sessions/s-new?from=edit&step=step-02", {
      state: { aiInstruction: null, recordOnArrival: true, instructionOnArrival: null },
    });
    // 명령이 지워지기 전에 소비됐다 — 도착하자 기록이 켜졌다 (009 FR-291).
    await waitFor(() =>
      expect(
        calls.some((c) => c.method === "POST" && c.url === "/api/sessions/s-new/record-actions:start"),
      ).toBe(true),
    );
    // 기록에는 명령이 없다. 돌아갈 곳(주소)은 그대로다.
    await waitFor(() =>
      expect(router.state.location.state).toEqual({
        aiInstruction: null,
        recordOnArrival: false,
        instructionOnArrival: null,
      }),
    );
    expect(router.state.location.search).toBe("?from=edit&step=step-02");
  });

  it("명령 없이 들어오면 기록을 켜지 않는다", async () => {
    const calls = stubServer({ session: { state: "paused", pause_before_index: null } });
    renderApp("/sessions/s-new");
    await waitFor(() => expect(document.querySelector("[data-phase-pill]")).not.toBeNull());
    await new Promise((r) => setTimeout(r, 50));
    expect(calls.some((c) => c.url.includes("record-actions:start"))).toBe(false);
  });

  it("편집에서 온 세션은 끝나면 편집으로 돌아간다 — 새로 고친 뒤에도 (006 FR-204)", async () => {
    stubServer({ session: { state: "paused", pause_before_index: null } });
    const { router } = renderApp("/sessions/s-new?from=edit&step=step-02");
    await waitFor(() => expect(action("nav.back")).not.toBeNull());
    act(() => action("nav.back")!.click());
    await waitFor(() => expect(router.state.location.pathname).toBe("/tests/TC-001/edit"));
    expect(router.state.location.search).toBe("?step=step-02");
  });

  it("그 밖의 세션은 끝나면 목록으로 간다", async () => {
    stubServer({ session: { state: "paused", pause_before_index: null } });
    const { router } = renderApp("/sessions/s-new");
    await waitFor(() => expect(action("nav.back")).not.toBeNull());
    act(() => action("nav.back")!.click());
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
  });

  it("실행이 끝나면 결과로 넘어간다 — 편집에서 온 세션은 예외다 (2026-09-10 결정)", async () => {
    stubServer({ session: { state: "completed" } });
    const auto = renderApp("/sessions/s-new");
    await waitFor(() => expect(auto.router.state.location.pathname).toBe("/tests/TC-001/result"));
    auto.unmount();

    const fromEdit = renderApp("/sessions/s-new?from=edit");
    await waitFor(() => expect(document.querySelector("[data-phase-pill]")).not.toBeNull());
    await new Promise((r) => setTimeout(r, 50));
    expect(fromEdit.router.state.location.pathname).toBe("/sessions/s-new");
  });

  it("세션을 찾지 못하면 오류 없이 목록으로 교체된다 (옛 `openSession` 의 실패와 같다)", async () => {
    stubServer({ missingSessions: ["s-gone"] });
    const { router } = renderApp("/sessions/s-gone");
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(await screen.findByText("로그인")).toBeTruthy();
    expect(document.querySelector("[data-app-notice]")).toBeNull();
  });
});

describe("만들기의 초안 (§3.4 · §5)", () => {
  it("초안을 읽지 못하면 오류를 알리고 목록에 남는다 — 빈 지시문으로 들어가지 않는다 (014 US3)", async () => {
    stubServer();
    const { router } = renderApp("/tests/new?draft=D-없음");
    expect(await screen.findByText("찾을 수 없습니다")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/");
    expect(screen.queryByLabelText("시작 URL")).toBeNull();
  });
});

describe("가져오기 미리보기 (§3.4)", () => {
  const plan = {
    plan_id: "p-1",
    file_name: "설계서.xlsx",
    expires_at: "2026-09-17T01:00:00Z",
    draft_count: 0,
    group_count: 0,
    sheets: [],
    skipped: [],
    capacity: { needed: 0, available: 999, ok: true, groups: [] },
    warnings: [],
  } as ImportPlanView;

  it("맡긴 계획이 있으면 미리보기를 그린다", async () => {
    stubServer();
    renderApp("/import/p-1", { prepare: (store) => store.keepImportPlan(plan) });
    expect(await screen.findByText("설계서.xlsx")).toBeTruthy();
  });

  it("계획이 없으면(새로 고침) 사라졌다고 알리고 목록으로 교체된다 — 백엔드는 그대로다", async () => {
    stubServer();
    const { router } = renderApp("/import/p-1");
    expect(await screen.findByText("가져오기 미리보기가 사라졌습니다.")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("뒤로가기·앞으로가기 (005 FR-167 · 007 FR-241)", () => {
  it("결과에서 뒤로 가면 목록, 앞으로 가면 지목까지 그대로인 결과다", async () => {
    stubServer();
    const { router } = renderApp("/");
    expect(await screen.findByText("로그인")).toBeTruthy();
    await act(() => router.navigate("/tests/TC-001/result?step=step-02"));
    expect(await screen.findByText("Step 02 고치기")).toBeTruthy();
    // 숫자 이동은 기록만 옮기고 곧바로 돌아온다 — 위치는 기다려서 본다.
    await act(() => router.navigate(-1));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    await act(() => router.navigate(1));
    await waitFor(() => expect(router.state.location.pathname).toBe("/tests/TC-001/result"));
    expect(router.state.location.search).toBe("?step=step-02");
  });
});

describe("실행 경로 (005 T021 · U-06)", () => {
  it("실행을 연달아 눌러도 세션은 하나이고, 실행 화면으로 간다", async () => {
    const calls = stubServer();
    const { router } = renderApp("/tests/TC-001/result");
    await waitFor(() => expect(action("run.all")).not.toBeNull());
    act(() => action("run.all")!.click());
    act(() => action("run.all")?.click());
    await waitFor(() => expect(router.state.location.pathname).toBe("/sessions/s-new"));
    expect(calls.filter((c) => c.url === "/api/sessions" && c.method === "POST")).toHaveLength(1);
  });
});
```

- [ ] **Step 4: 실패를 확인한다**

Run: `cd frontend && npx vitest run tests/Routing.test.tsx`
Expected: FAIL — `Failed to resolve import "../../src/app/AppRoot"`

- [ ] **Step 5: 도착 정보 — `src/app/arrival.ts`**

```ts
/**
 * 실행 화면의 도착 정보 (018 design §3.3).
 *
 * 옛 `App.tsx` 의 `runner` 화면은 세션 객체와 함께 다섯 가지를 들고 다녔다. 018 은 그것을 성격대로 나눴고,
 * 이 파일은 그중 **`location.state` 에 싣는 셋**을 다룬다.
 *
 * - `aiInstruction` — **기록**이다. 무엇을 시켰는지 화면에 남아야 한다 (001 FR-063 · UX U-07).
 * - `recordOnArrival` · `instructionOnArrival` — **일회성 명령**이다. 도착하면 한 번 수행하고 끝난다
 *   (009 FR-291 · 011 FR-374a).
 *
 * `history.state` 는 새로 고쳐도 남는다. 명령을 지우지 않으면 **새로 고침이 AI 지시문을 다시 수행한다** —
 * 같은 Step 이 두 벌 들어간다. 그래서 실행 화면은 명령을 첫 렌더에 꺼내 두고 기록에서는 지운다.
 */

export interface SessionArrival {
  readonly aiInstruction: string | null;
  readonly recordOnArrival: boolean;
  readonly instructionOnArrival: string | null;
}

export function arrivalState(a: Partial<SessionArrival>): SessionArrival {
  return {
    aiInstruction: a.aiInstruction ?? null,
    recordOnArrival: a.recordOnArrival ?? false,
    instructionOnArrival: a.instructionOnArrival ?? null,
  };
}

/** 기록에 무엇이 있든 모양을 믿지 않고 읽는다 — 다른 판의 앱이 남긴 기록일 수 있다. */
export function readArrival(state: unknown): SessionArrival {
  const s = (typeof state === "object" && state !== null ? state : {}) as Record<string, unknown>;
  return arrivalState({
    aiInstruction: typeof s.aiInstruction === "string" ? s.aiInstruction : null,
    recordOnArrival: s.recordOnArrival === true,
    instructionOnArrival: typeof s.instructionOnArrival === "string" ? s.instructionOnArrival : null,
  });
}

export function hasCommands(state: unknown): boolean {
  const a = readArrival(state);
  return a.recordOnArrival || a.instructionOnArrival !== null;
}

/** 명령만 지운다. 기록(`aiInstruction`)은 남긴다 — 하나로 합치면 수행이 끝난 뒤 기록도 사라진다. */
export function withoutCommands(state: unknown): SessionArrival {
  return { ...readArrival(state), recordOnArrival: false, instructionOnArrival: null };
}
```

- [ ] **Step 6: 세션을 여는 경로 — `src/app/actions.tsx`**

옛 `App.tsx` 의 `startRun` · `openBrowserAt` · `openRerecord` · `openSession` · 만들기 잠금을 옮긴다. **판단 주석은 원문을 옮기고**(아래에 줄인 것은 원문으로 채운다), 마지막 걸음만 `setScreen(...)` 에서 `navigate(...)` 로 바꾼다.

```tsx
/**
 * 세션을 여는 **유일한 경로** (018 design §3.5 · 005 T021 · FR-125·FR-127·FR-129).
 *
 * 옛 `App.tsx` 의 네 함수를 옮겼다. 달라진 것은 마지막 걸음뿐이다 — 화면 상태를 바꾸던 것이 이제 주소로
 * 옮긴다. `pendingRun` 을 여기 한 곳에 두는 이유는 그대로다: 화면마다 두면 한 화면이 빠뜨리고, 그 화면에서
 * 연타하면 브라우저 창이 둘 뜬다 (U-06 — 실측 5회 클릭에 201 이 2건이었다).
 */
import { createContext, useContext, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { sessions } from "../api/client";
import { describeError } from "../components/ErrorNotice";
import { paths } from "../lib/paths";
import { useAppStore } from "./appStore";
import { arrivalState } from "./arrival";

export interface AppActions {
  /** 실행 요청이 진행 중인 테스트 ID (005 FR-127·FR-129). `null` 이 아니면 어느 실행 버튼도 눌리지 않는다. */
  readonly pendingRun: string | null;
  startRun(testId: string, fromStepIndex?: number): void;
  openBrowserAt(testId: string, stepIndex: number, stepId: string | null, instruction: string | null): void;
  openRerecord(testId: string, stepIds: string[]): void;
  openSession(sessionId: string): void;
  /** 만들기 국면이 세션을 만드는 중인가 — 옛 `composePending` (005 U-06 과 같은 결함). */
  readonly composeBusy: boolean;
  /** 만들기 잠금을 건다. 이미 걸려 있으면 `false` — 그 요청은 버린다. */
  lockCompose(): boolean;
  unlockCompose(): void;
}

const AppActionsContext = createContext<AppActions | null>(null);

export function useAppActions(): AppActions {
  const actions = useContext(AppActionsContext);
  if (actions === null) throw new Error("AppActionsProvider 안에서만 쓸 수 있습니다.");
  return actions;
}

export function AppActionsProvider({ children }: { children: ReactNode }) {
  const store = useAppStore();
  const navigate = useNavigate();
  const [pendingRun, setPendingRun] = useState<string | null>(null);
  const [composeBusy, setComposeBusy] = useState(false);
  /*
    같은 틱 안의 두 번째 클릭을 막는 잠금 (옛 `composeLock` 주석 원문).
    `composeBusy` 만으로는 부족하다 — 상태는 다시 그려진 뒤에야 보이므로 …
  */
  const composeLock = useRef(false);

  const actions: AppActions = {
    pendingRun,
    composeBusy,

    /* 옛 `startRun` 의 머리주석 원문 */
    startRun(testId, fromStepIndex) {
      // 첫 클릭만 받는다. 0.3초 안에 화면이 변해야 하므로(FR-129) 응답을 기다리지 않고 즉시 상태를 세운다.
      if (pendingRun !== null) return;
      setPendingRun(testId);
      store.setError(null);
      void sessions
        .create({ mode: "replay", test_id: testId })
        .then(async (session) => {
          // "실패한 Step부터 실행" — 세션을 만든 뒤 곧바로 실행 위치를 옮긴다 (FR-055).
          if (fromStepIndex !== undefined && fromStepIndex > 0) {
            return await sessions.runFrom(session.session_id, fromStepIndex);
          }
          return session;
        })
        .then((session) => navigate(paths.session(session.session_id)))
        .catch((exc: unknown) => store.setError(describeError(exc)))
        // 성공해도 놓는다 (옛 주석 원문).
        .finally(() => setPendingRun(null));
    },

    /* 옛 `openBrowserAt` 의 머리주석 원문 */
    openBrowserAt(testId, stepIndex, stepId, instruction) {
      if (pendingRun !== null) return;
      setPendingRun(testId);
      store.setError(null);
      void sessions
        .create({ mode: "replay", test_id: testId, pause_before_index: stepIndex })
        .then((session) =>
          navigate(
            // 006 FR-204 — 끝나면 출발한 편집 화면으로 돌아온다. 돌아갈 곳은 주소에 싣는다 (018 §3.3).
            paths.session(session.session_id, { stepId }),
            {
              /*
                009 FR-291 · 011 FR-374a · 011 converge FR-377 — 옛 `openBrowserAt` 의 세 주석 원문.
                지시문으로 출발했으면 도착해서 그것을 수행하고, 아니면 기록을 켠다. **하나만** 켜진다.
                지시문은 명령(`instructionOnArrival`)과 기록(`aiInstruction`)으로 갈라 같은 문장을 싣는다.
              */
              state: arrivalState({
                aiInstruction: instruction,
                recordOnArrival: instruction === null,
                instructionOnArrival: instruction,
              }),
            },
          ),
        )
        .catch((exc: unknown) => store.setError(describeError(exc)))
        .finally(() => setPendingRun(null));
    },

    /* 옛 `openRerecord` 의 머리주석 원문 — 서버에서 다른 모드이므로 갈라 둔다. 기록을 켜지 않는다. */
    openRerecord(testId, stepIds) {
      if (pendingRun !== null) return;
      setPendingRun(testId);
      store.setError(null);
      void sessions
        .create({ mode: "rerecord", test_id: testId, rerecord_step_ids: stepIds })
        // 006 FR-204 — 끝나면 출발한 편집 화면으로 돌아온다. 재녹화도 편집의 일이다.
        .then((session) => navigate(paths.session(session.session_id, { stepId: stepIds[0] ?? null })))
        .catch((exc: unknown) => store.setError(describeError(exc)))
        .finally(() => setPendingRun(null));
    },

    /**
     * 거절 안내가 가리킨 세션으로 이동한다 (005 T024 · FR-126).
     *
     * 세션 조회는 실행 화면의 loader 가 한다. 그 사이에 끝났다면 loader 가 목록으로 옮긴다 (018 §5).
     */
    openSession(sessionId) {
      store.setError(null);
      void navigate(paths.session(sessionId));
    },

    lockCompose() {
      if (composeLock.current) return false;
      composeLock.current = true;
      setComposeBusy(true);
      return true;
    },

    unlockCompose() {
      composeLock.current = false;
      setComposeBusy(false);
    },
  };

  return <AppActionsContext.Provider value={actions}>{children}</AppActionsContext.Provider>;
}
```

`navigate(...)` 는 Data 라우터에서 `Promise<void>` 를 돌려준다. `.then(...)` 안에서 돌려주는 것은 괜찮고, 문장으로 부를 때는 `void navigate(...)` 로 적는다 (떠 있는 약속을 남기지 않는다는 이 저장소의 관용).

- [ ] **Step 7: 셸과 상태 화면 — `src/app/AppShell.tsx` · `src/app/RouteStatus.tsx`**

`src/app/AppShell.tsx`:

```tsx
/**
 * 레이아웃 라우트 — 열린 프로젝트가 있을 때의 모든 화면이 이 안에 그려진다 (018 design §2).
 *
 * 알림 층은 **앱 뿌리에 하나**다 (017 Phase 10 · T100). 그래야 알림이 한 자리에 모이고 동시에 보이는 수의
 * 상한이 한 번만 적용된다. 프로젝트 선택 화면은 이 밖에 있다 — 옛 `App.tsx` 에서도 그 화면은 알림 층
 * 밖에서 그려졌다.
 */
import { Outlet } from "react-router";

import { ErrorNotice } from "../components/ErrorNotice";
import { Toast, Toaster } from "../ui/Toast";
import { AppActionsProvider, useAppActions } from "./actions";
import { useAppState, useAppStore } from "./appStore";

export function AppShell() {
  return (
    <AppActionsProvider>
      <Toaster>
        <ShellError />
        <Outlet />
      </Toaster>
    </AppActionsProvider>
  );
}

/*
  2026-09-10 사용자 결정 — **토스트는 한 자리다.** (옛 `App.tsx` 주석 원문을 옮긴다)
  오류이므로 **스스로 사라지지 않는다** — 「닫기」가 유일한 퇴장이다.
*/
function ShellError() {
  const store = useAppStore();
  const actions = useAppActions();
  const error = useAppState((s) => s.error);
  if (error === null) return null;
  const sessionId = error.sessionId;
  return (
    <Toast mark="data-app-notice" tone="error" onDismiss={() => store.setError(null)}>
      <ErrorNotice
        error={error}
        action={
          // 거절 안내가 가리킨 세션으로 가는 수단 — 없으면 안내가 화면에 없는 조작을 지시한다 (005 U-01).
          sessionId ? { label: "실행 중인 세션 보기", onClick: () => actions.openSession(sessionId) } : null
        }
      />
    </Toast>
  );
}
```

`src/app/RouteStatus.tsx`:

```tsx
/**
 * 라우터가 화면을 그리지 못하는 동안의 두 화면 (018 design §2 · §5).
 */
import { useEffect } from "react";
import { useRouteError } from "react-router";

import { paths } from "../lib/paths";
import { ButtonLink } from "../ui/Button";

/**
 * 첫 조회(열린 프로젝트) 동안의 화면. 옛 `App.tsx` 의 `loading` 화면 그대로다.
 *
 * 실브라우저 하니스가 `main` 이 뜨기를 기다리므로 요소를 바꾸지 않는다 (`ui_context.py` 의 `open`).
 */
export function Loading() {
  return <main className="p-s6 text-ink-2">불러오는 중…</main>;
}

/**
 * 렌더 예외를 받는 루트 오류 화면. 018 전에는 흰 화면이었다.
 *
 * 「목록으로」는 **문서를 새로 연다** (`onNavigate` 없음). 예외가 난 앱의 상태를 믿고 그 안에서 옮기면
 * 같은 예외를 다시 밟을 수 있다. 원인은 콘솔에 남긴다 — 보고할 것이 거기 있다.
 */
export function RouteErrorScreen() {
  const error = useRouteError();
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <main className="p-s6 text-ink-2 flex flex-col items-start gap-s2">
      <div>화면을 그리지 못했습니다. 목록에서 다시 시작하세요.</div>
      <ButtonLink href={paths.list()}>목록으로</ButtonLink>
    </main>
  );
}
```

**「원문」으로 적은 주석의 출처** — 모두 `frontend/src/App.tsx`(커밋 `e8e3578`)의 해당 줄을 그대로 옮긴다. 주석 안의 `setScreen`·`screen.*` 같은 옛 이름만 새 이름으로 바꾼다.

| 옮길 자리 | `App.tsx` 줄 |
|---|---|
| `composeLock` 위 주석 | 148–155 |
| `startRun` 머리주석 | 281–291 |
| `startRun` 의 「성공해도 놓는다」 | 309–310 |
| `openBrowserAt` 머리주석 · 매개변수 주석 | 314–334 |
| `openBrowserAt` 의 009·011·011 converge 주석 | 347–368 |
| `openRerecord` 머리주석 | 376–388 |
| `ShellError` 위 토스트 주석 | 473–481 |
| `ListRoute` 의 세션 주기 조회 주석 (Step 8) | 199–203 |
| `ListRoute` 의 초안 녹화 주석 (Step 8) | 515–521 |
| `ComposeRoute` 의 세션 생성 주석 두 개 (Step 8) | 603–615 · 655–662 |
| `ImportRoute` 의 취소·결과 주석 (Step 8) | 689–693 · 698–701 |
| `ProjectsRoute` 의 세 주석 (Step 8) | 443–458 |
| `SessionRoute` 의 결과 자동 이동 · 고치기 주석 (Step 8) | 739–744 · 746–767 |

- [ ] **Step 8: 라우트 어댑터 9개 — `src/app/routes/`**

어댑터는 URL·loader 값을 **기존 페이지 prop 으로 옮기기만** 한다. 페이지는 고치지 않는다.

`ListRoute.tsx`:

```tsx
/** 테스트 목록 `/` (018 §2). 살아 있는 세션의 주기 조회는 이 화면만 쓰므로 여기 둔다 (§3.1). */
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router";

import { sessions, type SessionView } from "../../api/client";
import { describeError } from "../../components/ErrorNotice";
import { paths } from "../../lib/paths";
import { ImportDoneNotice } from "../../pages/ImportPreview";
import { TestList } from "../../pages/TestList";
import { useAppActions } from "../actions";
import { useAppState, useAppStore } from "../appStore";

export function ListRoute() {
  const navigate = useNavigate();
  const store = useAppStore();
  const actions = useAppActions();
  const project = useAppState((s) => s.project);
  const importDone = useAppState((s) => s.importDone);

  /** 살아 있는 세션. 목록 화면이 이것을 배너로 알린다 (UX U-05). */
  const [active, setActive] = useState<SessionView[]>([]);
  const refreshActive = useCallback(() => {
    void sessions
      .list()
      .then((r) => setActive(r.sessions))
      .catch(() => setActive([])); // 조회 실패가 목록 화면을 막을 이유는 없다
  }, []);

  useEffect(() => {
    refreshActive();
    // 005 FR-169 (U-17) — 목록에 머무는 동안 세션 상태를 따라간다. (App.tsx 199–203 원문)
    const timer = window.setInterval(refreshActive, 5000);
    return () => window.clearInterval(timer);
  }, [refreshActive]);

  return (
    <>
      {importDone !== null && (
        <ImportDoneNotice result={importDone} onDismiss={() => store.setImportDone(null)} />
      )}
      <TestList
        projectName={project?.name}
        onCreate={() => void navigate(paths.compose())}
        onRun={(testId) => actions.startRun(testId)}
        pendingRunId={actions.pendingRun}
        onOpenProjects={() => void navigate(paths.projects())}
        /* 014 US2 — 파일을 읽었을 뿐이고 아직 아무것도 만들어지지 않았다. 계획은 저장소가 맡는다 (§3.4). */
        onImportPlan={(plan) => {
          store.keepImportPlan(plan);
          void navigate(paths.importPreview(plan.plan_id));
        }}
        /*
          014 US3 — 초안에서 녹화를 시작한다. (App.tsx 515–521 원문)
          초안 조회는 `/tests/new` 의 loader 가 한다. 실패하면 목록이 그대로 남는다 (018 §3.4).
        */
        onRecordDraft={(draft) => void navigate(paths.compose(draft.draft_id))}
        onRefreshSessions={refreshActive}
        onOpenResult={(testId) => void navigate(paths.result(testId))}
        onOpenDefinition={(testId) => void navigate(paths.edit(testId))}
        onOpenSecrets={() => void navigate(paths.secrets())}
        onOpenKeys={() => void navigate(paths.keys())}
        activeSessions={active}
        onResumeSession={(session) => void navigate(paths.session(session.session_id))}
        onDiscardSession={(sessionId) =>
          void sessions
            .discard(sessionId)
            .catch((exc: unknown) => store.setError(describeError(exc)))
            .finally(refreshActive)
        }
      />
    </>
  );
}
```

`ComposeRoute.tsx`:

```tsx
/** 만들기 `/tests/new[?draft=]` (018 §3.4). 초안은 loader 가 읽어 온다 (`router.tsx`). */
import { useEffect } from "react";
import { useLoaderData, useNavigate } from "react-router";

import { sessions } from "../../api/client";
import { describeError } from "../../components/ErrorNotice";
import { paths } from "../../lib/paths";
import { ComposeView } from "../../pages/ComposeView";
import { useAppActions } from "../actions";
import { useAppState, useAppStore } from "../appStore";
import { arrivalState } from "../arrival";

/** 초안에서 출발한 만들기 (014 US3 · FR-030·FR-031) — 옛 `Screen` 의 `compose.draft` 와 같은 모양이다. */
export interface ComposeDraft {
  draft_id: string;
  name: string;
  group_prefix: string;
  instruction: string;
}

export function ComposeRoute() {
  const draft = useLoaderData() as ComposeDraft | null;
  const navigate = useNavigate();
  const store = useAppStore();
  const actions = useAppActions();
  const project = useAppState((s) => s.project) ?? null;

  // 지난 시도의 잠금을 들고 들어가지 않는다 — 세션 생성에 실패하고 목록으로 돌아온 뒤 다시 들어오면
  // 버튼이 눌리지 않는 채로 남는다 (옛 `onCreate` 주석).
  useEffect(() => {
    actions.unlockCompose();
    // 들어올 때 한 번만 — `actions` 는 매 렌더 새 객체다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fail = (exc: unknown) => {
    actions.unlockCompose();
    store.setError(describeError(exc));
  };

  return (
    <ComposeView
      // 초안이 바뀌면 입력칸을 새로 채운다 — `initialInstruction` 은 첫 렌더에만 읽힌다.
      key={draft?.draft_id ?? "new"}
      project={project}
      onCancel={() => void navigate(paths.list())}
      /* 014 FR-031 — 초안에서 출발했으면 지시문을 미리 채운다 */
      initialInstruction={draft?.instruction ?? null}
      fromDraft={draft ? { draft_id: draft.draft_id, name: draft.name } : null}
      /* (App.tsx 603–615 원문 — 세션 생성 경로를 새로 만들지 않는다 · 진행 중에는 다시 받지 않는다) */
      busy={actions.composeBusy}
      onRecord={(startUrl) => {
        if (!actions.lockCompose()) return;
        void sessions
          .create({
            mode: "record",
            start_url: startUrl,
            // 초안에서 손으로 녹화하는 것도 온전한 방법이다 (수렴 2회차).
            draft_id: draft?.draft_id ?? null,
          })
          // 저장 이름·그룹의 기본값은 세션 응답의 `draft` 가 나른다 (018 §3.3).
          .then((session) => navigate(paths.session(session.session_id)))
          .catch(fail);
      }}
      onStartAi={(startUrl, aiInstruction) => {
        if (!actions.lockCompose()) return;
        void sessions
          .create({
            mode: "ai",
            start_url: startUrl,
            ai_instruction: aiInstruction,
            /* 014 FR-030 — 초안에서 왔다는 사실을 서버에 알린다. (App.tsx 655–662 원문) */
            draft_id: draft?.draft_id ?? null,
          })
          .then((session) =>
            navigate(paths.session(session.session_id), { state: arrivalState({ aiInstruction }) }),
          )
          .catch(fail);
      }}
    />
  );
}
```

`EditRoute.tsx`:

```tsx
/** 편집 `/tests/:testId/edit[?step=]` (018 §2). 진입점이 몇이든 이 한 화면으로 온다 (006 FR-179). */
import { useNavigate, useParams, useSearchParams } from "react-router";

import { paths } from "../../lib/paths";
import { EditView } from "../../pages/EditView";
import { useAppActions } from "../actions";

export function EditRoute() {
  const { testId } = useParams() as { testId: string };
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const actions = useAppActions();
  return (
    <EditView
      testId={testId}
      focusStepId={search.get("step")}
      onRun={(id, fromStepIndex) => actions.startRun(id, fromStepIndex)}
      onOpenBrowserAt={(id, stepIndex, stepId, instruction) =>
        actions.openBrowserAt(id, stepIndex, stepId, instruction ?? null)
      }
      onRerecordRange={(id, stepIds) => actions.openRerecord(id, stepIds)}
      onOpenSession={(sessionId) => actions.openSession(sessionId)}
      /* 007 FR-239 — 편집 ↔ 결과 왕복에서도 보던 Step 을 잃지 않는다. */
      onShowResult={(id, stepId) => void navigate(paths.result(id, stepId ?? null))}
      runPending={actions.pendingRun !== null}
      onBack={() => void navigate(paths.list())}
    />
  );
}
```

`ResultView` 와 `EditView` 의 `testId` 가 바뀌어도 옛 `App.tsx` 는 화면을 다시 만들지 않았다. 같은 동작을 지키려고 여기서도 `key` 를 주지 않는다.

`ResultRoute.tsx`:

```tsx
/** 결과 `/tests/:testId/result[?step=]` (018 §2). */
import { useNavigate, useParams, useSearchParams } from "react-router";

import { paths } from "../../lib/paths";
import { ResultView } from "../../pages/ResultView";
import { useAppActions } from "../actions";

export function ResultRoute() {
  const { testId } = useParams() as { testId: string };
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const actions = useAppActions();
  return (
    <ResultView
      testId={testId}
      focusStepId={search.get("step")}
      onRunAll={(id) => actions.startRun(id)}
      onRunFrom={(id, stepIndex) => actions.startRun(id, stepIndex)}
      runPending={actions.pendingRun !== null}
      // FR-056 — 실패한 Step 의 상세로 바로 이동한다 (T170).
      onEditStep={(id, stepId) => void navigate(paths.edit(id, stepId))}
      onBack={() => void navigate(paths.list())}
    />
  );
}
```

`SessionRoute.tsx`:

```tsx
/**
 * 실행 화면 `/sessions/:sessionId[?from=edit&step=]` (018 §3.3).
 *
 * 세션은 loader 가 읽는다 — 주소만으로 되살아난다. 도착 정보는 `arrival.ts` 머리주석을 본다.
 */
import { useEffect, useState } from "react";
import { useLoaderData, useLocation, useNavigate, useSearchParams } from "react-router";

import type { SessionView } from "../../api/client";
import { paths } from "../../lib/paths";
import { SessionScreen } from "../../pages/SessionScreen";
import { useAppActions } from "../actions";
import { hasCommands, readArrival, withoutCommands } from "../arrival";

export function SessionRoute() {
  const session = useLoaderData() as SessionView;
  /*
    **세션마다 새로 그린다.** 같은 라우트 안에서 세션이 바뀌면(편집 세션에서 「고치기」로 새 세션을 열 때)
    React 는 컴포넌트를 재사용한다. 그러면 첫 렌더에 꺼낸 도착 정보와 `SessionScreen` 의 내부 상태가
    **옛 세션의 것**으로 남는다 — `SessionScreen` 은 `initial` 을 `useState` 초기값으로만 읽는다.
  */
  return <SessionBody key={session.session_id} session={session} />;
}

function SessionBody({ session }: { session: SessionView }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const actions = useAppActions();

  /*
    **명령은 첫 렌더에 꺼낸다.** 수행은 세션이 도착점에 멈춘 뒤라서, 그 전에 기록을 지우면 prop 이 먼저
    사라진다. 꺼낸 값은 이 컴포넌트가 사는 동안 상태에 남고, 기록에서는 곧바로 지운다 (§3.3).
  */
  const [arrival] = useState(() => readArrival(location.state));
  useEffect(() => {
    if (hasCommands(location.state)) {
      void navigate(location, { replace: true, state: withoutCommands(location.state) });
    }
    // 첫 렌더에만 — 꺼낸 명령은 이미 `arrival` 에 있다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 006 FR-204 — 편집에서 출발한 세션은 그 화면으로 돌아온다. 돌아갈 곳은 주소에 있다. */
  const fromEdit = search.get("from") === "edit";
  const backStep = search.get("step");

  return (
    <SessionScreen
      initial={session}
      aiInstruction={arrival.aiInstruction}
      /* 초안 출처는 세션 응답이 나른다 — 새로 고쳐도 남는다 (014 수렴 2회차). */
      draft={session.draft ?? null}
      /* 009 FR-291 — 목표 자리에 도착하면 기록을 켠다 */
      recordOnArrival={arrival.recordOnArrival}
      /* 011 FR-374a — 목표 자리에 도착하면 지시문을 수행한다 */
      instructionOnArrival={arrival.instructionOnArrival}
      /*
        편집 화면은 마운트마다 `GET /definition` 을 다시 읽으므로 세션에서 저장한 내용이 반영된
        상태로 보인다 (옛 App.tsx 주석).
      */
      onFinished={() =>
        void navigate(fromEdit && session.test_id ? paths.edit(session.test_id, backStep) : paths.list())
      }
      onShowResult={(testId, stepId) => void navigate(paths.result(testId, stepId ?? null))}
      /* (App.tsx 739–744 원문 — 실행이 끝나면 결과로. 편집에서 출발한 세션은 예외다) */
      autoShowResult={!fromEdit}
      /* (App.tsx 746–767 원문 — 실패한 실행에서 곧바로 고치기) */
      onEditStep={(testId, stepId, stepIndex) => {
        if (stepIndex < 0) {
          void navigate(paths.edit(testId, stepId));
          return;
        }
        actions.openBrowserAt(testId, stepIndex, stepId, null);
      }}
      onRerun={(testId, fromStepIndex) => actions.startRun(testId, fromStepIndex)}
    />
  );
}
```

`ImportRoute.tsx`:

```tsx
/** 가져오기 미리보기 `/import/:planId` (018 §3.4). 계획은 loader 가 저장소에서 꺼낸다. */
import { useLoaderData, useNavigate } from "react-router";

import type { ImportPlanView } from "../../api/client";
import { paths } from "../../lib/paths";
import { ImportPreview } from "../../pages/ImportPreview";
import { useAppStore } from "../appStore";

export function ImportRoute() {
  const plan = useLoaderData() as ImportPlanView;
  const navigate = useNavigate();
  const store = useAppStore();
  /*
    **목록으로 교체한다.** 끝난 미리보기로 뒤로 가면 계획이 없어 「사라졌습니다」가 뜬다 — 이미 끝낸 일을
    다시 알리는 셈이다. 교체하면 뒤로가기가 미리보기 전의 목록으로 간다.
  */
  const leave = () => {
    store.dropImportPlan(plan.plan_id);
    void navigate(paths.list(), { replace: true });
  };
  return (
    <ImportPreview
      plan={plan}
      /* (App.tsx 689–693 원문 — 취소는 목록으로 되돌아가는 것뿐이다) */
      onCancel={leave}
      /* (App.tsx 698–701 원문 — 결과를 버리지 않는다) */
      onDone={(result) => {
        store.setImportDone(result);
        leave();
      }}
    />
  );
}
```

`KeysRoute.tsx`:

```tsx
/** 키 관리 `/keys` (018 §2). */
import { useNavigate } from "react-router";

import { paths } from "../../lib/paths";
import { KeyManagement } from "../../pages/KeyManagement";

export function KeysRoute() {
  const navigate = useNavigate();
  return <KeyManagement onClose={() => void navigate(paths.list())} />;
}
```

`SecretsRoute.tsx`:

```tsx
/** 비밀 값 `/secrets` (018 §2). */
import { useNavigate } from "react-router";

import { paths } from "../../lib/paths";
import { SecretValues } from "../../pages/SecretValues";

export function SecretsRoute() {
  const navigate = useNavigate();
  return (
    <SecretValues
      onClose={() => void navigate(paths.list())}
      onManageKeys={() => void navigate(paths.keys())}
    />
  );
}
```

`ProjectsRoute.tsx`:

```tsx
/** 프로젝트 선택 `/projects` (018 §3.2). 알림 층 밖이다 — 옛 `App.tsx` 에서도 그랬다. */
import { useNavigate } from "react-router";

import { paths } from "../../lib/paths";
import { ProjectSetup } from "../../pages/ProjectSetup";
import { useAppState, useAppStore } from "../appStore";

export function ProjectsRoute() {
  const navigate = useNavigate();
  const store = useAppStore();
  const project = useAppState((s) => s.project);
  return (
    <ProjectSetup
      onOpened={(p) => {
        store.openProject(p);
        void navigate(paths.list());
      }}
      /* (App.tsx 443–446 원문) 열려 있던 프로젝트가 있을 때만 되돌아가는 길을 준다. */
      onCancel={project ? () => void navigate(paths.list()) : undefined}
      /* (App.tsx 448–451 원문) 삭제로 열린 프로젝트가 닫혔다 (012 FR-416). */
      onProjectClosed={() => store.openProject(null)}
      /* (App.tsx 453–458 원문) 목록에서 고친 이름이 다른 화면에도 나타나야 한다 (012 FR-405). */
      onProjectRenamed={(root, name) => store.renameProject(root, name)}
    />
  );
}
```

- [ ] **Step 9: 라우트 표 — `src/app/router.tsx`**

```tsx
/**
 * 라우트 표 (018 design §2).
 *
 * 005 R8 은 라우터를 두지 않았다 — 요구가 새로고침 복원과 뒤로가기 둘뿐이었다. 018 은 경로형 주소 · 모든 화면의
 * 딥링크 · 링크 기반 이동을 요구하고, 그래서 이 표가 생겼다 (design §1).
 *
 * **loader 는 URL 을 화면이 받는 값으로 바꾸기만 한다.** 화면이 스스로 읽던 데이터(결과 · 정의 · 목록)는 지금처럼
 * 화면이 읽는다. loader 가 읽는 것은 옛 `App.tsx` 가 화면을 고르기 **전에** 읽던 것뿐이다 — 세션 · 초안.
 *
 * **실패는 loader 가 끝낸다** (§5). 저장소에 알리고 `replace()` 로 옮긴다 — 오류 화면을 그렸다 다시 옮기는
 * 깜빡임이 없고, 기록에 죽은 주소가 남지 않는다. `errorElement` 는 렌더 예외를 받는 루트 하나뿐이다.
 */
import { Outlet, replace, type RouteObject } from "react-router";

import { drafts, sessions } from "../api/client";
import { describeError, type ErrorInfo } from "../components/ErrorNotice";
import { PATTERNS, legacyPath, paths } from "../lib/paths";
import { AppShell } from "./AppShell";
import type { AppStore } from "./appStore";
import { Loading, RouteErrorScreen } from "./RouteStatus";
import { ComposeRoute, type ComposeDraft } from "./routes/ComposeRoute";
import { EditRoute } from "./routes/EditRoute";
import { ImportRoute } from "./routes/ImportRoute";
import { KeysRoute } from "./routes/KeysRoute";
import { ListRoute } from "./routes/ListRoute";
import { ProjectsRoute } from "./routes/ProjectsRoute";
import { ResultRoute } from "./routes/ResultRoute";
import { SecretsRoute } from "./routes/SecretsRoute";
import { SessionRoute } from "./routes/SessionRoute";

/**
 * 새로 고친 미리보기 (§3.4 · 사용자 결정). 계획은 서버 메모리에만 있고 만료되며 조회 API 가 없다 —
 * 백엔드를 고치지 않고 다시 고르게 한다. 사용자가 고칠 수 있으므로 `blocked` 다.
 */
const IMPORT_PLAN_GONE: ErrorInfo = {
  message: "가져오기 미리보기가 사라졌습니다.",
  nextAction: "목록에서 파일을 다시 고르세요.",
  category: "blocked",
  code: "IMPORT_PLAN_GONE",
};

/**
 * 초안에서 출발한 만들기 (014 US3). **읽지 못하면 화면을 바꾸지 않는다** — 빈 지시문으로 들어가면 사용자는
 * 초안이 비어 있는 줄 안다. 목록에서 출발했다면 loader 가 끝날 때까지 목록이 그대로 보이고, 목록으로
 * **교체**하므로 목록은 다시 그려지지 않는다.
 */
async function loadDraft(store: AppStore, request: Request): Promise<ComposeDraft | null> {
  const draftId = new URL(request.url).searchParams.get("draft");
  if (!draftId) return null;
  try {
    const detail = await drafts.get(draftId);
    return {
      draft_id: detail.draft_id,
      name: detail.name,
      group_prefix: detail.group_prefix,
      instruction: detail.suggested_instruction,
    };
  } catch (exc) {
    store.setError(describeError(exc));
    throw replace(paths.list());
  }
}

export function createRoutes(store: AppStore): RouteObject[] {
  return [
    {
      id: "root",
      element: <Outlet />,
      hydrateFallbackElement: <Loading />,
      errorElement: <RouteErrorScreen />,
      /*
        **프로젝트 조회를 loader 보다 먼저 끝낸다** (§3.2). Data 라우터는 부모와 자식의 loader 를 동시에 돌린다 —
        그대로 두면 `/sessions/:id` 의 조회가 프로젝트 경로 없이 나가, 2026-09-10 사용자 보고 1번의 뒤바뀜
        (「a 프로젝트에서 만든 테스트가 b 에 들어갔다」)이 되살아난다. 미들웨어는 모든 loader 를 감싼다.
        이동마다 돌지만 조회는 처음 한 번뿐이다 (`ensureProject`).
      */
      middleware: [
        async (_args, next) => {
          await store.ensureProject();
          await next();
        },
      ],
      children: [
        { path: PATTERNS.projects, element: <ProjectsRoute /> },
        {
          id: "shell",
          element: <AppShell />,
          // 열린 프로젝트가 없으면 선택 화면부터다 (DR-002). 죽은 주소를 기록에 남기지 않도록 교체한다.
          loader: () => {
            if (store.getState().project === null) throw replace(paths.projects());
            return null;
          },
          children: [
            {
              index: true,
              // 옛 `?screen=` 주소 (§6) — 열어 둔 탭과 북마크를 끊지 않는다.
              loader: ({ request }) => {
                const to = legacyPath(new URL(request.url).search);
                if (to !== null) throw replace(to);
                return null;
              },
              element: <ListRoute />,
            },
            {
              path: PATTERNS.compose,
              loader: ({ request }) => loadDraft(store, request),
              element: <ComposeRoute />,
            },
            { path: PATTERNS.edit, element: <EditRoute /> },
            { path: PATTERNS.result, element: <ResultRoute /> },
            {
              path: PATTERNS.session,
              // 그 사이에 끝났다면 이동할 곳이 없다. 목록이 현재 상태를 보여준다 (옛 `openSession`).
              loader: async ({ params }) => {
                try {
                  return await sessions.get(params.sessionId ?? "");
                } catch {
                  throw replace(paths.list());
                }
              },
              // 같은 주소로의 이동(일회성 명령 지우기 · §3.3)에는 세션을 다시 읽지 않는다.
              shouldRevalidate: ({ currentUrl, nextUrl, defaultShouldRevalidate }) =>
                currentUrl.href === nextUrl.href ? false : defaultShouldRevalidate,
              element: <SessionRoute />,
            },
            {
              path: PATTERNS.importPreview,
              loader: ({ params }) => {
                const plan = store.importPlan(params.planId ?? "");
                if (plan === null) {
                  store.setError(IMPORT_PLAN_GONE);
                  throw replace(paths.list());
                }
                return plan;
              },
              element: <ImportRoute />,
            },
            { path: PATTERNS.keys, element: <KeysRoute /> },
            { path: PATTERNS.secrets, element: <SecretsRoute /> },
            // 모르는 주소는 목록이다 — 005 가 「알 수 없는 값은 목록」으로 정한 것과 같다.
            {
              path: "*",
              loader: () => {
                throw replace(paths.list());
              },
            },
          ],
        },
      ],
    },
  ];
}
```

- [ ] **Step 10: 뿌리 — `src/app/AppRoot.tsx`**

```tsx
/**
 * 앱 뿌리 — 저장소와 라우터를 잇는다 (018 design §2).
 *
 * 제품은 `createBrowserApp()` 로 한 벌을 **시작할 때 한 번** 만든다 — 브라우저 라우터는 `popstate` 를 듣고,
 * 컴포넌트 안에서 만들면 StrictMode 의 이중 마운트가 두 벌을 만든다. 검사는 같은 `createRoutes` 로 메모리
 * 라우터를 만들어 `AppRoot` 에 넘긴다 (`tests/helpers/app.tsx`).
 */
import { createBrowserRouter, type DataRouter } from "react-router";
import { RouterProvider } from "react-router/dom";

import { AppStoreContext, createAppStore, type AppStore } from "./appStore";
import { createRoutes } from "./router";

export interface AppParts {
  readonly store: AppStore;
  readonly router: DataRouter;
}

export function createBrowserApp(): AppParts {
  const store = createAppStore();
  return { store, router: createBrowserRouter(createRoutes(store)) };
}

export function AppRoot({ store, router }: AppParts) {
  return (
    <AppStoreContext.Provider value={store}>
      <RouterProvider router={router} />
    </AppStoreContext.Provider>
  );
}
```

- [ ] **Step 11: 라우팅 검사가 통과하는지 본다**

Run: `cd frontend && npx vitest run tests/Routing.test.tsx`
Expected: PASS (25 tests)

실패하면 원인별로:
- `No HydrateFallback element provided` 경고만 있고 통과 → 무시하지 말고 루트의 `hydrateFallbackElement` 가 표에 있는지 본다.
- 「일회성 명령」 검사에서 POST 가 없다 → `SessionBody` 의 `useState(() => readArrival(...))` 가 첫 렌더에 읽는지, `SessionRoute` 가 `key` 로 감싸는지 본다.
- 「세션 조회는 프로젝트를 확인한 뒤에」에서 헤더가 없다 → 미들웨어가 `await store.ensureProject()` **뒤에** `next()` 를 부르는지 본다.
- 「옛 주소」에서 `historyAction` 이 `PUSH` → `redirect()` 가 아니라 `replace()` 를 던지는지 본다.

- [ ] **Step 12: 전체 검사**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 타입 오류 0. 실패는 알려진 2건뿐. `VisualLanguage` · `OutcomeVocabulary` · `StepNumberConsistency` 는 `src/**` 전체를 훑으므로 새 파일도 그 규칙을 지나야 한다 — 실패하면 그 검사의 메시지대로 새 파일을 고친다(검사를 고치지 않는다).

- [ ] **Step 13: 커밋**

```bash
git add frontend/src/app frontend/tests/helpers/fakeServer.ts frontend/tests/helpers/app.tsx \
  frontend/tests/Routing.test.tsx frontend/tests/EditEntryPoints.test.tsx
git commit -m "$(cat <<'EOF'
feat(018): 라우트 표와 셸을 세운다 (T004)

URL 을 기존 화면 prop 으로 옮기는 어댑터 9개와, 세션을 여는 단일 경로를 라우터 위로 옮긴다.
아직 main.tsx 에 잇지 않는다 — 메모리 라우터로 25개 경로 검사를 먼저 세운다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---
### Task 5: 전환 — 제품을 새 뿌리로 잇고 옛 경로를 치운다

**Files:**
- Modify: `frontend/src/main.tsx`
- Delete: `frontend/src/App.tsx`
- Delete: `frontend/src/hooks/useScreenUrl.ts`
- Delete: `frontend/tests/ScreenUrl.test.ts`
- Modify: `frontend/tests/EditEntryPoints.test.tsx`
- Modify: `frontend/tests/PhaseContext.test.tsx`
- Modify: `frontend/tests/RecheckPhase12.test.tsx`
- Modify: `frontend/tests/DraftToRecording.test.tsx`
- Modify: `frontend/tests/RunRejectNavigation.test.tsx`

**Interfaces:**
- Consumes: `createBrowserApp` · `AppRoot` (Task 4), `renderApp` · `stubServer` (Task 4), `paths` · `PATTERNS` · `legacyPath` (Task 1)
- Produces: 없음 (옛 `App` · `useScreenUrl` · `initialLocation` · `locationToSearch` · `searchToLocation` · `WorkbenchLocation` 이 **사라진다**)

- [ ] **Step 1: 옛 이름을 아직 쓰는 곳을 확인한다**

Run: `cd frontend && grep -rn "useScreenUrl\|initialLocation\|locationToSearch\|searchToLocation\|WorkbenchLocation\|ScreenLocation\|src/App\b\|from \"./App\"\|App.tsx" src tests`
Expected: `src/main.tsx` · `src/App.tsx` · `src/hooks/useScreenUrl.ts` 와, 검사 다섯 파일(`ScreenUrl` · `EditEntryPoints` · `PhaseContext` · `RecheckPhase12` · `DraftToRecording` · `RunRejectNavigation`)만 나온다. 다른 파일이 나오면 이 작업 안에서 함께 옮긴다.

- [ ] **Step 2: 제품의 시작점을 바꾼다**

`frontend/src/main.tsx` 전체:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AppRoot, createBrowserApp } from "./app/AppRoot";
// 정본(`theme/tokens.css`)은 `tailwind.css` 가 @import 로 끌어온다. 여기서 따로
// 불러오면 같은 시트가 두 번 실리고, 나중에 순서가 어긋났을 때 원인을 찾기 어렵다.
import "./theme/tailwind.css";

const root = document.getElementById("root");
if (root === null) throw new Error("#root 를 찾을 수 없습니다.");

// 라우터는 여기서 한 번만 만든다 — `AppRoot` 머리주석.
const app = createBrowserApp();

createRoot(root).render(
  <StrictMode>
    <AppRoot {...app} />
  </StrictMode>,
);
```

- [ ] **Step 3: 옛 파일을 지운다**

```bash
git rm frontend/src/App.tsx frontend/src/hooks/useScreenUrl.ts frontend/tests/ScreenUrl.test.ts
rmdir frontend/src/hooks 2>/dev/null || true
```

`ScreenUrl.test.ts` 가 지키던 것은 이제 `paths.test.ts`(변환 · 옛 이름 · 왕복)와 `Routing.test.tsx`(뒤로가기 · 앞으로가기 · 옛 주소 교체 · 기본 화면에 파라미터 없음)가 지킨다. 「첫 렌더는 히스토리에 항목을 쌓지 않는다」는 라우터의 몫이 되었다 — 옛 주소의 교체 이동을 `Routing.test.tsx` 가 본다.

- [ ] **Step 4: `EditEntryPoints.test.tsx` 를 옮긴다**

(a) 가져오기: `import { App } from "../src/App";` 를 지우고 `import { renderApp } from "./helpers/app";` 를 더한다.

(b) `afterEach` 에서 `window.history.replaceState({}, "", "/");` 줄을 지운다 (메모리 라우터라 주소를 되돌릴 것이 없다). `vi.unstubAllGlobals();` 는 남긴다.

(c) 여섯 검사의 그리기를 바꾼다:

| 검사 | 지금 | 바꾼 뒤 |
|---|---|---|
| 목록 행 메뉴의 「편집」 | `render(<App />);` | `renderApp("/");` |
| 결과 화면의 「Step 02 고치기」 | `window.history.replaceState({}, "", "/?screen=result&test=TC-001");` + `render(<App />);` | `const { router } = renderApp("/tests/TC-001/result");` |
| 「정의 보기」 같은 도착지가 없다 | `render(<App />);` | `renderApp("/");` |
| 고쳐 저장한 뒤 「Step 02부터 실행」 | `replaceState(… "/?screen=result&test=TC-001")` + `render(<App />);` | `renderApp("/tests/TC-001/result");` |
| 「브라우저 열어 Step 02 에서 멈추기」 | `replaceState(… "/?screen=definition&test=TC-001&step=step-02")` + `render(<App />);` | `renderApp("/tests/TC-001/edit?step=step-02");` |
| 주소가 지목한 Step 을 새로고침 뒤에도 펼친다 | `replaceState(… "/?screen=definition&test=TC-001&step=step-02")` + `render(<App />);` | `renderApp("/tests/TC-001/edit?step=step-02");` |

(d) 「결과 화면의 Step 02 고치기」의 끝부분을 바꾼다 — **간헐 실패를 고치고, 주소도 본다**:

```tsx
    // 편집 가능한 화면이고, Step 02 가 지목·펼쳐져 있다.
    await waitFor(() => expect(screen.getByText("변경 저장")).toBeTruthy());
    // 펼침은 정의를 읽은 뒤에 그려진다 — 기다려서 본다 (전체 실행 부하에서 한 박자 늦던 간헐 실패).
    expect(await screen.findByText("dashboard-open")).toBeTruthy();
    expect(screen.getByLabelText("Step 대기 시간 (ms)")).toBeTruthy();
    // 006 FR-181 — 지목이 주소에 실린다. 새로 고쳐도 고치러 온 Step 을 잃지 않는다.
    expect(router.state.location.pathname).toBe("/tests/TC-001/edit");
    expect(router.state.location.search).toBe("?step=step-02");
```

(e) 더 쓰이지 않는 가져오기(`render` 등)는 `tsc` 가 알려 주는 대로 지운다.

Run: `cd frontend && npx vitest run tests/EditEntryPoints.test.tsx`
Expected: PASS (6 tests). 세 번 돌려 세 번 통과해야 한다.

- [ ] **Step 5: `PhaseContext.test.tsx` 의 주소 검사를 옮긴다**

(a) 가져오기에서 `../src/hooks/useScreenUrl` 묶음(`initialLocation` · `locationToSearch` · `searchToLocation` · `type WorkbenchLocation`)을 지우고 더한다:

```ts
import { matchPath } from "react-router";

import { PATTERNS, legacyPath, paths } from "../src/lib/paths";
```

(b) `describe("새로 고침이 위치를 되찾는다 (SC-006 · FR-240)", …)` 블록 **전체**를 다음으로 바꾼다:

```tsx
describe("새로 고침이 위치를 되찾는다 (SC-006 · FR-240 · 018)", () => {
  /**
   * 018 이 주소를 경로형으로 바꿨다. 묻는 것은 그대로다 — 어느 테스트의 어느 국면에서 어느 Step 을
   * 보고 있었나를 주소가 싣고, 되읽으면 그대로 나오는가. 되읽기는 라우트 표가 쓰는 `matchPath` 다.
   */
  const ROUND_TRIP: [pattern: string, url: string, params: Record<string, string>, step: string | null][] = [
    [PATTERNS.result, paths.result("TC-001", STEP), { testId: "TC-001" }, STEP],
    [PATTERNS.edit, paths.edit("TC-001", STEP), { testId: "TC-001" }, STEP],
    [PATTERNS.result, paths.result("TC-001"), { testId: "TC-001" }, null],
    [PATTERNS.edit, paths.edit("TC-002", "st-9"), { testId: "TC-002" }, "st-9"],
    [PATTERNS.session, paths.session("s-1"), { sessionId: "s-1" }, null],
  ];

  it("10번 중 10번 되찾는다 — 국면·테스트·Step 이 그대로다", () => {
    let restored = 0;
    for (let i = 0; i < 10; i += 1) {
      const [pattern, url, params, step] = ROUND_TRIP[i % ROUND_TRIP.length]!;
      const at = new URL(url, "http://localhost");
      const matched = matchPath(pattern, at.pathname);
      if (
        matched !== null &&
        JSON.stringify(matched.params) === JSON.stringify(params) &&
        at.searchParams.get("step") === step
      ) {
        restored += 1;
      }
    }
    expect(restored, "새로 고침이 위치를 잃었다").toBe(10);
  });

  it("결과 국면의 지목도 주소에 실린다 — 007 이 넓힌 자리다", () => {
    expect(paths.result("TC-001", STEP)).toBe(`/tests/TC-001/result?step=${STEP}`);
  });

  it("옛 주소로 열어 둔 탭도 같은 위치로 간다", () => {
    expect(legacyPath(`?screen=result&test=TC-001&step=${STEP}`)).toBe(
      `/tests/TC-001/result?step=${STEP}`,
    );
  });
});
```

Run: `cd frontend && npx vitest run tests/PhaseContext.test.tsx`
Expected: PASS

- [ ] **Step 6: `RecheckPhase12.test.tsx` 의 T118 을 옮긴다**

(a) `import { initialLocation, locationToSearch } from "../src/hooks/useScreenUrl";` 를 지우고 더한다:

```ts
import { renderApp } from "./helpers/app";
import { stubServer } from "./helpers/fakeServer";
```

(`afterEach` 와 `vi` 가 이 파일의 vitest 가져오기에 없으면 함께 더한다.)

(b) `describe("T118 새로고침이 화면 상태를 잃지 않는다 (FR-166 · N-01)", …)` 블록 **전체**를 다음으로 바꾼다:

```tsx
describe("T118 새로고침이 화면 상태를 잃지 않는다 (FR-166 · N-01)", () => {
  /**
   * 005 의 원인은 아직 화면을 정하지 못한 첫 렌더(`loading`)가 주소를 지운 것이었다 — 변환 함수는 처음부터
   * 옳았고, 틀린 것은 **그 국면**이었다. 018 은 그 국면을 라우터에 맡긴다. 여기서는 앱 전체를 그려
   * 「첫 조회를 기다리는 동안에도 주소가 그대로인가」를 본다.
   */
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("프로젝트 조회를 기다리는 동안에도 주소가 그대로이고, 끝나면 그 화면이다", async () => {
    stubServer({ projectDelayMs: 50 });
    const { router } = renderApp("/tests/TC-001/result");
    expect(screen.getByText("불러오는 중…")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/tests/TC-001/result");
    expect(await screen.findByText("Step 02 고치기")).toBeTruthy();
    expect(router.state.location.pathname).toBe("/tests/TC-001/result");
  });
});
```

`screen.getByText("불러오는 중…")` 이 실패하면 라우터가 첫 렌더에 대기 화면을 그리지 않은 것이다 — `findByText` 로 바꾸지 말고 `router.tsx` 루트의 `hydrateFallbackElement` 를 확인한다.

Run: `cd frontend && npx vitest run tests/RecheckPhase12.test.tsx`
Expected: PASS

- [ ] **Step 7: 소스를 읽는 가드 두 개의 대상을 옮긴다**

`DraftToRecording.test.tsx` — `describe("…")` 안의 「App 의 AI 시작 경로가 초안 식별자를 넘긴다」를 다음으로 바꾼다 (머리의 긴 주석은 남기고 `App.tsx` 를 `만들기 라우트` 로 고친다):

```tsx
  it("만들기 라우트의 AI 시작 경로가 초안 식별자를 넘긴다", async () => {
    /* (원래 주석 — `App.tsx` 를 `app/routes/ComposeRoute.tsx` 로 읽는다) */
    const source = await import("../src/app/routes/ComposeRoute.tsx?raw").then((m) => m.default as string);
    const aiCreate = /\.create\(\{[^}]*mode:\s*"ai"[\s\S]*?\}\)/.exec(source);
    expect(aiCreate, "만들기 라우트에 AI 세션 생성 경로가 없다").toBeTruthy();
    expect(aiCreate?.[0]).toContain("draft_id");
  });
```

`describe("저장 준비", …)` 의 첫 두 검사를 다음으로 바꾼다:

```tsx
  it("실행 화면이 초안을 받는다 — 세션 응답이 나른다 (018 §3.3)", async () => {
    // 이름·그룹의 기본값이 되려면 SessionScreen 이 초안을 알아야 한다.
    // 018 전에는 App 이 만들기 화면에서 들고 왔고, 이제는 새로 고쳐도 남는 세션 응답이 나른다.
    const source = await import("../src/app/routes/SessionRoute.tsx?raw").then((m) => m.default as string);
    expect(source).toContain("draft={session.draft ?? null}");
  });

  it("세션 응답의 초안은 그룹까지 갖는다", async () => {
    // 그룹이 빠지면 저장할 때 「그룹 없음」으로 떨어진다.
    const source = await import("../src/api/client.ts?raw").then((m) => m.default as string);
    expect(source).toContain("draft?: { draft_id: string; name: string; group_prefix: string } | null;");
  });
```

`RunRejectNavigation.test.tsx` — `// ─── 배선 ───` 아래의 `APP_SOURCE` 와 `describe("배너가 실제로 그 버튼을 받는다", …)` 를 다음으로 바꾼다:

```tsx
const raw = (path: string) =>
  (import.meta.glob(["../src/app/AppShell.tsx", "../src/app/actions.tsx", "../src/app/router.tsx"], {
    query: "?raw",
    import: "default",
    eager: true,
  }) as Record<string, string>)[path];

const SHELL_SOURCE = raw("../src/app/AppShell.tsx");
const ACTIONS_SOURCE = raw("../src/app/actions.tsx");
const ROUTER_SOURCE = raw("../src/app/router.tsx");

describe("배너가 실제로 그 버튼을 받는다", () => {
  it("셸이 `error.sessionId` 로 이동 액션을 만든다", () => {
    expect(SHELL_SOURCE).toContain("error.sessionId");
    expect(SHELL_SOURCE).toContain("실행 중인 세션 보기");
  });

  it("이동은 실행 화면 주소로 가고, 그 주소가 세션을 조회한다 — 목록으로 튕기지 않는다 (018 §3.5)", () => {
    expect(ACTIONS_SOURCE).toContain("navigate(paths.session(sessionId))");
    expect(ROUTER_SOURCE).toMatch(/sessions\.get\(/);
  });
});
```

`import.meta.glob` 의 첫 인자는 **리터럴**이어야 한다(Vite 가 빌드 때 푼다) — 함수 안에 두어도 인자가 리터럴이면 된다.

Run: `cd frontend && npx vitest run tests/DraftToRecording.test.tsx tests/RunRejectNavigation.test.tsx`
Expected: PASS

- [ ] **Step 8: 남은 옛 이름이 없는지, 빌드가 되는지 본다**

Run: `cd frontend && grep -rn "useScreenUrl\|initialLocation\|locationToSearch\|searchToLocation\|WorkbenchLocation\|src/App\b\|App\.tsx" src tests`
Expected: 출력 없음 (주석 속의 역사 서술 「옛 `App.tsx`」 는 남아도 된다 — 그 줄만 나오면 통과로 본다)

Run: `cd frontend && npm run build`
Expected: `tsc -b` 오류 0, `vite build` 성공

- [ ] **Step 9: 전체 검사**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 타입 오류 0. 실패는 알려진 2건뿐.

- [ ] **Step 10: 개발 서버로 한 번 띄워 본다**

`docs/DEVELOPMENT.md` 「실행」 절 그대로, 터미널 둘에서 띄운다:

```bash
cd backend && uv run uvicorn itb.api.app:app --host 127.0.0.1 --port 4320
cd frontend && npm run dev            # http://127.0.0.1:4310
```

브라우저에서 확인한다 — 결과가 다르면 멈추고 원인을 찾는다:
1. `http://127.0.0.1:4310/` → 목록(프로젝트가 없으면 `/projects`)
2. 목록에서 「결과 보기」 → 주소가 `/tests/<id>/result`
3. 새로 고침 → 같은 결과 화면
4. 뒤로가기 → 목록, 앞으로가기 → 결과
5. `http://127.0.0.1:4310/?screen=keys` 를 주소창에 붙여 넣기 → `/keys` 로 바뀌고 키 관리 화면

확인이 끝나면 두 프로세스를 끈다.

- [ ] **Step 11: 설계 문서의 뿌리 설명을 고친다**

`specs/018-react-router/design.md` §2 「바뀐다」 목록의 `main.tsx` · `App.tsx` 두 항목을 다음으로 바꾼다:

```markdown
- `main.tsx` — 시작할 때 `createBrowserApp()` 로 저장소와 브라우저 라우터를 **한 번** 만들어 `AppRoot` 에 넘긴다.
- `App.tsx` — **지운다** (구현 중 결정). 뿌리는 `app/AppRoot.tsx` 다. 라우터를 컴포넌트 안에서 만들면
  StrictMode 의 이중 마운트가 두 벌을 만들고, 버리는 시점도 애매하다. 검사는 같은 `createRoutes` 로
  메모리 라우터를 만들어 `AppRoot` 에 넘긴다 (`tests/helpers/app.tsx`) — 주소를 `replaceState` 로 바꾸고
  `<App />` 을 그리던 검사는 시작 주소를 직접 넘긴다.
```

같은 절의 「새로 만든다」 표에 `appStore.ts` · `arrival.ts` · `RouteStatus.tsx` · `AppRoot.tsx` 네 줄을 더한다 (각각 「화면을 넘어 사는 상태」 · 「실행 화면의 도착 정보」 · 「첫 로딩 · 루트 오류 화면」 · 「저장소와 라우터를 잇는 뿌리」).

- [ ] **Step 12: 커밋**

```bash
git add frontend/src/main.tsx frontend/tests/EditEntryPoints.test.tsx frontend/tests/PhaseContext.test.tsx \
  frontend/tests/RecheckPhase12.test.tsx frontend/tests/DraftToRecording.test.tsx \
  frontend/tests/RunRejectNavigation.test.tsx specs/018-react-router/design.md
git commit -m "$(cat <<'EOF'
feat(018): 제품을 라우터로 옮기고 옛 화면 상태를 지운다 (T005)

main.tsx 가 새 뿌리로 시작한다. App.tsx·useScreenUrl 을 지우고, 그 둘을 보던 검사는
경로·라우트 파일을 보도록 옮긴다. 편집 진입 검사의 간헐 실패도 함께 고친다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

(`git rm` 한 세 파일은 Step 3 에서 이미 스테이징됐다.)

---
### Task 6: 순수 이동을 링크로

**Files:**
- Modify: `frontend/src/pages/TestList.tsx` (가져오기 · 머리띠 네 조작 · 행의 「결과 보기」 · 행 메뉴의 「편집」)
- Modify: `frontend/src/pages/SecretValues.tsx` (「키 관리」 · 「닫기」)
- Modify: `frontend/src/pages/KeyManagement.tsx` (「닫기」)
- Test: `frontend/tests/NavLinks.test.tsx`
- Modify: `frontend/tests/ProjectListReachable.test.tsx` · `RunTrigger.test.tsx` · `RecheckPhase12.test.tsx` (역할 `button` → `link`)
- Modify: `backend/tests/abnormal/ui_context.py` · `backend/tests/abnormal/drivers/ui_drivers.py`

**Interfaces:**
- Consumes: `ButtonLink` · `MenuLinkItem` (Task 2), `paths` (Task 1)
- Produces (`ui_context.py`): `UiContext.follow(page, name, timeout_ms=ACT_TIMEOUT_MS) -> None` · `UiContext.follow_if_present(page, name, role="link") -> bool`

**페이지 prop 은 바꾸지 않는다.** 콜백(`onOpenSecrets` 등)은 그대로 받고, `href` 만 `paths` 에서 얻는다. 콜백이 없으면 지금처럼 조작 자체를 그리지 않는다.

- [ ] **Step 1: 실패하는 검사를 쓴다**

`frontend/tests/NavLinks.test.tsx`:

```tsx
/**
 * 018 §4 — 순수 이동은 링크다.
 *
 * 누르면 다른 화면으로 가기만 하는 조작이 `<a href>` 여야 Cmd·가운데 클릭으로 새 탭을 열고 링크 주소를
 * 복사할 수 있다. 보통 클릭은 지금처럼 콜백을 부른다 — 화면은 라우터를 모른다.
 *
 * 부수효과가 있는 조작(실행 · 녹화)과 비활성 사유를 보여야 하는 조작은 버튼으로 남는다 — 그것도 본다.
 */
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KeyManagement } from "../src/pages/KeyManagement";
import { SecretValues } from "../src/pages/SecretValues";
import { TestList, type TestListProps } from "../src/pages/TestList";
import { LIST } from "./helpers/fakeServer";

const noop = () => undefined;

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const u = String(url);
      if (u.startsWith("/api/tests")) return new Response(JSON.stringify(LIST), { status: 200 });
      if (u === "/api/secrets") {
        return new Response(
          JSON.stringify({ public_key_fingerprint: null, fingerprint_matches_key: true, names: [] }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({}), { status: 200 });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("목록 화면 (018 §4)", () => {
  it.each([
    ["바꾸기", "/projects", "onOpenProjects"],
    ["비밀 값", "/secrets", "onOpenSecrets"],
    ["키 관리", "/keys", "onOpenKeys"],
    ["테스트 만들기", "/tests/new", "onCreate"],
  ] as const)("머리띠의 「%s」는 %s 로 가는 링크다", async (name, href, prop) => {
    const spy = vi.fn();
    const props: TestListProps = {
      projectName: "P",
      onCreate: noop,
      onOpenResult: noop,
      onRun: noop,
      onOpenProjects: noop,
      onOpenSecrets: noop,
      onOpenKeys: noop,
    };
    (props as unknown as Record<string, unknown>)[prop] = spy;
    render(<TestList {...props} />);
    const link = await screen.findByRole("link", { name });
    expect(link.getAttribute("href")).toBe(href);
    act(() => link.click());
    expect(spy).toHaveBeenCalledOnce();
  });

  it("행의 「결과 보기」는 그 테스트의 결과로 가는 링크다", async () => {
    const onOpenResult = vi.fn();
    render(<TestList projectName="P" onCreate={noop} onOpenResult={onOpenResult} onRun={noop} />);
    const link = await screen.findByRole("link", { name: "결과 보기" });
    expect(link.getAttribute("href")).toBe("/tests/TC-001/result");
    act(() => link.click());
    expect(onOpenResult).toHaveBeenCalledWith("TC-001");
  });

  it("행 메뉴의 「편집」은 그 테스트의 편집으로 가는 링크 항목이다", async () => {
    const onOpenDefinition = vi.fn();
    render(
      <TestList
        projectName="P"
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        onOpenDefinition={onOpenDefinition}
      />,
    );
    await userEvent.setup().click(await screen.findByLabelText("로그인 추가 동작"));
    const item = await screen.findByRole("menuitem", { name: "편집" });
    expect(item.tagName).toBe("A");
    expect(item.getAttribute("href")).toBe("/tests/TC-001/edit");
    act(() => item.click());
    expect(onOpenDefinition).toHaveBeenCalledWith("TC-001");
  });

  it("실행은 버튼으로 남는다 — 부수효과가 있는 조작이다", async () => {
    render(<TestList projectName="P" onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByRole("link", { name: "결과 보기" });
    expect(screen.queryByRole("link", { name: /실행/ })).toBeNull();
  });
});

describe("비밀 값 · 키 관리 (018 §4)", () => {
  it("비밀 값의 「키 관리」와 「닫기」는 링크다", async () => {
    const onManageKeys = vi.fn();
    const onClose = vi.fn();
    render(<SecretValues onClose={onClose} onManageKeys={onManageKeys} />);
    const keys = await screen.findByRole("link", { name: "키 관리" });
    const close = screen.getByRole("link", { name: "닫기" });
    expect(keys.getAttribute("href")).toBe("/keys");
    expect(close.getAttribute("href")).toBe("/");
    act(() => keys.click());
    act(() => close.click());
    expect(onManageKeys).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("키 관리의 「닫기」는 목록으로 가는 링크다", async () => {
    const onClose = vi.fn();
    render(<KeyManagement onClose={onClose} />);
    const close = await screen.findByRole("link", { name: "닫기" });
    expect(close.getAttribute("href")).toBe("/");
    act(() => close.click());
    expect(onClose).toHaveBeenCalledOnce();
  });
});
```

`LIST` 의 행(`TC-001` · 「로그인」 · 실패 결과 있음)이 「결과 보기」를 그린다 — `EditEntryPoints` 가 같은 픽스처로 결과 화면에 들어간다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run tests/NavLinks.test.tsx`
Expected: FAIL — `Unable to find role="link" and name "바꾸기"` 등 (아직 버튼이다).

- [ ] **Step 3: `TestList.tsx` 를 고친다**

(a) 가져오기 (74·79행 근처):

```ts
import { Button, ButtonLink } from "../ui/Button";
```

```ts
import { Menu, MenuContent, MenuItem, MenuLinkItem, MenuTrigger } from "../ui/DropdownMenu";
```

그리고 `lib` 가져오기 묶음 옆에:

```ts
import { paths } from "../lib/paths";
```

(b) 머리띠 (517~545행). 세 `Button variant="nav"` 와 주 동작 `Button variant="primary"` 를 바꾼다. 주석은 그대로 둔다:

```tsx
          {onOpenProjects && (
            <ButtonLink variant="nav" href={paths.projects()} onNavigate={onOpenProjects}>
              바꾸기
            </ButtonLink>
          )}
```

```tsx
        {onOpenSecrets && (
          <ButtonLink variant="nav" href={paths.secrets()} onNavigate={onOpenSecrets}>
            비밀 값
          </ButtonLink>
        )}
        {onOpenKeys && (
          <ButtonLink variant="nav" href={paths.keys()} onNavigate={onOpenKeys}>
            키 관리
          </ButtonLink>
        )}
```

```tsx
        <ButtonLink variant="primary" href={paths.compose()} onNavigate={onCreate}>
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.9">
            <path d="M7 2.4v9.2M2.4 7h9.2" />
          </svg>
          테스트 만들기
        </ButtonLink>
```

(닫는 태그가 `</Button>` 이면 `</ButtonLink>` 로 함께 바꾼다.)

`EmptyProject` 안의 「녹화로 시작하기」·「AI 로 시작하기」·「언어모델 키 등록하기」는 **버튼으로 둔다** — 마지막 것은 비활성 사유를 보여야 하고(FR-014), 앞의 둘은 같은 카드 안의 짝이다.

(c) 행의 「결과 보기」 (1299~1303행). `Row` 는 `row.id` 를 안다:

```tsx
        {hasResult && !live && (
          <ButtonLink size="sm" href={paths.result(row.id)} onNavigate={onOpenResult}>
            결과 보기
          </ButtonLink>
        )}
```

(d) 행 메뉴의 「편집」 (1372~1376행). 주석은 그대로 둔다:

```tsx
            {onOpenDefinition && (
              <MenuLinkItem data-row-menu-item href={paths.edit(row.id)} onNavigate={onOpenDefinition}>
                {EDIT_ENTRY_LABEL}
              </MenuLinkItem>
            )}
```

- [ ] **Step 4: `SecretValues.tsx` · `KeyManagement.tsx` 를 고친다**

두 파일 모두 가져오기를 바꾼다:

```ts
import { Button, ButtonLink } from "../ui/Button";
import { paths } from "../lib/paths";
```

(파일이 `Button` 을 더 쓰지 않으면 `ButtonLink` 만 가져온다 — `tsc` 가 알려 준다.)

`SecretValues.tsx` (84~93행):

```tsx
        {onManageKeys && (
          <ButtonLink href={paths.keys()} onNavigate={onManageKeys}>
            키 관리
          </ButtonLink>
        )}
        {onClose && (
          <ButtonLink href={paths.list()} onNavigate={onClose}>
            닫기
          </ButtonLink>
        )}
```

`KeyManagement.tsx` (153~157행):

```tsx
        {onClose && (
          <ButtonLink href={paths.list()} onNavigate={onClose}>
            닫기
          </ButtonLink>
        )}
```

- [ ] **Step 5: 새 검사가 통과하는지 본다**

Run: `cd frontend && npx vitest run tests/NavLinks.test.tsx tests/ButtonLink.test.tsx tests/Routing.test.tsx`
Expected: PASS

- [ ] **Step 6: 역할이 바뀐 조작을 찾는 기존 검사를 고친다**

Run: `cd frontend && npx vitest run 2>&1 | grep -E "FAIL|✗|×" | head -30`

다음 자리는 **반드시** `"button"` 을 `"link"` 로 바꾼다. 특히 「없다」를 확인하는 `queryByRole(… ).toBeNull()` 두 줄은 역할이 바뀌면 **조용히 통과**하므로 실패 목록에 나오지 않는다:

| 파일 | 줄 | 바꾼 뒤 |
|---|---|---|
| `tests/ProjectListReachable.test.tsx` | 67, 84 | `screen.getByRole("link", { name: "바꾸기" })` |
| `tests/RunTrigger.test.tsx` | 230, 238, 247 | `screen.getByRole("link", { name: "결과 보기" })` |
| `tests/RunTrigger.test.tsx` | 261 | `screen.queryByRole("link", { name: "결과 보기" })` |
| `tests/RecheckPhase12.test.tsx` | 360 | `screen.getByRole("link", { name: "결과 보기" })` |
| `tests/RecheckPhase12.test.tsx` | 365 | `screen.queryByRole("link", { name: "결과 보기" })` |

`ProjectListReachable` 67행의 변수 이름은 이미 `link` 다. 위 표 밖에서 실패가 나오면, 그 검사가 **링크가 된 조작**을 버튼으로 찾는지 먼저 본다. 그렇다면 역할만 바꾸고, 아니라면 멈추고 원인을 찾는다.

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: 실패는 알려진 2건뿐.

- [ ] **Step 7: 실브라우저 하니스가 링크를 따라가게 한다**

`backend/tests/abnormal/ui_context.py` — `click` 메서드 바로 아래에 둔다:

```python
    async def follow(self, page: Page, name: str, timeout_ms: int = ACT_TIMEOUT_MS) -> None:
        """링크를 따라간다 (018 — 순수 이동은 `<a href>` 다).

        역할이 `button` 이 아니라 `link` 다. `click` 으로 찾으면 없는 버튼을 기다리다 시간이 다 간다.
        """
        await page.get_by_role("link", name=name, exact=False).first.click(timeout=timeout_ms)

    async def follow_if_present(self, page: Page, name: str, role: str = "link") -> bool:
        """`click_if_present` 의 링크판. 행 메뉴의 링크 항목은 `role="menuitem"` 으로 찾는다.

        예외로 끝내지 않는 이유는 `click_if_present` 와 같다 — 누르지 못한 것은 관측이다.
        """
        target = page.get_by_role(role, name=name, exact=False).first
        if await target.count() == 0:
            return False
        try:
            await target.click(timeout=3_000)
        except PlaywrightTimeout:
            return False
        return True
```

같은 파일에서 세 곳을 바꾼다:

- `open_definition` 의 `opened = await self.click_if_present(page, "편집")` → `opened = await self.follow_if_present(page, "편집", role="menuitem")`. 독스트링 끝에 한 줄을 더한다: `018 부터 「편집」은 링크 항목(\`<a role="menuitem">\`)이다.`
- `open_result` 의 `return await self.click_if_present(page, "결과 보기")` → `return await self.follow_if_present(page, "결과 보기")`
- 녹화 세션을 시작하는 메서드(565행)의 `await self.click(page, "테스트 만들기")` → `await self.follow(page, "테스트 만들기")`. 그 메서드 독스트링의 「화면에는 주소가 없다 — 상태로 화면을 고르므로 세션 화면에 URL 로 들어갈 수 없다.」를 「018 부터 세션 화면에도 주소가 있지만(`/sessions/:id`), 식별자는 여전히 **화면이 실제로 만든** 세션의 응답에서 읽는다.」로 바꾼다.

`backend/tests/abnormal/drivers/ui_drivers.py` — 여섯 곳의 `ctx.click` 을 `ctx.follow` 로 바꾼다:

| 줄 | 지금 | 바꾼 뒤 |
|---|---|---|
| 99 | `await ctx.click(page, "비밀 값")` | `await ctx.follow(page, "비밀 값")` |
| 125 | `await ctx.click(page, "키 관리")` | `await ctx.follow(page, "키 관리")` |
| 161 | `await ctx.click(page, "테스트 만들기")` | `await ctx.follow(page, "테스트 만들기")` |
| 409 | `await ctx.click(page, "키 관리")` | `await ctx.follow(page, "키 관리")` |
| 439 | `await ctx.click(page, "테스트 만들기")` | `await ctx.follow(page, "테스트 만들기")` |
| 569 | `await ctx.click(page, "비밀 값")` | `await ctx.follow(page, "비밀 값")` |

바꾸기 전에 각 줄이 **목록 화면의 머리띠**(또는 비밀 값 화면의 「키 관리」)를 누르는지 주변을 읽어 확인한다. 다른 화면의 같은 이름 버튼(예: 대화상자 안의 「키 관리」)이면 바꾸지 않는다.

- [ ] **Step 8: 실브라우저 검사를 돌려 기준선과 견준다**

```bash
cd backend && uv run ruff check tests/abnormal \
  && uv run pytest -m "browser and not timing" -q -n 2 2>&1 | tail -40
```

Expected: ruff 오류 0. 결과를 `.018-browser-baseline.txt` 와 견준다 — **기준선에 없던 실패는 `test_ui_surface_restore.py::test_result_screen_survives_a_reload` 하나뿐이어야 한다**(주소의 `screen` 파라미터를 본다 — Task 7 에서 고친다). 기준선에서 실패하던 `open_definition` 시나리오가 이제 통과하면 그것은 메뉴 항목을 역할로 제대로 찾게 된 결과다 — Task 7 보고에 적는다.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/pages/TestList.tsx frontend/src/pages/SecretValues.tsx frontend/src/pages/KeyManagement.tsx \
  frontend/tests/NavLinks.test.tsx frontend/tests/ProjectListReachable.test.tsx frontend/tests/RunTrigger.test.tsx \
  frontend/tests/RecheckPhase12.test.tsx backend/tests/abnormal/ui_context.py backend/tests/abnormal/drivers/ui_drivers.py
git commit -m "$(cat <<'EOF'
feat(018): 순수 이동을 링크로 그린다 (T006)

목록 머리띠·행의 결과 보기·행 메뉴의 편집·비밀 값과 키 관리의 이동이 <a href> 가 된다.
Cmd·가운데 클릭으로 새 탭을 열 수 있고, 보통 클릭은 지금처럼 앱 안에서 옮긴다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---
### Task 7: 실제 브라우저로 다시 재고 문서를 닫는다

**Files:**
- Modify: `backend/tests/abnormal/test_ui_surface_restore.py`
- Modify: `scripts/screen_sweep.py`
- Modify: `scripts/design_compare_ba.py`
- Regenerate: `frontend/tests/sweep-report.json` · `frontend/tests/l2-report.json` (스크립트가 쓴다)
- Modify: `README.md` · `specs/005-ux-walkthrough-repair/research.md` · `docs/PENDING-HUMAN-VERIFICATION.md`

**Interfaces:**
- Consumes: 전부 (Task 1~6)
- Produces: 없음

- [ ] **Step 1: 새로고침 복원 검사를 경로형 주소로 고친다**

`backend/tests/abnormal/test_ui_surface_restore.py`:

(a) 가져오기의 `from urllib.parse import parse_qs, urlparse` → `from urllib.parse import urlparse`

(b) `test_result_screen_survives_a_reload` 의 주소 단언 두 묶음을 바꾼다:

```python
    # 주소가 화면을 실었는가. 이것이 없으면 새로고침이 복원할 근거 자체가 없다.
    # 018 — 주소가 경로형이 됐다 (`/tests/{id}/result`).
    before = urlparse(page.url)
    assert before.path == f"/tests/{test_id}/result", (
        f"결과 화면인데 주소가 그것을 말하지 않는다: {page.url}"
    )

    await page.reload(wait_until="domcontentloaded")
    await ui_context.settle(page)

    # 1. 주소가 유지된다. `/` 로 초기화되던 것이 N-01 의 절반이다.
    after = urlparse(page.url)
    assert after.path == before.path, (
        f"새로고침이 주소를 잃었다: {page.url} (이전: {before.geturl()})"
    )
```

(뒤따르는 「2. 화면도 유지된다」 단언은 그대로 둔다.)

(c) `test_reload_on_the_list_stays_on_the_list` 의 단언과 독스트링을 바꾼다:

```python
    """목록에서 새로고침하면 목록이다 — 기본 화면에 아무것도 남기지 않는다.

    복원을 넣다가 **주소에 무엇이든 남기는** 쪽으로 가면 목록이 `/` 가 아니게 되고,
    그때부터 사용자의 북마크와 히스토리가 지저분해진다. 이 단정이 그 방향을 막는다.
    """
```

```python
    here = urlparse(page.url)
    assert here.path == "/" and not here.query, (
        f"목록인데 주소에 무엇이 남았다: {page.url}"
    )
    assert "테스트 만들기" in await ui_context.visible_text(page)
```

(d) 파일 끝에 옛 주소 검사를 더한다:

```python
async def test_an_old_screen_address_still_opens_its_screen(ui_context: UiContext) -> None:
    """005 의 옛 주소로 열어 둔 탭이 018 뒤에도 같은 화면에 닿는다 (018 §6).

    `?screen=result&test=…` 는 005~017 이 주소창에 남긴 모양이다. 사용자의 북마크와 열어 둔 탭에 그대로
    있다. 새 주소로 **교체**되므로 뒤로 가면 옛 주소가 아니라 그 전 화면이다.
    """
    ui_context.ensure_project()
    test_id = only_test(ui_context, "옛 주소로 연다")
    page = await ui_context.open()
    await ui_context.settle(page)

    await page.goto(f"{ui_context.ui.base_url}/?screen=result&test={test_id}", wait_until="domcontentloaded")
    await ui_context.settle(page)

    assert urlparse(page.url).path == f"/tests/{test_id}/result", (
        f"옛 주소가 새 주소로 옮겨지지 않았다: {page.url}"
    )
    assert "SCREENSHOT" in await ui_context.visible_text(page), "옛 주소로 결과 화면이 열리지 않았다"

    await page.go_back(wait_until="domcontentloaded")
    await ui_context.settle(page)
    assert "screen=" not in page.url, f"옛 주소가 기록에 남았다: {page.url}"
```

Run: `cd backend && uv run ruff check tests/abnormal && uv run pytest tests/abnormal/test_ui_surface_restore.py -q -n 0`
Expected: 4 passed

- [ ] **Step 2: 순회 스크립트를 경로형 주소와 링크로 고친다**

`scripts/screen_sweep.py`:

(a) `SCENARIOS` 에서 링크가 된 조작의 역할과, 주소 증거를 바꾼다:

```python
    {"name": "test-create", "phase": OPEN, "policy": "data",
     "steps": [("click_role", "link", "테스트 만들기")], "evidence": [("css", "[data-phase-pill]")],
     "measure": "compose", "expect": {"nlInputWidth": (">=", 240)}},
    {"name": "secrets", "phase": OPEN, "policy": "form",
     "steps": [("click_role", "link", "비밀 값")], "evidence": [("url", "/secrets")]},
    {"name": "keys", "phase": OPEN, "policy": "form",
     "steps": [("click_role", "link", "키 관리")], "evidence": [("url", "/keys")]},
```

(b) `"query": …` 를 전부 `"path": …` 로 바꾸고 값을 경로형으로 바꾼다 (018 — 주소가 질의 문자열이 아니다):

| 화면 | 지금 | 바꾼 뒤 |
|---|---|---|
| `result-pass` | `"query": "?screen=result&test=TC-001"` | `"path": "/tests/TC-001/result"` |
| `result-fail` | `"query": "?screen=result&test=TC-003"` | `"path": "/tests/TC-003/result"` |
| `edit` · `edit-delete-confirm` · `edit-notice` | `"query": "?screen=definition&test=TC-001"` | `"path": "/tests/TC-001/edit"` |
| `edit-long-name` | `"query": "?screen=definition&test=TC-002"` | `"path": "/tests/TC-002/edit"` |
| `edit-step-detail` | `"query": "?screen=definition&test=TC-001&step=step-02"` | `"path": "/tests/TC-001/edit?step=step-02"` |

(c) `capture` 의 `page.goto(ui + sc.get("query", "/"), wait_until="networkidle")` → `page.goto(ui + sc.get("path", "/"), wait_until="networkidle")`. `ui` 는 끝에 `/` 가 없으므로(`start_ui`) `//` 가 생기지 않는다.

Run: `grep -n "query\|screen=" scripts/screen_sweep.py`
Expected: 출력 없음 (자바스크립트 문자열 속의 `querySelector` 는 나와도 된다)

- [ ] **Step 3: L2 대조가 링크를 누르고, 링크의 모습도 계속 재게 한다**

`scripts/design_compare_ba.py`:

(a) `measure` 의 단계 조작(`loc = page.get_by_role("button", …).or_(…radio…)`)에 링크를 더한다:

```python
            # 018 — 순수 이동이 `<a href>` 가 됐다. 전환 전 코드(button)와 뒤 코드(link)를 **같은 단계**로 누른다.
            loc = (
                page.get_by_role("button", name=step["button"], exact=exact)
                .or_(page.get_by_role("radio", name=step["button"], exact=exact))
                .or_(page.get_by_role("link", name=step["button"], exact=exact))
                .first
            )
```

(b) 대조 함수의 짝짓기에서, 버튼이 링크가 된 자리를 **짝지어 계속 잰다.** 지금 코드:

```python
        by_path = {row["path"]: row for row in a}
        for row in b:
            other = by_path.get(row["path"])
            if other is None:
                mismatches.append({"screen": name, "kind": "unpaired", "path": row["path"]})
                continue
            if other["tag"] != row["tag"]:
                mismatches.append(
                    {"screen": name, "kind": "tag", "path": row["path"],
                     "before": row["tag"], "after": other["tag"]}
                )
                continue
```

바꾼 뒤:

```python
        by_path = {row["path"]: row for row in a}
        for row in b:
            other = by_path.get(row["path"])
            if other is None:
                # 018 — 순수 이동이 `<button>` 에서 `<a>` 가 됐다. 자리 번호는 같고 요소 이름만 다르므로 **같은 자리의
                # 링크와 짝짓는다.** 짝을 잃게 두면 그 조작과 안의 요소가 통째로 대조에서 빠진다 — 2026-09-16 에
                # 등록부로 덮었다가 되살린 90 칸(`INTENDED` 끝 주석)과 같은 종류의 손실이다.
                other = by_path.get(re.sub(r"BUTTON\[(\d+)\]", r"A[\1]", row["path"]))
            if other is None:
                mismatches.append({"screen": name, "kind": "unpaired", "path": row["path"]})
                continue
            if other["tag"] != row["tag"]:
                mismatches.append(
                    {"screen": name, "kind": "tag", "path": row["path"],
                     "before": row["tag"], "after": other["tag"]}
                )
                # 버튼 → 링크는 **모습을 계속 잰다** — 요소가 바뀌어도 사람이 보는 것은 같아야 한다.
                if {row["tag"], other["tag"]} != {"BUTTON", "A"}:
                    continue
```

(c) `INTENDED` 끝(마지막 주석 뒤, 닫는 `]` 앞)에 요소 이름 차이만 등록한다:

```python
    # ── 018 — 순수 이동이 링크가 됐다 (design §4) ───────────────────────────────────
    {
        "screens": ["test-list", "test-list-unrun", "test-list-passed", "secrets", "keys"],
        "kinds": ["tag"],
        "reason": (
            "누르면 다른 화면으로 가기만 하는 조작(목록 머리띠의 「바꾸기」·「비밀 값」·「키 관리」·「테스트 만들기」, "
            "행의 「결과 보기」, 비밀 값의 「키 관리」·「닫기」, 키 관리의 「닫기」)이 `<button>` 에서 `ui/Button` 의 "
            "`ButtonLink`(`<a href>`)가 됐다. Cmd·가운데 클릭으로 새 탭을 열고 주소를 복사할 수 있게 하려는 것이다. "
            "**요소 이름만 등록한다** — 대조는 같은 자리의 링크와 짝지어 모습을 계속 재므로, 계산 스타일이 하나라도 "
            "달라지면 `prop` 불일치로 따로 나온다."
        ),
    },
```

**계산 스타일(`prop`) 불일치는 등록하지 않는다.** 나오면 `ButtonLink` 가 버튼과 다르게 그려지는 것이다 — Step 5 에서 고친다.

- [ ] **Step 4: 순회를 다시 돌린다**

```bash
backend/.venv/bin/python scripts/screen_sweep.py
```

Expected: 18화면 × 4폭 순회가 끝나고 `frontend/tests/sweep-report.json` 이 새로 쓰인다. 끝의 요약에 「허용되지 않은 검출 0」·「닿지 못한 화면 0」.

닿지 못한 화면이 있으면 그 화면의 `steps`·`evidence` 가 Step 2 대로 바뀌었는지 본다. 새 검출(덮임·넘침·줄바꿈)이 있으면 **링크가 된 조작**인지 확인하고 `ButtonLink` 를 고친다 — 등록부(`KNOWN`)에 넣지 않는다.

Run: `cd frontend && npx vitest run tests/ScreenSweep.test.ts`
Expected: PASS

- [ ] **Step 5: L2 대조를 다시 돌린다**

```bash
backend/.venv/bin/python scripts/design_compare_ba.py --compare --rebuild
```

`--rebuild` 는 전 쪽 worktree(`.l2-before`)와 빌드를 지금의 `git merge-base main HEAD`(= `e8e3578`, 017 이 머지된 main)에서 다시 만든다. 지난 보고서의 기준(`75520ee`)과 다르므로 017 이 등록한 차이들은 더 나오지 않는다 — 쓰이지 않는 등록 줄은 실패가 아니다.

Expected: `불일치 0건 (의도된 차이 N건 제외)`. `frontend/tests/l2-report.json` 이 새로 쓰인다.

불일치가 남으면 종류별로:
- `kind: "prop"` 이고 자리가 링크가 된 조작(또는 그 안) → `ButtonLink` 의 모양이 버튼과 다르다. 흔한 원인은 `<a>` 의 기본값이다(`box-sizing` · `vertical-align` · `text-decoration`). 원인을 찾아 `ButtonLink` 에 **상자 계산 방식의 유틸리티**만 더하고(모양 값은 더하지 않는다), `ButtonLink.test.tsx` 의 「같은 변종의 버튼과 모양 클래스가 같다」 기대값을 함께 고친 뒤 Step 4 부터 다시 돈다.
- `kind: "unpaired"` 이고 자리가 `BUTTON[…]` → 대조의 짝짓기 변경(Step 3b)이 그 자리를 잡지 못했다. 경로를 출력해 전후를 비교한다.
- 그 밖 → 018 의 변경과 무관하게 달라진 것이다. 멈추고 원인을 찾는다.

Run: `cd frontend && npx vitest run tests/BeforeAfterParity.test.ts`
Expected: PASS (`compared` 가 30000 을 넘는다 — 링크를 짝지으므로 줄지 않는다)

- [ ] **Step 6: 전체 검사 — 이제 실패는 0 이다**

```bash
cd frontend && npx tsc --noEmit && npx vitest run && npm run build
cd ../backend && uv run ruff check . && uv run pytest -m "browser and not timing" -q -n 2 2>&1 | tail -40
```

Expected: 프론트 실패 **0** (알려진 2건이 사라졌다) · 빌드 성공 · 실브라우저 실패는 `.018-browser-baseline.txt` 에 있던 것뿐. 기준선보다 **줄어든** 실패가 있으면 이름을 적어 둔다(보고에 쓴다).

- [ ] **Step 7: 문서를 닫는다**

(a) `specs/005-ux-walkthrough-repair/research.md` — `## R8. 화면 상태의 URL 반영 — 라우터를 새로 넣지 않는다` 제목 바로 아래에 넣는다:

```markdown
> **018 에서 뒤집혔다 (2026-09-17).** 경로형 주소 · 모든 화면의 딥링크 · 링크 기반 이동이 요구되어
> React Router(Data 모드)를 들였다. 옛 `?screen=` 주소는 새 주소로 교체 이동한다 —
> [`specs/018-react-router/design.md`](../018-react-router/design.md).
```

(b) `README.md` — `### 부품 층 전환 (017)` 바로 **위**에 절을 넣는다:

```markdown
### 화면 주소 (018)

**화면마다 주소가 있다 — 새로 고쳐도, 새 탭에 붙여 넣어도 같은 화면이다.**

| 화면 | 주소 |
|---|---|
| 테스트 목록 | `/` |
| 프로젝트 선택 | `/projects` |
| 만들기 (초안에서) | `/tests/new` (`?draft=D-0001`) |
| 편집 · 결과 (지목한 Step) | `/tests/TC-001/edit` · `/tests/TC-001/result` (`?step=…`) |
| 실행 화면 | `/sessions/<세션>` |
| 가져오기 미리보기 | `/import/<계획>` — 새로 고치면 「사라졌습니다」 후 목록 (계획은 서버 메모리에만 있다) |
| 키 관리 · 비밀 값 | `/keys` · `/secrets` |

005 는 라우터 없이 `?screen=result&test=…` 질의 문자열로 새로고침과 뒤로가기만 지켰다(research R8).
018 은 React Router(Data 모드)를 들여 **실행·만들기 화면까지** 주소만으로 되살리고, 화면을 고르던 800줄
`App.tsx` 를 라우트 어댑터로 나눴다. 옛 주소는 새 주소로 교체되므로 열어 둔 탭과 북마크가 끊기지 않는다.

- **일회성 명령은 되살아나지 않는다** — 「이 앞에 추가」·「지시문으로 더하기」로 연 실행 화면은 도착해서 한 번
  수행하고, 새로 고치면 다시 수행하지 않는다.
- **순수 이동은 링크다** — 목록 머리띠 · 「결과 보기」 · 행 메뉴 「편집」 · 비밀 값/키 관리의 이동을 Cmd·가운데
  클릭으로 새 탭에서 연다. 실행·녹화처럼 부수효과가 있는 조작은 버튼이다.

**남은 것**: 새 탭 · 가운데 클릭 · 옛 북마크 같은 사람 판정 (`docs/PENDING-HUMAN-VERIFICATION.md` §18).
편집 중 브라우저 뒤로가기는 지금도 저장 안 한 변경을 묻지 않는다 — 018 범위 밖이다.
```

(c) `docs/PENDING-HUMAN-VERIFICATION.md` — `## 걷기 전에` 바로 **위**에 절을 넣는다:

```markdown
## 18. 018 — 주소와 링크가 사람이 쓰는 대로 동작하는가

**2026-09-17 · [018](../specs/018-react-router/)**

자동 검사가 「되는가」를 본다 — 주소마다 화면(`Routing.test.tsx` 25건) · 링크의 `href` 와 보통 클릭(`NavLinks` ·
`ButtonLink`) · 새로고침 복원과 옛 주소(`test_ui_surface_restore.py`) · 링크의 계산 스타일(L2) · 18화면 × 4폭 순회.
「브라우저가 링크를 링크로 대하는가」는 사람이 본다.

| # | 무엇 | 절차 | 닫히는 조건 | 결과 | 날짜 · 사람 |
|---|---|---|---|---|---|
| R-1 | 새 탭 | 목록에서 「결과 보기」·행 메뉴 「편집」·「비밀 값」을 Cmd(Ctrl)+클릭, 가운데 클릭 | 새 탭에 그 화면이 뜨고, 원래 탭은 목록에 남는다 | | |
| R-2 | 링크 주소 복사 | 「결과 보기」 오른쪽 클릭 → 링크 주소 복사 → 새 창에 붙여 넣기 | 같은 결과 화면 | | |
| R-3 | 옛 북마크 | 017 이전에 저장한 `?screen=definition&test=…&step=…` 주소를 연다 | 편집 화면에 그 Step 이 펼쳐지고 주소가 `/tests/…/edit?step=…` 로 바뀐다 | | |
| R-4 | 실행 화면 새로 고침 | 편집에서 「이 앞에 추가」로 연 실행 화면에서, 기록이 켜진 뒤 새로 고친다 | 기록이 **다시 켜지지 않고**, 끝내면 편집 화면으로 돌아간다 | | |
| R-5 | 가져오기 미리보기 새로 고침 | 엑셀을 골라 미리보기가 뜬 뒤 새로 고친다 | 「가져오기 미리보기가 사라졌습니다」 후 목록 | | |
```

- [ ] **Step 8: 기준선 파일을 지우고 커밋한다**

```bash
rm -f .018-browser-baseline.txt
git add backend/tests/abnormal/test_ui_surface_restore.py scripts/screen_sweep.py scripts/design_compare_ba.py \
  frontend/tests/sweep-report.json frontend/tests/l2-report.json \
  README.md specs/005-ux-walkthrough-repair/research.md docs/PENDING-HUMAN-VERIFICATION.md
git status --short   # 의도하지 않은 파일(.sweep/ · .l2-*)이 스테이징되지 않았는지 본다
git commit -m "$(cat <<'EOF'
test(018): 실제 브라우저로 주소와 링크를 다시 잰다 (T007)

새로고침 복원을 경로형 주소로 보고 옛 주소 교체를 더한다. 순회와 L2 를 다시 떴다 —
L2 는 버튼이 링크가 된 자리를 짝지어 모습을 계속 잰다. README·R8·사람 판정 절을 닫는다.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## 완료 판정

- `cd frontend && npx tsc --noEmit && npx vitest run && npm run build` — 실패 0
- `cd backend && uv run pytest -m "browser and not timing" -q -n 2` — 기준선보다 새로 생긴 실패 0
- `frontend/tests/sweep-report.json` · `frontend/tests/l2-report.json` 이 마지막 커밋의 소스로 잰 것이다 (`ScreenSweep` · `BeforeAfterParity` 통과)
- 개발 서버에서 Task 5 Step 10 의 다섯 확인이 그대로다
