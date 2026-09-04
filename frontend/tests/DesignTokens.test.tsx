/**
 * 디자인 토큰 회귀 가드. DC-004·DC-005.
 *
 * 002 라운드 이전의 토큰은 팔레트를 정확히 옮겨 놓고 기하를 지어냈다 — 확정 디자인에
 * `border-radius` 가 0회인데 `--radius: 10px` 를 두었다. 그 한 줄이 제품 전체의 모서리를
 * 둥글게 만들었고, 확정 디자인은 직각이다.
 *
 * 사람이 눈으로 잡기 어려운 종류의 이탈이라 자동으로 막는다. 기준(dc.html) 쪽이 바뀌면
 * `scripts/design_baseline.py` 가 먼저 멈춘다 — 양쪽에서 조인다.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const read = (rel: string) =>
  readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8");

const tokens = read("../src/theme/tokens.css");

/** 주석을 걷어낸 실제 선언부. 주석의 설명 문구가 단언을 통과시키면 안 된다. */
const declarations = tokens.replace(/\/\*[\s\S]*?\*\//g, "");

describe("디자인 토큰 — 확정 디자인 준수", () => {
  it("border-radius 를 선언하지 않는다 (dc.html 8종에 0회)", () => {
    expect(declarations).not.toMatch(/border-radius/);
  });

  it("--radius 토큰이 없다 — 확정 디자인에 없는 값이다", () => {
    expect(declarations).not.toMatch(/--radius/);
  });

  it("테두리에 1px 을 쓰지 않는다 (확정 디자인은 3px·2px 뿐)", () => {
    expect(declarations).not.toMatch(/border:\s*1px/);
  });

  it("3px·2px 테두리 토큰을 제공한다", () => {
    expect(declarations).toMatch(/--rule:\s*3px/);
    expect(declarations).toMatch(/--rule-sub:\s*2px/);
  });

  it("하드 오프셋 그림자를 제공한다 (흐림 반경 0, dc.html 에 26회)", () => {
    expect(declarations).toMatch(/--lift:\s*5px 5px 0/);
    expect(declarations).toMatch(/--lift-accent:\s*5px 5px 0/);
  });

  it("화면 배경이 #EFEBE0 이다 (--paper 가 아니다)", () => {
    expect(declarations).toMatch(/--surface:\s*#efebe0/i);
    expect(declarations).toMatch(/body\s*\{[^}]*background:\s*var\(--surface\)/);
  });

  it("확정 디자인의 글꼴 대체 순서를 그대로 쓴다", () => {
    expect(declarations).toMatch(/--font-display:\s*"Black Han Sans", "Arial Black", Impact/);
    expect(declarations).toMatch(/--font-body:\s*"IBM Plex Sans KR", system-ui/);
    expect(declarations).toMatch(/--font-mono:\s*"IBM Plex Mono", ui-monospace/);
  });

  it("확정 디자인의 팔레트를 유지한다", () => {
    // research R6 에서 dc.html 실측과 일치를 확인한 값들이다.
    for (const color of ["#14130f", "#fffdf6", "#6b675c", "#efebe0", "#2e9455", "#d9502f", "#f5d000", "#7c4ddb"]) {
      expect(declarations.toLowerCase()).toContain(color);
    }
  });
});
