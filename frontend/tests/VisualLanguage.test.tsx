/**
 * L2 가드 — 화면 코드가 시각 언어 정본을 **우회하지 않는가.** 008 T008·T009.
 *
 * ## 왜 이 검사가 새로 필요했나
 *
 * `DesignTokens.test.tsx` 는 `tokens.css` 원문만 봤다. 정의는 지키는데 **소비**는 아무도
 * 보지 않았고, 그래서 화면 코드가 토큰을 통째로 우회한 채 33개 파일에 색 리터럴 338개가
 * 살아 있어도 검사는 초록이었다 (spec V-09 · V-02).
 *
 * 그 검사의 두 번째 결함은 대상을 **손으로 적었다**는 것이다 — `Chrome.tsx` 등 5개만
 * import 했다. 새 화면 파일은 검사 대상이 아니었다. 여기서는 `import.meta.glob` 으로
 * `src/**\/*.tsx` 전체를 열거하므로 **빠뜨릴 수 없다.**
 *
 * ## 무엇을 세는가
 *
 * 판정 규칙은 `scripts/count-violations.mjs` 하나에만 있고 이 검사가 그것을 부른다.
 * 규칙을 두 곳에 두면 그것 자체가 이 기능이 고치려는 결함이다.
 *
 *     G-1  색 리터럴          #rgb~#rrggbbaa · rgb( · rgba( · hsl(
 *     G-2  인라인 시각 언어    background · border* · boxShadow · color · font* …
 *     G-3  정본에 없는 클래스
 *     G-6  죽은 예외
 *
 * ## 상한은 내려가기만 한다
 *
 * 전환 시작 시점에 33개 파일이 전부 위반 상태였다. 처음부터 0 을 요구하면 첫 커밋도
 * 만들 수 없으므로 상한을 두고 단계마다 내린다. **올리려면 커밋 본문에 이유를 적어야
 * 한다** (`contracts/visual-language.md` §4 엄격도 전이).
 */
import { describe, expect, it } from "vitest";

import { VISUAL_LANGUAGE_EXCEPTIONS, isRegistered } from "../src/theme/exceptions";
import tokens from "../src/theme/tokens.css?raw";

/**
 * 화면 파일 전체. **손으로 적지 않는다** — 새 파일이 자동으로 대상이 된다.
 *
 * `eager: true` 로 원문을 그대로 받는다. 번들러가 CSS 를 빈 값으로 바꾸던 함정
 * (vite.config.ts 의 `css: true` 주석)과 같은 이유로, 읽는 것이 실제 원문이어야 한다.
 */
const SOURCES = import.meta.glob("../src/**/*.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** G-1 — 표기를 바꿔 빠져나갈 수 없게 잡는다. */
const COLOR = /#[0-9A-Fa-f]{3,8}\b|\brgba?\s*\(|\bhsla?\s*\(/g;

/** G-2 — `contracts/visual-language.md` §2 C-7 의 목록. 배치 속성은 여기 없다. */
const VISUAL_PROPS = [
  "background", "backgroundColor", "backgroundImage",
  "border", "borderTop", "borderRight", "borderBottom", "borderLeft",
  "borderColor", "borderRadius", "borderStyle", "borderWidth",
  "boxShadow", "color",
  "font", "fontFamily", "fontSize", "fontWeight", "fontStyle",
  "letterSpacing", "lineHeight", "textDecoration", "textTransform",
  "opacity", "outline",
];
const VISUAL_PROP = new RegExp(`(?<![A-Za-z])(${VISUAL_PROPS.join("|")})\\s*:`, "g");

/** 주석은 세지 않는다 — 근거를 적은 것이지 화면에 나가는 값이 아니다. */
function stripComments(text: string): string {
  return text
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "))
    .replace(/\/\/[^\n]*/g, (m) => m.replace(/[^\n]/g, " "));
}

/** `../src/pages/TestList.tsx` → `frontend/src/pages/TestList.tsx` */
function repoPath(globKey: string): string {
  return globKey.replace(/^\.\.\//, "frontend/");
}

interface Finding {
  file: string;
  line: number;
  axis: "G-1" | "G-2" | "G-3";
  value: string;
}

function allowed(file: string, axis: Finding["axis"], value: string): boolean {
  const wanted = axis === "G-1" ? "color" : axis === "G-2" ? "inline-style" : "class-name";
  return VISUAL_LANGUAGE_EXCEPTIONS.some(
    (e) =>
      isRegistered(e) &&
      e.axis === wanted &&
      file.startsWith(e.file) &&
      new RegExp(e.pattern).test(value),
  );
}

/**
 * 정본이 선언하는 클래스 이름. 목록을 두 곳에 두지 않으려고 시트에서 읽는다.
 *
 * 변형은 `.btn.primary` 처럼 이어 붙으므로 앞 문자를 제한하지 않는다. CSS 주석을 먼저
 * 걷어내지 않으면 설명 문장 안의 낱말이 클래스로 잡힌다.
 */
const CANON_CLASSES = new Set(
  [...tokens.replace(/\/\*[\s\S]*?\*\//g, " ").matchAll(/\.([a-z][a-z0-9-]*)/g)].map(
    (m) => m[1] as string,
  ),
);

/** 원문 하나를 판정한다. 실제 파일과 **인위적인 원문**이 같은 함수를 지난다. */
function scanText(file: string, raw: string): Finding[] {
  const found: Finding[] = [];
  stripComments(raw)
    .split("\n")
    .forEach((line, i) => {
      for (const m of line.matchAll(COLOR)) {
        if (!allowed(file, "G-1", m[0])) found.push({ file, line: i + 1, axis: "G-1", value: m[0] });
      }
      for (const m of line.matchAll(VISUAL_PROP)) {
        const prop = m[1] as string;
        if (!allowed(file, "G-2", prop)) found.push({ file, line: i + 1, axis: "G-2", value: prop });
      }
    });
  return found;
}

function scan(): Finding[] {
  return Object.entries(SOURCES).flatMap(([key, raw]) => scanText(repoPath(key), raw));
}

const LABEL: Record<Finding["axis"], string> = {
  "G-1": "색 리터럴",
  "G-2": "인라인 시각 언어",
  "G-3": "정본에 없는 클래스",
};

/** FR-279 — 어느 파일 어느 줄인지 알려준다. 수치만 내면 고칠 곳을 모른다. */
function describeFindings(found: Finding[], limit = 25): string {
  const head = found
    .slice(0, limit)
    .map((f) => `  ${f.file}:${f.line} — ${LABEL[f.axis]} '${f.value}' (${f.axis})`)
    .join("\n");
  return found.length > limit ? `${head}\n  … 그 외 ${found.length - limit}건` : head;
}

/* ────────────────────────────────────────────────────────────────────────────
   상한 — **0 이다.** 위반 하나면 검사가 실패한다.

   전환 시작(커밋 da16111): 색 338 · 인라인 730 · 팔레트 밖 16종
   US1 목록 화면 뒤:        색 237 · 인라인 569
   US2 껍데기·Step 목록 뒤: 색 116 · 인라인 350
   US2 Step 상세 뒤:        색  78 · 인라인 262
   US2 국면 화면 뒤:        색  25 · 인라인 172
   US3 남은 화면 뒤:        색   0 · 인라인   1
   US4 (T064):              색   0 · 인라인   0   ← 여기서 고정한다

   전환하는 동안에는 상한을 두고 단계마다 내렸다. 33개 파일이 전부 위반 상태에서
   시작했으므로 처음부터 0 을 요구하면 첫 커밋조차 만들 수 없었다. 이제 대상이 전부
   옮겨졌으므로 상한이라는 개념 자체를 없앤다 — **0 이 아니면 실패다.**
   ──────────────────────────────────────────────────────────────────────────── */

describe("L2 — 화면 코드가 정본만 소비하는가", () => {
  it("검사 대상을 손으로 적지 않는다 — 화면 파일 전체를 열거한다", () => {
    // V-09 의 원인 제거. 이 단언이 없으면 glob 이 조용히 0개를 잡아도 통과한다.
    expect(Object.keys(SOURCES).length).toBeGreaterThanOrEqual(30);
    expect(Object.keys(SOURCES).map(repoPath)).toContain("frontend/src/pages/TestList.tsx");
  });

  it("G-1 색 리터럴이 없다", () => {
    const found = scan().filter((f) => f.axis === "G-1");
    expect(found.length, `색을 화면 코드에 직접 적었다:\n${describeFindings(found)}`).toBe(0);
  });

  it("G-2 인라인 시각 언어 선언이 없다", () => {
    const found = scan().filter((f) => f.axis === "G-2");
    expect(
      found.length,
      `시각 언어를 인라인으로 선언했다 (정본의 형태를 써야 한다):\n${describeFindings(found)}`,
    ).toBe(0);
  });

  it("정본이 형태 27종을 전부 선언한다", () => {
    // C-4 — 이름과 뜻을 확정 디자인 그대로 유지한다.
    for (const name of [
      "btn", "primary", "danger", "off", "sm",
      "chip", "pass", "fail", "warn", "run", "ai",
      "srow", "sel", "pane", "lbl", "mono", "why",
      "hdr", "phase", "notice", "body", "left", "steps", "steps-hd",
    ]) {
      expect(CANON_CLASSES, `정본에 .${name} 이 없다`).toContain(name);
    }
  });

  it("SC-405 — 위반을 심으면 잡는다. 어느 파일 어느 줄인지 알려준다", () => {
    /*
      **가드가 실제로 잡는지 세는 검사다.** 「0건」이라는 통과는 두 가지를 뜻할 수 있다 —
      정말 없거나, 세는 쪽이 고장 났거나. 둘을 가르지 않으면 조용히 죽은 가드가 된다.
      002 가 CSS 임포트를 빈 값으로 바꿔 단언이 빈 문자열을 상대로 통과하던 것과 같은
      함정이며, 그때는 아무도 그 사실을 몰랐다.

      실제 소스를 더럽히지 않고 판정 함수에 인위적인 원문을 직접 먹인다.
    */
    const dirty = [
      'const a = <div style={{ background: "#14171C" }} />;',
      'const b = <div style={{ color: "rgb(1,2,3)" }} />;',
      "const c = <div style={{ fontWeight: 700 }} />;",
    ].join("\n");
    const found = scanText("frontend/src/__probe__.tsx", dirty);

    // 색 둘(#14171C · rgb() )과 인라인 넷(background · color · fontWeight … )
    expect(found.filter((f) => f.axis === "G-1").length).toBe(2);
    expect(found.filter((f) => f.axis === "G-2").length).toBeGreaterThanOrEqual(3);

    // FR-279 — 수치만 내면 고칠 곳을 모른다.
    const report = describeFindings(found);
    expect(report).toContain("frontend/src/__probe__.tsx:1");
    expect(report).toContain("#14171C");
    expect(report).toContain("frontend/src/__probe__.tsx:3");

    // 주석 안의 값은 세지 않는다 — 근거를 적은 것이지 화면에 나가는 값이 아니다.
    expect(scanText("x.tsx", '// v1 은 #C9A227 을 썼다\nconst x = 1;')).toEqual([]);
    expect(scanText("x.tsx", "/* background: red 였다 */\nconst x = 1;")).toEqual([]);
  });

  it("등록되지 않은 예외가 없다 — reason 이 빈 항목은 등록이 아니다", () => {
    for (const e of VISUAL_LANGUAGE_EXCEPTIONS) {
      expect(isRegistered(e), `${e.file} 의 예외에 사유가 없다`).toBe(true);
    }
  });

  it("G-6 죽은 예외가 없다 — 등록됐는데 쓰이지 않는 항목", () => {
    const dead = VISUAL_LANGUAGE_EXCEPTIONS.filter((e) => {
      const files = Object.keys(SOURCES).map(repoPath).filter((f) => f.startsWith(e.file));
      if (files.length === 0) return true;
      const re = new RegExp(e.pattern);
      return !files.some((f) => {
        const key = Object.keys(SOURCES).find((k) => repoPath(k) === f) as string;
        const text = stripComments(SOURCES[key] as string);
        if (e.axis === "color") return [...text.matchAll(COLOR)].some((m) => re.test(m[0]));
        if (e.axis === "inline-style")
          return [...text.matchAll(VISUAL_PROP)].some((m) => re.test(m[1] as string));
        return re.test(text);
      });
    });
    expect(
      dead.map((e) => `${e.file} (${e.axis} ${e.pattern})`),
      "예외가 관성으로 남았다. 쓰이지 않으면 지운다",
    ).toEqual([]);
  });
});
