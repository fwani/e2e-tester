/**
 * 실행 결과. **`docs/design/RunResult.dc.html`(1440×900) 전사.** DC-001~DC-008.
 *
 * 확정 디자인은 FAIL 상태를 보여준다. PASS 는 정의돼 있지 않아 같은 구조에 색만
 * 바꿔 그린다 — `undefined-states.md` 에 기록했다 (DC-009).
 *
 * FR-050~FR-058: 총 시간·통과/전체·멈춘 Step·Step별 결과와 소요 시간·실패 이유·
 * 시도한 locator 후보·스크린샷/콘솔/네트워크 산출물·브라우저 종류.
 *
 * `TRACE` 탭은 확정 디자인에 있지만 서버가 `501` 을 돌려준다(001 의 알려진 차이).
 * 확정 디자인에 있는 것을 빼지 않으려고 그리되(DC-007), 비활성으로 둔다.
 */
import { useCallback, useEffect, useState } from "react";
import { ErrorNotice, describeError, localError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import { tests, type ArtifactKind } from "../api/client";
import type { RunResult as RunResultData, StepResult } from "../types/generated/run-result";
import { stepLabel, stepNumber } from "../lib/wording";

import {
  Artboard,
  BrandMark,
  Breadcrumb,
  HeaderBar,
  HeaderDivider,
  StatusPill,
} from "../components/design/Chrome";

const INK = "#14130F";
const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

/** 확정 디자인의 산출물 탭. 순서와 문구를 그대로 옮겼다. */
const TABS: { kind: ArtifactKind; label: string }[] = [
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
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [tab, setTab] = useState<ArtifactKind>("screenshot");
  /** 스크린샷은 주소(`src`), 로그는 본문(`text`). 경로를 그리지 않는다 (UX U-03). */
  const [artifact, setArtifact] = useState<{ src?: string; text?: string } | null>(null);
  const [artifactError, setArtifactError] = useState<ErrorInfo | null>(null);

  useEffect(() => {
    void tests
      .result(testId)
      .then(setResult)
      .catch((exc: unknown) => setError(describeError(exc)));
  }, [testId]);

  const loadArtifact = useCallback(
    (kind: ArtifactKind) => {
      setTab(kind);
      setArtifact(null);
      setArtifactError(null);
      if (kind === "trace") return; // 비활성 탭은 요청하지 않는다
      if (kind === "screenshot") {
        // 이미지는 브라우저가 직접 받는다. 실패는 <img onError> 가 잡는다.
        setArtifact({ src: tests.artifactUrl(testId, kind) });
        return;
      }
      void tests
        .artifactText(testId, kind)
        .then((text) => setArtifact({ text }))
        .catch((exc: unknown) =>
          setArtifactError(describeError(exc)),
        );
    },
    [testId],
  );

  useEffect(() => {
    if (result !== null) loadArtifact("screenshot");
  }, [result, loadArtifact]);

  const failedIndex = result?.failed_step_index ?? null;
  const failedStep =
    failedIndex !== null ? (result?.steps.find((s) => s.index === failedIndex) ?? null) : null;
  const failed = result?.outcome === "fail";

  return (
    <Artboard width={1440} height={900}>
      <HeaderBar>
        <BrandMark />
        <HeaderDivider />
        <Breadcrumb testId={testId} />
        <div style={{ flex: "1" }} />
        <button className="ghost" onClick={onBack}>
          목록으로
        </button>
        {result !== null && (
          <StatusPill
            background={failed ? "#D9502F" : "#2E9455"}
            color="#FFFDF6"
          >
            {failed ? "FAIL" : "PASS"}
          </StatusPill>
        )}
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
          {testName ?? testId}
        </div>
        {result !== null && (
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: "30px",
              padding: "0 11px",
              background: failed ? "#D9502F" : "#2E9455",
              color: "#FFFDF6",
              border: "3px solid #14130F",
              font: `700 13px/1 ${MONO}`,
              letterSpacing: "0.06em",
            }}
          >
            {failed ? "FAIL" : "PASS"}
          </div>
        )}
        <div style={{ flex: "1" }} />
        {failedIndex !== null && (
          <button
            onClick={() => onRunFrom(testId, failedIndex)}
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
              font: `600 15px/1 ${SANS}`,
            }}
          >
            <svg width="15" height="15" viewBox="0 0 16 16">
              <path d="M4 2l10 6-10 6z" fill="currentColor" />
            </svg>
            실패한 Step부터 실행
          </button>
        )}
        <button
          onClick={() => onRunAll(testId)}
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
            font: `600 15px/1 ${SANS}`,
          }}
        >
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.3">
            <path d="M13.5 8a5.5 5.5 0 1 1-1.8-4.1M13.5 1.4V5h-3.6" />
          </svg>
          처음부터 실행
        </button>
      </div>

      {error !== null && (
        <div
          role="alert"
          style={{
            borderBottom: "3px solid #14130F",
            background: "#FBEEEA",
            color: "#A83A22",
            padding: "12px 24px",
          }}
        >
          <ErrorNotice error={error} />
        </div>
      )}

      {result?.session_lost === true && (
        <div
          role="status"
          style={{ borderBottom: "3px solid #14130F", background: "#FFF9D6", padding: "12px 24px" }}
        >
          브라우저 세션이 유실된 상태로 끝났습니다. 이어서 실행할 수 없으니 처음부터 다시 실행해야 합니다.
        </div>
      )}

      <div style={{ flex: "1", minHeight: "0", display: "flex" }}>
        <div
          style={{
            flex: "1",
            minWidth: "0",
            padding: "22px 24px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            overflowY: "auto",
          }}
        >
          {result === null && error === null && (
            <p style={{ color: "#9A968A" }}>결과를 불러오는 중…</p>
          )}

          {result !== null && (
            <>
              {/* 요약 3칸 (FR-050) */}
              <div style={{ display: "flex", gap: "0", border: "3px solid #14130F", background: "#FFFDF6" }}>
                <Summary label="총 시간" value={`${(result.total_ms / 1000).toFixed(2)} s`} />
                <div style={{ width: "3px", background: INK }} />
                <Summary label="통과 / 전체" value={`${result.passed_count} / ${result.total_count}`} />
                <div style={{ width: "3px", background: INK }} />
                <Summary
                  label="멈춘 STEP"
                  value={stepNumber(failedIndex)}
                />
              </div>

              {/* Step 결과 (FR-051) */}
              <div style={{ border: "3px solid #14130F", background: "#FFFDF6" }}>
                <div
                  style={{
                    height: "40px",
                    display: "flex",
                    alignItems: "center",
                    padding: "0 16px",
                    background: "#14130F",
                    color: "#EFEBE0",
                    font: `600 12px/1 ${MONO}`,
                    letterSpacing: "0.12em",
                  }}
                >
                  STEP 결과
                </div>
                {result.steps.map((step) => (
                  <StepRow
                    key={step.step_id}
                    step={step}
                    onOpen={onEditStep ? () => onEditStep(testId, step.step_id) : undefined}
                  />
                ))}
              </div>

              {/* 실패 상세 (FR-054·FR-021) */}
              {failedStep !== null && (
                <div
                  style={{
                    border: "3px solid #D9502F",
                    background: "#FFFDF6",
                    boxShadow: "6px 6px 0 #14130F",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <div
                    style={{
                      height: "40px",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      padding: "0 16px",
                      background: "#D9502F",
                      color: "#FFFDF6",
                      font: `700 12px/1 ${MONO}`,
                      letterSpacing: "0.12em",
                    }}
                  >
                    {stepLabel(failedStep.index)} 실패
                  </div>
                  <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "14px" }}>
                    <div style={{ font: `600 17px/1.4 ${SANS}`, textWrap: "pretty" }}>
                      {failedStep.error_message ?? "실패 이유가 기록되지 않았습니다."}
                    </div>

                    {/* 004 FR-122·FR-123 — **`code` 로 분기한다.** 문구를 파싱하지
                        않는다. 문구는 다듬을 수 있어야 하고, 다듬는 순간 분류가 깨지면
                        안 된다. */}
                    {failureAdvice(failedStep.error_code) && (
                      <div
                        style={{
                          padding: "10px 12px",
                          background: "#FFF9D6",
                          border: "2px solid #14130F",
                          font: `500 13px/1.5 ${SANS}`,
                          textWrap: "pretty",
                        }}
                      >
                        {failureAdvice(failedStep.error_code)}
                      </div>
                    )}

                    {failedStep.locator_attempts.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                        <div
                          style={{
                            font: `600 11px/1 ${MONO}`,
                            letterSpacing: "0.12em",
                            color: "#6B675C",
                          }}
                        >
                          시도한 LOCATOR (우선순위 순)
                        </div>
                        {failedStep.locator_attempts.map((a) => (
                          <div
                            key={`${a.candidate}-${a.expression}`}
                            style={{ display: "flex", alignItems: "center", gap: "10px", font: `400 13px/1 ${MONO}` }}
                          >
                            <span style={{ color: a.matched ? "#2E9455" : "#A83A22", fontWeight: "700" }}>
                              {a.matched ? "✓" : "×"}
                            </span>
                            {a.expression}
                          </div>
                        ))}
                        <div style={{ font: `400 12px/1 ${MONO}`, color: "#6B675C", paddingLeft: "20px" }}>
                          {/* 004 FR-121 — **실제로 기다린 시간**이다. 예전에는 후보별
                              대기 중 최댓값을 "timeout" 으로 적었는데, 그것은 설정값도
                              실측값도 아닌 값이었다. */}
                          {`요소를 ${failedStep.element_wait_ms} ms 기다렸습니다`}
                        </div>
                      </div>
                    )}

                    {onEditStep && (
                      <button className="secondary" onClick={() => onEditStep(testId, failedStep.step_id)}>
                        {`${stepLabel(failedStep.index)} 고치기`}
                      </button>
                    )}
                  </div>
                </div>
              )}

              <div style={{ font: `400 13px/1 ${MONO}`, color: "#6B675C" }}>
                {result.browser}
              </div>
            </>
          )}
        </div>

        {/* 오른쪽 640px — 산출물 (FR-052·FR-053) */}
        <div
          style={{
            flex: "0 0 640px",
            borderLeft: "3px solid #14130F",
            background: "#FFFDF6",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ flex: "0 0 52px", display: "flex", borderBottom: "3px solid #14130F" }}>
            {TABS.map((t, i) => {
              const active = tab === t.kind;
              return (
                <button
                  key={t.kind}
                  disabled={t.kind === "trace"}
                  onClick={() => loadArtifact(t.kind)}
                  style={{
                    flex: "1",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    height: "100%",
                    background: active ? "#14130F" : "transparent",
                    color: active ? "#EFEBE0" : "#6B675C",
                    border: "none",
                    borderLeft: i === 0 ? "none" : "3px solid #14130F",
                    font: `600 13px/1 ${MONO}`,
                    letterSpacing: "0.06em",
                    boxShadow: "none",
                    padding: 0,
                  }}
                >
                  {t.label}
                </button>
              );
            })}
          </div>

          <div style={{ flex: "1", minHeight: "0", padding: "20px", display: "flex" }}>
            <div
              style={{
                flex: "1",
                minWidth: "0",
                border: "3px solid #14130F",
                background: "#FFFFFF",
                display: "flex",
                flexDirection: "column",
                overflow: "auto",
              }}
            >
              {tab === "trace" ? (
                // 확정 디자인에 있으므로 그리되, 서버가 501 을 돌려준다 (001 의 차이).
                <p style={{ padding: 20, color: "#6B675C" }}>
                  트레이스는 이 버전에서 제공하지 않습니다.
                </p>
              ) : artifactError !== null ? (
                <div style={{ padding: 20 }}>
                  <ErrorNotice error={artifactError} compact />
                </div>
              ) : artifact === null ? (
                <p style={{ padding: 20, color: "#9A968A" }}>불러오는 중…</p>
              ) : tab === "screenshot" ? (
                <img
                  src={artifact.src}
                  alt={`${stepLabel(failedIndex)} 실패 시점`}
                  style={{ width: "100%", height: "auto", display: "block" }}
                  onError={() =>
                    // 깨진 이미지 아이콘을 남기지 않는다 — 무엇이 없는지 말한다.
                    setArtifactError(
                      localError(
                        "실패 시점 스크린샷 파일을 불러올 수 없습니다.",
                        "실행 산출물(.runs/)이 지워졌을 수 있습니다. 다시 실행하면 새로 남습니다.",
                      ),
                    )
                  }
                />
              ) : (
                <pre
                  data-artifact-text
                  style={{ margin: 0, padding: 16, font: `400 12px/1.6 ${MONO}`, whiteSpace: "pre-wrap" }}
                >
                  {artifact.text === "" ? "(기록이 비어 있습니다)" : artifact.text}
                </pre>
              )}
            </div>
          </div>

          {failedIndex !== null && tab === "screenshot" && (
            <div
              style={{
                borderTop: "3px solid #14130F",
                background: "#EFEBE0",
                padding: "12px 20px",
                font: `400 13px/1 ${MONO}`,
                color: "#6B675C",
              }}
            >
              {stepLabel(failedIndex)} 실패 시점
            </div>
          )}
        </div>
      </div>
    </Artboard>
  );
}

/**
 * 실패 분류별 다음 행동 (004 FR-122·FR-123).
 *
 * **`code` 로만 판단한다.** 문구를 읽어 분기하면 문구를 다듬는 순간 분류가 깨진다.
 * 서버의 `next_action` 과 같은 내용을 말하되, 결과 화면은 "이 Step 을 고치기" 버튼을
 * 바로 옆에 두고 있으므로 그 맥락에 맞춰 다시 쓴다.
 */
function failureAdvice(code: StepResult["error_code"]): string | null {
  switch (code) {
    case "ELEMENT_NOT_READY":
      return (
        "기다렸지만 요소가 나타나지 않았습니다. 대상 화면이 느릴 수 있습니다 — " +
        "실행 속도를 '느림'으로 낮춰 화면을 눈으로 확인하거나, 아래에서 이 Step 의 " +
        "대기 시간을 늘린 뒤 이 Step부터 다시 실행하세요."
      );
    case "ELEMENT_AMBIGUOUS":
      return (
        "이 식별 정보가 더 이상 요소 하나를 가리키지 않습니다. 기다려도 달라지지 " +
        "않으므로 아래에서 대상을 다시 집으세요."
      );
    case "TARGET_UNREACHABLE":
      return "대상 사이트가 응답하지 않았습니다. 사이트를 확인한 뒤 다시 실행하세요.";
    default:
      // STEP_FAILED 와 미기록(옛 결과)은 기존 실패 사유 문장으로 충분하다.
      return null;
  }
}

function Summary({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ flex: "1", padding: "12px 16px", display: "flex", flexDirection: "column", gap: "5px" }}>
      <div style={{ font: `600 11px/1 ${MONO}`, letterSpacing: "0.12em", color: "#6B675C" }}>{label}</div>
      <div style={{ font: `700 20px/1 ${MONO}` }}>{value}</div>
    </div>
  );
}

function StepRow({ step, onOpen }: { step: StepResult; onOpen?: () => void }) {
  const failed = step.outcome === "fail";
  const skipped = step.outcome === "skipped" || step.outcome === "not_run";

  return (
    <div
      onClick={onOpen}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "14px",
        height: "54px",
        padding: "0 16px",
        borderTop: "2px solid #DCD8CC",
        cursor: onOpen ? "pointer" : "default",
        ...(failed ? { background: "#FBEEEA" } : {}),
        ...(skipped ? { opacity: 0.55 } : {}),
      }}
    >
      <div
        style={{
          width: "22px",
          height: "22px",
          background: failed ? "#D9502F" : skipped ? "transparent" : "#2E9455",
          border: skipped ? "2px solid #9A968A" : "none",
          color: "#FFFDF6",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {!skipped && (
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.8">
            <path d={failed ? "M4 4l8 8M12 4l-8 8" : "M3 8.5l3.5 3.5L13 4.5"} />
          </svg>
        )}
      </div>
      <div style={{ width: "30px", font: `700 14px/1 ${MONO}`, color: "#9A968A" }}>
        {stepNumber(step.index)}
      </div>
      <div style={{ flex: "1", minWidth: "0", font: `600 16px/1.3 ${SANS}` }}>{step.label}</div>
      <div style={{ width: "90px", textAlign: "right", font: `400 14px/1 ${MONO}`, color: "#6B675C" }}>
        {skipped ? "—" : `${step.duration_ms} ms`}
      </div>
    </div>
  );
}
