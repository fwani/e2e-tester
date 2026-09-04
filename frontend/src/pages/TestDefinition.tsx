/**
 * 저장된 테스트 정의 보기 (T169). FR-016·FR-019.
 *
 * **실행하지 않고 볼 수 있어야 한다.** 이 화면이 생기기 전에는 Step 목록과 후보를 보려면
 * 재실행 세션을 시작해야 했다 — 브라우저를 띄우고 대상 앱에 접속해야 Step 하나를 확인할
 * 수 있었다는 뜻이다.
 *
 * **"다시 집기"(FR-020)는 여기에 없다.** 그것은 살아 있는 브라우저에서 요소를 지목하는
 * 조작이므로 일시정지 세션에만 있다. 회색 버튼으로 두지 않고 아예 두지 않는다 — 회색
 * 버튼은 "곧 될 것" 처럼 읽힌다.
 *
 * 표시하는 것은 **저장된 그대로**다 (FR-016). 후보 상태는 기록 시점 검증 결과이며,
 * 표시 상태는 그 값에서 파생된다 (FR-019a) — 저장된 값이 아니다.
 */
import { useEffect, useState } from "react";

import { ApiError, tests } from "../api/client";
import { LocatorPriorityTable } from "../components/LocatorPriorityTable";
import { AuthoringBadge, AuthorBadge, StepTypeBadge, TabBadge } from "../components/Badges";
import type { Step } from "../types/generated/step";
import type { Test } from "../types/generated/step-dsl";

export interface TestDefinitionProps {
  testId: string;
  /** 결과 화면에서 실패한 Step 을 지목해 들어온 경우 (FR-056). */
  focusStepId?: string | null;
  onBack: () => void;
  onRun?: (testId: string) => void;
}

function valueOf(step: Step): string | null {
  if (step.type === "fill" || step.type === "select") return step.value;
  if (step.type === "navigate") return step.url;
  return null;
}

/** 민감 값은 참조로만 저장된다 (FR-082). 참조는 그대로 보여도 안전하다. */
function isReference(value: string): boolean {
  return /^\{\{[A-Z][A-Z0-9_]*\}\}$/.test(value);
}

export function TestDefinition({
  testId,
  focusStepId = null,
  onBack,
  onRun,
}: TestDefinitionProps) {
  const [test, setTest] = useState<Test | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(focusStepId);

  useEffect(() => {
    void tests
      .get(testId)
      .then((t) => {
        setTest(t);
        setError(null);
      })
      .catch((exc: unknown) =>
        setError(exc instanceof ApiError ? exc.message : String(exc)),
      );
  }, [testId]);

  useEffect(() => setSelected(focusStepId), [focusStepId]);

  if (error !== null) {
    return (
      <main style={{ maxWidth: 900, margin: "32px auto", padding: "0 16px" }}>
        <p role="alert" style={{ color: "var(--fail-dark)", whiteSpace: "pre-wrap" }}>
          {error}
        </p>
        <button className="secondary" onClick={onBack}>
          목록으로
        </button>
      </main>
    );
  }

  if (test === null) {
    return (
      <main style={{ padding: 32 }} className="muted">
        불러오는 중…
      </main>
    );
  }

  const steps = test.steps as unknown as Step[];
  const current = steps.find((s) => s.id === selected) ?? null;
  const sensitive = (test.variables ?? []).filter((v) => v.sensitive);

  return (
    <main style={{ maxWidth: 1080, margin: "24px auto", padding: "0 16px" }}>
      <div className="row" style={{ gap: 10 }}>
        <div>
          <div className="dim mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
            TEST DEFINITION
          </div>
          <h1 style={{ fontFamily: "var(--font-display)", fontSize: 24, margin: 0 }}>
            {test.name}
          </h1>
        </div>
        <span className="mono dim">{test.id}</span>
        <AuthoringBadge mode={test.authoring_mode as "record" | "ai"} />
        <span className="spacer" />
        {onRun && (
          <button className="secondary" onClick={() => onRun(test.id)}>
            ▶ 실행
          </button>
        )}
        <button className="secondary" onClick={onBack}>
          목록으로
        </button>
      </div>

      <p className="muted" style={{ fontSize: 12.5 }}>
        시작 주소 <span className="mono">{test.start_url}</span> · Step {steps.length}개
        {sensitive.length > 0 && (
          <>
            {" "}
            · 민감 변수{" "}
            <span className="mono">{sensitive.map((v) => v.name).join(", ")}</span>{" "}
            (값은 표시되지 않습니다)
          </>
        )}
      </p>

      {test.ai_instruction && (
        <div className="card" style={{ background: "var(--ai-tint)", borderColor: "var(--ai)" }}>
          <strong style={{ fontSize: 12 }}>작성 의도 (지시문)</strong>
          <p style={{ margin: "4px 0 0", fontSize: 13, whiteSpace: "pre-wrap" }}>
            {test.ai_instruction}
          </p>
          <p className="dim" style={{ margin: "6px 0 0", fontSize: 11.5 }}>
            이 문장은 기록일 뿐 실행 대상이 아닙니다. 다시 돌릴 때는 아래 Step 만
            실행합니다.
          </p>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: current === null ? "1fr" : "1fr 420px",
          gap: 16,
          marginTop: 16,
          alignItems: "start",
        }}
      >
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {steps.map((step, index) => (
            <button
              key={step.id}
              onClick={() => setSelected(step.id === selected ? null : step.id)}
              className="row"
              style={{
                width: "100%",
                gap: 10,
                padding: "10px 14px",
                borderTop: index === 0 ? "none" : "2px solid var(--border)",
                background:
                  step.id === selected ? "var(--surface)" : "var(--paper)",
                textAlign: "left",
                border: "none",
                boxShadow: "none",
                cursor: "pointer",
              }}
            >
              <span className="mono dim" style={{ width: 28 }}>
                {String(index + 1).padStart(2, "0")}
              </span>
              <StepTypeBadge type={step.type} />
              <span className="spacer">{step.label}</span>
              {valueOf(step) !== null && (
                <span className="mono dim" style={{ fontSize: 11.5 }}>
                  {isReference(valueOf(step) as string)
                    ? valueOf(step)
                    : `"${valueOf(step)}"`}
                </span>
              )}
              <TabBadge tab={step.tab} />
              <AuthorBadge author={step.author} />
            </button>
          ))}
        </div>

        {current !== null && (
          <div className="card">
            <div className="row" style={{ gap: 8 }}>
              <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
                {current.id.toUpperCase()} · {current.type.toUpperCase()}
              </strong>
              <span className="spacer" />
              <button className="ghost" onClick={() => setSelected(null)}>
                닫기
              </button>
            </div>

            <p className="muted" style={{ fontSize: 12, margin: "6px 0" }}>
              대기 시간 {current.timeout_ms}ms · 탭 {current.tab}
            </p>

            {"target" in current && (
              <LocatorPriorityTable
                target={current.target}
                title={current.type === "drag" ? "끄는 대상" : "대상 요소"}
              />
            )}
            {current.type === "drag" && (
              <div style={{ marginTop: 12 }}>
                <LocatorPriorityTable target={current.drop_target} title="놓는 위치" />
              </div>
            )}
            {current.type === "assertion" && current.assertion.target && (
              <LocatorPriorityTable target={current.assertion.target} title="검증 대상" />
            )}

            <p className="dim" style={{ fontSize: 11.5, marginTop: 10 }}>
              대상을 다시 지정하려면(다시 집기) 살아 있는 브라우저가 필요합니다. 실행을
              시작해 일시정지한 뒤 Step 상세에서 하세요 (FR-020).
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
