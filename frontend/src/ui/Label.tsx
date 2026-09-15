/**
 * 라벨 — 폼 라벨 · 구획 라벨 · 칸 위 설명. 017 T028.
 *
 * 출처: shadcn new-york-v4/label @ shadcn 4.21.0 (2026-09-15) — 부품 이름과 `data-slot` 만 가져왔다.
 * 원본은 Radix `Label` 을 감싸는데 그것이 하는 일은 **글자 선택을 막는 것** 하나라 들이지 않는다
 * (017 research R2 · contracts/ui-parts.md §1). 모양은 정본 `label{}` · `.lbl` · `.field-label` 이다.
 *
 * ## 셋이 다른 이유
 *
 * | 부품 | 정본 | 무엇을 담나 |
 * |---|---|---|
 * | `Label` | `label { display:block; font:600 11px/1 mono; uppercase; margin:12px 0 6px }` | 입력칸 위의 이름 (`<label htmlFor>`) |
 * | `Lbl` | `.lbl` | 구획의 이름 — 한 낱말 (`TEST STEPS`) |
 * | `FieldLabel` | `.field-label` | 칸 위의 **문장** 설명 |
 *
 * **라벨 형태로 문장을 담지 않는다.** 11px 대문자 모노는 한 문장을 읽는 형태가 아니다 — 정본이 답 칸
 * (`.answer-q`)을 따로 둔 이유다.
 *
 * ## `Label` 이 정본 요소 규칙을 **명시**하는 이유
 *
 * 전역 `label{}` 은 폼 라벨을 위한 규칙인데 `<label>` 을 쓰는 모든 자리에 번진다 — 파일 선택 버튼이
 * 그 여백·자간·대문자를 받아 이웃 버튼보다 12px 내려앉았다 (015 `.btn.file` 주석). 부품이 값을 명시하면
 * 번짐에 기대지 않고, 폼 라벨이 아닌 `<label>`(파일 선택·체크박스 묶음)은 이 부품을 쓰지 않는다.
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "./cn";

type LayoutProps = { layout?: string; children?: ReactNode };

/** 입력칸 위의 이름. 정본 `label{}` 을 그대로 옮겼다. */
export function Label({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"label">, "className"> & LayoutProps) {
  const cls = cn(
    "block font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3 mt-s3 mb-[6px] mx-0",
    layout,
  );
  return (
    <label className={cls} data-slot="label" {...rest}>
      {children}
    </label>
  );
}

/**
 * 정본 `.lbl` — 구획 라벨. 11px 대문자 모노다.
 *
 * **문장을 담지 않는다** (머리주석 「셋이 다른 이유」).
 */
export function Lbl({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"span">, "className"> & LayoutProps) {
  const cls = cn("font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3", layout);
  return (
    <span className={cls} {...rest}>
      {children}
    </span>
  );
}

/** 정본 `.field-label` — 칸 위의 설명. 라벨(`Lbl`)과 다르다 — 이쪽은 문장이다. */
export function FieldLabel({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  const cls = cn("font-sans text-[12px] leading-none font-normal text-ink-3", layout);
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
