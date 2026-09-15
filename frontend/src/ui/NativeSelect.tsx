/**
 * 선택칸 — **네이티브 `<select>`**. 017 T031.
 *
 * 출처: shadcn new-york-v4/native-select @ shadcn 4.21.0 (2026-09-15) — 네이티브 `<select>` 를 쓴다는 결정과
 * `NativeSelect`·`NativeSelectOption`·`data-slot` 이름을 가져왔다. **원본의 감싸개 `div` 와 `appearance-none`
 * + 펼침 아이콘은 들이지 않았다** — 정본의 선택칸은 브라우저의 펼침 표시를 그대로 쓰고, 아이콘을 새로
 * 그리면 정본에 없는 모양이 생긴다(사용자 결정 1). 원본의 `h-8`·`rounded-lg`·`focus-visible:ring-3`·
 * `disabled:pointer-events-none` 도 남지 않는다.
 *
 * ## 왜 Radix `Select` 가 아닌가 (017 research R2)
 *
 * 쓰는 자리 넷이 전부 짧은 목록이다. 네이티브는 첫 글자 이동·키보드 선택·폼 제출을 이미 갖고(FR-017),
 * Radix `Select` 는 jsdom 에서 클릭만 해도 예외를 던지며 번들이 5.8 kB 늘어난다. 테스트 8곳이 `fireEvent.change`
 * 로 고른다.
 *
 * ## 폭은 **내용만큼**이 기본이다 (B-07) — 축으로 둔다
 *
 * 정본 요소 규칙 `input,select,textarea{width:100%}` 가 선택칸에도 번져, 테스트 목록 선택 띠의
 * 「그룹으로 옮기기」 선택칸이 남은 폭 전부로 늘어났다. 이 부품은 `width="content"`(`w-auto`)를 기본으로
 * 명시해 번짐을 끊는다.
 *
 * 폼 안에서 위아래 칸과 폭을 맞춰야 하는 자리는 `width="fill"` 을 준다. **폭을 `layout` 으로 넘기지 않는다**
 * — `layout="w-full"` 은 부품의 `w-auto` 와 같은 속성을 다투고, 이기는 쪽을 산출 CSS 순서가 정한다
 * (015 의 흰 버튼과 같은 형태). 최대 폭(`max-w-*`)은 다른 속성이므로 `layout` 에 둬도 된다.
 */
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef } from "react";

import { cn } from "./cn";

export type NativeSelectWidth = "content" | "fill";

/**
 * 정본 `input,select,textarea{…}` 의 모양 + 비활성 점선 (015 state-styles S-07).
 *
 * 높이는 정본 요소 규칙(`min-height:32px`)에 맡긴다. 커서는 바꾸지 않는다 — 정본이 정하지 않았다.
 */
export const nativeSelectVariants = cva(
  "px-[10px] border border-hair-2 rounded-base font-sans text-[13px] font-normal leading-[1.4] bg-panel text-ink " +
    "disabled:bg-transparent disabled:border-dashed disabled:text-ink-3 " +
    // `aria-invalid:` 는 Tailwind v4 에 없는 변종이다 — `ui/Input` 주석 참조.
    "aria-[invalid=true]:border-fail",
  {
    variants: {
      width: {
        content: "w-auto",
        fill: "w-full",
      },
    },
    defaultVariants: { width: "content" },
  },
);

export interface NativeSelectProps extends Omit<ComponentPropsWithRef<"select">, "className"> {
  /** 머리주석 「폭은 내용만큼이 기본이다」. */
  readonly width?: NativeSelectWidth;
  /** **배치만** — 여백·최대 폭·줄어듦. 폭 자체는 `width` 로 정한다. */
  readonly layout?: string;
}

export function NativeSelect({ width = "content", layout, children, ...rest }: NativeSelectProps) {
  return (
    <select className={cn(nativeSelectVariants({ width }), layout)} data-slot="native-select" {...rest}>
      {children}
    </select>
  );
}

export function NativeSelectOption(props: Omit<ComponentPropsWithRef<"option">, "className">) {
  return <option data-slot="native-select-option" {...props} />;
}
