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

const indexLines = [];
for (const file of files.sort()) {
  const base = file.replace(/\.schema\.json$/, "");
  const ts = await compileFromFile(join(schemaDir, file), options);
  await writeFile(join(outDir, `${base}.d.ts`), ts, "utf8");
  indexLines.push(`export type * from "./${base}";`);
  console.log(`생성: src/types/generated/${base}.d.ts`);
}

await writeFile(
  join(outDir, "index.ts"),
  `${options.bannerComment}\n\n${indexLines.join("\n")}\n`,
  "utf8",
);
console.log("생성: src/types/generated/index.ts");
