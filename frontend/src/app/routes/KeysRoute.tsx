/** 키 관리 `/keys` (018 §2). */
import { useNavigate } from "react-router";

import { paths } from "../../lib/paths";
import { KeyManagement } from "../../pages/KeyManagement";

export function KeysRoute() {
  const navigate = useNavigate();
  return <KeyManagement onClose={() => void navigate(paths.list())} />;
}
