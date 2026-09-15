/**
 * 가드 G-G — 부품 밖의 **원시 조작 요소**를 센다. 017 T015 (contracts/guards.md G-G · FR-002 · FR-030).
 *
 * ## 무엇이 문제인가
 *
 * 017 전에는 화면 코드가 원시 `<button>` 50 · `<input>` 50 · `<select>` 4 · `<textarea>` 5 를 직접
 * 썼다. 그 자리들은 전역 요소 규칙(`button{}`·`input,select,textarea{width:100%;min-height:32px}`)에
 * 모양을 맡기거나 화면마다 유틸리티를 따로 조립했다. 결과가 전환 전 실측의 깨짐이다 —
 * 선택칸이 남은 폭 전체로 늘어나고(B-07), 같은 표의 체크박스 크기가 달랐다(B-08).
 *
 * 부품이 크기를 **명시**하면 번짐이 끊긴다. 그러려면 화면이 부품을 써야 하고, 이 가드가 그것을 센다.
 *
 * ## 줄어드는 예산
 *
 * 전환 중에는 원시 요소가 남아 있는 것이 정상이다. 그래서 빨갛게 두는 대신 **`REMAINING_BUDGET`**
 * 을 두고 화면을 옮길 때마다 내린다 (`ImplementationCount` 와 같은 규율).
 *
 * - 센 수 > 예산 → 실패. **새 원시 요소가 들어왔다.**
 * - 센 수 < 예산 → 실패. **예산을 내려라.** 예산이 커밋 이력에 남아 어느 단계에서 몇 개가 줄었는지 보인다.
 * - 완료 조건: 예산 = 0 (등록된 예외는 세지 않는다 — SC-005).
 *
 * ## 정당한 예외
 *
 * 부품이 될 수 없는 자리는 `theme/exceptions.ts` 에 `raw-element` 축으로 이유와 함께 등록한다.
 * 지금은 하나다 — 미러의 한글 조합 칸.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { VISUAL_LANGUAGE_EXCEPTIONS, isRegistered } from "../src/theme/exceptions";

import { withoutComments } from "./helpers/tailwind";

const ROOT = join(__dirname, "..");

/**
 * 남은 원시 조작 요소 수 — **화면을 옮길 때마다 같은 커밋에서 내린다.**
 *
 * 017 Foundational 기준값 **108** (2026-09-15) — `<button>` 50 · `<input>` 50 · `<select>` 4 ·
 * `<textarea>` 4 (미러 IME 칸은 등록된 예외라 세지 않는다). 병렬로 진행한 커밋을 합칠 때는 줄어든
 * 수를 **합산해서** 내린다.
 *
 * | 단계 | 줄어든 것 | 남은 예산 |
 * |---|---|---|
 * | Foundational | — | 108 |
 * | T026 `navLinkClasses` 26곳 → `Button variant="nav"` | `<button>` −26 | 82 |
 */
const REMAINING_BUDGET = 82;

const RAW = /<(button|input|select|textarea)\b/g;

interface Hit {
  readonly file: string;
  readonly line: number;
  readonly tag: string;
}

/** `//` 로 시작하는 줄을 지운다 (줄 번호는 보존한다). 블록 주석은 `withoutComments` 가 지운다. */
function withoutLineComments(text: string): string {
  return text.replace(/^[ \t]*\/\/.*$/gm, (m) => m.replace(/[^\n]/g, " "));
}

function rawHits(): Hit[] {
  const files = execFileSync("find", ["src", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
    .trim()
    .split("\n")
    .filter((f) => f !== "" && !f.startsWith("src/ui/"));
  const out: Hit[] = [];
  for (const file of files) {
    const txt = withoutLineComments(withoutComments(readFileSync(join(ROOT, file), "utf8")));
    for (const m of txt.matchAll(RAW)) {
      out.push({ file, line: txt.slice(0, m.index).split("\n").length, tag: m[1] as string });
    }
  }
  return out;
}

const EXCEPTIONS = VISUAL_LANGUAGE_EXCEPTIONS.filter((e) => e.axis === "raw-element");

function excusedBy(hit: Hit) {
  return EXCEPTIONS.find((e) => `frontend/${hit.file}`.startsWith(e.file) && new RegExp(e.pattern).test(hit.tag));
}

describe("G-G — 부품 밖의 원시 조작 요소 (017)", () => {
  const hits = rawHits();
  const unexcused = hits.filter((h) => excusedBy(h) === undefined);

  it("검사가 헛돌지 않는다 — 화면 코드를 읽고 등록된 예외를 찾는다", () => {
    expect(hits.length, "원시 요소를 하나도 찾지 못했다 — 예외로 등록한 자리조차 보이지 않는다").toBeGreaterThan(0);
    expect(EXCEPTIONS.every(isRegistered), "사유 없는 raw-element 등록이 있다").toBe(true);
  });

  it("남은 원시 조작 요소가 예산과 같다 (늘면 새로 들어온 것 · 줄면 예산을 내려라)", () => {
    const byTag = unexcused.reduce<Record<string, number>>((acc, h) => ({ ...acc, [h.tag]: (acc[h.tag] ?? 0) + 1 }), {});
    const list = unexcused.map((h) => `  ${h.file}:${h.line}  <${h.tag}>`).join("\n");
    const advice =
      unexcused.length > REMAINING_BUDGET
        ? `원시 조작 요소가 예산보다 ${unexcused.length - REMAINING_BUDGET}개 많다 — 새로 들어온 자리를 부품으로 바꾼다.\n` +
          "부품이 될 수 없는 자리라면 theme/exceptions.ts 에 raw-element 축으로 이유와 함께 등록한다."
        : `원시 조작 요소가 예산보다 ${REMAINING_BUDGET - unexcused.length}개 적다 — REMAINING_BUDGET 을 ${unexcused.length} 로 내린다.`;
    expect(unexcused.length, `${advice}\n태그별 ${JSON.stringify(byTag)}\n${list}`).toBe(REMAINING_BUDGET);
  });

  it("죽은 예외가 없다 — 등록됐는데 그 자리에 원시 요소가 없는 항목", () => {
    const dead = EXCEPTIONS.filter((e) => !hits.some((h) => excusedBy(h) === e));
    expect(dead.map((e) => `${e.file} (${e.pattern})`), "등록부에서 지운다 (G-6 과 같은 규율)").toEqual([]);
  });
});
