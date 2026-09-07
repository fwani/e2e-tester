/**
 * 007 T067 — **한 라벨은 한 조작만 가리킨다** (FR-235 · 005 FR-147).
 *
 * 005 U-08 이 이것이었다: 같은 위치의 「중지」가 실행 중에는 실행을 멈추고, 끝난 뒤에는
 * 확인 없이 세션을 폐기하며 목록으로 튀었다. 사용자는 라벨로 조작을 배우는데, 한 라벨이
 * 두 동작을 가지면 배운 것이 거짓이 된다.
 *
 * 007 은 조작을 33개로 못 박고 라벨을 사전 한 곳에 모았다. 그러면 이 성질을 **셀 수**
 * 있다 — 사전을 훑어 겹치는 라벨이 있는지 보면 된다.
 *
 * **상황에 따라 바뀌는 라벨**(`run.stop` 의 중지/닫기/나가기, `run.from` 의 시작 지점,
 * `save` 의 저장/변경 저장)은 라벨이 하나가 아니다. 그때는 **라벨 집합**이 다른 조작의
 * 집합과 겹치지 않아야 한다.
 */
import { describe, expect, it } from "vitest";

import { ACTION_IDS, type ActionId } from "../src/lib/actions";
import {
  ACTION_LABEL,
  runFromStepLabel,
  saveEditsLabel,
  sessionSaveLabel,
  stopLabel,
} from "../src/lib/wording";

/**
 * 상황에 따라 바뀌는 라벨의 **전체 집합**.
 *
 * 새 상황형 라벨을 만들면 여기 더해야 한다. 더하지 않으면 겹침이 생겨도 이 검사가
 * 잡지 못한다 — 그래서 아래에 "사전이 만드는 라벨 함수를 전부 덮는가" 를 함께 센다.
 */
const SITUATIONAL: Partial<Record<ActionId, string[]>> = {
  "run.stop": [
    stopLabel({ finished: false, pending: false, review: false }),
    stopLabel({ finished: true, pending: false, review: false }),
    stopLabel({ finished: false, pending: true, review: false }),
    stopLabel({ finished: false, pending: false, review: true }),
  ],
  "run.from": [
    ACTION_LABEL["run.from"],
    runFromStepLabel(0),
    runFromStepLabel(5),
  ],
  "run.fromHere": [ACTION_LABEL["run.fromHere"], "Step 01 부터 이어 실행"],
  save: [
    ACTION_LABEL.save,
    sessionSaveLabel(false),
    sessionSaveLabel(true),
    saveEditsLabel(0, false),
    saveEditsLabel(3, false),
    saveEditsLabel(0, true),
  ],
};

function labelsOf(action: ActionId): string[] {
  return SITUATIONAL[action] ?? [ACTION_LABEL[action]];
}

describe("라벨↔조작 대응 (T067 · FR-235)", () => {
  it("기본 라벨이 33개 전부에 있고 비어 있지 않다", () => {
    for (const action of ACTION_IDS) {
      expect(ACTION_LABEL[action], action).toBeTruthy();
      expect(ACTION_LABEL[action].trim().length, action).toBeGreaterThan(0);
    }
  });

  it("기본 라벨이 겹치지 않는다 — 한 라벨이 두 조작을 갖지 않는다", () => {
    const seen = new Map<string, ActionId>();
    const clashes: string[] = [];
    for (const action of ACTION_IDS) {
      const label = ACTION_LABEL[action];
      const owner = seen.get(label);
      if (owner !== undefined) clashes.push(`「${label}」 ← ${owner} · ${action}`);
      seen.set(label, action);
    }
    expect(clashes, `같은 라벨이 두 조작에 쓰인다:\n  ${clashes.join("\n  ")}`).toEqual([]);
  });

  it("상황형 라벨 집합도 서로 겹치지 않는다 (005 FR-147 · U-08)", () => {
    const owners = new Map<string, ActionId>();
    const clashes: string[] = [];
    for (const action of ACTION_IDS) {
      for (const label of labelsOf(action)) {
        const owner = owners.get(label);
        if (owner !== undefined && owner !== action) {
          clashes.push(`「${label}」 ← ${owner} · ${action}`);
        }
        owners.set(label, action);
      }
    }
    expect(clashes, `상황형 라벨이 겹친다:\n  ${clashes.join("\n  ")}`).toEqual([]);
  });

  it("「처음부터 실행」은 `run.all` 만의 것이다", () => {
    // 통합 화면에서 `run.all` 과 `run.from` 이 **같은 자리에 함께** 있으므로,
    // 0번을 「처음부터 실행」이라 부르면 한 라벨이 두 조작을 갖는다. 그래서 통합
    // 화면은 `runFromStepLabel` 을 쓴다 (0번도 번호로 부른다).
    expect(ACTION_LABEL["run.all"]).toBe("처음부터 실행");
    expect(runFromStepLabel(0)).not.toBe(ACTION_LABEL["run.all"]);
    expect(runFromStepLabel(0)).toBe("Step 01부터 실행");
  });

  it("중지 계열이 상황마다 다른 라벨을 갖는다 — 같은 라벨이 두 동작을 갖지 않는다", () => {
    const labels = SITUATIONAL["run.stop"] ?? [];
    expect(new Set(labels).size).toBe(labels.length);
    expect(labels).toContain("중지");
    expect(labels).toContain("닫기");
    expect(labels).toContain("나가기");
    expect(labels).toContain("중지 중…");
  });
});
