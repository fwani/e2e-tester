/**
 * Simplified workbench shell: one toolbar, a persistent Step list, and a primary work area.
 * Editing uses the shared Step detail inline; live/result views retain the temporary inspector.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Workbench } from "../src/components/workbench/Workbench";
import type { WorkbenchModel } from "../src/components/workbench/model";
import { PHASES } from "../src/lib/phase";
import { PHASE_LABEL } from "../src/lib/wording";
import { workbenchModel } from "./helpers/model";
import { stepResult } from "./helpers/workbench";

import { flexOf } from "./helpers/style";
function renderShell(model: WorkbenchModel) {
  return render(
    <Workbench
      model={model}
      phaseActions={null}
      onSelectStep={vi.fn()}
      onCloseDetail={vi.fn()}
    />,
  );
}

const el = (selector: string) => document.querySelector<HTMLElement>(selector)!;

describe("단일 도구 모음과 작업 영역", () => {
  it("제목과 주요 조작은 하나의 도구 모음에 있고 본문보다 앞선다", () => {
    renderShell(workbenchModel("running"));
    const bar = el("[data-workbench-phase-bar]");
    expect(document.querySelectorAll("[data-shell=header]")).toHaveLength(1);
    expect(el("[data-shell=header]").contains(bar)).toBe(true);
    const target = el("[data-workbench-target]");
    const panel = el("[data-workbench-step-panel]");
    // 문서 순서가 곧 층의 순서다.
    expect(bar.compareDocumentPosition(target) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(panel.compareDocumentPosition(target) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("국면 제목은 새 작업 공간 헤더를 쓴다", () => {
    renderShell(workbenchModel("running"));
    expect(el("[data-workbench-phase-bar]").className).toBe("workbench-heading");
  });

  it("Step 패널은 공통 고정 폭 토큰을 쓴다", () => {
    renderShell(workbenchModel("running"));
    expect(el("[data-workbench-step-panel]").className, "Step 패널이 고정 폭 토큰을 쓰지 않는다").toContain("basis-steps");
  });

  it("최소 기준 폭이 1440px 이고 넓으면 늘어난다 (FR-218·FR-218a)", () => {
    renderShell(workbenchModel("running"));
    // 아트보드 내부 컨테이너가 최소 폭을 갖고 100% 로 늘어난다.
    const frame = el("[data-slot=artboard-body]");
    expect(frame.style.minWidth).toBe("min(1440px, 100%)");
    expect(frame.style.width).toBe("100%");
  });

  it("넓어질 때 늘어나는 것은 좌측 대상 앱 영역뿐이다 (FR-218a)", () => {
    renderShell(workbenchModel("running"));
    // 좌측은 남는 폭을 가져가고(grow 1), Step 패널은 고정이다(grow 0 · basis 460px).
    const left = el("[data-workbench-target]").parentElement!;
    const panel = el("[data-workbench-step-panel]");
    // 015 T030 — 좌측 열이 클래스로 바뀌었다. `flex-1` 이 `flex:1 1 0%` 이므로 grow 는 1 이다.
    // 묻는 것은 그대로: **남는 폭을 가져가는 것이 좌측뿐인가.**
    expect(
      left.style.flexGrow !== "" ? left.style.flexGrow : /\bflex-1\b/.test(left.className) ? "1" : "0",
      "좌측 열이 남는 폭을 가져가지 않는다",
    ).toBe("1");
    expect(flexOf(panel), "Step 패널이 남는 폭을 가져간다").toBe("0 0 auto");
    expect(panel.className, "Step 패널 폭이 460px 이 아니다").toContain("basis-steps");
  });
});

describe("일곱 국면이 같은 껍데기를 쓴다 (SC-003 · FR-217)", () => {
  it("헤더·국면 띠·본문·Step 패널이 일곱 국면 전부에 있다", () => {
    for (const phase of PHASES) {
      const view = renderShell(workbenchModel(phase));
      expect(el("[data-workbench-phase-bar]"), phase).not.toBeNull();
      expect(el("[data-workbench-target]"), phase).not.toBeNull();
      expect(el("[data-workbench-step-panel]"), phase).not.toBeNull();
      const toolbar = el("[data-shell=header]");
      expect(toolbar.contains(el("[data-workbench-phase-bar]")), phase).toBe(true);
      expect(within(toolbar).getByText("TC-001"), phase).toBeTruthy();
      expect(within(toolbar).getByRole("button", { name: "화면 메뉴" }), phase).toBeTruthy();
      view.unmount();
    }
  });

  it("치수가 일곱 국면에서 동일하다 — 껍데기 불일치 0건", () => {
    const shapes = new Set<string>();
    for (const phase of PHASES) {
      const view = renderShell(workbenchModel(phase));
      shapes.add(
        [
          el("[data-workbench-phase-bar]").style.flex,
          el("[data-workbench-step-panel]").className,
          el("[data-workbench-target]").parentElement!.style.flex,
        ].join("|"),
      );
      view.unmount();
    }
    expect(shapes.size, `국면마다 껍데기가 달라졌다: ${[...shapes].join(" / ")}`).toBe(1);
  });

  it("국면 표시가 일곱 국면 전부에서 텍스트로 있다 (FR-219 · 색만으로 알리지 않는다)", () => {
    for (const phase of PHASES) {
      const view = renderShell(workbenchModel(phase));
      expect(el("[data-phase-pill]").textContent, phase).toBe(PHASE_LABEL[phase]);
      view.unmount();
    }
  });

  it("저장 전 세션은 가짜 식별자 없이 이름과 국면을 표시한다", () => {
    renderShell(workbenchModel("recording", { testId: null }));
    expect(el("[data-phase-test-name]").textContent).not.toBe("");
    expect(el("[data-phase-pill]").textContent).toBe(PHASE_LABEL.recording);
    expect(document.querySelector(".workbench-test-id")).toBeNull();
  });

  it("보조 이동은 화면 메뉴를 열어 실행하고 주요 조작은 밖에 유지한다", async () => {
    const onBack = vi.fn();
    const onRun = vi.fn();
    render(<Workbench model={workbenchModel("running")}
      phaseActions={<button onClick={onRun}>실행</button>}
      headerActions={<button onClick={onBack}>목록으로</button>}
      onSelectStep={vi.fn()} onCloseDetail={vi.fn()} />);
    const menu = screen.getByRole("button", { name: "화면 메뉴" });
    expect(menu.getAttribute("aria-expanded")).toBe("false");
    const run = screen.getByRole("button", { name: "실행" });
    expect(menu.contains(run)).toBe(false);
    await userEvent.click(run);
    expect(onRun).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole("button", { name: "화면 메뉴" }));
    expect(menu.getAttribute("aria-expanded")).toBe("true");
    await userEvent.click(screen.getByRole("button", { name: "목록으로" }));
    expect(onBack).toHaveBeenCalledOnce();
  });
});

describe("결말 요약은 화면에 하나뿐이다 (FR-218d · 005 FR-140 · U-19)", () => {
  it("국면 띠에만 있다", () => {
    renderShell(
      workbenchModel("result", {
        phaseBar: {
          phaseLabel: "결과",
          phaseTone: "success",
          runSummary: "통과 · 2 / 2 · 0.24 s",
          progressLabel: null,
        },
      }),
    );
    expect(document.querySelectorAll("[data-run-summary]")).toHaveLength(1);
  });

  it("일곱 국면 전부에서 자리가 하나를 넘지 않는다 (T063)", () => {
    // 요약을 **갖는** 국면과 **갖지 않는** 국면을 함께 돈다. 갖지 않는 국면에서 자리가
    // 생기면 빈 문장이 화면에 남고, 갖는 국면에서 둘이 되면 U-19 가 되살아난다.
    for (const phase of PHASES) {
      for (const runSummary of [null, "실패 · Step 02 에서 실패 · 1 / 2 통과"]) {
        const view = renderShell(
          workbenchModel(phase, {
            phaseBar: {
              phaseLabel: PHASE_LABEL[phase],
              phaseTone: "neutral",
              runSummary,
              progressLabel: null,
            },
          }),
        );
        const found = document.querySelectorAll("[data-run-summary]").length;
        expect(found, `${phase} · runSummary=${String(runSummary)}`).toBe(
          runSummary === null ? 0 : 1,
        );
        view.unmount();
      }
    }
  });

  it("실패 상세가 보조 영역에 있어도 결말 요약은 늘지 않는다", () => {
    renderShell(
      workbenchModel("result", {
        phaseBar: {
          phaseLabel: "결과",
          phaseTone: "danger",
          runSummary: "실패 · Step 02 에서 멈춤",
          progressLabel: null,
        },
        work: {
          kind: "failure_detail",
          step: stepResult({ outcome: "fail", error_message: "요소를 찾지 못했습니다" }),
          diagnosis: null,
        },
      }),
    );
    expect(document.querySelectorAll("[data-run-summary]")).toHaveLength(1);
  });
});

describe("국면 보조 영역 (FR-218e)", () => {
  it("없으면 자리를 차지하지 않는다", () => {
    renderShell(workbenchModel("running", { work: null }));
    expect(document.querySelector("[data-workbench-work]")).toBeNull();
  });

  it("있으면 좌측 대상 앱 영역 아래에 온다", () => {
    renderShell(
      workbenchModel("ai_authoring", {
        work: {
          kind: "ai_progress",
          instruction: "로그인하고 프로젝트를 만든다",
          messages: [],
          error: null,
          blocked: null,
        },
      }),
    );
    const target = el("[data-workbench-target]");
    const aside = el("[data-workbench-work='ai_progress']");
    expect(target.compareDocumentPosition(aside) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // 같은 부모(좌측 열) 안에 있다 — Step 패널 쪽이 아니다.
    expect(aside.parentElement).toBe(target.parentElement);
  });

  it("보조 영역이 있든 없든 다른 영역의 자리가 바뀌지 않는다", () => {
    const without = renderShell(workbenchModel("running", { work: null }));
    const shapeA = el("[data-workbench-step-panel]").className;
    without.unmount();

    renderShell(
      workbenchModel("running", {
        work: {
          kind: "ai_progress",
          instruction: "x",
          messages: [],
          error: null,
          blocked: null,
        },
      }),
    );
    expect(el("[data-workbench-step-panel]").className).toBe(shapeA);
  });
});

describe("AI 실패는 국면·세션 상태와 무관하게 보인다 (FR-218f · FR-253 · 001 R2)", () => {
  const blocked = {
    attempted: "click role=button \"저장\"",
    reason: "저장 버튼을 찾지 못했습니다",
    question: null,
    choices: ["사람이 이어받기", "다시 시도"],
  };

  it("AI 작성 국면에서 차단 사유가 상시 보인다", () => {
    renderShell(
      workbenchModel("ai_authoring", {
        work: {
          kind: "ai_progress",
          instruction: "x",
          messages: [],
          error: null,
          blocked,
        },
      }),
    );
    expect(el("[data-always-visible-failure]")).not.toBeNull();
    expect(screen.getByText("저장 버튼을 찾지 못했습니다")).toBeTruthy();
  });

  it("상태가 일시정지로 바뀌어도 차단 사유가 사라지지 않는다", () => {
    // 001 research R2 의 결함이 정확히 이것이었다 — AI 가 실패해 `paused` 로 바뀌는
    // 순간 실패를 그리는 컴포넌트가 조건 뒤로 숨었다.
    renderShell(
      workbenchModel("paused", {
        work: {
          kind: "ai_progress",
          instruction: "x",
          messages: [],
          error: null,
          blocked,
        },
      }),
    );
    expect(screen.getByText("저장 버튼을 찾지 못했습니다")).toBeTruthy();
  });

  it("사람이 직접 조작 국면에서도 보인다", () => {
    renderShell(
      workbenchModel("takeover", {
        work: { kind: "takeover_guide", recording: false, blocked, error: null },
      }),
    );
    expect(screen.getByText("저장 버튼을 찾지 못했습니다")).toBeTruthy();
  });
});

describe("대상 앱 영역 (FR-244·FR-245)", () => {
  it("비었을 때 이유를 밝힌다 — 네 이유가 서로 다른 문장이다", () => {
    const messages = new Set<string>();
    for (const reason of ["not_started", "not_collected", "session_lost", "not_supported"] as const) {
      const view = renderShell(workbenchModel("result", { target: { kind: "empty", reason } }));
      const box = el(`[data-target-empty='${reason}']`);
      messages.add(box.textContent ?? "");
      view.unmount();
    }
    expect(messages.size).toBe(4);
  });

  it("산출물이 미러와 같은 자리를 쓴다 (S-11 해소)", () => {
    const mirror = renderShell(
      workbenchModel("running", {
        target: { kind: "mirror", mirror: <div>미러</div>, currentUrl: "http://t/", tabs: null },
      }),
    );
    const mirrorParent = el("[data-workbench-target]").parentElement;
    mirror.unmount();

    renderShell(
      workbenchModel("result", {
        target: {
          kind: "artifacts",
          selected: "screenshot",
          available: ["screenshot", "console", "network"],
          body: <div>스크린샷</div>,
        },
      }),
    );
    // 같은 자리(좌측 열의 첫 자식)를 쓴다.
    expect(el("[data-workbench-target]").parentElement!.style.flex).toBe(
      mirrorParent!.style.flex,
    );
  });

  it("제공되는 산출물만 선택할 수 있다", () => {
    renderShell(
      workbenchModel("result", {
        target: {
          kind: "artifacts",
          selected: "screenshot",
          available: ["screenshot", "console", "network"],
          body: null,
        },
      }),
    );
    expect(el("[data-artifact-tab='trace']")).toBeNull();
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
      "SCREENSHOT", "CONSOLE", "NETWORK",
    ]);
  });
});

const DETAIL_FIXTURE = {
  step: null,
  index: 0,
  attempts: null,
  candidates: null,
  dropCandidates: null,
  repickWaiting: null,
  failure: null,
} as const;

/**
 * 008 — FR-230 이 표로 대체됐다.
 *
 * 007 은 「자리가 모든 국면에서 같다」로 S-05 를 막았다. 그런데 S-05 의 실제 원인은
 * **구현이 두 벌이라 갈라진 것**이었지 자리가 둘이라는 사실 자체가 아니었다. 같은
 * 라운드가 ③-b 를 「그 국면의 주 작업 자리」로 정하고 편집 국면에 `fill` 을 주면서
 * (FR-257 · 근거는 「하는 일은 Step 편집이다」) 정작 그 폼은 겹침에 두어, 편집 화면의
 * 절반이 빈 채로 남았다.
 *
 * 그래서 지키는 것을 바꾼다 — **구현이 한 벌인가**, **자리를 표가 정하는가**,
 * **항목이 두 배치에서 같은가**. 셋이 지켜지면 S-05 는 재발할 수 없다.
 */
describe("Step 상세는 하나의 구현을 작업 목적에 맞게 배치한다", () => {
  it("모든 국면에서 정확히 한 벌만 그려진다 (SC-001)", () => {
    for (const phase of PHASES) {
      const view = renderShell(
        workbenchModel(phase, { focusedStepId: "st-1", detail: { ...DETAIL_FIXTURE } }),
      );
      expect(
        document.querySelectorAll("[data-workbench-step-detail]"),
        `국면 ${phase}`,
      ).toHaveLength(1);
      view.unmount();
    }
  });

  it("편집 상세는 주 작업 영역에, 실행과 결과 상세는 임시 검사 창에 놓인다", () => {
    for (const phase of PHASES) {
      const view = renderShell(
        workbenchModel(phase, { focusedStepId: "st-1", detail: { ...DETAIL_FIXTURE } }),
      );
      const detail = el("[data-workbench-step-detail]");
      const layer = el("[data-workbench-detail-layer]");
      expect(layer.contains(detail), phase).toBe(true);
      if (phase === "editing") {
        expect(el("[data-workbench-left-column]").contains(layer)).toBe(true);
        expect(layer.hasAttribute("data-edit-detail-inline")).toBe(true);
        expect(detail.closest('[data-slot="scrim"]')).toBeNull();
      } else {
        expect(detail.closest('[data-slot="scrim"]')).toBe(layer);
      }
      view.unmount();
    }
  });


});
