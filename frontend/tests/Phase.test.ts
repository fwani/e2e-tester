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
  it("국면은 일곱이다", () => {
    expect(PHASES).toHaveLength(7);
  });

  it("세션이 없는 국면은 결과보기와 편집 둘뿐이다", () => {
    const withoutSession = PHASES.filter((p) => !isSessionPhase(p));
    expect(withoutSession).toEqual(["result", "editing"]);
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
    { state: "review", authoring: "record", expected: "paused", why: "중지 후 검토 (DR-010)" },
    { state: "lost", authoring: "record", expected: "paused", why: "유실 — 편집·저장은 받는다 (DR-015)" },
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

    it("검토와 유실은 브라우저가 없다 — 같은 paused 국면 안에서 갈린다", () => {
      expect(hasLiveBrowser(sessionView({ state: "review" }))).toBe(false);
      expect(hasLiveBrowser(sessionView({ state: "lost" }))).toBe(false);
      // 국면은 같다. 갈리는 것은 브라우저 생존이다.
      expect(phaseOfSession(sessionView({ state: "review" }))).toBe("paused");
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
