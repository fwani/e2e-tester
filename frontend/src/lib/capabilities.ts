/**
 * 국면 × 조작 권한표 (007 T009~T011 · contracts/ui-contract.md §3).
 *
 * > **UC-000 — 표가 정본이다.**
 * > 조작이 어느 국면에서 어떤 상태인지는 이 파일이 정한다. 컴포넌트가 스스로 판단하지
 * > 않는다. 표와 코드가 다르면 코드를 고친다. 단 **현재 쓸 수 있는 조작이 표에서
 * > 「해당 없음」이면 그것은 표의 오류**이며 표를 고친다 (UC-401 · FR-247).
 *
 * **왜 표인가.** 지금은 화면마다 `disabled` 를 스스로 판단한다. 한 화면이 빠뜨리면 그
 * 화면에서만 결함이 나고, 실제로 그랬다 — 실행 요청 중복 방지를 목록 화면만 갖고 있어서
 * 다른 화면에서 연타하면 브라우저 창이 둘 떴다 (005 U-06, 실측 5회 클릭에 201 이 2건).
 *
 * 판정은 두 층이다.
 *
 *   기본 표 (국면 × 조작)  →  런타임 덮어쓰기  →  최종 CapabilityState
 *   아래 PHASE_TABLE            O1~O4
 *
 * 두 층 모두 `capabilityOf()` 한 함수를 지난다. 덮어쓰기를 화면에 흩으면 한 화면이
 * 빠뜨린다.
 */

import { ACTION_IDS, type ActionId } from "./actions";
import type { Phase } from "./phase";
import {
  DISABLED_REASON,
  NOT_APPLICABLE_REASON,
  type DisabledReasonKey,
  type NotApplicableKey,
} from "./wording";

/** 쓸 수 있게 하는 방법. **이 화면에 실제로 있는 조작만** 가리킨다 (006 E-03). */
export interface Remedy {
  action: ActionId;
}

/**
 * 비활성 조작을 **자리에 남기는가, 그리지 않는가** (사용자 결정 · 2026-09-09).
 *
 * ## 왜 축이 하나 늘었나
 *
 * 007~010 은 「비활성 조작은 감추지 않는다」를 예외 없는 규칙으로 삼았다 (FR-234 ·
 * SC-004). 근거는 실측이었다 — 감춘 자리에서 사용자는 자기가 잘못 들어온 줄 알았다.
 *
 * 그 규칙을 한 줄 국면 띠에 **평면으로 펼친 결과**를 사용자가 보고했다: 검토 국면에서
 * 조작 자리 24개 중 14개가 비활성이고, 사유 문구까지 달려 활성 조작과 같은 무게로
 * 놓였다. 「처음부터 실행」이 버튼 하나 + 해소 링크 둘로 **한 띠에 세 번** 나왔다.
 * 사용자가 말한 「누를 수 없는 버튼이 다 보이고, 언제는 눌러지고, 애매함」이 그것이다.
 *
 * ## 규칙을 어떻게 갈랐나
 *
 * 비활성에는 **두 종류**가 있고, 007 은 그 둘을 한 칸에 뭉갰다.
 *
 * - `"hide"` — **이 상태의 조작이 아니다.** 브라우저가 닫혔는데 「계속하기」, 실행이
 *   끝났는데 「일시정지」, 녹화 중인데 「Step 삭제」. 사용자가 지금 이 화면에서 할 수
 *   있는 일이 아니고, 자리에 남겨도 배울 것이 없다. **그리지 않는다.**
 * - `"keep"` — **이 상태의 조작인데 전제가 덜 갖춰졌다.** 이름을 아직 안 썼다, Step 을
 *   아직 안 골랐다, 요청이 도는 중이다. 사용자가 **지금 이 화면에서 곧바로 해소할 수
 *   있다.** 감추면 「저장이 어디 갔지」가 되므로 FR-234 의 근거가 그대로 살아 있다.
 *
 * 판정은 **이유 키가 갖는다** — 조작마다·화면마다 정하면 한 곳이 갈리고, 갈린 자리가
 * 이 파일이 없애려던 결함이다. 표는 `REASON_VISIBILITY` 하나뿐이다.
 */
export type Visibility = "keep" | "hide";

export type CapabilityState =
  /** 쓸 수 있다 */
  | { kind: "enabled" }
  /**
   * 쓸 수 없다.
   *
   * `visibility` 가 `"keep"` 이면 같은 자리에 비활성으로 남기고 이유를 붙인다
   * (FR-234). `"hide"` 면 그리지 않는다 — 이 상태의 조작이 아니라는 뜻이다.
   */
  | { kind: "disabled"; reason: string; remedy: Remedy | null; visibility: Visibility }
  /** 이 국면의 조작이 아니다 — 그리지 않는다. §4-2 의 근거가 있어야 쓸 수 있다 */
  | { kind: "not_applicable"; basis: NotApplicableKey; note: string };

export type CapabilityMap = Record<ActionId, CapabilityState>;

/**
 * 그 조작을 **화면에 그리는가.**
 *
 * 화면·팔레트·행이 각자 `kind` 를 뜯어보면 한 곳이 `visibility` 를 빠뜨린다. 묻는
 * 방법을 하나로 둔다.
 */
export function isShown(state: CapabilityState): boolean {
  if (state.kind === "not_applicable") return false;
  if (state.kind === "disabled") return state.visibility === "keep";
  return true;
}

/* ─── 표의 셀 ──────────────────────────────────────────────────────────────── */

/** ● 가능 */
const ON = { t: "on" } as const;
/** ○ 비활성 — 이유 키와 해소 방법 */
const off = (reason: DisabledReasonKey, remedy?: ActionId) =>
  ({ t: "off", reason, remedy: remedy ?? null }) as const;
/** ◐ 런타임 조건 — 조건 키. 참이면 ●, 거짓이면 그 조건의 이유로 ○ */
const cond = (key: ConditionKey, remedy?: ActionId) =>
  ({ t: "cond", key, remedy: remedy ?? null }) as const;
/** – 해당 없음 — §4-2 의 근거(N1·N2·N3) */
const na = (basis: NotApplicableKey) => ({ t: "na", basis }) as const;

type Cell =
  | typeof ON
  | ReturnType<typeof off>
  | ReturnType<typeof cond>
  | ReturnType<typeof na>;

/* ─── 보임/숨김 (사용자 결정 · 2026-09-09) ─────────────────────────────────── */

/**
 * 이유 키 → 그 이유로 잠긴 조작을 **자리에 남기는가.**
 *
 * 읽는 법: `"keep"` 인 것은 **사용자가 지금 이 화면에서 곧바로 해소할 수 있는** 전제다.
 * 나머지는 「이 상태의 조작이 아니다」이며 그리지 않는다.
 *
 * 새 이유 키를 더하면 컴파일이 여기에 값을 요구한다 — `Record` 로 둔 이유이며, 빠뜨린
 * 키가 조용히 `undefined` 가 되어 「감출지 남길지 모르는 조작」이 되지 않게 한다.
 */
const REASON_VISIBILITY: Record<DisabledReasonKey, Visibility> = {
  /* ─── 016 구간 재녹화 ─── */
  /**
   * **셋은 감추고 둘은 남긴다.** 기준은 「지금 이 화면에서 곧바로 해소할 수 있는
   * 전제인가」다 (2026-09-09 에 이 파일이 좁힌 규칙).
   *
   * `C16`·`C17` 은 **진행 중인 교체가 없다**는 뜻이다. 확정·버리기 버튼이 재녹화가
   * 아닌 모든 화면에 상시로 떠 있을 이유가 없다 — 그것이 검토 국면에서 조작 자리
   * 24개 중 14개가 비활성이던 상태를 만든 종류의 판단이다.
   *
   * `ALREADY_IN_SESSION` 도 같다. 세션 안에서 「AI 로 다시 만들기」는 찾을 일이 없는
   * 조작이고(이미 그 안에 있다), 남기면 모든 일시정지 화면에 잠긴 버튼이 하나 는다.
   */
  C16: "hide",
  C17: "hide",
  ALREADY_IN_SESSION: "hide",
  /**
   * 이 둘은 **남긴다.** 사용자가 지금 곧바로 해소할 수 있고, 감추면 기능의 존재를
   * 알 방법이 없다 (FR-234).
   *
   * - `NEEDS_SESSION` — 「Step 을 골라 브라우저를 그 앞에서 멈추세요」를 가리킨다
   * - `USE_BLOCKED_ANSWER` — 「위의 답변 칸에 알려 주세요」를 가리킨다
   */
  NEEDS_SESSION: "keep",
  USE_BLOCKED_ANSWER: "keep",
  /* ─── 남긴다 — 지금 곧바로 해소할 수 있는 전제 ─── */
  /**
   * 요청이 도는 중인 넷은 **남긴다.** 곧 풀리는 상태이고, 그 사이 버튼이 사라지면
   * 사용자는 조작을 잃은 것으로 읽고 다른 길을 찾는다 — 연타가 그렇게 생겼다 (005 U-06).
   */
  O1: "keep",
  O2: "keep",
  O6: "keep",
  O8: "keep",
  /**
   * 저장의 전제 둘은 **남긴다.** 사용자가 보고한 「녹화하고 저장하는 부분이 명확하지
   * 않다」가 여기다 — 저장 자리가 조건에 따라 사라지면 「저장이 어디 갔지」가 되고,
   * 녹화가 저장되지 않은 채 실행으로 넘어간다.
   */
  C8: "keep",
  C9: "keep",
  NOTHING_TO_SAVE_YET: "keep",
  /** 이름칸은 만들기 국면에도 자리를 갖는다 — 언제 이름을 정하는지 말해 준다 (FR-258a) */
  NAME_ON_SAVE: "keep",
  /** 만들기 국면의 지시문 자리. 고르기 **전에도** 보여야 한다 (FR-234 의 원래 근거) */
  C14: "keep",
  C15: "keep",
  /**
   * 미러의 조작 통로 사정 넷은 **남긴다.** 이 넷의 「자리」는 버튼이 아니라 **미러
   * 자체**이고, `MirrorView` 가 사유를 미러 위에 얹는다 (010 SC-516 — 조작이 전달되지
   * 않은 모든 경우에 사유를 읽을 수 있어야 한다). 숨기면 미러를 클릭했을 때 조용히
   * 아무 일도 일어나지 않는다.
   */
  O10: "keep",
  O11: "keep",
  O12: "keep",
  O13: "keep",

  /* ─── 그리지 않는다 — 이 상태의 조작이 아니다 ─── */
  /** 세션이 열려 있어 새 실행을 걸 수 없다. 그 상태의 조작이 아니다 */
  C1: "hide",
  /** 브라우저가 닫혔다 — 검토 국면에서 「계속하기」·「건너뛰고 계속」이 사라진다 */
  C2: "hide",
  C3: "hide",
  /** 라벨의 근거이지 잠금의 근거가 아니다 (T041). 값은 형식상 둔다 */
  C4: "hide",
  C5: "hide",
  C6: "hide",
  /**
   * C7 — 다른 세션이 그 정의를 잡고 있어 편집할 수 없다. **남긴다.**
   *
   * `hide` 로 뒀다가 검사가 되돌렸다 (`TestDefinition`·`InsertViaBrowser`·
   * `EditEntryPoints`). 편집 화면을 열었는데 편집 조작 전부가 접히면 화면이 통째로
   * 비고, 사용자는 자기가 잘못 들어온 줄 안다 — FR-234 가 원래 막으려던 상태가 정확히
   * 그것이다 (006 FR-206).
   *
   * 그리고 **해소할 수 있다**: 해소 방법이 `session.open` 이며, 그 세션으로 가서 끝내면
   * 편집이 열린다.
   */
  C7: "keep",
  C10: "hide",
  C11: "hide",
  /**
   * C12 — 아직 실행이 끝나지 않아 결과를 볼 수 없다. **남긴다.**
   *
   * 자리는 헤더의 작은 조작 하나이고(소음이 아니다), 「실행이 끝나면 볼 수 있습니다」는
   * 기다리면 풀리는 전제다. 접으면 실행 중 화면에서 결과라는 것이 있는지 알 수 없다
   * (`RunFinished` 검사가 이것을 지킨다).
   */
  C12: "keep",
  C13: "hide",
  O3: "hide",
  O4: "hide",
  /**
   * O5 — 실행이 이미 끝났다.
   *
   * **지금 이 키를 쓰는 셀이 없다** (2026-09-09). 쓰던 둘이 차례로 없어졌다: 덮어쓰기는
   * 국면이 갈리면서 국면 열로 옮겼고(위 `OVERRIDES` 의 그 자리 주석), `finished` 열의
   * 실행 속도는 사용자 결정으로 활성이 됐다.
   *
   * 키를 지우지 않는 이유는 계약 §3-6 의 번호이기 때문이다 — 번호에 구멍을 내면 계약과
   * 코드를 대조할 때 O5 가 「빠뜨린 것」인지 「없앤 것」인지 알 수 없다. 값은 형식상
   * `keep` 이며, 쓰는 셀이 생기면 그때 이 판단을 다시 한다.
   */
  O5: "keep",
  /**
   * O7 — 실패한 Step 이 있어 「계속하기」를 쓸 수 없다. **남긴다.**
   *
   * 처음에는 `hide` 로 뒀다 — 「건너뛰고 계속」이 활성으로 남으니 사유는 그것으로
   * 충분하다고 봤다. 검사가 그 판단을 되돌렸다 (`RecheckPhase12` T121 · 005 FR-136).
   *
   * **사용자가 이 화면에서 해소할 수 있는 전제다.** 실패한 Step 을 고치면 「계속하기」가
   * 풀린다. 그리고 이 사유가 있어야 **같은 자리에 왜 버튼이 둘인지**가 읽힌다 —
   * 「계속하기(막힘: 실패한 Step 이 있다)」 옆의 「실패 건너뛰고 계속」. 접으면 남은
   * 버튼 하나가 왜 「건너뛰고」인지 알 수 없다.
   *
   * 005 U-05 가 고친 것이 「계속하기가 실패를 조용히 지나간 것」이었다. 그 규칙이 화면에
   * 보이는 자리가 여기다.
   */
  O7: "keep",
  O9: "hide",
  /** O14 — 교체가 끝나지 않아 저장을 잠갔다. 같은 화면의 「확정」으로 해소한다. **남긴다.** */
  O14: "keep",
  RUNNING_NO_EDIT: "hide",
  RUN_FINISHED_NO_EDIT: "hide",
  RESULT_NO_EDIT: "hide",
  NEEDS_BROWSER: "hide",
  NEEDS_PAUSE: "hide",
  AI_RUNNING: "hide",
  /**
   * 지시문은 **기록이며 읽기 전용 표시다** — 잠긴 버튼이 아니다. 그래서 남긴다.
   *
   * `hide` 로 뒀다가 검사가 되돌렸다 (`TestDefinition`·`AiRecord`). 001 FR-063·FR-064 가
   * 요구하는 것은 「무엇을 시켰는지 잃지 않는다」이고, 그것을 접으면 요구가 사라진다
   * (UX U-07 이 그 형태였다).
   */
  AI_INSTRUCTION_RECORD: "keep",
  NO_SESSION: "hide",
  EDIT_AFTER_SESSION: "hide",
  /**
   * 만들기 국면 — 아직 시작하지 않았다. **남긴다** (FR-260 · S-15).
   *
   * `hide` 로 뒀다가 검사가 되돌렸다 (`ComposePhase`). FR-260 자체가 사용자 보고(S-15)의
   * 수정이고 그 내용이 「조작이 어디에 쌓이는지 시작하기 전에 보인다」였다 — 접는 것은
   * 그 수정을 되돌리는 일이다. 그리고 **곧바로 해소된다**: 「녹화 시작」을 누르면 된다.
   */
  NOT_STARTED_YET: "keep",
};

/**
 * 이유와 무관하게 **자리를 지키는 조작.**
 *
 * 공통점은 **자리가 버튼이 아니라는 것**이다. 버튼은 접으면 사라지고 그만이지만, 이 둘의
 * 자리는 사용자가 계속 보거나 만지는 면이다.
 *
 * - `mirror.control` — 자리가 미러 화면 전체이고 사용자는 그 위를 **클릭해 본다.**
 *   숨기면 클릭이 조용히 삼켜진다 (010 SC-516 이 0건으로 두려는 상태). `MirrorView` 가
 *   사유를 화면 위에 얹는 것으로 대신한다.
 * - `ai.compose` — 자리가 지시문 칸이고 그 **내용이 정보다.** 잠긴 것은 「고칠 수 없다」는
 *   뜻일 뿐이고, 접으면 사용자가 자기가 무엇을 시켰는지 잃는다 (001 FR-063·FR-064 ·
 *   UX U-07). 검사가 이 판단을 되돌렸다 (`AiRecord`) — AI 수행 중에 지시문이 사라졌다.
 *
 * 「해당 없음」(`–`)은 이 목록과 무관하다. 그것은 애초에 그 국면의 조작이 아니라는 뜻이고,
 * 표가 근거(N1·N2·N3)를 갖는다.
 */
const ALWAYS_KEEP = new Set<ActionId>(["mirror.control", "ai.compose"]);

function visibilityOf(action: ActionId, key: DisabledReasonKey): Visibility {
  return ALWAYS_KEEP.has(action) ? "keep" : REASON_VISIBILITY[key];
}

/* ─── 런타임 조건 C1~C13 (ui-contract §3-5) ─────────────────────────────────── */

export type ConditionKey =
  | "C1"
  | "C2"
  | "C3"
  | "C4"
  | "C5"
  | "C6"
  | "C7"
  | "C8"
  | "C9"
  | "C10"
  | "C11"
  | "C12"
  | "C13"
  | "C14"
  | "C15"
  | "C16"
  | "C17";

/**
 * 조건을 평가하는 데 필요한 사실. **화면이 아는 것만** 담는다.
 *
 * 값이 `undefined` 인 조건은 **거짓으로 본다.** 모르는 것을 참으로 보면 화면이 쓸 수
 * 없는 조작을 활성으로 그리고, 누르면 서버가 거절한다 — 005 U-01 이 그 형태였다.
 */
export interface CapabilityFacts {
  /** C1 — 그 세션이 끝났다 */
  sessionFinished?: boolean;
  /** C2 — 브라우저 세션이 살아 있다 */
  liveBrowser?: boolean;
  /** C3 — 실패한 Step 이 있다 */
  hasFailedStep?: boolean;
  /** C4 — 사람이 조작하는 동안 속도 설정이 적용되는가 (T041 에서 실측으로 확정) */
  pacingAppliesInTakeover?: boolean;
  /** C5 — 이 테스트를 막고 있는 세션이 있다 */
  blockingSession?: boolean;
  /** C6 — 지금 기록 중이다 */
  recording?: boolean;
  /** C7 — 정의가 편집 가능하다 */
  definitionEditable?: boolean;
  /** C8 — Step 이 1개 이상이다 */
  hasSteps?: boolean;
  /** C9 — 저장할 변경이 1건 이상이다 */
  hasPendingEdits?: boolean;
  /** C10 — 외부 변경 충돌이 감지됐다 */
  staleConflict?: boolean;
  /** C11 — AI 가 막혀 선택지를 제시했다 */
  aiBlocked?: boolean;
  /** C12 — testId 가 있고 그 실행이 끝났다 */
  resultViewable?: boolean;
  /** C13 — 그 테스트에 결과가 있다 */
  hasResult?: boolean;
  /** C14 — 지시문이 비어 있지 않다 (2회차 · 만들기 국면) */
  hasInstruction?: boolean;
  /** C15 — 만드는 방법으로 AI 를 골랐다 (2회차 · 만들기 국면) */
  aiModeChosen?: boolean;
  /**
   * C16 — 재녹화를 확정할 수 있다 (016 불변식 10).
   *
   * **서버가 판정한 값을 그대로 쓴다** (`SessionView.rerecord.can_commit`). 화면이
   * 「만든 Step 이 1개 이상인가」를 스스로 세면 서버와 갈리고, 갈리면 활성으로 그린
   * 버튼이 눌린 뒤 거절된다 (005 U-01 의 형태).
   */
  canCommitRerecord?: boolean;
  /** C17 — 진행 중인 교체가 있다 (016). `SessionView.rerecord !== null` */
  hasRerecord?: boolean;

  /* ─── 전 국면 덮어쓰기 O1~O4 (§3-6) ─── */
  /** O1 — 실행 요청이 진행 중이다 */
  runPending?: boolean;
  /** O2 — 명령이 진행 중이다 */
  busy?: boolean;
  /** O3 — 세션이 유실됐다 */
  sessionLost?: boolean;
  /**
   * O6 — 일시정지 **전이 중**이다 (005 FR-143·FR-144).
   *
   * 요청은 갔지만 아직 Step 경계에 닿지 않았다. 그 동안 편집 팔레트를 열면 사용자는
   * 아직 돌고 있는 실행에 편집을 건다 — 리포트가 요청 0.12초 뒤에 본 것이 그것이다.
   */
  pausing?: boolean;
  /** O8 — 중지 요청이 진행 중이다 (005 FR-147). 「중지 중…」의 근거. */
  stopRequested?: boolean;

  /* ─── 010 미러 조작의 런타임 사정 O10~O13 (contracts/mirror-control.md §1) ───
   *
   * **국면 열에 적지 않는다.** 넷 다 국면과 무관한 사정이고, 국면마다 표에 적으면 한
   * 국면이 빠진다. 빠진 국면에서 화면은 쓸 수 없는 조작을 활성으로 그리고, 사용자는
   * 클릭해 보고 나서 알게 된다 — FR-319 가 금지하는 상태다 (research R9).
   *
   * 이름을 **참인 방향**으로 짓는다 (`mirrorFrameSeen` 이지 `mirrorNoFrame` 이 아니다).
   * `undefined` 는 거짓으로 읽히므로(이 인터페이스의 규칙), 모르는 상태가 「조작할 수
   * 없다」로 붙는다 — 모르는 것을 활성으로 그리지 않는다.
   */
  /** O10 — 프레임을 한 장이라도 받았는가 (FR-333) */
  mirrorFrameSeen?: boolean;
  /** O11 — 프레임이 지금 흐르고 있는가 (FR-346) */
  mirrorLive?: boolean;
  /** O12 — 조작 통로가 붙었는가 */
  controlChannelOpen?: boolean;
  /**
   * O13 — 지금 조작 위치가 미러인가 (FR-350 · data-model §6).
   *
   * 실제 창으로 전환한 동안 미러는 관찰용이다 — 그때 「실제 브라우저 창에서 조작 중」
   * 이라는 001 의 문구가 참이 된다. 010 은 그 문구를 지우지 않고 **참인 상태를 좁힌다.**
   */
  controlSurfaceIsMirror?: boolean;
}

const CONDITION_FACT: Record<ConditionKey, keyof CapabilityFacts> = {
  C1: "sessionFinished",
  C2: "liveBrowser",
  C3: "hasFailedStep",
  C4: "pacingAppliesInTakeover",
  C5: "blockingSession",
  C6: "recording",
  C7: "definitionEditable",
  C8: "hasSteps",
  C9: "hasPendingEdits",
  C10: "staleConflict",
  C11: "aiBlocked",
  C12: "resultViewable",
  C13: "hasResult",
  /** C14 — 지시문이 비어 있지 않다 (2회차). `AiCompose` 가 하던 판정을 표로 옮겼다 */
  C14: "hasInstruction",
  /** C15 — 만드는 방법으로 AI 를 골랐다 (2회차) */
  C15: "aiModeChosen",
  C16: "canCommitRerecord",
  C17: "hasRerecord",
};

/** 조건이 거짓일 때의 해소 방법. 표의 셀이 지정하지 않으면 이것을 쓴다. */
const CONDITION_REMEDY: Partial<Record<ConditionKey, ActionId>> = {
  C1: "run.stop",
  C2: "run.all",
  C6: "step.recordStart",
  C7: "session.open",
  C13: "run.all",
  C14: "ai.compose",
};

/* ─── 전 국면 덮어쓰기 O1~O4 (ui-contract §3-6) ─────────────────────────────── */

/**
 * 표와 조건보다 **먼저** 적용된다. 하나라도 걸리면 그 조작은 ○ 다.
 *
 * `runPending` 이 국면별 표에 없고 여기 있는 이유: 국면과 무관한 사정이다. 국면마다 표에
 * 적으면 한 국면이 빠지고, 빠진 국면에서 연타하면 브라우저 창이 둘 뜬다 (005 U-06).
 */
const OVERRIDES: {
  key: DisabledReasonKey;
  fact: keyof CapabilityFacts;
  actions: ActionId[];
  remedy: ActionId | null;
}[] = [
  {
    key: "O1",
    fact: "runPending",
    actions: ["run.all", "run.from", "browser.openAt"],
    remedy: null,
  },
  {
    key: "O2",
    fact: "busy",
    actions: [
      "run.pause",
      "run.resume",
      "run.resumeSkipFailure",
      "run.stop",
      "run.fromHere",
      "step.recordStart",
      "step.recordStop",
      "step.addNaturalLanguage",
      "step.addAssertion",
      "step.insertManual",
      "step.repick",
      "save",
      /*
        **`record.start` 가 빠져 있었다.** 이 표 바로 위 주석이 「한 국면이 빠지면 그
        국면에서 연타하면 브라우저 창이 둘 뜬다」고 적어 둔 바로 그 결함이 만들기 국면에
        남아 있었다 — 세션 생성은 브라우저를 띄우느라 오래 걸리는데 그동안 버튼이 계속
        눌렸고, 눌린 만큼 세션이 만들어졌다.
      */
      "record.start",
      "ai.start",
      "ai.chooseBlocked",
    ],
    remedy: null,
  },
  {
    key: "O3",
    fact: "sessionLost",
    actions: [
      "run.pause",
      "run.resume",
      "run.resumeSkipFailure",
      "run.fromHere",
      "run.pacing",
      "step.recordStart",
      "step.recordStop",
      "step.addNaturalLanguage",
      "step.addAssertion",
      "step.insertManual",
      "step.repick",
      "tab.select",
      /*
        010 FR-347 — **세션이 유실된 뒤에는 마지막 프레임이 남아 있어도 조작하지 않는다.**

        서버는 이미 채널을 닫는다 (`_loss_handler`). 그것만으로 충분해 보이지만 아니다:
        채널이 닫혔다는 사실이 화면에 닿기까지의 짧은 사이에 화면은 미러를 조작 가능으로
        그리고, 사용자가 그때 클릭하면 아무 일도 일어나지 않는다 — SC-516 이 0건으로
        두려는 조용한 실패다.

        **실제 창 전환도 함께 잠근다.** 옮겨 갈 세션이 없다. 다른 막힘(강등·끊김)에서는
        전환이 안전망으로 살아 있지만(FR-353a), 유실은 막힌 것이 아니라 사라진 것이다 —
        그때 남는 길은 새로 실행하는 것이고, `remedy` 가 그것을 가리킨다.
      */
      "mirror.control",
      "mirror.useWindow",
    ],
    remedy: "run.all",
  },
  {
    key: "O4",
    fact: "hasSteps",
    /*
      **`step.insertManual` 은 여기 넣지 않는다** (009 계약 §2-2). `O4` 는 「대상이 없으면
      뜻이 없는 조작」을 위한 것이고 삽입은 그 반대다 — Step 이 0개일 때야말로 넣을 수
      있어야 한다 (008 FR-260 과 같은 판단).

      **`save` 도 빼냈다** (2026-09-09). 같은 사실(Step 이 0개다)을 O4 와 셀의 조건 C8 이
      둘 다 말하고 있었고, 덮어쓰기가 먼저이므로 화면에 나오는 것은 O4 의 「Step 이
      없습니다」였다. 그 이유는 `hide` 이고 C8 은 `keep` 이라, 녹화를 시작한 직후
      **저장 자리가 화면에서 사라졌다.** 사용자가 보고한 「저장하는 부분이 명확하지
      않다」의 절반이 이것이다. 판정은 C8 하나가 갖는다 — 문구도 그쪽이 낫다
      (「Step 이 없으면 저장할 수 없습니다」).
    */
    actions: [
      "run.all",
      "run.from",
      "run.fromHere",
      "step.moveUp",
      "step.moveDown",
      "step.delete",
      /*
        011 — 복수 삭제도 대상이 없으면 뜻이 없다. `step.insertManual` 을 여기 넣지 않은
        것과 갈리는 이유는 같다: 삽입은 0개일 때야말로 필요하고, 삭제는 0개일 때 할 것이
        없다.
      */
      "step.toggleSelection",
      "step.selectAll",
      "step.deleteSelected",
      "step.deleteAfter",
    ],
    remedy: null,
  },
  /*
    O5~O8 은 T037·T041 의 **실측 대조**가 더한 것이다 (UC-401 · FR-247).

    표의 국면 열만으로는 같은 국면 안에서 갈리는 사정을 담을 수 없었다. 국면마다 표에
    적으면 한 국면이 빠지고, 빠진 국면에서 화면은 쓸 수 없는 조작을 활성으로 그린다 —
    O1 을 덮어쓰기로 둔 것과 같은 이유다.
  */
  /*
    **O5 는 덮어쓰기에서 빠졌다** (2026-09-09).

    하던 일: 세션이 끝났으면 「일시정지」와 「실행 속도」를 잠갔다 (005 U-08 의 이웃).
    국면이 갈린 뒤에는 그 일을 국면 열이 한다 — `finished` 는 실행 제어 셋을 `–`(N2)로,
    실행 속도를 `off("O5")` 로 갖는다.

    **그리고 이 덮어쓰기는 두 국면에서 서로 다른 답을 요구했다.** `review` 도
    `isFinished` 가 참인데 그 국면에서는 속도를 **바꿀 수 있다** — 서버가 받고
    (`set_pacing` 은 `TERMINAL_STATES`·`LOST` 만 거절한다), 그 값이 같은 화면의 활성
    조작인 「처음부터 실행」에 쓰인다 (004 FR-109). 덮어쓰기는 국면을 보지 않으므로 그
    구별을 표현할 수 없었다.

    사유 키 `O5` 는 남는다 — `finished` 열의 속도 셀이 그 문구를 쓴다.
  */
  {
    // O6 — 일시정지 전이 중 (005 FR-143·FR-144). **「중지」는 뺀다** — 기다리다
    // 포기하는 것이 가장 자연스러운 다음 행동이고, 그것까지 잠근 것이 U-04 였다.
    key: "O6",
    fact: "pausing",
    actions: [
      "run.resume",
      "run.resumeSkipFailure",
      "run.fromHere",
      "step.recordStart",
      "step.recordStop",
      "step.addNaturalLanguage",
      "step.addAssertion",
      "step.update",
      "step.markSensitive",
      "step.repick",
      "step.delete",
      "step.toggleSelection",
      "step.selectAll",
      "step.deleteSelected",
      "step.deleteAfter",
      "step.moveUp",
      "step.moveDown",
      "step.insertManual",
      "save",
    ],
    remedy: null,
  },
  {
    /*
      O7 — 실패한 Step 이 있으면 「계속하기」를 잠근다 (005 FR-136 · U-05).

      이전에는 「계속하기」가 실패를 조용히 지나가고 배지를 「완료」로 바꿨다. 저장된
      결과는 실패인데 화면은 완료라고 말했다.

      **해소 방법을 달지 않는다.** 건너뛰는 길(`run.resumeSkipFailure`)은 같은 자리에
      **별도 버튼**으로 있어야 하는 것이 FR-137 의 요구이고, 그것을 해소 방법 링크로
      대신하면 "다른 버튼" 이라는 요구가 사라진다.
    */
    key: "O7",
    fact: "hasFailedStep",
    actions: ["run.resume"],
    remedy: null,
  },
  {
    // O8 — 중지 요청이 도는 중 (005 FR-147). 라벨은 `stopLabel()` 이 「중지 중…」으로 바꾼다.
    key: "O8",
    fact: "stopRequested",
    actions: ["run.stop"],
    remedy: null,
  },
  {
    // O9 — 건너뛸 실패가 없으면 건너뛰기는 뜻이 없다. 참·거짓 방향이 반대다.
    // 계약(§3-6)과 **같은 이름**을 쓴다 — 문구를 고칠 때 계약의 어느 줄인지 즉시 찾는다.
    key: "O9",
    fact: "hasFailedStep",
    actions: ["run.resumeSkipFailure"],
    remedy: null,
  },
  /*
    O10~O13 — 010 미러 조작의 런타임 사정 (contracts/mirror-control.md §1).

    **순서가 곧 우선순위다.** 위에서부터 걸리는 첫 사유가 화면에 나온다. 프레임을 한 장도
    못 받은 것 → 끊긴 것 → 통로가 없는 것 → 창에서 조작 중인 것 순으로 둔 이유는 그것이
    사용자가 할 수 있는 일의 순서이기 때문이다. 프레임이 아예 없는데 「조작 통로가 준비되지
    않았습니다」를 보여 주면, 사용자는 통로를 기다리다 화면이 오지 않는다는 것을 놓친다.

    **넷 다 `mirror.useWindow` 를 막지 않는다.** 막히는 상황일수록 실제 창으로 내려가는
    수단이 살아 있어야 한다 (FR-353a) — 그것이 이 기능의 안전망이다.
  */
  {
    key: "O10",
    fact: "mirrorFrameSeen",
    actions: ["mirror.control"],
    remedy: null,
  },
  {
    key: "O11",
    fact: "mirrorLive",
    actions: ["mirror.control"],
    remedy: "mirror.useWindow",
  },
  {
    key: "O12",
    fact: "controlChannelOpen",
    actions: ["mirror.control"],
    remedy: "mirror.useWindow",
  },
  {
    key: "O13",
    fact: "controlSurfaceIsMirror",
    actions: ["mirror.control"],
    remedy: null,
  },
  /*
    O14 — 교체가 끝나지 않았으면 저장을 **미리** 잠근다 (2026-09-11 사용자 보고 · 016 FR-029).

    > 「ai 로 변경한 내용(추가,변경) 저장도 안돼」

    서버는 확정되지 않은 교체의 저장을 409 로 거절한다 (`sessions.py` 의 `save`). 그러나
    화면의 `save` 셀은 C8(Step 이 있다)만 봤으므로 버튼이 **활성으로 보이다가 눌러야**
    거절됐다 — 005 U-01 의 형태이고, `RerecordStart` 가 「미리 잠긴다 — 눌러 보고 409 를
    받지 않는다」로 같은 종류를 이미 막았던 자리다. 재녹화 띠가 목록 머리에 짓눌려
    확정 버튼이 보이지 않던 것과 겹쳐, 사용자에게는 「저장이 안 된다」로만 보였다.

    해소는 **확정**이다. 버리기도 정당한 길이지만 저장하려는 사람이 원하는 것은 만든
    것을 남기는 쪽이고, 해소 링크는 하나만 가리킨다 (FR-235). 버리기는 사유 문구가 말한다.

    `keep` 이다 — 이 화면에서 곧바로 해소할 수 있는 전제다 (재녹화 띠가 같은 화면에 있다).
  */
  {
    key: "O14",
    fact: "hasRerecord",
    actions: ["save"],
    remedy: "ai.rerecordCommit",
  },
];

/** O4·O9 는 「…이 있다」가 **거짓일 때** 걸린다 — 다른 덮어쓰기와 참·거짓 방향이 반대다. */
const NEGATED_OVERRIDES = new Set<DisabledReasonKey>(["O4", "O9", "O10", "O11", "O12", "O13"]);

/**
 * **명시적으로 참일 때만 통과시키는 덮어쓰기** (010 O10~O13).
 *
 * `NEGATED_OVERRIDES` 는 사실이 `false` 일 때만 걸린다 — `undefined` 는 걸리지 않는다.
 * O4·O9 에는 그 규칙이 맞다: 「Step 이 있는지 모른다」는 화면이 Step 목록을 아직 못 받은
 * 순간이고, 그때 저장을 잠그면 화면이 뜨자마자 전부 회색이 된다.
 *
 * **미러 조작에는 반대가 맞다.** 「프레임을 받았는지 모른다」에서 조작을 활성으로 그리면,
 * 사용자는 클릭해 보고 나서 안 된다는 것을 알게 된다 — FR-319 가 정확히 그것을 금지한다.
 * 게다가 서버가 그 조작을 거절하므로(FR-333·FR-341) 화면과 서버가 갈린 상태가 된다.
 *
 * 그래서 이 넷은 `undefined` 도 「아니다」로 읽는다.
 */
const REQUIRE_TRUE_OVERRIDES = new Set<DisabledReasonKey>(["O10", "O11", "O12", "O13"]);

/* ─── 표 (ui-contract §3-1 ~ §3-4) ─────────────────────────────────────────── */

type PhaseRow = Record<ActionId, Cell>;

/**
 * 열 국면 × 42 조작 (011 이 복수 삭제 넷을 더했다).
 *
 * 표를 읽는 법 — 각 국면 열이 그 국면 화면의 **전부**다. 여기 ●·○ 인 것은 화면에
 * 있어야 하고, – 인 것만 없어도 된다.
 */
const PHASE_TABLE: Record<Phase, PhaseRow> = {
  /*
    만들기 — 시작 주소를 정하고 만드는 방법을 고른다 (2회차 · FR-217b·FR-258).

    **저장된 테스트도 세션도 Step 도 없다.** 그래서 대부분이 「대상이 없음」(N2) 또는
    「세션이 없음」(N3)이다. 실제로 쓸 수 있는 것은 넷 — `test.setStartUrl` ·
    `ai.compose` · `record.start` · `nav.back`. `ai.start` 는 지시문이 비면 못 누른다.

    Step 조작을 `–` 가 아니라 `○` 로 두는 것이 FR-260 이다. 자리를 감추면 목록이
    0개일 때 「조작이 어디에 쌓이는지」를 보여 줄 수 없다 (S-15).
  */
  composing: {
    "ai.rerecord": na("N2"),
    "ai.chat": na("N2"),
    "ai.rerecordCommit": na("N2"),
    "ai.rerecordDiscard": na("N2"),
    "run.all": na("N2"),
    "run.from": na("N2"),
    "run.fromHere": na("N2"),
    "run.pause": na("N3"),
    "run.resume": na("N3"),
    "run.resumeSkipFailure": na("N3"),
    "run.stop": na("N3"),
    "run.pacing": na("N3"),
    "browser.openAt": na("N2"),
    "session.open": na("N2"),
    /** 이 국면의 주 조작. 세션을 녹화 모드로 만든다 */
    "record.start": ON,
    "step.recordStart": off("NOT_STARTED_YET", "record.start"),
    "step.recordStop": na("N2"),
    "step.addNaturalLanguage": off("NOT_STARTED_YET", "record.start"),
    "step.addAssertion": off("NOT_STARTED_YET", "record.start"),
    "step.insertManual": off("NOT_STARTED_YET", "record.start"),
    /* 목록이 그 자리다. 0개여도 목록은 남으므로 ○ 다 (FR-260) */
    "step.select": off("NOT_STARTED_YET", "record.start"),
    /*
      **이 셋의 자리는 Step 상세다.** Step 이 0개면 상세가 열릴 수 없으므로 자리가
      존재하지 않는다 — 「대상이 없음」(N2)이며 감춘 조작이 아니다 (§4-2).

      `step.select`·`delete`·`reorder` 와 갈리는 이유: 그것들의 자리는 목록과 조작
      팔레트이고, 둘 다 0개 상태에서도 있다. 자리가 있으면 ○, 자리 자체가 성립하지
      않으면 – 다.
    */
    "step.update": na("N2"),
    "step.markSensitive": na("N2"),
    "step.repick": na("N2"),
    /* 조작 팔레트가 그 자리다 */
    "step.delete": off("NOT_STARTED_YET", "record.start"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": off("NOT_STARTED_YET", "record.start"),
    "step.selectAll": off("NOT_STARTED_YET", "record.start"),
    "step.deleteSelected": off("NOT_STARTED_YET", "record.start"),
    "step.deleteAfter": off("NOT_STARTED_YET", "record.start"),
    "step.moveUp": off("NOT_STARTED_YET", "record.start"),
    "step.moveDown": off("NOT_STARTED_YET", "record.start"),
    /** 이름은 저장 시점에 정한다. 자리는 남기고 이유를 붙인다 (FR-258a) */
    "test.rename": off("NAME_ON_SAVE"),
    "test.setStartUrl": ON,
    save: off("NOTHING_TO_SAVE_YET", "record.start"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    /*
       지시문 자리는 방법을 고르기 전에도 **있다.** 고른 뒤에만 쓸 수 있으므로 조건이다
       (C15) — 감추면 「AI 로 만들 때 지시문을 쓴다」를 고른 뒤에야 알게 된다 (FR-234).
     */
    "ai.compose": cond("C15"),
    "ai.start": cond("C14"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    "result.show": na("N2"),
    "nav.editStep": na("N2"),
    "nav.back": ON,
    /** 대상 앱을 아직 열지 않았으므로 탭이라는 것이 존재하지 않는다 */
    /*
      010 미러 조작 (contracts/mirror-control.md §1). **세션이 없다** — 조작할 대상
      브라우저가 아직 없으므로 「세션 명령이며 이 국면에는 세션이 없습니다」(N3)다.
    */
    "mirror.control": na("N3"),
    "mirror.useWindow": na("N3"),
    "tab.select": na("N1"),
  },
  /* 녹화 — 사람이 대상 앱을 조작해 Step 을 만든다 */
  recording: {
    "ai.rerecord": na("N1"),
    "ai.chat": off("NEEDS_PAUSE", "run.pause"),
    "ai.rerecordCommit": na("N2"),
    "ai.rerecordDiscard": na("N2"),
    "run.all": na("N2"),
    "run.from": na("N2"),
    "run.fromHere": na("N2"),
    "run.pause": ON,
    "run.resume": na("N1"),
    "run.resumeSkipFailure": na("N2"),
    "run.stop": ON,
    "run.pacing": ON,
    "browser.openAt": na("N1"),
    "session.open": na("N1"),
    /** 이미 세션이 있다 — 「이미 충족됨」이며 감춘 조작이 아니다 */
    "record.start": na("N1"),
    "step.recordStart": na("N1"),
    "step.recordStop": ON,
    "step.addNaturalLanguage": off("NEEDS_PAUSE", "run.pause"),
    "step.addAssertion": off("NEEDS_PAUSE", "run.pause"),
    "step.insertManual": off("NEEDS_PAUSE", "run.pause"),
    "step.select": ON,
    "step.update": off("NEEDS_PAUSE", "run.pause"),
    "step.markSensitive": off("NEEDS_PAUSE", "run.pause"),
    "step.repick": off("NEEDS_PAUSE", "run.pause"),
    "step.delete": off("NEEDS_PAUSE", "run.pause"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": off("NEEDS_PAUSE", "run.pause"),
    "step.selectAll": off("NEEDS_PAUSE", "run.pause"),
    "step.deleteSelected": off("NEEDS_PAUSE", "run.pause"),
    "step.deleteAfter": off("NEEDS_PAUSE", "run.pause"),
    "step.moveUp": off("NEEDS_PAUSE", "run.pause"),
    "step.moveDown": off("NEEDS_PAUSE", "run.pause"),
    "test.rename": ON,
    "test.setStartUrl": na("N2"),
    save: cond("C8"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    "ai.compose": na("N2"),
    "ai.start": na("N2"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    "result.show": na("N2"),
    "nav.editStep": na("N2"),
    "nav.back": ON,
    /*
      010 FR-314 — **이 국면의 새 주 조작이다.** 001 에서는 조작을 실제 브라우저 창에서
      했고 미러는 포인터를 아예 받지 않았다 (FR-047a). 010 이 그것을 뒤집는다.

      실제 창은 폴백으로 남는다 (FR-349). 사용자가 누를 때만 열린다 — 제품이 상황을
      판단해 자동으로 창을 열지 않는다 (FR-353).
    */
    "mirror.control": ON,
    "mirror.useWindow": ON,
    "tab.select": ON,
  },

  /* AI 작성 — AI 가 지시문대로 Step 을 만든다 */
  ai_authoring: {
    "ai.rerecord": off("AI_RUNNING", "run.stop"),
    "ai.chat": off("AI_RUNNING", "run.pause"),
    "ai.rerecordCommit": off("AI_RUNNING", "run.pause"),
    "ai.rerecordDiscard": off("AI_RUNNING", "run.pause"),
    "run.all": na("N2"),
    "run.from": na("N2"),
    "run.fromHere": na("N2"),
    "run.pause": ON,
    "run.resume": na("N1"),
    "run.resumeSkipFailure": na("N2"),
    "run.stop": ON,
    "run.pacing": ON,
    "browser.openAt": na("N1"),
    "session.open": na("N1"),
    /** 이미 세션이 있다 — 「이미 충족됨」이며 감춘 조작이 아니다 */
    "record.start": na("N1"),
    "step.recordStart": off("AI_RUNNING", "run.pause"),
    "step.recordStop": na("N2"),
    "step.addNaturalLanguage": off("NEEDS_PAUSE", "run.pause"),
    "step.addAssertion": off("NEEDS_PAUSE", "run.pause"),
    "step.insertManual": off("NEEDS_PAUSE", "run.pause"),
    "step.select": ON,
    "step.update": off("NEEDS_PAUSE", "run.pause"),
    "step.markSensitive": off("NEEDS_PAUSE", "run.pause"),
    "step.repick": off("NEEDS_PAUSE", "run.pause"),
    "step.delete": off("NEEDS_PAUSE", "run.pause"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": off("NEEDS_PAUSE", "run.pause"),
    "step.selectAll": off("NEEDS_PAUSE", "run.pause"),
    "step.deleteSelected": off("NEEDS_PAUSE", "run.pause"),
    "step.deleteAfter": off("NEEDS_PAUSE", "run.pause"),
    "step.moveUp": off("NEEDS_PAUSE", "run.pause"),
    "step.moveDown": off("NEEDS_PAUSE", "run.pause"),
    "test.rename": ON,
    "test.setStartUrl": na("N2"),
    save: cond("C8"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    // 지시문은 수행 중에는 고칠 수 없다. 기록으로 계속 보인다 (FR-063).
    "ai.compose": off("AI_RUNNING", "run.stop"),
    "ai.start": off("AI_RUNNING"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    "result.show": na("N2"),
    "nav.editStep": na("N2"),
    "nav.back": ON,
    /*
      010 FR-315 — **관찰 국면이다.** AI 가 전진하는 중에 사람 조작이 끼어들면 같은
      Step 이 두 번 돈다. 감추지 않고 이유를 붙이는 이유는 SC-516 이다 — 조작할 수
      없는 모든 상황에서 사용자가 사유를 읽을 수 있어야 한다.
    */
    "mirror.control": off("AI_RUNNING", "run.pause"),
    "mirror.useWindow": off("AI_RUNNING", "run.pause"),
    "tab.select": ON,
  },

  /* 사람이 직접 조작 — AI 가 막힌 자리를 사람이 이어받는다 */
  takeover: {
    "ai.rerecord": off("AI_RUNNING", "run.stop"),
    "ai.chat": off("USE_BLOCKED_ANSWER", "ai.chooseBlocked"),
    "ai.rerecordCommit": off("NEEDS_PAUSE", "run.resume"),
    "ai.rerecordDiscard": off("NEEDS_PAUSE", "run.resume"),
    "run.all": na("N2"),
    "run.from": na("N2"),
    "run.fromHere": na("N2"),
    "run.pause": na("N1"),
    "run.resume": ON,
    "run.resumeSkipFailure": na("N2"),
    "run.stop": ON,
    /*
      T041 — **C4 를 실측으로 확정했다.** 사람이 조작하는 동안 재생 속도는 지금 실행에
      적용되지 않는다 (`PacingControl` 의 `manipulationPhase`). 그러나 그것은 조작을
      막을 근거가 아니라 **라벨의 근거**다 — 004 FR-109 로 여기서 고른 값이 다음 실행의
      기본값이 되므로, 비활성으로 두면 005 FR-174 가 요구한 "무엇에 쓰이는 값인지
      밝히되 감추지 않는다" 를 어긴다. 표를 고친다 (UC-401).
    */
    "run.pacing": ON,
    "browser.openAt": na("N1"),
    "session.open": na("N1"),
    /** 이미 세션이 있다 — 「이미 충족됨」이며 감춘 조작이 아니다 */
    "record.start": na("N1"),
    "step.recordStart": ON,
    "step.recordStop": cond("C6"),
    "step.addNaturalLanguage": off("NEEDS_PAUSE", "run.resume"),
    "step.addAssertion": off("NEEDS_PAUSE", "run.resume"),
    "step.insertManual": off("NEEDS_PAUSE", "run.resume"),
    "step.select": ON,
    "step.update": off("NEEDS_PAUSE", "run.resume"),
    "step.markSensitive": off("NEEDS_PAUSE", "run.resume"),
    "step.repick": ON,
    "step.delete": off("NEEDS_PAUSE", "run.resume"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": off("NEEDS_PAUSE", "run.resume"),
    "step.selectAll": off("NEEDS_PAUSE", "run.resume"),
    "step.deleteSelected": off("NEEDS_PAUSE", "run.resume"),
    "step.deleteAfter": off("NEEDS_PAUSE", "run.resume"),
    "step.moveUp": off("NEEDS_PAUSE", "run.resume"),
    "step.moveDown": off("NEEDS_PAUSE", "run.resume"),
    "test.rename": ON,
    "test.setStartUrl": na("N2"),
    save: cond("C8"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    "ai.compose": off("AI_RUNNING", "run.stop"),
    "ai.start": na("N1"),
    "ai.chooseBlocked": cond("C11"),
    "artifact.select": na("N2"),
    "result.show": na("N2"),
    "nav.editStep": na("N2"),
    "nav.back": ON,
    /* 010 FR-314 — 사람이 이어받는 국면이다. 미러에서 조작한다 */
    "mirror.control": ON,
    "mirror.useWindow": ON,
    "tab.select": ON,
  },

  /* 실행 중 — 저장된 테스트를 재생한다 */
  running: {
    "ai.rerecord": off("RUNNING_NO_EDIT", "run.pause"),
    "ai.chat": off("RUNNING_NO_EDIT", "run.pause"),
    "ai.rerecordCommit": off("RUNNING_NO_EDIT", "run.pause"),
    "ai.rerecordDiscard": off("RUNNING_NO_EDIT", "run.pause"),
    /*
      T037 대조 — 끝난 실행에서는 **재실행이 실제로 열린다.** `SessionScreen` 의
      `rerun()` 이 세션을 폐기하고 새 세션을 연다. 표가 `○` 로 못박고 있던 것은
      현재 동작과 어긋났다 (UC-401). 조건 C1 로 바꾼다 — 세션이 살아 있는 동안에는
      같은 이유·같은 해소 방법으로 비활성이므로 실행 중 동작은 바뀌지 않는다.
    */
    "run.all": cond("C1"),
    "run.from": cond("C1"),
    "run.fromHere": na("N2"),
    "run.pause": ON,
    "run.resume": na("N2"),
    "run.resumeSkipFailure": na("N2"),
    "run.stop": ON,
    "run.pacing": ON,
    "browser.openAt": na("N1"),
    "session.open": na("N1"),
    /** 이미 세션이 있다 — 「이미 충족됨」이며 감춘 조작이 아니다 */
    "record.start": na("N1"),
    "step.recordStart": off("RUNNING_NO_EDIT", "run.pause"),
    "step.recordStop": na("N2"),
    "step.addNaturalLanguage": off("RUNNING_NO_EDIT", "run.pause"),
    "step.addAssertion": off("RUNNING_NO_EDIT", "run.pause"),
    "step.insertManual": off("RUNNING_NO_EDIT", "run.pause"),
    "step.select": ON,
    "step.update": off("RUNNING_NO_EDIT", "run.pause"),
    "step.markSensitive": off("RUNNING_NO_EDIT", "run.pause"),
    "step.repick": off("RUNNING_NO_EDIT", "run.pause"),
    "step.delete": off("RUNNING_NO_EDIT", "run.pause"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": off("RUNNING_NO_EDIT", "run.pause"),
    "step.selectAll": off("RUNNING_NO_EDIT", "run.pause"),
    "step.deleteSelected": off("RUNNING_NO_EDIT", "run.pause"),
    "step.deleteAfter": off("RUNNING_NO_EDIT", "run.pause"),
    "step.moveUp": off("RUNNING_NO_EDIT", "run.pause"),
    "step.moveDown": off("RUNNING_NO_EDIT", "run.pause"),
    "test.rename": off("RUNNING_NO_EDIT", "run.pause"),
    "test.setStartUrl": off("EDIT_AFTER_SESSION", "run.stop"),
    save: off("RUNNING_NO_EDIT", "run.pause"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    "ai.compose": na("N2"),
    "ai.start": na("N2"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    // T037 대조 — 끝난 실행의 「결과 자세히 보기」는 이 국면에도 있다 (005 FR-133).
    "result.show": cond("C12"),
    "nav.editStep": na("N2"),
    "nav.back": ON,
    /*
      010 FR-315 — **관찰 국면이다.** 러너가 전진하는 중이다. 「일시정지」가 해소
      방법인 것이 요점이다 — 멈추면 미러에서 조작할 수 있다 (US3).
    */
    "mirror.control": off("NEEDS_PAUSE", "run.pause"),
    "mirror.useWindow": off("NEEDS_PAUSE", "run.pause"),
    "tab.select": ON,
  },

  /* 일시정지 / 검토 — 세션이 멈춰 있고 편집·저장을 받는다 */
  paused: {
    /* ─── 016 구간 재녹화 (contracts/ui-contract.md §2) ───────────────────
       **`paused` 가 재녹화의 집이다.** 확정·버리기·교체 대상 보기·손 편집이 전부 이
       국면에서 일어난다 (research R4). 채팅이 `ON` 인 유일한 행이기도 하다.

       `ai.rerecord` 가 `off` 인 이유: 재녹화는 세션을 **만드는** 조작이므로 세션
       안에서는 성립하지 않는다. 대신 이 세션에서 대화로 진행하면 된다. */
    "ai.rerecord": off("ALREADY_IN_SESSION"),
    "ai.chat": ON,
    "ai.rerecordCommit": cond("C16"),
    "ai.rerecordDiscard": cond("C17"),
    "run.all": cond("C1"),
    "run.from": cond("C1"),
    "run.fromHere": cond("C2"),
    "run.pause": na("N1"),
    "run.resume": cond("C2"),
    /*
      T037 대조 — 건너뛰기는 **둘 다** 필요하다: 이어갈 브라우저(C2)와 건너뛸 실패(C3).
      표의 셀은 조건 하나만 담으므로 브라우저를 셀에, 실패 유무를 덮어쓰기(아래 `C3`)에
      둔다. 이전 표는 C3 만 보고 있어서 브라우저가 없는 검토 상태에서도 활성이었다 —
      누르면 서버가 거절한다. 그것이 005 U-01 의 형태다.
    */
    "run.resumeSkipFailure": cond("C2"),
    "run.stop": ON,
    "run.pacing": cond("C2"),
    "browser.openAt": na("N1"),
    "session.open": na("N1"),
    /** 이미 세션이 있다 — 「이미 충족됨」이며 감춘 조작이 아니다 */
    "record.start": na("N1"),
    "step.recordStart": cond("C2"),
    "step.recordStop": cond("C6"),
    "step.addNaturalLanguage": cond("C2"),
    "step.addAssertion": cond("C2"),
    /*
      **`C2`(브라우저가 살아 있다)를 요구하지 않는다** (009 계약 §2-1).

      위의 `step.recordStart`·`addNaturalLanguage`·`addAssertion` 은 브라우저를 만져야
      하므로 `C2` 다. 이것은 정의 목록만 고치고 **브라우저에 아무 명령도 보내지 않는다** —
      `step.delete` 가 같은 이유로 이미 `●` 인 것과 같다. 검토 상태(브라우저가 닫힌 채
      목록만 보는 상태)에서도 넣고 옮기고 지울 수 있어야 한다.
    */
    "step.insertManual": ON,
    "step.select": ON,
    "step.update": ON,
    "step.markSensitive": ON,
    "step.repick": cond("C2"),
    "step.delete": ON,
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": ON,
    "step.selectAll": ON,
    "step.deleteSelected": ON,
    "step.deleteAfter": ON,
    "step.moveUp": ON,
    "step.moveDown": ON,
    "test.rename": ON,
    "test.setStartUrl": off("EDIT_AFTER_SESSION", "run.stop"),
    save: cond("C8"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    "ai.compose": na("N2"),
    "ai.start": na("N2"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    "result.show": cond("C12"),
    "nav.editStep": na("N2"),
    "nav.back": ON,
    /*
      010 FR-314 · US3 — **일시정지가 조작 국면인 것이 이 기능의 요점 하나다.**
      실패한 실행을 같은 화면에서 이어받는다. 세션 상태(인증·화면·입력값)는 그대로
      유지된다 (헌법 원칙 III).
    */
    "mirror.control": ON,
    "mirror.useWindow": ON,
    "tab.select": cond("C2"),
  },

  /*
    검토 — 기록을 확인하고 고치고 저장한다. **브라우저는 이미 닫혔다** (2026-09-09).

    `paused` 열을 복사해 만들지 **않았다.** 두 열의 차이가 이 국면을 만든 이유이므로,
    차이 나는 칸을 하나씩 판정했다.

    - 브라우저를 만지는 조작 여섯(`run.resume`·`resumeSkipFailure`·`run.fromHere`·
      `run.pacing`·`step.recordStart`·`step.addNaturalLanguage`·`step.addAssertion`·
      `step.repick`·`tab.select`)은 조건 C2 로 남긴다. 국면이 갈렸으니 `off("NEEDS_BROWSER")`
      로 못박을 수도 있지만, C2 를 쓰면 **사실을 보고 판정한다**는 이 표의 성질이 유지된다.
      둘 다 `hide` 라 화면 결과는 같다.
    - 정의만 고치는 조작(`insertManual`·`update`·`markSensitive`·`delete`·`moveUp`·
      `moveDown`)은 `●` 다. 서버가 `REVIEW` 에서 `EDIT_STEPS` 를 받는다.
    - `save` 는 이 국면의 **주 조작**이다 (`SessionScreen` 이 강조를 준다).
  */
  review: {
    "ai.rerecord": off("NEEDS_BROWSER", "run.all"),
    "ai.chat": off("NEEDS_BROWSER", "run.all"),
    /*
      **확정·버리기는 여기서도 쓸 수 있다** (2026-09-11 사용자 보고).

      016 초안은 넷을 묶어 「브라우저가 없다」(N3)로 적었다. 그것이 `ai.rerecord`·
      `ai.chat` 에는 맞고 이 둘에는 틀렸다 — 확정은 **정의만 고치는 편집**이고,
      서버도 `REVIEW` 에서 받는다 (`require_paused` 는 `is_editable` 을 쓴다).

      막다른 길을 만든 것이 이 두 칸이었다. 교체를 연 채 「AI 작성 끝내기」나 「중지」를
      누르면 세션은 `REVIEW` 로 온다. 저장은 미확정 교체를 거절하고(FR-029), 화면에는
      확정도 버리기도 없다 — 남은 길이 「나가기」뿐이고 그것은 만든 것을 전부 버린다.
      실측에서 사용자가 그 상태로 남긴 세션을 그대로 만났다.

      비활성 사유의 해소 링크(O14)가 `ai.rerecordCommit` 을 가리키는 것도 이 칸이
      `na` 인 동안에는 아무 데도 닿지 않았다.
    */
    "ai.rerecordCommit": cond("C16"),
    "ai.rerecordDiscard": cond("C17"),
    /** 저장된 테스트가 있으면 다시 걸 수 있다. 세션은 이미 끝났으므로 C1 은 참이다 */
    "run.all": cond("C1"),
    "run.from": cond("C1"),
    /** 이어갈 브라우저가 없다 */
    "run.fromHere": cond("C2"),
    "run.pause": na("N1"),
    "run.resume": cond("C2"),
    "run.resumeSkipFailure": cond("C2"),
    /** 라벨은 「나가기」다 (`stopLabel`) — 세션을 버리고 목록으로 간다 */
    "run.stop": ON,
    /**
     * **활성이다** — 서버가 `review` 에서 속도 변경을 받는다 (`sessions.set_pacing` 은
     * `TERMINAL_STATES` 와 `LOST` 만 거절하고 `REVIEW` 는 거절하지 않는다).
     *
     * 처음에는 `cond("C2")` 로 접었다. 브라우저가 없으니 돌릴 것이 없다고 봤는데,
     * 이 국면에는 **「처음부터 실행」이 활성으로 있다.** 여기서 고른 값이 그 실행의
     * 속도가 되고, 그것이 004 FR-109 다. 라벨은 「다음 실행 속도」로 밝힌다 (FR-174).
     */
    "run.pacing": ON,
    "browser.openAt": na("N1"),
    "session.open": na("N1"),
    "record.start": na("N1"),
    "step.recordStart": cond("C2"),
    "step.recordStop": cond("C6"),
    "step.addNaturalLanguage": cond("C2"),
    "step.addAssertion": cond("C2"),
    /** 브라우저에 아무 명령도 보내지 않는다 (009 계약 §2-1) */
    "step.insertManual": ON,
    "step.select": ON,
    "step.update": ON,
    "step.markSensitive": ON,
    "step.repick": cond("C2"),
    "step.delete": ON,
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": ON,
    "step.selectAll": ON,
    "step.deleteSelected": ON,
    "step.deleteAfter": ON,
    "step.moveUp": ON,
    "step.moveDown": ON,
    /** 저장 이름이다. 이 국면에서 정한다 (005 FR-156) */
    "test.rename": ON,
    "test.setStartUrl": off("EDIT_AFTER_SESSION", "run.stop"),
    save: cond("C8"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    "ai.compose": na("N2"),
    "ai.start": na("N2"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    "result.show": cond("C12"),
    "nav.editStep": na("N2"),
    "nav.back": ON,
    /**
     * 미러는 **마지막 화면이 남은 관찰면**이다. 조작할 브라우저가 없다.
     *
     * `mirror.control` 은 `ALWAYS_KEEP` 이라 숨지 않는다 — 사용자가 미러를 클릭해 볼
     * 것이고, 그때 사유가 화면 위에 있어야 한다 (010 SC-516).
     */
    "mirror.control": off("NEEDS_BROWSER", "run.all"),
    "mirror.useWindow": off("NEEDS_BROWSER", "run.all"),
    "tab.select": cond("C2"),
  },

  /*
    실행 종료 — 결말을 보고, 다시 실행하거나 저장한다 (2026-09-09).

    **편집이 전부 닫힌다.** 서버가 이 상태에서 받는 편집 명령이 없다
    (`state_machine.py` 의 `COMPLETED`·`FAILED`·`STOPPED` 는 전이표가 비어 있다).
    이전 판은 `running` 열을 그대로 써서 「실행 중이어서 편집할 수 없습니다 → 일시정지」
    를 붙였다 — 사유도 해소 방법도 사실이 아니었다.

    **`save` 는 살아 있다.** 저장은 상태 전이를 거치지 않고 Step 유무만 본다. AI 작성이
    끝까지 성공한 세션을 저장할 길이 여기밖에 없다.
  */
  finished: {
    "ai.rerecord": off("RUN_FINISHED_NO_EDIT", "save"),
    "ai.chat": off("RUN_FINISHED_NO_EDIT", "save"),
    "ai.rerecordCommit": na("N2"),
    "ai.rerecordDiscard": na("N2"),
    /** 이 국면의 주 조작. 세션이 끝났으므로 새 실행이 열린다 */
    "run.all": ON,
    "run.from": ON,
    "run.fromHere": off("NEEDS_BROWSER", "run.all"),
    /*
      실행 제어 셋은 **「대상이 없음」(N2)이다.** 제어할 진행 중인 실행이 없다.

      처음에는 `off("O5")` 로 뒀는데, 그러면 사유가 `keep` 이라 「일시정지 ✕ 실행이 이미
      끝났습니다」가 실행 종료 띠에 남는다. 눌러서 될 일이 아니고 기다려서 될 일도 아니다.
    */
    "run.pause": na("N2"),
    "run.resume": na("N2"),
    "run.resumeSkipFailure": na("N2"),
    /** 라벨은 「닫기」다. 강조를 뺀다 — 결과 접근을 끊을 수 있다 (005 FR-147·FR-148) */
    "run.stop": ON,
    /**
     * **활성이다** (2026-09-09 사용자 결정: 「속도 선택은 실행중이든 아니든 바꿀수있어야함」).
     *
     * 처음에는 `off("O5")` 로 뒀다 — 서버가 끝난 세션의 속도 변경을 거절했기 때문이고,
     * 화면이 서버보다 관대해서는 안 된다는 규율(005 U-01)에 따른 것이었다. 사용자가
     * 지목한 뒤 **서버의 거절을 없앴다** (`sessions.set_pacing` — 거절에 실질적 근거가
     * 없었다). 이 국면에는 「처음부터 실행」이 활성으로 있고, 여기서 고른 값이 그 실행의
     * 속도가 된다 (004 FR-109).
     *
     * 라벨은 「다음 실행 속도」다 — 지금 돌고 있는 것에 적용되지 않는다는 사실을 밝힌다
     * (005 FR-174).
     */
    "run.pacing": ON,
    "browser.openAt": na("N1"),
    "session.open": na("N1"),
    "record.start": na("N2"),
    "step.recordStart": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.recordStop": na("N2"),
    "step.addNaturalLanguage": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.addAssertion": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.insertManual": off("RUN_FINISHED_NO_EDIT", "save"),
    /** 결말을 보려면 골라야 한다. 고르는 것은 편집이 아니다 */
    "step.select": ON,
    "step.update": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.markSensitive": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.repick": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.delete": off("RUN_FINISHED_NO_EDIT", "save"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.selectAll": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.deleteSelected": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.deleteAfter": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.moveUp": off("RUN_FINISHED_NO_EDIT", "save"),
    "step.moveDown": off("RUN_FINISHED_NO_EDIT", "save"),
    /** 저장이 살아 있으므로 이름도 살아 있어야 한다 */
    "test.rename": ON,
    "test.setStartUrl": off("EDIT_AFTER_SESSION", "run.stop"),
    save: cond("C8"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    "ai.compose": off("AI_INSTRUCTION_RECORD"),
    "ai.start": na("N2"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    "result.show": cond("C12"),
    /**
     * **실패한 실행을 고치러 가는 길** (2026-09-09 사용자 보고).
     *
     * 보고된 것: 「실행 후 에러가 났을 때, 고치기 즉 편집을 하는 방법이 없음」. 실제로
     * 없었다 — 이 국면에서 서버는 편집 명령을 받지 않고(`state_machine` 의 `FAILED` 는
     * 전이표가 비어 있다), 편집 화면으로 가는 조작은 표에서 `–` 였다.
     *
     * 게다가 이 화면은 그 없는 조작을 **이름으로 안내하고 있었다**: 실패 알림이
     * 「「Step nn 고치기」 또는 「Step nn부터 실행」을 쓰세요」라고 적는다. 006 E-03 이
     * 정확히 그 형태였다 — 안내하면서 그리로 가는 버튼을 주지 않는 것.
     *
     * 자리는 **헤더**다 (`ACTION_GROUP` 의 배치 규칙 · 결과 국면과 같은 자리). 저장되지
     * 않은 변경이 있으면 화면이 좁힌다 — 편집 화면은 **저장된 정의**를 읽으므로, 저장하지
     * 않고 넘어가면 방금 기록한 것이 화면에서 사라진다.
     */
    "nav.editStep": ON,
    "nav.back": ON,
    /** 조작할 브라우저 세션이 없다 (010 FR-347) */
    "mirror.control": off("NEEDS_BROWSER", "run.all"),
    "mirror.useWindow": off("NEEDS_BROWSER", "run.all"),
    "tab.select": off("NEEDS_BROWSER", "run.all"),
  },

  /* 결과보기 — 끝난 실행의 결말과 산출물 */
  result: {
    "ai.rerecord": off("RESULT_NO_EDIT", "nav.editStep"),
    "ai.chat": off("RESULT_NO_EDIT", "nav.editStep"),
    "ai.rerecordCommit": na("N2"),
    "ai.rerecordDiscard": na("N2"),
    "run.all": ON,
    "run.from": ON,
    "run.fromHere": na("N3"),
    "run.pause": na("N3"),
    "run.resume": na("N3"),
    "run.resumeSkipFailure": na("N3"),
    "run.stop": na("N3"),
    "run.pacing": na("N3"),
    "browser.openAt": off("RESULT_NO_EDIT", "nav.editStep"),
    "session.open": cond("C5"),
    /** 만들 대상이 없다. 새 테스트는 목록에서 시작한다 */
    "record.start": na("N2"),
    "step.recordStart": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.recordStop": na("N3"),
    "step.addNaturalLanguage": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.addAssertion": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.insertManual": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.select": ON,
    "step.update": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.markSensitive": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.repick": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.delete": off("RESULT_NO_EDIT", "nav.editStep"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.selectAll": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.deleteSelected": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.deleteAfter": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.moveUp": off("RESULT_NO_EDIT", "nav.editStep"),
    "step.moveDown": off("RESULT_NO_EDIT", "nav.editStep"),
    "test.rename": off("RESULT_NO_EDIT", "nav.editStep"),
    "test.setStartUrl": off("RESULT_NO_EDIT", "nav.editStep"),
    save: na("N2"),
    "save.overwriteStale": na("N2"),
    "edits.revert": na("N2"),
    "ai.compose": off("AI_INSTRUCTION_RECORD"),
    "ai.start": na("N2"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": ON,
    "result.show": na("N1"),
    "nav.editStep": ON,
    "nav.back": ON,
    /* 010 — 끝난 실행이다. 조작할 브라우저 세션이 없다 (FR-347) */
    "mirror.control": na("N3"),
    "mirror.useWindow": na("N3"),
    "tab.select": na("N3"),
  },

  /* 편집 — 세션 없이 정의를 고친다 */
  editing: {
    /* ─── 016 구간 재녹화 (contracts/ui-contract.md §2) ───────────────────
       **`ai.rerecord` 가 `cond("C7")` 인 이유**는 009 T063 이 고친 결함이다 — 다른
       세션이 그 테스트를 잡고 있으면 서버가 409 로 거절하는데, 화면이 활성으로 그리면
       눌린 뒤에 거절된다. `step.recordStart`·`step.addNaturalLanguage` 가 같은 자리에서
       같은 판정을 받는다.

       **`ai.chat` 이 `off("NEEDS_SESSION")` 인 것이 R6 의 결정이 표에 나타난 형태다.**
       채팅은 세션 안에서만 산다. 자리는 보이되 잠기고 해소 조작을 가리킨다 (FR-234).

       해소 조작은 **「브라우저 열어 이 Step 앞에서 멈추기」다** (2026-09-11 사용자 보고).
       016 은 `ai.rerecord` 를 가리켰는데, 그것은 「구간을 골라 교체」하는 한 가지 쓰임이다.
       사용자가 말한 그림은 「위치를 고르면 브라우저가 그 앞까지 실행해 멈추고, 거기서
       AI 가 끼운다」이고, 그 조작이 `browser.openAt` 이다 — 일시정지 세션의 대화는 그
       위치에 끼운다 (FR-023a). 교체는 사유 문구가 두 번째 길로 말한다. */
    "ai.rerecord": cond("C7"),
    "ai.chat": off("NEEDS_SESSION", "browser.openAt"),
    "ai.rerecordCommit": na("N3"),
    "ai.rerecordDiscard": na("N3"),
    "run.all": ON,
    "run.from": ON,
    "run.fromHere": na("N3"),
    "run.pause": na("N3"),
    "run.resume": na("N3"),
    "run.resumeSkipFailure": na("N3"),
    "run.stop": na("N3"),
    "run.pacing": na("N3"),
    /*
      **009 T063 — `ON` 에서 `C7` 로 좁혔다** (US2 인수 시나리오 5 · FR-234).

      이 조작은 그 테스트로 **세션을 만든다.** 다른 세션이 이미 그것을 잡고 있으면 만들 수
      없다 — 서버가 `409 SESSION_ALREADY_ACTIVE` 로 거절한다. `ON` 인 동안 화면은 그 사실을
      모르고 활성으로 그렸고, 누르면 거절됐다. 그것이 005 U-01 의 형태다.

      `C7`(정의가 편집 가능하다)이 맞는 조건인 이유: 그 값은 「이 테스트를 잡은 세션이
      없다」에서 나온다(`blocking_session_id is None`). 해소 방법도 이미 맞다 —
      `CONDITION_REMEDY["C7"]` 이 `session.open` 이며, 그것이 「그 세션으로 가는 방법」이다.

      009 가 이 조작을 다섯 걸음에서 한 걸음으로 만들었으므로(FR-291) 눌리는 빈도가 크게
      늘었다. 거절되는 경로를 남겨 둘 수 없다.
    */
    "browser.openAt": cond("C7"),
    "session.open": cond("C5"),
    /** 만들 대상이 없다. 새 테스트는 목록에서 시작한다 */
    "record.start": na("N2"),
    /*
      ─── 011 — 두 셀이 `off("NEEDS_BROWSER")` 에서 `cond("C7")` 로 열렸다 ──────────

      **사용자 보고 3번의 실체가 이 두 줄이었다** — 「스텝을 새로 녹화하는것처럼, ai
      지시문으로도 스텝을 추가할 수 있어야한다」. 두 조작은 이미 있었고 해소 방법
      (`browser.openAt`)도 맞았다. 문제는 사용자가 **두 걸음을 걸어야** 했다는 것이고,
      그래서 두 길이 대등하게 보이지 않았다.

      이제 화면이 그 걸음을 대신 걷는다 — 누르면 브라우저를 열고 이어서 수행한다
      (FR-374a · UC-011-23). 009 가 `browser.openAt` 을 다섯 걸음에서 한 걸음으로 만든
      것과 같은 종류의 수정이다.

      **`cond("C7")` 인 이유**: 이 둘은 이제 세션을 **만든다.** 그러므로
      `browser.openAt` 과 같은 전제를 갖는다 — 다른 세션이 그 테스트를 잡고 있으면 만들
      수 없고, 서버가 `409` 로 거절한다. `ON` 으로 두면 009 T063 이 고친 결함
      (활성으로 그렸다가 눌리면 거절)이 이 두 셀에서 되살아난다.

      **둘 다 바꾼다.** 하나만 자동으로 열면 대등성이 다시 깨진다 (research R7).

      `step.addAssertion` 은 **바꾸지 않는다.** 검증 추가는 요소를 지목해야 하고
      (헌법 원칙 IV), 지목은 살아 있는 화면에서 사용자가 하는 일이다 — 브라우저를 열어
      주는 것으로 끝나지 않는다.
    */
    "step.recordStart": cond("C7"),
    "step.recordStop": na("N3"),
    "step.addNaturalLanguage": cond("C7"),
    "step.addAssertion": off("NEEDS_BROWSER", "browser.openAt"),
    /*
      **009 의 핵심 셀이다** (FR-307 · 계약 §2-1).

      위 셋은 전부 `NEEDS_BROWSER` 다. 그 잠금의 근거는 하나뿐이다 — 요소 후보는 살아
      있는 페이지에서만 수집·검증된다(헌법 원칙 IV). 그런데 **요소를 지목하지 않는 Step
      종류**(주소 이동·탭 닫기·주소 검증·화면 텍스트 검증)에는 그 근거가 적용되지 않는다.

      006 이 이 화면을 만들 때 삽입을 뺀 것은 원칙 IV 때문이었고 그 판단은 옳았다. 다만
      「일부는 손으로 만들 수 있다」를 표현할 자리가 없어서 **전부** 못 만드는 쪽으로
      정리됐다 (관찰 M-11). 그것을 여기서 가른다.

      잠금의 근거는 「정의를 고칠 수 있는가」(C7) 하나다. 실행 중이면 그 세션이 정의를
      잡고 있으므로 C7 이 거짓이 되고, 그것이 FR-306 이 요구하는 잠금이다 — 러너와 목록
      편집이 겹치는 것을 여기서도 같은 근거로 막는다.
    */
    "step.insertManual": cond("C7"),
    "step.select": ON,
    "step.update": cond("C7"),
    "step.markSensitive": cond("C7"),
    // 새 요소를 브라우저 없이 지목할 수는 없다 (006 의 범위 밖).
    "step.repick": off("NEEDS_BROWSER", "browser.openAt"),
    "step.delete": cond("C7"),
    /* 011 복수 삭제 — 판정은 `step.delete` 와 같다. 한 개를 지울 수 없는
       상태에서 여러 개를 지울 수 있으면 안 되고, 그 역도 안 된다.
       대상 개수(0개인가)는 국면이 아니므로 화면이 좁힌다 (`narrow`) */
    "step.toggleSelection": cond("C7"),
    "step.selectAll": cond("C7"),
    "step.deleteSelected": cond("C7"),
    "step.deleteAfter": cond("C7"),
    "step.moveUp": cond("C7"),
    "step.moveDown": cond("C7"),
    "test.rename": cond("C7"),
    "test.setStartUrl": cond("C7"),
    save: cond("C9"),
    "save.overwriteStale": cond("C10"),
    "edits.revert": cond("C9"),
    // 지시문은 기록일 뿐 실행 대상이 아니므로 읽기 전용이다 (006 의 결정).
    "ai.compose": off("AI_INSTRUCTION_RECORD"),
    "ai.start": na("N2"),
    "ai.chooseBlocked": na("N2"),
    "artifact.select": na("N2"),
    "result.show": cond("C13"),
    "nav.editStep": na("N1"),
    "nav.back": ON,
    /* 010 — 세션 없이 정의를 고치는 국면이다. 조작할 브라우저가 없다 */
    "mirror.control": na("N3"),
    "mirror.useWindow": na("N3"),
    "tab.select": na("N3"),
  },
};

/* ─── 판정 ─────────────────────────────────────────────────────────────────── */

function cellToState(action: ActionId, cell: Cell, facts: CapabilityFacts): CapabilityState {
  switch (cell.t) {
    case "on":
      return { kind: "enabled" };
    case "off":
      return {
        kind: "disabled",
        reason: DISABLED_REASON[cell.reason],
        remedy: cell.remedy ? { action: cell.remedy } : null,
        visibility: visibilityOf(action, cell.reason),
      };
    case "na":
      return {
        kind: "not_applicable",
        basis: cell.basis,
        note: NOT_APPLICABLE_REASON[cell.basis],
      };
    case "cond": {
      // 모르는 것을 참으로 보지 않는다. 모르면 비활성이다 — 활성으로 그리면
      // 누른 뒤 서버가 거절하고, 그것이 005 U-01 의 형태였다.
      if (facts[CONDITION_FACT[cell.key]] === true) return { kind: "enabled" };
      const remedy = cell.remedy ?? CONDITION_REMEDY[cell.key] ?? null;
      return {
        kind: "disabled",
        reason: DISABLED_REASON[cell.key],
        remedy: remedy ? { action: remedy } : null,
        visibility: visibilityOf(action, cell.key),
      };
    }
  }
}

/** 그 국면에서 그 조작이 어떤 상태인가. **화면이 묻는 유일한 질문이다.** */
export function capabilityOf(
  phase: Phase,
  action: ActionId,
  facts: CapabilityFacts = {},
): CapabilityState {
  // 덮어쓰기가 표보다 먼저다 (§3-6).
  for (const o of OVERRIDES) {
    if (!o.actions.includes(action)) continue;
    const value = facts[o.fact];
    const triggered = REQUIRE_TRUE_OVERRIDES.has(o.key)
      ? value !== true
      : NEGATED_OVERRIDES.has(o.key)
        ? value === false
        : value === true;
    if (!triggered) continue;
    // 그 국면에서 애초에 해당 없는 조작은 덮어쓰기도 하지 않는다 — 없는 조작에
    // 「실행을 준비하는 중…」을 붙이면 화면이 쓸 수 없는 조작으로 뒤덮인다.
    const base = PHASE_TABLE[phase][action];
    if (base.t === "na") break;
    /*
      **표가 접은 조작은 덮어쓰기가 되살리지 않는다** (2026-09-09).

      검사가 잡은 것 (`RecheckPhase12` T121): 검토 국면에서 실패한 Step 이 있으면
      「계속하기」가 O7 의 사유(「실패한 Step 이 있어 이어서 갈 수 없습니다」)를 달고
      되살아났다. 그 국면의 진짜 사정은 **브라우저가 없다**는 것이고, 그것은 O7 보다
      근본적이다 — 실패를 고쳐도 이어갈 수 없다.

      규칙으로 적으면: 국면이 「이 상태의 조작이 아니다」라고 답했으면 런타임 사정이 그
      답을 뒤집을 수 없다. 덮어쓰기가 국면보다 먼저인 것은 「할 수 있는 것을 잠그기」
      위해서이고, 「할 수 없는 것을 되살리기」 위해서가 아니다.
    */
    const baseState = cellToState(action, base, facts);
    if (baseState.kind === "disabled" && baseState.visibility === "hide") return baseState;
    return {
      kind: "disabled",
      reason: DISABLED_REASON[o.key],
      remedy: o.remedy ? { action: o.remedy } : null,
      visibility: visibilityOf(action, o.key),
    };
  }
  return cellToState(action, PHASE_TABLE[phase][action], facts);
}

/** 그 국면의 33개 조작 전부. 화면은 이것을 한 번 만들어 아래로 넘긴다. */
export function capabilitiesFor(phase: Phase, facts: CapabilityFacts = {}): CapabilityMap {
  const map = {} as CapabilityMap;
  for (const action of ACTION_IDS) {
    map[action] = capabilityOf(phase, action, facts);
  }
  return map;
}

/** 표를 그대로 읽어야 하는 검사(T012)를 위한 접근자. 화면은 이것을 쓰지 않는다. */
export function rawCell(phase: Phase, action: ActionId): Cell {
  return PHASE_TABLE[phase][action];
}

/**
 * 이유 키의 보임/숨김. **검사를 위한 접근자다** (2026-09-09).
 *
 * `CapabilityUI` 가 「그 국면 화면에 반드시 있어야 하는 조작」을 세려면 이 판정을 읽어야
 * 한다. 검사가 자기 사본을 들면 표와 갈리고, 갈린 날 검사는 통과하면서 화면은 조작을
 * 잃는다 — 이 파일이 존재하는 이유와 같은 종류의 위험이다.
 */
export function reasonVisibility(key: DisabledReasonKey): Visibility {
  return REASON_VISIBILITY[key];
}

/**
 * 그 국면에서 **화면에 반드시 있어야 하는** 조작인가 (검사용).
 *
 * 세 경우다 — ① 언제나 쓸 수 있다(`ON`) ② 잠기지만 사유가 `keep` 이다(`off`) ③ 조건에
 * 걸리지만 그 조건의 사유가 `keep` 이다(`cond`). ③ 이 요점이다: 조건이 참이면 활성으로,
 * 거짓이면 사유를 달고 **어느 쪽이든 자리에 있다.**
 *
 * `hide` 인 `off`·`cond` 는 여기서 빠진다 — 그 국면·그 사실에서는 「이 상태의 조작이
 * 아니다」이며, 접히는 것이 2026-09-09 의 결정이다.
 */
export function alwaysPresent(phase: Phase, action: ActionId): boolean {
  const cell = PHASE_TABLE[phase][action];
  switch (cell.t) {
    case "on":
      return true;
    case "na":
      return false;
    case "off":
      return REASON_VISIBILITY[cell.reason] === "keep";
    case "cond":
      return REASON_VISIBILITY[cell.key] === "keep";
  }
}


/**
 * 실제 창으로 갈 수 없는 사정을 표의 판정 위에 얹는다 (010 FR-351 · FR-234).
 *
 * **문구를 화면이 갖지 않는다.** 창을 띄울 수 있는지는 서버만 아는 사실이고(운영체제·
 * 표시 서버, 그리고 그 브라우저를 창 없이 띄웠는지), 화면이 같은 뜻의 문장을 따로 가지면
 * 서버가 거절할 때 쓰는 문장과 갈린다 — `wording.ts` 의 O13 옆 주석이 남긴 결정이다.
 * 그래서 여기 들어오는 `reason` 은 **서버가 준 문장 그대로**다.
 *
 * 표가 이미 막고 있으면 그대로 둔다. 표의 사유가 더 앞선 사정이기 때문이다 — 예를 들어
 * AI 가 도는 중이라면 창이 있든 없든 먼저 멈춰야 한다.
 *
 * 이것이 없던 동안: 창 없이 띄운 세션에서도 버튼이 눌렸고, 서버는 「옮겼다」고 답한 뒤
 * 미러의 조작 통로를 닫았다. 창은 뜨지 않아 조작할 곳이 하나도 남지 않았다
 * (사용자 보고 2026-09-09 「실제창에서 조작하기 변환이 안됨」).
 */
export function narrowByWindowAvailability(
  base: CapabilityState,
  reason: string | null,
): CapabilityState {
  if (reason === null || base.kind !== "enabled") return base;
  // `"keep"` — **자리를 남기고 이유를 붙인다** (FR-234). 감추면 사용자는 「실제 창에서
  // 조작하기가 어디 갔지」를 묻게 되고, 왜 못 쓰는지는 어디에도 나타나지 않는다.
  return { kind: "disabled", reason, remedy: null, visibility: "keep" };
}
