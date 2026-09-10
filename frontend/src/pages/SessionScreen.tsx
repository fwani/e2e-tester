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
  groups as groupsApi,
  sessions,
  type AddAssertionBody,
  type AiChoice,
  type ManualStepSpec,
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
import {
  BrowserPromptPanel,
  type BrowserPromptState,
} from "../components/BrowserPromptPanel";
import { MirrorView, type MirrorPhase } from "../components/MirrorView";
import type {
  FrameGeometry,
  InputEvent as MirrorInputEvent,
} from "../components/mirror/useMirrorInput";
import { createMoveThrottle } from "../components/mirror/useMirrorInput";
import {
  connectControlChannel,
  type ControlChannel,
} from "../api/control";
import { PacingControl } from "../components/PacingControl";
import { TabStrip } from "../components/TabStrip";
import { BrowserFrame } from "../components/design/BrowserFrame";
import { ActionButton } from "../components/workbench/ActionButton";
import { ActionPalette } from "../components/workbench/ActionPalette";
import { BulkDeleteConfirm } from "../components/workbench/BulkDeleteConfirm";
import { InsertStepForm } from "../components/workbench/InsertStepForm";
import { ConfirmDelete, StepRowOps } from "../components/workbench/StepRowOps";
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
  narrowByWindowAvailability,
  type CapabilityFacts,
  type CapabilityState,
  isShown,
} from "../lib/capabilities";
import { hasLiveBrowser, isFinished, phaseOfSession, type Phase } from "../lib/phase";
import {
  ACTION_LABEL,
  DISABLED_REASON,
  FINISHED_WHILE_PAUSING_TITLE,
  PHASE_LABEL,
  editSavedNotice,
  pausedAfterLabel,
  pauseTargetProgress,
  pauseTargetUnreached,
  ARRIVED_RECORDING_STARTED,
  progressLabel as progressText,
  sessionPhaseLabel,
  runFromStepLabel,
  runSummary,
  sessionSaveLabel,
  sessionSaveState,
  skipFailureNotice,
  stepLabel,
  stopLabel,
  type ControlSurface,
  type OutcomeTone,
  SAVE_NEEDS_NAME,
  EDIT_NEEDS_SAVE,
  NO_DELETE_SELECTION,
  NO_STEPS_AFTER,
  RUN_NEEDS_SAVE,
} from "../lib/wording";
import type { Step } from "../types/generated/step";
import type { Outcome, StepOutcome as RunStepOutcome } from "../types/generated/run-result";

export type { AiBlockedState } from "../components/workbench/model";

/**
 * 끊김을 알리기까지 기다리는 시간. 재연결이 700ms 마다 일어나므로 짧은 끊김은
 * 배너가 깜빡이기만 하고 정보를 주지 않는다.
 */
const OFFLINE_NOTICE_DELAY_MS = 1500;


const MANIPULATION_STATES = new Set(["recording", "takeover_recording"]);

/**
 * 조작 국면 — 미러가 조작을 받는 상태들 (010 FR-314 · contracts/mirror-control.md §1).
 *
 * `MANIPULATION_STATES` 와 **다르다.** 그것은 「실제 브라우저 창을 앞으로 가져와야
 * 하는가」를 묻고 `paused` 를 뺀다. 이것은 「사람이 지금 브라우저를 조작하는가」를 묻고
 * `paused` 를 넣는다 — 일시정지에서 사람이 막힌 곳을 손으로 지나야 하기 때문이다 (US3).
 *
 * 서버의 `is_control_phase` 와 같은 집합이다 (`execution/state_machine.py`). 갈리면
 * 화면은 붙으려 하고 서버는 거절한다.
 */
const CONTROL_PHASE_STATES = new Set(["recording", "takeover_recording", "paused"]);
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
  /** 검토 — 아직 결말이 아니다. 저장할 것이 남아 있으므로 주의색이다 */
  review: "warn",
  /**
   * 실행 종료 — **중립이다.**
   *
   * 결말 색을 여기서 정하지 않는다. 통과·실패는 `phaseTone` 계산이 요약에서 가져오고
   * (`SessionWorkbench` 의 `phaseTone`), 이 표는 결말이 없을 때의 기본값이다. 여기에
   * 실패색을 박으면 중지한 세션이 실패로 보인다 (005 U-03).
   */
  finished: "neutral",
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

  /* ─── 010 미러 조작의 런타임 사정 (contracts/mirror-control.md §1) ───
   *
   * **국면이 아니라 런타임 사정이다.** 권한표에 사실로 넘기고, 판정은 표가 한다
   * (FR-316). 이 컴포넌트가 스스로 「지금 조작할 수 있나」를 계산하지 않는다.
   *
   * 값을 주지 않으면 `undefined` 이고, 표는 그것을 **거짓**으로 읽는다 — 모르는 것을
   * 조작 가능으로 그리지 않는다 (`CapabilityFacts` 의 규칙).
   */
  /** 프레임을 한 장이라도 받았는가 (FR-333) */
  mirrorFrameSeen?: boolean;
  /** 프레임이 지금 흐르고 있는가 (FR-346) */
  mirrorLive?: boolean;
  /** 조작 통로가 붙었는가 */
  controlChannelOpen?: boolean;
  /** 지금 조작이 어디서 이루어지는가 (FR-350 · data-model §6) */
  controlSurface?: ControlSurface;

  focusedStepId?: string | null;
  /** Step 상세 겹침이 열려 있는가. 지목과 상세 열기는 다른 조작이다 (FR-227·FR-230). */
  detailOpen?: boolean;
  repickWaiting?: RepickSlot | null;
  saveName?: string;

  onSelectStep: (stepId: string) => void;
  onOpenDetail?: (stepId: string) => void;
  onCloseDetail?: () => void;
  onSaveStep?: (patch: {
    label?: string;
    value?: string;
    timeout_ms?: number;
    sensitive?: boolean;
    /** 올릴 파일의 이름 — `upload` Step 만 갖는다 (2026-09-09) */
    file_name?: string;
  }) => void;
  onRepick?: (slot: RepickSlot) => void;
  onSaveNameChange?: (name: string) => void;
  /** 저장할 그룹 (013 FR-443). 아직 저장되지 않은 세션에만 뜻이 있다 */
  saveGroup?: string | null;
  onSaveGroupChange?: (prefix: string | null) => void;
  groupOptions?: { prefix: string; name: string }[];
  onSave?: () => void;
  onShowList?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onResumeSkippingFailure?: () => void;
  onStop?: () => void;
  onRecordStart?: () => void;
  onRecordStop?: () => void;
  onAddAssertion?: (body: AddAssertionBody) => void;
  /** 009 FR-290 — 일시정지 중 직접 입력으로 Step 추가. `at` 은 일시정지 위치다 */
  onInsertManual?: (spec: ManualStepSpec, at?: number) => void;
  onNaturalLanguage?: (instruction: string) => void;
  onDeleteStep?: (stepId: string) => void;
  /**
   * 여러 Step 을 **한 번에** 지운다 (011 FR-382·FR-388).
   *
   * `onDeleteStep` 을 반복 호출하지 않는다 — 중간에 끊기면 부분 적용이 남는다.
   */
  onDeleteSteps?: (stepIds: string[]) => void;
  /** 삭제 대상으로 고른 Step id 들. 소유는 `SessionScreen` 이다 */
  deleteSelection?: string[];
  onToggleDeleteTarget?: (stepId: string) => void;
  onToggleAllDeleteTargets?: () => void;
  /**
   * 009 FR-298·FR-301 — **행에서** 순서를 바꾼다.
   *
   * 이전에는 `onToggleReorder` 로 별도 패널을 열고 그 안에서 옮긴 뒤 「적용」을 눌렀다.
   * 화면에 Step 목록이 둘 뜨는 상태였고(SC-505), 세 칸 옮기는 데 다섯 번이 걸렸다.
   *
   * **순서 전체를 넘긴다.** 서버 계약(`steps:reorder`)이 순서 목록을 받으므로 화면이
   * 자리를 바꾼 결과를 만들어 보낸다 — 「위로/아래로」를 서버 연산으로 새로 만들지 않는다.
   */
  onApplyReorder?: (order: string[]) => void;
  onRunFromHere?: (stepIndex: number) => void;
  onRerunAll?: () => void;
  onRerunFrom?: (stepIndex: number) => void;
  onShowResult?: () => void;
  /**
   * 고치러 간다 (2026-09-09 사용자 보고 — 「실행 후 에러가 났을 때 고치는 방법이 없음」).
   *
   * 인자는 고칠 Step 의 식별자와 **자리**다. 자리가 필요한 이유는 목적지가 그 자리 앞까지
   * 재생한 세션이기 때문이다 (아래 `editStep` 의 주석).
   */
  onEditStep?: (stepId: string | null, stepIndex: number) => void;
  onChooseBlocked?: (choice: string, answer?: string) => void;
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
  /**
   * 삽입 입력면이 열려 있는가 (009 FR-290).
   *
   * 검증 추가와 **같은 문법**이다 — 여는 조작은 Step 패널 바닥에, 폼은 그 자리에 펼쳐진다.
   */
  const [insertOpen, setInsertOpen] = useState(false);
  /** 지우기 확인을 기다리는 Step (009 FR-302). **행 안에서** 묻는다. */
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  /**
   * 복수 삭제 확인을 기다리는 Step id 들 (011 FR-384 · UC-011-18).
   *
   * **개수와 범위를 문장으로 보여 준 뒤에 지운다.** 여러 개를 한 번에 지우는 조작은
   * 되돌리기가 비싸고, 「11개」만으로는 어느 11개인지 알 수 없다.
   */
  const [pendingBulk, setPendingBulk] = useState<string[] | null>(null);
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
    saveName = "",
    onSelectStep,
    onOpenDetail,
    onCloseDetail,
    onSaveStep,
    onRepick,
    onSaveNameChange,
    saveGroup = null,
    onSaveGroupChange,
    groupOptions = [],
    onSave,
    onShowList,
    onPause,
    onResume,
    onResumeSkippingFailure,
    onStop,
    onRecordStart,
    onRecordStop,
    onAddAssertion,
    onInsertManual,
    onNaturalLanguage,
    onDeleteStep,
    onDeleteSteps,
    deleteSelection = [],
    onToggleDeleteTarget,
    onToggleAllDeleteTargets,
    onApplyReorder,
    onRunFromHere,
    onRerunAll,
    onRerunFrom,
    onShowResult,
    onEditStep,
    onChooseBlocked,
    onPacingChange,
    onReconnect,
    onDismissNotice,
  } = props;

  const phase = phaseOfSession(view);
  const testId = view.test_id;
  const title = testId ?? "새 테스트";

  /**
   * 이 테스트에 **이름이 이미 있는가** (011 UC-011-4 · FR-362).
   *
   * **`view.saved_at` 이 아니다.** 그 값은 「이 **세션에서** 저장했는가」이고, 저장된
   * 테스트를 열어 만든 세션은 첫 저장 전까지 `null` 이다. 그래서 이름이 멀쩡히 있는데도
   * 라벨이 「저장」이 되고 빈 이름칸을 채워야 저장이 열렸다 — 사용자 보고 2번이 그것이다.
   *
   * 물어야 할 것은 「이 **테스트에** 이름이 있는가」이고, 그것은 `test_id` 다.
   */
  const hasName = testId !== null;

  /**
   * 국면 띠에 그릴 이름 (011 UC-011-2).
   *
   * 세션에서 테스트 이름은 **저장 이름을 겸한다** — 세션이 저장될 때 그 이름으로 파일이
   * 생긴다. 그래서 표시하는 값과 저장에 실리는 값이 하나여야 한다.
   *
   * **이 컴포넌트는 되돌림 규칙을 갖지 않는다.** `saveName` 을 그대로 그린다 — 서버가 준
   * 이름을 기본값으로 쓰는 판단은 상태를 소유한 `SessionScreen` 이 한다.
   *
   * 처음에는 여기서 「비었으면 서버 이름을 쓴다」로 메웠다. 그러면 **이름을 지울 수
   * 없다** — 사용자가 칸을 비우는 순간 서버 값이 되돌려 놓고, 저장이 잠기지 않아
   * FR-366(이름 없는 저장 거절)을 검사할 수도 없다. 되돌림을 표시 쪽에 두면 그 규칙이
   * 사용자 입력과 싸운다.
   */
  const displayName = saveName;
  /** 저장 요청에 실릴 이름. 표시와 같은 값이다 (두 칸에 넣게 하지 않는다) */
  const effectiveSaveName = displayName;

  const isDone = TERMINAL_STATES.has(view.state);
  const review = SAVEABLE_WITHOUT_BROWSER.has(view.state);
  const manipulating = MANIPULATION_STATES.has(view.state);
  const finished = isFinished(view);
  const liveBrowser = hasLiveBrowser(view) && lost === null;
  /** 멈추기 전에 실행이 끝났다 (005 FR-146). 실행 결말과 세션 상태는 다른 축이다. */
  const finishedWhilePausing = view.state === "paused" && summary !== null;

  /**
   * 저장한 뒤 더해진 Step (011 FR-379). 행의 「미저장」 표식이 이것을 본다.
   *
   * 009 가 편집 국면에 만든 표식과 **같은 뜻·같은 자리**다. 세션에서는 판정 근거가
   * 서버에 있어(`saved_snapshot`) 그때 붙이지 못했다 — 011 이 `unsaved_step_ids` 로
   * 그것을 실었다.
   */
  const unsavedIds = new Set(view.unsaved_step_ids ?? []);

  const steps: WorkbenchStep[] = view.steps.map((step, index) => ({
    id: step.id,
    index,
    step,
    label: step.label,
    outcome: outcomeOf(step, index),
    durationMs: durationOf(step) ?? null,
    isPausedHere: !review && phase === "paused" && index === view.current_step_index,
    isUnsaved: unsavedIds.has(step.id),
  }));

  const failedStepIndex = (() => {
    const at = steps.findIndex((s) => s.outcome === "fail");
    return at < 0 ? null : at;
  })();

  /**
   * 아직 도달하지 않은 목표 지점 (009 FR-293·FR-294).
   *
   * **서버가 준다** (`SessionView.pause_before_index`). 화면 상태로 들고 있으면 새로 고침
   * 한 번에 사라진다 — 005 U-18 과 같은 형태다 (research R5).
   */
  const pauseTarget = view.pause_before_index ?? null;
  const failedIndex = failedStepIndex ?? -1;

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
    /*
      **실행이 도는 동안에는 결말을 말하지 않는다** (사용자 보고 · 2026-09-09).

      `summary` 는 `run_finished` 로 채워지고 **지워지는 곳이 없었다.** 그래서 같은
      세션에서 다시 실행하면 국면 표시는 「실행 중」인데 그 옆에 지난 실행의
      「실패 · … · 10.07 s」가 그대로 남았다 — 한 화면이 두 가지를 주장하는 상태이며,
      005 U-19·U-20 이 고친 것과 같은 형태다.

      **그리고 그것이 국면 띠를 터뜨렸다.** 실측: 그 문장이 남으면 요약 칸이 폭 0 으로
      찌그러진 채 글자를 한 줄에 하나씩 쌓아 **높이 546px** 이 된다 (48px 짜리 띠에서).

      `step_started` 에서도 지우지만(아래 이벤트 처리), **여기서도 막는다.** 이벤트를
      놓친 화면이 있다는 것이 아래 주석의 전제이고, 그 화면에서도 같은 모순이
      나와서는 안 된다. 조건은 국면 표시가 「실행 중」이 되는 조건과 **같은 것**을 쓴다
      (`sessionPhaseLabel`) — 둘이 갈리면 그 틈에서 다시 두 주장이 공존한다.
    */
    if (phase === "running" && !isDone && !review && !pausing) return null;
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
  /**
   * 「이 뒤 전부」의 대상 (011 FR-383).
   *
   * **화면이 계산한다 — 서버 개념이 아니다.** 서버에 범위를 넣으면 「그 사이 목록이
   * 바뀌면 무엇을 지우는가」가 서버와 화면 양쪽에 생긴다 (research R5).
   *
   * 지목이 없으면 빈 배열이고, 그때 조작은 `narrowByPick` 이 이미 잠근다.
   */
  const afterTargets =
    selectedIndex >= 0 ? steps.slice(selectedIndex + 1).map((s) => s.id) : [];

  /**
   * 자리를 한 칸 옮긴다 (009 FR-299).
   *
   * **서버 연산을 새로 만들지 않는다.** `steps:reorder` 가 순서 목록을 받으므로 화면이
   * 맞바꾼 결과를 만들어 보낸다. 「위로/아래로」를 서버에 새 엔드포인트로 두면 순서 규칙이
   * 두 곳에 생긴다.
   *
   * 갈 곳이 없으면 아무 일도 하지 않는다 — 행 조작이 이미 비활성이지만(FR-300) 팔레트
   * 경로도 같은 함수를 지나므로 여기서도 막는다.
   */
  const moveStep = (index: number, delta: number) => {
    const to = index + delta;
    if (to < 0 || to >= steps.length) return;
    const ids = steps.map((s) => s.id);
    const order = ids.map((id, i) => (i === index ? ids[to] : i === to ? ids[index] : id));
    onApplyReorder?.(order as string[]);
  };

  /*
    009 FR-298 — 행 조작. **그 행의 자리를 인자로 받는다** — 고르는 조작이 끼지 않는다.
    일시정지 화면에서 세 칸 옮기는 데 다섯 번(패널 열기 + ↓×3 + 적용)이 걸렸던 것이
    세 번이 된다 (SC-503).
  */
  const runRowAction = (action: ActionId, index: number) => {
    const step = steps[index];
    if (step === undefined) return;
    switch (action) {
      case "step.moveUp":
        moveStep(index, -1);
        break;
      case "step.moveDown":
        moveStep(index, 1);
        break;
      case "step.delete":
        // FR-302 — 확인을 거친다.
        setConfirmDelete(step.id);
        break;
      case "step.insertManual":
        onSelectStep(step.id);
        setInsertOpen(true);
        break;
      default:
        break;
    }
  };

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
    /*
      010 미러 조작의 런타임 사정 (contracts/mirror-control.md §1).

      넷 다 **국면이 아니다.** 국면 열에 적으면 한 국면이 빠지고, 빠진 국면에서 화면은
      쓸 수 없는 조작을 활성으로 그린다 (research R9).
    */
    mirrorFrameSeen: props.mirrorFrameSeen,
    mirrorLive: props.mirrorLive,
    controlChannelOpen: props.controlChannelOpen,
    controlSurfaceIsMirror: (props.controlSurface ?? "mirror") === "mirror",
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
    /*
      009 FR-294 — **도달과 실패를 구별한다.**

      목표가 남아 있는데(= 닿지 못했다) 실패한 Step 이 있으면 그 사실을 말한다.
      「일시정지됨」만 말하면 사용자는 도달한 것으로 읽고 없는 자리에 Step 을 넣으려 한다.
      판정을 화면이 조립하지 않는다 — 「도달했는가」는 서버가 주는 목표 유무가 정한다.
    */
    if (pauseTarget !== null && failedIndex >= 0) {
      return pauseTargetUnreached(failedIndex, pauseTarget);
    }
    if (phase === "paused") return pausedAfterLabel(view.current_step_index);
    if (phase === "takeover") return "AI 실패 → 사람이 이어받음";
    // 005 FR-139 (U-14) — 끝난 실행에서는 진행 표시를 쓰지 않는다. 결말은 요약이 말한다.
    if (isDone) return null;
    if (phase === "running") {
      // 009 FR-293 — 목표가 있으면 **어디서 멈출 예정인지**를 함께 말한다.
      if (pauseTarget !== null) return pauseTargetProgress(view.current_step_index, pauseTarget);
      return progressText(view.current_step_index, view.steps.length);
    }
    return null;
  })();

  const phaseTone: OutcomeTone = (() => {
    if (view.state === "completed") return "success";
    if (view.state === "failed" || view.state === "lost") return "danger";
    if (view.state === "stopped" || view.state === REVIEW_STATE) return "neutral";
    return PHASE_TONE[phase];
  })();

  /* ─── 층③ 좌측 — 대상 앱 ────────────────────────────────────────────────── */

  /**
   * 미러 위의 상태 표식. **뜻만 정한다** — 색은 정본의 `.chip` 변형이 갖는다.
   *
   * 008 전에는 여기서 배경색과 글자색을 여섯 번 손으로 정했고, 그중 어느 것도 정본을
   * 거치지 않았다. 같은 상태를 다른 화면이 다른 색으로 칠할 수 있는 형태였다.
   */
  const badge = (() => {
    if (finishedWhilePausing) return { label: "실행 종료", tone: "" as const };
    if (pausing) return { label: "일시정지 중…", tone: "" as const };
    if (review) return { label: "SESSION ENDED", tone: "" as const };
    if (phase === "takeover") {
      return view.state === "takeover_recording"
        ? { label: "HUMAN CONTROL", tone: "fail" as const }
        : { label: "AI STOPPED", tone: "ai" as const };
    }
    if (phase === "paused") {
      return view.pacing === "step"
        ? { label: "한 스텝씩 — 다음 Step 을 기다립니다", tone: "warn" as const }
        : { label: "PAUSED", tone: "warn" as const };
    }
    if (manipulating) return { label: "RECORDING", tone: "fail" as const };
    return { label: "READ ONLY", tone: "" as const };
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
    /*
      009 FR-290 — 삽입 입력면. 검증 추가 폼과 **같은 자리**다 (T036 의 판단을 따른다).
      닫혀 있으면 자리를 차지하지 않는다.
    */
    if (insertOpen && capabilities["step.insertManual"].kind === "enabled") {
      return {
        kind: "paused_tools",
        tools: (
          <InsertStepForm
            atLabel={`Step ${stepLabel(view.current_step_index)}`}
            busy={busy}
            capability={capabilities["step.insertManual"]}
            /*
              세션 안에서는 브라우저가 **이미 열려 있다.** 그래서 요소가 필요한 종류의 갈
              길은 「브라우저 열기」가 아니라 그 자리에서의 「직접 조작으로 Step 추가」다 —
              표가 그 국면에 그 조작을 두고 있고, 폼은 그것을 가리킨다.
            */
            browserCapability={capabilities["step.recordStart"]}
            onSubmit={(spec) => {
              onInsertManual?.(spec);
              setInsertOpen(false);
            }}
            onOpenBrowser={() => runAction("step.recordStart")}
            onCancel={() => setInsertOpen(false)}
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

  /*
    2026-09-09 — **저장하지 않은 기록이 있으면 화면이 먼저 말한다** (사용자 보고).

    보고된 것: 「녹화하고 저장하는 부분이 명확하지 않다」. 실측에서 저장 자리는 Step 패널
    **바닥**에 있고(FR-235 가 정한 집이다), 잠긴 이유는 그 옆 작은 글씨였다. 녹화를 끝낸
    사용자의 눈은 국면 띠와 Step 목록에 있으므로 저장이 남았다는 사실이 보이지 않았고,
    그대로 「처음부터 실행」을 눌러 기록을 잃었다.

    **조작을 옮기지 않는다.** 자리는 그대로 두고 알림이 그 자리를 가리킨다 (`action` 이
    `save` 를 나른다) — 조작을 두 자리에 두면 FR-235 를 어긴다.

    브라우저가 없는 두 국면에만 낸다. 녹화·실행 중에는 아직 기록이 쌓이는 중이고, 그때
    저장을 재촉하면 매 Step 마다 알림이 뜬다.
  */
  if (
    (phase === "review" || phase === "finished") &&
    view.steps.length > 0 &&
    (view.saved_at == null || view.has_unsaved_changes)
  ) {
    push({
      id: "unsaved-record",
      tone: "warn",
      role: "status",
      message:
        view.saved_at == null
          ? `기록된 Step ${view.steps.length}개가 아직 저장되지 않았습니다.`
          : `저장한 뒤 바뀐 것이 있습니다. 기록된 Step ${view.steps.length}개.`,
      /*
        011 — **자리 안내가 화면 위쪽을 가리킨다.** 저장과 이름의 집이 Step 패널 바닥에서
        국면 띠로 옮겨졌으므로(007 계약 §2-7), 「Step 목록 아래에서」는 이제 틀린 안내다.
        문구가 자리를 말하는 이상 자리가 바뀔 때 함께 바뀌어야 한다.
      */
      nextAction:
        effectiveSaveName.trim() === ""
          ? "화면 위 국면 띠에서 테스트 이름을 정하고 「저장」을 누르세요. 저장하지 않으면 나가거나 다시 실행할 때 사라집니다."
          : "화면 위 국면 띠의 「저장」을 누르세요. 저장하지 않으면 나가거나 다시 실행할 때 사라집니다.",
      /*
        **버튼을 달지 않는다.** 저장의 자리는 국면 띠 하나이고(FR-235), 여기 버튼을
        또 두면 같은 라벨이 두 자리에 생긴다 — 바로 위 「run-failure」 알림이 같은 이유로
        결과 버튼을 달지 않았고, 이 파일이 그 결정을 이미 기록해 두었다. 검사가 그것을
        즉시 잡았다(`RunnerReview`: 「저장」 버튼이 둘). 알림은 자리를 **가리키기만** 한다.
      */
      action: null,
      dismissible: false,
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
      /*
        009 FR-298 — 옮기는 조작의 **자리는 행이다.** 팔레트에서 눌렀다면 지목한 Step 을
        대상으로 삼는다 — 표가 그 국면에 그 조작을 두고 있으므로 자리가 있어야 하고,
        팔레트는 `hidden` 으로 행에 양도한다 (계약 §3-3). 여기 남는 것은 표가 요구하는
        경로가 실제로 동작한다는 보장이다.
      */
      case "step.moveUp":
        if (selectedIndex >= 0) moveStep(selectedIndex, -1);
        break;
      case "step.moveDown":
        if (selectedIndex >= 0) moveStep(selectedIndex, 1);
        break;
      case "step.addAssertion":
        setAssertOpen((v) => !v);
        break;
      case "step.insertManual":
        setInsertOpen((v) => !v);
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
      /*
        011 — 복수 삭제. **확인은 팔레트가 아니라 이 화면이 세운다** (아래 `pendingBulk`).
        겹침 대화상자를 쓰지 않는 것은 009 FR-302 와 같은 근거다: 대상이 화면에서
        사라지면 무엇을 지우려던 것인지 다시 확인해야 한다.
      */
      case "step.deleteSelected":
        if (deleteSelection.length > 0) setPendingBulk(deleteSelection);
        break;
      case "step.deleteAfter":
        if (afterTargets.length > 0) setPendingBulk(afterTargets);
        break;
      case "step.update":
        if (focusedStepId !== null) onOpenDetail?.(focusedStepId);
        break;
      case "result.show":
        onShowResult?.();
        break;
      case "nav.editStep":
        onEditStep?.(steps[editTargetIndex]?.id ?? null, editTargetIndex);
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
  /**
   * 011 — 고른 것이 없으면 「고른 것 지우기」는 뜻이 없다 (FR-385 · UC-011-19).
   *
   * 「이 뒤 전부」가 **마지막 Step 에서** 잠기는 것도 여기서 본다. 둘 다 국면이 아니라
   * 화면이 아는 사실이라 표에 담을 수 없다.
   */
  const narrowByDeleteSelection = (id: ActionId, base: CapabilityState): CapabilityState => {
    if (base.kind !== "enabled") return base;
    if (id === "step.deleteSelected" && deleteSelection.length === 0) {
      return { kind: "disabled", reason: NO_DELETE_SELECTION, remedy: null, visibility: "keep" };
    }
    if (id === "step.deleteAfter" && selectedIndex >= 0 && afterTargets.length === 0) {
      // 해소 방법을 달지 않는다 — 끝단이라는 사실은 사용자가 고칠 것이 아니다 (009 AT_BOTTOM).
      return { kind: "disabled", reason: NO_STEPS_AFTER, remedy: null, visibility: "keep" };
    }
    return base;
  };

  const narrowByPick = (id: ActionId, base: CapabilityState): CapabilityState =>
    // `run.from` 은 여기서 제외한다 — 지목이 없어도 실패한 자리·멈춘 자리를 쓸 수 있고,
    // 그 판단은 `runFromIndex` 가 한다.
    id !== "run.from" && STEP_SCOPED.has(id) && focusedStepId === null && base.kind === "enabled"
      ? {
            kind: "disabled",
            reason: "먼저 Step 을 고르세요",
            remedy: { action: "step.select" },
            // `keep` — Step 을 고르면 곧바로 풀린다
            visibility: "keep",
          }
      : base;

  /**
   * **저장하지 않은 세션에는 실행할 대상이 없다** (2026-09-09 · 사용자 보고).
   *
   * 실행 조작 둘은 저장된 정의로 **새 세션을 연다** (`SessionScreen.rerun` → `App.startRun`).
   * 아직 저장하지 않은 녹화 세션(`test_id === null`)에는 그 정의가 없으므로 `rerun` 이
   * 첫 줄에서 그대로 돌아간다 — 실측에서 검토 국면의 「처음부터 실행」이 **활성인데
   * 눌러도 아무 일이 없는 버튼**이었다.
   *
   * 국면 표에 담을 수 없다: 「저장됐는가」는 국면이 아니라 세션의 사실이고, 같은 검토
   * 국면 안에서 갈린다. 표가 국면을 말하고 이 좁히기가 사실을 말한다.
   *
   * **`keep` 이다.** 자리를 남기는 것이 여기서는 안내가 된다 — 녹화한 뒤 무엇을 먼저
   * 해야 하는지(저장)를 실행 버튼 자리가 말해 준다. 해소 방법은 달지 않는다: 저장은 이름을
   * 요구하고 그 칸은 같은 화면의 조작 팔레트에 있으므로, 링크로 대신 누르면 이름 없는
   * 저장이 서버에서 거절된다.
   */
  const narrowByUnsaved = (id: ActionId, base: CapabilityState): CapabilityState =>
    (id === "run.all" || id === "run.from") && testId === null && base.kind === "enabled"
      ? { kind: "disabled", reason: RUN_NEEDS_SAVE, remedy: null, visibility: "keep" }
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
          ? {
            kind: "disabled",
            reason: "먼저 Step 을 고르세요",
            remedy: { action: "step.select" },
            // `keep` — Step 을 고르면 곧바로 풀린다
            visibility: "keep",
          }
          : narrowByUnsaved(id, narrowByPick(id, capabilities[id]))
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
  /**
   * 편집 화면으로 가는 조작의 상태 (2026-09-09 사용자 보고).
   *
   * 표는 국면을 말한다(`finished` 에서 ●). **저장 여부는 화면이 안다** — 편집 화면은
   * 저장된 정의를 읽으므로, 저장하지 않은 기록을 두고 넘어가면 그 기록이 사라진다.
   * `keep` 이다: 같은 화면의 「저장」으로 곧바로 해소된다.
   */
  const editStepCapability: CapabilityState = (() => {
    const base = capabilities["nav.editStep"];
    if (base.kind !== "enabled") return base;
    if (testId === null || view.has_unsaved_changes) {
      return { kind: "disabled", reason: EDIT_NEEDS_SAVE, remedy: null, visibility: "keep" };
    }
    return base;
  })();

  /**
   * 고치러 갈 Step. **실패한 자리를 먼저 고른다** (005 FR-136 · 009 FR-294).
   *
   * 실행이 실패해서 이 국면에 온 사용자가 고치려는 것은 그 Step 이다. 지목한 것이 있으면
   * 그것을 존중한다 — 사용자가 방금 고른 것을 화면이 되돌리면 안 된다.
   */
  const editTargetIndex = selectedIndex >= 0 ? selectedIndex : (failedStepIndex ?? -1);

  const headerActions = (
    <>
      <ActionButton
        action="nav.editStep"
        capability={editStepCapability}
        label={
          editTargetIndex >= 0
            ? `${stepLabel(editTargetIndex)} 고치기`
            : ACTION_LABEL["nav.editStep"]
        }
        compact
        onRun={() => runAction("nav.editStep")}
        onRemedy={onRemedy}
      />
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
      : effectiveSaveName.trim() === ""
        ? /*
             **저장 자리는 절대 사라지지 않는다** (`keep`).

             사용자가 보고한 「녹화하고 저장하는 부분이 명확하지 않다」의 절반이 이것이다.
             이름을 아직 안 썼다는 것은 사용자가 이 화면에서 곧바로 해소할 수 있는
             전제이고, 그때 저장 버튼이 사라지면 저장하는 방법을 배울 자리가 없어진다.

             011 — 이름이 **이미 있는** 테스트는 이 가지에 들어오지 않는다.
             `effectiveSaveName` 이 서버가 준 이름으로 채워져 있기 때문이다. 사용자가
             그것을 지우면 다시 들어온다 (FR-366 — 이름 없는 테스트로 만들지 않는다).
           */
          /*
             해소 방법은 **달지 않는다.** 이름칸은 국면 띠의 바로 왼쪽에 있고, 그것은
             누를 버튼이 아니라 채울 칸이다 — 링크로 만들면 눌러도 아무 일이 없다.
           */
          { kind: "disabled", reason: SAVE_NEEDS_NAME, remedy: null, visibility: "keep" }
        : !hasChangesToSave
          ? { kind: "disabled", reason: DISABLED_REASON.C9, remedy: null, visibility: "keep" }
          : { kind: "enabled" };

  /*
    **국면 띠의 조작 순서는 고정이다** (FR-235·FR-236). 국면마다 목록을 다르게 만들지
    않는다 — 「해당 없음」인 조작은 `ActionButton` 이 스스로 그리지 않으므로, 하나의
    순서를 두면 같은 조작이 언제나 같은 자리에 온다.
  */
  const phaseActions = (
    <>
      {/*
        실행 속도의 자리.

        **2026-09-09 — 「이 상태의 조작이 아니다」면 접는다.** 이전에는 「해당 없음」만
        보고 그렸고, 그래서 브라우저가 없는 국면(검토·실행 종료)에서 속도 선택 넷이
        「실행이 이미 끝났습니다」를 달고 국면 띠에 남았다. 돌릴 것이 없는 자리에서
        고르라고 내놓는 컨트롤이었다.
      */}
      {isShown(capabilities["run.pacing"]) && (
        <span
          data-action="run.pacing"
          /*
            **줄지 않는다.** 안의 버튼 넷은 `white-space: nowrap` 이라 좁아지면 줄어드는
            대신 잘린다 — 국면 띠에서 줄어드는 몫은 이유 문구가 받는다 (`ActionButton`).
          */
          style={{ display: "inline-flex", flexDirection: "column", gap: 4, flex: "0 0 auto" }}
        >
          <PacingControl
            value={view.pacing}
            busy={busy}
            disabled={capabilities["run.pacing"].kind === "disabled"}
            preferenceSaved={pacingSaved}
            /*
              005 FR-174 (U-23) — 지금 실행에 쓰이지 않는 국면에서는 「다음 실행 속도」로
              밝힌다 (T041).

              **검토·실행 종료를 더했다** (2026-09-09). 두 국면에는 돌고 있는 실행이 없고
              「처음부터 실행」이 활성으로 있다 — 여기서 고른 값은 그 실행의 속도다
              (004 FR-109). 「속도」라고만 쓰면 사용자는 지금 무언가에 적용된다고 읽는다.
            */
            manipulationPhase={manipulating || phase === "review" || phase === "finished"}
            onChange={(next) => onPacingChange?.(next)}
          />
          {capabilities["run.pacing"].kind === "disabled" && (
            <span
              data-disabled-reason="run.pacing"
              className="why"
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
      {/*
        ─── 저장 (011 · 007 계약 §2-7) ──────────────────────────────────────

        **실행 조작 뒤, 띠의 오른쪽 끝이다.** 순서를 고정하는 이유는 위 주석과 같다 —
        국면마다 자리가 바뀌면 근육 기억이 서지 않는다.

        011 이전 이 조작의 집은 Step 패널 바닥의 조작 팔레트였다. 저장하려면 Step 목록을
        다 지나 내려와야 했고, 못 찾고 나가면 기록이 사라졌다 (사용자 보고 1).
      */}
      {isShown(saveCapability) && (
        <ActionButton
          action="save"
          capability={saveCapability}
          label={sessionSaveLabel(hasName)}
          compact
          emphasis
          onRun={() => runAction("save")}
          onRemedy={onRemedy}
        />
      )}
    </>
  );

  /*
    005 FR-154·FR-158 (U-09) — **저장 성공을 화면을 옮기지 않고 알 수 있다.**
    토스트로 끝내지 않는 이유는 사라지면 근거가 남지 않기 때문이다.
  */
  const savedNotice =
    view.saved_at != null ? (
      <div
        role="status"
        className="tint-pass"
        style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px" }}
      >
        <svg className="pass-ink" width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.8">
          <path d="M3 8.5l3.5 3.5L13 4.5" />
        </svg>
        {/*
          011 converge — **이름을 말한다** (FR-367).

          `title` 은 `testId ?? "새 테스트"` 라 「저장했습니다 · TC-001」로 **id** 가
          나왔다. 011 이 `SessionView.test_name` 을 실었으므로 이제 사용자가 정한 이름을
          쓸 수 있다 — 확인줄이 id 를 말하면 사용자는 방금 저장한 것이 무엇인지 그 문장
          에서 알 수 없다.
        */}
        <span className="strong-sm">{editSavedNotice(displayName || title)}</span>
        <div className="spacer" />
        {onShowList && (
          <button className="btn sm" onClick={onShowList} disabled={busy}>
            목록에서 보기
          </button>
        )}
      </div>
    ) : null;

  const model: WorkbenchModel = {
    phase,
    testId,
    // 005 FR-134·FR-155 — 저장된 것은 「초안」이 아니다. 판정 규칙은 사전이 소유한다.
    /*
      011 UC-011-2 — **이름만** 넣는다. 저장 상태는 이름 옆의 칩이 갖는다 (`phaseName.status`).

      이전에는 `sessionTitle` 이 둘을 한 문장으로 붙였다 — 「TC-001 · 저장됨」. 이름 자리가
      입력칸이 된 뒤로 그 문장을 넣으면 「· 저장됨」까지 저장 이름이 된다.

      **이름이 「TC-001」에서 실제 이름으로 바뀌었다.** 세션이 그 값을 몰라 id 를 그리고
      있었고(`title = testId ?? "새 테스트"`), 011 이 `SessionView.test_name` 을 실었다.
    */
    testName: displayName,
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
    deleteSelection,
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
      /*
        011 UC-011-2 — 이름을 국면 띠 그 자리에서 고친다. 세션에서 이 값은 **저장 이름을
        겸한다**: 세션이 저장될 때 그 이름으로 파일이 생긴다. 조작을 둘로 나누면 같은
        값을 두 칸에 넣게 된다.
      */
      phaseName={{
        capability: capabilities["test.rename"],
        onChange: (v) => onSaveNameChange?.(v),
        onRemedy,
        status: sessionSaveState({
          persisted: testId !== null,
          savedAt: view.saved_at ?? null,
          hasUnsavedChanges: view.has_unsaved_changes,
        }),
      }}
      /*
        013 FR-443 — 저장할 그룹. **이미 저장된 테스트에는 주지 않는다**: 그룹 변경은
        자산을 옮기는 일이고 목록 화면의 「그룹으로 옮기기」가 그것을 한다.
      */
      phaseGroup={
        testId === null && onSaveGroupChange !== undefined
          ? { options: groupOptions, value: saveGroup, onChange: onSaveGroupChange }
          : undefined
      }
      headerActions={headerActions}
      /*
        009 FR-298 — 행 조작. **결과 국면은 이 화면이 아니다**(`ResultView` 가 그린다)
        므로 계약 §3-3-1 의 예외가 여기 걸리지 않는다 — 세션 국면은 전부 행이 갖는다.
      */
      rowActions={(step) =>
        confirmDelete === step.id ? (
          <ConfirmDelete
            label={step.label}
            onConfirm={() => {
              onDeleteStep?.(step.id);
              setConfirmDelete(null);
            }}
            onCancel={() => setConfirmDelete(null)}
          />
        ) : (
          <StepRowOps
            index={step.index}
            total={steps.length}
            label={step.label}
            capabilities={capabilities}
            busy={busy}
            onRun={runRowAction}
          />
        )
      }
      /*
        011 — 삭제 대상 고르기 (UC-011-14·15).

        **언제나 넘긴다.** 그릴지 말지는 `StepList` 가 **권한표**를 보고 정한다 — prop 이
        있는지로 정하면 표 밖에 판정이 하나 더 생기고, 그것이 007 이 없앤 형태다
        (`capabilities.ts` 머리말 — 각 국면 열이 그 국면 화면의 전부).

        결과 국면처럼 삭제 대상 선택이 없는 곳에서는 표가 접으라고 하므로 칸이 그려지지
        않는다. 콜백이 없어도 안전하다 — 그때는 조작 자체가 비활성이다.
      */
      deleteTargets={{
        selected: deleteSelection,
        capability: capabilities["step.toggleDeleteTarget"],
        allCapability: capabilities["step.selectAllDeleteTargets"],
        onToggle: (stepId) => onToggleDeleteTarget?.(stepId),
        onToggleAll: () => onToggleAllDeleteTargets?.(),
        onRemedy,
      }}
      noticesExtra={
        offline ? <LiveConnectionBanner onReconnect={() => onReconnect?.()} /> : null
      }
      stepEmptyNotice={
        phase === "running" ? "아직 기록된 Step 이 없습니다." : "기록된 Step 이 없습니다."
      }
      stepFooter={
        <>
        {/*
          011 UC-011-18 — 복수 삭제 확인. **겹침 대화상자를 쓰지 않는다** (009 FR-302 와
          같은 근거) — 대상이 화면에서 사라지면 무엇을 지우려던 것인지 다시 확인해야 한다.
          목록 바로 아래이므로 지울 것을 보면서 답한다.
        */}
        {pendingBulk !== null && (
          <BulkDeleteConfirm
            targets={pendingBulk}
            /* 011 FR-386 — 세션은 요청이 즉시 서버에 적용된다 — 되돌릴 수 없다 */
            revertible={false}
            steps={steps}
            busy={busy}
            onConfirm={() => {
              onDeleteSteps?.(pendingBulk);
              setPendingBulk(null);
            }}
            onCancel={() => setPendingBulk(null)}
          />
        )}
        <ActionPalette
          capabilities={capabilities}
          onRun={runAction}
          onRemedy={onRemedy}
          narrow={(id, base) => narrowByDeleteSelection(id, narrowByPick(id, base))}
          labels={{
            "run.fromHere":
              selectedIndex >= 0 ? `${stepLabel(selectedIndex)} 부터 이어 실행` : undefined,
            "step.addAssertion": assertOpen ? "검증 추가 닫기" : undefined,
            "step.insertManual": insertOpen ? "직접 입력 닫기" : undefined,
          }}
          nl={{
            value: nl,
            onChange: setNl,
            onSubmit: () => {
              onNaturalLanguage?.(nl.trim());
              setNl("");
            },
          }}
          startUrl={view.steps[0]?.type === "navigate" ? view.steps[0].url : ""}
          onStartUrlChange={() => undefined}
          instruction={aiInstruction}
          saveNotice={savedNotice}
          stepCount={steps.length}
          emptyHint="Step 이 없으면 저장할 수 없습니다."
        />
        </>
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

/**
 * 지목한 Step 이 있어야 뜻이 있는 조작.
 *
 * **009 T059 — 이동 두 조작을 더했다.** 빠져 있는 동안 일시정지 국면에서 Step 을 고르지
 * 않은 채 팔레트의 「위로/아래로 옮기기」를 누르면 `moveStep(-1, …)` 이 조용히 아무 일도
 * 하지 않았다 — **활성인데 동작하지 않는 조작**이며 005 U-01 이 그 형태였다.
 *
 * 조작의 **자리**는 팔레트가 선언하고 행은 사례다 (009 계약 §3-3-0). 자리가 선언되어
 * 있으면 그 경로도 동작해야 한다 — 그것이 표가 거짓말하지 않는다는 뜻이다.
 *
 * `step.insertManual` 은 **넣지 않는다.** 고른 Step 이 없으면 일시정지 위치에 넣으므로
 * 지목 없이도 뜻이 있다 (`step_edits._clamp`).
 */
const STEP_SCOPED = new Set<ActionId>([
  "step.update",
  "step.delete",
  "step.moveUp",
  "step.moveDown",
  "run.fromHere",
  "run.from",
  /*
    011 — 「이 뒤 전부 지우기」는 **어디 뒤인지**를 알아야 뜻이 있다. 지목이 없으면
    대상이 정해지지 않는다.

    `step.deleteSelected` 는 여기 없다 — 그것의 전제는 지목이 아니라 **체크한 것이
    있는가**이며, 아래 `narrowByDeleteSelection` 이 따로 좁힌다. 둘을 같은 사유로
    묶으면 「먼저 Step 을 고르세요」가 체크를 뜻하는지 지목을 뜻하는지 갈리지 않는다.
  */
  "step.deleteAfter",
]);

/*
  009 FR-301 · SC-505 — **`ReorderPanel` 을 없앴다.**

  별도 패널은 화면에 Step 목록을 **둘** 띄웠다. 목록은 이미 오른쪽 460px 패널에 있는데
  순서를 바꾸려면 그 사본을 하나 더 열어야 했고, 세 칸 옮기는 데 다섯 번(패널 열기 +
  ↓×3 + 적용)이 걸렸다 (관찰 M-06).

  이제 순서는 행의 위로·아래로가 바꾼다. 「적용」이 없다 — 누르는 즉시 반영된다.

  그 패널의 주석이 기록한 판단은 **유지된다**: 끌어놓기를 쓰지 않는다. 목록이 200개까지
  갈 수 있고 끌어놓기는 긴 목록에서 정확히 놓기 어렵다. 위·아래 이동이 느리지만 틀리지
  않는다 (009 명세 Assumptions 가 같은 판단을 다시 기록했다).
*/

// ─────────────────────────────────────────────────────────────────────────────
// 소유 — `SessionScreen`
// ─────────────────────────────────────────────────────────────────────────────

export interface SessionScreenProps {
  initial: SessionView;
  aiInstruction?: string | null;
  /**
   * 초안에서 출발한 세션 (014 3차 요청).
   *
   * 저장 이름과 그룹의 기본값이 된다 — 설계서에 이미 적혀 있는 것을 저장할 때 다시
   * 치게 하지 않는다. **저장을 누르면 바로 저장된다.**
   */
  draft?: { draft_id: string; name: string; group_prefix: string } | null;
  /**
   * 목표 자리에 도착하면 직접 조작 기록을 켠다 (009 FR-291·FR-295).
   *
   * 「이 앞에 추가」로 출발한 세션에만 참이다. **이 값은 화면 상태이며 서버에 없다** —
   * 새로 고치면 기록은 켜지지 않은 채로 오고, 그때 팔레트의 같은 조작을 쓸 수 있다
   * (research R5). 잃어도 막히지 않는 정보만 화면에 둔다.
   */
  recordOnArrival?: boolean;
  /**
   * 도착하면 이 지시문을 수행한다 (011 FR-374a·FR-375 · UC-011-23).
   *
   * `recordOnArrival` 과 **대칭이다.** 편집 국면에서 「지시문으로 더하기」를 누르면
   * 브라우저가 열리고 그 자리에서 지시문이 돈다 — 녹화가 도착하면 기록을 켜는 것과
   * 같은 흐름이다. 그 대칭이 없어서 두 길이 대등하게 보이지 않았다 (사용자 보고 3).
   *
   * **서버 상태에 저장하지 않는다** (009 research R5 와 같은 규칙). 새로 고치면 지시문은
   * 수행되지 않은 채로 오고, 그때 팔레트의 같은 조작을 그대로 쓸 수 있다.
   */
  instructionOnArrival?: string | null;
  onFinished: () => void;
  onShowResult?: (testId: string, stepId?: string | null) => void;
  /**
   * 실행이 끝나면 **스스로** 결과 국면으로 넘어간다 (2026-09-10 사용자 결정).
   *
   * 「실행이 완료되면 결과화면으로 자동 이전되면 좋겠다. 결과 상세보기나, 실행 후 결과를
   * 보는 것이나 사실은 같은 건데 버튼을 눌러 가는 게 UX 적으로 불편하다」.
   *
   * **`false` 인 경우가 있다.** 편집 화면에서 「Step nn 에서 멈추기」로 출발한 세션은
   * 돌아갈 곳이 편집 화면이다 (006 FR-204) — 거기서 결과로 튀면 사용자는 자기가 출발한
   * 화면을 잃는다. 판단 근거(`returnToEdit`)는 `App` 이 갖고 있으므로 `App` 이 정한다.
   */
  autoShowResult?: boolean;
  /**
   * 편집 화면으로 간다 (2026-09-09 사용자 보고).
   *
   * **세션을 먼저 버린다** — 그 일은 `SessionScreen` 이 한다 (아래 `editStep`). 편집
   * 화면은 저장된 정의를 읽고, 살아 있는 세션이 그 테스트를 잡고 있으면 편집이 잠긴다
   * (006 FR-206 · 조건 C7).
   */
  onEditStep?: (testId: string, stepId: string | null, stepIndex: number) => void;
  /** 다시 실행 — 이 세션을 버리고 같은 테스트로 새 세션을 연다 (UX U-02). */
  onRerun?: (testId: string, fromStepIndex?: number) => void;
}

export function SessionScreen({
  initial,
  aiInstruction = null,
  draft = null,
  recordOnArrival = false,
  instructionOnArrival = null,
  onFinished,
  onShowResult,
  autoShowResult = true,
  onEditStep,
  onRerun,
}: SessionScreenProps) {
  const [view, setView] = useState<SessionView>(initial);
  const [tabs, setTabs] = useState<TabsResponse | null>(null);
  const [frame, setFrame] = useState<string | null>(null);
  const [mirrorTab, setMirrorTab] = useState<number>(initial.mirrored_tab_index);
  const [mirrorStopped, setMirrorStopped] = useState<string | null>(null);
  const [mirrorDegraded, setMirrorDegraded] = useState<string | null>(null);
  /**
   * 010 — 마지막 프레임이 실어 온 좌표 변환의 근거 (FR-331 · data-model §2).
   *
   * `null` 이면 프레임을 한 장도 받지 못한 상태다. 그 상태에서는 좌표를 보낼 근거가
   * 없으므로 조작을 전달하지 않는다 (FR-333).
   */
  const [geometry, setGeometry] = useState<FrameGeometry | null>(null);
  /** 프레임이 지금 흐르고 있는가 (FR-346). 끊김과 정적 화면은 다르다 */
  const [mirrorLive, setMirrorLive] = useState(false);
  /** 조작 통로가 붙었는가 (contracts §1 런타임 덮어쓰기) */
  const [controlOpen, setControlOpen] = useState(false);
  /** 지금 조작이 어디서 이루어지는가 (FR-350 · data-model §6) */
  const [surface, setSurface] = useState<ControlSurface>(
    /*
      **서버가 아는 값에서 출발한다** (010 FR-349).

      이벤트로만 받으면 새로 고친 화면은 조작 위치를 잊는다 — 서버는 「창」이라고 알고
      화면은 「미러」라고 아는 상태가 되고, 그때 미러는 조작을 받는 것처럼 보인다.
      `SessionWork.control_surface` 는 처음부터 이 목적으로 있었는데 응답에 실리지
      않아 쓰이지 않고 있었다.
    */
    initial.control_surface ?? "mirror",
  );
  /**
   * 조작이 전달되지 않은 사유 (SC-516).
   *
   * 서버가 거절했거나, 화면이 조작을 받지 않는 상태에서 사용자가 시도했다. **조용히
   * 아무 일도 일어나지 않는 경우가 0건이어야 한다**는 것이 이 상태의 존재 이유다.
   */
  const [controlNotice, setControlNotice] = useState<string | null>(null);
  /**
   * 응답을 기다리는 브라우저 요구 (010 FR-338·FR-339).
   *
   * **하나만 들고 있는다.** 대화상자는 페이지를 세우므로 둘이 동시에 뜰 수 없고, 파일
   * 선택은 사용자가 하나씩 고른다. 목록으로 두면 화면이 무엇을 먼저 물을지 정해야 하고,
   * 그 순서는 대상 페이지가 정할 일이다.
   */
  const [prompt, setPrompt] = useState<BrowserPromptState | null>(null);
  const control = useRef<ControlChannel | null>(null);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [lost, setLost] = useState<string | null>(null);
  const [runningIndex, setRunningIndex] = useState<number | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  /**
   * 이번 실행이 멈춘 Step 의 위치 (2026-09-10 사용자 결정 — 「편집도 마찬가지 개념」).
   *
   * 결과 국면으로 자동으로 넘어갈 때 **지목을 함께 들고 간다.** 실패한 실행에서
   * 사용자가 다음에 하는 일은 그 Step 을 고치는 것이고, 결과 화면 맨 위에 떨어뜨리면
   * 그 자리를 다시 찾아야 한다 (007 FR-239 가 국면을 넘어 지목을 유지한 것과 같은 이유).
   */
  const [failedIndex, setFailedIndex] = useState<number | null>(null);
  const [failure, setFailure] = useState<{ index: number; message: string } | null>(null);
  /**
   * 사용자가 친 이름. **`null` 은 「아직 손대지 않았다」다** (011 FR-362).
   *
   * 빈 문자열과 갈라야 한다. 011 이전에는 이 상태가 `""` 로 시작했고, 그래서 「아직
   * 안 썼다」와 「지웠다」가 같은 값이었다 — 저장된 테스트를 연 세션은 이름이 멀쩡히
   * 있는데도 사용자가 처음부터 다시 쳐야 했고(사용자 보고 2), 반대로 「비었으면 서버
   * 이름을 쓴다」로 메우면 이름을 **지울 수 없게** 된다.
   *
   * `null` 이면 서버가 준 이름을 쓰고, 문자열이면 — 빈 문자열이라도 — 그것이 이긴다.
   */
  const [nameOverride, setNameOverride] = useState<string | null>(null);
  /**
   * 저장 요청과 표시에 함께 쓰이는 이름. 두 칸에 넣게 하지 않는다.
   *
   * **초안에서 온 세션은 초안의 제목이 기본값이다** (014 3차 요청). 설계서에 이미 이름이
   * 적혀 있는데 저장할 때 다시 치라고 하면, 사용자는 같은 것을 두 번 쓰게 되고 두 이름이
   * 어긋날 자리가 생긴다. 사용자가 고칠 수 있으므로 **값이 아니라 기본값**이다.
   */
  /*
    초안의 출처는 **응답이 먼저다** (수렴 2회차). prop 은 화면 기억이라 새로 고치면
    사라지고, 응답은 세션이 살아 있는 동안 계속 온다. 둘 다 없을 때만 빈 값이다.
  */
  const origin = view.draft ?? draft;
  const effectiveSaveName = nameOverride ?? view.test_name ?? origin?.name ?? "";

  /**
   * 저장할 그룹 (013 FR-443 · converge T062).
   *
   * **이름과 같은 자리에 산다** — 둘이 함께 「이 테스트가 무엇으로 저장되는가」를 정하고,
   * 그룹은 식별자에 들어가므로(`USER-001`) 저장 시점에 정해져야 한다.
   *
   * **아직 저장되지 않은 세션에만 쓴다.** 이미 저장된 테스트의 그룹을 바꾸는 것은 파일과
   * 실행 산출물을 옮기는 일이고, `tests.move` 가 원자성 규약과 함께 그것을 한다 — 저장에
   * 자산 이동을 숨기지 않는다.
   */
  const [saveGroup, setSaveGroup] = useState<string | null>(null);

  /*
    초안의 그룹을 저장 그룹의 기본값으로 삼는다 (014 3차 요청).

    초안은 어느 시트에서 왔는지가 곧 소속이므로, 저장할 때 그룹을 다시 고르게 하면
    사용자는 이미 정해진 것을 또 정하게 된다. 한 번만 맞춘다 — 이후에는 사용자가 고른
    값이 이긴다.
  */
  const draftGroupApplied = useRef(false);
  useEffect(() => {
    if (draftGroupApplied.current) return;
    if (!origin || view.test_id !== null) return;
    draftGroupApplied.current = true;
    setSaveGroup(origin.group_prefix === "TC" ? null : origin.group_prefix);
  }, [origin, view.test_id]);
  const [groupOptions, setGroupOptions] = useState<{ prefix: string; name: string }[]>([]);

  useEffect(() => {
    void groupsApi
      .list()
      .then((r) =>
        setGroupOptions((r.groups ?? []).map((g) => ({ prefix: g.prefix, name: g.name }))),
      )
      // 그룹을 못 불러와도 저장은 되어야 한다 — 그룹은 선택 사항이다.
      .catch(() => setGroupOptions([]));
  }, []);


  /**
   * 삭제 대상으로 고른 Step (011 FR-380·FR-380b · UC-011-16).
   *
   * **인덱스가 아니라 id 다.** 인덱스로 가지면 순서 변경 뒤에 다른 Step 이 지워진다 —
   * 고른 것은 「세 번째 행」이 아니라 「그 Step」이다.
   *
   * **저장되지 않는다.** 화면 안에서만 사는 일시 상태이며 서버로 가지 않는다
   * (data-model §6).
   */
  const [deleteSelection, setDeleteSelection] = useState<string[]>([]);
  /*
    목록이 바뀌면 **사라진 id 만** 뺀다 (data-model §4-1).

    비우지 않는 이유: 녹화가 Step 을 더하는 동안에도 고른 것은 그대로여야 한다. 순서가
    바뀌어도 남는 것이 FR-380b 이며, id 로 갖는 것이 그것을 공짜로 만든다.

    `join` 으로 비교하는 이유는 `view.steps` 가 매 응답마다 새 배열이라서다 — 참조로 비교하면
    내용이 같아도 매번 돈다.
  */
  const stepIdsKey = view.steps.map((s) => s.id).join(",");
  useEffect(() => {
    const alive = new Set(stepIdsKey === "" ? [] : stepIdsKey.split(","));
    setDeleteSelection((prev) => {
      const next = prev.filter((id) => alive.has(id));
      return next.length === prev.length ? prev : next;
    });
  }, [stepIdsKey]);
  /** 이 테스트에 이름이 이미 있는가. 확인 대화상자가 이름을 묻는지를 정한다 (UC-011-5) */
  const testHasName = (view.test_id ?? null) !== null;
  const [busy, setBusy] = useState(false);
  const sessionId = initial.session_id;
  const [progress, setProgress] = useState<Record<string, StepProgress>>({});
  /**
   * **이번 실행에서 아직 돌지 않은 Step** (2026-09-09 사용자 보고).
   *
   * 보고 문장: 「테스트를 다시 실행하는 스텝이면, 상태 표기가 업데이트 되어야함」.
   *
   * 왜 갱신되지 않았나. 결말은 두 곳에서 온다 — 이 화면이 모은 `progress`(이벤트)와
   * 서버가 준 `view.step_results`(지난 실행의 기록). 세션 안에서 다시 실행하면
   * (「이 Step 부터 이어 실행」·「계속하기」) 화면이 다시 마운트되지 않으므로 **둘 다
   * 지난 실행의 값을 그대로 들고 있었다.** 그래서 다시 도는 Step 의 행이 지난 실행의
   * 「통과」를 계속 보여 줬고, 「실행 중」 표시조차 그 뒤에 가려 나오지 못했다
   * (`outcomeOf` 의 판정 순서 — 아래에서 함께 고쳤다).
   *
   * 담는 것은 **자리 하나**다 — 이 자리부터 뒤는 이번 실행에서 아직 돌지 않았다.
   * `step_started(i)` 가 올 때마다 i 로 올라간다. 앞으로 진행하는 경우에도 참이므로
   * 「다시 실행인가」를 화면이 추측하지 않는다 — 추측이 틀린 국면에서 옛 결말이 되살아난다.
   *
   * **Step 목록을 훑지 않는다.** 처음에는 무효화된 Step 의 `id` 집합으로 만들었는데,
   * 그러려면 이벤트를 받는 시점에 Step 목록이 필요하고 그 목록은 이벤트 핸들러가 붙은
   * 시점의 것이다(닫힘). 자리 하나면 그 문제가 없다.
   *
   * `null` 이면 이 화면은 이번 세션에서 실행 시작을 보지 못했다 — 새로 고침으로 복원한
   * 화면이 그렇다. 그때 화면이 아는 것은 서버가 준 기록뿐이고, 그것을 사실이 아니라고
   * 말할 근거가 없다.
   */
  const [staleFromIndex, setStaleFromIndex] = useState<number | null>(null);
  const durations = useRef<Record<string, number>>({});
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [repickWaiting, setRepickWaiting] = useState<RepickSlot | null>(null);
  const [notice, setNotice] = useState<ErrorInfo | null>(null);
  const [confirmingLeave, setConfirmingLeave] = useState(false);
  /** 끝난 실행 화면을 닫기 전 확인 (005 FR-148 · U-08). */
  const [confirmingClose, setConfirmingClose] = useState(false);
  /**
   * 「처음부터 실행」·「Step nn부터 실행」이 저장하지 않은 기록을 만난 자리 (2026-09-09).
   *
   * `null` 이면 확인 창이 없다. 값이 있으면 그 안의 `fromStepIndex` 가 확인 뒤에 걸
   * 실행의 시작 자리다 — 확인 창이 어느 버튼에서 왔는지를 잊으면 「처음부터」를 눌렀는데
   * 부분 실행이 걸린다.
   */
  const [confirmingRerun, setConfirmingRerun] = useState<{ fromStepIndex: number | null } | null>(
    null,
  );
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
            setMirrorLive(true);
            // 좌표 변환의 근거를 프레임과 **함께** 갱신한다 (FR-331). 따로 두면 프레임이
            // 바뀐 뒤 옛 배율로 좌표를 계산하는 순간이 생긴다.
            setGeometry({
              width: event.width,
              height: event.height,
              pageScale: event.pageScale,
              offsetTop: event.offsetTop,
              frameSeq: event.frameSeq,
            });
            break;
          case "mirror_tab_changed":
            setMirrorTab(event.tab);
            break;
          case "mirror_degraded":
            setMirrorDegraded(event.reason ?? null);
            break;
          case "mirror_stopped":
            setMirrorStopped(event.reason ?? "미러가 중단됐습니다.");
            setMirrorLive(false);
            break;
          case "browser_prompt":
            setPrompt({
              promptId: event.promptId,
              kind: event.kind,
              message: event.message,
              multiple: event.multiple,
              blocking: event.blocking,
            });
            break;
          case "browser_prompt_resolved":
            // `promptId: "*"` 는 세션 종료 시의 일괄 정리다 (`prompts.dismiss_all`).
            setPrompt((current) =>
              current === null ||
              event.promptId === "*" ||
              current.promptId === event.promptId
                ? null
                : current,
            );
            break;
          case "control_surface":
            setSurface(event.surface);
            break;
          case "session_lost":
            setLost(event.reason ?? "브라우저 세션이 유실됐습니다.");
            void resync();
            break;
          case "step_started": {
            // 새 실행이 결과를 내기 시작했다. 지난 실행의 결말 요약은 이 시점부터
            // 사실이 아니다 — 남겨 두면 「실행 중」 옆에서 끝난 실행을 말한다.
            setSummary(null);
            setRunningIndex(event.index);
            /*
              2026-09-09 — **이 자리부터의 지난 결과를 걷는다** (사용자 보고).

              `event.index` 부터 뒤는 이번 실행에서 아직 돌지 않았다. 다시 실행이든 앞으로
              진행이든 같은 사실이므로 조건을 나누지 않는다.

              **결말도 소요 시간도 지우지 않는다 — 가린다.** 처음에는 `progress` 에서
              지우고 `durations`(ref)에서도 지웠는데, 검사가 그것을 잡았다: 상태 갱신
              함수 안에서 ref 를 변형하면 그 함수가 다시 불릴 때(React 는 갱신 함수를
              순수하다고 보고 여러 번 부를 수 있다) 방금 도착한 이번 실행의 값이 함께
              지워진다. 실제로 `step_finished` 의 55ms 가 사라졌다.

              자리 하나를 올려 두고 **읽는 쪽이 가리는** 방식이면 그 위험이 없다
              (`outcomeOf`·`durationOf`).
            */
            setStaleFromIndex((prev) => (prev === null ? event.index : Math.max(prev, event.index)));
            /*
              실패 배너도 그 자리에서 걷는다. 실패한 Step 을 고쳐 다시 돌리는 중에 「Step
              06 이 실패했습니다」가 남아 있으면, 사용자는 방금 고친 것이 또 실패한 줄 안다.
            */
            setFailure((prev) => (prev !== null && prev.index >= event.index ? null : prev));
            break;
          }
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
            setFailedIndex(event.failed_step_index ?? null);
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
              question: event.question ?? null,
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
      .save(sessionId, effectiveSaveName.trim(), view.test_id === null ? saveGroup : null)
      .then((saved) => {
        // 005 FR-158 (U-09) — 성공 시 이전 오류 배너를 걷어낸다.
        setError(null);
        /*
          014 FR-032 — 초안의 희망 번호를 주지 못했으면 **그 사실을 말한다.**
          사용자의 설계서에는 원래 번호가 적혀 있다. 조용히 다른 번호를 주면
          제품과 설계서가 어긋난 것을 나중에 발견하게 된다.
        */
        const taken = saved.desired_id_taken;
        setNotice(
          taken
            ? localError(
                `${taken.wanted} 은 이미 쓰이고 있어 ${taken.assigned} 로 저장했습니다.`,
                "설계서의 번호를 맞추려면 「번호 정리」를 쓰거나 설계서를 고치세요.",
              )
            : null,
        );
        return resync();
      })
      .catch((exc: unknown) => setError(describeError(exc)))
      .finally(() => setBusy(false));
  };

  const isDone = TERMINAL_STATES.has(view.state);
  const isSaveableWithoutBrowser = SAVEABLE_WITHOUT_BROWSER.has(view.state);
  const testId = view.test_id;
  const isPaused = view.state === "paused";

  /*
    009 FR-291·FR-295 — 목표 자리에 **도착하면** 기록을 켠다.

    조건이 셋이다. ① 「이 앞에 추가」로 출발했다 ② 일시정지에 닿았다 ③ 목표가 비었다
    (= 실제로 도달했다). ③ 이 없으면 목표 앞에서 **실패해 멈춘** 경우에도 기록이 켜져,
    사용자는 실패한 자리에서 브라우저를 만지게 된다 (FR-294 가 없애려는 혼동이다).

    한 번만 켠다 — 「기록 멈추기」를 누른 뒤 다시 켜지면 멈출 수 없다.
  */
  const armedRecord = useRef(false);
  useEffect(() => {
    if (!recordOnArrival || armedRecord.current) return;
    if (view.state !== "paused") return;
    if ((view.pause_before_index ?? null) !== null) return;
    armedRecord.current = true;
    setNotice(
      localError(
        ARRIVED_RECORDING_STARTED,
        "그만 기록하려면 「기록 멈추기」를 누르세요.",
      ),
    );
    void act(() => sessions.recordActionsStart(sessionId));
    // `act` 는 위에서 선언됐다. 의존성에 넣으면 매 렌더마다 새 함수라 효과가 다시 돈다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordOnArrival, view.state, view.pause_before_index, sessionId]);

  /*
    011 FR-374a — 목표 자리에 **도착하면** 지시문을 수행한다.

    위 효과와 **같은 조건 셋**이다 (출발 의도가 있다 · 일시정지에 닿았다 · 목표가 비었다).
    같게 두는 이유는 대등성 그 자체다 — 조건이 다르면 한쪽만 되는 상황이 생기고, 그것이
    사용자가 「녹화처럼 되지 않는다」로 겪는 것이다.

    한 번만 수행한다. 두 번 돌면 같은 Step 이 두 벌 들어간다.
  */
  const armedInstruction = useRef(false);
  useEffect(() => {
    const instruction = (instructionOnArrival ?? "").trim();
    if (instruction === "" || armedInstruction.current) return;
    if (view.state !== "paused") return;
    if ((view.pause_before_index ?? null) !== null) return;
    armedInstruction.current = true;
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
    // `resync` 는 매 렌더마다 새 함수다 — 넣으면 효과가 다시 돈다 (위 효과와 같은 이유).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [instructionOnArrival, view.state, view.pause_before_index, sessionId]);
  /*
    2026-09-10 사용자 결정 — **실행이 끝나면 결과 국면으로 스스로 넘어간다.**

    「결과 상세보기나, 실행 후 결과를 보는 것이나 사실은 같은 건데 버튼을 눌러 가는 게
    UX 적으로 불편하다」. 실제로 같다 — 두 자리가 그리는 것은 같은 `RunResult` 하나다.

    ## 조건

    - **`completed`·`failed` 만이다.** `stopped`·`lost` 는 「실행이 완료된 것」이 아니다.
      사용자가 중지한 자리·유실된 자리에서 화면을 뺏으면, 그 순간 화면에 있던 것(멈춘
      지점·유실 사유)을 잃는다.
    - **저장된 테스트여야 한다.** `test_id` 가 없는 초안은 결과 화면이 읽을 대상이 없다.
    - **한 번만 넘어간다.** 뒤로가기로 돌아왔을 때 다시 튕겨 나가면 실행 화면에 머물 수
      없다.

    결과 파일은 이미 디스크에 있다 — 러너가 결과를 쓴 **뒤에만** 종료 상태로 옮긴다
    (`execution/runner.py` 의 `_settle`). 그래서 도착한 결과 화면이 빈손일 수 없다.

    **세션을 버리지 않는다.** 브라우저는 실패보다 오래 살아야 하고 (헌법 원칙 III),
    목록의 세션 배너가 돌아갈 길을 갖고 있다 — 「결과 보기」 버튼이 하던 것과 정확히
    같은 일을 자동으로 할 뿐, 세션 수명을 바꾸지는 않는다.
  */
  const jumpedToResult = useRef(false);
  useEffect(() => {
    if (!autoShowResult || jumpedToResult.current) return;
    if (view.state !== "completed" && view.state !== "failed") return;
    if (testId === null || onShowResult === undefined) return;
    jumpedToResult.current = true;
    // 실패한 Step 을 지목해 넘긴다 — 고치러 갈 자리를 결과 화면이 이미 펼쳐 놓는다.
    onShowResult(testId, failedIndex === null ? null : (view.steps[failedIndex]?.id ?? null));
    // `onShowResult` 는 매 렌더 새 함수일 수 있다 — 넣으면 효과가 다시 돈다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoShowResult, view.state, testId]);

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

  /* ─── 010 조작 채널 (contracts/mirror-control.md §2) ─────────────────────
   *
   * **국면이 조작 국면일 때만 붙는다.** 서버도 같은 판정을 하고 아니면 수립을 거절한다
   * (FR-342) — 화면이 붙지 않는 것에 의존하지 않는 것이 그 요구의 요점이므로, 여기서
   * 거는 조건은 헛된 접속을 줄이기 위한 것이지 안전장치가 아니다.
   *
   * 국면이 바뀌면 붙였다 끊는다. 이 효과가 `view.state` 에 의존하는 이유다.
   */
  const controlPhase = CONTROL_PHASE_STATES.has(view.state);

  useEffect(() => {
    if (!controlPhase) {
      control.current?.close();
      control.current = null;
      setControlOpen(false);
      return;
    }
    const channel = connectControlChannel(sessionId, {
      onState: (state, reason) => {
        setControlOpen(state === "open");
        // **사유 없이 끊긴 것으로 두지 않는다** (SC-516). 서버가 닫을 때 사유를 싣는다.
        if (reason !== null) setControlNotice(reason);
      },
      onRejected: (reason) => setControlNotice(reason),
    });
    control.current = channel;
    return () => {
      channel.close();
      control.current = null;
      setControlOpen(false);
    };
  }, [sessionId, controlPhase]);

  /**
   * 이동 사건의 전송량 억제 (FR-336).
   *
   * 마우스 이동은 초당 수십 건이다. 전부 보내면 채널이 이동으로 가득 차고 그 뒤의 클릭이
   * 밀린다. **마지막 위치는 반드시 보낸다** — 마우스 올리기로 열리는 메뉴는 포인터가
   * 머무는 위치로 판정되므로, 마지막 이동을 버리면 메뉴가 열리지 않는다.
   */
  const moveThrottle = useRef(createMoveThrottle());

  const sendInput = useCallback((event: MirrorInputEvent) => {
    const channel = control.current;
    if (channel === null) return;
    if (event.kind === "pointer.move") {
      const now = Date.now();
      const due = moveThrottle.current.offer(event, now);
      if (due !== null) channel.send(due);
      return;
    }
    // 이동이 아닌 사건 앞에서는 **미뤄 둔 이동을 먼저 흘린다.** 순서가 뒤집히면 클릭이
    // 포인터가 아직 도착하지 않은 자리에서 일어난다.
    const pending = moveThrottle.current.flush(Date.now());
    if (pending !== null) channel.send(pending);
    channel.send(event);
  }, []);

  /**
   * 브라우저 요구에 답한다 (FR-337·FR-338).
   *
   * **파일을 먼저 올리고 식별자를 보낸다** (research R6). 조작 채널이 큰 페이로드에
   * 막히면 FR-336 이 깨지므로 파일은 REST 를 탄다. 업로드 응답을 받은 **뒤에** 응답을
   * 보내는 순서가 곧 파일 지정과 그 다음 조작의 순서 보장이다.
   */
  const answerPrompt = useCallback(
    (answer: { accept: boolean; text?: string; files?: File[] }) => {
      const current = prompt;
      if (current === null) return;
      void (async () => {
        try {
          const ids: string[] = [];
          for (const file of answer.files ?? []) {
            const uploaded = await sessions.uploadFile(sessionId, file);
            ids.push(uploaded.file_id);
          }
          await sessions.answerPrompt(sessionId, current.promptId, {
            accept: answer.accept,
            text: answer.text,
            file_ids: ids,
          });
          setPrompt(null);
        } catch (exc) {
          // **조용히 실패하지 않는다** (FR-339 · SC-516). 상한 초과 거절도 여기로 온다.
          const failure = describeError(exc);
          setControlNotice(failure.message);
          /*
            2026-09-09 — **끝난 요구의 패널은 걷는다.**

            이전에는 어떤 실패에서도 `prompt` 를 그대로 뒀다. 상한 초과(`UPLOAD_REJECTED`)
            에서는 그것이 맞다 — 사용자가 작은 파일로 다시 고를 수 있어야 한다. 그러나
            **이미 끝난 요구**(`PROMPT_NOT_FOUND`)에서는 응답할 대상이 없으므로 패널이
            영구히 남고, 그 패널이 미러 자리를 계속 잠식한다 (사용자 보고: 「파일 업로드
            후에 미러 화면이 작아지는 버그」의 한 경로).

            판정은 서버가 준 코드로 한다 — 문구로 판정하면 문구를 고칠 때 조용히 갈린다.
          */
          if (failure.code === "PROMPT_NOT_FOUND") setPrompt(null);
        }
      })();
    },
    [prompt, sessionId],
  );

  /**
   * 실제 창으로 전환한다 (FR-349·FR-353 · US5).
   *
   * **사용자가 누를 때만 일어난다.** 제품이 상황을 판단해 자동으로 창을 열지 않는다.
   */
  const useWindow = useCallback(() => {
    void sessions
      .setControlSurface(sessionId, "window")
      .then((next) => setSurface(next.surface))
      .catch((exc) => setControlNotice(describeError(exc).message));
  }, [sessionId]);

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
    /*
      **판정 순서가 바뀌었다** (2026-09-09 사용자 보고 — 「다시 실행하는 스텝이면 상태
      표기가 업데이트 되어야함」).

      「지금 돌고 있다」가 **맨 위**다. 이전에는 `progress` → `restored` → `running` 순서
      였고, 다시 도는 Step 은 앞의 둘에 지난 실행의 결말을 갖고 있으므로 `running` 에
      닿지 못했다. 사용자가 본 것은 「다시 돌리는데 여전히 통과라고 적힌 행」이다.

      지금 돌고 있다는 것은 **관측된 사실**이고 지난 결말은 **기록**이다. 사실이 기록을
      이긴다 — 그 순서가 어긋나면 화면이 지난 실행을 현재로 말한다 (005 U-20 과 같은 형태).
    */
    if (runningIndex === index) return "running";
    const recorded = progress[step.id]?.outcome;
    if (recorded !== undefined) return recorded;
    /*
      이번 실행이 이 자리를 지나갔거나 아직 닿지 않았으면 **서버 기록을 쓰지 않는다.**
      그 기록은 지난 실행의 것이다 (`staleResults` 의 주석).
    */
    if (staleFromIndex !== null && index >= staleFromIndex) {
      return authoringPhase ? "recorded" : "pending";
    }
    const fromView = restored.get(step.id)?.outcome;
    if (fromView !== undefined && fromView !== "not_run") return fromView;
    return authoringPhase ? "recorded" : "pending";
  };
  const durationOf = (step: Step) => {
    /*
      **이번 실행이 실제로 잰 값이 먼저다.** `step_finished` 가 넣은 것이며, 그 자리가
      가려질 대상인지와 무관하게 참이다 — 방금 잰 값을 가리면 행이 결말만 있고 시간이
      없는 반쪽 상태가 된다.
    */
    const measured = durations.current[step.id];
    if (measured !== undefined) return measured;
    // 결말과 같은 규칙 — 지난 실행의 소요 시간을 이번 실행의 것으로 보여 주지 않는다.
    const index = view.steps.findIndex((s) => s.id === step.id);
    if (staleFromIndex !== null && index >= staleFromIndex) return undefined;
    return restored.get(step.id)?.duration_ms;
  };

  /*
    010 — 미러 조작의 권한표 판정.

    `SessionWorkbench` 가 같은 표를 지나 자기 사실로 계산하지만, `MirrorView` 는 그
    컴포넌트 **밖에서** 그려져 props 로 들어간다. 그래서 여기서도 한 번 계산한다 —
    같은 함수·같은 사실을 지나므로 두 값이 갈릴 수 없다 (FR-316).
  */
  const mirrorPhaseOfSession = phaseOfSession(view);
  const mirrorFacts: CapabilityFacts = {
    mirrorFrameSeen: frame !== null && geometry !== null,
    mirrorLive: mirrorLive && mirrorStopped === null,
    controlChannelOpen: controlOpen,
    controlSurfaceIsMirror: surface === "mirror",
    sessionLost: lost !== null,
    liveBrowser: hasLiveBrowser(view) && lost === null,
  };
  const mirrorCaps = capabilitiesFor(mirrorPhaseOfSession, mirrorFacts);

  /**
   * 실제 창으로 갈 수 없으면 **누르기 전에** 잠근다 (010 FR-351 · FR-234).
   *
   * **문구는 서버가 준다.** 그 판정은 서버만 할 수 있고(운영체제·표시 서버의 사정,
   * 그리고 이 브라우저를 창 없이 띄웠는지), 화면이 같은 뜻의 문장을 따로 가지면 서버가
   * 거절할 때 쓰는 문장과 갈린다 — `wording.ts` 의 O13 옆 주석이 남긴 결정이다.
   * 그 결정을 지키면서 FR-234 를 채우는 방법이 **서버가 문장을 주는 것**이다.
   *
   * 이것이 없던 동안: 창 없이 띄운 세션에서도 버튼이 눌렸고, 서버는 「옮겼다」고 답한
   * 뒤 미러의 조작 통로를 닫았다. 창은 뜨지 않아 조작할 곳이 하나도 남지 않았다
   * (사용자 보고 2026-09-09).
   */
  const useWindowCapability = narrowByWindowAvailability(
    mirrorCaps["mirror.useWindow"],
    view.window_unavailable_reason ?? null,
  );

  const mirror = (
    <>
      {/*
        010 FR-338·FR-339 — 브라우저 요구를 **미러 바로 위에** 둔다. 그 요구는 미러가
        보여 주지 못하는 것에 대한 것이므로, 미러를 보던 눈이 곧바로 닿는 자리가 맞다.
      */}
      <BrowserPromptPanel
        prompt={prompt}
        onAnswer={answerPrompt}
        onUseWindow={useWindow}
        canUseWindow={useWindowCapability.kind === "enabled"}
      />
      <MirrorView
      frame={frame}
      phase={mirrorPhase}
      stoppedReason={mirrorStopped}
      degradedReason={mirrorDegraded}
      tabIndex={mirrorTab}
      control={mirrorCaps["mirror.control"]}
      useWindowCapability={useWindowCapability}
      surface={surface}
      geometry={geometry}
      onInput={sendInput}
      onBlockedAttempt={setControlNotice}
      onUseWindow={useWindow}
      />
    </>
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

  /**
   * 이 세션을 버리고 다시 실행한다. 같은 테스트에 세션이 둘일 수는 없다 (FR-043).
   *
   * ## 2026-09-09 — **확인 없이 세션을 버리던 경로였다** (사용자 보고)
   *
   * 사용자가 보고한 것: 「처음부터 실행을 누르니 새로운 녹화가 사라지고 기존 스텝으로
   * 변경됨」. 경로는 정확히 이 함수였다 — `discard` 로 세션을 버리면 세션이 들고 있던
   * 기록이 함께 사라지고, `onRerun` 이 여는 새 세션은 **저장된 정의**를 재생한다
   * (`App.startRun`). 그래서 화면이 기존 Step 으로 바뀐다.
   *
   * 같은 파일의 `leave()` 는 이미 같은 상황에서 확인을 받는다 (DR-014). 빠져 있던 것은
   * 이 경로 하나였고, 그것이 「어느 버튼이 무엇을 버리는지」를 사용자가 알 수 없게 했다.
   *
   * **자동 저장하지 않는다.** 저장은 이름을 요구하는 별개의 명령이고, 제품이 대신
   * 결정하지 않는다 (`sessions.py` 의 `has_unsaved_changes` 주석과 같은 판단).
   */
  const rerun = (fromStepIndex?: number) => {
    if (testId === null || onRerun === undefined) return;
    if (view.has_unsaved_changes && view.steps.length > 0) {
      setConfirmingRerun({ fromStepIndex: fromStepIndex ?? null });
      return;
    }
    runRerun(fromStepIndex);
  };

  /** 확인을 마친 뒤의 실제 실행. 확인을 거치지 않는 경로는 위 `rerun` 뿐이다. */
  const runRerun = (fromStepIndex?: number) => {
    if (testId === null || onRerun === undefined) return;
    setConfirmingRerun(null);
    setBusy(true);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(() => onRerun(testId, fromStepIndex));
  };

  /** 저장한 뒤 그대로 다시 실행한다 — 확인 창의 주 선택 (2026-09-09). */
  const saveThenRerun = (fromStepIndex?: number) => {
    setBusy(true);
    void sessions
      .save(sessionId, effectiveSaveName.trim(), view.test_id === null ? saveGroup : null)
      .then(() => {
        setError(null);
        setNotice(null);
        runRerun(fromStepIndex);
      })
      .catch((exc: unknown) => {
        // 저장이 실패하면 **실행하지 않는다.** 버리는 쪽으로 넘어가면 유실이 된다.
        setConfirmingRerun(null);
        setError(describeError(exc));
      })
      .finally(() => setBusy(false));
  };

  /**
   * 고치러 간다 — **세션을 버리고, 그 자리 앞까지 다시 세운다** (2026-09-09 사용자 결정).
   *
   * ## 왜 「그 자리 앞까지 다시 세운다」인가
   *
   * 첫 판은 편집 화면으로만 보냈다. 사용자가 그 결과를 곧바로 지적했다: 「실행과정에서
   * 에러가 발생하여, 스텝을 편집 할 경우, 직전 스텝까지의 세션을 제공하던지 해서, 이어서
   * 편집이 가능해야함」. 옳은 지적이다 — 실패한 Step 을 고치는 일은 대개 **요소를 다시
   * 집는 것**이고, 그것은 살아 있는 페이지에서만 된다 (헌법 원칙 IV).
   *
   * 그 장치는 이미 있다. 009 FR-291 의 「브라우저 열어 Step nn 앞에서 멈추기」가 지정한
   * 자리 전까지 재생한 뒤 멈추고 **직접 조작 기록을 켠다** (FR-295). 없던 것은 실패한
   * 실행에서 거기로 가는 길뿐이었다.
   *
   * **세션을 먼저 버린다.** 테스트당 세션은 하나다 (FR-043) — 버리지 않으면 새 세션
   * 생성이 거절된다.
   *
   * **저장 여부는 여기서 묻지 않는다.** 저장되지 않은 상태에서는 조작이 이미 잠겨 있고
   * (`editStepCapability`), 새 세션은 **저장된 정의**를 재생하므로 저장이 전제다.
   */
  const editStep = (stepId: string | null, stepIndex: number) => {
    if (testId === null || onEditStep === undefined) return;
    setBusy(true);
    void sessions
      .discard(sessionId)
      .catch(() => undefined)
      .finally(() => onEditStep(testId, stepId, stepIndex));
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
      .save(sessionId, effectiveSaveName.trim(), view.test_id === null ? saveGroup : null)
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
        /*
          010 SC-516 — **조작이 전달되지 않은 사유를 화면에 남긴다.**

          서버가 거절했거나 화면이 조작을 받지 않는 상태에서 사용자가 시도했다. 조용히
          아무 일도 일어나지 않으면 사용자는 제품이 고장난 것으로 읽는다. `notes` 에
          싣는 이유는 그 자리가 이미 「사용자 조작 없이 알려야 하는 사실」의 집이기
          때문이다 — 새 자리를 만들면 같은 종류가 두 곳에 흩어진다.
        */
        notes={controlNotice === null ? notes : [...notes, controlNotice]}
        lost={lost}
        offline={showOffline}
        mirror={mirror}
        tabs={tabStrip}
        /*
          `tabs` 만 지키고 `tabs.tabs` 를 지키지 않으면, 탭 응답이 기대한 형이 아닐 때
          화면이 통째로 죽는다 — 이 저장소가 두 번 겪은 형태다 (baseline.md 의 미처리 오류
          3건 중 「`run-from` 이 `{ok: true}` 로 떨어졌다」). 011 의 검사가 그것을 다시
          드러냈으므로 여기서 닫는다.
        */
        currentUrl={tabs?.tabs?.[mirrorTab]?.url ?? ""}
        mirroredTab={mirrorTab}
        focusedStepId={selectedStepId}
        detailOpen={inspecting}
        repickWaiting={repickWaiting}
        saveName={effectiveSaveName}
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
        onSaveNameChange={setNameOverride}
        saveGroup={saveGroup}
        onSaveGroupChange={setSaveGroup}
        groupOptions={groupOptions}
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
        /*
          009 FR-290 — 직접 입력 삽입. **`at` 을 넘기지 않는다.**

          넘기지 않으면 서버가 일시정지 위치에 넣는다(`step_edits._clamp`). 화면이 인덱스를
          계산해 보내면 그 사이 러너가 전진한 경우 다른 자리에 들어간다 — `run.fromHere` 가
          인덱스를 넘기지 않는 것과 같은 근거다 (005 T129).
        */
        onInsertManual={(spec) => void edit(() => sessions.insertStepManual(sessionId, spec))}
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
        /*
          011 FR-382·FR-388 — **한 번의 요청으로 지운다.** `deleteStep` 을 반복하면
          중간에 끊길 때 부분 적용이 남는다.

          지운 뒤 선택을 비운다 (data-model §4-1) — 지워진 id 가 남아 있으면 다음 삭제가
          없는 것을 지우려 한다.
        */
        onDeleteSteps={(stepIds) => {
          void edit(() => sessions.deleteSteps(sessionId, stepIds)).then(() =>
            setDeleteSelection([]),
          );
        }}
        deleteSelection={deleteSelection}
        onToggleDeleteTarget={(stepId) =>
          setDeleteSelection((prev) =>
            prev.includes(stepId) ? prev.filter((id) => id !== stepId) : [...prev, stepId],
          )
        }
        /*
          전부 고르기 / 전부 풀기 (FR-380c). **지금 목록을 기준으로 판정한다** — 고른 것이
          목록 전체와 같으면 풀고, 아니면 전부 고른다.
        */
        onToggleAllDeleteTargets={() =>
          setDeleteSelection((prev) =>
            prev.length === view.steps.length ? [] : view.steps.map((s) => s.id),
          )
        }
        onApplyReorder={(order) => void edit(() => sessions.reorderSteps(sessionId, order))}
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
        onEditStep={editStep}
        /*
          2026-09-10 — 답변을 함께 나른다. **막힘 표시를 먼저 지운다**는 규칙은 그대로다:
          지우지 않으면 AI 가 다시 도는 동안에도 「막혔습니다」가 화면에 남는다.
        */
        onChooseBlocked={(choice, answer) => {
          setAiBlocked(null);
          void act(() => sessions.aiChoice(sessionId, choice as AiChoice, answer));
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
          /* 011 UC-011-5 — 이름이 이미 있으면 묻지 않는다 */
          askName={!testHasName}
          saveName={effectiveSaveName}
          busy={busy}
          onSaveNameChange={setNameOverride}
          onSave={saveAndLeave}
          onDiscard={leaveConfirmed}
          onCancel={() => setConfirmingLeave(false)}
        />
      )}
      {confirmingClose && (
        <CloseConfirm onCancel={() => setConfirmingClose(false)} onConfirm={closeConfirmed} />
      )}
      {confirmingRerun !== null && (
        <RerunConfirm
          stepCount={view.steps.length}
          fromStepIndex={confirmingRerun.fromStepIndex}
          saveName={effectiveSaveName}
          busy={busy}
          onSaveAndRun={() => saveThenRerun(confirmingRerun.fromStepIndex ?? undefined)}
          onDiscardAndRun={() => runRerun(confirmingRerun.fromStepIndex ?? undefined)}
          onCancel={() => setConfirmingRerun(null)}
        />
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
      className="modal-scrim"
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 30,
      }}
    >
      <div className="modal" style={{ width: 520, padding: 24 }}>
        {children}
      </div>
    </div>
  );
}

function CloseConfirm({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  return (
    <Modal label="실행 화면 닫기 확인">
      <div className="title">실행 화면을 닫습니다</div>
      <p className="note">결과는 목록의 「결과 보기」에서 다시 볼 수 있습니다.</p>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
        <button className="secondary" onClick={onCancel}>
          돌아가기
        </button>
        <button onClick={onConfirm}>닫기</button>
      </div>
    </Modal>
  );
}

/**
 * 「처음부터 실행」이 저장하지 않은 기록을 만났다 (2026-09-09 · 사용자 보고).
 *
 * **선택이 셋이고, 무엇을 버리는지 문장이 말한다.** `LeaveConfirm` 과 같은 문법을 쓴다 —
 * 두 창이 다른 모양이면 사용자는 같은 종류의 결정을 두 번 배운다.
 *
 * 주 선택은 **저장하고 실행**이다. 유실이 일어나는 쪽을 기본으로 두지 않는다.
 */
function RerunConfirm({
  stepCount,
  fromStepIndex,
  saveName,
  busy,
  onSaveAndRun,
  onDiscardAndRun,
  onCancel,
}: {
  stepCount: number;
  /** `null` 이면 처음부터. 값이 있으면 그 자리부터 */
  fromStepIndex: number | null;
  /**
   * 저장에 실릴 이름. **묻지 않는다** (011 UC-011-5 · FR-364).
   *
   * 이 확인은 **저장된 테스트에서만 열린다** — `rerun()` 이 `testId === null` 이면 먼저
   * 돌아간다. 즉 여기 닿았다는 것은 이름이 이미 있다는 뜻이다.
   *
   * 011 이전에는 그런데도 이름칸을 그렸다. 사용자는 「이름을 바꾸려는 것이 아닌데 왜
   * 묻는가」를 판단해야 했고, 잘못 채우면 이름이 바뀌었다 (사용자 보고 2). 011 이
   * 조건부로 만들자 그 가지가 **한 번도 참이 되지 않는다**는 것이 드러나 아예 걷었다.
   */
  saveName: string;
  busy: boolean;
  onSaveAndRun: () => void;
  onDiscardAndRun: () => void;
  onCancel: () => void;
}) {
  const scope = fromStepIndex === null ? "처음부터" : `${stepLabel(fromStepIndex)}부터`;
  return (
    <Modal label="저장하지 않고 다시 실행 확인">
      <div className="title">저장하지 않은 기록이 있습니다</div>
      <p className="note">
        기록된 Step {stepCount}개 중 저장하지 않은 변경이 있습니다. {scope} 실행하면 지금
        세션을 버리고 <strong>저장된 정의</strong>를 재생하므로, 저장하지 않은 기록은
        사라집니다.
      </p>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
        <button className="secondary" onClick={onCancel}>
          돌아가기
        </button>
        <button className="danger" disabled={busy} onClick={onDiscardAndRun}>
          버리고 실행
        </button>
        <button disabled={busy || saveName.trim() === ""} onClick={onSaveAndRun}>
          저장하고 실행
        </button>
      </div>
    </Modal>
  );
}

function LeaveConfirm({
  stepCount,
  askName,
  saveName,
  busy,
  onSaveNameChange,
  onSave,
  onDiscard,
  onCancel,
}: {
  stepCount: number;
  /** 이름을 물어야 하는가 (011 UC-011-5 · FR-364). 이름이 있으면 거짓 */
  askName: boolean;
  saveName: string;
  busy: boolean;
  onSaveNameChange: (v: string) => void;
  onSave: () => void;
  onDiscard: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal label="저장하지 않고 나가기 확인">
      <div className="title">저장하지 않은 기록이 있습니다</div>
      <p className="note">
        기록된 Step {stepCount}개가 있습니다. 저장하지 않고 나가면 사라집니다.
      </p>
      {askName && (
        <>
          <label htmlFor="leave-save-name">테스트 이름</label>
          <input
            id="leave-save-name"
            value={saveName}
            autoFocus
            onChange={(e) => onSaveNameChange(e.target.value)}
            placeholder="프로젝트 생성"
          />
        </>
      )}
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
