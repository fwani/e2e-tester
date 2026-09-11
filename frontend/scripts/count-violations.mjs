#!/usr/bin/env node
/**
 * 시각 언어 위반 계수기 — 008 T001.
 *
 * `contracts/visual-language.md` §4 의 축 G-1·G-2 와 팔레트 이탈을 **파일별로** 센다.
 * 검사(`tests/VisualLanguage.test.tsx`)와 **같은 판정 규칙**을 쓰며, 이 파일이 규칙의
 * 정의처다 — 검사는 여기서 내보내는 함수를 부른다. 두 곳에 규칙을 두면 그것 자체가
 * 이 기능이 고치려는 결함이다.
 *
 *     node frontend/scripts/count-violations.mjs           # 사람이 읽는 표
 *     node frontend/scripts/count-violations.mjs --json    # 사실만
 *     node frontend/scripts/count-violations.mjs --lines    # 파일:줄 전부
 *
 * 왜 수치가 아니라 `파일:줄` 을 내는가 — FR-279. 수치만 보고하는 검사는 고칠 곳을
 * 알려주지 못한다. V-09 가 정확히 그 형태였다.
 *
 * ## 이 수치는 **원시 계수**다 (015 T052 가 명시함)
 *
 * 여기는 예외 등록부(`theme/exceptions.ts`)를 보지 않는다. 등록된 정당한 이탈까지
 * 함께 세므로, **합계가 0 이 아니어도 위반이라는 뜻은 아니다.**
 *
 * 판정은 `tests/VisualLanguage.test.tsx` 가 한다 — 이 파일의 규칙으로 세고, 예외
 * 등록부로 거른 뒤 단언한다. 「위반이 있는가」를 물으려면 그쪽을 돌린다.
 *
 * 둘을 나눈 이유: 계수기는 **고칠 곳을 보여주는 도구**이고 검사는 **막는 장치**다.
 * 계수기가 예외를 걸러 버리면 「등록된 것이 지금 몇 개인지」를 볼 수 없다.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
export const SRC_ROOT = resolve(HERE, "..", "src");
export const REPO_ROOT = resolve(HERE, "..", "..");

/**
 * G-1 — 색 리터럴. 어떤 표기든 잡는다.
 *
 * `#14171C` 도 `rgb(20,23,28)` 도 같은 값이므로 표기를 바꿔 빠져나갈 수 없어야 한다.
 * 002 라운드가 정규식을 빠져나간 하드 그림자 1건을 뒤늦게 찾은 전례가 있다.
 */
const COLOR = /#[0-9A-Fa-f]{3,8}\b|\brgba?\s*\(|\bhsla?\s*\(/g;

/**
 * G-2 — 시각 언어 속성의 인라인 선언.
 *
 * 목록은 `contracts/visual-language.md` §2 C-7 이 정본이다. 배치 속성(§2 허용 목록)은
 * 여기에 없다 — 그것은 007 배치 계약의 관할이고, 클래스로 옮기면 `Record<Phase, …>` 의
 * 컴파일 시점 강제를 잃는다 (research R3).
 */
const VISUAL_PROPS = [
  "background",
  "backgroundColor",
  "backgroundImage",
  "border",
  "borderTop",
  "borderRight",
  "borderBottom",
  "borderLeft",
  "borderColor",
  "borderRadius",
  "borderStyle",
  "borderWidth",
  "boxShadow",
  "color",
  "font",
  "fontFamily",
  "fontSize",
  "fontWeight",
  "fontStyle",
  "letterSpacing",
  "lineHeight",
  "textDecoration",
  "textTransform",
  "opacity",
  "outline",

  /*
    015 T052 — **배치 속성도 여기로 들어왔다.**

    008 계약 §2 는 배치 속성(`display`·`flex`·`position`·`width`…)의 인라인을
    허용했다. 007 배치 계약이 `Record<Phase, …>` 표의 값을 DOM 까지 나르는 통로로
    쓰고 있었기 때문이다.

    015 가 그 계약을 개정했다 (contracts/layout-contract-v2.md LC-3): 인라인에
    남을 자격은 **런타임 계산값**뿐이다. 표는 그대로 있고 출력만 클래스로 바뀌었다.

    그래서 허용 목록이 사라지고 이 목록이 넓어진다. 정당한 예외는
    `theme/exceptions.ts` 에 이유와 함께 등록한다 — 등록되지 않은 이탈은 존재할 수
    없다는 008 의 규율은 그대로다 (C-11~C-14).
  */
  "display",
  "flex",
  "flexBasis",
  "flexDirection",
  "flexGrow",
  "flexShrink",
  "flexWrap",
  "gap",
  "rowGap",
  "columnGap",
  "gridTemplateColumns",
  "gridTemplateRows",
  "alignItems",
  "justifyContent",
  "placeItems",
  "width",
  "minWidth",
  "maxWidth",
  "height",
  "minHeight",
  "maxHeight",
  "padding",
  "paddingTop",
  "paddingRight",
  "paddingBottom",
  "paddingLeft",
  "margin",
  "marginTop",
  "marginRight",
  "marginBottom",
  "marginLeft",
  "position",
  "top",
  "right",
  "bottom",
  "left",
  "inset",
  "zIndex",
  "overflow",
  "overflowX",
  "overflowY",
  "whiteSpace",
  "textOverflow",
  "wordBreak",
  "overflowWrap",
  "textAlign",
  "visibility",
  "cursor",
  "pointerEvents",
  "userSelect",
  "resize",
];
/** 규칙의 **정의처**. 검사가 이것을 가져다 쓴다 — 두 곳에 두면 말없이 갈린다. */
export const VISUAL_PROP_SOURCE = `(?<![A-Za-z])(${VISUAL_PROPS.join("|")})\\s*:`;
const VISUAL_PROP = new RegExp(VISUAL_PROP_SOURCE, "g");

/** 정본이 선언하는 색. `tokens.css` 에서 읽는다 — 목록을 두 곳에 두지 않는다. */
export function canonColors() {
  const css = readFileSync(join(SRC_ROOT, "theme", "tokens.css"), "utf8");
  return new Set((css.match(/#[0-9a-fA-F]{6}\b/g) ?? []).map((c) => c.toUpperCase()));
}

/** 검사 대상 열거. 손으로 적지 않는다 — 새 파일이 자동으로 대상이 된다 (V-09 의 원인 제거). */
export function screenFiles(root = SRC_ROOT) {
  const out = [];
  for (const name of readdirSync(root)) {
    const p = join(root, name);
    if (statSync(p).isDirectory()) out.push(...screenFiles(p));
    else if (name.endsWith(".tsx")) out.push(p);
  }
  return out.sort();
}

/**
 * 한 파일의 위반을 줄 단위로 낸다.
 *
 * 주석은 제외한다 — 주석 안의 `#F2F4F7` 은 근거를 적은 것이지 화면에 나가는 값이 아니다.
 * 002 의 `DesignTokens.test.tsx` 가 같은 이유로 주석을 걷어내고 단언한다.
 */
export function scan(text, palette) {
  const stripped = text
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "))
    .replace(/\/\/[^\n]*/g, (m) => m.replace(/[^\n]/g, " "));
  /*
    G-2 는 **인라인 `style` 안**만 본다 (015 T052).

    015 가 배치 속성을 목록에 넣으면서 범위를 좁혀야 했다. 파일 전체를 훑으면
    타입 정의(`interface SlotStyle { flex: string }`)와 일반 객체까지 세고, 실제
    인라인이 7곳인데 71건이 나온다 — 그 수치로는 무엇을 고쳐야 하는지 알 수 없다.
    계수기가 고칠 곳을 보여 주지 못하면 존재 이유가 없다 (FR-279).
  */
  const inlineStyleSpans = [];
  for (const m of stripped.matchAll(/style=\{\{/g)) {
    let depth = 2;
    let i = m.index + m[0].length;
    while (i < stripped.length && depth > 0) {
      if (stripped[i] === "{") depth += 1;
      else if (stripped[i] === "}") depth -= 1;
      i += 1;
    }
    inlineStyleSpans.push([m.index, i]);
  }
  const lineStart = [];
  {
    let acc = 0;
    for (const l of stripped.split("\n")) {
      lineStart.push(acc);
      acc += l.length + 1;
    }
  }
  const inInlineStyle = (lineIndex, col) => {
    const abs = lineStart[lineIndex] + col;
    return inlineStyleSpans.some(([a, b]) => abs >= a && abs < b);
  };
  const lines = stripped.split("\n");
  const found = [];
  lines.forEach((line, i) => {
    for (const m of line.matchAll(COLOR)) {
      const value = m[0];
      const hex = /^#/.test(value) ? value.toUpperCase() : null;
      found.push({
        line: i + 1,
        axis: "G-1",
        value,
        offPalette: hex !== null && palette !== undefined && !palette.has(hex),
      });
    }
    for (const m of line.matchAll(VISUAL_PROP)) {
      if (!inInlineStyle(i, m.index)) continue;
      found.push({ line: i + 1, axis: "G-2", value: m[1], offPalette: false });
    }
  });
  return found;
}

export function report(files = screenFiles(), palette = canonColors()) {
  const rows = [];
  for (const file of files) {
    const found = scan(readFileSync(file, "utf8"), palette);
    if (found.length === 0) continue;
    rows.push({
      file: relative(REPO_ROOT, file),
      color: found.filter((f) => f.axis === "G-1").length,
      inline: found.filter((f) => f.axis === "G-2").length,
      offPalette: [...new Set(found.filter((f) => f.offPalette).map((f) => f.value.toUpperCase()))],
      found,
    });
  }
  const offPalette = [...new Set(rows.flatMap((r) => r.offPalette))].sort();
  return {
    total: {
      color: rows.reduce((s, r) => s + r.color, 0),
      inline: rows.reduce((s, r) => s + r.inline, 0),
      offPaletteKinds: offPalette.length,
    },
    offPalette,
    rows,
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const r = report();
  if (process.argv.includes("--json")) {
    console.log(JSON.stringify(r, (k, v) => (k === "found" ? undefined : v), 2));
  } else if (process.argv.includes("--lines")) {
    for (const row of r.rows)
      for (const f of row.found)
        console.log(
          `${row.file}:${f.line} — ${f.axis === "G-1" ? "색 리터럴" : "인라인"} '${f.value}'` +
            `${f.offPalette ? " [팔레트 밖]" : ""} (${f.axis})`,
        );
  } else {
    console.log(`${"파일".padEnd(46)}${"색".padStart(5)}${"인라인".padStart(8)}  팔레트 밖`);
    for (const row of [...r.rows].sort((a, b) => b.color - a.color))
      console.log(
        `${row.file.padEnd(46)}${String(row.color).padStart(5)}${String(row.inline).padStart(8)}  ${row.offPalette.join(" ")}`,
      );
    console.log(
      `${"합계".padEnd(46)}${String(r.total.color).padStart(5)}${String(r.total.inline).padStart(8)}  ${r.total.offPaletteKinds}종`,
    );
  }
}
