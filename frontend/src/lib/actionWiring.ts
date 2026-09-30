/**
 * 조작 하나를 **화면이 할 수 있는 일**에 잇는다. 027 FR-001~FR-007.
 *
 * ## 왜 이 모듈이 있는가
 *
 * 007 이 화면의 껍데기를 통합하면서 「소유와 표시를 나눈다」까지 했다. 그러나 **소유하는
 * 쪽(어댑터 3개)을 합치지 않았고**, 그래서 같은 조작이 두 벌로 구현됐다 — 「Step 을
 * 지운다」가 `SessionScreen` 과 `EditView` 에 각각 있었다.
 *
 * 한쪽만 고치면 조용히 갈린다. 타입 검사도 조작표도 그것을 잡지 못했고, 실제로 사고가
 * 났다 (026: 「AI 에게 고쳐 달라기」가 한 화면에만 붙어 사용자가 찾지 못했다).
 *
 * ## 이 모듈이 **하지 않는** 것 (contracts/wiring-contract.md §2)
 *
 * | 하지 않는다 | 왜 |
 * |---|---|
 * | 국면을 인자로 받는다 | 판정이 조작표 밖에 하나 더 생긴다 (011 이 막은 것) |
 * | 「이 조작은 이 국면에서만」을 안다 | 같은 이유 |
 * | 화면 상태를 직접 읽는다 | 소유가 어댑터에 있다는 007 의 결정을 깬다 |
 * | 없는 능력을 만들어 낸다 | 없는 것은 없는 채로 둔다 — 조작표가 이미 「해당 없음」이라 말한다 |
 *
 * **이 목록이 깨지면 이 증분은 실패다** (research R7). 배선이 국면을 알아야만 동작하거나
 * 능력 묶음이 화면마다 다른 모양이 되기 시작하면, 층만 하나 더한 것이므로 되돌린다.
 *
 * ## 세 요구를 동시에 만족시키는 방법
 *
 * | 요구 | 이 모양이 만족시키는 방식 |
 * |---|---|
 * | FR-003 해당 없으면 제공 안 해도 됨 | 능력이 **선택적**이다. 없으면 그 조작이 이어지지 않는다 |
 * | FR-004 화면마다 다른 일 | 능력의 **구현**이 화면마다 다르다 (「저장」이 그렇다) |
 * | FR-005 화면마다 다른 선행 확인 | 능력 구현 **안에** 있다 (「먼저 저장하고 열기」) |
 *
 * ## 능력은 「지금 고른 것」을 안다
 *
 * `deleteStep()` 이 인자를 받지 않는 것이 요점이다. **어느 Step 인지는 화면이 알고**,
 * 배선은 알 필요가 없다. 인자를 받게 하면 배선이 화면 상태를 읽어야 하고, 그것이 위
 * 표의 셋째 줄이다.
 *
 * 예외는 **조작 자체가 정하는 값**이다 — `moveStep(dir)` 의 방향은 화면 상태가 아니라
 * 「위로인가 아래로인가」이며, 그것은 조작 식별자가 말한다.
 */
import type { ActionId } from "./actions";

/**
 * 화면이 제공하는 「내가 할 수 있는 일」. **전부 선택적이다.**
 *
 * 주지 않는 것은 그 국면에 그 일이 없다는 뜻이며, 조작표가 이미 「해당 없음」으로
 * 말하고 있다 (FR-003).
 */
export interface ScreenCapabilities {
  /* ─── Step 하나에 대한 편집 ─────────────────────────────────────────── */
  /** 지금 고른 Step 을 지운다. **어느 것인지는 화면이 안다** */
  deleteStep?: () => void;
  /** 지금 고른 Step 을 한 칸 옮긴다 */
  moveStep?: (direction: -1 | 1) => void;
  /** 지금 고른 Step 의 상세·편집면을 연다 */
  openStepDetail?: () => void;

  /* ─── 여러 Step · 삽입 ──────────────────────────────────────────────── */
  /** 체크한 Step 들을 지운다. **확인 대화는 화면의 사정이다** */
  deleteSelected?: () => void;
  /** 고른 Step 뒤 전부를 지운다 */
  deleteAfter?: () => void;
  /** 손으로 Step 을 넣는 입력면을 연다 */
  insertManual?: () => void;
  /** 검증을 더하는 입력면을 연다 */
  addAssertion?: () => void;

  /* ─── 화면을 옮기는 일 — **하는 일이 화면마다 다르다** (FR-004) ───── */
  /** 처음부터 실행 */
  runAll?: () => void;
  /** 고른 Step 부터 실행 */
  runFrom?: () => void;
  /** 결과 화면으로 */
  showResult?: () => void;
  /** 뒤로 */
  goBack?: () => void;

  /* ─── 선행 확인이 화면마다 다른 것 (FR-005) ────────────────────────── */
  /** 저장. 편집 화면은 정의를 디스크에 쓰고 세션은 세션의 저장이다 */
  save?: () => void;
  /** 녹화 시작. 편집 화면은 먼저 저장할 수 있다 */
  recordStart?: () => void;
  /** 자연어로 Step 추가 */
  addNaturalLanguage?: () => void;
}

/** 능력 이름 하나. 검사가 이 목록을 쓴다 */
export type CapabilityName = keyof ScreenCapabilities;

/**
 * 조작 하나가 어떤 능력을 부르는가.
 *
 * **여기 없는 조작은 기존 경로로 떨어진다** (`fallback`). 그것이 이행 중의 공존을
 * 가능하게 한다 (FR-022 · contracts §5).
 *
 * 값이 함수인 이유는 `moveStep` 처럼 **조작이 인자를 정하는** 경우가 있기 때문이다.
 * 그 인자는 화면 상태가 아니라 조작 식별자가 말하는 것이다.
 */
const ACTION_WIRING: Partial<
  Record<ActionId, (caps: ScreenCapabilities) => (() => void) | undefined>
> = {
  "step.delete": (c) => c.deleteStep,
  "step.moveUp": (c) => (c.moveStep ? () => c.moveStep?.(-1) : undefined),
  "step.moveDown": (c) => (c.moveStep ? () => c.moveStep?.(1) : undefined),
  "step.update": (c) => c.openStepDetail,
  "step.deleteSelected": (c) => c.deleteSelected,
  "step.deleteAfter": (c) => c.deleteAfter,
  "step.insertManual": (c) => c.insertManual,
  "step.addAssertion": (c) => c.addAssertion,
  "run.all": (c) => c.runAll,
  "run.from": (c) => c.runFrom,
  "result.show": (c) => c.showResult,
  "nav.back": (c) => c.goBack,
  save: (c) => c.save,
  "step.recordStart": (c) => c.recordStart,
  "step.addNaturalLanguage": (c) => c.addNaturalLanguage,
};

/** 이 모듈이 잇는 조작 전부. 검사가 쓴다 */
export const WIRED_ACTION_IDS = Object.keys(ACTION_WIRING) as ActionId[];

export interface ActionRunner {
  /** 조작을 실행한다. 이어져 있지 않으면 `fallback` 으로 간다 */
  run: (action: ActionId) => void;
  /**
   * **이 화면이 실제로 이어 둔 조작들.**
   *
   * 화면이 손으로 적지 않는다 — 능력 묶음에서 도출한다. 화면은 이것을
   * `data-wired-actions` 로 내보내고, 검사가 조작표와 대조한다 (FR-014·FR-016).
   */
  wired: ActionId[];
}

/**
 * 능력 묶음을 받아 `runAction` 을 만든다.
 *
 * `fallback` 은 **아직 옮기지 않은 조작**을 기존 `switch` 로 보내는 통로다. 이행이
 * 끝나면 쓰이지 않으며, 그 사실을 검사가 확인한다 (contracts §5).
 */
export function makeRunAction(
  caps: ScreenCapabilities,
  fallback?: (action: ActionId) => void,
): ActionRunner {
  const run = (action: ActionId) => {
    const handler = ACTION_WIRING[action]?.(caps);
    if (handler !== undefined) {
      handler();
      return;
    }
    fallback?.(action);
  };
  return { run, wired: wiredActionsOf(caps) };
}

/**
 * 그 능력 묶음으로 실제로 이어지는 조작들.
 *
 * **도출한다.** 화면이 목록을 적으면 그것이 곧 낡고, 낡은 목록을 검사가 믿는다
 * (research R2).
 */
export function wiredActionsOf(caps: ScreenCapabilities): ActionId[] {
  return WIRED_ACTION_IDS.filter((id) => ACTION_WIRING[id]?.(caps) !== undefined);
}

/** `data-wired-actions` 속성 값. 화면 뿌리에 붙인다 */
export function wiredAttribute(wired: ActionId[]): string {
  return wired.join(",");
}
