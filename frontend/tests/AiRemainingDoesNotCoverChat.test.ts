/**
 * **남은 할 일 목록이 대화를 덮지 않는다** (2026-09-30 사용자 보고).
 *
 * ## 보고된 것
 *
 * > 「아직 하지 않은 일 24개 의 부분이 fix 되어 대화를 가린다」
 *
 * ## 왜 그랬나 — **하루 전에 고친 것과 같은 결함이다**
 *
 * `.ai-authoring-content` 는 세로 flex 이고, 그 안에서 **줄어들 수 있는 것은
 * `.ai-timeline`(flex: 1 1 0) 하나뿐**이다. 나머지는 전부 `0 0 auto` 로 자기 내용만큼
 * 자리를 갖는다. 그래서 목록에 상한이 없는 블록이 하나라도 있으면, 그 블록이 길어질 때
 * 생기는 음의 여백을 대화가 전부 먹는다.
 *
 * 2026-09-29 에 `.plan-body` 가 정확히 그랬다 — 21개 항목을 펼쳐 대화가 0까지 줄고
 * 답변 자리가 밀려났다. 그때 `max-height: 40vh` + 자체 스크롤로 고쳤는데, **같은 패널의
 * `.ai-remaining` 에는 그 처방이 가지 않았다.** 24개 × 18px ≈ 500px 이다.
 *
 * 하필 이 블록은 `ai_finished` 에만 뜬다 — 사용자가 다음 지시를 입력하려는 그때다.
 *
 * ## 이 파일이 재는 것
 *
 * 높이는 브라우저의 레이아웃 결과이고 jsdom 은 그것을 계산하지 않는다. 그래서
 * `ChatDoesNotCoverMirror` 와 같은 방식으로 **결과가 아니라 선언**을 잰다 — 상한이
 * 있는가, 넘치는 것을 자기 안에서 처리하는가. 그리고 상한의 **값**은 구조가 아니라
 * 산수이므로 따로 센다 (마지막 describe).
 *
 * 선언은 손으로 쓴 `workspace.css` 에 있으므로 Tailwind 산출이 아니라 그 파일을 읽는다
 * (`ClassExistence` 가 산출 CSS 를 읽는 것과 같은 수단, 다른 원천).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const CSS = readFileSync(
  join(__dirname, "..", "src", "theme", "workspace.css"),
  "utf8",
);

/**
 * 선택자 하나의 선언 블록을 꺼낸다.
 *
 * **찾지 못하면 빈 문자열이 아니라 실패다.** 규칙 이름이 바뀌었는데 검사가 조용히
 * 통과하면 이 파일이 재는 것이 하나도 없다 (`ClassExistence` 머리말의 「가드가 자기
 * 대상을 못 보면 통과는 아무 뜻이 없다」).
 */
function rule(selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const found = new RegExp(`^\\s*${escaped}\\s*\\{([^}]*)\\}`, "m").exec(CSS);
  expect(found, `${selector} 규칙을 찾지 못했다 — 이름이 바뀌었거나 사라졌다`).not.toBeNull();
  return (found as RegExpExecArray)[1] as string;
}

/** `max-height: 20vh` 같은 선언에서 vh 값을 읽는다. 없으면 null. */
function maxHeightVh(declarations: string): number | null {
  const found = /max-height:\s*([\d.]+)vh/.exec(declarations);
  return found === null ? null : Number.parseFloat(found[1] as string);
}

describe("남은 할 일 목록", () => {
  it("높이 상한이 있다 — 없으면 항목 수만큼 대화를 밀어낸다", () => {
    expect(maxHeightVh(rule(".ai-remaining ol"))).not.toBeNull();
  });

  it("넘치는 것을 자기 안에서 처리한다", () => {
    const declarations = rule(".ai-remaining ol");
    expect(/overflow-y:\s*(auto|scroll)/.test(declarations)).toBe(true);
    // 상한에 닿았을 때 목록의 스크롤이 바깥 대화로 새지 않는다.
    expect(/overscroll-behavior:\s*contain/.test(declarations)).toBe(true);
  });

  it("블록 자체도 줄어들 수 있다", () => {
    // 목록에 상한을 줘도 바깥이 `0 0 auto` 면 그 상한까지는 통째로 자리를 갖는다.
    const declarations = rule(".ai-remaining");
    const shrink = /flex:\s*\d+\s+(\d+)/.exec(declarations);
    expect(shrink, ".ai-remaining 에 flex 선언이 없다").not.toBeNull();
    expect((shrink as RegExpExecArray)[1]).not.toBe("0");
  });
});

describe("상한의 값 — 구조가 옳아도 산수가 틀리면 눌린다", () => {
  /**
   * 같은 패널에서 자리를 갖는 두 목록이다. 둘 다 펼쳐질 수 있으므로 **합**을 본다.
   *
   * 나머지 자리(상태 줄·머리줄·채팅 `min-height: 210px`)가 이미 상당하므로, 두 목록의
   * 합이 화면의 절반을 넘으면 `.ai-timeline` 이 `min-height: 48px` 까지 눌린다 —
   * 그것이 보고된 상태다.
   */
  it("남은 할 일과 작업 계획의 상한 합이 화면 절반을 넘지 않는다", () => {
    const remaining = maxHeightVh(rule(".ai-remaining ol"));
    const plan = maxHeightVh(rule(".plan-body"));
    expect(remaining, "남은 할 일에 vh 상한이 없다").not.toBeNull();
    expect(plan, "작업 계획에 vh 상한이 없다").not.toBeNull();
    expect((remaining as number) + (plan as number)).toBeLessThanOrEqual(60);
  });

  it("남은 할 일이 작업 계획보다 크지 않다", () => {
    // 이쪽은 「몇 개가 남았다」를 알리는 경고이고, 항목을 훑는 자리는 작업 계획이다.
    expect(maxHeightVh(rule(".ai-remaining ol")) as number).toBeLessThanOrEqual(
      maxHeightVh(rule(".plan-body")) as number,
    );
  });
});
