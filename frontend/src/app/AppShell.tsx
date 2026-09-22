/**
 * 레이아웃 라우트 — 열린 프로젝트가 있을 때의 모든 화면이 이 안에 그려진다 (018 design §2).
 *
 * 알림 층은 **앱 뿌리에 하나**다 (017 Phase 10 · T100). 그래야 알림이 한 자리에 모이고 동시에 보이는 수의
 * 상한이 한 번만 적용된다. 화면은 층을 모르고 `<Toast>` 만 조건부로 그린다. 프로젝트 선택 화면은 이 밖에
 * 있다 — 옛 `App.tsx` 에서도 그 화면은 알림 층 밖에서 그려졌다.
 */
import { WorkspaceNavigation } from "./WorkspaceNavigation";
import { Outlet, useLocation } from "react-router";

import { ErrorNotice } from "../components/ErrorNotice";
import { Toast, Toaster } from "../ui/Toast";
import { AppActionsProvider, useAppActions } from "./actions";
import { useAppState, useAppStore } from "./appStore";

export function AppShell() {
  const workbench = /^\/(tests|sessions)\//.test(useLocation().pathname);
  return (
    <AppActionsProvider>
      <Toaster docked={workbench}>
        <ShellError />
        <div className="workspace-shell"><WorkspaceNavigation /><div className="workspace-main"><Outlet /></div></div>
      </Toaster>
    </AppActionsProvider>
  );
}

/*
  2026-09-10 사용자 결정 — **토스트는 한 자리다.** (자리는 2026-09-16 에 아래로 옮겼다 — N-02)

  이 배너는 화면 맨 위 문서 흐름 안에 있었고, 그래서 뜰 때마다 아래 화면 전부를
  밀어 내렸다 (2026-09-09 에 `Workbench` 의 알림이 고친 것과 **같은 결함**이 여기
  남아 있었다). 자리도 달랐다 — 국면 화면의 알림은 다른 데서 떴다.

  같은 층(`.toast-layer`)에 올린다. 오류이므로 **스스로 사라지지 않는다** —
  「닫기」가 유일한 퇴장이다 (`NoticeStack` 의 `LINGER_MS` 와 같은 규칙).
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
