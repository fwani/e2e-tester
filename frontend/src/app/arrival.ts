/**
 * 실행 화면의 도착 정보 (018 design §3.3).
 *
 * 옛 `App.tsx` 의 `runner` 화면은 세션 객체와 함께 다섯 가지를 들고 다녔다. 018 은 그것을 성격대로 나눴고,
 * 이 파일은 그중 **`location.state` 에 싣는 셋**을 다룬다.
 *
 * - `aiInstruction` — **기록**이다. 무엇을 시켰는지 화면에 남아야 한다 (001 FR-063 · UX U-07).
 * - `recordOnArrival` · `instructionOnArrival` — **일회성 명령**이다. 도착하면 한 번 수행하고 끝난다
 *   (009 FR-291 · 011 FR-374a).
 *
 * `history.state` 는 새로 고쳐도 남는다. 명령을 지우지 않으면 **새로 고침이 AI 지시문을 다시 수행한다** —
 * 같은 Step 이 두 벌 들어간다. 그래서 실행 화면은 명령을 첫 렌더에 꺼내 두고 기록에서는 지운다.
 */

export interface SessionArrival {
  readonly aiInstruction: string | null;
  readonly recordOnArrival: boolean;
  readonly instructionOnArrival: string | null;
}

export function arrivalState(a: Partial<SessionArrival>): SessionArrival {
  return {
    aiInstruction: a.aiInstruction ?? null,
    recordOnArrival: a.recordOnArrival ?? false,
    instructionOnArrival: a.instructionOnArrival ?? null,
  };
}

/** 기록에 무엇이 있든 모양을 믿지 않고 읽는다 — 다른 판의 앱이 남긴 기록일 수 있다. */
export function readArrival(state: unknown): SessionArrival {
  const s = (typeof state === "object" && state !== null ? state : {}) as Record<string, unknown>;
  return arrivalState({
    aiInstruction: typeof s.aiInstruction === "string" ? s.aiInstruction : null,
    recordOnArrival: s.recordOnArrival === true,
    instructionOnArrival: typeof s.instructionOnArrival === "string" ? s.instructionOnArrival : null,
  });
}

export function hasCommands(state: unknown): boolean {
  const a = readArrival(state);
  return a.recordOnArrival || a.instructionOnArrival !== null;
}

/** 명령만 지운다. 기록(`aiInstruction`)은 남긴다 — 하나로 합치면 수행이 끝난 뒤 기록도 사라진다. */
export function withoutCommands(state: unknown): SessionArrival {
  return { ...readArrival(state), recordOnArrival: false, instructionOnArrival: null };
}
