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
