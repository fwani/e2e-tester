/**
 * 배선 모듈 자체. 027 FR-001~FR-006 (contracts/wiring-contract.md §1·§2).
 *
 * 이 파일이 고정하는 것은 **모듈이 하지 않는 일**이다. 능력을 잇는 것은 쉽고, 어려운
 * 것은 「국면을 알지 않는 채로」 잇는 것이다 — 그것이 무너지면 판정이 조작표 밖에 하나
 * 더 생기고, 011 이 표를 만든 이유가 없어진다.
 */

import { describe, expect, it, vi } from "vitest";

const SOURCE = import.meta.glob("../src/lib/actionWiring.ts", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

import {
  WIRED_ACTION_IDS,
  makeRunAction,
  wiredActionsOf,
  wiredAttribute,
  type ScreenCapabilities,
} from "../src/lib/actionWiring";

describe("능력이 없으면 이어지지 않는다 (FR-003)", () => {
  it("빈 묶음은 **아무 조작도** 잇지 않는다", () => {
    expect(wiredActionsOf({})).toEqual([]);
  });

  it("준 것만 이어진다", () => {
    const wired = wiredActionsOf({ deleteStep: vi.fn(), save: vi.fn() });
    expect(wired).toContain("step.delete");
    expect(wired).toContain("save");
    expect(wired).not.toContain("run.all");
  });

  it("이어지지 않은 조작을 실행해도 **터지지 않는다**", () => {
    const { run } = makeRunAction({});
    expect(() => run("step.delete")).not.toThrow();
  });
});

describe("이어진 조작은 그 능력을 부른다", () => {
  it("한 능력에 한 조작", () => {
    const deleteStep = vi.fn();
    makeRunAction({ deleteStep }).run("step.delete");
    expect(deleteStep).toHaveBeenCalledOnce();
  });

  it("**방향은 조작이 정한다** — 화면 상태가 아니다", () => {
    const moveStep = vi.fn();
    const { run } = makeRunAction({ moveStep });

    run("step.moveUp");
    expect(moveStep).toHaveBeenLastCalledWith(-1);

    run("step.moveDown");
    expect(moveStep).toHaveBeenLastCalledWith(1);
  });

  it("능력은 **인자를 받지 않는다** — 어느 Step 인지는 화면이 안다", () => {
    const deleteStep = vi.fn();
    makeRunAction({ deleteStep }).run("step.delete");
    // 배선이 화면 상태를 읽어 넘기기 시작하면 contracts §2 의 셋째 줄이 깨진다.
    expect(deleteStep).toHaveBeenCalledWith();
  });
});

describe("이행 중의 공존 (FR-022 · contracts §5)", () => {
  it("표에 없는 조작은 `fallback` 으로 간다", () => {
    const fallback = vi.fn();
    makeRunAction({}, fallback).run("ai.chat");
    expect(fallback).toHaveBeenCalledWith("ai.chat");
  });

  it("이어진 조작은 `fallback` 으로 **가지 않는다**", () => {
    const fallback = vi.fn();
    const deleteStep = vi.fn();
    makeRunAction({ deleteStep }, fallback).run("step.delete");
    expect(deleteStep).toHaveBeenCalledOnce();
    expect(fallback).not.toHaveBeenCalled();
  });

  it("능력이 없으면 표에 **있는** 조작도 `fallback` 으로 간다", () => {
    // 아직 그 화면이 옮기지 않은 상태다 — 기존 경로가 받아야 한다.
    const fallback = vi.fn();
    makeRunAction({}, fallback).run("step.delete");
    expect(fallback).toHaveBeenCalledWith("step.delete");
  });
});

describe("모듈이 하지 않는 일 (contracts §2)", () => {
  it("**국면을 받지 않는다**", () => {
    // 인자가 둘(능력·fallback)이다. 국면이 끼어들면 여기서 걸린다.
    expect(makeRunAction.length).toBe(2);
  });

  it("모듈에 국면·권한을 다루는 이름이 없다", () => {
    /*
      **소스를 읽어서 본다.** 이 모듈이 국면을 알기 시작하는 것은 타입으로 막을 수
      없다 — 임포트 한 줄이면 되기 때문이다. 그것이 research R7 의 「실패의 정의」이고,
      실패를 검사가 잡아야 되돌릴 시점을 안다.
    */
    const source = SOURCE["../src/lib/actionWiring.ts"] ?? "";
    expect(source, "모듈 소스를 읽지 못했다").not.toBe("");

    // 주석이 「판정하지 않는다」를 설명하므로 **코드 줄만** 본다.
    const code = source
      .split("\n")
      .filter((line) => !/^\s*(\*|\/\*|\/\/)/.test(line))
      .join("\n");
    for (const forbidden of ["capabilitiesFor", "phase", "Phase", "enabled", "disabled"]) {
      expect(code, `배선이 ${forbidden} 를 안다 — 판정이 두 곳에 생겼다`).not.toContain(
        forbidden,
      );
    }
  });
});

describe("이어 둔 목록은 도출된다 (FR-016 · research R2)", () => {
  it("화면이 적는 것이 아니라 능력에서 나온다", () => {
    const caps: ScreenCapabilities = { deleteStep: vi.fn(), moveStep: vi.fn() };
    expect(makeRunAction(caps).wired).toEqual(wiredActionsOf(caps));
  });

  it("한 능력이 여러 조작을 이으면 **전부** 목록에 든다", () => {
    const wired = wiredActionsOf({ moveStep: vi.fn() });
    expect(wired).toContain("step.moveUp");
    expect(wired).toContain("step.moveDown");
  });

  it("속성 값은 쉼표로 잇는다", () => {
    expect(wiredAttribute(["step.delete", "save"])).toBe("step.delete,save");
  });
});

describe("표 자체의 성질", () => {
  it("잇는 조작이 **하나 이상**이다", () => {
    expect(WIRED_ACTION_IDS.length).toBeGreaterThan(0);
  });

  it("같은 조작이 두 번 나오지 않는다", () => {
    expect(new Set(WIRED_ACTION_IDS).size).toBe(WIRED_ACTION_IDS.length);
  });

  it("**13개 중복 조작이 전부 표에 있다** (SC-006)", () => {
    // baseline.md T003 이 잰 목록. 이것들이 편집과 세션에 두 벌로 있었다.
    for (const id of [
      "nav.back",
      "result.show",
      "run.all",
      "run.from",
      "save",
      "step.addNaturalLanguage",
      "step.delete",
      "step.deleteAfter",
      "step.deleteSelected",
      "step.insertManual",
      "step.moveDown",
      "step.moveUp",
      "step.recordStart",
    ] as const) {
      expect(WIRED_ACTION_IDS, `${id} 가 표에 없다`).toContain(id);
    }
  });
});
