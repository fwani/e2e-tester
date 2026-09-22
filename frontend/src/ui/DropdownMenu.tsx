/**
 * 떠 있는 메뉴 — 행의 추가 동작. 017 T055 · **Base UI 이식 T105**.
 *
 * 출처: shadcn base/dropdown-menu @ shadcn 4.21.x (style base-nova) · `@base-ui/react` 1.8.x — 구조
 * (`Root`·`Trigger`·`Portal`·`Positioner`·`Popup`·`Item` · `data-slot` · 위험 항목 변종)를 가져왔다. 이름은
 * contracts/ui-parts.md §1 대로 `Menu`·`MenuTrigger`·`MenuContent`·`MenuItem` 이고 위험 항목은 `variant="danger"` 다.
 * 클래스는 §2 대응표대로 옮겼다 — `bg-popover` → `bg-panel` · `border` → `border-hair-2` · `shadow-md` → `shadow-e2` ·
 * `rounded-md` → `rounded-base` · `p-1` → `p-[4px]` · `min-w-[8rem]` → `min-w-[160px]` · `z-50` → `z-40`
 * (layout-contract-v3 L1) · 항목 `focus:bg-accent` → `data-[highlighted]:bg-sunken` · `text-destructive` → `text-fail` ·
 * `data-[disabled]:opacity-50` → `data-[disabled]:text-ink-3`. 원본의 움직임 클래스·`outline-hidden`·`[&_svg]:size-4`,
 * 체크·라디오 항목·하위 메뉴·단축키 표시는 들이지 않았다 — 쓰는 자리가 없다.
 *
 * ## Radix 에서 옮기며 달라진 것 (T105)
 *
 * | 옛 형태 (radix) | 지금 (base) | 왜 |
 * |---|---|---|
 * | `Content` 하나가 자리(`align`·`sideOffset`·`collisionPadding`)와 모습을 함께 가졌다 | **`Positioner`(자리) + `Popup`(모습)** | 부품이 둘을 나눈다. **값은 그대로다** — 2px 는 단추와 붙어 보이지 않게, 8px 는 창 가장자리에 물리지 않게 |
 * | `onCloseAutoFocus` **두 겹**으로 초점을 붙잡았다 | **`finalFocus` 하나** | 「닫힌 뒤 어디로 보낼지」를 부품이 직접 받는다. 되돌리려는 것을 막고(`preventDefault`) 다시 옮기던 수고가 없어졌다 (N-08) |
 * | 트리거 `asChild` | **`render`** | 갈래가 쓰는 이름이 다르다. 호출부 모양(`<MenuTrigger><Button/></MenuTrigger>`)은 **그대로 둔다** — 자식을 `render` 로 넘긴다 |
 * | 항목 `onSelect` | **`onClick`** | 같은 뜻이다 |
 * | `data-state="open"` | **`data-open`** | 검사의 판정 방법만 옮겼다 (test-ledger 09-16) |
 *
 * `data-[highlighted]` · `data-[disabled]` 는 **그대로다** — 항목 모양 표(`menuItemVariants`)는 한 줄도 고치지 않았다.
 *
 * **자리는 창 기준이다** (`positionMethod="fixed"`). 스크롤 상자 안의 자리로 잡으면 목록이 다시 잘라 낸다 —
 * `RowMenuVisible` 이 그 이유와 함께 못 박고 있다.
 *
 * ## 017 전에 화면이 손으로 하던 것
 *
 * `TestList` 의 행 메뉴는 포털 · 자리 계산(아래로 열다 모자라면 위로) · 창 가장자리 8px · 스크롤하면 닫기 · 창 크기가
 * 바뀌면 닫기를 직접 했다(`MENU_Z`·`menuPos`). 그것을 부품(floating-ui)이 한다 — 모자라면 뒤집고, 가장자리 여백을
 * 두고, 열린 동안은 뒤쪽 스크롤을 잠근다. 키보드(Enter·Space·↓ 로 열기 · 화살표 이동 · Esc 로 닫고 단추로 초점 복귀)와
 * `aria-haspopup`·`aria-expanded` 는 손으로 만든 판에 **없던 것**이다 (FR-012).
 */
import { Menu as MenuPrimitive } from "@base-ui/react/menu";
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef, ReactElement, ReactNode } from "react";

import { cn } from "./cn";
import { isPlainClick } from "./Button";

type LayoutProps = { layout?: string; children?: ReactNode };

export function Menu(props: ComponentPropsWithRef<typeof MenuPrimitive.Root>) {
  return <MenuPrimitive.Root {...props} />;
}

/**
 * 여는 단추. **자식 하나를 그대로 단추로 쓴다**(`render`) — 모양은 `ui/Button` 이 정한다. 부품이 그 자식에
 * `aria-haspopup="menu"`·`aria-expanded`·`data-popup-open` 을 붙인다.
 */
export function MenuTrigger({
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof MenuPrimitive.Trigger>, "className" | "render" | "children"> & {
  children: ReactElement;
}) {
  return <MenuPrimitive.Trigger render={children} {...rest} />;
}

type PositionerProps = ComponentPropsWithRef<typeof MenuPrimitive.Positioner>;

export function MenuContent({
  layout,
  children,
  align = "end",
  sideOffset = 2,
  collisionPadding = 8,
  ...rest
}: Omit<ComponentPropsWithRef<typeof MenuPrimitive.Popup>, "className"> &
  LayoutProps & {
    align?: PositionerProps["align"];
    sideOffset?: PositionerProps["sideOffset"];
    collisionPadding?: PositionerProps["collisionPadding"];
  }) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Positioner
        // 오른쪽 끝을 단추에 맞춘다 — 단추가 행의 오른쪽 끝에 있다 (017 전 `MENU_GAP`·`MENU_EDGE` 와 같은 값).
        align={align}
        sideOffset={sideOffset}
        collisionPadding={collisionPadding}
        // 머리주석 「자리는 창 기준이다」 — 스크롤 상자 기준으로 잡으면 목록이 다시 잘라 낸다.
        positionMethod="fixed"
        data-slot="menu-positioner"
      >
        <MenuPrimitive.Popup
          className={cn(
            "z-40 min-w-[160px] flex flex-col gap-[2px] p-[4px] bg-panel border border-hair-2 rounded-base shadow-e2",
            layout,
          )}
          data-slot="menu-content"
          {...rest}
        >
          {children}
        </MenuPrimitive.Popup>
      </MenuPrimitive.Positioner>
    </MenuPrimitive.Portal>
  );
}

/**
 * 항목 — 정본 `.navlink` 의 글자 모양(017 전 행 메뉴가 `Button variant="nav"` 로 그리던 것)을 그대로 쓰고, 지목은
 * hover 와 키보드가 같은 표시(`data-[highlighted]`)로 말한다.
 */
export const menuItemVariants = cva(
  "h-[28px] flex items-center px-[10px] rounded-base font-sans text-[14px] font-medium leading-none " +
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

/**
 * 링크인 메뉴 항목 (018 §4) — Base UI `Menu.LinkItem` 이 `<a role="menuitem">` 을 그린다.
 *
 * 모습은 `MenuItem` 의 기본 변종 그대로다. 행 메뉴의 「편집」처럼 **다른 화면으로 가기만 하는** 항목에
 * 쓴다 — 가운데 클릭으로 새 탭에서 열 수 있다. 보통 클릭은 `ButtonLink` 와 같은 규칙으로 가로챈다.
 *
 * `closeOnClick`: 링크 항목의 기본값은 「닫지 않는다」다. 앱 안에서 옮기면 메뉴가 그 자리에 남아
 * 다음 화면을 덮을 수 있으므로 닫는다.
 */
export function MenuLinkItem({
  href,
  onNavigate,
  onClick,
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof MenuPrimitive.LinkItem>, "className" | "href"> &
  LayoutProps & { href: string; onNavigate: () => void }) {
  return (
    <MenuPrimitive.LinkItem
      href={href}
      closeOnClick
      className={cn(menuItemVariants({ variant: "default" }), layout)}
      data-slot="menu-item"
      data-variant="default"
      onClick={(event) => {
        onClick?.(event);
        if (!isPlainClick(event)) return;
        event.preventDefault();
        onNavigate();
      }}
      {...rest}
    >
      {children}
    </MenuPrimitive.LinkItem>
  );
}
