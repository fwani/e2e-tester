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
