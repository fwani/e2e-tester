/** 빈 목록은 공통 시작 화면으로 안내한다. 작성 방식과 AI 준비 상태는 거기서 확인한다. */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TestList } from "../src/pages/TestList";

const EMPTY_LISTING = { counts: { total: 0, pass: 0, fail: 0 }, tests: [], problems: [] };
const noop = () => undefined;

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("빈 프로젝트의 단일 시작 경로", () => {
  it("첫 테스트 만들기가 공통 시작 화면으로 이동한다", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(EMPTY_LISTING), { status: 200 })));
    const onCreate = vi.fn();
    render(<TestList onCreate={onCreate} onOpenResult={noop} onRun={noop} onOpenKeys={noop} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "첫 테스트 만들기" }));
    expect(onCreate).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "AI 로 시작하기" })).toBeNull();
    expect(screen.queryByRole("button", { name: "녹화로 시작하기" })).toBeNull();
  });

  it("방식을 고르기 전에 AI 자격 증명을 중복 조회하거나 요구하지 않는다", async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL) => new Response(JSON.stringify(EMPTY_LISTING), { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} onOpenKeys={noop} />);
    await screen.findByRole("button", { name: "첫 테스트 만들기" });
    expect(fetcher.mock.calls.some((args) => String(args[0]).includes("/ai/availability"))).toBe(false);
    expect(screen.queryByText("키 필요")).toBeNull();
    expect(screen.queryByRole("textbox", { name: "테스트 검색" })).toBeNull();
  });
});
