/**
 * 026 FR-034 — **수정 중에 무엇이 바뀌었는지 보이는가.**
 *
 * `/speckit-converge` 가 찾은 갭이다. 띠가 「고치는 중」과 새로 만든 개수만 말하면,
 * 사용자는 확정할지 버릴지를 **목록을 눈으로 훑어** 판단해야 한다 — US2 의 판단 근거가
 * 화면에 없는 상태다.
 *
 * ## 이 파일이 재는 것
 *
 * 1. 세션에 들어간 시점의 모습을 **화면이 붙잡는다** — 서버가 차이를 주지 않는다
 * 2. 바뀐 **항목 이름**이 보인다 (값이 아니다 — 값은 아래 Step 행에 이미 있다)
 * 3. 아무것도 안 바뀌었으면 그 사실도 말한다
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { clickStep, sessionView } from "./helpers/workbench";

afterEach(cleanup);

const STEPS = [
  clickStep({ id: "st-1", label: "첫 동작" }),
  clickStep({ id: "st-2", label: "둘째 동작" }),
  clickStep({ id: "st-3", label: "셋째 동작" }),
];

function viewWith(steps: typeof STEPS) {
  return sessionView({
    state: "paused",
    steps,
    current_step_index: 1,
    step_edit: {
      target_step_id: "st-2",
      target_index: 1,
      created_step_ids: [],
      can_commit: true,
    },
  });
}

function changesText(): string {
  return document.querySelector('[data-cell="step-edit-changes"]')?.textContent ?? "";
}

describe("바뀐 항목이 보인다 (FR-034)", () => {
  it("아무것도 안 바뀌었으면 **그 사실을 말한다**", () => {
    const { rerender } = render(
      <SessionWorkbench {...sessionProps({ view: viewWith(STEPS) })} />,
    );
    rerender(<SessionWorkbench {...sessionProps({ view: viewWith(STEPS) })} />);

    expect(changesText()).toContain("아직 바뀐 것이 없습니다");
  });

  it("표시 이름만 바뀌면 **그 항목만** 말한다", () => {
    const { rerender } = render(
      <SessionWorkbench {...sessionProps({ view: viewWith(STEPS) })} />,
    );

    const after = [STEPS[0], clickStep({ id: "st-2", label: "고친 이름" }), STEPS[2]];
    rerender(<SessionWorkbench {...sessionProps({ view: viewWith(after as typeof STEPS) })} />);

    expect(changesText()).toContain("표시 이름");
    expect(changesText()).not.toContain("입력값");
  });

  it("바뀐 것이 여럿이면 **전부** 나열한다", () => {
    const { rerender } = render(
      <SessionWorkbench {...sessionProps({ view: viewWith(STEPS) })} />,
    );

    const after = [
      STEPS[0],
      clickStep({ id: "st-2", label: "고친 이름", timeout_ms: 9000 }),
      STEPS[2],
    ];
    rerender(<SessionWorkbench {...sessionProps({ view: viewWith(after as typeof STEPS) })} />);

    const text = changesText();
    expect(text).toContain("표시 이름");
    expect(text).toContain("제한 시간");
  });

  it("대상이 지워지면 **그 사실을 말한다** — 버리기로 되돌아온다", () => {
    const { rerender } = render(
      <SessionWorkbench {...sessionProps({ view: viewWith(STEPS) })} />,
    );

    const after = [STEPS[0], STEPS[2]];
    rerender(<SessionWorkbench {...sessionProps({ view: viewWith(after as typeof STEPS) })} />);

    expect(changesText()).toContain("지워졌습니다");
  });

  it("**비교 대상은 세션에 들어간 시점의 모습이다** — 직전 렌더가 아니다", () => {
    const { rerender } = render(
      <SessionWorkbench {...sessionProps({ view: viewWith(STEPS) })} />,
    );

    // 한 번 고치고
    const once = [STEPS[0], clickStep({ id: "st-2", label: "한 번" }), STEPS[2]];
    rerender(<SessionWorkbench {...sessionProps({ view: viewWith(once as typeof STEPS) })} />);
    // 또 고친다 — 직전과 비교하면 여전히 「표시 이름」 하나지만, 시작 시점과 비교해도
    // 그렇다. 중요한 것은 **되돌아가서 원래 이름이 되면 「바뀐 것 없음」이 되는 것**이다.
    const back = [STEPS[0], clickStep({ id: "st-2", label: "둘째 동작" }), STEPS[2]];
    rerender(<SessionWorkbench {...sessionProps({ view: viewWith(back as typeof STEPS) })} />);

    expect(changesText()).toContain("아직 바뀐 것이 없습니다");
  });

  it("수정 세션이 아니면 띠가 없다", () => {
    render(
      <SessionWorkbench
        {...sessionProps({ view: sessionView({ state: "paused", steps: STEPS }) })}
      />,
    );
    expect(document.querySelector('[data-cell="step-edit-changes"]')).toBeNull();
    expect(screen.queryByLabelText("Step 수정")).toBeNull();
  });
});
