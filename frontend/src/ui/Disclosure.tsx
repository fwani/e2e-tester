/**
 * 접었다 펴는 자리 — **네이티브 `<details>`**. 017 T065.
 *
 * 출처: 015 — 화면마다 `<details>`·`<summary>` 에 글자 모양을 따로 입히던 자리(10곳)와 `StepDetail` 의 ▸/▾ 수제 토글(3곳)을
 * 한 부품으로 모았다. Radix `Collapsible` 은 쓰지 않는다 (research R2) — 네이티브가 Enter·Space 토글과 펼침 상태 알림을
 * 이미 갖고, 찾기(Ctrl+F)가 접힌 내용도 연다.
 *
 * ## 017 전
 *
 * - `<details>` 10곳의 요약 줄이 **세 모양**이었다 — 11px 흐린 글자 · 13px 굵은 글자 · 13.5px 굵은 글자. 표식은 브라우저
 *   기본 삼각형이었다.
 * - `StepDetail` 의 세 토글은 `<details>` 가 아니라 **단추**가 `▸`/`▾` 글자를 바꿔 그렸다. 보조기술에는 무엇이 펼쳐졌는지가
 *   없었다(`aria-expanded` 없음).
 *
 * ## 표식은 하나다
 *
 * 브라우저 기본 삼각형을 지우고 `▸`(접힘)·`▾`(펼침) 글자를 쓴다 — `StepDetail` 토글이 쓰던 것이며 글자 기호 규칙
 * (ui-parts §0-6)이다. 어느 글자를 보일지는 **CSS 가 `details[open]` 으로 정한다** — 펼침 상태를 두 곳에 두지 않는다.
 *
 * ## 요약 줄 세 모양 (`tone`)
 *
 * | tone | 글자 | 자리 |
 * |---|---|---|
 * | `quiet` | 정본 `.why` — 11px · ink-3 | 옮긴 자리 · 바뀐 식별자 · 잘린 칸 · 머리글 행 · 열 짝짓기 · 번호가 바뀐 행 · 건너뛴 행 |
 * | `strong` | 13px · 600 · ink | 건너뛸 행(확정 전) · 엑셀 파일을 더 넣기 |
 * | `action` | 정본 `.navlink` — 13px · 500 · ink-2 · hover 우물 | Step 상세의 비밀 값 넣기 · DSL 미리보기 — 조작처럼 읽히는 자리 |
 */
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef, ReactNode } from "react";

export type DisclosureTone = "quiet" | "strong" | "action";

export const disclosureSummaryVariants = cva(
  "inline-flex items-center gap-[6px] cursor-pointer select-none [&::-webkit-details-marker]:hidden",
  {
    variants: {
      tone: {
        quiet: "font-sans text-[11px] leading-[1.4] font-normal text-ink-3",
        strong: "font-sans text-[13px] font-semibold leading-none text-ink",
        action: "h-[28px] px-[10px] rounded-base font-sans text-[13px] font-medium leading-none text-ink-2 hover:bg-sunken",
      },
    },
    defaultVariants: { tone: "quiet" },
  },
);

export interface DisclosureProps extends Omit<ComponentPropsWithRef<"details">, "className" | "onToggle" | "children"> {
  /** 요약 줄의 글. 표식(▸·▾)은 부품이 붙인다. */
  readonly summary: ReactNode;
  readonly tone?: DisclosureTone;
  /** 펼침이 바뀌었을 때. 펼침을 화면 상태로 쥐는 자리(다른 Step 을 고르면 접는다)가 쓴다. */
  readonly onOpenChange?: (open: boolean) => void;
  /** **배치만** — 위 간격·폭. */
  readonly layout?: string;
  readonly children?: ReactNode;
}

export function Disclosure({ summary, tone = "quiet", onOpenChange, layout, children, ...rest }: DisclosureProps) {
  return (
    <details
      className={layout}
      data-slot="disclosure"
      onToggle={onOpenChange === undefined ? undefined : (event) => onOpenChange(event.currentTarget.open)}
      {...rest}
    >
      <summary className={disclosureSummaryVariants({ tone })} data-slot="disclosure-summary">
        {/* 접힘 · 펼침 표식. 낭독기는 요약 줄의 펼침 상태를 따로 알리므로 글자는 숨긴다. */}
        <span aria-hidden="true" className="[details[open]>summary>&]:hidden">
          ▸
        </span>
        <span aria-hidden="true" className="hidden [details[open]>summary>&]:inline">
          ▾
        </span>
        {summary}
      </summary>
      {children}
    </details>
  );
}
