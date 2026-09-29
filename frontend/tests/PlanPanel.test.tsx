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

/**
 * 025 는 이 패널을 **접힌 채로** 그린다 (2026-09-29 사용자 보고). 목록을 보려면 먼저
 * 펼쳐야 한다 — 그것이 이 패널의 기본 상태이고, 검증도 그 상태에서 출발한다.
 */
async function expand() {
  await userEvent.click(screen.getByRole("button", { name: /할 일 목록 펼치기/ }));
}

describe("작업 계획 진척", () => {
  it("접힌 채로 시작한다 — 대화와 답변 자리를 빼앗지 않는다", () => {
    render(<PlanPanel plan={PLAN} />);

    const heading = document.querySelector(".plan-heading strong");
    // 「3」은 완료 2 + 건너뜀 1 이다 — 남은 것과 대비되는 「결론이 난 것」의 수다.
    expect(heading?.textContent).toContain("할 일 3/5");
    expect(heading?.textContent).toContain("남은 것 2");
    // 목록은 접혀 있다. `hidden` 이므로 DOM 에는 있지만 보이지 않는다.
    const body = document.getElementById("plan-body");
    expect(body?.hasAttribute("hidden")).toBe(true);
  });

  it("접혀 있어도 다음 할 일 한 줄은 보인다", () => {
    render(<PlanPanel plan={PLAN} />);

    // 「AI 가 지금 무엇을 하고 있는가」에 가장 가까운 사실이다.
    expect(document.querySelector(".plan-next")?.textContent).toContain(
      "새 메뉴를 등록한다",
    );
  });

  it("막힘 답변을 기다릴 때는 숨는다 — 답변이 최우선이다", () => {
    const { container } = render(<PlanPanel plan={PLAN} hidden />);

    expect(container.firstChild).toBeNull();
  });

  it("제약을 할 일보다 먼저 보인다", async () => {
    render(<PlanPanel plan={PLAN} />);
    await expand();

    const headings = screen.getAllByRole("heading");
    expect(headings[0]?.textContent).toContain("반드시 지킬 것");
    expect(screen.getByText("기존 등록된 데이터는 검증에 사용하지 않는다")).toBeTruthy();
  });

  it("다음에 할 것을 지목한다", async () => {
    render(<PlanPanel plan={PLAN} />);
    await expand();

    const next = screen.getByText("새 메뉴를 등록한다").closest("li");
    expect(next?.getAttribute("data-next")).toBe("true");

    const later = screen.getByText("사용 여부를 전환한다").closest("li");
    expect(later?.getAttribute("data-next")).toBe("false");
  });

  it("건너뛴 항목에 사유가 붙는다", async () => {
    render(<PlanPanel plan={PLAN} />);
    await expand();

    expect(screen.getByText(/제품에 해당 설정이 없다/)).toBeTruthy();
  });

  it("남은 개수를 머리줄에 보인다 — 펼치지 않아도 알 수 있다", () => {
    render(<PlanPanel plan={PLAN} />);

    expect(document.querySelector(".plan-heading strong")?.textContent).toContain(
      "남은 것 2",
    );
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
    const buttons = document.querySelectorAll(".plan-items button");
    expect(buttons).toHaveLength(3);
  });

  it("되돌리면 어느 항목인지 알린다", async () => {
    const onRevert = vi.fn();
    render(<PlanPanel plan={PLAN} onRevert={onRevert} />);
    await expand();

    const row = screen.getByText("관리자 계정으로 로그인한다").closest("li");
    const button = row?.querySelector("button");
    expect(button).toBeTruthy();
    await userEvent.click(button as HTMLElement);

    expect(onRevert).toHaveBeenCalledWith("i1");
  });

  it("진행 중에는 되돌리기가 잠긴다 — AI 가 읽는 값을 바꾸는 조작이다", async () => {
    render(<PlanPanel plan={PLAN} onRevert={vi.fn()} busy />);
    await expand();

    for (const button of document.querySelectorAll(".plan-items button")) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
    }
  });
});
