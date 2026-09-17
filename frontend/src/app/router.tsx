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
