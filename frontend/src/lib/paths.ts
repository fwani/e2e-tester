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
