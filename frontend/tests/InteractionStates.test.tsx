/**
 * 상호작용 상태가 보존되는가 — hover · focus · 선택 · 비활성. 015 T058 (FR-009 · SC-008).
 *
 * ## 왜 자동으로 봐야 하나
 *
 * 015 가 정본을 `layer(base)` 로 내렸다. 그러지 않으면 요소 규칙(`button{…}`)이
 * 유틸리티를 이겨 015 가 통째로 막힌다 ([contracts/tailwind-theme.md] C-8).
 *
 * 그 대가로 **요소 규칙의 상태 스타일도 유틸리티에 진다.** `button:hover` 가 `bg-panel`
 * 에 지면 hover 배경 변화가 사라지는데, **화면은 멀쩡해 보이고 기존 테스트도 통과한다** —
 * 마우스를 올려야만 보인다. `ui/Button` 에서 실제로 그렇게 됐고 손으로 고쳤다 (T016).
 *
 * 부품마다 되풀이될 함정이라 목록을 만들었고
 * ([contracts/state-styles.md]) 이 검사가 그 목록이 실제로 지켜지는지 본다.
 *
 * ## 무엇을 보는가
 *
 * jsdom 은 CSS 를 계산하지 않으므로 **hover 한 모습**을 잴 수 없다. 대신 부품이
 * 그 상태를 **선언했는지**를 본다 — `hover:` · `disabled:` · `focus-within:` 접두사.
 * 선언이 없으면 그 상태에서 아무 일도 일어나지 않는다는 뜻이고, 그것이 FR-009 가
 * 막으려는 회귀다.
 *
 * 클래스가 실제로 CSS 를 만드는지는 가드 G-B 가 따로 본다 (LC-4 의 3겹).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { classNameGroups } from "./helpers/tailwind";

const ROOT = join(__dirname, "..");

/** 한 부품 파일이 선언한 상태 접두사 전부. */
function statesOf(rel: string): Set<string> {
  const groups = classNameGroups().filter((g) => g.file === rel);
  const out = new Set<string>();
  for (const g of groups) {
    for (const n of g.names) {
      const m = /^([a-z-]+):/.exec(n);
      if (m !== null) out.add(m[1] as string);
    }
  }
  return out;
}

describe("상호작용 상태가 보존된다 (FR-009 · state-styles.md)", () => {
  it("`ui/Button` 이 hover·active·disabled 를 갖는다", () => {
    /*
      정본의 `button:hover`(S-01) · `button:active`(S-02) · `button:disabled`(S-03) 가
      여기로 왔다. 하나라도 빠지면 그 상태에서 아무 일도 일어나지 않는다 —
      비활성 버튼이 활성처럼 보이거나, 누를 수 있는 것이 눌리는 느낌을 주지 않는다.
    */
    const s = statesOf("src/ui/Button.tsx");
    for (const state of ["hover", "active", "disabled"]) {
      expect(s.has(state), `Button 에 ${state} 상태 선언이 없다 (state-styles.md S-01~S-03)`).toBe(
        true,
      );
    }
  });

  it("`ui/Field` 의 파일 선택이 초점 링을 그린다", () => {
    /*
      S-16·S-17 — `<label>` 은 초점을 받지 못한다. 안쪽 `<input>` 이 받고 라벨이
      `:focus-within` 으로 링을 그린다. 그 구조가 깨지면 **파일 선택 버튼이
      키보드에서 사라진다** — 마우스로는 아무 차이가 없다.
    */
    /*
      **두 분기를 모두 본다.** `focus-within` 이 하나라도 있으면 통과하게 두었더니
      쓸 수 있는 쪽의 링만 지워도 검사가 초록이었다 — 그 상태에서 키보드 사용자는
      파일 선택 버튼에 초점이 갔는지 알 수 없다.
    */
    const src = readFileSync(join(ROOT, "src/ui/Field.tsx"), "utf8");
    expect(src, "쓸 수 있는 파일 선택에 초점 링이 없다 (S-16)").toContain(
      "focus-within:outline-run",
    );
    expect(src, "쓸 수 없는 파일 선택에 초점 링이 없다 (S-17)").toContain(
      "focus-within:outline-hair-2",
    );
    // 링을 그리려면 `outline` 자체도 켜져 있어야 한다.
    expect(src, "focus-within 에 outline 이 켜지지 않았다").toContain("focus-within:outline-2");
  });

  it("`ui/Field` 의 입력칸이 placeholder·비활성을 갖는다", () => {
    // S-06·S-07 — 옮기지 않으면 비활성 입력칸이 활성처럼 보인다.
    const src = readFileSync(join(ROOT, "src/ui/Field.tsx"), "utf8");
    expect(src, "입력칸 placeholder 색이 없다 (S-06)").toContain("placeholder:text-ink-3");
    expect(src, "비활성 입력칸 표시가 없다 (S-07)").toMatch(/\[&_input:disabled\]|disabled:/);
  });

  it("`ui/Table` 의 탭이 비활성 표시를 갖는다", () => {
    // S-11 — 없으면 비활성 탭이 활성과 구별되지 않는다.
    const src = readFileSync(join(ROOT, "src/ui/Table.tsx"), "utf8");
    expect(src, "비활성 탭 표시가 없다 (S-11)").toContain("[&>button:disabled]");
  });

  it("`ui/StepRow` 의 체크 상자가 비활성 표시를 갖는다", () => {
    // S-13
    const src = readFileSync(join(ROOT, "src/ui/StepRow.tsx"), "utf8");
    expect(src, "비활성 체크 상자 표시가 없다 (S-13)").toContain("[&_input:disabled]");
  });

  it("선택 상태가 다른 채널을 쓴다 — 결말을 덮지 않는다", () => {
    /*
      011 이전에는 결말·일시정지·지목이 `border-left-color` 와 `background` 둘을 다퉜고,
      삼항이 셋을 줄 세워 **언제나 하나만 남았다** — 통과한 Step 을 고르면 결말이
      사라졌다 (사용자 보고 7).

      지금은 결말이 왼쪽 테두리·바탕, 지목이 **안쪽 링**이다. 두 채널이 겹치지 않으므로
      함께 보인다. `shadow-[inset…]` 이 그 링이다.
    */
    const src = readFileSync(join(ROOT, "src/ui/StepRow.tsx"), "utf8");
    expect(src, "지목이 안쪽 링을 쓰지 않는다 — 결말과 채널이 겹친다").toMatch(
      /shadow-\[inset_0_0_0_2px/,
    );
    // 결말 쪽은 테두리·바탕만 쓴다 — 링을 쓰면 채널이 겹친다.
    const markTable = /const MARK: Record<StepMark, string> = \{[\s\S]*?\};/.exec(src)?.[0] ?? "";
    expect(markTable, "결말 표가 비었다 — 검사가 헛돈다").toContain("border-l-");
    expect(markTable, "결말이 지목의 채널(안쪽 링)을 쓴다").not.toContain("shadow-[inset");
  });

  it("검사가 헛돌지 않는다 — 부품 파일을 실제로 읽는다", () => {
    expect(statesOf("src/ui/Button.tsx").size, "Button 에서 상태를 하나도 읽지 못했다").toBeGreaterThan(
      0,
    );
  });
});
