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
 * ## 폭은 **내용만큼**이 기본이다 (B-07)
 *
 * 정본 요소 규칙 `input,select,textarea{width:100%}` 가 선택칸에도 번져, 테스트 목록 선택 띠의
 * 「그룹으로 옮기기」 선택칸이 남은 폭 전부로 늘어났다. 이 부품은 `w-auto` 를 기본으로 명시해 번짐을 끊는다.
 * 폭이 필요한 자리는 `layout` 으로 준다.
 */
import type { ComponentPropsWithRef } from "react";

import { cn } from "./cn";

export interface NativeSelectProps extends Omit<ComponentPropsWithRef<"select">, "className"> {
  /** **배치만** — 폭·여백. 모양은 부품이 정한다. */
  readonly layout?: string;
}

/**
 * 정본 `input,select,textarea{…}` 의 모양 + 비활성 점선 (015 state-styles S-07).
 *
 * 폭만 기본값을 바꾼다 — 머리주석 「폭은 내용만큼」. 높이는 정본 요소 규칙(`min-height:32px`)에 맡긴다.
 */
const SELECT =
  "w-auto px-[10px] border border-hair-2 rounded-base font-sans text-[13px] font-normal leading-[1.4] " +
  "bg-panel text-ink cursor-pointer " +
  "disabled:bg-transparent disabled:border-dashed disabled:text-ink-3 disabled:cursor-not-allowed " +
  // `aria-invalid:` 는 Tailwind v4 에 없는 변종이다 — `ui/Input` 주석 참조.
  "aria-[invalid=true]:border-fail";

export function NativeSelect({ layout, children, ...rest }: NativeSelectProps) {
  return (
    <select className={cn(SELECT, layout)} data-slot="native-select" {...rest}>
      {children}
    </select>
  );
}

export function NativeSelectOption(props: Omit<ComponentPropsWithRef<"option">, "className">) {
  return <option data-slot="native-select-option" {...props} />;
}
