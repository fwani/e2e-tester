/**
 * 믿을 수 없으면 그리지 않는다 (024 US3 · T050·T051·T059b).
 *
 * ## 표와 검증이 1:1 이다
 *
 * [research R8](../../specs/024-ai-focus-overlay/research.md) 의 판정 표가 권위이며,
 * 아래 `SUPPRESSION_TABLE` 이 그 표를 그대로 옮긴 것이다. **한 줄씩 짝지어 두는 이유**는
 * 표에서 한 줄이 빠지거나 코드에서 한 조건이 사라졌을 때 그것이 드러나야 하기 때문이다 —
 * 조건을 뭉쳐 검사하면 어느 줄이 죽었는지 알 수 없다.
 *
 * ## 왜 억제가 이 기능에서 가장 중요한가
 *
 * 이 기능의 값 전부가 「저기가 맞다」는 **믿음**에서 나온다 (US3). 한 번 엉뚱한 자리를
 * 가리키면 그다음부터 사용자는 표시를 믿지 않고, 그러면 기능이 있으나 마나 해진다.
 * **잘못된 자리에 뜬 테두리는 표시가 없는 것보다 나쁘다.**
 */
import { describe, expect, it } from "vitest";

import {
  FOCUS_MARK_TTL_MS,
  focusToDraw,
  type FocusFacts,
  type FocusMark,
} from "../src/lib/focusMark";

const NOW = 1_700_000_000_000;

const MARK: FocusMark = {
  tab: 0,
  rect: { x: 100, y: 200, width: 80, height: 30 },
  status: "done",
  label: "로그인 버튼 클릭",
  at: NOW,
};

/** 아무것도 막지 않는 상태 — 여기서 한 가지씩 무너뜨린다. */
const CLEAR: FocusFacts = { hasFrame: true, stopped: false, viewingTab: 0 };

describe("판정 표를 한 줄씩 (T050 · research R8)", () => {
  const SUPPRESSION_TABLE: Array<{
    row: string;
    basis: string;
    mark: FocusMark | null;
    facts: FocusFacts;
    now: number;
  }> = [
    {
      row: "자리를 받은 적이 없다",
      basis: "—",
      mark: null,
      facts: CLEAR,
      now: NOW,
    },
    {
      row: "프레임을 한 장도 못 받았다",
      basis: "FR-016",
      mark: MARK,
      facts: { ...CLEAR, hasFrame: false },
      now: NOW,
    },
    {
      row: "미러가 중단됐다",
      basis: "FR-016 — 멈춘 그림 위의 자리는 지금이 아니다",
      mark: MARK,
      facts: { ...CLEAR, stopped: true },
      now: NOW,
    },
    {
      row: "알림의 탭 ≠ 보고 있는 탭",
      basis: "FR-018",
      mark: MARK,
      facts: { ...CLEAR, viewingTab: 1 },
      now: NOW,
    },
    {
      row: "표시할 시간이 지났다",
      basis: "FR-015",
      mark: MARK,
      facts: CLEAR,
      now: NOW + FOCUS_MARK_TTL_MS,
    },
  ];

  for (const { row, basis, mark, facts, now } of SUPPRESSION_TABLE) {
    it(`${row} → 그리지 않는다 (${basis})`, () => {
      expect(focusToDraw(mark, facts, now)).toBeNull();
    });
  }

  it("아무것도 막지 않으면 그린다 — 표가 전부를 막고 있지는 않다", () => {
    // 이것이 없으면 위 다섯 줄은 「언제나 null 을 주는 함수」로도 통과한다.
    const drawn = focusToDraw(MARK, CLEAR, NOW);
    expect(drawn).toEqual({ rect: MARK.rect, status: "done", label: MARK.label });
  });
});

describe("수명의 경계 (FR-015)", () => {
  it("시간이 지나기 직전까지는 그린다", () => {
    expect(focusToDraw(MARK, CLEAR, NOW + FOCUS_MARK_TTL_MS - 1)).not.toBeNull();
  });

  it("시간이 꽉 차면 사라진다", () => {
    expect(focusToDraw(MARK, CLEAR, NOW + FOCUS_MARK_TTL_MS)).toBeNull();
  });

  it("한참 지난 자리는 되살아나지 않는다", () => {
    expect(focusToDraw(MARK, CLEAR, NOW + 60_000)).toBeNull();
  });
});

describe("강등 상태는 억제하지 않는다 (T053 · research R8)", () => {
  it("판정이 강등을 입력으로 받지 않는다", () => {
    // 테두리가 그림보다 앞서지만 **좌표 자체는 옳고**, 강등 사실은 이미 미러 상단이
    // 말하고 있다. 입력으로 받으면 언젠가 그것으로 판정하고 싶어진다 — 그래서 아예
    // 받지 않는 것이 이 결정의 구현이다.
    const keys = Object.keys(CLEAR);
    expect(keys).toEqual(["hasFrame", "stopped", "viewingTab"]);
  });
});

describe("화면을 새로 고치면 복원되지 않는다 (T051)", () => {
  it("자리가 없는 상태에서 시작한다", () => {
    // 테두리는 흘러가는 순간의 표시다. 다시 붙었을 때 지나간 자리를 복원하면 과거가
    // 지금처럼 보인다 — 서버가 마지막 자리를 다시 보내지 않는 이유이기도 하다
    // (`mirror_frame` 은 마지막 프레임을 다시 보내지만, 그것은 「지금 화면」이다).
    expect(focusToDraw(null, CLEAR, NOW)).toBeNull();
  });
});

describe("모르는 이벤트를 무시한다 (T059b · FR-026 · contracts §5)", () => {
  /**
   * 필수 필드가 빠진 알림을 받아도 화면이 깨지지 않고 **그리지 않는다.**
   *
   * 부분적으로 해석해 그리면 안 된다 — 좌표가 하나라도 없으면 그린 자리가 틀린다.
   * 옛 서버·손상된 페이로드에서 이 일이 일어날 수 있다.
   */
  const BROKEN: Array<{ name: string; mark: unknown }> = [
    { name: "rect 가 없다", mark: { ...MARK, rect: undefined } },
    { name: "rect 의 좌표가 모자란다", mark: { ...MARK, rect: { x: 1, y: 2 } } },
    { name: "tab 이 없다", mark: { ...MARK, tab: undefined } },
  ];

  for (const { name, mark } of BROKEN) {
    it(`${name} → 그리더라도 좌표 변환이 막는다`, () => {
      // 판정은 통과할 수 있다 (탭이 undefined 면 막힌다). 통과하더라도 `toDisplayRect`
      // 가 수치가 아닌 좌표를 `null` 로 돌려주므로 아무것도 그려지지 않는다 —
      // `MirrorFocusGeometry.test.ts` 가 그 성질을 고정한다.
      const drawn = focusToDraw(mark as FocusMark, CLEAR, NOW);
      if (drawn === null) return;
      const rect = drawn.rect as { x?: number; y?: number } | undefined;
      const usable =
        rect !== undefined &&
        Number.isFinite(rect.x) &&
        Number.isFinite(rect.y) &&
        Number.isFinite((rect as { width?: number }).width) &&
        Number.isFinite((rect as { height?: number }).height);
      expect(usable).toBe(false);
    });
  }
});
