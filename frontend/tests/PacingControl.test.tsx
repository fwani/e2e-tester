/**
 * 실행 속도 컨트롤 (004 US1, FR-102·FR-103·FR-107).
 *
 * **실행 중에도 눌러야 한다.** 속도를 바꾸는 이유가 대개 "지금 너무 빨라서 못 보겠다"
 * 이므로, 끝난 뒤에만 바꿀 수 있으면 이 기능은 쓸모가 없다.
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { PacingControl } from "../src/components/PacingControl";
import { PACING_ORDER } from "../src/api/client";

describe("PacingControl", () => {
  it("네 단계를 모두 보여준다 (FR-102)", () => {
    render(<PacingControl value="normal" onChange={vi.fn()} />);
    for (const pacing of PACING_ORDER) {
      expect(screen.getByTestId(`pacing-${pacing}`)).toBeDefined();
    }
    expect(PACING_ORDER).toHaveLength(4);
  });

  it("현재 속도를 눌린 상태로 표시한다", () => {
    render(<PacingControl value="slow" onChange={vi.fn()} />);
    /*
      **T106 에서 되돌아갔다 — 낭독되는 의미가 내려간다.**

      017 은 고른 속도를 **라디오로** 알렸다(`role="radio"`·`aria-checked`). 017 전의 `aria-pressed` 는
      「눌린 단추 셋」으로 들려 **하나만 고른다는 사실이 전달되지 않았고**, 그것을 고친 것이 T060 이었다.
      Base UI 의 `ToggleGroup`·`Toggle` 은 **눌림**(`aria-pressed`)만 주고 라디오 통로가 없다 — 사용자 결정
      (2026-09-16 「Base UI 기준에 맞춘다」)으로 그 기준을 따랐다.

      **묻는 것은 그대로다: 무엇을 골랐는지가 보조기술에 남는가.** 다만 「셋 중 하나」라는 뜻은 잃었다.
      그 손실은 test-ledger 와 사람 확인 H-10(「고르기 낭독」)에 적혀 있다.
    */
    // (아래 주석은 T060 당시의 것 — 017 전의 `aria-pressed` 는 「눌린
    // 단추 넷」으로 들려 하나만 고른다는 사실이 없었다. 묻는 것은 그대로다 — 무엇이 골라져 있는가.
    expect(screen.getByTestId("pacing-slow").getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByTestId("pacing-fast").getAttribute("aria-pressed")).toBe("false");
  });

  it("다른 속도를 고르면 알린다 (FR-103)", () => {
    const onChange = vi.fn();
    render(<PacingControl value="fast" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("pacing-slow"));
    expect(onChange).toHaveBeenCalledWith("slow");
  });

  it("이미 고른 속도를 다시 눌러도 요청하지 않는다", () => {
    const onChange = vi.fn();
    render(<PacingControl value="slow" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("pacing-slow"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("요청이 도는 중에는 연타를 막는다", () => {
    const onChange = vi.fn();
    render(<PacingControl value="fast" onChange={onChange} busy />);
    fireEvent.click(screen.getByTestId("pacing-slow"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("바꿀 수 없는 상태에서도 숨기지 않고 비활성으로 둔다", () => {
    render(<PacingControl value="slow" onChange={vi.fn()} disabled />);
    // 컨트롤이 사라지면 자기가 고른 속도가 무엇이었는지도 확인할 수 없다.
    const slow = screen.getByTestId("pacing-slow") as HTMLButtonElement;
    expect(slow.disabled).toBe(true);
    expect(slow.getAttribute("aria-pressed")).toBe("true");
  });

  it("취향을 남기지 못하면 그 사실만 알리고 실행을 막지 않는다", () => {
    render(<PacingControl value="slow" onChange={vi.fn()} preferenceSaved={false} />);
    expect(screen.getByRole("status").textContent).toContain("다음 실행에는 유지되지 않습니다");
    // 속도 자체는 바뀌었으므로 컨트롤은 그대로 눌린다.
    expect(screen.getByTestId("pacing-slow").getAttribute("aria-pressed")).toBe("true");
  });

  it("정상 저장되면 경고를 띄우지 않는다", () => {
    render(<PacingControl value="slow" onChange={vi.fn()} />);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
