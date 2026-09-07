/**
 * 국면 판정의 **유일한 지점** (007 T006 · data-model.md §1).
 *
 * 사용자가 제기한 문제는 "측정·실행·결과보기·편집 페이지가 다 달라서" 였다. 그 네 개는
 * 실제로 **일곱 국면**이고, 지금은 국면마다 다른 화면 컴포넌트가 자기 조건으로 자기를
 * 고른다. 조건이 흩어져 있으면 한 곳이 빠지고, 빠진 자리에서 화면이 다른 것을 주장한다.
 *
 * **AI 세션 판정은 `authoring_mode` 로 한다 — `state` 가 아니다.** 001 DR-020 이 세운
 * 규칙이고 이유는 실측이다: AI 가 실패해 `paused` 로 바뀌는 순간 화면이 AI 세션임을 잊고
 * 실패 사유를 그리는 컴포넌트가 조건 뒤로 숨었다 (001 research R2 — "AI 로 만들기
 * 무반응"). `authoring_mode` 는 세션의 불변 속성이므로 상태가 바뀌어도 유지된다.
 *
 * 이 파일은 **판정만 한다.** 국면이 무엇을 할 수 있는지는 `capabilities.ts` 가 갖는다.
 */

import type { SessionState, SessionView } from "../api/client";

/**
 * 한 테스트를 놓고 사용자가 지금 있는 위치. 일곱이다.
 *
 * 사용자가 말한 "측정" 은 `recording` · `ai_authoring` · `takeover` 세 국면을 함께
 * 가리킨다.
 */
export type Phase =
  /** 녹화 — 사람이 대상 앱을 조작해 Step 을 만든다 */
  | "recording"
  /** AI 작성 — AI 가 지시문대로 Step 을 만든다 */
  | "ai_authoring"
  /** 사람이 직접 조작 — AI 가 막힌 자리를 사람이 이어받는다 */
  | "takeover"
  /** 실행 중 — 저장된 테스트를 재생한다 */
  | "running"
  /** 일시정지 / 검토 — 세션이 멈춰 있고 편집·저장을 받는다 */
  | "paused"
  /** 결과보기 — 끝난 실행의 결말과 산출물 */
  | "result"
  /** 편집 — 세션 없이 정의를 고친다 */
  | "editing";

export const PHASES: Phase[] = [
  "recording",
  "ai_authoring",
  "takeover",
  "running",
  "paused",
  "result",
  "editing",
];

/** 세션이 있어야 성립하는 국면. */
export const SESSION_PHASES: Phase[] = [
  "recording",
  "ai_authoring",
  "takeover",
  "running",
  "paused",
];

export function isSessionPhase(phase: Phase): boolean {
  return SESSION_PHASES.includes(phase);
}

/**
 * 세션이 멈춰 있는 상태 — 브라우저가 있을 수도, 이미 없을 수도 있다.
 *
 * `review` 와 `lost` 를 여기 넣는 것이 005 DR-010·DR-015 의 결정이다. 브라우저는 없지만
 * 기록된 Step 을 보고 고치고 저장할 수 있어야 한다 — 001 에서는 중지하는 순간 목록으로
 * 튕겨 나가 기록이 통째로 유실됐다.
 */
const PAUSED_STATES: SessionState[] = ["paused", "review", "lost"];

/** 사람이 AI 를 이어받은 상태. */
const TAKEOVER_STATES: SessionState[] = ["takeover_recording", "ai_blocked"];

/**
 * 세션에서 국면을 정한다.
 *
 * **판정 순서가 있다.** `takeover_recording` 은 AI 세션의 상태이면서 사람이 조작하는
 * 국면이다. 한 세션이 두 조건을 동시에 만족하므로 순서 없이는 답이 갈린다. 아래 순서는
 * 지금 `SessionScreen` 의 분기 순서(`isPaused` → `isTakeover` → `showsAiScreen`)와
 * 같은 결론을 낸다 — 007 이 국면 판정을 옮기면서 동작을 바꾸지 않는다는 뜻이다.
 */
export function phaseOfSession(view: SessionView): Phase {
  if (PAUSED_STATES.includes(view.state)) return "paused";
  if (TAKEOVER_STATES.includes(view.state)) return "takeover";
  if (view.authoring_mode === "ai") return "ai_authoring";
  if (view.state === "recording") return "recording";
  return "running";
}

/**
 * 그 국면의 브라우저 세션이 **살아 있는가** (ui-contract §3-5 의 조건 C2).
 *
 * `paused` 국면 안에서 갈린다 — 일시정지는 브라우저가 있고, 검토(`review`)와
 * 유실(`lost`)은 없다. 상태 이름만으로는 구별되지 않으므로 판정을 여기 둔다.
 */
export function hasLiveBrowser(view: SessionView | null): boolean {
  if (view === null) return false;
  switch (view.state) {
    case "starting":
    case "recording":
    case "replaying":
    case "ai_running":
    case "ai_blocked":
    case "takeover_recording":
    case "paused":
      return true;
    case "completed":
    case "failed":
    case "review":
    case "stopped":
    case "lost":
      return false;
  }
}

/**
 * 그 세션이 **끝났는가** (조건 C1).
 *
 * 끝난 세션에서는 새 실행을 걸 수 있다. 열려 있는 세션에서는 거절된다 — 그 거절이
 * 005 U-01 이었고, 화면이 그 사실을 미리 말하지 않아 사용자는 항상 409 를 받았다.
 */
export function isFinished(view: SessionView | null): boolean {
  if (view === null) return true;
  switch (view.state) {
    case "completed":
    case "failed":
    case "review":
    case "stopped":
    case "lost":
      return true;
    default:
      return false;
  }
}
