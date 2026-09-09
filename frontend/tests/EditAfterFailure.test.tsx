/**
 * 2026-09-09 사용자 보고 — **실행 후 에러가 났을 때 고치는 방법이 없었다.**
 *
 * 보고 문장: 「실행후 에러가 났을때, 고치기 즉 편집을 하는 방법이 없음」.
 *
 * 그 상태가 왜 생겼나. 실패로 끝난 세션에서 서버는 편집 명령을 받지 않고
 * (`state_machine.py` 의 `FAILED` 는 전이표가 비어 있다), 편집 화면으로 가는 조작은
 * 권한표에서 `–`(해당 없음)였다. 그런데 **같은 화면이 그 없는 조작을 이름으로 안내했다** —
 * 실패 알림이 「「Step nn 고치기」 또는 「Step nn부터 실행」을 쓰세요」라고 적는다.
 * 006 E-03 이 정확히 그 형태이며, 이 파일이 그것을 되살아나지 않게 센다.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { sessionProps } from "./helpers/session";
import { clickStep, fillStep, sessionView } from "./helpers/workbench";
import type { SessionView } from "../src/api/client";

afterEach(cleanup);

/** 실패로 끝난 실행 — Step 02 에서 멈췄다. */
function failedRun(overrides: Partial<SessionView> = {}) {
  return sessionView({
    state: "failed",
    authoring_mode: "record",
    test_id: "TC-001",
    current_step_index: 1,
    saved_at: "2026-09-09T00:00:00Z",
    has_unsaved_changes: false,
    steps: [clickStep({ id: "st-1" }), fillStep({ id: "st-2" })],
    ...overrides,
  });
}

const OUTCOMES: Record<string, "pass" | "fail"> = { "st-1": "pass", "st-2": "fail" };

function props(view: SessionView, extra = {}) {
  return sessionProps({
    view,
    outcomeOf: (step) => OUTCOMES[step.id] ?? "not_run",
    ...extra,
  });
}

function action(id: string): HTMLButtonElement | null {
  return document.querySelector(`button[data-action="${id}"]`);
}

describe("실패한 실행에서 고치러 가는 길 (2026-09-09)", () => {
  it("실패한 Step 을 가리키는 「고치기」가 화면에 있다", () => {
    render(<SessionWorkbench {...props(failedRun(), { onEditStep: () => undefined })} />);
    const button = action("nav.editStep");
    expect(button, "실패한 실행 화면에 편집으로 가는 조작이 없다").not.toBeNull();
    expect(button!.disabled).toBe(false);
    /*
      **라벨이 어느 Step 인지 말한다.** 실패한 자리를 화면이 이미 알고 있는데 「고치기」
      라고만 쓰면 사용자는 무엇을 고치러 가는지 모른 채 화면을 옮긴다 (005 FR-136 이
      알림에서 같은 판단을 했다).
    */
    expect(button!.textContent).toContain("Step 02");
  });

  it("누르면 그 Step 의 식별자와 자리를 함께 넘긴다", () => {
    const onEditStep = vi.fn();
    render(<SessionWorkbench {...props(failedRun(), { onEditStep })} />);
    action("nav.editStep")!.click();
    /*
      **자리도 넘긴다.** 목적지가 「그 자리 앞까지 재생한 뒤 멈춘 세션」이기 때문이다
      (009 FR-291 · 2026-09-09 사용자 결정 — 「직전 스텝까지의 세션을 제공」). 식별자만
      넘기면 어디까지 재생할지 알 수 없다.
    */
    expect(onEditStep).toHaveBeenCalledWith("st-2", 1);
  });

  it("지목한 Step 이 있으면 그것을 존중한다", () => {
    const onEditStep = vi.fn();
    render(
      <SessionWorkbench {...props(failedRun(), { onEditStep, focusedStepId: "st-1" })} />,
    );
    expect(action("nav.editStep")!.textContent).toContain("Step 01");
    action("nav.editStep")!.click();
    expect(onEditStep).toHaveBeenCalledWith("st-1", 0);
  });

  it("저장하지 않은 기록이 있으면 잠기고 순서를 말한다 — 감추지 않는다", () => {
    /*
      편집 화면은 **저장된 정의**를 읽는다. 저장하지 않고 넘어가면 방금 기록한 것이
      화면에서 사라지므로, 자리는 남기고 순서를 말한다 (저장 → 편집). `keep` 인 사유다 —
      같은 화면의 「저장」으로 곧바로 풀린다.
    */
    render(
      <SessionWorkbench
        {...props(failedRun({ has_unsaved_changes: true }), { onEditStep: () => undefined })}
      />,
    );
    expect(action("nav.editStep")!.disabled).toBe(true);
    expect(
      document.querySelector("[data-disabled-reason='nav.editStep']")?.textContent,
    ).toContain("저장한 뒤");
    // 저장은 같은 화면에 있다 — 갈 곳 없는 안내가 되지 않는다 (006 E-03).
    expect(action("save")).not.toBeNull();
  });

  it("실패 알림이 이름으로 안내하는 조작이 실제로 화면에 있다 (006 E-03)", () => {
    render(<SessionWorkbench {...props(failedRun(), { onEditStep: () => undefined })} />);
    /*
      알림 문구와 버튼 라벨이 **같은 이름**을 써야 한다. 문구가 「Step 02 고치기」라고
      말하는데 화면의 버튼이 다른 이름이면, 사용자는 안내받은 것을 찾지 못한다.
    */
    const notice = document.querySelector("[data-notice='resume-blocked']");
    if (notice !== null) {
      expect(notice.textContent).toContain("Step 02 고치기");
      expect(action("nav.editStep")!.textContent).toContain("Step 02 고치기");
    } else {
      // 알림이 없는 경로여도 조작은 있어야 한다 — 그것이 이 파일의 본론이다.
      expect(action("nav.editStep")).not.toBeNull();
    }
  });

  it("돌고 있는 실행에서는 이 길이 열리지 않는다 — 실행 중 정의를 고치지 않는다", () => {
    render(
      <SessionWorkbench
        {...props(
          sessionView({ state: "replaying", test_id: "TC-001", saved_at: "2026-09-09T00:00:00Z" }),
          { onEditStep: () => undefined },
        )}
      />,
    );
    expect(action("nav.editStep")).toBeNull();
  });
});
