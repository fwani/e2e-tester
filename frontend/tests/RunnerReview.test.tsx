/**
 * 중지 후 검토 국면. DR-010·DR-012·DR-013·DR-014.
 *
 * 사용자가 겪은 것: 직접 녹화 중 중지를 누르면 화면이 목록으로 튕겨 나가고 기록한
 * Step 을 보지도 저장하지도 못했다. **화면이 남아 있는지**가 이 파일의 요점이다.
 * 서버 쪽(세션이 살아남아 저장이 성공하는지)은 `test_stop_then_save.py` 가 본다.
 *
 * **007 이행 2** — `RunnerPaused` 대신 `SessionWorkbench` 를 그린다. 검토 국면은
 * `state: "review"` 가 만든다. 브라우저를 요구하는 도구를 **감추던 것을 비활성 + 이유로**
 * 바꿨다 (FR-234) — 막힌다는 사실은 같고, 왜 막혔는지가 화면에 남는다.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Step } from "../src/types/generated/step";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

const steps = [
  {
    id: "step-01",
    type: "click",
    label: "로그인 버튼 클릭",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    target: { test_id: { value: "login", status: "verified" } },
  },
  {
    id: "step-02",
    type: "fill",
    label: "이메일 입력",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    value: "a@b.c",
    target: { test_id: { value: "email", status: "verified" } },
  },
] as unknown as Step[];

function props(
  view: Record<string, unknown> = {},
  overrides: Record<string, unknown> = {},
) {
  return sessionProps({
    view: sessionView({
      state: "review",
      test_id: null,
      steps,
      current_step_index: 2,
      ...view,
    }),
    outcomeOf: () => "pass",
    durationOf: () => 120,
    ...overrides,
  });
}

const act = (id: string) =>
  document.querySelector(`button[data-action="${id}"]`) as HTMLButtonElement;

afterEach(cleanup);

describe("중지 후 검토 (DR-010)", () => {
  it("기록된 Step 이 화면에 남아 있다", () => {
    render(<SessionWorkbench {...props()} />);

    expect(screen.getByText("로그인 버튼 클릭")).toBeTruthy();
    expect(screen.getByText("이메일 입력")).toBeTruthy();
  });

  it("이름을 붙여 저장할 수 있다 (DR-013)", () => {
    const onSave = vi.fn();
    render(<SessionWorkbench {...props({}, { saveName: "내 테스트", onSave })} />);

    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("Step 이 없으면 그 사실을 안내한다", () => {
    render(<SessionWorkbench {...props({ steps: [] })} />);
    expect(screen.getByText("기록된 Step 이 없습니다.")).toBeTruthy();
  });

  it("Step 이 없으면 저장할 수 없다 (001 FR-029)", () => {
    render(<SessionWorkbench {...props({ steps: [] }, { saveName: "이름" })} />);

    expect((screen.getByRole("button", { name: "저장" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Step 이 없으면 저장할 수 없습니다.")).toBeTruthy();
  });

  it("이름이 비면 저장할 수 없다", () => {
    render(<SessionWorkbench {...props({}, { saveName: "" })} />);

    expect((screen.getByRole("button", { name: "저장" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("브라우저가 없으므로 「계속하기」를 잠그고 이유를 붙인다 (001 FR-043a)", () => {
    render(<SessionWorkbench {...props()} />);
    expect(act("run.resume").disabled).toBe(true);
    expect(
      document.querySelector("[data-disabled-reason='run.resume']")?.textContent,
    ).toContain("브라우저");

    // 일시정지 상태에서는 눌린다 — 잠그는 조건이 「브라우저 없음」임을 못 박는다.
    cleanup();
    render(<SessionWorkbench {...props({ state: "paused" })} />);
    expect(act("run.resume").disabled).toBe(false);
  });

  it("검토 상태에서는 브라우저가 필요한 도구를 잠그되 감추지 않는다", () => {
    render(<SessionWorkbench {...props({}, { focusedStepId: "step-01" })} />);

    expect(act("step.recordStart").disabled).toBe(true);
    expect(act("step.addAssertion").disabled).toBe(true);
    expect((screen.getByLabelText("자연어로 Step 추가") as HTMLInputElement).disabled).toBe(true);
    // 브라우저 없이도 되는 것은 눌린다 (DR-012).
    expect(act("step.delete").disabled).toBe(false);
    expect(act("step.reorder").disabled).toBe(false);
  });

  it("Step 을 골라 지울 수 있다 (DR-012)", () => {
    const onDeleteStep = vi.fn();
    render(<SessionWorkbench {...props({}, { focusedStepId: "step-01", onDeleteStep })} />);

    fireEvent.click(act("step.delete"));
    expect(onDeleteStep).toHaveBeenCalledWith("step-01");
  });

  it("브라우저 유실 뒤에도 이름을 붙여 저장할 수 있다 (DR-015)", () => {
    // 백엔드는 유실된 세션의 Step 을 보존하고 LOST 에서 SAVE 를 허용한다. `lost` 는
    // `review` 와 처지가 같으므로(브라우저 없음·Step 살아 있음) 같은 국면이 맡는다.
    const onSave = vi.fn();
    render(
      <SessionWorkbench
        {...props({ state: "lost" }, { saveName: "유실 후 저장", onSave })}
      />,
    );

    expect(screen.getByLabelText("테스트 이름")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("나가기 버튼의 문구가 검토 상태에서 달라진다", () => {
    render(<SessionWorkbench {...props()} />);
    expect(act("run.stop").textContent).toBe("나가기");

    cleanup();
    render(<SessionWorkbench {...props({ state: "paused" })} />);
    expect(act("run.stop").textContent).toBe("중지");
  });
});
