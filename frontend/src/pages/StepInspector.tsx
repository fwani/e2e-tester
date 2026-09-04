/**
 * Step 상세. **`docs/design/StepInspector.dc.html`(640×1140) 전사.** DC-001~DC-008.
 *
 * 확정 디자인이 독립 artboard 로 정의하므로 `SessionScreen` 이 겹침 화면으로 띄운다.
 *
 * Step 상세 (T141). `StepInspector.dc.html` 이식.
 *
 * 두 가지를 한다 — **보여 주는 것**(어떤 기준으로 요소를 찾는지)과 **고치는 것**(표시
 * 이름·입력값·타임아웃·민감 여부).
 *
 * 후보 우선순위 표는 `LocatorPriorityTable` 이 그린다. `drag` 는 대상 요소를 둘 가지므로
 * 표를 둘 그리고, "다시 집기" 도 어느 쪽인지 골라서 요청한다 (T166) — 하나만 그리면
 * 놓는 위치의 후보를 볼 수 없고 고칠 수도 없다.
 *
 * **민감 지정은 값을 옮기는 조작이다** (FR-082b). 지정하면 지금 정의에 남아 있는 평문이
 * 변수 참조로 바뀌고 실제 값은 봉인되어 비밀 파일로 간다. 되돌리는 기능은 없다 — 되돌리려면
 * 평문을 다시 정의에 쓰는 것이므로 FR-082 위반이다.
 */
import { useEffect, useState } from "react";

import type { RepickSlot } from "../api/client";
import type { Step } from "../types/generated/step";
import { LocatorPriorityTable } from "../components/LocatorPriorityTable";

export interface StepInspectorProps {
  step: Step;
  index: number;
  busy?: boolean;
  /** 다시 집기 대기 중인 슬롯. 대기 중이면 안내를 보여 준다 (FR-020). */
  repickWaiting?: RepickSlot | null;
  onSave: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    sensitive?: boolean;
  }) => void;
  onRepick: (slot: RepickSlot) => void;
  onClose?: () => void;
}

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

export function StepInspector({
  step,
  index,
  busy = false,
  repickWaiting = null,
  onSave,
  onRepick,
  onClose,
}: StepInspectorProps) {
  const [label, setLabel] = useState(step.label);
  const [value, setValue] = useState(hasValue(step) ? step.value : "");
  const [timeout, setTimeout] = useState(step.timeout_ms);
  const [sensitive, setSensitive] = useState(false);
  const [showDsl, setShowDsl] = useState(false);

  // 다른 Step 을 고르면 입력값을 그 Step 기준으로 다시 잡는다.
  useEffect(() => {
    setLabel(step.label);
    setValue(hasValue(step) ? step.value : "");
    setTimeout(step.timeout_ms);
    setSensitive(false);
  }, [step]);

  const editable = hasValue(step);
  const alreadyReference = editable && isReference(value);

  return (
    <div
      style={{
        width: "640px",
        minHeight: "1020px",
        background: "#FFFDF6",
        borderLeft: "3px solid #14130F",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          flex: "0 0 56px",
          background: "#14130F",
          color: "#EFEBE0",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "0 20px",
        }}
      >
        <div style={{ font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.12em" }}>
          STEP 상세
        </div>
        <div style={{ flex: "1" }} />
        {onClose && (
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
        )}
      </div>

      <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "18px" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ font: "700 15px/1 'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}>
            {String(index + 1).padStart(2, "0")}
          </div>
          <div
            style={{
              padding: "5px 8px",
              border: "2px solid #14130F",
              background: "#EFEBE0",
              font: "700 11px/1 'IBM Plex Mono', ui-monospace, monospace",
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
              border: "2px solid #14130F",
              background: step.author === "ai" ? "#F0EBFC" : "#FFFDF6",
              font: "700 11px/1 'IBM Plex Mono', ui-monospace, monospace",
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
        </div>
        <div
          style={{
            fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
            fontSize: "28px",
            lineHeight: "1.1",
          }}
        >
          {step.label}
        </div>
      </div>

      <div>
        <label htmlFor="inspector-label">표시 이름</label>
        <input
          id="inspector-label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
      </div>

      {editable && (
        <div>
          <label htmlFor="inspector-value">입력값</label>
          <input
            id="inspector-value"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          {alreadyReference ? (
            <p className="dim" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
              변수 참조입니다. 실제 값은 비밀 파일의 암호문에 있으며 화면에 표시되지
              않습니다.
            </p>
          ) : (
            <label className="row" style={{ gap: 6, marginTop: 6 }}>
              <input
                type="checkbox"
                checked={sensitive}
                onChange={(e) => setSensitive(e.target.checked)}
              />
              <span>
                민감 값으로 지정 — 값을 변수 참조로 옮기고 봉인합니다 (되돌릴 수 없습니다)
              </span>
            </label>
          )}
        </div>
      )}

      <div>
        <label htmlFor="inspector-timeout">대기 시간 (ms)</label>
        <input
          id="inspector-timeout"
          type="number"
          min={1}
          max={60000}
          value={timeout}
          onChange={(e) => setTimeout(Number(e.target.value))}
        />
      </div>

      {"target" in step && (
        <LocatorPriorityTable
          target={step.target}
          title={step.type === "drag" ? "끄는 대상" : "대상 요소"}
          onRepick={() => onRepick("target")}
          repicking={repickWaiting === "target"}
          busy={busy}
        />
      )}

      {step.type === "drag" && (
        <LocatorPriorityTable
          target={step.drop_target}
          title="놓는 위치"
          onRepick={() => onRepick("drop_target")}
          repicking={repickWaiting === "drop_target"}
          busy={busy}
        />
      )}

      {step.type === "assertion" && step.assertion.target && (
        <LocatorPriorityTable
          target={step.assertion.target}
          title="검증 대상"
          busy={busy}
        />
      )}

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

      <div style={{ display: "flex", gap: "10px" }}>
        <button
          disabled={busy}
          onClick={() =>
            onSave({
              label: label.trim() !== "" ? label.trim() : undefined,
              value: editable && !alreadyReference ? value : undefined,
              timeout_ms: timeout,
              sensitive: sensitive || undefined,
            })
          }
          style={{
            flex: "1",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "9px",
            height: "48px",
            border: "3px solid #14130F",
            background: "#14130F",
            color: "#F5F2E9",
            boxShadow: "5px 5px 0 #F5D000",
            font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
          }}
        >
          저장
        </button>
        {"target" in step && (
          <button
            disabled={busy || repickWaiting !== null}
            onClick={() => onRepick("target")}
            style={{
              flex: "1",
              display: "flex",
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
          >
            <svg width="15" height="15" viewBox="0 0 20 20">
              <circle cx="10" cy="10" r="5" fill="#D9502F" />
            </svg>
            다시 집기
          </button>
        )}
      </div>
      </div>
    </div>
  );
}
