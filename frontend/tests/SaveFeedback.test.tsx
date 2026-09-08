/**
 * 저장 피드백 (005 T074·T075 · FR-154~FR-159).
 *
 * **사용자가 직접 신고한 것이다.** "저장하면 목록으로 가거나, 저장이 완료되었다거나,
 * 등등 동작이 없어서, 저장이 된건지 모르고."
 *
 * 리포트 U-09 의 실측 — `POST …/save` 는 30 ms 에 200 으로 성공하는데:
 * - 성공 알림이 없다(토스트·배너·체크 어느 것도)
 * - 제목이 여전히 「TC-001 초안」
 * - 이름 입력칸과 「저장」이 그대로 활성
 * - 화면 이동도 없다
 * - 유일한 변화는 빵부스러기 하나. 알아채기 어렵다
 *
 * 그리고 U-10 — 저장에 성공했는데도 정리 버튼이 "Step 6개가 사라집니다" 를 띄웠다.
 *
 * **007 이행 2** — `RunnerPaused` 대신 `SessionWorkbench` 를 그린다. 저장 상자는 국면
 * 보조 영역으로 옮겼고 문구·판정 규칙은 그대로 `lib/wording.ts` 가 소유한다.
 */

import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { TestList } from "../src/pages/TestList";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import type { Step } from "../src/types/generated/step";

const noop = () => undefined;

function steps(n: number): Step[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `step-${String(i + 1).padStart(2, "0")}`,
    label: `Step ${i + 1}`,
    type: "click" as const,
    author: "human" as const,
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    target: {
      tag: "button",
      test_id: { value: "x", status: "verified" as const },
      role: null,
      accessible_name: null,
      role_status: null,
      label: null,
      text: null,
      stable_attr: null,
      css: { value: "#x", status: "verified" as const },
    },
  })) as unknown as Step[];
}

/**
 * 일시정지 국면의 세션. **`test_id` 를 비운다** — 「초안」 판정이 `persisted` 에
 * 달려 있으므로(005 재점검 U-03-a), 저장 여부를 재는 이 파일은 아직 파일이 없는
 * 세션을 대상으로 삼아야 한다.
 */
function pausedProps(overrides: Record<string, unknown> = {}) {
  const { savedAt, ...rest } = overrides as { savedAt?: string | null };
  return sessionProps({
    view: sessionView({
      state: "paused",
      // 저장하면 정의 파일이 생긴다 — 그때부터 「초안」이 아니다 (005 재점검 U-03-a).
      test_id: savedAt ? "TC-001" : null,
      steps: steps(6),
      current_step_index: 2,
      saved_at: savedAt ?? null,
      has_unsaved_changes: (overrides.hasChangesToSave as boolean | undefined) ?? false,
    }),
    outcomeOf: () => "pass",
    durationOf: () => 90,
    saveName: "TC-001",
    ...(rest as Record<string, unknown>),
  });
}

afterEach(cleanup);

describe("저장 성공 표시 (FR-154·FR-155·FR-156 · U-09)", () => {
  it("저장 전에는 성공 표시가 없다", () => {
    render(<SessionWorkbench {...pausedProps({ savedAt: null })} />);
    expect(screen.queryByText(/저장했습니다/)).toBeNull();
    expect(screen.getByRole("button", { name: "저장" })).toBeTruthy();
  });

  it("저장 성공을 화면을 옮기지 않고 알 수 있고 이름이 함께 보인다 (SC-217)", () => {
    render(<SessionWorkbench {...pausedProps({ savedAt: "2026-09-07T05:00:00Z" })} />);
    // role=status 는 스크린리더에도 전달된다.
    expect(screen.getByText("저장했습니다 · TC-001")).toBeTruthy();
  });

  it("저장 성공 후 제목에 「초안」이 없다 (FR-155)", () => {
    render(<SessionWorkbench {...pausedProps({ savedAt: "2026-09-07T05:00:00Z" })} />);
    expect(screen.queryByText(/초안/)).toBeNull();
    expect(screen.getByText("TC-001 · 저장됨")).toBeTruthy();
  });

  it("저장하지 않은 세션의 제목은 「초안」이다", () => {
    render(<SessionWorkbench {...pausedProps({ savedAt: null })} />);
    expect(screen.getByText("새 테스트 초안")).toBeTruthy();
  });

  it("저장 후 버튼이 「변경 저장」이고 바뀐 것이 없으면 비활성이다 (FR-156)", () => {
    render(
      <SessionWorkbench
        {...pausedProps({ savedAt: "2026-09-07T05:00:00Z", hasChangesToSave: false })}
      />,
    );
    const button = screen.getByRole("button", { name: "변경 저장" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("저장 후 다시 고쳤으면 「변경 저장」이 눌린다", () => {
    render(
      <SessionWorkbench
        {...pausedProps({ savedAt: "2026-09-07T05:00:00Z", hasChangesToSave: true })}
      />,
    );
    const button = screen.getByRole("button", { name: "변경 저장" });
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });

  it("「목록에서 보기」로 목록에 갈 수 있다 (FR-154)", async () => {
    const onShowList = vi.fn();
    render(
      <SessionWorkbench
        {...pausedProps({ savedAt: "2026-09-07T05:00:00Z", onShowList })} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "목록에서 보기" }));
    expect(onShowList).toHaveBeenCalledTimes(1);
  });

  it("저장 버튼은 in-flight 동안 잠긴다 — 중복 저장을 막는다", () => {
    render(<SessionWorkbench {...pausedProps({ busy: true })} />);
    const button = screen.getByRole("button", { name: "저장" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("저장된 세션의 정리 문구 (FR-159 · U-10)", () => {
  function listFetch() {
    return vi.fn(async () =>
      new Response(JSON.stringify({ tests: [], problems: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
  }

  const session = (overrides: Record<string, unknown>) =>
    ({
      session_id: "s1",
      state: "review",
      state_label: "검토 중",
      test_id: "TC-001",
      current_step_index: 0,
      steps: steps(6),
      tabs_open: 0,
      active_tab_index: 0,
      mirrored_tab_index: 0,
      edit_warnings: [],
      recorder_warnings: [],
      allowed_commands: [],
      has_unsaved_changes: false,
      authoring_mode: "record",
      pacing: "normal",
      ...overrides,
    }) as never;

  it("저장된 세션에는 「사라집니다」를 쓰지 않는다", async () => {
    vi.stubGlobal("fetch", listFetch());
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        activeSessions={[session({ saved_at: "2026-09-07T05:00:00Z" })]}
        onDiscardSession={noop}
      />,
    );
    // 정리 버튼 라벨부터 파괴적이지 않다.
    const button = await screen.findByRole("button", { name: "닫기" });
    await userEvent.click(button);
    expect(screen.getByText(/TC-001 로 저장돼 있습니다/)).toBeTruthy();
    expect(screen.queryByText(/사라집니다/)).toBeNull();
  });

  it("저장하지 않은 세션에는 기존 경고를 그대로 쓴다", async () => {
    vi.stubGlobal("fetch", listFetch());
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        activeSessions={[session({ saved_at: null, has_unsaved_changes: true })]}
        onDiscardSession={noop}
      />,
    );
    const button = await screen.findByRole("button", { name: "중지하고 버리기" });
    await userEvent.click(button);
    expect(screen.getByText(/Step 6개가 사라집니다/)).toBeTruthy();
  });
});
