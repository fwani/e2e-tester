/**
 * ③ 좌측 두 자리의 세로 배분 (007 T098 · FR-256·FR-257 · ui-contract §1-5).
 *
 * > **UC-100 — 한 국면에서 두 자리가 동시에 `fill` 일 수 없고, 동시에 `content` 일
 * > 수도 없다.** 앞은 그 국면의 주 작업이 어느 자리인지 화면이 말하지 못하게 하고,
 * > 뒤는 남는 높이를 어디로도 보내지 않는다.
 *
 * ## 왜 표인가
 *
 * 1회차에는 표시 컴포넌트가 **자기 자리 크기를 스스로 고정**했다 — `TargetPane` 이
 * `flex: "1"` 을, `PhaseAside` 가 `flex: 0 0 auto` 를 하드코딩했다. 둘 다 자기 파일
 * 안에서는 옳았고, **합쳐 보면 편집 국면에서 뒤바뀌었다**: 채울 것이 「브라우저가 열려
 * 있지 않습니다」 두 줄뿐인 자리가 700px 를 가져가고, 편집 폼 전체가 42px 띠에 들어갔다
 * (spec S-12).
 *
 * 판단이 두 파일에 흩어져 있으면 어느 한 쪽만 보고는 그 결함을 볼 수 없다. 표로 모으면
 * 「동시에 `fill` 일 수 없다」를 검사 하나로 셀 수 있고 (SC-010), 국면이 늘어날 때
 * 빠뜨릴 수 없다 — `Record<Phase, …>` 가 컴파일 시점에 요구한다. `capabilities.ts` 의
 * `PHASE_TABLE` 과 같은 규율이며 이유도 같다 (research R9).
 *
 * ## 이 파일이 하지 않는 것
 *
 * **폭을 정하지 않는다.** ③ 좌측이 남는 폭을 갖고 Step 패널이 460px 고정인 것은
 * FR-218a 이며 1회차에서 바뀌지 않았다. 2회차가 더한 것은 **세로**뿐이다.
 *
 * **표시 컴포넌트가 이 파일을 읽지 않는다.** `Workbench` 가 국면으로 한 번 조회해 두
 * 자리에 내려 준다 — `TargetPane`·`WorkArea` 는 자기 크기를 모른다. 그것이 S-12 가
 * 되살아나지 않게 하는 배치다.
 */

import type { Phase } from "./phase";

/**
 * 한 자리가 남는 높이를 갖는 방식.
 *
 * `fixed` 를 쓸 수 있는 경우는 둘뿐이다 (ui-contract §1-5) — ③-a 가 세션이 없어 담을
 * 것이 정해져 있을 때(B1), ③-b 의 내용이 정해진 행 수를 가질 때(B4). 그 밖에는
 * `fill` 또는 `content` 다. `fixed` 를 남용하면 창 높이가 바뀔 때 잘린다.
 */
export type SlotSize =
  /** 남는 높이 전부 */
  | { kind: "fill" }
  /** 내용에 맞는 높이. 최소 `CONTENT_MIN_HEIGHT` */
  | { kind: "content" }
  /** 정해진 높이 */
  | { kind: "fixed"; px: number };

export interface VerticalSplit {
  /** ③-a 대상 앱 슬롯 */
  targetSlot: SlotSize;
  /** ③-b 국면 작업 영역 */
  workArea: SlotSize;
}

/** ③ 좌측의 두 자리. 순서와 개수는 국면에 따라 바뀌지 않는다 (FR-218c). */
export type SlotName = "target" | "work";

/**
 * `content` 자리의 최소 높이.
 *
 * 008 「계기판」의 안내 띠는 32px 다 (`Record`·`Takeover`·`Paused` 공통). v1 의 42px 는
 * 3px 테두리와 15px 세로 여백을 안고 있던 값이다 — 경계 비용이 1px 로 내려가면서
 * 같은 한 줄이 32px 에 들어간다.
 */
export const CONTENT_MIN_HEIGHT = 32;

/**
 * 세션이 없는 국면의 ③-a 높이 (승인 대상 B1).
 *
 * 32px 강조 버튼 + 상하 27px 여백 + 1px 테두리 = 88. **자리를 없애는 것이 아니라 줄이는
 * 것이다** (FR-261) — 자리가 사라지면 「이 화면에는 원래 없는 것」과 구별되지 않는다.
 *
 * 008 에서 118 → 88 로 내렸다. 조작 높이가 46 → 32 로 내려간 만큼이며, 담는 것(안내
 * 두 줄 + 「브라우저 열어 Step nn 에서 멈추기」)은 그대로다.
 */
export const TARGET_SLOT_MIN_PX = 88;

/**
 * 결과 국면 ③-b 높이 (승인 대상 B4).
 *
 * 실패 사유 2줄 + 시도한 LOCATOR 4행 + 경고 1개가 스크롤 없이 들어가는 높이.
 */
export const RESULT_WORK_PX = 424;

const FILL: SlotSize = { kind: "fill" };
const CONTENT: SlotSize = { kind: "content" };
const fixed = (px: number): SlotSize => ({ kind: "fixed", px });

/**
 * 국면 × 두 자리 → 배분. **표가 정본이다** (ui-contract §1-5).
 *
 * 세션이 있는 다섯 국면(`recording`·`ai_authoring`·`takeover`·`running`·`paused`)은
 * ③-a 가 `fill` 이다 — **미러를 보면서 하는 일**이므로 1회차 배분이 이미 옳았다.
 * 2회차가 고치는 것은 세션이 없는 `editing` 과 끝난 실행 `result` 다.
 *
 * `composing`(만들기)은 묶음 B 에서 더했다. `Phase` 에 그 값을 넣는 순간 이 표와
 * `PHASE_TABLE`·`PRIMARY_SLOT` 셋이 **동시에** 값을 요구했다 — 타입이 빠뜨림을 막는다는
 * 것이 이 배치의 값이다 (research R9).
 */
export const VERTICAL_SPLIT: Record<Phase, VerticalSplit> = {
  /** 아직 열지 않았다는 사실만 필요하다. 하는 일은 시작 조건 입력이다 (FR-258) */
  composing: { targetSlot: fixed(TARGET_SLOT_MIN_PX), workArea: FILL },
  /** 미러를 보면서 조작한다. ③-b 는 42px 안내 띠 (B9) */
  recording: { targetSlot: FILL, workArea: CONTENT },
  /** 미러 + 지시문·진행·차단. 차단 시 내용이 늘어난다 (B10) */
  ai_authoring: { targetSlot: FILL, workArea: CONTENT },
  /** 녹화와 같다 */
  takeover: { targetSlot: FILL, workArea: CONTENT },
  /** 미러 + 진행 한 줄·실행 속도 */
  running: { targetSlot: FILL, workArea: CONTENT },
  /** 미러를 보면서 고친다. 검증 추가 폼이 펼쳐지면 늘어난다 */
  paused: { targetSlot: FILL, workArea: CONTENT },
  /** 산출물이 남는 높이. ③-b 는 사유 + LOCATOR 4행 (B4 · FR-262) */
  result: { targetSlot: FILL, workArea: fixed(RESULT_WORK_PX) },
  /** 브라우저 여는 조작만 필요하다. 하는 일은 Step 편집이다 (FR-261) */
  editing: { targetSlot: fixed(TARGET_SLOT_MIN_PX), workArea: FILL },
};

/**
 * 그 국면의 **주 작업이 어느 자리인가** (FR-257).
 *
 * 검사가 「주 작업」을 알 방법이 필요하다. 「크기가 큰 쪽이 주 작업이다」는 순환 정의라
 * 아무것도 세지 못하므로, 국면이 **선언**하고 검사가 배분과 대조한다.
 *
 * 이 선언과 `VERTICAL_SPLIT` 이 어긋나면 그것이 S-12 의 형태다 — 선언은 「편집면이 주
 * 작업」인데 배분은 대상 앱 슬롯에 `fill` 을 준 상태.
 */
export const PRIMARY_SLOT: Record<Phase, SlotName> = {
  composing: "work",
  recording: "target",
  ai_authoring: "target",
  takeover: "target",
  running: "target",
  paused: "target",
  result: "target",
  editing: "work",
};

/**
 * Step 상세를 **어디에 거는가** (008 · FR-230 개정 대상).
 *
 * ## 왜 표인가 — 007 이 남긴 모순
 *
 * 007 은 Step 상세 구현 2벌을 1벌로 합치면서 자리도 하나로 고정했다 (FR-229·FR-230).
 * 그 통합은 옳았다 — S-05 의 실제 원인은 **두 구현이 갈라진 것**이었다.
 *
 * 그런데 같은 라운드가 ③-b 를 「그 국면의 주 작업 자리」로 정하고 편집 국면에
 * `fill` 을 줬다 (FR-257 · `VERTICAL_SPLIT.editing`). 그 항목의 주석은 이렇게 적혀
 * 있다 — **「하는 일은 Step 편집이다」**. 그런데 Step 편집 폼은 겹침에 있고, ③-b 에
 * 담기로 했던 테스트 이름·시작 주소·지시문은 FR-235 로 조작 팔레트에 갔다.
 *
 * 결과는 **비어 있는 것이 정상인 자리에 남는 높이를 전부 주는 배분**이었다. 편집
 * 화면에 들어오면 화면의 절반이 아무 말도 하지 않았다.
 *
 * ## 무엇을 고치고 무엇을 지키는가
 *
 * **구현은 그대로 1벌이다** (FR-229 · SC-001). 항목과 순서도 그대로다 (FR-231).
 * 바뀌는 것은 **거는 자리**뿐이며, 그것을 국면이 정하되 **표가 정본**이다 —
 * `VERTICAL_SPLIT` 과 같은 규율이고 이유도 같다. 컴포넌트가 스스로 판단하면 그 판단이
 * 두 곳으로 갈리고, 갈리는 순간이 S-05 다.
 *
 * FR-230(자리가 모든 국면에서 같다)은 이 표로 대체된다. 명세 개정이 필요하며
 * `docs/design/008-visual-language/replacement-map.md` §5 에 등록했다.
 */
export type DetailPlacement = "overlay" | "inline";

export const DETAIL_PLACEMENT: Record<Phase, DetailPlacement> = {
  /** 만들기 — 아직 Step 이 없다. 생기면 겹침으로 본다 */
  composing: "overlay",
  /** 미러를 보면서 하는 국면들은 전부 겹침이다 — 미러를 가리지 않아야 한다 */
  recording: "overlay",
  ai_authoring: "overlay",
  takeover: "overlay",
  running: "overlay",
  paused: "overlay",
  /** 끝난 실행의 기록. 산출물을 보면서 대조하므로 겹침이다 */
  result: "overlay",
  /**
   * 편집 — **인라인이다.**
   *
   * 이 국면에는 미러가 없다 (③-a 가 88px 로 줄어 있다). 가릴 것이 없고, 고치는 일이
   * 이 국면의 주 작업이므로 주 작업 자리에 있어야 한다 (FR-257·FR-261).
   */
  editing: "inline",
};

/** 「내용에 맞는 높이」자리의 상한. 1회차 값을 그대로 쓴다. */
export const CONTENT_MAX_HEIGHT = "45%";

export interface SlotStyle {
  flex: string;
  minHeight: number;
  maxHeight?: string;
  overflowY: "auto";
}

/**
 * 배분을 CSS 값으로. **`Workbench` 만 부른다.**
 *
 * 최소·최대 높이가 여기 있는 이유: 표시 컴포넌트가 42px·45% 를 알 필요가 없다. 1회차에는
 * `PhaseAside` 가 그 둘을 자기 파일에 하드코딩했고, `maxHeight: 45%` 는 **`fill` 자리를
 * 무력화한다** — 편집 국면에서 편집면이 남는 높이 전부를 가져야 하는데 45% 에서 잘린다.
 * 상한은 `content` 에만 붙는다.
 */
export function flexOf(size: SlotSize): SlotStyle {
  switch (size.kind) {
    case "fill":
      // 단위를 명시한다 — 브라우저가 `1 1 0` 을 `1 1 0px` 로 정규화하므로 왕복이 되게 한다
      return { flex: "1 1 0px", minHeight: 0, overflowY: "auto" };
    case "content":
      // 내용이 정하는 높이이므로 상한이 필요하다 — 없으면 검증 추가 폼이 미러를 밀어낸다
      return {
        flex: "0 0 auto",
        minHeight: CONTENT_MIN_HEIGHT,
        maxHeight: CONTENT_MAX_HEIGHT,
        overflowY: "auto",
      };
    case "fixed":
      return { flex: `0 0 ${size.px}px`, minHeight: size.px, overflowY: "auto" };
  }
}

/** 그 국면의 배분. `Workbench` 가 한 번 조회한다. */
export function splitFor(phase: Phase): VerticalSplit {
  return VERTICAL_SPLIT[phase];
}
