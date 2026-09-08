/**
 * 결과 국면의 **어댑터** (007 T047~T051 · FR-217·FR-244).
 *
 * 007 이전에는 `RunResult.tsx` 가 자기만의 껍데기·Step 목록·상세를 갖고 있었다. 그래서
 * 같은 정보가 다른 국면과 정반대 자리에 있었다 — 결말 표식이 세션 화면은 행의 **오른쪽
 * 끝**, 결과 화면은 행의 **왼쪽 첫 칸**이었다 (S-02). 대상 앱 영역은 아예 없고 산출물이
 * 본문 오른쪽 별도 영역이었다 (S-11).
 *
 * ## 두 곳을 읽어 한 행을 만든다 (research R3)
 *
 * **결과 스냅샷에는 Step DSL 이 없다.** `StepResult` 는 `label`·`outcome`·`duration_ms`
 * 만 갖고 동작 종류·대상·값을 갖지 않는다. 통합 Step 행은 그것들을 보여 주므로 현재
 * 정의를 함께 읽어 `step_id` 로 맞춘다.
 *
 * 맞지 않는 행이 생기면 **그 사이에 정의가 바뀐 것**이다. 그 행은 동작 종류·대상 요약·
 * 값 칸이 비고 다른 칸이 그 자리로 당겨지지 않으며 (FR-223), 화면이 그 사실을 알린다
 * (FR-254 A5) — 지금은 알 방법조차 없다.
 *
 * **정의를 읽지 못하면 어긋남을 주장하지 않는다.** 모르는 것과 바뀐 것은 다르다.
 */
import { useCallback, useEffect, useState } from "react";

import { definition, tests, type ArtifactKind, type DefinitionView } from "../api/client";
import type { RunResultView as RunResultData } from "../api/client";
import { ErrorNotice, describeError, localError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";
import { ActionButton } from "../components/workbench/ActionButton";
import { ActionPalette } from "../components/workbench/ActionPalette";
import { Workbench } from "../components/workbench/Workbench";
import type {
  Notice,
  WorkAreaView,
  StepOutcome,
  TargetView,
  WorkbenchModel,
  WorkbenchStep,
} from "../components/workbench/model";
import type { ActionId } from "../lib/actions";
import { capabilitiesFor, type CapabilityFacts } from "../lib/capabilities";
import {
  ACTION_LABEL,
  PHASE_LABEL,
  outcomeTone,
  partialRunDiagnosis,
  partialRunNotice,
  resultDefinitionDrift,
  runFromStepLabel,
  runSummary,
  stepLabel,
} from "../lib/wording";
import type { Step } from "../types/generated/step";
import type { ErrorCode, StepResult } from "../types/generated/run-result";

const MONO = "'IBM Plex Mono', ui-monospace, monospace";
const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

/** 산출물 종류. `trace` 는 서버가 501 을 돌려준다 (001 의 알려진 차이 · DC-007). */
const SUPPORTED_ARTIFACTS: ArtifactKind[] = ["screenshot", "console", "network"];

export interface ResultViewProps {
  testId: string;
  /** 결과 국면으로 들어올 때 지목한 Step (007 FR-239 · S-10). */
  focusStepId?: string | null;
  /** 처음부터 다시 실행 (FR-055). */
  onRunAll: (testId: string) => void;
  /** 지목한 Step 부터 다시 실행 (FR-055). */
  onRunFrom: (testId: string, stepIndex: number) => void;
  /** 그 Step 을 편집 국면에서 연다 (FR-056). */
  onEditStep?: (testId: string, stepId: string) => void;
  onBack: () => void;
  /** 실행 요청이 진행 중인가 (005 FR-127·FR-129). 덮어쓰기 O1 의 근거다. */
  runPending?: boolean;
}

export function ResultView({
  testId,
  focusStepId = null,
  onRunAll,
  onRunFrom,
  onEditStep,
  onBack,
  runPending = false,
}: ResultViewProps) {
  const [result, setResult] = useState<RunResultData | null>(null);
  const [defn, setDefn] = useState<DefinitionView | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [tab, setTab] = useState<ArtifactKind>("screenshot");
  /** 스크린샷은 주소(`src`), 로그는 본문(`text`). 경로를 그리지 않는다 (UX U-03). */
  const [artifact, setArtifact] = useState<{ src?: string; text?: string } | null>(null);
  const [artifactError, setArtifactError] = useState<ErrorInfo | null>(null);
  const [focused, setFocused] = useState<string | null>(focusStepId);
  const [detailOpen, setDetailOpen] = useState(focusStepId !== null);

  // 007 FR-239 — 지목해 들어왔으면 그 Step 을 **펼쳐서** 준다. 다시 찾게 하지 않는다.
  useEffect(() => {
    setFocused(focusStepId);
    setDetailOpen(focusStepId !== null);
  }, [focusStepId]);

  useEffect(() => {
    void tests
      .result(testId)
      .then(setResult)
      .catch((exc: unknown) => setError(describeError(exc)));
    /*
      정의는 **보조 입력**이다. 읽지 못해도 결과는 보여야 한다 — 결과를 보러 온
      사용자에게 정의 조회 실패로 빈 화면을 주는 것은 이 화면이 존재하는 이유를 지운다.
    */
    void definition
      .get(testId)
      // **형태를 보고 받는다.** 보조 입력이므로 실패해도 결과는 보여야 하고, 형태가
      // 다른 응답을 그대로 담으면 결과 화면 전체가 그것 하나 때문에 죽는다.
      .then((v) => setDefn(isDefinitionView(v) ? v : null))
      .catch(() => setDefn(null));
  }, [testId]);

  const loadArtifact = useCallback(
    (kind: ArtifactKind, hasFailure: boolean) => {
      setTab(kind);
      setArtifact(null);
      setArtifactError(null);
      if (kind === "trace") return; // 지원되지 않는 종류는 요청하지 않는다
      if (kind === "screenshot") {
        /*
          005 FR-173 (재점검 N-03) — **없는 것을 없다고 말한다.**

          스크린샷은 실패 시점에만 남는다. 통과한 실행에는 파일이 없는 것이 정상인데,
          그래도 요청하면 `<img onError>` 가 「산출물이 지워졌을 수 있습니다」를 띄운다 —
          아무 문제 없는 실행을 보러 온 사용자에게 하는 거짓말이다.
        */
        if (!hasFailure) {
          setArtifact({ text: "" });
          return;
        }
        setArtifact({ src: tests.artifactUrl(testId, kind) });
        return;
      }
      void tests
        .artifactText(testId, kind)
        .then((text) => setArtifact({ text }))
        .catch((exc: unknown) => setArtifactError(describeError(exc)));
    },
    [testId],
  );

  const failedIndex = result?.failed_step_index ?? null;

  useEffect(() => {
    if (result !== null) loadArtifact("screenshot", failedIndex !== null);
  }, [result, failedIndex, loadArtifact]);

  /*
    아직 결말을 모른다. 모르는 채로 조작을 내주면 사용자는 존재하지 않는 실패 지점부터
    실행을 걸 수 있다 (005 U-11 이 그 구간이었다).

    **오류는 `ErrorNotice` 가 그린다.** 문구만 옮겨 적으면 분류(`code`·`category`)와
    다음 행동이 화면에 닿지 않는다 — 003 EC-004 가 그것이고, 실브라우저 계층(AS-028)이
    삭제된 테스트의 결과를 열 때 그 형태를 요구한다.
  */
  if (result === null) {
    return (
      <main style={{ padding: 32 }}>
        {error !== null ? (
          <ErrorNotice error={error} />
        ) : (
          <p style={{ color: "#6E757F" }}>결과를 불러오는 중…</p>
        )}
      </main>
    );
  }

  /* ─── 결과 행 × 정의 (research R3) ────────────────────────────────────────── */

  const byId = new Map<string, Step>((defn?.test.steps ?? []).map((s) => [s.id, s]));
  const steps: WorkbenchStep[] = result.steps.map((r) => ({
    id: r.step_id,
    index: r.index,
    // 정의를 못 읽었으면 `null` 이다 — 칸을 비우되 다른 칸을 당기지 않는다 (FR-223).
    step: byId.get(r.step_id) ?? null,
    label: r.label,
    outcome: r.outcome as StepOutcome,
    durationMs: r.outcome === "skipped" || r.outcome === "not_run" ? null : r.duration_ms,
    isPausedHere: false,
  }));
  /** 정의를 실제로 읽었을 때만 어긋남을 센다. 모르는 것과 바뀐 것은 다르다. */
  const unmatched = defn === null ? 0 : steps.filter((s) => s.step === null).length;

  const failedStep: StepResult | null =
    failedIndex !== null ? (result.steps.find((s) => s.index === failedIndex) ?? null) : null;
  const focusedIndex = steps.findIndex((s) => s.id === focused);
  /** `run.from`·`nav.editStep` 이 가리키는 Step — 지목한 것, 없으면 실패한 것. */
  const targetIndex = focusedIndex >= 0 ? focusedIndex : failedIndex;

  const facts: CapabilityFacts = {
    runPending,
    hasSteps: steps.length > 0,
    // C5 — 이 테스트를 막고 있는 세션. 결과 조회만으로는 알 수 없으므로 정의가 말해 준다.
    blockingSession: defn?.blocking_session_id != null,
    resultViewable: true,
    hasResult: true,
  };
  const capabilities = capabilitiesFor("result", facts);

  /* ─── 좌측 — 산출물이 미러와 **같은 자리**를 쓴다 (T049 · FR-244 · S-11) ──── */

  const target: TargetView =
    tab === "trace"
      ? { kind: "empty", reason: "not_supported" }
      : {
          kind: "artifacts",
          selected: tab,
          available: SUPPORTED_ARTIFACTS,
          body: artifactBody({ tab, artifact, artifactError, failedIndex, onImageError: () =>
            setArtifactError(
              localError(
                "실패 시점 스크린샷 파일을 불러올 수 없습니다.",
                "실행 산출물(.runs/)이 지워졌을 수 있습니다. 다시 실행하면 새로 남습니다.",
              ),
            ),
          }),
        };

  /*
    ③-b 국면 작업 영역 — 왜 멈췄나 (FR-231·FR-262).

    **시도한 locator 를 여기서 싣지 않는다.** `failedStep.locator_attempts` 에 이미
    있고 `WorkArea` 가 그것을 그린다. 2회차가 고친 것은 그 표가 놓이는 **자리의
    크기**다 (`layout.ts` 의 `result.workArea = fixed 424`).
  */

  const work: WorkAreaView | null =
    failedStep !== null
      ? {
          kind: "failure_detail",
          step: failedStep,
          /*
            004 FR-122·FR-123 — 진단은 **`code` 로 분기한다.** 문구를 파싱하지 않는다.
            005 FR-153 — 부분 실행이면 건너뛴 선행 상태를 먼저 말한다. 그것이 원인일 때
            "속도를 낮추세요" 라고 하면 사용자를 헛돌게 한다 (U-02 관찰 4).
          */
          diagnosis:
            (result.scope === "partial" ? partialRunDiagnosis(result.start_index) : null) ??
            failureAdvice(failedStep.error_code),
        }
      : null;

  /* ─── 알림 ────────────────────────────────────────────────────────────────── */

  const notices: Notice[] = [];
  if (error !== null) {
    notices.push({
      id: "error",
      tone: "error",
      role: "alert",
      message: error.message,
      nextAction: error.nextAction || null,
      action: null,
      dismissible: false,
    });
  }
  // T048 · FR-254 A5 — 이 결과 이후 정의가 바뀌었다.
  if (unmatched > 0) {
    notices.push({
      id: "definition-drift",
      tone: "warn",
      role: "status",
      message: resultDefinitionDrift(unmatched),
      nextAction: null,
      action: null,
      dismissible: false,
    });
  }
  if (result.session_lost) {
    notices.push({
      id: "session-lost",
      tone: "warn",
      role: "status",
      message: "브라우저 세션이 유실된 상태로 끝났습니다.",
      nextAction: "이어서 실행할 수 없으니 처음부터 다시 실행해야 합니다.",
      action: null,
      dismissible: false,
    });
  }
  // 005 FR-152 (U-02) — 이전 전체 실행 결과를 지우지 않는다. 보조로 함께 둔다.
  if (result.last_full_run != null) {
    const f = result.last_full_run;
    notices.push({
      id: "last-full-run",
      tone: "info",
      role: "note",
      message: `최근 전체 실행: ${runSummary({
        outcome: f.outcome,
        passedCount: f.passed_count,
        attemptedCount: f.attempted_count,
        totalCount: f.total_count,
        totalMs: f.total_ms,
        scope: f.scope,
        startIndex: f.start_index,
        failedStepIndex: f.failed_step_index,
        stoppedStepIndex: f.stopped_step_index,
      })}`,
      nextAction: null,
      action: null,
      dismissible: false,
    });
  }
  /*
    005 FR-150 — 부분 실행을 걸기 **전에** 건너뛰는 구간과 선행 상태를 알린다.
    모달로 막지 않는다 — 보조 문구로 충분하다.
  */
  const partialNotice = targetIndex !== null ? partialRunNotice(targetIndex) : null;
  if (partialNotice !== null) {
    notices.push({
      id: "partial-run",
      tone: "info",
      role: "note",
      message: partialNotice,
      nextAction: null,
      action: null,
      dismissible: false,
    });
  }
  if (artifactError !== null) {
    notices.push({
      id: "artifact-error",
      tone: "warn",
      role: "status",
      message: artifactError.message,
      nextAction: artifactError.nextAction || null,
      action: null,
      dismissible: false,
    });
  }

  /* ─── 조작 ────────────────────────────────────────────────────────────────── */

  function runAction(action: ActionId) {
    switch (action) {
      case "run.all":
        onRunAll(testId);
        break;
      case "run.from":
        if (targetIndex !== null) onRunFrom(testId, targetIndex);
        break;
      case "nav.editStep": {
        const stepId = targetIndex !== null ? steps[targetIndex]?.id : undefined;
        if (stepId !== undefined) onEditStep?.(testId, stepId);
        break;
      }
      case "nav.back":
        onBack();
        break;
      default:
        break;
    }
  }

  /** 지목한 Step 이 있어야 뜻이 있는 조작. 표는 국면을, 이것은 화면이 아는 사실을 본다. */
  const needsTarget = (id: ActionId) =>
    targetIndex === null && capabilities[id].kind === "enabled"
      ? ({
          kind: "disabled",
          reason: "먼저 Step 을 고르세요",
          remedy: { action: "step.select" as ActionId },
        } as const)
      : capabilities[id];

  const phaseActions = (
    <>
      <ActionButton
        action="session.open"
        capability={capabilities["session.open"]}
        compact
        onRemedy={runAction}
      />
      <ActionButton
        action="run.all"
        capability={capabilities["run.all"]}
        onRun={() => runAction("run.all")}
        onRemedy={runAction}
      />
      <ActionButton
        action="run.from"
        capability={needsTarget("run.from")}
        label={runFromStepLabel(targetIndex ?? 0)}
        emphasis={failedIndex !== null}
        onRun={() => runAction("run.from")}
        onRemedy={runAction}
      />
    </>
  );

  const headerActions = (
    <>
      <ActionButton
        action="nav.editStep"
        capability={needsTarget("nav.editStep")}
        label={targetIndex !== null ? `${stepLabel(targetIndex)} 고치기` : ACTION_LABEL["nav.editStep"]}
        compact
        onRun={() => runAction("nav.editStep")}
        onRemedy={runAction}
      />
      <ActionButton
        action="nav.back"
        capability={capabilities["nav.back"]}
        compact
        onRun={() => runAction("nav.back")}
        onRemedy={runAction}
      />
    </>
  );

  const focusedResult =
    focusedIndex >= 0 ? (result.steps[focusedIndex] ?? null) : null;
  const focusedDsl = focusedResult !== null ? (byId.get(focusedResult.step_id) ?? null) : null;

  const model: WorkbenchModel = {
    phase: "result",
    testId,
    testName: defn?.test.name ?? testId,
    phaseBar: {
      phaseLabel: PHASE_LABEL.result,
      phaseTone: outcomeTone(result.outcome),
      /*
        **결말 요약은 이 자리 하나뿐이다** (FR-218d · 005 FR-140 · U-19). 총 시간 ·
        통과/전체 · 멈춘 Step 이 이 한 문장에 다 들어 있다 (FR-050) — 이전에는 같은
        사실이 요약 바와 3칸 패널에 나뉘어 두 번 있었다.
      */
      runSummary: runSummary({
        outcome: result.outcome,
        passedCount: result.passed_count,
        attemptedCount: result.attempted_count,
        totalCount: result.total_count,
        totalMs: result.total_ms,
        scope: result.scope,
        startIndex: result.start_index,
        failedStepIndex: result.failed_step_index,
        stoppedStepIndex: result.stopped_step_index,
      }),
      // FR-058 — 어느 브라우저로 돌았는가.
      progressLabel: result.browser,
    },
    target,
    work,
    steps,
    focusedStepId: focused,
    detail:
      detailOpen && focusedResult !== null
        ? {
            step: focusedDsl,
            index: focusedResult.index,
            // 결과 국면의 축은 **그때 무엇을 시도했는가** 다 (FR-229).
            attempts: focusedResult.locator_attempts,
            candidates: focusedDsl !== null && "target" in focusedDsl ? focusedDsl.target : null,
            dropCandidates:
              focusedDsl !== null && focusedDsl.type === "drag" ? focusedDsl.drop_target : null,
            repickWaiting: null,
            failure:
              focusedResult.outcome === "fail"
                ? { code: focusedResult.error_code, message: focusedResult.error_message }
                : null,
          }
        : null,
    capabilities,
    notices,
    authoring: defn?.test.authoring_mode === "ai" ? "ai" : "record",
    pacing: null,
  };

  return (
    <Workbench
      model={model}
      phaseActions={phaseActions}
      headerActions={headerActions}
      stepEmptyNotice="이 실행에는 Step 이 없습니다."
      /*
        **끝난 실행에서 할 수 없는 것들도 같은 자리에 남는다** (FR-234·FR-238).
        전부 「이 Step 고치기」로 가는 길을 달고 있으므로, 감추는 것보다 이쪽이
        사용자를 덜 막는다 — 감추면 "여기서는 원래 안 되는 일" 로 읽힌다.
      */
      stepFooter={
        <ActionPalette
          capabilities={capabilities}
          onRun={runAction}
          onRemedy={runAction}
          nl={{ value: "", onChange: () => undefined, onSubmit: () => undefined }}
          name={defn?.test.name ?? testId}
          onNameChange={() => undefined}
          startUrl={defn?.test.start_url ?? ""}
          onStartUrlChange={() => undefined}
          instruction={defn?.test.ai_instruction ?? null}
          saveLabel="저장"
          stepCount={steps.length}
        />
      }
      onSelectStep={(stepId) => {
        setFocused(stepId);
        setDetailOpen(true);
      }}
      onCloseDetail={() => setDetailOpen(false)}
      onSelectArtifact={(kind) => loadArtifact(kind, failedIndex !== null)}
      onAction={runAction}
    />
  );
}

/**
 * 정의 조회 응답이 쓸 수 있는 형태인가.
 *
 * 결과 국면에서 정의는 **보조 입력**이다 (research R3). 없어도 결말·소요 시간은
 * 보여야 하므로, 형태가 다르면 조용히 없는 것으로 다룬다 — 담아 두었다가 렌더에서
 * 터지면 결과를 보러 온 사용자가 빈 화면을 받는다.
 */
function isDefinitionView(value: unknown): value is DefinitionView {
  const v = value as DefinitionView | undefined;
  return v != null && v.test != null && Array.isArray(v.test.steps);
}

/** 산출물 본문. 종류마다 그리는 방법이 다르고 자리는 같다. */
function artifactBody({
  tab,
  artifact,
  artifactError,
  failedIndex,
  onImageError,
}: {
  tab: ArtifactKind;
  artifact: { src?: string; text?: string } | null;
  artifactError: ErrorInfo | null;
  failedIndex: number | null;
  onImageError: () => void;
}) {
  if (artifactError !== null) {
    return (
      <p style={{ font: `400 13px/1.6 ${SANS}`, color: "#A32C13" }}>{artifactError.message}</p>
    );
  }
  if (artifact === null) return <p style={{ color: "#6E757F" }}>불러오는 중…</p>;
  if (tab === "screenshot" && artifact.src !== undefined) {
    return (
      <img
        src={artifact.src}
        alt={`${stepLabel(failedIndex)} 실패 시점`}
        style={{ width: "100%", height: "auto", display: "block" }}
        // 깨진 이미지 아이콘을 남기지 않는다 — 무엇이 없는지 말한다.
        onError={onImageError}
      />
    );
  }
  return (
    <pre
      data-artifact-text
      style={{ margin: 0, font: `400 12px/1.6 ${MONO}`, whiteSpace: "pre-wrap" }}
    >
      {artifact.text === "" || artifact.text === undefined
        ? emptyArtifactMessage(tab)
        : artifact.text}
    </pre>
  );
}

/**
 * 실패 분류별 다음 행동 (004 FR-122·FR-123).
 *
 * **`code` 로만 판단한다.** 문구를 읽어 분기하면 문구를 다듬는 순간 분류가 깨진다.
 */
function failureAdvice(code: ErrorCode | null): string | null {
  switch (code) {
    case "ELEMENT_NOT_READY":
      return (
        "기다렸지만 요소가 나타나지 않았습니다. 대상 화면이 느릴 수 있습니다 — " +
        "실행 속도를 '느림'으로 낮춰 화면을 눈으로 확인하거나, 이 Step 의 대기 시간을 " +
        "늘린 뒤 이 Step부터 다시 실행하세요."
      );
    case "ELEMENT_AMBIGUOUS":
      return (
        "이 식별 정보가 더 이상 요소 하나를 가리키지 않습니다. 기다려도 달라지지 " +
        "않으므로 대상을 다시 집으세요."
      );
    case "TARGET_UNREACHABLE":
      return "대상 사이트가 응답하지 않았습니다. 사이트를 확인한 뒤 다시 실행하세요.";
    default:
      // STEP_FAILED 와 미기록(옛 결과)은 기존 실패 사유 문장으로 충분하다.
      return null;
  }
}

/**
 * 기록이 없는 증거의 문구 (005 FR-173 · U-22).
 *
 * 리포트는 `CONSOLE`·`NETWORK` 가 큰 빈 상자에 "(기록 없음)" 한 줄만 두는 것을 봤다.
 * 사용자는 그것이 "수집을 안 했다" 인지 "수집했는데 비었다" 인지 알 수 없다.
 */
function emptyArtifactMessage(kind: ArtifactKind): string {
  switch (kind) {
    case "console":
      return "콘솔 오류가 없었습니다.\n\n실행 중 대상 페이지가 남긴 콘솔 메시지를 모읍니다.";
    case "network":
      return "실패한 네트워크 요청이 없었습니다.\n\n실행 중 실패한 요청(4xx·5xx·차단)을 모읍니다.";
    case "trace":
      return "이 실행에는 trace 가 남지 않았습니다 (MVP 미지원).";
    case "screenshot":
      return "실패 시점 스크린샷이 없습니다.\n\n실패한 실행에서만 수집합니다.";
  }
}
