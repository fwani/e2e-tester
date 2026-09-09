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
import { describe, expect, it, vi } from "vitest";

import { MirrorView } from "../src/components/MirrorView";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { TestList } from "../src/pages/TestList";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
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

/**
 * 일시정지·검토 국면의 `SessionWorkbench` 속성 (007 이행 2).
 *
 * 옛 `RunnerPaused` 는 「초안」·「검토」 같은 판정을 개별 prop 으로 받았다. 통합 뒤에는
 * **세션 뷰가 국면을 정한다** — `persisted` 는 `test_id` 의 유무이고 `review` 는
 * `state: "review"` 다. 재는 성질은 같고 입력이 사실로 바뀌었을 뿐이다.
 */
function pausedProps(overrides: Record<string, unknown> = {}) {
  const o = overrides as Record<string, never> & {
    persisted?: boolean;
    review?: boolean;
    savedAt?: string | null;
    hasUnsavedChanges?: boolean;
    title?: string;
    steps?: Step[];
    currentStepIndex?: number;
  };
  const {
    persisted = true,
    review = false,
    savedAt = null,
    hasUnsavedChanges = false,
    title,
    steps: stepList,
    currentStepIndex,
    ...rest
  } = o;
  return sessionProps({
    view: sessionView({
      state: review ? "review" : "paused",
      test_id: persisted ? (title ?? "TC-001") : null,
      /*
        011 — 이름과 저장 상태가 갈렸다. 정의 파일이 없으면 이름도 없다 (그때가 곧
        「초안」이다). 있으면 서버가 준 이름이 국면 띠의 입력칸에 들어간다.
      */
      test_name: persisted ? "로그인 흐름" : null,
      steps: stepList ?? steps(7),
      current_step_index: currentStepIndex ?? 5,
      saved_at: savedAt,
      has_unsaved_changes: hasUnsavedChanges,
    }),
    outcomeOf: () => "pending",
    durationOf: () => undefined,
    saveName: "",
    ...(rest as Record<string, unknown>),
  });
}

/** 조작 식별자로 버튼을 집는다 — 해소 방법 링크와 부딪히지 않는다. */
const act = (id: string) =>
  document.querySelector(`button[data-action="${id}"]`) as HTMLButtonElement | null;

// ─── T112 — 재실행 세션 제목의 「초안」 (U-03-a · FR-134) ────────────────────

/**
 * **2026-09-10 (011) — 재는 자리가 둘로 갈렸다.**
 *
 * T112 가 잰 것은 「TC-001 · 저장됨」이라는 **한 문장**이었다. 011 이 국면 띠의 이름
 * 자리를 입력칸으로 만들면서 그 문장을 넣을 수 없게 됐다 — 사용자가 이름을 고치는 칸에
 * 「· 저장됨」이 들어 있으면 그것까지 저장 이름이 된다 (UC-011-2).
 *
 * 그래서 이름은 입력칸이 갖고 저장 상태는 그 옆의 칩(`data-phase-save-state`)이 갖는다.
 * **재는 요구는 그대로다** — 재실행 세션이 「초안」으로 보이지 않아야 하고, 파일이 없는
 * 녹화는 「초안」이어야 한다. 자리만 둘이 됐으므로 단언도 둘이 된다.
 */
function saveStateText(): string {
  const el = document.querySelector("[data-phase-save-state]");
  expect(el, "국면 띠에 저장 상태 칩이 없다").not.toBeNull();
  return (el!.textContent ?? "").trim();
}

function nameFieldValue(): string {
  const el = document.querySelector('[data-action="test.rename"]') as HTMLInputElement | null;
  expect(el, "국면 띠에 이름 자리가 없다").not.toBeNull();
  return el!.value;
}

describe("T112 저장된 테스트의 재실행 세션은 초안이 아니다 (FR-134 · U-03-a)", () => {
  it("이 세션에서 저장하지 않았어도 정의 파일이 있으면 초안이 아니다", () => {
    // 재점검이 본 상태 그대로 — 재실행 세션은 `saved_at` 이 없다.
    render(<SessionWorkbench {...pausedProps({ persisted: true, savedAt: null })} />);
    expect(screen.queryByText(/초안/)).toBeNull();
    expect(saveStateText()).toBe("저장됨");
  });

  it("아직 파일이 없는 녹화는 초안이다 — 「초안」을 없애는 것이 목적이 아니다", () => {
    render(
      <SessionWorkbench {...pausedProps({ persisted: false, savedAt: null })} />,
    );
    expect(saveStateText()).toBe("초안");
    // 011 — 이름이 아직 없다. 입력칸은 비어 있고 무엇을 넣는지는 placeholder 가 말한다.
    expect(nameFieldValue()).toBe("");
  });

  it("저장된 테스트에 저장하지 않은 편집이 남으면 「저장됨」을 단정하지 않는다", () => {
    render(
      <SessionWorkbench
        {...pausedProps({ persisted: true, savedAt: null, hasUnsavedChanges: true })}
      />,
    );
    expect(saveStateText()).toBe("저장하지 않은 변경 있음");
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
  /** 중지로 끝난 세션. 결말 요약은 국면 띠가 하나만 갖는다 (FR-218d). */
  const stopped = {
    review: true,
    summary: "중지 · Step 06 에서 중지 · 5 / 7 통과 · 3.21 s",
    onShowResult: noop,
    onRerunAll: noop,
    onRerunFrom: noop,
    onShowList: noop,
  };

  it("ui-contract §8 의 다음 행동 네 개가 모두 있다 — 이전에는 셋이었다", () => {
    render(<SessionWorkbench {...pausedProps({ ...stopped })} />);
    // 네 개가 **모두 눌린다.** 이전에는 셋만 있었고, 없던 하나가 결과 경로였다.
    for (const id of ["result.show", "run.all", "run.from", "nav.back"]) {
      expect(act(id), id).not.toBeNull();
      expect(act(id)!.disabled, id).toBe(false);
    }
    // 시작 지점이 라벨에 드러난다 (FR-236 · 005 FR-149).
    expect(act("run.from")!.textContent).toBe("Step 06부터 실행");
  });

  /**
   * **007 이 이 단정을 바꿨다.** 005 ui-contract §8 금지 4 는 「결말 화면에 저장
   * 프롬프트를 두지 말라」였다. 금지의 이유는 저장이 결말 화면 **맨 아래 자리**를
   * 차지해 "지금 해야 할 일" 로 읽힌 것이었다.
   *
   * 통합 뒤에는 결말 화면이 따로 없다. 저장은 국면 보조 영역의 도구로 살고, 저장할
   * 것이 없으면 FR-234 가 요구하는 대로 **이유를 붙여 비활성으로** 남는다. 사용자가
   * 그것을 해야 할 일로 읽지 않는다는 성질은 유지되고, "왜 못 누르지" 에 답이 생겼다.
   */
  it("저장된 테스트의 결말 화면에서 저장은 비활성이고 이유가 붙는다 (§8 금지 4 의 대체)", () => {
    render(<SessionWorkbench {...pausedProps({ ...stopped, savedAt: null })} />);
    const save = act("save")!;
    expect(save.disabled).toBe(true);
    expect(document.querySelector("[data-disabled-reason='save']")?.textContent).toContain(
      "테스트 이름",
    );
  });

  it("이름 없는 녹화를 중지한 결말 화면에는 저장이 남는다 — 감추면 기록이 사라진다", () => {
    render(
      <SessionWorkbench {...pausedProps({ ...stopped, persisted: false, savedAt: null })} />,
    );
    expect(screen.getByLabelText("테스트 이름")).toBeTruthy();
  });

  it("결말 화면이 아니면 저장 자리를 걷지 않는다 (FR-156 은 비활성을 요구한다)", () => {
    render(
      <SessionWorkbench
        {...pausedProps({ persisted: true, savedAt: "2026-09-07T05:00:00Z", saveName: "TC-001" })}
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
    render(<SessionWorkbench {...pausedProps({ ...failing, onResumeSkippingFailure: onSkip })} />);
    expect(act("run.resume")!.disabled).toBe(true);
    const skip = act("run.resumeSkipFailure")!;
    expect(skip.textContent).toBe("실패한 Step 건너뛰고 계속");
    expect(skip.disabled).toBe(false);
    fireEvent.click(skip);
    // **인자를 넘기지 않는다** (T129). 건너뛸 Step 은 서버가 스스로 찾으므로
    // (`sessions.py:resume` 의 `first_failed_index()`) 화면이 인덱스를 실어 보내면
    // 그것이 반영되는 것처럼 읽히고 실제로는 무시된다.
    expect(onSkip).toHaveBeenCalledTimes(1);
    expect(onSkip.mock.calls[0]?.length ?? 0).toBe(0);
  });

  it("누르기 전에 결말이 「부분 성공」이 된다는 사실을 말한다", () => {
    render(<SessionWorkbench {...pausedProps({ ...failing, onResumeSkippingFailure: noop })} />);
    expect(screen.getByText(/부분 성공/)).toBeTruthy();
    expect(screen.getByText(/Step 06 을 건너뛰고 다음 Step 부터 이어갑니다/)).toBeTruthy();
  });

  /*
    2026-09-09 — **건너뛸 것이 없으면 자리도 없다** (사용자 결정).

    이전 단언의 근거는 「「없다」와 「지금은 안 된다」는 사용자에게 다른 뜻이고, 감추면 그
    구별이 사라진다」였다. 그 구별은 실재하지만, 이 조작에서는 값이 없다 — **건너뛸 실패가
    없는 것은 정상 상태**이고 사용자가 해소할 일이 아니다. 실측에서 이 버튼은 실패 없는
    모든 일시정지 화면에 「건너뛸 실패가 없습니다」를 달고 남아 있었다.

    **짝인 「계속하기」는 남는다** (`REASON_VISIBILITY` 의 O7 = `keep`). 그래서 실패가
    있을 때는 두 버튼이 나란히 서고 (위 검사), 없을 때는 「계속하기」 하나만 남는다 —
    자리 수가 상태를 말한다.
  */
  it("실패가 없으면 자리에 없다 — 건너뛸 것이 없다", () => {
    render(<SessionWorkbench {...pausedProps({ onResumeSkippingFailure: noop })} />);
    expect(act("run.resumeSkipFailure")).toBeNull();
    expect(document.querySelector("[data-disabled-reason='run.resumeSkipFailure']")).toBeNull();
    // 짝은 남는다 — 실패가 없으므로 활성이다.
    expect(act("run.resume")!.disabled).toBe(false);
  });

  it("검토 상태(브라우저 없음)에서는 자리에 없다 — 이어갈 실행이 없다", () => {
    render(
      <SessionWorkbench
        {...pausedProps({ ...failing, review: true, onResumeSkippingFailure: noop })}
      />,
    );
    // 브라우저가 없으면 이어가는 조작 둘 다 성립하지 않는다 (국면 `review`).
    expect(act("run.resumeSkipFailure")).toBeNull();
    expect(act("run.resume")).toBeNull();
    // 그 대신 이 국면의 조작이 있다 — 저장하고, 처음부터 다시 실행한다.
    expect(act("save")).not.toBeNull();
    expect(act("run.all")).not.toBeNull();
  });
});

// ─── T122 — 녹화 일시정지 부제의 Step 번호 (N-06 · FR-138) ───────────────────

describe("T122 멈춘 지점은 직전 Step 이다 (FR-138 · N-06)", () => {
  it("Step 5개를 녹화하고 멈추면 「Step 05 이후 정지」다", () => {
    // `currentStepIndex` 는 **다음에 실행할** 위치다. 5개를 마쳤으면 5 다.
    render(<SessionWorkbench {...pausedProps({ steps: steps(5), currentStepIndex: 5 })} />);
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
