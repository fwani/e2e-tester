/**
 * 016 T040 — 재녹화 띠와 교체 대상 표시 (US2 · FR-024·FR-025·FR-028).
 *
 * ## 이 파일이 재는 것
 *
 * **확정 가능 여부를 화면이 다시 세지 않는가**가 핵심이다. 「만든 Step 이 1개 이상인가」를
 * 화면이 판단하면 서버와 갈리고, 갈리면 활성으로 그린 버튼이 눌린 뒤 거절된다 —
 * 005 U-01 이 그 형태였다. 그래서 `can_commit` 을 서버가 주고 표가 조건으로 받는다.
 *
 * 그리고 **교체 대상 표시가 Step 에 없는가** (불변식 7). 화면이 세션이 준 id 목록과
 * 대조해 계산한다 — Step 에 필드를 두면 작성 주체 외의 의미가 저장 형식에 생기고,
 * 확정되지 않은 상태가 디스크에 내려갈 문이 열린다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { RerecordView } from "../src/api/client";
import { RerecordBar, rangeLabelOf } from "../src/components/workbench/RerecordBar";
import { StepList } from "../src/components/workbench/StepList";
import type { WorkbenchStep } from "../src/components/workbench/model";
import { capabilitiesFor } from "../src/lib/capabilities";

afterEach(cleanup);

function view(created: string[]): RerecordView {
  return {
    range_step_ids: ["step-05", "step-06"],
    created_step_ids: created,
    // **서버가 판정한 값이다.** 화면이 `created.length > 0` 을 다시 세지 않는다.
    can_commit: created.length > 0,
  };
}

function capsFor(rr: RerecordView) {
  return capabilitiesFor("paused", {
    liveBrowser: true,
    hasRerecord: true,
    canCommitRerecord: rr.can_commit,
  });
}

describe("재녹화 띠 (ui-contract §3-2)", () => {
  it("무엇을 교체 중인지와 몇 개를 만들었는지 말한다", () => {
    const rr = view(["step-09", "step-10", "step-11"]);
    render(
      <RerecordBar
        rerecord={rr}
        capabilities={capsFor(rr)}
        rangeLabel="Step 5~6 (2개)"
        onCommit={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.getByText(/Step 5~6 \(2개\)/)).toBeTruthy();
    expect(screen.getByText(/새로 만든 것 3개/)).toBeTruthy();
  });

  it("아직 만든 것이 없으면 그 사실을 말한다", () => {
    const rr = view([]);
    render(
      <RerecordBar
        rerecord={rr}
        capabilities={capsFor(rr)}
        rangeLabel="Step 5~6 (2개)"
        onCommit={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );
    expect(screen.getByText(/아직 만든 Step 이 없습니다/)).toBeTruthy();
  });

  it("만든 것이 있으면 확정이 눌린다", async () => {
    const rr = view(["step-09"]);
    const onCommit = vi.fn();
    render(
      <RerecordBar
        rerecord={rr}
        capabilities={capsFor(rr)}
        rangeLabel="Step 5~6 (2개)"
        onCommit={onCommit}
        onDiscard={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /확정/ }));
    expect(onCommit).toHaveBeenCalled();
  });

  it("**만든 것이 없으면 확정을 누를 수 없고, 띠가 그 이유를 말한다** (FR-028 · 불변식 10)", () => {
    /*
      옛 구간을 빈 것으로 교체하는 것은 「구간 삭제」이지 재녹화가 아니다. 재녹화
      버튼으로 삭제가 일어나면 사용자는 무엇이 지워질지 예측할 수 없다.

      ## 왜 「잠긴 버튼」이 아니라 「없는 버튼 + 문장」인가

      `C16`(만든 것이 없다)의 가시성이 `hide` 이기 때문이다. 그 판정은 재녹화가 **아닌**
      화면을 위한 것이다 — 확정 버튼이 모든 일시정지 화면에 잠긴 채 떠 있으면
      검토 국면에서 조작 자리 24개 중 14개가 비활성이던 상태가 돌아온다.

      그래서 사유를 말하는 것은 **띠 자신**이다. 띠는 교체가 진행 중일 때만 존재하므로
      (`rerecord !== null`), 그 자리에서 「아직 만든 Step 이 없습니다」를 읽으면 왜
      확정할 수 없는지 알 수 있다. 감춰진 조작이 아니다 — 조작이 아직 성립하지 않은
      것이고, 그 사실이 화면에 있다.
    */
    const rr = view([]);
    render(
      <RerecordBar
        rerecord={rr}
        capabilities={capsFor(rr)}
        rangeLabel="Step 5~6 (2개)"
        onCommit={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: /확정/ })).toBeNull();
    expect(screen.getByText(/아직 만든 Step 이 없습니다/)).toBeTruthy();
  });

  it("**버리기는 만든 것이 없어도 활성이다** — 그만두는 것은 정상이다", async () => {
    const rr = view([]);
    const onDiscard = vi.fn();
    render(
      <RerecordBar
        rerecord={rr}
        capabilities={capsFor(rr)}
        rangeLabel="Step 5~6 (2개)"
        onCommit={vi.fn()}
        onDiscard={onDiscard}
      />,
    );

    const discard = screen.getByRole("button", { name: /버리기/ }) as HTMLButtonElement;
    expect(discard.disabled).toBe(false);
    await userEvent.click(discard);
    expect(onDiscard).toHaveBeenCalled();
  });

  it("**세션을 끝내는 조작은 여기 없다** (FR-031a)", () => {
    /*
      끝내는 것은 기존 「중지」다. 둘이 나란히 있으면 사용자는 누를 때마다 차이를
      확인해야 한다.
    */
    const rr = view(["step-09"]);
    render(
      <RerecordBar
        rerecord={rr}
        capabilities={capsFor(rr)}
        rangeLabel="Step 5~6 (2개)"
        onCommit={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: /중지|닫기|나가기/ })).toBeNull();
  });
});

describe("구간 이름 — 지금 목록에서 센다", () => {
  const all = ["step-01", "step-02", "step-03", "step-04", "step-05"];

  it("연속 구간을 1-기반 범위로 적는다", () => {
    expect(rangeLabelOf(["step-03", "step-04"], all)).toBe("Step 3~4 (2개)");
  });

  it("한 개면 범위가 아니라 하나로 적는다", () => {
    expect(rangeLabelOf(["step-02"], all)).toBe("Step 2 (1개)");
  });

  it("**앞에 Step 이 들어오면 번호가 따라 밀린다**", () => {
    /*
      구간은 id 로 잡혀 있고(data-model §1-1) 번호는 앞 구간에 Step 이 들어올 때마다
      밀린다. 서버가 준 번호를 들고 있으면 곧 거짓이 된다.
    */
    const grown = ["step-01", "step-09", "step-02", "step-03", "step-04", "step-05"];
    expect(rangeLabelOf(["step-03", "step-04"], grown)).toBe("Step 4~5 (2개)");
  });

  it("목록에 없으면 그 사실을 말한다 — 조용히 빈 문자열을 내지 않는다", () => {
    expect(rangeLabelOf(["step-99"], all)).toBe("교체 대상을 찾을 수 없습니다");
  });
});

describe("교체 대상 표시 (FR-024 · 불변식 7)", () => {
  function steps(): WorkbenchStep[] {
    return ["step-01", "step-02", "step-03"].map((id, i) => ({
      id,
      index: i,
      step: {
        type: "navigate",
        id,
        label: `동작 ${i + 1}`,
        author: "human",
        tab: 0,
        timeout_ms: 10000,
        frame_url: null,
        url: "https://example.test/",
      },
      label: `동작 ${i + 1}`,
      outcome: "not_run",
      durationMs: null,
      isPausedHere: false,
    })) as WorkbenchStep[];
  }

  it("세션이 준 id 만 「교체 대상」으로 보인다", () => {
    render(
      <StepList
        steps={steps()}
        authoring="ai"
        focusedStepId={null}
        onSelect={vi.fn()}
        rerecordTargets={["step-02"]}
      />,
    );

    const marks = screen.getAllByText("교체 대상");
    expect(marks).toHaveLength(1);
    // 그 표식이 붙은 행이 step-02 다.
    const row = marks[0]?.closest("[data-step-row]");
    expect(row?.getAttribute("data-step-row")).toBe("step-02");
  });

  it("목록을 주지 않으면 아무 표식도 없다 — 재녹화가 아닌 화면", () => {
    render(
      <StepList steps={steps()} authoring="record" focusedStepId={null} onSelect={vi.fn()} />,
    );
    expect(screen.queryByText("교체 대상")).toBeNull();
  });

  it("**Step 자체에는 표식이 없다** (불변식 7)", () => {
    /*
      `WorkbenchStep` 에 `isRerecordTarget` 같은 필드를 두면 작성 주체 외의 의미가
      생기고, 확정되지 않은 상태가 저장 형식으로 내려갈 문이 열린다. 화면이 계산한다.
    */
    const one = steps()[0];
    expect(Object.keys(one ?? {})).not.toContain("isRerecordTarget");
  });
});
