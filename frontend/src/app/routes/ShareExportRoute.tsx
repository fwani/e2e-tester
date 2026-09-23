/**
 * 공유용 내보내기 `/share/export` (019 US1·US4).
 *
 * 고른 테스트는 **주소의 질의**로 받는다. 저장소 상태로 나르지 않는 이유는 새로 고쳐도
 * 대상이 유지되어야 하기 때문이다 — 확인 화면을 읽는 동안 새로 고친 사용자가 프로젝트
 * 전체를 내보내게 되면 안 된다.
 */
import { useNavigate, useSearchParams } from "react-router";

import { paths } from "../../lib/paths";
import { ShareExport } from "../../pages/ShareExport";

export function ShareExportRoute() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const raw = params.get("tests");
  const testIds = raw ? raw.split(",").filter(Boolean) : null;

  return <ShareExport testIds={testIds} onClose={() => void navigate(paths.list())} />;
}
