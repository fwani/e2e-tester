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

import {
  ApiError,
  sessions,
  type AddAssertionBody,
  type AiChoice,
  type RepickSlot,
  type SessionView,
  type TabsResponse,
} from "../api/client";
import { subscribeSessionEvents, type SessionEvent } from "../api/ws";
import { MirrorView, type MirrorPhase } from "../components/MirrorView";
import { SessionLostBanner } from "../components/SessionLostBanner";
import { StartingIndicator } from "../components/StartingIndicator";
import { StepInspector } from "./StepInspector";
import { TabStrip } from "../components/TabStrip";
import type { StepOutcome } from "../components/design/DesignStepList";
import type { Step } from "../types/generated/step";
import { AiRecord, type AiBlockedState } from "./AiRecord";
import { Runner } from "./Runner";
import { RunnerPaused } from "./RunnerPaused";
import { Takeover } from "./Takeover";

const MANIPULATION_STATES = new Set(["recording", "takeover_recording"]);
const OBSERVATION_STATES = new Set(["replaying", "ai_running"]);
/** 세션이 살아 있지 않은 상태. `review` 는 여기 없다 — 편집·저장을 받는다 (DR-010). */
const TERMINAL_STATES = new Set(["completed", "failed", "stopped", "lost"]);
/** 중지 후 검토 상태. 브라우저는 없지만 Step 은 살아 있다 (contracts §6). */
const REVIEW_STATE = "review";

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
}

export function SessionScreen({
  initial,
  aiInstruction = null,
  onFinished,
  onShowResult,
}: SessionScreenProps) {
  const [view, setView] = useState<SessionView>(initial);
  const [tabs, setTabs] = useState<TabsResponse | null>(null);
  const [frame, setFrame] = useState<string | null>(null);
  const [mirrorTab, setMirrorTab] = useState<number>(initial.mirrored_tab_index);
  const [mirrorStopped, setMirrorStopped] = useState<string | null>(null);
  const [mirrorDegraded, setMirrorDegraded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [lost, setLost] = useState<string | null>(null);
  const [runningIndex, setRunningIndex] = useState<number | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [saveName, setSaveName] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionId = initial.session_id;
  const [progress, setProgress] = useState<Record<string, StepProgress>>({});
  const durations = useRef<Record<string, number>>({});
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [repickWaiting, setRepickWaiting] = useState<RepickSlot | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmingLeave, setConfirmingLeave] = useState(false);
  const [aiMessages, setAiMessages] = useState<string[]>([]);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiBlocked, setAiBlocked] = useState<AiBlockedState | null>(null);

  const resync = useCallback(async () => {
    try {
      setView(await sessions.get(sessionId));
      setTabs(await sessions.tabs(sessionId));
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : String(exc));
    }
  }, [sessionId]);

  useEffect(() => {
    const stop = subscribeSessionEvents(sessionId, {
      onResync: () => void resync(),
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
          case "run_finished":
            setRunningIndex(null);
            setSummary(
              `${event.outcome === "pass" ? "PASS" : "FAIL"} · ` +
                `${event.passed_count} / ${event.total_count} 통과 · ` +
                `${(event.total_ms / 1000).toFixed(2)} s`,
            );
            void resync();
            break;
          case "run_error":
            // 실행이 끝났는데 결과를 남기지 못한 경우 — 조용히 넘기면 실행이 없었던
            // 것처럼 보인다 (contracts/websocket.md §진단 이벤트).
            setError(event.reason);
            break;
          case "artifact_note":
            // 산출물 일부를 남기지 못한 사유. 실행 자체는 유효하므로 오류로 다루지 않는다.
            setNotes((prev) =>
              prev.includes(event.message) ? prev : [...prev, event.message],
            );
            break;
          case "tab_limit_reached":
            setError(event.message ?? "탭 상한에 도달했습니다.");
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
            setAiError(event.reason);
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
    return stop;
  }, [sessionId, resync]);

  const act = async (fn: () => Promise<SessionView>) => {
    setBusy(true);
    setError(null);
    try {
      setView(await fn());
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  /** 편집 요청 공통 처리. 실패 사유를 알리되 화면을 떠나지 않는다 (FR-081). */
  const edit = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await resync();
    } catch (exc) {
      setNotice(exc instanceof ApiError ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    setBusy(true);
    void sessions
      .save(sessionId, saveName.trim())
      .then(() => resync())
      .catch((exc: unknown) => setError(exc instanceof ApiError ? exc.message : String(exc)))
      .finally(() => setBusy(false));
  };

  // ─── 상태 판정 ────────────────────────────────────────────────────────────

  /** **`authoring_mode` 로 판정한다** — 세션의 불변 속성이다 (research R2·DR-020). */
  const isAiSession = view.authoring_mode === "ai";
  const isPaused = view.state === "paused";
  const isReview = view.state === REVIEW_STATE;
  const isTakeover = view.state === "takeover_recording" || view.state === "ai_blocked";
  const isManipulating = MANIPULATION_STATES.has(view.state);
  const isObserving = OBSERVATION_STATES.has(view.state);
  const isDone = TERMINAL_STATES.has(view.state);
  const testId = view.test_id;
  const currentIndex = runningIndex ?? view.current_step_index;

  const phase: MirrorPhase = isManipulating
    ? "manipulation"
    : isPaused
      ? "paused"
      : isDone || isReview
        ? "terminated"
        : "observation";

  const outcomeOf = (step: Step, index: number): StepOutcome => {
    const recorded = progress[step.id]?.outcome;
    if (recorded !== undefined) return recorded;
    if (runningIndex === index) return "running";
    return "pending";
  };
  const durationOf = (step: Step) => durations.current[step.id];

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
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(onFinished);
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
      .catch((exc: unknown) => setError(exc instanceof ApiError ? exc.message : String(exc)))
      .finally(() => setBusy(false));
  };

  const banners = (
    <>
      {error !== null && <Banner tone="fail">{error}</Banner>}
      {lost !== null && (
        <SessionLostBanner
          reason={lost}
          stepCount={view.steps.length}
          busy={busy}
          onSave={saveName.trim() === "" ? undefined : save}
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
          {notice}
        </Banner>
      )}
      {notes.map((n) => (
        <Banner key={n} tone="info">
          {n}
        </Banner>
      ))}
      {summary !== null && <Banner tone="info">{summary}</Banner>}
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
                setNotice(resp.message);
                if (!resp.waiting) setRepickWaiting(null);
                return resync();
              })
              .catch((exc: unknown) => {
                setRepickWaiting(null);
                setNotice(exc instanceof ApiError ? exc.message : String(exc));
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
    selectedStepId,
    onSelectStep: (stepId: string) => setSelectedStepId(stepId),
  };

  // ─── 화면 선택 — 정확히 하나를 고른다 (DC-008) ────────────────────────────

  if (isAiSession && !isPaused && !isTakeover) {
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
          onStop={isDone || isReview ? leave : stop}
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
          onStop={leave}
        />
        {overlays}
      </>
    );
  }

  if (isPaused || isReview) {
    return (
      <>
        <RunnerPaused
          {...shared}
          title={testId ?? "새 테스트"}
          review={isReview}
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
                setNotice(resp.message);
                return resync();
              })
              .catch((exc: unknown) => setNotice(exc instanceof ApiError ? exc.message : String(exc)))
              .finally(() => setBusy(false));
          }}
          onShowResult={
            testId !== null && onShowResult && isDone ? () => onShowResult(testId) : undefined
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
        progressLabel={`step ${String(Math.min(currentIndex + 1, view.steps.length)).padStart(2, "0")} / ${String(view.steps.length).padStart(2, "0")}`}
        statusLabel={isObserving ? "RUNNING" : view.state_label}
        authoring={view.authoring_mode}
        canPause={!isDone}
        onPause={() => void act(() => sessions.pause(sessionId))}
        onStop={isDone ? leave : stop}
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
      <div onClick={(e) => e.stopPropagation()} style={{ overflowY: "auto" }}>
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
