/**
 * 007 T081 — **대상 앱을 보는 자리가 하나다** (US4 · FR-244·FR-245·FR-246).
 *
 * 007 이전에는 그렇지 않았다. 결과 화면에는 대상 앱 영역이 아예 없고 산출물이 본문
 * 오른쪽 별도 영역(`flex: 0 0 640px`)에 있어, 다른 국면의 미러 자리와 대응하지 않았다
 * (S-11). 사용자는 "그 화면에서 무엇을 봤는가" 를 국면마다 다른 곳에서 찾았다.
 *
 * 여기서 재는 것은 셋이다.
 *
 * 1. 네 내용(미러·산출물·브라우저 열기·빈 상태)이 **같은 자리**를 쓴다
 * 2. 비어 있으면 **왜 비었는지** 넷을 구별해 말한다 (FR-245 · 005 U-22)
 * 3. 고를 수 없는 산출물을 **감추지 않고** 이유를 붙여 남긴다 (FR-246 · DC-007)
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Workbench } from "../src/components/workbench/Workbench";
import type { EmptyReason, TargetView } from "../src/components/workbench/model";
import { PHASES, type Phase } from "../src/lib/phase";
import { workbenchModel } from "./helpers/model";

const el = (selector: string) => document.querySelector<HTMLElement>(selector);

function show(target: TargetView, phase: Phase = "running") {
  return render(
    <Workbench
      model={workbenchModel(phase, { target })}
      phaseActions={null}
      onSelectStep={vi.fn()}
      onCloseDetail={vi.fn()}
    />,
  );
}

/** 좌측 열에서 대상 앱 영역이 차지하는 자리 — 부모의 배치와 자기 배치. */
function place(): string {
  const pane = el("[data-workbench-target]")!;
  return `${pane.parentElement!.style.flex}|${pane.style.flex}|${pane.style.minWidth}`;
}

const ALL_TARGETS: TargetView[] = [
  { kind: "mirror", mirror: <div>미러</div>, currentUrl: "http://t/", tabs: null },
  {
    kind: "artifacts",
    selected: "screenshot",
    available: ["screenshot", "console", "network"],
    body: <div>스크린샷</div>,
  },
  { kind: "open_browser", stepIndex: 1 },
  { kind: "empty", reason: "not_started" },
];

afterEach(cleanup);

describe("네 내용이 같은 자리를 쓴다 (FR-244 · S-11 해소)", () => {
  it("자리가 내용에 따라 바뀌지 않는다", () => {
    const places = new Set<string>();
    for (const target of ALL_TARGETS) {
      const view = show(target);
      places.add(place());
      view.unmount();
    }
    expect(places.size, `내용마다 자리가 달라졌다: ${[...places].join(" / ")}`).toBe(1);
  });

  it("일곱 국면에서 같은 자리다", () => {
    const places = new Set<string>();
    for (const phase of PHASES) {
      const view = show(ALL_TARGETS[0]!, phase);
      places.add(place());
      view.unmount();
    }
    expect(places.size).toBe(1);
  });

  it("Step 패널보다 앞에 온다 — 좌우 배치가 국면과 무관하다", () => {
    show(ALL_TARGETS[1]!);
    const pane = el("[data-workbench-target]")!;
    const panel = el("[data-workbench-step-panel]")!;
    expect(pane.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

describe("빈 이유를 구별한다 (T077 · FR-245 · 005 FR-173·U-22)", () => {
  const REASONS: EmptyReason[] = ["not_started", "not_collected", "session_lost", "not_supported"];

  it("넷이 서로 다른 문장을 갖는다 — 「(기록 없음)」 한 줄로 뭉개지 않는다", () => {
    const messages = new Set<string>();
    for (const reason of REASONS) {
      const view = show({ kind: "empty", reason });
      const box = el(`[data-target-empty='${reason}']`);
      expect(box, reason).not.toBeNull();
      messages.add(box!.textContent ?? "");
      view.unmount();
    }
    expect(messages.size, "빈 이유가 구별되지 않는다").toBe(4);
  });

  it("각 이유가 **다음 행동**을 담는다 — 사실만 말하고 끝내지 않는다", () => {
    // "아직 시작하지 않음" 과 "수집되지 않음" 과 "세션 유실" 은 사용자에게 서로 다른
    // 다음 행동을 요구한다. 그것이 넷을 가른 이유다.
    const next: Record<EmptyReason, RegExp> = {
      not_started: /실행을 걸면/,
      not_collected: /수집/,
      session_lost: /처음부터 다시 실행/,
      not_supported: /지원되지 않습니다/,
    };
    for (const reason of REASONS) {
      const view = show({ kind: "empty", reason });
      expect(el(`[data-target-empty='${reason}']`)!.textContent, reason).toMatch(next[reason]);
      view.unmount();
    }
  });

  it("빈 상태도 상태 표시로 전달된다 — 조용히 비어 있지 않다", () => {
    show({ kind: "empty", reason: "not_collected" });
    expect(el("[data-target-empty='not_collected']")!.getAttribute("role")).toBe("status");
  });
});

describe("산출물 고르기는 이 영역 안에 있다 (T078 · FR-246 · DC-007)", () => {
  const artifacts: TargetView = {
    kind: "artifacts",
    selected: "screenshot",
    available: ["screenshot", "console", "network"],
    body: <div>본문</div>,
  };

  it("고르는 조작이 대상 앱 영역 안에 산다", () => {
    show(artifacts);
    const pane = el("[data-workbench-target]")!;
    const picker = el("[data-action='artifact.select']")!;
    expect(pane.contains(picker)).toBe(true);
  });

  it("지원되지 않는 종류를 감추지 않고 비활성으로 남긴다", () => {
    show(artifacts);
    const trace = el("[data-artifact-tab='trace']") as HTMLButtonElement;
    expect(trace, "확정 디자인에 있는 탭을 뺐다 (DC-007)").not.toBeNull();
    expect(trace.disabled).toBe(true);
    // 고를 수 있는 것은 그대로 눌린다.
    expect((el("[data-artifact-tab='console']") as HTMLButtonElement).disabled).toBe(false);
  });

  it("왜 못 고르는지 화면에도 적는다 — `title` 만 두지 않는다 (005 FR-172)", () => {
    show(artifacts);
    const reason = el("[data-disabled-reason='artifact.select']");
    expect(reason, "이유가 마우스를 올려야만 보인다").not.toBeNull();
    expect(reason!.textContent).toContain("TRACE");
  });

  it("전부 고를 수 있으면 이유를 쓰지 않는다 — 없는 문제를 말하지 않는다", () => {
    show({ ...artifacts, available: ["screenshot", "console", "network", "trace"] });
    expect(el("[data-disabled-reason='artifact.select']")).toBeNull();
  });
});

describe("브라우저를 여는 자리 (T079 · FR-244)", () => {
  it("편집 국면의 「브라우저 열어 Step nn 에서 멈추기」가 이 영역 안에 있다", () => {
    show({ kind: "open_browser", stepIndex: 1 }, "editing");
    const pane = el("[data-workbench-target]")!;
    const button = el("[data-action='browser.openAt']")!;
    expect(pane.contains(button)).toBe(true);
    expect(button.textContent).toContain("Step 02");
  });

  it("무엇은 브라우저 없이 되는지 함께 말한다 — 회색 버튼만 두지 않는다", () => {
    show({ kind: "open_browser", stepIndex: 0 }, "editing");
    expect(screen.getByText(/값·순서·삭제는 브라우저 없이 고칠 수 있습니다/)).toBeTruthy();
  });
});

describe("국면 보조 영역이 자리를 바꾸지 않는다 (T080 · FR-218e)", () => {
  it("없으면 자리를 차지하지 않는다", () => {
    show(ALL_TARGETS[0]!);
    expect(el("[data-workbench-aside]")).toBeNull();
  });

  it("있어도 대상 앱 영역과 Step 패널의 자리가 그대로다", () => {
    const without = show(ALL_TARGETS[0]!);
    const before = `${place()}|${el("[data-workbench-step-panel]")!.style.flex}`;
    without.unmount();

    render(
      <Workbench
        model={workbenchModel("running", {
          target: ALL_TARGETS[0]!,
          aside: {
            kind: "ai_progress",
            instruction: "x",
            messages: ["a", "b", "c"],
            error: null,
            blocked: null,
          },
        })}
        phaseActions={null}
        onSelectStep={vi.fn()}
        onCloseDetail={vi.fn()}
      />,
    );
    expect(el("[data-workbench-aside]")).not.toBeNull();
    expect(`${place()}|${el("[data-workbench-step-panel]")!.style.flex}`).toBe(before);
  });
});
