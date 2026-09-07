/**
 * 007 T027 — 구현 개수 (SC-001).
 *
 * **사용자가 제기한 문제를 직접 센다.** "다 따로 만드니까 사용성이 떨어진다" 는 말의
 * 코드 상 형태가 이것이다 — Step 목록을 그리는 구현이 **4벌**, Step 상세가 **2벌**이었다.
 *
 * 이 검사가 필요한 이유는 통합이 **또 하나의 구현**이 될 수 있기 때문이다. 통합 화면을
 * 만들고 기존 화면을 남기면 4벌이 5벌이 된다 (research R7). 그래서 이행 묶음마다 옛
 * 구현을 삭제하고, 이 검사가 그것을 센다.
 *
 * **남은 개수를 예산으로 둔다.** 이행 중에는 옛 구현이 남아 있는 것이 정상이므로, 검사를
 * 빨갛게 두는 대신 `REMAINING_BUDGET` 을 두고 이행 묶음마다 내린다. 그러면
 *
 * - 빨강은 항상 **무언가 깨진 것**을 뜻한다. "설계된 빨강" 과 "깨진 빨강" 이 섞이지 않는다
 * - 예산이 늘면 즉시 실패한다 — 통합 화면이 **또 하나의 구현**이 되는 순간이 그것이다
 * - 예산 숫자가 커밋 이력에 남아 어느 이행에서 몇 벌이 줄었는지 보인다
 *
 * 완료 조건은 `REMAINING_BUDGET === 0` 이다 (SC-001).
 *
 * 파일 목록을 `node:fs` 가 아니라 `import.meta.glob` 으로 읽는 이유: `@types/node` 를
 * 들이지 않기 위해서다. 이 프로젝트의 프런트엔드는 브라우저 대상이고 tsconfig 의
 * `types` 가 `vitest/globals`·`vite/client` 둘뿐이다. 검사 하나를 위해 그 경계를 넓히지
 * 않는다.
 */
import { describe, expect, it } from "vitest";

/** `src` 전체의 경로 → 소스 텍스트. 경로는 이 파일 기준의 상대 경로다. */
const SOURCES = import.meta.glob("../src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** `../src/pages/Runner.tsx` → `pages/Runner.tsx` */
const srcPaths = new Set(
  Object.keys(SOURCES).map((p) => p.replace(/^\.\.\/src\//, "")),
);

function exists(path: string): boolean {
  return srcPaths.has(path);
}

/** 그 모듈을 `src` 안에서 참조하는 파일들 (자기 자신 제외). */
function referencedFrom(moduleBase: string): string[] {
  return Object.entries(SOURCES)
    .filter(([path, text]) => {
      const rel = path.replace(/^\.\.\/src\//, "");
      if (rel.replace(/\.tsx?$/, "").endsWith(moduleBase)) return false;
      return text.includes(`/${moduleBase}"`) || text.includes(`/${moduleBase}'`);
    })
    .map(([path]) => path.replace(/^\.\.\/src\//, ""));
}

/**
 * 통합으로 사라져야 하는 옛 구현.
 *
 * `이행` 은 `research.md` R7 의 순서다. 각 항목은 그 이행 묶음이 끝나면 **파일이 없고
 * 참조가 0건**이어야 한다.
 */
const RETIRED: { path: string; kind: "목록" | "상세" | "화면"; 이행: number }[] = [
  { path: "pages/Runner.tsx", kind: "화면", 이행: 1 },
  { path: "pages/RunnerPaused.tsx", kind: "화면", 이행: 2 },
  { path: "pages/Takeover.tsx", kind: "화면", 이행: 3 },
  { path: "components/design/DesignStepList.tsx", kind: "목록", 이행: 3 },
  { path: "pages/AiRecord.tsx", kind: "화면", 이행: 4 },
  { path: "pages/RunResult.tsx", kind: "화면", 이행: 5 },
  { path: "pages/StepInspector.tsx", kind: "상세", 이행: 6 },
  { path: "pages/TestDefinition.tsx", kind: "화면", 이행: 6 },
];

/**
 * 아직 남아 있어도 되는 옛 구현의 수. **이행 묶음마다 내린다.**
 *
 * | 값 | 시점 |
 * |---|---|
 * | 8 | Phase 2 종료 — 공통 계약만 만들었고 어느 국면도 옮기지 않았다 |
 * | 4 | 이행 1~4 종료 — 세션 국면 다섯이 통합 화면으로 옮겨졌다 |
 * | 3 | 이행 5 종료 — 결과 국면이 옮겨졌다 |
 * | 0 | 이행 3·6 종료 — 옛 Step 목록·상세·편집 화면이 사라졌다 |
 * | 0 | 이행 6 종료 — SC-001 달성 |
 *
 * 이 숫자를 **올리는 변경은 허용되지 않는다.** 올려야 한다면 통합이 구현을 늘리고 있는
 * 것이고, 그것이 사용자가 제기한 문제를 키우는 일이다.
 */
// `number` 로 못박는 이유: 리터럴 타입(`8`)이면 아래 `=== 0` 비교가 "겹치지 않는 타입"
// 으로 컴파일 오류가 된다. 예산은 내려가는 값이므로 그 비교가 의도된 것이다.
const REMAINING_BUDGET: number = 0;

describe("구현 개수 (T027 · SC-001)", () => {
  it("통합 구현이 있다 — StepList 1개 · StepDetail 1개", () => {
    expect(exists("components/workbench/StepList.tsx")).toBe(true);
    expect(exists("components/workbench/StepDetail.tsx")).toBe(true);
  });

  it(`남은 옛 구현이 예산(${REMAINING_BUDGET})을 넘지 않는다`, () => {
    const remaining = RETIRED.filter((r) => exists(r.path)).map(
      (r) => `${r.path} (이행 ${r.이행})`,
    );
    expect(
      remaining.length,
      `옛 구현이 예산보다 많다 — 통합이 구현을 늘리고 있다:\n  ${remaining.join("\n  ")}`,
    ).toBeLessThanOrEqual(REMAINING_BUDGET);
  });

  it("예산이 실제와 어긋나지 않는다 — 줄었으면 예산도 내려야 한다", () => {
    // 예산을 내리지 않고 지나가면 다음 이행에서 늘어난 것을 잡을 수 없다.
    const remaining = RETIRED.filter((r) => exists(r.path)).length;
    expect(
      remaining,
      `옛 구현이 ${remaining}벌 남았는데 예산은 ${REMAINING_BUDGET} 이다. ` +
        `REMAINING_BUDGET 을 ${remaining} 으로 내려라`,
    ).toBe(REMAINING_BUDGET);
  });

  it("이행이 끝나면 예산이 0이어야 한다 (SC-001 의 완료 조건)", () => {
    // 이행 중에는 이 단정이 「아직 0이 아니다」를 기록으로 남긴다. 0 이 되는 순간
    // 이 검사가 SC-001 의 최종 판정이 된다.
    const done = REMAINING_BUDGET === 0;
    const remaining = RETIRED.filter((r) => exists(r.path)).map((r) => r.path);
    if (!done) {
      expect(remaining.length).toBe(REMAINING_BUDGET);
      return;
    }
    expect(remaining).toEqual([]);
    expect(exists("components/workbench/StepList.tsx")).toBe(true);
    expect(exists("components/workbench/StepDetail.tsx")).toBe(true);
  });

  it("삭제된 구현을 참조하는 곳이 없다 — 참조가 남으면 이행이 끝나지 않았다", () => {
    const dangling: string[] = [];
    for (const r of RETIRED) {
      if (exists(r.path)) continue; // 아직 삭제 전이면 위 검사가 잡는다
      const base = r.path.replace(/\.tsx?$/, "");
      const refs = referencedFrom(base.split("/").pop()!);
      if (refs.length > 0) dangling.push(`${base} ← ${refs.join(", ")}`);
    }
    expect(dangling).toEqual([]);
  });
});
