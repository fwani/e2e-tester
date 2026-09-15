/**
 * 탭. 017 T058.
 *
 * 출처: shadcn new-york-v4/tabs @ shadcn 4.21.0 (2026-09-15) — `Tabs`·`TabsList`·`TabsTrigger`·`TabsContent` 의 구조와
 * `data-slot` 을 가져왔다. 클래스는 정본 `.tabs`·`.tabs > button` 으로 옮겼다 — contracts/ui-parts.md §2 의
 * `data-[state=active]:bg-background data-[state=active]:shadow-sm` → `data-[state=active]:bg-panel
 * data-[state=active]:text-ink`. 원본의 `rounded-lg`·`bg-muted`·`p-[3px]`·`h-9`·`focus-visible:ring-[3px]`·
 * `transition-[color,box-shadow]` 은 남지 않는다.
 *
 * **표에 없는 변경 하나** — 뿌리(`Tabs`)가 `asChild` 를 받는다. 탭 줄과 내용을 감싸는 판(테두리·바탕)은 화면의
 * 요소이고, 부품이 `<div>` 를 하나 더 두면 판 안의 세로 배치(`flex-col`)가 한 겹 멀어진다.
 *
 * ## 017 전
 *
 * `ui/Table` 의 `Tabs`(부모가 `[&>button]` 로 자식 단추를 칠하던 형태)와 `TargetPane` 의 **같은 클래스 복사본**이
 * 있었다. 자식이 원시 `<button aria-pressed>` 라 보조기술에는 「눌린 단추 넷」으로 들렸고 화살표로 오갈 수 없었다.
 * 이제 `tablist`·`tab`(`aria-selected`)·`tabpanel` 이고 ←·→ 로 오간다 (FR-013 · ui-parts §4).
 *
 * ## 탭 단추의 높이는 정하지 않는다
 *
 * 정본 요소 규칙 `button{height:var(--h-control)}` 이 준다 — 017 전과 같은 값이다. 줄의 높이는 부르는 쪽이 정한다.
 */
import { Tabs as TabsPrimitive } from "radix-ui";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "./cn";

type LayoutProps = { layout?: string; children?: ReactNode };

/** 뿌리. 모양이 없다 — `asChild` 로 화면의 판을 뿌리로 쓸 수 있다 (머리주석). */
export function Tabs({ layout, children, ...rest }: Omit<ComponentPropsWithRef<typeof TabsPrimitive.Root>, "className"> & LayoutProps) {
  return (
    <TabsPrimitive.Root className={layout} data-slot="tabs" {...rest}>
      {children}
    </TabsPrimitive.Root>
  );
}

/** 정본 `.tabs` — 옅은 우물 바탕의 줄 · 아래 실선. 탭은 줄 높이만큼 늘어난다. */
export function TabsList({ layout, children, ...rest }: Omit<ComponentPropsWithRef<typeof TabsPrimitive.List>, "className"> & LayoutProps) {
  return (
    <TabsPrimitive.List className={cn("bg-sunken border-b border-hair-2 flex items-stretch", layout)} data-slot="tabs-list" {...rest}>
      {children}
    </TabsPrimitive.List>
  );
}

/**
 * 정본 `.tabs > button` — 오른쪽 실선으로 칸을 가르고, 모노 11px 대문자 간격. 고른 탭은 판 바탕(`bg-panel`)으로
 * 줄에서 떠오른다. 비활성 탭은 **실선** 테두리에 흐린 글자다 (015 S-11 — 요소 규칙의 점선을 되돌린다).
 */
const TRIGGER =
  "border-0 border-r border-hair-2 rounded-none bg-transparent shadow-none px-s4 " +
  "font-mono text-[11px] font-semibold leading-none tracking-[0.1em] text-ink-2 cursor-pointer " +
  "data-[state=active]:bg-panel data-[state=active]:text-ink " +
  "disabled:border-solid disabled:text-ink-3 disabled:cursor-not-allowed";

export function TabsTrigger({ layout, children, ...rest }: Omit<ComponentPropsWithRef<typeof TabsPrimitive.Trigger>, "className"> & LayoutProps) {
  return (
    <TabsPrimitive.Trigger className={cn(TRIGGER, layout)} data-slot="tabs-trigger" {...rest}>
      {children}
    </TabsPrimitive.Trigger>
  );
}

/** 고른 탭의 내용. 모양이 없다 — 여백·스크롤은 부르는 쪽의 자리다. */
export function TabsContent({ layout, children, ...rest }: Omit<ComponentPropsWithRef<typeof TabsPrimitive.Content>, "className"> & LayoutProps) {
  return (
    <TabsPrimitive.Content className={layout} data-slot="tabs-content" {...rest}>
      {children}
    </TabsPrimitive.Content>
  );
}
