import { NavLink, useLocation } from "react-router";
import { useAppState } from "./appStore";

function NavIcon({ kind }: { kind: "tests" | "create" | "secrets" | "keys" | "projects" }) {
  const paths = {
    tests: "M4 4h16v16H4zM8 8h8M8 12h8M8 16h4",
    create: "M12 5v14M5 12h14",
    secrets: "M7 10V7a5 5 0 0 1 10 0v3M5 10h14v11H5zM12 14v3",
    keys: "M14 5a5 5 0 1 1-3 9l-7 7H1v-3l7-7a5 5 0 0 1 6-6z",
    projects: "M3 6h7l2 3h9v11H3z",
  };
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[kind]} /></svg>;
}

export function WorkspaceNavigation() {
  const project = useAppState((s) => s.project);
  const pathname = useLocation().pathname;
  const compact = pathname !== "/tests/new" && /^\/(tests|sessions)\//.test(pathname);
  return <aside className={`workspace-navigation${compact ? " is-compact" : ""}`} aria-label="작업 공간">
    <NavLink to="/" className="workspace-brand" aria-label="ITB 테스트 목록"><span className="workspace-logo"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12l5 5L20 6" /></svg></span><span className="nav-copy">ITB <small>Test workspace</small></span></NavLink>
    <NavLink to="/projects" className="workspace-project" title={project?.name ?? "프로젝트"}><NavIcon kind="projects" /><span className="nav-copy"><small>현재 프로젝트</small><strong>{project?.name ?? "프로젝트"}</strong></span></NavLink>
    <nav aria-label="주 메뉴">
      <NavLink to="/" end title="테스트 라이브러리"><NavIcon kind="tests" /><span className="nav-copy">테스트 라이브러리</span></NavLink>
      <NavLink to="/tests/new" title="테스트 작성"><NavIcon kind="create" /><span className="nav-copy">테스트 작성</span></NavLink>
    </nav>
    <nav className="workspace-settings" aria-label="프로젝트 설정">
      <NavLink to="/secrets" title="비밀 값"><NavIcon kind="secrets" /><span className="nav-copy">비밀 값</span></NavLink>
      <NavLink to="/keys" title="키 관리"><NavIcon kind="keys" /><span className="nav-copy">키 관리</span></NavLink>
    </nav>
    <div className="workspace-caption nav-copy">작성부터 결과 확인까지</div>
  </aside>;
}
