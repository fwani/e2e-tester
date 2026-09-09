/**
 * 「실제 창에서 조작하기」 (사용자 보고 · 2026-09-09).
 *
 * ## 보고된 것
 *
 * > 실제창에서 조작하기 변환이 안됨
 *
 * ## 왜 그랬나
 *
 * 판정이 **기계만** 보고 있었다. macOS·Windows 는 창 서버가 항상 있으므로 서버의
 * `can_open_a_window()` 는 언제나 참이었고, **창 없이 띄운 브라우저에도** 「옮겼다」고
 * 200 을 돌려주며 미러의 조작 통로를 닫았다. 창은 어디에도 뜨지 않으니 사용자에게
 * 조작할 곳이 하나도 남지 않는다.
 *
 * Chromium 의 창 유무는 띄울 때 정해지고 나중에 바뀌지 않는다. 그래서 이미 떠 있는
 * 세션을 창으로 옮기는 길은 없고, 할 수 있는 정직한 일은 **누르기 전에 사유를 말하는
 * 것**이다 (FR-234·FR-351).
 *
 * ## 문구를 화면이 갖지 않는다
 *
 * 그 판정은 서버만 할 수 있으므로 문장도 서버가 준다 (`wording.ts` 의 O13 옆 주석이
 * 남긴 결정). 화면은 받은 문장을 그대로 붙인다 — 이 파일이 그 성질을 고정한다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MirrorView } from "../src/components/MirrorView";
import { narrowByWindowAvailability } from "../src/lib/capabilities";
import type { CapabilityState } from "../src/lib/capabilities";

afterEach(cleanup);

const ENABLED: CapabilityState = { kind: "enabled" };
/** 서버가 주는 문장이다. 화면이 지어내지 않는다. */
const FROM_SERVER = "이 세션의 브라우저는 창 없이 떠 있어 옮겨 갈 창이 없습니다.";

describe("창으로 갈 수 없으면 누르기 전에 잠근다", () => {
  it("서버가 사유를 주면 잠기고, 그 문장을 그대로 쓴다", () => {
    const next = narrowByWindowAvailability(ENABLED, FROM_SERVER);
    expect(next.kind).toBe("disabled");
    expect(next.kind === "disabled" && next.reason).toBe(FROM_SERVER);
  });

  it("갈 수 있으면 표의 판정을 그대로 둔다", () => {
    expect(narrowByWindowAvailability(ENABLED, null)).toBe(ENABLED);
  });

  it("표가 이미 막고 있으면 덮어쓰지 않는다 — 표의 사유가 더 앞선 사정이다", () => {
    const byTable: CapabilityState = {
      kind: "disabled",
      reason: "AI 가 실행 중입니다",
      remedy: { action: "run.pause" },
      visibility: "keep",
    };
    expect(narrowByWindowAvailability(byTable, FROM_SERVER)).toBe(byTable);
  });

  it("「해당 없음」은 그대로 둔다 — 자리 자체가 없는 국면이다", () => {
    const na: CapabilityState = {
      kind: "not_applicable",
      basis: "N3",
      note: "세션이 없습니다",
    };
    expect(narrowByWindowAvailability(na, FROM_SERVER)).toBe(na);
  });

  it("화면은 잠긴 버튼과 서버의 사유를 같은 자리에 그린다 (FR-234)", () => {
    render(
      <MirrorView
        frame="AAAABBBB"
        phase="manipulation"
        control={ENABLED}
        geometry={{ width: 800, height: 600, pageScale: 1, offsetTop: 0 }}
        useWindowCapability={narrowByWindowAvailability(ENABLED, FROM_SERVER)}
      />,
    );
    const button = document.querySelector<HTMLButtonElement>('[data-action="mirror.useWindow"]');
    expect(button).not.toBeNull();
    expect(button?.disabled, "갈 수 없는데 버튼이 눌린다").toBe(true);
    // 감추지 않는다 — 자리는 남고 이유가 붙는다.
    expect(screen.getByText(FROM_SERVER)).toBeTruthy();
  });

  it("갈 수 있으면 버튼이 살아 있다 — 막는 것이 목적이 아니다", () => {
    render(
      <MirrorView
        frame="AAAABBBB"
        phase="manipulation"
        control={ENABLED}
        geometry={{ width: 800, height: 600, pageScale: 1, offsetTop: 0 }}
        useWindowCapability={narrowByWindowAvailability(ENABLED, null)}
      />,
    );
    const button = document.querySelector<HTMLButtonElement>('[data-action="mirror.useWindow"]');
    expect(button?.disabled).toBe(false);
  });
});
