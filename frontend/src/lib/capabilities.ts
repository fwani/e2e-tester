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

export type CapabilityState =
  /** 쓸 수 있다 */
  | { kind: "enabled" }
  /** 쓸 수 없다 — 같은 자리에 비활성으로 남기고 이유를 붙인다 (FR-234) */
  | { kind: "disabled"; reason: string; remedy: Remedy | null }
  /** 이 국면의 조작이 아니다 — 그리지 않는다. §4-2 의 근거가 있어야 쓸 수 있다 */
  | { kind: "not_applicable"; basis: NotApplicableKey; note: string };

export type CapabilityMap = Record<ActionId, CapabilityState>;

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
  | "C15";

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
    */
    actions: [
      "save",
      "run.all",
      "run.from",
      "run.fromHere",
      "step.moveUp",
      "step.moveDown",
      "step.delete",
    ],
    remedy: null,
  },
  /*
    O5~O8 은 T037·T041 의 **실측 대조**가 더한 것이다 (UC-401 · FR-247).

    표의 국면 열만으로는 같은 국면 안에서 갈리는 사정을 담을 수 없었다. 국면마다 표에
    적으면 한 국면이 빠지고, 빠진 국면에서 화면은 쓸 수 없는 조작을 활성으로 그린다 —
    O1 을 덮어쓰기로 둔 것과 같은 이유다.
  */
  {
    // O5 — 실행이 이미 끝났다. 「일시정지」가 활성으로 남아 있던 것이 005 U-08 의 이웃이다.
    key: "O5",
    fact: "sessionFinished",
    actions: ["run.pause", "run.pacing"],
    remedy: null,
  },
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
];

/**
 * 「…이다」가 **거짓일 때** 걸리는 덮어쓰기 — 다른 것들과 참·거짓 방향이 반대다.
 *
 * O10~O13 이 여기 있는 이유는 이름을 참인 방향으로 지었기 때문이다 (`mirrorFrameSeen`).
 * 반대로 지으면(`mirrorNoFrame`) `undefined` 가 「프레임이 있다」로 읽혀, 모르는 상태에서
 * 화면이 조작을 활성으로 그린다.
 */
const NEGATED_OVERRIDES = new Set<DisabledReasonKey>([
  "O4",
  "O9",
  "O10",
  "O11",
  "O12",
  "O13",
]);

/* ─── 표 (ui-contract §3-1 ~ §3-4) ─────────────────────────────────────────── */

type PhaseRow = Record<ActionId, Cell>;

/**
 * 여덟 국면 × 34 조작.
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

  /* 결과보기 — 끝난 실행의 결말과 산출물 */
  result: {
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
    "step.recordStart": off("NEEDS_BROWSER", "browser.openAt"),
    "step.recordStop": na("N3"),
    "step.addNaturalLanguage": off("NEEDS_BROWSER", "browser.openAt"),
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

function cellToState(cell: Cell, facts: CapabilityFacts): CapabilityState {
  switch (cell.t) {
    case "on":
      return { kind: "enabled" };
    case "off":
      return {
        kind: "disabled",
        reason: DISABLED_REASON[cell.reason],
        remedy: cell.remedy ? { action: cell.remedy } : null,
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
    const triggered = NEGATED_OVERRIDES.has(o.key) ? value === false : value === true;
    if (!triggered) continue;
    // 그 국면에서 애초에 해당 없는 조작은 덮어쓰기도 하지 않는다 — 없는 조작에
    // 「실행을 준비하는 중…」을 붙이면 화면이 쓸 수 없는 조작으로 뒤덮인다.
    const base = PHASE_TABLE[phase][action];
    if (base.t === "na") break;
    return {
      kind: "disabled",
      reason: DISABLED_REASON[o.key],
      remedy: o.remedy ? { action: o.remedy } : null,
    };
  }
  return cellToState(PHASE_TABLE[phase][action], facts);
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
