/**
 * 확인 대화상자 — 되돌릴 수 없는 선택 앞에서 멈춘다. 017 T048 · **Base UI 이식 T104**.
 *
 * 출처: shadcn base/alert-dialog @ shadcn 4.21.x (style base-nova) · `@base-ui/react` 1.8.x — 구조
 * (`Root`·`Portal`·`Backdrop`·`Viewport`·`Popup`·`Title`·`Description`·`Close`)와 `data-slot` 을 가져왔다.
 * 가림막·판·제목·설명·조작 줄의 클래스는 `ui/Dialog` 와 **같은 것**을 쓴다 — 같은 종류의 창이 두 모습·
 * 두 동작을 갖지 않는다 (SC-010).
 *
 * ## `Dialog` 와 다른 점 — 부품이 정한다 (T104 실측)
 *
 * - 역할이 `alertdialog` 다.
 * - 바깥을 눌러도 **닫히지 않는다.** `AlertDialog.Root` 는 `modal`·`disablePointerDismissal` 을 아예
 *   받지 않는다(타입에서 빠져 있다) — 가림막을 눌러도 `onOpenChange` 가 **불리지 않는다**(실측).
 *   되돌릴 수 없는 선택을 실수로 넘기지 않는다.
 * - 열리면 초점이 **첫 tabbable** 에 간다. 조작 줄에서 「돌아가기」가 먼저 오므로 거기 앉는다(실측 ·
 *   `initialFocus` 를 따로 심지 않아도 된다). 기본 초점이 위험한 조작에 있지 않다.
 * - Esc 는 「돌아가기」와 같다 — 조작을 실행하지 않고 닫는다 (FR-011).
 * - 닫히면 **연 자리로** 초점이 돌아온다 — `finalFocus` 기본값이 직전 초점을 기억한다. 017 이 손으로
 *   만든 `useReturnFocus` 는 사라졌다 (`ui/Dialog` 머리주석).
 *
 * ## 원본의 `AlertDialogAction` 은 들이지 않았다
 *
 * 원본의 실행 조작은 누르는 순간 대화상자를 닫는다. 이 제품의 확인 창은 **저장·실행 요청이 도는 동안 남아서**
 * 조작을 비활성으로 보여 준다(`busy`) — 닫는 때는 화면이 정한다. 실행 조작은 평범한 `Button` 이다.
 */
import { AlertDialog as AlertDialogPrimitive } from "@base-ui/react/alert-dialog";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { Button, type ButtonProps } from "./Button";
import { cn } from "./cn";
import {
  DIALOG_BACKDROP_CLASSES,
  DIALOG_CONTENT_CLASSES,
  DIALOG_DESCRIPTION_CLASSES,
  DIALOG_FOOTER_CLASSES,
  DIALOG_TITLE_CLASSES,
  DIALOG_VIEWPORT_CLASSES,
} from "./Dialog";

type LayoutProps = { layout?: string; children?: ReactNode };

export function AlertDialog(props: ComponentPropsWithRef<typeof AlertDialogPrimitive.Root>) {
  return <AlertDialogPrimitive.Root {...props} />;
}

export function AlertDialogContent({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof AlertDialogPrimitive.Popup>, "className"> & LayoutProps) {
  return (
    <AlertDialogPrimitive.Portal>
      <AlertDialogPrimitive.Backdrop className={DIALOG_BACKDROP_CLASSES} data-slot="alert-dialog-overlay" />
      <AlertDialogPrimitive.Viewport className={DIALOG_VIEWPORT_CLASSES} data-slot="alert-dialog-viewport">
        <AlertDialogPrimitive.Popup
          className={cn(DIALOG_CONTENT_CLASSES, layout)}
          data-slot="alert-dialog-content"
          {...rest}
        >
          {children}
        </AlertDialogPrimitive.Popup>
      </AlertDialogPrimitive.Viewport>
    </AlertDialogPrimitive.Portal>
  );
}

export function AlertDialogFooter({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  return (
    <div className={cn(DIALOG_FOOTER_CLASSES, layout)} data-slot="alert-dialog-footer" {...rest}>
      {children}
    </div>
  );
}

export function AlertDialogTitle({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof AlertDialogPrimitive.Title>, "className"> & LayoutProps) {
  return (
    <AlertDialogPrimitive.Title className={cn(DIALOG_TITLE_CLASSES, layout)} data-slot="alert-dialog-title" {...rest}>
      {children}
    </AlertDialogPrimitive.Title>
  );
}

export function AlertDialogDescription({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof AlertDialogPrimitive.Description>, "className"> & LayoutProps) {
  return (
    <AlertDialogPrimitive.Description
      className={cn(DIALOG_DESCRIPTION_CLASSES, layout)}
      data-slot="alert-dialog-description"
      {...rest}
    >
      {children}
    </AlertDialogPrimitive.Description>
  );
}

/**
 * 「돌아가기」 — 누르면 닫힌다. 모양은 `Button` 의 변종으로 고른다 (기본형).
 *
 * `render` 로 준 요소는 **정본 클래스를 그대로 지킨다**(T104 실측 — 기준 버튼과 클래스 문자열이 같고
 * `data-slot`·`data-variant` 도 남는다). `Button` 은 `className` 을 받지 않으므로 여기서도 주지 않는다.
 */
export function AlertDialogCancel({ children, ...rest }: ButtonProps) {
  return (
    <AlertDialogPrimitive.Close render={<Button data-slot="alert-dialog-cancel" {...rest} />}>
      {children}
    </AlertDialogPrimitive.Close>
  );
}
