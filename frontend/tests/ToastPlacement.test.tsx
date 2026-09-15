/**
 * 토스트의 **자리와 머무는 시간** (2026-09-10 사용자 결정).
 *
 * 「토스트 알림의 위치를 오른쪽 위로 정의한다 (mac 의 알림과 같은 개념). warning 은 일정
 * 시간 뜨고 사라지면 될 것 같고, 에러의 경우 warning 보다 길게라던지 닫기 전까지라던지
 * 정리가 필요하다」.
 *
 * 두 가지를 고정한다.
 *
 * 1. 알림 층은 **한 자리**다 (`.toast-layer`). 국면마다 다른 데서 뜨면 사용자는 그것을
 *    찾아야 한다 — 007 이 자리를 모은 것과 같은 이유이며, 여기서 그 자리를 화면 밖
 *    (뷰포트 오른쪽 위)으로 옮긴다.
 * 2. 머무는 시간.
 *
 * ## 2026-09-11 — (2)가 뒤집혔다 (사용자 결정)
 *
 * 그때의 조항은 「**오류는 스스로 사라지지 않는다** — 다음 행동은 읽고 나서 하는
 * 것이므로 수행하는 동안에도 화면에 있어야 한다」였다.
 *
 * 「toast 가 계속 떠있음. … 토스트이기 때문에 자동으로 5초 뒤에 사라져야 함」.
 *
 * 그 조항이 화면에서 만든 것은 영영 떠 있는 알림이었다. 이제 **뜻에 관계없이 5초**이며,
 * 여기서 그것을 잰다. 자세한 근거는 `NoticeStack` 의 `LINGER_MS`.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NoticeStack } from "../src/components/workbench/NoticeStack";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import type { Notice } from "../src/components/workbench/model";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";
import { TOAST_LAYER_CLASSES } from "../src/ui/Notice";
import { TOAST_LINGER_MS } from "../src/ui/useToastDismiss";

afterEach(cleanup);

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

describe("알림 층의 자리 (2026-09-10)", () => {
  it("작업대의 알림은 토스트 층 안에 있다", () => {
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ state: "replaying" }) })} />);
    const layer = document.querySelector("[data-workbench-notice-layer]");
    expect(layer).not.toBeNull();
    // 015 — `.toast-layer` 가 유틸리티로 해체됐다. **묻는 것은 그대로다**: 알림 층이
    // 뷰포트 오른쪽 위 한 자리인가. 국면마다 다른 데서 뜨면 사용자는 그것을 찾아야 한다.
    expect(layer!.className, "알림 층이 화면에 고정되지 않았다").toContain("fixed");
    expect(layer!.className, "알림 층이 오른쪽에 붙지 않았다").toContain("right-s4");
  });
});

/**
 * 017 B-01 — **자리의 높이**를 못 박는다. 이 파일은 015 까지 「오른쪽 위에 고정인가」만 봤고,
 * 그래서 알림 층이 국면 띠를 덮는 회귀가 들어왔다: 2026-09-11 수정이 국면 띠 몫을 정본 클래스
 * (`.toast-layer`)에만 더했는데 앱은 그 규칙을 싣지 않았고, 결과·녹화 화면이 쓰는 층은
 * `Workbench` 의 **클래스 복사본**이었다.
 *
 * 높이는 값 하나로 정할 수 없다 — 국면 띠가 있는 화면·머리띠만 있는 화면·띠가 없는 화면이 섞여
 * 있다. 그래서 층이 **문서에 있는 띠**를 읽는다 (017 layout-contract-v3 L2). 실제 픽셀은 jsdom 이
 * 계산하지 않으므로 화면 순회(chromium)가 재고, 여기서는 그 규칙의 **형태**를 본다.
 */
describe("알림 층의 높이는 문서에 있는 띠가 정한다 (017 B-01)", () => {
  const classes = TOAST_LAYER_CLASSES.split(/\s+/);
  const HEADER_ONLY = ":root:has([data-shell=header]):not(:has([data-shell=phase]))";
  const PHASE = ":root:has([data-shell=phase])";

  it("띠 조건 셋 — 없음 · 머리띠만 · 국면 띠까지 — 이 각자의 자리를 갖는다", () => {
    expect(classes).toContain("top-s4");
    expect(classes).toContain(`[${HEADER_ONLY}_&]:top-[calc(var(--h-header)+8px)]`);
    expect(classes).toContain(`[${PHASE}_&]:top-[calc(var(--h-header)+var(--h-phase)+8px)]`);
    expect(classes).toContain(`[${HEADER_ONLY}_&]:max-h-[calc(100vh-var(--h-header)-24px)]`);
    expect(classes).toContain(`[${PHASE}_&]:max-h-[calc(100vh-var(--h-header)-var(--h-phase)-24px)]`);
  });

  it("조건이 서로 배제된다 — 승부를 산출 CSS 순서에 맡기지 않는다", () => {
    // 국면 띠가 있는 문서에는 머리띠도 있다. 머리띠 조건이 국면 띠를 배제하지 않으면 두 규칙이
    // 동시에 성립하고, 이기는 쪽은 Tailwind 가 정한 순서다 — 015 의 흰 버튼과 같은 형태다.
    const headerRules = classes.filter((c) => c.includes("data-shell=header"));
    expect(headerRules.length).toBeGreaterThan(0);
    expect(headerRules.filter((c) => !c.includes(":not(:has([data-shell=phase]))"))).toEqual([]);
  });

  it("작업대의 알림 층은 같은 정의를 쓴다 — 복사본이 없다", () => {
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ state: "replaying" }) })} />);
    const layer = document.querySelector("[data-workbench-notice-layer]");
    expect(layer!.className, "작업대 알림 층이 정의를 복사해 따로 갖고 있다 — B-01 의 원인이었다").toBe(
      TOAST_LAYER_CLASSES,
    );
  });

  it("띠가 자기 존재를 알린다 — 층이 읽을 표식이 있다", () => {
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ state: "replaying" }) })} />);
    expect(document.querySelectorAll('[data-shell="header"]').length).toBe(1);
    expect(document.querySelectorAll('[data-shell="phase"]').length).toBe(1);
  });

  it("알림 층은 aria-live 다 — 모달이 뒤쪽에 aria-hidden 을 걸어도 알림은 읽힌다", () => {
    // Radix 모달은 열릴 때 body 의 다른 자식에 aria-hidden 을 걸되 `aria-live` 요소는 건너뛴다
    // (017 research R6 ③ 실측). 층이 aria-live 가 아니면 모달이 열린 동안 알림이 낭독되지 않는다.
    render(<SessionWorkbench {...sessionProps({ view: sessionView({ state: "replaying" }) })} />);
    expect(document.querySelector("[data-workbench-notice-layer]")!.getAttribute("aria-live")).toBe("polite");
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

    fireEvent.mouseEnter(document.querySelector("[data-workbench-notices]")!);
    act(() => void vi.advanceTimersByTime(60_000));

    expect(screen.getByText("대상 앱에 연결할 수 없습니다")).toBeTruthy();
  });

  it("5초를 기다리지 않고 손으로도 걷힌다", () => {
    render(<NoticeStack notices={[notice("error", "대상 앱에 연결할 수 없습니다")]} />);

    fireEvent.click(screen.getByLabelText("알림 닫기"));

    expect(screen.queryByText("대상 앱에 연결할 수 없습니다")).toBeNull();
  });
});
