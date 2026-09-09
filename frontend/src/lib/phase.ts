/**
 * 국면 판정의 **유일한 지점** (007 T006 · data-model.md §1).
 *
 * 사용자가 제기한 문제는 "측정·실행·결과보기·편집 페이지가 다 달라서" 였다. 그 네 개는
 * 실제로 **여덟 국면**이다 (2회차에 만들기가 들어왔다). 007 이전에는 국면마다 다른 화면
 * 컴포넌트가 자기 조건으로 자기를 골랐다. 조건이 흩어져 있으면 한 곳이 빠지고, 빠진
 * 자리에서 화면이 다른 것을 주장한다.
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
 * 한 테스트를 놓고 사용자가 지금 있는 위치. 여덟이다.
 *
 * 사용자가 말한 "측정" 은 `recording` · `ai_authoring` · `takeover` 세 국면을 함께
 * 가리킨다.
 */
export type Phase =
  /**
   * 만들기 — 시작 주소를 정하고 만드는 방법을 고른다 (2회차 · FR-217b·FR-258).
   *
   * 세션도 저장된 테스트도 Step 도 없다. **그것이 화면을 갈아탈 이유가 되지 못한다** —
   * 편집 국면도 세션이 없고 같은 껍데기를 쓴다. 1회차는 이 위치를 「일곱 국면에 속하지
   * 않는다」고 판정해 별도 화면 둘(`CreateTest` 1000px 가운데 정렬 · `AiCompose`)로
   * 두었고, 그 결과 한 번의 「테스트를 만든다」 안에서 껍데기가 두 번 바뀌었다 (S-14).
   */
  | "composing"
  /** 녹화 — 사람이 대상 앱을 조작해 Step 을 만든다 */
  | "recording"
  /** AI 작성 — AI 가 지시문대로 Step 을 만든다 */
  | "ai_authoring"
  /** 사람이 직접 조작 — AI 가 막힌 자리를 사람이 이어받는다 */
  | "takeover"
  /** 실행 중 — 저장된 테스트를 재생한다 */
  | "running"
  /** 일시정지 — 세션이 **살아 있는 채로** 멈춰 있고 편집·저장을 받는다 */
  | "paused"
  /**
   * 검토 — 기록을 확인하고 고치고 저장한다. **브라우저는 이미 닫혔다.**
   *
   * 사용자가 「녹화 확인중」이라고 부른 위치다 (2026-09-09). 서버 상태 `review`(중지 후)
   * 와 `lost`(세션 유실)가 여기 온다.
   *
   * **`paused` 에서 갈라냈다.** 1회차는 `paused`·`review`·`lost` 셋을 한 국면으로 봤고
   * (005 DR-010·DR-015), 「멈춰 있고 편집·저장을 받는다」는 성질은 실제로 같았다. 갈라내는
   * 이유는 **성질이 아니라 조작 목록**이다. 검토에는 브라우저가 없으므로 「계속하기」·
   * 「건너뛰고 계속」·「직접 조작으로 Step 추가」·「실행 속도」가 성립하지 않는다. 한
   * 국면으로 두면 그 넷이 조건 C2 로 잠긴 채 자리를 지키고, 실측에서 검토 화면의 조작
   * 자리 24개 중 14개가 그렇게 비활성이었다.
   *
   * 서버도 이 둘을 이미 갈라 본다 — `state_machine.py` 의 `REVIEW` 는 `EDIT_STEPS`·
   * `SAVE`·`DISCARD` 만 받고 실행 명령을 받지 않는다.
   */
  | "review"
  /**
   * 실행 종료 — 결말을 보고, 다시 실행하거나 저장한다. **세션은 남아 있고 편집은 닫혔다.**
   *
   * 사용자가 「결과 조회중」이라고 부른 위치다. 서버 상태 `completed`·`failed`·`stopped`
   * 가 여기 온다.
   *
   * **`running` 에서 갈라냈다.** 1회차는 끝난 세션도 `running` 으로 판정했고 표시만
   * 「실행 종료」로 바꿨다 (`wording.ts` 의 `sessionPhaseLabel`). 그 주석은 「끝난 실행에서
   * 무엇을 할 수 있는지는 지금 표가 정확히 말하고 있다」고 적었지만 **그렇지 않았다** —
   * 실측에서 끝난 실행의 편집 조작 11개가 「실행 중이어서 편집할 수 없습니다 → 일시정지」
   * 를 달고 있었다. 실행은 이미 끝났고 그 「일시정지」 버튼도 화면에 없다. 화면이 사용자에게
   * 거짓을 말하는 상태이며, 국면 판정이 뭉개져 있는 한 문구만으로는 고칠 수 없다.
   *
   * 서버도 이 상태에서 편집 명령을 받지 않는다 — `state_machine.py` 의 `COMPLETED`·
   * `FAILED`·`STOPPED` 는 전이표가 비어 있다. **저장은 예외로 받는다** (`save` 는 상태
   * 전이를 거치지 않고 Step 유무만 본다) — AI 작성이 끝까지 성공한 세션을 저장할 수
   * 있어야 하므로 그것이 옳고, 그래서 이 국면의 `save` 는 살아 있다.
   */
  | "finished"
  /** 결과보기 — 저장된 테스트의 지난 실행 결말과 산출물 (세션 없음) */
  | "result"
  /** 편집 — 세션 없이 정의를 고친다 */
  | "editing";

export const PHASES: Phase[] = [
  "composing",
  "recording",
  "ai_authoring",
  "takeover",
  "running",
  "paused",
  "review",
  "finished",
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
  "review",
  "finished",
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
const PAUSED_STATES: SessionState[] = ["paused"];

/**
 * 검토 국면의 상태 — 멈췄고 **브라우저가 없다.**
 *
 * `review` 와 `lost` 를 `paused` 에서 갈라낸 것이 2026-09-09 의 수정이다. 근거는 위
 * `Phase.review` 의 주석에 있다 — 성질은 같지만 **조작 목록이 다르다.**
 */
const REVIEW_STATES: SessionState[] = ["review", "lost"];

/** 실행이 끝난 상태 — 세션은 남아 있고 편집은 닫혔다. */
const FINISHED_STATES: SessionState[] = ["completed", "failed", "stopped"];

/** 사람이 AI 를 이어받은 상태. */
const TAKEOVER_STATES: SessionState[] = ["takeover_recording", "ai_blocked"];

/**
 * 세션에서 국면을 정한다.
 *
 * **`composing` 은 여기서 나오지 않는다.** 세션이 생기는 순간 이미 다른 국면이므로
 * (녹화 또는 AI 작성) 이 함수는 2회차에도 그대로다 (research R10). 만들기 국면은
 * 「세션이 아직 없다」는 위치이며 세션에서 판정할 대상이 아니다.
 *
 * **판정 순서가 있다.** `takeover_recording` 은 AI 세션의 상태이면서 사람이 조작하는
 * 국면이다. 한 세션이 두 조건을 동시에 만족하므로 순서 없이는 답이 갈린다. 아래 순서는
 * 지금 `SessionScreen` 의 분기 순서(`isPaused` → `isTakeover` → `showsAiScreen`)와
 * 같은 결론을 낸다 — 007 이 국면 판정을 옮기면서 동작을 바꾸지 않는다는 뜻이다.
 */
export function phaseOfSession(view: SessionView): Phase {
  /*
    **끝난 것을 먼저 본다.** 이 두 줄이 2026-09-09 에 들어왔고, 순서가 위인 것이 요점이다 —
    아래 `authoring_mode === "ai"` 보다 뒤에 두면 AI 세션이 끝난 뒤에도 「AI 작성 중」으로
    판정되고, 그것이 001 research R2 가 규명한 결함의 형태다.
  */
  if (REVIEW_STATES.includes(view.state)) return "review";
  if (FINISHED_STATES.includes(view.state)) return "finished";
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
