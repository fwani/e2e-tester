/**
 * 칩 — shadcn/ui `badge` 를 정본 `.chip` 모습으로 이식한 부품. 017 T027.
 *
 * 출처: shadcn new-york-v4/badge @ shadcn 4.21.0 (2026-09-15) — 구조(`cva` 의 한 축 · `data-slot`)를
 * 가져오고 클래스는 contracts/ui-parts.md §2 대응표대로 정본으로 옮겼다. 원본의 `rounded-full`·
 * `bg-primary`·`focus-visible:ring`·`[a&]:hover` 는 남지 않는다. `asChild` 는 들이지 않았다 — 칩을
 * 링크로 그리는 자리가 없고, 누를 수 있는 칩(그룹 거르기)은 버튼이 `chipClasses` 를 쓴다.
 *
 * 상태를 **색과 형태로 함께** 말한다. 정본 주석이 「색만으로 구분하지 않는다」고 적었고, 그것이
 * 접근성 요건이다 — 칩 안의 글자가 상태를 말하고 색은 거든다.
 *
 * ## 값이 부품에 있는 이유 (015 에서 이어짐)
 *
 * `gap:5px` · `height:19px` · `padding:0 6px` · `10px` 글자 · `letter-spacing:.06em` 은 정본에도
 * 토큰이 아니라 리터럴이었다. 화면 38곳으로 흩어지면 008 이 고친 문제의 재발이다.
 *
 * ## 상태 색은 정본 토큰을 쓴다
 *
 * `--pass`·`--pass-t` 처럼 짝으로 있는 토큰을 그대로 참조한다. 새 색을 만들지 않는다.
 */
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "./cn";

/** 정본의 `.chip.{pass,fail,warn,run,ai,off}`. `default` 는 수식 없는 `.chip`. */
export type ChipTone = "default" | "pass" | "fail" | "warn" | "run" | "ai" | "off";

export interface ChipProps extends Omit<ComponentPropsWithRef<"span">, "className"> {
  readonly tone?: ChipTone;
  /** **배치만.** 모양은 `tone` 으로 정한다 (`ui/Button` 의 `layout` 과 같은 규율). */
  readonly layout?: string;
  readonly children?: ReactNode;
}

/**
 * 정본 `.chip`. 바탕은 모양이고 `tone` 이 테두리·글자·배경 **셋을 함께** 정한다.
 *
 * **덧칠이 아니라 전부다.** `default` 도 색 셋을 적는다. 바탕에 두고 덮어쓰게 하면 덮이지 않는다 —
 * `.bg-sunken-2` 가 `.bg-pass-t` 보다 산출 CSS 에서 뒤에 오므로 상태 배경이 전부 회색으로 그려지고
 * 있었다 (2026-09-11). 가드 G-E 가 `cva` 조합 전부를 산출 CSS 순서와 대조한다.
 */
export const chipVariants = cva(
  "inline-flex items-center gap-[5px] h-[19px] px-[6px] border rounded-chip " +
    "font-mono text-[10px] font-semibold leading-none tracking-[.06em]",
  {
    variants: {
      tone: {
        default: "border-hair-2 text-ink-2 bg-sunken-2",
        pass: "border-pass text-pass bg-pass-t",
        fail: "border-fail text-fail bg-fail-t",
        warn: "border-warn text-warn bg-warn-t",
        run: "border-run text-run bg-run-t",
        ai: "border-ai text-ai bg-ai-t",
        // 정본 `.chip.off` — 미실행. 점선이고 자리를 지킨다. **테두리 색은 기본과 같다** — 정본이
        // `border-style` 만 바꾸고 `.chip` 의 `border-color:var(--hair-2)` 를 남긴다.
        off: "border-dashed border-hair-2 text-ink-3 bg-transparent",
      },
    },
    defaultVariants: { tone: "default" },
  },
);

/**
 * 칩의 클래스. **`<span>` 이 아닌 칩도 이것을 쓴다** — 누를 수 있는 그룹 거르기 칩(`TestGroupBar`)이
 * 자기 힘으로 칩 모양을 조립하면 같은 종류의 표식이 두 모습을 갖는다 (SC-010). 017 T061 에서 그 자리가
 * `ToggleGroup` 으로 옮겨 가면 이 함수를 쓰는 곳이 사라진다.
 */
export function chipClasses(tone: ChipTone = "default", layout?: string): string {
  return cn(chipVariants({ tone }), layout);
}

/**
 * 정본 `.pill` — 칩보다 한 치수 큰 표식. 프로젝트 이름·「초안」처럼 **머리띠에서 지금 무엇을 다루는지**를
 * 말하는 자리에 쓴다. 015 T028 이 화면 세 곳에서 따로 조립되던 것을 한 곳으로 모았다.
 */
export function Pill({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<"span">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = cn(
    "h-control-sm inline-flex items-center gap-[7px] px-[9px] border border-hair-2 rounded-base bg-panel text-ink " +
      "font-sans text-[12px] font-semibold leading-none shadow-none",
    layout,
  );
  return (
    <span className={cls} data-slot="pill" {...rest}>
      {children}
    </span>
  );
}

export function Chip({ tone = "default", layout, children, ...rest }: ChipProps) {
  const cls = chipClasses(tone, layout);
  // `data-tone` 으로 의도를 내보낸다. 검사가 유틸리티 조합 대신 이것을 읽으면 「이 칩이 실패를 말하는가」
  // 라는 질문이 살아남는다 (LC-4 ②).
  return (
    <span className={cls} data-slot="chip" data-tone={tone} {...rest}>
      {children}
    </span>
  );
}
