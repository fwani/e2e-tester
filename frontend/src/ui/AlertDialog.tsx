/**
 * 확인 대화상자 — 되돌릴 수 없는 선택 앞에서 멈춘다. 017 T048.
 *
 * 출처: shadcn new-york-v4/alert-dialog @ shadcn 4.21.0 (2026-09-15) — `AlertDialog`·`AlertDialogContent`·
 * `AlertDialogFooter`·`AlertDialogTitle`·`AlertDialogDescription`·`AlertDialogCancel` 의 구조와 `data-slot` 을 가져왔다.
 * 가림막·판·제목·설명·조작 줄의 클래스와 초점 복귀는 `ui/Dialog` 와 **같은 것**을 쓴다 — 같은 종류의 창이 두 모습·
 * 두 동작을 갖지 않는다 (SC-010). `ui/Dialog` 머리주석의 「표에 없는 변경」(가림막이 내용을 감싼다 · 연 자리로
 * 초점을 돌려준다)도 같다.
 *
 * ## `Dialog` 와 다른 점 — Radix 가 정한다
 *
 * - 역할이 `alertdialog` 다.
 * - 바깥을 눌러도 **닫히지 않는다.** 되돌릴 수 없는 선택을 실수로 넘기지 않게 한다. 그래서 알림 층 보호
 *   (`ui/Dialog` R6 ④)가 따로 필요 없다.
 * - 열리면 초점이 **「돌아가기」**(`AlertDialogCancel`)로 간다. 기본 초점이 위험한 조작에 있지 않다.
 * - Esc 는 「돌아가기」와 같다 — 조작을 실행하지 않고 닫는다 (FR-011).
 *
 * ## 원본의 `AlertDialogAction` 은 들이지 않았다
 *
 * 원본의 실행 조작은 누르는 순간 대화상자를 닫는다. 이 제품의 확인 창은 **저장·실행 요청이 도는 동안 남아서**
 * 조작을 비활성으로 보여 준다(`busy`) — 닫는 때는 화면이 정한다. 실행 조작은 평범한 `Button` 이다.
 */
import { AlertDialog as AlertDialogPrimitive } from "radix-ui";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { Button, type ButtonProps } from "./Button";
import { cn } from "./cn";
import {
  DIALOG_CONTENT_CLASSES,
  DIALOG_DESCRIPTION_CLASSES,
  DIALOG_FOOTER_CLASSES,
  DIALOG_OVERLAY_CLASSES,
  DIALOG_TITLE_CLASSES,
  useReturnFocus,
} from "./Dialog";

type LayoutProps = { layout?: string; children?: ReactNode };

export function AlertDialog(props: ComponentPropsWithRef<typeof AlertDialogPrimitive.Root>) {
  return <AlertDialogPrimitive.Root {...props} />;
}

export function AlertDialogContent({
  layout,
  children,
  onCloseAutoFocus,
  ...rest
}: Omit<ComponentPropsWithRef<typeof AlertDialogPrimitive.Content>, "className"> & LayoutProps) {
  const returnFocus = useReturnFocus(onCloseAutoFocus);
  return (
    <AlertDialogPrimitive.Portal>
      <AlertDialogPrimitive.Overlay className={DIALOG_OVERLAY_CLASSES} data-slot="alert-dialog-overlay">
        <AlertDialogPrimitive.Content
          className={cn(DIALOG_CONTENT_CLASSES, layout)}
          data-slot="alert-dialog-content"
          onCloseAutoFocus={returnFocus}
          {...rest}
        >
          {children}
        </AlertDialogPrimitive.Content>
      </AlertDialogPrimitive.Overlay>
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

/** 「돌아가기」 — 누르면 닫힌다. 모양은 `Button` 의 변종으로 고른다 (기본형). */
export function AlertDialogCancel({ children, ...rest }: ButtonProps) {
  return (
    <AlertDialogPrimitive.Cancel asChild>
      <Button data-slot="alert-dialog-cancel" {...rest}>
        {children}
      </Button>
    </AlertDialogPrimitive.Cancel>
  );
}
