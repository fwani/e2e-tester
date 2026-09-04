/**
 * AI로 테스트 만들기. **`docs/design/AiRecord.dc.html`(1440×900) 전사.** DC-001~DC-008.
 *
 * **독립 화면이다** (DC-008). 001 에서는 `Runner.tsx` 안의 조건부 패널이었고, 그 얽힘이
 * 이 라운드 결함의 원인이었다 — `ai_error` 를 그리는 유일한 컴포넌트가 세션 상태 조건
 * 뒤에 숨어, 실패가 상태에 담겨도 화면에 도달하지 못했다 (research R2).
 *
 * **실패 표시는 세션 상태와 무관하다** (DR-020). AI 세션인지는 `view.state` 가 아니라
 * `authoring_mode` 로 판정한다 — 그것이 세션의 불변 속성이다. 상태가 `paused` 로
 * 바뀌어도 실패 사유는 계속 보인다.
 *
 * 확정 디자인의 왼쪽 흰 영역은 **대상 앱의 미러**다. 우리 UI 가 아니므로 `MirrorView`
 * 가 그린다 — 확정 디자인의 표본 화면(프로젝트 목록)을 우리가 그리면 안 된다.
 */
import { useState } from "react";
import { ErrorNotice } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import type { Step } from "../types/generated/step";
import {
  Artboard,
  BrandMark,
  HeaderBar,
  HeaderDivider,
} from "../components/design/Chrome";

export interface AiBlockedState {
  attempted: string | null;
  reason: string;
  choices: string[];
}

export interface AiRecordProps {
  /** 사용자가 쓴 자연어 지시. 화면에만 쓴다 — 저장은 하지 않는다 (FR-063). */
  instruction: string;
  /** 아직 지시문을 쓰는 중인가. 확정 디자인은 수행 중만 보여준다 (DC-009). */
  composing?: boolean;
  onInstructionChange?: (value: string) => void;
  onStart?: () => void;

  running: boolean;
  steps: Step[];
  /** AI 진행 로그. 실패도 여기 남는다 — 볼 경로를 둘로 만든다 (research R2). */
  messages: string[];
  /** **세션 상태와 무관하게** 그린다. 이것이 이 라운드의 핵심 수정이다. */
  error: ErrorInfo | null;
  blocked: AiBlockedState | null;

  busy?: boolean;
  saveName: string;
  onSaveNameChange: (name: string) => void;
  onSave: () => void;
  onPause?: () => void;
  onStop?: () => void;
  /** 대상 앱 미러. 확정 디자인의 흰 영역이다. */
  mirror?: React.ReactNode;
  currentUrl?: string;
}

const INK = "#14130F";

export function AiRecord({
  instruction,
  composing = false,
  onInstructionChange,
  onStart,
  running,
  steps,
  messages,
  error,
  blocked,
  busy = false,
  saveName,
  onSaveNameChange,
  onSave,
  onPause,
  onStop,
  mirror,
  currentUrl = "",
}: AiRecordProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Artboard width={1440} height={900}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            font: "500 14px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            color: "#6B675C",
          }}
        >
          테스트
          <span style={{ color: INK }}>/</span>
          <span style={{ color: INK, fontWeight: "600" }}>새 테스트</span>
        </div>
        <div style={{ flex: "1" }} />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            height: "40px",
            padding: "0 14px",
            border: "3px solid #14130F",
            background: "#F0EBFC",
            font: "600 13px/1 'IBM Plex Mono', ui-monospace, monospace",
            letterSpacing: "0.06em",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7C4DDB" strokeWidth="2.6">
            <path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3" />
          </svg>
          {statusLabel({ composing, running, error, blocked })}
        </div>
      </HeaderBar>

      <div
        style={{
          flex: "0 0 74px",
          borderBottom: "3px solid #14130F",
          background: "#EFEBE0",
          display: "flex",
          alignItems: "center",
          gap: "18px",
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
          AI로 테스트 만들기
        </div>
        <div style={{ flex: "1" }} />
        {onPause && (
          <button
            disabled={busy || !running}
            onClick={onPause}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "9px",
              height: "46px",
              padding: "0 18px",
              border: "3px solid #14130F",
              background: "#F5D000",
              color: INK,
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
        )}
        {onStop && (
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
              color: INK,
              boxShadow: "5px 5px 0 #14130F",
              font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 16 16">
              <rect x="3" y="3" width="10" height="10" fill="currentColor" />
            </svg>
            중지
          </button>
        )}
      </div>

      <div style={{ flex: "1", minHeight: "0", display: "flex" }}>
        {/* 왼쪽 — 대상 앱 미러. 흰 영역의 내용은 대상 앱이지 우리 UI 가 아니다. */}
        <div
          style={{
            flex: "1",
            minWidth: "0",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "0",
          }}
        >
          <div
            style={{
              border: "3px solid #14130F",
              background: "#14130F",
              flex: "1",
              minHeight: "0",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div
              style={{
                flex: "0 0 46px",
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "0 12px",
                background: "#14130F",
              }}
            >
              <div style={{ display: "flex", gap: "0", color: "#8E897C" }}>
                {[
                  "M10 3.5L5.5 8l4.5 4.5",
                  "M6 3.5L10.5 8 6 12.5",
                  "M13 8a5 5 0 1 1-1.6-3.7M13 1.6v3.2h-3.2",
                ].map((d) => (
                  <div
                    key={d}
                    style={{
                      width: "44px",
                      height: "44px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <path d={d} />
                    </svg>
                  </div>
                ))}
              </div>
              <div
                style={{
                  flex: "1",
                  display: "flex",
                  alignItems: "center",
                  height: "28px",
                  padding: "0 10px",
                  background: "#2A2823",
                  color: "#C9C4B4",
                  font: "400 12px/1 'IBM Plex Mono', ui-monospace, monospace",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {currentUrl}
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  height: "28px",
                  padding: "0 9px",
                  background: "#7C4DDB",
                  color: "#FFFDF6",
                  font: "700 11px/1 'IBM Plex Mono', ui-monospace, monospace",
                  letterSpacing: "0.08em",
                }}
              >
                AI CONTROL
              </div>
            </div>
            <div
              style={{
                flex: "1",
                minHeight: "0",
                background: "#FFFFFF",
                display: "flex",
                borderTop: "3px solid #14130F",
              }}
            >
              {mirror}
            </div>
          </div>
        </div>

        {/* 오른쪽 540px — 지시문과 기록된 Step */}
        <div
          style={{
            flex: "0 0 540px",
            borderLeft: "3px solid #14130F",
            background: "#FFFDF6",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              padding: "18px 20px",
              borderBottom: "3px solid #14130F",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
            }}
          >
            <label
              htmlFor="ai-instruction"
              style={{
                font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace",
                letterSpacing: "0.12em",
                color: "#6B675C",
                margin: 0,
                textTransform: "none",
              }}
            >
              자연어 지시
            </label>
            {composing ? (
              <>
                <textarea
                  id="ai-instruction"
                  rows={5}
                  value={instruction}
                  autoFocus
                  onChange={(e) => onInstructionChange?.(e.target.value)}
                  placeholder={"로그인한 다음 프로젝트 메뉴로 이동해서\nTEST라는 프로젝트를 생성하고\n프로젝트 목록에 TEST가 있는지 확인해."}
                  style={{
                    border: "3px solid #14130F",
                    background: "#F0EBFC",
                    padding: "12px",
                    font: "500 15px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
                    minHeight: "auto",
                  }}
                />
                <button disabled={busy || instruction.trim() === ""} onClick={onStart}>
                  AI 실행 →
                </button>
              </>
            ) : (
              <div
                id="ai-instruction"
                style={{
                  border: "3px solid #14130F",
                  background: "#F0EBFC",
                  padding: "12px",
                  font: "500 15px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
                  whiteSpace: "pre-line",
                  textWrap: "pretty",
                }}
              >
                {instruction}
              </div>
            )}
          </div>

          {/* 실패 — 세션 상태와 무관하게 그린다 (DR-020). 이 라운드의 핵심 수정이다. */}
          {error !== null && (
            <div
              role="alert"
              style={{
                borderBottom: "3px solid #14130F",
                background: "#FBEEEA",
                color: "#A83A22",
                padding: "14px 20px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ font: "700 13px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.06em" }}>
                AI 수행 실패
              </div>
              <ErrorNotice error={error} compact />
              <div style={{ font: "400 13px/1.4 'IBM Plex Sans KR', system-ui, sans-serif", color: "#6B675C" }}>
                그때까지 기록된 Step {steps.length}개는 보존됐습니다. 이름을 붙여 저장하거나
                직접 이어서 만들 수 있습니다.
              </div>
            </div>
          )}

          {blocked !== null && (
            <div
              role="alert"
              style={{
                borderBottom: "3px solid #14130F",
                background: "#FFF9D6",
                padding: "14px 20px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ font: "700 13px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.06em" }}>
                AI 가 멈췄습니다
              </div>
              <div style={{ font: "500 14px/1.5 'IBM Plex Sans KR', system-ui, sans-serif" }}>{blocked.reason}</div>
            </div>
          )}

          <div
            style={{
              flex: "0 0 46px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "0 20px",
              borderBottom: "3px solid #14130F",
              background: "#E4DFD1",
            }}
          >
            <div style={{ font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.12em" }}>
              AI 수행 → 기록된 STEP
            </div>
            <div style={{ flex: "1" }} />
            <div style={{ font: "700 13px/1 'IBM Plex Mono', ui-monospace, monospace" }}>{steps.length}</div>
          </div>

          <div style={{ flex: "1", minHeight: "0", display: "flex", flexDirection: "column", overflowY: "auto" }}>
            {/* 확정 디자인은 Step 이 이미 쌓인 상태만 보여준다 (DC-009). */}
            {steps.length === 0 && (
              <div style={{ padding: "16px 20px", color: "#9A968A" }}>
                {running ? "AI 가 수행 중입니다…" : "아직 기록된 Step 이 없습니다."}
              </div>
            )}

            {steps.map((step) => (
              <StepRow key={step.id} step={step} />
            ))}

            {/* 진행 로그. 실패도 여기 남아 볼 경로가 둘이 된다 (research R2). */}
            {messages.length > 0 && (
              <div style={{ padding: "12px 20px", borderTop: "2px solid #DCD8CC" }}>
                <button className="ghost" onClick={() => setExpanded(!expanded)} style={{ padding: 0, height: 28 }}>
                  진행 기록 {messages.length}건 {expanded ? "접기" : "펼치기"}
                </button>
                {expanded && (
                  <div
                    style={{
                      marginTop: 8,
                      font: "400 12px/1.6 'IBM Plex Mono', ui-monospace, monospace",
                      color: "#6B675C",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {messages.join("\n")}
                  </div>
                )}
              </div>
            )}
          </div>

          <div
            style={{
              borderTop: "3px solid #14130F",
              padding: "16px 20px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              background: "#EFEBE0",
            }}
          >
            <div style={{ display: "flex", gap: "10px", borderLeft: "4px solid #14130F", paddingLeft: "12px" }}>
              <div style={{ font: "500 13px/1.5 'IBM Plex Sans KR', system-ui, sans-serif", textWrap: "pretty" }}>
                지시문은 테스트로 저장되지 않습니다. AI가 실제로 성공한 동작만 Step으로
                저장되고, 다시 돌릴 때는 AI를 쓰지 않습니다.
              </div>
            </div>

            {/* 확정 디자인에 이름 입력이 없다 — 저장에는 이름이 필요하다 (FR-028). */}
            <input
              aria-label="테스트 이름"
              placeholder="테스트 이름"
              value={saveName}
              onChange={(e) => onSaveNameChange(e.target.value)}
              style={{ border: "3px solid #14130F", background: "#FFFDF6", minHeight: "44px" }}
            />

            <button
              disabled={busy || steps.length === 0 || saveName.trim() === ""}
              onClick={onSave}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "9px",
                height: "50px",
                background: "#14130F",
                color: "#F5F2E9",
                border: "3px solid #14130F",
                boxShadow: "5px 5px 0 #F5D000",
                font: "600 16px/1 'IBM Plex Sans KR', system-ui, sans-serif",
              }}
            >
              테스트로 저장
            </button>

            {steps.length === 0 && (
              <div style={{ color: "#6B675C", fontSize: 13 }}>Step 이 없으면 저장할 수 없습니다.</div>
            )}
          </div>
        </div>
      </div>
    </Artboard>
  );
}

function statusLabel({
  composing,
  running,
  error,
  blocked,
}: {
  composing: boolean;
  running: boolean;
  error: ErrorInfo | null;
  blocked: AiBlockedState | null;
}): string {
  // 확정 디자인은 「AI 수행 중」 하나만 보여준다. 나머지는 DC-009 기록 대상이다.
  if (composing) return "지시문 작성";
  if (error !== null) return "AI 수행 실패";
  if (blocked !== null) return "AI 멈춤";
  if (running) return "AI 수행 중";
  return "AI 수행 완료";
}

function StepRow({ step }: { step: Step }) {
  const byAi = step.author === "ai";
  return (
    <div
      style={{
        display: "flex",
        gap: "12px",
        padding: "10px 20px",
        borderBottom: "2px solid #DCD8CC",
        ...(byAi ? { background: "#F0EBFC" } : {}),
      }}
    >
      <div
        style={{
          flex: "0 0 24px",
          height: "24px",
          background: byAi ? "#7C4DDB" : "#2E9455",
          color: "#FFFDF6",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.8">
          <path d="M3 8.5l3.5 3.5L13 4.5" />
        </svg>
      </div>
      <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ font: "600 15px/1.2 'IBM Plex Sans KR', system-ui, sans-serif" }}>{step.label}</div>
        <div
          style={{
            font: "400 13px/1.4 'IBM Plex Mono', ui-monospace, monospace",
            color: byAi ? "#55507A" : "#6B675C",
          }}
        >
          {describe(step)}
        </div>
      </div>
    </div>
  );
}

/** 확정 디자인의 `click role=button "저장"` 형태를 따른다. */
function describe(step: Step): string {
  const s = step as unknown as Record<string, unknown>;
  const target = typeof s.target === "object" && s.target !== null ? (s.target as Record<string, unknown>) : null;
  const hint = target?.role ?? target?.label ?? target?.text ?? target?.test_id ?? "";
  const value = typeof s.value === "string" ? ` "${s.value}"` : "";
  return `${step.type}${hint ? ` ${String(hint)}` : ""}${value}`.trim();
}
