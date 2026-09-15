/**
 * 여러 줄 입력. 017 T030.
 *
 * 출처: shadcn new-york-v4/textarea @ shadcn 4.21.0 (2026-09-15) — 네이티브 `<textarea>` 를 감싸는 구조와
 * `data-slot` 을 가져오고, 클래스는 정본 `input,select,textarea{}` · `textarea{}` · `textarea.ai` 로
 * 옮겼다. 원본의 `field-sizing-content`·`min-h-16`·`rounded-md`·`shadow-xs`·`focus-visible:ring`·
 * `disabled:opacity-50` 은 남지 않는다.
 *
 * ## 폭·높이는 여기서 정하지 않는다
 *
 * 정본 요소 규칙이 `width:100%` · `min-height:var(--h-control)` 을 이미 준다(`layer(base)`). 부품이 같은
 * 값을 유틸리티로 또 적으면 호출부의 `layout`(`min-h-[120px]` 따위)과 **같은 속성을 다투게 되고**,
 * 이기는 쪽을 산출 CSS 순서가 정한다 — 015 의 흰 버튼과 같은 형태다. 요소 규칙은 어떤 유틸리티에도
 * 지므로, 폭·높이를 비워 두면 호출부가 늘 이긴다.
 *
 * ## 미러의 한글 조합 칸은 이것을 쓰지 않는다
 *
 * 보이지 않고 포인터를 받지 않는 칸이라 모양이 전부 방해가 된다 — `theme/exceptions.ts` 에 원시 요소
 * 예외로 등록돼 있다 (017 contracts/ui-parts.md §3).
 */
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef } from "react";

import { cn } from "./cn";

export type TextareaVariant = "default" | "ai";

/**
 * 정본 `textarea{padding:8px 10px;line-height:1.5}` + `input,select,textarea{…}` 의 모양.
 *
 * `ai` 는 정본 `textarea.ai{border-color:var(--ai)}` — AI 가 쓰는 지시문 칸이 사람이 쓰는 칸과 갈리는
 * 유일한 자리다. **테두리 색만 다르다** — 두 값이 각자 온전히 갖는다 (같은 속성을 덮어쓰지 않는다).
 */
export const textareaVariants = cva(
  "py-[8px] px-[10px] border rounded-base font-sans text-[13px] font-normal leading-[1.5] " +
    "bg-panel text-ink placeholder:text-ink-3 " +
    "disabled:bg-transparent disabled:border-dashed disabled:text-ink-3 disabled:cursor-not-allowed " +
    // `aria-invalid:` 는 Tailwind v4 에 없는 변종이다 — `ui/Input` 주석 참조.
    "aria-[invalid=true]:border-fail",
  {
    variants: {
      variant: {
        default: "border-hair-2",
        ai: "border-ai",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface TextareaProps extends Omit<ComponentPropsWithRef<"textarea">, "className"> {
  readonly variant?: TextareaVariant;
  /** **배치만** — 높이·폭·여백. 모양은 `variant` 로 정한다. */
  readonly layout?: string;
}

export function Textarea({ variant = "default", layout, ...rest }: TextareaProps) {
  return (
    <textarea
      className={cn(textareaVariants({ variant }), layout)}
      data-slot="textarea"
      data-variant={variant}
      {...rest}
    />
  );
}
