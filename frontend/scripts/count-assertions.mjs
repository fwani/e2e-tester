#!/usr/bin/env node
/**
 * 단언 계수기 — 헌법 Quality Gate 4 를 **수치로** 확인한다. 015 T014.
 *
 * > 4. **No disabled tests** — a test MUST NOT be deleted, skipped, or weakened to make
 * >    a build pass.
 *
 * 015 는 인라인 스타일을 클래스로 바꾼다. `element.style.flex` 를 읽던 단언 68개가
 * 한꺼번에 빈 문자열을 보게 되고, 그때 **가장 쉬운 길은 단언을 지우거나 무르게 바꾸는
 * 것**이다. 그것이 게이트 4 위반이며, 말로 "지키겠다"고 하는 것으로는 막히지 않는다.
 *
 *     node frontend/scripts/count-assertions.mjs            # 표
 *     node frontend/scripts/count-assertions.mjs --json     # 사실만
 *     node frontend/scripts/count-assertions.mjs --since N  # 기준선 N 과 비교, 줄면 종료 1
 *
 * 기준선은 `specs/015-tailwind-css-migration/baseline.md` 에 있다 (착수 시점 1934).
 *
 * ## 무른 단언도 센다
 *
 * 수만 지키고 `toBeDefined()` 로 바꾸면 수치는 통과하고 검증은 사라진다.
 * 그래서 「무엇도 걸러내지 못하는 단언」을 따로 센다 — 이 수가 늘면 그것도 신호다.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
export const TESTS_ROOT = resolve(HERE, "..", "tests");

/** 사실상 아무것도 걸러내지 못하는 단언. 무르게 바꾸는 흔한 형태들이다. */
const WEAK = /\.(toBeDefined|toBeTruthy|toBeFalsy|not\.toBeNull|toBeUndefined)\(\)/g;

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (/\.test\.tsx?$/.test(name)) out.push(p);
  }
  return out;
}

export function count() {
  const files = walk(TESTS_ROOT).sort();
  let total = 0;
  let weak = 0;
  let skipped = 0;
  const per = [];
  for (const f of files) {
    const txt = readFileSync(f, "utf8");
    const n = (txt.match(/expect\(/g) ?? []).length;
    const w = (txt.match(WEAK) ?? []).length;
    const s = (txt.match(/\b(it|test|describe)\.(skip|todo)\b/g) ?? []).length;
    total += n;
    weak += w;
    skipped += s;
    per.push({ file: relative(resolve(HERE, "..", ".."), f), assertions: n, weak: w, skipped: s });
  }
  return { files: files.length, total, weak, skipped, per };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const r = count();
  const args = process.argv.slice(2);
  if (args.includes("--json")) {
    console.log(JSON.stringify({ files: r.files, total: r.total, weak: r.weak, skipped: r.skipped }, null, 2));
  } else {
    console.log(`테스트 파일 ${r.files} · 단언 ${r.total} · 무른 단언 ${r.weak} · 건너뛴 것 ${r.skipped}`);
    const worst = r.per.filter((x) => x.weak > 0).sort((a, b) => b.weak - a.weak).slice(0, 10);
    if (worst.length > 0) {
      console.log("\n무른 단언이 있는 파일:");
      for (const x of worst) console.log(`  ${x.weak.toString().padStart(3)}  ${x.file}`);
    }
  }
  const i = args.indexOf("--since");
  if (i >= 0) {
    const base = Number(args[i + 1]);
    if (Number.isFinite(base) && r.total < base) {
      console.error(
        `\n단언이 ${base} → ${r.total} 로 ${base - r.total}개 줄었다.\n` +
          "헌법 Quality Gate 4 — 테스트를 지우거나 건너뛰어 통과시키지 않는다.\n" +
          "줄어든 자리를 지목하고 이유를 대야 한다.",
      );
      process.exit(1);
    }
  }
  if (r.skipped > 0) {
    console.error(`\n건너뛴 테스트 ${r.skipped}개가 있다. 게이트 4 위반이다.`);
    process.exit(1);
  }
}
