/**
 * Tailwind 산출물 조회 — 가드 G-B·G-C 가 공유한다. 015.
 *
 * 「이 이름이 Tailwind 유틸리티인가」를 **형태로 판정하지 않는다.** 1회차에 어간 목록으로
 * 갈랐다가 `.grid-head`(정본 클래스)를 `grid-*` 유틸리티로 잘못 봤다. 이름 규칙은
 * 우리가 정하는 것이 아니므로 추측할 수 없다 — **Tailwind 가 실제로 무엇을 만들었는지
 * 물어보는 수밖에 없다.**
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(__dirname, "..", "..");

let cache: Set<string> | null = null;

/**
 * 현재 소스를 대상으로 Tailwind 를 한 번 돌려 산출 CSS 에 들어간 클래스 이름을 모은다.
 *
 * 한 테스트 실행 안에서 한 번만 돈다 (실측 ~1.2초, Tailwind 자체는 54ms).
 * 임시 파일은 **프로젝트 안에** 만든다 — 시스템 임시 디렉터리에는 `tailwindcss/…` 를
 * 해석할 `node_modules` 가 없다.
 */
export function generatedClasses(): Set<string> {
  if (cache !== null) return cache;
  const dir = mkdtempSync(join(ROOT, ".tw-probe-"));
  try {
    const input = join(dir, "in.css");
    const output = join(dir, "out.css");
    writeFileSync(input, `@import "tailwindcss/theme.css";\n@import "tailwindcss/utilities.css";\n`);
    execFileSync("npx", ["@tailwindcss/cli", "-i", input, "-o", output, "--content", "./src/**/*.tsx"], {
      cwd: ROOT,
      stdio: "pipe",
    });
    const css = readFileSync(output, "utf8");
    const out = new Set<string>();
    for (const m of css.matchAll(/\.((?:\\.|[a-zA-Z0-9_-])+)(?=[\s,{:>~+])/g)) {
      out.add((m[1] as string).replace(/\\(.)/g, "$1"));
    }
    cache = out;
    return out;
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

/**
 * 정본(`tokens.css`)이 정의하는 의미 클래스 전부.
 *
 * **전환이 끝나도 비지 않는다.** 정본 구획(자동 추출)의 클래스는 확정 디자인의 기록이자
 * L1 대조의 기준이므로 남는다 — 사라지는 것은 *화면 코드의 사용*이다
 * (contracts/class-migration.md 「완료」의 정의).
 */
export function canonClasses(): Set<string> {
  const css = readFileSync(join(ROOT, "src/theme/tokens.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const out = new Set<string>();
  for (const m of css.matchAll(/([^{}]+)\{/g)) {
    const sel = m[1] as string;
    if (sel.trim().startsWith("@")) continue;
    for (const c of sel.matchAll(/\.([a-zA-Z][a-zA-Z0-9_-]*)/g)) out.add(c[1] as string);
  }
  return out;
}

/** `${…}` 를 공백으로 지운다. 중괄호 깊이를 세므로 중첩 템플릿 리터럴에서도 끊기지 않는다. */
export function stripHoles(t: string): string {
  let acc = "";
  for (let i = 0; i < t.length; i += 1) {
    if (t[i] === "$" && t[i + 1] === "{") {
      let depth = 1;
      i += 2;
      while (i < t.length && depth > 0) {
        if (t[i] === "{") depth += 1;
        else if (t[i] === "}") depth -= 1;
        i += 1;
      }
      i -= 1;
      acc += " ";
    } else acc += t[i];
  }
  return acc;
}

/** `.tsx` 의 `className` 한 덩어리. 세 표기(`"…"` · `{"…"}` · 템플릿)를 모두 본다. */
export function classNameGroups(): { names: string[]; file: string; line: number }[] {
  const out: { names: string[]; file: string; line: number }[] = [];
  const files = execFileSync("find", ["src", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
    .trim()
    .split("\n");
  for (const rel of files) {
    const txt = readFileSync(join(ROOT, rel), "utf8");
    const add = (blob: string, index: number): void => {
      const names = blob.split(/\s+/).filter(Boolean);
      if (names.length > 0) out.push({ names, file: rel, line: txt.slice(0, index).split("\n").length });
    };
    for (const m of txt.matchAll(/className="([^"]*)"/g)) add(m[1] as string, m.index ?? 0);
    for (const m of txt.matchAll(/className=\{\s*"([^"]*)"\s*\}/g)) add(m[1] as string, m.index ?? 0);
    for (const m of txt.matchAll(/className=\{\s*`([^]*?)`/g)) {
      add(stripHoles(m[1] as string).replace(/`/g, " "), m.index ?? 0);
    }
  }
  return out;
}

/**
 * 손으로 쓴 파생 구획(정본 구획 뒤)에서 정의된 클래스.
 *
 * 정본 구획은 `scripts/extract_canon.py` 의 출력이라 손댈 수 없다. 파생 구획은 다르다 —
 * 화면이 쓰지 않으면 남길 이유가 없으므로 **여기 것은 삭제가 「완료」다.**
 */
export function derivedClasses(): Set<string> {
  const raw = readFileSync(join(ROOT, "src/theme/tokens.css"), "utf8");
  const marker = raw.indexOf("정본에서 파생된 것");
  const css = (marker < 0 ? raw : raw.slice(marker)).replace(/\/\*[\s\S]*?\*\//g, "");
  const out = new Set<string>();
  for (const m of css.matchAll(/([^{}]+)\{/g)) {
    const sel = m[1] as string;
    if (sel.trim().startsWith("@")) continue;
    for (const c of sel.matchAll(/\.([a-zA-Z][a-zA-Z0-9_-]*)/g)) out.add(c[1] as string);
  }
  return out;
}
