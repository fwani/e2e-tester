/**
 * Step 목록. `Main.dc.html` · `RunnerPaused.dc.html` 의 우측 패널 (T067).
 *
 * **원칙 I 을 UI 계층까지 밀어 놓은 지점이다.** 사람·AI·자연어 경로가 같은
 * `step_added` 이벤트를 쓰므로 이 컴포넌트에 작성 주체별 분기가 없다.
 * `author` 는 배지 표시에만 쓴다 (FR-014·FR-075).
 */
import type { Step } from "../types/generated/step";
import { AuthorBadge, StepTypeBadge, TabBadge } from "./Badges";

export interface StepListProps {
  steps: Step[];
  /** 다음에 실행할 Step 위치. 일시정지 구분선을 그리는 기준이다 (FR-034). */
  currentIndex?: number;
  /** 일시정지 상태에서만 구분선을 그린다. */
  showPauseMarker?: boolean;
  /** 지금 실행 중인 Step 위치. 실행 중임을 표시한다 (FR-046). */
  runningIndex?: number | null;
  /** Step id → 실행 결과. 통과·실패를 목록에서 바로 보여준다 (FR-046). */
  outcomes?: Record<string, "pass" | "fail">;
  selectedStepId?: string | null;
  durationsMs?: Record<string, number>;
  onSelect?: (stepId: string) => void;
  onDelete?: (stepId: string) => void;
}

/** 적용된 식별 정보 요약. 어느 후보가 쓰일지 보여준다 (FR-027). */
function locatorSummary(step: Step): string | null {
  if (step.type === "navigate") return step.url;
  if (step.type === "close_tab") return `탭 ${step.tab}`;
  if (step.type === "assertion") {
    const a = step.assertion;
    return a.value ? `${a.kind} ${a.value}` : a.kind;
  }
  const t = step.target;
  if (t.test_id?.status === "verified") return `testId=${t.test_id.value}`;
  if (t.role && t.accessible_name && t.role_status === "verified")
    return `role=${t.role} "${t.accessible_name}"`;
  if (t.label?.status === "verified") return `label=${t.label.value}`;
  if (t.text?.status === "verified") return `text="${t.text.value}"`;
  if (t.css?.status === "verified") return `css=${t.css.value}`;
  return "식별 후보 없음";
}

function stepValue(step: Step): string | null {
  if (step.type === "fill" || step.type === "select") return step.value;
  return null;
}

export function StepList({
  steps,
  currentIndex = 0,
  showPauseMarker = false,
  runningIndex = null,
  outcomes = {},
  selectedStepId = null,
  durationsMs = {},
  onSelect,
  onDelete,
}: StepListProps) {
  if (steps.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center", color: "var(--muted)" }}>
        아직 기록된 Step 이 없습니다.
        <br />
        브라우저 창에서 조작하면 여기에 쌓입니다.
      </div>
    );
  }

  return (
    <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
      {steps.map((step, index) => (
        <li key={step.id}>
          {showPauseMarker && index === currentIndex && <PauseMarker />}
          <div
            onClick={() => onSelect?.(step.id)}
            style={{
              display: "grid",
              gridTemplateColumns: "34px 1fr auto",
              gap: 10,
              alignItems: "start",
              padding: "10px 12px",
              borderBottom: "1px solid var(--border)",
              background:
                index === runningIndex
                  ? "var(--warn-tint)"
                  : step.id === selectedStepId
                    ? "var(--surface-soft)"
                    : "transparent",
              cursor: onSelect ? "pointer" : "default",
            }}
          >
            <span className="mono dim">{String(index + 1).padStart(2, "0")}</span>
            <div>
              <div style={{ fontWeight: 500 }}>{step.label}</div>
              <div className="row" style={{ gap: 6, marginTop: 4, flexWrap: "wrap" }}>
                <StepTypeBadge type={step.type} />
                <TabBadge tab={step.tab} />
                {step.author === "ai" && <AuthorBadge author={step.author} />}
                <code className="dim">{locatorSummary(step)}</code>
                {stepValue(step) !== null && (
                  <code className="mono" style={{ color: "var(--ai-dark)" }}>
                    {stepValue(step)}
                  </code>
                )}
              </div>
            </div>
            <div className="row" style={{ gap: 6 }}>
              {index === runningIndex && (
                <span className="badge warn" aria-label="실행 중">
                  실행 중
                </span>
              )}
              {outcomes[step.id] !== undefined && (
                <span className={`badge ${outcomes[step.id]}`}>
                  {outcomes[step.id] === "pass" ? "PASS" : "FAIL"}
                </span>
              )}
              {durationsMs[step.id] !== undefined && (
                <span className="mono dim">{durationsMs[step.id]} ms</span>
              )}
              {onDelete && (
                <button
                  className="ghost"
                  aria-label={`${step.label} 삭제`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(step.id);
                  }}
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        </li>
      ))}
      {showPauseMarker && currentIndex >= steps.length && <PauseMarker />}
    </ol>
  );
}

/** FR-034 — 일시정지 위치를 시각적으로 구분한다. */
function PauseMarker() {
  return (
    <div
      className="row"
      style={{
        gap: 8,
        padding: "8px 12px",
        background: "var(--warn-tint)",
        borderTop: "2px solid var(--warn)",
        borderBottom: "2px solid var(--warn)",
      }}
    >
      <strong className="mono">PAUSE</strong>
      <span className="spacer" />
      <span className="muted">여기서 고친 뒤 이어서 실행합니다</span>
    </div>
  );
}
