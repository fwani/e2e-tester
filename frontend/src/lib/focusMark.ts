/**
 * AI 가 만진 자리를 **지금 그릴 수 있는가** (024 research R8 의 판정 표).
 *
 * ## 왜 화면 컴포넌트 밖에 있는가
 *
 * 판정이 한 곳에 모여야 한다. `capabilities.ts` 가 「미러에서 조작할 수 있는가」에 대해
 * 세운 구조와 같다 (010 FR-316) — 컴포넌트가 스스로 국면을 보면 판정이 둘로 갈리고,
 * 갈리는 날 화면은 그릴 수 있다고 그리고 좌표는 틀린다.
 *
 * 순수 함수인 것은 **표와 검증을 1:1 로 맞추기 위해서**다. `SessionScreen` 안에
 * 인라인으로 두면 그 거대한 화면을 통째로 그려야 한 줄을 잴 수 있고, 그러면 표의 한 줄이
 * 빠져도 아무도 모른다.
 *
 * ## 여기서 보지 않는 것
 *
 * **좌표 근거가 없는 경우와 표시 영역 밖인 경우는 변환이 판정한다** (`toDisplayRect` 가
 * `null` 을 준다 · FR-017·FR-019). 두 곳에서 같은 판정을 하면 갈릴 자리가 생긴다.
 */

/** 서버가 알려 온 자리 하나. 받은 시각을 함께 든다 (024 data-model §7). */
export interface FocusMark {
  tab: number;
  rect: { x: number; y: number; width: number; height: number };
  status: "done" | "failed";
  label: string;
  /** 받은 시각. 수명 계산의 기준 */
  at: number;
}

/** 지금 화면이 아는 사실들. 판정의 입력이며, 여기 없는 것은 판정에 쓰이지 않는다. */
export interface FocusFacts {
  /** 미러에 그림이 있는가. 한 장도 못 받았으면 거짓 */
  hasFrame: boolean;
  /** 미러가 중단됐는가 */
  stopped: boolean;
  /** 지금 보고 있는 탭 */
  viewingTab: number;
}

/**
 * 표시할 시간 (024 FR-015 · research R6).
 *
 * **화면이 센다.** 서버가 「지워라」를 보내지 않는다 — 그 이벤트가 유실되면 테두리가
 * 영구히 남는다. 프레임 유실이 실행에 영향을 주지 않아야 한다는 미러의 기존 성질과 같은
 * 이유로, 표시는 스스로 꺼지는 쪽이어야 한다.
 *
 * 값의 근거: 1초면 AI 의 동작 간격(도구 호출 왕복)보다 짧아 대부분의 시간 동안 아무것도
 * 안 보이고, 5초면 막힘 화면이 뜬 뒤에도 테두리가 남아 「아직 하는 중」으로 읽힌다.
 * **최적값을 아는 상태가 아니다** — 이름 붙인 상수 하나로 두어 실측 후 한 곳만 고친다.
 */
export const FOCUS_MARK_TTL_MS = 2500;

/** 미러에 넘길 것. 그리지 않을 상황이면 `null` */
export interface FocusToDraw {
  rect: { x: number; y: number; width: number; height: number };
  status: "done" | "failed";
  label: string;
}

/**
 * research R8 의 판정 표를 그대로 옮긴 것.
 *
 * | 조건 | 그리는가 | 근거 |
 * |---|---|---|
 * | 자리를 받은 적이 없다 | ✕ | — |
 * | 프레임을 한 장도 못 받았다 | ✕ | FR-016 |
 * | 미러가 중단됐다 | ✕ | FR-016 — 멈춘 그림 위의 자리는 지금이 아니다 |
 * | 알림의 탭 ≠ 보고 있는 탭 | ✕ | FR-018 |
 * | 표시할 시간이 지났다 | ✕ | FR-015 |
 * | 그 밖 | ● | |
 *
 * **강등(초당 1장) 상태는 억제하지 않는다.** 테두리가 그림보다 앞서지만 좌표 자체는
 * 옳고, 강등 사실은 이미 미러 상단이 말하고 있다. 그래서 이 함수는 강등을 **입력으로도
 * 받지 않는다** — 받으면 언젠가 그것으로 판정하고 싶어진다.
 */
export function focusToDraw(
  mark: FocusMark | null,
  facts: FocusFacts,
  now: number,
): FocusToDraw | null {
  if (mark === null) return null;
  if (!facts.hasFrame) return null;
  if (facts.stopped) return null;
  if (mark.tab !== facts.viewingTab) return null;
  if (now - mark.at >= FOCUS_MARK_TTL_MS) return null;
  return { rect: mark.rect, status: mark.status, label: mark.label };
}
