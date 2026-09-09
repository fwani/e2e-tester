/**
 * 007 T007 — 국면 판정 (data-model.md §1).
 *
 * **이 파일이 지키는 것은 판정의 우선순위다.** `takeover_recording` 은 AI 세션의
 * 상태이면서 사람이 조작하는 국면이다. 한 세션이 두 조건을 동시에 만족하므로 순서 없이는
 * 답이 갈린다.
 *
 * 그리고 **AI 세션 판정이 `state` 로 새지 않는지**를 본다. 001 research R2 가 규명한
 * 결함이 그것이었다 — AI 가 실패해 `paused` 로 바뀌는 순간 화면이 AI 세션임을 잊었다.
 */
import { describe, expect, it } from "vitest";

import type { SessionState } from "../src/api/client";
import {
  PHASES,
  hasLiveBrowser,
  isFinished,
  isSessionPhase,
  phaseOfSession,
} from "../src/lib/phase";
import { sessionView } from "./helpers/workbench";

describe("국면 판정 (T006·T007)", () => {
  /**
   * 2회차에 만들기가 들어와 여덟이 됐다 (FR-217b · S-14).
   * 2026-09-09 에 검토·실행 종료가 갈라져 열이 됐다 (사용자 보고 — `phase.ts` 의 주석).
   */
  it("국면은 열이다", () => {
    expect(PHASES).toHaveLength(10);
  });

  it("세션이 없는 국면은 만들기·결과보기·편집 셋이다", () => {
    const withoutSession = PHASES.filter((p) => !isSessionPhase(p));
    expect(withoutSession).toEqual(["composing", "result", "editing"]);
  });

  /**
   * **`composing` 은 세션 판정에서 나오지 않는다** (research R10).
   *
   * 세션이 생기는 순간 이미 다른 국면(녹화 또는 AI 작성)이므로 `phaseOfSession` 은
   * 2회차에도 그대로다. 만들기 국면은 「세션이 아직 없다」는 위치이고 세션에서 판정할
   * 대상이 아니다 — 이 성질이 깨지면 만들기 국면이 살아 있는 세션 위에 그려진다.
   */
  it("세션에서는 만들기 국면이 나오지 않는다", () => {
    const states: SessionState[] = [
      "starting",
      "recording",
      "replaying",
      "ai_running",
      "ai_blocked",
      "takeover_recording",
      "paused",
      "review",
      "lost",
      "completed",
      "failed",
      "stopped",
    ];
    for (const state of states) {
      for (const authoring of ["record", "ai"] as const) {
        const phase = phaseOfSession(sessionView({ state, authoring_mode: authoring }));
        expect(phase, `${state}/${authoring}`).not.toBe("composing");
      }
    }
  });

  const cases: {
    state: SessionState;
    authoring: "record" | "ai";
    expected: string;
    why: string;
  }[] = [
    { state: "replaying", authoring: "record", expected: "running", why: "저장된 테스트 재생" },
    { state: "starting", authoring: "record", expected: "running", why: "브라우저를 띄우는 중" },
    { state: "recording", authoring: "record", expected: "recording", why: "사람이 녹화" },
    { state: "ai_running", authoring: "ai", expected: "ai_authoring", why: "AI 수행 중" },
    { state: "takeover_recording", authoring: "ai", expected: "takeover", why: "사람이 이어받아 녹화" },
    { state: "ai_blocked", authoring: "ai", expected: "takeover", why: "AI 가 막혀 선택을 기다린다" },
    { state: "paused", authoring: "record", expected: "paused", why: "일시정지" },
    /*
      2026-09-09 — **검토가 `paused` 에서 갈라졌다.** 성질(멈췄고 편집·저장을 받는다)은
      DR-010·DR-015 그대로이고, 갈라낸 이유는 조작 목록이다 — 브라우저가 없으므로
      「계속하기」·「건너뛰고 계속」·「직접 조작으로 Step 추가」·「실행 속도」가 성립하지
      않는다. 한 국면으로 두면 그 넷이 잠긴 채 자리를 지켰다.
    */
    { state: "review", authoring: "record", expected: "review", why: "중지 후 검토 (DR-010)" },
    { state: "lost", authoring: "record", expected: "review", why: "유실 — 편집·저장은 받는다 (DR-015)" },
    /*
      끝난 실행은 **`running` 이 아니다** (2026-09-09). 이전에는 `running` 으로 판정하고
      표시만 「실행 종료」로 바꿨는데, 그 국면의 표가 편집 조작 11개에 「실행 중이어서
      편집할 수 없습니다」를 붙였다 — 라벨과 사유가 서로 다른 말을 했다.
    */
    { state: "completed", authoring: "record", expected: "finished", why: "실행이 통과로 끝났다" },
    { state: "failed", authoring: "record", expected: "finished", why: "실행이 실패로 끝났다" },
    { state: "stopped", authoring: "record", expected: "finished", why: "버려진 세션" },
    {
      state: "completed",
      authoring: "ai",
      expected: "finished",
      why: "AI 세션도 끝나면 실행 종료 국면이다 — authoring_mode 가 국면을 되돌리지 않는다",
    },
  ];

  for (const c of cases) {
    it(`${c.state} + ${c.authoring} → ${c.expected} (${c.why})`, () => {
      expect(phaseOfSession(sessionView({ state: c.state, authoring_mode: c.authoring }))).toBe(
        c.expected,
      );
    });
  }

  describe("우선순위 — 두 조건을 동시에 만족하는 세션 (001 DR-020)", () => {
    it("AI 세션이 일시정지되면 paused 다 — ai_authoring 이 아니다", () => {
      const view = sessionView({ state: "paused", authoring_mode: "ai" });
      expect(phaseOfSession(view)).toBe("paused");
    });

    it("AI 세션이 사람에게 넘어가면 takeover 다 — ai_authoring 이 아니다", () => {
      const view = sessionView({ state: "takeover_recording", authoring_mode: "ai" });
      expect(phaseOfSession(view)).toBe("takeover");
    });

    it("AI 세션 여부는 state 가 아니라 authoring_mode 가 정한다", () => {
      // 같은 state 인데 authoring_mode 만 다르면 국면이 갈려야 한다.
      const byAi = sessionView({ state: "replaying", authoring_mode: "ai" });
      const byHuman = sessionView({ state: "replaying", authoring_mode: "record" });
      expect(phaseOfSession(byAi)).toBe("ai_authoring");
      expect(phaseOfSession(byHuman)).toBe("running");
    });
  });

  describe("브라우저 생존 (조건 C2)", () => {
    it("일시정지는 브라우저가 있다", () => {
      expect(hasLiveBrowser(sessionView({ state: "paused" }))).toBe(true);
    });

    it("검토와 유실은 브라우저가 없다 — 그래서 국면도 갈린다", () => {
      expect(hasLiveBrowser(sessionView({ state: "review" }))).toBe(false);
      expect(hasLiveBrowser(sessionView({ state: "lost" }))).toBe(false);
      /*
        **2026-09-09 에 이 단언이 뒤집혔다.** 이전에는 「국면은 같다. 갈리는 것은 브라우저
        생존이다」였다. 그 배치가 검토 화면에 브라우저 조작 넷을 잠긴 채 남겼으므로,
        브라우저 생존이 국면을 가르게 했다.
      */
      expect(phaseOfSession(sessionView({ state: "review" }))).toBe("review");
      expect(phaseOfSession(sessionView({ state: "lost" }))).toBe("review");
      expect(phaseOfSession(sessionView({ state: "paused" }))).toBe("paused");
    });

    it("세션이 없으면 브라우저도 없다", () => {
      expect(hasLiveBrowser(null)).toBe(false);
    });
  });

  describe("세션 종료 (조건 C1)", () => {
    it("실행 중·일시정지는 끝나지 않았다", () => {
      expect(isFinished(sessionView({ state: "replaying" }))).toBe(false);
      expect(isFinished(sessionView({ state: "paused" }))).toBe(false);
    });

    it("검토·유실·완료·실패·중지는 끝났다", () => {
      for (const state of ["review", "lost", "completed", "failed", "stopped"] as SessionState[]) {
        expect(isFinished(sessionView({ state }))).toBe(true);
      }
    });

    it("세션이 없으면 끝난 것으로 본다 — 새 실행을 막을 이유가 없다", () => {
      expect(isFinished(null)).toBe(true);
    });
  });
});
