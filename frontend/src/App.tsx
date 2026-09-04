/**
 * 화면 전환. 단독 로컬 도구이므로 라우터를 두지 않고 상태로 화면을 고른다 —
 * 화면이 4개이고 딥링크 요구가 없다.
 */
import { useEffect, useState } from "react";

import { project, sessions, type ProjectView, type SessionView } from "./api/client";
import { ErrorNotice, describeError, type ErrorInfo } from "./components/ErrorNotice";
import { CreateTest } from "./pages/CreateTest";
import { KeyManagement } from "./pages/KeyManagement";
import { ProjectSetup } from "./pages/ProjectSetup";
import { RunResult } from "./pages/RunResult";
import { SecretValues } from "./pages/SecretValues";
import { TestDefinition } from "./pages/TestDefinition";
import { AiCompose } from "./pages/AiCompose";
import { SessionScreen } from "./pages/SessionScreen";
import { TestList } from "./pages/TestList";

type Screen =
  | { name: "loading" }
  | { name: "setup" }
  | { name: "list" }
  | { name: "create" }
  | { name: "runner"; session: SessionView; aiInstruction?: string | null }
  /** AI 지시문 작성. 확정 디자인이 독립 artboard 로 정의한다 (DC-008). */
  | { name: "ai-compose"; startUrl: string }
  | { name: "result"; testId: string }
  | { name: "definition"; testId: string; focusStepId?: string | null }
  | { name: "keys" }
  | { name: "secrets" };

export function App() {
  const [opened, setOpened] = useState<ProjectView | null>(null);
  const [screen, setScreen] = useState<Screen>({ name: "loading" });
  // 문자열이 아니라 ErrorInfo 를 담는다 — 문자열로 받으면 next_action 이 여기서 죽는다
  // (003 EC-004). "대상 앱에 연결할 수 없습니다" 뒤에 "떠 있는지 확인하세요" 가 따라와야 한다.
  const [error, setError] = useState<ErrorInfo | null>(null);

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
      .catch((exc: unknown) => setError(describeError(exc)));
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
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, padding: "8px 16px" }}>
          <div style={{ flex: 1 }}>
            <ErrorNotice error={error} />
          </div>
          <button className="ghost" onClick={() => setError(null)}>
            닫기
          </button>
        </div>
      )}

      {screen.name === "list" && (
        <TestList
          projectName={opened.name}
          onCreate={() => setScreen({ name: "create" })}
          onRun={(testId) => startReplay(testId)}
          onOpenResult={(testId) => setScreen({ name: "result", testId })}
          onOpenDefinition={(testId) => setScreen({ name: "definition", testId })}
          onOpenSecrets={() => setScreen({ name: "secrets" })}
          onOpenKeys={() => setScreen({ name: "keys" })}
        />
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
          onRecord={(startUrl) => {
            void sessions
              .create({ mode: "record", start_url: startUrl })
              .then((session) => setScreen({ name: "runner", session }))
              .catch((exc: unknown) => setError(describeError(exc)));
          }}
          // 지시문은 다음 화면에서 쓴다 — 확정 디자인의 「지시문 쓰기」다 (DC-008).
          onWriteInstruction={(startUrl) => setScreen({ name: "ai-compose", startUrl })}
        />
      )}

      {screen.name === "ai-compose" && (
        <AiCompose
          startUrl={screen.startUrl}
          onCancel={() => setScreen({ name: "create" })}
          onStarted={(session, aiInstruction) =>
            setScreen({ name: "runner", session, aiInstruction })
          }
        />
      )}

      {screen.name === "runner" && (
        <SessionScreen
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
