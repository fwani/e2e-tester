/**
 * 세션 이벤트 구독. contracts/websocket.md.
 *
 * **서버 → 클라이언트 단방향.** 클라이언트는 명령을 보내지 않는다.
 *
 * **재연결 시 전체 상태를 다시 받는다.** 서버는 이벤트를 재전송하지 않으므로,
 * 끊긴 사이에 놓친 것을 복구하는 유일한 방법이다.
 *
 * `mirror_*` 이벤트는 유실 가능하다 — 마지막 프레임만 그리면 되고, 유실이 실행에
 * 영향을 주지 않는다 (FR-047b).
 */
import type { Step } from "../types/generated/step";
import type { SessionState } from "./client";

export interface SessionEventBase {
  type: string;
  seq: number;
}

export type SessionEvent =
  | (SessionEventBase & {
      type: "state_changed";
      state: SessionState;
      current_step_index: number;
      active_tab: number;
    })
  | (SessionEventBase & { type: "session_lost"; reason?: string })
  | (SessionEventBase & { type: "edit_warning"; messages: string[] })
  | (SessionEventBase & { type: "step_added"; step: Step; at_index: number })
  | (SessionEventBase & { type: "step_updated"; step: Step })
  | (SessionEventBase & { type: "step_removed"; step_id: string })
  | (SessionEventBase & { type: "steps_reordered"; order: string[] })
  | (SessionEventBase & { type: "step_started"; step_id: string; index: number; tab: number })
  | (SessionEventBase & {
      type: "step_finished";
      step_id: string;
      index: number;
      outcome: string;
      duration_ms: number;
    })
  | (SessionEventBase & {
      type: "step_failed";
      step_id: string;
      index: number;
      error_message: string;
      locator_attempts: unknown[];
      tab_wait_ms: number;
    })
  | (SessionEventBase & {
      type: "run_finished";
      outcome: string;
      total_ms: number;
      passed_count: number;
      total_count: number;
      failed_step_index: number | null;
    })
  | (SessionEventBase & { type: "mirror_frame"; tab: number; data: string; width: number; height: number })
  | (SessionEventBase & { type: "mirror_tab_changed"; tab: number })
  | (SessionEventBase & { type: "mirror_degraded"; mode: string; reason?: string })
  | (SessionEventBase & { type: "mirror_stopped"; reason?: string })
  /** 조용한 실패를 막는 진단 이벤트 (contracts/websocket.md §진단 이벤트). */
  | (SessionEventBase & { type: "run_error"; reason: string })
  | (SessionEventBase & { type: "artifact_note"; message: string })
  | (SessionEventBase & { type: "tab_opened"; tab: number; url: string; title: string })
  | (SessionEventBase & { type: "tab_closed"; tab: number })
  | (SessionEventBase & { type: "tab_limit_reached"; limit: number; message?: string })
  | (SessionEventBase & { type: "unknown_event" });
/**
 * **포괄 변형(`{ type: string; [key: string]: unknown }`)을 두지 않는다.**
 *
 * 그 변형이 있으면 `case "run_error"` 로 좁혀도 포괄 변형이 함께 남아 모든 필드가
 * `unknown` 이 된다. 그러면 이벤트마다 캐스팅을 붙이게 되고, 캐스팅은 계약이 바뀐 것을
 * 컴파일러가 알려 주지 못하게 만든다 — 타입을 둔 이유가 사라진다.
 *
 * 계약에 아직 없는 이벤트(AI 이벤트 등)는 `switch` 의 `default` 에서 전체 상태 재조회로
 * 처리된다. 런타임은 안전하고, 새 이벤트를 쓰려면 여기 변형을 추가해야 한다.
 */

export interface SubscribeOptions {
  onEvent: (event: SessionEvent) => void;
  /** 연결이 (재)수립될 때 호출된다. 전체 상태를 다시 받아야 한다. */
  onResync: () => void;
  onClosed?: () => void;
}

const RECONNECT_DELAY_MS = 700;

/** 세션 이벤트를 구독한다. 반환된 함수를 호출하면 구독을 끊는다. */
export function subscribeSessionEvents(
  sessionId: string,
  options: SubscribeOptions,
): () => void {
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;
  let lastSeq = 0;

  const connect = (): void => {
    if (closed) return;
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(
      `${scheme}://${window.location.host}/api/sessions/${sessionId}/events`,
    );

    socket.onopen = () => {
      // 끊긴 사이의 이벤트는 복구할 수 없다. 전체 상태를 다시 받는다.
      options.onResync();
    };

    socket.onmessage = (message) => {
      let parsed: SessionEvent;
      try {
        parsed = JSON.parse(message.data as string) as SessionEvent;
      } catch {
        return; // 형식이 깨진 프레임은 버린다
      }
      if (typeof parsed.seq === "number") {
        // seq 가 뒤로 가면 서버가 재시작된 것이다 — 전체 상태를 다시 받는다.
        if (parsed.seq < lastSeq) options.onResync();
        lastSeq = parsed.seq;
      }
      options.onEvent(parsed);
    };

    socket.onclose = () => {
      socket = null;
      if (closed) {
        options.onClosed?.();
        return;
      }
      timer = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    socket.onerror = () => socket?.close();
  };

  connect();

  return () => {
    closed = true;
    if (timer !== null) clearTimeout(timer);
    socket?.close();
  };
}
