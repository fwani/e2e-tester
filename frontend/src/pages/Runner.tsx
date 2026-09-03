/**
 * Interactive Runner (T068·T090). `Main.dc.html` 이식 + 실행 중 상태.
 *
 * 좌측은 **관찰용 읽기 전용 미러**이고, 조작은 실제 브라우저 창에서 한다
 * (clarify 결정 3, FR-023b). 조작 국면에서는 그 사실을 명시한다.
 *
 * FR-026: 녹화 중임과 기록된 Step 개수를 항상 표시한다.
 * FR-046·FR-047: 실행 중에는 현재 Step·통과 여부·Step별 소요 시간을 실시간으로 보여준다.
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
import { AppHeader } from "../components/AppHeader";
import { MirrorView, type MirrorPhase } from "../components/MirrorView";
import { SessionLostBanner } from "../components/SessionLostBanner";
import { StartingIndicator } from "../components/StartingIndicator";
import { StepInspector } from "../components/StepInspector";
import { StepList } from "../components/StepList";
import { TabStrip } from "../components/TabStrip";
import { AiRecord, type AiBlockedState } from "./AiRecord";
import { PausedBanner, RunnerPaused } from "./RunnerPaused";
import { Takeover, TakeoverBanner } from "./Takeover";

const MANIPULATION_STATES = new Set(["recording", "takeover_recording"]);
const OBSERVATION_STATES = new Set(["replaying", "ai_running"]);
const TERMINAL_STATES = new Set(["completed", "failed", "stopped", "lost"]);

/** 실행이 끝난 뒤 결과 화면으로 넘어갈 수 있는 상태 (FR-048). */
const RESULT_STATES = new Set(["completed", "failed"]);

export interface RunnerProps {
  initial: SessionView;
  /** AI 세션이면 사용자가 준 지시문 원문. 화면에만 쓰고 저장은 서버가 한다 (FR-063). */
  aiInstruction?: string | null;
  onFinished: () => void;
  /** 실행이 끝났을 때 결과 화면으로 이동한다 (FR-050). */
  onShowResult?: (testId: string) => void;
}

interface StepProgress {
  outcome?: "pass" | "fail";
  durationMs?: number;
}

export function Runner({
  initial,
  aiInstruction = null,
  onFinished,
  onShowResult,
}: RunnerProps) {
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
  const [aiMessages, setAiMessages] = useState<string[]>([]);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiBlocked, setAiBlocked] = useState<AiBlockedState | null>(null);
  const [aiStepCount, setAiStepCount] = useState(0);

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
      // 끊긴 사이의 이벤트는 복구할 수 없다. 전체 상태를 다시 받는다.
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
            // 실패해도 Step 은 보존된다 (FR-067). 오류 배너가 아니라 AI 패널에 남긴다.
            setAiError(event.reason);
            void resync();
            break;
          case "ai_finished":
            setAiBlocked(null);
            setAiStepCount(event.step_count);
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

  /** 편집 요청 공통 처리. 응답의 `steps`·`edit_warnings` 로 화면을 갱신한다 (FR-040b). */
  const edit = async (fn: () => Promise<{ steps: unknown; edit_warnings: string[] }>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await resync();
    } catch (exc) {
      // 실패 사유를 그대로 보여 준다 — 대상을 찾지 못한 것도 여기로 온다 (FR-081).
      setNotice(exc instanceof ApiError ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  };

  const AI_STATES = ["ai_running", "ai_blocked"];
  const isAiSession = AI_STATES.includes(view.state) || aiMessages.length > 0;
  const isPaused = view.state === "paused";
  const isManipulating = MANIPULATION_STATES.has(view.state);
  const isObserving = OBSERVATION_STATES.has(view.state);
  const isDone = TERMINAL_STATES.has(view.state);
  const canSave = view.steps.length > 0 && saveName.trim() !== "";
  const testId = view.test_id;
  const currentIndex = runningIndex ?? view.current_step_index;

  const phase: MirrorPhase = isManipulating
    ? "manipulation"
    : isPaused
      ? "paused"
      : isDone
        ? "terminated"
        : "observation";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <AppHeader
        breadcrumb={<>테스트 / {testId ?? "새 테스트 (저장 전)"}</>}
        status={<StateBadge state={view.state} label={view.state_label} />}
      />

      <div
        className="row"
        style={{ gap: 12, padding: "8px 16px", borderBottom: "1px solid var(--border)" }}
      >
        <strong>{testId ?? "새 테스트"}</strong>
        <span className="mono dim">
          step {String(Math.min(currentIndex + 1, view.steps.length))} /{" "}
          {view.steps.length}
        </span>
        {isObserving && <span className="badge">실행 중</span>}
        {summary !== null && <span className="mono dim">{summary}</span>}
        <span className="spacer" />
        {!isPaused && !isDone && (
          <button
            className="secondary"
            disabled={busy}
            onClick={() => void act(() => sessions.pause(sessionId))}
          >
            ⏸ 일시정지
          </button>
        )}
        {isPaused && (
          <button disabled={busy} onClick={() => void act(() => sessions.resume(sessionId))}>
            ▶ 계속하기
          </button>
        )}
        {RESULT_STATES.has(view.state) && testId !== null && onShowResult && (
          <button onClick={() => onShowResult(testId)}>실행 결과 보기</button>
        )}
        <button
          className="danger"
          disabled={busy}
          onClick={async () => {
            await act(() => sessions.stop(sessionId));
            onFinished();
          }}
        >
          ■ {isDone ? "닫기" : "중지"}
        </button>
      </div>

      {lost !== null && (
        <div style={{ padding: "8px 16px" }}>
          <SessionLostBanner
            reason={lost}
            stepCount={view.steps.length}
            busy={busy}
            onClose={() => setLost(null)}
            onSave={
              saveName.trim() === ""
                ? undefined
                : () => {
                    setBusy(true);
                    void sessions
                      .save(sessionId, saveName.trim())
                      .then(() => resync())
                      .catch((exc: unknown) =>
                        setError(exc instanceof ApiError ? exc.message : String(exc)),
                      )
                      .finally(() => setBusy(false));
                  }
            }
          />
        </div>
      )}

      {error !== null && (
        <div
          style={{
            padding: "8px 16px",
            background: "var(--fail-tint)",
            color: "var(--fail-dark)",
            whiteSpace: "pre-wrap",
          }}
        >
          {error}
        </div>
      )}

      {view.state === "takeover_recording" && <TakeoverBanner />}

      {isPaused && (
        <PausedBanner
          currentStepIndex={view.current_step_index}
          totalSteps={view.steps.length}
        />
      )}

      {view.recorder_warnings.map((w) => (
        <div key={w} style={{ padding: "8px 16px", background: "var(--surface-soft)" }} className="muted">
          {w}
        </div>
      ))}

      {notice !== null && (
        <div
          role="status"
          style={{ padding: "8px 16px", background: "var(--warn-tint)", borderTop: "1px solid var(--warn)" }}
        >
          {notice}
          <button className="ghost" onClick={() => setNotice(null)}>
            닫기
          </button>
        </div>
      )}

      {notes.map((n) => (
        <div key={n} style={{ padding: "8px 16px", background: "var(--surface-soft)" }} className="muted">
          {n}
        </div>
      ))}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", flex: 1, minHeight: 0 }}>
        {/* 좌측 — 관찰용 읽기 전용 미러 (FR-047a) */}
        <section
          style={{
            borderRight: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
          }}
        >
          {tabs !== null && (
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
          )}

          {view.state === "starting" ? (
            <StartingIndicator />
          ) : (
          <MirrorView
            frame={frame}
            phase={phase}
            stoppedReason={mirrorStopped}
            degradedReason={mirrorDegraded}
            tabIndex={mirrorTab}
          />
          )}
        </section>

        {/* 우측 — Step 목록 */}
        <section style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div
            className="row"
            style={{ gap: 8, padding: "10px 14px", borderBottom: "1px solid var(--border)" }}
          >
            <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
              TEST STEPS
            </strong>
            <span className="spacer" />
            <span className="badge">{view.steps.length}</span>
          </div>

          <div style={{ flex: 1, overflowY: "auto" }}>
            <StepList
              steps={view.steps}
              currentIndex={currentIndex}
              runningIndex={runningIndex}
              selectedStepId={selectedStepId}
              onSelect={(stepId) => setSelectedStepId(stepId)}
              outcomes={Object.fromEntries(
                Object.entries(progress).flatMap(([id, p]) =>
                  p.outcome !== undefined ? [[id, p.outcome]] : [],
                ),
              )}
              showPauseMarker={isPaused}
              durationsMs={durations.current}
              onDelete={
                isPaused
                  ? (stepId) => {
                      void sessions
                        .deleteStep(sessionId, stepId)
                        .then(() => resync())
                        .catch((exc: unknown) =>
                          setError(exc instanceof ApiError ? exc.message : String(exc)),
                        );
                    }
                  : undefined
              }
            />
          </div>

          {isAiSession && (
            <AiRecord
              instruction={aiInstruction}
              messages={aiMessages}
              running={view.state === "ai_running"}
              error={aiError}
              blocked={aiBlocked}
              stepCount={aiStepCount || view.steps.length}
              busy={busy}
              onChoose={(choice) => {
                setAiBlocked(null);
                void act(() => sessions.aiChoice(sessionId, choice));
              }}
            />
          )}

          {view.state === "takeover_recording" && (
            <Takeover
              blockedReason={aiBlocked?.reason ?? null}
              recordedCount={view.steps.filter((s) => s.author === "human").length}
              busy={busy}
              onResume={() => void act(() => sessions.resume(sessionId))}
              onStop={async () => {
                await act(() => sessions.stop(sessionId));
                onFinished();
              }}
            />
          )}

          {isPaused && (
            <RunnerPaused
              currentStepIndex={view.current_step_index}
              totalSteps={view.steps.length}
              editWarnings={view.edit_warnings}
              busy={busy}
              tab={mirrorTab}
              recording={false}
              selectedStepId={selectedStepId}
              selectedStepLabel={
                view.steps.find((s) => s.id === selectedStepId)?.label ?? null
              }
              selectedStepIndex={
                selectedStepId === null
                  ? null
                  : view.steps.findIndex((s) => s.id === selectedStepId)
              }
              onRecordActionsStart={() =>
                void act(() => sessions.recordActionsStart(sessionId))
              }
              onRecordActionsStop={() =>
                void act(() => sessions.recordActionsStop(sessionId))
              }
              onAddAssertion={(body: AddAssertionBody) =>
                void edit(() => sessions.addAssertion(sessionId, body))
              }
              onEditStep={(stepId) => {
                setSelectedStepId(stepId);
                setInspecting(true);
              }}
              onReorder={() => setReordering((v) => !v)}
              onRunFrom={(stepIndex) =>
                void act(() => sessions.runFrom(sessionId, stepIndex))
              }
              onDeleteStep={(stepId) =>
                void edit(() => sessions.deleteStep(sessionId, stepId))
              }
              onNaturalLanguage={(instruction) => {
                setBusy(true);
                setNotice(null);
                void sessions
                  .aiStep(sessionId, instruction)
                  .then((resp) => {
                    // 실패도 오류가 아니다 — 사유를 알리고 일시정지를 유지한다 (FR-081).
                    setNotice(resp.message);
                    return resync();
                  })
                  .catch((exc: unknown) =>
                    setNotice(exc instanceof ApiError ? exc.message : String(exc)),
                  )
                  .finally(() => setBusy(false));
              }}
              naturalLanguageNotice={notice}
              onDismissWarnings={() => setNotice(null)}
            />
          )}

          {isPaused && reordering && (
            <ReorderPanel
              steps={view.steps.map((s) => ({ id: s.id, label: s.label }))}
              busy={busy}
              onApply={(order) => {
                void edit(() => sessions.reorderSteps(sessionId, order));
                setReordering(false);
              }}
              onCancel={() => setReordering(false)}
            />
          )}

          {isPaused && inspecting && selectedStepId !== null && (() => {
            const index = view.steps.findIndex((s) => s.id === selectedStepId);
            const step = view.steps[index];
            if (index < 0 || step === undefined) return null;
            return (
              <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>
                <StepInspector
                  step={step}
                  index={index}
                  busy={busy}
                  repickWaiting={repickWaiting}
                  onClose={() => setInspecting(false)}
                  onSave={(patch) =>
                    void edit(() =>
                      sessions.patchStep(sessionId, selectedStepId, patch),
                    )
                  }
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
              </div>
            );
          })()}

          <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>
            <label htmlFor="save-name">테스트 이름</label>
            <div className="row">
              <input
                id="save-name"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="프로젝트 생성"
              />
              <button
                disabled={busy || !canSave}
                onClick={() => {
                  setBusy(true);
                  void sessions
                    .save(sessionId, saveName.trim())
                    .then(() => resync())
                    .catch((exc: unknown) =>
                      setError(exc instanceof ApiError ? exc.message : String(exc)),
                    )
                    .finally(() => setBusy(false));
                }}
              >
                저장
              </button>
            </div>
            {view.steps.length === 0 && (
              <p className="dim" style={{ fontSize: 12, marginTop: 6 }}>
                Step 이 없으면 저장할 수 없습니다.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function StateBadge({ state, label }: { state: string; label: string }) {
  const tone =
    state === "paused"
      ? "warn"
      : state === "failed" || state === "lost"
        ? "fail"
        : state === "completed"
          ? "pass"
          : state === "ai_running" || state === "ai_blocked"
            ? "ai"
            : "";
  return <span className={`badge ${tone}`}>{label}</span>;
}


/**
 * 순서 변경 패널 (FR-035).
 *
 * 드래그 앤 드롭을 쓰지 않는다. 목록이 200개까지 갈 수 있고(research R8) 드래그는 긴
 * 목록에서 정확히 놓기 어렵다. 위·아래 이동 버튼이 느리지만 틀리지 않는다.
 */
function ReorderPanel({
  steps,
  busy,
  onApply,
  onCancel,
}: {
  steps: { id: string; label: string }[];
  busy: boolean;
  onApply: (order: string[]) => void;
  onCancel: () => void;
}) {
  const [order, setOrder] = useState(steps.map((s) => s.id));
  const labels = new Map(steps.map((s) => [s.id, s.label]));

  const move = (index: number, delta: number) => {
    const next = [...order];
    const target = index + delta;
    const a = next[index];
    const b = next[target];
    if (a === undefined || b === undefined) return;
    next[index] = b;
    next[target] = a;
    setOrder(next);
  };

  return (
    <div style={{ padding: 12, borderTop: "1px solid var(--border)" }}>
      <strong style={{ fontSize: 13 }}>순서 변경</strong>
      <ol style={{ paddingLeft: 20, margin: "8px 0" }}>
        {order.map((id, i) => (
          <li key={id} className="row" style={{ gap: 6, alignItems: "center" }}>
            <span style={{ flex: 1 }}>{labels.get(id) ?? id}</span>
            <button className="ghost" disabled={i === 0} onClick={() => move(i, -1)}>
              ↑
            </button>
            <button
              className="ghost"
              disabled={i === order.length - 1}
              onClick={() => move(i, 1)}
            >
              ↓
            </button>
          </li>
        ))}
      </ol>
      <div className="row" style={{ gap: 8 }}>
        <button disabled={busy} onClick={() => onApply(order)}>
          적용
        </button>
        <button className="secondary" disabled={busy} onClick={onCancel}>
          취소
        </button>
      </div>
    </div>
  );
}
