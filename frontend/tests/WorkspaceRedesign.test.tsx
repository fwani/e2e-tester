import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, useLocation } from "react-router";
import { WorkspaceNavigation } from "../src/app/WorkspaceNavigation";
import { Toast, ToastDock, Toaster } from "../src/ui/Toast";

vi.mock("../src/app/appStore", () => ({
  useAppState: (select: (state: unknown) => unknown) => select({ project: { name: "QA 프로젝트" } }),
}));
afterEach(cleanup);
function Location() { return <output aria-label="현재 경로">{useLocation().pathname}</output>; }

describe("작업 공간 내비게이션", () => {
  it("프로젝트를 표시하고 테스트 작성·설정·프로젝트 전환으로 이동한다", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><WorkspaceNavigation /><Location /></MemoryRouter>);
    expect(screen.getByText("QA 프로젝트")).toBeTruthy();
    for (const [name, path] of [["테스트 작성", "/tests/new"], ["비밀 값", "/secrets"], ["키 관리", "/keys"], ["QA 프로젝트", "/projects"], ["테스트 라이브러리", "/"]] as const) {
      await user.click(screen.getByRole("link", { name: new RegExp(name) }));
      expect(screen.getByLabelText("현재 경로").textContent).toBe(path);
    }
  });
  it("작업대의 축소 메뉴에서도 이름으로 찾고 목록으로 돌아갈 수 있다", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter initialEntries={["/tests/TC-001/edit"]}><WorkspaceNavigation /><Location /></MemoryRouter>);
    expect(screen.getByLabelText("작업 공간").className).toContain("is-compact");
    await user.click(screen.getByRole("link", { name: "테스트 라이브러리" }));
    expect(screen.getByLabelText("현재 경로").textContent).toBe("/");
    expect(screen.getByLabelText("작업 공간").className).not.toContain("is-compact");
  });
});

describe("작업대 알림 영역", () => {
  it("알림을 작업대 안 한 곳에 표시하고 닫기를 제공한다", async () => {
    const dismiss = vi.fn();
    const user = userEvent.setup();
    const view = render(<Toaster docked><section aria-label="작업대"><ToastDock /><button>Step 수정</button><Toast onDismiss={dismiss}>변경을 저장했습니다.</Toast></section></Toaster>);
    await screen.findByText("변경을 저장했습니다.");
    expect(document.querySelectorAll("[data-toast-layer]").length).toBe(1);
    expect(screen.getByLabelText("작업대").contains(screen.getByRole("status"))).toBe(true);
    await user.click(screen.getByRole("button", { name: "알림 닫기" }));
    await waitFor(() => expect(dismiss).toHaveBeenCalledOnce());
    expect(view.container.querySelector(".workspace-notice-dock")).toBeTruthy();
  });
});
