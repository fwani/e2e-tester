/**
 * Interactive Runner — 실행 중. **`docs/design/Main.dc.html`(1440×900) 전사.**
 * DC-001~DC-008.
 *
 * **표시만 한다.** 세션 구독·상태·명령은 `SessionScreen` 이 owns 한다. 001 에서는 이
 * 파일 하나가 세션 상태 조합으로 4개 화면을 그렸고, 그 얽힘이 "AI 실패가 안 보이는"
 * 결함의 원인이었다 (research R2). 화면 선택과 세션 상태를 분리한 것이 이 라운드의
 * 구조적 수정이다.
 */
import type { ReactNode } from "react";

import type { Step } from "../types/generated/step";
import { BrowserFrame } from "../components/design/BrowserFrame";
import {
  DesignStepRow,
  StepPanelHeader,
  type StepOutcome,
} from "../components/design/DesignStepList";
import {
  Artboard,
  BrandMark,
  Breadcrumb,
  HeaderBar,
  HeaderDivider,
  LiveDot,
  StatusPill,
} from "../components/design/Chrome";

export interface RunnerProps {
  title: string;
  testId: string;
  /** 확정 디자인의 `step 04 / 05` 자리. */
  progressLabel: string;
  statusLabel: string;
  authoring: "record" | "ai";
  currentUrl: string;
  steps: Step[];
  outcomeOf: (step: Step, index: number) => StepOutcome;
  durationOf: (step: Step) => number | undefined;
  busy: boolean;
  canPause: boolean;
  onPause: () => void;
  onStop: () => void;
  onSelectStep?: (stepId: string) => void;
  selectedStepId?: string | null;
  /** 대상 앱 미러 (FR-047a). 확정 디자인의 흰 영역. */
  mirror: ReactNode;
  /** 탭 목록. 확정 디자인에 없는 상태이므로 미러 위에 얹는다 (DC-009). */
  tabs?: ReactNode;
  banners?: ReactNode;
  /** 확정 디자인의 「Step 추가」 버튼. 실행 중에는 비활성이다. */
  onAddStep?: () => void;
  /**
   * 실행이 끝난 뒤의 **다음 행동** (UX U-02). 없으면 아직 실행 중이다.
   *
   * 실행이 끝난 화면에 사용자가 서 있다. 요약(`FAIL · 3/5 통과`)과 빨간 ✕ 만 있고 이유도
   * 갈 곳도 없으면 새로고침을 누르게 되고, 그러면 목록으로 튕긴다. 결과 화면에 이유와
   * 행동이 다 있으므로 거기로 가는 길을 여기서 준다.
   */
  finished?: RunFinished;
}

export interface RunFinished {
  summary: string;
  /** 실패한 Step 의 사유 한 줄. 통과했으면 null. */
  failureReason: string | null;
  onShowResult?: () => void;
  onRerunFromFailure?: () => void;
  onRerunAll?: () => void;
  onBack: () => void;
}

export function Runner({
  title,
  testId,
  progressLabel,
  statusLabel,
  authoring,
  currentUrl,
  steps,
  outcomeOf,
  durationOf,
  busy,
  canPause,
  onPause,
  onStop,
  onSelectStep,
  selectedStepId = null,
  mirror,
  tabs,
  banners,
  onAddStep,
  finished,
}: RunnerProps) {
  return (
    <Artboard width={1440} height={900}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <Breadcrumb testId={testId} />
        <div style={{ flex: "1" }} />
        <StatusPill background="#14130F" color="#F5D000">
          <LiveDot className="tb-live" />
          {statusLabel}
        </StatusPill>
      </HeaderBar>

      <div
        style={{
          flex: "0 0 74px",
          borderBottom: "3px solid #14130F",
          background: "#EFEBE0",
          display: "flex",
          alignItems: "center",
          gap: "16px",
          padding: "0 24px",
        }}
      >
        <div
          style={{
            fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
            fontSize: "26px",
            lineHeight: "1",
          }}
        >
          {title}
        </div>
        <div style={{ font: "400 14px/1 'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}>
          {progressLabel}
        </div>
        <div style={{ flex: "1" }} />
        <button
          disabled={busy || !canPause}
          onClick={onPause}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "9px",
            height: "46px",
            padding: "0 18px",
            border: "3px solid #14130F",
            background: "#F5D000",
            color: "#14130F",
            boxShadow: "5px 5px 0 #14130F",
            font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
          }}
        >
          <svg width="15" height="15" viewBox="0 0 16 16">
            <rect x="3" y="2" width="3.5" height="12" fill="currentColor" />
            <rect x="9.5" y="2" width="3.5" height="12" fill="currentColor" />
          </svg>
          일시정지
        </button>
        <button
          disabled={busy}
          onClick={onStop}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "9px",
            height: "46px",
            padding: "0 18px",
            border: "3px solid #14130F",
            background: "#FFFDF6",
            color: "#14130F",
            boxShadow: "5px 5px 0 #14130F",
            font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 16 16">
            <rect x="3" y="3" width="10" height="10" fill="currentColor" />
          </svg>
          중지
        </button>
      </div>

      {banners}

      {finished && <FinishedBar {...finished} />}

      <div style={{ flex: "1", minHeight: "0", display: "flex" }}>
        <div style={{ flex: "1", minWidth: "0", padding: "20px", display: "flex", flexDirection: "column" }}>
          {tabs}
          <BrowserFrame
            url={currentUrl}
            badge={{ label: "READ ONLY", background: "#6B675C", color: "#FFFDF6" }}
          >
            {mirror}
          </BrowserFrame>
        </div>

        <div
          style={{
            flex: "0 0 460px",
            borderLeft: "3px solid #14130F",
            background: "#FFFDF6",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <StepPanelHeader authoring={authoring} count={steps.length} />

          <div style={{ flex: "1", minHeight: "0", display: "flex", flexDirection: "column", overflowY: "auto" }}>
            {steps.length === 0 && (
              // 확정 디자인은 Step 이 있는 상태만 보여준다 (DC-009).
              <div style={{ padding: "16px 18px", color: "#9A968A" }}>아직 기록된 Step 이 없습니다.</div>
            )}
            {steps.map((step, index) => (
              <DesignStepRow
                key={step.id}
                index={index}
                step={step}
                outcome={outcomeOf(step, index)}
                durationMs={durationOf(step)}
                selected={selectedStepId === step.id}
                onSelect={onSelectStep ? () => onSelectStep(step.id) : undefined}
              />
            ))}
          </div>

          <div
            style={{
              borderTop: "3px solid #14130F",
              padding: "16px 18px",
              background: "#EFEBE0",
              display: "flex",
              gap: "10px",
            }}
          >
            <button
              disabled={busy || onAddStep === undefined}
              onClick={onAddStep}
              style={{
                flex: "1",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "9px",
                height: "48px",
                border: "3px solid #14130F",
                background: "#FFFDF6",
                color: "#14130F",
                boxShadow: "5px 5px 0 #14130F",
                font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
              }}
              title={onAddStep === undefined ? "일시정지 상태에서 Step 을 추가할 수 있습니다." : undefined}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M8 3v10M3 8h10" />
              </svg>
              Step 추가
            </button>
          </div>
        </div>
      </div>
    </Artboard>
  );
}

// ─── 확정 디자인이 정의하지 않은 상태 (DC-009) ────────────────────────────

const ACTION_BUTTON: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  height: "40px",
  padding: "0 16px",
  border: "3px solid #14130F",
  boxShadow: "4px 4px 0 #14130F",
  font: "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
};

function FinishedBar({
  summary,
  failureReason,
  onShowResult,
  onRerunFromFailure,
  onRerunAll,
  onBack,
}: RunFinished) {
  const failed = failureReason !== null;
  return (
    <div
      role="status"
      data-run-finished
      style={{
        borderBottom: "3px solid #14130F",
        background: failed ? "#FBEEEA" : "#F5F2E9",
        padding: "12px 24px",
        display: "flex",
        alignItems: "center",
        gap: "14px",
        flexWrap: "wrap",
      }}
    >
      <div style={{ flex: 1, minWidth: 240, display: "flex", flexDirection: "column", gap: 4 }}>
        <strong style={{ font: "700 14px/1.2 'IBM Plex Mono', ui-monospace, monospace" }}>
          {summary}
        </strong>
        {failed && (
          <span
            data-failure-reason
            style={{ font: "400 13px/1.5 'IBM Plex Sans KR', system-ui, sans-serif", color: "#A83A22" }}
          >
            {failureReason}
          </span>
        )}
      </div>
      {onShowResult && (
        <button onClick={onShowResult} style={{ ...ACTION_BUTTON, background: "#14130F", color: "#F5F2E9" }}>
          결과 자세히 보기
        </button>
      )}
      {failed && onRerunFromFailure && (
        <button onClick={onRerunFromFailure} style={{ ...ACTION_BUTTON, background: "#F5D000", color: "#14130F" }}>
          실패한 Step부터 다시 실행
        </button>
      )}
      {onRerunAll && (
        <button onClick={onRerunAll} style={{ ...ACTION_BUTTON, background: "#FFFDF6", color: "#14130F" }}>
          처음부터 다시 실행
        </button>
      )}
      <button className="ghost" onClick={onBack}>
        목록으로
      </button>
    </div>
  );
}
