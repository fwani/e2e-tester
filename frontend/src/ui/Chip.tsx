/**
 * 칩 — 의미 클래스 `.chip` 계열이 해체되어 온 곳. 015 T020.
 *
 * 상태를 **색과 형태로 함께** 말한다. 정본 주석이 「색만으로 구분하지 않는다」고 적었고,
 * 그것이 접근성 요건이다 — 칩 안의 글자가 상태를 말하고 색은 거든다.
 *
 * ## 값이 부품에 있는 이유
 *
 * `gap:5px` · `height:19px` · `padding:0 6px` · `10px` 글자 · `letter-spacing:.06em` 은
 * 정본에도 토큰이 아니라 리터럴이었다. 화면 38곳으로 흩어지면 008 이 고친 문제의 재발이다
 * (`ui/Button` 머리주석과 같은 이유).
 *
 * ## 상태 색은 정본 토큰을 쓴다
 *
 * `--pass`·`--pass-t` 처럼 짝으로 있는 토큰을 그대로 참조한다. 새 색을 만들지 않는다
 * (FR-003 · 008 규율).
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

/** 정본의 `.chip.{pass,fail,warn,run,ai}`. `default` 는 수식 없는 `.chip`. */
export type ChipTone = "default" | "pass" | "fail" | "warn" | "run" | "ai" | "off";

export interface ChipProps extends Omit<ComponentPropsWithRef<"span">, "className"> {
  readonly tone?: ChipTone;
  /** **배치만.** 모양은 `tone` 으로 정한다 (`ui/Button` 의 `layout` 과 같은 규율). */
  readonly layout?: string;
  readonly children?: ReactNode;
}

/**
 * 정본 `.chip` 을 그대로 옮긴 것.
 *
 * `h-[19px]`·`gap-[5px]`·`px-[6px]`·`text-[10px]`·`tracking-[.06em]` 은 정본에 토큰이
 * 없는 값이다. `rounded-chip` 은 `--radius-chip` 토큰이 있으므로 반드시 토큰을 쓴다.
 */
const BASE =
  "inline-flex items-center gap-[5px] h-[19px] px-[6px] " +
  "border rounded-chip " +
  "font-mono text-[10px] font-semibold leading-none tracking-[.06em]";

/**
 * 상태별 색. **`Record` 로 두어 상태가 늘 때 빠뜨릴 수 없게 한다.**
 * 셋 다(테두리·글자·배경) 함께 바꾸는 것이 정본의 규율이다 — 하나만 바꾸면
 * 대비가 무너져 글자가 배경에 묻힌다.
 *
 * **덧칠이 아니라 전부다.** `default` 도 색 셋을 적는다. BASE 에 두고 덮어쓰게 하면
 * 덮이지 않는다 — `.bg-sunken-2` 가 `.bg-pass-t` 보다 산출 CSS 에서 뒤에 오므로
 * 상태 배경이 전부 회색으로 그려지고 있었다 (2026-09-11, `ui/Button` 과 같은 원인).
 * 가드 `tests/ClassConflict.test.ts`(G-E)가 막는다.
 */
const TONE: Record<ChipTone, string> = {
  default: "border-hair-2 text-ink-2 bg-sunken-2",
  pass: "border-pass text-pass bg-pass-t",
  fail: "border-fail text-fail bg-fail-t",
  warn: "border-warn text-warn bg-warn-t",
  run: "border-run text-run bg-run-t",
  ai: "border-ai text-ai bg-ai-t",
  // 정본 `.chip.off` — 미실행. 점선이고 자리를 지킨다. **테두리 색은 기본과 같다** —
  // 정본이 `border-style` 만 바꾸고 `.chip` 의 `border-color:var(--hair-2)` 를 남긴다.
  off: "border-dashed border-hair-2 text-ink-3 bg-transparent",
};

/**
 * 칩의 클래스. **`<span>` 이 아닌 칩도 이것을 쓴다.**
 *
 * 그룹 거르기(`TestGroupBar`)의 칩은 누를 수 있어야 하므로 `<button>` 이다. 그 자리가
 * 자기 힘으로 칩 모양을 조립하면 같은 종류의 표식이 두 모습을 갖는다 (SC-010).
 */
export function chipClasses(tone: ChipTone = "default", layout?: string): string {
  return [BASE, TONE[tone], layout].filter(Boolean).join(" ");
}

export function Chip({ tone = "default", layout, children, ...rest }: ChipProps) {
  // 클래스를 조립하지 않는다 — 표에서 완성된 문자열을 꺼내 이을 뿐이다 (가드 G-B).
  const cls = chipClasses(tone, layout);
  // `data-tone` 으로 의도를 내보낸다. 검사가 유틸리티 조합 대신 이것을 읽으면
  // 「이 칩이 실패를 말하는가」라는 질문이 살아남는다 (LC-4 ②).
  return (
    <span className={cls} data-tone={tone} {...rest}>
      {children}
    </span>
  );
}
