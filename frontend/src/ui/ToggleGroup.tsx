/**
 * 하나를 고르는 단추 묶음. 017 T059.
 *
 * 출처: shadcn new-york-v4/toggle-group @ shadcn 4.21.0 (2026-09-15) — `ToggleGroup`·`ToggleGroupItem` 의 구조, 묶음이
 * 항목에 모양을 물려주는 컨텍스트, `data-slot` 을 가져왔다. new-york-v4/toggle 의 `toggleVariants` 자리에 정본 네
 * 모양(`appearance`)을 둔다. 원본의 `data-[state=on]:bg-accent` 는 모양마다 정본 값으로(ui-parts §2), `rounded-md`·
 * `h-9`·`focus-visible:ring`·`transition-[color,box-shadow]` 은 남지 않는다. 원본의 `type="multiple"` 은 들이지
 * 않았다 — 쓰는 자리가 없다.
 *
 * ## 네 모양 — 전부 017 전 화면에 있던 것이다
 *
 * | appearance | 정본 | 자리 | 017 전 |
 * |---|---|---|---|
 * | `segmented` | `.segmented` | 실행 속도 | `ui/Table` `Segmented` 가 `[&>button]` 로 자식 원시 단추를 칠함 |
 * | `filter` | `.btn.sm` · 고른 것은 `.btn.primary` | 목록 결말 거르기 · Step 넣기의 종류·일치 방식 | `Button` 에 `variant={고름 ? "primary" : "default"}` |
 * | `chip` | `.chip` · 고른 것은 잉크 테두리 | 그룹 거르기 | 원시 `<button className={chipClasses()}>` — 고른 칩이 **구별되지 않았다** (017 N-06) |
 * | `card` | `.pick` · `.pick.on` | 만드는 방법 | 원시 `<button>` 에 조건부 클래스 |
 *
 * `filter`·`chip` 은 버튼·칩 부품의 **같은 값**을 쓴다 (`buttonVariants`·`chipVariants`) — 같은 종류가 두 모습을 갖지 않는다.
 *
 * ## 무엇이 새로 성립하는가 (FR-013)
 *
 * - 고른 항목을 **라디오로** 알린다 — 묶음은 `radiogroup`, 항목은 `radio`·`aria-checked`. 017 전에는 `aria-pressed`
 *   였고 「눌린 토글 단추 넷」으로 들려 하나만 고른다는 사실이 없었다.
 * - 화살표로 오가고, 묶음 전체가 Tab 한 번이다 (roving focus).
 * - **늘 하나가 골라져 있다.** Radix 는 고른 항목을 다시 누르면 선택을 비운다 — 이 부품은 빈 값을 넘기지 않는다.
 *
 * ## 고름과 비활성이 겹칠 때 — 산출 CSS 순서에 맡기지 않는다
 *
 * 고른 색(`data-[state=on]:`)과 비활성 색(`disabled:`)은 명시도가 같아 이기는 쪽을 산출 CSS 순서가 정한다 (015 흰 버튼).
 * 고른 색은 `enabled:data-[state=on]:` 로 **쓸 수 있을 때만** 준다. 정본도 `.segmented > button:disabled` 가
 * `[aria-pressed=true]` 뒤에 와서 비활성이 이긴다.
 */
import { cva } from "class-variance-authority";
import { ToggleGroup as ToggleGroupPrimitive } from "radix-ui";
import { createContext, useContext, type ComponentPropsWithRef, type ReactNode } from "react";

import { buttonVariants } from "./Button";
import { chipVariants } from "./Chip";
import { cn } from "./cn";

export type ToggleAppearance = "segmented" | "filter" | "chip" | "card";

const Appearance = createContext<ToggleAppearance>("filter");

/** 묶음의 모양 — 칸 사이 간격과 줄 세우기. `segmented` 만 묶음 자체가 테두리를 갖는다. */
const groupVariants = cva("", {
  variants: {
    appearance: {
      segmented: "inline-flex border border-hair-2 rounded-base overflow-hidden",
      filter: "flex items-center gap-[6px]",
      chip: "flex items-center gap-s2",
      card: "flex gap-[14px]",
    },
  },
});

/** 고른 칩 — 정본이 「고른 것」을 말하는 문법(`.pick.on` 의 잉크 테두리). 채우지 않는다. N-06. */
const CHIP_ON = "data-[state=on]:border-ink data-[state=on]:text-ink";

/** 고른 거르기 — 정본 `.btn.primary`. 쓸 수 있을 때만 (머리주석 「고름과 비활성이 겹칠 때」). */
const FILTER_ON =
  "enabled:data-[state=on]:bg-ink enabled:data-[state=on]:border-ink enabled:data-[state=on]:text-panel " +
  "enabled:data-[state=on]:hover:bg-ink-2";

const itemVariants = cva("", {
  variants: {
    appearance: {
      // 정본 `.segmented > button` — 왼쪽 실선으로 칸을 가르고(첫 칸은 없음) 바탕·그림자를 벗는다.
      segmented:
        "px-s3 border-0 border-l border-hair-2 first:border-l-0 rounded-none bg-transparent shadow-none " +
        "text-ink-2 font-medium cursor-pointer data-[state=on]:font-bold " +
        "enabled:data-[state=on]:bg-sunken enabled:data-[state=on]:text-ink " +
        "disabled:bg-transparent disabled:border-solid disabled:text-ink-3 disabled:cursor-default",
      filter: "",
      chip: "",
      // 정본 `.pick` — 글이 왼쪽에 서는 카드. 높이는 내용이 정한다(요소 규칙의 32px 를 되돌린다).
      card:
        "border rounded-base text-left text-ink h-auto py-s4 px-[18px] flex flex-col gap-s2 " +
        "data-[state=on]:border-ink data-[state=on]:shadow-e1",
    },
    tone: {
      default: "",
      // 정본 `.tint-ai` — 카드에서만 뜻이 있다. AI 로 만드는 쪽을 사람 작성과 가르는 유일한 색이다.
      ai: "",
    },
  },
  compoundVariants: [
    { appearance: "card", tone: "default", class: "bg-panel border-hair" },
    { appearance: "card", tone: "ai", class: "bg-ai-t border-ai" },
  ],
  defaultVariants: { tone: "default" },
});

/** 버튼·칩 부품의 값을 그대로 잇는 두 모양. `cva` 문자열 안에 부품 함수를 넣을 수 없어 따로 만든다. */
const BORROWED: Partial<Record<ToggleAppearance, string>> = {
  filter: cn(buttonVariants({ variant: "default", size: "sm" }), FILTER_ON),
  chip: cn(chipVariants({ tone: "default" }), CHIP_ON),
};

export interface ToggleGroupProps extends Omit<ComponentPropsWithRef<"div">, "className" | "defaultValue" | "dir" | "onChange"> {
  readonly appearance: ToggleAppearance;
  /** 고른 항목의 값. 어느 항목과도 맞지 않으면 아무것도 골라지지 않은 채로 그린다. */
  readonly value: string;
  /** 다른 항목을 골랐을 때만 불린다 — 고른 항목을 다시 눌러 선택을 비우는 일은 없다. */
  readonly onValueChange: (value: string) => void;
  readonly disabled?: boolean;
  /** **배치만.** */
  readonly layout?: string;
  readonly children?: ReactNode;
}

export function ToggleGroup({ appearance, value, onValueChange, disabled, layout, children, ...rest }: ToggleGroupProps) {
  return (
    <Appearance.Provider value={appearance}>
      <ToggleGroupPrimitive.Root
        type="single"
        value={value}
        onValueChange={(next) => {
          if (next !== "") onValueChange(next);
        }}
        disabled={disabled}
        className={cn(groupVariants({ appearance }), layout)}
        data-slot="toggle-group"
        data-appearance={appearance}
        {...rest}
      >
        {children}
      </ToggleGroupPrimitive.Root>
    </Appearance.Provider>
  );
}

export interface ToggleGroupItemProps
  extends Omit<ComponentPropsWithRef<typeof ToggleGroupPrimitive.Item>, "className"> {
  /** 카드 모양에서만 뜻이 있다 — AI 로 만드는 쪽. */
  readonly tone?: "default" | "ai";
  /** **배치만** — 카드가 줄을 나눠 갖는 폭(`flex-1 min-w-0`) 따위. */
  readonly layout?: string;
}

export function ToggleGroupItem({ tone = "default", layout, children, ...rest }: ToggleGroupItemProps) {
  const appearance = useContext(Appearance);
  return (
    <ToggleGroupPrimitive.Item
      className={cn(BORROWED[appearance], itemVariants({ appearance, tone }), layout)}
      data-slot="toggle-group-item"
      data-appearance={appearance}
      {...rest}
    >
      {children}
    </ToggleGroupPrimitive.Item>
  );
}
