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
 */
import { readFileSync } from "node:fs";
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

  it("정본 파일은 그대로 있다 — 뺀 것이지 지운 것이 아니다", () => {
    // 규칙을 **지우는** 것과 번들에서 **빼는** 것은 다르다. 정본은 확정 디자인의
    // 기록이자 L1 대조의 기준이므로 남아 있어야 한다.
    expect(canon, "정본에서 의미 클래스가 사라졌다").toMatch(/\.btn\s*\{/);
    expect(canon, "정본에서 의미 클래스가 사라졌다").toMatch(/\.chip\s*\{/);
  });
});
