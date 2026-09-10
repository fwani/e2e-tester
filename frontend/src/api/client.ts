/**
 * REST 클라이언트. contracts/rest-api.md.
 *
 * **명령은 REST, 관찰은 WebSocket.** 이 파일은 명령만 담당한다.
 *
 * 타입은 backend/schema 에서 생성된 것만 쓴다 — 손으로 정의하면 원칙 I 의
 * Cross-language schema duty 를 위반한다.
 */
import type { Category, ErrorBody, ErrorCode } from "../types/generated/error-response";
import type { ManualStep as GeneratedManualStep } from "../types/generated/manual-step";
import type { RunResult } from "../types/generated/run-result";

/**
 * 실행 결과 + 보조 문맥 (005 FR-152).
 *
 * `last_full_run` 은 **부분 실행일 때만** 온다. 부분 실행이 전체 실행 결과를 덮어써서
 * `5 / 7` → `0 / 7` 로 보이던 것이 U-02 였다 — 이제 둘을 함께 보여줄 수 있다.
 */
export interface RunResultView extends RunResult {
  last_full_run?: RunResult | null;
}
import type { Step } from "../types/generated/step";
import type { Test } from "../types/generated/step-dsl";

// ErrorCode·Category 는 backend/src/itb/domain/error.py 에서 생성된다. 손으로 쓰지 않는다.
export type { Category, ErrorBody, ErrorCode } from "../types/generated/error-response";

/**
 * 서버가 계약 형태로 보낸 오류. 메시지를 그대로 사용자에게 보여줄 수 있다.
 *
 * `category` 는 이 오류가 **막은 것**(사용자가 고칠 수 있다)인지 **깨진 것**(할 수 있는
 * 일이 없다)인지를 말한다. 상태 코드로 유추하지 않는다 — 둘은 일대일이 아니다 (003 EC-002).
 * 계약 형태가 아닌 응답(연결 실패 등)은 `code: "UNKNOWN"` 에 `category: "broken"` 이다.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: ErrorCode | "UNKNOWN",
    message: string,
    readonly detail: Record<string, unknown> = {},
    readonly category: Category = "broken",
    readonly nextAction: string = "",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * 화면이 믿는 프로젝트의 경로 (2026-09-10 사용자 보고 1번).
 *
 * 서버는 열린 프로젝트를 **하나만** 들고 있고, 화면은 자기가 어느 프로젝트를 보고 있는지
 * 따로 기억한다. 둘은 갈라질 수 있다 — 프로젝트를 새로 만들면 서버가 즉시 그리로 옮겨
 * 가는데, 화면에서 「계속」 대신 「돌아가기」를 누르면 화면은 이전 프로젝트에 남는다.
 * 그 상태에서 만든 테스트는 **화면이 보여 주는 프로젝트가 아닌 곳에 저장된다.**
 *
 * 그래서 모든 요청이 「내가 믿는 프로젝트」를 함께 말한다. 서버는 다르면 아무 일도 하기
 * 전에 `PROJECT_MISMATCH` 로 거절하고, 여기서 그 프로젝트를 다시 연 뒤 **같은 요청을 한
 * 번** 다시 보낸다. 거절된 요청은 실행되지 않았으므로 다시 보내는 것이 안전하다.
 */
let expectedProjectRoot: string | null = null;

export function setExpectedProjectRoot(root: string | null): void {
  expectedProjectRoot = root;
}

const PROJECT_ROOT_HEADER = "X-ITB-Project-Root";

/**
 * 헤더에 실을 수 있게 경로를 **퍼센트 인코딩**한다.
 *
 * HTTP 헤더 값은 ISO-8859-1 이다. 프로젝트 이름이 한글이면 디렉터리 이름도 한글이고
 * (`storage/paths.py` 의 `slugify` 가 한글을 남긴다 — 사용자가 파일 탐색기에서 자기
 * 프로젝트를 알아볼 수 있어야 하기 때문이다), 그 경로를 그대로 헤더에 넣으면 브라우저가
 * `fetch` 자체를 거절한다:
 *
 *     Failed to read the 'headers' property from 'RequestInit':
 *     String contains non ISO-8859-1 code point.
 *
 * **요청이 나가지도 않는다.** 한글 이름 프로젝트에서는 화면의 모든 조작이 그 자리에서
 * 멈추는 것이고, 실측으로 확인했다 (이상 조작 UI 검증이 잡았다).
 *
 * 서버는 `urllib.parse.unquote` 로 되돌린다 (`api/app.py`).
 */
const encodeRoot = (root: string) => encodeURIComponent(root);

/** 프로젝트를 바꾸는 조작 자체는 대조 대상이 아니다 — 막으면 프로젝트를 옮길 수 없다. */
const isProjectPath = (path: string) => path.startsWith("/api/project");

async function send(path: string, init?: RequestInit): Promise<Response> {
  const guard: Record<string, string> =
    expectedProjectRoot !== null && !isProjectPath(path)
      ? { [PROJECT_ROOT_HEADER]: encodeRoot(expectedProjectRoot) }
      : {};
  return await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...guard, ...(init?.headers ?? {}) },
  });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp = await send(path, init);

  /*
    서버가 다른 프로젝트를 열고 있다. **조용히 맞춘다.** 사용자에게 물을 것이 없다 —
    화면이 보여 주던 프로젝트가 사용자가 뜻한 프로젝트이고, 서버가 거기로 돌아가면 된다.
    한 번만 다시 보낸다: 다시 어긋나면 그것은 다른 문제이고 오류로 보이는 편이 낫다.
  */
  if (resp.status === 409 && expectedProjectRoot !== null && !isProjectPath(path)) {
    const peeked = await resp.clone().text();
    if (apiErrorFromBody(409, peeked).code === "PROJECT_MISMATCH") {
      const reopened = await fetch("/api/project/open", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: expectedProjectRoot }),
      });
      if (reopened.ok) resp = await send(path, init);
    }
  }

  if (resp.status === 204) return undefined as T;

  const text = await resp.text();
  if (!resp.ok) throw apiErrorFromBody(resp.status, text);
  return (text ? JSON.parse(text) : null) as T;
}

/** 실패 응답 본문을 `ApiError` 로 바꾼다. 계약 형태가 아니어도 던질 수 있는 것을 만든다. */
function apiErrorFromBody(status: number, text: string): ApiError {
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null; // 계약 형태가 아닌 본문(HTML 오류 페이지 등)
  }
  const err = (body as { error?: Partial<ErrorBody> } | null)?.error;
  return new ApiError(
    status,
    err?.code ?? "UNKNOWN",
    err?.message ?? `요청이 실패했습니다 (${status}).`,
    (err?.detail ?? {}) as Record<string, unknown>,
    // 계약 형태가 아니면 제품이 스스로를 설명하지 못한 것이므로 "깨진 것" 이다.
    err?.category ?? "broken",
    err?.next_action ?? "화면을 새로 고쳐 다시 시도하세요. 계속 발생하면 서버 로그를 확인하세요.",
  );
}

const get = <T,>(p: string) => request<T>(p);
const post = <T,>(p: string, body?: unknown) =>
  request<T>(p, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
const patch = <T,>(p: string, body: unknown) =>
  request<T>(p, { method: "PATCH", body: JSON.stringify(body) });
const put = <T,>(p: string, body: unknown) =>
  request<T>(p, { method: "PUT", body: JSON.stringify(body) });
// DELETE 에 본문을 실을 수 있게 한다 — 프로젝트를 목록에서 치울 때 `root` 를 보낸다.
const del = <T,>(p: string, body?: unknown) =>
  request<T>(p, {
    method: "DELETE",
    body: body === undefined ? undefined : JSON.stringify(body),
  });

// ─── 프로젝트 ───────────────────────────────────────────────────────────────

export interface ProjectView {
  root: string;
  name: string;
  default_start_url: string;
  browser: "chromium";
  test_id_attribute: string;
  max_tabs: number;
  gitignore_present: boolean;
  secrets_file_present: boolean;
}

/** 도구가 알고 있는 프로젝트 하나. 첫 화면 목록의 항목이다 (DR-002·DR-003). */
export interface ProjectListItem {
  root: string;
  name: string;
  last_opened_at: string;
  origin: "managed" | "external";
  /** 지금 열 수 있는가. 조회 시점에 계산된다 — 파일 시스템은 도구 밖에서 바뀐다. */
  accessible: boolean;
  unavailable_reason: string | null;
}

export interface ProjectListResponse {
  projects: ProjectListItem[];
  /** 레지스트리를 읽지 못했을 때의 사유. 목록 조회 자체는 실패하지 않는다. */
  warning: string | null;
}

/** 삭제 확인 단계가 보여줄 것 (012 FR-411). */
export interface ProjectSummary {
  root: string;
  name: string;
  test_count: number;
  origin: "managed" | "external";
}

/** 휴지통으로 옮긴 결과 (012 · contracts/api-contract.md §2). */
export interface TrashProjectResponse {
  root: string;
  name: string;
  /**
   * 옮겨진 자리. **이 값이 되돌리는 방법 전부다** (FR-410·FR-425).
   * `null` 이면 요청 시점에 이미 없어서 목록에서 빼기만 했다 (FR-420).
   */
  trashed_to: string | null;
  /** 이 삭제로 열린 프로젝트가 닫혔는가 (FR-416). */
  was_open: boolean;
}

export const project = {
  current: () => get<ProjectView>("/api/project"),
  /** 첫 화면 목록. 관리 위치 스캔 ∪ 레지스트리를 최근 연 순으로 준다. */
  list: () => get<ProjectListResponse>("/api/project/list"),
  /**
   * 새 프로젝트. **`path` 를 보내지 않는다** (DR-001) — 사용자는 서버의 실행 경로를
   * 알 수 없다. 도구가 위치를 정하고 응답의 `root` 로 알려 준다.
   */
  create: (body: { name: string; default_start_url: string; test_id_attribute?: string }) =>
    post<ProjectView>("/api/project/create", body),
  /** 사용자가 폴더 선택기로 고른 경로를 연다. 위치를 지정하는 유일한 경로다 (DR-005). */
  open: (path: string) => post<ProjectView>("/api/project/open", { path }),
  /** 목록에서만 치운다. **디스크의 프로젝트는 지우지 않는다** (DR-009). */
  forget: (root: string) => del<void>("/api/project/registry", { root }),
  /**
   * 삭제 확인 단계가 보여줄 것 (012 FR-411). **목록 응답에 싣지 않는다** — 목록을
   * 그리려고 프로젝트 N개를 열어 테스트를 세면 첫 화면이 느려진다.
   */
  summary: (root: string) =>
    get<ProjectSummary>(`/api/project/summary?root=${encodeURIComponent(root)}`),
  /**
   * 표시 이름만 바꾼다 (012 FR-399·FR-400). 디렉터리 경로는 바뀌지 않는다.
   *
   * 응답이 **갱신된 목록 항목 하나**다. 화면은 이것을 그 줄과 바꿔 끼운다 — 목록
   * 전체를 다시 불러오면 편집 중이던 다른 줄의 상태가 날아간다.
   */
  renameProject: (root: string, name: string) =>
    patch<ProjectListItem>("/api/project/name", { root, name }),
  /**
   * 프로젝트를 **휴지통으로 옮긴다** (012 FR-409). 파일을 파괴하지 않는다.
   *
   * `forget` 과 헷갈리면 안 되므로 **`delete` 라는 이름을 쓰지 않는다.** 어느 쪽이
   * 자산을 옮기는 쪽인지 읽는 사람이 헷갈리는 순간, 화면이 잘못된 쪽을 부른다.
   */
  trash: (root: string) => post<TrashProjectResponse>("/api/project/trash", { root }),
};

// ─── 디렉터리 탐색 (DR-005) ─────────────────────────────────────────────────
//
// 브라우저는 임의 절대 경로를 줄 수 없다. 서버가 홈 하위 디렉터리 목록을 그린다.
// **디렉터리만 온다 — 파일 이름은 오지 않는다.**

export interface DirectoryEntry {
  name: string;
  path: string;
  /** 유효한 프로젝트 구조인가. 사용자가 어디를 골라야 하는지 알려 준다. */
  is_project: boolean;
}

export interface BrowseResponse {
  path: string;
  /** 홈 최상위에서는 `null`. 경계 밖으로 올라갈 수 없다. */
  parent: string | null;
  entries: DirectoryEntry[];
}

export const fs = {
  browse: (path?: string) =>
    get<BrowseResponse>(
      path === undefined ? "/api/fs/browse" : `/api/fs/browse?path=${encodeURIComponent(path)}`,
    ),
};

// ─── AI 사용 가능 여부 (DR-021) ─────────────────────────────────────────────
//
// **작성 경로 전용이다.** 재실행 경로는 이것을 읽지 않는다 (원칙 II).
// 자격 증명의 조각은 오지 않는다 — 가능 여부와 안내 문구뿐이다.

export interface AiAvailability {
  available: boolean;
  /** 쓸 수 없을 때 무엇이 준비되지 않았고 무엇을 하면 되는지. */
  reason: string | null;
}

export const ai = {
  availability: () => get<AiAvailability>("/api/ai/availability"),
};

// ─── 테스트 ─────────────────────────────────────────────────────────────────

export interface FailureSummary {
  step_index: number;
  message: string;
}

export interface TestListRow {
  id: string;
  name: string;
  step_count: number;
  authoring_mode: "record" | "ai";
  outcome: "pass" | "fail" | null;
  last_run_at: string | null;
  failure_summary: FailureSummary | null;
  /**
   * 이 테스트가 속한 그룹의 접두어 (013 FR-438). 그룹 없음은 `TC`.
   *
   * **식별자에서 유도한 값이다.** 저장된 필드가 아니다 (013 data-model §3).
   */
  group_prefix: string;
}

/** 목록 위 그룹 띠가 그릴 것 (013 FR-440). */
export interface GroupSummary {
  prefix: string;
  /** 사람이 읽는 이름. 그룹 없음(`TC`)과 **정의가 없는 접두어**는 `null` 이다. */
  name: string | null;
  /** **걸러 보기 전** 개수다 — 걸러 본 뒤에도 다른 그룹으로 갈 수 있어야 한다. */
  count: number;
}

/** 그룹 하나 (013 · contracts/api-contract.md §5). */
export interface TestGroup {
  prefix: string;
  name: string;
  count: number;
}

export const groups = {
  list: () => get<{ groups: TestGroup[] }>("/api/groups"),
  /**
   * 그룹 만들기 (013 FR-444d). **이름과 접두어를 따로 받는다** — 한글 이름을 유지하면서
   * 식별자는 짧게 둔다.
   */
  create: (prefix: string, name: string) =>
    post<TestGroup>("/api/groups", { prefix, name }),
  /** 이름만 바꾼다. **접두어는 바꾸지 않는다** — 그것은 자산을 옮기는 일이다. */
  rename: (prefix: string, name: string) =>
    patch<TestGroup>(`/api/groups/${prefix}`, { name }),
  /**
   * 그룹을 없앤다. **그 안의 테스트는 지우지 않는다** (013 FR-451) — 전부 `TC-###` 로
   * 돌아간다. 묶음을 푸는 것과 자산을 지우는 것은 다른 조작이다.
   */
  remove: (prefix: string) => del<{ ungrouped: string[] }>(`/api/groups/${prefix}`),
};

export interface TestListResponse {
  counts: { total: number; pass: number; fail: number };
  /** 테스트가 **있는** 그룹만 (FR-450). 고르는 자리는 `groups.list()` 를 쓴다. */
  groups: GroupSummary[];
  tests: TestListRow[];
  problems: string[];
}

/** 산출물 종류. `trace` 는 서버가 `501` 을 돌려준다 (spec 디자인 차이 1). */
export type ArtifactKind = "screenshot" | "trace" | "console" | "network";

/** 휴지통으로 간 테스트 하나 (013 · contracts/api-contract.md §2). */
export interface TrashedTest {
  id: string;
  name: string;
  /** 옮겨진 자리. **이 값이 되돌리는 방법 전부다** (FR-437a). */
  trashed_to: string;
}

export const tests = {
  /** 목록. `q`(이름·식별자)와 `group`(접두어)이 **함께** 걸린다 (013 FR-441). */
  list: (q?: string, group?: string) => {
    const query = new URLSearchParams();
    if (q) query.set("q", q);
    if (group) query.set("group", group);
    const suffix = query.toString();
    return get<TestListResponse>(`/api/tests${suffix ? `?${suffix}` : ""}`);
  },
  get: (id: string) => get<Test>(`/api/tests/${id}`),
  rename: (id: string, name: string) => patch<Test>(`/api/tests/${id}`, { name }),
  /**
   * 테스트 하나를 **휴지통으로 옮긴다** (013 FR-437). 파괴하지 않는다.
   *
   * 204 가 아니라 옮겨진 자리를 돌려준다 — 그 값이 되돌리는 방법 전부다.
   */
  remove: (id: string) => del<TrashedTest>(`/api/tests/${id}`),
  /**
   * 여러 개를 한 번에 (013 FR-432). **전부 되거나 전부 안 되거나.**
   *
   * `DELETE` 에 본문을 싣지 않는 이유는 011 이 정했다 — 프록시가 벗기고, 쿼리는 URL
   * 길이와 접근 로그 문제가 있다.
   */
  deleteMany: (ids: string[]) =>
    post<{ deleted: TrashedTest[] }>("/api/tests:delete", { test_ids: ids }),
  /**
   * 그룹을 바꾼다 (013 FR-446·FR-448). **표시가 아니라 자산이 움직인다** — 정의 파일과
   * 실행 산출물이 새 식별자 자리로 간다. 번호는 그대로이고 접두어만 바뀐다.
   */
  move: (ids: string[], toPrefix: string) =>
    post<{ moved: { from_id: string; to_id: string; name: string }[] }>("/api/tests:move", {
      test_ids: ids,
      to_prefix: toPrefix,
    }),
  /**
   * 번호의 빈자리를 없애 `001` 부터 다시 붙인다 (2026-09-10 사용자 보고 2번).
   *
   * **접두어와 상대 순서는 그대로다.** `USER-005` 는 `USER-003` 이 되지 `TC-003` 이
   * 되지 않는다. `move` 와 같은 성질의 조작이다 — 정의 파일과 실행 산출물이 새 식별자
   * 자리로 함께 간다.
   */
  renumber: () =>
    post<{
      renumbered: { from_id: string; to_id: string; name: string }[];
      unchanged: number;
    }>("/api/tests:renumber"),
  /** 최근 실행 결과. 테스트당 1건만 보관된다 (FR-050~FR-054). */
  result: (id: string) => get<RunResultView>(`/api/tests/${id}/result`),
  /**
   * 산출물 주소. 서버가 **바이트**를 돌려주므로 스크린샷은 `<img src>` 에 그대로 넣는다.
   * 예전에는 `{kind, path}` JSON 을 받아 그 상대 경로를 `src` 에 넣었고, 화면에는 깨진
   * 이미지와 경로 문자열만 남았다 (UX U-03).
   */
  artifactUrl: (id: string, kind: ArtifactKind) => `/api/tests/${id}/result/artifacts/${kind}`,
  /**
   * 그 Step 이 끝난 시점의 화면 (011 FR-390 · api-contract §3).
   *
   * **`artifactUrl` 과 갈라 둔다.** 그쪽은 실행 전체에 하나씩인 산출물이고 `kind` 별
   * media type 표가 그 전제 위에 있다. Step 별은 인덱스를 갖는 다른 성질이라 `kind` 에
   * 넣으면 인덱스를 실을 자리가 없다.
   *
   * **인덱스는 0-기반이다** — 저장·API·이벤트와 같다. 화면에 보이는 번호로 바꾸는 것은
   * `stepNumber()` 한 곳뿐이며 여기서 하지 않는다 (FR-138).
   */
  stepScreenshotUrl: (id: string, index: number) =>
    `/api/tests/${id}/result/steps/${index}/screenshot`,
  /** 로그 산출물 본문. 실패는 계약 형태 오류로 온다. */
  artifactText: async (id: string, kind: ArtifactKind): Promise<string> => {
    const resp = await fetch(`/api/tests/${id}/result/artifacts/${kind}`);
    const text = await resp.text();
    if (!resp.ok) throw apiErrorFromBody(resp.status, text);
    return text;
  },
};

// ─── 정의 편집 (006) ────────────────────────────────────────────────────────
//
// **저장 요청은 편집 결과가 아니라 편집 연산 목록이다** (006 research R3). 결과를 보내면
// "어느 Step 종류가 값을 갖는가" 같은 판정이 화면으로 넘어오고, 그것이 규칙의 두 번째
// 구현이 된다. 연산을 보내면 서버의 `step_edits` 가 유일한 구현으로 남는다.

/** 편집 불가 항목의 이유. **문구가 아니라 키다** — 문장은 `lib/wording.ts` 가 만든다. */
export type LockedReason =
  | "live_browser_required"
  | "delete_and_insert_instead"
  | "record_only";

export interface LockedField {
  field: string;
  reason: LockedReason;
}

export interface DefinitionView {
  test: Test;
  /** 정의 파일 내용의 지문. 저장 요청에 되돌려 보낸다 (FR-209). */
  revision: string;
  editable: boolean;
  /** 편집할 수 없는 이유. `null` 이면 편집 가능. */
  blocked_by: "running" | null;
  /** 화면이 「실행 중인 세션 보기」 버튼을 만들기 위한 값 (005 FR-135). */
  blocking_session_id: string | null;
  locked_fields: LockedField[];
  /** 저장을 막지 않는 것들 (FR-216 · 순서 변경 경고). */
  warnings: string[];
}

/**
 * 손으로 넣을 Step 의 서술 (009 FR-286).
 *
 * **종류 목록을 화면이 갖지 않는다.** 생성 타입(`types/generated/manual-step.d.ts`)이
 * 백엔드 `itb/domain/manual_step.py` 에서 나오고, 이것은 그것을 **요청 형태**로 좁힌 것이다.
 *
 * 생성 타입의 필드가 전부 required 인 이유: 그 스키마는 **직렬화** 스키마다(기본값이 채워진
 * 상태를 나타낸다). 요청에서는 `label`·`tab`·`timeout_ms`·`match` 를 생략할 수 있고 그때
 * 서버가 정본 기본값을 쓴다 — 화면이 기본값을 복제하면 두 곳에서 갈린다.
 */
export type ManualStepSpec =
  | { kind: "navigate"; url: string; label?: string; tab?: number; timeout_ms?: number }
  | { kind: "close_tab"; label?: string; tab?: number; timeout_ms?: number }
  | {
      kind: "assert_url";
      url: string;
      match?: MatchMode;
      label?: string;
      tab?: number;
      timeout_ms?: number;
    }
  | {
      kind: "assert_text";
      value: string;
      match?: MatchMode;
      label?: string;
      tab?: number;
      timeout_ms?: number;
    };

/**
 * 손으로 넣을 수 있는 종류. **생성 타입에서 파생한다** (009 FR-286 · T062).
 *
 * 이전 판은 위의 손으로 쓴 `ManualStepSpec` 에서 파생했다. 그러면 백엔드가 다섯째 종류를
 * 더해도 화면은 모르고 **아무 검사도 실패하지 않는다** — FR-286 이 요구하는 「한 곳만
 * 고쳐 반영된다」가 성립하지 않는다.
 *
 * 이제 `types/generated/manual-step.d.ts` 가 근원이고, 그 파일은
 * `backend/src/itb/domain/manual_step.py` 에서 나온다. CI 의 스키마 드리프트 잡이 생성물이
 * 커밋된 것과 같은지 확인하므로, 백엔드에서 종류가 늘면 생성 타입이 늘고 아래 `_Exhaustive`
 * 가 **컴파일에서** 터진다.
 */
export type InsertableKind = GeneratedManualStep["kind"];

/**
 * 참이어야 하는 타입 조건. `Assert<false>` 는 **컴파일되지 않는다.**
 *
 * 조건 타입을 그냥 선언만 하면 아무 오류도 나지 않는다 — 쓰이지 않는 타입 별칭은 검사받지
 * 않기 때문이다. 그래서 조건을 이 형태로 **소비한다.** 런타임 산출물은 없다.
 */
type Assert<T extends true> = T;

/**
 * 요청 타입의 종류 집합이 생성 타입과 **같은지** 컴파일 시점에 못박는다 (FR-286).
 *
 * 두 방향을 모두 본다.
 *
 *   생성에만 있다 → 백엔드가 종류를 늘렸는데 화면이 모른다 (FR-286 이 없애려는 것)
 *   요청에만 있다 → 화면이 서버가 모르는 종류를 보낸다 (422 로 거절된다)
 *
 * 어느 쪽이든 컴파일이 멈춘다. 실측으로 확인했다 — 요청 타입에서 `close_tab` 을 빼면
 * 네 곳에서 타입 오류가 난다.
 */
type _KindsMatch = Assert<
  [Exclude<ManualStepSpec["kind"], GeneratedManualStep["kind"]>] extends [never]
    ? [Exclude<GeneratedManualStep["kind"], ManualStepSpec["kind"]>] extends [never]
      ? true
      : false
    : false
>;
/** 위 단언을 내보내 「쓰이지 않는 타입」으로 지워지지 않게 한다. */
export type ManualStepKindsAreExhaustive = _KindsMatch;

/** 편집 연산 하나. 이 목록의 길이가 곧 「저장할 변경 건수」다 (FR-189). */
export type EditOp =
  /**
   * 009 FR-285 — 목록의 `at` 위치 **앞**에 넣는다.
   *
   * 위치는 저장 직전에 **미리보기 목록 기준으로** 확정한다 (research R7). 미저장 상태에서
   * 삽입 → 순서 변경 → 삭제가 이어지면 정수 위치가 가리키는 곳이 앞선 연산에 따라 바뀐다.
   */
  | { op: "insert"; at: number; spec: ManualStepSpec }
  | {
      op: "update";
      step_id: string;
      label?: string;
      value?: string;
      timeout_ms?: number;
      tab?: number;
      url?: string;
      assertion_value?: string;
      /** 올릴 파일의 이름 — `upload` Step 만 갖는다 (2026-09-09) */
      file_name?: string;
    }
  | { op: "delete"; step_id: string }
  | { op: "reorder"; order: string[] }
  | { op: "set_name"; name: string }
  | { op: "set_start_url"; url: string };

export const definition = {
  /** 편집을 위한 조회. **브라우저를 만들지 않는다** (FR-182). */
  get: (testId: string) => get<DefinitionView>(`/api/tests/${testId}/definition`),
  /** 편집 저장. 응답의 새 `revision` 을 받아 다음 저장에 쓴다 — 다시 조회하지 않는다. */
  save: (testId: string, revision: string, edits: EditOp[]) =>
    put<DefinitionView>(`/api/tests/${testId}/definition`, { revision, edits }),
};

// ─── 세션 ───────────────────────────────────────────────────────────────────

export type SessionState =
  | "starting"
  | "recording"
  | "replaying"
  | "ai_running"
  | "ai_blocked"
  | "takeover_recording"
  | "paused"
  | "completed"
  | "failed"
  /** 중지 후 검토. **종료 상태가 아니다** — 편집·저장을 받는다 (DR-010). */
  | "review"
  | "stopped"
  | "lost";

/**
 * 실행 속도 (004 FR-102). 값과 간격의 대응표는 **서버가 갖는다** —
 * `pacing_changed` 이벤트가 `delay_ms` 와 `auto_pause` 를 함께 실어 보낸다.
 * 화면이 대응표를 복제하면 서버와 갈린다.
 */
export type RunPacing = "fast" | "normal" | "slow" | "step";

/** 화면 표기. 값 → 이름은 표기일 뿐이라 여기 둬도 서버와 갈리지 않는다. */
export const PACING_LABEL: Record<RunPacing, string> = {
  fast: "빠름",
  normal: "보통",
  slow: "느림",
  step: "한 스텝씩",
};

export const PACING_ORDER: RunPacing[] = ["fast", "normal", "slow", "step"];

export interface PreferencesView {
  run_pacing: RunPacing;
  /** 설정을 읽지 못한 사유. **조회 자체는 실패하지 않는다.** */
  warning: string | null;
}

export interface SessionView {
  session_id: string;
  state: SessionState;
  state_label: string;
  test_id: string | null;
  /**
   * 저장된 테스트의 이름 (011 FR-362). 아직 저장된 적 없으면 `null`.
   *
   * **`test_id` 와 갈라서 갖는다.** 화면은 「이름이 이미 있는가」로 저장 라벨과 이름
   * 요구를 정하는데(UC-011-4), id 만 알면 그 이름을 보여 줄 수도 다시 저장할 때 실을
   * 수도 없다 — 011 이전에 국면 띠가 이름 자리에 「TC-001」을 그리고 있었다.
   */
  test_name?: string | null;
  /**
   * 저장한 뒤 **더해진** Step 의 id (011 FR-379).
   *
   * `has_unsaved_changes` 는 「무언가 달라졌는가」 한 값이고, 이것은 **어느 행이** 아직
   * 파일에 없는지다. 세션에서는 서버만 그것을 안다 — 저장 시점의 목록을 들고 있는 곳이
   * 거기다.
   */
  unsaved_step_ids?: string[];
  current_step_index: number;
  steps: Step[];
  tabs_open: number;
  active_tab_index: number;
  mirrored_tab_index: number;
  /** 지금 조작이 어디서 이루어지는가 (010 FR-349). 새로 고쳐도 잃지 않는다 */
  control_surface?: ControlSurfaceValue;
  /**
   * 실제 창으로 옮겨 갈 수 없는 이유. 옮겨 갈 수 있으면 `null` (010 FR-351).
   *
   * **문장을 서버가 준다.** 화면이 같은 뜻의 문구를 따로 가지면 서버가 거절할 때 쓰는
   * 문장과 갈린다 (`wording.ts` 의 O13 옆 주석).
   */
  window_unavailable_reason?: string | null;
  edit_warnings: string[];
  recorder_warnings: string[];
  allowed_commands: string[];
  /** 저장하지 않은 편집이 있는가. 중지 확인의 근거다 (FR-042). */
  has_unsaved_changes: boolean;
  /**
   * 어떻게 만드는 세션인가. **세션의 불변 속성이다.**
   *
   * 화면이 AI 세션 여부를 `state` 로 판정하면 AI 가 실패해 `paused` 로 바뀌는 순간
   * 실패 사유가 사라진다 — 001 의 "AI 로 만들기 무반응" 이 그것이다 (research R2).
   */
  authoring_mode: "record" | "ai";
  /**
   * 이 세션의 실행 속도 (004).
   *
   * `paused` 의 **문구를 가르는 유일한 근거**다. 자동 일시정지(`한 스텝씩`)와 사용자가
   * 직접 누른 일시정지는 상태가 같고 의미가 다르다 — 상태로는 구별할 수 없다.
   */
  pacing: RunPacing;

  /**
   * 이 세션에서 지금까지 확정된 Step별 결과 (005 FR-171).
   *
   * **이벤트 없이도 화면이 복원되게 하는 것이 목적이다.** 이전에는 Step별 결과가
   * WebSocket 이벤트로만 채워지는 컴포넌트 로컬 상태에 있어, 화면을 다시 그리면
   * 모든 Step 이 빈 체크박스가 됐다 (U-18). 같은 뿌리가 U-05 의 "실패한 Step 이
   * 화면에서 지워지는" 증상이다.
   */
  step_results?: StepProgress[];

  /**
   * **아직 도달하지 않은** 목표 지점 (009 FR-293·FR-294 · 계약 §4-3).
   *
   * 「이 앞에 추가」가 만든 세션은 지정한 Step 앞에서 멈춘다. 도달하면 `null` 이 된다 —
   * 값의 뜻이 하나다: `null` 이 아니면 아직 그 자리에 닿지 않았다.
   *
   * `step_results` 와 **같은 이유로** 여기 있다. 목표를 화면 상태로만 들고 있으면 새로
   * 고침 한 번에 「어디서 멈출 예정인지」가 사라진다 (005 U-18).
   */
  pause_before_index?: number | null;

  /**
   * 일시정지가 **실제로** 걸렸는가 (005 FR-142).
   *
   * `false` 면 요청은 갔지만 아직 Step 경계에 닿지 않은 전이 중이다. 이전 화면은
   * 요청 즉시 `PAUSED` 라고 말했는데 실제로는 19초를 더 돌았다 (U-04).
   */
  pause_settled?: boolean;

  /** 현재 실행의 범위 (005 FR-152). */
  run_scope?: "full" | "partial";

  /** 현재 실행이 시작한 Step (005 FR-149·FR-150). 0-기반. */
  run_start_index?: number;

  /** 마지막 저장 시각 (005 FR-154). `null` 이면 미저장 — U-09 가 이것이었다. */
  saved_at?: string | null;
}

/** 화면 복원에 필요한 최소 Step 결과 (005 FR-171). */
export interface StepProgress {
  step_id: string;
  outcome: "pass" | "fail" | "skipped" | "not_run";
  duration_ms: number;
}

export interface TabView {
  tab_index: number;
  url: string;
  title: string;
  closed: boolean;
}

export interface TabsResponse {
  tabs: TabView[];
  active_tab_index: number;
  mirrored_tab_index: number;
  max_tabs: number;
}

export interface StepsResponse {
  steps: Step[];
  edit_warnings: string[];
  current_step_index: number;
}

/** 검증 조건 4종 (FR-013a). 요소 갯수·입력값 검증은 범위 외 (FR-013c). */
export type AssertionKind = "visible" | "hidden" | "text" | "url";
export type MatchMode = "equals" | "contains";

export interface AddAssertionBody {
  kind: AssertionKind;
  /** 대상 요소. **후보 수집은 제품이 한다** — 클라이언트는 셀렉터만 준다 (원칙 IV). */
  target_selector?: string | null;
  value?: string | null;
  match?: MatchMode;
  label?: string | null;
  at?: number | null;
  tab?: number | null;
}

/**
 * AI 실패 시 선택지 (FR-071~FR-074 + `answer`).
 *
 * 2026-09-10 에 `answer` 가 더해져 다섯이 됐다 — 「대화를 통해서 답변을 하거나 인터뷰로
 * 답변을 하고, 그러면 다시 AI 가 테스트 스텝을 생성하거나 수정한다」 (사용자 결정).
 */
export type AiChoice = "takeover" | "answer" | "retry" | "skip" | "abort";

export interface AiStepResponse {
  created: boolean;
  message: string;
  step_id: string | null;
  steps: Step[];
  current_step_index: number;
  state: SessionState;
}

/** 다시 집을 대상. `drag` 만 두 번째 값을 쓴다 (T166). */
export type RepickSlot = "target" | "drop_target";

export interface RepickResponse extends StepsResponse {
  waiting: boolean;
  slot: RepickSlot;
  message: string;
}

export interface SessionListResponse {
  sessions: SessionView[];
}

/** 조작 위치 (010 data-model §6). `mirror` 가 기본이고 `window` 는 폴백이다. */
export type ControlSurfaceValue = "mirror" | "window";

export interface ControlSurfaceResponse {
  surface: ControlSurfaceValue;
}

/** 업로드된 파일 하나 (010 data-model §5). `fileId` 는 **서버가 발급한다.** */
export interface UploadedFileView {
  file_id: string;
  display_name: string;
  size: number;
}

export const sessions = {
  /** 살아 있는 세션 전부. 새로고침으로 놓친 세션을 되찾는 길이다 (UX U-05). */
  list: () => get<SessionListResponse>("/api/sessions"),
  create: (body: {
    mode: "record" | "replay" | "ai";
    test_id?: string | null;
    start_url?: string | null;
    ai_instruction?: string | null;
    /** 생략하면 저장된 취향, 그것도 없으면 서버 기본값 (FR-109). */
    pacing?: RunPacing;
    /**
     * 편집을 위해 멈출 지점 (006 FR-200·FR-201). `replay` 모드에서만 쓴다.
     *
     * 선행 Step 을 실행한 뒤 이 인덱스의 Step 을 실행하기 **전에** 멈춘다. 이것이
     * 없으면 사용자는 편집 상태에 닿기 위해 달리는 실행을 「일시정지」로 잡아야 했고,
     * 빠르게 통과하는 테스트에서는 잡을 창이 사실상 없었다 (006 E-06).
     */
    pause_before_index?: number;
  }) => post<SessionView>("/api/sessions", body),
  get: (id: string) => get<SessionView>(`/api/sessions/${id}`),
  /**
   * 실행 속도 변경 (FR-103). **실행 중에도 부를 수 있다** — 진행 중인 Step 을 끊지
   * 않고 다음 Step 경계부터 적용된다.
   */
  setPacing: (id: string, pacing: RunPacing) =>
    post<SessionView>(`/api/sessions/${id}/pacing`, { pacing }),
  pause: (id: string) => post<SessionView>(`/api/sessions/${id}/pause`),
  /**
   * 이어서 실행 (FR-038).
   *
   * `skipFailed` 는 **실패한 Step 을 건너뛰고** 다음 Step 부터 이어가는 별도 경로다
   * (005 FR-137 · rest-api.md §3-b). 붙이지 않으면 실패 Step 이 있는 재개는 409
   * `CANNOT_RESUME_PAST_FAILURE` 로 거절된다 — 조용히 지나가지 않는 것이 요구사항이다.
   *
   * 본문을 아예 보내지 않는 기존 동작을 유지한다: `skip_failed=false` 와 같으므로
   * 필드를 항상 실으면 계약은 같지만 요청 로그가 달라져 회귀를 읽기 어려워진다.
   */
  resume: (id: string, skipFailed = false) =>
    post<SessionView>(
      `/api/sessions/${id}/resume`,
      skipFailed ? { skip_failed: true } : undefined,
    ),
  runFrom: (id: string, stepIndex: number) =>
    post<SessionView>(`/api/sessions/${id}/run-from`, { step_index: stepIndex }),
  recordActionsStart: (id: string) =>
    post<SessionView>(`/api/sessions/${id}/record-actions:start`),
  recordActionsStop: (id: string) =>
    post<SessionView>(`/api/sessions/${id}/record-actions:stop`),
  /**
   * 중지 — **브라우저만 정리한다.** 세션은 `review` 로 남아 Step 을 계속 보고 저장할
   * 수 있다 (DR-010·DR-013). 001 은 여기서 세션을 파괴해 이후 저장이 불가능했다.
   */
  stop: (id: string) => post<SessionView>(`/api/sessions/${id}/stop`),
  /** 검토 중인 초안을 버린다. **여기서 비로소 세션이 파괴된다** (DR-014). */
  discard: (id: string) => post<void>(`/api/sessions/${id}/discard`),
  /**
   * 테스트로 저장한다. `group` 은 **아직 저장되지 않은 세션에만** 뜻이 있다 (013 FR-443) —
   * 이미 저장된 테스트의 그룹을 바꾸는 것은 `tests.move` 가 원자성 규약과 함께 한다.
   */
  save: (id: string, name: string, group?: string | null) =>
    post<SavedTestView>(`/api/sessions/${id}/save`, group ? { name, group } : { name }),
  tabs: (id: string) => get<TabsResponse>(`/api/sessions/${id}/tabs`),
  setMirrorTab: (id: string, tabIndex: number) =>
    post<TabsResponse>(`/api/sessions/${id}/mirror-tab`, { tab_index: tabIndex }),
  /**
   * 조작 위치를 옮긴다 (010 FR-349·FR-353 · contracts/mirror-control.md §3).
   *
   * **사용자 요청으로만 일어난다.** 서버가 상황을 판단해 스스로 창을 열지 않는다 —
   * 요청하지 않은 창은 그 자체로 조작 위치를 잃게 만들고, 화면 없는 기계에서는 자동
   * 전환이 실패한다 (FR-353).
   *
   * 창을 띄울 수 없는 환경이면 **사유와 함께 거절된다** (FR-351). 조용히 실패하지 않는다.
   */
  setControlSurface: (id: string, surface: ControlSurfaceValue) =>
    post<ControlSurfaceResponse>(`/api/sessions/${id}/control-surface`, { surface }),
  /**
   * 브라우저 요구에 답한다 (010 FR-338 · contracts §3).
   *
   * 이미 해소된 요구나 다른 세션의 `promptId` 는 서버가 거절한다 (FR-340).
   */
  answerPrompt: (
    id: string,
    promptId: string,
    body: { accept: boolean; text?: string; file_ids?: string[] },
  ) => post<void>(`/api/sessions/${id}/prompts/${promptId}`, body),
  /**
   * 사용자가 자기 기계에서 고른 파일을 올린다 (010 FR-337).
   *
   * **제품이 도는 기계의 경로를 사용자가 입력하는 방식이 아니다.** 그러면 화면 없는
   * 원격 기계에서 파일 첨부 녹화가 성립하지 않는다 (SC-518).
   *
   * 상한을 넘으면 서버가 **사유와 함께** 거절한다 (FR-337a). 자르지 않는다.
   */
  uploadFile: async (id: string, file: File): Promise<UploadedFileView> => {
    const form = new FormData();
    form.append("file", file);
    // `request` 를 쓰지 않는다 — 그것은 `Content-Type: application/json` 을 붙이고,
    // multipart 요청에 그 헤더가 붙으면 경계 문자열이 사라져 서버가 본문을 읽지 못한다.
    // 브라우저가 `FormData` 에 맞는 헤더를 스스로 붙이게 둔다.
    const response = await fetch(`/api/sessions/${id}/files`, { method: "POST", body: form });
    const text = await response.text();
    if (!response.ok) throw apiErrorFromBody(response.status, text);
    return JSON.parse(text) as UploadedFileView;
  },
  deleteStep: (id: string, stepId: string) =>
    del<StepsResponse>(`/api/sessions/${id}/steps/${stepId}`),
  /**
   * 여러 Step 을 **한 번에** 지운다 (011 FR-382·FR-388 · api-contract §1).
   *
   * `deleteStep` 을 반복하지 않는다 — 중간에 끊기면 부분 적용이 남는다. 서버가 검증 →
   * 새 목록 구성 → 교체 순으로 처리하므로 「셋 중 둘만 지워진 채 오류」가 되지 않는다.
   *
   * **단건은 그대로 남는다.** 한 개를 지우는 행 조작이 그것을 쓰고, 배치로 대체하면
   * 한 개 삭제가 더 비싸진다.
   */
  deleteSteps: (id: string, stepIds: string[]) =>
    post<StepsResponse>(`/api/sessions/${id}/steps:delete`, { step_ids: stepIds }),
  reorderSteps: (id: string, order: string[]) =>
    post<StepsResponse>(`/api/sessions/${id}/steps:reorder`, { order }),
  /** Step 삽입. `at` 을 생략하면 일시정지 위치다 (FR-035). */
  /**
   * 완성된 Step 을 통째로 넣는다. 리코더·AI 컴파일러가 만든 것을 위한 입구다.
   *
   * 사람이 손으로 넣는 것은 `insertStepManual` 이다 — 그쪽은 요소를 요구하는 종류를
   * **요청 모델 단계에서** 거절한다 (009 research R2).
   */
  insertStep: (id: string, step: unknown, at?: number) =>
    post<StepsResponse>(`/api/sessions/${id}/steps`, { step, at: at ?? null }),
  /** 일시정지 중 직접 입력으로 Step 추가 (009 FR-290). `at` 을 생략하면 일시정지 위치다. */
  insertStepManual: (id: string, spec: ManualStepSpec, at?: number) =>
    post<StepsResponse>(`/api/sessions/${id}/steps:manual`, { spec, at: at ?? null }),
  /** 표시 이름·입력값·타임아웃·민감 여부 수정 (FR-035·FR-082b). */
  patchStep: (
    id: string,
    stepId: string,
    body: {
      label?: string;
      value?: string;
      timeout_ms?: number;
      sensitive?: boolean;
      /** 올릴 파일의 이름 — `upload` Step 만 갖는다 (2026-09-09) */
      file_name?: string;
    },
  ) => patch<StepsResponse>(`/api/sessions/${id}/steps/${stepId}`, body),
  /** 검증 Step 추가 (FR-037·FR-013a). */
  addAssertion: (id: string, body: AddAssertionBody) =>
    post<StepsResponse>(`/api/sessions/${id}/assertions`, body),
  /**
   * "다시 집기" (FR-020). `selector` 를 생략하면 브라우저에서 클릭할 때까지 대기한다 —
   * 그 클릭은 Step 으로 기록되지 않는다.
   */
  /**
   * AI 실패 시 선택 (FR-071~FR-074 + `answer`). `AI_BLOCKED` 에서만 받는다.
   *
   * `answer` 는 `choice="answer"` 에서만 실린다 — 다른 선택지에 실어 보내면 서버가
   * 거절한다. 조용히 버리면 사용자는 자기가 쓴 문장이 AI 에게 갔다고 믿는다.
   */
  aiChoice: (id: string, choice: AiChoice, answer?: string) =>
    post<SessionView>(`/api/sessions/${id}/ai-choice`, {
      choice,
      ...(choice === "answer" ? { answer } : {}),
    }),
  /**
   * 일시정지 중 자연어로 Step 하나 추가 (FR-078).
   *
   * 대상을 찾지 못하면 `created: false` 와 사유가 온다 — 실패해도 일시정지 상태가
   * 유지된다 (FR-081).
   */
  aiStep: (id: string, instruction: string) =>
    post<AiStepResponse>(`/api/sessions/${id}/ai-step`, { instruction }),
  repick: (id: string, stepId: string, body: { slot?: RepickSlot; selector?: string }) =>
    post<RepickResponse>(`/api/sessions/${id}/steps/${stepId}/repick`, {
      slot: body.slot ?? "target",
      selector: body.selector ?? null,
    }),
};

// ─── 비밀 값·키 ─────────────────────────────────────────────────────────────

export interface KeyStatus {
  private_key_present: boolean;
  public_key_present: boolean;
  passphrase_protected: boolean;
  public_key_fingerprint: string | null;
  permission_warning: string | null;
  /** 키가 실제로 놓인 곳. 화면은 고정 문구 대신 이것을 찍는다 (UX U-09). */
  key_dir: string;
  /** 지금 키로 봉인된 값을 가진 프로젝트 이름들 — 키 교체·삭제의 실제 영향 범위. */
  sealed_projects: string[];
  /**
   * 지금 이 백엔드가 비밀키를 열 수 있는가 (FR-089e-3). 암호구가 없는 키는 항상 true.
   * false 면 민감 변수를 쓰는 실행이 실패한다 — 화면이 미리 잠금 해제를 안내한다.
   */
  unlocked: boolean;
}

export interface SecretsResponse {
  public_key_fingerprint: string | null;
  fingerprint_matches_key: boolean;
  names: { name: string; present: boolean }[];
}

/** 되돌릴 수 없는 키 조작의 확인 문구. 서버의 `DESTROY_CONFIRM` 과 같은 값이다. */
export const DESTROY_CONFIRM = "DELETE";

export interface DestroyKeyResult {
  status: KeyStatus;
  purged_secret_count: number;
  project_open: boolean;
}

export const secrets = {
  keyStatus: () => get<KeyStatus>("/api/keys/status"),
  generateKey: (passphrase?: string) =>
    post<KeyStatus>("/api/keys/generate", { passphrase: passphrase ?? null }),
  /** 키를 지운다. 봉인된 값도 함께 사라진다 — 호출 전에 사용자 확인을 받는다. */
  destroyKey: () =>
    del<DestroyKeyResult>("/api/keys", { confirm: DESTROY_CONFIRM, passphrase: null }),
  /** 지우고 다시 만드는 것을 한 번의 확인으로 묶는다. */
  regenerateKey: (passphrase?: string) =>
    post<DestroyKeyResult>("/api/keys/regenerate", {
      confirm: DESTROY_CONFIRM,
      passphrase: passphrase ?? null,
    }),
  /**
   * 암호구로 잠긴 비밀키를 이 백엔드 프로세스에서 연다 (FR-089e-3).
   *
   * **암호구는 여기서만 오간다.** 응답에 담기지 않고 디스크에도 쓰이지 않는다 — 백엔드를
   * 다시 띄우면 잠기고, 그때 다시 해제한다.
   */
  unlockKey: (passphrase: string) => post<KeyStatus>("/api/keys/unlock", { passphrase }),
  /** 들고 있던 암호구를 버린다. 되돌릴 수 없는 조작이 아니라 확인 문구를 받지 않는다. */
  lockKey: () => del<KeyStatus>("/api/keys/unlock"),
  list: () => get<SecretsResponse>("/api/secrets"),
  /** 값은 응답에 없다. 공개키만으로 봉인한다 (FR-089b). */
  put: (name: string, value: string) =>
    request<void>(`/api/secrets/${name}`, { method: "PUT", body: JSON.stringify({ value }) }),
  remove: (name: string) => del<void>(`/api/secrets/${name}`),
};

// ─── 사용자 취향 (004) ──────────────────────────────────────────────────────

export const preferences = {
  get: () => get<PreferencesView>("/api/preferences"),
  put: (runPacing: RunPacing) =>
    put<PreferencesView>("/api/preferences", { run_pacing: runPacing }),
};

export const health = () =>
  get<{ status: string; bind: string; project_open: boolean; active_sessions: number }>(
    "/api/health",
  );

/* ─── 엑셀 통로 (014) ────────────────────────────────────────────────────── */

export interface SheetRenameView {
  group_name: string;
  sheet_name: string;
  reason: string;
}

export interface TruncationView {
  test_id: string;
  column: string;
  kept_lines: number;
  dropped_lines: number;
}

export interface ExportWarningsView {
  sheet_renames: SheetRenameView[];
  truncations: TruncationView[];
  unreadable: string[];
  test_count: number;
  sheet_count: number;
}

/**
 * `Content-Disposition` 에서 파일 이름을 읽는다.
 *
 * 서버는 ASCII 대체 이름(`filename=`)과 RFC 5987 이름(`filename*=UTF-8''…`)을 **둘 다**
 * 싣는다 (014 research R9). 한글 이름을 살리려면 후자를 먼저 본다 — 전자는 한글이
 * 떨어져 나간 나머지다.
 */
export function filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const extended = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (extended) {
    try {
      return decodeURIComponent(extended[1] ?? "") || fallback;
    } catch {
      /* 인코딩이 깨졌으면 아래 ASCII 이름으로 떨어진다 */
    }
  }
  const plain = /filename="([^"]*)"/i.exec(header);
  return plain?.[1] || fallback;
}

/**
 * 받은 바이트를 사용자의 다운로드로 넘긴다.
 *
 * 이 저장소의 **첫 파일 내려받기**다. `<a href="/api/export">` 로 끝내지 않는 이유는,
 * 그러면 `X-ITB-Project-Root` 헤더가 붙지 않아 서버의 프로젝트 대조를 지나칠 수 없기
 * 때문이다 — 화면이 보여 주는 프로젝트와 서버가 연 프로젝트가 다를 때 조용히 남의 것을
 * 받게 된다.
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export const excel = {
  /** 프로젝트를 워크북으로 내려받는다. 파일 이름은 서버가 정한다. */
  exportProject: async (): Promise<{ blob: Blob; filename: string; warnings: number }> => {
    const resp = await send("/api/export");
    if (!resp.ok) throw apiErrorFromBody(resp.status, await resp.text());
    const filename = filenameFromDisposition(
      resp.headers.get("Content-Disposition"),
      "itb-export.xlsx",
    );
    const warnings = Number(resp.headers.get("X-ITB-Export-Warnings") ?? 0);
    return { blob: await resp.blob(), filename, warnings };
  },

  /** 내보내면 무엇이 바뀌는지 미리 본다. 파일을 만들지 않는다. */
  warnings: () => get<ExportWarningsView>("/api/export/warnings"),
};

/* ─── 가져오기와 초안 (014) ──────────────────────────────────────────────── */

export interface RenumberedRow {
  row: number;
  from: string;
  to: string;
}

export interface SkippedRow {
  sheet_name: string;
  row: number;
  reason: "no_title" | "no_columns" | "empty";
}

export interface SheetPlanView {
  sheet_name: string;
  prefix: string | null;
  prefix_source: "from_rows" | "user_supplied" | "ungrouped" | null;
  needs_prefix: boolean;
  group_name: string | null;
  existing_group_name: string | null;
  name_differs: boolean;
  row_count: number;
  renumbered: RenumberedRow[];
}

export interface ImportPlanView {
  plan_id: string;
  file_name: string;
  expires_at: string;
  draft_count: number;
  group_count: number;
  sheets: SheetPlanView[];
  skipped: SkippedRow[];
  capacity: { needed: number; available: number; ok: boolean };
  warnings: string[];
}

export interface GroupRef {
  prefix: string;
  name: string;
}

export interface DraftRef {
  draft_id: string;
  name: string;
  group_prefix: string;
  desired_test_id: string | null;
}

export interface ImportResultView {
  created_groups: GroupRef[];
  reused_groups: GroupRef[];
  drafts: DraftRef[];
  skipped: SkippedRow[];
  skipped_sheets: { sheet_name: string; reason: string }[];
  renumbered: RenumberedRow[];
}

export interface CreateProjectImportResult extends ImportResultView {
  project: ProjectView;
}

export interface DraftSourceView {
  file_name: string;
  sheet_name: string;
  row: number;
}

export interface DraftRow {
  draft_id: string;
  name: string;
  description: string | null;
  actor: string | null;
  group_prefix: string;
  desired_test_id: string | null;
  desired_id_available: boolean;
  source: DraftSourceView;
  created_at: string;
}

export interface DraftDetail extends DraftRow {
  procedure: string | null;
  expectation: string | null;
  suggested_instruction: string;
}

export interface DraftListResponse {
  drafts: DraftRow[];
  count: number;
  problems: string[];
}

/**
 * 파일을 multipart 로 올린다.
 *
 * **`X-ITB-Project-Root` 를 손으로 붙인다.** `send()` 는 `Content-Type: application/json`
 * 을 붙이는데 multipart 요청에 그 헤더가 붙으면 경계 문자열이 사라져 서버가 본문을 읽지
 * 못한다. 그래서 `send()` 를 쓸 수 없지만, 그렇다고 프로젝트 대조 가드를 빼면 화면이
 * 보여 주는 프로젝트와 다른 프로젝트로 가져오게 된다.
 */
async function postFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const guard: Record<string, string> =
    expectedProjectRoot !== null ? { [PROJECT_ROOT_HEADER]: encodeRoot(expectedProjectRoot) } : {};
  // Content-Type 은 브라우저가 경계 문자열과 함께 정하게 둔다.
  const resp = await fetch(path, { method: "POST", body: form, headers: guard });
  const text = await resp.text();
  if (!resp.ok) throw apiErrorFromBody(resp.status, text);
  return JSON.parse(text) as T;
}

export const imports = {
  /** 파일을 해석해 계획을 만든다. 프로젝트에는 아무것도 만들지 않는다. */
  preview: (file: File) => postFile<ImportPlanView>("/api/import/preview", file),

  /** 열린 프로젝트로 가져온다. 전부 아니면 전무다. */
  commit: (planId: string, prefixes: Record<string, string> = {}) =>
    post<ImportResultView>("/api/import/commit", { plan_id: planId, prefixes }),

  /** 파일에서 새 프로젝트를 만들며 가져온다. */
  createProject: (body: {
    plan_id: string;
    name: string;
    default_start_url: string;
    test_id_attribute?: string;
    prefixes?: Record<string, string>;
  }) => post<CreateProjectImportResult>("/api/import/create-project", body),
};

export const drafts = {
  list: () => get<DraftListResponse>("/api/drafts"),
  get: (id: string) => get<DraftDetail>(`/api/drafts/${encodeURIComponent(id)}`),
  remove: (id: string) => del<void>(`/api/drafts/${encodeURIComponent(id)}`),
};

/**
 * 저장 응답 (014).
 *
 * 저장된 테스트에 **이번 저장에서만 참인 사실 둘**이 얹혀 온다. 저장 형식에는 들어가지
 * 않는다 — 서버가 디스크에는 `Test` 를 쓴다.
 */
export interface SavedTestView extends Test {
  /** 어느 초안에서 왔는가. 초안에서 출발한 세션에만 있다. */
  from_draft?: string | null;
  /**
   * 희망 번호를 주지 못했을 때만 실린다 (FR-032).
   *
   * **조용히 다른 번호를 주지 않는다.** 사용자의 설계서에는 원래 번호가 적혀 있고,
   * 어긋났다는 사실을 지금 말하지 않으면 나중에 발견하게 된다.
   */
  desired_id_taken?: { wanted: string; assigned: string } | null;
}
