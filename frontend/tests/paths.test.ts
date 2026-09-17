/**
 * 018 — 주소 모양과 옛 주소 변환 (design §2 · §6).
 *
 * `ScreenUrl.test.ts`(005·006·007) 가 지키던 것을 물려받는다: 기본 화면은 주소에 아무것도 남기지 않고,
 * 지목한 Step 은 주소에 실리며, 옛 주소(`?screen=` · 1회차의 `create`·`ai-compose`)로 들어와도 같은
 * 화면에 닿는다. 왕복은 라우트 표가 실제로 쓰는 `matchPath` 로 확인한다.
 */
import { matchPath } from "react-router";
import { describe, expect, it } from "vitest";

import { PATTERNS, legacyPath, paths } from "../src/lib/paths";

describe("주소 빌더 (018 §2)", () => {
  it("목록은 `/` 다 — 기본 화면에 파라미터를 남기지 않는다 (005 FR-166)", () => {
    expect(paths.list()).toBe("/");
  });

  it("결과·편집은 테스트를 경로에, 지목한 Step 을 질의에 싣는다 (006 FR-181 · 007 FR-239)", () => {
    expect(paths.result("TC-001")).toBe("/tests/TC-001/result");
    expect(paths.result("TC-001", "st-2")).toBe("/tests/TC-001/result?step=st-2");
    expect(paths.edit("TC-001", null)).toBe("/tests/TC-001/edit");
    expect(paths.edit("TC-001", "st-2")).toBe("/tests/TC-001/edit?step=st-2");
  });

  it("만들기는 초안이 있을 때만 질의를 싣는다 (014 US3)", () => {
    expect(paths.compose()).toBe("/tests/new");
    expect(paths.compose("D-0001")).toBe("/tests/new?draft=D-0001");
  });

  it("실행 화면은 편집에서 왔을 때만 돌아갈 곳을 싣는다 (006 FR-204)", () => {
    expect(paths.session("s-1")).toBe("/sessions/s-1");
    expect(paths.session("s-1", { stepId: "st-2" })).toBe("/sessions/s-1?from=edit&step=st-2");
    expect(paths.session("s-1", { stepId: null })).toBe("/sessions/s-1?from=edit");
  });

  it("나머지 화면", () => {
    expect(paths.projects()).toBe("/projects");
    expect(paths.importPreview("p-1")).toBe("/import/p-1");
    expect(paths.keys()).toBe("/keys");
    expect(paths.secrets()).toBe("/secrets");
  });

  it("식별자는 경로 조각으로 인코딩된다 — 슬래시가 경로를 쪼개지 않는다", () => {
    expect(paths.result("A/B")).toBe("/tests/A%2FB/result");
  });

  it("왕복이 값을 잃지 않는다 — 라우트 표의 모양으로 되읽는다 (007 FR-240)", () => {
    const cases: [string, string, Record<string, string>][] = [
      [PATTERNS.result, paths.result("TC-001", "st-2"), { testId: "TC-001" }],
      [PATTERNS.edit, paths.edit("TC-002"), { testId: "TC-002" }],
      [PATTERNS.session, paths.session("s-9", { stepId: "st-1" }), { sessionId: "s-9" }],
      [PATTERNS.importPreview, paths.importPreview("p-1"), { planId: "p-1" }],
    ];
    for (const [pattern, url, params] of cases) {
      const pathname = url.split("?")[0]!;
      expect(matchPath(pattern, pathname)?.params, url).toEqual(params);
    }
  });
});

describe("옛 주소 → 새 주소 (018 §6 · 열어 둔 탭과 북마크를 끊지 않는다)", () => {
  it.each([
    ["?screen=result&test=TC-001", "/tests/TC-001/result"],
    ["?screen=result&test=TC-001&step=st-2", "/tests/TC-001/result?step=st-2"],
    ["?screen=definition&test=TC-001&step=st-2", "/tests/TC-001/edit?step=st-2"],
    ["?screen=keys", "/keys"],
    ["?screen=secrets", "/secrets"],
    ["?screen=compose", "/tests/new"],
    ["?screen=create", "/tests/new"],
    ["?screen=ai-compose", "/tests/new"],
    ["?screen=runner&session=s-1", "/sessions/s-1"],
    ["?screen=list", "/"],
    ["?screen=result", "/"],
    ["?screen=runner", "/"],
    ["?screen=없는-화면", "/"],
  ])("%s → %s", (search, expected) => {
    expect(legacyPath(search)).toBe(expected);
  });

  it("`screen` 이 없으면 옮기지 않는다", () => {
    expect(legacyPath("")).toBeNull();
    expect(legacyPath("?step=st-2")).toBeNull();
  });
});
