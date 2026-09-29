/**
 * 정제 결과를 확인하고 시작한다 (025 T047 · US4).
 *
 * ## 이 파일이 지키는 경계
 *
 * **정제는 작성의 관문이 아니다** (FR-019·FR-020). 실패했든 사용자가 결과를 받아들이지
 * 않든, 작성을 시작할 수 있어야 한다. 그 길이 막히면 이 기능은 값이 아니라 비용이다.
 *
 * ## 확인 없이 시작되는 경로를 만들지 않는다 (FR-018)
 *
 * 정제 결과를 보여 주기 전에 세션이 만들어지면, 사용자는 브라우저가 뜬 뒤에 계획을 보고
 * 이미 시작된 일을 되돌려야 한다.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ComposeView } from "../src/pages/ComposeView";
import * as client from "../src/api/client";

const PROJECT = {
  default_start_url: "https://example.test/login",
} as unknown as client.ProjectView;

const PLAN: client.WorkPlan = {
  items: [
    { id: "i1", order: 1, text: "로그인한다", status: "pending" },
    { id: "i2", order: 2, text: "메뉴관리로 이동한다", status: "pending" },
  ],
  constraints: [{ text: "기존 데이터는 검증에 쓰지 않는다", scope: "global" }],
  source: "refined",
};

function setup(refine: () => Promise<client.RefineResponse>) {
  vi.spyOn(client.ai, "availability").mockResolvedValue({
    available: true,
    reason: null,
  });
  vi.spyOn(client.ai, "refine").mockImplementation(refine);
  const onStartAi = vi.fn();
  render(
    <ComposeView
      project={PROJECT}
      onCancel={vi.fn()}
      onRecord={vi.fn()}
      onStartAi={onStartAi}
      initialInstruction="로그인하고 메뉴관리로 간다"
    />,
  );
  return onStartAi;
}

/** AI 모드를 고르고 시작을 누른다 — 정제가 불리는 지점까지. */
async function askToStart() {
  await userEvent.click(screen.getByRole("button", { name: /AI로 만들기/ }));
  await userEvent.click(screen.getByRole("button", { name: /AI 시작/ }));
}

beforeEach(() => vi.restoreAllMocks());
afterEach(cleanup);

describe("정제 결과 확인", () => {
  it("확인하기 전에는 세션을 만들지 않는다", async () => {
    const onStartAi = setup(async () => ({ refined: true, plan: PLAN, notes: [] }));

    await askToStart();

    await waitFor(() => expect(screen.getByText("이렇게 진행합니다")).toBeTruthy());
    expect(onStartAi).not.toHaveBeenCalled();
  });

  it("계획을 보여 주고, 확정하면 그것으로 시작한다", async () => {
    const onStartAi = setup(async () => ({ refined: true, plan: PLAN, notes: [] }));

    await askToStart();
    await waitFor(() => expect(screen.getByText("로그인한다")).toBeTruthy());
    await userEvent.click(screen.getByRole("button", { name: "이 계획으로 시작" }));

    expect(onStartAi).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(String),
      PLAN,
    );
  });

  it("뜻이 바뀐 자리를 알린다 — 자격 증명 치환 같은", async () => {
    setup(async () => ({
      refined: true,
      plan: PLAN,
      notes: ["「비밀번호」 값을 변수 참조로 바꿨습니다."],
    }));

    await askToStart();

    await waitFor(() =>
      expect(screen.getByText(/변수 참조로 바꿨습니다/)).toBeTruthy(),
    );
  });

  it("원문으로 진행하는 길이 항상 있다", async () => {
    const onStartAi = setup(async () => ({ refined: true, plan: PLAN, notes: [] }));

    await askToStart();
    await waitFor(() => expect(screen.getByText("이렇게 진행합니다")).toBeTruthy());
    await userEvent.click(screen.getByRole("button", { name: "원문으로 시작" }));

    expect(onStartAi).toHaveBeenCalledWith(expect.any(String), expect.any(String), null);
  });

  it("정제에 실패해도 시작할 수 있다 — 정제는 관문이 아니다", async () => {
    const onStartAi = setup(async () => ({
      refined: false,
      plan: null,
      notes: ["지시문을 정제하지 못했습니다."],
    }));

    await askToStart();
    await waitFor(() =>
      expect(screen.getByText(/정제하지 못했습니다/)).toBeTruthy(),
    );

    // 계획이 없으므로 「이 계획으로 시작」은 없고, 원문 경로만 남는다.
    expect(screen.queryByRole("button", { name: "이 계획으로 시작" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "원문으로 시작" }));

    expect(onStartAi).toHaveBeenCalledWith(expect.any(String), expect.any(String), null);
  });

  it("호출 자체가 실패해도 같은 자리로 수렴한다", async () => {
    const onStartAi = setup(async () => {
      throw new Error("네트워크가 끊겼다");
    });

    await askToStart();
    await waitFor(() =>
      expect(screen.getByText(/원문 그대로 진행할 수 있습니다/)).toBeTruthy(),
    );
    await userEvent.click(screen.getByRole("button", { name: "원문으로 시작" }));

    expect(onStartAi).toHaveBeenCalled();
  });

  it("지시문을 고치러 돌아갈 수 있다", async () => {
    setup(async () => ({ refined: true, plan: PLAN, notes: [] }));

    await askToStart();
    await waitFor(() => expect(screen.getByText("이렇게 진행합니다")).toBeTruthy());
    await userEvent.click(screen.getByRole("button", { name: "지시문 고치기" }));

    expect(screen.queryByText("이렇게 진행합니다")).toBeNull();
  });
});
