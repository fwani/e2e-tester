/**
 * **국면이 실제로 다른 것은 그대로 다르다.** 027 FR-018 · SC-008 (US4).
 *
 * 통합에는 늘 이런 위험이 있다 — 「같아 보이는 것」을 합치다 보면 **달라야 하는 것**도
 * 함께 지운다. 결과 화면의 스크린샷, 편집 화면의 충돌 해소, AI 작성의 곁줄은 국면이
 * 실제로 달라서 다른 것이고, 027 은 그것들을 건드리지 않았어야 한다.
 *
 * 이 파일은 **그 셋이 아직 있는지**만 본다. 어떻게 생겼는지는 각 기능의 검사가 본다.
 */
import { describe, expect, it } from "vitest";

const SOURCES = import.meta.glob("../src/pages/*.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

function source(name: string): string {
  return SOURCES[`../src/pages/${name}.tsx`] ?? "";
}

describe("국면 고유의 것이 사라지지 않았다 (FR-018)", () => {
  it("결과 화면 — **스크린샷·산출물**이 그대로다", () => {
    const s = source("ResultView");
    expect(s, "결과 화면 소스를 읽지 못했다").not.toBe("");
    // 산출물 선택은 이 화면에만 있는 것이다.
    expect(s).toContain("SUPPORTED_ARTIFACTS");
    expect(s).toContain("screenshot");
  });

  it("편집 화면 — **외부 변경 충돌 해소**가 그대로다", () => {
    const s = source("EditView");
    expect(s).toContain("save.overwriteStale");
    expect(s).toContain("onReloadDefinition");
  });

  it("세션 화면 — **AI 작성 곁줄·작업 계획**이 그대로다", () => {
    const s = source("SessionScreen");
    expect(s).toContain("aiAuthoringSidebar");
    expect(s).toContain("workPlan");
  });

  it("세션 화면 — **재녹화 띠·Step 수정 띠**가 그대로다 (016·026)", () => {
    const s = source("SessionScreen");
    expect(s).toContain("RerecordBar");
    expect(s).toContain("StepEditBar");
  });
});

describe("화면이 조작을 더 좁히는 통로가 살아 있다 (FR-007)", () => {
  it("편집 화면의 좁히기 셋이 그대로다", () => {
    const s = source("EditView");
    // 026 이 만든 「고칠 Step 을 고르세요」 같은 잠금 사유가 여기 산다.
    // 배선 통합은 「눌렸을 때 무엇을 하는가」만 옮기고 「언제 누를 수 있는가」는
    // 건드리지 않는다.
    expect(s).toContain("narrowByAiEntry");
    expect(s).toContain("narrowByDeleteSelection");
    expect(s).toContain("narrowByPick");
  });
});

describe("배선이 권한을 판정하지 않는다 (FR-006)", () => {
  it("**조작표가 유일한 판정으로 남는다**", () => {
    const wiring = (
      import.meta.glob("../src/lib/actionWiring.ts", {
        query: "?raw",
        import: "default",
        eager: true,
      }) as Record<string, string>
    )["../src/lib/actionWiring.ts"];
    expect(wiring).toBeTruthy();
    // 세 화면 모두 여전히 조작표를 쓴다.
    for (const name of ["SessionScreen", "EditView", "ResultView"]) {
      expect(source(name), `${name} 이 조작표를 쓰지 않는다`).toContain("capabilitiesFor");
    }
  });
});
