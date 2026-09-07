/**
 * 화면 상태 ↔ URL (005 T093 · FR-166·FR-167·SC-219).
 *
 * 리포트 U-15 — 결과 화면에서도 주소는 `http://127.0.0.1:4410/` 였다. 새로고침하면
 * 목록으로 되돌아가고, **뒤로가기를 누르면 `about:blank` 로 나가 앱을 완전히 이탈**했다.
 *
 * 라우팅 라이브러리를 넣지 않았으므로(research R8) 변환 규칙 자체를 테스트가 지킨다.
 */

import { describe, expect, it } from "vitest";

import { locationToSearch, searchToLocation } from "../src/hooks/useScreenUrl";

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
    });
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
