/**
 * StepList 컴포넌트 테스트 (T067·T151 일부).
 *
 * **원칙 I 을 UI 계층에서 검증한다**: 사람 Step 과 AI Step 이 구조적으로 같게 렌더된다.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { StepList } from "../src/components/StepList";
import type { Step } from "../src/types/generated/step";

const verifiedCss = { css: { value: "#save", status: "verified" as const } };

function clickStep(overrides: Partial<Step> = {}): Step {
  return {
    type: "click",
    id: "step-01",
    label: "저장 클릭",
    author: "human",
    tab: 0,
    timeout_ms: 5000,
    frame_url: null,
    target: verifiedCss,
    ...overrides,
  } as Step;
}

describe("StepList", () => {
  it("Step 이 없으면 안내를 보여준다", () => {
    render(<StepList steps={[]} />);
    expect(screen.getByText(/아직 기록된 Step 이 없습니다/)).toBeDefined();
  });

  it("번호와 표시 이름을 보여준다 (FR-027)", () => {
    render(<StepList steps={[clickStep()]} />);
    expect(screen.getByText("01")).toBeDefined();
    expect(screen.getByText("저장 클릭")).toBeDefined();
  });

  it("동작 종류 배지를 보여준다", () => {
    render(<StepList steps={[clickStep()]} />);
    expect(screen.getByText("CLICK")).toBeDefined();
  });

  it("사람 Step 과 AI Step 을 같은 구조로 렌더한다 (원칙 I)", () => {
    const human = clickStep({ id: "step-01", label: "동일 동작", author: "human" });
    const ai = clickStep({ id: "step-02", label: "동일 동작", author: "ai" });
    const { container } = render(<StepList steps={[human, ai]} />);
    const rows = container.querySelectorAll("li");
    expect(rows.length).toBe(2);
    // 두 행 모두 같은 종류 배지를 갖는다 — 구조가 같다는 증거
    expect(screen.getAllByText("CLICK").length).toBe(2);
    // AI 만 작성 주체 배지를 추가로 갖는다 (표시만 다르다)
    expect(screen.getAllByText("AI").length).toBe(1);
  });

  it("최초 탭이 아닌 Step 에만 탭 배지를 보여준다 (FR-030a)", () => {
    render(
      <StepList
        steps={[clickStep({ id: "step-01", tab: 0 }), clickStep({ id: "step-02", tab: 1 })]}
      />,
    );
    expect(screen.getByText("탭 1")).toBeDefined();
    expect(screen.queryByText("탭 0")).toBeNull();
  });

  it("적용된 식별 정보를 우선순위대로 요약한다 (FR-027)", () => {
    const withTestId = clickStep({
      target: {
        test_id: { value: "create-project", status: "verified" },
        ...verifiedCss,
      },
    } as Partial<Step>);
    render(<StepList steps={[withTestId]} />);
    expect(screen.getByText("testId=create-project")).toBeDefined();
  });

  it("모호한 후보는 요약에 쓰지 않는다 (FR-019b)", () => {
    const ambiguous = clickStep({
      target: {
        text: { value: "저장", status: "ambiguous" },
        css: { value: "#save", status: "verified" },
      },
    } as Partial<Step>);
    render(<StepList steps={[ambiguous]} />);
    expect(screen.getByText("css=#save")).toBeDefined();
    expect(screen.queryByText('text="저장"')).toBeNull();
  });

  it("확보된 후보가 없으면 그 사실을 알린다", () => {
    const none = clickStep({
      target: { css: { value: "#save", status: "ambiguous" } },
    } as Partial<Step>);
    render(<StepList steps={[none]} />);
    expect(screen.getByText("식별 후보 없음")).toBeDefined();
  });

  it("일시정지 위치에 구분선을 그린다 (FR-034)", () => {
    render(
      <StepList
        steps={[clickStep({ id: "step-01" }), clickStep({ id: "step-02" })]}
        currentIndex={1}
        showPauseMarker
      />,
    );
    expect(screen.getByText("PAUSE")).toBeDefined();
    expect(screen.getByText(/여기서 고친 뒤 이어서 실행합니다/)).toBeDefined();
  });

  it("일시정지가 아니면 구분선을 그리지 않는다", () => {
    render(<StepList steps={[clickStep()]} currentIndex={0} />);
    expect(screen.queryByText("PAUSE")).toBeNull();
  });

  it("삭제 처리기가 있을 때만 삭제 버튼을 보여준다 (FR-035a)", () => {
    const onDelete = vi.fn();
    const { rerender } = render(<StepList steps={[clickStep()]} onDelete={onDelete} />);
    expect(screen.getByLabelText("저장 클릭 삭제")).toBeDefined();

    rerender(<StepList steps={[clickStep()]} />);
    expect(screen.queryByLabelText("저장 클릭 삭제")).toBeNull();
  });

  it("입력값을 보여준다 — 민감 값은 변수 참조로만 (FR-083)", () => {
    const fill = {
      type: "fill",
      id: "step-01",
      label: "비밀번호 입력 (민감)",
      author: "human",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      target: verifiedCss,
      value: "{{SECRET_PASSWORD}}",
    } as unknown as Step;
    render(<StepList steps={[fill]} />);
    expect(screen.getByText("{{SECRET_PASSWORD}}")).toBeDefined();
  });

  it("Step 200개를 렌더한다 (research R8)", () => {
    const many: Step[] = Array.from({ length: 200 }, (_, i) =>
      clickStep({ id: `step-${String(i + 1).padStart(3, "0")}`, label: `동작 ${i + 1}` }),
    );
    const started = performance.now();
    const { container } = render(<StepList steps={many} />);
    const elapsed = performance.now() - started;
    expect(container.querySelectorAll("li").length).toBe(200);
    expect(elapsed).toBeLessThan(3000);
  });

  it("hover Step 을 표시한다 (FR-023c)", () => {
    const hover = {
      type: "hover",
      id: "step-01",
      label: "도구 에 마우스 올리기",
      author: "human",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      target: { test_id: { value: "tools-menu", status: "verified" as const } },
    } as unknown as Step;
    render(<StepList steps={[hover]} />);
    expect(screen.getByText("HOVER")).toBeDefined();
    expect(screen.getByText("도구 에 마우스 올리기")).toBeDefined();
    expect(screen.getByText("testId=tools-menu")).toBeDefined();
  });

  it("drag Step 은 끄는 대상과 놓는 위치를 함께 보여준다 (FR-023c)", () => {
    // 끄는 대상만 보여주면 어디로 놓는지 알 수 없다.
    const drag = {
      type: "drag",
      id: "step-01",
      label: "events 을 보관함 으로 끌어다 놓기",
      author: "human",
      tab: 0,
      timeout_ms: 5000,
      frame_url: null,
      target: { test_id: { value: "chip-events", status: "verified" as const } },
      drop_target: { label: { value: "보관함", status: "verified" as const } },
    } as unknown as Step;
    render(<StepList steps={[drag]} />);
    expect(screen.getByText("DRAG")).toBeDefined();
    expect(screen.getByText("testId=chip-events → label=보관함")).toBeDefined();
  });
});
