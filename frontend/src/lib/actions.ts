/**
 * 조작 식별자 33개 (007 T008 · contracts/ui-contract.md §2).
 *
 * **이 목록이 FR-247 의 검사 대상이다** — 통합으로 사라지는 조작이 있어서는 안 된다.
 * 지금 조작은 7개 화면의 props 로 흩어져 있고, 같은 일이 다른 이름으로 여러 곳에 있다.
 * Step 지목이 `onSelectStep`(3곳) · `onEditStep`(2곳) · 내부 상태(1곳)로 셋이었다.
 *
 * 타입으로 고정하는 이유는 오타를 컴파일에서 잡기 위해서다. 권한표의 키와 화면이 묻는
 * 키가 문자열로 갈리면, 화면은 "없는 조작" 을 물어 `undefined` 를 받고 조용히 아무것도
 * 그리지 않는다 — 감춰진 조작이 되고 FR-234 위반이다.
 */

/** 실행·세션 (10) */
export const RUN_ACTIONS = [
  /** 처음부터 실행 (새 세션) */
  "run.all",
  /** Step nn 부터 실행 (새 세션) */
  "run.from",
  /** Step nn 부터 이어 실행 (열린 세션 안에서) */
  "run.fromHere",
  /** 일시정지 */
  "run.pause",
  /** 계속하기 / AI 에게 돌려주기 */
  "run.resume",
  /** 실패 건너뛰고 계속 */
  "run.resumeSkipFailure",
  /** 중지 / 닫기 / 나가기 */
  "run.stop",
  /** 실행 속도 */
  "run.pacing",
  /** 브라우저 열어 Step nn 에서 멈추기 */
  "browser.openAt",
  /** 실행 중인 세션 보기 */
  "session.open",
] as const;

/** Step 작성 (4) */
export const AUTHORING_ACTIONS = [
  "step.recordStart",
  "step.recordStop",
  "step.addNaturalLanguage",
  "step.addAssertion",
] as const;

/** Step 편집 (6) */
export const STEP_ACTIONS = [
  "step.select",
  "step.update",
  "step.markSensitive",
  "step.repick",
  "step.delete",
  "step.reorder",
] as const;

/** 테스트 속성·저장 (5) */
export const TEST_ACTIONS = [
  "test.rename",
  "test.setStartUrl",
  "save",
  "save.overwriteStale",
  "edits.revert",
] as const;

/** AI (3) */
export const AI_ACTIONS = ["ai.compose", "ai.start", "ai.chooseBlocked"] as const;

/** 결과·이동 (5) */
export const NAV_ACTIONS = [
  "artifact.select",
  "result.show",
  "nav.editStep",
  "nav.back",
  "tab.select",
] as const;

export const ACTION_IDS = [
  ...RUN_ACTIONS,
  ...AUTHORING_ACTIONS,
  ...STEP_ACTIONS,
  ...TEST_ACTIONS,
  ...AI_ACTIONS,
  ...NAV_ACTIONS,
] as const;

export type ActionId = (typeof ACTION_IDS)[number];

/**
 * 조작이 속한 묶음. 화면이 조작을 어느 자리에 놓을지 정할 때 쓴다.
 *
 * `run` 계열은 국면 띠에, `step` 계열은 Step 목록·상세에, `nav` 계열은 헤더에 산다.
 * 자리를 묶음으로 정하면 "같은 자리의 같은 조작" (FR-235)이 배치 규칙으로 보장된다.
 */
export type ActionGroup = "run" | "authoring" | "step" | "test" | "ai" | "nav";

export const ACTION_GROUP: Record<ActionId, ActionGroup> = {
  ...Object.fromEntries(RUN_ACTIONS.map((a) => [a, "run" as ActionGroup])),
  ...Object.fromEntries(AUTHORING_ACTIONS.map((a) => [a, "authoring" as ActionGroup])),
  ...Object.fromEntries(STEP_ACTIONS.map((a) => [a, "step" as ActionGroup])),
  ...Object.fromEntries(TEST_ACTIONS.map((a) => [a, "test" as ActionGroup])),
  ...Object.fromEntries(AI_ACTIONS.map((a) => [a, "ai" as ActionGroup])),
  ...Object.fromEntries(NAV_ACTIONS.map((a) => [a, "nav" as ActionGroup])),
} as Record<ActionId, ActionGroup>;
