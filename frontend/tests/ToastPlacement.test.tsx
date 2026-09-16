/**
 * 알림 층의 **자리와 퇴장**.
 *
 * ## 무엇을 붙잡는 파일인가 (바뀌지 않는다)
 *
 * 1. 알림은 **한 자리**에서 뜬다 — 국면마다 다른 데서 뜨면 사용자는 그것을 찾아야 한다.
 * 2. 그 자리의 정의는 **한 곳**이다 — 복사본이 있으면 한쪽만 고쳐진다 (017 B-01 의 원인).
 * 3. 층은 낭독된다 — 대화상자가 뒤쪽에 `aria-hidden` 을 걸어도 알림은 읽혀야 한다 (research R6 ③).
 * 4. 퇴장은 셋이다 — 5초 · 읽는 동안 멈춤 · 손으로 닫기 (2026-09-11 사용자 결정).
 *
 * ## 2026-09-16 에 바뀐 것 — 자리가 **위에서 아래로** 내려왔다
 *
 * 017 의 자리는 오른쪽 **위**였고, 층이 머리띠·국면 띠를 덮지 않도록 문서에 있는 띠를 읽어
 * `top` 을 세 값으로 갈랐다(B-01). 그 규칙이 이 파일의 「띠 조건 셋」 검사였다.
 *
 * 그런데 오른쪽 위는 작업 화면에서 **Step 패널의 머리 줄과 첫 행들**이다. 알림이 그 조작을 가렸고
 * (N-02), 순회가 그것을 실제로 잡았다 — `covered button{전부 고르기} by div{먼저 저장해야…}`.
 * 사용자 결정(2026-09-16)으로 층을 **아래**로 내렸고, 어느 쪽 아래인지는 실측이 정했다 — **왼쪽 아래,
 * 바닥에서 88px**. 아래에서는 띠와 겹치지 않으므로 띠를 읽는 조건 셋이 필요 없어졌다 — 그 검사를
 * **「층이 왼쪽 아래에 있고 바닥에서 64px 이상 떠 있다」로 바꾼다.**
 *
 * **이것은 판정 방법이 아니라 판단의 변경이다.** 그래서 근거를 테스트 밖에도 둔다:
 * layout-contract-v3 L2(개정) · research R6(개정) · 순회 `edit-notice` 화면. 실제 픽셀은 jsdom 이
 * 계산하지 않으므로 순회(chromium)가 재고, 여기서는 규칙의 **형태**를 본다.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NoticeStack } from "../src/components/workbench/NoticeStack";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import type { Notice } from "../src/components/workbench/model";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import { TOAST_VIEWPORT_CLASSES, TOAST_LINGER_MS, Toaster } from "../src/ui/Toast";

afterEach(() => {
  cleanup();
  document.querySelectorAll("[data-toast-layer]").forEach((el) => el.remove());
});

function notice(tone: Notice["tone"], message: string): Notice {
  return {
    id: `n-${tone}`,
    tone,
    role: tone === "error" ? "alert" : "status",
    message,
    nextAction: null,
    action: null,
    dismissible: true,
  };
}

/** 앱처럼 층을 뿌리에 두고 작업 화면을 그린다 (`App` 이 하는 일과 같다). */
function renderWorkbench() {
  return render(
    <Toaster>
      <SessionWorkbench {...sessionProps({ view: sessionView({ state: "replaying" }) })} />
    </Toaster>,
  );
}

describe("알림 층의 자리 (2026-09-10 · 2026-09-16 아래로)", () => {
  it("작업대의 알림은 토스트 층 안에 있다", () => {
    renderWorkbench();
    const layer = document.querySelector("[data-toast-layer]");
    expect(layer).not.toBeNull();
    // 묻는 것은 그대로다: 알림 층이 화면에 고정된 한 자리인가.
    expect(layer!.className, "알림 층이 화면에 고정되지 않았다").toContain("fixed");
  });

  /**
   * 자리를 **실측이 정했다** (2026-09-16 · 계약 T-2). 여기서는 그 결론의 **형태**만 지킨다 —
   * 실제 덮임은 chromium 이 잰다 (`edit-notice`).
   *
   * 화면 7 × 폭 4 에서 후보 전부를 한 번에 쟀다 (덮는 조작 수):
   * 오른쪽 아래 **60** · 오른쪽 위 **58**(N-02) · 아래 가운데 **10** · 위 가운데 **7** · **왼쪽 아래 0**.
   *
   * 여기서 **띄운 거리까지** 붙잡는 이유: 왼쪽 아래도 바닥에 붙이면(16~48px) 1440 에서 Step 상세 판의
   * 「저장」을 덮는다. 깨끗한 것은 **64px 이상**이므로, 자리 이름만 지키고 거리를 놓치면 같은 깨짐이
   * 돌아온다. 그래서 숫자를 읽어 **띠**를 지킨다 — 리터럴 88 을 박으면 띠 안에서 옮길 수도 없다.
   */
  it("층은 왼쪽 아래에 있고, 바닥에서 64px 이상 떠 있다", () => {
    const classes = TOAST_VIEWPORT_CLASSES.split(/\s+/);
    expect(classes, "층이 왼쪽 기둥에 서지 않았다").toContain("left-s4");
    expect(classes.filter((c) => /^right-/.test(c)), "층이 오른쪽 기둥에 붙어 있다 — 실측에서 가장 많이 덮은 자리다(60)").toEqual([]);
    expect(classes.filter((c) => /^top-/.test(c)), "층이 위에 붙어 있다 — Step 패널 머리 줄을 덮는다(N-02)").toEqual([]);
    expect(classes.filter((c) => /translate-x/.test(c)), "가운데 정렬이 남아 있다 — 1440·1920 에서 「AI 에게 말하기」를 덮는다").toEqual([]);

    // 「하나인가」를 먼저 못 박는다 — `not.toBeNull()` 은 무른 단언이고(계수기의 WEAK), 자리를
    // 정하는 클래스가 둘이면 어느 쪽이 이기는지 이 검사가 말하지 못한다.
    const bottoms = classes.filter((c) => /^bottom-\[\d+px\]$/.test(c));
    expect(bottoms.length, "바닥에서 띄운 거리를 px 로 읽을 수 없다 — 자리 규칙이 바뀌었다").toBe(1);
    expect(
      Number(/(\d+)/.exec(bottoms[0] ?? "")?.[1]),
      "바닥에 너무 붙었다 — 16~48px 는 1440 에서 Step 상세 판의 「저장」을 덮는다",
    ).toBeGreaterThanOrEqual(64);

    // 아래에 있으므로 머리띠·국면 띠를 피하려고 띠를 읽을 필요가 없다 (017 B-01 의 조건 셋).
    expect(classes.filter((c) => c.includes("data-shell"))).toEqual([]);
  });
});

describe("층의 정의는 한 곳이다 (017 B-01)", () => {
  it("작업대는 층을 따로 그리지 않는다 — 복사본이 없다", () => {
    renderWorkbench();
    expect(
      document.querySelectorAll("[data-workbench-notice-layer]").length,
      "작업대가 알림 층을 따로 그린다 — 정의가 둘이면 한쪽만 고쳐진다 (B-01 의 원인)",
    ).toBe(0);
    expect(document.querySelectorAll("[data-toast-layer]").length, "층이 하나가 아니다").toBe(1);
  });

  it("띠가 자기 존재를 알린다 — 화면 종류를 읽을 표식이 있다", () => {
    renderWorkbench();
    expect(document.querySelectorAll('[data-shell="header"]').length).toBe(1);
    expect(document.querySelectorAll('[data-shell="phase"]').length).toBe(1);
  });

  it("알림 층은 aria-live 다 — 대화상자가 뒤쪽에 aria-hidden 을 걸어도 알림은 읽힌다", () => {
    renderWorkbench();
    expect(document.querySelector("[data-toast-layer]")!.getAttribute("aria-live")).toBe("polite");
  });
});

describe("머무는 시간 (2026-09-10)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("경고는 스스로 사라진다", () => {
    render(<NoticeStack notices={[notice("warn", "지나간 사실")]} />);
    expect(screen.getByText("지나간 사실")).toBeTruthy();

    act(() => void vi.advanceTimersByTime(TOAST_LINGER_MS + 100));

    expect(screen.queryByText("지나간 사실")).toBeNull();
  });

  it("오류도 스스로 사라진다 — 5초다 (2026-09-11)", () => {
    render(<NoticeStack notices={[notice("error", "대상 앱에 연결할 수 없습니다")]} />);

    // 5초 직전까지는 그대로다 — 읽을 시간을 주지 않고 걷어 가면 그것도 고장이다.
    act(() => void vi.advanceTimersByTime(TOAST_LINGER_MS - 500));
    expect(screen.getByText("대상 앱에 연결할 수 없습니다")).toBeTruthy();

    act(() => void vi.advanceTimersByTime(600));
    expect(screen.queryByText("대상 앱에 연결할 수 없습니다")).toBeNull();
  });

  it("읽는 동안에는 세지 않는다 — 마우스를 올려 두면 남는다", () => {
    render(<NoticeStack notices={[notice("error", "대상 앱에 연결할 수 없습니다")]} />);

    // 멈추는 자리가 층에서 **알림 자체**로 옮겨졌다 — 부품이 그 규칙을 갖는다.
    fireEvent.mouseEnter(document.querySelector("[data-slot=toast]")!);
    act(() => void vi.advanceTimersByTime(60_000));

    expect(screen.getByText("대상 앱에 연결할 수 없습니다")).toBeTruthy();
  });

  it("5초를 기다리지 않고 손으로도 걷힌다", () => {
    render(<NoticeStack notices={[notice("error", "대상 앱에 연결할 수 없습니다")]} />);

    fireEvent.click(screen.getByLabelText("알림 닫기"));

    expect(screen.queryByText("대상 앱에 연결할 수 없습니다")).toBeNull();
  });
});
