/**
 * **편집면이 하나인가.** 027 FR-008~FR-013 · SC-004.
 *
 * ## 이 검사가 존재하는 이유
 *
 * 027 이전에는 Step 편집면이 두 벌이었다 — `StepEditFields`(편집 화면)와 `StepDetail`
 * 의 자체 칸들(세션 화면). 한쪽에 칸을 더할 때마다 다른 쪽에 없는 칸이 생겼고, 실제로
 * **「올릴 파일 이름」이 세션 화면에만 있었다.** 사용자에게는 「편집 화면에서는 못
 * 고치는 것」으로 보인다.
 *
 * ## 무엇을 재는가
 *
 * 「두 화면이 같은 컴포넌트를 쓰는가」가 아니라 **「고칠 수 있는 항목이 같은가」**를
 * 잰다. 앞의 것은 구현이고 뒤의 것이 사용자가 겪는 사실이다.
 *
 * 항목 목록을 **적어 두지 않는다** — 렌더 결과에서 읽는다. 적어 두면 그 목록이 낡고,
 * 낡은 목록을 검사가 믿는다 (research R2).
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { StepEditFields } from "../src/components/StepEditFields";
import { StepDetail } from "../src/components/workbench/StepDetail";
import { capabilitiesFor } from "../src/lib/capabilities";
import { clickStep, fillStep } from "./helpers/workbench";
import type { Step } from "../src/types/generated/step";

afterEach(cleanup);

const CAPS = capabilitiesFor("paused", { definitionEditable: true, liveBrowser: true });

/** 그 화면이 **고칠 수 있게 그린** 항목들. 접근 이름으로 읽는다 */
function editableLabels(): string[] {
  return [...document.querySelectorAll("input")]
    .map((el) => el.getAttribute("aria-label") ?? el.getAttribute("id") ?? "")
    .filter((name) => name !== "");
}

function renderDetail(step: Step) {
  render(
    <StepDetail
      detail={{
        step,
        index: 0,
        attempts: null,
        candidates: null,
        dropCandidates: null,
        repickWaiting: null,
        failure: null,
      }}
      capabilities={CAPS}
      onSave={() => undefined}
      onRepick={() => undefined}
      onClose={() => undefined}
    />,
  );
}

function renderFields(step: Step) {
  render(
    <StepEditFields
      step={step}
      sensitiveNames={[]}
      editable
      onChange={() => undefined}
    />,
  );
}

describe("두 화면이 같은 항목을 고친다 (FR-009 · SC-004)", () => {
  it.each([
    ["클릭 Step", clickStep({ id: "st-1" })],
    ["채우기 Step", fillStep({ id: "st-2" })],
  ])("%s — Step 상세와 편집면이 **같은 항목**을 그린다", (_name, step) => {
    renderDetail(step as Step);
    const inDetail = editableLabels();
    cleanup();

    renderFields(step as Step);
    const inFields = editableLabels();

    // 상세는 편집면을 품고 있으므로 편집면의 항목을 **전부** 가져야 한다.
    for (const label of inFields) {
      expect(inDetail, `「${label}」이 Step 상세에 없다 — 편집면이 갈렸다`).toContain(label);
    }
  });
});

describe("Step 종류가 항목을 정한다 (FR-010)", () => {
  it("클릭 Step 에는 입력값 칸이 없다", () => {
    renderFields(clickStep({ id: "st-1" }) as Step);
    expect(screen.queryByLabelText("Step 입력값")).toBeNull();
  });

  it("채우기 Step 에는 입력값 칸이 있다", () => {
    renderFields(fillStep({ id: "st-2" }) as Step);
    expect(screen.getByLabelText("Step 입력값")).toBeTruthy();
  });

  it("**판정이 한 곳이다** — 상세도 같은 결과를 그린다", () => {
    renderDetail(clickStep({ id: "st-1" }) as Step);
    expect(screen.queryByLabelText("Step 입력값")).toBeNull();
    cleanup();

    renderDetail(fillStep({ id: "st-2" }) as Step);
    expect(screen.getByLabelText("Step 입력값")).toBeTruthy();
  });
});

describe("읽기 전용을 표현한다 (FR-011)", () => {
  it("`editable={false}` 이면 **모든 칸이 잠긴다**", () => {
    render(
      <StepEditFields
        step={fillStep({ id: "st-2" }) as Step}
        sensitiveNames={[]}
        editable={false}
        onChange={() => undefined}
      />,
    );
    for (const el of document.querySelectorAll("input")) {
      expect(el.disabled, `${el.getAttribute("aria-label")} 이 잠기지 않았다`).toBe(true);
    }
  });

  it("**참조는 읽기 전용이다** — 민감 변수 목록을 몰라도 그렇다", () => {
    render(
      <StepEditFields
        step={fillStep({ id: "st-2", value: "{{PASSWORD}}" }) as Step}
        sensitiveNames={[]}
        editable
        onChange={() => undefined}
      />,
    );
    expect((screen.getByLabelText("Step 입력값") as HTMLInputElement).disabled).toBe(true);
  });
});

describe("항목을 더하면 모든 화면이 갖는다 (FR-013)", () => {
  it("**올릴 파일 이름** — 027 이전에는 세션 화면에만 있었다", () => {
    const upload = {
      ...clickStep({ id: "st-3" }),
      type: "upload",
      file_name: "보고서.xlsx",
    } as unknown as Step;

    renderFields(upload);
    expect(
      screen.getByLabelText("올릴 파일 이름"),
      "편집면에 파일 이름 칸이 없다 — 한쪽에만 있던 구멍이 되살아났다",
    ).toBeTruthy();
    cleanup();

    renderDetail(upload);
    expect(screen.getByLabelText("올릴 파일 이름")).toBeTruthy();
  });
});
