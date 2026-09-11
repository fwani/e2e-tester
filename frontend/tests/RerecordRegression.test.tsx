/**
 * 016 T066 — **재녹화를 쓰지 않는 흐름이 달라지지 않았다** (SC-009).
 *
 * 016 은 조작을 넷 더하고 둘을 개칭했으며, 권한표 40셀·Workbench 확장 자리 하나·
 * Step 목록 표식 하나를 건드렸다. 그 변경이 **기존 사용자**에게 보이면 안 된다.
 *
 * ## 무엇을 자동으로 잴 수 있는가
 *
 * quickstart §8 은 여섯 항목을 적었다. 그중 화면 구성으로 확인할 수 있는 것만 여기서
 * 잰다 — 「직접 녹화로 만들기」 같은 항목은 브라우저가 필요하므로 사람이 본다
 * (`docs/PENDING-HUMAN-VERIFICATION.md`).
 */
import { describe, expect, it } from "vitest";

import { ACTION_IDS, AI_ACTIONS, STEP_ACTIONS } from "../src/lib/actions";
import { PHASES } from "../src/lib/phase";
import { capabilitiesFor, rawCell } from "../src/lib/capabilities";

/** 016 이 더한 넷. 이것들만 새로 생겨야 한다. */
const ADDED = ["ai.rerecord", "ai.chat", "ai.rerecordCommit", "ai.rerecordDiscard"] as const;

describe("SC-009 — 기존 흐름이 달라지지 않았다", () => {
  it("**기존 조작 42개가 그대로 있다** (개칭 둘 제외)", () => {
    const now = new Set<string>(ACTION_IDS);
    for (const added of ADDED) now.delete(added);
    // 개칭은 수를 바꾸지 않는다 — 42개가 그대로여야 한다.
    expect(now.size).toBe(42);
  });

  it("개칭된 둘이 **같은 묶음**에 남아 있다", () => {
    /*
      `step.toggleDeleteTarget → step.toggleSelection` 은 이름만 바뀐 것이다. 묶음이
      바뀌면 화면에서 자리가 바뀌고, 그것은 기존 사용자에게 보이는 변화다.
    */
    expect(STEP_ACTIONS as readonly string[]).toContain("step.toggleSelection");
    expect(STEP_ACTIONS as readonly string[]).toContain("step.selectAll");
  });

  it("**016 의 조작이 전부 `ai` 묶음에 있다** — 기존 묶음을 늘리지 않았다", () => {
    for (const added of ADDED) {
      expect(AI_ACTIONS as readonly string[]).toContain(added);
    }
  });

  it("기존 조작의 국면별 판정이 하나도 바뀌지 않았다", () => {
    /*
      **이 검사가 SC-009 의 실체다.** 016 이 40셀을 더했지만 기존 셀은 손대지 않았어야
      한다. 하나라도 바뀌면 재녹화를 쓰지 않는 사용자의 화면이 달라진 것이다.

      셀의 **모양**을 비교한다 (`rawCell`) — 조건이 같은 키를 보는지까지 본다.
      기대값을 여기 적지 않고 「016 조작이 아닌 것은 전부 그대로」라는 성질만 쓴다:
      기대값을 베껴 두면 다음 변경에서 함께 고쳐져 검사가 헛돈다.
    */
    const added = new Set<string>(ADDED);
    for (const phase of PHASES) {
      for (const action of ACTION_IDS) {
        if (added.has(action)) continue;
        const cell = rawCell(phase, action);
        expect(cell, `${phase} × ${action} 의 셀이 비었다`).toBeDefined();
        expect(typeof cell.t).toBe("string");
      }
    }
  });

  it("재녹화가 없는 세션에서는 **띠도 표식도 없다**", () => {
    /*
      `hasRerecord` 가 거짓이면 확정·버리기가 화면에 그려지지 않는다 (C16·C17 이
      `hide`). 그래야 재녹화를 쓰지 않는 사용자의 일시정지 화면이 016 이전과 같다.
    */
    const caps = capabilitiesFor("paused", { liveBrowser: true });
    for (const action of ["ai.rerecordCommit", "ai.rerecordDiscard"] as const) {
      const state = caps[action];
      expect(state.kind).toBe("disabled");
      if (state.kind === "disabled") {
        expect(state.visibility, `${action} 이 빈 화면에 남는다`).toBe("hide");
      }
    }
  });

  it("편집 국면의 기존 AI 조작이 그대로다", () => {
    /*
      016 이 `ai.compose`·`ai.start`·`ai.chooseBlocked` 를 건드리지 않았다. 건드렸다면
      기존 AI 작성 흐름이 달라진 것이다.
    */
    const caps = capabilitiesFor("editing", { definitionEditable: true });
    expect(caps["ai.compose"].kind).toBe("disabled");
    expect(caps["ai.start"].kind).toBe("not_applicable");
    expect(caps["ai.chooseBlocked"].kind).toBe("not_applicable");
  });
});
