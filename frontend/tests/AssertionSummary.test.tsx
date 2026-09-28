/**
 * 검증 어휘와 목록 요약 (021 T030 · FR-023·FR-026).
 *
 * ## 이 파일이 지키는 것 하나
 *
 * 021 이전 목록 요약은 종류를 영문 원문으로 찍고 **비교 방식을 아예 보이지 않았다.**
 * 그래서 「`오류` 가 있어야 한다」와 「`오류` 가 없어야 한다」가 목록에서 **똑같이
 * 보였다.** 정반대 뜻의 두 Step 을 구별할 수 없는 것은 표시 문제가 아니라 결함이고,
 * 부정 검증을 노출하기 전에 먼저 고쳐야 하는 선결 조건이었다 (research R6).
 *
 * 아래 `두 검증이 다르게 읽힌다` 가 그 하나를 지킨다. 나머지는 그것이 우연히
 * 성립하지 않도록 어휘의 완전성을 함께 세운다.
 */
import { describe, expect, it } from "vitest";

import type { AssertionKind, MatchMode } from "../src/api/client";
import {
  ASSERTION_KIND_HINT,
  ASSERTION_KIND_LABEL,
  MATCH_MODE_LABEL,
  NEGATED_MATCH_NOTE,
  assertionSummary,
  comparesValue,
  isNegatedMatch,
} from "../src/lib/wording";

const KINDS: AssertionKind[] = ["visible", "hidden", "enabled", "disabled", "text", "url"];
const MATCHES: MatchMode[] = ["equals", "contains", "not_equals", "not_contains"];

describe("목록 요약이 긍정과 부정을 가른다 (FR-023)", () => {
  it("같은 값의 두 검증이 다르게 읽힌다 — **이 파일의 핵심**", () => {
    const positive = assertionSummary({ kind: "text", match: "contains", value: "오류" });
    const negative = assertionSummary({
      kind: "text",
      match: "not_contains",
      value: "오류",
    });

    expect(positive).not.toBe(negative);
    expect(negative).toContain("포함하지 않는다");
  });

  it("주소 검증도 마찬가지다", () => {
    const positive = assertionSummary({ kind: "url", match: "equals", value: "/login" });
    const negative = assertionSummary({ kind: "url", match: "not_equals", value: "/login" });
    expect(positive).not.toBe(negative);
  });

  it("종류를 영문 원문으로 찍지 않는다", () => {
    for (const kind of KINDS) {
      const summary = assertionSummary({ kind, match: "equals", value: "x" });
      expect(summary).not.toContain(kind);
    }
  });

  it("값을 쓰지 않는 종류는 종류 이름만으로 읽힌다", () => {
    expect(assertionSummary({ kind: "disabled", match: "equals" })).toBe(
      ASSERTION_KIND_LABEL.disabled,
    );
  });
});

describe("어휘가 빠짐없이 있다", () => {
  it("여섯 종류 모두 이름과 설명을 갖는다", () => {
    for (const kind of KINDS) {
      expect(ASSERTION_KIND_LABEL[kind]?.length ?? 0).toBeGreaterThan(0);
      expect(ASSERTION_KIND_HINT[kind]?.length ?? 0).toBeGreaterThan(0);
    }
  });

  it("네 비교 방식 모두 이름을 갖는다", () => {
    for (const match of MATCHES) {
      expect(MATCH_MODE_LABEL[match]?.length ?? 0).toBeGreaterThan(0);
    }
  });

  it("상태 검증의 설명이 hidden 과 갈리는 지점을 말한다", () => {
    // 대상이 없을 때의 동작이 다르다는 것을 고르는 자리에서 알아야 한다.
    expect(ASSERTION_KIND_HINT.disabled).toContain("대상이 없으면 실패");
    expect(ASSERTION_KIND_HINT.hidden).toContain("모두 통과");
  });
});

describe("판단 함수", () => {
  it("부정 비교 둘만 부정으로 센다", () => {
    expect(MATCHES.filter(isNegatedMatch)).toEqual(["not_equals", "not_contains"]);
  });

  it("값을 비교하는 종류는 텍스트와 주소뿐이다", () => {
    expect(KINDS.filter(comparesValue)).toEqual(["text", "url"]);
  });
});

describe("부정 비교의 안내 (FR-026)", () => {
  it("제한 시간이 관찰 기간이라는 뜻을 말한다", () => {
    expect(NEGATED_MATCH_NOTE).toContain("유지되는지");
    expect(NEGATED_MATCH_NOTE).toContain("제한 시간을 모두");
  });

  it("기간 뒤에 나타나는 것은 잡지 못한다고 말한다", () => {
    // 알려진 한계를 말하지 않는 것은 거짓 통과를 제품이 보증하는 것과 같다.
    expect(NEGATED_MATCH_NOTE).toContain("잡지 못하므로");
  });

  it("경고가 아니라 조언으로 읽힌다", () => {
    // 「하지 마세요」가 아니라 「~하면 좋습니다」다. 정당한 사용을 막지 않는다.
    expect(NEGATED_MATCH_NOTE).toContain("좋습니다");
    expect(NEGATED_MATCH_NOTE).not.toContain("마세요");
  });
});
