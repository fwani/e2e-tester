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
      /*
        가져오기 미리보기 (014 US2).

        **취소는 목록으로 되돌아가는 것뿐이다** — 계획은 서버 메모리에만 있고 프로젝트에는
        아무것도 만들어지지 않았으므로 치울 것이 없다 (FR-016).
      */
      onCancel={leave}
      /*
        014 FR-018a — **결과를 버리지 않는다.** 미리보기에서만 보이면 확정하는 순간
        사라지고, 무엇이 빠졌는지 다시 확인할 길이 없다 (수렴 T088).
      */
      onDone={(result) => {
        store.setImportDone(result);
        leave();
      }}
    />
  );
}
