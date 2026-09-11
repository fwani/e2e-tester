/**
 * 가드 G-E — 한 요소에 **같은 속성을 두 번 선언하지 않는다.** 015 T076.
 *
 * ## 이 가드가 없어서 흰 버튼이 나왔다
 *
 * 2026-09-11 사용자 신고: 「버튼과 글자가 모두 흰색이라 안 보인다」. `ui/Button` 의
 * primary 버튼이 **흰 배경 위의 흰 글자**로 그려지고 있었다.
 *
 *     BASE     = "… bg-panel text-ink …"
 *     VARIANT.primary = "bg-ink border-ink text-panel …"
 *
 * 두 배경이 동시에 붙었고, `bg-ink` 를 나중에 적었으니 이길 것 같지만 지지 않는다 —
 * **CSS 는 `class` 속성의 순서를 보지 않는다.** 특이도가 같으면 산출 CSS 에서 뒤에
 * 오는 규칙이 이기고, Tailwind 는 그 순서를 자기 규칙대로 정한다. 실측:
 *
 *     .bg-ink   @7152   ← 진다
 *     .bg-panel @7188   ← 이긴다
 *
 * 배경은 `bg-panel`(흰색)로, 글자는 `text-panel`(흰색)로 그려졌다. 글자 쪽이 「의도대로」
 * 된 것은 운이었을 뿐이고, 같은 함정에서 danger 버튼은 **테두리도 글자도 빨갛지 않았다.**
 *
 * ## 왜 눈으로도 테스트로도 안 잡혔나
 *
 * `toHaveClass("bg-ink")` 는 통과한다. 클래스는 실제로 붙어 있기 때문이다. G-B 도
 * 통과한다. `bg-ink` 는 실재하는 유틸리티이기 때문이다. **둘 다 사실이고, 화면만 틀렸다.**
 * 빠진 질문은 「이 요소에 배경이 몇 개 붙었는가」였다.
 *
 * ## 무엇을 실패로 보는가 — 「나중에 적은 쪽이 진다」
 *
 * 같은 속성이 두 번 붙었더라도, **나중에 적은 쪽이 CSS 에서도 이기면** 화면은 적은
 * 대로 나온다. 그것까지 실패로 보면 Tailwind 의 정상 조합(`border border-dashed`,
 * `outline outline-2` — 뒤엣것이 앞엣것을 다듬는 형태)이 전부 걸린다.
 *
 * 그래서 **의도 역전**만 실패로 본다: 나중에 적은 유틸리티가 산출 CSS 에서 지는 경우다.
 * 그것이 곧 「적은 대로 그려지지 않는다」이며, 흰 버튼이 그것이었다. 실측 65곳 중
 * 43곳이 역전이었다.
 *
 * **한계를 적어 둔다.** 역전이 아닌 중복(우연히 맞게 그려지는 것)은 통과한다. 화면은
 * 지금 옳지만 승부가 Tailwind 의 정렬 규칙에 달려 있어 판이 올라가면 뒤집힐 수 있다.
 * 그 목록은 실패 메시지에 참고로 함께 싣는다 — 검사를 통과시키되 숨기지는 않는다.
 *
 * 고치는 방법은 **지우는 것**이다. 어느 쪽을 남길지는 전환 전 화면이 정한다.
 *
 * ## 두 갈래를 본다
 *
 * 1. **리터럴** — `className="…"` 과 부품의 클래스 상수 하나하나.
 * 2. **조립** — `[BASE, SIZE[size], VARIANT[variant]].filter(Boolean).join(" ")` 의
 *    조합 전부. 흰 버튼은 여기에만 나타난다. ①만으로는 영원히 못 본다.
 */
import { describe, expect, it } from "vitest";

import { canonClasses, classNameGroups, composedClassGroups, splitVariant, utilityDeclarations } from "./helpers/tailwind";

interface Conflict {
  readonly where: string;
  readonly key: string;
  readonly names: string[];
  readonly winner: string;
  readonly lastWritten: string;
}

/** 한 덩어리 안에서 같은 (변형, 속성) 을 다투는 유틸리티를 찾는다. */
function conflictsIn(names: readonly string[], where: string): Conflict[] {
  const decls = utilityDeclarations();
  const canon = canonClasses();
  const byKey = new Map<string, { name: string; idx: number; order: number }[]>();
  names.forEach((name, idx) => {
    // 정본 의미 클래스는 이 가드의 관할이 아니다 — 공존 자체를 G-C 가 막는다.
    if (canon.has(name)) return;
    const d = decls.get(name);
    if (d === undefined) return;
    const { variant } = splitVariant(name);
    for (const prop of d.props) {
      const key = `${variant}|${prop}`;
      let list = byKey.get(key);
      if (list === undefined) {
        list = [];
        byKey.set(key, list);
      }
      if (!list.some((x) => x.name === name)) list.push({ name, idx, order: d.order });
    }
  });
  const out: Conflict[] = [];
  for (const [key, list] of byKey) {
    if (list.length < 2) continue;
    const winner = list.reduce((a, b) => (b.order > a.order ? b : a));
    const lastWritten = list.reduce((a, b) => (b.idx > a.idx ? b : a));
    out.push({ where, key, names: list.map((x) => x.name), winner: winner.name, lastWritten: lastWritten.name });
  }
  return out;
}

/** 나중에 적은 쪽이 지는 것 — 적은 대로 그려지지 않는다. */
function inverted(list: readonly Conflict[]): Conflict[] {
  return list.filter((c) => c.winner !== c.lastWritten);
}

function render(list: readonly Conflict[]): string {
  return Array.from(
    new Set(
      list.map((c) => {
        const flag = c.winner === c.lastWritten ? "  " : "✗ ";
        return `  ${flag}${c.where}  [${c.key}]  ${c.names.join(" vs ")}  → CSS 승자 ${c.winner}`;
      }),
    ),
  )
    .sort()
    .join("\n");
}

const ADVICE =
  "한 요소에 같은 속성을 선언하는 유틸리티가 둘 이상 붙어 있다.\n" +
  "`className` 의 순서는 승부를 정하지 않는다 — 산출 CSS 의 순서가 정하고, 그것은\n" +
  "Tailwind 가 정한다. `✗` 표시는 **나중에 적은 쪽이 지고 있다**는 뜻이며 대개 회귀다.\n" +
  "고치는 방법은 지는 쪽이 아니라 **필요 없는 쪽을 지우는 것**이다. 어느 쪽이 필요한지는\n" +
  "전환 전 화면이 정한다 (git 으로 그 요소의 옛 `className` 과 인라인 `style` 을 본다).\n";

describe("G-E — 한 요소에 같은 속성이 두 번 붙지 않는다", () => {
  const literals = classNameGroups();
  const composed = composedClassGroups();

  it("검사가 헛돌지 않는다 — 유틸리티 선언·리터럴·조립을 모두 읽는다", () => {
    expect(utilityDeclarations().size, "유틸리티 선언을 읽지 못했다").toBeGreaterThan(100);
    expect(literals.length, "className 리터럴을 읽지 못했다").toBeGreaterThan(50);
    expect(composed.length, "조립된 클래스 조합을 읽지 못했다 — 부품을 보지 못하고 있다").toBeGreaterThan(20);
  });

  it("일부러 겹치면 잡는다 (실효성 확인)", () => {
    // 흰 버튼과 같은 형태 — `bg-ink` 를 뒤에 적었지만 `.bg-panel` 이 산출 CSS 에서 뒤에 온다.
    const bad = inverted(conflictsIn(["bg-panel", "text-ink", "bg-ink"], "probe"));
    expect(bad.map((c) => c.key)).toContain("|background-color");
    // 겹치지 않는 조합은 조용해야 한다 — 아무거나 잡는 검사는 검사가 아니다.
    expect(inverted(conflictsIn(["bg-panel", "text-ink", "rounded-base"], "probe"))).toEqual([]);
    // 정상 조합(뒤엣것이 앞엣것을 다듬는 형태)은 통과해야 한다.
    expect(inverted(conflictsIn(["border", "border-hair-2", "border-dashed"], "probe"))).toEqual([]);
  });

  it("`className` 리터럴이 적은 대로 그려진다", () => {
    const all = literals.flatMap((g) => conflictsIn(g.names, `${g.file}:${g.line}`));
    const bad = inverted(all);
    expect(bad.map((c) => `${c.where} [${c.key}]`).sort(), `${ADVICE}\n${render(all)}`).toEqual([]);
  });

  it("부품이 조립하는 조합이 적은 대로 그려진다", () => {
    const all = composed.flatMap((g) => conflictsIn(g.names, `${g.file}:${g.line}`));
    const bad = inverted(all);
    expect(bad.map((c) => `${c.where} [${c.key}]`).sort(), `${ADVICE}\n${render(all)}`).toEqual([]);
  });
});
