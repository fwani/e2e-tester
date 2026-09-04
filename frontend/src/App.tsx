/**
 * 화면 전환. 단독 로컬 도구이므로 라우터를 두지 않고 상태로 화면을 고른다 —
 * 화면이 4개이고 딥링크 요구가 없다.
 */
import { useEffect, useState } from "react";

import { ApiError, project, sessions, type ProjectView, type SessionView } from "./api/client";
import { CreateTest } from "./pages/CreateTest";
import { KeyManagement } from "./pages/KeyManagement";
import { ProjectSetup } from "./pages/ProjectSetup";
import { RunResult } from "./pages/RunResult";
import { SecretValues } from "./pages/SecretValues";
import { TestDefinition } from "./pages/TestDefinition";
import { Runner } from "./pages/Runner";
import { TestList } from "./pages/TestList";

type Screen =
  | { name: "loading" }
  | { name: "setup" }
  | { name: "list" }
  | { name: "create" }
  | { name: "runner"; session: SessionView; aiInstruction?: string | null }
  | { name: "result"; testId: string }
  | { name: "definition"; testId: string; focusStepId?: string | null }
  | { name: "keys" }
  | { name: "secrets" };

export function App() {
  const [opened, setOpened] = useState<ProjectView | null>(null);
  const [screen, setScreen] = useState<Screen>({ name: "loading" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // 이미 열린 프로젝트가 있으면 목록으로 간다. 없으면 프로젝트 선택 화면부터 —
    // 그 화면이 기존 프로젝트를 자동으로 불러 보여준다 (DR-002). 서버를 재시작해도
    // 사용자가 경로를 타이핑할 일이 없다.
    void project
      .current()
      .then((p) => {
        setOpened(p);
        setScreen({ name: "list" });
      })
      .catch(() => setScreen({ name: "setup" }));
  }, []);

  const startReplay = (testId: string, fromStepIndex?: number) => {
    void sessions
      .create({ mode: "replay", test_id: testId })
      .then(async (session) => {
        // "실패한 Step부터 실행" — 세션을 만든 뒤 곧바로 실행 위치를 옮긴다 (FR-055).
        if (fromStepIndex !== undefined && fromStepIndex > 0) {
          return await sessions.runFrom(session.session_id, fromStepIndex);
        }
        return session;
      })
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
        <>
          {/* 민감 값·키는 목록에서 들어간다 — 확정 디자인에 없는 화면이므로 진입점도
              눈에 띄지 않게 둔다 (spec 디자인 차이 3). */}
          <div className="row" style={{ gap: 8, padding: "8px 16px 0" }}>
            <span className="spacer" />
            <button className="ghost" onClick={() => setScreen({ name: "secrets" })}>
              비밀 값
            </button>
            <button className="ghost" onClick={() => setScreen({ name: "keys" })}>
              키 관리
            </button>
          </div>
          <TestList
            onCreate={() => setScreen({ name: "create" })}
            onRun={(testId) => startReplay(testId)}
            onOpenResult={(testId) => setScreen({ name: "result", testId })}
            onOpenDefinition={(testId) => setScreen({ name: "definition", testId })}
          />
        </>
      )}

      {screen.name === "definition" && (
        <TestDefinition
          testId={screen.testId}
          focusStepId={screen.focusStepId ?? null}
          onRun={(testId) => startReplay(testId)}
          onBack={() => setScreen({ name: "list" })}
        />
      )}

      {screen.name === "keys" && (
        <KeyManagement onClose={() => setScreen({ name: "list" })} />
      )}

      {screen.name === "secrets" && (
        <SecretValues
          onClose={() => setScreen({ name: "list" })}
          onManageKeys={() => setScreen({ name: "keys" })}
        />
      )}

      {screen.name === "create" && (
        <CreateTest
          project={opened}
          onCancel={() => setScreen({ name: "list" })}
          onStarted={(session, aiInstruction) =>
            setScreen({ name: "runner", session, aiInstruction })
          }
        />
      )}

      {screen.name === "runner" && (
        <Runner
          initial={screen.session}
          aiInstruction={screen.aiInstruction ?? null}
          onFinished={() => setScreen({ name: "list" })}
          onShowResult={(testId) => setScreen({ name: "result", testId })}
        />
      )}

      {screen.name === "result" && (
        <RunResult
          testId={screen.testId}
          onRunAll={(testId) => startReplay(testId)}
          onRunFrom={(testId, stepIndex) => startReplay(testId, stepIndex)}
          onEditStep={(testId, stepId) =>
            // FR-056 — 실패한 Step 의 상세로 바로 이동한다 (T170).
            setScreen({ name: "definition", testId, focusStepId: stepId })
          }
          onBack={() => setScreen({ name: "list" })}
        />
      )}
    </>
  );
}
