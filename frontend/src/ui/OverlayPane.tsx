/**
 * 겹쳐 뜨는 상세 판 — **모달이 아니다.** 017 T052.
 *
 * 출처: 015 — 정본 `.overlay-pane` 모양(`ui/Surface` 의 `OverlayPane`)에 `radix-ui` `Dialog` 의 동작을 입혔다. shadcn 에
 * 대응하는 부품이 없다 (`sheet` 는 모달이고 포털로 body 에 붙는다 — research R7).
 *
 * ## 무엇을 Radix 에게 맡기는가
 *
 * `Dialog` 를 `modal={false}` 로, **포털 없이** 쓴다.
 *
 * | 동작 | 누가 |
 * |---|---|
 * | 열리면 초점이 **판 자체**로 간다 | Radix `FocusScope` + `onOpenAutoFocus` — 첫 조작(닫기)에 두면 그 툴팁이 판을 열 때마다 뜬다. 판에 초점이 가면 낭독기는 판의 이름(「STEP 상세」)을 먼저 읽고, Tab 한 번이 닫기다 |
 * | Esc 로 닫힌다 | Radix `DismissableLayer` |
 * | 닫히면 연 자리로 초점이 돌아간다 | `ui/Dialog` 의 `useReturnFocus` (Radix 는 트리거로 보내는데 트리거가 없다) |
 * | 역할 `dialog` · 제목과의 연결(`aria-labelledby`) | Radix |
 * | **초점을 가두지 않는다** · 뒤쪽을 `aria-hidden` 으로 숨기지 않는다 | `modal={false}` |
 *
 * ## 바깥 클릭·바깥 초점은 닫힘이 아니다
 *
 * 판은 Step 목록 **옆에** 뜨고, 사용자는 판을 연 채 다른 행을 눌러 옮겨 간다(`DetailPlacement`). Radix 의 비모달
 * 대화상자는 바깥으로 초점이 가면 닫히므로, 그대로 두면 행을 누르는 순간 판이 닫힌다. 판 옆 가림막을 누르는 것도
 * 017 전에 아무 일도 하지 않았다. 그래서 바깥 상호작용은 전부 막고, 닫는 길은 판 안의 「닫기」와 Esc 둘이다.
 *
 * ## 자리는 부모가 정한다
 *
 * 판의 자리(목록 왼쪽 가장자리 · `Workbench` 의 가림막 안)는 007 배치 계약이다. 포털로 body 에 붙이면 그 자리를 다시
 * 계산해야 한다 — 포털을 쓰지 않는 이유다.
 */
import { Dialog as DialogPrimitive } from "radix-ui";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "./cn";
import { useReturnFocus } from "./Dialog";

type LayoutProps = { layout?: string; children?: ReactNode };

export function DetailPanel({
  onClose,
  layout,
  children,
  onOpenAutoFocus,
  onCloseAutoFocus,
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Content>, "className" | "onInteractOutside"> &
  LayoutProps & {
    /** Esc 나 판 안의 닫기 조작이 부른다. */
    onClose: () => void;
  }) {
  const returnFocus = useReturnFocus(onCloseAutoFocus);
  return (
    <DialogPrimitive.Root
      open
      modal={false}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogPrimitive.Content
        // 정본 `.overlay-pane`. `shadow-e2` 는 `Toast` 와 같다 — 같은 층에 뜨는 것은 같은 높이다.
        className={cn("bg-panel border-l border-hair-2 shadow-e2", layout)}
        data-slot="detail-panel"
        // 설명 문단이 따로 없다 — 제목과 내용이 판 전체다. Radix 가 설명을 찾지 않게 명시한다.
        aria-describedby={undefined}
        onInteractOutside={(event) => event.preventDefault()}
        onOpenAutoFocus={(event) => {
          onOpenAutoFocus?.(event);
          if (event.defaultPrevented) return;
          // 머리주석 표 — 초점은 판 자체로. 판은 FocusScope 가 `tabIndex=-1` 을 줘 초점을 받을 수 있다.
          event.preventDefault();
          (event.currentTarget as HTMLElement | null)?.focus({ preventScroll: true });
        }}
        onCloseAutoFocus={returnFocus}
        {...rest}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Root>
  );
}

/** 판의 머리 문구 — 정본 `.pane-hd` 의 라벨 글자. Radix 가 `<h2>` 로 그리므로 기본 여백·크기를 끊는다. */
export function DetailPanelTitle({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Title>, "className"> & LayoutProps) {
  return (
    <DialogPrimitive.Title
      className={cn("m-0 font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3", layout)}
      data-slot="detail-panel-title"
      {...rest}
    >
      {children}
    </DialogPrimitive.Title>
  );
}
