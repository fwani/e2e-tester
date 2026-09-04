/**
 * 중지 후 검토 화면. DR-010·DR-012·DR-013·DR-014.
 *
 * 사용자가 겪은 것: 직접 녹화 중 중지를 누르면 화면이 목록으로 튕겨 나가고 기록한
 * Step 을 보지도 저장하지도 못했다. **화면이 남아 있는지**가 이 파일의 요점이다.
 * 서버 쪽(세션이 살아남아 저장이 성공하는지)은 `test_stop_then_save.py` 가 본다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Step } from "../src/types/generated/step";
import { RunnerPaused } from "../src/pages/RunnerPaused";

const steps = [
  {
    id: "step-01",
    type: "click",
    label: "로그인 버튼 클릭",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    target: { test_id: { value: "login", status: "verified" } },
  },
  {
    id: "step-02",
    type: "fill",
    label: "이메일 입력",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    value: "a@b.c",
    target: { test_id: { value: "email", status: "verified" } },
  },
] as unknown as Step[];

const base = {
  title: "TC-001",
  testId: "TC-001",
  currentStepIndex: 2,
  editWarnings: [],
  steps,
  outcomeOf: () => "pass" as const,
  durationOf: () => 120,
  busy: false,
  currentUrl: "https://x.test/",
  mirror: <div />,
  selectedStepId: null,
  onSelectStep: () => undefined,
  reordering: false,
  saveName: "",
  onSaveNameChange: () => undefined,
  onSave: () => undefined,
  onResume: () => undefined,
  onStop: () => undefined,
  onRecordActionsStart: () => undefined,
  onRecordActionsStop: () => undefined,
  onAddAssertion: () => undefined,
  onEditStep: () => undefined,
  onToggleReorder: () => undefined,
  onApplyReorder: () => undefined,
  onRunFrom: () => undefined,
  onDeleteStep: () => undefined,
  onNaturalLanguage: () => undefined,
};

afterEach(cleanup);

describe("중지 후 검토 (DR-010)", () => {
  it("기록된 Step 이 화면에 남아 있다", () => {
    render(<RunnerPaused {...base} review />);

    expect(screen.getByText("로그인 버튼 클릭")).toBeTruthy();
    expect(screen.getByText("이메일 입력")).toBeTruthy();
  });

  it("이름을 붙여 저장할 수 있다 (DR-013)", () => {
    const onSave = vi.fn();
    render(<RunnerPaused {...base} review saveName="내 테스트" onSave={onSave} />);

    fireEvent.click(screen.getByText("저장"));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("Step 이 없으면 저장할 수 없다 (001 FR-029)", () => {
    render(<RunnerPaused {...base} review steps={[]} saveName="이름" />);

    expect((screen.getByText("저장") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Step 이 없으면 저장할 수 없습니다.")).toBeTruthy();
  });

  it("이름이 비면 저장할 수 없다", () => {
    render(<RunnerPaused {...base} review saveName="" />);

    expect((screen.getByText("저장") as HTMLButtonElement).disabled).toBe(true);
  });

  it("브라우저가 없으므로 「계속하기」를 그리지 않는다 (001 FR-043a)", () => {
    render(<RunnerPaused {...base} review />);

    expect(screen.queryByText("계속하기")).toBeNull();
    // 일시정지 상태에서는 있어야 한다 — 감추는 조건이 review 임을 못 박는다.
    cleanup();
    render(<RunnerPaused {...base} review={false} />);
    expect(screen.getByText("계속하기")).toBeTruthy();
  });

  it("검토 상태에서는 브라우저가 필요한 도구를 감춘다", () => {
    render(<RunnerPaused {...base} review />);

    expect(screen.queryByText("직접 동작 추가")).toBeNull();
    expect(screen.queryByText("Assertion 추가")).toBeNull();
    expect(screen.queryByLabelText("자연어로 Step 추가")).toBeNull();
    // 브라우저 없이도 되는 것은 남는다 (DR-012).
    expect(screen.getByText("Step 삭제")).toBeTruthy();
    expect(screen.getByText("순서 변경")).toBeTruthy();
  });

  it("Step 을 골라 지울 수 있다 (DR-012)", () => {
    const onDeleteStep = vi.fn();
    render(
      <RunnerPaused {...base} review selectedStepId="step-01" onDeleteStep={onDeleteStep} />,
    );

    fireEvent.click(screen.getByText("Step 삭제"));
    expect(onDeleteStep).toHaveBeenCalledWith("step-01");
  });

  it("나가기 버튼의 문구가 검토 상태에서 달라진다", () => {
    render(<RunnerPaused {...base} review />);
    expect(screen.getByText("나가기")).toBeTruthy();

    cleanup();
    render(<RunnerPaused {...base} review={false} />);
    expect(screen.getByText("중지")).toBeTruthy();
  });
});
