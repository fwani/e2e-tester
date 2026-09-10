/**
 * ③ 좌측 세로 배분 검사 (007 T099 · SC-010 · UC-100 · FR-256·FR-257).
 *
 * **이 검사가 막는 것은 S-12 의 재발이다.** 1회차에는 표시 컴포넌트가 각자 자기 자리
 * 크기를 하드코딩했고(`TargetPane` 의 `flex: "1"`, `PhaseAside` 의 `flex: 0 0 auto`),
 * 합쳐 보면 편집 국면에서 채울 것이 없는 자리가 700px 를 가져갔다. 판단이 두 파일에
 * 흩어져 있으면 어느 한 쪽만 보고는 그 결함을 볼 수 없다 — 그래서 표로 모았고, 이
 * 검사가 그 표와 두 파일을 함께 센다.

 * ## 2026-09-10 (015 T029) — 판정 방법을 바꿨다. 검증 대상은 그대로다
 *
 * 배분이 스타일 객체(`SlotStyle`)에서 클래스 문자열로 바뀌었다. `size: SlotStyle` 과
 * `...size,` 를 찾던 단언이 성립하지 않는다.
 *
 * **이 검사가 묻는 것은 「표시 컴포넌트가 자기 크기를 스스로 정하지 않는가」다** —
 * 007 이 S-12(편집 국면에서 두 자리가 뒤바뀜)를 고치며 세운 성질이고, 015 가 배치
 * 계약을 개정해도 **그 성질은 개정 대상이 아니다** (FR-020b).
 *
 * 그래서 같은 것을 새 표기로 묻는다. 하드코딩 금지 단언은 **늘렸다** — 인라인
 * `flex: "1"` 뿐 아니라 유틸리티 `flex-1` 로 같은 일을 하는 것도 막는다. 표기만 바꿔
 * 빠져나갈 수 있으면 검사가 아니다.
 */
import { describe, expect, it } from "vitest";

import {
  CONTENT_MIN_HEIGHT,
  PRIMARY_SLOT,
  VERTICAL_SPLIT,
  flexOf,
  splitFor,
  type SlotSize,
} from "../src/lib/layout";
import { PHASES } from "../src/lib/phase";

/**
 * 표시 컴포넌트의 원문. `DeterministicPhase.test.ts` 와 같은 방식이다 (`?raw` glob) —
 * 이 리포지토리에는 `@types/node` 가 없고, 원문 대조는 Vite 가 해 준다.
 */
const SOURCES = import.meta.glob("../src/components/workbench/{TargetPane,WorkArea}.tsx", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** 주석을 지운다 — 주석은 **옛 값을 설명하려고** 그것을 인용한다. */
function code(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/(^|[^:])\/\/.*$/gm, "$1 ");
}

function sourceOf(file: string): string {
  const hit = Object.entries(SOURCES).find(([path]) => path.endsWith(`/${file}`));
  // 원문을 못 읽은 채 통과하는 상태를 막는다
  expect(hit, `${file} 원문을 읽지 못했다`).toBeDefined();
  return code(hit![1]);
}

describe("세로 배분 표 (FR-256)", () => {
  it("여덟 국면 전부가 배분을 갖는다", () => {
    // `Record<Phase, …>` 가 타입 시점에 이미 요구하지만, 값이 실제로 채워졌는지는 별개다
    for (const phase of PHASES) {
      const split = splitFor(phase);
      expect(split.targetSlot, `${phase} 의 ③-a`).toBeDefined();
      expect(split.workArea, `${phase} 의 ③-b`).toBeDefined();
    }
    expect(Object.keys(VERTICAL_SPLIT).sort()).toEqual([...PHASES].sort());
  });

  it("모든 국면이 주 자리를 선언한다 (FR-257)", () => {
    expect(Object.keys(PRIMARY_SLOT).sort()).toEqual([...PHASES].sort());
  });

  /**
   * UC-100 — 배분표의 유일한 불변식.
   *
   * 두 자리가 동시에 `fill` 이면 그 국면의 주 작업이 어느 자리인지 화면이 말하지 못한다.
   * 동시에 `content` 면 남는 높이가 어디로도 가지 않는다.
   */
  it("한 국면에서 두 자리가 동시에 fill 이거나 동시에 content 이지 않다 (UC-100)", () => {
    for (const phase of PHASES) {
      const { targetSlot, workArea } = splitFor(phase);
      expect(
        targetSlot.kind === "fill" && workArea.kind === "fill",
        `${phase}: 두 자리가 동시에 fill 이면 주 작업이 어느 자리인지 알 수 없다`,
      ).toBe(false);
      expect(
        targetSlot.kind === "content" && workArea.kind === "content",
        `${phase}: 두 자리가 동시에 content 이면 남는 높이가 어디로도 가지 않는다`,
      ).toBe(false);
    }
  });

  /**
   * 선언한 주 자리와 실제 배분이 어긋나면 그것이 **S-12 의 형태**다 — 선언은
   * 「편집면이 주 작업」인데 배분은 대상 앱 슬롯에 남는 높이를 준 상태.
   */
  it("선언한 주 자리가 실제로 더 큰 배분을 갖는다 (FR-257 · SC-010)", () => {
    /** 남는 높이를 갖는 정도. 큰 값이 더 큰 자리다 */
    const weight = (s: SlotSize): number =>
      s.kind === "fill" ? 2 : s.kind === "fixed" ? 1 : 0;

    for (const phase of PHASES) {
      const { targetSlot, workArea } = splitFor(phase);
      const primary = PRIMARY_SLOT[phase];
      const primaryWeight = primary === "target" ? weight(targetSlot) : weight(workArea);
      const otherWeight = primary === "target" ? weight(workArea) : weight(targetSlot);
      expect(
        primaryWeight,
        `${phase}: 주 자리는 ${primary} 인데 배분이 그보다 작거나 같다 — S-12 의 형태다`,
      ).toBeGreaterThan(otherWeight);
    }
  });

  it("편집 국면은 작업 영역이 주 자리이고 대상 앱 슬롯은 최소 높이만 갖는다 (FR-261)", () => {
    const { targetSlot, workArea } = splitFor("editing");
    expect(PRIMARY_SLOT.editing).toBe("work");
    expect(workArea.kind).toBe("fill");
    // 자리를 **없애지 않는다.** 줄이는 것과 없애는 것은 다르다
    expect(targetSlot.kind).toBe("fixed");
    if (targetSlot.kind === "fixed") expect(targetSlot.px).toBeGreaterThan(0);
  });

  it("결과 국면의 작업 영역은 스크롤 없이 담을 높이를 갖는다 (FR-262 · SC-012)", () => {
    const { workArea } = splitFor("result");
    expect(workArea.kind).toBe("fixed");
    // 실패 사유 2줄 + 시도한 LOCATOR 4행 + 경고 1개. 1회차에는 45% 상한에 갇혔다
    if (workArea.kind === "fixed") expect(workArea.px).toBeGreaterThanOrEqual(400);
  });

  it("세션이 있는 다섯 국면은 대상 앱 슬롯이 주 자리다 — 1회차 배분을 바꾸지 않는다", () => {
    for (const phase of ["recording", "ai_authoring", "takeover", "running", "paused"] as const) {
      expect(PRIMARY_SLOT[phase], `${phase}`).toBe("target");
      expect(splitFor(phase).targetSlot.kind, `${phase}`).toBe("fill");
    }
  });
});

describe("배분의 CSS 환산 (flexOf)", () => {
  it("fill 은 남는 높이를 갖고 상한이 없다", () => {
    const style = flexOf({ kind: "fill" });
    expect(style.flex).toBe("1 1 0px");
    // `maxHeight` 가 붙으면 **fill 이 무력화된다** — 1회차 `maxHeight: 45%` 가 그것이었다
    expect(style.maxHeight).toBeUndefined();
  });

  it("content 는 최소 높이와 상한을 함께 갖는다", () => {
    const style = flexOf({ kind: "content" });
    expect(style.minHeight).toBe(CONTENT_MIN_HEIGHT);
    // 상한이 없으면 검증 추가 폼이 미러를 밀어낸다
    expect(style.maxHeight).toBeDefined();
  });

  it("fixed 는 정해진 높이를 갖고 상한이 없다", () => {
    const style = flexOf({ kind: "fixed", px: 424 });
    expect(style.flex).toBe("0 0 424px");
    expect(style.minHeight).toBe(424);
    expect(style.maxHeight).toBeUndefined();
  });
});

/**
 * S-12 재발 방지 — **표시 컴포넌트는 자기 크기를 모른다** (research R9).
 *
 * 크기가 인자로만 오는지를 원문으로 센다. 자리 **안쪽** 자식의 `flex: 1` 은 정당하므로,
 * 뿌리 요소가 `size` 를 펼치는지와 옛 하드코딩 형태가 없는지를 본다.
 */
describe("표시 컴포넌트가 자기 크기를 갖지 않는다 (S-12 재발 방지)", () => {
  const cases = [
    { file: "TargetPane.tsx", marker: "data-workbench-target" },
    { file: "WorkArea.tsx", marker: "data-workbench-work" },
  ];

  it("훑을 파일이 실제로 있다", () => {
    expect(Object.keys(SOURCES)).toHaveLength(2);
  });

  for (const { file, marker } of cases) {
    it(`${file} 의 뿌리 요소가 크기를 인자로 받는다`, () => {
      const source = sourceOf(file);

      // 크기 인자를 받는다 — 015 T029 에서 스타일 객체가 클래스 문자열로 바뀌었다
      expect(source, `${file} 에 크기 인자가 없다`).toContain("sizeClass: string");
      // 뿌리 요소가 그것을 쓴다
      expect(source).toContain(marker);
      expect(source, `${file} 뿌리가 sizeClass 를 붙이지 않는다`).toContain("${sizeClass}");

      // 1회차의 하드코딩 형태가 남아 있지 않다 (인라인·유틸리티 양쪽 표기를 본다)
      expect(source, `${file} 에 flex: "1" 하드코딩이 남았다`).not.toContain('flex: "1"');
      expect(source, `${file} 에 flex: 0 0 auto 하드코딩이 남았다`).not.toContain("0 0 auto");
      expect(source, `${file} 에 maxHeight 하드코딩이 남았다 — fill 을 무력화한다`).not.toContain(
        'maxHeight: "45%"',
      );
      // 유틸리티로 같은 일을 하는 것도 막는다 — 표기만 바꿔 빠져나갈 수 없어야 한다.
      expect(source, `${file} 에 flex-1 하드코딩이 남았다`).not.toMatch(/className=[^\n]*\bflex-1\b/);
      expect(source, `${file} 에 max-h-[45%] 하드코딩이 남았다`).not.toContain("max-h-[45%]");
    });
  }
});
