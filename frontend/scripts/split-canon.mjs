/**
 * 정본에서 **앱이 실제로 쓰는 부분만** 뽑는다. 015 T075 (SC-007).
 *
 * ## 왜 나누는가
 *
 * `theme/tokens.css` 는 두 가지를 한 파일에 담고 있다.
 *
 *   ① `:root` 변수와 요소 규칙 (`button{}`·`input{}`·`:focus-visible{}`·리셋)
 *   ② 의미 클래스 규칙 148개 (`.btn`·`.chip`·`.notice` …)
 *
 * 015 가 끝난 뒤 **화면 코드는 ②를 하나도 쓰지 않는다.** 그런데 파일 전체를 번들에
 * 넣고 있었으므로 **12.5 kB 가 아무도 읽지 않는 채 사용자에게 내려가고 있었다**
 * (실측: base 레이어 14.7 kB 중 클래스 규칙이 12.5 kB).
 *
 * ②를 지울 수는 없다. `scripts/extract_canon.py` 가 확정 디자인에서 추출한 **기록**
 * 이고 L1 대조(`scripts/design_render.py`)의 기준이다. 그래서 **지우는 대신 번들에서
 * 뺀다** — 파일은 그대로 두고, 앱은 여기서 뽑은 `tokens.app.css` 를 불러온다.
 *
 * ## 왜 손으로 쓰지 않는가
 *
 * `tokens.css` 는 생성물이다 (계약 C-2 — 손대지 않는다). 그 파생물도 손으로 쓰면
 * 정본이 바뀔 때 조용히 어긋난다. 그래서 뽑아내고, `tests/CanonSplit.test.ts` 가
 * 산출물이 낡았는지 본다.
 *
 * ## 판정 규칙
 *
 * 선택자에 `.` 가 있으면 의미 클래스 규칙으로 보고 뺀다. 그 밖(요소·의사클래스·
 * 변수 선언)은 남긴다. `button.danger` 처럼 요소와 클래스가 섞인 것도 뺀다 —
 * 그 모양은 `ui/Button` 의 변종이 갖는다.
 *
 *     node scripts/split-canon.mjs          # 다시 뽑는다
 *     node scripts/split-canon.mjs --check  # 낡았으면 종료 코드 1
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
export const SOURCE = join(ROOT, "src/theme/tokens.css");
export const TARGET = join(ROOT, "src/theme/tokens.app.css");

const HEADER = `/**
 * **생성물이다. 손대지 않는다.** \`scripts/split-canon.mjs\` 가 \`theme/tokens.css\` 에서
 * 뽑는다 (015 T075).
 *
 * 정본의 \`:root\` 변수와 요소 규칙만 담는다. 의미 클래스 규칙은 화면 코드가 더 이상
 * 쓰지 않으므로 번들에 싣지 않는다 — 정본 파일에는 그대로 남아 있고
 * (\`theme/tokens.css\`), L1 대조가 그것을 읽는다.
 *
 * 고칠 일이 있으면 정본을 고치고 다시 뽑는다:  node scripts/split-canon.mjs
 */
`;

/** 선택자에 클래스가 들어간 규칙을 뺀다. 중첩 at-규칙은 파고들어 같은 규칙을 적용한다. */
export function splitCanon(css) {
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const out = [];
  walk(stripped, out);
  return `${HEADER}\n${out.join("\n\n")}\n`;
}

function walk(text, out) {
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
    const selector = sel.trim().replace(/\s+/g, " ");
    if (selector.startsWith("@")) {
      const inner = [];
      walk(body, inner);
      if (inner.length > 0) out.push(`${selector} {\n${inner.join("\n\n")}\n}`);
    } else if (selector !== "" && !selector.includes(".")) {
      out.push(`${selector} {${body.replace(/\s+$/, "")}\n}`);
    }
    sel = "";
    i = j;
  }
}

const invoked = process.argv[1] !== undefined && import.meta.url.endsWith(process.argv[1].split("/").pop());
if (invoked) {
  const made = splitCanon(readFileSync(SOURCE, "utf8"));
  if (process.argv.includes("--check")) {
    let current = "";
    try {
      current = readFileSync(TARGET, "utf8");
    } catch {
      current = "";
    }
    if (current !== made) {
      console.error("tokens.app.css 가 정본과 어긋난다. `node scripts/split-canon.mjs` 로 다시 뽑는다.");
      process.exit(1);
    }
    console.log("tokens.app.css 최신");
  } else {
    writeFileSync(TARGET, made);
    console.log(`${TARGET} 을 다시 뽑았다 (${made.length} 바이트)`);
  }
}
