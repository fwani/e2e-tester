/**
 * 정본 회귀 가드. DC-004·DC-005.
 *
 * ## 2026-09-08 (008) — 역할이 둘로 갈렸다
 *
 * 이 파일은 `tokens.css` **원문**을 본다. 화면 코드가 그 정본을 실제로 **소비하는지**는
 * `VisualLanguage.test.tsx` 가 본다. 그 구분이 없어서 V-09 가 생겼다 — 정의는 지키는데
 * 소비는 아무도 보지 않아, 화면 코드에 색 리터럴 338개가 살아 있어도 초록이었다.
 *
 * | | 보는 것 | 어떻게 |
 * |---|---|---|
 * | 이 파일 | 정본이 v2 를 담고 v1 을 담지 않는가 | `tokens.css` 원문 정규식 |
 * | `VisualLanguage.test.tsx` | 화면 코드가 정본만 쓰는가 | `src/**\/*.tsx` **전체** 열거 |
 * | `CanonMatchesDesign.test.ts` | 정본이 확정 디자인과 같은 값을 그리는가 | chromium 계산값 |
 *
 * **아래 컴포넌트 import 5개는 색 검사가 아니다.** 밀도·껍데기·결말 표식처럼 원문
 * 정규식으로만 셀 수 있는 **구조** 단언이며, 소비 가드가 대신할 수 없다. 지우면 검사를
 * 지우는 것이므로 남긴다 (헌법 품질 게이트 4).
 *
 * ## 2026-09-08 — 이 파일은 앞서 통째로 뒤집혔다
 *
 * 이전 판은 v1「브루탈리스트」를 지켰다 — `border-radius` 금지, 1px 테두리 금지,
 * 하드 오프셋 그림자 필수, 배경 `#EFEBE0`. 그 다섯 단언이 전부 v2 와 정반대다.
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
    // 008 — 값이 확정 디자인에서 기계로 오므로 **표기도 디자인 것**이다. 디자인은
    // `rgba(20,23,28,.07)` 로 쓴다(공백 없음·선행 0 없음). 값은 같고 표기만 다르므로
    // 단언을 공백·선행 0 무관하게 갱신했다 — 약화가 아니라 기준 갱신이다.
    expect(declarations).toMatch(/--e-1:\s*0 1px 2px rgba\(\s*20\s*,\s*23\s*,\s*28\s*,\s*0?\.07\s*\)/);
    expect(declarations).toMatch(/--e-2:\s*0 16px 40px rgba\(\s*20\s*,\s*23\s*,\s*28\s*,\s*0?\.18\s*\)/);
  });

  it("화면 배경이 #F2F4F7 이다 (v1 의 #EFEBE0 이 아니다)", () => {
    expect(declarations).toMatch(/--bg:\s*#f2f4f7/i);
    expect(declarations).toMatch(/body\s*\{[^}]*background:\s*var\(--bg\)/);
    expect(declarations.toLowerCase()).not.toContain("#efebe0");
  });

  it("전용 디스플레이 서체를 두지 않는다 — 굵은 제목 서체는 밀도와 싸운다", () => {
    expect(declarations).not.toMatch(/Black Han Sans/);
    expect(declarations).not.toMatch(/--font-display/);
    // 위와 같은 이유로 쉼표 뒤 공백을 강제하지 않는다.
    expect(declarations).toMatch(/--font-sans:\s*"IBM Plex Sans KR"\s*,\s*system-ui/);
    expect(declarations).toMatch(/--font-mono:\s*"IBM Plex Mono"\s*,\s*ui-monospace/);
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

  it("정본 구획이 추출물임을 밝힌다 — 손으로 고치면 안 되는 부분이 어디인지 말한다", () => {
    // 값이 어디서 오는지 파일이 스스로 말하지 않으면, 다음 사람이 손으로 고친다.
    // 007 의 「전사」가 그렇게 굳었다.
    expect(tokens).toContain("scripts/extract_canon.py");
    expect(tokens).toMatch(/정본 —[\s\S]*손으로 고치지 않는다/);
  });

  it("확정 디자인의 v1 대조 예시를 정본에 들이지 않았다", () => {
    /*
      `Language.dc.html` 은 v2 를 설명하려고 v1 을 나란히 보여준다 (「03 · 기하」).
      그 예시 안의 값은 확정 디자인 **파일에는 있지만** v2 가 아니다. 파일에 있다는
      사실만으로 정본에 넣으면 폐기한 언어가 되살아난다.
    */
    expect(declarations.toLowerCase()).not.toContain("#f5d000");
    expect(declarations.toLowerCase()).not.toContain("#14130f");
    expect(declarations).not.toMatch(/box-shadow:\s*5px 5px 0/);
    expect(declarations).not.toMatch(/border:\s*3px solid/);
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
    /*
      008 — 행의 높이가 **정본에** 있다. 이전에는 컴포넌트가 `minHeight:"52px"` 를 전사했고
      이 단언은 그 사본을 봤다. 사본을 보면 정본이 바뀌어도 사본이 그대로면 통과한다 —
      그것이 v1→v2 에서 색과 구조가 남은 경로다. 이제 둘을 나눠 센다.

      (a) 정본의 `.srow` 가 52px 를 선언한다  (b) 행이 그 형태를 실제로 쓴다
    */
    expect(declarations).toMatch(/\.srow\{[^}]*height:52px/);
    expect(stepList).toMatch(/className=\{`srow /);
  });

  it("Step 이름을 한 줄로 자른다 — 감싸면 52px 가 성립하지 않는다", () => {
    // 확정 디자인은 `.srow .t b` 로, 제품은 누를 수 있는 `.srow-name` 으로 그린다.
    // **둘 다** 잘라야 한다 — 한쪽만 자르면 화면에서 행 높이가 흔들린다.
    expect(declarations).toMatch(/\.srow \.t b\{[^}]*text-overflow:ellipsis/);
    expect(declarations).toMatch(/\.srow \.t \.srow-name \{[\s\S]*?text-overflow: ellipsis/);
    expect(stepList).toMatch(/className="srow-name"/);
  });

  it("결말을 색만으로 구분하지 않는다 — 왼쪽 표식과 오른쪽 형태가 짝을 이룬다", () => {
    expect(stepList).toMatch(/OUTCOME_MARK/);
    expect(stepList).toMatch(/data-cell="outcome"/);
  });
});

describe("DC-011 — 기준 폭을 유지한 채 스크롤한다", () => {
  it("Artboard 가 가로 스크롤 컨테이너다", () => {
    // 디자인은 고정 폭이다. 좁은 창에서 임의로 재배치하지 않고 스크롤한다.
    // 015 — 배치가 클래스로 바뀌었다. 두 표기를 모두 받는다.
    expect(chrome).toMatch(/overflowX:\s*"auto"|\boverflow-x-auto\b/);
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
    //
    // 015 T030 — 배치가 클래스로 바뀌었다. **묻는 것은 그대로다.** 두 표기를 모두
    // 받는다 — 아직 전환하지 않은 화면이 있는 동안 인라인도 정답이기 때문이다.
    expect(workbench).toMatch(/overflowX:\s*"auto"|\boverflow-x-auto\b/);
  });
});
