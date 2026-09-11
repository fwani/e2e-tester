/**
 * **재녹화 띠는 자기 줄을 갖고, 교체 중에는 저장이 미리 잠긴다** (2026-09-11 사용자 보고).
 *
 * ## 보고된 것
 *
 * > 「ai 로 변경한 내용(추가,변경) 저장도 안돼. 저장되게 해라」
 *
 * ## 왜 그렇게 보였나 — 둘이 겹쳤다
 *
 * 1. 016 이 재녹화 띠(`RerecordBar`)를 Step 목록 **머리 한 줄**의 오른쪽(`headerExtra`)에
 *    걸었다. 머리는 36px 에 「TEST STEPS · 작성 · 개수」가 이미 있어, 띠가 받은 폭이 60px
 *    남짓이었다. 문장이 세로로 꺾여 겹치고 **확정·버리기 버튼이 보이지 않았다.**
 * 2. 저장 버튼은 활성으로 보였다 — `save` 셀이 C8(Step 이 있다)만 봤다. 눌러야 서버의
 *    409(「확정으로 끝내거나 버리기로 되돌린 뒤 저장하세요」)를 받았다 (005 U-01 의 형태).
 *
 * 확정이 저장의 전제인데(FR-029) 확정 버튼은 안 보이고 저장은 눌러야 거절되니, 사용자에게
 * 남는 것은 「저장이 안 된다」였다.
 *
 * ## 이 파일이 재는 것
 *
 * 폭은 브라우저의 결과라 jsdom 이 재지 못한다. **구조**를 잰다 — 띠가 머리 **밖**의 자기
 * 줄에 있고, 두 버튼이 실제로 그려지며, 저장이 **눌러 보기 전에** 잠기고 확정을 가리킨다.
 * 서버 쪽 길(확정 → 저장 → 디스크)은 `backend/tests/us_rerecord/test_save_after_commit.py`.
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SessionWorkbench } from "../src/pages/SessionScreen";
import { capabilitiesFor } from "../src/lib/capabilities";
import { DISABLED_REASON } from "../src/lib/wording";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import type { SessionView } from "../src/api/client";

afterEach(cleanup);

/** 교체 중인 일시정지 세션 — 보고된 화면의 상태다. */
function rerecording(over: Partial<SessionView> = {}): SessionView {
  const view = sessionView({ state: "paused", ...over });
  const ids = view.steps.map((s) => s.id);
  return {
    ...view,
    rerecord: {
      range_step_ids: [ids[ids.length - 1]!],
      created_step_ids: [ids[0]!],
      can_commit: true,
    },
  };
}

function renderRerecording() {
  return render(<SessionWorkbench {...sessionProps({ view: rerecording() })} />);
}

describe("재녹화 띠의 자리 (사용자 보고 2026-09-11)", () => {
  it("**띠가 목록 머리 안에 없다** — 자기 줄에 있다", () => {
    renderRerecording();
    const band = screen.getByLabelText("구간 재녹화");
    const head = screen.getByText("TEST STEPS").parentElement!;
    expect(head.contains(band), "띠가 머리 한 줄에 끼워져 있다 — 60px 남짓을 받는다").toBe(false);
  });

  it("띠의 줄은 머리 **바로 다음**이다 — 목록 위에서 늘 보인다", () => {
    renderRerecording();
    const head = screen.getByText("TEST STEPS").parentElement!;
    const row = document.querySelector("[data-step-panel-band]");
    expect(row, "띠의 줄이 없다").not.toBeNull();
    expect(head.nextElementSibling).toBe(row);
    expect(row!.contains(screen.getByLabelText("구간 재녹화"))).toBe(true);
  });

  it("**확정과 버리기가 둘 다 그려진다** — 저장으로 가는 문이다", () => {
    renderRerecording();
    const band = screen.getByLabelText("구간 재녹화");
    expect(within(band).getByRole("button", { name: /확정/ })).toBeTruthy();
    expect(within(band).getByRole("button", { name: /버리기/ })).toBeTruthy();
  });

  it("교체가 없으면 줄도 없다 — 자리를 차지하지 않는다", () => {
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ state: "paused" }) })} />);
    expect(document.querySelector("[data-step-panel-band]")).toBeNull();
  });
});

describe("교체 중에는 저장이 **미리** 잠긴다 (FR-029 · O14)", () => {
  it("표 — 일시정지 국면에서 교체가 있으면 저장이 잠기고 확정을 가리킨다", () => {
    const cell = capabilitiesFor("paused", { hasSteps: true, hasRerecord: true })["save"];
    expect(cell.kind).toBe("disabled");
    if (cell.kind !== "disabled") return;
    expect(cell.reason).toBe(DISABLED_REASON.O14);
    expect(cell.remedy?.action).toBe("ai.rerecordCommit");
    // 이 화면에서 곧바로 해소할 수 있으므로 자리는 남는다 (FR-234).
    expect(cell.visibility).toBe("keep");
  });

  it("표 — 교체가 없으면 저장은 그대로 활성이다 (SC-009 · 기존 흐름 불변)", () => {
    const cell = capabilitiesFor("paused", { hasSteps: true, hasRerecord: false })["save"];
    expect(cell.kind).toBe("enabled");
  });

  it("사유가 **서버의 거절과 같은 사실**을 말한다 — 확정과 버리기 둘 다", () => {
    expect(DISABLED_REASON.O14).toMatch(/확정/);
    expect(DISABLED_REASON.O14).toMatch(/버리기/);
  });

  it("화면 — 저장 자리에 그 사유가 **눌러 보기 전에** 보인다", () => {
    renderRerecording();
    const reason = document.querySelector('[data-disabled-reason="save"]');
    expect(reason, "저장 자리에 사유가 없다 — 눌러야 409 를 받는다").not.toBeNull();
    expect(reason!.textContent).toContain("확정");
  });
});

describe("검토 국면에서도 교체를 끝낼 수 있다 (사용자 보고 2026-09-11)", () => {
  /*
    **막다른 길이 있었다.**

    교체를 연 채 「AI 작성 끝내기」나 「중지」를 누르면 세션은 `review` 로 온다. 거기서
    저장은 미확정 교체를 거절하고(FR-029), 016 초안의 국면표는 확정·버리기를
    `na("N3") 브라우저가 없다` 로 적었다 — 화면에 둘 다 없었다.

    남은 길은 「나가기」뿐이고 그것은 만든 것을 전부 버린다. 실측에서 사용자가 그 상태로
    남긴 세션(27 Step · 저장 안 됨)을 그대로 만났다.

    확정은 **정의만 고치는 편집**이므로 브라우저가 필요 없다. 서버도 `REVIEW` 에서
    받는다 (`require_paused` 가 `is_editable` 을 쓴다).
  */
  it("표 — 검토 국면의 확정은 「해당 없음」이 아니다", () => {
    const cell = capabilitiesFor("review", {
      hasSteps: true,
      hasRerecord: true,
      canCommitRerecord: true,
    })["ai.rerecordCommit"];
    expect(cell.kind, "브라우저가 없다는 이유로 확정이 사라지면 저장이 막다른 길이 된다").toBe(
      "enabled",
    );
  });

  it("표 — 버리기도 같다. 그만두는 것도 정당한 길이다", () => {
    const cell = capabilitiesFor("review", { hasSteps: true, hasRerecord: true })[
      "ai.rerecordDiscard"
    ];
    expect(cell.kind).toBe("enabled");
  });

  it("표 — 저장은 잠기되 **쓸 수 있는** 확정을 가리킨다 (막다른 길이 아니다)", () => {
    const caps = capabilitiesFor("review", {
      hasSteps: true,
      hasRerecord: true,
      canCommitRerecord: true,
    });
    const save = caps["save"];
    expect(save.kind).toBe("disabled");
    if (save.kind !== "disabled") return;
    const remedy = save.remedy?.action;
    expect(remedy).toBe("ai.rerecordCommit");
    // **해소 링크가 가리키는 조작이 실제로 눌린다.** 이것이 빠져 있었다 — 링크는
    // 있는데 그 조작이 `na` 라 눌러도 아무 데도 닿지 않았다.
    expect(caps[remedy!].kind, "해소 링크가 쓸 수 없는 조작을 가리킨다").toBe("enabled");
  });

  it("화면 — 검토 국면에도 띠와 두 버튼이 그려진다", () => {
    const view = { ...rerecording(), state: "review" as const };
    render(<SessionWorkbench {...sessionProps({ view })} />);
    const band = screen.getByLabelText("구간 재녹화");
    expect(within(band).getByRole("button", { name: /확정/ })).toBeTruthy();
    expect(within(band).getByRole("button", { name: /버리기/ })).toBeTruthy();
  });
});
