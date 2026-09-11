/**
 * 토스트의 **퇴장 세 가지** (2026-09-11 사용자 결정).
 *
 * 「toast 가 계속 떠있음. 토스트는 맥의 알림처럼 좌→우로 드래그로 없애거나, x 가
 * 가능해야함. 또한 토스트이기 때문에 자동으로 5초 뒤에 사라져야 함」.
 *
 * 재발을 막으려는 결함은 **닫는 길을 화면마다 정하는 것**이다. 11개 화면이 `onDismiss`
 * 만 주고 시간은 아무도 주지 않아 오류 토스트가 영영 떠 있었다. 그래서 여기서 재는
 * 것은 개별 화면이 아니라 통로(`components/Toast`) 하나다 — 그것이 퇴장을 소유한다.
 */
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toast } from "../src/components/Toast";
import { TOAST_LINGER_MS } from "../src/ui/useToastDismiss";

afterEach(() => {
  cleanup();
  document.querySelectorAll("[data-toast-layer]").forEach((el) => el.remove());
});

const at = (mark: string) => document.querySelector<HTMLElement>(`[${mark}]`);

/**
 * 포인터 사건을 손으로 만든다.
 *
 * jsdom 에는 `PointerEvent` 가 없다. `fireEvent.pointerDown(el, {clientX: 42})` 는
 * 조용히 `Event` 로 떨어지고 **좌표와 단추가 통째로 사라진다** — 핸들러는
 * `e.clientX === undefined` 를 받는다. `MouseEvent` 에 포인터 이름을 붙이면 좌표가
 * 살아 오고, 브라우저에서 실제로 오는 것과 같은 모양이 된다.
 */
function pointer(el: HTMLElement, type: string, clientX: number) {
  fireEvent(el, new MouseEvent(type, { bubbles: true, cancelable: true, button: 0, clientX }));
}

function swipe(el: HTMLElement, to: number) {
  pointer(el, "pointerdown", 0);
  pointer(el, "pointermove", to);
  pointer(el, "pointerup", to);
}

describe("시간 — 5초 뒤 스스로 사라진다", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("오류도 예외가 아니다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast tone="error" mark="data-err" onDismiss={onDismiss}>
        실패했습니다
      </Toast>,
    );

    act(() => void vi.advanceTimersByTime(TOAST_LINGER_MS - 500));
    expect(onDismiss, "5초도 되기 전에 걷어 갔다").not.toHaveBeenCalled();

    act(() => void vi.advanceTimersByTime(600));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("매 렌더 새 함수를 받아도 타이머는 한 번만 선다", () => {
    // 부르는 쪽은 거의 언제나 `onDismiss={() => setError(null)}` 이다. 이것을 의존성에
    // 넣으면 타이머가 매 렌더 다시 서서 **영영 울리지 않는다** — 고치려던 결함 그대로다.
    const spy = vi.fn();
    const { rerender } = render(
      <Toast mark="data-x" onDismiss={() => spy()}>
        무엇이든
      </Toast>,
    );
    for (let i = 0; i < 5; i++) {
      rerender(
        <Toast mark="data-x" onDismiss={() => spy()}>
          무엇이든
        </Toast>,
      );
    }

    act(() => void vi.advanceTimersByTime(TOAST_LINGER_MS + 100));
    expect(spy, "다시 그릴 때마다 타이머가 새로 서 울리지 않았다").toHaveBeenCalledTimes(1);
  });

  it("읽는 동안에는 세지 않는다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast mark="data-hold" onDismiss={onDismiss}>
        읽는 중
      </Toast>,
    );

    fireEvent.mouseEnter(at("data-hold")!);
    act(() => void vi.advanceTimersByTime(60_000));
    expect(onDismiss).not.toHaveBeenCalled();

    fireEvent.mouseLeave(at("data-hold")!);
    act(() => void vi.advanceTimersByTime(TOAST_LINGER_MS + 100));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("닫을 길이 없는 토스트는 시간으로도 사라지지 않는다", () => {
    // 「지금 돌고 있다」는 상태이지 지나간 사실이 아니다 (`TestList` 의 진행 중 세션).
    render(<Toast mark="data-live">돌고 있습니다</Toast>);
    act(() => void vi.advanceTimersByTime(60_000));
    expect(at("data-live")).not.toBeNull();
  });
});

describe("손 — 좌→우 밀어내기", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("충분히 밀면 사라진다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast mark="data-sw" onDismiss={onDismiss}>
        밀어 보낸다
      </Toast>,
    );

    swipe(at("data-sw")!, 140);
    // 날아가는 동안은 아직 살아 있다 — 사라지는 것이 보여야 한다.
    expect(onDismiss).not.toHaveBeenCalled();
    act(() => void vi.advanceTimersByTime(300));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("조금 밀면 제자리로 돌아온다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast mark="data-sw2" onDismiss={onDismiss}>
        살짝 스쳤다
      </Toast>,
    );

    swipe(at("data-sw2")!, 12);
    act(() => void vi.advanceTimersByTime(300));
    expect(onDismiss).not.toHaveBeenCalled();
    expect(at("data-sw2")!.style.transform, "제자리로 돌아오지 않았다").toBe("");
  });

  it("왼쪽으로는 끌리지 않는다 — 나가는 쪽은 오른쪽이다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast mark="data-sw3" onDismiss={onDismiss}>
        반대로 끈다
      </Toast>,
    );

    swipe(at("data-sw3")!, -200);
    act(() => void vi.advanceTimersByTime(300));
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("닫을 길이 없으면 밀리지도 않는다", () => {
    render(<Toast mark="data-sw4">돌고 있습니다</Toast>);
    swipe(at("data-sw4")!, 200);
    act(() => void vi.advanceTimersByTime(300));
    expect(at("data-sw4")).not.toBeNull();
    expect(at("data-sw4")!.style.transform).toBe("");
  });

  it("`×` 를 누르려던 손짓이 끌기로 새지 않는다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast mark="data-sw5" onDismiss={onDismiss}>
        닫기를 누른다
      </Toast>,
    );

    const x = screen.getByRole("button", { name: "알림 닫기" });
    pointer(x, "pointerdown", 0);
    pointer(at("data-sw5")!, "pointermove", 200);
    expect(at("data-sw5")!.style.transform, "단추 위에서 시작한 손짓이 토스트를 끌었다").toBe("");
  });
});

describe("손 — `×`", () => {
  it("눌러서 닫는다", () => {
    const onDismiss = vi.fn();
    render(
      <Toast tone="error" mark="data-x2" onDismiss={onDismiss}>
        실패했습니다
      </Toast>,
    );

    const x = screen.getByRole("button", { name: "알림 닫기" });
    expect(x.textContent, "닫기가 × 가 아니다").toBe("×");
    x.click();
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
