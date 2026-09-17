/** 프로젝트 선택 `/projects` (018 §3.2). 알림 층 밖이다 — 옛 `App.tsx` 에서도 그랬다. */
import { useNavigate } from "react-router";

import { paths } from "../../lib/paths";
import { ProjectSetup } from "../../pages/ProjectSetup";
import { useAppState, useAppStore } from "../appStore";

export function ProjectsRoute() {
  const navigate = useNavigate();
  const store = useAppStore();
  const project = useAppState((s) => s.project);
  return (
    <ProjectSetup
      onOpened={(p) => {
        store.openProject(p);
        void navigate(paths.list());
      }}
      /*
        **열려 있던 프로젝트가 있을 때만** 되돌아가는 길을 준다. 첫 실행에는 돌아갈
        곳이 없으므로 그 길도 없다 — `project` 가 없는 것(`null`·`undefined`)이 그 조건이다.
      */
      onCancel={project ? () => void navigate(paths.list()) : undefined}
      /*
        삭제로 열린 프로젝트가 닫혔다 (012 FR-416). 비우지 않으면 사용자는 사라진
        프로젝트를 가리키는 「돌아가기」를 계속 보고, 그것을 누르면 없는 것을 그린다.
      */
      onProjectClosed={() => store.openProject(null)}
      /*
        목록에서 고친 이름이 다른 화면에도 나타나야 한다 (012 FR-405).

        **경로가 같을 때만 갈아 끼운다.** 목록의 어느 줄에서나 이름을 고칠 수 있으므로,
        지금 열려 있는 것과 다른 프로젝트를 고쳤는데 열린 것의 이름을 바꾸면 안 된다.
      */
      onProjectRenamed={(root, name) => store.renameProject(root, name)}
    />
  );
}
