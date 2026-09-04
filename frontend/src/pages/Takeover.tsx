/**
 * AI 실패 → 사람이 이어받기. **`docs/design/Takeover.dc.html`(1440×900) 전사.**
 * DC-001~DC-008.
 *
 * 001 에서는 `Runner.tsx` 안의 조건부 패널이었다. 확정 디자인이 독립 artboard 로
 * 정의하므로 독립 화면으로 분리했다 (DC-008).
 *
 * **AI 가 실패해도 세션은 유지된다** (001 FR-069). 확정 디자인이 `세션 유지` 를 붉은 띠에
 * 명시하는 이유다 — 사용자가 그 자리에서 이어받을 수 있다는 것이 이 화면의 요점이다.
 */
import type { ReactNode } from "react";

import type { AiChoice } from "../api/client";
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
import type { AiBlockedState } from "./AiRecord";

/** 확정 디자인의 4선택지 (001 FR-070). 순서와 문구를 그대로 옮겼다. */
const CHOICES: { key: AiChoice; label: string; primary?: boolean }[] = [
  { key: "takeover", label: "직접 수행", primary: true },
  { key: "retry", label: "AI에게 다시" },
  { key: "skip", label: "건너뛰기" },
  { key: "abort", label: "종료" },
];

export interface TakeoverProps {
  title: string;
  testId: string;
  blocked: AiBlockedState | null;
  /** 사람이 이어받아 녹화 중인가. 확정 디자인의 붉은 띠 상태다. */
  recording: boolean;
  steps: Step[];
  outcomeOf: (step: Step, index: number) => StepOutcome;
  durationOf: (step: Step) => number | undefined;
  busy: boolean;
  currentUrl: string;
  mirror: ReactNode;
  tabs?: ReactNode;
  banners?: ReactNode;
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
  onChoose: (choice: AiChoice) => void;
  onStopRecording: () => void;
  onStop: () => void;
}

export function Takeover({
  title,
  testId,
  blocked,
  recording,
  steps,
  outcomeOf,
  durationOf,
  busy,
  currentUrl,
  mirror,
  tabs,
  banners,
  selectedStepId,
  onSelectStep,
  onChoose,
  onStopRecording,
  onStop,
}: TakeoverProps) {
  const humanSteps = steps.filter((s) => s.author === "human").length;

  return (
    <Artboard width={1440} height={900}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <Breadcrumb testId={testId} />
        <div style={{ flex: "1" }} />
        <StatusPill background="#D9502F" color="#FFFDF6">
          <LiveDot className="tb-live" />
          {recording ? "사람이 녹화 중" : "AI 멈춤"}
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
          AI 실패 → 사람이 이어받음
        </div>
        <div style={{ flex: "1" }} />
        {recording && (
          <button
            disabled={busy}
            onClick={onStopRecording}
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
            <svg width="15" height="15" viewBox="0 0 16 16">
              <rect x="3" y="2" width="3.5" height="12" fill="currentColor" />
              <rect x="9.5" y="2" width="3.5" height="12" fill="currentColor" />
            </svg>
            녹화 정지
          </button>
        )}
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

      <div style={{ flex: "1", minHeight: "0", display: "flex" }}>
        <div style={{ flex: "1", minWidth: "0", padding: "20px", display: "flex", flexDirection: "column" }}>
          {tabs}
          <BrowserFrame
            url={currentUrl}
            badge={
              recording
                ? { label: "HUMAN CONTROL", background: "#D9502F", color: "#FFFDF6" }
                : { label: "AI STOPPED", background: "#7C4DDB", color: "#FFFDF6" }
            }
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
          <StepPanelHeader authoring="ai" count={steps.length} />

          {/* 실패한 동작과 4선택지 (FR-069·FR-070) */}
          {blocked !== null && (
            <div
              style={{
                borderTop: "3px solid #14130F",
                borderBottom: "3px solid #14130F",
                background: "#F0EBFC",
                padding: "13px 18px",
                display: "flex",
                flexDirection: "column",
                gap: "11px",
              }}
            >
              <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <div
                  style={{
                    flex: "0 0 24px",
                    height: "24px",
                    background: "#D9502F",
                    color: "#FFFDF6",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.8">
                    <path d="M4 4l8 8M12 4l-8 8" />
                  </svg>
                </div>
                <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column", gap: "4px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{ font: "700 14px/1.2 'IBM Plex Sans KR', system-ui, sans-serif" }}>
                      {blocked.attempted ?? title}
                    </div>
                    <div
                      style={{
                        padding: "3px 6px",
                        background: "#7C4DDB",
                        color: "#FFFDF6",
                        font: "700 10px/1 'IBM Plex Mono', ui-monospace, monospace",
                        letterSpacing: "0.06em",
                      }}
                    >
                      AI
                    </div>
                  </div>
                  <div
                    style={{
                      font: "500 13px/1.45 'IBM Plex Sans KR', system-ui, sans-serif",
                      color: "#55507A",
                      textWrap: "pretty",
                    }}
                  >
                    {blocked.reason}
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "8px" }}>
                {CHOICES.filter((c) => blocked.choices.length === 0 || blocked.choices.includes(c.key)).map(
                  (choice) => (
                    <button
                      key={choice.key}
                      disabled={busy}
                      onClick={() => onChoose(choice.key)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                        height: "46px",
                        border: "3px solid #14130F",
                        background: choice.primary ? "#14130F" : "#FFFDF6",
                        color: choice.primary ? "#F5F2E9" : "#14130F",
                        font: choice.primary
                          ? "700 14px/1 'IBM Plex Sans KR', system-ui, sans-serif"
                          : "600 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
                        boxShadow: "none",
                      }}
                    >
                      {choice.primary && (
                        <svg width="15" height="15" viewBox="0 0 20 20">
                          <circle cx="10" cy="10" r="5" fill="#D9502F" />
                        </svg>
                      )}
                      {choice.label}
                    </button>
                  ),
                )}
              </div>
            </div>
          )}

          {/* 사람이 이어받아 녹화 중임을 명시하는 띠. 「세션 유지」가 이 화면의 요점이다. */}
          {recording && (
            <div
              style={{
                flex: "0 0 42px",
                background: "#D9502F",
                color: "#FFFDF6",
                borderBottom: "3px solid #14130F",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "0 18px",
              }}
            >
              <LiveDot className="tb-live" />
              <div style={{ font: "700 13px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.08em" }}>
                사람이 이어받아 녹화 중
              </div>
              <div style={{ flex: "1" }} />
              <div style={{ font: "500 13px/1 'IBM Plex Sans KR', system-ui, sans-serif" }}>세션 유지</div>
            </div>
          )}

          <div style={{ flex: "1", minHeight: "0", overflowY: "auto" }}>
            {steps.map((step, index) => (
              <DesignStepRow
                key={step.id}
                index={index}
                step={step}
                outcome={outcomeOf(step, index)}
                durationMs={durationOf(step)}
                selected={selectedStepId === step.id}
                onSelect={() => onSelectStep(step.id)}
                actions={
                  step.author === "human" ? (
                    <div
                      style={{
                        alignSelf: "flex-start",
                        padding: "3px 6px",
                        border: "2px solid #14130F",
                        background: "#FFFDF6",
                        font: "700 10px/1 'IBM Plex Mono', ui-monospace, monospace",
                      }}
                    >
                      HUMAN
                    </div>
                  ) : undefined
                }
              />
            ))}
          </div>

          <div
            style={{
              borderTop: "3px solid #14130F",
              background: "#EFEBE0",
              padding: "14px 18px",
              color: "#6B675C",
              font: "500 13px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
            }}
          >
            사람이 이어받아 만든 Step {humanSteps}개. 작성 주체는 구분해 표시되지만 AI 가 만든
            Step 과 **같은 모델**로 저장됩니다 (FR-075).
          </div>
        </div>
      </div>
    </Artboard>
  );
}
