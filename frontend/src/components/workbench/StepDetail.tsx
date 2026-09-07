/**
 * **단일 Step 상세** (007 T022 · FR-229·FR-230·FR-231).
 *
 * 이 파일이 생기기 전 Step 상세를 그리는 구현이 **2벌**이었다.
 *
 *   `pages/StepInspector.tsx`         ← 세션 화면이 겹침으로 띄운다 (640×1140)
 *   `pages/TestDefinition.tsx:633`    ← 편집 화면이 목록 아래 인라인으로 편다
 *
 * 같은 Step 을 보는데 국면에 따라 **열리는 자리**가 달랐다 (S-05). 007 은 하나로 합치고
 * 자리를 고정한다 — 우측에서 겹치는 640px 이며 일곱 국면 전부에서 같다 (FR-230).
 *
 * **`attempts` 와 `candidates` 를 둘 다 갖는다.** 결과 국면에서 사용자가 알아야 하는 것은
 * "정의에 무엇이 있는가" 가 아니라 "그때 무엇을 시도했고 왜 못 찾았는가" 다. 편집
 * 국면에서는 반대다. 한 칸에 뭉개면 국면에 따라 같은 자리가 다른 뜻을 갖는다.
 *
 * **조작 가능 여부는 스스로 판단하지 않는다** — `capabilities` 를 받아 그대로 따른다
 * (UC-000). 이전에는 편집 화면과 세션 화면이 각자 판단했고, 그래서 편집 화면은 "실행을
 * 시작해 일시정지한 뒤 하세요" 라고 안내하면서 그리로 가는 버튼을 주지 않았다 (006 E-03).
 *
 * 인라인 style 값은 `docs/design/StepInspector.dc.html` 에서 그대로 옮겼다 (DC-001) —
 * `pages/StepInspector.tsx` 가 이미 전사해 둔 것을 이식했다.
 */
import { useEffect, useState } from "react";

import type { RepickSlot } from "../../api/client";
import { InlineSecretInput, referenceName } from "../InlineSecretInput";
import { LocatorPriorityTable } from "../LocatorPriorityTable";
import type { CapabilityMap } from "../../lib/capabilities";
import { stepNumber } from "../../lib/wording";
import type { Step } from "../../types/generated/step";
import { ActionButton } from "./ActionButton";
import type { StepDetail as StepDetailModel } from "./model";

const INK = "#14130F";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

/** 값이 `{{변수명}}` 참조인가. 민감 값은 참조로만 저장된다 (FR-082). */
function isReference(value: string): boolean {
  return /^\{\{[A-Z][A-Z0-9_]*\}\}$/.test(value);
}

function hasValue(step: Step): step is Extract<Step, { value: string }> {
  return step.type === "fill" || step.type === "select";
}

/** 저장된 정의 그대로의 미리보기 (FR-016). 파일 내용과 일치해야 한다. */
function dslPreview(step: Step): string {
  return JSON.stringify(step, null, 2);
}

export interface StepDetailProps {
  detail: StepDetailModel;
  capabilities: CapabilityMap;
  busy?: boolean;
  onSave: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    sensitive?: boolean;
  }) => void;
  onRepick: (slot: RepickSlot) => void;
  onClose: () => void;
  /** 비활성 조작의 해소 방법을 눌렀을 때 */
  onRemedy?: (action: keyof CapabilityMap) => void;
}

export function StepDetail({
  detail,
  capabilities,
  busy = false,
  onSave,
  onRepick,
  onClose,
  onRemedy,
}: StepDetailProps) {
  const step = detail.step;
  const [label, setLabel] = useState(step?.label ?? "");
  const [value, setValue] = useState(step && hasValue(step) ? step.value : "");
  const [timeoutMs, setTimeoutMs] = useState(step?.timeout_ms ?? 5000);
  const [sensitive, setSensitive] = useState(false);
  const [showDsl, setShowDsl] = useState(false);
  const [secretOpen, setSecretOpen] = useState(false);

  // 다른 Step 을 고르면 입력값을 그 Step 기준으로 다시 잡는다.
  useEffect(() => {
    setLabel(step?.label ?? "");
    setValue(step && hasValue(step) ? step.value : "");
    setTimeoutMs(step?.timeout_ms ?? 5000);
    setSensitive(false);
    setSecretOpen(false);
  }, [step]);

  const canEdit = capabilities["step.update"].kind === "enabled";
  const canMarkSensitive = capabilities["step.markSensitive"].kind === "enabled";
  const hasValueField = step !== null && hasValue(step);
  const alreadyReference = hasValueField && isReference(value);

  return (
    <div
      data-workbench-step-detail
      role="dialog"
      aria-label="Step 상세"
      style={{
        width: "640px",
        background: "#FFFDF6",
        borderLeft: `3px solid ${INK}`,
        display: "flex",
        flexDirection: "column",
        overflowY: "auto",
      }}
    >
      <div
        style={{
          flex: "0 0 56px",
          background: INK,
          color: "#EFEBE0",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "0 20px",
        }}
      >
        <div style={{ font: `600 12px/1 ${MONO}`, letterSpacing: "0.12em" }}>STEP 상세</div>
        <div style={{ flex: "1" }} />
        <button
          aria-label="닫기"
          onClick={onClose}
          style={{
            width: "44px",
            height: "44px",
            border: "2px solid #6B675C",
            background: "transparent",
            color: "inherit",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 0,
            boxShadow: "none",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.4">
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </button>
      </div>

      <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "18px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ font: `700 15px/1 ${MONO}`, color: "#6B675C" }}>
              {stepNumber(detail.index)}
            </div>
            {step !== null && (
              <>
                <div
                  style={{
                    padding: "5px 8px",
                    border: `2px solid ${INK}`,
                    background: "#EFEBE0",
                    font: `700 11px/1 ${MONO}`,
                    letterSpacing: "0.08em",
                  }}
                >
                  {step.type.toUpperCase()}
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "5px 8px",
                    border: `2px solid ${INK}`,
                    background: step.author === "ai" ? "#F0EBFC" : "#FFFDF6",
                    font: `700 11px/1 ${MONO}`,
                  }}
                >
                  {step.author === "ai" ? (
                    <svg width="10" height="10" viewBox="0 0 18 18" fill="none" stroke="#7C4DDB" strokeWidth="2.4">
                      <path d="M9 1.5v4M9 12.5v4M1.5 9h4M12.5 9h4" />
                    </svg>
                  ) : (
                    <svg width="10" height="10" viewBox="0 0 12 12">
                      <circle cx="6" cy="6" r="4" fill="#D9502F" />
                    </svg>
                  )}
                  {step.author === "ai" ? "AI" : "RECORD"}
                </div>
              </>
            )}
          </div>
          <div
            style={{
              fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
              fontSize: "28px",
              lineHeight: "1.1",
            }}
          >
            {step?.label ?? "이 결과 이후 정의에서 사라진 Step"}
          </div>
        </div>

        {/*
          실패 사유 — 결과 국면에만 있다. 국면에 따라 자리가 달라지지 않게 상세의
          **항목 순서 안에** 둔다 (FR-231).
        */}
        {detail.failure !== null && (
          <div
            role="note"
            style={{
              border: "3px solid #D9502F",
              background: "#FBEEEA",
              padding: "12px 14px",
              font: `500 14px/1.5 ${SANS}`,
              color: "#A83A22",
            }}
          >
            {detail.failure.message ?? "실패 이유가 기록되지 않았습니다."}
          </div>
        )}

        {step === null ? (
          <p className="dim" style={{ font: `400 13px/1.6 ${SANS}` }}>
            이 실행에는 있었지만 지금 정의에는 없는 Step 입니다. 결말과 소요 시간은 그때의
            기록이고, 동작 종류·대상 요약·값은 보여줄 수 없습니다.
          </p>
        ) : (
          <>
            <div>
              <label htmlFor="detail-label">표시 이름</label>
              <input
                id="detail-label"
                value={label}
                disabled={!canEdit}
                onChange={(e) => setLabel(e.target.value)}
              />
            </div>

            {hasValueField && (
              <div>
                <label htmlFor="detail-value">입력값</label>
                <input
                  id="detail-value"
                  value={value}
                  disabled={!canEdit || alreadyReference}
                  onChange={(e) => setValue(e.target.value)}
                />
                {alreadyReference ? (
                  <>
                    <p className="dim" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
                      변수 참조입니다. 실제 값은 비밀 파일의 암호문에 있으며 화면에 표시되지
                      않습니다.
                    </p>
                    {canMarkSensitive && (
                      <button
                        className="ghost"
                        style={{ padding: 0, height: 28 }}
                        onClick={() => setSecretOpen((v) => !v)}
                      >
                        {secretOpen ? "▾" : "▸"} 비밀 값 다시 넣기
                      </button>
                    )}
                  </>
                ) : (
                  <label className="row" style={{ gap: 6, marginTop: 6 }}>
                    <input
                      type="checkbox"
                      checked={sensitive}
                      disabled={!canMarkSensitive}
                      onChange={(e) => setSensitive(e.target.checked)}
                    />
                    <span>
                      민감 값으로 지정 — 값을 변수 참조로 옮기고 봉인합니다 (되돌릴 수
                      없습니다)
                    </span>
                  </label>
                )}

                {/* DR-023·SC-106 — 화면 이동 0회. 비밀 값을 이 자리에서 넣는다. */}
                {!alreadyReference && canMarkSensitive && (
                  <button
                    className="ghost"
                    style={{ padding: 0, height: 28, marginTop: 4 }}
                    onClick={() => setSecretOpen((v) => !v)}
                  >
                    {secretOpen ? "▾" : "▸"} 여기서 비밀 값 넣기
                  </button>
                )}

                {secretOpen && (
                  <div style={{ marginTop: 8 }}>
                    <InlineSecretInput
                      currentName={alreadyReference ? referenceName(value) : null}
                      busy={busy}
                      onLinked={(reference) => {
                        setValue(reference);
                        setSecretOpen(false);
                      }}
                    />
                  </div>
                )}
              </div>
            )}

            <div>
              <label htmlFor="detail-timeout">대기 시간 (ms)</label>
              <input
                id="detail-timeout"
                type="number"
                min={1}
                max={60000}
                value={timeoutMs}
                disabled={!canEdit}
                onChange={(e) => setTimeoutMs(Number(e.target.value))}
              />
            </div>
          </>
        )}

        {/*
          그 실행에서 **실제로 시도한** locator — 결과 국면. 정의의 후보와 다른 축이다.
          정의는 "무엇으로 찾을 계획인가" 이고 이것은 "무엇을 시도했고 몇 개가 맞았나" 다.
        */}
        {detail.attempts !== null && detail.attempts.length > 0 && (
          <div style={{ border: `3px solid ${INK}`, background: "#FFFDF6" }}>
            <div
              style={{
                height: "36px",
                display: "flex",
                alignItems: "center",
                padding: "0 12px",
                background: INK,
                color: "#EFEBE0",
                font: `600 11px/1 ${MONO}`,
                letterSpacing: "0.1em",
              }}
            >
              시도한 LOCATOR (우선순위 순)
            </div>
            {detail.attempts.map((a, i) => (
              <div
                key={`${a.candidate}-${i}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 12px",
                  borderTop: "2px solid #DCD8CC",
                  font: `400 12.5px/1.4 ${MONO}`,
                  color: a.matched ? INK : "#6B675C",
                }}
              >
                <span style={{ width: 84, fontWeight: 700 }}>{a.candidate}</span>
                <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {a.expression}
                </span>
                <span style={{ width: 54, textAlign: "right" }}>{a.match_count}개</span>
                <span style={{ width: 62, textAlign: "right" }}>{a.waited_ms} ms</span>
                <span style={{ width: 44, textAlign: "right", fontWeight: 700 }}>
                  {a.matched ? "맞음" : "아님"}
                </span>
              </div>
            ))}
          </div>
        )}

        {/*
          정의가 가진 후보와 적용 순서. **순서는 제품 전역의 고정 규칙이다** —
          Step 마다 바꾸지 않는다 (Principle IV · 006 FR-187).
        */}
        {detail.candidates !== null && (
          <LocatorPriorityTable
            target={detail.candidates}
            title={step?.type === "drag" ? "끄는 대상" : "대상 요소"}
            onRepick={
              capabilities["step.repick"].kind === "enabled" ? () => onRepick("target") : undefined
            }
            repicking={detail.repickWaiting === "target"}
            busy={busy}
          />
        )}

        {detail.dropCandidates !== null && (
          <LocatorPriorityTable
            target={detail.dropCandidates}
            title="놓는 위치"
            onRepick={
              capabilities["step.repick"].kind === "enabled"
                ? () => onRepick("drop_target")
                : undefined
            }
            repicking={detail.repickWaiting === "drop_target"}
            busy={busy}
          />
        )}

        {step !== null && (
          <div>
            <button className="ghost" onClick={() => setShowDsl((v) => !v)}>
              {showDsl ? "▾" : "▸"} 테스트 DSL 미리보기
            </button>
            {showDsl && (
              <pre
                className="mono"
                style={{
                  fontSize: 11,
                  background: "var(--ink)",
                  color: "var(--paper)",
                  padding: 10,
                  overflowX: "auto",
                  margin: "6px 0 0",
                }}
              >
                {dslPreview(step)}
              </pre>
            )}
          </div>
        )}

        {/*
          조작은 **감추지 않는다.** 쓸 수 없으면 비활성으로 남고 이유와 해소 방법이
          붙는다 (FR-234). 「해당 없음」인 국면에서만 `ActionButton` 이 `null` 을 낸다.
        */}
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <ActionButton
            action="step.update"
            capability={capabilities["step.update"]}
            label="저장"
            emphasis
            onRemedy={onRemedy}
            onRun={() =>
              onSave({
                label: label.trim() !== "" ? label.trim() : undefined,
                value: hasValueField && !alreadyReference ? value : undefined,
                timeout_ms: timeoutMs,
                sensitive: sensitive || undefined,
              })
            }
          />
          <ActionButton
            action="step.repick"
            capability={capabilities["step.repick"]}
            label="다시 집기"
            onRemedy={onRemedy}
            onRun={() => onRepick("target")}
            icon={
              <svg width="15" height="15" viewBox="0 0 20 20">
                <circle cx="10" cy="10" r="5" fill="#D9502F" />
              </svg>
            }
          />
        </div>
      </div>
    </div>
  );
}
