/**
 * 프로젝트 목록으로 가는 길 (사용자 보고 · 2026-09-09).
 *
 * ## 보고된 것
 *
 * > 프로젝트 목록으로 가는 방법이 없다.
 *
 * ## 왜 그랬나
 *
 * 프로젝트 선택 화면(`ProjectSetup`)은 처음부터 있었다. 그런데 거기로 가는 길이
 * **`project.current()` 가 실패할 때 하나뿐**이었다 — 즉 첫 실행에만 열렸다. 한 번
 * 프로젝트를 열고 나면 다른 프로젝트로 갈 방법이 화면 어디에도 없었고, 남은 수단은
 * 서버를 다시 띄우는 것뿐이었다.
 *
 * 그래서 두 가지를 붙인다.
 *
 * 1. 목록 화면의 **프로젝트 이름 옆**에 「바꾸기」 — 「어느 프로젝트인가」를 읽는 자리가
 *    「다른 것으로 간다」를 찾는 자리다.
 * 2. 선택 화면에 **「돌아가기」** — 이 화면이 첫 화면이기만 하던 동안에는 돌아갈 곳이
 *    없었지만, 이제 중간 화면이기도 하므로 마음을 바꿀 수 있어야 한다. 첫 실행에는
 *    돌아갈 곳이 없으므로 그때는 그리지 않는다.
 */
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProjectSetup } from "../src/pages/ProjectSetup";
import { TestList } from "../src/pages/TestList";

const LISTING = {
  counts: { total: 0, pass: 0, fail: 0 },
  problems: [],
  tests: [],
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      String(url).includes("/api/project/list")
        ? new Response(JSON.stringify({ projects: [], warning: null }), { status: 200 })
        : new Response(JSON.stringify(LISTING), { status: 200 }),
    ),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

const noop = () => undefined;

describe("목록 화면에서 프로젝트를 바꿀 수 있다", () => {
  it("프로젝트 이름 옆에 목록으로 가는 길이 있다", async () => {
    const onOpenProjects = vi.fn();
    render(
      <TestList
        projectName="픽스처 프로젝트"
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        onOpenProjects={onOpenProjects}
      />,
    );
    await waitFor(() => expect(screen.getByText("픽스처 프로젝트")).toBeTruthy());

    const link = screen.getByRole("button", { name: "바꾸기" });
    act(() => link.click());
    expect(onOpenProjects).toHaveBeenCalledOnce();
  });

  it("길이 프로젝트 이름과 같은 자리에 있다 — 찾을 곳이 거기다", async () => {
    render(
      <TestList
        projectName="픽스처 프로젝트"
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        onOpenProjects={noop}
      />,
    );
    await waitFor(() => expect(screen.getByText("픽스처 프로젝트")).toBeTruthy());
    const name = screen.getByText("픽스처 프로젝트");
    expect(name.parentElement?.contains(screen.getByRole("button", { name: "바꾸기" }))).toBe(
      true,
    );
  });
});

describe("선택 화면에서 되돌아갈 수 있다", () => {
  it("열려 있던 프로젝트가 있으면 돌아가는 길이 있다", async () => {
    const onCancel = vi.fn();
    render(<ProjectSetup onOpened={noop} onCancel={onCancel} />);
    await screen.findByRole("button", { name: "돌아가기" });
    // 목록을 불러오며 다시 그리므로 누르기 직전에 다시 찾는다.
    fireEvent.click(screen.getByRole("button", { name: "돌아가기" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("첫 화면에는 돌아가는 길이 없다 — 돌아갈 곳이 없다", async () => {
    render(<ProjectSetup onOpened={noop} />);
    await waitFor(() => expect(screen.getByText("프로젝트")).toBeTruthy());
    expect(screen.queryByRole("button", { name: "돌아가기" })).toBeNull();
  });
});
