/**
 * 007 T025 — 통합 화면 껍데기 (SC-003 · FR-217·FR-218·FR-218a~f).
 *
 * **이 파일이 지키는 것은 껍데기의 동일성이다.** 지금은 편집 국면만 껍데기 자체가 다르다 —
 * 다른 화면은 기준 폭 1440 아트보드 + 60px 헤더인데 편집 화면은 최대 폭 1080 의 가운데
 * 정렬 본문이고 헤더·경로·상태 표시가 없다 (S-06).
 *
 * 치수는 확정 디자인에서 온 값이다 (research R1) — 60px·74px 는 5종 공통, 460px 는
 * Step 패널을 가진 3종 공통. **007 이 새로 정한 값이 아니다.**
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Workbench } from "../src/components/workbench/Workbench";
import type { WorkbenchModel } from "../src/components/workbench/model";
import { PHASES } from "../src/lib/phase";
import { PHASE_LABEL } from "../src/lib/wording";
import { workbenchModel } from "./helpers/model";
import { stepResult } from "./helpers/workbench";

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

describe("3층 구조 (T018 · FR-218c)", () => {
  it("층의 구성과 순서가 고정이다 — 헤더 → 국면 띠 → 본문", () => {
    renderShell(workbenchModel("running"));
    const bar = el("[data-workbench-phase-bar]");
    const target = el("[data-workbench-target]");
    const panel = el("[data-workbench-step-panel]");
    // 문서 순서가 곧 층의 순서다.
    expect(bar.compareDocumentPosition(target) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(target.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("국면 띠는 74px 이다 — 확정 디자인 5종 공통값", () => {
    renderShell(workbenchModel("running"));
    expect(el("[data-workbench-phase-bar]").style.flex).toBe("0 0 74px");
  });

  it("Step 패널은 460px 고정이다 — 확정 디자인 3종 공통값", () => {
    renderShell(workbenchModel("running"));
    expect(el("[data-workbench-step-panel]").style.flex).toBe("0 0 460px");
  });

  it("최소 기준 폭이 1440px 이고 넓으면 늘어난다 (FR-218·FR-218a)", () => {
    renderShell(workbenchModel("running"));
    // 아트보드 내부 컨테이너가 최소 폭을 갖고 100% 로 늘어난다.
    const frame = el("[data-workbench-phase-bar]").parentElement!;
    expect(frame.style.minWidth).toBe("1440px");
    expect(frame.style.width).toBe("100%");
  });

  it("넓어질 때 늘어나는 것은 좌측 대상 앱 영역뿐이다 (FR-218a)", () => {
    renderShell(workbenchModel("running"));
    // 좌측은 남는 폭을 가져가고(grow 1), Step 패널은 고정이다(grow 0 · basis 460px).
    const left = el("[data-workbench-target]").parentElement!;
    const panel = el("[data-workbench-step-panel]");
    expect(left.style.flexGrow).toBe("1");
    expect(panel.style.flexGrow).toBe("0");
    expect(panel.style.flexBasis).toBe("460px");
  });
});

describe("일곱 국면이 같은 껍데기를 쓴다 (SC-003 · FR-217)", () => {
  it("헤더·국면 띠·본문·Step 패널이 일곱 국면 전부에 있다", () => {
    for (const phase of PHASES) {
      const view = renderShell(workbenchModel(phase));
      expect(el("[data-workbench-phase-bar]"), phase).not.toBeNull();
      expect(el("[data-workbench-target]"), phase).not.toBeNull();
      expect(el("[data-workbench-step-panel]"), phase).not.toBeNull();
      expect(screen.getByText("TEST BUILDER"), phase).toBeTruthy();
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
          el("[data-workbench-step-panel]").style.flex,
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

  it("테스트 식별자가 없는 작성 세션도 경로 자리를 비우지 않는다", () => {
    renderShell(workbenchModel("recording", { testId: null }));
    expect(screen.getByText("테스트 / 초안")).toBeTruthy();
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

  it("실패 상세가 보조 영역에 있어도 결말 요약은 늘지 않는다", () => {
    renderShell(
      workbenchModel("result", {
        phaseBar: {
          phaseLabel: "결과",
          phaseTone: "danger",
          runSummary: "실패 · Step 02 에서 멈춤",
          progressLabel: null,
        },
        aside: {
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
    renderShell(workbenchModel("running", { aside: null }));
    expect(document.querySelector("[data-workbench-aside]")).toBeNull();
  });

  it("있으면 좌측 대상 앱 영역 아래에 온다", () => {
    renderShell(
      workbenchModel("ai_authoring", {
        aside: {
          kind: "ai_progress",
          instruction: "로그인하고 프로젝트를 만든다",
          messages: [],
          error: null,
          blocked: null,
        },
      }),
    );
    const target = el("[data-workbench-target]");
    const aside = el("[data-workbench-aside='ai_progress']");
    expect(target.compareDocumentPosition(aside) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // 같은 부모(좌측 열) 안에 있다 — Step 패널 쪽이 아니다.
    expect(aside.parentElement).toBe(target.parentElement);
  });

  it("보조 영역이 있든 없든 다른 영역의 자리가 바뀌지 않는다", () => {
    const without = renderShell(workbenchModel("running", { aside: null }));
    const shapeA = el("[data-workbench-step-panel]").style.flex;
    without.unmount();

    renderShell(
      workbenchModel("running", {
        aside: {
          kind: "ai_progress",
          instruction: "x",
          messages: [],
          error: null,
          blocked: null,
        },
      }),
    );
    expect(el("[data-workbench-step-panel]").style.flex).toBe(shapeA);
  });
});

describe("AI 실패는 국면·세션 상태와 무관하게 보인다 (FR-218f · FR-253 · 001 R2)", () => {
  const blocked = {
    attempted: "click role=button \"저장\"",
    reason: "저장 버튼을 찾지 못했습니다",
    choices: ["사람이 이어받기", "다시 시도"],
  };

  it("AI 작성 국면에서 차단 사유가 상시 보인다", () => {
    renderShell(
      workbenchModel("ai_authoring", {
        aside: {
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
        aside: {
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
        aside: { kind: "takeover_guide", recording: false, blocked, error: null },
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

  it("지원되지 않는 산출물은 감추지 않고 비활성으로 남는다 (FR-246 · DC-007)", () => {
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
    const trace = el("[data-artifact-tab='trace']") as HTMLButtonElement;
    expect(trace).not.toBeNull();
    expect(trace.disabled).toBe(true);
  });
});

describe("Step 상세는 모든 국면에서 같은 자리다 (FR-230)", () => {
  it("우측 겹침 640px 로 열린다", () => {
    renderShell(
      workbenchModel("editing", {
        focusedStepId: "st-1",
        detail: {
          step: null,
          index: 0,
          attempts: null,
          candidates: null,
          dropCandidates: null,
          repickWaiting: null,
          failure: null,
        },
      }),
    );
    const detail = el("[data-workbench-step-detail]");
    expect(detail.style.width).toBe("640px");
  });

  it("일곱 국면에서 같은 폭·같은 자리로 열린다", () => {
    const shapes = new Set<string>();
    for (const phase of PHASES) {
      const view = renderShell(
        workbenchModel(phase, {
          focusedStepId: "st-1",
          detail: {
            step: null,
            index: 0,
            attempts: null,
            candidates: null,
            dropCandidates: null,
            repickWaiting: null,
            failure: null,
          },
        }),
      );
      const detail = el("[data-workbench-step-detail]");
      shapes.add(`${detail.style.width}|${detail.parentElement!.style.position}`);
      view.unmount();
    }
    expect(shapes.size).toBe(1);
  });
});
