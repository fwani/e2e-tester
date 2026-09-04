/**
 * 오른쪽 460px Step 패널. `Main.dc.html`·`RunnerPaused.dc.html`·`Takeover.dc.html` 공통.
 *
 * 확정 디자인의 행 구조를 그대로 옮겼다: `26px` 번호 · 이름 + 동작 칩 + locator 요약 ·
 * 소요 시간 · `24px` 결과 표식.
 *
 * 원칙 I — 사람 Step 과 AI Step 은 **같은 모델**이다. 여기서 다르게 그리는 것은
 * 작성 주체 표시(색)뿐이고, 구조는 하나다.
 */
import type { ReactNode } from "react";

import type { Step } from "../../types/generated/step";
import type { TargetLocator } from "../../types/generated/step";

export type StepOutcome = "pass" | "fail" | "running" | "pending";

/** 확정 디자인의 헤더 바 (잉크 배경 + TEST STEPS + 작성 배지 + 개수). */
export function StepPanelHeader({
  authoring,
  count,
  children,
}: {
  authoring: "record" | "ai";
  count: number;
  children?: ReactNode;
}) {
  return (
    <div
      style={{
        flex: "0 0 50px",
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "0 18px",
        background: "#14130F",
        color: "#EFEBE0",
      }}
    >
      <div style={{ font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.12em" }}>
        TEST STEPS
      </div>
      <div style={{ flex: "1" }} />
      {children}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "7px",
          padding: "5px 9px",
          border: "2px solid #6B675C",
          font: "600 11px/1 'IBM Plex Mono', ui-monospace, monospace",
          letterSpacing: "0.06em",
        }}
      >
        {authoring === "ai" ? (
          <svg width="10" height="10" viewBox="0 0 18 18" fill="none" stroke="#7C4DDB" strokeWidth="2.4">
            <path d="M9 1.5v4M9 12.5v4M1.5 9h4M12.5 9h4" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 12 12">
            <circle cx="6" cy="6" r="4" fill="#D9502F" />
          </svg>
        )}
        작성 {authoring === "ai" ? "AI" : "RECORD"}
      </div>
      <div style={{ font: "700 14px/1 'IBM Plex Mono', ui-monospace, monospace" }}>{count}</div>
    </div>
  );
}

/** 확정 디자인의 결과 표식. 통과는 초록 체크, 실패는 붉은 ×, 대기는 빈 테두리. */
export function OutcomeMark({ outcome }: { outcome: StepOutcome }) {
  if (outcome === "pending") {
    return (
      <div
        style={{
          width: "24px",
          height: "24px",
          border: "2px solid #9A968A",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      />
    );
  }
  if (outcome === "running") {
    return (
      <div
        style={{
          width: "24px",
          height: "24px",
          border: "2px solid #14130F",
          background: "#F5D000",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      />
    );
  }
  const pass = outcome === "pass";
  return (
    <div
      style={{
        width: "24px",
        height: "24px",
        background: pass ? "#2E9455" : "#D9502F",
        color: "#FFFDF6",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {pass ? (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.8">
          <path d="M3 8.5l3.5 3.5L13 4.5" />
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.8">
          <path d="M4 4l8 8M12 4l-8 8" />
        </svg>
      )}
    </div>
  );
}

/**
 * 요소를 어떻게 찾는지 한 줄로. 확정 디자인의 `role=menuitem`·`testId=…` 형태.
 *
 * **`verified` 후보만 쓴다** (원칙 IV). 모호(`ambiguous`)하거나 검증에 실패한 후보를
 * 요약에 넣으면 실제로 쓰이지 않을 후보를 "이걸로 찾습니다" 라고 보여 주는 셈이 된다.
 */
export function locatorSummary(step: Step): string {
  if (step.type === "navigate") return step.url;
  if (step.type === "close_tab") return `탭 ${step.tab}`;
  if (step.type === "assertion") {
    const a = step.assertion;
    return a.value ? `${a.kind} ${a.value}` : a.kind;
  }
  if (step.type === "drag") {
    // 끄는 대상만 보여주면 어디로 놓는지 알 수 없다 — 두 요소를 함께 요약한다.
    return `${describeTarget(step.target)} → ${describeTarget(step.drop_target)}`;
  }
  return describeTarget(step.target);
}

/** 한 요소의 적용될 식별 정보. `verified` 후보만 쓴다 (원칙 IV). */
function describeTarget(t: TargetLocator): string {
  if (t.test_id?.status === "verified") return `testId=${t.test_id.value}`;
  if (t.role && t.accessible_name && t.role_status === "verified")
    return `role=${t.role} "${t.accessible_name}"`;
  if (t.label?.status === "verified") return `label=${t.label.value}`;
  if (t.text?.status === "verified") return `text="${t.text.value}"`;
  if (t.css?.status === "verified") return `css=${t.css.value}`;
  return "식별 후보 없음";
}

/** 입력값. 민감 값은 `{{변수명}}` 참조로만 저장되므로 그대로 보여도 안전하다 (FR-083). */
function stepValue(step: Step): string | null {
  if (step.type === "fill" || step.type === "select") return step.value;
  return null;
}

export function DesignStepRow({
  index,
  step,
  outcome,
  durationMs,
  selected,
  paused,
  onSelect,
  actions,
}: {
  index: number;
  step: Step;
  outcome: StepOutcome;
  durationMs?: number;
  /** Step 상세를 보고 있는 항목. */
  selected?: boolean;
  /** 일시정지 위치 (FR-034) — 확정 디자인이 노란 왼쪽 띠로 구분한다. */
  paused?: boolean;
  onSelect?: () => void;
  actions?: ReactNode;
}) {
  return (
    <div
      onClick={onSelect}
      style={{
        display: "flex",
        gap: "14px",
        padding: "15px 18px",
        borderBottom: "2px solid #DCD8CC",
        alignItems: "flex-start",
        cursor: onSelect ? "pointer" : "default",
        ...(paused ? { borderLeft: "4px solid #F5D000", background: "#FFF9D6" } : {}),
        ...(selected && !paused ? { background: "#F6F4EE" } : {}),
      }}
    >
      <div
        style={{
          flex: "0 0 26px",
          font: "700 15px/1.2 'IBM Plex Mono', ui-monospace, monospace",
          color: "#9A968A",
        }}
      >
        {String(index + 1).padStart(2, "0")}
      </div>

      <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ font: "600 15px/1.3 'IBM Plex Sans KR', system-ui, sans-serif" }}>{step.label}</div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <div
            style={{
              padding: "4px 7px",
              border: "2px solid #14130F",
              background: step.author === "ai" ? "#F0EBFC" : "#EFEBE0",
              font: "700 10px/1 'IBM Plex Mono', ui-monospace, monospace",
              letterSpacing: "0.08em",
            }}
          >
            {step.type.toUpperCase()}
          </div>

          {/*
            FR-030a — 최초 탭이 아닌 Step 은 어느 탭에서 일어나는지 보여야 한다.
            확정 디자인의 표본이 단일 탭이라 이 배지가 없다. 없는 상태를 정의하지 않은
            것이지 요구를 없앤 것이 아니므로, 같은 칩 형태로 그린다 (DC-009).
          */}
          {step.tab > 0 && (
            <div
              style={{
                padding: "4px 7px",
                border: "2px solid #14130F",
                background: "#FFFDF6",
                font: "700 10px/1 'IBM Plex Mono', ui-monospace, monospace",
                letterSpacing: "0.08em",
              }}
            >
              탭 {step.tab}
            </div>
          )}

          <div style={{ font: "400 13px/1 'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}>
            {locatorSummary(step)}
          </div>

          {/* FR-083 — 민감 값은 참조로만 저장되므로 표시해도 평문이 새지 않는다. */}
          {stepValue(step) !== null && (
            <div
              style={{
                font: "400 13px/1 'IBM Plex Mono', ui-monospace, monospace",
                color: "#5A31B8",
              }}
            >
              {stepValue(step)}
            </div>
          )}
        </div>
        {actions}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {durationMs !== undefined && (
          <div style={{ font: "400 13px/1 'IBM Plex Mono', ui-monospace, monospace", color: "#6B675C" }}>
            {durationMs} ms
          </div>
        )}
        <OutcomeMark outcome={outcome} />
      </div>
    </div>
  );
}
