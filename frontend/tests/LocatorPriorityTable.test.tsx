/**
 * 후보 우선순위 표 (T142·T151). FR-019·FR-019a.
 *
 * **파생 규칙이 백엔드와 같은지 본다.** 같은 판정 사례를
 * `backend/tests/unit/test_candidate_display.py` 가 고정하고 있으며, 여기 사례는 그것과
 * 짝을 이룬다 — 한쪽만 바뀌면 화면과 API 응답의 설명이 갈린다.
 */
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  LocatorPriorityTable,
  displayStates,
} from "../src/components/LocatorPriorityTable";
import type { TargetLocator } from "../src/types/generated/step";

const verified = (value: string) => ({ value, status: "verified" as const });

function target(overrides: Partial<TargetLocator> = {}): TargetLocator {
  return {
    tag: null,
    test_id: null,
    role: null,
    accessible_name: null,
    role_status: null,
    label: null,
    text: null,
    stable_attr: null,
    css: null,
    ...overrides,
  } as TargetLocator;
}

describe("displayStates — 파생 규칙", () => {
  it("우선순위가 가장 높은 verified 후보가 '사용 중' 이다", () => {
    const states = displayStates(
      target({ test_id: verified("save"), label: verified("저장"), css: verified(".s") }),
    );
    expect(states.test_id).toBe("사용 중");
    expect(states.label).toBe("대체 1");
    expect(states.css).toBe("최후");
  });

  it("CSS 만 있으면 그것이 '사용 중' 이다", () => {
    expect(displayStates(target({ css: verified(".only") })).css).toBe("사용 중");
  });

  it("'모호' 와 '수집되지 않음' 을 구분한다", () => {
    const states = displayStates(
      target({
        text: { value: "삭제", status: "ambiguous" },
        css: verified("button.delete"),
      }),
    );
    expect(states.text).toBe("모호(사용 불가)");
    expect(states.label).toBe("수집되지 않음");
    // 모호한 후보는 사용 가능으로 세지 않는다 — CSS 가 '사용 중' 이 된다.
    expect(states.css).toBe("사용 중");
  });

  it("'검증 실패' 를 따로 표기한다", () => {
    const states = displayStates(
      target({ test_id: { value: "stale", status: "unverified" }, css: verified(".x") }),
    );
    expect(states.test_id).toBe("검증 실패");
    expect(states.css).toBe("사용 중");
  });

  it("role 후보는 role 과 이름이 짝일 때만 성립한다", () => {
    expect(displayStates(target({ role: "button", css: verified(".x") })).role).toBe(
      "수집되지 않음",
    );
    const paired = displayStates(
      target({
        role: "button",
        accessible_name: "저장",
        role_status: "verified",
        css: verified(".x"),
      }),
    );
    expect(paired.role).toBe("사용 중");
  });

  it("6단 전부에 표기가 있다", () => {
    expect(Object.keys(displayStates(target({ css: verified(".x") })))).toHaveLength(6);
  });
});

describe("LocatorPriorityTable", () => {
  it("수집된 값과 상태를 함께 보여 준다", () => {
    render(
      <LocatorPriorityTable
        target={target({ test_id: verified("save-dataset"), css: verified(".s") })}
      />,
    );
    expect(screen.getByText("save-dataset")).toBeTruthy();
    expect(screen.getByText("사용 중")).toBeTruthy();
    expect(screen.getByText("최후")).toBeTruthy();
  });

  it("수집되지 않은 후보는 값 칸에 '수집되지 않음' 을 보여 준다", () => {
    // 002 — 문구를 확정 디자인에 맞췄다. `StepInspector.dc.html` 의 5행("고정 속성")은
    // 값 칸에 "수집되지 않음" 을 흐린 색으로 쓰고 상태 배지를 두지 않는다. 배지를 또
    // 두면 확정 디자인에 없는 요소를 더하는 것이라 DC-007 위반이다.
    render(<LocatorPriorityTable target={target({ css: verified(".x") })} />);
    // testId·role·label·text·stable_attr 5칸이 비어 있다.
    expect(screen.getAllByText("수집되지 않음")).toHaveLength(5);
  });

  it("사용 가능 후보 수를 표시한다 (SC-008 의 화면 대응)", () => {
    render(
      <LocatorPriorityTable
        target={target({ test_id: verified("a"), css: verified(".b") })}
      />,
    );
    expect(screen.getByText("사용 가능 후보 2")).toBeTruthy();
  });

  it("다시 집기 버튼은 핸들러가 있을 때만 그린다 (FR-020)", () => {
    const { rerender } = render(
      <LocatorPriorityTable target={target({ css: verified(".x") })} />,
    );
    expect(screen.queryByText("다시 집기")).toBeNull();

    const onRepick = vi.fn();
    rerender(
      <LocatorPriorityTable target={target({ css: verified(".x") })} onRepick={onRepick} />,
    );
    screen.getByText("다시 집기").click();
    expect(onRepick).toHaveBeenCalledOnce();
  });

  it("대기 중에는 브라우저에서 클릭하라고 안내한다", () => {
    render(
      <LocatorPriorityTable
        target={target({ css: verified(".x") })}
        onRepick={() => undefined}
        repicking
      />,
    );
    expect(screen.getByText(/브라우저 창에서 대상 요소를 클릭/)).toBeTruthy();
    // 대기 중에는 다시 누를 수 없다.
    const button = screen.getByRole("button");
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("drag 의 두 대상을 구분해 그릴 수 있다 (T166)", () => {
    const { container } = render(
      <>
        <LocatorPriorityTable
          title="끄는 대상"
          target={target({ test_id: verified("chip-events") })}
        />
        <LocatorPriorityTable title="놓는 위치" target={target({ label: verified("보관함") })} />
      </>,
    );
    expect(within(container).getByText("끄는 대상")).toBeTruthy();
    expect(within(container).getByText("놓는 위치")).toBeTruthy();
  });
});
