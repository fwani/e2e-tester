/**
 * 백엔드 JSON Schema → TypeScript 타입 생성. 헌법 Cross-language schema duty.
 *
 * 권위 정의는 backend/src/itb/domain 의 Pydantic 모델이다. 이 스크립트의 산출물은
 * 생성물이며 **손으로 고치지 않는다.** CI 의 schema-drift 잡이 재생성 결과와 비교한다.
 */
import { readdir, mkdir, writeFile } from "node:fs/promises";
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
    "",
  ].join("\n"),
  "utf8",
);
console.log("생성: src/types/generated/README.md");
