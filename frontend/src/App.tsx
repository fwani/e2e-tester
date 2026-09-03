/**
 * 화면 전환. 단독 로컬 도구이므로 라우터를 두지 않고 상태로 화면을 고른다 —
 * 화면이 4개이고 딥링크 요구가 없다.
 */
import { useEffect, useState } from "react";

import { ApiError, project, sessions, type ProjectView, type SessionView } from "./api/client";
import { CreateTest } from "./pages/CreateTest";
import { ProjectSetup } from "./pages/ProjectSetup";
import { Runner } from "./pages/Runner";
import { TestList } from "./pages/TestList";

type Screen =
  | { name: "loading" }
  | { name: "setup" }
  | { name: "list" }
  | { name: "create" }
  | { name: "runner"; session: SessionView };

export function App() {
  const [opened, setOpened] = useState<ProjectView | null>(null);
  const [screen, setScreen] = useState<Screen>({ name: "loading" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // 이미 열린 프로젝트가 있으면 목록으로 간다. 없으면 프로젝트 화면부터.
    void project
      .current()
      .then((p) => {
        setOpened(p);
        setScreen({ name: "list" });
      })
      .catch(() => setScreen({ name: "setup" }));
  }, []);

  const startReplay = (testId: string) => {
    void sessions
      .create({ mode: "replay", test_id: testId })
      .then((session) => setScreen({ name: "runner", session }))
      .catch((exc: unknown) =>
        setError(exc instanceof ApiError ? exc.message : String(exc)),
      );
  };

  if (screen.name === "loading") {
    return <main style={{ padding: 32 }} className="muted">불러오는 중…</main>;
  }

  if (screen.name === "setup" || opened === null) {
    return (
      <ProjectSetup
        onOpened={(p) => {
          setOpened(p);
          setScreen({ name: "list" });
        }}
      />
    );
  }

  return (
    <>
      {error !== null && (
        <div
          style={{
            padding: "8px 16px",
            background: "var(--fail-tint)",
            color: "var(--fail-dark)",
          }}
        >
          {error}
          <button className="ghost" onClick={() => setError(null)}>
            닫기
          </button>
        </div>
      )}

      {screen.name === "list" && (
        <TestList
          onCreate={() => setScreen({ name: "create" })}
          onRun={startReplay}
          onOpenResult={startReplay}
        />
      )}

      {screen.name === "create" && (
        <CreateTest
          project={opened}
          onCancel={() => setScreen({ name: "list" })}
          onStarted={(session) => setScreen({ name: "runner", session })}
        />
      )}

      {screen.name === "runner" && (
        <Runner initial={screen.session} onFinished={() => setScreen({ name: "list" })} />
      )}
    </>
  );
}
