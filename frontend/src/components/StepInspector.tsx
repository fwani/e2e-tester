/**
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
import { LocatorPriorityTable } from "./LocatorPriorityTable";

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
        border: "3px solid var(--ink)",
        background: "var(--paper)",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <div className="row" style={{ gap: 8 }}>
        <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
          STEP {String(index + 1).padStart(2, "0")} · {step.type.toUpperCase()}
        </strong>
        <span className="spacer" />
        {onClose && (
          <button className="ghost" onClick={onClose}>
            닫기
          </button>
        )}
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

      <div className="row" style={{ gap: 8 }}>
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
        >
          저장
        </button>
      </div>
    </div>
  );
}
