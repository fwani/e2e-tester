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
    // 005 FR-169 (U-17) — 목록에 머무는 동안 세션 상태를 따라간다.
    //
    // 리포트는 실행이 끝난 뒤 25초를 더 기다려도 배너가 "실행 중" 으로 남아 있는 것을
    // 봤다. 5초 주기는 로컬 단독 도구에서 충분히 싸고, 25초 안에 반영된다는 요구를
    // 여유 있게 만족한다.
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
          014 US3 — 초안에서 녹화를 시작한다.

          **기존 AI 작성 경로로 들어간다.** 지시문은 서버가 지은 것을 받아 미리 채우고
          (FR-031), 사용자가 고칠 수 있다. 초안을 읽는 데 실패하면 그 사실을 알리고
          화면을 바꾸지 않는다 — 빈 지시문으로 들어가면 사용자는 초안이 비어 있는 줄 안다.

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
