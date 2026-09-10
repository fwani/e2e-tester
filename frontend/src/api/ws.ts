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
import type { ErrorBody } from "../types/generated/error-response";
import type { RunScope } from "../types/generated/run-result";
import type { RunPacing, SessionState } from "./client";

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
  | (SessionEventBase & { type: "session_lost"; reason?: string; error?: ErrorBody })
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
      /** 요소가 나타나기를 기다린 시간 (004 FR-114). 옛 서버에는 없다. */
      element_wait_ms?: number;
    })
  | (SessionEventBase & {
      type: "step_failed";
      step_id: string;
      index: number;
      error_message: string;
      locator_attempts: unknown[];
      tab_wait_ms: number;
      element_wait_ms?: number;
      error?: ErrorBody;
    })
  /**
   * 실행 속도가 바뀌었다 (004).
   *
   * **간격 값을 함께 싣는다.** 화면이 대응표를 따로 들고 있으면 서버와 갈린다 —
   * 화면이 "1.5초 쉽니다" 라고 말하는 동안 러너가 0.5초를 쉬는 상태가 만들어진다.
   */
  | (SessionEventBase & {
      type: "pacing_changed";
      pacing: RunPacing;
      delay_ms: number;
      auto_pause: boolean;
      /** 취향 파일에 남겼는가. false 면 다음 실행에 유지되지 않는다. */
      preference_saved: boolean;
    })
  /**
   * 실행이 끝났다 (contracts/websocket.md §2).
   *
   * 005 에서 세 필드가 늘었다 — 화면이 **결말 요약을 스스로 조립하지 않고**
   * `runSummary()` 에 그대로 넘길 수 있어야 하기 때문이다. 분모가 `total_count` 면
   * 5개를 건너뛴 부분 실행이 `0 / 7` 로 보인다 (U-02).
   */
  | (SessionEventBase & {
      type: "run_finished";
      outcome: string;
      total_ms: number;
      passed_count: number;
      total_count: number;
      /** 실제로 시도한 Step 수 (전체 − 건너뜀). 요약의 **분모**다. */
      attempted_count?: number;
      scope?: RunScope;
      start_index?: number;
      stopped_step_index?: number | null;
      failed_step_index: number | null;
    })
  /**
   * 프레임 한 장 (010 T007 · contracts/mirror-control.md §4).
   *
   * **`width`·`height` 는 대상 화면 크기다** — 프레임 이미지의 픽셀 크기가 아니다.
   * 이미지 크기는 `<img>` 의 `naturalWidth`/`naturalHeight` 로 읽는다. 요청한 상한과
   * 실제 프레임 크기가 다르기 때문이다 (1280×800 을 요청해 1067×800 을 받았다 —
   * research R3). 서버가 보낸 값과 이미지가 어긋날 여지를 만들지 않는다.
   *
   * 뒤의 셋은 010 이 더한 **좌표 역변환의 근거**다 (FR-331). 옛 서버에는 없으므로
   * 선택 항목이고, 없으면 변환이 기본값(배율 1 · 오프셋 0)으로 붙는다.
   */
  | (SessionEventBase & {
      type: "mirror_frame";
      tab: number;
      data: string;
      width: number;
      height: number;
      /** 페이지 배율 (`pageScaleFactor`). 없으면 1. */
      pageScale?: number;
      /** 화면 상단 오프셋. 없으면 0. */
      offsetTop?: number;
      /**
       * 프레임 일련번호. 조작 사건이 이 값을 되돌려 보낸다 (data-model §1).
       *
       * 봉투의 `seq` 와 **다른 값이다** — 봉투의 것은 서버 재시작 감지용이고 이것은
       * 「이 좌표를 계산한 근거가 어느 프레임인가」다. 계약 문서는 이 필드를 `seq` 라
       * 불렀으나 봉투와 이름이 겹쳐 구현이 `frameSeq` 로 두었다 (contracts §4 정정).
       */
      frameSeq?: number;
    })
  | (SessionEventBase & { type: "mirror_tab_changed"; tab: number })
  | (SessionEventBase & { type: "mirror_degraded"; mode: string; reason?: string })
  | (SessionEventBase & { type: "mirror_stopped"; reason?: string })
  /**
   * 대상 브라우저가 사용자에게 요구하는 것 (010 · contracts/mirror-control.md §4).
   *
   * 대화상자·파일 선택처럼 **페이지 화면이 아닌 것**이다. 미러는 페이지 화면을 그리므로
   * 여기 나타나지 않고, 창이 없으면 운영체제도 대신 보여 주지 않는다.
   *
   * **`message` 는 대상 페이지에서 온 값이다.** 표시할 때 이스케이프해야 한다 —
   * 외부 입력은 경계에서 검증한다는 헌법 보안 요건이 화면에 걸리는 자리다.
   */
  | (SessionEventBase & {
      type: "browser_prompt";
      promptId: string;
      kind:
        | "dialog.alert"
        | "dialog.confirm"
        | "dialog.prompt"
        | "file.choose"
        | "unsupported";
      message: string;
      multiple?: boolean;
      /** 응답이 없으면 대상 페이지가 멈추는가. 대화상자는 참 */
      blocking?: boolean;
    })
  | (SessionEventBase & { type: "browser_prompt_resolved"; promptId: string; reason?: string })
  /** 조작 위치가 바뀌었다 (010 FR-350 · data-model §6). */
  | (SessionEventBase & { type: "control_surface"; surface: "mirror" | "window" })
  /** 조용한 실패를 막는 진단 이벤트 (contracts/websocket.md §진단 이벤트). */
  | (SessionEventBase & { type: "run_error"; reason: string; error?: ErrorBody })
  | (SessionEventBase & { type: "artifact_note"; message: string })
  | (SessionEventBase & { type: "tab_opened"; tab: number; url: string; title: string })
  | (SessionEventBase & { type: "tab_closed"; tab: number })
  | (SessionEventBase & { type: "tab_limit_reached"; limit: number; message?: string })
  /** AI 이벤트 — **작성 세션에서만 나간다** (contracts/websocket.md §AI 이벤트).
   * `replay` 세션에서 관측되면 원칙 II 위반이며, 그것을 테스트로 고정한다 (SC-006). */
  | (SessionEventBase & { type: "ai_progress"; message: string })
  | (SessionEventBase & {
      type: "ai_blocked";
      attempted: string | null;
      /**
       * AI 가 사람에게 물을 한 문장 (2026-09-10 사용자 결정).
       *
       * 없을 수 있다 — 막혔지만 물을 것이 특정되지 않은 경우다. 그때도 사람이 먼저
       * 말할 수 있으므로 답 칸은 열린다 (질문이 답변의 전제는 아니다).
       */
      question?: string | null;
      reason: string;
      choices: string[];
    })
  | (SessionEventBase & { type: "ai_finished"; step_count: number })
  | (SessionEventBase & { type: "ai_error"; reason: string })
  | (SessionEventBase & { type: "unknown_event" });
/**
 * **포괄 변형(`{ type: string; [key: string]: unknown }`)을 두지 않는다.**
 *
 * 그 변형이 있으면 `case "run_error"` 로 좁혀도 포괄 변형이 함께 남아 모든 필드가
 * `unknown` 이 된다. 그러면 이벤트마다 캐스팅을 붙이게 되고, 캐스팅은 계약이 바뀐 것을
 * 컴파일러가 알려 주지 못하게 만든다 — 타입을 둔 이유가 사라진다.
 *
 * 계약에 아직 없는 이벤트는 `switch` 의 `default` 에서 전체 상태 재조회로
 * 처리된다. 런타임은 안전하고, 새 이벤트를 쓰려면 여기 변형을 추가해야 한다.
 */

export interface SubscribeOptions {
  onEvent: (event: SessionEvent) => void;
  /** 연결이 (재)수립될 때 호출된다. 전체 상태를 다시 받아야 한다. */
  onResync: () => void;
  /**
   * 연결 상태가 바뀔 때 호출된다.
   *
   * **화면이 이것을 반드시 그려야 한다.** 끊긴 채로 자동 재시도만 하면 사용자에게는
   * "조작해도 아무 일도 일어나지 않는 제품" 으로 보인다 — 실제로는 서버가 다 기록하고
   * 있다 (UX U-01 에서 실제로 겪었다).
   */
  onConnectionChange?: (connected: boolean) => void;
  onClosed?: () => void;
}

const RECONNECT_DELAY_MS = 700;

export interface SessionSubscription {
  /** 구독을 끊는다. */
  stop: () => void;
  /** 자동 재시도를 기다리지 않고 지금 다시 붙는다. */
  reconnect: () => void;
}

/** 세션 이벤트를 구독한다. */
export function subscribeSessionEvents(
  sessionId: string,
  options: SubscribeOptions,
): SessionSubscription {
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;
  /** 사용자가 「지금 다시 연결」을 눌렀다 — 다음 재시도는 기다리지 않는다. */
  let immediate = false;
  let lastSeq = 0;

  const connect = (): void => {
    if (closed) return;
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(
      `${scheme}://${window.location.host}/api/sessions/${sessionId}/events`,
    );

    socket.onopen = () => {
      options.onConnectionChange?.(true);
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
      // 첫 연결이 실패한 경우도 여기로 온다 — 프록시가 업그레이드를 막으면 그렇다.
      options.onConnectionChange?.(false);
      const delay = immediate ? 0 : RECONNECT_DELAY_MS;
      immediate = false;
      timer = setTimeout(connect, delay);
    };

    socket.onerror = () => socket?.close();
  };

  connect();

  return {
    stop: () => {
      closed = true;
      if (timer !== null) clearTimeout(timer);
      socket?.close();
    },
    reconnect: () => {
      if (closed) return;
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
      if (socket === null) {
        connect();
        return;
      }
      // 붙어 있는 소켓은 **연결 중인 채로 멎어 있는** 것이다 (프록시가 업그레이드를
      // 삼키면 그렇게 된다 — U-01 의 실제 모습). 닫아서 다시 건다. 닫기 처리가
      // 재연결을 맡으므로 여기서 connect() 를 또 부르면 소켓이 둘이 된다.
      immediate = true;
      socket.close();
    },
  };
}
