/**
 * 국면별 `WorkbenchModel` 픽스처 (007 T004 의 나머지 절반).
 *
 * `workbench.ts` 는 **도메인** 픽스처(`SessionView`·`DefinitionView`·`RunResultView`)를
 * 만들고, 이 파일은 **표시 모델**을 만든다. 둘을 가른 이유는 쓰는 곳이 다르기 때문이다 —
 * 어댑터를 검사할 때는 도메인 픽스처를, 표시 컴포넌트를 검사할 때는 표시 모델을 쓴다.
 *
 * 규칙은 같다 — **팩토리는 항상 온전한 객체를 만든다.**
 */

import { capabilitiesFor } from "../../src/lib/capabilities";
import type { Phase } from "../../src/lib/phase";
import { PHASE_LABEL } from "../../src/lib/wording";
import type {
  StepOutcome,
  WorkbenchModel,
  WorkbenchStep,
} from "../../src/components/workbench/model";
import { clickStep, fillStep } from "./workbench";

/** 조건을 모두 참으로 둔 사실 — ◐ 셀이 ● 가 되는 최대 상태. */
export const ALL_FACTS = {
  sessionFinished: true,
  liveBrowser: true,
  hasFailedStep: true,
  pacingAppliesInTakeover: true,
  blockingSession: true,
  recording: true,
  definitionEditable: true,
  hasSteps: true,
  hasPendingEdits: true,
  staleConflict: true,
  aiBlocked: true,
  resultViewable: true,
  hasResult: true,
};

export function workbenchStep(overrides: Partial<WorkbenchStep> = {}): WorkbenchStep {
  return {
    id: "st-1",
    index: 0,
    step: clickStep({ id: "st-1" }),
    label: "로그인 버튼 클릭",
    outcome: "pending",
    durationMs: null,
    isPausedHere: false,
    ...overrides,
  };
}

/** 두 개짜리 기본 목록. 두 번째는 값을 가진 Step 이라 값 칸이 검사에 걸린다. */
export function workbenchSteps(outcome: StepOutcome = "pending"): WorkbenchStep[] {
  return [
    workbenchStep({ id: "st-1", index: 0, outcome }),
    workbenchStep({
      id: "st-2",
      index: 1,
      outcome,
      step: fillStep({ id: "st-2" }),
      label: "아이디 입력",
    }),
  ];
}

/** 국면 하나의 온전한 표시 모델. */
export function workbenchModel(
  phase: Phase,
  overrides: Partial<WorkbenchModel> = {},
): WorkbenchModel {
  return {
    phase,
    testId: "TC-001",
    testName: "로그인",
    phaseBar: {
      phaseLabel: PHASE_LABEL[phase],
      phaseTone: "neutral",
      runSummary: null,
      progressLabel: null,
    },
    target: { kind: "empty", reason: "not_started" },
    work: null,
    steps: workbenchSteps(),
    focusedStepId: null,
    detail: null,
    capabilities: capabilitiesFor(phase, ALL_FACTS),
    notices: [],
    authoring: "record",
    pacing: null,
    ...overrides,
  };
}
