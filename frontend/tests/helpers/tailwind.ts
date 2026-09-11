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
function runTailwindRaw(inputCss: string): string {
  const dir = mkdtempSync(join(ROOT, ".tw-probe-"));
  try {
    const input = join(dir, "in.css");
    const output = join(dir, "out.css");
    writeFileSync(input, inputCss);
    execFileSync("npx", ["@tailwindcss/cli", "-i", input, "-o", output, "--content", "./src/**/*.tsx"], {
      cwd: ROOT,
      stdio: "pipe",
    });
    return readFileSync(output, "utf8");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function runTailwind(inputCss: string): Set<string> {
  {
    const css = runTailwindRaw(inputCss);
    const out = new Set<string>();
    // 이스케이프된 형태(`.basis-\[460px\]`)를 원래 이름으로 되돌린다.
    for (const m of css.matchAll(/\.((?:\\.|[a-zA-Z0-9_-])+)(?=[\s,{:>~+])/g)) {
      out.add((m[1] as string).replace(/\\(.)/g, "$1"));
    }
    return out;
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

/* ────────────────────────────────────────────────────────────────────────────
 * 가드 G-E 가 쓰는 것 — 「한 요소에 같은 속성이 두 번」을 보려면 두 가지가 더 필요하다.
 * (1) 각 유틸리티가 **어떤 속성을 선언하는가**, (2) 산출 CSS 에서 **누가 뒤에 오는가**.
 * ──────────────────────────────────────────────────────────────────────────── */

/** 한 유틸리티 클래스가 선언하는 속성과 산출 CSS 에서의 위치. */
export interface UtilityDecl {
  readonly props: ReadonlySet<string>;
  /** 산출 CSS 안의 위치. 같은 속성을 다투면 **큰 쪽이 이긴다** (동일 특이도). */
  readonly order: number;
}

let declCache: Map<string, UtilityDecl> | null = null;

/**
 * Tailwind 가 만든 유틸리티의 속성과 순서.
 *
 * **정본을 뺀 입력으로 묻는다** — `utilityOnlyClasses()` 와 같은 이유다. 정본 클래스가
 * 섞이면 「`.meta` 와 `.mono` 가 font-family 를 다툰다」 같은, 이 가드의 관할이 아닌
 * 것까지 나온다 (그쪽은 정본의 캐스케이드이고 G-C 가 공존 자체를 막는다).
 */
export function utilityDeclarations(): Map<string, UtilityDecl> {
  if (declCache !== null) return declCache;
  const theme = readFileSync(join(ROOT, "src/theme/tailwind.css"), "utf8").replace(
    /@import\s+"\.\/tokens\.css"[^;]*;/,
    "",
  );
  const tokens = readFileSync(join(ROOT, "src/theme/tokens.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const vars = Array.from(tokens.matchAll(/:root\s*\{[^}]*\}/g), (m) => m[0]).join("\n");
  const css = runTailwindRaw(`${theme}\n${vars}\n`);

  const head = css.match(/@layer\s+utilities\s*\{/);
  const out = new Map<string, { props: Set<string>; order: number }>();
  if (head === null || head.index === undefined) {
    declCache = out;
    return out;
  }
  // 여는 중괄호에서 시작해 짝을 맞춘다. **한 칸 뒤에서 시작하면** 첫 규칙의 닫는
  // 괄호를 레이어의 끝으로 오인한다 — 이 가드를 만들며 실제로 겪었고, 그때 읽힌
  // 클래스가 1개였다.
  const open = head.index + head[0].length - 1;
  let depth = 0;
  let close = open;
  for (let i = open; i < css.length; i += 1) {
    if (css[i] === "{") depth += 1;
    else if (css[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        close = i;
        break;
      }
    }
  }
  walkRules(css.slice(open + 1, close), open + 1, out);
  declCache = out;
  return out;
}

/** 규칙을 훑어 「선택자의 첫 클래스 → 선언된 속성」을 모은다. 중첩 at-규칙은 파고든다. */
function walkRules(text: string, base: number, out: Map<string, { props: Set<string>; order: number }>): void {
  let i = 0;
  let sel = "";
  while (i < text.length) {
    if (text[i] !== "{") {
      sel += text[i];
      i += 1;
      continue;
    }
    let depth = 1;
    let j = i + 1;
    while (j < text.length && depth > 0) {
      if (text[j] === "{") depth += 1;
      else if (text[j] === "}") depth -= 1;
      j += 1;
    }
    const body = text.slice(i + 1, j - 1);
    const selector = sel.trim();
    if (selector.startsWith("@")) {
      walkRules(body, base + i + 1, out);
    } else {
      const props: string[] = [];
      for (const d of body.matchAll(/(?:^|;)\s*([-a-zA-Z][-a-zA-Z0-9]*)\s*:/g)) props.push(d[1] as string);
      for (const part of selector.split(",")) {
        const m = part.match(/\.((?:\\.|[a-zA-Z0-9_-])+)/);
        if (m === null) continue;
        const name = (m[1] as string).replace(/\\(.)/g, "$1");
        let entry = out.get(name);
        if (entry === undefined) {
          entry = { props: new Set<string>(), order: base + i };
          out.set(name, entry);
        }
        // `--tw-*` 는 Tailwind 내부 변수다. 그것까지 세면 관계없는 유틸리티가
        // 서로 다투는 것처럼 보인다 (`shadow-*` 와 `ring-*` 등).
        for (const p of props) if (!p.startsWith("--tw")) entry.props.add(p);
      }
    }
    sel = "";
    i = j;
  }
}

/** 변형 접두(`hover:`·`disabled:`)와 유틸리티 본체를 가른다. 대괄호 안의 `:` 는 세지 않는다. */
export function splitVariant(name: string): { variant: string; utility: string } {
  let depth = 0;
  const cut: number[] = [];
  for (let i = 0; i < name.length; i += 1) {
    const c = name[i];
    if (c === "[") depth += 1;
    else if (c === "]") depth -= 1;
    else if (c === ":" && depth === 0) cut.push(i);
  }
  if (cut.length === 0) return { variant: "", utility: name };
  const last = cut[cut.length - 1] as number;
  return { variant: name.slice(0, last), utility: name.slice(last + 1) };
}

/**
 * 부품이 **조립해서** 요소에 붙이는 클래스 조합 전부.
 *
 * ## 왜 리터럴만 보면 부족한가
 *
 * `ui/Button` 은 흰 배경 위에 흰 글자를 그리고 있었다 (2026-09-11 사용자 신고).
 * 원인은 `BASE` 의 `bg-panel` 과 `VARIANT.primary` 의 `bg-ink` 가 **둘 다 살아
 * 있었던 것**이고, Tailwind 는 `className` 의 순서가 아니라 **산출 CSS 의 순서**로
 * 승자를 정하므로 나중에 적은 `bg-ink` 가 졌다.
 *
 * 그런데 두 클래스는 **서로 다른 문자열 리터럴**에 있다. 리터럴을 하나씩 보는 검사는
 * 조립된 결과를 영원히 보지 못한다 — 그래서 이 부분이 있다.
 *
 * ## 무엇을 조합으로 치는가
 *
 *     const cls = [BASE, SIZE[size], VARIANT[variant], layout].filter(Boolean).join(" ");
 *
 * 배열의 각 자리를 **선택지 목록**으로 푼다. `BASE` 는 하나, `VARIANT[variant]` 는
 * 그 표의 값 전부, 삼항은 양쪽. `layout` 처럼 알 수 없는 것은 빈 문자열로 둔다 —
 * 부품 밖에서 오는 배치이며 이 검사의 관할이 아니다.
 *
 * 표의 값끼리는 **서로 조합하지 않는다.** `primary` 와 `danger` 는 동시에 붙지 않는다.
 */
export function composedClassGroups(): { names: string[]; file: string; line: number; via: string }[] {
  const out: { names: string[]; file: string; line: number; via: string }[] = [];
  const files = execFileSync("find", ["src", "-name", "*.tsx"], { cwd: ROOT, encoding: "utf8" })
    .trim()
    .split("\n");
  for (const rel of files) {
    const txt = stripLineComments(withoutComments(readFileSync(join(ROOT, rel), "utf8")));
    const consts = stringConstants(txt);
    const records = recordConstants(txt);
    for (const m of txt.matchAll(/\]\s*\.filter\(Boolean\)\s*\.join\(" "\)/g)) {
      // **`[` 를 앞에서 찾으면 안 된다.** `gap-[6px]` 의 대괄호에서 매칭이 시작되어
      // 배열이 아닌 것을 배열로 읽는다 (실제로 그래서 `ui/Button` 을 통째로 놓쳤다).
      // 닫는 `]` 에서 뒤로 짝을 맞춰 여는 `[` 를 찾는다.
      const close = m.index ?? 0;
      let depth = 0;
      let open = -1;
      for (let i = close; i >= 0; i -= 1) {
        if (txt[i] === "]") depth += 1;
        else if (txt[i] === "[") {
          depth -= 1;
          if (depth === 0) {
            open = i;
            break;
          }
        }
      }
      if (open < 0) continue;
      const slots = splitTopLevel(txt.slice(open + 1, close)).map((s) => resolveSlot(s.trim(), consts, records));
      const line = txt.slice(0, open).split("\n").length;
      let combos: string[][] = [[]];
      for (const choices of slots) {
        const next: string[][] = [];
        for (const acc of combos) for (const c of choices) next.push(c === "" ? acc : [...acc, ...c.split(/\s+/)]);
        // 폭발 방지. 실측에서 가장 큰 것이 6×2 이므로 여유가 크다.
        combos = next.slice(0, 64);
      }
      const via = txt.slice(open + 1, close).replace(/\s+/g, " ").trim();
      for (const names of combos) {
        if (names.length > 1) out.push({ names, file: rel, line, via });
      }
    }
  }
  return out;
}

/**
 * `//` 주석을 지운다 (줄 번호는 보존한다). **문자열 안의 `//` 는 건드리지 않는다** —
 * `"https://…"` 를 자르면 없는 클래스를 만들어 낸다.
 *
 * 부품의 클래스 상수는 조각 사이에 주석을 끼워 두는 일이 잦고(`ui/Button` 의 BASE 가
 * 그렇다), 그것을 지우지 않으면 `"…" + "…"` 연결이 거기서 끊겨 **상수를 통째로 놓친다.**
 * 흰 버튼이 이 가드에 처음 안 잡힌 이유가 그것이었다.
 */
function stripLineComments(text: string): string {
  let out = "";
  let quote: string | null = null;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i] as string;
    if (quote !== null) {
      out += c;
      if (c === "\\") {
        i += 1;
        out += text[i] ?? "";
      } else if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") {
      quote = c;
      out += c;
      continue;
    }
    if (c === "/" && text[i + 1] === "/") {
      while (i < text.length && text[i] !== "\n") i += 1;
      out += "\n";
      continue;
    }
    out += c;
  }
  return out;
}

/** `const NAME = "…"` / `const NAME =\n  "…" + "…"` 를 이어 붙여 모은다. */
function stringConstants(txt: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const m of txt.matchAll(/const\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*string\s*)?=\s*((?:"[^"]*"|`[^`]*`)(?:\s*\+\s*(?:"[^"]*"|`[^`]*`))*)\s*;/g)) {
    const joined = Array.from((m[2] as string).matchAll(/"([^"]*)"|`([^`]*)`/g), (x) => (x[1] ?? x[2] ?? "") as string).join(" ");
    out.set(m[1] as string, joined);
  }
  return out;
}

/** `const NAME: Record<…> = { a: "…", b: "…" }` 의 값 전부. */
function recordConstants(txt: string): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const m of txt.matchAll(/const\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*Record<[^>]*>\s*=\s*\{([^}]*)\}/g)) {
    out.set(
      m[1] as string,
      Array.from((m[2] as string).matchAll(/:\s*"([^"]*)"/g), (x) => x[1] as string),
    );
  }
  return out;
}

/** 대괄호·중괄호·괄호 깊이를 세며 최상위 쉼표로 가른다. */
function splitTopLevel(text: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let acc = "";
  for (const ch of text) {
    if ("([{".includes(ch)) depth += 1;
    else if (")]}".includes(ch)) depth -= 1;
    if (ch === "," && depth === 0) {
      out.push(acc);
      acc = "";
    } else acc += ch;
  }
  if (acc.trim() !== "") out.push(acc);
  return out;
}

/** 배열의 한 자리가 될 수 있는 클래스 문자열 전부. 알 수 없으면 `[""]`. */
function resolveSlot(slot: string, consts: Map<string, string>, records: Map<string, string[]>): string[] {
  const lit = slot.match(/^(?:"([^"]*)"|`([^`$]*)`)$/);
  if (lit !== null) return [(lit[1] ?? lit[2] ?? "") as string];
  const rec = slot.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*\[/);
  if (rec !== null && records.has(rec[1] as string)) return records.get(rec[1] as string) as string[];
  if (consts.has(slot)) return [consts.get(slot) as string];
  const tern = slot.match(/\?([^]*)$/);
  if (tern !== null) {
    const parts = Array.from((tern[1] as string).matchAll(/"([^"]*)"|`([^`$]*)`/g), (x) => (x[1] ?? x[2] ?? "") as string);
    if (parts.length > 0) return parts;
  }
  return [""];
}
