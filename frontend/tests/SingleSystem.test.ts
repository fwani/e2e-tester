/**
 * 가드 G-C — 한 요소에 **두 체계가 겹치지 않는가.** 015 T011.
 *
 * ## 왜 겹치면 안 되나
 *
 * `tokens.css` 머리주석이 특이도 사고 둘을 기록하고 있다. `.tint-*` 가 (0,1,0) 싸움에서
 * 져 **모든 토스트가 흰색**이 됐던 일, 기준 크기(`flex-basis`)가 `height` 를 이겨 두 줄
 * 알림이 잘렸던 일. 둘 다 규칙 둘이 같은 속성을 다툰 결과다.
 *
 * Tailwind 를 얹으면 다투는 규칙이 하나 더 늘어난다. **우선순위를 이해하는 것보다
 * 겹치지 않는 것이 안전하다** (contracts/layout-contract-v2.md LC-5).
 *
 * ## 이 가드는 진행률 계기이기도 하다
 *
 * 전환이 끝나면 의미 클래스가 사라지므로 겹칠 것이 없어진다. 그때까지 이 수치는
 * **아직 한 발을 옛 체계에 걸치고 있는 요소의 수**다.
 */
import { describe, expect, it } from "vitest";

import { canonClasses, classNameGroups, generatedClasses } from "./helpers/tailwind";

describe("G-C — 한 요소는 한 체계만 쓴다", () => {
  const canon = canonClasses();
  const generated = generatedClasses();
  const groups = classNameGroups();

  /**
   * 「Tailwind 유틸리티인가」를 **형태로 판정하지 않는다.** 1회차에 어간 목록으로 갈랐다가
   * 정본 클래스 `.grid-head` 를 `grid-*` 유틸리티로 잘못 봤다. 이름 규칙은 우리가 정하는
   * 것이 아니므로 추측할 수 없고, Tailwind 가 실제로 만든 것만이 답이다.
   */
  const isUtility = (n: string): boolean => generated.has(n) && !canon.has(n);

  it("`className` 을 읽는다 (검사가 헛돌지 않는다)", () => {
    expect(groups.length, "className 을 하나도 읽지 못했다 — 파서가 깨졌다").toBeGreaterThan(50);
  });

  it("의미 클래스와 Tailwind 유틸리티가 같은 요소에 겹치지 않는다", () => {
    const mixed = groups
      .filter((g) => g.names.some((n) => canon.has(n)) && g.names.some(isUtility))
      .map((g) => `  ${g.file}:${g.line}  ${g.names.join(" ")}`);

    expect(
      mixed,
      "한 요소에 의미 클래스와 Tailwind 유틸리티가 함께 걸려 있다.\n" +
        "특이도 다툼이 생긴다 — tokens.css 주석이 기록한 두 사고와 같은 형태다 (LC-5).\n" +
        "그 요소를 한 체계로 끝까지 옮긴다.\n" +
        mixed.join("\n"),
    ).toEqual([]);
  });

  it("정본 클래스명과 Tailwind 유틸리티명이 충돌하지 않는다 (계약 C-7)", () => {
    // 같은 이름이 두 가지를 뜻하면 어느 쪽이 적용되는지 읽는 사람이 알 수 없다.
    // 착수 시점 실측은 `.table` 1개. 해체하면서 부품 이름을 다르게 준다.
    const clash = Array.from(canon).filter((c) => generated.has(c)).sort();
    expect(
      clash,
      "정본 클래스 이름이 Tailwind 유틸리티와 겹친다 (C-7).\n" +
        "해체할 때 부품 이름을 다르게 준다.\n" +
        clash.map((c) => `  .${c}`).join("\n"),
    ).toEqual(["table"]);
  });
});
