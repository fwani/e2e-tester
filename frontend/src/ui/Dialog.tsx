/**
 * 대화상자. 017 T048 · **Base UI 이식 T104**.
 *
 * 출처: shadcn base/dialog @ shadcn 4.21.x (style base-nova) · `@base-ui/react` 1.8.x — 구조
 * (`Root`·`Portal`·`Backdrop`·`Viewport`·`Popup`·`Title`·`Description`·`Close`)와 `data-slot` 을 가져왔다.
 * 클래스는 015·017 이 정본으로 옮겨 둔 값 그대로다 — `bg-scrim-strong` · `bg-panel` · `border-hair-2` ·
 * `shadow-e2` · `rounded-lg`(정본 6px) · `p-s5` · `w-[520px]`(정본 `.modal`). 원본의 움직임 클래스
 * (`data-[state=open]:animate-in`·`fade-*`·`zoom-*`·`duration-*`)·`focus:ring-2`·`XIcon`·`sr-only` 는 남지 않는다.
 *
 * ## Radix 에서 옮기며 달라진 것 (T104 · 실측으로 정했다)
 *
 * | 옛 형태 (radix) | 지금 (base) | 왜 |
 * |---|---|---|
 * | `Overlay` 하나가 가림막이자 가운데 놓기 | **`Backdrop`(가림막) + `Viewport`(가운데·스크롤)** | Base UI 의 `Backdrop` 은 「팝업 **아래** 깔리는 것」이라 내용을 감싸지 않는다. 감싸서 얻던 것(창이 낮으면 스크롤 · 반 픽셀 이동 없음)은 `Viewport` 가 그대로 한다 — 「스크롤 가능한 자리 상자」가 그 부품의 정의다 |
 * | 수제 `useReturnFocus` | `finalFocus` **기본값** | 트리거 없이 열어도 닫히면 직전 초점으로 돌아온다(실측). 손으로 기억할 이유가 없어져 훅을 지웠다 |
 * | `onInteractOutside` 로 알림 층 누름 막기 | **없앴다** | 모달은 **자기 포털 안**에서 시작한 누름만 `outside-press` 로 받는다(실측). 알림 층은 body 의 다른 직계 자식이고 열린 동안 `data-base-ui-inert` 를 받아 애초에 닫기 사건을 만들지 않는다 — R6 ④ 가 공짜가 됐다 |
 * | `data-state="open"` | **`data-open`** | 부품이 쓰는 표식이 다르다. 검사의 판정 방법만 옮겼다 (test-ledger 09-16) |
 *
 * `showCloseButton` 의 기본값은 여전히 거짓이다 — 정본 `.modal` 에 닫기 표시가 없고 「돌아가기」가 그 몫을 한다.
 *
 * ## 층 (layout-contract-v3 L1)
 *
 * z 30. 알림 층(z 60)이 위에 있다 — 대화상자가 열린 동안에도 알림이 보이고 눌린다 (research R6 ③).
 * 층은 `aria-live` 를 갖고 body 직계라 모달의 `aria-hidden` 에 휩쓸리지 않는다(실측).
 */
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { Button } from "./Button";
import { cn } from "./cn";

/** 정본 `.modal-scrim` — 가림막은 색만 갖는다. 가운데 놓기는 `Viewport` 가 한다. */
export const DIALOG_BACKDROP_CLASSES = "fixed inset-0 z-30 bg-scrim-strong";

/**
 * 가운데 놓기와 스크롤. 창이 낮으면 **이 상자가** 스크롤해 내용이 잘리지 않는다.
 *
 * 가림막과 같은 z 에 두고 **뒤에 그린다** — 같은 z 에서는 나중에 그린 것이 위다. 내용이 가림막 위에 온다.
 */
export const DIALOG_VIEWPORT_CLASSES =
  "fixed inset-0 z-30 flex items-center justify-center overflow-y-auto p-s4";

/** 정본 `.modal` — 판보다 큰 모서리(`--radius-lg`), 떠 있는 승강(`e2`). 좁은 창에서는 창 폭에 맞춘다. */
export const DIALOG_CONTENT_CLASSES = "relative w-[520px] max-w-full bg-panel border border-hair-2 rounded-lg shadow-e2 p-s5";

/** 제목 — 부품이 `<h2>` 로 그린다. 브라우저 기본 여백·크기를 끊는다 (`m-0`). */
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
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Popup>, "className"> & LayoutProps & { showCloseButton?: boolean }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Backdrop className={DIALOG_BACKDROP_CLASSES} data-slot="dialog-overlay" />
      <DialogPrimitive.Viewport className={DIALOG_VIEWPORT_CLASSES} data-slot="dialog-viewport">
        <DialogPrimitive.Popup className={cn(DIALOG_CONTENT_CLASSES, layout)} data-slot="dialog-content" {...rest}>
          {children}
          {showCloseButton && (
            <DialogPrimitive.Close
              render={<Button variant="ghost" size="icon" layout="absolute top-s3 right-s3" aria-label="닫기" />}
            >
              <span aria-hidden="true">×</span>
            </DialogPrimitive.Close>
          )}
        </DialogPrimitive.Popup>
      </DialogPrimitive.Viewport>
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
