/**
 * Interactive Runner (T068). `Main.dc.html` 이식 (녹화 상태).
 *
 * 좌측은 **관찰용 읽기 전용 미러**이고, 조작은 실제 브라우저 창에서 한다
 * (clarify 결정 3, FR-023b). 조작 국면에서는 그 사실을 명시한다.
 *
 * FR-026: 녹화 중임과 기록된 Step 개수를 항상 표시한다.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  sessions,
  type SessionView,
  type TabsResponse,
} from "../api/client";
import { subscribeSessionEvents, type SessionEvent } from "../api/ws";
import { AppHeader } from "../components/AppHeader";
import { StepList } from "../components/StepList";
import { TabStrip } from "../components/TabStrip";

const MANIPULATION_STATES = new Set(["recording", "takeover_recording"]);
const OBSERVATION_STATES = new Set(["replaying", "ai_running"]);
const TERMINAL_STATES = new Set(["completed", "failed", "stopped", "lost"]);

export interface RunnerProps {
  initial: SessionView;
  onFinished: () => void;
}

export function Runner({ initial, onFinished }: RunnerProps) {
  const [view, setView] = useState<SessionView>(initial);
  const [tabs, setTabs] = useState<TabsResponse | null>(null);
  const [frame, setFrame] = useState<string | null>(null);
  const [mirrorStopped, setMirrorStopped] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveName, setSaveName] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionId = initial.session_id;
  const durations = useRef<Record<string, number>>({});

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
            setFrame(event.data as string);
            setMirrorStopped(null);
            break;
          case "mirror_stopped":
            setMirrorStopped((event.reason as string | undefined) ?? "미러가 중단됐습니다.");
            break;
          case "step_finished":
            durations.current[event.step_id as string] = event.duration_ms as number;
            void resync();
            break;
          case "tab_limit_reached":
            setError((event.message as string | undefined) ?? "탭 상한에 도달했습니다.");
            break;
          default:
            // step_added·step_updated·step_removed·state_changed 등은 전체 상태를 다시 받는다.
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

  const isPaused = view.state === "paused";
  const isManipulating = MANIPULATION_STATES.has(view.state);
  const isObserving = OBSERVATION_STATES.has(view.state);
  const isDone = TERMINAL_STATES.has(view.state);
  const canSave = view.steps.length > 0 && saveName.trim() !== "";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <AppHeader
        breadcrumb={<>테스트 / {view.test_id ?? "새 테스트 (저장 전)"}</>}
        status={<StateBadge state={view.state} label={view.state_label} />}
      />

      <div
        className="row"
        style={{ gap: 12, padding: "8px 16px", borderBottom: "1px solid var(--border)" }}
      >
        <strong>{view.test_id ?? "새 테스트"}</strong>
        <span className="mono dim">
          step {String(Math.min(view.current_step_index + 1, view.steps.length))} /{" "}
          {view.steps.length}
        </span>
        <span className="spacer" />
        {!isPaused && !isDone && (
          <button className="secondary" disabled={busy} onClick={() => void act(() => sessions.pause(sessionId))}>
            ⏸ 일시정지
          </button>
        )}
        {isPaused && (
          <button disabled={busy} onClick={() => void act(() => sessions.resume(sessionId))}>
            ▶ 계속하기
          </button>
        )}
        <button
          className="danger"
          disabled={busy || isDone}
          onClick={async () => {
            await act(() => sessions.stop(sessionId));
            onFinished();
          }}
        >
          ■ 중지
        </button>
      </div>

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

      {view.edit_warnings.map((w) => (
        <div
          key={w}
          style={{ padding: "8px 16px", background: "var(--warn-tint)", borderTop: "1px solid var(--warn)" }}
        >
          ⚠ {w}
        </div>
      ))}

      {view.recorder_warnings.map((w) => (
        <div key={w} style={{ padding: "8px 16px", background: "var(--surface-soft)" }} className="muted">
          {w}
        </div>
      ))}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", flex: 1, minHeight: 0 }}>
        {/* 좌측 — 관찰용 읽기 전용 미러 (FR-047a) */}
        <section style={{ borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", minWidth: 0 }}>
          {tabs !== null && (
            <TabStrip
              tabs={tabs.tabs}
              mirroredTabIndex={tabs.mirrored_tab_index}
              maxTabs={tabs.max_tabs}
              onSelect={(index) => {
                void sessions.setMirrorTab(sessionId, index).then(setTabs).catch(() => undefined);
              }}
            />
          )}

          {isManipulating && (
            <div className="row" style={{ gap: 8, padding: "10px 14px", background: "var(--warn-tint)" }}>
              <strong>실제 브라우저 창에서 조작하세요.</strong>
              <span className="muted">
                이 영역은 관찰용이며 조작 대상이 아닙니다.
              </span>
            </div>
          )}

          {isPaused && (
            <div className="row" style={{ gap: 8, padding: "10px 14px", background: "var(--surface)" }}>
              <strong>일시정지</strong>
              <span className="muted">
                브라우저 세션과 화면 상태를 그대로 유지하고 있습니다.
              </span>
            </div>
          )}

          <div
            style={{
              flex: 1,
              display: "grid",
              placeItems: "center",
              background: "var(--paper-alt)",
              overflow: "hidden",
            }}
          >
            {frame !== null ? (
              <img
                src={`data:image/jpeg;base64,${frame}`}
                alt="대상 브라우저 화면 (읽기 전용)"
                style={{ maxWidth: "100%", maxHeight: "100%", pointerEvents: "none" }}
              />
            ) : (
              <p className="muted" style={{ textAlign: "center", padding: 24 }}>
                {mirrorStopped ??
                  (isObserving
                    ? "미러 프레임을 기다리고 있습니다."
                    : "실제 브라우저 창에서 조작하세요. 이 영역은 관찰용입니다.")}
              </p>
            )}
          </div>
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
              currentIndex={view.current_step_index}
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
