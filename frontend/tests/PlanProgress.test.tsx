/**
 * 세션 화면의 진척 표시 (025 T088 · 수렴 작업).
 *
 * ## 왜 이 파일이 수렴에서 나왔는가
 *
 * `PlanPanel` 을 만들고 정제 미리보기(`ComposeView`)에만 붙인 채로 US5 를 완료 표시했다.
 * **세션 화면 배선을 하지 않았다** — 백엔드는 이벤트도 내보내고 API 도 있는데 아무도
 * 읽지 않는 상태였고, 백엔드 검증만 있었으므로 전부 통과했다.
 *
 * `/speckit-converge` 가 그것을 찾았다. 이 파일이 같은 일이 다시 일어나지 않게 한다.
 *
 * ## 무엇을 재는가
 *
 * **완료 보고가 남은 일을 덮지 않는다**가 가장 중요하다 (FR-028). 모델은 「끝냈다」고
 * 말하면서 구획 하나를 건너뛸 수 있고, 그 사실이 사용자에게 보이지 않으면 사용자는
 * 테스트가 온전하다고 믿는다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AiAuthoringPanel } from "../src/components/workbench/AiAuthoringPanel";
import type { WorkPlan } from "../src/api/client";

const PLAN: WorkPlan = {
  items: [
    { id: "i1", order: 1, text: "로그인한다", status: "done" },
    { id: "i2", order: 2, text: "메뉴를 등록한다", status: "pending" },
  ],
  constraints: [{ text: "기존 데이터는 검증에 쓰지 않는다", scope: "global" }],
  source: "refined",
};

function show(over: Record<string, unknown> = {}) {
  return render(
    <AiAuthoringPanel
      work={null}
      entries={[]}
      instruction="원래 지시문"
      status="작성 중"
      chooseBlocked={{ allowed: true } as never}
      onChooseBlocked={vi.fn()}
      busy={false}
      {...over}
    >
      <div />
    </AiAuthoringPanel>,
  );
}

afterEach(cleanup);

describe("세션 화면의 진척", () => {
  it("계획이 있으면 할 일과 제약을 보인다", () => {
    show({ plan: PLAN });

    expect(screen.getByText("기존 데이터는 검증에 쓰지 않는다")).toBeTruthy();
    expect(screen.getByText("메뉴를 등록한다")).toBeTruthy();
  });

  it("계획이 없으면 아무것도 그리지 않는다 — FR-012 회귀 방어선", () => {
    show({ plan: null });

    expect(screen.queryByText("반드시 지킬 것")).toBeNull();
    expect(screen.queryByText("할 일")).toBeNull();
  });

  it("남은 항목을 완료 보고와 함께 보인다 — 덮지 않는다 (FR-028)", () => {
    show({
      plan: PLAN,
      remainingItems: [
        { order: 3, text: "삭제 확인창에서 취소를 선택한다" },
        { order: 4, text: "삭제를 확정한다" },
      ],
    });

    expect(screen.getByText("아직 하지 않은 일 2개")).toBeTruthy();
    expect(screen.getByText(/삭제 확인창에서 취소를 선택한다/)).toBeTruthy();
  });

  it("남은 항목이 없으면 그 자리를 만들지 않는다", () => {
    show({ plan: PLAN, remainingItems: [] });

    expect(screen.queryByText(/아직 하지 않은 일/)).toBeNull();
  });

  it("사용자가 항목을 되돌린다 — 모델은 할 수 없는 일이다", async () => {
    const onRevertItem = vi.fn();
    show({ plan: PLAN, onRevertItem });

    const row = screen.getByText("로그인한다").closest("li");
    await userEvent.click(row?.querySelector("button") as HTMLElement);

    expect(onRevertItem).toHaveBeenCalledWith("i1");
  });

  it("진행 중에는 되돌리기가 잠긴다", () => {
    show({ plan: PLAN, onRevertItem: vi.fn(), busy: true });

    const button = screen.getByRole("button", { name: "되돌리기" }) as HTMLButtonElement;
    expect(button.disabled).toBe(true);
  });
});
