/**
 * 떠 있는 메뉴 — 행의 추가 동작. 017 T055.
 *
 * 출처: shadcn new-york-v4/dropdown-menu @ shadcn 4.21.0 (2026-09-15) — `DropdownMenu`·`DropdownMenuTrigger`·
 * `DropdownMenuContent`·`DropdownMenuItem` 의 구조(포털 · `data-slot` · 항목의 `variant="destructive"`)를 가져왔다. 이름은
 * contracts/ui-parts.md §1 대로 `Menu`·`MenuTrigger`·`MenuContent`·`MenuItem` 이고 위험 항목은 `variant="danger"` 다.
 * 클래스는 §2 대응표대로 옮겼다 — `bg-popover` → `bg-panel` · `border` → `border-hair-2` · `shadow-md` → `shadow-e2` ·
 * `rounded-md` → `rounded-base` · `p-1` → `p-[4px]` · `min-w-[8rem]` → `min-w-[160px]` · `z-50` → `z-40`
 * (layout-contract-v3 L1) · 항목 `focus:bg-accent` → `data-[highlighted]:bg-sunken` · `data-[variant=destructive]:
 * text-destructive` → `text-fail` · `data-[disabled]:opacity-50` → `data-[disabled]:text-ink-3`. 원본의
 * `data-[state=open]:animate-in`·`slide-in-from-*`·`outline-hidden`·`[&_svg]:size-4`, 체크·라디오 항목·하위 메뉴·단축키
 * 표시는 들이지 않았다 — 쓰는 자리가 없다.
 *
 * **표에 없는 변경 하나** — 닫힐 때 초점이 **이미 다른 조작에 가 있으면** 여는 단추로 되돌리지 않는다
 * (`onCloseAutoFocus`). 「이름」을 고르면 행 안에 이름 칸이 열리며 초점을 받는데, Radix 는 그 뒤에 초점을 단추로
 * 가져가 사용자가 적은 글자가 단추로 갔다.
 *
 * **실제 브라우저에서는 이 조건만으로 모자랐다** (2026-09-15 브라우저 확인). 메뉴가 열린 동안 초점을 가두므로 새로
 * 연 칸의 `autoFocus` 가 들어가지 않고, 닫히는 순간 초점은 문서 바닥에 있어 이 조건이 거짓이 된다. 항목이 연 칸에
 * 초점을 줘야 하는 쪽은 `onCloseAutoFocus` 를 넘겨 **닫힌 뒤에** 직접 옮긴다 (`TestList` 행 메뉴의 「이름」).
 *
 * ## 017 전에 화면이 손으로 하던 것
 *
 * `TestList` 의 행 메뉴는 포털 · 자리 계산(아래로 열다 모자라면 위로) · 창 가장자리 8px · 스크롤하면 닫기 · 창 크기가
 * 바뀌면 닫기를 직접 했다(`MENU_Z`·`menuPos`). 그것을 Radix(floating-ui)가 한다 — 모자라면 뒤집고, 가장자리 여백을
 * 두고, 열린 동안은 뒤쪽 스크롤을 잠근다. 키보드(Enter·Space·↓ 로 열기 · 화살표 이동 · Esc 로 닫고 단추로 초점 복귀)와
 * `aria-haspopup`·`aria-expanded` 는 손으로 만든 판에 **없던 것**이다 (FR-012).
 */
import { cva } from "class-variance-authority";
import { DropdownMenu as MenuPrimitive } from "radix-ui";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "./cn";

type LayoutProps = { layout?: string; children?: ReactNode };

export function Menu(props: ComponentPropsWithRef<typeof MenuPrimitive.Root>) {
  return <MenuPrimitive.Root {...props} />;
}

/**
 * 여는 단추. **자식 하나를 그대로 단추로 쓴다**(`asChild`) — 모양은 `ui/Button` 이 정한다. Radix 가 그 자식에
 * `aria-haspopup="menu"`·`aria-expanded`·`data-state` 를 붙인다.
 */
export function MenuTrigger(props: Omit<ComponentPropsWithRef<typeof MenuPrimitive.Trigger>, "className" | "asChild">) {
  return <MenuPrimitive.Trigger asChild {...props} />;
}

export function MenuContent({
  layout,
  children,
  align = "end",
  sideOffset = 2,
  collisionPadding = 8,
  onCloseAutoFocus,
  ...rest
}: Omit<ComponentPropsWithRef<typeof MenuPrimitive.Content>, "className"> & LayoutProps) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Content
        // 오른쪽 끝을 단추에 맞춘다 — 단추가 행의 오른쪽 끝에 있다. 2px 는 단추와 메뉴가 붙어 보이지 않게, 8px 는 창
        // 가장자리에 물리지 않게 (017 전 `MENU_GAP`·`MENU_EDGE` 와 같은 값).
        align={align}
        sideOffset={sideOffset}
        collisionPadding={collisionPadding}
        className={cn(
          "z-40 min-w-[160px] flex flex-col gap-[2px] p-[4px] bg-panel border border-hair-2 rounded-base shadow-e2",
          layout,
        )}
        data-slot="menu-content"
        onCloseAutoFocus={(event) => {
          onCloseAutoFocus?.(event);
          if (event.defaultPrevented) return;
          // 머리주석 「표에 없는 변경」 — 고른 항목이 연 칸이 이미 초점을 가졌으면 빼앗지 않는다.
          const active = document.activeElement;
          if (active instanceof HTMLElement && active !== document.body) event.preventDefault();
        }}
        {...rest}
      >
        {children}
      </MenuPrimitive.Content>
    </MenuPrimitive.Portal>
  );
}

/**
 * 항목 — 정본 `.navlink` 의 글자 모양(017 전 행 메뉴가 `Button variant="nav"` 로 그리던 것)을 그대로 쓰고, 지목은
 * hover 와 키보드가 같은 표시(`data-[highlighted]`)로 말한다.
 */
export const menuItemVariants = cva(
  "h-[28px] flex items-center px-[10px] rounded-base font-sans text-[13px] font-medium leading-none " +
    "cursor-pointer select-none data-[highlighted]:bg-sunken data-[disabled]:text-ink-3 data-[disabled]:cursor-not-allowed",
  {
    variants: {
      variant: {
        default: "text-ink-2",
        // 되돌릴 수 없는 조작 — 글자만 실패색이다. 채우지 않는다 (정본 `.btn.danger` 와 같은 문법).
        danger: "text-fail",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export function MenuItem({
  variant = "default",
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof MenuPrimitive.Item>, "className"> & LayoutProps & { variant?: "default" | "danger" }) {
  return (
    <MenuPrimitive.Item
      className={cn(menuItemVariants({ variant }), layout)}
      data-slot="menu-item"
      data-variant={variant}
      {...rest}
    >
      {children}
    </MenuPrimitive.Item>
  );
}
