/** 배지 테스트 — 상태·작성 방식 표기가 디자인을 따르는지 확인한다. */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuthoringBadge, OutcomeBadge, TabBadge } from "../src/components/Badges";

describe("배지", () => {
  it("실행 결과를 PASS/FAIL/미실행 으로 표기한다", () => {
    const { rerender } = render(<OutcomeBadge outcome="pass" />);
    expect(screen.getByText("PASS")).toBeDefined();
    rerender(<OutcomeBadge outcome="fail" />);
    expect(screen.getByText("FAIL")).toBeDefined();
    rerender(<OutcomeBadge outcome={null} />);
    expect(screen.getByText("미실행")).toBeDefined();
  });

  it("작성 방식은 테스트를 시작한 방식으로 고정된다 (FR-002a)", () => {
    const { rerender } = render(<AuthoringBadge mode="record" />);
    expect(screen.getByText("RECORD")).toBeDefined();
    rerender(<AuthoringBadge mode="ai" />);
    expect(screen.getByText("AI")).toBeDefined();
  });

  it("최초 탭에는 탭 배지를 붙이지 않는다", () => {
    const { container, rerender } = render(<TabBadge tab={0} />);
    expect(container.textContent).toBe("");
    rerender(<TabBadge tab={2} />);
    expect(screen.getByText("탭 2")).toBeDefined();
  });
});
