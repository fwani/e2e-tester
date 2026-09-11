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
 * 2. **오류는 스스로 사라지지 않는다.** 「다음 행동」은 읽고 나서 하는 것이므로,
 *    수행하는 동안에도 화면에 있어야 한다.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NoticeStack } from "../src/components/workbench/NoticeStack";
import { SessionWorkbench } from "../src/pages/SessionScreen";
import type { Notice } from "../src/components/workbench/model";
import { sessionProps } from "./helpers/session";
import { sessionView } from "./helpers/workbench";

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

describe("머무는 시간 (2026-09-10)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("경고는 스스로 사라진다", () => {
    render(<NoticeStack notices={[notice("warn", "지나간 사실")]} />);
    expect(screen.getByText("지나간 사실")).toBeTruthy();

    act(() => void vi.advanceTimersByTime(10_000));

    expect(screen.queryByText("지나간 사실")).toBeNull();
  });

  it("오류는 닫기 전까지 남는다", () => {
    render(<NoticeStack notices={[notice("error", "대상 앱에 연결할 수 없습니다")]} />);

    // 옛 상한(12초)의 두 배를 넘겨도 그대로다.
    act(() => void vi.advanceTimersByTime(60_000));

    expect(screen.getByText("대상 앱에 연결할 수 없습니다")).toBeTruthy();
  });

  it("오류도 닫기로는 걷힌다 — 남는다는 것이 못 지운다는 뜻은 아니다", () => {
    render(<NoticeStack notices={[notice("error", "대상 앱에 연결할 수 없습니다")]} />);

    fireEvent.click(screen.getByLabelText("알림 닫기"));

    expect(screen.queryByText("대상 앱에 연결할 수 없습니다")).toBeNull();
  });
});
