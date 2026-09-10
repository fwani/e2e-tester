/**
 * 가드 — **초점 링을 지우지 않는다.** 015 T068 (SC-008 · FR-009).
 *
 * ## 왜 자동으로 막아야 하나
 *
 * 정본에 전역 규칙이 있고 주석이 그 이유를 적었다 — 「초점 링을 지우지 않는다.
 * 키보드로 도는 도구다」.
 *
 *     :focus-visible { outline: 2px solid var(--run); outline-offset: 2px; }
 *
 * 015 가 정본을 `layer(base)` 로 내렸으므로 이 규칙도 base 에 있다. 부품이나 화면에
 * `outline-none` 계열 유틸리티가 **하나만 들어가도** 그 요소의 초점 링이 사라진다.
 *
 * **이 회귀는 눈으로 잡히지 않는다.** 마우스로 쓰면 아무 차이가 없고, 스크린샷도 같고,
 * 기존 테스트도 통과한다. Tab 키를 눌러야만 보인다 — 그리고 그때 보는 사람은 이미
 * 키보드로만 조작하는 사용자다.
 *
 * SC-008 이 「초점 표시가 사라진 요소 0건」을 요구하고, 이 검사가 그것을 지킨다.
 *
 * ## 정당한 예외는 있다
 *
 * `input.phase-name:focus { outline: none }` 은 의도된 것이다 — 테두리 색으로 초점을
 * 표시하므로 링이 겹치면 지저분하다. 그런 경우는 `theme/exceptions.ts` 에 **이유와 함께**
 * 등록한다. 등록되지 않은 이탈은 존재할 수 없다 (008 C-11~C-14 를 승계).
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { VISUAL_LANGUAGE_EXCEPTIONS } from "../src/theme/exceptions";
import tokensCss from "../src/theme/tokens.css?raw";

import { classNameGroups, withoutComments } from "./helpers/tailwind";

const ROOT = join(__dirname, "..");

/**
 * 초점 링을 지우는 표기.
 *
 * Tailwind 의 `outline-none`·`focus:outline-none`·`focus-visible:outline-none`, 그리고
 * 임의값으로 같은 일을 하는 `outline-0` 을 함께 본다. 표기를 바꿔 빠져나갈 수 없어야
 * 한다 — 008 이 색 리터럴에서 겪은 교훈이다.
 */
const KILLS_RING = /^(?:[a-z-]+:)*outline-(?:none|0)$/;

/** 등록된 예외인가. 디렉터리를 가리키는 등록도 받는다. */
function excused(rel: string, what: string): boolean {
  return VISUAL_LANGUAGE_EXCEPTIONS.some(
    (e) => `frontend/${rel}`.startsWith(e.file) && new RegExp(e.pattern).test(what),
  );
}

/**
 * 초점 링을 지우는 곳 — 클래스와 인라인 둘 다 본다.
 *
 * **클래스 쪽은 공용 스캐너를 쓴다.** 1회차에 자체 스캐너로 `className=` 만 봤고,
 * 그래서 `ui/Button` 의 `BASE` 상수에 심은 `focus:outline-none` 을 놓쳤다 — 015 는
 * 클래스를 부품 상수로 옮기는 작업이므로, 그곳을 못 보는 가드는 정작 봐야 할 곳을
 * 비워 둔 것이다.
 */
function ringKillers(): string[] {
  const out: string[] = [];
  for (const g of classNameGroups()) {
    for (const name of g.names) {
      if (KILLS_RING.test(name) && !excused(g.file, name)) out.push(`  ${g.file}:${g.line}  ${name}`);
    }
  }
  // 인라인으로 같은 일을 하는 경우 — 유틸리티만 막으면 우회로가 남는다.
  const files = execFileSync("find", ["src", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
    .trim()
    .split("\n");
  for (const rel of files) {
    const txt = withoutComments(readFileSync(join(ROOT, rel), "utf8"));
    for (const m of txt.matchAll(/outline\s*:\s*["']?\s*(none|0)\b/g)) {
      const what = `style outline:${m[1]}`;
      if (!excused(rel, "outline")) out.push(`  ${rel}:${txt.slice(0, m.index).split("\n").length}  ${what}`);
    }
  }
  return out;
}

describe("초점 링을 지우지 않는다 (SC-008)", () => {
  it("정본에 전역 `:focus-visible` 규칙이 살아 있다", () => {
    // 이 규칙이 사라지면 아래 검사가 통과해도 초점 링이 없다.
    // 「지우지 않았는가」를 보기 전에 「있는가」를 먼저 본다.
    expect(
      /:focus-visible\s*\{[^}]*outline\s*:\s*2px\s+solid\s+var\(--run\)/.test(tokensCss),
      "정본의 전역 :focus-visible 규칙이 사라졌다. 키보드로 도는 도구다 (정본 주석).",
    ).toBe(true);
  });

  it("화면 코드가 초점 링을 지우지 않는다", () => {
    const killers = ringKillers();
    expect(
      killers,
      "초점 링을 지우고 있다. 마우스로 쓰면 아무 차이가 없고 스크린샷도 같지만,\n" +
        "Tab 키로 도는 사용자는 자기가 어디에 있는지 알 수 없게 된다 (SC-008).\n" +
        "테두리 색 같은 다른 표시로 대체하는 것이 의도라면 `theme/exceptions.ts` 에\n" +
        "`axis: \"class-name\"` 과 **이유**를 함께 등록한다.\n" +
        killers.join("\n"),
    ).toEqual([]);
  });

  it("검사가 헛돌지 않는다 — 실제로 잡을 수 있다", () => {
    // 대상 파일을 하나도 읽지 못하면 위 검사가 빈 배열로 통과한다.
    const files = execFileSync("find", ["src", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
      .trim()
      .split("\n");
    expect(files.length, ".tsx 를 하나도 찾지 못했다").toBeGreaterThan(30);
    expect(KILLS_RING.test("focus:outline-none"), "패턴이 대표 표기를 잡지 못한다").toBe(true);
    expect(KILLS_RING.test("outline-0"), "패턴이 outline-0 을 잡지 못한다").toBe(true);
    expect(KILLS_RING.test("outline-hair"), "패턴이 정상 유틸리티를 잘못 잡는다").toBe(false);
    // 부품 상수까지 보는가 — 이 가드가 1회차에 놓친 자리다.
    expect(
      classNameGroups().some((g) => g.file.startsWith("src/ui/")),
      "부품 파일의 클래스 상수를 하나도 읽지 못했다",
    ).toBe(true);
  });
});
