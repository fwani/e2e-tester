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
import { scan as rawScan } from "../scripts/count-violations.mjs";

import { generatedClasses } from "./helpers/tailwind";
import tokens from "../src/theme/tokens.css?raw";
import uiContract from "../../specs/007-unify-test-screens/contracts/ui-contract.md?raw";

/**
 * 확정 디자인 18장의 **원문 전체** (시트 + 인라인). G-4 의 출처 목록이다.
 *
 * 시트만 보면 안 된다 — `#E5D3AC`(주의 계열 경계선) 같은 값은 인라인에만 있고 그래도
 * v2 의 값이다. 반대로 인라인에 있다고 다 v2 인 것도 아니다 (아래 v1 표본 참고).
 */
const DESIGN_PAGES = import.meta.glob("../../docs/design/008-visual-language/*.dc.html", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;
const DESIGN_TEXT = Object.values(DESIGN_PAGES).join("\n").toLowerCase();

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

/**
 * Tailwind 가 실제로 만들어 내는 클래스. 015 T053.
 *
 * 이름 규칙을 형태로 추측하지 않는다 — 어간 목록으로 갈랐다가 정본 `.grid-head` 를
 * `grid-*` 유틸리티로 잘못 본 전례가 있다.
 */
const TAILWIND_CLASSES = generatedClasses();

interface Finding {
  file: string;
  line: number;
  axis: "G-1" | "G-2" | "G-3";
  value: string;
}

/** 축 → 예외 등록부의 `axis`. 등록부는 축 이름으로 예외를 좁힌다 (C-12). */
const EXCEPTION_AXIS: Record<string, string> = {
  "G-1": "color",
  "G-2": "inline-style",
  "G-3": "class-name",
  "G-4": "token",
};

function allowed(file: string, axis: Finding["axis"] | "G-4", value: string): boolean {
  const wanted = EXCEPTION_AXIS[axis];
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

/**
 * 원문 하나를 판정한다. 실제 파일과 **인위적인 원문**이 같은 함수를 지난다.
 *
 * ## 세는 일은 계수기가 한다 (015 T052)
 *
 * 이 파일이 자체 정규식으로 훑던 것을 `scripts/count-violations.mjs` 의 `scan()` 에
 * 넘겼다. 015 가 G-2 에 배치 속성을 더하면서 두 곳이 갈렸고, 그 결과 오탐이 쏟아졌다 —
 * `visibility: "keep"` 은 capability 모델의 필드이지 CSS 가 아닌데 G-2 로 잡혔다.
 *
 * 계수기는 인라인 `style={{…}}` **안**만 본다. 그 범위 판정이 여기 없었기 때문에
 * 생긴 차이이고, 규칙을 두 곳에 두면 그것 자체가 이 기능이 고치려는 결함이라는 말이
 * 규칙의 *적용 범위*에도 그대로 맞았다.
 *
 * 예외 거르기(`allowed`)는 여기 남는다 — 계수기는 원시 계수를 내고 판정은 검사가 한다.
 */
function scanText(file: string, raw: string): Finding[] {
  return (rawScan(raw) as { line: number; axis: string; value: string }[])
    .filter((f) => (f.axis === "G-1" || f.axis === "G-2") && !allowed(file, f.axis as Finding["axis"], f.value))
    .map((f) => ({ file, line: f.line, axis: f.axis as Finding["axis"], value: f.value }));
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

  it("G-3 — 화면이 정본에 없는 클래스를 쓰지 않는다", () => {
    /*
      C-8. 정본이 선언하지 않은 이름을 쓰면 그 자리는 **아무 형태도 받지 못한다** — 화면은
      스타일이 빠진 채로 그려지고 검사는 초록이다. 008 전환 중에 실제로 그 상태가 있었다:
      `.badge` 를 `.chip` 으로 통일한 순간 6개 파일이 존재하지 않는 클래스를 가리켰고,
      675건이 전부 통과하는 동안 아무도 그것을 몰랐다.

      **한계 — 문자열 리터럴만 본다.** `` className={`chip ${variant}`} `` 의 `${…}` 는
      클래스 이름이 아니라 식이므로 통째로 버린다. 그 계산된 변형은 `theme/tone.ts` 의
      `as const` 표가 좁히고, 아래 「정본이 형태 27종을 전부 선언한다」가 받친다.

      ## 2026-09-10 (015 T053) — 판정 기준을 넓혔다. 검증 대상은 그대로다

      015 가 Tailwind 를 들이면서 **형태의 출처가 둘이 됐다** — 정본과 Tailwind 산출물.
      「정본에 있는가」만 물으면 `bg-panel`·`flex-none` 같은 정상 유틸리티가 전부 위반이
      된다. 그것은 이 검사가 막으려던 것이 아니다.

      이 검사가 묻는 것은 처음부터 **「그 자리가 아무 형태도 받지 못하는가」**였다
      (008 에서 `.badge`→`.chip` 통일 후 6개 파일이 존재하지 않는 클래스를 가리켰고
      675건이 전부 통과했다). 그 질문은 그대로 두고, 답이 될 수 있는 곳을 하나 늘린다.

      Tailwind 쪽 판정은 **산출물을 실제로 조회한다** — 이름 규칙을 추측하지 않는다
      (`tests/helpers/tailwind.ts`). 같은 것을 가드 G-B 가 더 촘촘히 보므로, 여기는
      008 이 세운 축(G-1·G-2·G-3·G-6)의 일관성을 지키는 자리로 남는다.
    */
    const CLASS_ATTR = /className=(?:"([^"]*)"|\{`([^`]*)`\})/g;
    const orphans: string[] = [];
    for (const [key, raw] of Object.entries(SOURCES)) {
      const file = repoPath(key);
      for (const m of stripComments(raw).matchAll(CLASS_ATTR)) {
        const literal = m[1] ?? (m[2] as string).replace(/\$\{[^}]*\}/g, " ");
        for (const name of literal.split(/\s+/)) {
          if (!/^[a-z][a-z0-9-]*$/.test(name)) continue;
          if (CANON_CLASSES.has(name) || TAILWIND_CLASSES.has(name) || allowed(file, "G-3", name)) continue;
          orphans.push(`${file} — .${name}`);
        }
      }
    }
    expect(
      [...new Set(orphans)],
      "정본이 선언하지 않은 클래스를 쓴다. 그 자리는 아무 형태도 받지 못한다",
    ).toEqual([]);
  });

  it("G-4 — 정본에 확정 디자인에 없는 값이 없다", () => {
    /*
      **정본이 값을 지어내지 않는지 센다** (FR-266 · C-3).

      002 라운드의 결함이 정확히 이것이었다 — 확정 디자인에 `border-radius` 가 0회인데
      토큰에 `--radius: 10px` 가 있었다. 사람 눈으로 잡기 어려운 종류의 이탈이다.

      정본은 두 구획이다. 위는 `scripts/extract_canon.py` 가 dc.html 에서 **기계로 뽑은**
      것이라 정의상 디자인에 있다. 아래 파생 구획이 이 검사의 대상이다 — 확정 디자인이
      인라인으로 되풀이하는 형태에 이름을 붙인 곳이며, 이름을 붙이는 김에 값을 지어낼 수
      있는 자리다.
    */
    const marker = "정본에서 파생된 것";
    expect(tokens, "정본에 파생 구획 표시가 없다").toContain(marker);
    const derived = stripComments(tokens.slice(tokens.indexOf(marker)));

    const values = [
      ...(derived.match(/#[0-9A-Fa-f]{3,8}\b/g) ?? []),
      ...(derived.match(/\b\d+(?:\.\d+)?px\b/g) ?? []),
      ...(derived.match(/rgba?\([^)]*\)/g) ?? []),
    ];

    const orphan = [...new Set(values)].filter(
      (v) => !DESIGN_TEXT.includes(v.toLowerCase()) && !allowed("frontend/src/theme/tokens.css", "G-4", v),
    );
    expect(
      orphan,
      "확정 디자인 어디에도 없는 값을 정본이 갖고 있다. 값을 더하려면 먼저 디자인에서 " +
        "그 값을 찾거나, theme/exceptions.ts 에 사유와 함께 등록한다 (FR-266)",
    ).toEqual([]);
  });

  it("G-4 — 확정 디자인의 v1 대조 예시를 출처로 인정하지 않는다", () => {
    /*
      `Language.dc.html` 은 v2 를 설명하려고 v1 을 나란히 그린다 (「03 · 기하」). 그 값들은
      확정 디자인 **파일에는** 있지만 폐기된 언어다. 「디자인에 있으니 써도 된다」로 읽으면
      v1 이 되살아난다 — G-4 의 출처 목록이 넓기 때문에 이 단언이 함께 있어야 한다.
    */
    for (const dead of ["#f5d000", "#14130f"]) {
      expect(DESIGN_TEXT, `표본이 사라졌다면 이 단언을 다시 판단해야 한다: ${dead}`).toContain(dead);
      expect(stripComments(tokens).toLowerCase(), `v1 표본 값이 정본에 들어왔다: ${dead}`).not.toContain(dead);
    }
    expect(stripComments(tokens)).not.toMatch(/box-shadow:\s*\d+px \d+px 0(\s|;)/);
    expect(stripComments(tokens)).not.toMatch(/border:\s*3px solid/);
  });

  it("G-5 — 껍데기 치수 사본이 `ui-contract.md` §1-2 표와 같다", () => {
    /*
      정본은 그 표이고 `tokens.css` 는 **사본**이다 (C-5). 사본이 정본과 어긋나면 화면은
      둘 중 어느 쪽도 아닌 값을 그린다 — 007 이 표를 세운 이유가 컴포넌트가 자기 치수를
      스스로 정하던 것이었다.
    */
    const table = new Map(
      [...uiContract.matchAll(/^\|\s*\**([^|*]+?)\**\s*\|\s*\**(\d+)px\**/gm)].map(
        (m) => [(m[1] as string).trim(), `${m[2] as string}px`],
      ),
    );
    const COPY: Record<string, string> = {
      "헤더 높이": "--h-header",
      "국면 띠 높이": "--h-phase",
      "알림 띠 높이": "--h-notice",
      "조작 높이": "--h-control",
      "Step 행 높이": "--h-step",
      "Step 패널 폭": "--w-steps",
      "Step 상세 폭": "--w-detail",
      "최소 기준 폭": "--w-min",
    };

    // 표의 행 이름이 바뀌면 대조가 조용히 0건이 된다 — 그것부터 막는다.
    for (const label of Object.keys(COPY)) {
      expect(table.has(label), `ui-contract §1-2 표에 「${label}」 행이 없다`).toBe(true);
    }
    for (const [label, token] of Object.entries(COPY)) {
      const re = new RegExp(`${token}:\\s*([^;]+);`);
      const got = re.exec(stripComments(tokens))?.[1]?.trim();
      expect(got, `${token} 이 ui-contract §1-2 의 「${label}」 과 다르다`).toBe(table.get(label));
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
    /*
      예외가 관성으로 쌓이면 규칙을 갉아먹는다. 등록만 하고 실제로 쓰이지 않는 항목을
      보고한다 — 이 검사는 이미 한 번 일했다. 껍데기 경계선 예외가 불필요해진 것을
      잡아냈고 그 자리는 정본의 `.hdr`·`.phase` 가 이미 갖고 있었다.
    */
    const CORPUS: Record<string, string> = {
      ...Object.fromEntries(Object.entries(SOURCES).map(([k, v]) => [repoPath(k), v])),
      // 정본 자신도 예외의 대상이다 (`token` 축).
      "frontend/src/theme/tokens.css": tokens,
    };

    const dead = VISUAL_LANGUAGE_EXCEPTIONS.filter((e) => {
      const files = Object.keys(CORPUS).filter((f) => f.startsWith(e.file));
      if (files.length === 0) return true;
      const re = new RegExp(e.pattern);
      return !files.some((f) => {
        const text = stripComments(CORPUS[f] as string);
        if (e.axis === "color") return [...text.matchAll(COLOR)].some((m) => re.test(m[0]));
        if (e.axis === "inline-style")
          // 계수기가 세고 여기는 매칭만 본다 — 규칙이 한 곳에 있어야 갈리지 않는다.
          return (rawScan(text) as { axis: string; value: string }[])
            .filter((x) => x.axis === "G-2")
            .some((x) => re.test(x.value));
        if (e.axis === "token")
          return [...text.matchAll(/rgba?\([^)]*\)|#[0-9A-Fa-f]{3,8}\b|\b\d+(?:\.\d+)?px\b/g)].some(
            (m) => re.test(m[0]),
          );
        if (e.axis === "class-name")
          /*
            **클래스 이름 하나하나에 건다.** 파일 전체 텍스트에 걸면 `^outline-none$`
            처럼 앵커가 붙은 패턴이 영원히 맞지 않아, 살아 있는 예외가 죽은 것으로
            보고된다. 예외를 쓰는 쪽(`FocusRing` 의 `excused`)이 **토큰 하나**를 주므로
            여기서도 같은 단위로 물어야 한다 — 두 곳이 다른 단위를 쓰면 한쪽이 거짓말한다.
            (`class-name` 축이 처음 쓰인 2026-09-11 에 드러났다.)
          */
          return [...text.matchAll(/"([^"\n]*)"|`([^`\n]*)`/g)]
            .flatMap((m) => ((m[1] ?? m[2] ?? "") as string).split(/\s+/))
            .some((tok) => tok !== "" && re.test(tok));
        return re.test(text);
      });
    });
    expect(
      dead.map((e) => `${e.file} (${e.axis} ${e.pattern})`),
      "예외가 관성으로 남았다. 쓰이지 않으면 지운다",
    ).toEqual([]);
  });
});
