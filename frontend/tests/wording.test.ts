/**
 * 어휘 사전 (005 T012 · FR-138·FR-141).
 *
 * 이 테스트가 지키는 것은 **변환 규칙이 하나라는 사실**이다. 리포트 U-07 은 저장소의
 * 8곳이 `index + 1` 을 각자 하고 한 곳만 빠뜨린 결과였다 — 한 줄 고치면 증상은 사라지지만
 * 같은 실수가 다시 난다.
 */

import { describe, expect, it } from "vitest";

import {
  countsAsFailure,
  outcomeChip,
  outcomeLabel,
  outcomeTone,
  partialRunDiagnosis,
  partialRunNotice,
  progressLabel,
  runFromLabel,
  runSummary,
  skippedRange,
  stepLabel,
  stepNumber,
  stepOutcomeLabel,
} from "../src/lib/wording";
import type { Outcome } from "../src/types/generated/run-result";

const ALL_OUTCOMES: Outcome[] = ["pass", "fail", "stopped", "partial_pass"];

describe("Step 번호 변환 (FR-138)", () => {
  it("0-기반 인덱스를 1-기반 2자리로 만든다", () => {
    expect(stepLabel(5)).toBe("Step 06");
    expect(stepLabel(0)).toBe("Step 01");
    expect(stepNumber(5)).toBe("06");
  });

  it("목록이 보던 0-기반 그대로가 아니다", () => {
    // U-07 — 목록만 `String(step_index).padStart(2,"0")` 로 05 를 보여줬다.
    expect(stepLabel(5)).not.toContain("05");
  });

  it("없는 인덱스를 숫자로 꾸미지 않는다", () => {
    expect(stepLabel(null)).toBe("Step —");
    expect(stepLabel(undefined)).toBe("Step —");
    expect(stepNumber(null)).toBe("—");
  });

  it("건너뛴 구간을 사람 말로 적는다", () => {
    expect(skippedRange(5)).toBe("01~05");
    expect(skippedRange(1)).toBe("01");
    expect(skippedRange(0)).toBeNull();
  });
});

describe("결말 어휘 (FR-141)", () => {
  it("네 결말이 각각 한 문장·한 칩에 대응한다", () => {
    const labels = ALL_OUTCOMES.map(outcomeLabel);
    const chips = ALL_OUTCOMES.map(outcomeChip);
    expect(labels).toEqual(["통과", "실패", "중지", "부분 성공"]);
    expect(chips).toEqual(["PASS", "FAIL", "STOPPED", "PARTIAL"]);
    // 한 결말이 두 이름을 갖지 않는다.
    expect(new Set(labels).size).toBe(labels.length);
    expect(new Set(chips).size).toBe(chips.length);
  });

  it("중지와 부분 성공은 실패로 집계하지 않는다 (FR-131)", () => {
    expect(countsAsFailure("fail")).toBe(true);
    expect(countsAsFailure("stopped")).toBe(false);
    expect(countsAsFailure("partial_pass")).toBe(false);
    expect(countsAsFailure("pass")).toBe(false);
  });

  it("알 수 없는 결말을 통과로 표시하지 않는다", () => {
    // 보수적 기본값 — 결말이 늘 때 화면이 조용히 성공을 말하지 않게 한다.
    const unknown = "brand_new" as Outcome;
    expect(outcomeLabel(unknown)).toBe("실패");
    expect(outcomeChip(unknown)).toBe("FAIL");
    expect(outcomeTone(unknown)).toBe("danger");
  });

  it("값이 없는 것과 모르는 값을 구분한다", () => {
    expect(outcomeLabel(null)).toBe("—");
    expect(outcomeTone(null)).toBe("unknown");
  });

  it("색 역할이 결말마다 다르다 (색만으로 구분하지 않지만 겹치지도 않는다)", () => {
    const tones = ALL_OUTCOMES.map(outcomeTone);
    expect(new Set(tones).size).toBe(tones.length);
  });
});

describe("Step 실행 상태 (FR-151)", () => {
  it("건너뜀과 미실행이 다른 말이다", () => {
    expect(stepOutcomeLabel("skipped")).toBe("건너뜀");
    expect(stepOutcomeLabel("not_run")).toBe("미실행");
    expect(stepOutcomeLabel("skipped")).not.toBe(stepOutcomeLabel("not_run"));
  });
});

describe("결말 요약 (FR-152 · U-02)", () => {
  it("전체 실행 실패는 실패 Step 을 말한다", () => {
    const s = runSummary({
      outcome: "fail",
      passedCount: 5,
      attemptedCount: 7,
      totalCount: 7,
      totalMs: 3210,
      scope: "full",
      startIndex: 0,
      failedStepIndex: 5,
    });
    expect(s).toBe("실패 · Step 06 에서 실패 · 5 / 7 통과 · 3.21 s");
  });

  it("중지는 중지 Step 을 말하고 실패라고 하지 않는다 (U-03)", () => {
    const s = runSummary({
      outcome: "stopped",
      passedCount: 5,
      attemptedCount: 7,
      totalCount: 7,
      totalMs: 3210,
      stoppedStepIndex: 5,
    });
    expect(s).toContain("중지");
    expect(s).not.toContain("실패");
  });

  it("부분 실행의 분모는 실행 대상 수다 — 0 / 7 이 아니다 (U-02)", () => {
    const s = runSummary({
      outcome: "fail",
      passedCount: 0,
      attemptedCount: 2,
      totalCount: 7,
      scope: "partial",
      startIndex: 5,
      failedStepIndex: 5,
    });
    expect(s).toContain("0 / 2 통과");
    expect(s).not.toContain("0 / 7");
    expect(s).toContain("부분 실행");
    expect(s).toContain("(01~05 건너뜀)");
  });

  it("부분 실행임과 실행 구간이 드러난다", () => {
    const s = runSummary({
      outcome: "pass",
      passedCount: 2,
      attemptedCount: 2,
      totalCount: 7,
      scope: "partial",
      startIndex: 5,
    });
    // 부분 구간을 전부 통과한 실행은 「통과」다 — 결말과 범위는 다른 축이다.
    expect(s.startsWith("통과")).toBe(true);
    expect(s).toContain("부분 실행 Step 06~07");
  });

  it("아무것도 돌지 않았으면 비율을 적지 않는다", () => {
    const s = runSummary({
      outcome: "stopped",
      passedCount: 0,
      attemptedCount: 0,
      totalCount: 0,
    });
    expect(s).not.toContain("/");
  });
});

describe("진행 표시 (FR-139)", () => {
  it("전체 수를 넘지 않는다", () => {
    expect(progressLabel(3, 7)).toBe("Step 04 / 07");
    expect(progressLabel(99, 7)).toBe("Step 07 / 07");
  });
});

describe("실행 트리거 라벨 (FR-149·FR-150)", () => {
  it("시작점이 라벨에 드러난다", () => {
    expect(runFromLabel(5)).toBe("Step 06부터 실행");
    expect(runFromLabel(0)).toBe("처음부터 실행");
  });

  it("건너뛰는 구간과 선행 상태 경고를 함께 안내한다", () => {
    const notice = partialRunNotice(5);
    expect(notice).toContain("01~05");
    expect(notice).toContain("처음부터 실행");
  });

  it("전체 실행에는 건너뜀 안내가 없다", () => {
    expect(partialRunNotice(0)).toBeNull();
  });
});

describe("부분 실행 진단 (FR-153 · 헌법 원칙 II)", () => {
  it("첫 줄이 선행 Step 건너뜀을 먼저 지시한다", () => {
    const d = partialRunDiagnosis(5);
    expect(d).toContain("건너뛰었기 때문에");
    expect(d).toContain("처음부터 실행");
    // U-02 — 대기 시간을 늘리라는 틀린 방향을 첫 줄에 두지 않는다.
    expect(d).not.toContain("대기 시간");
    expect(d).not.toContain("느림");
  });

  it("같은 입력에 같은 문구 — 규칙 기반이다", () => {
    expect(partialRunDiagnosis(5)).toBe(partialRunDiagnosis(5));
  });

  it("전체 실행에는 이 진단을 붙이지 않는다", () => {
    expect(partialRunDiagnosis(0)).toBeNull();
  });
});
