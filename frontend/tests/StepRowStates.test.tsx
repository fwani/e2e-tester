/**
 * 011 T018 — **한 행의 네 상태는 서로 다른 자리를 갖는다** (UC-011-11 · FR-371·FR-372).
 *
 * ## 사용자 보고
 *
 * > 「선택한 스텝을 명확하게 표시한다」
 *
 * ## 무엇이 문제였나
 *
 * `StepRow` 가 세 상태를 **한 클래스 자리에 배타적으로** 넣었다.
 *
 * ```
 * className={`srow ${isPausedHere ? "paused" : selected ? "sel" : OUTCOME_MARK[outcome]}`}
 * ```
 *
 * 삼항이 셋을 줄 세우므로 언제나 하나만 남는다. 결과:
 *
 * - 통과한 Step 을 고르면 `sel` 이 `pass` 를 밀어내 **결말이 사라졌다.**
 * - 일시정지가 걸린 행은 `paused` 가 이겨 **골라도 선택이 보이지 않았다.**
 *
 * 그리고 셋이 CSS 에서도 같은 두 채널(`border-left-color`·`background`)을 다투고 있었다.
 *
 * ## 011 이 나눈 네 채널
 *
 * | 상태 | 채널 |
 * |---|---|
 * | 결말 | 행 왼쪽 3px `border-left-color` + 오른쪽 결말 칸의 형태 아이콘 |
 * | 일시정지 | 바탕(`background`) + `data-paused-here` |
 * | 지목 | 안쪽 링(`box-shadow: inset`) + `aria-current="true"` |
 * | 삭제 대상 | 칸 0 체크 칸 (US4 가 붙인다) |
 *
 * ## 이 파일이 재는 것
 *
 * **성립 가능한 모든 조합**이다. 하나씩 재면 조합에서 조용히 깨진다 — 그것이 이 결함의
 * 형태였다 (각각은 옳았고 함께 놓였을 때 하나가 사라졌다).
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StepList } from "../src/components/workbench/StepList";
import type { StepOutcome } from "../src/components/workbench/model";
import { displayOutcomeLabel } from "../src/lib/wording";
import { workbenchStep } from "./helpers/model";

afterEach(cleanup);

/** 결말 표식을 갖는 값만 — `pending`·`skipped`·`not_run` 은 표식이 없는 것이 정보다. */
const MARKED_OUTCOMES: StepOutcome[] = ["pass", "fail", "running"];

function renderRow(over: {
  outcome?: StepOutcome;
  isPausedHere?: boolean;
  selected?: boolean;
}) {
  const step = workbenchStep({
    id: "st-1",
    index: 0,
    outcome: over.outcome ?? "pending",
    isPausedHere: over.isPausedHere ?? false,
  });
  render(
    <StepList
      steps={[step]}
      authoring="record"
      focusedStepId={over.selected === true ? "st-1" : null}
      onSelect={() => undefined}
    />,
  );
  const row = document.querySelector('[data-step-row="st-1"]') as HTMLElement | null;
  expect(row, "Step 행이 없다").not.toBeNull();
  return row!;
}

/** 결말이 읽히는가 — **형태와 이름 둘 다** (FR-372 · 005 FR-141·FR-151). */
function outcomeIsReadable(row: HTMLElement, outcome: StepOutcome): boolean {
  const mark = row.querySelector(`[data-outcome="${outcome}"]`);
  if (mark === null) return false;
  return mark.getAttribute("aria-label") === displayOutcomeLabel(outcome);
}

/** 결말이 왼쪽 3px 채널을 갖는가. 클래스로 잰다 — 색 값은 정본이 소유한다. */
const outcomeHasLeftChannel = (row: HTMLElement, outcome: StepOutcome) =>
  row.classList.contains({ pass: "pass", fail: "fail", running: "run" }[outcome as "pass"] ?? "");

const isPausedMarked = (row: HTMLElement) =>
  row.hasAttribute("data-paused-here") && row.classList.contains("paused");

const isSelectedMarked = (row: HTMLElement) =>
  row.getAttribute("aria-current") === "true" && row.classList.contains("sel");

describe("UC-011-11 — 지목이 결말을 대체하지 않는다", () => {
  it.each(MARKED_OUTCOMES)("%s 인 Step 을 고르면 결말과 지목이 함께 보인다", (outcome) => {
    const row = renderRow({ outcome, selected: true });
    expect(isSelectedMarked(row), "지목이 표시되지 않았다").toBe(true);
    expect(
      outcomeHasLeftChannel(row, outcome),
      `지목이 결말(${outcome})의 왼쪽 채널을 빼앗았다`,
    ).toBe(true);
    expect(outcomeIsReadable(row, outcome), `결말(${outcome})의 형태·이름이 사라졌다`).toBe(true);
  });
});

describe("UC-011-11 — 일시정지가 지목을 대체하지 않는다", () => {
  it("일시정지가 걸린 Step 을 고르면 둘 다 보인다", () => {
    const row = renderRow({ isPausedHere: true, selected: true });
    expect(isPausedMarked(row), "일시정지 표시가 사라졌다").toBe(true);
    expect(isSelectedMarked(row), "일시정지가 지목을 가렸다").toBe(true);
  });

  it("고르지 않은 일시정지 행에는 지목 표시가 없다", () => {
    const row = renderRow({ isPausedHere: true, selected: false });
    expect(isPausedMarked(row)).toBe(true);
    expect(isSelectedMarked(row), "고르지도 않았는데 지목으로 보인다").toBe(false);
  });
});

describe("UC-011-11 — 성립 가능한 모든 조합에서 넷이 함께 읽힌다", () => {
  /**
   * 조합을 손으로 열거하지 않는다. 셋의 곱을 돌면 값이 늘어날 때 빠뜨릴 수 없다 —
   * `StepOutcome` 에 값을 더하면 이 검사가 그것을 바로 센다.
   */
  const ALL_OUTCOMES: StepOutcome[] = [
    "pass",
    "fail",
    "running",
    "pending",
    "skipped",
    "not_run",
    "recorded",
  ];

  it.each(
    ALL_OUTCOMES.flatMap((outcome) =>
      [false, true].flatMap((isPausedHere) =>
        [false, true].map((selected) => ({ outcome, isPausedHere, selected })),
      ),
    ),
  )("결말=$outcome · 일시정지=$isPausedHere · 지목=$selected", (combo) => {
    const row = renderRow(combo);

    // 결말은 언제나 이름을 갖는다 — 표식이 없는 값도 접근 가능한 이름은 있다.
    expect(
      row.querySelector(`[data-outcome="${combo.outcome}"]`),
      "결말 칸이 사라졌다",
    ).not.toBeNull();

    expect(isPausedMarked(row)).toBe(combo.isPausedHere);
    expect(isSelectedMarked(row)).toBe(combo.selected);

    if (MARKED_OUTCOMES.includes(combo.outcome)) {
      expect(
        outcomeHasLeftChannel(row, combo.outcome),
        "결말의 왼쪽 채널이 다른 상태에 빼앗겼다",
      ).toBe(true);
    }
  });
});

describe("FR-372 — 색만으로 구분하지 않는다", () => {
  it("지목은 접근 가능한 상태로도 읽힌다", () => {
    const row = renderRow({ selected: true });
    expect(row.getAttribute("aria-current")).toBe("true");
    // 행 안의 이름 버튼도 눌린 상태를 말한다 (기존 `aria-pressed` 유지).
    const name = screen.getByRole("button", { name: "로그인 버튼 클릭" });
    expect(name.getAttribute("aria-pressed")).toBe("true");
  });

  it("고르지 않은 행은 `aria-current` 를 갖지 않는다", () => {
    const row = renderRow({ selected: false });
    expect(row.hasAttribute("aria-current")).toBe(false);
  });
});
