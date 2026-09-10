/**
 * 가드 G-A1 — Tailwind 테마에 **값이 없는가.** 015 T009.
 *
 * `theme/tailwind.css` 는 정본 토큰에 이름만 다시 붙이는 파일이다. 오른쪽은 전부
 * `var(정본토큰)` 이어야 하고, 리터럴 값이 하나라도 들어오면 정본이 둘이 된다
 * (FR-001·FR-016 · contracts/tailwind-theme.md C-1).
 *
 * ## 왜 이 검사가 규칙보다 강한가
 *
 * 값이 없으면 정본과 **어긋날 수가 없다.** 「정본을 복제하지 말자」는 규칙은 지켜야
 * 하는 것이지만, 「이 파일에 값이 없다」는 검사할 수 있는 것이다. 008 이 값 리터럴
 * 338개를 겪은 뒤 배운 것이 이 차이다.
 */
import { describe, expect, it } from "vitest";

// `?raw` 로 원문을 읽는다 — 이 저장소의 방식이다 (`CanonMatchesDesign.test.ts` 와 같다).
// `vite.config.ts` 가 `css: true` 로 두었으므로 CSS 도 원문 그대로 온다 (DC-004).
import tailwindCss from "../src/theme/tailwind.css?raw";
import tokensCss from "../src/theme/tokens.css?raw";

/** 주석을 지운 원문. 주석 안의 예시(`--color-pass: #1A7F45` 같은 반례)에 걸리면 안 된다. */
function withoutComments(css: string): string {
  return css.replace(/\/\*[\s\S]*?\*\//g, "");
}

/** `@theme` 블록 안의 선언만. 바깥의 `@import`·`@layer` 는 대상이 아니다. */
function themeDeclarations(css: string): { name: string; value: string; line: number }[] {
  const out: { name: string; value: string; line: number }[] = [];
  const start = css.indexOf("@theme");
  if (start < 0) return out;
  let depth = 0;
  let end = start;
  for (let i = css.indexOf("{", start); i < css.length; i += 1) {
    if (css[i] === "{") depth += 1;
    else if (css[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  const block = css.slice(start, end);
  const before = css.slice(0, start).split("\n").length;
  block.split("\n").forEach((raw, i) => {
    const m = /^\s*(--[a-zA-Z0-9_*-]+)\s*:\s*([^;]+);/.exec(raw);
    if (m !== null) out.push({ name: m[1] as string, value: (m[2] as string).trim(), line: before + i });
  });
  return out;
}

/**
 * 값으로 인정하지 않는 것 — 참조가 아닌 모든 것.
 *
 * `initial` 은 값이 아니라 **지우기**다 (`--color-*: initial` 로 Tailwind 기본 팔레트를
 * 비운다). CSS 키워드(`transparent`·`currentColor`·`inherit`)도 정본이 정할 성질의 것이
 * 아니므로 허용한다 — 색이 아니라 「색을 쓰지 않음」의 표현이다.
 */
const ALLOWED_LITERALS = new Set(["initial", "transparent", "currentColor", "inherit"]);

describe("G-A1 — Tailwind 테마에는 값이 없다", () => {
  const css = withoutComments(tailwindCss);
  const decls = themeDeclarations(css);

  it("`@theme` 블록에서 선언을 읽는다 (검사가 헛돌지 않는다)", () => {
    // 파일 구조가 바뀌어 파싱이 0건을 내면 이 검사는 아무것도 막지 못한다.
    // 그 조용한 실패를 여기서 잡는다.
    expect(decls.length, "@theme 블록에서 선언을 하나도 읽지 못했다 — 파서가 깨졌다").toBeGreaterThan(20);
  });

  it("모든 선언의 오른쪽이 `var(정본토큰)` 이거나 허용 키워드다", () => {
    const violations = decls
      .filter((d) => !ALLOWED_LITERALS.has(d.value) && !/^var\(--[a-zA-Z0-9_-]+\)$/.test(d.value))
      .map((d) => `  theme/tailwind.css:${d.line}  ${d.name}: ${d.value}`);

    expect(
      violations,
      "Tailwind 테마에 값이 적혔다. 정본이 둘이 된다 (FR-001 · C-1).\n" +
        "오른쪽은 var(정본토큰) 이어야 한다. 정본에 없는 값이 필요하면 그것은\n" +
        "정본에 넣을 값인지 먼저 판단할 일이다 (FR-003).\n" +
        violations.join("\n"),
    ).toEqual([]);
  });

  it("참조하는 정본 토큰이 실제로 `tokens.css` 에 있다", () => {
    const tokens = tokensCss;
    const defined = new Set(Array.from(tokens.matchAll(/(--[a-zA-Z0-9_-]+)\s*:/g), (m) => m[1]));
    const dangling = decls
      .filter((d) => /^var\(--[a-zA-Z0-9_-]+\)$/.test(d.value))
      .map((d) => ({ d, ref: d.value.slice(4, -1) }))
      .filter(({ ref }) => !defined.has(ref))
      .map(({ d, ref }) => `  ${d.name} → ${ref} (정본에 없다)`);

    // 오타로 없는 토큰을 가리키면 유틸리티가 조용히 아무 값도 내지 않는다.
    // 「값이 없다」만 검사하면 이 실패를 놓친다.
    expect(dangling, "정본에 없는 토큰을 참조한다:\n" + dangling.join("\n")).toEqual([]);
  });
});
