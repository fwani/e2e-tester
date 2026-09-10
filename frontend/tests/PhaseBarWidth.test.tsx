/**
 * 국면 띠는 한 줄에 담기고 창 밖으로 나가지 않는다 (사용자 보고 · 2026-09-09).
 *
 * ## 보고된 것
 *
 * 실행 중 화면에서 국면 띠가 창 폭의 두 배로 늘어났다. 같은 줄의 결말 요약은 폭 0 으로
 * 찌그러진 채 **글자 하나씩 세로로 쌓였고**, 오른쪽 조작들은 화면 밖으로 밀려났다.
 *
 * ## 왜 그랬나
 *
 * 실행 중에는 네 조작이 한꺼번에 잠긴다 — 일시정지·중지는 「요청을 보내는 중」이고,
 * 처음부터 실행·Step 01부터 실행은 「실행 중인 세션이 열려 있습니다」다. 잠긴 조작마다
 * 이유 문구가 버튼 옆에 붙는데, 조작 묶음이 `flex: 0 0 auto` 라 **제 내용 폭을 끝까지
 * 요구했다.** 줄어들 수 있는 것은 결말 요약뿐이었고, 그것이 0 까지 줄어든 뒤로는 띠가
 * 통째로 넘쳤다.
 *
 * ## 이 파일이 재는 것
 *
 * 넘침은 브라우저의 레이아웃 결과이고 jsdom 은 그것을 계산하지 않는다. 그래서
 * `WorkbenchHeight.test.tsx` 와 같은 방식으로 **결과가 아니라 구조**를 잰다 — 무엇이
 * 줄어들고 무엇이 줄지 않는지의 선언이 제자리에 있는가. 그 배분이 있으면 실제
 * 브라우저에서 띠가 한 줄에 담긴다.
 *
 * 함께 지키는 것이 하나 더 있다: **줄어들어도 잃지 않는다.** 이유 전문은
 * `aria-describedby` 로 버튼에 남아야 하고 (ui-contract §7), 해소 수단은 말줄임에
 * 잘려서는 안 된다 (§4-1 의 3번) — 빠져나갈 길이 잘리면 이유를 읽고도 할 수 있는 일이
 * 없다.

 * ## 2026-09-11 (015) — 판정 방법을 바꿨다. 검증 대상은 그대로다
 *
 * 배치가 인라인에서 유틸리티로 옮겨져 `element.style.*` 이 빈 문자열이 됐다.
 * `tests/helpers/style.ts` 가 두 표기를 같은 뜻으로 환산해 읽는다 — 이 검사가 묻는
 * 것(「버튼이 줄어들지 않는가」·「이유 문구가 말줄임하는가」)은 그대로다.
 *
 * `.row` 셀렉터로 조작 묶음을 찾던 자리는 `data-phase-actions` 표식으로 바꿨다.
 * 클래스가 해체되면 이름으로 찾을 수 없고, **자리를 찾는 일에 모양을 쓰는 것**이
 * 애초에 약한 결합이었다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ActionButton } from "../src/components/workbench/ActionButton";
import { PhaseBar } from "../src/components/workbench/PhaseBar";
import { renderSession } from "./helpers/session";

import { canShrink, hasMaxWidth, minWidthIsZero, truncates } from "./helpers/style";

afterEach(cleanup);

const bar = (el: Element | null) => el as HTMLElement;

/** 실행 중 + 요청 대기 — 보고된 화면의 조건이다. 여러 조작이 한꺼번에 잠긴다. */
function renderRunningWithPendingRequest() {
  return renderSession({ state: "replaying" }, { busy: true });
}

const STALE_SUMMARY =
  "실패 · 부분 실행 Step 08~17 · Step 08 에서 실패 · 0 / 10 통과 · (01~07 건너뜀) · 10.07 s";

describe("국면 띠가 한 줄에 담긴다", () => {
  it("결말 요약은 줄 바꿈하지 않는다 — 세로로 쌓이던 자리다", () => {
    render(
      <PhaseBar
        bar={{
          phaseLabel: "실행 중",
          phaseTone: "neutral",
          runSummary: "실패 · 부분 실행 Step 08~17 · Step 08에서 실패 · 0 / 10 통과 · 10.07s",
          progressLabel: "Step 08 / 17",
        }}
        testName="TC-020 · 저장 흐름"
        actions={null}
      />,
    );
    const summary = bar(document.querySelector("[data-run-summary]"));
    expect(summary).not.toBeNull();
    // 폭 0 까지 줄어드는 칸이 줄 바꿈까지 하면 글자가 한 줄에 하나씩 쌓인다.
    expect(truncates(summary), "결말 요약이 말줄임하지 않는다 — 글자가 한 줄에 하나씩 쌓인다").toBe(true);
  });

  it("조작 묶음은 줄어들 수 있다 — `0 0 auto` 가 띠를 밀어냈다", () => {
    renderRunningWithPendingRequest();
    const phase = bar(document.querySelector("[data-workbench-phase-bar]"));
    // 015 — `.row` 가 유틸리티로 해체돼 셀렉터로 찾을 수 없다. 자리 표식을 붙였다.
    const group = bar(phase.querySelector(":scope > [data-phase-actions]"));
    expect(group).not.toBeNull();
    expect(canShrink(group), "조작 묶음이 줄어들지 못한다 — 띠가 밀려난다").toBe(true);
    expect(minWidthIsZero(group), "최소 폭이 0 이 아니면 내용 폭 밑으로 줄지 못한다").toBe(true);
  });

  it("버튼은 줄지 않는다 — 줄어드는 몫은 이유 문구가 받는다", () => {
    renderRunningWithPendingRequest();
    const phase = bar(document.querySelector("[data-workbench-phase-bar]"));
    const buttons = phase.querySelectorAll<HTMLElement>("button[data-action]");
    expect(buttons.length).toBeGreaterThan(0);
    for (const button of buttons) {
      expect(canShrink(button), `${button.dataset.action} 이 줄어든다`).toBe(false);
    }
  });

  it("잠긴 조작의 이유 문구는 폭이 묶이고 넘치면 말줄임한다", () => {
    renderRunningWithPendingRequest();
    const phase = bar(document.querySelector("[data-workbench-phase-bar]"));
    const reasons = phase.querySelectorAll<HTMLElement>("[data-disabled-reason]");
    expect(reasons.length, "실행 중인데 잠긴 조작이 하나도 없다 — 조건이 재현되지 않았다")
      .toBeGreaterThan(0);
    for (const reason of reasons) {
      expect(minWidthIsZero(reason), `${reason.dataset.disabledReason}`).toBe(true);
      expect(hasMaxWidth(reason), `${reason.dataset.disabledReason} 의 폭이 묶이지 않았다`).toBe(true);
      const text = reason.querySelector<HTMLElement>("[data-disabled-reason-text]");
      // `run.pacing` 은 자체 이유 자리를 갖는다 (버튼이 아니라 속도 선택기다).
      if (text === null) continue;
      expect(truncates(text), "이유 문구가 말줄임하지 않는다").toBe(true);
    }
  });
});

describe("줄어들어도 잃지 않는다", () => {
  it("이유 전문은 버튼에 묶인 채로 남는다 (ui-contract §7)", () => {
    render(
      <ActionButton
        action="run.all"
        capability={{
          kind: "disabled",
          reason: "실행 중인 세션이 열려 있습니다",
          remedy: null,
          visibility: "keep",
        }}
      />,
    );
    const button = screen.getByRole("button");
    const described = document.getElementById(button.getAttribute("aria-describedby") ?? "");
    expect(described?.textContent).toContain("실행 중인 세션이 열려 있습니다");
    // 마우스에도 전문이 닿는다 — 말줄임된 문장을 읽을 길이 하나는 있어야 한다.
    expect(
      described?.querySelector<HTMLElement>("[data-disabled-reason-text]")?.title,
    ).toBe("실행 중인 세션이 열려 있습니다");
  });

  it("해소 수단은 말줄임 밖에 있어 잘리지 않는다 (ui-contract §4-1)", () => {
    render(
      <ActionButton
        action="run.all"
        capability={{
          kind: "disabled",
          reason: "실행 중인 세션이 열려 있습니다",
          remedy: { action: "run.stop" },
          visibility: "keep",
        }}
        onRemedy={() => undefined}
      />,
    );
    const remedy = bar(document.querySelector("[data-remedy-for='run.all']"));
    expect(remedy).not.toBeNull();
    // 말줄임하는 칸 **안**에 있으면 폭이 모자랄 때 빠져나갈 길이 사라진다.
    expect(remedy.closest("[data-disabled-reason-text]")).toBeNull();
    expect(canShrink(remedy), "해소 수단이 줄어든다 — 말줄임에 잘린다").toBe(false);
  });
});

/**
 * 국면 띠가 세로로 터진 **진짜 원인**은 지난 실행의 결말 요약이 남은 것이다.
 *
 * `summary` 는 `run_finished` 로 채워지고 지워지는 곳이 없었다. 같은 세션에서 다시
 * 실행하면 국면 표시는 「실행 중」인데 그 옆에 지난 실행의 「실패 · … · 10.07 s」가
 * 그대로 남았다 — 한 화면이 두 가지를 주장한다 (005 U-19·U-20 과 같은 형태).
 *
 * 실제 브라우저 실측: 그 문장이 남으면 요약 칸의 높이가 **546px** 이 된다 (48px 짜리
 * 띠에서). 지우면 그 칸 자체가 없다. 폭이 모자라 한 글자씩 세로로 쌓인 결과이며,
 * 보고된 화면이 정확히 그것이었다.
 */
describe("실행 중에는 지난 실행의 결말을 말하지 않는다", () => {
  it("실행이 도는 동안에는 결말 요약 자리가 없다", () => {
    renderSession({ state: "replaying" }, { summary: STALE_SUMMARY });
    expect(
      document.querySelector("[data-run-summary]"),
      "「실행 중」 옆에 끝난 실행의 결말이 남아 있다",
    ).toBeNull();
  });

  it("실행이 끝나면 같은 요약이 제자리에 나온다 — 지우는 것이 아니라 때를 가린다", () => {
    renderSession({ state: "failed" }, { summary: STALE_SUMMARY });
    expect(document.querySelector("[data-run-summary]")?.textContent).toBe(STALE_SUMMARY);
  });

  it("일시정지 중 끝난 실행의 결말은 남는다 (005 FR-146)", () => {
    // 실행 결말과 세션 상태는 다른 축이다. 멈추기 전에 끝났으면 그 사실은 사실이다.
    renderSession({ state: "paused" }, { summary: STALE_SUMMARY });
    expect(document.querySelector("[data-run-summary]")?.textContent).toBe(STALE_SUMMARY);
  });
});
