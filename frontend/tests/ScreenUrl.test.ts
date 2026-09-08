/**
 * 화면 상태 ↔ URL (005 T093 · FR-166·FR-167·SC-219).
 *
 * 리포트 U-15 — 결과 화면에서도 주소는 `http://127.0.0.1:4410/` 였다. 새로고침하면
 * 목록으로 되돌아가고, **뒤로가기를 누르면 `about:blank` 로 나가 앱을 완전히 이탈**했다.
 *
 * 라우팅 라이브러리를 넣지 않았으므로(research R8) 변환 규칙 자체를 테스트가 지킨다.
 */

import { afterEach, describe, expect, it } from "vitest";

import { renderHook } from "@testing-library/react";

import {
  locationToSearch,
  searchToLocation,
  useScreenUrl,
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

/**
 * 007 T094 (converge 1회차) — **뒤로 가기는 앱을 이탈하지 않는다** (FR-241 · 005 FR-167).
 *
 * 005 U-15 가 본 것: 뒤로 가기를 누르면 `about:blank` 로 나가 앱을 완전히 이탈했다.
 *
 * **변환만 재는 검사는 이 결함을 못 잡는다.** 005 N-01 이 정확히 그 형태였다 — 변환
 * 함수 테스트는 초록인데 실제 새로 고침이 복원되지 않았고, 틀린 것은 변환이 아니라 첫
 * 렌더의 국면이었다. 그래서 여기서는 **훅을 실제로 걸고 `popstate` 를 쏜다.**
 */
describe("뒤로 가기가 앱 안에 머문다 (T094 · FR-241)", () => {
  const at = (search: string) =>
    window.history.replaceState({}, "", `${window.location.pathname}${search}`);

  afterEach(() => at(""));

  it("`popstate` 가 주소의 국면으로 화면을 되돌린다", () => {
    const seen: WorkbenchLocation[] = [];
    at("?screen=result&test=TC-001&step=st-2");
    renderHook(() =>
      useScreenUrl({ name: "definition", testId: "TC-001", stepId: "st-2" }, (loc) =>
        seen.push(loc),
      ),
    );

    // 브라우저가 뒤로 갔다 — 주소가 먼저 바뀌고 그 다음 이벤트가 온다.
    at("?screen=result&test=TC-001&step=st-2");
    window.dispatchEvent(new PopStateEvent("popstate"));

    expect(seen, "뒤로 가기가 앱 안의 이동으로 이어지지 않는다").toHaveLength(1);
    expect(seen[0]).toEqual({
      name: "result",
      testId: "TC-001",
      sessionId: null,
      stepId: "st-2",
    });
  });

  it("빈 주소로 돌아가면 목록이다 — 앱 밖으로 나가지 않는다", () => {
    const seen: WorkbenchLocation[] = [];
    renderHook(() => useScreenUrl({ name: "result", testId: "TC-001" }, (loc) => seen.push(loc)));

    at("");
    window.dispatchEvent(new PopStateEvent("popstate"));

    expect(seen[0]?.name, "빈 주소가 앱 밖으로 읽혔다").toBe("list");
  });

  it("지목한 Step 도 뒤로 가기로 되돌아온다 (FR-239 와 같은 값)", () => {
    const seen: WorkbenchLocation[] = [];
    renderHook(() => useScreenUrl({ name: "list" }, (loc) => seen.push(loc)));

    at("?screen=definition&test=TC-009&step=st-7");
    window.dispatchEvent(new PopStateEvent("popstate"));

    expect(seen[0]?.stepId).toBe("st-7");
  });

  it("첫 렌더는 히스토리에 항목을 쌓지 않는다 — 첫 뒤로 가기가 헛돌지 않는다", () => {
    const before = window.history.length;
    renderHook(() => useScreenUrl({ name: "result", testId: "TC-001" }, () => undefined));
    expect(window.history.length).toBe(before);
  });

  /**
   * 2회차 — **옛 주소를 떨어뜨리지 않는다** (research R12 · FR-240).
   *
   * 만들기가 화면 둘(`create` · `ai-compose`)에서 국면 하나(`compose`)로 합쳐졌다
   * (FR-259). 옛 이름으로 들어온 주소를 알 수 없는 값으로 보고 목록으로 떨어뜨리면
   * **사용자가 열어 둔 탭과 북마크가 끊긴다** — 그것은 이 라운드가 고치려는 문제와
   * 무관한 손해다.
   */
  describe("옛 만들기 주소가 만들기 국면으로 열린다 (2회차 · FR-240)", () => {
    it("`create` 가 `compose` 로 읽힌다", () => {
      expect(searchToLocation("?screen=create").name).toBe("compose");
    });

    it("`ai-compose` 가 `compose` 로 읽힌다", () => {
      expect(searchToLocation("?screen=ai-compose").name).toBe("compose");
    });

    it("뒤로 가기로 옛 주소에 닿아도 만들기 국면이다 (FR-241)", () => {
      const seen: WorkbenchLocation[] = [];
      renderHook(() => useScreenUrl({ name: "list" }, (loc) => seen.push(loc)));

      at("?screen=ai-compose");
      window.dispatchEvent(new PopStateEvent("popstate"));

      expect(seen[0]?.name, "옛 주소가 목록으로 떨어졌다").toBe("compose");
    });

    it("만들기 국면은 주소에 국면만 남긴다 — 입력 중인 값을 싣지 않는다", () => {
      // 시작 주소·지시문·고른 방법은 새로 고침으로 되살릴 대상이 아니다 (research R12)
      expect(locationToSearch({ name: "compose" })).toBe("?screen=compose");
    });

    it("모르는 이름은 그대로 둔다 — 정규화가 다른 주소를 삼키지 않는다", () => {
      expect(searchToLocation("?screen=composer").name).toBe("composer");
    });
  });
});
