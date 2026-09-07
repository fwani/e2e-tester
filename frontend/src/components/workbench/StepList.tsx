/**
 * **단일 Step 목록** (007 T021 · FR-221·FR-222·FR-223).
 *
 * 007 이 고치는 것의 핵심이다. 이 파일이 생기기 전 Step 목록을 그리는 구현이 **4벌**
 * 따로 있었다.
 *
 *   `components/design/DesignStepList.tsx` 의 `DesignStepRow`  ← 실행·일시정지·사람조작
 *   `pages/AiRecord.tsx:532` 의 `StepRow`                       ← AI 작성
 *   `pages/RunResult.tsx:718` 의 `StepRow`                      ← 결과보기
 *   `pages/TestDefinition.tsx:540` 의 인라인 렌더                ← 편집
 *
 * 그 결과 같은 정보가 국면에 따라 정반대 자리에 있었다 — 결말 표식이 세션 화면은 행의
 * **오른쪽 끝**, 결과 화면은 행의 **왼쪽 첫 칸**이었다 (S-02). AI 작성 화면에는 Step
 * 번호가 아예 없어서(S-08) 「Step 06 …」 안내와 대응되지 않았고, 결말 자리에는 **항상
 * 체크 표식**이 있어 통과처럼 보였다 (S-09).
 *
 * **칸의 자리는 국면과 무관하게 고정이다** (FR-222).
 *
 *   [번호 26px] [이름 + 동작 칩 + 탭 배지 + 대상 요약 + 값] [소요 시간] [결말 표식 24px]
 *
 * 그 국면에서 값이 없는 칸은 **비우되 다른 칸을 그 자리로 당기지 않는다** (FR-223).
 *
 * 인라인 style 값은 `docs/design/Main.dc.html`·`RunnerPaused.dc.html` 에서 그대로 옮겼다
 * (DC-001). `DesignStepList.tsx` 가 이미 그렇게 옮겨 둔 것을 흡수했다.
 */
import type { ReactNode } from "react";

import { displayOutcomeLabel, stepNumber } from "../../lib/wording";
import type { Step, TargetLocator } from "../../types/generated/step";
import type { StepOutcome, WorkbenchStep } from "./model";

const INK = "#14130F";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

/**
 * 확정 디자인의 헤더 바 (잉크 배경 + TEST STEPS + 작성 배지 + 개수).
 * `Main.dc.html` 의 `flex: 0 0 50px` 블록 전사.
 */
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
        background: INK,
        color: "#EFEBE0",
      }}
    >
      <div style={{ font: `600 12px/1 ${MONO}`, letterSpacing: "0.12em" }}>TEST STEPS</div>
      <div style={{ flex: "1" }} />
      {children}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "7px",
          padding: "5px 9px",
          border: "2px solid #6B675C",
          font: `600 11px/1 ${MONO}`,
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
      <div style={{ font: `700 14px/1 ${MONO}` }}>{count}</div>
    </div>
  );
}

/**
 * 결말 표식. **일곱 값 전부 텍스트 라벨을 갖는다** (005 FR-141·FR-151).
 *
 * `recorded`(기록됨)가 007 이 더한 값이다. 통과 체크를 그리지 않는다 — 근거는
 * `design-conformance/undefined-states.md` 에 있다 (research R4).
 */
export function OutcomeMark({ outcome }: { outcome: StepOutcome }) {
  const label = displayOutcomeLabel(outcome);

  if (outcome === "recorded") {
    return (
      <div
        aria-label={label}
        title={`${label} — 작성 중이라 재생 결말이 아직 없습니다`}
        data-outcome="recorded"
        style={{
          width: "24px",
          height: "24px",
          border: "2px solid #9A968A",
          background: "#FFFDF6",
          color: "#6B675C",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          font: `600 10px/1 ${SANS}`,
        }}
      >
        기록
      </div>
    );
  }

  if (outcome === "skipped") {
    return (
      <div
        aria-label={label}
        title={`${label} — 이 실행에서 실행 대상이 아니었습니다`}
        data-outcome="skipped"
        style={{
          width: "24px",
          height: "24px",
          border: "2px solid #9A968A",
          background: "#EDEAE0",
          color: "#6B675C",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          font: `600 11px/1 ${SANS}`,
        }}
      >
        건너뜀
      </div>
    );
  }

  if (outcome === "not_run") {
    return (
      <div
        aria-label={label}
        title={`${label} — 앞선 Step 이 실패해 도달하지 못했습니다`}
        data-outcome="not_run"
        style={{
          width: "24px",
          height: "24px",
          border: "2px dashed #9A968A",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      />
    );
  }

  if (outcome === "pending") {
    return (
      <div
        aria-label={label}
        data-outcome="pending"
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
        aria-label={label}
        data-outcome="running"
        style={{
          width: "24px",
          height: "24px",
          border: `2px solid ${INK}`,
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
      aria-label={label}
      data-outcome={outcome}
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
 * **`verified` 후보만 쓴다** (원칙 IV). 모호하거나 검증에 실패한 후보를 요약에 넣으면
 * 실제로 쓰이지 않을 후보를 "이걸로 찾습니다" 라고 보여 주는 셈이 된다.
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

export interface StepListProps {
  steps: WorkbenchStep[];
  authoring: "record" | "ai";
  focusedStepId: string | null;
  /** Step 지목. 일곱 국면 전부에서 같은 방식이다 (FR-227) */
  onSelect: (stepId: string) => void;
  /** 행 안의 편집 조작. 권한이 허락하는 국면에서만 어댑터가 준다 */
  rowActions?: (step: WorkbenchStep) => ReactNode;
  /** 헤더 오른쪽에 얹는 것 (순서 변경 토글 등) */
  headerExtra?: ReactNode;
  /** Step 이 0개일 때의 안내. 국면마다 다르다 */
  emptyNotice?: ReactNode;
}

/**
 * 우측 460px 패널. `Main.dc.html`·`RunnerPaused.dc.html`·`Takeover.dc.html` 공통.
 */
export function StepList({
  steps,
  authoring,
  focusedStepId,
  onSelect,
  rowActions,
  headerExtra,
  emptyNotice,
}: StepListProps) {
  return (
    <div
      data-workbench-step-panel
      style={{
        flex: "0 0 460px",
        borderLeft: `3px solid ${INK}`,
        background: "#FFFDF6",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <StepPanelHeader authoring={authoring} count={steps.length}>
        {headerExtra}
      </StepPanelHeader>

      <div style={{ flex: "1", minHeight: "0", overflowY: "auto" }}>
        {steps.length === 0 && (
          <div style={{ padding: "18px", color: "#9A968A", font: `400 13px/1.5 ${SANS}` }}>
            {emptyNotice ?? "아직 Step 이 없습니다."}
          </div>
        )}
        {steps.map((s) => (
          <StepRow
            key={s.id}
            step={s}
            selected={s.id === focusedStepId}
            onSelect={() => onSelect(s.id)}
            actions={rowActions?.(s)}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * Step 행 하나 — **유일한 구현**.
 *
 * 행 전체가 누를 수 있는 요소다. `button` 역할을 갖는 이유는 접근성이자 기존 테스트의
 * `getByRole` 이 그것에 의존하기 때문이다 (002 §2 의 4번 예외).
 */
function StepRow({
  step,
  selected,
  onSelect,
  actions,
}: {
  step: WorkbenchStep;
  selected: boolean;
  onSelect: () => void;
  actions?: ReactNode;
}) {
  const dsl = step.step;
  const value = dsl ? stepValue(dsl) : null;

  return (
    <div
      data-step-row={step.id}
      style={{
        display: "flex",
        gap: "14px",
        padding: "15px 18px",
        borderBottom: "2px solid #DCD8CC",
        alignItems: "flex-start",
        ...(step.isPausedHere ? { borderLeft: "4px solid #F5D000", background: "#FFF9D6" } : {}),
        ...(selected && !step.isPausedHere ? { background: "#F6F4EE" } : {}),
      }}
    >
      {/* 칸 1 — 번호 26px. **모든 국면에서 보인다** (FR-224 · S-08) */}
      <div
        data-cell="number"
        style={{ flex: "0 0 26px", font: `700 15px/1.2 ${MONO}`, color: "#9A968A" }}
      >
        {stepNumber(step.index)}
      </div>

      {/* 칸 2 — 이름과 부속 정보 */}
      <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column", gap: "6px" }}>
        <button
          type="button"
          onClick={onSelect}
          aria-pressed={selected}
          style={{
            border: "none",
            background: "transparent",
            boxShadow: "none",
            padding: 0,
            textAlign: "left",
            font: `600 15px/1.3 ${SANS}`,
            color: INK,
            cursor: "pointer",
          }}
        >
          {step.label}
        </button>

        <div
          data-cell="detail"
          style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", minHeight: 18 }}
        >
          {/*
            결과 국면에서 정의와 매칭되지 않은 행은 이 칸들이 **빈다.** 다른 칸을 그
            자리로 당기지 않는다 (FR-223 · research R3).
          */}
          {dsl !== null && (
            <>
              <div
                data-cell="type"
                style={{
                  padding: "4px 7px",
                  border: `2px solid ${INK}`,
                  background: dsl.author === "ai" ? "#F0EBFC" : "#EFEBE0",
                  font: `700 10px/1 ${MONO}`,
                  letterSpacing: "0.08em",
                }}
              >
                {dsl.type.toUpperCase()}
              </div>

              {/* FR-030a — 최초 탭이 아닌 Step 은 어느 탭에서 일어나는지 보여야 한다 */}
              {dsl.tab > 0 && (
                <div
                  data-cell="tab"
                  style={{
                    padding: "4px 7px",
                    border: `2px solid ${INK}`,
                    background: "#FFFDF6",
                    font: `700 10px/1 ${MONO}`,
                    letterSpacing: "0.08em",
                  }}
                >
                  탭 {dsl.tab}
                </div>
              )}

              <div data-cell="locator" style={{ font: `400 13px/1 ${MONO}`, color: "#6B675C" }}>
                {locatorSummary(dsl)}
              </div>

              {/* FR-083 — 민감 값은 참조로만 저장되므로 표시해도 평문이 새지 않는다 */}
              {value !== null && (
                <div data-cell="value" style={{ font: `400 13px/1 ${MONO}`, color: "#5A31B8" }}>
                  {value}
                </div>
              )}
            </>
          )}
        </div>
        {actions}
      </div>

      {/* 칸 3 — 소요 시간. 없으면 자리를 비운다 (FR-223) */}
      <div
        data-cell="duration"
        style={{
          flex: "0 0 66px",
          textAlign: "right",
          font: `400 13px/1 ${MONO}`,
          color: "#6B675C",
          paddingTop: 4,
        }}
      >
        {step.durationMs !== null ? `${step.durationMs} ms` : ""}
      </div>

      {/* 칸 4 — 결말 표식 24px. **오른쪽 끝이다** (S-02 해소) */}
      <div data-cell="outcome" style={{ flex: "0 0 24px", paddingTop: 2 }}>
        <OutcomeMark outcome={step.outcome} />
      </div>
    </div>
  );
}
