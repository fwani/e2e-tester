/**
 * 알 수 없는 결말은 실패로 취급한다 (005 T106 · data-model.md §1 보수적 기본값).
 *
 * 결말은 이번에 둘에서 넷으로 늘었고, **또 늘 수 있다.** 그때 낡은 화면이 새 값을 만나면
 * 두 가지 중 하나를 한다 — 통과로 보이거나, 실패로 보이거나.
 *
 * 통과로 보이는 쪽이 훨씬 나쁘다. 사용자는 확인하지 않고 넘어가고, 도구는 "테스트가
 * 통과했다" 는 가장 하면 안 되는 거짓말을 한다. 제품이 테스트 도구이므로 이 거짓말은
 * 제품의 존재 이유를 무너뜨린다.
 *
 * 그래서 기본값이 실패다. 사전 함수 **전부**가 같은 기본값을 갖는지 본다 — 하나만
 * 어긋나도 화면은 "실패" 라고 쓰인 옆에 초록 칩을 띄운다.
 */

import { describe, expect, it } from "vitest";

import {
  countsAsFailure,
  displayOutcomeLabel,
  meansPassed,
  outcomeChip,
  outcomeLabel,
  outcomeTone,
  runSummary,
} from "../src/lib/wording";
import type { StepOutcome as WorkbenchStepOutcome } from "../src/components/workbench/model";
import type { Outcome } from "../src/types/generated/run-result";

/** 아직 존재하지 않는 결말. 타입을 뚫는 것은 **런타임에 실제로 올 수 있기** 때문이다. */
const FUTURE = "flaky_pass" as Outcome;

describe("알 수 없는 결말 (T106)", () => {
  it("문장은 「실패」다 — 통과로 보이면 사용자가 확인하지 않고 넘어간다", () => {
    expect(outcomeLabel(FUTURE)).toBe("실패");
  });

  it("칩은 FAIL 이다", () => {
    expect(outcomeChip(FUTURE)).toBe("FAIL");
  });

  it("색 역할은 danger 다 — 문장과 색이 어긋나면 어느 쪽을 믿을지 알 수 없다", () => {
    expect(outcomeTone(FUTURE)).toBe("danger");
  });

  it("실패로 집계한다 — 문장이 「실패」인데 집계가 0 이면 화면이 자기와 어긋난다", () => {
    expect(countsAsFailure(FUTURE)).toBe(true);
  });

  it("요약 문장도 실패로 시작한다", () => {
    const summary = runSummary({
      outcome: FUTURE,
      passedCount: 3,
      attemptedCount: 5,
      totalCount: 5,
    });
    expect(summary.startsWith("실패")).toBe(true);
    expect(summary).not.toContain("통과 ·"); // 결말 자리에 「통과」가 오지 않는다
  });
});

describe("값이 없는 것과 모르는 것은 다르다", () => {
  it("null 은 「—」다 — 아직 실행하지 않은 것을 실패로 적지 않는다", () => {
    expect(outcomeLabel(null)).toBe("—");
    expect(outcomeChip(null)).toBe("—");
    expect(outcomeTone(null)).toBe("unknown");
    expect(countsAsFailure(null)).toBe(false);
  });

  it("undefined 도 마찬가지다", () => {
    expect(outcomeLabel(undefined)).toBe("—");
    expect(outcomeChip(undefined)).toBe("—");
    expect(outcomeTone(undefined)).toBe("unknown");
  });
});

describe("아는 네 값은 그대로다", () => {
  const KNOWN: Array<[Outcome, string, string]> = [
    ["pass", "통과", "PASS"],
    ["fail", "실패", "FAIL"],
    ["stopped", "중지", "STOPPED"],
    ["partial_pass", "부분 성공", "PARTIAL"],
  ];

  it.each(KNOWN)("%s → %s / %s", (outcome, label, chip) => {
    expect(outcomeLabel(outcome)).toBe(label);
    expect(outcomeChip(outcome)).toBe(chip);
  });

  it("중지와 부분 성공은 실패로 집계하지 않는다 (FR-131)", () => {
    expect(countsAsFailure("stopped")).toBe(false);
    expect(countsAsFailure("partial_pass")).toBe(false);
    expect(countsAsFailure("fail")).toBe(true);
  });
});

/* ─── 007 T016 — 표시 결말이 늘어도 같은 원칙이 유지되는가 ──────────────────── */

describe("표시 결말의 알 수 없는 값 (007 T016)", () => {
  /** 아직 존재하지 않는 표시 결말. 런타임에 실제로 올 수 있다. */
  const FUTURE_DISPLAY = "flaky" as WorkbenchStepOutcome;

  it("알 수 없는 표시 결말을 통과로 부르지 않는다", () => {
    // `displayOutcomeLabel` 은 완전 스위치이므로 새 값에 `undefined` 를 돌려준다.
    // 중요한 것은 그것이 **「통과」가 아니라는 것**이다 — 통과로 보이는 쪽이 훨씬 나쁘다.
    expect(displayOutcomeLabel(FUTURE_DISPLAY)).not.toBe("통과");
  });

  it("`meansPassed` 는 `pass` 하나에만 참이다 — 「기록됨」은 통과가 아니다 (FR-225)", () => {
    expect(meansPassed("pass")).toBe(true);
    for (const o of [
      "fail",
      "running",
      "pending",
      "skipped",
      "not_run",
      "recorded",
    ] as WorkbenchStepOutcome[]) {
      expect(meansPassed(o), o).toBe(false);
    }
    expect(meansPassed(FUTURE_DISPLAY)).toBe(false);
  });

  it("일곱 표시 결말이 서로 다른 라벨을 갖는다 — 두 값이 같은 말을 쓰면 구분이 사라진다", () => {
    const all: WorkbenchStepOutcome[] = [
      "pass",
      "fail",
      "running",
      "pending",
      "skipped",
      "not_run",
      "recorded",
    ];
    const labels = all.map(displayOutcomeLabel);
    expect(new Set(labels).size).toBe(all.length);
  });
});
