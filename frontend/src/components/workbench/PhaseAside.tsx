/**
 * 층③ 좌측 아래 국면 보조 영역 (007 T024 · FR-218e·FR-218f).
 *
 * **국면 고유 내용의 유일한 자리다.** AI 지시문·진행 로그·차단 사유와 선택지, 사람이
 * 직접 조작 안내, 일시정지의 검증 추가 폼, 편집의 변경 요약이 여기 온다.
 *
 * 자리의 근거는 `RunnerPaused.dc.html`·`Takeover.dc.html` 이 미러에 붙여 둔 국면 안내
 * 띠(`flex: 0 0 42px`)다. 내용에 따라 늘어나는 것은 **확정 디자인에 대응이 없으므로**
 * 승인 대상이다 (research R8 A1 · `design-conformance/undefined-states.md`).
 *
 * ## 이 파일의 유일한 불변식
 *
 * **`error` 와 `blocked` 는 값이 있으면 조건 없이 그린다** (FR-218f · FR-253).
 *
 * 001 research R2 가 규명한 결함이 정확히 이것이었다 — `ai_error` 를 렌더하는 유일한
 * 컴포넌트가 `isAiSession` 조건 뒤에 숨어, 실패가 상태에 담겨도 화면에 도달하지 못했다.
 * 사용자에게는 "아무 일도 일어나지 않음" 으로 보였다. 접힘·탭·겹침 뒤에 두지 않는다.
 */
import { ErrorNotice } from "../ErrorNotice";
import { STALE_OVERWRITE_LABEL, editSavedNotice, staleReloadLabel } from "../../lib/wording";
import type { AiBlockedState, PhaseAside as PhaseAsideModel } from "./model";

const INK = "#14130F";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

/** 이 영역의 최소 높이 (승인 대상 A1). `RunnerPaused`·`Takeover` 의 42px 띠. */
const MIN_HEIGHT = 42;

export interface PhaseAsideProps {
  aside: PhaseAsideModel;
  onChooseBlocked?: (choice: string) => void;
  onReload?: () => void;
  onOverwriteStale?: () => void;
  busy?: boolean;
}

export function PhaseAside({
  aside,
  onChooseBlocked,
  onReload,
  onOverwriteStale,
  busy = false,
}: PhaseAsideProps) {
  return (
    <div
      data-workbench-aside={aside.kind}
      style={{
        flex: `0 0 auto`,
        minHeight: MIN_HEIGHT,
        borderTop: `3px solid ${INK}`,
        background: "#FFFDF6",
        padding: "14px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        maxHeight: "45%",
        overflowY: "auto",
      }}
    >
      {aside.kind === "ai_progress" && (
        <>
          <Section title="지시문">
            <p style={{ margin: 0, font: `400 13px/1.6 ${SANS}`, whiteSpace: "pre-wrap" }}>
              {aside.instruction}
            </p>
          </Section>

          {/* 실패는 **먼저** 온다. 로그 아래로 밀면 스크롤에 묻힌다. */}
          <AlwaysVisibleFailure error={aside.error} blocked={aside.blocked} onChoose={onChooseBlocked} busy={busy} />

          <Section title="진행">
            {aside.messages.length === 0 ? (
              <p className="dim" style={{ margin: 0, font: `400 12.5px/1.6 ${MONO}` }}>
                아직 기록이 없습니다.
              </p>
            ) : (
              <ol style={{ margin: 0, paddingLeft: 18, font: `400 12.5px/1.7 ${MONO}` }}>
                {aside.messages.map((m, i) => (
                  <li key={`${i}-${m}`}>{m}</li>
                ))}
              </ol>
            )}
          </Section>
        </>
      )}

      {aside.kind === "takeover_guide" && (
        <>
          <div
            role="status"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              minHeight: MIN_HEIGHT,
              padding: "0 12px",
              background: aside.recording ? "#D9502F" : "#F5D000",
              color: aside.recording ? "#FFFDF6" : INK,
              border: `3px solid ${INK}`,
              font: `600 13px/1.4 ${SANS}`,
            }}
          >
            {aside.recording
              ? "사람이 조작하는 중입니다 — 지금 하는 조작이 Step 으로 기록됩니다."
              : "AI 가 멈췄습니다. 직접 조작해 이어가거나 AI 에게 돌려줄 수 있습니다."}
          </div>
          <AlwaysVisibleFailure error={aside.error} blocked={aside.blocked} onChoose={onChooseBlocked} busy={busy} />
        </>
      )}

      {aside.kind === "paused_tools" && aside.tools}

      {aside.kind === "failure_detail" && (
        <>
          <Section title={`실패 — ${aside.step.label}`}>
            <p style={{ margin: 0, font: `500 14px/1.6 ${SANS}`, color: "#A83A22" }}>
              {aside.step.error_message ?? "실패 이유가 기록되지 않았습니다."}
            </p>
          </Section>

          {/*
            001 FR-021·FR-054 — **그때 무엇을 시도했는가.** 결과 국면에서 사용자가
            알아야 하는 것은 정의의 후보가 아니라 실제 시도다. Step 상세를 열지 않아도
            보여야 한다 — 실패는 이 화면에 온 이유이고, 한 번 더 누르게 하면 그만큼
            원인 파악이 늦어진다 (SC-009).
          */}
          {aside.step.locator_attempts.length > 0 && (
            <Section title="시도한 LOCATOR (우선순위 순)">
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {aside.step.locator_attempts.map((a) => (
                  <div
                    key={`${a.candidate}-${a.expression}`}
                    style={{ display: "flex", alignItems: "center", gap: 10, font: `400 12.5px/1.4 ${MONO}` }}
                  >
                    <span style={{ color: a.matched ? "#2E9455" : "#A83A22", fontWeight: 700 }}>
                      {a.matched ? "✓" : "×"}
                    </span>
                    <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {a.expression}
                    </span>
                  </div>
                ))}
                {/*
                  004 FR-121 — **실제로 기다린 시간**이다. 예전에는 후보별 대기 중
                  최댓값을 "timeout" 이라 불렀는데, 그것은 설정값도 실측값도 아니었다.
                */}
                <div style={{ font: `400 12px/1.4 ${MONO}`, color: "#6B675C", paddingLeft: 20 }}>
                  {`요소를 ${aside.step.element_wait_ms} ms 기다렸습니다`}
                </div>
              </div>
            </Section>
          )}
          {/*
            004 FR-122·FR-123 — 진단은 **`code` 로 분기한다.** 문구를 파싱하지 않는다.
            규칙 기반이며 언어모델을 쓰지 않는다 (Principle II).
          */}
          {aside.diagnosis !== null && (
            <div
              role="note"
              style={{
                border: `3px solid ${INK}`,
                background: "#FFF6D9",
                padding: "12px 14px",
                font: `500 13.5px/1.6 ${SANS}`,
              }}
            >
              {aside.diagnosis}
            </div>
          )}
        </>
      )}

      {aside.kind === "edit_summary" && (
        <>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              minHeight: MIN_HEIGHT,
              font: `600 13px/1.4 ${SANS}`,
            }}
          >
            <span data-pending-edits>
              {aside.pendingCount === 0
                ? "바꾼 것이 없습니다"
                : `저장할 변경 ${aside.pendingCount}건`}
            </span>
            {aside.savedName !== null && (
              <span role="status" style={{ color: "#1F7A3D", font: `600 13px/1.4 ${SANS}` }}>
                ✓ {editSavedNotice(aside.savedName)}
              </span>
            )}
          </div>

          {/* FR-216 — 저장을 막지 않는 것들. 경고로만 알린다. */}
          {aside.warnings.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 18, font: `400 12.5px/1.6 ${SANS}`, color: "#8A6A16" }}>
              {aside.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          {aside.fields}

          {/* 006 FR-209 — 편집 도중 정의 파일이 밖에서 바뀌었다. */}
          {aside.stale !== null && (
            <div
              role="alert"
              style={{ border: `3px solid ${INK}`, background: "#FFF6D8", padding: 14 }}
            >
              <strong style={{ fontSize: 13 }}>
                ⚠ 이 테스트의 정의 파일이 편집을 시작한 뒤에 바뀌었습니다.
              </strong>
              <p style={{ fontSize: 12.5, margin: "6px 0 10px" }}>
                파일 밖에서 고친 내용이 있습니다. 어떻게 할지 고르세요.
              </p>
              {/* 무엇을 버리는지 라벨에 적는다 (006 FR-209 · ui-contract §7). */}
              <div className="row" style={{ gap: 8 }}>
                <button className="secondary" onClick={onReload}>
                  {staleReloadLabel(aside.pendingCount)}
                </button>
                <button onClick={onOverwriteStale}>{STALE_OVERWRITE_LABEL}</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ font: `600 11px/1 ${MONO}`, letterSpacing: "0.1em", color: "#6B675C" }}>
        {title}
      </div>
      {children}
    </div>
  );
}

/**
 * 실패와 차단은 **조건 없이** 그린다 (FR-218f · FR-253 · 001 research R2).
 *
 * 이 컴포넌트가 국면·세션 상태를 인자로 받지 않는 것이 요점이다. 받으면 언젠가 그것으로
 * 분기하게 되고, 그 분기가 실패를 숨긴다.
 */
function AlwaysVisibleFailure({
  error,
  blocked,
  onChoose,
  busy,
}: {
  error: import("../ErrorNotice").ErrorInfo | null;
  blocked: AiBlockedState | null;
  onChoose?: (choice: string) => void;
  busy: boolean;
}) {
  if (error === null && blocked === null) return null;
  return (
    <div data-always-visible-failure style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {error !== null && <ErrorNotice error={error} />}
      {blocked !== null && (
        <div
          role="alert"
          style={{ border: `3px solid ${INK}`, background: "#FBEEEA", padding: "12px 14px" }}
        >
          <strong style={{ font: `700 13px/1.4 ${SANS}`, color: "#A83A22" }}>
            AI 가 막혔습니다
          </strong>
          {blocked.attempted !== null && (
            <p style={{ margin: "6px 0 0", font: `400 12.5px/1.6 ${MONO}` }}>
              시도: {blocked.attempted}
            </p>
          )}
          <p style={{ margin: "6px 0 10px", font: `400 13px/1.6 ${SANS}` }}>{blocked.reason}</p>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            {blocked.choices.map((c) => (
              <button key={c} className="secondary" disabled={busy} onClick={() => onChoose?.(c)}>
                {c}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
