/**
 * Step 행 렌더. **실제 렌더 경로를 잰다.**
 *
 * 이 파일은 `StepList.test.tsx` 의 단언을 옮겨 온 것이다. converge 1회차가 잡은 것:
 * 전사 이후 어느 페이지도 `components/StepList.tsx` 를 임포트하지 않는데, 그것을 재는
 * 테스트 15건은 그대로 통과하고 있었다. **테스트 수가 줄지 않아 RG-001 은 초록으로
 * 보이지만 가드는 아무것도 지키지 않았다.**
 *
 * 옮기면서 전사 때 빠뜨린 동작 셋이 드러나 함께 되돌렸다 — 탭 배지(FR-030a),
 * 입력값 표시(FR-083), 그리고 **`verified` 후보만 요약에 쓰는 규칙**(원칙 IV).
 * 마지막 것은 단순 누락이 아니라 정확성 문제였다: 모호한 후보를 "이걸로 찾습니다" 라고
 * 보여 주고 있었다.
 *
 * **원칙 I 을 UI 계층에서 검증한다**: 사람 Step 과 AI Step 이 구조적으로 같게 렌더된다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DesignStepRow, locatorSummary } from "../src/components/design/DesignStepList";
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

function row(step: Step, props: Partial<Parameters<typeof DesignStepRow>[0]> = {}) {
  return render(<DesignStepRow index={0} step={step} outcome="pending" {...props} />);
}

afterEach(cleanup);

describe("DesignStepRow — 표시 (FR-027)", () => {
  it("번호와 표시 이름을 보여준다", () => {
    row(clickStep());
    expect(screen.getByText("01")).toBeDefined();
    expect(screen.getByText("저장 클릭")).toBeDefined();
  });

  it("동작 종류 배지를 보여준다", () => {
    row(clickStep());
    expect(screen.getByText("CLICK")).toBeDefined();
  });

  it("번호는 1부터, 두 자리로 채운다", () => {
    row(clickStep(), { index: 8 });
    expect(screen.getByText("09")).toBeDefined();
  });
});

describe("DesignStepRow — 원칙 I", () => {
  it("사람 Step 과 AI Step 을 같은 구조로 렌더한다", () => {
    const { container: human } = row(clickStep({ author: "human" } as Partial<Step>));
    const humanShape = human.querySelectorAll("div").length;
    cleanup();

    const { container: ai } = row(clickStep({ author: "ai" } as Partial<Step>));
    // 구조는 같고 색만 다르다. 개수가 달라지면 구조가 갈린 것이다.
    expect(ai.querySelectorAll("div").length).toBe(humanShape);
  });
});

describe("DesignStepRow — 식별 정보 요약 (FR-027·원칙 IV)", () => {
  it("적용된 식별 정보를 우선순위대로 요약한다", () => {
    row(
      clickStep({
        target: {
          test_id: { value: "save", status: "verified" },
          ...verifiedCss,
        },
      } as Partial<Step>),
    );
    // testId 가 최우선이다.
    expect(screen.getByText("testId=save")).toBeDefined();
  });

  it("모호한 후보는 요약에 쓰지 않는다 (FR-019b)", () => {
    row(
      clickStep({
        target: {
          test_id: { value: "save", status: "ambiguous" },
          ...verifiedCss,
        },
      } as Partial<Step>),
    );
    // 모호한 testId 대신 검증된 css 로 떨어진다 — 실제 실행이 그렇게 하기 때문이다.
    expect(screen.queryByText("testId=save")).toBeNull();
    expect(screen.getByText("css=#save")).toBeDefined();
  });

  it("확보된 후보가 없으면 그 사실을 알린다", () => {
    row(clickStep({ target: {} } as Partial<Step>));
    expect(screen.getByText("식별 후보 없음")).toBeDefined();
  });

  it("drag Step 은 끄는 대상과 놓는 위치를 함께 보여준다 (FR-023c)", () => {
    const step = {
      type: "drag",
      id: "step-01",
      label: "끌어 놓기",
      author: "human",
      tab: 0,
      timeout_ms: 5000,
      target: { css: { value: "#from", status: "verified" } },
      drop_target: { css: { value: "#to", status: "verified" } },
    } as unknown as Step;

    expect(locatorSummary(step)).toBe("css=#from → css=#to");
  });

  it("navigate 는 URL 을, close_tab 은 탭 번호를 요약한다", () => {
    expect(
      locatorSummary({
        type: "navigate",
        url: "https://x.test/a",
      } as unknown as Step),
    ).toBe("https://x.test/a");
    expect(
      locatorSummary({ type: "close_tab", tab: 2 } as unknown as Step),
    ).toBe("탭 2");
  });
});

describe("DesignStepRow — 동작 종류 (FR-023c)", () => {
  it("hover Step 을 표시한다", () => {
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

    row(hover);

    expect(screen.getByText("HOVER")).toBeDefined();
    expect(screen.getByText("도구 에 마우스 올리기")).toBeDefined();
    expect(screen.getByText("testId=tools-menu")).toBeDefined();
  });
});

describe("DesignStepRow — 탭 (FR-030a)", () => {
  it("최초 탭이 아닌 Step 에만 탭 배지를 보여준다", () => {
    row(clickStep({ tab: 2 } as Partial<Step>));
    expect(screen.getByText("탭 2")).toBeDefined();
  });

  it("최초 탭이면 배지를 그리지 않는다", () => {
    row(clickStep({ tab: 0 } as Partial<Step>));
    expect(screen.queryByText("탭 0")).toBeNull();
  });
});

describe("DesignStepRow — 입력값 (FR-083)", () => {
  it("입력값을 보여준다 — 민감 값은 변수 참조로만", () => {
    row(
      clickStep({
        type: "fill",
        value: "{{LOGIN_PASSWORD}}",
      } as Partial<Step>),
    );
    // 참조만 저장되므로 화면에 나와도 평문이 새지 않는다.
    expect(screen.getByText("{{LOGIN_PASSWORD}}")).toBeDefined();
  });

  it("값이 없는 동작에는 값 칸을 그리지 않는다", () => {
    const { container } = row(clickStep());
    expect(container.textContent).not.toContain("{{");
  });
});

describe("DesignStepRow — 상태 표시 (FR-034·FR-046)", () => {
  it("일시정지 위치를 구분해 표시한다", () => {
    const { container } = row(clickStep(), { paused: true });
    const marked = container.querySelector('[style*="border-left"]');
    expect(marked).not.toBeNull();
  });

  it("일시정지가 아니면 구분하지 않는다", () => {
    const { container } = row(clickStep(), { paused: false });
    expect(container.querySelector('[style*="border-left"]')).toBeNull();
  });

  it("결과와 소요 시간을 보여준다", () => {
    row(clickStep(), { outcome: "pass", durationMs: 302 });
    expect(screen.getByText("302 ms")).toBeDefined();
  });

  it("실행 전에는 소요 시간을 그리지 않는다", () => {
    const { container } = row(clickStep(), { outcome: "pending" });
    expect(container.textContent).not.toContain("ms");
  });
});
