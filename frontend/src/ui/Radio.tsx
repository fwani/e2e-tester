/**
 * 라디오 — **네이티브 `<input type="radio">`**. 017 T033.
 *
 * 출처: 015 — 체크박스(`ui/Checkbox`)와 같은 판단이다. shadcn `radio-group` 은 Radix `RadioGroup` 이라 **쓰지
 * 않는다** (017 research R2): 네이티브 라디오는 같은 `name` 끼리 화살표 이동과 상태 알림을 이미 갖는다.
 *
 * 크기를 명시해 정본 요소 규칙 `input{width:100%;min-height:32px}` 의 번짐을 끊는다 (`Checkbox` 와 같은 이유).
 * 모양은 체크박스와 같은 잉크 강조다 — 정본에 라디오 전용 규칙이 없고, 같은 종류의 선택 표식이 두 모습을
 * 갖지 않게 한다 (SC-010).
 */
import type { ChangeEvent, ComponentPropsWithRef } from "react";

import { cn } from "./cn";

export interface RadioProps extends Omit<ComponentPropsWithRef<"input">, "className" | "type"> {
  /** 네이티브 `onChange` 와 함께 불린다. 골라졌을 때만 부른다. */
  readonly onSelect?: () => void;
  /** **배치만.** */
  readonly layout?: string;
}

const RADIO = "size-[14px] min-h-0 m-0 p-0 accent-ink cursor-pointer disabled:cursor-default";

export function Radio({ onSelect, onChange, layout, ...rest }: RadioProps) {
  const handle = (event: ChangeEvent<HTMLInputElement>): void => {
    onChange?.(event);
    if (event.target.checked) onSelect?.();
  };
  return <input type="radio" className={cn(RADIO, layout)} data-slot="radio" onChange={handle} {...rest} />;
}
