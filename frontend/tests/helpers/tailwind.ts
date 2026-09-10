/**
 * Tailwind 산출물 조회 — 가드 G-B·G-C·초점 링이 공유한다. 015.
 *
 * 「이 이름이 Tailwind 유틸리티인가」를 **형태로 판정하지 않는다.** 어간 목록으로 갈랐다가
 * 정본 클래스 `.grid-head` 를 `grid-*` 유틸리티로 잘못 봤다. 이름 규칙은 우리가 정하는
 * 것이 아니므로 추측할 수 없다 — **Tailwind 가 실제로 무엇을 만들었는지 물어보는
 * 수밖에 없다.**
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(__dirname, "..", "..");

let cache: Set<string> | null = null;
let utilCache: Set<string> | null = null;

/**
 * Tailwind CLI 를 한 번 돌려 산출 CSS 의 클래스 이름을 모은다.
 *
 * 임시 파일은 **프로젝트 안에** 만든다 — 시스템 임시 디렉터리에는 `tailwindcss/…` 를
 * 해석할 `node_modules` 가 없다. 실측 ~1.2초 (Tailwind 자체는 54ms).
 */
function runTailwind(inputCss: string): Set<string> {
  const dir = mkdtempSync(join(ROOT, ".tw-probe-"));
  try {
    const input = join(dir, "in.css");
    const output = join(dir, "out.css");
    writeFileSync(input, inputCss);
    execFileSync("npx", ["@tailwindcss/cli", "-i", input, "-o", output, "--content", "./src/**/*.tsx"], {
      cwd: ROOT,
      stdio: "pipe",
    });
    const css = readFileSync(output, "utf8");
    const out = new Set<string>();
    // 이스케이프된 형태(`.basis-\[460px\]`)를 원래 이름으로 되돌린다.
    for (const m of css.matchAll(/\.((?:\\.|[a-zA-Z0-9_-])+)(?=[\s,{:>~+])/g)) {
      out.add((m[1] as string).replace(/\\(.)/g, "$1"));
    }
    return out;
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

/**
 * 현재 소스가 만들어 내는 클래스 전부.
 *
 * **실제 앱과 같은 입력을 쓴다.** tailwindcss 의 theme·utilities 만 넣고 물었다가
 * 우리 `@theme inline` 이 만드는 유틸리티(`bg-panel`·`px-s3`·`rounded-base`)를
 * 「실재하지 않는다」고 판정했다. 테마를 빼고 물으면 답이 틀린다.
 */
export function generatedClasses(): Set<string> {
  if (cache !== null) return cache;
  cache = runTailwind(`@import "../src/theme/tailwind.css";\n`);
  return cache;
}

/**
 * **정본을 뺀** 산출물 — Tailwind 가 만드는 것만.
 *
 * 이름 충돌(계약 C-7)을 보려면 「Tailwind 가 만든 것」과 「정본이 정의한 것」이 갈려야
 * 한다. `generatedClasses()` 는 실제 테마를 쓰므로 정본 클래스까지 포함하며, 그것으로
 * 충돌을 물으면 **정본 클래스 전부가 충돌로 나온다.**
 *
 * 정본에서 CSS 변수 선언만 남기고(변수가 없으면 `@theme inline` 이 깨진다) 클래스 규칙을
 * 걷어낸 입력으로 다시 돌린다.
 */
export function utilityOnlyClasses(): Set<string> {
  if (utilCache !== null) return utilCache;
  const theme = readFileSync(join(ROOT, "src/theme/tailwind.css"), "utf8").replace(
    /@import\s+"\.\/tokens\.css"[^;]*;/,
    "",
  );
  // `:root { … }` 블록만 통째로 뽑는다. 줄 단위로 거르면 중괄호가 짝을 잃어
  // Tailwind 가 CssSyntaxError 로 멈춘다 (1회차에 겪었다).
  const tokens = readFileSync(join(ROOT, "src/theme/tokens.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const vars = Array.from(tokens.matchAll(/:root\s*\{[^}]*\}/g), (m) => m[0]).join("\n");
  utilCache = runTailwind(`${theme}\n${vars}\n`);
  return utilCache;
}

/** 정본(`tokens.css`)이 정의하는 의미 클래스 전부.
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

/** 주석을 지운 원문 (줄 번호는 보존한다). 주석 안의 예시가 검사 대상이 되면 안 된다. */
export function withoutComments(t: string): string {
  return t.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "));
}

/**
 * `.tsx` 가 실제로 화면에 붙이는 클래스 덩어리.
 *
 * ## `className=` 만 보면 부품을 놓친다
 *
 * 1회차는 `className="…"`·`{"…"}`·템플릿 세 표기를 봤다. 그것으로는 **부품 파일의 클래스
 * 상수를 보지 못한다.**
 *
 *     const BASE = "inline-flex items-center gap-[6px] …";   // ui/Button.tsx
 *     const VARIANT: Record<…, string> = { primary: "bg-ink …" };
 *
 * 015 는 의미 클래스를 부품으로 해체하므로 **앞으로 클래스의 대부분이 여기에 산다.**
 * 그것을 못 보는 가드는 정작 봐야 할 곳을 비워 둔 것이다 — T068 에서 `focus:outline-none`
 * 을 `ui/Button` 의 BASE 에 심었는데 초점 링 가드가 통과했다.
 *
 * 그래서 클래스 상수도 본다. 다만 문자열 리터럴을 **전부** 훑으면 SVG path
 * (`"M4 4l4-4M9…"`)까지 클래스로 오인하므로(1회차에 5건), 클래스 문법에 맞는 토큰만
 * 있고 그중 하나 이상이 알려진 클래스인 리터럴로 좁힌다.
 */
export function classNameGroups(): { names: string[]; file: string; line: number }[] {
  const out: { names: string[]; file: string; line: number }[] = [];
  const known = new Set([...canonClasses(), ...generatedClasses()]);
  const files = execFileSync("find", ["src", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
    .trim()
    .split("\n");
  const looksLikeClassList = (blob: string): boolean => {
    const names = blob.split(/\s+/).filter(Boolean);
    // **토큰 2개 이상**만 본다. 단일 토큰은 prop 값일 때가 많다 —
    // `variant="primary"` 의 `"primary"` 가 정본 클래스 이름과 같아서 오인됐다.
    //
    // 한계: 클래스 하나만 담은 상수는 여기서 놓친다. 그런 상수는 드물고(부품 상수는
    // 대개 여러 클래스를 잇는다), prop 값을 클래스로 오인하는 쪽이 더 자주 틀린다.
    if (names.length < 2) return false;
    if (!names.every((n) => /^[a-zA-Z][a-zA-Z0-9_:./[\]#%!-]*$/.test(n))) return false;
    return names.some((n) => known.has(n));
  };
  for (const rel of files) {
    const txt = withoutComments(readFileSync(join(ROOT, rel), "utf8"));
    const seen = new Set<number>();
    const add = (blob: string, index: number): void => {
      const names = blob.split(/\s+/).filter(Boolean);
      if (names.length > 0 && !seen.has(index)) {
        seen.add(index);
        out.push({ names, file: rel, line: txt.slice(0, index).split("\n").length });
      }
    };
    // ① className= 문맥 — 확실한 것부터
    for (const m of txt.matchAll(/className="([^"]*)"/g)) add(m[1] as string, m.index ?? 0);
    for (const m of txt.matchAll(/className=\{\s*"([^"]*)"\s*\}/g)) add(m[1] as string, m.index ?? 0);
    for (const m of txt.matchAll(/className=\{\s*`([^]*?)`/g)) {
      add(stripHoles(m[1] as string).replace(/`/g, " "), m.index ?? 0);
    }
    // ② 부품의 클래스 상수
    for (const m of txt.matchAll(/"([^"\n]{2,})"|`([^`\n]{2,})`/g)) {
      const blob = stripHoles((m[1] ?? m[2] ?? "") as string).replace(/`/g, " ");
      if (looksLikeClassList(blob)) add(blob, m.index ?? 0);
    }
  }
  return out;
}
