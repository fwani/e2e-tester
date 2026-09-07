/**
 * 007 T095 (converge 1회차) — **국면 판정과 조작 권한은 규칙으로만 이루어진다**
 * (FR-251 · Constitution II NON-NEGOTIABLE).
 *
 * 헌법 원칙 II 는 「저장된 테스트의 재생 경로는 언어모델을 부르지 않는다」이고, 007 이
 * 그 경로에 새 판정 층을 하나 얹었다 — 어느 국면인가, 그 국면에서 무엇을 할 수 있는가.
 * 이 두 판정이 규칙이 아닌 것에 기대면, 재생 경로가 그만큼 결정적이지 않게 된다.
 *
 * **지금 실제로 규칙만으로 이루어져 있다.** 이 파일은 그것을 지킨다 — 백엔드의
 * `lint-imports` 가 계층 경계에 대해 하는 일을 화면 쪽 판정 모듈에 대해 한다.
 *
 * 왜 원문으로 보는가: 호출을 런타임에 잡으려면 무엇을 부르는지 미리 알아야 하는데,
 * 막으려는 것은 **아직 없는 호출**이다. 원문에 그 이름이 들어오는 순간을 잡는 것이
 * 이 성질을 지키는 방법이다.
 */
import { describe, expect, it } from "vitest";

import { capabilitiesFor, capabilityOf } from "../src/lib/capabilities";
import { phaseOfSession } from "../src/lib/phase";
import { PHASES } from "../src/lib/phase";
import { ACTION_IDS } from "../src/lib/actions";
import { sessionView } from "./helpers/workbench";
import { ALL_FACTS } from "./helpers/model";

/** 판정 모듈의 원문. 경로는 이 파일 기준이다. */
const SOURCES = import.meta.glob("../src/lib/{phase,capabilities,actions}.ts", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const MODULES = Object.entries(SOURCES).map(
  ([path, text]) => [path.replace(/^\.\.\/src\//, ""), text] as const,
);

/** 코드에서 주석과 문자열을 걷어낸다 — 설명에 나온 이름을 호출로 세지 않는다. */
function code(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/(^|[^:])\/\/.*$/gm, "$1 ")
    .replace(/"(?:[^"\\]|\\.)*"/g, '""')
    .replace(/'(?:[^'\\]|\\.)*'/g, "''")
    .replace(/`(?:[^`\\]|\\.)*`/g, "``");
}

describe("판정 모듈이 규칙만으로 이루어진다 (T095 · FR-251 · Constitution II)", () => {
  it("훑을 모듈이 실제로 있다", () => {
    // 목록을 못 읽은 채 통과하는 상태를 막는다.
    expect(MODULES.map(([p]) => p).sort()).toEqual([
      "lib/actions.ts",
      "lib/capabilities.ts",
      "lib/phase.ts",
    ]);
  });

  it.each(MODULES)("%s 는 언어모델·네트워크를 부르지 않는다", (path, source) => {
    const body = code(source);
    for (const forbidden of ["fetch(", "XMLHttpRequest", "WebSocket", "anthropic", "openai", "llm"]) {
      expect(body.toLowerCase().includes(forbidden.toLowerCase()), `${path}: ${forbidden}`).toBe(
        false,
      );
    }
  });

  it.each(MODULES)("%s 는 값을 임포트하지 않는다 — 판정에 부수효과가 섞이지 않는다", (path, source) => {
    /*
      `api/client` 를 **타입으로만** 가져온다. 값으로 가져오면 그 모듈의 부수효과가
      판정 모듈에 딸려 들어오고, 판정이 "지금 서버가 무엇을 아는가" 에 매달리게 된다.
      규칙은 받은 사실로만 답해야 한다.
    */
    for (const line of code(source).split("\n")) {
      const m = /^import\s+(?!type\b)([\s\S]*?)from\s+["']([^"']+)["']/.exec(line.trim());
      if (m === null) continue;
      const from = m[2] ?? "";
      // 같은 판정 층 안의 모듈만 값으로 가져올 수 있다.
      expect(from.startsWith("./"), `${path}: ${from} 을 값으로 가져온다`).toBe(true);
    }
  });

  it.each(MODULES)("%s 는 시간·무작위에 기대지 않는다 — 같은 사실이면 같은 답이다", (path, source) => {
    const body = code(source);
    for (const forbidden of ["Math.random", "Date.now", "new Date(", "performance.now"]) {
      expect(body.includes(forbidden), `${path}: ${forbidden}`).toBe(false);
    }
  });
});

describe("같은 입력이 같은 판정을 낸다 (Constitution II 의 관측 가능한 형태)", () => {
  it("국면 판정을 100번 반복해도 답이 하나다", () => {
    const view = sessionView({ state: "takeover_recording", authoring_mode: "ai" });
    const answers = new Set(Array.from({ length: 100 }, () => phaseOfSession(view)));
    expect(answers.size).toBe(1);
    // `takeover_recording` 은 AI 세션이면서 사람이 조작하는 국면이다 — 순서가 답을 정한다.
    expect([...answers][0]).toBe("takeover");
  });

  it("권한 판정을 반복해도 7 × 33 이 그대로다", () => {
    for (const phase of PHASES) {
      const a = capabilitiesFor(phase, ALL_FACTS);
      const b = capabilitiesFor(phase, ALL_FACTS);
      expect(JSON.stringify(b), phase).toBe(JSON.stringify(a));
      expect(Object.keys(a).length, phase).toBe(ACTION_IDS.length);
    }
  });

  it("사실이 같으면 순서와 무관하게 같은 답이다", () => {
    const forward = ACTION_IDS.map((a) => capabilityOf("paused", a, ALL_FACTS).kind);
    const backward = [...ACTION_IDS]
      .reverse()
      .map((a) => capabilityOf("paused", a, ALL_FACTS).kind)
      .reverse();
    expect(backward).toEqual(forward);
  });
});
