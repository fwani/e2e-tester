/**
 * 툴팁 — 글자가 없거나 잘린 조작의 이름을 보여 준다. 017 T063.
 *
 * 출처: shadcn new-york-v4/tooltip @ shadcn 4.21.0 (2026-09-15) — `Tooltip`·`TooltipTrigger`·`TooltipContent` 의 구조와
 * `data-slot`, **툴팁마다 공급자를 두는 형태**(원본 `Tooltip` 이 뿌리를 `TooltipProvider` 로 감싼다)를 가져왔다. 클래스는
 * contracts/ui-parts.md §2 대응표대로 옮겼다 — `bg-foreground text-background` → `bg-ink text-panel` · `rounded-md` →
 * `rounded-base` · `px-3 py-1.5 text-xs` → `px-[8px] py-[5px] text-[12px]` · `z-50` → `z-[70]`(layout-contract-v3 L1 — 알림 층 위).
 * 원본의 `animate-in`·`fade-in-0`·`zoom-in-95`·`slide-in-from-*` 와 화살표(`TooltipPrimitive.Arrow`)는 들이지 않았다 —
 * 움직임 언어가 없고, 가리키는 조작이 바로 옆이다.
 *
 * ## 공급자를 앱 뿌리에 두지 않는다 — 계획(T063)에서 바꿨다
 *
 * 계획은 `App.tsx` 뿌리에 공급자를 한 번 두는 것이었다. 그러나 화면을 낱개로 렌더하는 검사가 많아(`TestList`·`Toast`·
 * `StepDetail` 만 그리는 검사) 뿌리에만 두면 그 검사들이 「공급자 밖의 툴팁」 예외로 멈춘다. shadcn 원본처럼 툴팁마다
 * 둔다 — 대기 시간이 툴팁 사이에 공유되지 않는 것 말고 잃는 것이 없다.
 *
 * ## 쓰지 않는 자리 — 비활성 조작 (research R2)
 *
 * 비활성 조작의 사유는 `title` 로 남긴다. 비활성 단추는 포인터 사건을 받지 않아 툴팁이 뜨지 않고, 뜨게 하려고 감싸면
 * 초점 순서에 요소가 하나 더 생긴다. 이 부품은 **글자 없는 아이콘 조작**과 **잘린 글자**(`Truncate`)에 쓴다.
 */
import { Tooltip as TooltipPrimitive } from "radix-ui";
import { useLayoutEffect, useRef, useState, type ComponentPropsWithRef, type ReactNode } from "react";

import { cn } from "./cn";

/** 포인터를 올린 뒤 뜨기까지. 0 이면 줄을 훑는 포인터마다 툴팁이 번쩍인다. 초점에는 기다리지 않는다(Radix). */
const DELAY_MS = 300;

/**
 * 떠 있는 것은 `e2` (정본 규율). 어두운 바탕은 정본의 코드 미리보기(`bg-ink text-panel`)와 같은 짝이다.
 * 층은 알림(z 60) **위**다 — 알림 안의 `×` 를 가리키는 툴팁이 그 알림에 가려지지 않게 (layout-contract-v3 L1).
 */
const CONTENT =
  "z-[70] max-w-[320px] px-[8px] py-[5px] rounded-base bg-ink text-panel shadow-e2 " +
  "font-sans text-[12px] font-normal leading-[1.4] break-words";

export interface TooltipProps {
  /** 보여 줄 문구. 조작의 접근 가능한 이름**에 들어 있는** 글로 둔다 — 보이는 이름과 들리는 이름이 갈리지 않게. */
  readonly content: ReactNode;
  /** 트리거가 될 요소 하나. 그 요소가 초점을 받을 수 있어야 키보드로도 뜬다. */
  readonly children: ReactNode;
  readonly side?: "top" | "right" | "bottom" | "left";
  /** 참이면 뜨지 않는다 — `Truncate` 가 글자가 잘리지 않았을 때 쓴다. 구조는 그대로라 트리거가 다시 그려지지 않는다. */
  readonly disabled?: boolean;
}

export function Tooltip({ content, children, side = "top", disabled = false }: TooltipProps) {
  const [open, setOpen] = useState(false);
  return (
    <TooltipPrimitive.Provider delayDuration={DELAY_MS}>
      <TooltipPrimitive.Root open={open && !disabled} onOpenChange={setOpen}>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            side={side}
            sideOffset={4}
            collisionPadding={8}
            className={CONTENT}
            data-slot="tooltip-content"
          >
            {content}
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}

/**
 * 한 줄로 자르고, **잘렸을 때만** 포인터·초점에 전체 문구를 보여 준다 (FR-019).
 *
 * `title` 만으로는 키보드 사용자가 잘린 이름을 읽을 수 없었다. 잘리지 않았으면 툴팁도 초점 자리도 두지 않는다 — 다
 * 보이는 글자에 같은 글자를 한 번 더 띄우지 않고, Tab 순서에 쓸데없는 정거장을 만들지 않는다.
 */
export function Truncate({
  children,
  layout,
  ...rest
}: Omit<ComponentPropsWithRef<"span">, "className" | "children" | "tabIndex"> & { children: string; layout?: string }) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const [clipped, setClipped] = useState(false);
  useLayoutEffect(() => {
    const el = ref.current;
    if (el === null) return undefined;
    const measure = () => setClipped(el.scrollWidth > el.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [children]);
  return (
    <Tooltip content={children} disabled={!clipped}>
      <span
        ref={ref}
        className={cn("block min-w-0 overflow-hidden text-ellipsis whitespace-nowrap", layout)}
        data-slot="truncate"
        data-clipped={clipped ? "true" : undefined}
        tabIndex={clipped ? 0 : undefined}
        {...rest}
      >
        {children}
      </span>
    </Tooltip>
  );
}
