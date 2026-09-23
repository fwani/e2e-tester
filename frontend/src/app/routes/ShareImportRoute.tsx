/**
 * 공유 파일에서 가져오기 `/share/import` (019 US2·US3·US5).
 *
 * 열린 프로젝트가 **없어도 동작해야 한다** — 프로젝트 목록 화면에서 곧장 들어오는 길이
 * 있기 때문이다. 그래서 `hasOpenProject` 로 「이 프로젝트에 더하기」 선택지만 접는다.
 *
 * 가져오기가 끝나면 서버가 새 프로젝트를 열었으므로 **화면의 프로젝트 상태를 맞춘다** —
 * 맞추지 않으면 다음 요청이 프로젝트 대조에서 어긋난다.
 */
import { useNavigate } from "react-router";

import { project as projectApi } from "../../api/client";
import { paths } from "../../lib/paths";
import { ShareImport } from "../../pages/ShareImport";
import { useAppState, useAppStore } from "../appStore";

export function ShareImportRoute() {
  const navigate = useNavigate();
  const store = useAppStore();
  const project = useAppState((s) => s.project);

  return (
    <ShareImport
      hasOpenProject={project !== null}
      onDone={() => {
        /*
          서버가 새 프로젝트를 열었다 (`target=new`). 저장소의 캐시를 갈아 끼우지 않으면
          다음 요청이 옛 경로를 `X-ITB-Project-Root` 로 보내고, 프로젝트 대조에서 어긋난다.
          실패해도 화면을 막지 않는다 — 가져오기는 이미 끝났다.
        */
        void projectApi
          .current()
          .then((p) => store.openProject(p))
          .catch(() => undefined);
      }}
      onClose={() => void navigate(paths.list())}
    />
  );
}
