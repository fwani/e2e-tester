/**
 * 화면 상태 ↔ URL (005 T093 · FR-166·FR-167·SC-219).
 *
 * 리포트 U-15 — 결과 화면에서도 주소는 `http://127.0.0.1:4410/` 였다. 새로고침하면
 * 목록으로 되돌아가고, **뒤로가기를 누르면 `about:blank` 로 나가 앱을 완전히 이탈**했다.
 *
 * 라우팅 라이브러리를 넣지 않았으므로(research R8) 변환 규칙 자체를 테스트가 지킨다.
 */

import { describe, expect, it } from "vitest";

import {
  locationToSearch,
  searchToLocation,
  type WorkbenchLocation,
} from "../src/hooks/useScreenUrl";

describe("화면 → URL (FR-166)", () => {
  it("목록은 파라미터를 남기지 않는다", () => {
    expect(locationToSearch({ name: "list" })).toBe("");
    expect(locationToSearch({ name: "loading" })).toBe("");
    expect(locationToSearch({ name: "setup" })).toBe("");
  });

  it("결과 화면은 테스트를 주소에 싣는다", () => {
    expect(locationToSearch({ name: "result", testId: "TC-002" })).toBe(
      "?screen=result&test=TC-002",
    );
  });

  /**
   * 007 T076 (FR-239·FR-240) — **결과 국면도 지목한 Step 을 싣는다.**
   *
   * 006 은 편집 국면에만 실었다. 007 이 국면을 넘어 지목을 잇기로 했으므로, 새로
   * 고침을 견디는 자리도 함께 넓어져야 한다 — 넓히지 않으면 결과 국면에서 새로
   * 고치는 순간만 지목이 사라지고, 그 한 자리를 사용자는 예측할 수 없다.
   */
  it("결과 화면도 지목한 Step 을 싣는다 (007 FR-239)", () => {
    expect(locationToSearch({ name: "result", testId: "TC-002", stepId: "st-3" })).toBe(
      "?screen=result&test=TC-002&step=st-3",
    );
  });

  it("정의 화면도 같은 규칙을 쓴다", () => {
    expect(locationToSearch({ name: "definition", testId: "TC-002" })).toBe(
      "?screen=definition&test=TC-002",
    );
  });

  it("실행 화면은 세션을 싣는다", () => {
    expect(locationToSearch({ name: "runner", sessionId: "abc123" })).toBe(
      "?screen=runner&session=abc123",
    );
  });
});

describe("URL → 화면 (FR-166·FR-167)", () => {
  it("빈 주소는 목록이다", () => {
    expect(searchToLocation("")).toEqual({ name: "list" });
  });

  it("결과 화면을 복원한다 — 새로고침해도 같은 화면이다", () => {
    expect(searchToLocation("?screen=result&test=TC-002")).toEqual({
      name: "result",
      testId: "TC-002",
      sessionId: null,
      stepId: null,
    });
  });

  /**
   * 006 T046 · FR-181 — 편집 화면은 지목된 Step 도 주소에 싣는다.
   *
   * 결과 화면의 「Step nn 고치기」로 들어온 뒤 새로고침하면 그 Step 이 다시 펼쳐져야
   * 한다. 지목을 잃으면 사용자는 어느 Step 을 고치러 왔는지부터 다시 찾는다.
   */
  it("편집 화면의 지목된 Step 을 복원한다 (006 FR-181)", () => {
    expect(searchToLocation("?screen=definition&test=TC-001&step=step-06")).toEqual({
      name: "definition",
      testId: "TC-001",
      sessionId: null,
      stepId: "step-06",
    });
    expect(
      locationToSearch({ name: "definition", testId: "TC-001", stepId: "step-06" }),
    ).toBe("?screen=definition&test=TC-001&step=step-06");
  });

  it("알 수 없는 화면 이름은 목록으로 떨어진다 — 앱을 이탈하지 않는다", () => {
    const loc = searchToLocation("?screen=whatever");
    // 앱 **안의** 어떤 화면으로 해석된다. `about:blank` 로 나가지 않는다.
    expect(loc.name).toBe("whatever");
    // App 쪽 분기가 알 수 없는 이름을 목록으로 처리한다 — 그 계약을 여기서 문서화한다.
  });

  it("왕복이 값을 잃지 않는다", () => {
    for (const loc of [
      { name: "result", testId: "TC-002" },
      { name: "definition", testId: "TC-009" },
      { name: "keys" },
      { name: "secrets" },
    ]) {
      const back = searchToLocation(locationToSearch(loc));
      expect(back.name).toBe(loc.name);
      if ("testId" in loc) expect(back.testId).toBe(loc.testId);
    }
  });
});

/**
 * 007 T076 — **국면 · 테스트 · Step 셋이 왕복을 견딘다** (FR-240).
 *
 * 한쪽 방향만 재면 "쓰기는 맞는데 읽기가 틀린" 상태를 놓친다 — 그때 사용자는 주소가
 * 옳게 보이는 화면에서 새로 고쳐 다른 곳에 떨어진다.
 */
describe("왕복 변환 (007 T076 · FR-240)", () => {
  const CASES: WorkbenchLocation[] = [
    { name: "result", testId: "TC-001", sessionId: null, stepId: "st-2" },
    { name: "result", testId: "TC-001", sessionId: null, stepId: null },
    { name: "definition", testId: "TC-001", sessionId: null, stepId: "st-2" },
    { name: "definition", testId: "TC-009", sessionId: null, stepId: null },
    { name: "runner", testId: null, sessionId: "s-1", stepId: null },
    { name: "keys", testId: null, sessionId: null, stepId: null },
    { name: "secrets", testId: null, sessionId: null, stepId: null },
  ];

  it.each(CASES)("$name · $testId · $stepId 을 그대로 되찾는다", (at) => {
    expect(searchToLocation(locationToSearch(at))).toEqual(at);
  });

  it("목록은 파라미터가 없고, 없는 주소는 목록으로 떨어진다", () => {
    expect(locationToSearch({ name: "list" })).toBe("");
    expect(searchToLocation("")).toEqual({ name: "list" });
  });
});
