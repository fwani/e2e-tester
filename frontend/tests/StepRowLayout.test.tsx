/**
 * 007 T026 — Step 행의 칸 자리 (SC-002 · FR-222·FR-223·FR-227·FR-228).
 *
 * **이 파일이 지키는 것은 자리다.** 사용자가 제기한 문제의 가장 구체적인 형태가 이것이다 —
 * 같은 정보가 국면에 따라 정반대 위치에 있었다.
 *
 * - 결말 표식이 세션 화면은 행의 **오른쪽 끝**, 결과 화면은 행의 **왼쪽 첫 칸** (S-02)
 * - AI 작성 화면에는 Step **번호가 없었다** (S-08)
 * - 결과 화면에는 **대상 요약이 없었다** (S-03)
 * - Step 지목이 국면마다 다른 방식이었다 — 행 전체 / 행 안 버튼 / 불가 (S-04)
 *
 * 그래서 검사는 **칸의 순서와 개수**를 본다. 값이 있는지가 아니다.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { StepList } from "../src/components/workbench/StepList";
import { PHASES } from "../src/lib/phase";
import { workbenchStep, workbenchSteps } from "./helpers/model";
import { fillStep } from "./helpers/workbench";

import { flexOf } from "./helpers/style";
/** 행 안의 칸을 `data-cell` 로 읽는다. 순서가 곧 자리다. */
function cellsOf(row: HTMLElement): string[] {
  return Array.from(row.querySelectorAll("[data-cell]")).map(
    (el) => el.getAttribute("data-cell") ?? "",
  );
}

function renderList(steps = workbenchSteps(), onSelect = vi.fn()) {
  const view = render(
    <StepList
      steps={steps}
      authoring="record"
      focusedStepId={null}
      onSelect={onSelect}
    />,
  );
  return { view, onSelect };
}

/** 칸의 고정 순서 (contracts/ui-contract.md §1-1). */
const CELL_ORDER = ["number", "detail", "duration", "outcome"];

describe("Step 행의 칸 자리 (T026 · SC-002)", () => {
  it("칸의 순서가 고정이다 — 번호 → 상세 → 소요 시간 → 결말 표식", () => {
    renderList();
    const row = document.querySelector<HTMLElement>("[data-step-row='st-1']")!;
    expect(cellsOf(row).filter((c) => CELL_ORDER.includes(c))).toEqual(CELL_ORDER);
  });

  it("결말 표식은 행의 마지막 칸이다 (S-02 해소)", () => {
    renderList();
    const row = document.querySelector<HTMLElement>("[data-step-row='st-1']")!;
    const fixed = cellsOf(row).filter((c) => CELL_ORDER.includes(c));
    expect(fixed[fixed.length - 1]).toBe("outcome");
  });

  it("번호는 행의 첫 칸이며 모든 행에 있다 (S-08 해소 · FR-224)", () => {
    renderList();
    for (const id of ["st-1", "st-2"]) {
      const row = document.querySelector<HTMLElement>(`[data-step-row='${id}']`)!;
      const numberCell = row.querySelector("[data-cell='number']");
      expect(numberCell, `${id} 에 번호 칸이 없다`).not.toBeNull();
      expect(numberCell!.textContent!.trim()).not.toBe("");
      expect(cellsOf(row)[0]).toBe("number");
    }
  });

  it("일곱 국면에서 칸의 순서·개수가 같다 — 국면은 행 구조를 바꾸지 않는다", () => {
    const seen = new Set<string>();
    for (const phase of PHASES) {
      // 국면마다 결말이 다르다. 결말이 달라도 **칸 구성은 같아야** 한다.
      const outcome =
        phase === "recording" || phase === "ai_authoring" || phase === "takeover"
          ? "recorded"
          : phase === "running"
            ? "running"
            : phase === "result"
              ? "pass"
              : "pending";
      const { view } = renderList(workbenchSteps(outcome));
      const row = document.querySelector<HTMLElement>("[data-step-row='st-1']")!;
      seen.add(cellsOf(row).filter((c) => CELL_ORDER.includes(c)).join(","));
      view.unmount();
    }
    expect(seen.size, `국면마다 칸 구성이 달라졌다: ${[...seen].join(" | ")}`).toBe(1);
  });
});

describe("값이 없는 칸 (FR-223)", () => {
  it("소요 시간이 없으면 칸은 비지만 사라지지 않는다", () => {
    renderList(workbenchSteps());
    const row = document.querySelector<HTMLElement>("[data-step-row='st-1']")!;
    const duration = row.querySelector("[data-cell='duration']");
    expect(duration).not.toBeNull();
    expect(duration!.textContent).toBe("");
  });

  it("소요 시간이 있으면 그 칸에 들어간다 — 다른 칸이 밀리지 않는다", () => {
    renderList([workbenchStep({ durationMs: 120 })]);
    const row = document.querySelector<HTMLElement>("[data-step-row='st-1']")!;
    expect(row.querySelector("[data-cell='duration']")!.textContent).toContain("120 ms");
    expect(cellsOf(row).filter((c) => CELL_ORDER.includes(c))).toEqual(CELL_ORDER);
  });

  it("정의와 매칭되지 않은 행은 동작 종류·대상 요약·값이 비고 다른 칸이 당겨지지 않는다", () => {
    // 결과 국면에서 정의가 바뀐 뒤의 행 (research R3).
    renderList([workbenchStep({ step: null, durationMs: 88, outcome: "pass" })]);
    const row = document.querySelector<HTMLElement>("[data-step-row='st-1']")!;
    expect(row.querySelector("[data-cell='type']")).toBeNull();
    expect(row.querySelector("[data-cell='locator']")).toBeNull();
    expect(row.querySelector("[data-cell='value']")).toBeNull();
    // 고정 칸 넷은 그대로 있다.
    expect(cellsOf(row).filter((c) => CELL_ORDER.includes(c))).toEqual(CELL_ORDER);
    expect(row.querySelector("[data-cell='duration']")!.textContent).toContain("88 ms");
  });

  it("값을 가진 Step 은 값 칸을 갖는다 (FR-083 — 참조 형태로만)", () => {
    renderList([
      workbenchStep({ step: fillStep({ id: "st-1", value: "{{PASSWORD}}" }) }),
    ]);
    const row = document.querySelector<HTMLElement>("[data-step-row='st-1']")!;
    expect(row.querySelector("[data-cell='value']")!.textContent).toBe("{{PASSWORD}}");
  });
});

describe("결말 표식 (FR-225·FR-226)", () => {
  it("「기록됨」은 통과가 아니다 — 통과 체크를 그리지 않는다 (S-09 해소)", () => {
    renderList(workbenchSteps("recorded"));
    const mark = document.querySelector("[data-outcome='recorded']")!;
    expect(mark.getAttribute("aria-label")).toBe("기록됨");
    expect(document.querySelector("[data-outcome='pass']")).toBeNull();
  });

  it("건너뜀과 미실행이 서로 다른 표식이고 둘 다 라벨을 갖는다 (005 FR-151)", () => {
    renderList([
      workbenchStep({ id: "st-1", index: 0, outcome: "skipped" }),
      workbenchStep({ id: "st-2", index: 1, outcome: "not_run" }),
    ]);
    const skipped = document.querySelector("[data-outcome='skipped']")!;
    const notRun = document.querySelector("[data-outcome='not_run']")!;
    expect(skipped.getAttribute("aria-label")).toBe("건너뜀");
    expect(notRun.getAttribute("aria-label")).toBe("미실행");
    expect(skipped).not.toBe(notRun);
  });

  it("일곱 결말이 서로 다른 라벨을 갖는다 — 색만으로 구분하지 않는다", () => {
    const labels = new Set<string>();
    for (const outcome of [
      "pass",
      "fail",
      "running",
      "pending",
      "skipped",
      "not_run",
      "recorded",
    ] as const) {
      const { view } = renderList([workbenchStep({ outcome })]);
      const mark = document.querySelector("[data-cell='outcome'] [aria-label]");
      labels.add(mark?.getAttribute("aria-label") ?? `(없음:${outcome})`);
      view.unmount();
    }
    expect(labels.size).toBe(7);
  });
});

describe("Step 지목 (FR-227 · S-04 해소)", () => {
  it("행의 이름을 눌러 지목한다 — 국면에 따라 다른 방식이 아니다", async () => {
    const onSelect = vi.fn();
    renderList(workbenchSteps(), onSelect);
    await userEvent.click(screen.getByRole("button", { name: "로그인 버튼 클릭" }));
    expect(onSelect).toHaveBeenCalledWith("st-1");
  });

  it("지목한 행이 눌린 상태로 표시된다", () => {
    render(
      <StepList
        steps={workbenchSteps()}
        authoring="record"
        focusedStepId="st-2"
        onSelect={vi.fn()}
      />,
    );
    const row = document.querySelector<HTMLElement>("[data-step-row='st-2']")!;
    expect(within(row).getByRole("button", { name: "아이디 입력" }).getAttribute("aria-pressed")).toBe(
      "true",
    );
  });
});

describe("작성 주체 (FR-228 · Principle I)", () => {
  it("AI Step 과 사람 Step 의 칸 구성이 같다 — 배지로만 드러난다", () => {
    const human = workbenchStep({ id: "st-1", step: fillStep({ id: "st-1", author: "human" }) });
    const ai = workbenchStep({ id: "st-2", index: 1, step: fillStep({ id: "st-2", author: "ai" }) });
    renderList([human, ai]);
    const a = cellsOf(document.querySelector<HTMLElement>("[data-step-row='st-1']")!);
    const b = cellsOf(document.querySelector<HTMLElement>("[data-step-row='st-2']")!);
    expect(a).toEqual(b);
  });

  it("작성 배지는 Step 패널 헤더에 있다 — 행마다 그리지 않는다", () => {
    renderList();
    expect(screen.getByText(/작성 RECORD/)).toBeTruthy();
  });
});

describe("Step 패널 (FR-221)", () => {
  it("폭이 460px 고정이다 — 확정 디자인 3종 공통값 (research R1)", () => {
    renderList();
    const panel = document.querySelector<HTMLElement>("[data-workbench-step-panel]")!;
    expect(panel.className, "Step 패널이 460px 고정이 아니다").toContain("basis-steps");
    expect(flexOf(panel), "Step 패널이 줄어든다").toBe("0 0 auto");
  });

  it("Step 이 0개면 국면별 안내를 보여준다", () => {
    render(
      <StepList
        steps={[]}
        authoring="ai"
        focusedStepId={null}
        onSelect={vi.fn()}
        emptyNotice="AI 가 아직 Step 을 만들지 않았습니다."
      />,
    );
    expect(screen.getByText("AI 가 아직 Step 을 만들지 않았습니다.")).toBeTruthy();
  });
});
