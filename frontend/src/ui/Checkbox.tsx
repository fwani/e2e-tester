/**
 * 체크박스 — **네이티브 `<input type="checkbox">`**. 017 T032.
 *
 * 출처: 015 — 정본 `.srow-check input[type=checkbox]` 모양(`ui/StepRow` 의 `StepCheck`)을 부품으로 올렸다.
 * shadcn `checkbox` 는 Radix `Checkbox`(`<button role="checkbox">` 에 표시를 직접 그린다)라 **쓰지 않는다**
 * (017 research R2): 정본의 체크 상자는 `accent-color` 잉크로 그린 네이티브 14px 상자이고, 결말 아이콘
 * (✓ · X · 점)과 **형태로 갈리는 유일한 사각형**이다. Radix 로 그리면 모양을 새로 만들어야 하고, 네이티브가
 * 이미 주는 상태 알림·Space 동작 외에 얻는 것이 없다. 테스트가 `.checked`·`input[type=checkbox]` 를 읽는다.
 *
 * API 는 shadcn 을 따른다 — `checked` · `onCheckedChange(boolean)`. 네이티브 `onChange`·`onClick` 도 그대로
 * 넘긴다: **부품이 사건을 삼키지 않는다** — 목록 행의 체크박스는 클릭 전파를 스스로 멈춘다.
 *
 * ## 크기를 명시한다 (B-08)
 *
 * 정본 요소 규칙 `input{width:100%;min-height:32px}` 가 체크박스에도 번졌다. 테스트 목록 머리의 전체 선택은
 * 블록 안에서 28px 로, 행의 체크박스는 flex 안에서 줄어 21px 로 그려져 **같은 표의 두 체크박스 크기가
 * 달랐다.** 이 부품이 14px 를 명시해 번짐을 끊는다.
 */
import type { ChangeEvent, ComponentPropsWithRef } from "react";

import { cn } from "./cn";

export interface CheckboxProps extends Omit<ComponentPropsWithRef<"input">, "className" | "type"> {
  /** 네이티브 `onChange` 와 함께 불린다 — shadcn 과 같은 이름. */
  readonly onCheckedChange?: (checked: boolean) => void;
  /** **배치만.** 모양은 부품이 정한다. */
  readonly layout?: string;
}

/**
 * 정본 `.srow-check input[type="checkbox"]{width:14px;height:14px;min-height:0;margin:0;padding:0;
 * accent-color:var(--ink);cursor:pointer}` 와 `:disabled{cursor:default}`.
 *
 * 비활성의 흐림(`opacity:.4`)은 **Step 행 체크 칸에서만** 정본이 정했다 — 그 자리(`StepCheck`)가 갖는다.
 */
const CHECKBOX = "size-[14px] min-h-0 m-0 p-0 accent-ink cursor-pointer disabled:cursor-default";

export function Checkbox({ onCheckedChange, onChange, layout, ...rest }: CheckboxProps) {
  const handle = (event: ChangeEvent<HTMLInputElement>): void => {
    onChange?.(event);
    onCheckedChange?.(event.target.checked);
  };
  return (
    <input type="checkbox" className={cn(CHECKBOX, layout)} data-slot="checkbox" onChange={handle} {...rest} />
  );
}
