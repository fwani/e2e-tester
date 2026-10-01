/**
 * 백엔드 JSON Schema → TypeScript 타입 **과 값 제약** 생성. 헌법 Cross-language schema duty.
 *
 * 권위 정의는 backend/src/itb/domain 의 Pydantic 모델이다. 이 스크립트의 산출물은
 * 생성물이며 **손으로 고치지 않는다.** CI 의 schema-drift 잡이 재생성 결과와 비교한다.
 *
 * ## 왜 타입만으로는 모자란가 (028)
 *
 * TypeScript 타입에는 정규식도 길이 상한도 실리지 않는다 — `prefix: string` 이 전부다.
 * 그래서 화면이 값을 검사하려면 규칙을 **손으로 한 벌 더** 적게 되고, 실제로
 * `TestGroupBar` 가 그룹 접두어 정규식을 복제하고 있었다. 두 벌이 우연히 같았기 때문에
 * 드러나지 않다가, 028 이 한쪽만 고치는 순간 갈릴 뻔했다.
 *
 * 그래서 `constraints.ts` 를 함께 만든다. 화면은 규칙을 적지 않고 **읽는다.**
 */
import { readdir, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { compileFromFile } from "json-schema-to-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const schemaDir = resolve(here, "../../backend/schema");
const outDir = resolve(here, "../src/types/generated");

const options = {
  bannerComment: [
    "/* eslint-disable */",
    "/**",
    " * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.",
    " * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)",
    " * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types",
    " */",
  ].join("\n"),
  additionalProperties: false,
  style: { singleQuote: false, semi: true },
  unknownAny: true,
};

await mkdir(outDir, { recursive: true });

const files = (await readdir(schemaDir)).filter((f) => f.endsWith(".schema.json"));
if (files.length === 0) {
  console.error(
    `스키마가 없습니다: ${schemaDir}\n` +
      `cd backend && uv run python -m itb.schema.export 를 먼저 실행하세요.`,
  );
  process.exit(1);
}

// 배럴 파일(index.ts)을 만들지 않는다. json-schema-to-typescript 가 스키마마다
// `Name`·`Label`·`Tab` 같은 별칭 타입을 만들어서 한곳에 모으면 이름이 충돌한다.
// 소비자는 파일을 직접 임포트한다: import type { Step } from "../types/generated/step";
const generated = [];
for (const file of files.sort()) {
  const base = file.replace(/\.schema\.json$/, "");
  const ts = await compileFromFile(join(schemaDir, file), options);
  await writeFile(join(outDir, `${base}.d.ts`), ts, "utf8");
  generated.push(base);
  console.log(`생성: src/types/generated/${base}.d.ts`);
}

/**
 * 스키마를 훑어 문자열 제약(`pattern` · `maxLength` · `minLength`)을 모은다.
 *
 * 키는 `<스키마>/<정의>/<속성>` 이다 — `project/TestGroup/prefix`. 최상위 속성은
 * 정의 자리에 스키마의 `title` 을 쓴다.
 */
function collectConstraints(schemaName, schema) {
  const found = {};
  const visit = (owner, props) => {
    for (const [name, prop] of Object.entries(props ?? {})) {
      if (typeof prop !== "object" || prop === null) continue;
      if (prop.type !== "string") continue;
      const rule = {};
      if (typeof prop.pattern === "string") rule.pattern = prop.pattern;
      if (typeof prop.maxLength === "number") rule.maxLength = prop.maxLength;
      if (typeof prop.minLength === "number") rule.minLength = prop.minLength;
      // 제약이 없는 문자열은 담지 않는다 — 읽을 것이 없는 항목이 목록을 채운다.
      if (Object.keys(rule).length > 0) found[`${schemaName}/${owner}/${name}`] = rule;
    }
  };
  visit(schema.title ?? schemaName, schema.properties);
  for (const [defName, def] of Object.entries(schema.$defs ?? {})) {
    if (typeof def === "object" && def !== null) visit(defName, def.properties);
  }
  return found;
}

const constraints = {};
for (const file of files.sort()) {
  const base = file.replace(/\.schema\.json$/, "");
  const schema = JSON.parse(await readFile(join(schemaDir, file), "utf8"));
  Object.assign(constraints, collectConstraints(base, schema));
}

await writeFile(
  join(outDir, "constraints.ts"),
  [
    "/* eslint-disable */",
    "/**",
    " * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.",
    " * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)",
    " * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types",
    " *",
    " * 화면이 값을 검사할 때 쓰는 규칙이다. 여기 있는 것을 **읽고**, 다시 적지 않는다",
    " * (헌법 Cross-language schema duty).",
    " */",
    "",
    "export const CONSTRAINTS = {",
    ...Object.entries(constraints)
      .sort(([a], [b]) => (a < b ? -1 : 1))
      .map(([key, rule]) => `  ${JSON.stringify(key)}: ${JSON.stringify(rule)},`),
    "} as const;",
    "",
    "export type ConstraintKey = keyof typeof CONSTRAINTS;",
    "",
    "/** 규칙 하나를 값에 적용한다 — 모양과 길이를 **함께** 본다. */",
    "export function satisfies(key: ConstraintKey, value: string): boolean {",
    "  const rule: { pattern?: string; maxLength?: number; minLength?: number } = CONSTRAINTS[key];",
    "  if (rule.pattern !== undefined && !new RegExp(rule.pattern).test(value)) return false;",
    "  if (rule.maxLength !== undefined && value.length > rule.maxLength) return false;",
    "  if (rule.minLength !== undefined && value.length < rule.minLength) return false;",
    "  return true;",
    "}",
    "",
  ].join("\n"),
  "utf8",
);
console.log(`생성: src/types/generated/constraints.ts (제약 ${Object.keys(constraints).length}개)`);

await writeFile(
  join(outDir, "README.md"),
  [
    "# 생성된 타입 (손으로 고치지 마세요)",
    "",
    "권위 정의: `backend/src/itb/domain/*.py` (Pydantic v2). 헌법 Cross-language schema duty.",
    "",
    "재생성:",
    "",
    "```bash",
    "cd backend && uv run python -m itb.schema.export",
    "cd ../frontend && npm run gen:types",
    "```",
    "",
    "배럴 파일을 두지 않는다 — 스키마마다 생성되는 별칭 타입(`Name`, `Label`, `Tab` 등)이",
    "한곳에 모이면 이름이 충돌한다. 파일을 직접 임포트한다.",
    "",
    "## 파일",
    "",
    ...generated.map((b) => `- \`${b}.d.ts\``),
    "- `constraints.ts` — 스키마의 값 제약(정규식·길이). 화면이 규칙을 다시 적지 않게 한다",
    "",
  ].join("\n"),
  "utf8",
);
console.log("생성: src/types/generated/README.md");
