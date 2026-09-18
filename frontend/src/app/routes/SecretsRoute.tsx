/** 비밀 값 `/secrets` (018 §2). */
import { useNavigate } from "react-router";

import { paths } from "../../lib/paths";
import { SecretValues } from "../../pages/SecretValues";

export function SecretsRoute() {
  const navigate = useNavigate();
  return (
    <SecretValues
      onClose={() => void navigate(paths.list())}
      onManageKeys={() => void navigate(paths.keys())}
    />
  );
}
