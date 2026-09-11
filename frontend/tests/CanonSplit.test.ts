/**
 * 앱이 들이는 정본이 **낡지 않았고, 필요한 것만 담았는가.** 015 T075 (SC-007).
 *
 * ## 왜 이 검사가 필요한가
 *
 * `theme/tokens.app.css` 는 생성물이다 — `scripts/split-canon.mjs` 가 정본에서 뽑는다.
 * 생성물을 저장소에 두면 **원본이 바뀌어도 조용히 옛 값을 쓴다.** 정본의 색 하나를
 * 고치고 다시 뽑는 것을 잊으면, 화면은 옛 색으로 그려지는데 L1 대조는 정본을 읽으므로
 * 통과한다. 아무 검사도 실패하지 않는 회귀다.
 *
 * ## 무엇을 보는가
 *
 * 1. **낡지 않았는가** — 지금 정본으로 다시 뽑은 것과 글자 하나까지 같은가.
 * 2. **필요한 것이 다 있는가** — `:root` 변수와 요소 규칙. 이것이 빠지면 화면이 통째로
 *    무너지므로 대표적인 것들을 짚는다.
 * 3. **필요 없는 것이 없는가** — 의미 클래스 규칙이 하나도 없는가. 있으면 SC-007 이
 *    되돌아간 것이다.
 * 4. **앱이 실제로 그것을 들이는가** — `tailwind.css` 가 정본 전체를 도로 들이면
 *    위 셋이 다 통과해도 번들은 그대로다.
 * 5. **화면이 뺀 것을 아직 쓰지 않는가** ← 2026-09-11 에 추가됐다. 아래 참조.
 *
 * ## 2026-09-11 — 다섯째가 없어서 Step 목록이 통째로 무너졌다 (사용자 보고)
 *
 * 「테스트 스텝 리스트 뷰가 매우 깨졌다」.
 *
 * T075 가 의미 클래스 규칙 148개를 번들에서 뺀 근거는 「전환이 끝나 화면 코드가 의미
 * 클래스를 하나도 쓰지 않는다」였다. **그 전제를 재는 검사가 없었다.**
 * `components/workbench/StepList.tsx` 가 `className="srow pass sel"` 로 마지막까지
 * 쓰고 있었고, 그 클래스는 번들에 없으므로 **아무 규칙도 받지 못했다** — 행이
 * `display:block` 이 되어 52px 가 137px 로 늘고 체크칸은 452px 짜리 입력 상자가 됐다.
 *
 * 모든 검사가 초록이었다. 클래스 이름은 실제로 붙어 있었으므로
 * `classList.contains("srow")` 는 통과한다 — 015 가 `ui/Button` 에서 겪은 것과 같은
 * 형태의 사고다 (「`toHaveClass("bg-ink")` 는 통과했다. 클래스는 실제로 붙어 있었기
 * 때문이다」).
 *
 * 그래서 전제를 **매번 다시 잰다.** 번들에서 뺀 이름을 화면이 `className` 으로 쓰면
 * 여기서 걸린다.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { SOURCE, TARGET, splitCanon } from "../scripts/split-canon.mjs";

const ROOT = join(__dirname, "..");

describe("앱이 들이는 정본 (T075 · SC-007)", () => {
  const canon = readFileSync(SOURCE, "utf8");
  const app = readFileSync(TARGET, "utf8");

  it("낡지 않았다 — 지금 정본에서 다시 뽑은 것과 같다", () => {
    expect(
      app,
      "`tokens.app.css` 가 정본과 어긋난다. 정본이 바뀌었는데 다시 뽑지 않았다.\n" +
        "`node scripts/split-canon.mjs` 로 다시 뽑는다.\n" +
        "이 상태에서는 화면이 옛 값으로 그려지는데 L1 대조는 정본을 읽으므로 통과한다.",
    ).toBe(splitCanon(canon));
  });

  it("화면이 서려면 있어야 하는 것이 들어 있다", () => {
    // 변수가 없으면 Tailwind 테마가 통째로 빈다.
    expect(app, "정본 변수가 없다").toMatch(/--ink:\s*#14171C/);
    expect(app, "치수 토큰이 없다").toMatch(/--h-control:\s*32px/);
    // 요소 규칙 — 맨 `<button>` 과 입력칸의 모양이 여기서 온다.
    expect(app, "button 요소 규칙이 없다").toMatch(/\bbutton\s*\{/);
    expect(app, "입력칸 요소 규칙이 없다").toMatch(/input,\s*select,\s*textarea\s*\{/);
    // 초점 링 — 없으면 키보드 사용자가 자기 자리를 잃는다 (SC-008).
    expect(app, "전역 초점 링 규칙이 없다").toMatch(/:focus-visible\s*\{[^}]*outline/);
    // 리셋 — 정본이 preflight 대신 갖고 있는 것.
    expect(app, "box-sizing 리셋이 없다").toMatch(/\*,\*::before,\*::after\s*\{/);
  });

  it("의미 클래스 규칙이 하나도 없다 — 아무도 읽지 않는 것을 싣지 않는다", () => {
    const withClass: string[] = [];
    // **주석을 먼저 걷는다.** 머리주석에 `theme/tokens.css` 같은 점 찍힌 말이 있어
    // 선택자로 읽히고, 검사가 자기 설명문을 위반으로 보고했다.
    const body = splitCanon(canon).replace(/\/\*[\s\S]*?\*\//g, "");
    for (const m of body.matchAll(/([^{}]+)\{/g)) {
      const sel = (m[1] as string).trim();
      if (!sel.startsWith("@") && sel.includes(".")) withClass.push(sel);
    }
    expect(withClass, "앱이 들이는 정본에 의미 클래스 규칙이 남아 있다").toEqual([]);
  });

  it("`tailwind.css` 가 정본 전체가 아니라 이것을 들인다", () => {
    const theme = readFileSync(join(ROOT, "src/theme/tailwind.css"), "utf8");
    const imports = Array.from(theme.matchAll(/@import\s+"([^"]+)"/g), (m) => m[1] as string);
    expect(imports, "앱이 정본 전체를 도로 들이고 있다").not.toContain("./tokens.css");
    expect(imports, "앱이 뽑아낸 정본을 들이지 않는다").toContain("./tokens.app.css");
  });

  /**
   * 뺀 이름을 화면이 아직 쓰는가 (2026-09-11).
   *
   * ## 왜 `className` 만 보는가
   *
   * 정본 클래스 이름 중에는 `pass`·`fail`·`sm`·`off` 처럼 **뜻 어휘와 겹치는 것**이
   * 많다 (`tone="pass"`, `size="sm"`). 문자열 리터럴을 전부 훑으면 그것들이 전부
   * 위반으로 잡혀 검사가 소음이 된다.
   *
   * 실제 결함은 언제나 `className` 자리에서 난다 — 그 자리에 있는 이름만 브라우저가
   * 클래스로 읽기 때문이다. 그래서 거기만 본다. `VisualLanguage` 의 G-3 와 같은
   * 한계이자 같은 이유다.
   */
  it("화면이 번들에서 뺀 정본 클래스를 쓰지 않는다 — 그 자리는 아무 형태도 받지 못한다", () => {
    const classNames = (css: string) =>
      new Set(Array.from(css.matchAll(/\.([a-zA-Z][\w-]*)/g), (m) => m[1] as string));
    const dropped = classNames(canon);
    for (const kept of classNames(app)) dropped.delete(kept);

    const files: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const full = join(dir, name);
        if (statSync(full).isDirectory()) walk(full);
        else if (full.endsWith(".tsx")) files.push(full);
      }
    };
    walk(join(ROOT, "src"));

    const found: string[] = [];
    for (const file of files) {
      const text = readFileSync(file, "utf8");
      /*
        **주석을 먼저 걷는다.** 이 저장소의 주석은 옛 코드를 그대로 인용한다 —
        `className="srow pass sel"` 가 사고 기록으로 남아 있고, 그것을 위반으로
        보고하면 검사가 자기 설명문을 가리키게 된다 (`CanonSplit` 의 다른 검사도
        같은 이유로 주석을 걷는다).
      */
      const code = text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
      // `className="…"` · `className={"…"}` · `className={`…`}` 세 형태.
      for (const m of code.matchAll(/className=(?:"([^"\n]*)"|\{"([^"\n]*)"\}|\{`([^`]*)`\})/g)) {
        /*
          `${…}` 는 **식이지 클래스 이름이 아니다.** 통째로 버린다 —
          `${busy || disabled ? …}` 의 `disabled` 가 정본 `.disabled` 로 읽히면
          검사가 소음이 된다. `VisualLanguage` 의 G-3 가 적은 것과 같은 한계다.
        */
        const value = ((m[1] ?? m[2] ?? m[3]) as string).replace(/\$\{[^}]*\}/g, " ");
        for (const token of value.split(/\s+/)) {
          if (dropped.has(token)) {
            const line = code.slice(0, m.index).split("\n").length;
            found.push(`${file.slice(ROOT.length + 1)}:${line}  .${token}`);
          }
        }
      }
    }

    expect(
      Array.from(new Set(found)),
      "화면이 번들에 없는 정본 클래스를 쓰고 있다.\n" +
        "그 자리는 **아무 규칙도 받지 못한다** — 화면은 스타일이 빠진 채 그려지고 검사는 초록이다.\n" +
        "`ui/` 의 부품이나 유틸리티로 옮긴다 (2026-09-11 Step 목록이 이렇게 무너졌다).",
    ).toEqual([]);
  });

  it("정본 파일은 그대로 있다 — 뺀 것이지 지운 것이 아니다", () => {
    // 규칙을 **지우는** 것과 번들에서 **빼는** 것은 다르다. 정본은 확정 디자인의
    // 기록이자 L1 대조의 기준이므로 남아 있어야 한다.
    expect(canon, "정본에서 의미 클래스가 사라졌다").toMatch(/\.btn\s*\{/);
    expect(canon, "정본에서 의미 클래스가 사라졌다").toMatch(/\.chip\s*\{/);
  });
});
