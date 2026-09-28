/**
 * 어긋난 검증이 화면에 드러난다 (020 T026·T034·T040 · FR-013~FR-015·FR-019·FR-024).
 *
 * ## 이 파일이 지키는 것
 *
 * US1 이 만든 상태 — 정의에 통과하지 않는 검증이 있다 — 를 사람이 모르면, US1 은
 * 「조용히 실패하는 테스트를 만드는 기능」이 된다. 화면 셋이 그것을 말해야 한다:
 * Step 목록의 칩, Step 상세의 기대값·관찰값, 실행 결과의 분류.
 *
 * **0건 규칙을 세 자리에서 함께 확인한다.** 없는 것을 0으로 표시하면 읽을 것이 늘기만
 * 하고, 정상 완료가 경고처럼 보인다.
 */
import { describe, expect, it } from "vitest";

import {
  assertionClassHint,
  assertionClassLabel,
  assertionClassSummary,
  assertionClassTone,
  countAssertionClasses,
  mismatchNotice,
} from "../src/lib/wording";
import type { AssertionClass } from "../src/types/generated/run-result";

function results(...classes: (AssertionClass | null)[]) {
  return classes.map((assertion_class) => ({ assertion_class }));
}

describe("검증 분류의 어휘 (020 FR-018~FR-020)", () => {
  it("세 분류가 모두 이름을 갖는다", () => {
    expect(assertionClassLabel("regression")).toBe("회귀");
    expect(assertionClassLabel("known_defect")).toBe("알려진 결함");
    expect(assertionClassLabel("resolved")).toBe("해소됨");
  });

  it("모르는 값에는 이름을 지어내지 않는다", () => {
    // 결말 어휘와 **다른 판단이다.** 그쪽은 보수적 기본값(실패)이 안전하지만, 여기서
    // 아무 분류나 붙이면 사용자가 없는 회귀를 찾는다.
    expect(assertionClassLabel(null)).toBeNull();
    expect(assertionClassLabel(undefined)).toBeNull();
    expect(assertionClassLabel("unknown" as AssertionClass)).toBeNull();
  });

  it("회귀가 가장 강한 색을 갖는다 (FR-020)", () => {
    expect(assertionClassTone("regression")).toBe("danger");
    expect(assertionClassTone("known_defect")).toBe("warn");
  });

  it("해소됨을 성공 색으로 칠하지 않는다", () => {
    // 그 실행에서 통과한 것은 맞지만 사용자가 할 일(표시 걷어내기)이 남아 있다.
    // 초록으로 칠하면 끝난 것으로 읽힌다.
    expect(assertionClassTone("resolved")).not.toBe("success");
  });

  it("분류마다 사용자가 무엇을 해야 하는지까지 말한다", () => {
    expect(assertionClassHint("resolved")).toContain("걷어낼 수 있습니다");
    expect(assertionClassHint("regression")).toContain("지금 실패");
  });
});

describe("건수 세기와 요약 (FR-019)", () => {
  it("분류가 없는 행은 세지 않는다", () => {
    expect(countAssertionClasses(results(null, null))).toEqual({});
  });

  it("같은 분류를 모아 센다", () => {
    expect(countAssertionClasses(results("known_defect", "known_defect", "regression"))).toEqual({
      known_defect: 2,
      regression: 1,
    });
  });

  it("020 이전 결과 파일에는 칸 자체가 없다 — 그때도 세지 않는다", () => {
    // **`null` 과 `undefined` 를 같게 다뤄야 한다.** 생성된 타입은 이 칸을 필수로
    // 표기하지만(직렬화 스키마의 규칙), 옛 결과 파일에서 오는 값은 `undefined` 다.
    // `!== null` 만 보는 코드는 없는 기록을 그리려다 터진다 — 실제로 그렇게 터졌다.
    expect(countAssertionClasses([{}, {}])).toEqual({});
    expect(countAssertionClasses([{}, { assertion_class: "regression" }])).toEqual({
      regression: 1,
    });
  });

  it("0건인 분류는 열쇠 자체가 없다", () => {
    const counts = countAssertionClasses(results("regression"));
    expect("known_defect" in counts).toBe(false);
    expect("resolved" in counts).toBe(false);
  });

  it("요약은 회귀를 먼저 적는다 (FR-020)", () => {
    const counts = countAssertionClasses(results("known_defect", "resolved", "regression"));
    const summary = assertionClassSummary(counts);
    expect(summary).not.toBeNull();
    expect(summary!.indexOf("회귀")).toBeLessThan(summary!.indexOf("알려진 결함"));
    expect(summary!.indexOf("알려진 결함")).toBeLessThan(summary!.indexOf("해소됨"));
  });

  it("0건인 분류는 요약에 실리지 않는다", () => {
    const summary = assertionClassSummary(countAssertionClasses(results("regression")));
    expect(summary).toBe("회귀 1");
  });

  it("말할 것이 없으면 요약이 서지 않는다", () => {
    expect(assertionClassSummary(countAssertionClasses(results(null)))).toBeNull();
    expect(assertionClassSummary({})).toBeNull();
    expect(assertionClassSummary(null)).toBeNull();
  });
});

describe("작성 종료 알림 (FR-013)", () => {
  it("어긋난 검증이 있으면 건수를 말한다", () => {
    expect(mismatchNotice(3)).toContain("3건");
  });

  it("0건이면 아무 말도 하지 않는다", () => {
    // **없는 것을 0으로 알리면 정상 완료가 경고처럼 보인다.**
    expect(mismatchNotice(0)).toBeNull();
    expect(mismatchNotice(null)).toBeNull();
    expect(mismatchNotice(undefined)).toBeNull();
  });

  it("음수는 없는 것으로 본다", () => {
    expect(mismatchNotice(-1)).toBeNull();
  });
});

describe("제품 결함이라고 단정하지 않는다 (spec Assumptions)", () => {
  it("칩과 안내가 「결함」이 아니라 「결함 후보」로 말한다", async () => {
    const { MISMATCH_CHIP, MISMATCH_HINT } = await import("../src/lib/wording");
    expect(MISMATCH_CHIP).toBe("결함 후보");
    // 제품은 기대와 달랐다는 사실만 기록한다. 그것이 제품 결함인지 지시문 오류인지는
    // 사람이 판단한다.
    expect(MISMATCH_HINT).not.toContain("결함입니다");
    expect(MISMATCH_HINT).toContain("통과하지 않");
  });

  it("걷어내기 안내가 그 결과까지 말한다 (FR-027·FR-029)", async () => {
    const { CLEAR_MISMATCH_HINT } = await import("../src/lib/wording");
    expect(CLEAR_MISMATCH_HINT).toContain("회귀");
    // 기록도 함께 사라진다는 것이 사용자 결정이다 (2026-09-28).
    expect(CLEAR_MISMATCH_HINT).toContain("기록도 함께");
  });
});

describe("제품 동작 불일치의 안내 (FR-024)", () => {
  it("사람이 알려 줄 것이 없다는 사실 자체를 말한다", async () => {
    const { PRODUCT_MISMATCH_NOTE } = await import("../src/lib/wording");
    expect(PRODUCT_MISMATCH_NOTE).toContain("답변 칸을 열지 않습니다");
    // 막다른 길로 두지 않는다 — 사람이 이어받는 길은 여전히 열려 있다 (FR-026).
    expect(PRODUCT_MISMATCH_NOTE).toContain("직접 이어받");
  });
});
