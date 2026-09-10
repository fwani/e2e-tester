/**
 * 빈 프로젝트 화면의 AI 카드가 **확인한 사실**을 말한다 (001 DR-021).
 *
 * 사용자가 겪은 것: `ANTHROPIC_API_KEY` 가 있고 `/api/ai/availability` 도
 * `available: true` 를 돌려주는데, 첫 화면은 「키 필요」와 「언어모델 키 등록하기」만
 * 보여줬다. 표식과 버튼이 고정 문구여서 응답을 아예 읽지 않았다. 그 상태에서는 이
 * 화면에서 AI 로 시작하는 길이 없다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";

const EMPTY_LISTING = { counts: { total: 0, pass: 0, fail: 0 }, tests: [], problems: [] };

const noop = () => undefined;

/** 경로별로 답한다 — 목록과 가능 여부는 다른 응답이다. */
function stubFetch(availability: { available: boolean; reason: string | null }) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.includes("/api/ai/availability") ? availability : EMPTY_LISTING;
      return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
    }),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("빈 프로젝트 화면의 AI 카드", () => {
  it("쓸 수 있으면 키를 요구하지 않고 시작하게 한다", async () => {
    stubFetch({ available: true, reason: null });
    const onCreate = vi.fn();

    render(<TestList onCreate={onCreate} onOpenResult={noop} onRun={noop} onOpenKeys={noop} />);

    const start = await screen.findByRole("button", { name: "AI 로 시작하기" });
    expect(screen.queryByText("키 필요")).toBeNull();
    expect(screen.queryByRole("button", { name: "언어모델 키 등록하기" })).toBeNull();

    start.click();
    expect(onCreate).toHaveBeenCalled();
  });

  it("쓸 수 없으면 사유를 그대로 보여주고 키 등록으로 보낸다", async () => {
    stubFetch({
      available: false,
      reason: "언어모델 자격 증명을 찾을 수 없습니다.",
    });

    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} onOpenKeys={noop} />);

    expect(await screen.findByText("키 필요")).toBeTruthy();
    expect(screen.getByText(/자격 증명을 찾을 수 없습니다/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "언어모델 키 등록하기" })).toBeTruthy();
  });
});
