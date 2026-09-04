/**
 * 목록 화면이 **살아 있는 세션**을 알리고 되찾게 한다 (UX U-05).
 *
 * 사용자가 겪은 것: 녹화 도중 새로고침 → 빈 목록. 서버에는 recording · Step 5개 세션과
 * 실제 브라우저 창이 그대로 있었지만 화면 어디에도 돌아가는 길이 없었다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { SessionView } from "../src/api/client";
import { TestList } from "../src/pages/TestList";

const EMPTY_LISTING = { counts: { total: 0, pass: 0, fail: 0 }, tests: [], problems: [] };

const live = {
  session_id: "sess-1",
  state: "recording",
  state_label: "녹화 중",
  test_id: null,
  current_step_index: 5,
  steps: [1, 2, 3, 4, 5].map((i) => ({ id: `s${i}` })),
  tabs_open: 1,
  active_tab_index: 0,
  mirrored_tab_index: 0,
  edit_warnings: [],
  recorder_warnings: [],
  allowed_commands: [],
  has_unsaved_changes: true,
  authoring_mode: "record",
} as unknown as SessionView;

const noop = () => undefined;

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response(JSON.stringify(EMPTY_LISTING), { status: 200 }))),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("진행 중 세션 배너", () => {
  it("세션이 없으면 나오지 않는다", async () => {
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} />);
    expect(await screen.findByText(/아직 테스트가 없습니다/)).toBeTruthy();
    expect(screen.queryByText("진행 중인 세션이 있습니다")).toBeNull();
  });

  it("무엇이 살아 있는지 말하고 이어서 보게 한다", async () => {
    const onResume = vi.fn();
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        activeSessions={[live]}
        onResumeSession={onResume}
        onDiscardSession={noop}
      />,
    );

    const banner = await screen.findByText("진행 중인 세션이 있습니다");
    const box = banner.closest("[data-active-sessions]");
    expect(box?.textContent).toContain("녹화 중 · Step 5개 · 저장되지 않음");

    fireEvent.click(screen.getByRole("button", { name: "이어서 보기" }));
    expect(onResume).toHaveBeenCalledWith(live);
  });

  it("버리기는 한 번 더 묻고 나서야 실행한다", async () => {
    const onDiscard = vi.fn();
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        activeSessions={[live]}
        onResumeSession={noop}
        onDiscardSession={onDiscard}
      />,
    );
    await screen.findByText("진행 중인 세션이 있습니다");

    fireEvent.click(screen.getByRole("button", { name: "중지하고 버리기" }));
    expect(onDiscard).not.toHaveBeenCalled();
    expect(screen.getByText(/Step 5개가 사라집니다/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(screen.queryByText(/사라집니다/)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "중지하고 버리기" }));
    fireEvent.click(screen.getByRole("button", { name: "버리기" }));
    expect(onDiscard).toHaveBeenCalledWith("sess-1");
  });
});
