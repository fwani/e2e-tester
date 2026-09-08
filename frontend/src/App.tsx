/**
 * 화면 전환. 단독 로컬 도구이므로 라우터를 두지 않고 상태로 화면을 고른다 —
 * 화면이 4개이고 딥링크 요구가 없다.
 */
import { useCallback, useEffect, useState } from "react";

import { initialLocation, useScreenUrl } from "./hooks/useScreenUrl";

import { project, sessions, type ProjectView, type SessionView } from "./api/client";
import { ErrorNotice, describeError, type ErrorInfo } from "./components/ErrorNotice";
import { ComposeView } from "./pages/ComposeView";
import { KeyManagement } from "./pages/KeyManagement";
import { ProjectSetup } from "./pages/ProjectSetup";
import { ResultView } from "./pages/ResultView";
import { SecretValues } from "./pages/SecretValues";
import { EditView } from "./pages/EditView";
import { SessionScreen } from "./pages/SessionScreen";
import { TestList } from "./pages/TestList";

type Screen =
  | { name: "loading" }
  | { name: "setup" }
  | { name: "list" }
  /**
   * 만들기 국면 (2회차 · FR-217b·FR-259).
   *
   * 1회차의 `create` 와 `ai-compose` 두 화면을 **하나로 합친 것**이다. 방법을 고르고
   * 지시문을 쓰는 일이 같은 화면 안에서 일어나므로 중간 상태가 없다 — 그것이
   * SC-011(껍데기가 바뀌는 횟수 0)의 뜻이다.
   */
  | { name: "compose" }
  | {
      name: "runner";
      session: SessionView;
      aiInstruction?: string | null;
      /**
       * 이 세션이 끝나면 돌아갈 편집 화면 (006 FR-204 · converge T094).
       *
       * 편집 화면에서 「브라우저 열어 Step nn 에서 멈추기」로 출발한 경우에만 있다.
       * 없으면 목록으로 간다 — 실행 버튼으로 시작한 세션은 돌아갈 편집 화면이 없다.
       *
       * **왜 필요한가**: 편집하다 브라우저를 열었는데 끝나고 목록에 떨어지면 사용자는
       * 자기가 출발한 화면을 잃는다. 고치던 Step 을 다시 찾아 들어가야 한다.
       */
      returnToEdit?: { testId: string; stepId: string | null } | null;
      /**
       * 도착하면 직접 조작 기록을 켠다 (009 FR-291·FR-295).
       *
       * 「이 앞에 추가」로 출발한 세션에만 있다. 사용자가 그 조작을 고른 뜻이 「여기서
       * 브라우저를 만져 Step 을 만들겠다」이므로, 다섯 걸음을 한 걸음으로 줄이는 마지막
       * 단계가 기록을 켜는 것이다 (관찰 M-04).
       *
       * **서버 상태에 저장하지 않는다** (research R5). 새로 고치면 기록은 켜지지 않은 채로
       * 오고, 그때 팔레트의 같은 조작을 그대로 쓸 수 있다 — 잃어도 막히지 않는 정보만
       * 화면에 둔다.
       */
      recordOnArrival?: boolean;
    }
  /**
   * 결과 국면. `focusStepId` 는 **국면을 넘어 유지되는 지목**이다 (007 FR-239 · S-10).
   *
   * 세션에서 결과로 넘어올 때 보던 Step 을 함께 넘긴다 — 이전에는 `onShowResult` 가
   * 테스트 식별자만 날라서, 사용자는 결과 화면에서 그 Step 을 다시 찾아야 했다.
   */
  | { name: "result"; testId: string; focusStepId?: string | null }
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
    if (screen.name !== "list") return;
    refreshActive();
    // 005 FR-169 (U-17) — 목록에 머무는 동안 세션 상태를 따라간다.
    //
    // 리포트는 실행이 끝난 뒤 25초를 더 기다려도 배너가 "실행 중" 으로 남아 있는 것을
    // 봤다. 5초 주기는 로컬 단독 도구에서 충분히 싸고, 25초 안에 반영된다는 요구를
    // 여유 있게 만족한다.
    const timer = window.setInterval(refreshActive, 5000);
    return () => window.clearInterval(timer);
  }, [screen.name, refreshActive]);

  useEffect(() => {
    // 이미 열린 프로젝트가 있으면 목록으로 간다. 없으면 프로젝트 선택 화면부터 —
    // 그 화면이 기존 프로젝트를 자동으로 불러 보여준다 (DR-002). 서버를 재시작해도
    // 사용자가 경로를 타이핑할 일이 없다.
    void project
      .current()
      .then((p) => {
        setOpened(p);
        // 005 FR-166 (U-15) — 주소가 가리키는 화면으로 복원한다.
        //
        // 이전에는 결과 화면에서 새로고침하면 목록으로 되돌아갔다. 결과 자체는 남아
        // 있어 다시 열 수는 있었지만, 사용자는 자기가 보던 화면을 잃었다.
        const at = initialLocation();
        if (at.name === "result" && at.testId) {
          setScreen({ name: "result", testId: at.testId, focusStepId: at.stepId ?? null });
        } else if (at.name === "definition" && at.testId) {
          setScreen({
            name: "definition",
            testId: at.testId,
            focusStepId: at.stepId ?? null,
          });
        } else if (at.name === "keys") {
          setScreen({ name: "keys" });
        } else if (at.name === "secrets") {
          setScreen({ name: "secrets" });
        } else {
          // 실행 화면(`runner`)은 복원하지 않는다 — 세션 객체가 필요하고, 그것은
          // 목록의 세션 배너가 「이어서 보기」로 되찾는다(FR-168). URL 만으로
          // 되살리면 죽은 세션 화면을 그릴 수 있다.
          setScreen({ name: "list" });
        }
      })
      .catch(() => setScreen({ name: "setup" }));
  }, []);

  /**
   * 005 FR-166·FR-167 — 화면 상태를 주소에 반영하고 뒤로가기를 앱 안에 붙잡는다.
   *
   * 뒤로가기가 `about:blank` 로 나가 앱을 이탈하던 것이 U-15 였다.
   */
  useScreenUrl(
    {
      name: screen.name,
      testId: "testId" in screen ? screen.testId : null,
      sessionId: screen.name === "runner" ? screen.session.session_id : null,
      // 006 FR-181 — 지목된 Step 도 주소에 남긴다. 새로고침해도 고치러 온 Step 을 잃지
      // 않는다.
      // 007 FR-239 — 지목한 Step 은 결과 국면에서도 주소에 남는다. 새로 고쳐도
      // 보던 Step 을 잃지 않는다 (006 FR-181 을 결과 국면으로 넓힌 것).
      stepId:
        screen.name === "definition" || screen.name === "result"
          ? (screen.focusStepId ?? null)
          : null,
    },
    (loc) => {
      if (loc.name === "result" && loc.testId) {
        setScreen({ name: "result", testId: loc.testId, focusStepId: loc.stepId ?? null });
      } else if (loc.name === "definition" && loc.testId) {
        setScreen({
          name: "definition",
          testId: loc.testId,
          focusStepId: loc.stepId ?? null,
        });
      } else if (loc.name === "keys") {
        setScreen({ name: "keys" });
      } else if (loc.name === "secrets") {
        setScreen({ name: "secrets" });
      } else {
        setScreen({ name: "list" });
      }
    },
  );

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

  /**
   * 편집을 위해 브라우저를 열고 지정한 Step **직전**에서 멈춘다 (006 FR-200·FR-201).
   *
   * 실행 진입과 **같은 가드**를 지난다 — `pendingRun` 이 세션 중복 생성을 막는다.
   * 여기에 별도 경로를 만들면 편집 쪽에서만 연타로 브라우저가 둘 뜬다 (005 U-06 과
   * 같은 종류의 결함).
   *
   * 도달한 뒤의 편집은 지금의 일시정지 팔레트 그대로다 — 새 편집 UI 를 만들지 않는다
   * (FR-205).
   */
  const openBrowserAt = (
    testId: string,
    stepIndex: number,
    stepId: string | null = null,
  ) => {
    if (pendingRun !== null) return;
    setPendingRun(testId);
    setError(null);
    void sessions
      .create({ mode: "replay", test_id: testId, pause_before_index: stepIndex })
      .then((session) =>
        setScreen({
          name: "runner",
          session,
          // 006 FR-204 — 끝나면 출발한 편집 화면으로 돌아온다.
          returnToEdit: { testId, stepId },
          /*
            009 FR-291 — 이 조작의 목적이 「그 자리에 Step 을 넣는 것」이므로 도착하면
            기록이 켜진 상태여야 한다. 이전에는 도착한 뒤 사용자가 팔레트에서 「직접
            조작으로 Step 추가」를 다시 찾아야 했다 — 그것이 다섯 걸음의 마지막 걸음이다.
          */
          recordOnArrival: true,
        }),
      )
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setPendingRun(null));
  };

  /**
   * 거절 안내가 가리킨 세션으로 이동한다 (005 T024 · FR-126).
   *
   * 거절은 목록에서도 결과 화면에서도 날 수 있고 배너는 두 화면 **위**에 있다. 그래서
   * 이동 수단도 여기 한 곳에 둔다 — 화면마다 두면 한쪽이 빠지고, 빠진 화면에서는 안내가
   * 다시 "화면에 없는 조작" 을 지시하게 된다.
   */
  const openSession = (sessionId: string) => {
    void sessions
      .get(sessionId)
      .then((session) => {
        setError(null);
        setScreen({ name: "runner", session });
      })
      // 그 사이에 끝났다면 이동할 곳이 없다. 목록이 현재 상태를 보여준다.
      .catch(() => {
        setError(null);
        setScreen({ name: "list" });
      });
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
            <ErrorNotice
              error={error}
              action={
                error.sessionId
                  ? { label: "실행 중인 세션 보기", onClick: () => openSession(error.sessionId!) }
                  : null
              }
            />
          </div>
          <button className="ghost" onClick={() => setError(null)}>
            닫기
          </button>
        </div>
      )}

      {screen.name === "list" && (
        <TestList
          projectName={opened.name}
          onCreate={() => setScreen({ name: "compose" })}
          onRun={(testId) => startRun(testId)}
          pendingRunId={pendingRun}
          onRefreshSessions={refreshActive}
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

      {/*
        006 — 편집 화면. 진입점 3개(목록 행 메뉴, 결과 화면 「Step nn 고치기」, 주소)가
        모두 이 **한 화면**으로 온다 (FR-179). 실행 진입과 세션 이동은 005 가 만든
        단일 경로(`startRun`·`openSession`)를 그대로 쓴다 — 화면마다 새로 만들면
        U-01·U-06 이 되살아난다.
      */}
      {screen.name === "definition" && (
        <EditView
          testId={screen.testId}
          focusStepId={screen.focusStepId ?? null}
          onRun={(testId, fromStepIndex) => startReplay(testId, fromStepIndex)}
          onOpenBrowserAt={(testId, stepIndex, stepId) =>
            openBrowserAt(testId, stepIndex, stepId)
          }
          onOpenSession={openSession}
          /* 007 FR-239 — 편집 ↔ 결과 왕복에서도 보던 Step 을 잃지 않는다. */
          onShowResult={(testId, stepId) =>
            setScreen({ name: "result", testId, focusStepId: stepId ?? null })
          }
          runPending={pendingRun !== null}
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

      {screen.name === "compose" && (
        <ComposeView
          project={opened}
          onCancel={() => setScreen({ name: "list" })}
          /*
            **세션 생성 경로를 새로 만들지 않는다** (FR-248 · 005 U-01·U-06).
            아래 두 호출은 1회차에 `CreateTest`·`AiCompose` 가 부르던 것과 같다 —
            화면이 하나로 합쳐졌을 뿐 경로는 그대로다.
          */
          onRecord={(startUrl) => {
            void sessions
              .create({ mode: "record", start_url: startUrl })
              .then((session) => setScreen({ name: "runner", session }))
              .catch((exc: unknown) => setError(describeError(exc)));
          }}
          onStartAi={(startUrl, aiInstruction) => {
            void sessions
              .create({ mode: "ai", start_url: startUrl, ai_instruction: aiInstruction })
              .then((session) => setScreen({ name: "runner", session, aiInstruction }))
              .catch((exc: unknown) => setError(describeError(exc)));
          }}
        />
      )}

      {screen.name === "runner" && (
        <SessionScreen
          initial={screen.session}
          aiInstruction={screen.aiInstruction ?? null}
          /* 009 FR-291 — 목표 자리에 도착하면 기록을 켠다 */
          recordOnArrival={screen.recordOnArrival ?? false}
          /*
            006 FR-204 — 편집 화면에서 출발한 세션은 그 화면으로 돌아온다. 편집 화면은
            마운트마다 `GET /definition` 을 다시 읽으므로 세션에서 저장한 내용이 반영된
            상태로 보인다.
          */
          onFinished={() => {
            const back = screen.returnToEdit;
            setScreen(
              back
                ? {
                    name: "definition",
                    testId: back.testId,
                    focusStepId: back.stepId,
                  }
                : { name: "list" },
            );
          }}
          onShowResult={(testId, stepId) =>
            setScreen({ name: "result", testId, focusStepId: stepId ?? null })
          }
          onRerun={(testId, fromStepIndex) => startReplay(testId, fromStepIndex)}
        />
      )}

      {screen.name === "result" && (
        <ResultView
          testId={screen.testId}
          focusStepId={screen.focusStepId ?? null}
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
