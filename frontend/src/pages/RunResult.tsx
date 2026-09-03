/**
 * 실행 결과 (T089). `RunResult.dc.html` 이식.
 *
 * FR-050~FR-058: 요약 3항목(총 시간·통과/전체·멈춘 Step), Step 결과 목록, 실패 상세
 * (시도한 후보를 우선순위 순으로 + 대기 시간 상한), 산출물 탭, 재실행 두 갈래.
 *
 * `TRACE` 탭은 **비활성**이다. 실행 추적은 MVP 범위에 없고, 서버도 `501` 을 돌려준다
 * (spec 디자인 차이 1). 탭을 숨기지 않고 비활성으로 두는 이유는, 디자인에 있는 기능이
 * 조용히 사라지면 사용자가 자기가 잘못 본 줄 알기 때문이다.
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, tests, type ArtifactKind } from "../api/client";
import { AppHeader } from "../components/AppHeader";
import type { LocatorAttempt, RunResult as RunResultData, StepResult } from "../types/generated/run-result";

const ARTIFACT_TABS: { kind: ArtifactKind; label: string }[] = [
  { kind: "screenshot", label: "SCREENSHOT" },
  { kind: "trace", label: "TRACE" },
  { kind: "console", label: "CONSOLE" },
  { kind: "network", label: "NETWORK" },
];

export interface RunResultProps {
  testId: string;
  testName?: string;
  /** 처음부터 다시 실행 (FR-055). */
  onRunAll: (testId: string) => void;
  /** 실패한 Step 부터 다시 실행 (FR-055). */
  onRunFrom: (testId: string, stepIndex: number) => void;
  /** 실패한 Step 상세로 이동 (FR-056). */
  onEditStep?: (testId: string, stepId: string) => void;
  onBack: () => void;
}

export function RunResult({
  testId,
  testName,
  onRunAll,
  onRunFrom,
  onEditStep,
  onBack,
}: RunResultProps) {
  const [result, setResult] = useState<RunResultData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<ArtifactKind>("screenshot");
  const [artifactPath, setArtifactPath] = useState<string | null>(null);
  const [artifactError, setArtifactError] = useState<string | null>(null);

  useEffect(() => {
    void tests
      .result(testId)
      .then(setResult)
      .catch((exc: unknown) =>
        setError(exc instanceof ApiError ? exc.message : String(exc)),
      );
  }, [testId]);

  const loadArtifact = useCallback(
    (kind: ArtifactKind) => {
      setTab(kind);
      setArtifactPath(null);
      setArtifactError(null);
      if (kind === "trace") return; // 비활성 탭은 요청하지 않는다
      void tests
        .artifact(testId, kind)
        .then((a) => setArtifactPath(a.path))
        .catch((exc: unknown) =>
          setArtifactError(exc instanceof ApiError ? exc.message : String(exc)),
        );
    },
    [testId],
  );

  useEffect(() => {
    if (result !== null) loadArtifact("screenshot");
  }, [result, loadArtifact]);

  if (error !== null) {
    return (
      <ResultShell testId={testId} testName={testName} onBack={onBack}>
        <div className="card" style={{ color: "var(--fail-dark)" }}>
          {error}
        </div>
      </ResultShell>
    );
  }

  if (result === null) {
    return (
      <ResultShell testId={testId} testName={testName} onBack={onBack}>
        <p className="muted" style={{ padding: 24 }}>
          결과를 불러오는 중…
        </p>
      </ResultShell>
    );
  }

  const failedIndex = result.failed_step_index;
  const failedStep =
    failedIndex !== null
      ? (result.steps.find((s) => s.index === failedIndex) ?? null)
      : null;

  return (
    <ResultShell
      testId={testId}
      testName={testName}
      onBack={onBack}
      browser={result.browser}
      outcome={result.outcome}
      actions={
        <>
          {failedIndex !== null && (
            <button onClick={() => onRunFrom(testId, failedIndex)}>
              실패한 Step부터 실행
            </button>
          )}
          <button className="secondary" onClick={() => onRunAll(testId)}>
            처음부터 실행
          </button>
        </>
      }
    >
      {result.session_lost && (
        <div
          style={{
            padding: "10px 16px",
            background: "var(--warn-tint)",
            borderBottom: "1px solid var(--warn)",
          }}
        >
          ⚠ 브라우저 세션이 유실되어 실행이 중단됐습니다. 그때까지의 Step 결과만 남아
          있습니다. 이어서 실행은 할 수 없고, 처음부터 다시 실행해야 합니다.
        </div>
      )}

      <Summary result={result} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
          gap: 0,
          flex: 1,
          minHeight: 0,
        }}
      >
        <section
          style={{
            borderRight: "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          <SectionTitle>STEP 결과</SectionTitle>
          <div style={{ flex: 1, overflowY: "auto" }}>
            <StepResultList steps={result.steps} failedIndex={failedIndex} />
          </div>
        </section>

        <section style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          {failedStep !== null && (
            <FailureDetail
              step={failedStep}
              onEdit={
                onEditStep ? () => onEditStep(testId, failedStep.step_id) : undefined
              }
            />
          )}

          <SectionTitle>산출물</SectionTitle>
          <div
            className="row"
            style={{ gap: 4, padding: "6px 12px", borderBottom: "1px solid var(--border)" }}
          >
            {ARTIFACT_TABS.map(({ kind, label }) => {
              const unsupported = kind === "trace";
              return (
                <button
                  key={kind}
                  className={tab === kind && !unsupported ? "" : "secondary"}
                  disabled={unsupported}
                  aria-disabled={unsupported ? "true" : undefined}
                  title={
                    unsupported
                      ? "실행 추적은 이번 범위에 없습니다."
                      : undefined
                  }
                  onClick={() => loadArtifact(kind)}
                >
                  <span className="mono" style={{ fontSize: 11 }}>
                    {label}
                  </span>
                </button>
              );
            })}
          </div>

          <div style={{ flex: 1, overflow: "auto", padding: 12, minHeight: 0 }}>
            <ArtifactPane
              kind={tab}
              path={artifactPath}
              error={artifactError}
            />
          </div>
        </section>
      </div>
    </ResultShell>
  );
}

// ─── 조각들 ─────────────────────────────────────────────────────────────────

function ResultShell({
  testId,
  testName,
  browser,
  outcome,
  actions,
  onBack,
  children,
}: {
  testId: string;
  testName?: string;
  browser?: string;
  outcome?: "pass" | "fail";
  actions?: React.ReactNode;
  onBack: () => void;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <AppHeader
        breadcrumb={
          <>
            테스트 / {testId} / 실행 결과
          </>
        }
        status={browser !== undefined ? <span className="dim mono">{browser}</span> : null}
      />
      <div
        className="row"
        style={{ gap: 12, padding: "8px 16px", borderBottom: "1px solid var(--border)" }}
      >
        <button className="ghost" onClick={onBack}>
          ← 목록
        </button>
        <strong>{testName ?? testId}</strong>
        {outcome !== undefined && (
          <span className={`badge ${outcome}`}>
            {outcome === "pass" ? "PASS" : "FAIL"}
          </span>
        )}
        <span className="spacer" />
        {actions}
      </div>
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="row"
      style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)" }}
    >
      <strong className="mono" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
        {children}
      </strong>
    </div>
  );
}

/** FR-050 — 총 소요 시간, 통과/전체, 멈춘 Step 번호. */
function Summary({ result }: { result: RunResultData }) {
  const stopped =
    result.failed_step_index !== null
      ? String(result.failed_step_index + 1).padStart(2, "0")
      : "—";
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <SummaryCell label="총 시간" value={`${(result.total_ms / 1000).toFixed(2)} s`} />
      <SummaryCell
        label="통과 / 전체"
        value={`${result.passed_count} / ${result.total_count}`}
      />
      <SummaryCell label="멈춘 STEP" value={stopped} />
    </div>
  );
}

function SummaryCell({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: "12px 16px", borderRight: "1px solid var(--border)" }}>
      <div className="mono dim" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
        {label}
      </div>
      <div style={{ fontSize: 20, fontWeight: 500, marginTop: 2 }}>{value}</div>
    </div>
  );
}

/** FR-051 — Step별 결과와 소요 시간. */
function StepResultList({
  steps,
  failedIndex,
}: {
  steps: StepResult[];
  failedIndex: number | null;
}) {
  return (
    <ol style={{ listStyle: "none", margin: 0, padding: 0 }}>
      {steps.map((step) => (
        <li
          key={step.step_id}
          style={{
            display: "grid",
            gridTemplateColumns: "34px 1fr auto",
            gap: 10,
            alignItems: "center",
            padding: "10px 12px",
            borderBottom: "1px solid var(--border)",
            background:
              step.index === failedIndex ? "var(--fail-tint)" : "transparent",
          }}
        >
          <span className="mono dim">{String(step.index + 1).padStart(2, "0")}</span>
          <div>
            <div style={{ fontWeight: 500 }}>{step.label}</div>
            <div className="row" style={{ gap: 6, marginTop: 2, flexWrap: "wrap" }}>
              <StepOutcomeBadge outcome={step.outcome} />
              {step.tab > 0 && <span className="badge warn mono">탭 {step.tab}</span>}
              {step.resolved_candidate !== null && (
                <code className="dim">{step.resolved_candidate}</code>
              )}
              {step.tab_wait_ms > 0 && (
                <span className="dim mono">탭 대기 {step.tab_wait_ms} ms</span>
              )}
            </div>
            {step.candidate_disagreement.map((note) => (
              <div key={note} className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                ⚠ {note}
              </div>
            ))}
          </div>
          <span className="mono dim">
            {step.outcome === "not_run" || step.outcome === "skipped"
              ? "—"
              : `${step.duration_ms} ms`}
          </span>
        </li>
      ))}
    </ol>
  );
}

function StepOutcomeBadge({ outcome }: { outcome: StepResult["outcome"] }) {
  const label: Record<StepResult["outcome"], string> = {
    pass: "PASS",
    fail: "FAIL",
    skipped: "건너뜀",
    not_run: "미실행",
  };
  const tone = outcome === "pass" ? "pass" : outcome === "fail" ? "fail" : "";
  return <span className={`badge ${tone}`}>{label[outcome]}</span>;
}

/** FR-054·FR-021·FR-056 — 실패 이유, 시도한 후보, 고치기로 이동. */
function FailureDetail({
  step,
  onEdit,
}: {
  step: StepResult;
  onEdit?: () => void;
}) {
  return (
    <div style={{ borderBottom: "1px solid var(--border)" }}>
      <div
        className="row"
        style={{ gap: 8, padding: "10px 14px", background: "var(--fail-tint)" }}
      >
        <strong className="mono">
          STEP {String(step.index + 1).padStart(2, "0")} 실패
        </strong>
        <span className="spacer" />
        {onEdit && (
          <button className="secondary" onClick={onEdit}>
            Step {String(step.index + 1).padStart(2, "0")} 고치기
          </button>
        )}
      </div>

      <p style={{ padding: "10px 14px", margin: 0, whiteSpace: "pre-wrap" }}>
        {step.error_message ?? "실패 이유가 기록되지 않았습니다."}
      </p>

      {step.locator_attempts.length > 0 && (
        <div style={{ padding: "0 14px 12px" }}>
          <div className="mono dim" style={{ fontSize: 11, letterSpacing: "0.08em" }}>
            시도한 LOCATOR (우선순위 순)
          </div>
          <ul style={{ listStyle: "none", margin: "6px 0 0", padding: 0 }}>
            {step.locator_attempts.map((attempt, order) => (
              <AttemptRow
                key={`${attempt.candidate}-${order}`}
                attempt={attempt}
              />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AttemptRow({ attempt }: { attempt: LocatorAttempt }) {
  return (
    <li className="row" style={{ gap: 8, padding: "3px 0", flexWrap: "wrap" }}>
      <span
        aria-label={attempt.matched ? "매칭됨" : "매칭 실패"}
        style={{ color: attempt.matched ? "var(--pass)" : "var(--fail)" }}
      >
        {attempt.matched ? "✓" : "×"}
      </span>
      <code className="mono">{attempt.expression}</code>
      {attempt.match_count > 1 && (
        <span className="badge warn mono">{attempt.match_count}개 매칭</span>
      )}
      {attempt.waited_ms > 0 && (
        <span className="dim mono">timeout {attempt.waited_ms} ms</span>
      )}
    </li>
  );
}

/** FR-052·FR-053 — 산출물 표시. `trace` 는 비활성이다. */
function ArtifactPane({
  kind,
  path,
  error,
}: {
  kind: ArtifactKind;
  path: string | null;
  error: string | null;
}) {
  if (kind === "trace") {
    return (
      <p className="muted">
        실행 추적(Trace)은 이번 범위에 없습니다. 실패 원인은 스크린샷·콘솔·네트워크 기록으로
        확인하세요.
      </p>
    );
  }
  if (error !== null) {
    return <p className="muted">{error}</p>;
  }
  if (path === null) {
    return <p className="muted">불러오는 중…</p>;
  }
  return (
    <div>
      <p className="dim" style={{ fontSize: 12, marginTop: 0 }}>
        프로젝트 디렉터리 기준 경로입니다. 파일을 직접 열어 확인할 수 있습니다.
      </p>
      <code className="mono" style={{ wordBreak: "break-all" }}>
        {path}
      </code>
    </div>
  );
}
