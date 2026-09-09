/**
 * 실행 중 국면이 어디까지 왔는지 보여준다 (004 FR-107).
 *
 * **Step 간 간격이 이 요구의 이유다.** 간격 동안 화면이 아무것도 말하지 않으면, 속도를
 * 낮춘 사용자는 멈춘 것인지 쉬는 것인지 구별할 수 없다.
 *
 * 간격 중에는 `step_started` 가 발행되지 않는다. 그래서 마지막으로 온 `step_finished`
 * 상태가 그대로 남아 **방금 끝난 Step 과 그 결과**가 보인다. 그것이 성립의 근거인데,
 * 지금까지 암묵적이었다 — 누군가 간격 중 이벤트를 추가하면 조용히 깨진다. 여기서 고정한다.
 *
 * **007 이행 1** — 그리는 것이 `Runner` 에서 `SessionWorkbench` 로 바뀌었다. 진행 표시가
 * 넘겨받은 문자열이 아니라 세션 뷰에서 계산된 값이라는 것만 다르고, **재는 행동은 같다**.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import type { Step } from "../src/types/generated/step";

const steps = [
  {
    id: "s1", type: "click", label: "로그인", author: "human", tab: 0,
    timeout_ms: 10000, frame_url: null,
    target: { test_id: { value: "login", status: "verified" } },
  },
  {
    id: "s2", type: "click", label: "데이터 메뉴", author: "human", tab: 0,
    timeout_ms: 10000, frame_url: null,
    target: { test_id: { value: "data", status: "verified" } },
  },
  {
    id: "s3", type: "click", label: "업로드", author: "human", tab: 0,
    timeout_ms: 10000, frame_url: null,
    target: { test_id: { value: "upload", status: "verified" } },
  },
] as unknown as Step[];

/** Step 02 를 막 끝낸 상태 — 곧 03 이 시작되기 전, 즉 **간격 중**이다. */
function inTheGap(overrides: Record<string, unknown> = {}) {
  return sessionProps({
    view: sessionView({ state: "replaying", steps, current_step_index: 1 }),
    // 간격 중에는 `step_started` 가 없으므로 03 은 `running` 이 아니라 `pending` 이다 —
    // 그것이 "아직 시작하지 않았다" 를 화면에 말하는 방식이다.
    outcomeOf: (_s: Step, index: number) => (index <= 1 ? "pass" : "pending"),
    durationOf: (s: Step) => (s.id === "s2" ? 342 : undefined),
    ...overrides,
  });
}

afterEach(cleanup);

describe("간격 중 진행 표시 (FR-107)", () => {
  it("어디까지 왔는지 보여준다", () => {
    render(<SessionWorkbench {...inTheGap()} />);
    expect(screen.getByText("Step 02 / 03")).toBeDefined();
  });

  it("방금 끝난 Step 과 그 결과가 보인다", () => {
    render(<SessionWorkbench {...inTheGap()} />);
    // 사용자가 간격 동안 읽는 것: 무엇이 끝났고 얼마나 걸렸는가.
    expect(screen.getByText("데이터 메뉴")).toBeDefined();
    expect(screen.getByText("342 ms")).toBeDefined();
  });

  it("아직 시작하지 않은 Step 을 끝난 것으로 보이게 하지 않는다", () => {
    render(<SessionWorkbench {...inTheGap()} />);
    // 03 이 이미 통과한 것처럼 보이면, 간격 중 화면은 거짓을 말하는 것이다.
    expect(screen.getByText("업로드")).toBeDefined();
    // 소요 시간이 붙은 Step 은 실제로 끝난 것 하나뿐이다.
    expect(screen.queryAllByText(/\d+ ms/)).toHaveLength(1);
  });

  it("실행 중에도 속도를 바꿀 수 있다 (FR-103)", () => {
    const onPacingChange = vi.fn();
    render(<SessionWorkbench {...inTheGap({ onPacingChange })} />);
    fireEvent.click(screen.getByTestId("pacing-fast"));
    expect(onPacingChange).toHaveBeenCalledWith("fast");
  });

  /*
    2026-09-09 — **끝난 실행에서도 바꿀 수 있다** (사용자 결정).

    이전 단언은 「바꿀 수 없되 무엇을 골랐는지는 남는다」였다. 서버가 종료 상태의 속도
    변경을 거절했으므로(`sessions.set_pacing` 의 `TERMINAL_STATES`) 화면이 그보다 관대해서
    는 안 된다는 규율(005 U-01)에 따른 단언이었고, 그 규율 자체는 그대로다.

    바뀐 것은 **서버의 거절**이다. 사용자가 그것을 지목했다: 「속도 선택은 실행중이든
    아니든 바꿀수있어야함」. 거절에 실질적 근거가 없었다 — 이 연산은 세션의 값을 바꾸고
    취향 파일에 남기는 것이 전부이고, 끝난 세션에는 그 값을 읽을 러너가 없다. 반대로
    **가장 쓸모 있는 자리**였다: 실행 종료 화면에는 「처음부터 실행」이 있고, 여기서 고른
    값이 그 실행의 속도가 된다 (004 FR-109).

    「무엇을 골랐는지 남는다」는 그대로 지킨다 — `aria-pressed` 가 그것을 말한다.
  */
  it("실행이 끝나도 속도를 바꿀 수 있고, 무엇을 골랐는지도 남는다", () => {
    const onPacingChange = vi.fn();
    render(
      <SessionWorkbench
        {...inTheGap({
          onPacingChange,
          view: sessionView({
            state: "completed",
            steps,
            current_step_index: 2,
            pacing: "slow",
          }),
        })}
      />,
    );
    const slow = screen.getByTestId("pacing-slow") as HTMLButtonElement;
    expect(slow.disabled).toBe(false);
    expect(slow.getAttribute("aria-pressed")).toBe("true");

    // 다음 실행의 속도를 여기서 정한다 (FR-109).
    fireEvent.click(screen.getByTestId("pacing-fast"));
    expect(onPacingChange).toHaveBeenCalledWith("fast");

    /*
      **라벨이 「다음 실행 속도」다** (005 FR-174). 지금 돌고 있는 것에 적용되지 않는다는
      사실을 밝히지 않으면, 사용자는 끝난 실행의 기록이 바뀌는 줄 안다.
    */
    expect(document.querySelector('[data-action="run.pacing"]')?.textContent).toContain(
      "다음 실행 속도",
    );
  });
});
