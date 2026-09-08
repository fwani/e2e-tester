/**
 * 세션 국면의 **어댑터**. 다섯 국면(녹화·AI 작성·사람이 직접 조작·실행 중·일시정지)이
 * 하나의 `Workbench` 껍데기를 쓴다 (007 T032~T046 · FR-217).
 *
 * ## 무엇이 바뀌었나
 *
 * 007 이전에는 이 파일이 확정 디자인 4종에 대응하는 **페이지 컴포넌트 넷** 중 하나를
 * 골랐다 (`Runner`·`RunnerPaused`·`Takeover`·`AiRecord`). 넷은 Step 목록을 각자 그렸고,
 * 같은 정보가 국면에 따라 정반대 자리에 있었다 (S-02·S-05·S-08). 사용자가 제기한
 * "다 따로 만드니까 사용성이 떨어진다" 의 코드 상 형태가 그것이다.
 *
 * 지금은 **국면을 `WorkbenchModel` 로 바꾸는 일만** 한다. 그리는 것은 `Workbench` 하나다.
 *
 * ## 소유와 표시를 나눈다 (research R2)
 *
 *   `SessionScreen`   — 구독·상태·명령을 **소유**한다. 001 의 얽힘이 여기서 끝난다
 *   `SessionWorkbench` — 받은 사실로 `WorkbenchModel` 을 만들어 그린다. 부수효과가 없다
 *
 * 표시 컴포넌트를 따로 내보내는 이유는 검사 때문이다. 실시간 통로와 미러를 흉내 내지
 * 않고 국면별 화면을 그대로 그려 볼 수 있어야 한다 — 옛 페이지 컴포넌트들이 그랬듯이.
 *
 * **AI 세션 판정은 `authoring_mode` 로 한다** — `view.state` 가 아니다 (DR-020). 판정은
 * `lib/phase.ts` 가 소유한다.
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { describeError, fromEvent, localError } from "../components/ErrorNotice";
import type { ErrorInfo } from "../components/ErrorNotice";

import {
  sessions,
  type AddAssertionBody,
  type AiChoice,
  type RepickSlot,
  type RunPacing,
  type SessionView,
  type TabsResponse,
} from "../api/client";
import {
  subscribeSessionEvents,
  type SessionEvent,
  type SessionSubscription,
} from "../api/ws";
import { AssertionForm } from "../components/AssertionForm";
import { LiveConnectionBanner } from "../components/LiveConnectionBanner";
import { MirrorView, type MirrorPhase } from "../components/MirrorView";
import { PacingControl } from "../components/PacingControl";
import { TabStrip } from "../components/TabStrip";
import { BrowserFrame } from "../components/design/BrowserFrame";
import { ActionButton } from "../components/workbench/ActionButton";
import { ActionPalette } from "../components/workbench/ActionPalette";
import { Workbench } from "../components/workbench/Workbench";
import type {
  AiBlockedState,
  Notice,
  WorkAreaView,
  StepOutcome,
  WorkbenchModel,
  WorkbenchStep,
} from "../components/workbench/model";
import type { ActionId } from "../lib/actions";
import {
  capabilitiesFor,
  type CapabilityFacts,
  type CapabilityState,
} from "../lib/capabilities";
import { hasLiveBrowser, isFinished, phaseOfSession, type Phase } from "../lib/phase";
import {
  ACTION_LABEL,
  DISABLED_REASON,
  FINISHED_WHILE_PAUSING_TITLE,
  PHASE_LABEL,
  editSavedNotice,
  pausedAfterLabel,
  progressLabel as progressText,
  sessionPhaseLabel,
  runFromStepLabel,
  runSummary,
  sessionSaveLabel,
  sessionTitle,
  skipFailureNotice,
  stepLabel,
  stepNumber,
  stopLabel,
  type OutcomeTone,
} from "../lib/wording";
import type { Step } from "../types/generated/step";
import type { Outcome, StepOutcome as RunStepOutcome } from "../types/generated/run-result";

export type { AiBlockedState } from "../components/workbench/model";

/**
 * 끊김을 알리기까지 기다리는 시간. 재연결이 700ms 마다 일어나므로 짧은 끊김은
 * 배너가 깜빡이기만 하고 정보를 주지 않는다.
 */
const OFFLINE_NOTICE_DELAY_MS = 1500;

const SANS = "'IBM Plex Sans KR', system-ui, sans-serif";

const MANIPULATION_STATES = new Set(["recording", "takeover_recording"]);
/** 세션이 살아 있지 않은 상태. `review` 는 여기 없다 — 편집·저장을 받는다 (DR-010). */
const TERMINAL_STATES = new Set(["completed", "failed", "stopped", "lost"]);
/** 중지 후 검토 상태. 브라우저는 없지만 Step 은 살아 있다 (contracts §6). */
const REVIEW_STATE = "review";
/** 브라우저는 없지만 기록은 살아 있는 상태 (DR-015). */
const SAVEABLE_WITHOUT_BROWSER = new Set([REVIEW_STATE, "lost"]);
/** 브라우저가 없어 **탭을 물을 대상이 없는** 상태 (005 FR-135 · 재점검 U-03-b). */
const TABLESS_STATES = new Set([...TERMINAL_STATES, REVIEW_STATE]);

interface StepProgress {
  outcome?: RunStepOutcome;
  durationMs?: number;
}

/** 국면 띠의 색 역할. **색은 보조이며 라벨이 항상 함께 있다** (005 FR-141). */
const PHASE_TONE: Record<Phase, OutcomeTone> = {
  /** 만들기는 아직 아무 결말도 없다 — 중립이다 */
  composing: "neutral",
  recording: "danger",
  ai_authoring: "neutral",
  takeover: "warn",
  running: "neutral",
  paused: "warn",
  result: "neutral",
  editing: "neutral",
};

// ─────────────────────────────────────────────────────────────────────────────
// 표시 — `SessionWorkbench`
// ─────────────────────────────────────────────────────────────────────────────

export interface SessionWorkbenchProps {
  view: SessionView;
  /** AI 세션이면 사용자가 준 지시문 원문. 화면에만 쓴다 (FR-063). */
  aiInstruction?: string | null;
  aiMessages?: string[];
  /** **세션 상태와 무관하게** 그린다 (FR-218f · FR-253 · 001 R2). */
  aiError?: ErrorInfo | null;
  aiBlocked?: AiBlockedState | null;

  /** 끝난 실행의 결말 요약. `runSummary()` 가 만든 문장이다 (005 FR-140). */
  summary?: string | null;
  /** 실패한 Step 의 인덱스와 사유. 실행이 끝난 화면이 이유를 말하는 근거다. */
  failure?: { index: number; message: string } | null;

  outcomeOf: (step: Step, index: number) => StepOutcome;
  durationOf: (step: Step) => number | undefined;

  busy?: boolean;
  /** 일시정지 전이 중 (005 FR-142~FR-145). */
  pausing?: boolean;
  stopRequested?: boolean;
  /** 실행 요청이 진행 중 (005 FR-127). */
  runPending?: boolean;
  /**
   * 사용자가 누르지 않았는데 국면이 바뀌었다 (007 T074 · FR-220).
   *
   * 실행이 끝나 결과를 보여 주게 되는 순간이 그것이다. 화면이 말없이 바뀌면 사용자는
   * 자기가 무엇을 눌렀는지 되짚게 되고, 보던 Step 을 다시 찾는다.
   */
  autoTransition?: string | null;
  pacingSaved?: boolean;

  error?: ErrorInfo | null;
  notice?: ErrorInfo | null;
  notes?: string[];
  lost?: string | null;
  offline?: boolean;

  mirror: ReactNode;
  tabs?: ReactNode;
  currentUrl?: string;
  mirroredTab?: number;

  focusedStepId?: string | null;
  /** Step 상세 겹침이 열려 있는가. 지목과 상세 열기는 다른 조작이다 (FR-227·FR-230). */
  detailOpen?: boolean;
  repickWaiting?: RepickSlot | null;
  reordering?: boolean;
  saveName?: string;

  onSelectStep: (stepId: string) => void;
  onOpenDetail?: (stepId: string) => void;
  onCloseDetail?: () => void;
  onSaveStep?: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    sensitive?: boolean;
  }) => void;
  onRepick?: (slot: RepickSlot) => void;
  onSaveNameChange?: (name: string) => void;
  onSave?: () => void;
  onShowList?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onResumeSkippingFailure?: () => void;
  onStop?: () => void;
  onRecordStart?: () => void;
  onRecordStop?: () => void;
  onAddAssertion?: (body: AddAssertionBody) => void;
  onNaturalLanguage?: (instruction: string) => void;
  onDeleteStep?: (stepId: string) => void;
  onToggleReorder?: () => void;
  onApplyReorder?: (order: string[]) => void;
  onRunFromHere?: (stepIndex: number) => void;
  onRerunAll?: () => void;
  onRerunFrom?: (stepIndex: number) => void;
  onShowResult?: () => void;
  onChooseBlocked?: (choice: string) => void;
  onPacingChange?: (next: RunPacing) => void;
  onReconnect?: () => void;
  onDismissNotice?: (id: string) => void;
}

export function SessionWorkbench(props: SessionWorkbenchProps) {
  /*
    검증 추가 폼이 열려 있는가.

    **여는 버튼은 Step 패널 바닥에, 펼쳐지는 폼은 국면 보조 영역에** 있다 (T036).
    폼은 가로 공간이 필요하고 조작은 Step 곁에 있어야 하므로 자리가 다르며, 그래서
    상태를 둘의 공통 조상인 여기서 갖는다.
  */
  const [assertOpen, setAssertOpen] = useState(false);
  /** 자연어 Step 입력. 팔레트가 아니라 어댑터가 갖는다 — 보내는 것은 어댑터다. */
  const [nl, setNl] = useState("");
  const {
    view,
    aiInstruction = null,
    aiMessages = [],
    aiError = null,
    aiBlocked = null,
    summary = null,
    failure = null,
    outcomeOf,
    durationOf,
    busy = false,
    pausing = false,
    stopRequested = false,
    runPending = false,
    autoTransition = null,
    pacingSaved = true,
    error = null,
    notice = null,
    notes = [],
    lost = null,
    offline = false,
    mirror,
    tabs,
    currentUrl = "",
    mirroredTab = 0,
    focusedStepId = null,
    detailOpen = false,
    repickWaiting = null,
    reordering = false,
    saveName = "",
    onSelectStep,
    onOpenDetail,
    onCloseDetail,
    onSaveStep,
    onRepick,
    onSaveNameChange,
    onSave,
    onShowList,
    onPause,
    onResume,
    onResumeSkippingFailure,
    onStop,
    onRecordStart,
    onRecordStop,
    onAddAssertion,
    onNaturalLanguage,
    onDeleteStep,
    onToggleReorder,
    onApplyReorder,
    onRunFromHere,
    onRerunAll,
    onRerunFrom,
    onShowResult,
    onChooseBlocked,
    onPacingChange,
    onReconnect,
    onDismissNotice,
  } = props;

  const phase = phaseOfSession(view);
  const testId = view.test_id;
  const title = testId ?? "새 테스트";
  const isDone = TERMINAL_STATES.has(view.state);
  const review = SAVEABLE_WITHOUT_BROWSER.has(view.state);
  const manipulating = MANIPULATION_STATES.has(view.state);
  const finished = isFinished(view);
  const liveBrowser = hasLiveBrowser(view) && lost === null;
  /** 멈추기 전에 실행이 끝났다 (005 FR-146). 실행 결말과 세션 상태는 다른 축이다. */
  const finishedWhilePausing = view.state === "paused" && summary !== null;

  const steps: WorkbenchStep[] = view.steps.map((step, index) => ({
    id: step.id,
    index,
    step,
    label: step.label,
    outcome: outcomeOf(step, index),
    durationMs: durationOf(step) ?? null,
    isPausedHere: !review && phase === "paused" && index === view.current_step_index,
  }));

  const failedStepIndex = (() => {
    const at = steps.findIndex((s) => s.outcome === "fail");
    return at < 0 ? null : at;
  })();

  /**
   * 007 T091 걷기(W-1)가 잡은 것 — **이벤트를 놓친 화면도 결말을 말한다.**
   *
   * 결말 요약은 `run_finished` 이벤트로만 채워진다. 그래서 목록의 「실행 화면 보기」로
   * **이미 끝난 세션에 돌아오면** 화면이 「실행 종료」·「닫기」라고 말하면서 무엇이
   * 끝났는지는 말하지 못한다. 걷기에서 실제로 그 화면을 만났다.
   *
   * 005 FR-171 이 Step별 결과에서 이미 고친 것과 **같은 종류**다 — 실시간 이벤트에만
   * 사는 값은 그 이벤트를 못 받은 화면에서 없는 것이 된다. 세션 뷰가 아는 것으로
   * 되살린다: 상태가 결말을 말하고, `step_results` 가 개수를 말한다.
   *
   * **실시간 이벤트를 우선한다.** 뷰는 폴링 시점의 스냅샷이므로 방금 온 이벤트보다
   * 오래됐을 수 있고, 총 소요 시간처럼 뷰에 없는 값도 있다.
   */
  const restoredSummary = (() => {
    if (summary !== null) return summary;
    if (!finished || steps.length === 0) return null;
    const outcome: Outcome | null =
      view.state === "completed"
        ? "pass"
        : view.state === "failed" || view.state === "lost"
          ? "fail"
          : view.state === "stopped" || view.state === REVIEW_STATE
            ? "stopped"
            : null;
    if (outcome === null) return null;
    const attempted = steps.filter(
      (s) => s.outcome !== "pending" && s.outcome !== "not_run" && s.outcome !== "skipped",
    ).length;
    // 아무 Step 도 확정되지 않았으면 지어내지 않는다 — 모르는 것을 말하는 것이 더 나쁘다.
    if (attempted === 0) return null;
    return runSummary({
      outcome,
      passedCount: steps.filter((s) => s.outcome === "pass").length,
      attemptedCount: attempted,
      totalCount: steps.length,
      totalMs: null,
      scope: view.run_scope ?? null,
      startIndex: view.run_start_index ?? null,
      failedStepIndex,
      stoppedStepIndex: outcome === "stopped" ? view.current_step_index : null,
    });
  })();
  const selectedIndex = steps.findIndex((s) => s.id === focusedStepId);

  /*
    권한표에 넘기는 **사실**. 화면이 아는 것만 담는다 — 모르는 것은 `undefined` 로 두고
    표가 보수적으로 판정한다 (`capabilities.ts` 의 주석).
  */
  const facts: CapabilityFacts = {
    sessionFinished: finished,
    liveBrowser,
    hasFailedStep: failedStepIndex !== null,
    recording: view.state === "recording" || view.state === "takeover_recording",
    hasSteps: view.steps.length > 0,
    aiBlocked: aiBlocked !== null && aiBlocked.choices.length > 0,
    // 005 FR-133 — 판단 근거는 「세션이 끝났는가」가 아니라 **「볼 결과가 남았는가」**다.
    // 멈추기 전에 실행이 끝난 세션(`paused` + 요약)도 볼 결과를 가졌다 (FR-146).
    resultViewable: testId !== null && (finished || summary !== null),
    // 005 FR-144 — 전이 중에도 「중지」는 살린다. `busy` 를 그대로 넘기면 O2 가 그것까지
    // 잠그고, 사용자는 최대 10초 동안 기다리는 것 말고 할 일이 없어진다 (U-04).
    busy: busy && !pausing,
    pausing,
    stopRequested,
    runPending,
    sessionLost: lost !== null,
  };
  const capabilities = capabilitiesFor(phase, facts);

  /* ─── 층② 국면 띠 ─────────────────────────────────────────────────────── */

  const progressLabel = (() => {
    if (finishedWhilePausing) return FINISHED_WHILE_PAUSING_TITLE;
    if (pausing) {
      const budget = view.steps[view.current_step_index]?.timeout_ms ?? null;
      // 005 FR-142·FR-145 — 기다리는 이유와 남은 예산을 **즉시** 말한다.
      return (
        `현재 Step 이 끝나면 멈춥니다 · ${stepLabel(view.current_step_index)} 대기 중` +
        (budget ? ` (최대 ${Math.round(budget / 1000)}s)` : "")
      );
    }
    if (review) return `기록된 Step ${view.steps.length}개 · 브라우저 종료됨`;
    if (phase === "paused") return pausedAfterLabel(view.current_step_index);
    if (phase === "takeover") return "AI 실패 → 사람이 이어받음";
    // 005 FR-139 (U-14) — 끝난 실행에서는 진행 표시를 쓰지 않는다. 결말은 요약이 말한다.
    if (isDone) return null;
    if (phase === "running") return progressText(view.current_step_index, view.steps.length);
    return null;
  })();

  const phaseTone: OutcomeTone = (() => {
    if (view.state === "completed") return "success";
    if (view.state === "failed" || view.state === "lost") return "danger";
    if (view.state === "stopped" || view.state === REVIEW_STATE) return "neutral";
    return PHASE_TONE[phase];
  })();

  /* ─── 층③ 좌측 — 대상 앱 ────────────────────────────────────────────────── */

  const badge = (() => {
    if (finishedWhilePausing) return { label: "실행 종료", background: "#6B675C", color: "#FFFDF6" };
    if (pausing) return { label: "일시정지 중…", background: "#EDEAE0", color: "#14130F" };
    if (review) return { label: "SESSION ENDED", background: "#6B675C", color: "#FFFDF6" };
    if (phase === "takeover") {
      return view.state === "takeover_recording"
        ? { label: "HUMAN CONTROL", background: "#D9502F", color: "#FFFDF6" }
        : { label: "AI STOPPED", background: "#7C4DDB", color: "#FFFDF6" };
    }
    if (phase === "paused") {
      return view.pacing === "step"
        ? { label: "한 스텝씩 — 다음 Step 을 기다립니다", background: "#F5D000", color: "#14130F" }
        : { label: "PAUSED", background: "#F5D000", color: "#14130F" };
    }
    if (manipulating) return { label: "RECORDING", background: "#D9502F", color: "#FFFDF6" };
    return { label: "READ ONLY", background: "#6B675C", color: "#FFFDF6" };
  })();

  /* ─── 층③ 좌측 아래 — 국면 보조 영역 ────────────────────────────────────── */

  /**
   * 층③ 좌측 아래 국면 보조 영역 — **국면 고유 내용의 유일한 자리** (FR-218e).
   *
   * 조작 버튼은 여기 오지 않는다. 그것은 Step 패널 바닥에 있고 일곱 국면에서 같은
   * 자리다 (FR-235). 여기 오는 것은 국면이 **다른 국면과 공유하지 않는 내용** 뿐이다 —
   * AI 진행과 차단, 사람이 이어받았다는 사실, 그리고 펼쳐진 편집 폼.
   */
  const work: WorkAreaView | null = (() => {
    if (phase === "ai_authoring") {
      return {
        kind: "ai_progress",
        instruction: aiInstruction ?? "",
        messages: aiMessages,
        error: aiError,
        blocked: aiBlocked,
      };
    }
    if (phase === "takeover") {
      return {
        kind: "takeover_guide",
        recording: view.state === "takeover_recording",
        blocked: aiBlocked,
        error: aiError,
      };
    }
    // T036 — 검증 추가 폼과 순서 변경 패널. 닫혀 있으면 **자리를 차지하지 않는다**
    // (FR-218e) — 빈 영역이 남아 다른 영역의 자리를 바꾸지 않는다.
    if (assertOpen && capabilities["step.addAssertion"].kind === "enabled") {
      return {
        kind: "paused_tools",
        tools: (
          <AssertionForm
            busy={busy}
            tab={mirroredTab}
            onSubmit={(body) => {
              onAddAssertion?.(body);
              setAssertOpen(false);
            }}
            onCancel={() => setAssertOpen(false)}
          />
        ),
      };
    }
    if (reordering) {
      return {
        kind: "paused_tools",
        tools: (
          <ReorderPanel
            steps={steps.map((s2) => ({ id: s2.id, label: s2.label }))}
            busy={busy}
            onApply={(order) => onApplyReorder?.(order)}
            onCancel={() => onToggleReorder?.()}
          />
        ),
      };
    }
    return null;
  })();

  /* ─── 알림 ──────────────────────────────────────────────────────────────── */

  const notices: Notice[] = [];
  const push = (n: Notice) => notices.push(n);

  /*
    007 FR-220 (T074) — **사용자 조작 없이 국면이 바뀌면 무엇이 바뀌었는지 알린다.**

    화면이 하나가 되면서 생긴 새 위험이다. 화면이 통째로 갈리던 때는 전환이 그 자체로
    보였지만, 지금은 같은 껍데기 안에서 국면만 바뀐다 — 알리지 않으면 사용자는 자기가
    무엇을 눌렀는지 되짚는다. 보던 Step 과 스크롤은 그대로 둔다 (FR-239).
  */
  if (autoTransition !== null) {
    push({
      id: "auto-transition",
      tone: "info",
      role: "status",
      message: autoTransition,
      nextAction: "보고 있던 Step 은 그대로 있습니다.",
      action: null,
      dismissible: true,
    });
  }

  if (error !== null) {
    push({
      id: "error",
      tone: "error",
      role: "alert",
      message: error.message,
      nextAction: error.nextAction || null,
      action: null,
      dismissible: false,
    });
  }
  /*
    003 AP-032·DR-020 — **AI 실패 사유를 화면에 붙들어 둔다.**

    보조 영역이 이것을 그리는 국면(AI 작성·사람이 직접 조작)에서는 두 번 나오지 않게
    막는다. 그 밖의 국면에서는 여기가 유일한 자리다 — AI 가 실패하면 세션이 검토를 위해
    `paused` 로 옮겨가고, 그때 사유가 사라지던 것이 001 의 결함이었다.
  */
  if (aiError !== null && phase !== "ai_authoring" && phase !== "takeover") {
    push({
      id: "ai-error",
      tone: "error",
      role: "alert",
      message: aiError.message,
      nextAction: aiError.nextAction || null,
      action: null,
      dismissible: false,
    });
  }
  if (
    view.authoring_mode === "ai" &&
    phase !== "ai_authoring" &&
    aiInstruction !== null &&
    aiInstruction !== ""
  ) {
    // UX U-07 — AI 화면을 떠난 순간 무엇을 시켰는지가 사라지면, 실패 없이 다른 모드로
    // 갈아탄 것처럼 보인다.
    push({
      id: "ai-instruction",
      tone: "info",
      role: "note",
      message: `AI 지시문: ${aiInstruction}`,
      nextAction: null,
      action: null,
      dismissible: false,
    });
  }
  if (lost !== null) {
    push({
      id: "session-lost",
      tone: "error",
      role: "alert",
      message: lost,
      nextAction: `기록된 Step ${view.steps.length}개는 남아 있습니다. 저장한 뒤 처음부터 다시 실행하세요.`,
      action: { label: ACTION_LABEL["run.stop"], actionId: "run.stop" },
      dismissible: false,
    });
  }
  for (const w of view.recorder_warnings) {
    push({ id: `rec-${w}`, tone: "warn", role: "status", message: w, nextAction: null, action: null, dismissible: false });
  }
  for (const w of view.edit_warnings) {
    push({ id: `edit-${w}`, tone: "warn", role: "status", message: w, nextAction: null, action: null, dismissible: false });
  }
  if (notice !== null) {
    push({
      id: "notice",
      tone: "warn",
      role: "status",
      message: notice.message,
      nextAction: notice.nextAction || null,
      action: null,
      dismissible: true,
    });
  }
  for (const n of notes) {
    push({ id: `note-${n}`, tone: "info", role: "note", message: n, nextAction: null, action: null, dismissible: false });
  }
  /*
    005 FR-136 (U-05) — 실패한 Step 이 있으면 이어서 갈 수 없다는 사실과 **대가**를
    누르기 전에 말한다. 권한표는 「계속하기」를 잠그는 것까지 하고(O7), 무엇을 잃는지는
    문장이 말해야 한다.
  */
  if (!review && failedStepIndex !== null && !isDone) {
    push({
      id: "failed-step",
      tone: "warn",
      role: "status",
      message:
        `${stepLabel(failedStepIndex)} 이 실패해 이어서 갈 수 없습니다. ` +
        `「${stepLabel(failedStepIndex)} 고치기」 또는 「${stepLabel(failedStepIndex)}부터 실행」을 쓰세요.`,
      nextAction: onResumeSkippingFailure ? skipFailureNotice(failedStepIndex) : null,
      action: null,
      dismissible: false,
    });
  }
  /*
    005 FR-146·FR-133 — 실행이 끝났으면 **실패 사유**가 화면에 남는다.

    결말 요약은 국면 띠가 하나만 갖는다 (FR-218d). 여기 오는 것은 요약이 담지 못하는
    사유이며, 그것이 없으면 사용자는 빨간 ✕ 만 보고 새로고침을 누른다 (U-02).
  */
  if (failure !== null && (isDone || finishedWhilePausing || review)) {
    push({
      id: "run-failure",
      tone: "error",
      role: "status",
      message: failure.message,
      // 결과로 가는 길은 **헤더에 하나 있다.** 여기 버튼을 또 두면 같은 라벨이 두 자리에
      // 생기고, 그것이 FR-235 가 금지하는 것이다 (`LabelUniqueness` 가 센다).
      nextAction: null,
      action: null,
      dismissible: false,
    });
  }

  /* ─── 조작 ──────────────────────────────────────────────────────────────── */

  function onRemedy(action: ActionId) {
    runAction(action);
  }

  function runAction(action: ActionId) {
    switch (action) {
      case "run.pause":
        onPause?.();
        break;
      case "run.resume":
        onResume?.();
        break;
      case "run.resumeSkipFailure":
        onResumeSkippingFailure?.();
        break;
      case "run.stop":
        onStop?.();
        break;
      case "run.all":
        onRerunAll?.();
        break;
      case "run.from":
        onRerunFrom?.(Math.max(failedStepIndex ?? selectedIndex, 0));
        break;
      case "run.fromHere":
        if (selectedIndex >= 0) onRunFromHere?.(selectedIndex);
        break;
      case "step.recordStart":
        onRecordStart?.();
        break;
      case "step.recordStop":
        onRecordStop?.();
        break;
      case "step.reorder":
        onToggleReorder?.();
        break;
      case "step.addAssertion":
        setAssertOpen((v) => !v);
        break;
      case "step.addNaturalLanguage":
        if (nl.trim() !== "") {
          onNaturalLanguage?.(nl.trim());
          setNl("");
        }
        break;
      case "step.delete":
        if (focusedStepId !== null) onDeleteStep?.(focusedStepId);
        break;
      case "step.update":
        if (focusedStepId !== null) onOpenDetail?.(focusedStepId);
        break;
      case "result.show":
        onShowResult?.();
        break;
      case "save":
        onSave?.();
        break;
      case "nav.back":
        onShowList?.();
        break;
      default:
        break;
    }
  }

  /**
   * `run.from` 이 가리키는 Step.
   *
   * 실패한 것 → 지목한 것 → **끝난 세션이 멈춘 자리** 순서다. 마지막 항목이 005 FR-133 이
   * 요구한 「Step nn부터 실행」의 근거다 — 중지한 세션에서 사용자가 다시 걸고 싶은 곳은
   * 멈춘 자리이고, 그것을 화면이 알고 있는데 다시 고르라고 하면 한 번 더 일을 시킨다.
   */
  const runFromIndex =
    failedStepIndex ??
    (selectedIndex >= 0
      ? selectedIndex
      : finished && view.current_step_index > 0 && view.current_step_index < view.steps.length
        ? view.current_step_index
        : -1);

  /**
   * 표를 화면이 아는 사실로 한 겹 더 좁힌다.
   *
   * 표는 **국면**을 말한다. "지목한 Step 이 없다" 는 국면이 아니므로 표에 담을 수 없고,
   * 담지 않으면 무엇에 걸지 모르는 조작이 활성으로 남아 눌러도 아무 일이 없다.
   */
  const narrowByPick = (id: ActionId, base: CapabilityState): CapabilityState =>
    // `run.from` 은 여기서 제외한다 — 지목이 없어도 실패한 자리·멈춘 자리를 쓸 수 있고,
    // 그 판단은 `runFromIndex` 가 한다.
    id !== "run.from" && STEP_SCOPED.has(id) && focusedStepId === null && base.kind === "enabled"
      ? { kind: "disabled", reason: "먼저 Step 을 고르세요", remedy: { action: "step.select" } }
      : base;

  const action = (
    id: ActionId,
    extra: { label?: string; emphasis?: boolean | "quiet" } = {},
  ) => (
    <ActionButton
      key={id}
      action={id}
      capability={
        // `run.from` 은 지목이 없어도 **끝난 세션이 멈춘 자리**를 쓸 수 있다.
        id === "run.from" && runFromIndex < 0 && capabilities[id].kind === "enabled"
          ? { kind: "disabled", reason: "먼저 Step 을 고르세요", remedy: { action: "step.select" } }
          : narrowByPick(id, capabilities[id])
      }
      onRun={() => runAction(id)}
      onRemedy={onRemedy}
      {...extra}
    />
  );

  /**
   * 이동 조작은 **헤더**에 산다 (`lib/actions.ts` 의 배치 규칙).
   *
   * 자리를 묶음으로 정하면 "같은 자리의 같은 조작" (FR-235)이 배치 규칙으로 보장된다 —
   * 국면마다 결과·목록으로 가는 길이 다른 곳에 있던 것이 사용자가 매번 찾게 만들었다.
   */
  const headerActions = (
    <>
      <ActionButton
        action="result.show"
        capability={capabilities["result.show"]}
        compact
        onRun={() => runAction("result.show")}
        onRemedy={onRemedy}
      />
      <ActionButton
        action="nav.back"
        capability={capabilities["nav.back"]}
        compact
        onRun={() => runAction("nav.back")}
        onRemedy={onRemedy}
      />
    </>
  );

  /*
    **국면 띠의 조작 순서는 고정이다** (FR-235·FR-236). 국면마다 목록을 다르게 만들지
    않는다 — 「해당 없음」인 조작은 `ActionButton` 이 스스로 그리지 않으므로, 하나의
    순서를 두면 같은 조작이 언제나 같은 자리에 온다.
  */
  const phaseActions = (
    <>
      {capabilities["run.pacing"].kind !== "not_applicable" && (
        /* 실행 속도의 **자리**. 잠겨도 자리와 이유는 남는다 (FR-234). */
        <span data-action="run.pacing" style={{ display: "inline-flex", flexDirection: "column", gap: 4 }}>
          <PacingControl
            value={view.pacing}
            busy={busy}
            disabled={capabilities["run.pacing"].kind === "disabled"}
            preferenceSaved={pacingSaved}
            // 005 FR-174 (U-23) — 녹화·인수 국면에서는 「다음 실행 속도」로 밝힌다 (T041).
            manipulationPhase={manipulating}
            onChange={(next) => onPacingChange?.(next)}
          />
          {capabilities["run.pacing"].kind === "disabled" && (
            <span
              data-disabled-reason="run.pacing"
              style={{ font: `400 11.5px/1.3 ${SANS}`, color: "#6B675C" }}
            >
              {capabilities["run.pacing"].reason}
            </span>
          )}
        </span>
      )}
      {/* `step.recordStop` 의 집은 조작 팔레트다 (FR-235). 여기 두면 자리가 둘이 된다. */}
      {action("run.resume", { emphasis: true })}
      {action("run.resumeSkipFailure")}
      {action("run.pause", { emphasis: !isDone })}
      {action("run.all")}
      {action("run.from", { label: runFromStepLabel(Math.max(runFromIndex, 0)) })}
      {action("run.stop", {
        label: stopLabel({ finished: isDone, pending: stopRequested, review }),
        // 005 FR-147 (U-08) — 끝난 실행의 「닫기」에서는 강조를 뺀다.
        emphasis: isDone || review ? "quiet" : false,
      })}
    </>
  );

  /**
   * 저장할 수 있는가 (005 FR-156).
   *
   * 표는 국면을 말하고(Step 이 있는가·실행 중인가), 이름과 변경 유무는 화면이 안다.
   * 라벨은 바뀌지 않는다 — 「변경 저장」이 상황마다 다른 말이 되면 배운 것이 흔들린다.
   */
  const hasChangesToSave = view.saved_at == null || view.has_unsaved_changes;
  const saveCapability: CapabilityState =
    capabilities.save.kind !== "enabled"
      ? capabilities.save
      : saveName.trim() === ""
        ? { kind: "disabled", reason: "테스트 이름을 입력하세요", remedy: null }
        : !hasChangesToSave
          ? { kind: "disabled", reason: DISABLED_REASON.C9, remedy: null }
          : { kind: "enabled" };

  /*
    005 FR-154·FR-158 (U-09) — **저장 성공을 화면을 옮기지 않고 알 수 있다.**
    토스트로 끝내지 않는 이유는 사라지면 근거가 남지 않기 때문이다.
  */
  const savedNotice =
    view.saved_at != null ? (
      <div
        role="status"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          border: "3px solid #2E9455",
          background: "#F0F7F2",
          padding: "8px 12px",
        }}
      >
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="#2E9455" strokeWidth="2.8">
          <path d="M3 8.5l3.5 3.5L13 4.5" />
        </svg>
        <span style={{ font: `600 13px/1.3 ${SANS}` }}>{editSavedNotice(title)}</span>
        <div style={{ flex: 1 }} />
        {onShowList && (
          <button className="ghost" onClick={onShowList} disabled={busy}>
            목록에서 보기
          </button>
        )}
      </div>
    ) : null;

  const model: WorkbenchModel = {
    phase,
    testId,
    // 005 FR-134·FR-155 — 저장된 것은 「초안」이 아니다. 판정 규칙은 사전이 소유한다.
    testName: sessionTitle({
      title,
      persisted: testId !== null,
      savedAt: view.saved_at ?? null,
      hasUnsavedChanges: view.has_unsaved_changes,
    }),
    phaseBar: {
      // 걷기 W-1 이 잡은 것 — 끝난 실행에서 「실행 중」이라고 말하면 그 옆의 결말
      // 요약과 한 화면이 두 가지를 주장한다 (005 U-20).
      phaseLabel: sessionPhaseLabel(phase, { finished: isDone, review, pausing }),
      phaseTone,
      runSummary: restoredSummary,
      progressLabel,
    },
    target: {
      kind: "mirror",
      mirror: (
        <BrowserFrame url={currentUrl} badge={badge}>
          {mirror}
        </BrowserFrame>
      ),
      currentUrl,
      tabs: tabs ?? null,
    },
    work,
    steps,
    focusedStepId,
    detail:
      detailOpen && selectedIndex >= 0
        ? {
            step: view.steps[selectedIndex] ?? null,
            index: selectedIndex,
            // 세션 국면에는 그때의 시도 기록이 없다 — 그것은 결과 국면의 축이다.
            attempts: null,
            candidates: candidatesOf(view.steps[selectedIndex]),
            dropCandidates: dropCandidatesOf(view.steps[selectedIndex]),
            repickWaiting,
            failure:
              failure !== null && failure.index === selectedIndex
                ? { code: null, message: failure.message }
                : null,
          }
        : null,
    capabilities,
    notices,
    authoring: view.authoring_mode,
    pacing: view.pacing,
  };

  return (
    <Workbench
      model={model}
      phaseActions={phaseActions}
      headerActions={headerActions}
      noticesExtra={
        offline ? <LiveConnectionBanner onReconnect={() => onReconnect?.()} /> : null
      }
      stepEmptyNotice={
        phase === "running" ? "아직 기록된 Step 이 없습니다." : "기록된 Step 이 없습니다."
      }
      stepFooter={
        <ActionPalette
          capabilities={capabilities}
          onRun={runAction}
          onRemedy={onRemedy}
          narrow={narrowByPick}
          labels={{
            "run.fromHere":
              selectedIndex >= 0 ? `${stepLabel(selectedIndex)} 부터 이어 실행` : undefined,
            "step.addAssertion": assertOpen ? "검증 추가 닫기" : undefined,
          }}
          nl={{
            value: nl,
            onChange: setNl,
            onSubmit: () => {
              onNaturalLanguage?.(nl.trim());
              setNl("");
            },
          }}
          /*
            세션에서 테스트 이름은 **저장 이름을 겸한다** — 세션이 저장될 때 그 이름으로
            파일이 생긴다. 조작을 둘로 나누면 같은 값을 두 칸에 넣게 된다.
          */
          name={saveName}
          onNameChange={(v) => onSaveNameChange?.(v)}
          startUrl={view.steps[0]?.type === "navigate" ? view.steps[0].url : ""}
          onStartUrlChange={() => undefined}
          instruction={aiInstruction}
          saveLabel={sessionSaveLabel(view.saved_at != null)}
          saveCapability={saveCapability}
          saveNotice={savedNotice}
          stepCount={steps.length}
          emptyHint="Step 이 없으면 저장할 수 없습니다."
        />
      }
      onSelectStep={onSelectStep}
      onCloseDetail={() => onCloseDetail?.()}
      onSaveStep={onSaveStep}
      onRepick={onRepick}
      onChooseBlocked={onChooseBlocked}
      onDismissNotice={onDismissNotice}
      onAction={runAction}
      busy={busy}
    />
  );
}

/** `drag` 만 두 번째 대상을 갖는다. 나머지는 `null` 이어서 그 칸이 그려지지 않는다. */
function candidatesOf(step: Step | undefined) {
  if (step === undefined) return null;
  return "target" in step ? step.target : null;
}

function dropCandidatesOf(step: Step | undefined) {
  if (step === undefined) return null;
  return step.type === "drag" ? step.drop_target : null;
}

/** 지목한 Step 이 있어야 뜻이 있는 조작. */
const STEP_SCOPED = new Set<ActionId>([
  "step.update",
  "step.delete",
  "run.fromHere",
  "run.from",
]);

/**
 * 순서 변경 (FR-035).
 *
 * 드래그 앤 드롭을 쓰지 않는다. 목록이 200개까지 갈 수 있고(research R8) 드래그는 긴
 * 목록에서 정확히 놓기 어렵다. 위·아래 이동 버튼이 느리지만 틀리지 않는다.
 */
function ReorderPanel({
  steps,
  busy,
  onApply,
  onCancel,
}: {
  steps: { id: string; label: string }[];
  busy: boolean;
  onApply: (order: string[]) => void;
  onCancel: () => void;
}) {
  const [order, setOrder] = useState(steps.map((s) => s.id));
  const labelOf = (id: string) => steps.find((s) => s.id === id)?.label ?? id;

  const move = (index: number, delta: number) => {
    const next = [...order];
    const target = index + delta;
    const a = next[index];
    const b = next[target];
    if (target < 0 || target >= next.length || a === undefined || b === undefined) return;
    next[index] = b;
    next[target] = a;
    setOrder(next);
  };

  return (
    <div style={{ border: "3px solid #14130F", background: "#FFFDF6", padding: 12, maxHeight: 240, overflowY: "auto" }}>
      <strong style={{ font: "600 11px/1 'IBM Plex Mono', ui-monospace, monospace", letterSpacing: "0.1em" }}>
        순서 변경
      </strong>
      {order.map((id, index) => (
        <div key={id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0" }}>
          <span className="mono dim">{stepNumber(index)}</span>
          <span style={{ flex: 1 }}>{labelOf(id)}</span>
          <button className="ghost" aria-label={`${labelOf(id)} 위로`} onClick={() => move(index, -1)}>
            ↑
          </button>
          <button className="ghost" aria-label={`${labelOf(id)} 아래로`} onClick={() => move(index, 1)}>
            ↓
          </button>
        </div>
      ))}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
        <button className="secondary" onClick={onCancel}>
          취소
        </button>
        <button disabled={busy} onClick={() => onApply(order)}>
          적용
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 소유 — `SessionScreen`
// ─────────────────────────────────────────────────────────────────────────────

export interface SessionScreenProps {
  initial: SessionView;
  aiInstruction?: string | null;
  onFinished: () => void;
  onShowResult?: (testId: string, stepId?: string | null) => void;
  /** 다시 실행 — 이 세션을 버리고 같은 테스트로 새 세션을 연다 (UX U-02). */
  onRerun?: (testId: string, fromStepIndex?: number) => void;
}

export function SessionScreen({
  initial,
  aiInstruction = null,
  onFinished,
  onShowResult,
  onRerun,
}: SessionScreenProps) {
  const [view, setView] = useState<SessionView>(initial);
  const [tabs, setTabs] = useState<TabsResponse | null>(null);
  const [frame, setFrame] = useState<string | null>(null);
  const [mirrorTab, setMirrorTab] = useState<number>(initial.mirrored_tab_index);
  const [mirrorStopped, setMirrorStopped] = useState<string | null>(null);
  const [mirrorDegraded, setMirrorDegraded] = useState<string | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [lost, setLost] = useState<string | null>(null);
  const [runningIndex, setRunningIndex] = useState<number | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [failure, setFailure] = useState<{ index: number; message: string } | null>(null);
  const [saveName, setSaveName] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionId = initial.session_id;
  const [progress, setProgress] = useState<Record<string, StepProgress>>({});
  const durations = useRef<Record<string, number>>({});
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [repickWaiting, setRepickWaiting] = useState<RepickSlot | null>(null);
  const [notice, setNotice] = useState<ErrorInfo | null>(null);
  const [confirmingLeave, setConfirmingLeave] = useState(false);
  /** 끝난 실행 화면을 닫기 전 확인 (005 FR-148 · U-08). */
  const [confirmingClose, setConfirmingClose] = useState(false);
  const [aiMessages, setAiMessages] = useState<string[]>([]);
  const [aiError, setAiError] = useState<ErrorInfo | null>(null);
  const [aiBlocked, setAiBlocked] = useState<AiBlockedState | null>(null);
  const [pacingSaved, setPacingSaved] = useState(true);
  /** 일시정지 요청을 보냈고 아직 확정되지 않았다 (005 FR-142 · U-04). */
  const [pauseRequested, setPauseRequested] = useState(false);
  const [stopRequested, setStopRequested] = useState(false);
  /** 사용자 조작 없이 바뀐 국면의 알림 (FR-220). 사용자가 닫을 수 있다. */
  const [autoTransition, setAutoTransition] = useState<string | null>(null);
  const [live, setLive] = useState(true);
  const [showOffline, setShowOffline] = useState(false);
  const subscription = useRef<SessionSubscription | null>(null);

  const resync = useCallback(async () => {
    let fresh: SessionView;
    try {
      fresh = await sessions.get(sessionId);
      setView(fresh);
    } catch (exc) {
      setError(describeError(exc));
      return;
    }
    // 005 FR-135 (재점검 U-03-b) — **끝난 세션에는 탭을 묻지 않는다.** 조회 실패도
    // 오류로 다루지 않는다 — 보조 정보 하나 때문에 붉은 배너를 띄울 이유가 없다.
    if (TABLESS_STATES.has(fresh.state)) return;
    try {
      setTabs(await sessions.tabs(sessionId));
    } catch {
      // 조용히 넘긴다 — 위 주석. 세션 자체의 실패는 이미 위에서 잡았다.
    }
  }, [sessionId]);

  useEffect(() => {
    const sub = subscribeSessionEvents(sessionId, {
      onResync: () => void resync(),
      onConnectionChange: setLive,
      onEvent: (event: SessionEvent) => {
        switch (event.type) {
          case "mirror_frame":
            setFrame(event.data);
            setMirrorStopped(null);
            break;
          case "mirror_tab_changed":
            setMirrorTab(event.tab);
            break;
          case "mirror_degraded":
            setMirrorDegraded(event.reason ?? null);
            break;
          case "mirror_stopped":
            setMirrorStopped(event.reason ?? "미러가 중단됐습니다.");
            break;
          case "session_lost":
            setLost(event.reason ?? "브라우저 세션이 유실됐습니다.");
            void resync();
            break;
          case "step_started":
            setRunningIndex(event.index);
            break;
          case "step_finished": {
            const stepId = event.step_id;
            const durationMs = event.duration_ms;
            durations.current[stepId] = durationMs;
            setProgress((prev) => ({
              ...prev,
              [stepId]: { outcome: event.outcome as RunStepOutcome, durationMs },
            }));
            setRunningIndex(null);
            break;
          }
          case "step_failed":
            setFailure({ index: event.index, message: event.error_message });
            setRunningIndex(null);
            break;
          case "run_finished":
            setRunningIndex(null);
            // 005 FR-140·FR-141 (U-19·U-20·U-03) — 요약을 **사전에서 받는다.**
            setSummary(
              runSummary({
                outcome: event.outcome as Outcome,
                passedCount: event.passed_count,
                attemptedCount: event.attempted_count ?? event.total_count,
                totalCount: event.total_count,
                totalMs: event.total_ms,
                scope: event.scope ?? null,
                startIndex: event.start_index ?? null,
                failedStepIndex: event.failed_step_index,
                stoppedStepIndex: event.stopped_step_index ?? null,
              }),
            );
            void resync();
            break;
          case "run_error":
            setError(
              fromEvent(
                event.error,
                event.reason,
                "이 실행의 결과는 남지 않았습니다. 다시 실행하거나 Step을 확인하세요.",
              ),
            );
            break;
          case "pacing_changed":
            setPacingSaved(event.preference_saved);
            void resync();
            break;
          case "artifact_note":
            setNotes((prev) => (prev.includes(event.message) ? prev : [...prev, event.message]));
            break;
          case "tab_limit_reached":
            setError(
              localError(
                event.message ?? "탭 상한에 도달했습니다.",
                "쓰지 않는 탭을 닫은 뒤 다시 시도하세요.",
              ),
            );
            break;
          case "edit_warning":
            void resync();
            break;
          case "ai_progress":
            setAiMessages((prev) => [...prev, event.message]);
            break;
          case "ai_blocked":
            setAiBlocked({
              attempted: event.attempted ?? null,
              reason: event.reason ?? "AI 가 더 진행하지 못했습니다.",
              choices: (event.choices ?? []) as AiChoice[],
            });
            void resync();
            break;
          case "ai_error":
            // 실패해도 Step 은 보존된다 (FR-067). **진행 로그에도 남긴다** (002) —
            // 렌더 조건이 하나 어긋나도 사용자가 볼 경로가 둘이 되게 한다.
            setAiError(
              localError(
                event.reason,
                "다시 시도하거나, 직접 이어받아 Step을 만들 수 있습니다. 기록된 Step은 남아 있습니다.",
              ),
            );
            setAiMessages((prev) => [...prev, `실패: ${event.reason}`]);
            void resync();
            break;
          case "ai_finished":
            setAiBlocked(null);
            void resync();
            break;
          case "step_updated":
            setRepickWaiting(null);
            void resync();
            break;
          default:
            void resync();
        }
      },
    });
    subscription.current = sub;
    return () => {
      subscription.current = null;
      sub.stop();
    };
  }, [sessionId, resync]);

  /**
   * 007 FR-220 — 국면이 **사용자 조작 없이** 바뀐 순간을 잡는다.
   *
   * "조작 없이" 를 판정하는 근거는 요청 중이 아니라는 것이다 — 중지·일시정지를 누른
   * 전환에는 사용자가 이미 무엇을 했는지 안다. 남는 것이 서버가 스스로 넘긴 전환이고,
   * 그것이 알려야 하는 것이다.
   */
  const lastPhase = useRef<Phase>(phaseOfSession(initial));
  useEffect(() => {
    const next = phaseOfSession(view);
    const previous = lastPhase.current;
    lastPhase.current = next;
    if (next === previous) return;
    if (busy || stopRequested || pauseRequested) return;
    setAutoTransition(`화면이 「${PHASE_LABEL[previous]}」에서 「${PHASE_LABEL[next]}」로 바뀌었습니다.`);
  }, [view, busy, stopRequested, pauseRequested]);

  useEffect(() => {
    if (live) {
      setShowOffline(false);
      return;
    }
    const timer = setTimeout(() => setShowOffline(true), OFFLINE_NOTICE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [live]);

  const act = async (fn: () => Promise<SessionView>) => {
    setBusy(true);
    setError(null);
    try {
      setView(await fn());
    } catch (exc) {
      setError(describeError(exc));
    } finally {
      setBusy(false);
    }
  };

  /** 실행 속도 변경 (004 FR-103). **낙관적으로 반영하지 않는다** — 서버가 권위다. */
  const changePacing = (next: RunPacing) => {
    setPacingSaved(true);
    void act(() => sessions.setPacing(sessionId, next));
  };

  /** 편집 요청 공통 처리. 실패 사유를 알리되 화면을 떠나지 않는다 (FR-081). */
  const edit = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await resync();
    } catch (exc) {
      setNotice(describeError(exc));
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    setBusy(true);
    void sessions
      .save(sessionId, saveName.trim())
      .then(() => {
        // 005 FR-158 (U-09) — 성공 시 이전 오류 배너를 걷어낸다.
        setError(null);
        setNotice(null);
        return resync();
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  const isDone = TERMINAL_STATES.has(view.state);
  const isSaveableWithoutBrowser = SAVEABLE_WITHOUT_BROWSER.has(view.state);
  const testId = view.test_id;
  const isPaused = view.state === "paused";
  /** 005 FR-142~FR-146 — 일시정지 **전이 중**인가 (U-04). */
  const isPausing =
    (pauseRequested || view.pause_settled === false) && !TERMINAL_STATES.has(view.state);

  // 저장하지 않은 기록이 있는 동안 새로고침·닫기를 한 번 묻는다 (UX U-05).
  useEffect(() => {
    if (!view.has_unsaved_changes || isDone) return;
    const guard = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [view.has_unsaved_changes, isDone]);

  /*
    005 재점검 U-04-b — 미리보기 국면이 **전이와 종료를 구분한다.**
    순서가 판정이다: 조작 > 종료(브라우저 없음) > 실행 끝남 > 전이 중 > 일시정지.
  */
  const mirrorPhase: MirrorPhase = MANIPULATION_STATES.has(view.state)
    ? "manipulation"
    : isDone || isSaveableWithoutBrowser
      ? "terminated"
      : isPaused && summary !== null
        ? "finished"
        : isPausing
          ? "pausing"
          : isPaused
            ? "paused"
            : "observation";

  /**
   * 005 FR-171 (U-18·U-05) — 이벤트를 못 받은 화면도 결과를 복원한다.
   * 실시간 이벤트를 **우선한다** — 세션 뷰는 폴링 시점의 스냅샷이다.
   */
  const restored = new Map((view.step_results ?? []).map((r) => [r.step_id, r] as const));

  /**
   * 007 FR-225 (research R4 · S-09) — 작성 국면의 Step 은 **「기록됨」**이다.
   *
   * 이전 AI 작성 화면은 결말 자리에 **항상 체크 표식**을 그렸다. 결말을 모르는 국면인데
   * 통과처럼 보였다. 005 가 `skipped` 와 `not_run` 을 가른 것과 같은 종류의 구별이다.
   */
  const authoringPhase =
    view.state === "recording" ||
    view.state === "ai_running" ||
    view.state === "ai_blocked" ||
    view.state === "takeover_recording";

  const outcomeOf = (step: Step, index: number): StepOutcome => {
    const recorded = progress[step.id]?.outcome;
    if (recorded !== undefined) return recorded;
    const fromView = restored.get(step.id)?.outcome;
    if (fromView !== undefined && fromView !== "not_run") return fromView;
    if (runningIndex === index) return "running";
    return authoringPhase ? "recorded" : "pending";
  };
  const durationOf = (step: Step) =>
    durations.current[step.id] ?? restored.get(step.id)?.duration_ms;

  const mirror = (
    <MirrorView
      frame={frame}
      phase={mirrorPhase}
      stoppedReason={mirrorStopped}
      degradedReason={mirrorDegraded}
      tabIndex={mirrorTab}
    />
  );

  const tabStrip =
    tabs !== null ? (
      <TabStrip
        tabs={tabs.tabs}
        mirroredTabIndex={mirrorTab}
        maxTabs={tabs.max_tabs}
        onSelect={(index) => {
          void sessions
            .setMirrorTab(sessionId, index)
            .then((next) => {
              setTabs(next);
              setMirrorTab(next.mirrored_tab_index);
            })
            .catch(() => undefined);
        }}
      />
    ) : undefined;

  /**
   * DR-014 — 저장하지 않은 기록이 있는데 나가려 하면 확인을 받는다.
   * **중지는 화면을 떠나지 않는다** (DR-010).
   */
  const stop = () => void act(() => sessions.stop(sessionId));

  const leave = () => {
    if (view.has_unsaved_changes && view.steps.length > 0) {
      setConfirmingLeave(true);
      return;
    }
    // 005 FR-148 — 끝난 실행을 닫는 것은 **결과 접근을 끊을 수 있는** 조작이다.
    if (TERMINAL_STATES.has(view.state) && testId !== null) {
      setConfirmingClose(true);
      return;
    }
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(onFinished);
  };

  const closeConfirmed = () => {
    setConfirmingClose(false);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(onFinished);
  };

  /** 이 세션을 버리고 다시 실행한다. 같은 테스트에 세션이 둘일 수는 없다 (FR-043). */
  const rerun = (fromStepIndex?: number) => {
    if (testId === null || onRerun === undefined) return;
    setBusy(true);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(() => onRerun(testId, fromStepIndex));
  };

  const leaveConfirmed = () => {
    setConfirmingLeave(false);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(onFinished);
  };

  const saveAndLeave = () => {
    setBusy(true);
    void sessions
      .save(sessionId, saveName.trim())
      .then(() => {
        setConfirmingLeave(false);
        onFinished();
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  return (
    <>
      <SessionWorkbench
        view={view}
        aiInstruction={aiInstruction}
        aiMessages={aiMessages}
        aiError={aiError}
        aiBlocked={aiBlocked}
        summary={summary}
        failure={failure}
        outcomeOf={outcomeOf}
        durationOf={durationOf}
        busy={busy}
        pausing={isPausing}
        stopRequested={stopRequested}
        pacingSaved={pacingSaved}
        autoTransition={autoTransition}
        error={error}
        notice={notice}
        notes={notes}
        lost={lost}
        offline={showOffline}
        mirror={mirror}
        tabs={tabStrip}
        currentUrl={tabs?.tabs[mirrorTab]?.url ?? ""}
        mirroredTab={mirrorTab}
        focusedStepId={selectedStepId}
        detailOpen={inspecting}
        repickWaiting={repickWaiting}
        reordering={reordering}
        saveName={saveName}
        onSelectStep={(stepId) => setSelectedStepId(stepId)}
        onOpenDetail={(stepId) => {
          setSelectedStepId(stepId);
          setInspecting(true);
        }}
        onCloseDetail={() => setInspecting(false)}
        onSaveStep={(patch) => {
          if (selectedStepId === null) return;
          void edit(() => sessions.patchStep(sessionId, selectedStepId, patch));
        }}
        onRepick={(slot) => {
          if (selectedStepId === null) return;
          setRepickWaiting(slot);
          void sessions
            .repick(sessionId, selectedStepId, { slot })
            .then((resp) => {
              setNotice(localError(resp.message, "표시된 내용을 확인한 뒤 이어서 진행하세요."));
              if (!resp.waiting) setRepickWaiting(null);
              return resync();
            })
            .catch((exc: unknown) => {
              setRepickWaiting(null);
              setNotice(describeError(exc));
            });
        }}
        onSaveNameChange={setSaveName}
        onSave={save}
        onShowList={onFinished}
        onPause={() => {
          // 005 FR-142 — 요청 즉시 전이 표시를 켠다. 응답이 실패해도 걷는다.
          setPauseRequested(true);
          void act(() => sessions.pause(sessionId)).finally(() => setPauseRequested(false));
        }}
        onResume={() => void act(() => sessions.resume(sessionId))}
        /*
          005 FR-137 (재점검 N-04) — 실패한 Step 을 **건너뛰고** 이어간다.
          **인덱스를 넘기지 않는다** (T129). 건너뛸 Step 은 서버가 스스로 찾는다.
        */
        onResumeSkippingFailure={() => void act(() => sessions.resume(sessionId, true))}
        onStop={
          isDone || isSaveableWithoutBrowser
            ? leave
            : () => {
                setStopRequested(true);
                void Promise.resolve(stop()).finally(() => setStopRequested(false));
              }
        }
        onRecordStart={() => void act(() => sessions.recordActionsStart(sessionId))}
        onRecordStop={() => void act(() => sessions.recordActionsStop(sessionId))}
        onAddAssertion={(body) => void edit(() => sessions.addAssertion(sessionId, body))}
        onNaturalLanguage={(instruction) => {
          setBusy(true);
          setNotice(null);
          void sessions
            .aiStep(sessionId, instruction)
            .then((resp) => {
              setNotice(localError(resp.message, "표시된 내용을 확인한 뒤 이어서 진행하세요."));
              return resync();
            })
            .catch((exc: unknown) => setNotice(describeError(exc)))
            .finally(() => setBusy(false));
        }}
        onDeleteStep={(stepId) => void edit(() => sessions.deleteStep(sessionId, stepId))}
        onToggleReorder={() => setReordering((v) => !v)}
        onApplyReorder={(order) => {
          void edit(() => sessions.reorderSteps(sessionId, order));
          setReordering(false);
        }}
        onRunFromHere={(stepIndex) => void act(() => sessions.runFrom(sessionId, stepIndex))}
        onRerunAll={() => rerun()}
        onRerunFrom={(stepIndex) => rerun(stepIndex)}
        /*
          005 FR-133 (재점검 U-03-a) — 판단 근거는 "세션이 끝났는가" 가 아니라
          **"볼 결과가 남았는가"** 다. 중지 후 상태(`review`)는 종료 상태 집합에 없다.
        */
        onShowResult={
          testId !== null && onShowResult && (isDone || isSaveableWithoutBrowser)
            ? // 007 FR-239 (S-10) — 보던 Step 을 결과 국면으로 함께 넘긴다.
              () => onShowResult(testId, selectedStepId)
            : undefined
        }
        onChooseBlocked={(choice) => {
          setAiBlocked(null);
          void act(() => sessions.aiChoice(sessionId, choice as AiChoice));
        }}
        onPacingChange={changePacing}
        onReconnect={() => subscription.current?.reconnect()}
        onDismissNotice={(id) => {
          if (id === "notice") setNotice(null);
          if (id === "auto-transition") setAutoTransition(null);
        }}
      />

      {confirmingLeave && (
        <LeaveConfirm
          stepCount={view.steps.length}
          saveName={saveName}
          busy={busy}
          onSaveNameChange={setSaveName}
          onSave={saveAndLeave}
          onDiscard={leaveConfirmed}
          onCancel={() => setConfirmingLeave(false)}
        />
      )}
      {confirmingClose && (
        <CloseConfirm onCancel={() => setConfirmingClose(false)} onConfirm={closeConfirmed} />
      )}
    </>
  );
}

// ─── 확정 디자인이 정의하지 않은 조각들 (DC-009) ────────────────────────────

function Modal({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      role="dialog"
      aria-label={label}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(20, 19, 15, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 30,
      }}
    >
      <div
        style={{
          width: 520,
          border: "3px solid #14130F",
          background: "#FFFDF6",
          boxShadow: "10px 10px 0 #14130F",
          padding: 24,
        }}
      >
        {children}
      </div>
    </div>
  );
}

function CloseConfirm({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  return (
    <Modal label="실행 화면 닫기 확인">
      <div style={{ fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif", fontSize: 24 }}>
        실행 화면을 닫습니다
      </div>
      <p style={{ color: "#6B675C" }}>결과는 목록의 「결과 보기」에서 다시 볼 수 있습니다.</p>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
        <button className="secondary" onClick={onCancel}>
          돌아가기
        </button>
        <button onClick={onConfirm}>닫기</button>
      </div>
    </Modal>
  );
}

function LeaveConfirm({
  stepCount,
  saveName,
  busy,
  onSaveNameChange,
  onSave,
  onDiscard,
  onCancel,
}: {
  stepCount: number;
  saveName: string;
  busy: boolean;
  onSaveNameChange: (v: string) => void;
  onSave: () => void;
  onDiscard: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal label="저장하지 않고 나가기 확인">
      <div style={{ fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif", fontSize: 24 }}>
        저장하지 않은 기록이 있습니다
      </div>
      <p style={{ color: "#6B675C" }}>
        기록된 Step {stepCount}개가 있습니다. 저장하지 않고 나가면 사라집니다.
      </p>
      <label htmlFor="leave-save-name">테스트 이름</label>
      <input
        id="leave-save-name"
        value={saveName}
        autoFocus
        onChange={(e) => onSaveNameChange(e.target.value)}
        placeholder="프로젝트 생성"
      />
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
        <button className="secondary" onClick={onCancel}>
          돌아가기
        </button>
        <button className="danger" disabled={busy} onClick={onDiscard}>
          저장하지 않고 나가기
        </button>
        <button disabled={busy || saveName.trim() === ""} onClick={onSave}>
          저장하고 나가기
        </button>
      </div>
    </Modal>
  );
}
