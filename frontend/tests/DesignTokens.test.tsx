/**
 * 디자인 토큰 회귀 가드. DC-004·DC-005.
 *
 * ## 2026-09-08 — 이 파일은 통째로 뒤집혔다
 *
 * 이전 판은 v1「브루탈리스트」를 지켰다 — `border-radius` 금지, 1px 테두리 금지,
 * 하드 오프셋 그림자 필수, 배경 `#EFEBE0`. 그 다섯 단언이 전부 v2 와 정반대다.
 *
 * 디자인이 `docs/design/008-visual-language/` 로 바뀌었으므로 가드도 바뀐다. 가드를
 * 그대로 두면 **폐기된 디자인이 코드를 계속 지배한다** — 그것이 이 파일을 먼저 고쳐야
 * 하는 이유다 (`replacement-map.md` §4 의 1번).
 *
 * 이전 판의 존재 이유는 그대로다. 002 라운드 이전의 토큰은 팔레트를 정확히 옮겨 놓고
 * 기하를 지어냈다 — 확정 디자인에 `border-radius` 가 0회인데 `--radius: 10px` 를
 * 두었다. 사람이 눈으로 잡기 어려운 종류의 이탈이라 자동으로 막는다. 기준(dc.html)
 * 쪽이 바뀌면 `scripts/design_baseline.py` 가 먼저 멈춘다 — 양쪽에서 조인다.
 */
import { describe, expect, it } from "vitest";

// Vite 의 `?raw` 로 원문을 그대로 읽는다. node:fs 를 쓰면 @types/node 가 필요해진다.
import tokens from "../src/theme/tokens.css?raw";
import chrome from "../src/components/design/Chrome.tsx?raw";
// 2회차 — `CreateTest` 가 만들기 국면(`ComposeView`)으로 흡수됐다 (FR-217b · T117)
import compose from "../src/pages/ComposeView.tsx?raw";
import workbench from "../src/components/workbench/Workbench.tsx?raw";
import stepList from "../src/components/workbench/StepList.tsx?raw";

/** 주석을 걷어낸 실제 선언부. 주석의 설명 문구가 단언을 통과시키면 안 된다. */
const declarations = tokens.replace(/\/\*[\s\S]*?\*\//g, "");

describe("디자인 토큰 — 008「계기판」 준수", () => {
  it("모서리 토큰 셋을 제공한다 — 칩 2 · 조작 3 · 겹침 6", () => {
    expect(declarations).toMatch(/--radius-chip:\s*2px/);
    expect(declarations).toMatch(/--radius:\s*3px/);
    expect(declarations).toMatch(/--radius-lg:\s*6px/);
  });

  it("v1 의 3px·2px 테두리 토큰이 없다 — 그 문법을 버렸다", () => {
    expect(declarations).not.toMatch(/--rule:\s*3px/);
    expect(declarations).not.toMatch(/--rule-sub:\s*2px/);
  });

  it("하드 오프셋 그림자를 쓰지 않는다 (흐림 반경 0 은 v1 의 서명이었다)", () => {
    // `5px 5px 0 #14130F` 같은 꼴. 흐림 반경이 0 인 그림자를 통째로 막는다.
    expect(declarations).not.toMatch(/box-shadow:[^;]*\d+px\s+\d+px\s+0(\s|;|$)/);
    expect(declarations).not.toMatch(/--lift/);
  });

  it("부드러운 그림자 두 단계를 제공한다", () => {
    expect(declarations).toMatch(/--e-1:\s*0 1px 2px rgba\(20, 23, 28, 0\.07\)/);
    expect(declarations).toMatch(/--e-2:\s*0 16px 40px rgba\(20, 23, 28, 0\.18\)/);
  });

  it("화면 배경이 #F2F4F7 이다 (v1 의 #EFEBE0 이 아니다)", () => {
    expect(declarations).toMatch(/--bg:\s*#f2f4f7/i);
    expect(declarations).toMatch(/body\s*\{[^}]*background:\s*var\(--bg\)/);
    expect(declarations.toLowerCase()).not.toContain("#efebe0");
  });

  it("전용 디스플레이 서체를 두지 않는다 — 굵은 제목 서체는 밀도와 싸운다", () => {
    expect(declarations).not.toMatch(/Black Han Sans/);
    expect(declarations).not.toMatch(/--font-display/);
    expect(declarations).toMatch(/--font-sans:\s*"IBM Plex Sans KR", system-ui/);
    expect(declarations).toMatch(/--font-mono:\s*"IBM Plex Mono", ui-monospace/);
  });

  it("008 의 팔레트를 유지한다", () => {
    // `scripts/design_baseline.py --json` 이 18종에서 뽑은 값들이다.
    for (const color of [
      "#14171c", // ink
      "#ffffff", // panel
      "#f2f4f7", // bg
      "#4a515c", // ink-2
      "#6e757f", // ink-3
      "#1a7f45", // pass
      "#c8371d", // fail
      "#8f5a00", // warn
      "#0b6bcb", // run
      "#6b3fd4", // ai
    ]) {
      expect(declarations.toLowerCase()).toContain(color);
    }
  });

  it("v1 팔레트가 남아 있지 않다", () => {
    for (const dead of ["#14130f", "#fffdf6", "#6b675c", "#2e9455", "#d9502f", "#f5d000", "#7c4ddb"]) {
      expect(declarations.toLowerCase()).not.toContain(dead);
    }
  });

  it("숫자를 고정폭으로 그린다 — 소요 시간 열이 자릿수마다 흔들리면 안 된다", () => {
    expect(declarations).toMatch(/font-variant-numeric:\s*tabular-nums/);
  });

  it("초점 링을 지우지 않는다", () => {
    expect(declarations).toMatch(/:focus-visible\s*\{[^}]*outline:\s*2px solid/);
  });

  it("쓸 수 없는 조작을 감추지 않고 무게만 낮춘다 (SC-004)", () => {
    // v1 은 채운 상자에 불투명도만 낮춰서 활성 조작보다 더 큰 자리를 먹었다.
    expect(declarations).toMatch(/button:disabled\s*\{[^}]*border:\s*1px dashed/);
    expect(declarations).toMatch(/button:disabled\s*\{[^}]*box-shadow:\s*none/);
    expect(declarations).not.toMatch(/button:disabled\s*\{[^}]*display:\s*none/);
  });
});

describe("밀도 — 이 개편이 실제로 사는 곳", () => {
  it("껍데기 층의 높이가 008 값이다", () => {
    expect(declarations).toMatch(/--h-header:\s*56px/);
    expect(declarations).toMatch(/--h-phase:\s*48px/);
    expect(declarations).toMatch(/--h-notice:\s*32px/);
    expect(declarations).toMatch(/--h-control:\s*32px/);
  });

  it("폭 셋은 바뀌지 않았다 — 고친 것은 세로다", () => {
    expect(declarations).toMatch(/--w-steps:\s*460px/);
    expect(declarations).toMatch(/--w-detail:\s*640px/);
    expect(declarations).toMatch(/--w-min:\s*1440px/);
  });

  it("Step 행이 52px 다 (v1 은 125px 였다)", () => {
    expect(declarations).toMatch(/--h-step:\s*52px/);
    // 행을 그리는 쪽도 같은 값이어야 한다. 토큰만 바꾸고 행이 안 따라오면 의미가 없다.
    expect(stepList).toMatch(/minHeight:\s*"52px"/);
  });

  it("Step 이름을 한 줄로 자른다 — 감싸면 52px 가 성립하지 않는다", () => {
    expect(stepList).toMatch(/textOverflow:\s*"ellipsis"/);
  });

  it("결말을 색만으로 구분하지 않는다 — 왼쪽 표식과 오른쪽 형태가 짝을 이룬다", () => {
    expect(stepList).toMatch(/OUTCOME_MARK/);
    expect(stepList).toMatch(/data-cell="outcome"/);
  });
});

describe("DC-011 — 기준 폭을 유지한 채 스크롤한다", () => {
  it("Artboard 가 가로 스크롤 컨테이너다", () => {
    // 디자인은 고정 폭이다. 좁은 창에서 임의로 재배치하지 않고 스크롤한다.
    expect(chrome).toMatch(/overflowX:\s*"auto"/);
  });

  it("고정 폭 화면이 맨몸으로 놓이지 않는다", () => {
    /*
      1회차 converge 2회차가 잡은 것: 8화면 중 둘만 `Artboard` 없이 고정 폭을 두고
      있었고, 만들기 화면은 `<Artboard width={1000}>` 으로 감쌌다.

      **2회차에 그 화면이 사라졌다.** 만들기가 통합 국면이 되면서 껍데기를 스스로 갖지
      않고 `Workbench` 의 1440 `Artboard` 를 지난다 (FR-258·FR-259). 그러므로 이 검사가
      세는 것은 「1000px 아트보드가 있는가」가 아니라 **「스스로 껍데기를 만들지 않는가」**
      다 — 자기 `Artboard` 를 가지면 껍데기가 다시 둘이 된다 (SC-011).
    */
    expect(compose).not.toMatch(/<Artboard/);
    expect(compose).toMatch(/<Workbench/);
  });

  it("Step 상세 겹침에 가로 스크롤이 있다", () => {
    // 절대 배치라 페이지 스크롤이 닿지 않는다. 없으면 좁은 창에서 잘린다.
    // 007 통합으로 겹침의 주인이 `SessionScreen` 에서 `Workbench` 로 옮겨졌다 —
    // 일곱 국면이 **같은 겹침 하나**를 쓴다 (FR-230).
    expect(workbench).toMatch(/overflowX:\s*"auto"/);
  });
});
