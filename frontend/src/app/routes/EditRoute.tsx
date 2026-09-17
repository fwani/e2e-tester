/**
 * 편집 `/tests/:testId/edit[?step=]` (018 §2).
 *
 * 006 — 진입점 3개(목록 행 메뉴, 결과 화면 「Step nn 고치기」, 주소)가 모두 이 **한 화면**으로 온다
 * (FR-179). 실행 진입과 세션 이동은 005 가 만든 단일 경로(`actions.startRun`·`actions.openSession`)를
 * 그대로 쓴다 — 화면마다 새로 만들면 U-01·U-06 이 되살아난다.
 */
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
