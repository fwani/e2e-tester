/**
 * 세션 상태를 화면이 읽는 **유일한 판정 지점** (005 Phase 12 · FR-168·FR-169).
 *
 * 재점검 리포트 N-02 가 본 것 — 목록 행의 칩은 실행이 끝난 뒤에도 `RUNNING`·「실행 중」에
 * 고착됐고, **같은 화면**의 세션 배너는 「실패」로 갱신됐다. 배너와 행이 다른 말을 했다.
 *
 * 원인은 행이 세션의 **상태**를 보지 않고 **존재**를 봤다는 것이다
 * (`activeSessions.find(...) !== null`). 실행이 끝나도 세션은 `failed`·`review` 로 등록에
 * 남으므로 그 조건은 계속 참이었다. 등록 여부와 실행 여부는 다른 축이고, 005 는 이미
 * 백엔드에서 같은 착오를 고쳤다 — `active_session_for_test` 가 등록이 아니라 생존을
 * 세게 한 것이 FR-124 였다. 화면 쪽 절반이 남아 있었다.
 *
 * `SessionScreen.tsx` 는 자기 화면 선택을 위해 더 세분된 집합(조작·관찰·종료)을 갖는다.
 * 여기 있는 것은 **여러 화면이 함께 묻는 질문**이며, 목록과 세션 화면이 각자 답을 만들면
 * 지금 고치는 어긋남이 그대로 되살아난다.
 */

import type { SessionState } from "../api/client";

/**
 * 지금 Step 이 돌고 있는가.
 *
 * `paused`·`ai_blocked` 는 **아니다** — 세션은 열려 있지만 아무것도 진행되지 않고,
 * 사용자의 다음 조작을 기다린다. 그것을 「실행 중」이라고 부르면 사용자는 기다리면
 * 끝난다고 읽는다.
 *
 * `starting` 은 포함한다. 브라우저를 띄우는 약 1초 동안도 사용자가 건 실행이 진행
 * 중이며, 그 사실이 행에서 사라지면 연타로 이어진다 (U-11).
 */
export function isRunning(state: SessionState): boolean {
  switch (state) {
    case "starting":
    case "recording":
    case "replaying":
    case "ai_running":
    case "takeover_recording":
      return true;
    case "ai_blocked":
    case "paused":
    case "completed":
    case "failed":
    case "review":
    case "stopped":
    case "lost":
      return false;
  }
}

/*
 * ─── 「돌아갈 수 있는가」를 여기 두지 않는 이유 (T128) ──────────────────────
 *
 * 처음에는 `isResumable(state)` 를 함께 뒀다. `stopped` 를 제외하는 판정이었고, 목록
 * 행의 복귀 수단(「실행 화면 보기」)이 그것을 써야 하는 것처럼 보였다.
 *
 * **그 판정은 성립하지 않는다.** `stopped` 로 가는 유일한 길은 `discard` 이고
 * (`state_machine.py`: `Command.DISCARD → STOPPED`), 그 경로는 세션 등록을 함께
 * 지운다(`sessions.py`: `_WORK.pop(session_id, None)`). 그래서 `GET /api/sessions` 가
 * 돌려주는 목록에 `stopped` 는 **나타날 수 없다.** 목록에 있는 세션은 전부 돌아갈 수
 * 있고, 행의 조건 `liveSession !== null` 이 이미 그 사실을 정확히 말한다.
 *
 * 쓰지 않는 판정 함수를 남기면 다음 사람이 그것을 **이미 적용된 규칙**으로 읽는다.
 * 여기에 없다는 것이 "복귀는 세션 존재로 판정한다" 는 결정의 기록이다.
 *
 * 상태 하나가 등록에 남게 바뀌면 그때 다시 만든다 — 그때는 판정이 실제로 갈린다.
 */
