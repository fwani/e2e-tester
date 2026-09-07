/**
 * 005 Phase 12 — T110 재발 검증이 등록한 남은 작업의 회귀 고정 (T112~T122).
 *
 * 출처: [docs/ux/ux-recheck-005.md](../../docs/ux/ux-recheck-005.md). 이 파일이 지키는
 * 것은 **한 화면이 두 가지를 주장하지 않는다** 는 성질이다. 부분 재발 2건(U-03·U-04)은
 * 모두 핵심 증상이 사라진 뒤 곁가지 문구·잔여 UI 가 남은 형태였고, 그 곁가지들은 전부
 * "고친 곳 옆에 같은 사실을 말하는 다른 곳이 있었다" 는 한 가지 원인을 공유한다.
 *
 * 그래서 단정은 문구 하나가 아니라 **두 자리가 같은 말을 하는지**를 본다.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";

import { MirrorView } from "../src/components/MirrorView";
import { RunnerPaused } from "../src/pages/RunnerPaused";
import { TestList } from "../src/pages/TestList";
import { isRunning } from "../src/lib/sessionState";
import { pausedAfterLabel, sessionTitle } from "../src/lib/wording";
import type { SessionState, SessionView } from "../src/api/client";
import type { Step } from "../src/types/generated/step";
import { initialLocation, locationToSearch } from "../src/hooks/useScreenUrl";

const noop = () => undefined;

function steps(n: number): Step[] {
  return Array.from({ length: n }, (_, i) => ({
    id: `step-${String(i + 1).padStart(2, "0")}`,
    label: `Step ${i + 1}`,
    type: "click" as const,
    author: "human" as const,
    tab: 0,
    timeout_ms: 20_000,
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

function pausedProps(overrides: Record<string, unknown> = {}) {
  return {
    title: "TC-001",
    authoring: "record" as const,
    steps: steps(7),
    currentStepIndex: 5,
    currentUrl: "http://127.0.0.1:4300/projects.html",
    mirror: <div />,
    mirroredTab: 0,
    busy: false,
    review: false,
    editWarnings: [],
    saveName: "",
    selectedStepId: null,
    reordering: false,
    outcomeOf: () => "pending" as const,
    durationOf: () => undefined,
    onSaveNameChange: noop,
    onSave: noop,
    onResume: noop,
    onStop: noop,
    onRunFrom: noop,
    onEditStep: noop,
    onDeleteStep: noop,
    onSelectStep: noop,
    onToggleReorder: noop,
    onApplyReorder: noop,
    onRecordActionsStart: noop,
    onRecordActionsStop: noop,
    onAddAssertion: noop,
    onNaturalLanguage: noop,
    testId: "TC-001",
    ...overrides,
  } as unknown as ComponentProps<typeof RunnerPaused>;
}

// ─── T112 — 재실행 세션 제목의 「초안」 (U-03-a · FR-134) ────────────────────

describe("T112 저장된 테스트의 재실행 세션은 초안이 아니다 (FR-134 · U-03-a)", () => {
  it("이 세션에서 저장하지 않았어도 정의 파일이 있으면 초안이 아니다", () => {
    // 재점검이 본 상태 그대로 — 재실행 세션은 `saved_at` 이 없다.
    render(<RunnerPaused {...pausedProps({ persisted: true, savedAt: null })} />);
    expect(screen.queryByText(/초안/)).toBeNull();
    expect(screen.getByText("TC-001 · 저장됨")).toBeTruthy();
  });

  it("아직 파일이 없는 녹화는 초안이다 — 「초안」을 없애는 것이 목적이 아니다", () => {
    render(
      <RunnerPaused
        {...pausedProps({ title: "새 테스트", testId: "TC-000", persisted: false, savedAt: null })}
      />,
    );
    expect(screen.getByText("새 테스트 초안")).toBeTruthy();
  });

  it("저장된 테스트에 저장하지 않은 편집이 남으면 「저장됨」을 단정하지 않는다", () => {
    render(
      <RunnerPaused
        {...pausedProps({ persisted: true, savedAt: null, hasUnsavedChanges: true })}
      />,
    );
    expect(screen.getByText("TC-001 · 저장하지 않은 변경 있음")).toBeTruthy();
  });

  it("판정 규칙은 사전 한 곳에 있다 — 화면이 각자 만들지 않는다", () => {
    const base = { title: "TC-003", hasUnsavedChanges: false };
    expect(sessionTitle({ ...base, persisted: false, savedAt: null })).toBe("TC-003 초안");
    expect(sessionTitle({ ...base, persisted: true, savedAt: null })).toBe("TC-003 · 저장됨");
    expect(sessionTitle({ ...base, persisted: false, savedAt: "2026-09-07T05:00:00Z" })).toBe(
      "TC-003 · 저장됨",
    );
  });
});

// ─── T113 — 중지 결과 화면 (U-03-a · FR-133 · ui-contract §8) ───────────────

describe("T113 중지 결과 화면은 저장 프롬프트가 아니다 (FR-133 · U-03-a)", () => {
  const stopResult = {
    summary: "중지 · Step 06 에서 중지 · 5 / 7 통과 · 3.21 s",
    stoppedStepIndex: 5,
    onRerunAll: noop,
    onRerunFromStop: noop,
    onBack: noop,
  };

  it("ui-contract §8 의 다음 행동 네 개가 모두 있다 — 이전에는 셋이었다", () => {
    render(
      <RunnerPaused
        {...pausedProps({
          review: true,
          persisted: true,
          savedAt: null,
          hasChangesToSave: false,
          stopResult,
          onShowResult: noop,
        })}
      />,
    );
    expect(screen.getByRole("button", { name: "결과 자세히 보기" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "처음부터 실행" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Step 06부터 실행" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "목록으로" })).toBeTruthy();
  });

  it("저장된 테스트의 결말 화면에는 이름 입력칸과 「저장」이 없다 (§8 금지 4)", () => {
    render(
      <RunnerPaused
        {...pausedProps({
          review: true,
          persisted: true,
          savedAt: null,
          hasChangesToSave: false,
          stopResult,
          onShowResult: noop,
        })}
      />,
    );
    expect(screen.queryByLabelText("테스트 이름")).toBeNull();
    expect(screen.queryByRole("button", { name: /^저장$/ })).toBeNull();
  });

  it("이름 없는 녹화를 중지한 결말 화면에는 저장이 남는다 — 감추면 기록이 사라진다", () => {
    render(
      <RunnerPaused
        {...pausedProps({
          title: "새 테스트",
          review: true,
          persisted: false,
          savedAt: null,
          stopResult,
        })}
      />,
    );
    expect(screen.getByLabelText("테스트 이름")).toBeTruthy();
  });

  it("결말 화면이 아니면 저장 자리를 걷지 않는다 (FR-156 은 비활성을 요구한다)", () => {
    render(
      <RunnerPaused
        {...pausedProps({
          persisted: true,
          savedAt: "2026-09-07T05:00:00Z",
          hasChangesToSave: false,
        })}
      />,
    );
    const button = screen.getByRole("button", { name: "변경 저장" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
});

// ─── T116 — 미러 오버레이 (U-04-b · FR-142·FR-146) ──────────────────────────

describe("T116 미리보기 안내가 실제 상태와 같은 말을 한다 (U-04-b)", () => {
  it("전이 중에는 유지를 단정하지 않는다 — 아직 실행 중이다", () => {
    render(<MirrorView frame="AAA" phase="pausing" />);
    expect(screen.getByText("일시정지 중…")).toBeTruthy();
    expect(screen.getByText(/현재 Step 이 끝나면 멈춥니다/)).toBeTruthy();
    expect(screen.queryByText(/그대로 유지하고 있습니다/)).toBeNull();
  });

  it("실행이 끝난 뒤에는 일시정지라고 말하지 않는다", () => {
    render(<MirrorView frame="AAA" phase="finished" />);
    expect(screen.getByText("실행 종료")).toBeTruthy();
    expect(screen.queryByText("일시정지")).toBeNull();
    expect(screen.queryByText(/그대로 유지하고 있습니다/)).toBeNull();
  });

  it("실제 일시정지에서는 유지를 말한다 — FR-033 이 그것을 요구한다", () => {
    render(<MirrorView frame="AAA" phase="paused" />);
    expect(screen.getByText("일시정지")).toBeTruthy();
    expect(screen.getByText(/브라우저 세션과 화면 상태를 그대로 유지하고 있습니다/)).toBeTruthy();
  });

  it("프레임이 없는 전이 중에도 「곧 온다」고 말하지 않는다 (FR-163)", () => {
    render(<MirrorView frame={null} phase="pausing" />);
    expect(screen.getByText(/현재 Step 이 끝나기를 기다리고 있습니다/)).toBeTruthy();
  });
});

// ─── T118 — 새로고침 복원 (N-01 · FR-166·FR-167) ────────────────────────────

describe("T118 새로고침이 화면 상태를 잃지 않는다 (FR-166 · N-01)", () => {
  /**
   * 변환 함수 테스트(`ScreenUrl.test.ts`)는 이 결함을 잡지 못했다 — 변환은 처음부터
   * 옳았고, 화면이 아직 `loading` 인 첫 렌더에서 주소를 지운 것이 원인이었다.
   * 그래서 이 파일은 **그 국면의 질의 문자열**을 직접 고정한다.
   */
  it("아직 화면을 정하지 못한 상태(loading)는 주소에 아무것도 쓰지 않는다", () => {
    expect(locationToSearch({ name: "loading" })).toBe("");
  });

  it("주소가 결과 화면을 가리키면 최초 로드가 그것을 읽는다", () => {
    window.history.replaceState({}, "", "/?screen=result&test=TC-001");
    expect(initialLocation()).toEqual({
      name: "result",
      testId: "TC-001",
      sessionId: null,
      stepId: null,
    });
    window.history.replaceState({}, "", "/");
  });
});

// ─── T119 — 목록 행 배지 (N-02 · FR-168·FR-169) ──────────────────────────────

const listRow = (overrides: Record<string, unknown> = {}) => ({
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

const sessionOf = (state: SessionState) =>
  ({
    session_id: "abcdef123456",
    state,
    // 배너는 이 값을 쓴다 — 재점검 N-02 는 배너가 「실패」인데 행이 RUNNING 인 상태였다.
    state_label: state === "failed" ? "실패" : state === "review" ? "검토 중" : "실행 중",
    test_id: "TC-002",
    current_step_index: 5,
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
  }) as unknown as SessionView;

function renderList(state: SessionState) {
  vi.stubGlobal("fetch", listFetch([listRow()]));
  render(
    <TestList
      onCreate={noop}
      onOpenResult={noop}
      onRun={noop}
      activeSessions={[sessionOf(state)]}
      onResumeSession={noop}
      onDiscardSession={noop}
    />,
  );
  return screen.findByText("실패한 테스트");
}

describe("T119 목록 행은 세션의 상태를 본다 (FR-169 · N-02)", () => {
  it("실행이 끝난 세션이 열려 있어도 행은 저장된 결말을 말한다", async () => {
    await renderList("failed");
    expect(screen.queryByText("RUNNING")).toBeNull();
    // 배너는 「실패」로 갱신되고 행은 `FAIL` 을 말한다 — 둘이 같은 사실을 가리킨다.
    expect(screen.getAllByText("FAIL").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/실패/).length).toBeGreaterThanOrEqual(1);
  });

  it("돌고 있으면 RUNNING 이다 — FR-168 을 되돌리지 않는다", async () => {
    await renderList("replaying");
    expect(screen.getByText("RUNNING")).toBeTruthy();
  });

  it("끝난 세션에도 복귀 수단은 남는다 — 칩과 복귀는 다른 요구사항이다 (FR-168)", async () => {
    await renderList("review");
    expect(screen.getByRole("button", { name: "실행 화면 보기" })).toBeTruthy();
  });

  it("중지 후 목록에서도 결과에 도달할 수 있다 — 세션이 남았다고 감추지 않는다", async () => {
    await renderList("review");
    expect(screen.getByRole("button", { name: "결과 보기" })).toBeTruthy();
  });

  it("돌고 있는 동안에는 결과 버튼을 감춘다 — 낡은 결과를 지금 결과로 읽는다", async () => {
    await renderList("replaying");
    expect(screen.queryByRole("button", { name: "결과 보기" })).toBeNull();
  });

  it("일시정지는 실행 중이 아니다 — 기다리면 끝난다고 읽히면 안 된다", () => {
    expect(isRunning("paused")).toBe(false);
    expect(isRunning("ai_blocked")).toBe(false);
    expect(isRunning("starting")).toBe(true);
    expect(isRunning("review")).toBe(false);
  });
});

// ─── T121 — 실패 Step 건너뛰기 (N-04 · FR-137 · ui-contract §6-5) ───────────

describe("T121 실패한 Step 을 건너뛰는 별도 조작이 화면에 있다 (FR-137 · N-04)", () => {
  const failing = {
    outcomeOf: (_s: Step, index: number) => (index === 5 ? ("fail" as const) : ("pass" as const)),
  };

  it("실패가 있으면 「계속하기」와 **다른** 버튼이 나온다", () => {
    const onSkip = vi.fn();
    render(<RunnerPaused {...pausedProps({ ...failing, onResumeSkippingFailure: onSkip })} />);
    const resume = screen.getByRole("button", { name: /계속하기$/ });
    expect((resume as HTMLButtonElement).disabled).toBe(true);
    const skip = screen.getByRole("button", { name: "실패한 Step 건너뛰고 계속" });
    expect((skip as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(skip);
    // 실패한 Step 의 인덱스를 넘긴다 — 화면이 그것을 다시 계산하지 않게 한다.
    expect(onSkip).toHaveBeenCalledWith(5);
  });

  it("누르기 전에 결말이 「부분 성공」이 된다는 사실을 말한다", () => {
    render(<RunnerPaused {...pausedProps({ ...failing, onResumeSkippingFailure: noop })} />);
    expect(screen.getByText(/부분 성공/)).toBeTruthy();
    expect(screen.getByText(/Step 06 을 건너뛰고 다음 Step 부터 이어갑니다/)).toBeTruthy();
  });

  it("실패가 없으면 그 버튼을 두지 않는다 — 건너뛸 것이 없다", () => {
    render(<RunnerPaused {...pausedProps({ onResumeSkippingFailure: noop })} />);
    expect(screen.queryByRole("button", { name: "실패한 Step 건너뛰고 계속" })).toBeNull();
  });

  it("검토 상태(브라우저 없음)에는 두지 않는다 — 이어갈 실행이 없다", () => {
    render(
      <RunnerPaused {...pausedProps({ ...failing, review: true, onResumeSkippingFailure: noop })} />,
    );
    expect(screen.queryByRole("button", { name: "실패한 Step 건너뛰고 계속" })).toBeNull();
  });
});

// ─── T122 — 녹화 일시정지 부제의 Step 번호 (N-06 · FR-138) ───────────────────

describe("T122 멈춘 지점은 직전 Step 이다 (FR-138 · N-06)", () => {
  it("Step 5개를 녹화하고 멈추면 「Step 05 이후 정지」다", () => {
    // `currentStepIndex` 는 **다음에 실행할** 위치다. 5개를 마쳤으면 5 다.
    render(<RunnerPaused {...pausedProps({ steps: steps(5), currentStepIndex: 5 })} />);
    expect(screen.getByText("Step 05 이후 정지")).toBeTruthy();
    expect(screen.queryByText("Step 06 이후 정지")).toBeNull();
  });

  it("아무것도 실행하지 않았으면 없는 Step 을 말하지 않는다", () => {
    expect(pausedAfterLabel(0)).toBe("첫 Step 실행 전 정지");
  });

  it("변환은 stepLabel 을 지난다 — 두 규칙을 만들지 않는다 (FR-138)", () => {
    expect(pausedAfterLabel(5)).toBe("Step 05 이후 정지");
    expect(pausedAfterLabel(1)).toBe("Step 01 이후 정지");
  });
});
