/**
 * 실시간 연결이 끊겼을 때 **화면이 그 사실을 말하는지** (UX U-01 후속).
 *
 * 사용자가 겪은 것: 실제 브라우저에서 5개를 조작했는데 화면은 끝까지 "아직 기록된
 * Step 이 없습니다" 였고, 서버에는 5개가 다 있었다. 프록시 설정이 원인이었지만 진짜
 * 문제는 **조용히 실패한 것**이다 — 어떤 원인으로 끊기든 사용자는 알아야 한다.
 *
 * 여기서 고정하는 것은 두 가지다. 전송 계층이 끊김을 알리는가, 배너가 "기록은 계속되고
 * 있다" 를 말하는가.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LiveConnectionBanner } from "../src/components/LiveConnectionBanner";
import { subscribeSessionEvents } from "../src/api/ws";

class FakeSocket {
  static instances: FakeSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }

  close() {
    this.closed = true;
    this.onclose?.();
  }
}

describe("세션 이벤트 전송 계층", () => {
  beforeEach(() => {
    FakeSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  /** `noUncheckedIndexedAccess` 아래에서 인덱스를 그대로 쓰지 않는다. */
  const socketAt = (index: number): FakeSocket => {
    const socket = FakeSocket.instances[index];
    if (socket === undefined) throw new Error(`소켓 ${index} 이 만들어지지 않았다`);
    return socket;
  };

  const subscribe = (onConnectionChange: (c: boolean) => void) =>
    subscribeSessionEvents("sess-1", {
      onEvent: () => undefined,
      onResync: () => undefined,
      onConnectionChange,
    });

  it("연결이 끊기면 끊겼다고 알린다 — 조용히 재시도만 하지 않는다", () => {
    const changes: boolean[] = [];
    subscribe((c) => changes.push(c));

    socketAt(0).close();

    expect(changes).toEqual([false]);
  });

  it("첫 연결이 아예 열리지 않은 경우도 알린다 (프록시가 업그레이드를 막는 경우)", () => {
    const changes: boolean[] = [];
    subscribe((c) => changes.push(c));

    // 한 번도 open 되지 않은 채 닫힌다.
    socketAt(0).onclose?.();

    expect(changes).toEqual([false]);
    expect(socketAt(0).onopen).not.toBeNull();
  });

  it("다시 붙으면 붙었다고 알린다", () => {
    const changes: boolean[] = [];
    subscribe((c) => changes.push(c));

    socketAt(0).close();
    vi.advanceTimersByTime(700);
    socketAt(1).onopen?.();

    expect(changes).toEqual([false, true]);
  });

  it("「지금 다시 연결」은 자동 재시도를 기다리지 않는다", () => {
    const sub = subscribe(() => undefined);

    // 소켓이 연결 중인 채로 멎어 있다 — onclose 가 스스로 오지 않는 상태다.
    sub.reconnect();
    vi.advanceTimersByTime(0);

    expect(FakeSocket.instances).toHaveLength(2);
    expect(socketAt(0).closed).toBe(true);
  });

  it("구독을 끊은 뒤에는 다시 붙지 않는다", () => {
    const sub = subscribe(() => undefined);

    sub.stop();
    vi.advanceTimersByTime(5000);

    expect(FakeSocket.instances).toHaveLength(1);
  });
});

describe("끊김 배너", () => {
  afterEach(cleanup);

  it("기록이 계속되고 있다는 사실을 말한다", () => {
    render(<LiveConnectionBanner />);

    // 이 문장이 없으면 사용자는 지금까지 한 조작이 날아간 줄 알고 처음부터 다시 한다.
    expect(screen.getByRole("status").textContent).toMatch(/서버에 계속 기록되고/);
    expect(screen.getByRole("status").textContent).toMatch(/실시간 연결이 끊겼습니다/);
  });

  it("다시 연결할 수단을 준다", () => {
    const onReconnect = vi.fn();
    render(<LiveConnectionBanner onReconnect={onReconnect} />);

    fireEvent.click(screen.getByRole("button", { name: "지금 다시 연결" }));

    expect(onReconnect).toHaveBeenCalledTimes(1);
  });
});
