/**
 * 결말 어휘 → 확정 디자인의 형태 이름. 008.
 *
 * `lib/wording.ts` 의 `outcomeTone()` 은 결말 넷을 **뜻**으로 옮긴다
 * (`success`·`danger`·`neutral`·`warn`·`unknown`). 확정 디자인의 형태 이름은 다르다
 * (`.chip.pass`·`.chip.fail`·`.chip.warn`·`.chip.off`). 이 파일이 그 사이를 잇는 **유일한**
 * 자리다.
 *
 * ## 왜 필요했나
 *
 * 008 전까지 화면은 `className={`badge ${outcomeTone(outcome)}`}` 로 썼다. 시트에는
 * `.badge.pass`·`.badge.fail` 만 있었고 `success`·`danger` 규칙은 **없었다** — 통과한
 * 테스트의 표식이 아무 변형도 받지 못한 채 기본형으로 그려지고 있었다. 두 어휘가 말없이
 * 어긋난 형태이고, 잇는 자리가 없어서 아무도 그것을 볼 수 없었다.
 *
 * ## 왜 여기서 잇는가
 *
 * `wording.ts` 는 **말**을 정하고 여기는 **형태**를 정한다. 뜻 이름을 형태 이름으로 바꾸면
 * 화면마다 `outcome === "pass" ? …` 이 다시 생기고, 그것이 중지를 실패로 보이게 한 U-03 의
 * 형태다 (`tests/OutcomeVocabulary.test.tsx`).
 */
import { outcomeTone } from "../lib/wording";
import type { OutcomeTone } from "../lib/wording";
import type { Outcome } from "../types/generated/run-result";

/**
 * 뜻 → `.chip` 변형.
 *
 * `neutral`(중지)에는 변형을 주지 않는다 — 확정 디자인의 중립 표식이 기본형이다.
 * `unknown`(미실행)은 점선이고 자리를 지킨다.
 */
const CHIP_VARIANT = {
  success: "pass",
  danger: "fail",
  warn: "warn",
  neutral: "",
  unknown: "off",
} as const;

/**
 * 뜻 → 목록 행의 왼쪽 표식.
 *
 * 확정 디자인이 정의한 표식은 통과·실패·실행 중·선택 넷뿐이다. 중지와 부분 성공은 표식을
 * 갖지 않으며 **표식이 없다는 것 자체가 정보다** — 실패로 칠하면 U-03 이 되살아난다.
 * 결말은 같은 행의 표식(`.chip`)이 글자로 말한다.
 */
const ROW_VARIANT = {
  success: "pass",
  danger: "fail",
  warn: "",
  neutral: "",
  unknown: "",
} as const;

/**
 * 뜻에서 바로 표식 클래스를 얻는다.
 *
 * 국면 띠처럼 결말이 아니라 **국면의 뜻**을 이미 갖고 있는 자리가 쓴다 (`model.ts` 의
 * `phaseTone`). 그 자리가 뜻 이름을 형태 이름으로 직접 옮기면 이 매핑이 두 곳이 된다.
 */
export function chipClassForTone(tone: OutcomeTone): string {
  return `chip ${CHIP_VARIANT[tone]}`.trimEnd();
}

/** 결말 표식의 클래스. 넷을 전부 다룬다. */
export function chipClass(outcome: Outcome | null | undefined): string {
  return chipClassForTone(outcomeTone(outcome));
}

/** 목록 행의 클래스. 돌고 있으면 결말보다 그 사실이 이긴다 (005 FR-168 · U-16). */
export function rowClass(outcome: Outcome | null | undefined, running = false): string {
  return `trow ${running ? "run" : ROW_VARIANT[outcomeTone(outcome)]}`.trimEnd();
}
