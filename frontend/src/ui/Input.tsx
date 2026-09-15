/**
 * 한 줄 입력. 017 T029.
 *
 * 출처: shadcn new-york-v4/input @ shadcn 4.21.0 (2026-09-15) — 네이티브 `<input>` 을 감싸는 구조와 `data-slot` 을
 * 가져오고, 클래스는 정본 `input,select,textarea{}` · `.field input` · `input.phase-name` 으로 옮겼다. 원본의
 * `h-9`·`rounded-md`·`shadow-xs`·`file:*`·`focus-visible:ring-[3px]`·`disabled:opacity-50`·`md:text-sm` 은
 * 남지 않는다.
 *
 * ## 네 모양
 *
 * | variant | 정본 | 자리 |
 * |---|---|---|
 * | `default` | `input,select,textarea{…}` + `input:disabled` (S-07) | 폼의 입력칸 |
 * | `ai` | 위와 같고 테두리만 `--ai` (`textarea.ai` 와 같은 문법) | AI 에게 건네는 자연어 한 줄 |
 * | `bare` | `.field input` | 테두리 상자(`ui/Field`) 안의 입력 — 테두리·초점 링은 **상자가** 그린다 |
 * | `title` | `input.phase-name` (S-08~S-10) | 국면 띠의 테스트 이름 — 평소 제목처럼 보이고 hover·초점에 테두리가 드러난다 |
 *
 * ## 글꼴은 축으로 둔다 (`font`)
 *
 * 주소·셀렉터·확인 문구처럼 **글자를 그대로 옮겨 적어야 하는 칸**은 모노 글꼴이다. 017 전에는 화면이
 * `className="font-mono"` 를 입혔고, 한 곳(`ActionPalette`)은 정본 클래스 `mono` 를 문자열로 넘겼다 —
 * 015 가 정본 클래스를 번들에서 뺀 뒤로 **아무 CSS 도 만들지 않는 이름**이었다(017 N-03). `layout` 으로
 * 넘기면 부품의 `font-sans` 와 같은 속성을 다투므로(승부는 산출 CSS 순서가 정한다) 이 표에 둔다.
 *
 * ## 폭·높이는 여기서 정하지 않는다 (`default`·`ai`)
 *
 * 정본 요소 규칙이 `width:100%` · `min-height:var(--h-control)` 을 이미 준다(`layer(base)`). 부품이 같은 값을
 * 유틸리티로 또 적으면 호출부의 `layout`(`w-[180px]` 따위)과 **같은 속성을 다투고**, 이기는 쪽을 산출 CSS
 * 순서가 정한다 — 015 의 흰 버튼과 같은 형태다. 요소 규칙은 어떤 유틸리티에도 지므로 비워 두면 호출부가
 * 늘 이긴다. `bare`·`title` 은 정본이 크기를 **바꾸는** 자리라 명시한다.
 *
 * ## 초점 링을 지우는 두 자리 — 예외로 등록돼 있다
 *
 * `bare` 는 상자가 `focus-within` 링을 그리므로 안쪽 링을 벗는다(017 N-01). `title` 은 링 대신 테두리와 바탕이
 * 드러나 초점을 말한다(정본이 `outline:none` 으로 정했다). 둘 다 `theme/exceptions.ts` 에 이유와 함께 있다.
 */
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef } from "react";

import { cn } from "./cn";

export type InputVariant = "default" | "ai" | "bare" | "title";
export type InputFont = "sans" | "mono";

export const inputVariants = cva("", {
  variants: {
    variant: {
      // 폼 칸의 모양은 아래 `compoundVariants` 가 둘에 함께 준다. 여기는 **테두리 색만** 갈린다.
      default: "border-hair-2",
      ai: "border-ai",
      bare:
        "flex-1 min-h-auto p-0 border-0 bg-transparent shadow-none outline-none " +
        "text-[13px] leading-none placeholder:text-ink-3",
      title:
        "w-auto min-h-[26px] px-[6px] border border-transparent bg-transparent text-ink " +
        "text-[17px] font-bold leading-none whitespace-nowrap overflow-hidden text-ellipsis " +
        "enabled:hover:border-hair-2 focus:border-hair-2 focus:bg-panel focus:outline-none " +
        "disabled:border-transparent disabled:text-ink-2",
    },
    font: {
      sans: "font-sans",
      mono: "font-mono",
    },
  },
  compoundVariants: [
    {
      variant: ["default", "ai"],
      class:
        "px-[10px] border rounded-base text-[13px] font-normal leading-[1.4] " +
        "bg-panel text-ink placeholder:text-ink-3 " +
        // `aria-invalid:` 는 Tailwind v4 에 **없는** 변종이다(불리언 aria 변종 목록에 invalid 가 없다) — 쓰면 아무 CSS 도
        // 생기지 않는다. 가드 G-B 가 잡았다. 표준 형태 `aria-[invalid=true]:` 를 쓴다.
        "disabled:bg-transparent disabled:border-dashed disabled:text-ink-3 aria-[invalid=true]:border-fail",
    },
  ],
  defaultVariants: { variant: "default", font: "sans" },
});

export interface InputProps extends Omit<ComponentPropsWithRef<"input">, "className"> {
  readonly variant?: InputVariant;
  /** 옮겨 적어야 하는 글자(주소·셀렉터·변수 이름·확인 문구)는 `mono`. */
  readonly font?: InputFont;
  /** **배치만** — 폭·여백·줄어듦. 모양은 `variant`·`font` 로 정한다. */
  readonly layout?: string;
}

export function Input({ variant = "default", font = "sans", layout, ...rest }: InputProps) {
  return (
    <input
      className={cn(inputVariants({ variant, font }), layout)}
      data-slot="input"
      data-variant={variant}
      {...rest}
    />
  );
}
