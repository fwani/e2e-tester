/**
 * 가드 G-B — 코드가 쓰는 클래스가 **실제로 CSS 를 만드는가.** 015 T010.
 *
 * ## 왜 이 가드가 필요한가 — 인라인 시절에는 없던 실패
 *
 * `expect(panel.style.flex).toBe("0 0 460px")` 한 줄은 세 가지를 한꺼번에 봤다.
 * 배치 판단이 옳고, 값이 그 요소까지 갔고, **그 값이 실재한다는 것**.
 *
 * 클래스로 바꾸면 셋째가 사라진다. `expect(el).toHaveClass("basis-[460px]")` 는
 * **오타가 있어도 통과한다** — 클래스가 붙기만 하면 되고, Tailwind 가 그 이름으로 CSS 를
 * 만들었는지는 묻지 않기 때문이다. 화면은 스타일 없이 렌더되는데 검사는 초록이다.
 *
 * 이 가드가 그 구멍을 막는다 (contracts/layout-contract-v2.md LC-4 ③).
 *
 * ## 두 가지를 본다
 *
 * 1. **실재** — 코드의 정적 클래스가 Tailwind 산출 CSS 에 있는가. 오타를 잡는다.
 * 2. **조립 금지** — 클래스 이름을 문자열로 조립하는 곳이 없는가. Tailwind 는 소스를
 *    텍스트로 스캔하므로 `` `bg-${tone}` `` 을 찾지 못하고 CSS 를 만들지 않는다.
 *    **①만으로는 이 실패를 못 잡는다** — 조립된 문자열은 애초에 추출 대상에 없다.
 *
 * ## 이 가드를 만들며 네 번 헛돌 뻔했다
 *
 * 실효성 확인(일부러 어겨 보기)이 매번 잡아냈다. 기록해 둔다 — 같은 함정이다.
 *
 * 1. `className="…"` 만 봐서 `className={"…"}` 의 오타를 놓쳤다
 * 2. 파일 전체를 훑어 `id={`row-${n}`}` 를 조립으로 오인했다 (12건)
 * 3. `` `row${c ? " on" : ""}` `` 을 조립으로 오인했다 — 끼우는 값이 공백으로 시작하면 안전하다
 * 4. 삼항의 **비교값**(`x === "manipulation"`)을 삽입값으로 오인했다
 *
 * 가드가 자기 대상을 못 보면 통과는 아무 뜻이 없다. 그래서 「검사가 헛돌지 않는다」를
 * 매 검사마다 함께 둔다.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { classNameGroups, generatedClasses } from "./helpers/tailwind";

const ROOT = join(__dirname, "..");

/**
 * 클래스 이름을 문자열로 조립하는 곳. Tailwind 가 찾지 못하는 형태다.
 *
 *     className={`bg-${tone}`}              위반 — bg-warn 이 소스 어디에도 없다
 *     className={`btn ${extra}`}            정상 — 완성된 클래스를 끼운다
 *     className={`row${c ? " on" : ""}`}    정상 — 끼우는 값이 공백으로 시작
 *
 * 판정: `${…}` 의 **삽입 결과**가 될 문자열 리터럴이 전부 빈 문자열이거나 공백으로
 * 시작하면 안전. 리터럴이 하나도 없으면(순수 변수) 위험. 삼항이면 `?` 이후만 본다.
 */
function assembledClassNames(): string[] {
  const out: string[] = [];
  const files = execFileSync("find", ["src", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
    .trim()
    .split("\n");
  for (const rel of files) {
    const txt = readFileSync(join(ROOT, rel), "utf8");
    for (const m of txt.matchAll(/className=\{([^]*?)\}\s*(?:>|\n|[a-zA-Z-]+=)/g)) {
      const expr = m[1] as string;
      let risky = false;
      for (const ins of expr.matchAll(/[a-zA-Z0-9_-]\$\{([^]*?)\}/g)) {
        const raw = ins[1] as string;
        const q = raw.indexOf("?");
        const inner = q >= 0 ? raw.slice(q + 1) : raw;
        const literals = Array.from(inner.matchAll(/["'`]([^"'`]*)["'`]/g), (x) => x[1] as string);
        if (literals.length === 0) {
          risky = true;
          break;
        }
        if (literals.some((l) => l !== "" && !l.startsWith(" "))) {
          risky = true;
          break;
        }
      }
      if (!risky) continue;
      out.push(`  ${rel}:${txt.slice(0, m.index).split("\n").length}  ${expr.replace(/\s+/g, " ").slice(0, 90)}`);
    }
  }
  return out;
}

describe("G-B — 코드가 쓰는 클래스가 실제로 CSS 를 만든다", () => {
  const generated = generatedClasses();
  const groups = classNameGroups();

  it("Tailwind 산출물과 `className` 을 읽는다 (검사가 헛돌지 않는다)", () => {
    expect(generated.size, "Tailwind 산출 CSS 에서 클래스를 하나도 읽지 못했다").toBeGreaterThan(5);
    expect(groups.length, "className 을 하나도 읽지 못했다").toBeGreaterThan(50);
  });

  it("정적 클래스가 전부 실재한다 — Tailwind 산출물에 있는 것", () => {
    /*
      **정본 클래스를 더 이상 봐주지 않는다 (2026-09-11 · T075).**

      T075 가 정본의 클래스 규칙을 번들에서 뺐다 — 화면 코드가 쓰지 않으므로 아무도
      읽지 않는 12.5 kB 였다. 그 순간부터 `className="chip warn"` 은 **아무 CSS 도 만들지
      않는다.** 파일(`tokens.css`)에는 규칙이 남아 있으므로 `canon.has(name)` 은 참이고,
      이 검사는 통과했다 — **검사가 거짓말을 하고 있었다.**

      L2 대조(`scripts/design_compare_ba.py`)가 그 사실을 잡았다. 화면 여덟 개에서
      요소 열 몇 개가 통째로 무스타일이 됐고, 그중 하나는 「없음」 칩이었다.

      이제 **Tailwind 가 실제로 만든 것만** 실재로 본다. `generated` 는 앱과 같은
      입력(`theme/tailwind.css` → `tokens.app.css`)으로 물으므로 정본 클래스는 들어
      있지 않다. 정본 클래스가 남아 있으면 여기서 걸린다.
    */
    const missing = new Set<string>();
    for (const g of groups) {
      for (const name of g.names) {
        if (!generated.has(name)) missing.add(`  ${g.file}:${g.line}  .${name}`);
      }
    }
    const list = Array.from(missing).sort();
    expect(
      list,
      "이 클래스는 아무 CSS 도 만들지 않는다. 화면은 스타일 없이 렌더된다.\n" +
        "오타이거나, Tailwind 가 스캔하지 못한 이름이다 (LC-4 ③).\n" +
        list.join("\n"),
    ).toEqual([]);
  });

  it("클래스 이름을 문자열로 조립하지 않는다", () => {
    const assembled = assembledClassNames();
    expect(
      assembled,
      "클래스 이름을 조립하고 있다. Tailwind 는 소스를 텍스트로 스캔하므로 이런 이름을\n" +
        "찾지 못하고 CSS 를 만들지 않는다 — 화면이 조용히 무스타일이 된다.\n" +
        "조건마다 완성된 클래스 문자열을 쓰거나, 표(Record)로 빼서 전수를 드러낸다.\n" +
        assembled.join("\n"),
    ).toEqual([]);
  });
});
