/**
 * 대화상자. 017 T048.
 *
 * 출처: shadcn new-york-v4/dialog @ shadcn 4.21.0 (2026-09-15) — `Dialog`·`DialogClose`·`DialogContent`·`DialogHeader`·
 * `DialogFooter`·`DialogTitle`·`DialogDescription` 의 구조와 `data-slot`, 내용이 가림막과 닫기 표시를 함께 그리는 형태
 * (`showCloseButton`)를 가져왔다. 클래스는 contracts/ui-parts.md §2 대응표대로 옮겼다 — `bg-black/50` → `bg-scrim-strong` ·
 * `bg-background` → `bg-panel` · `border` → `border-hair-2` · `shadow-lg` → `shadow-e2` · `rounded-lg`(정본 6px) ·
 * `p-6` → `p-s5` · `sm:max-w-lg` → `w-[520px]`(정본 `.modal`). 원본의 `data-[state=open]:animate-in`·`fade-*`·`zoom-*`·
 * `duration-200`·`focus:ring-2`·`XIcon`·`sr-only` 는 남지 않는다.
 *
 * **표에 없는 변경 셋.**
 *
 * 1. 원본은 가림막과 내용을 형제로 두고 내용을 `translate(-50%,-50%)` 로 가운데에 놓는다. 여기서는 가림막이 내용을
 *    **감싸고** flex 로 가운데에 둔다 (Radix 가 허용하는 형태). 017 전 대화상자(`SessionScreen` 지역 `Modal`)가 그렇게
 *    그렸고, 창이 낮으면 가림막이 스크롤해 내용이 잘리지 않으며, 반 픽셀 이동으로 글자가 흐려지지 않는다.
 * 2. `showCloseButton` 의 기본값이 거짓이다. 정본 `.modal` 에는 닫기 표시가 없고 「돌아가기」가 그 몫을 한다.
 * 3. 닫히면 **연 자리로** 초점을 돌려준다 (`useReturnFocus`). 아래 절.
 *
 * ## 층 (layout-contract-v3 L1)
 *
 * z 30. 알림 층(z 60)이 위에 있다 — 대화상자가 열린 동안에도 알림이 보이고 눌린다.
 *
 * ## 알림 층 안의 상호작용은 닫힘이 아니다 (research R6 ④)
 *
 * Radix 는 내용 바깥의 포인터·초점을 닫힘으로 친다. 그대로 두면 알림의 「닫기」를 누르는 순간 대화상자가 닫혔다
 * (조사 실측). `onInteractOutside` 가 그 사건이 알림 층 안이면 막는다. 층은 `aria-live` 를 가져 Radix 가 뒤쪽에 거는
 * `aria-hidden` 에서도 빠진다.
 *
 * ## 닫히면 연 자리로 초점이 돌아온다 (FR-011)
 *
 * Radix 는 닫힐 때 기본 복귀를 막고 `Trigger` 로 초점을 보낸다. 이 제품의 대화상자는 트리거 없이 **화면 상태로**
 * 열린다(`{확인 중 && <…Confirm/>}`) — 보낼 곳이 비어 초점이 문서 처음으로 떨어진다. 키보드 사용자는 방금 누른
 * 조작을 다시 찾아야 한다. 내용이 처음 그려지는 순간의 초점(= 연 조작)을 기억했다가 돌려준다.
 */
import { Dialog as DialogPrimitive } from "radix-ui";
import { useState, type ComponentPropsWithRef, type ReactNode } from "react";

import { Button } from "./Button";
import { cn } from "./cn";

/** 알림 층 — 모달이 열린 동안에도 살아 있어야 하는 자리 (`ui/Toast` 의 층). */
const NOTICE_LAYER_SELECTOR = "[data-toast-layer], [data-workbench-notice-layer]";

export function inNoticeLayer(target: EventTarget | null): boolean {
  return target instanceof Element && target.closest(NOTICE_LAYER_SELECTOR) !== null;
}

/**
 * 닫힐 때 연 자리로 초점을 돌려주는 `onCloseAutoFocus`. 머리주석 「닫히면 연 자리로」.
 *
 * 연 자리는 **첫 렌더 순간의 초점**이다 — Radix 가 초점을 안으로 옮기는 것은 그 뒤(효과)다. 연 자리가 사라졌거나
 * (조작이 대화상자와 함께 없어짐) 초점이 어디에도 없었으면 Radix 에게 맡긴다. `AlertDialog`·`DetailPanel` 도 쓴다.
 */
export function useReturnFocus(onCloseAutoFocus?: (event: Event) => void): (event: Event) => void {
  const [opener] = useState<Element | null>(() => (typeof document === "undefined" ? null : document.activeElement));
  return (event) => {
    onCloseAutoFocus?.(event);
    if (event.defaultPrevented) return;
    if (opener instanceof HTMLElement && opener !== document.body && opener.isConnected) {
      event.preventDefault();
      opener.focus();
    }
  };
}

/** 정본 `.modal-scrim` + 가운데 놓기. 창이 낮으면 가림막이 스크롤한다. `AlertDialog` 도 같은 값을 쓴다. */
export const DIALOG_OVERLAY_CLASSES =
  "fixed inset-0 z-30 flex items-center justify-center overflow-y-auto p-s4 bg-scrim-strong";

/** 정본 `.modal` — 판보다 큰 모서리(`--radius-lg`), 떠 있는 승강(`e2`). 좁은 창에서는 창 폭에 맞춘다. */
export const DIALOG_CONTENT_CLASSES = "relative w-[520px] max-w-full bg-panel border border-hair-2 rounded-lg shadow-e2 p-s5";

/** 제목 — Radix 가 `<h2>` 로 그린다. 브라우저 기본 여백·크기를 끊는다 (`m-0`). */
export const DIALOG_TITLE_CLASSES = "m-0 font-sans text-[20px] font-bold leading-[1.3] text-ink";

/** 설명 — `<p>`. 제목과 조작 사이의 간격은 문단의 기본 여백이 만든다 (017 전 대화상자와 같다). */
export const DIALOG_DESCRIPTION_CLASSES = "font-sans text-[13.5px] leading-[1.7] font-normal text-ink-2";

/** 조작 줄 — 오른쪽 끝에 모은다. 되돌리는 조작이 먼저, 주 선택이 끝에 온다. */
export const DIALOG_FOOTER_CLASSES = "flex justify-end gap-[10px] mt-[18px]";

type LayoutProps = { layout?: string; children?: ReactNode };

export function Dialog(props: ComponentPropsWithRef<typeof DialogPrimitive.Root>) {
  return <DialogPrimitive.Root {...props} />;
}

export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  layout,
  children,
  showCloseButton = false,
  onInteractOutside,
  onCloseAutoFocus,
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Content>, "className"> & LayoutProps & { showCloseButton?: boolean }) {
  const returnFocus = useReturnFocus(onCloseAutoFocus);
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className={DIALOG_OVERLAY_CLASSES} data-slot="dialog-overlay">
        <DialogPrimitive.Content
          className={cn(DIALOG_CONTENT_CLASSES, layout)}
          data-slot="dialog-content"
          onInteractOutside={(event) => {
            if (inNoticeLayer(event.target)) event.preventDefault();
            onInteractOutside?.(event);
          }}
          onCloseAutoFocus={returnFocus}
          {...rest}
        >
          {children}
          {showCloseButton && (
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon" layout="absolute top-s3 right-s3" aria-label="닫기">
                <span aria-hidden="true">×</span>
              </Button>
            </DialogPrimitive.Close>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Overlay>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  return (
    <div className={cn("flex flex-col gap-s2", layout)} data-slot="dialog-header" {...rest}>
      {children}
    </div>
  );
}

export function DialogFooter({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  return (
    <div className={cn(DIALOG_FOOTER_CLASSES, layout)} data-slot="dialog-footer" {...rest}>
      {children}
    </div>
  );
}

export function DialogTitle({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Title>, "className"> & LayoutProps) {
  return (
    <DialogPrimitive.Title className={cn(DIALOG_TITLE_CLASSES, layout)} data-slot="dialog-title" {...rest}>
      {children}
    </DialogPrimitive.Title>
  );
}

export function DialogDescription({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Description>, "className"> & LayoutProps) {
  return (
    <DialogPrimitive.Description className={cn(DIALOG_DESCRIPTION_CLASSES, layout)} data-slot="dialog-description" {...rest}>
      {children}
    </DialogPrimitive.Description>
  );
}
