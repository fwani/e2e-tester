/**
 * 작업 계획의 진척 표시 (025 T061 · US5).
 *
 * ## 무엇을 재는가
 *
 * **사용자와 AI 가 같은 목록을 본다**는 것이 이 패널의 전부다. 둘이 갈라지면 사용자는
 * 「AI 가 무엇을 하고 있는지」를 추측해야 하고, 그 추측이 025 전체가 없애려는 것이다.
 *
 * 그래서 AI 에게 가는 문자열과 **같은 기호**(`✓`·`▶`·`—`)를 쓴다. 여기서 다른 기호를
 * 쓰면 사용자가 보는 진척과 모델이 읽는 진척이 같은 값인지 확인할 길이 없어진다.
 *
 * ## 계획이 없는 것과 할 일이 없는 것은 다르다
 *
 * 정제에 실패했거나 사용자가 거절한 세션은 계획을 **쓰지 않는다.** 빈 목록을 그리면
 * 사용자는 「할 일이 없다」로 읽는데, 그것은 다른 사실이다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlanPanel } from "../src/components/workbench/PlanPanel";
import type { WorkPlan } from "../src/api/client";

const PLAN: WorkPlan = {
  items: [
    { id: "i1", order: 1, text: "관리자 계정으로 로그인한다", status: "done" },
    { id: "i2", order: 2, text: "메뉴관리로 이동한다", status: "done" },
    { id: "i3", order: 3, text: "새 메뉴를 등록한다", status: "pending" },
    { id: "i4", order: 4, text: "사용 여부를 전환한다", status: "pending" },
    {
      id: "i5",
      order: 5,
      text: "정렬 순서를 바꾼다",
      status: "skipped",
      skip_reason: "제품에 해당 설정이 없다",
    },
  ],
  constraints: [
    { text: "기존 등록된 데이터는 검증에 사용하지 않는다", scope: "global" },
    { text: "연결 주소는 {{url_a}} 를 쓴다", scope: "item", item_id: "i3" },
  ],
  source: "refined",
};

afterEach(cleanup);

describe("작업 계획 진척", () => {
  it("제약을 할 일보다 먼저 보인다", () => {
    render(<PlanPanel plan={PLAN} />);

    const headings = screen.getAllByRole("heading");
    expect(headings[0]?.textContent).toContain("반드시 지킬 것");
    expect(screen.getByText("기존 등록된 데이터는 검증에 사용하지 않는다")).toBeTruthy();
  });

  it("다음에 할 것을 지목한다", () => {
    render(<PlanPanel plan={PLAN} />);

    const next = screen.getByText("새 메뉴를 등록한다").closest("li");
    expect(next?.getAttribute("data-next")).toBe("true");

    const later = screen.getByText("사용 여부를 전환한다").closest("li");
    expect(later?.getAttribute("data-next")).toBe("false");
  });

  it("건너뛴 항목에 사유가 붙는다", () => {
    render(<PlanPanel plan={PLAN} />);

    expect(screen.getByText(/제품에 해당 설정이 없다/)).toBeTruthy();
  });

  it("남은 개수를 보인다", () => {
    render(<PlanPanel plan={PLAN} />);

    expect(screen.getByText("2개 남음")).toBeTruthy();
  });

  it("계획이 없으면 아무것도 그리지 않는다", () => {
    const { container } = render(<PlanPanel plan={null} />);

    expect(container.firstChild).toBeNull();
  });

  it("빈 계획도 그리지 않는다 — 할 일이 없는 것과 다른 사실이다", () => {
    const empty: WorkPlan = { items: [], constraints: [], source: "refined" };
    const { container } = render(<PlanPanel plan={empty} />);

    expect(container.firstChild).toBeNull();
  });

  it("끝난 항목만 되돌릴 수 있다 — 아직 안 한 것에는 되돌릴 것이 없다", () => {
    render(<PlanPanel plan={PLAN} onRevert={vi.fn()} />);

    // done 2건 + skipped 1건 = 3
    expect(screen.getAllByRole("button", { name: "되돌리기" })).toHaveLength(3);
  });

  it("되돌리면 어느 항목인지 알린다", async () => {
    const onRevert = vi.fn();
    render(<PlanPanel plan={PLAN} onRevert={onRevert} />);

    const row = screen.getByText("관리자 계정으로 로그인한다").closest("li");
    const button = row?.querySelector("button");
    expect(button).toBeTruthy();
    await userEvent.click(button as HTMLElement);

    expect(onRevert).toHaveBeenCalledWith("i1");
  });

  it("진행 중에는 되돌리기가 잠긴다 — AI 가 읽는 값을 바꾸는 조작이다", () => {
    render(<PlanPanel plan={PLAN} onRevert={vi.fn()} busy />);

    for (const button of screen.getAllByRole("button", { name: "되돌리기" })) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
    }
  });
});
