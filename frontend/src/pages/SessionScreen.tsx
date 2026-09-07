/**
 * 세션 화면 호스트. **화면 선택과 세션 상태를 분리한다** (DC-008 · research R2).
 *
 * 001 에서는 `Runner.tsx` 하나가 세션 상태 조합으로 네 화면을 그렸다. 그 얽힘 때문에
 * `ai_error` 를 렌더하는 유일한 컴포넌트가 `isAiSession` 조건 뒤에 숨었고, 실패가 상태에
 * 담겨도 화면에 도달하지 못했다 — 사용자에게는 "아무 일도 일어나지 않음" 으로 보였다.
 *
 * 이 파일이 **구독·상태·명령을 전부 소유**하고, 확정 디자인 4종에 대응하는 페이지
 * 컴포넌트 중 **정확히 하나**를 고른다. 페이지는 표시만 한다.
 *
 *   Main.dc.html         → Runner
 *   RunnerPaused.dc.html → RunnerPaused
 *   Takeover.dc.html     → Takeover
 *   AiRecord.dc.html     → AiRecord
 *
 * **AI 세션 판정은 `authoring_mode` 로 한다** — `view.state` 가 아니다. 그것이 세션의
 * 불변 속성이고, 상태가 `paused` 로 바뀌어도 AI 화면과 실패 사유가 유지된다 (DR-020).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorNotice, describeError, fromEvent, localError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import {
  sessions,
  type AddAssertionBody,
  type AiChoice,
  type RepickSlot,
  type RunPacing,
  type SessionView,
  type TabsResponse,
} from "../api/client";
import {
  subscribeSessionEvents,
  type SessionEvent,
  type SessionSubscription,
} from "../api/ws";
import { LiveConnectionBanner } from "../components/LiveConnectionBanner";
import { MirrorView, type MirrorPhase } from "../components/MirrorView";
import { SessionLostBanner } from "../components/SessionLostBanner";
import { StartingIndicator } from "../components/StartingIndicator";
import { StepInspector } from "./StepInspector";
import { TabStrip } from "../components/TabStrip";
import type { StepOutcome } from "../components/design/DesignStepList";
import type { Step } from "../types/generated/step";
import type { Outcome } from "../types/generated/run-result";
import { AiRecord, type AiBlockedState } from "./AiRecord";
import { PacingControl } from "../components/PacingControl";
import { Runner } from "./Runner";
import { RunnerPaused } from "./RunnerPaused";
import { Takeover } from "./Takeover";
import { progressLabel, runSummary } from "../lib/wording";


/**
 * 끊김을 알리기까지 기다리는 시간. 재연결이 700ms 마다 일어나므로 짧은 끊김은
 * 배너가 깜빡이기만 하고 정보를 주지 않는다. 이 시간을 넘겨 못 붙으면 사용자가
 * 알아야 하는 끊김이다.
 */
const OFFLINE_NOTICE_DELAY_MS = 1500;

const MANIPULATION_STATES = new Set(["recording", "takeover_recording"]);
const OBSERVATION_STATES = new Set(["replaying", "ai_running"]);
/** 세션이 살아 있지 않은 상태. `review` 는 여기 없다 — 편집·저장을 받는다 (DR-010). */
const TERMINAL_STATES = new Set(["completed", "failed", "stopped", "lost"]);
/** 중지 후 검토 상태. 브라우저는 없지만 Step 은 살아 있다 (contracts §6). */
const REVIEW_STATE = "review";
/**
 * **브라우저는 없지만 기록은 살아 있는 상태** (DR-015).
 *
 * `lost` 는 종료 상태이면서도 서버가 Step 을 보존하고 `SAVE` 를 허용한다. 검토(`review`)와
 * 처지가 같으므로 같은 화면이 맡는다 — 이전에는 저장 상자가 없는 Main 화면으로 보내
 * "기록된 Step 은 보존됐습니다" 라고 적어 두고 저장할 방법을 주지 않았다.
 */
const SAVEABLE_WITHOUT_BROWSER = new Set([REVIEW_STATE, "lost"]);

interface StepProgress {
  outcome?: "pass" | "fail";
  durationMs?: number;
}

export interface SessionScreenProps {
  initial: SessionView;
  /** AI 세션이면 사용자가 준 지시문 원문. 화면에만 쓴다 — 저장은 하지 않는다 (FR-063). */
  aiInstruction?: string | null;
  onFinished: () => void;
  onShowResult?: (testId: string) => void;
  /** 다시 실행 — 이 세션을 버리고 같은 테스트로 새 세션을 연다 (UX U-02). */
  onRerun?: (testId: string, fromStepIndex?: number) => void;
}

export function SessionScreen({
  initial,
  aiInstruction = null,
  onFinished,
  onShowResult,
  onRerun,
}: SessionScreenProps) {
  const [view, setView] = useState<SessionView>(initial);
  const [tabs, setTabs] = useState<TabsResponse | null>(null);
  const [frame, setFrame] = useState<string | null>(null);
  const [mirrorTab, setMirrorTab] = useState<number>(initial.mirrored_tab_index);
  const [mirrorStopped, setMirrorStopped] = useState<string | null>(null);
  const [mirrorDegraded, setMirrorDegraded] = useState<string | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [lost, setLost] = useState<string | null>(null);
  const [runningIndex, setRunningIndex] = useState<number | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  /** 실패한 Step 의 사유. 실행이 끝난 화면이 이유를 말하려면 이것을 잡아 둬야 한다 (UX U-02). */
  const [failure, setFailure] = useState<{ index: number; message: string } | null>(null);
  const [saveName, setSaveName] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionId = initial.session_id;
  const [progress, setProgress] = useState<Record<string, StepProgress>>({});
  const durations = useRef<Record<string, number>>({});
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [repickWaiting, setRepickWaiting] = useState<RepickSlot | null>(null);
  const [notice, setNotice] = useState<ErrorInfo | null>(null);
  const [confirmingLeave, setConfirmingLeave] = useState(false);
  /**
   * 끝난 실행 화면을 닫기 전 확인 (005 FR-148 · U-08).
   *
   * 미저장 변경이 없으면 확인 없이 세션을 폐기했다. 저장된 테스트의 재실행에는 미저장
   * 변경이 없으므로 **항상** 무확인 경로를 탔고, 그 클릭 한 번으로 결과 화면에 도달할
   * 길이 사라졌다.
   */
  const [confirmingClose, setConfirmingClose] = useState(false);
  const [aiMessages, setAiMessages] = useState<string[]>([]);
  const [aiError, setAiError] = useState<ErrorInfo | null>(null);
  const [aiBlocked, setAiBlocked] = useState<AiBlockedState | null>(null);
  /**
   * 속도 변경을 취향 파일에 남겼는가 (004).
   *
   * 남기지 못해도 속도 자체는 바뀌었으므로 실행을 막지 않는다. 다만 조용히 넘기지도
   * 않는다 — 다음 실행에 유지되지 않는다는 사실을 사용자가 알아야 한다.
   */
  const [pacingSaved, setPacingSaved] = useState(true);
  /**
   * 일시정지 요청을 보냈고 아직 확정되지 않았다 (005 FR-142 · U-04).
   *
   * **응답을 기다리지 않고 즉시 켠다.** `POST /pause` 는 Step 경계를 최대 10초 기다린
   * 뒤 응답하므로, 응답을 기다리면 그 10초간 화면이 아무 말도 못 한다. 리포트가 본
   * 것은 그것보다 나빴다 — 화면은 0.12초에 이미 `PAUSED` 라고 말했고 모든 버튼이
   * 비활성이었으며 실측 19초간 실행이 계속됐다.
   *
   * 확정은 응답의 `pause_settled` 가 한다.
   */
  const [pauseRequested, setPauseRequested] = useState(false);
  /** 중지 요청이 진행 중인가 (005 FR-147). 「중지 중…」 전이 상태의 근거다. */
  const [stopRequested, setStopRequested] = useState(false);
  const [live, setLive] = useState(true);
  const [showOffline, setShowOffline] = useState(false);
  const subscription = useRef<SessionSubscription | null>(null);

  const resync = useCallback(async () => {
    try {
      setView(await sessions.get(sessionId));
      setTabs(await sessions.tabs(sessionId));
    } catch (exc) {
      setError(describeError(exc));
    }
  }, [sessionId]);

  useEffect(() => {
    const sub = subscribeSessionEvents(sessionId, {
      onResync: () => void resync(),
      onConnectionChange: setLive,
      onEvent: (event: SessionEvent) => {
        switch (event.type) {
          case "mirror_frame":
            setFrame(event.data);
            setMirrorStopped(null);
            break;
          case "mirror_tab_changed":
            setMirrorTab(event.tab);
            break;
          case "mirror_degraded":
            setMirrorDegraded(event.reason ?? null);
            break;
          case "mirror_stopped":
            setMirrorStopped(event.reason ?? "미러가 중단됐습니다.");
            break;
          case "session_lost":
            setLost(event.reason ?? "브라우저 세션이 유실됐습니다.");
            void resync();
            break;
          case "step_started":
            setRunningIndex(event.index);
            break;
          case "step_finished": {
            const stepId = event.step_id;
            const durationMs = event.duration_ms;
            durations.current[stepId] = durationMs;
            setProgress((prev) => ({
              ...prev,
              [stepId]: { outcome: event.outcome as "pass" | "fail", durationMs },
            }));
            setRunningIndex(null);
            break;
          }
          case "step_failed":
            // 예전에는 default 로 흘러 전체 상태만 다시 받았다 — 사유는 어디에도 남지
            // 않았고, 실행이 끝난 화면은 빨간 ✕ 만 보여줬다 (UX U-02).
            setFailure({ index: event.index, message: event.error_message });
            setRunningIndex(null);
            break;
          case "run_finished":
            setRunningIndex(null);
            // 005 FR-140·FR-141 (U-19·U-20·U-03) — 요약을 **사전에서 받는다.**
            //
            // 이전에는 여기서 `outcome === "pass" ? "PASS" : "FAIL"` 로 조립했다.
            // 결말이 넷으로 늘어난 뒤에도 이 줄이 남아 있어서, 사용자가 누른 중지가
            // 실행 화면에서 `FAIL` 로 보였다 — 저장된 결과는 `stopped` 인데 화면만
            // 실패라고 말하는, 005 가 없애려던 바로 그 어긋남이다.
            setSummary(
              runSummary({
                outcome: event.outcome as Outcome,
                passedCount: event.passed_count,
                attemptedCount: event.attempted_count ?? event.total_count,
                totalCount: event.total_count,
                totalMs: event.total_ms,
                scope: event.scope ?? null,
                startIndex: event.start_index ?? null,
                failedStepIndex: event.failed_step_index,
                stoppedStepIndex: event.stopped_step_index ?? null,
              }),
            );
            void resync();
            break;
          case "run_error":
            // 실행이 끝났는데 결과를 남기지 못한 경우 — 조용히 넘기면 실행이 없었던
            // 것처럼 보인다 (contracts/websocket.md §진단 이벤트).
            // 서버가 계약 본문을 실어 보내면 그것을 쓴다 (003 EC-008). 없으면
            // 실시간 통로가 아직 옛 형태인 경우이므로 다음 행동을 화면이 붙인다.
            setError(fromEvent(event.error, event.reason,
              "이 실행의 결과는 남지 않았습니다. 다시 실행하거나 Step을 확인하세요."));
            break;
          case "pacing_changed":
            // 다른 창에서 바꾼 속도를 반영한다. 값 자체는 전체 상태 동기화로 오므로
            // 여기서는 취향 저장 여부만 잡아 둔다 — 그것은 세션 뷰에 없는 정보다.
            setPacingSaved(event.preference_saved);
            void resync();
            break;
          case "artifact_note":
            // 산출물 일부를 남기지 못한 사유. 실행 자체는 유효하므로 오류로 다루지 않는다.
            setNotes((prev) =>
              prev.includes(event.message) ? prev : [...prev, event.message],
            );
            break;
          case "tab_limit_reached":
            setError(
              localError(
                event.message ?? "탭 상한에 도달했습니다.",
                "쓰지 않는 탭을 닫은 뒤 다시 시도하세요.",
              ),
            );
            break;
          case "edit_warning":
            void resync();
            break;
          case "ai_progress":
            setAiMessages((prev) => [...prev, event.message]);
            break;
          case "ai_blocked":
            // 세션은 유지된다. 사용자가 4선택지 중 하나를 고를 때까지 기다린다 (FR-069).
            setAiBlocked({
              attempted: event.attempted ?? null,
              reason: event.reason ?? "AI 가 더 진행하지 못했습니다.",
              choices: (event.choices ?? []) as AiChoice[],
            });
            void resync();
            break;
          case "ai_error":
            // 실패해도 Step 은 보존된다 (FR-067).
            //
            // **진행 로그에도 남긴다** (002). 렌더 조건이 하나 어긋나도 사용자가 볼
            // 경로가 둘이 되게 한다 — 001 에서는 이 값이 상태에만 담기고 그것을 그리는
            // 컴포넌트가 세션 상태 조건 뒤에 숨어 화면에 도달하지 못했다 (research R2).
            setAiError(
              localError(
                event.reason,
                "다시 시도하거나, 직접 이어받아 Step을 만들 수 있습니다. 기록된 Step은 남아 있습니다.",
              ),
            );
            setAiMessages((prev) => [...prev, `실패: ${event.reason}`]);
            void resync();
            break;
          case "ai_finished":
            setAiBlocked(null);
            void resync();
            break;
          case "step_updated":
            // 다시 집기 결과가 도착했다 (FR-020). 대기 표시를 내린다.
            setRepickWaiting(null);
            void resync();
            break;
          default:
            // step_added·step_removed·state_changed 등은 전체 상태를 다시 받는다.
            // 로컬 도구이므로 이것이 싸고, 부분 갱신 버그가 생기지 않는다.
            void resync();
        }
      },
    });
    subscription.current = sub;
    return () => {
      subscription.current = null;
      sub.stop();
    };
  }, [sessionId, resync]);

  // 짧은 끊김으로 배너가 깜빡이지 않게 유예를 둔다. 붙는 순간 즉시 걷는다.
  useEffect(() => {
    if (live) {
      setShowOffline(false);
      return;
    }
    const timer = setTimeout(() => setShowOffline(true), OFFLINE_NOTICE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [live]);

  const act = async (fn: () => Promise<SessionView>) => {
    setBusy(true);
    setError(null);
    try {
      setView(await fn());
    } catch (exc) {
      setError(describeError(exc));
    } finally {
      setBusy(false);
    }
  };

  /**
   * 실행 속도 변경 (004 FR-103).
   *
   * **낙관적으로 반영하지 않는다.** 서버가 돌려주는 세션 뷰가 권위이며, 실패하면 이전
   * 값이 그대로 보여야 한다 — 화면이 먼저 바뀌면 사용자는 적용되지 않은 속도를 적용된
   * 것으로 믿는다.
   */
  const changePacing = (next: RunPacing) => {
    setPacingSaved(true);
    void act(() => sessions.setPacing(sessionId, next));
  };

  /** 편집 요청 공통 처리. 실패 사유를 알리되 화면을 떠나지 않는다 (FR-081). */
  const edit = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await resync();
    } catch (exc) {
      setNotice(describeError(exc));
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    setBusy(true);
    void sessions
      .save(sessionId, saveName.trim())
      .then(() => {
        // 005 FR-158 (U-09) — 성공 시 이전 오류 배너를 걷어낸다.
        //
        // 리포트는 저장 성공 시점에 앞선 경고("세션을 찾을 수 없습니다: …")가 그대로
        // 남아 있어 **새로 뜬 것이 없다는 인상이 더 강해지는** 것을 봤다.
        setError(null);
        setNotice(null);
        return resync();
      })
      // 005 FR-157 — 실패는 사실과 사유를 화면에 남긴다.
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  // ─── 상태 판정 ────────────────────────────────────────────────────────────

  /** **`authoring_mode` 로 판정한다** — 세션의 불변 속성이다 (research R2·DR-020). */
  const isAiSession = view.authoring_mode === "ai";
  const isPaused = view.state === "paused";
  /**
   * 005 FR-142~FR-146 — 일시정지 **전이 중**인가 (U-04).
   *
   * 두 근거를 함께 본다.
   * - `pauseRequested`: 우리가 방금 요청을 보냈다(낙관적 표시)
   * - `pause_settled === false`: 서버가 아직 Step 경계에 닿지 않았다고 말한다
   *
   * 둘 중 하나라도 참이면 전이 중이다. 낙관적 표시만 쓰면 응답이 온 뒤 새로고침한
   * 화면이 전이 사실을 잃고, 서버 값만 쓰면 요청 직후 최대 10초간 화면이 침묵한다.
   */
  const isPausing =
    (pauseRequested || view.pause_settled === false) && !TERMINAL_STATES.has(view.state);
  /**
   * 멈추기 전에 실행이 끝났다 (005 FR-146).
   *
   * 실행 결말과 세션 상태는 **다른 축**이다. 실행은 끝났고(요약 있음) 세션은 일시정지다
   * (브라우저 살아 있음, 편집 가능) — 둘 다 참이다. 이전 화면은 그 관계를 설명하지
   * 않아 `PAUSED` 배지와 `FAIL` 요약이 나란히 떠 있었다.
   */
  const finishedWhilePausing = isPaused && summary !== null;
  /** 브라우저 없이 검토·저장만 가능한 상태 — `review` 와 `lost` (DR-015). */
  const isSaveableWithoutBrowser = SAVEABLE_WITHOUT_BROWSER.has(view.state);
  const isTakeover = view.state === "takeover_recording" || view.state === "ai_blocked";
  const isManipulating = MANIPULATION_STATES.has(view.state);
  const isObserving = OBSERVATION_STATES.has(view.state);
  const isDone = TERMINAL_STATES.has(view.state);
  const testId = view.test_id;
  const currentIndex = runningIndex ?? view.current_step_index;

  // 저장하지 않은 기록이 있는 동안 새로고침·닫기를 한 번 묻는다 (UX U-05). 서버의 세션은
  // 남지만 화면이 사라지면 사용자는 기록이 사라진 줄 안다 — 새로고침은 막혔다고 느낄 때
  // 가장 먼저 누르는 키다.
  useEffect(() => {
    if (!view.has_unsaved_changes || isDone) return;
    const guard = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [view.has_unsaved_changes, isDone]);

  /**
   * AI 화면이 지금 그려지는가.
   *
   * 이것을 이름으로 두는 이유는 **AI 실패 사유가 이 조건 뒤에 갇히지 않게** 하려는
   * 것이다. 001 은 `ai_error` 를 렌더하는 유일한 컴포넌트가 `isAiSession` 뒤에 있어
   * 실패가 화면에 닿지 못했다. 002 가 그것을 고쳤지만 구멍이 옮겨졌을 뿐이다 —
   * AI 수행이 실패하면 세션이 검토를 위해 `paused` 로 가고, 그러면 이 조건이 거짓이
   * 되어 다시 사유가 사라진다 (003 AP-032·DR-020).
   */
  const showsAiScreen = isAiSession && !isPaused && !isTakeover;

  const phase: MirrorPhase = isManipulating
    ? "manipulation"
    : isPaused
      ? "paused"
      : isDone || isSaveableWithoutBrowser
        ? "terminated"
        : "observation";

  /**
   * 005 FR-171 (U-18·U-05) — 이벤트를 못 받은 화면도 결과를 복원한다.
   *
   * Step별 결과가 WebSocket 이벤트로만 채워지는 화면 로컬 상태에 있어서, 화면을 다시
   * 그리면 모든 Step 이 빈 체크박스가 됐다. 같은 뿌리가 "실패한 Step 이 화면에서
   * 지워지는" 증상이다 — 실패 이벤트를 놓친 화면은 실패가 없었던 것처럼 보인다.
   *
   * 실시간 이벤트를 **우선한다.** 세션 뷰는 폴링 시점의 스냅샷이므로 방금 온 이벤트보다
   * 오래됐을 수 있다.
   */
  const restored = new Map(
    (view.step_results ?? []).map((r) => [r.step_id, r] as const),
  );

  const outcomeOf = (step: Step, index: number): StepOutcome => {
    const recorded = progress[step.id]?.outcome;
    if (recorded !== undefined) return recorded;
    const fromView = restored.get(step.id)?.outcome;
    if (fromView !== undefined && fromView !== "not_run") return fromView;
    if (runningIndex === index) return "running";
    return "pending";
  };
  const durationOf = (step: Step) =>
    durations.current[step.id] ?? restored.get(step.id)?.duration_ms;

  const mirror =
    view.state === "starting" ? (
      <StartingIndicator />
    ) : (
      <MirrorView
        frame={frame}
        phase={phase}
        stoppedReason={mirrorStopped}
        degradedReason={mirrorDegraded}
        tabIndex={mirrorTab}
      />
    );

  const tabStrip =
    tabs !== null ? (
      <TabStrip
        tabs={tabs.tabs}
        mirroredTabIndex={mirrorTab}
        maxTabs={tabs.max_tabs}
        onSelect={(index) => {
          void sessions
            .setMirrorTab(sessionId, index)
            .then((next) => {
              setTabs(next);
              setMirrorTab(next.mirrored_tab_index);
            })
            .catch(() => undefined);
        }}
      />
    ) : undefined;

  /**
   * DR-014 — 저장하지 않은 기록이 있는데 나가려 하면 확인을 받는다.
   *
   * **중지는 화면을 떠나지 않는다** (DR-010). 서버가 세션을 `review` 로 남기므로
   * Step 을 계속 보고 저장할 수 있다. 떠나는 것은 별개의 조작이다.
   */
  const stop = () => void act(() => sessions.stop(sessionId));

  const leave = () => {
    if (view.has_unsaved_changes && view.steps.length > 0) {
      setConfirmingLeave(true);
      return;
    }
    // 005 FR-148 — 끝난 실행을 닫는 것은 **결과 접근을 끊을 수 있는** 조작이다.
    // 한 번 묻고, 결과를 다시 볼 경로를 안내한다. FR-130 으로 목록의 「결과 보기」가
    // 결말과 무관하게 항상 있으므로 그 안내가 사실이다.
    if (TERMINAL_STATES.has(view.state) && testId !== null) {
      setConfirmingClose(true);
      return;
    }
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(onFinished);
  };

  const closeConfirmed = () => {
    setConfirmingClose(false);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(onFinished);
  };

  /** 이 세션을 버리고 다시 실행한다. 같은 테스트에 세션이 둘일 수는 없다 (FR-043). */
  const rerun = (fromStepIndex?: number) => {
    if (testId === null || onRerun === undefined) return;
    setBusy(true);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(() => onRerun(testId, fromStepIndex));
  };

  const leaveConfirmed = () => {
    setConfirmingLeave(false);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(onFinished);
  };

  const saveAndLeave = () => {
    setBusy(true);
    void sessions
      .save(sessionId, saveName.trim())
      .then(() => {
        setConfirmingLeave(false);
        onFinished();
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  const banners = (
    <>
      {/* 끊김을 맨 위에 둔다 — 아래 화면이 낡았다는 사실을 먼저 알아야 한다. */}
      {showOffline && (
        <LiveConnectionBanner onReconnect={() => subscription.current?.reconnect()} />
      )}
      {error !== null && <ErrorNotice error={error} />}
      {/*
        003 AP-032·DR-020 — **AI 실패 사유를 화면에 붙들어 둔다.**
        AI 화면이 이것을 스스로 그리지만, 실패한 세션은 검토를 위해 `paused` 로 옮겨가
        그 화면을 떠난다. 여기서 한 번 더 내보내지 않으면 사용자에게는 "아무 일도
        일어나지 않음" 으로 보인다 — 그 화면이 실패를 말하는 유일한 자리였기 때문이다.
        AI 화면이 그리는 동안은 두 번 나오지 않게 막는다.
      */}
      {aiError !== null && !showsAiScreen && <ErrorNotice error={aiError} />}
      {/* 지시문도 같은 이유로 붙들어 둔다 (UX U-07). AI 화면을 떠난 순간 사용자가 무엇을
          시켰는지가 화면에서 사라지면, 실패 없이 다른 모드로 갈아탄 것처럼 보인다. */}
      {isAiSession && !showsAiScreen && aiInstruction !== null && aiInstruction !== "" && (
        <Banner tone="info">AI 지시문: {aiInstruction}</Banner>
      )}
      {lost !== null && (
        <SessionLostBanner
          reason={lost}
          stepCount={view.steps.length}
          busy={busy}
          // 저장은 검토 화면의 저장 상자가 맡는다 — 배너에는 이름 입력이 없어
          // 여기에 저장 버튼을 두면 이름 없이 누르게 된다 (DR-015).
          onClose={leave}
        />
      )}
      {view.recorder_warnings.map((w) => (
        <Banner key={w} tone="warn">
          {w}
        </Banner>
      ))}
      {notice !== null && (
        <Banner tone="warn" onDismiss={() => setNotice(null)}>
          <ErrorNotice error={notice} compact />
        </Banner>
      )}
      {notes.map((n) => (
        <Banner key={n} tone="info">
          {n}
        </Banner>
      ))}
      {/*
        005 FR-140 (U-19) — 결말 요약은 **한 화면에 한 번만** 나온다.

        이전에는 이 얇은 띠와 아래 결말 바에 같은 문장이 동시에 있었다. 같은 값이 두 번
        나오면 사용자는 둘이 다른 것인지 확인하느라 멈추고, 세로 공간도 배너 쌓임과 겹쳐
        Step 목록을 밀어냈다(중지 직후에는 배너 3개 + 요약 2개로 Step 이 2개만 보였다).

        확정 디자인(docs/design/Main.dc.html)에 얇은 띠는 정의돼 있지 않다 — 구현 과정에서
        쌓인 것이다. 끝난 실행에서는 결말 바가 요약을 갖는다.
      */}
      {summary !== null && !isDone && <Banner tone="info">{summary}</Banner>}
    </>
  );

  const overlays = (
    <>
      {confirmingLeave && (
        <LeaveConfirm
          stepCount={view.steps.length}
          saveName={saveName}
          busy={busy}
          onSaveNameChange={setSaveName}
          onSave={saveAndLeave}
          onDiscard={leaveConfirmed}
          onCancel={() => setConfirmingLeave(false)}
        />
      )}
      {confirmingClose && (
        <div
          role="dialog"
          aria-label="실행 화면 닫기 확인"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(20, 19, 15, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 20,
          }}
        >
          <div
            style={{
              width: 520,
              border: "3px solid #14130F",
              background: "#FFFDF6",
              boxShadow: "10px 10px 0 #14130F",
              padding: 24,
            }}
          >
            <div
              style={{
                fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
                fontSize: 24,
              }}
            >
              실행 화면을 닫습니다
            </div>
            <p style={{ color: "#6B675C" }}>
              결과는 목록의 「결과 보기」에서 다시 볼 수 있습니다.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
              <button className="secondary" onClick={() => setConfirmingClose(false)}>
                돌아가기
              </button>
              <button onClick={closeConfirmed}>닫기</button>
            </div>
          </div>
        </div>
      )}
      {inspecting && selectedStepId !== null && (
        <StepInspectorOverlay
          steps={view.steps}
          selectedStepId={selectedStepId}
          busy={busy}
          repickWaiting={repickWaiting}
          onClose={() => setInspecting(false)}
          onSave={(patch) => void edit(() => sessions.patchStep(sessionId, selectedStepId, patch))}
          onRepick={(slot) => {
            setRepickWaiting(slot);
            void sessions
              .repick(sessionId, selectedStepId, { slot })
              .then((resp) => {
                setNotice(localError(resp.message, "표시된 내용을 확인한 뒤 이어서 진행하세요."));
                if (!resp.waiting) setRepickWaiting(null);
                return resync();
              })
              .catch((exc: unknown) => {
                setRepickWaiting(null);
                setNotice(describeError(exc));
              });
          }}
        />
      )}
    </>
  );

  const shared = {
    testId: testId ?? "새 테스트",
    steps: view.steps,
    outcomeOf,
    durationOf,
    busy,
    mirror,
    tabs: tabStrip,
    banners,
    currentUrl: tabs?.tabs[mirrorTab]?.url ?? "",
    mirroredTab: mirrorTab,
    selectedStepId,
    onSelectStep: (stepId: string) => setSelectedStepId(stepId),
  };

  // ─── 화면 선택 — 정확히 하나를 고른다 (DC-008) ────────────────────────────

  if (showsAiScreen) {
    return (
      <>
        <AiRecord
          instruction={aiInstruction ?? ""}
          running={view.state === "ai_running"}
          steps={view.steps}
          messages={aiMessages}
          error={aiError}
          blocked={aiBlocked}
          busy={busy}
          saveName={saveName}
          onSaveNameChange={setSaveName}
          onSave={save}
          onPause={view.state === "ai_running" ? () => void act(() => sessions.pause(sessionId)) : undefined}
          onStop={isDone || isSaveableWithoutBrowser ? leave : stop}
          mirror={mirror}
          currentUrl={shared.currentUrl}
        />
        {banners}
        {overlays}
      </>
    );
  }

  if (isTakeover) {
    return (
      <>
        <Takeover
          {...shared}
          title={testId ?? "새 테스트"}
          blocked={aiBlocked}
          recording={view.state === "takeover_recording"}
          onChoose={(choice) => {
            setAiBlocked(null);
            void act(() => sessions.aiChoice(sessionId, choice));
          }}
          onStopRecording={() => void act(() => sessions.recordActionsStop(sessionId))}
          // 001 FR-076 — 사람이 이어받은 뒤 AI 가 남은 지시를 이어서 맡는다.
          onResume={
            view.state === "takeover_recording"
              ? () => void act(() => sessions.resume(sessionId))
              : undefined
          }
          onStop={leave}
        />
        {overlays}
      </>
    );
  }

  if (isPaused || isSaveableWithoutBrowser) {
    return (
      <>
        <RunnerPaused
          {...shared}
          title={testId ?? "새 테스트"}
          authoring={view.authoring_mode}
          review={isSaveableWithoutBrowser}
          savedAt={view.saved_at ?? null}
          /*
            005 FR-156 — 저장할 변경이 남아 있는가. 저장 직후에는 거짓이므로 「변경
            저장」이 비활성이 되고, 사용자는 같은 내용을 다시 저장하도록 유도받지 않는다.
          */
          hasChangesToSave={view.saved_at === null || view.has_unsaved_changes}
          onShowList={onFinished}
          pausing={isPausing}
          pausingBudgetMs={view.steps[currentIndex]?.timeout_ms ?? null}
          finishedWhilePausing={
            finishedWhilePausing
              ? {
                  summary: `멈추기 전에 실행이 끝났습니다 · ${summary ?? ""}`,
                  failureReason: failure?.message ?? null,
                  onShowResult:
                    testId !== null && onShowResult !== undefined
                      ? () => onShowResult(testId)
                      : undefined,
                }
              : null
          }
          stopResult={
            view.state === "review"
              ? {
                  summary: summary ?? view.state_label,
                  stoppedStepIndex: view.current_step_index,
                  onRerunAll:
                    testId !== null && onRerun !== undefined ? () => rerun() : undefined,
                  onRerunFromStop:
                    testId !== null && onRerun !== undefined
                      ? () => rerun(view.current_step_index)
                      : undefined,
                  onBack: leave,
                }
              : null
          }
          currentStepIndex={view.current_step_index}
          editWarnings={view.edit_warnings}
          reordering={reordering}
          saveName={saveName}
          onSaveNameChange={setSaveName}
          onSave={save}
          onResume={() => void act(() => sessions.resume(sessionId))}
          onStop={leave}
          onRecordActionsStart={() => void act(() => sessions.recordActionsStart(sessionId))}
          onRecordActionsStop={() => void act(() => sessions.recordActionsStop(sessionId))}
          onAddAssertion={(body: AddAssertionBody) => void edit(() => sessions.addAssertion(sessionId, body))}
          onEditStep={(stepId) => {
            setSelectedStepId(stepId);
            setInspecting(true);
          }}
          onToggleReorder={() => setReordering((v) => !v)}
          onApplyReorder={(order) => {
            void edit(() => sessions.reorderSteps(sessionId, order));
            setReordering(false);
          }}
          onRunFrom={(stepIndex) => void act(() => sessions.runFrom(sessionId, stepIndex))}
          onDeleteStep={(stepId) => void edit(() => sessions.deleteStep(sessionId, stepId))}
          onNaturalLanguage={(instruction) => {
            setBusy(true);
            setNotice(null);
            void sessions
              .aiStep(sessionId, instruction)
              .then((resp) => {
                setNotice(localError(resp.message, "표시된 내용을 확인한 뒤 이어서 진행하세요."));
                return resync();
              })
              .catch((exc: unknown) => setNotice(describeError(exc)))
              .finally(() => setBusy(false));
          }}
          onShowResult={
            testId !== null && onShowResult && isDone ? () => onShowResult(testId) : undefined
          }
          pacing={view.pacing}
          pacingControl={
            <PacingControl
              value={view.pacing}
              busy={busy}
              preferenceSaved={pacingSaved}
              onChange={changePacing}
            />
          }
        />
        {overlays}
      </>
    );
  }

  return (
    <>
      <Runner
        {...shared}
        title={testId ?? "새 테스트"}
        /*
          005 FR-139 (U-14) — 끝난 실행에서는 진행 표시를 쓰지 않는다.

          step 06 에서 실패해 07 이 돌지 않았는데 헤더가 `step 07 / 07` 이면 전부 처리한
          것으로 읽힌다. 실패 Step 번호는 아래 요약에서 따로 찾아야 했다.
        */
        progressLabel={
          isDone && summary !== null
            ? summary
            : progressLabel(currentIndex, view.steps.length)
        }
        statusLabel={isObserving ? "RUNNING" : view.state_label}
        authoring={view.authoring_mode}
        canPause={!isDone}
        pacing={
          <PacingControl
            value={view.pacing}
            busy={busy}
            disabled={isDone}
            preferenceSaved={pacingSaved}
            /*
              005 FR-174 (U-23) — 녹화·인수 국면에서는 「다음 실행 속도」로 밝힌다.
              지금 실행에 쓰이는 값이 아니라는 사실을 라벨이 말한다.
            */
            manipulationPhase={isManipulating}
            onChange={changePacing}
          />
        }
        onPause={() => {
          // 005 FR-142 — 요청 즉시 전이 표시를 켠다. 응답이 오면 아래 effect 가
          // `pause_settled` 로 확정하거나 걷는다.
          setPauseRequested(true);
          void act(() => sessions.pause(sessionId)).finally(() => {
            // 응답이 실패해도 전이 표시를 걷는다. 남기면 정지하지 않았는데
            // 「일시정지 중…」이 영구히 붙는다 (plan 위험표).
            setPauseRequested(false);
          });
        }}
        /*
          005 FR-147 (U-08) — 실행 중 「중지」와 종료 후 「닫기」는 **다른 버튼**이다.

          이전에는 같은 위치의 같은 라벨이 두 동작을 가졌다. 종료 후에도 「중지」만
          활성으로 남아 화면에서 가장 눈에 띄는 컨트롤이었고, 누르면 확인 없이 세션을
          폐기하며 목록으로 튀었다. PASS 한 실행의 결과는 목록에서 열 수 없었으므로
          (U-13) 그 클릭 한 번으로 결과에 도달할 길이 사라졌다.
        */
        onStop={
          isDone
            ? leave
            : () => {
                setStopRequested(true);
                void Promise.resolve(stop()).finally(() => setStopRequested(false));
              }
        }
        stopLabel={isDone ? "닫기" : stopRequested ? "중지 중…" : "중지"}
        stopDisabled={stopRequested}
        stopEmphasis={!isDone}
        finished={
          isDone
            ? {
                summary: summary ?? view.state_label,
                failureReason: failure?.message ?? null,
                onShowResult:
                  testId !== null && onShowResult !== undefined
                    ? () => onShowResult(testId)
                    : undefined,
                onRerunFromFailure:
                  testId !== null && onRerun !== undefined && failure !== null
                    ? () => rerun(failure.index)
                    : undefined,
                onRerunAll:
                  testId !== null && onRerun !== undefined ? () => rerun() : undefined,
                onBack: leave,
              }
            : undefined
        }
      />
      {overlays}
    </>
  );
}

// ─── 확정 디자인이 정의하지 않은 조각들 (DC-009) ────────────────────────────

function Banner({
  tone,
  children,
  onDismiss,
}: {
  tone: "fail" | "warn" | "info";
  children: React.ReactNode;
  onDismiss?: () => void;
}) {
  const skin =
    tone === "fail"
      ? { background: "#FBEEEA", color: "#A83A22" }
      : tone === "warn"
        ? { background: "#FFF9D6", color: "#14130F" }
        : { background: "#F5F2E9", color: "#6B675C" };
  return (
    <div
      role={tone === "fail" ? "alert" : "status"}
      style={{
        ...skin,
        borderBottom: "3px solid #14130F",
        padding: "10px 24px",
        display: "flex",
        alignItems: "center",
        gap: 12,
        whiteSpace: "pre-wrap",
      }}
    >
      <span style={{ flex: 1 }}>{children}</span>
      {onDismiss && (
        <button className="ghost" onClick={onDismiss}>
          닫기
        </button>
      )}
    </div>
  );
}

function LeaveConfirm({
  stepCount,
  saveName,
  busy,
  onSaveNameChange,
  onSave,
  onDiscard,
  onCancel,
}: {
  stepCount: number;
  saveName: string;
  busy: boolean;
  onSaveNameChange: (v: string) => void;
  onSave: () => void;
  onDiscard: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      role="dialog"
      aria-label="저장하지 않고 나가기 확인"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(20, 19, 15, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 20,
      }}
    >
      <div
        style={{
          width: 520,
          border: "3px solid #14130F",
          background: "#FFFDF6",
          boxShadow: "10px 10px 0 #14130F",
          padding: 24,
        }}
      >
        <div style={{ fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif", fontSize: 24 }}>
          저장하지 않은 기록이 있습니다
        </div>
        <p style={{ color: "#6B675C" }}>
          기록된 Step {stepCount}개가 있습니다. 저장하지 않고 나가면 사라집니다.
        </p>
        <label htmlFor="leave-save-name">테스트 이름</label>
        <input
          id="leave-save-name"
          value={saveName}
          autoFocus
          onChange={(e) => onSaveNameChange(e.target.value)}
          placeholder="프로젝트 생성"
        />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
          <button className="secondary" onClick={onCancel}>
            돌아가기
          </button>
          <button className="danger" disabled={busy} onClick={onDiscard}>
            저장하지 않고 나가기
          </button>
          <button disabled={busy || saveName.trim() === ""} onClick={onSave}>
            저장하고 나가기
          </button>
        </div>
      </div>
    </div>
  );
}

function StepInspectorOverlay({
  steps,
  selectedStepId,
  busy,
  repickWaiting,
  onClose,
  onSave,
  onRepick,
}: {
  steps: Step[];
  selectedStepId: string;
  busy: boolean;
  repickWaiting: RepickSlot | null;
  onClose: () => void;
  onSave: (patch: Record<string, unknown>) => void;
  onRepick: (slot: RepickSlot) => void;
}) {
  const index = steps.findIndex((s) => s.id === selectedStepId);
  const step = steps[index];
  if (index < 0 || step === undefined) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        zIndex: 15,
        display: "flex",
        background: "rgba(20, 19, 15, 0.25)",
        left: 0,
        justifyContent: "flex-end",
      }}
      onClick={onClose}
    >
      {/*
        DC-011 — 창이 확정 디자인의 기준 폭(640px)보다 좁으면 **기준 폭을 유지한 채
        스크롤한다.** 겹침이 `position: fixed` 라 페이지 스크롤이 닿지 않으므로 가로
        스크롤을 여기서 준다. 없으면 좁은 창에서 판이 잘린 채 접근할 수 없다.
      */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ overflowY: "auto", overflowX: "auto", maxWidth: "100%" }}
      >
        <StepInspector
          step={step}
          index={index}
          busy={busy}
          repickWaiting={repickWaiting}
          onClose={onClose}
          onSave={onSave}
          onRepick={onRepick}
        />
      </div>
    </div>
  );
}
