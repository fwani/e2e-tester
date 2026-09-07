/**
 * 화면 전환. 단독 로컬 도구이므로 라우터를 두지 않고 상태로 화면을 고른다 —
 * 화면이 4개이고 딥링크 요구가 없다.
 */
import { useCallback, useEffect, useState } from "react";

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
  /**
   * 실행 요청이 진행 중인 테스트 ID (005 FR-127·FR-129).
   *
   * `null` 이 아니면 어느 화면의 실행 버튼도 눌리지 않는다. 브라우저를 띄우는 데 약
   * 1초가 걸리는데 그 동안 화면이 아무 말도 하지 않아 사용자가 다시 눌렀고(U-11),
   * 그것이 세션 중복으로 직결됐다(U-06).
   */
  const [pendingRun, setPendingRun] = useState<string | null>(null);
  /** 살아 있는 세션. 목록 화면이 이것을 배너로 알린다 (UX U-05). */
  const [active, setActive] = useState<SessionView[]>([]);

  const refreshActive = useCallback(() => {
    void sessions
      .list()
      .then((r) => setActive(r.sessions))
      .catch(() => setActive([])); // 조회 실패가 목록 화면을 막을 이유는 없다
  }, []);

  useEffect(() => {
    if (screen.name === "list") refreshActive();
  }, [screen.name, refreshActive]);

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

  /**
   * 실행을 거는 **유일한 경로** (005 T021 · FR-125·FR-127·FR-129).
   *
   * 이전에는 결과 화면이 이것을 직접 부르고 실행 화면은 `discard` 후 새로 만드는 다른
   * 경로를 썼다. 같은 이름의 버튼이 두 화면에서 다르게 동작했고, 결과 화면 쪽은 종료된
   * 세션 때문에 **항상 409 로 거부**됐다 (U-01).
   *
   * `pendingRun` 을 여기서 관리하는 이유는 in-flight 가드가 한 곳에 있어야 하기
   * 때문이다. 화면마다 두면 한 화면이 빠뜨리고, 그 화면에서 연타하면 브라우저 창이
   * 둘 뜬다 (U-06 — 실측 5회 클릭에 201 이 2건이었다).
   */
  const startRun = (testId: string, fromStepIndex?: number) => {
    // 첫 클릭만 받는다. 0.3초 안에 화면이 변해야 하므로(FR-129) 응답을 기다리지 않고
    // 즉시 상태를 세운다 — 버튼은 이 값을 보고 비활성이 된다.
    if (pendingRun !== null) return;
    setPendingRun(testId);
    setError(null);
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
      .catch((exc: unknown) => setError(describeError(exc)))
      // 성공해도 놓는다. 화면이 이미 바뀌었으므로 남겨 두면 그 테스트를 다시 실행할 수
      // 없게 되고, 그것은 고치려던 것과 같은 종류의 막힘이다.
      .finally(() => setPendingRun(null));
  };

  /** 이전 이름을 쓰는 화면이 남아 있어도 같은 경로를 지나게 한다. */
  const startReplay = startRun;

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
          onRun={(testId) => startRun(testId)}
          pendingRunId={pendingRun}
          onOpenResult={(testId) => setScreen({ name: "result", testId })}
          onOpenDefinition={(testId) => setScreen({ name: "definition", testId })}
          onOpenSecrets={() => setScreen({ name: "secrets" })}
          onOpenKeys={() => setScreen({ name: "keys" })}
          activeSessions={active}
          onResumeSession={(session) => setScreen({ name: "runner", session })}
          onDiscardSession={(sessionId) =>
            void sessions
              .discard(sessionId)
              .catch((exc: unknown) => setError(describeError(exc)))
              .finally(refreshActive)
          }
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
          onRerun={(testId, fromStepIndex) => startReplay(testId, fromStepIndex)}
        />
      )}

      {screen.name === "result" && (
        <RunResult
          testId={screen.testId}
          onRunAll={(testId) => startRun(testId)}
          onRunFrom={(testId, stepIndex) => startRun(testId, stepIndex)}
          runPending={pendingRun !== null}
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
