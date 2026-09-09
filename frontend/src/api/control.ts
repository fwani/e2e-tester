/**
 * 조작 채널 클라이언트 (010 T029 · contracts/mirror-control.md §2 · research R4).
 *
 * **관찰 소켓(`ws.ts`)과 별개의 소켓이다.** 그쪽은 서버 → 클라이언트 단방향이고 이쪽은
 * 조작을 보낸다. 한 소켓에 합치면 조작 폭주가 프레임 전달을 막고 그 역도 성립한다
 * (FR-336). 여기가 끊겨도 관찰은 그대로여야 하고, 그 역도 같다 (FR-348).
 *
 * **성공 응답을 기다리지 않는다** (contracts §5 불변식 5). 보내고 끝이다 — 성공의 증거는
 * 프레임이다. 응답을 기다리면 다음 키가 앞 키의 전달 완료를 기다리게 되고, 그것이
 * FR-327a 가 금지하는 구조다. 서버가 보내는 것은 **거절 사유와 채널 상태뿐**이다.
 *
 * **끊김을 조용히 두지 않는다** (SC-516). 서버가 닫을 때는 사유를 함께 보내고, 이 모듈은
 * 그것을 화면으로 올린다. 사유 없이 끊긴 것으로 보이면 사용자는 클릭했는데 아무 일도
 * 없는 것으로 읽는다.
 */

import type { InputEvent } from "../components/mirror/useMirrorInput";

/** 서버가 보내는 채널 상태 (data-model §3). */
export type ControlChannelState = "closed" | "open" | "suspended";

/** 서버 → 클라이언트 메시지 (contracts §2). */
export type ControlMessage =
  | { type: "control_state"; state: ControlChannelState; reason: string | null }
  | { type: "control_rejected"; reason: string; kind: string | null };

export interface ControlOptions {
  /** 채널 상태가 바뀌었다. 사유가 있으면 화면이 그것을 그려야 한다 (SC-516) */
  onState: (state: ControlChannelState, reason: string | null) => void;
  /** 사건이 거절됐다. **조용히 버리지 않는다** (FR-341 · SC-516) */
  onRejected: (reason: string, kind: string | null) => void;
}

export interface ControlChannel {
  /** 사건 하나를 보낸다. 붙어 있지 않으면 보내지 않고 `false` */
  send: (event: InputEvent) => boolean;
  /** 채널을 닫는다. 사용자가 국면을 떠날 때 */
  close: () => void;
  /** 지금 붙어 있는가 */
  readonly connected: boolean;
}

const RECONNECT_DELAY_MS = 700;

/**
 * 서버가 「다시 붙지 말라」고 닫은 코드들.
 *
 * **재시도하지 않는다.** 국면이 아니거나 이미 다른 곳에서 조작 중인 것은 시간이 지난다고
 * 풀리지 않는다. 재시도하면 소켓이 초당 한 번씩 거절당하고, 그 거절이 화면에 사유로
 * 쏟아진다 — 사용자에게는 잡음이고 서버에는 부하다. 국면이 다시 조작 국면이 되면
 * 화면이 이 함수를 **다시 부른다** (그것이 재시도의 올바른 계기다).
 */
const FINAL_CLOSE_CODES = new Set([4403, 4404, 4409]);

/** 조작 채널에 붙는다 (contracts §2). */
export function connectControlChannel(
  sessionId: string,
  options: ControlOptions,
): ControlChannel {
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;
  let open = false;

  const connect = (): void => {
    if (stopped) return;
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(
      `${scheme}://${window.location.host}/api/sessions/${sessionId}/control`,
    );

    socket.onopen = () => {
      open = true;
    };

    socket.onmessage = (message) => {
      let parsed: ControlMessage;
      try {
        parsed = JSON.parse(String(message.data)) as ControlMessage;
      } catch {
        // 읽을 수 없는 메시지는 버린다. 조작 채널의 사정이 화면을 깨뜨리지 않는다.
        return;
      }
      if (parsed.type === "control_state") {
        // `suspended` 는 붙어 있으나 지금은 받지 않는 상태다 — 보내기를 막는 것은
        // 서버지만, 화면이 그 사실을 알아야 사용자에게 이유를 말할 수 있다 (FR-346).
        open = parsed.state === "open";
        options.onState(parsed.state, parsed.reason);
      } else if (parsed.type === "control_rejected") {
        options.onRejected(parsed.reason, parsed.kind);
      }
    };

    socket.onclose = (event) => {
      open = false;
      socket = null;
      options.onState("closed", null);
      if (stopped || FINAL_CLOSE_CODES.has(event.code)) return;
      timer = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    socket.onerror = () => {
      // `onclose` 가 뒤따르므로 여기서 재시도를 걸지 않는다. 두 곳에서 걸면 타이머가 겹친다.
    };
  };

  connect();

  return {
    send(event) {
      if (!open || socket === null || socket.readyState !== WebSocket.OPEN) return false;
      try {
        socket.send(JSON.stringify(event));
        return true;
      } catch {
        // 보내기 실패가 화면을 깨뜨리지 않는다 (FR-348). `onclose` 가 곧 뒤따른다.
        return false;
      }
    },
    close() {
      stopped = true;
      if (timer !== null) clearTimeout(timer);
      timer = null;
      open = false;
      socket?.close();
      socket = null;
    },
    get connected() {
      return open;
    },
  };
}
