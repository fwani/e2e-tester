/**
 * 목록의 실행 중 표시와 컨트롤 설명 (005 T094·T100·T101 · FR-168~FR-174).
 *
 * 리포트 U-16 — 실행 중 새로고침하면 목록으로 떨어진다. 상단 배너는 회수 수단을 주지만
 * **그 행의 상태 칩은 이전 실행의 `FAIL`** 이고 버튼도 이전 결과를 가리켰다. 지금 돌고
 * 있다는 표시가 행에는 없었다.
 *
 * U-06 — 연타로 세션이 둘 만들어졌을 때 구분 불가능한 배너가 두 줄로 떴다.
 * U-22 — `TRACE` 만 비활성인데 이유가 없고, 빈 탭은 "(기록 없음)" 한 줄이었다.
 * U-23 — 녹화 중에도 실행용 속도 컨트롤이 같은 자리에 그대로 있었다.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PacingControl } from "../src/components/PacingControl";
import { TestList } from "../src/pages/TestList";
import type { SessionView } from "../src/api/client";

const noop = () => undefined;

const row = (overrides: Record<string, unknown> = {}) => ({
  id: "TC-002",
  name: "실패한 테스트",
  step_count: 7,
  authoring_mode: "record",
  updated_at: "2026-09-07T00:00:00Z",
  last_run_at: "2026-09-07T00:00:03Z",
  outcome: "fail",
  failure_summary: null,
  ...overrides,
});

function listFetch(rows: unknown[]) {
  return vi.fn(async (input: RequestInfo | URL) => {
    if (String(input).includes("/api/tests")) {
      return new Response(JSON.stringify({ tests: rows, problems: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }
    return new Response("{}", { status: 200, headers: { "content-type": "application/json" } });
  });
}

const session = (overrides: Record<string, unknown> = {}) =>
  ({
    session_id: "abcdef123456",
    state: "replaying",
    state_label: "실행 중",
    test_id: "TC-002",
    current_step_index: 2,
    steps: [],
    tabs_open: 1,
    active_tab_index: 0,
    mirrored_tab_index: 0,
    edit_warnings: [],
    recorder_warnings: [],
    allowed_commands: [],
    has_unsaved_changes: false,
    authoring_mode: "record",
    pacing: "normal",
    ...overrides,
  }) as unknown as SessionView;

describe("실행 중인 테스트의 행 (FR-168 · U-16)", () => {
  it("행이 RUNNING 을 말하고 실행 화면으로 돌아갈 수단이 있다", async () => {
    vi.stubGlobal("fetch", listFetch([row()]));
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        activeSessions={[session()]}
        onResumeSession={noop}
      />,
    );

    await screen.findByText("실패한 테스트");
    expect(screen.getByText("RUNNING")).toBeTruthy();
    expect(screen.getByRole("button", { name: "실행 화면 보기" })).toBeTruthy();
    // 이전 실행의 결말이 행을 대표하지 않는다 — 지금 돌고 있다는 사실이 이긴다.
    //
    // 화면에는 헤더의 통계 칩("FAIL 1")이 하나 있다. 행의 칩이 RUNNING 이면 FAIL 은
    // 그 하나뿐이어야 한다.
    expect(screen.getAllByText("FAIL")).toHaveLength(1);
  });

  it("실행 중이 아니면 이전 결말을 그대로 보여준다", async () => {
    vi.stubGlobal("fetch", listFetch([row()]));
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} activeSessions={[]} />);

    await screen.findByText("실패한 테스트");
    // 헤더 통계 칩 + 행의 결말 칩 = 둘.
    expect(screen.getAllByText("FAIL")).toHaveLength(2);
    expect(screen.queryByText("RUNNING")).toBeNull();
  });

  it("중지·부분 성공 결말도 칩으로 구분된다 (FR-141)", async () => {
    for (const [outcome, chip] of [
      ["stopped", "STOPPED"],
      ["partial_pass", "PARTIAL"],
    ] as const) {
      vi.stubGlobal("fetch", listFetch([row({ outcome })]));
      const view = render(
        <TestList onCreate={noop} onOpenResult={noop} onRun={noop} activeSessions={[]} />,
      );
      await screen.findByText("실패한 테스트");
      expect(screen.getByText(chip)).toBeTruthy();
      view.unmount();
    }
  });
});

describe("세션 배너 (FR-169·FR-170)", () => {
  it("새로 고침 수단이 있다 (U-17)", async () => {
    vi.stubGlobal("fetch", listFetch([]));
    const onRefreshSessions = vi.fn();
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        activeSessions={[session()]}
        onRefreshSessions={onRefreshSessions}
      />,
    );
    const button = await screen.findByRole("button", { name: "세션 상태 새로 고침" });
    expect(button).toBeTruthy();
  });

  it("같은 테스트의 세션이 여럿이면 구분 정보를 준다 (U-06)", async () => {
    vi.stubGlobal("fetch", listFetch([]));
    render(
      <TestList
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        activeSessions={[
          session({ session_id: "aaaaaa111111" }),
          session({ session_id: "bbbbbb222222" }),
        ]}
      />,
    );
    await screen.findByText("진행 중인 세션이 있습니다");
    // 두 줄이 구분된다 — 이전에는 완전히 같은 문장이 두 번 떴다.
    expect(screen.getByText(/#aaaaaa/)).toBeTruthy();
    expect(screen.getByText(/#bbbbbb/)).toBeTruthy();
  });

  it("세션이 하나면 구분자를 붙이지 않는다 — 잡음을 만들지 않는다", async () => {
    vi.stubGlobal("fetch", listFetch([]));
    render(
      <TestList onCreate={noop} onOpenResult={noop} onRun={noop} activeSessions={[session()]} />,
    );
    await screen.findByText("진행 중인 세션이 있습니다");
    expect(screen.queryByText(/#abcdef/)).toBeNull();
  });
});

describe("속도 컨트롤의 국면 라벨 (FR-174 · U-23)", () => {
  it("실행 국면에서는 「속도」다", () => {
    render(<PacingControl value="normal" onChange={noop} />);
    expect(screen.getByText("속도")).toBeTruthy();
  });

  it("사람이 조작하는 국면에서는 「다음 실행 속도」로 밝힌다", () => {
    render(<PacingControl value="normal" onChange={noop} manipulationPhase />);
    expect(screen.getByText("다음 실행 속도")).toBeTruthy();
    // 감추지 않는다 — 004 FR-109 가 그 값을 다음 실행에 쓴다.
    expect(screen.getByText("보통")).toBeTruthy();
  });
});
