/**
 * 일시정지 전이와 종료 후 컨트롤 (005 T050·T051 · FR-142~FR-148).
 *
 * 리포트 U-04 의 실측 타임라인이 이 파일의 대상이다.
 *
 * | 시각 | 화면 | 실제 |
 * |---|---|---|
 * | +0.12s | 배지 `PAUSED`, "step 05 이후 정지", 편집 팔레트 전부 노출 | step 06 **실행 중** |
 * | +0.12~10s | **모든 버튼 비활성.** 아무 설명 없음 | 실행 중 |
 * | +10.0s | 노란 배너 "…아직 실행 중입니다" | 실행 중 |
 * | +19.3s | `PAUSED` 배지 + `FAIL · 5 / 7` 요약이 **동시에** | 실행 종료 |
 *
 * 그리고 U-08 — 실행이 끝난 뒤에도 「중지」만 활성으로 남아 화면에서 가장 눈에 띄는
 * 컨트롤이었고, 누르면 확인 없이 세션을 폐기하며 목록으로 튀었다.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";

import { RunnerPaused } from "../src/pages/RunnerPaused";
import { Runner } from "../src/pages/Runner";
import type { Step } from "../src/types/generated/step";

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
    title: "TC-002",
    authoring: "record" as const,
    steps: steps(7),
    currentStepIndex: 5,
    currentUrl: "http://127.0.0.1:4300/projects.html",
    mirror: <div />,
    mirroredTab: 0,
    busy: false,
    editWarnings: [],
    recorderWarnings: [],
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
    onMoveStep: noop,
    onRecordActionsStart: noop,
    onAddAssertion: noop,
    onAddNlStep: noop,
    ...overrides,
  } as unknown as ComponentProps<typeof RunnerPaused>;
}

describe("일시정지 전이 (FR-142~FR-145 · U-04)", () => {
  it("전이 중에는 배지가 「일시정지 중…」이다 — 아직 정지가 아니다", () => {
    render(<RunnerPaused {...pausedProps({ pausing: true })} />);
    expect(screen.getAllByText("일시정지 중…").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("PAUSED")).toBeNull();
  });

  it("기다리는 이유를 즉시 말한다 — 10초 뒤 배너를 기다리지 않는다 (FR-142)", () => {
    render(<RunnerPaused {...pausedProps({ pausing: true, pausingBudgetMs: 20000 })} />);
    expect(screen.getByText(/현재 Step 이 끝나면 멈춥니다/)).toBeTruthy();
    // FR-145 — 대기 중인 Step 과 예산을 함께 말한다.
    expect(screen.getByText(/Step 06 대기 중/)).toBeTruthy();
    expect(screen.getByText(/최대 20s/)).toBeTruthy();
  });

  it("전이 중에는 편집 팔레트를 열지 않는다 (FR-143)", () => {
    render(<RunnerPaused {...pausedProps({ pausing: true })} />);
    expect(screen.getByText(/정지되면 편집할 수 있습니다/)).toBeTruthy();
    // 리포트가 본 것 — 요청 0.12초 뒤 팔레트가 전부 노출됐다.
    expect(screen.queryByText("Step 수정")).toBeNull();
    expect(screen.queryByText("Step 삭제")).toBeNull();
    expect(screen.queryByText("직접 동작 추가")).toBeNull();
  });

  it("정지가 성립하면 편집 팔레트가 열린다", () => {
    render(<RunnerPaused {...pausedProps({ pausing: false })} />);
    expect(screen.getByText("Step 수정")).toBeTruthy();
    expect(screen.queryByText(/정지되면 편집할 수 있습니다/)).toBeNull();
  });

  it("전이 중에도 「중지」는 누를 수 있다 (FR-144)", () => {
    // `busy` 가 참인 상태 — pause 요청이 진행 중이다. 그때도 중지는 살아 있어야 한다.
    render(<RunnerPaused {...pausedProps({ pausing: true, busy: true })} />);
    const stop = screen.getByRole("button", { name: /중지/ });
    expect((stop as HTMLButtonElement).disabled).toBe(false);
  });

  it("전이 중에는 「계속하기」를 잠근다 — 아직 멈추지 않았다", () => {
    render(<RunnerPaused {...pausedProps({ pausing: true })} />);
    const resume = screen.getByRole("button", { name: /계속하기/ });
    expect((resume as HTMLButtonElement).disabled).toBe(true);
  });

  it("멈추기 전에 실행이 끝났으면 일시정지가 아니라 결말을 말한다 (FR-146)", () => {
    render(
      <RunnerPaused
        {...pausedProps({
          pausing: true,
          finishedWhilePausing: {
            // 제목은 화면이 사전에서 받는다 — 요약에 접두로 섞지 않는다 (FR-140).
            summary: "실패 · Step 06 에서 실패 · 5 / 7 통과",
            failureReason: "요소를 찾을 수 없습니다",
            onShowResult: noop,
          },
        })}
      />,
    );
    // 제목은 **한 번만** 나온다. 요약과 함께 두 번 쓰면 U-19 가 되살아난다 (FR-140).
    expect(screen.getByText("멈추기 전에 실행이 끝났습니다")).toBeTruthy();
    // `PAUSED` 배지와 결말이 동시에 뜨지 않는다.
    expect(screen.queryByText("PAUSED")).toBeNull();
    expect(screen.queryByText("일시정지 중…")).toBeNull();
    // 헤더 배지와 미러 배지 둘 다 같은 말을 한다 — 한 화면에서 두 배지가 다른 말을
    // 하는 것이 U-20 이었다.
    expect(screen.getAllByText("실행 종료").length).toBeGreaterThanOrEqual(1);
  });

  /**
   * 재점검 U-04-c (T117) — 그 화면에 **진단 경로**가 있어야 한다.
   *
   * 배지와 부제는 고쳐졌지만 요약 한 줄만 있었다. 실패 사유도, 결과로 가는 길도 없어서
   * 사용자는 왜 실패했는지 보려고 세션을 닫아야 했고, 닫는 순간 이 화면이 사라졌다.
   */
  it("멈추기 전에 끝난 실행이 실패 사유와 결과 경로를 준다 (FR-146 · U-04-c)", () => {
    const onShowResult = vi.fn();
    render(
      <RunnerPaused
        {...pausedProps({
          finishedWhilePausing: {
            summary: "실패 · Step 06 에서 실패 · 5 / 7 통과",
            failureReason: "요소를 찾을 수 없습니다: #submit",
            onShowResult,
          },
        })}
      />,
    );
    expect(screen.getByText(/요소를 찾을 수 없습니다: #submit/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "결과 자세히 보기" }));
    expect(onShowResult).toHaveBeenCalledTimes(1);
  });

  it("실패 사유가 없으면 그 자리를 비워 둔다 — 없는 사유를 지어내지 않는다", () => {
    render(
      <RunnerPaused
        {...pausedProps({
          finishedWhilePausing: {
            summary: "통과 · 7 / 7 통과",
            failureReason: null,
            onShowResult: noop,
          },
        })}
      />,
    );
    expect(screen.getByText("통과 · 7 / 7 통과")).toBeTruthy();
    expect(screen.getByText("멈추기 전에 실행이 끝났습니다")).toBeTruthy();
  });
});

describe("실패 Step 재개 차단 (FR-136 · U-05)", () => {
  it("실패한 Step 이 있으면 「계속하기」가 잠기고 이유가 보인다", () => {
    render(
      <RunnerPaused
        {...pausedProps({
          outcomeOf: (_s: unknown, index: number) => (index === 5 ? "fail" : "pass"),
        })}
      />,
    );
    const resume = screen.getByRole("button", { name: /계속하기/ });
    expect((resume as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/Step 06 이 실패해 이어서 갈 수 없습니다/)).toBeTruthy();
    expect(screen.getByText(/Step 06부터 실행」을 쓰세요/)).toBeTruthy();
  });

  it("실패가 없으면 잠기지 않는다", () => {
    render(<RunnerPaused {...pausedProps({ outcomeOf: () => "pass" as const })} />);
    const resume = screen.getByRole("button", { name: /계속하기/ });
    expect((resume as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("종료 후 컨트롤 (FR-147 · U-08)", () => {
  function runnerProps(overrides: Record<string, unknown> = {}) {
    return {
      title: "TC-003",
      authoring: "record" as const,
      steps: steps(5),
      progressLabel: "Step 05 / 05",
      currentUrl: "http://127.0.0.1:4300/projects.html",
      mirror: <div />,
      mirroredTab: 0,
      busy: false,
      canPause: true,
      editWarnings: [],
      recorderWarnings: [],
      outcomeOf: () => "pass" as const,
      durationOf: () => 90,
      onPause: noop,
      onStop: noop,
      onSelectStep: noop,
      selectedStepId: null,
      statusLabel: "실행 중",
      ...overrides,
    } as unknown as ComponentProps<typeof Runner>;
  }

  it("실행 중에는 「중지」다", () => {
    render(<Runner {...runnerProps()} />);
    expect(screen.getByRole("button", { name: /중지/ })).toBeTruthy();
  });

  it("끝난 실행에서는 「닫기」이고 강조가 없다", () => {
    render(<Runner {...runnerProps({ stopLabel: "닫기", stopEmphasis: false })} />);
    const close = screen.getByRole("button", { name: "닫기" });
    expect(close).toBeTruthy();
    // 같은 위치의 같은 라벨이 두 동작을 갖지 않는다.
    expect(screen.queryByRole("button", { name: "중지" })).toBeNull();
    expect((close as HTMLElement).style.boxShadow).toBe("none");
  });

  it("중지 요청 중에는 「중지 중…」으로 잠긴다 (FR-147)", () => {
    render(<Runner {...runnerProps({ stopLabel: "중지 중…", stopDisabled: true })} />);
    const stop = screen.getByRole("button", { name: "중지 중…" });
    expect((stop as HTMLButtonElement).disabled).toBe(true);
  });

  it("중지 요청 콜백은 한 번만 불린다", async () => {
    const onStop = vi.fn();
    render(<Runner {...runnerProps({ onStop, stopDisabled: true, stopLabel: "중지 중…" })} />);
    const stop = screen.getByRole("button", { name: "중지 중…" });
    stop.click();
    stop.click();
    expect(onStop).toHaveBeenCalledTimes(0);
  });
});
