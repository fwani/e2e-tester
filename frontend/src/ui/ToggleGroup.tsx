/**
 * 하나를 고르는 단추 묶음. 017 T059 · **Base UI 이식 T106**.
 *
 * 출처: shadcn base/toggle-group @ shadcn 4.21.x (style base-nova) · `@base-ui/react` 1.8.x — `ToggleGroup` 과
 * `Toggle` 의 구조, 묶음이 항목에 모양을 물려주는 컨텍스트, `data-slot` 을 가져왔다. 원본 `toggle` 의
 * `toggleVariants` 자리에 정본 네 모양(`appearance`)을 둔다. `rounded-md`·`h-9`·`focus-visible:ring`·
 * `transition-[color,box-shadow]` 은 남지 않는다.
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
 * ## 낭독되는 의미가 바뀌었다 — **접근성이 한 단계 내려간다** (T106 · 사용자 결정 2026-09-16)
 *
 * 017 은 이 묶음을 **라디오**로 만들었다(`radiogroup`·`radio`·`aria-checked`). 017 전에는 `aria-pressed` 라
 * 「눌린 토글 단추 넷」으로 들려 **하나만 고른다는 사실이 전달되지 않았고**, 그것을 고친 것이 FR-013 이었다.
 *
 * Base UI 의 `ToggleGroup` 은 **눌림**(`aria-pressed`·`data-pressed`)이 기본이고 라디오 통로를 주지 않는다.
 * 스파이크 S7 에서 라디오 대안(`RadioGroup` + `render`)을 검토했으나 **쓰지 않기로 했고**(research S7),
 * 사용자가 「Base UI 기준에 맞춘다」로 정했다. 그래서 낭독은 017 전 수준으로 돌아간다:
 *
 * | | 낭독기가 읽는 말 |
 * |---|---|
 * | 017 (라디오) | 「느리게, 라디오 버튼, 선택됨, 3개 중 1번째」 |
 * | 지금 (눌림) | 「느리게, 버튼, 눌림」 |
 *
 * **모습과 동작은 하나도 바뀌지 않는다** — 네 모양의 클래스 표도 그대로다. 바뀐 것은 보조기술이 듣는 말뿐이다.
 * 사람 확인 H-10 이 「고르기 낭독」을 듣는다 (quickstart).
 *
 * ## 늘 하나가 골라져 있다 — 값을 우리가 쥔다 (S7)
 *
 * 부품의 값은 **배열**이고, 고른 항목을 다시 누르면 **빈 배열**이 온다. 이 부품의 계약은 「늘 하나」이므로
 * 빈 배열을 무시한다 — 바깥으로는 여전히 문자열 하나를 주고받는다.
 *
 * ## 고름과 비활성이 겹칠 때 — 산출 CSS 순서에 맡기지 않는다
 *
 * 고른 색(`data-[pressed]:`)과 비활성 색(`disabled:`)은 명시도가 같아 이기는 쪽을 산출 CSS 순서가 정한다
 * (015 흰 버튼). 고른 색은 `enabled:data-[pressed]:` 로 **쓸 수 있을 때만** 준다 — 부품이 네이티브 `<button>` 을
 * 그리므로(`Toggle` — "Renders a `<button>` element") `enabled:`·`disabled:` 가 그대로 산다. 정본도
 * `.segmented > button:disabled` 가 `[aria-pressed=true]` 뒤에 와서 비활성이 이긴다.
 */
import { Toggle as TogglePrimitive } from "@base-ui/react/toggle";
import { ToggleGroup as ToggleGroupPrimitive } from "@base-ui/react/toggle-group";
import { cva } from "class-variance-authority";
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
const CHIP_ON = "data-[pressed]:border-ink data-[pressed]:text-ink";

/** 고른 거르기 — 정본 `.btn.primary`. 쓸 수 있을 때만 (머리주석 「고름과 비활성이 겹칠 때」). */
const FILTER_ON =
  "enabled:data-[pressed]:bg-ink enabled:data-[pressed]:border-ink enabled:data-[pressed]:text-panel " +
  "enabled:data-[pressed]:hover:bg-ink-2";

const itemVariants = cva("", {
  variants: {
    appearance: {
      // 정본 `.segmented > button` — 왼쪽 실선으로 칸을 가르고(첫 칸은 없음) 바탕·그림자를 벗는다.
      segmented:
        "px-s3 border-0 border-l border-hair-2 first:border-l-0 rounded-none bg-transparent shadow-none " +
        "text-ink-2 font-medium cursor-pointer data-[pressed]:font-bold " +
        "enabled:data-[pressed]:bg-sunken enabled:data-[pressed]:text-ink " +
        "disabled:bg-transparent disabled:border-solid disabled:text-ink-3 disabled:cursor-default",
      filter: "",
      chip: "",
      // 정본 `.pick` — 글이 왼쪽에 서는 카드. 높이는 내용이 정한다(요소 규칙의 32px 를 되돌린다).
      card:
        "border rounded-base text-left text-ink h-auto py-s4 px-[18px] flex flex-col gap-s2 " +
        "data-[pressed]:border-ink data-[pressed]:shadow-e1",
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
      <ToggleGroupPrimitive
        // 바깥은 문자열 하나, 부품은 배열이다 (머리주석 「늘 하나가 골라져 있다」).
        value={[value]}
        onValueChange={(next) => {
          const [first] = next;
          // 빈 배열 = 고른 것을 다시 누른 것. 이 묶음의 계약은 「늘 하나」이므로 무시한다 (S7).
          if (first !== undefined) onValueChange(first);
        }}
        disabled={disabled}
        className={cn(groupVariants({ appearance }), layout)}
        data-slot="toggle-group"
        data-appearance={appearance}
        {...rest}
      >
        {children}
      </ToggleGroupPrimitive>
    </Appearance.Provider>
  );
}

export interface ToggleGroupItemProps extends Omit<ComponentPropsWithRef<typeof TogglePrimitive>, "className"> {
  /** 카드 모양에서만 뜻이 있다 — AI 로 만드는 쪽. */
  readonly tone?: "default" | "ai";
  /** **배치만** — 카드가 줄을 나눠 갖는 폭(`flex-1 min-w-0`) 따위. */
  readonly layout?: string;
}

export function ToggleGroupItem({ tone = "default", layout, children, ...rest }: ToggleGroupItemProps) {
  const appearance = useContext(Appearance);
  return (
    <TogglePrimitive
      className={cn(BORROWED[appearance], itemVariants({ appearance, tone }), layout)}
      data-slot="toggle-group-item"
      data-appearance={appearance}
      {...rest}
    >
      {children}
    </TogglePrimitive>
  );
}
