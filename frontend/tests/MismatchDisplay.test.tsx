/**
 * 결함 후보가 Step 목록과 상세에 드러난다 (020 T026 · FR-014·FR-015·FR-027).
 *
 * **작성 직후가 사람이 맥락을 가장 많이 들고 있는 시점이다.** 여기서 보이지 않으면
 * 나중에 재실행 결과를 보고 「이건 왜 실패하지」부터 다시 시작한다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Workbench } from "../src/components/workbench/Workbench";
import type {
  StepDetail as StepDetailModel,
  WorkbenchModel,
  WorkbenchStep,
} from "../src/components/workbench/model";
import type { AssertionStep, Step } from "../src/types/generated/step";
import { workbenchModel } from "./helpers/model";

const RECORDED_AT = "2026-09-28T12:00:00Z";

function assertionStep(mismatched: boolean, observed = "처리 완료"): AssertionStep {
  return {
    id: "step-01",
    type: "assertion",
    label: "저장 문구 확인",
    author: "ai",
    tab: 0,
    timeout_ms: 10000,
    frame_url: null,
    assertion: {
      kind: "text",
      target: null,
      match: "equals",
      value: "저장되었습니다",
    },
    mismatch: mismatched
      ? { observed, truncated: false, recorded_at: RECORDED_AT }
      : null,
  } as AssertionStep;
}

function row(step: Step): WorkbenchStep {
  return {
    id: step.id,
    index: 0,
    label: step.label,
    step,
    outcome: "recorded",
    durationMs: null,
    isPausedHere: false,
  };
}

/** 상세 판은 필수 칸이 많다. Step 말고는 전부 비운다 — 이 파일이 재는 것이 아니다. */
function detailOf(step: Step): StepDetailModel {
  return {
    step,
    index: 0,
    attempts: null,
    candidates: null,
    dropCandidates: null,
    repickWaiting: null,
    failure: null,
  };
}

function mount(over: Partial<WorkbenchModel>, onClearMismatch?: (id: string) => void) {
  return render(
    <Workbench
      model={workbenchModel("review", over)}
      phaseActions={null}
      onSelectStep={vi.fn()}
      onCloseDetail={vi.fn()}
      {...(onClearMismatch ? { onClearMismatch } : {})}
    />,
  );
}

const chip = () => document.querySelector('[data-cell="mismatch"]');
const panel = () => document.querySelector('[data-field="mismatch"]');

afterEach(cleanup);

describe("Step 목록의 결함 후보 칩 (FR-014)", () => {
  it("어긋난 검증은 다른 Step 과 구별된다", () => {
    mount({ steps: [row(assertionStep(true))] });
    expect(chip()).not.toBeNull();
    expect(chip()!.textContent).toBe("결함 후보");
  });

  it("통과한 검증에는 칩이 없다", () => {
    mount({ steps: [row(assertionStep(false))] });
    expect(chip()).toBeNull();
  });

  it("020 이전 서버가 보낸 Step 에는 칸 자체가 없다 — 그때도 칩이 없다", () => {
    // **`null` 과 `undefined` 를 같게 다뤄야 한다.** 생성된 타입은 이 칸을 필수로
    // 표기하지만 옛 서버의 응답에는 없고, 그때 값은 `undefined` 다. `!== null` 만
    // 보면 없는 기록을 그리려다 화면이 터진다 — 실제로 그렇게 터졌다.
    const legacy = assertionStep(false);
    delete (legacy as unknown as Record<string, unknown>).mismatch;
    mount({ steps: [row(legacy)], focusedStepId: legacy.id, detail: detailOf(legacy) });
    expect(chip()).toBeNull();
    expect(panel()).toBeNull();
  });

  it("칩은 「결함」이 아니라 「결함 후보」다", () => {
    // 제품은 기대와 달랐다는 사실만 기록한다. 그것이 제품 결함인지 지시문 오류인지는
    // 사람이 판단한다 (spec Assumptions).
    mount({ steps: [row(assertionStep(true))] });
    expect(chip()!.textContent).not.toBe("결함");
  });
});

describe("Step 상세의 기대값과 관찰값 (FR-015)", () => {
  const detailModel = (mismatched: boolean, observed?: string, truncated = false) => {
    const step = assertionStep(mismatched, observed);
    if (mismatched && truncated && step.mismatch !== null) {
      step.mismatch = { ...step.mismatch, truncated: true };
    }
    return {
      steps: [row(step)],
      focusedStepId: step.id,
      detail: detailOf(step),
    } satisfies Partial<WorkbenchModel>;
  };

  it("기대값과 작성 시점 화면이 함께 보인다", () => {
    mount(detailModel(true));
    expect(panel()).not.toBeNull();
    const expected = document.querySelector<HTMLInputElement>("#detail-expected")!;
    const observed = document.querySelector<HTMLInputElement>("#detail-observed")!;
    // 기대값만 보여 주면 왜 결함 후보인지 알 수 없고, 관찰값만 보여 주면 무엇을
    // 요구했는지 알 수 없다. 둘이 같은 자리에 있어야 「달랐다」가 읽힌다.
    expect(expected.value).toBe("저장되었습니다");
    expect(observed.value).toBe("처리 완료");
  });

  it("기대값은 고칠 수 없다 — 이 칸은 기록이지 입력이 아니다", () => {
    mount(detailModel(true));
    expect(document.querySelector<HTMLInputElement>("#detail-observed")!.readOnly).toBe(true);
  });

  it("잘렸으면 그 사실이 드러난다 (FR-008)", () => {
    mount(detailModel(true, "가".repeat(100), true));
    expect(screen.getByText(/잘랐습니다/)).toBeTruthy();
  });

  it("어긋나지 않은 검증에는 이 칸이 없다", () => {
    mount(detailModel(false));
    expect(panel()).toBeNull();
  });
});

describe("표시 걷어내기 (FR-027)", () => {
  it("걷어낼 수 있는 자리에서는 조작이 보인다", () => {
    const onClear = vi.fn();
    mount(
      { steps: [row(assertionStep(true))], detail: detailOf(assertionStep(true)) },
      onClear,
    );
    expect(screen.getByText("결함 후보 표시 걷어내기")).toBeTruthy();
  });

  it("고칠 수 없는 국면에서는 조작을 그리지 않는다", () => {
    // 눌리지 않는 단추를 두면 사용자가 왜 안 되는지 묻게 된다 (`ownFields` 와 같은 판단).
    mount({
      steps: [row(assertionStep(true))],
      detail: detailOf(assertionStep(true)),
    });
    expect(screen.queryByText("결함 후보 표시 걷어내기")).toBeNull();
  });
});
