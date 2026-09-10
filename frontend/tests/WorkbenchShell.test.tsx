/**
 * 007 T025 — 통합 화면 껍데기 (SC-003 · FR-217·FR-218·FR-218a~f).
 *
 * **이 파일이 지키는 것은 껍데기의 동일성이다.** 지금은 편집 국면만 껍데기 자체가 다르다 —
 * 다른 화면은 기준 폭 1440 아트보드 + 56px 헤더인데 편집 화면은 최대 폭 1080 의 가운데
 * 정렬 본문이고 헤더·경로·상태 표시가 없다 (S-06).
 *
 * 치수는 디자인에서 온 값이다 (008) — 56px·48px 는 국면 공통, 460px 는
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

  it("국면 띠는 48px 이다 — 008 「계기판」 값 (v1 은 74px 였다)", () => {
    renderShell(workbenchModel("running"));
    expect(el("[data-workbench-phase-bar]").style.flex).toBe("0 0 48px");
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
    // 015 T030 — 좌측 열이 클래스로 바뀌었다. `flex-1` 이 `flex:1 1 0%` 이므로 grow 는 1 이다.
    // 묻는 것은 그대로: **남는 폭을 가져가는 것이 좌측뿐인가.**
    expect(
      left.style.flexGrow !== "" ? left.style.flexGrow : /\bflex-1\b/.test(left.className) ? "1" : "0",
      "좌측 열이 남는 폭을 가져가지 않는다",
    ).toBe("1");
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
      // 008 — 확정 디자인이 제품 표시를 「ITB」로 그린다. 헤더가 56px 로 내려온 만큼
      // 표시도 줄었다. 단언 대상은 그대로다 — 모든 국면에 제품 표시가 있는가.
      expect(screen.getByText("ITB"), phase).toBeTruthy();
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
    // 008 — 경로 표시가 확정 디자인의 형태(`.lbl` + `.pill`)로 나뉘었다. 자리를
    // 비우지 않는다는 요구는 그대로다 (FR-217).
    expect(screen.getByText("초안")).toBeTruthy();
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
    const shapeA = el("[data-workbench-step-panel]").style.flex;
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
    expect(el("[data-workbench-step-panel]").style.flex).toBe(shapeA);
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
describe("Step 상세 — 구현도 하나, 자리도 하나다 (FR-229·FR-230·FR-231)", () => {
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

  it("자리가 모든 국면에서 같다 — 우측 겹침 하나다 (FR-230 · 2026-09-09)", () => {
    /*
      **008 의 표가 없어졌다.** 그 라운드는 자리를 국면별 표(`DETAIL_PLACEMENT`)로 빼고
      편집 국면만 ③-b 인라인으로 걸었다. 근거는 「편집 국면에는 미러가 없어 가릴 것이
      없다」였고 그 자체로는 옳았다.

      사용자가 그 배치를 문제로 보고했다 (2026-09-09): 「step 상세 보는 위치는 오른쪽에
      뜨고, 편집하기하면 왼쪽 아래에 뜨는데, 한쪽에 뜨도록 해야함」. 같은 것을 보는 자리가
      두 곳이면 사용자는 매번 어디를 볼지 판단해야 한다 — 007 이 FR-230 으로 정한 성질이
      실제로 필요한 것이었다.

      그래서 이 검사는 표와 대조하지 않고 **자리가 하나임을** 센다. 표와 대조하는 검사는
      표가 없어졌으므로 있을 수 없고, 있으면 그것이 표를 되살리라는 압력이 된다.
    */
    for (const phase of PHASES) {
      const view = renderShell(
        workbenchModel(phase, { focusedStepId: "st-1", detail: { ...DETAIL_FIXTURE } }),
      );
      const detail = el("[data-workbench-step-detail]");
      expect(detail.style.width, `국면 ${phase}`).toBe("640px");
      expect(detail.getAttribute("role"), `국면 ${phase}`).toBe("dialog");
      // ③-b 안에 상세가 걸린 국면이 없다 — 인라인 자리는 사라졌다.
      expect(
        document.querySelector('[data-workbench-work="step_detail"]'),
        `국면 ${phase}`,
      ).toBeNull();
      view.unmount();
    }
  });

  /*
    ─── 「배치는 껍데기만 바꾼다」 검사가 없어졌다 (2026-09-09) ───────────────────

    008 판은 같은 입력을 주고 `placement` 만 바꿔 두 껍데기의 본문 텍스트가 **같은지**
    봤다. FR-231 이 요구한 「항목이 두 배치에서 같다」를 그대로 센 검사였다.

    배치가 하나로 돌아왔으므로 **비교할 두 번째 배치가 없다.** 대신 국면끼리 비교해
    보았고, 그것은 성립하지 않는다는 것을 곧 확인했다 — 같은 입력이어도 국면마다 접히는
    조작이 다르므로 본문이 다르다 (편집 국면에는 「다시 집기」가 없고 일시정지에는 있다).
    그 차이는 결함이 아니라 이 라운드가 만든 정상 동작이다.

    남은 성질은 위 두 검사가 센다 — **구현이 한 벌**(「정확히 한 벌만 그려진다」)이고
    **자리가 하나**(「우측 겹침 하나다」)라는 것. FR-231 이 막으려던 S-05 의 원인은
    구현이 둘이라 갈라진 것이었고, 그 원인은 첫 번째 검사가 계속 지킨다.
  */
});
