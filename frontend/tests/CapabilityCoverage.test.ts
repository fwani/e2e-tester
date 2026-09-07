/**
 * 007 T012 — 권한표 커버리지 (SC-007 · FR-247 · FR-234).
 *
 * **이 파일이 지키는 것은 셋이다.**
 *
 * 1. 33개 조작 전부가 일곱 국면에 답을 갖는다 — 빠진 칸이 있으면 화면은 `undefined` 를
 *    받고 조용히 아무것도 그리지 않는다. 감춰진 조작이 되고 FR-234 위반이다.
 * 2. 모든 「해당 없음」이 §4-2 의 닫힌 목록(N1·N2·N3)에서 근거를 갖는다 — 근거 없이
 *    그리지 않는 것이 곧 조작을 잃는 것이다 (FR-247).
 * 3. 모든 해소 방법이 **33개 목록 안의 조작**을 가리킨다 — 006 E-03 이 정확히 그
 *    결함이었다. "실행을 시작해 일시정지한 뒤 하세요" 라고 안내하면서 그리로 가는
 *    버튼을 주지 않았다.
 */
import { describe, expect, it } from "vitest";

import { ACTION_IDS, type ActionId } from "../src/lib/actions";
import {
  capabilitiesFor,
  capabilityOf,
  rawCell,
  type CapabilityFacts,
} from "../src/lib/capabilities";
import { PHASES, type Phase } from "../src/lib/phase";
import { NOT_APPLICABLE_REASON } from "../src/lib/wording";

/** 모든 조건을 참으로 둔 사실 — ◐ 셀이 ● 가 되는 최대 상태. */
const ALL_TRUE: CapabilityFacts = {
  sessionFinished: true,
  liveBrowser: true,
  hasFailedStep: true,
  pacingAppliesInTakeover: true,
  blockingSession: true,
  recording: true,
  definitionEditable: true,
  hasSteps: true,
  hasPendingEdits: true,
  staleConflict: true,
  aiBlocked: true,
  resultViewable: true,
  hasResult: true,
};

describe("조작 목록 (T008)", () => {
  it("33개다 — contracts/ui-contract.md §2 의 합계와 같아야 한다", () => {
    expect(ACTION_IDS).toHaveLength(33);
  });

  it("중복이 없다", () => {
    expect(new Set(ACTION_IDS).size).toBe(ACTION_IDS.length);
  });
});

describe("권한표 커버리지 (T012)", () => {
  it("일곱 국면 × 33 조작 전부에 답이 있다", () => {
    for (const phase of PHASES) {
      const map = capabilitiesFor(phase);
      for (const action of ACTION_IDS) {
        expect(map[action], `${phase} × ${action} 이 비어 있다`).toBeDefined();
      }
      expect(Object.keys(map)).toHaveLength(33);
    }
  });

  it("모든 「해당 없음」이 N1·N2·N3 중 하나를 근거로 갖는다 (§4-2)", () => {
    const bases = Object.keys(NOT_APPLICABLE_REASON);
    for (const phase of PHASES) {
      for (const action of ACTION_IDS) {
        const state = capabilityOf(phase, action, ALL_TRUE);
        if (state.kind !== "not_applicable") continue;
        expect(bases, `${phase} × ${action} 의 근거가 닫힌 목록 밖이다`).toContain(state.basis);
        expect(state.note.length).toBeGreaterThan(0);
      }
    }
  });

  it("모든 「비활성」이 이유를 갖는다 (FR-234)", () => {
    for (const phase of PHASES) {
      for (const action of ACTION_IDS) {
        for (const facts of [{}, ALL_TRUE]) {
          const state = capabilityOf(phase, action, facts);
          if (state.kind !== "disabled") continue;
          expect(
            state.reason.length,
            `${phase} × ${action} 에 이유가 없다`,
          ).toBeGreaterThan(0);
        }
      }
    }
  });

  it("모든 해소 방법이 33개 목록 안의 조작을 가리킨다 (006 E-03)", () => {
    const known = new Set<string>(ACTION_IDS);
    for (const phase of PHASES) {
      for (const action of ACTION_IDS) {
        for (const facts of [{}, ALL_TRUE]) {
          const state = capabilityOf(phase, action, facts);
          if (state.kind !== "disabled" || state.remedy === null) continue;
          expect(
            known.has(state.remedy.action),
            `${phase} × ${action} 의 해소 방법 ${state.remedy.action} 이 목록 밖이다`,
          ).toBe(true);
        }
      }
    }
  });

  it("해소 방법이 그 국면에서 실제로 쓸 수 있는 조작이다", () => {
    // 화면에 없는 조작을 지시하지 않는다. 해소 방법이 그 국면에서 「해당 없음」이면
    // 사용자는 존재하지 않는 버튼을 찾게 된다 — 006 E-03 과 같은 종류의 거짓 안내다.
    for (const phase of PHASES) {
      for (const action of ACTION_IDS) {
        const state = capabilityOf(phase, action, ALL_TRUE);
        if (state.kind !== "disabled" || state.remedy === null) continue;
        const remedyState = capabilityOf(phase, state.remedy.action, ALL_TRUE);
        expect(
          remedyState.kind,
          `${phase} × ${action} 이 그 국면에 없는 ${state.remedy.action} 을 지시한다`,
        ).not.toBe("not_applicable");
      }
    }
  });

  it("해소 방법이 자기 자신을 가리키지 않는다", () => {
    for (const phase of PHASES) {
      for (const action of ACTION_IDS) {
        for (const facts of [{}, ALL_TRUE]) {
          const state = capabilityOf(phase, action, facts);
          if (state.kind !== "disabled" || state.remedy === null) continue;
          expect(state.remedy.action, `${phase} × ${action} 이 자기를 지시한다`).not.toBe(action);
        }
      }
    }
  });
});

describe("런타임 조건 (T010)", () => {
  it("조건을 모르면 비활성이다 — 모르는 것을 참으로 보지 않는다", () => {
    // paused 국면의 「계속하기」는 브라우저 생존(C2)에 달려 있다.
    const unknown = capabilityOf("paused", "run.resume", {});
    expect(unknown.kind).toBe("disabled");
    const known = capabilityOf("paused", "run.resume", { liveBrowser: true });
    expect(known.kind).toBe("enabled");
  });

  it("검토 상태에서는 브라우저를 요구하는 조작이 비활성이고 이유가 붙는다", () => {
    const facts: CapabilityFacts = { liveBrowser: false, sessionFinished: true, hasSteps: true };
    const resume = capabilityOf("paused", "run.resume", facts);
    expect(resume.kind).toBe("disabled");
    if (resume.kind === "disabled") {
      expect(resume.reason).toContain("브라우저");
      expect(resume.remedy).not.toBeNull();
    }
  });

  it("끝난 세션에서는 재실행이 열린다 (C1)", () => {
    expect(capabilityOf("paused", "run.all", { sessionFinished: true, hasSteps: true }).kind).toBe(
      "enabled",
    );
    expect(capabilityOf("paused", "run.all", { sessionFinished: false, hasSteps: true }).kind).toBe(
      "disabled",
    );
  });
});

describe("전 국면 덮어쓰기 (T011 · §3-6)", () => {
  it("O1 — 실행 요청이 진행 중이면 어느 국면의 실행도 눌리지 않는다 (005 U-06)", () => {
    // 국면마다 표에 적지 않고 덮어쓰기로 두는 이유가 이것이다. 한 국면이라도
    // 빠지면 그 국면에서 연타로 브라우저 창이 둘 뜬다.
    const phasesWithRun: Phase[] = ["result", "editing"];
    for (const phase of phasesWithRun) {
      for (const action of ["run.all", "run.from"] as ActionId[]) {
        const state = capabilityOf(phase, action, { ...ALL_TRUE, runPending: true });
        expect(state.kind, `${phase} × ${action}`).toBe("disabled");
        if (state.kind === "disabled") expect(state.reason).toContain("준비");
      }
    }
  });

  it("O1 은 편집 국면의 「브라우저 열기」에도 걸린다", () => {
    const state = capabilityOf("editing", "browser.openAt", { ...ALL_TRUE, runPending: true });
    expect(state.kind).toBe("disabled");
  });

  it("O3 — 세션 유실은 브라우저를 요구하는 조작 전부를 막고 재실행을 지시한다", () => {
    const state = capabilityOf("paused", "run.resume", { ...ALL_TRUE, sessionLost: true });
    expect(state.kind).toBe("disabled");
    if (state.kind === "disabled") {
      expect(state.reason).toContain("유실");
      expect(state.remedy?.action).toBe("run.all");
    }
  });

  it("O4 — Step 이 0개면 저장이 막힌다 (006 FR-197)", () => {
    const state = capabilityOf("paused", "save", { ...ALL_TRUE, hasSteps: false });
    expect(state.kind).toBe("disabled");
  });

  it("덮어쓰기가 「해당 없음」을 활성·비활성으로 바꾸지 않는다", () => {
    // 결과 국면에 세션 명령은 없다. 거기에 「요청을 보내는 중…」을 붙이면 화면이
    // 쓸 수 없는 조작으로 뒤덮인다.
    const state = capabilityOf("result", "run.pause", { ...ALL_TRUE, busy: true });
    expect(state.kind).toBe("not_applicable");
  });
});

describe("표의 모양 — 국면별 성질 (§3)", () => {
  it("실행 중 국면의 편집 조작은 감추지 않고 비활성이다 (FR-238)", () => {
    for (const action of ["step.update", "step.delete", "step.reorder", "save"] as ActionId[]) {
      const state = capabilityOf("running", action, ALL_TRUE);
      expect(state.kind, action).toBe("disabled");
      if (state.kind === "disabled") expect(state.remedy).not.toBeNull();
    }
  });

  it("결과 국면의 편집 조작은 「이 Step 고치기」로 안내한다", () => {
    for (const action of ["step.update", "step.delete", "step.reorder"] as ActionId[]) {
      const state = capabilityOf("result", action, ALL_TRUE);
      expect(state.kind, action).toBe("disabled");
      if (state.kind === "disabled") expect(state.remedy?.action).toBe("nav.editStep");
    }
  });

  it("편집 국면의 브라우저 요구 조작은 「브라우저 열기」로 안내한다 (006 FR-200·FR-202)", () => {
    for (const action of [
      "step.repick",
      "step.recordStart",
      "step.addNaturalLanguage",
      "step.addAssertion",
    ] as ActionId[]) {
      const state = capabilityOf("editing", action, ALL_TRUE);
      expect(state.kind, action).toBe("disabled");
      if (state.kind === "disabled") expect(state.remedy?.action).toBe("browser.openAt");
    }
  });

  it("Step 지목은 일곱 국면 전부에서 가능하다 (FR-227)", () => {
    for (const phase of PHASES) {
      expect(capabilityOf(phase, "step.select", ALL_TRUE).kind, phase).toBe("enabled");
    }
  });

  it("목록으로 돌아가기는 일곱 국면 전부에서 가능하다", () => {
    for (const phase of PHASES) {
      expect(capabilityOf(phase, "nav.back", ALL_TRUE).kind, phase).toBe("enabled");
    }
  });

  it("실행 진입은 세션이 없는 두 국면에서 가능하다 (FR-236)", () => {
    for (const phase of ["result", "editing"] as Phase[]) {
      expect(capabilityOf(phase, "run.all", ALL_TRUE).kind, phase).toBe("enabled");
      expect(capabilityOf(phase, "run.from", ALL_TRUE).kind, phase).toBe("enabled");
    }
  });

  it("편집 국면의 실행 조작은 저장 여부와 무관하다 (S-07 · FR-237)", () => {
    // 저장할 변경이 없어도(C9 거짓) 실행은 열려 있어야 한다. 이전에는 저장에
    // 성공한 뒤에만 실행 버튼이 나타났다.
    const noEdits: CapabilityFacts = { hasSteps: true, definitionEditable: true };
    expect(capabilityOf("editing", "run.all", noEdits).kind).toBe("enabled");
    expect(capabilityOf("editing", "run.from", noEdits).kind).toBe("enabled");
    // 같은 사실 아래에서 저장은 비활성이다 — 두 조작의 조건이 다르다는 것이 요점이다.
    expect(capabilityOf("editing", "save", noEdits).kind).toBe("disabled");
  });

  it("어느 국면도 33개 전부를 「해당 없음」으로 두지 않는다", () => {
    for (const phase of PHASES) {
      const map = capabilitiesFor(phase, ALL_TRUE);
      const usable = ACTION_IDS.filter((a) => map[a].kind !== "not_applicable");
      expect(usable.length, `${phase} 이 아무 조작도 갖지 않는다`).toBeGreaterThan(5);
    }
  });

  it("rawCell 이 표를 그대로 돌려준다 — 검사가 판정을 거치지 않고 표를 볼 수 있어야 한다", () => {
    expect(rawCell("running", "run.pause").t).toBe("on");
    expect(rawCell("result", "run.stop").t).toBe("na");
    expect(rawCell("paused", "run.resume").t).toBe("cond");
    expect(rawCell("running", "step.update").t).toBe("off");
  });
});
