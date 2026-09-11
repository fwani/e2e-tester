/**
 * 토스트가 **스스로 비켜 주는 방법** (2026-09-11 사용자 결정).
 *
 * 「toast 가 계속 떠있음. 토스트는 맥의 알림처럼 좌→우로 드래그로 없애거나, x 가
 * 가능해야함. 또한 토스트이기 때문에 자동으로 5초 뒤에 사라져야 함」.
 *
 * ## 2026-09-10 의 판단을 뒤집는다
 *
 * 그때는 **오류만 닫을 때까지 남겼다** (`NoticeStack` 의 `LINGER_MS`). 근거는 「다음
 * 행동은 읽고 나서 하는 것이므로 수행하는 동안에도 화면에 있어야 한다」였다.
 * 실제 화면에서 그 규칙이 만든 것은 **영영 떠 있는 알림**이었다 — 오류는 대개 상태에서
 * 파생되므로 화면을 옮겨도 다시 그려졌고, 닫기는 손으로 눌러야 했다.
 *
 * 사용자가 지목한 것은 이름이다. 토스트는 **비켜 주는 알림**이고, 비켜 주지 않으면
 * 그것은 배너다. 근거는 결과 화면의 기록에 남는다는 2026-09-09 의 논거가 그대로 산다.
 *
 * ## 퇴장은 셋이다
 *
 * | 길 | 누가 | 어떻게 |
 * |---|---|---|
 * | 시간 | 아무도 | 5초. 마우스를 올린 동안에는 세지 않는다 |
 * | 밀어내기 | 손 | 좌→우 드래그. `SWIPE_PX` 를 넘기면 날아간다 |
 * | 닫기 | 손 | `×` |
 *
 * 오른쪽으로만 미는 이유는 자리 때문이다 — 층이 뷰포트 오른쪽에 붙어 있으므로
 * (`ui/Notice` 의 `TOAST_LAYER_CLASSES`) 나가는 쪽은 오른쪽이다. 왼쪽으로 끌면
 * 화면 안쪽으로 들어오고, 그 손짓에는 끝이 없다.
 *
 * ## 왜 `onDismiss` 를 ref 에 담는가
 *
 * 부르는 쪽은 거의 언제나 `onDismiss={() => setError(null)}` 을 쓴다 — **매 렌더 새
 * 함수**다. 그것을 의존성에 넣으면 타이머가 매 렌더 다시 서므로 **영영 울리지
 * 않는다.** 고치려는 결함이 그대로 남는 모양이 된다. 그래서 최신 함수는 ref 로 들고,
 * 타이머는 「닫을 길이 있는가 · 멈춰 있는가」만 보고 선다.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";

/** 머무는 시간. 뜻에 따라 다르지 않다 — 토스트는 전부 비켜 준다 (2026-09-11). */
export const TOAST_LINGER_MS = 5000;

/** 이만큼 밀면 놓는 순간 날아간다. 손가락·트랙패드 양쪽에서 우연히 넘지 않을 거리. */
const SWIPE_PX = 72;

/** 이만큼 밀면 완전히 투명해진다. 미는 동안 사라져 가는 것이 보여야 한다. */
const FADE_PX = 240;

/** 날아 나가는 시간. 이 뒤에 `onDismiss` 를 부른다. */
const FLY_MS = 180;

export interface ToastDismiss {
  /** 토스트 요소에 그대로 펼친다. 포인터·마우스 손잡이가 들어 있다. */
  readonly handlers: {
    onPointerDown: (e: ReactPointerEvent<HTMLElement>) => void;
    onPointerMove: (e: ReactPointerEvent<HTMLElement>) => void;
    onPointerUp: (e: ReactPointerEvent<HTMLElement>) => void;
    onPointerCancel: (e: ReactPointerEvent<HTMLElement>) => void;
    onMouseEnter: () => void;
    onMouseLeave: () => void;
  };
  /** 미는 만큼 따라오는 모양. `transform`·`opacity` 만 건드린다 (되돌릴 수 있다). */
  readonly style: CSSProperties;
  /** 사용자가 읽고 있거나 끌고 있다 — 이 동안에는 시간을 세지 않는다. */
  readonly held: boolean;
}

/**
 * 좌→우 밀어내기.
 *
 * `onDismiss` 가 없으면 아무 일도 하지 않는다 — 닫을 길이 없는 토스트(진행 중 상태)를
 * 손으로 치울 수 있게 하면, 상태는 그대로인데 알림만 사라진다.
 */
export function useSwipeDismiss(onDismiss?: () => void): ToastDismiss {
  const [dx, setDx] = useState(0);
  const [leaving, setLeaving] = useState(false);
  const [hover, setHover] = useState(false);
  /** 끌고 있는가. ref 가 아니라 상태인 이유는 **첫 움직임에 전환을 꺼야** 하기 때문이다
   *  — ref 만 바꾸면 다시 그리지 않아 손가락보다 180ms 늦게 따라온다. */
  const [dragging, setDragging] = useState(false);
  /** 끌기 시작한 x. `null` 이면 끌고 있지 않다. */
  const from = useRef<number | null>(null);
  const flight = useRef<ReturnType<typeof setTimeout> | null>(null);

  const can = onDismiss !== undefined;
  // 최신 함수를 의존성에 넣지 않고 읽는다 (위 주석).
  const cb = useRef(onDismiss);
  cb.current = onDismiss;

  useEffect(
    () => () => {
      if (flight.current !== null) clearTimeout(flight.current);
    },
    [],
  );

  const down = useCallback((e: ReactPointerEvent<HTMLElement>) => {
    if (!can || leaving) return;
    // 왼쪽 단추(또는 손가락)만. 그리고 **버튼 위에서 시작한 손짓은 버튼의 것이다** —
    // `×` 를 누르려다 1px 움직이면 끌기로 새는 것을 막는다.
    if (e.button !== 0) return;
    if ((e.target as HTMLElement).closest("button") !== null) return;
    from.current = e.clientX;
    setDragging(true);
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }, [can, leaving]);

  const move = useCallback((e: ReactPointerEvent<HTMLElement>) => {
    if (from.current === null) return;
    // 오른쪽으로만 따라간다 (위 주석).
    setDx(Math.max(0, e.clientX - from.current));
  }, []);

  const up = useCallback((e: ReactPointerEvent<HTMLElement>) => {
    if (from.current === null) return;
    const moved = Math.max(0, e.clientX - from.current);
    from.current = null;
    setDragging(false);
    e.currentTarget.releasePointerCapture?.(e.pointerId);
    if (moved < SWIPE_PX) {
      setDx(0);
      return;
    }
    setLeaving(true);
    flight.current = setTimeout(() => {
      flight.current = null;
      cb.current?.();
    }, FLY_MS);
  }, []);

  const cancel = useCallback(() => {
    from.current = null;
    setDragging(false);
    setDx(0);
  }, []);

  const style: CSSProperties = {
    transform: leaving ? "translateX(110%)" : dx === 0 ? undefined : `translateX(${dx}px)`,
    opacity: leaving ? 0 : dx === 0 ? undefined : Math.max(0, 1 - dx / FADE_PX),
    // 끄는 동안에는 손을 그대로 따라오고, 놓는 순간에만 붙는다.
    transition: dragging ? "none" : `transform ${FLY_MS}ms ease-out, opacity ${FLY_MS}ms ease-out`,
    // 세로 스크롤은 살리고 가로만 가져간다 — 층이 스크롤되는 자리이기 때문이다.
    touchAction: can ? "pan-y" : undefined,
    cursor: can ? (dragging ? "grabbing" : "grab") : undefined,
  };

  return {
    handlers: {
      onPointerDown: down,
      onPointerMove: move,
      onPointerUp: up,
      onPointerCancel: cancel,
      onMouseEnter: () => setHover(true),
      onMouseLeave: () => setHover(false),
    },
    style,
    held: hover || dragging || leaving,
  };
}

/**
 * 밀어내기 + **스스로 사라지기**.
 *
 * `lingerMs` 가 `null` 이면 시간으로는 사라지지 않는다 (손으로만). 지금 그렇게 부르는
 * 곳은 없지만, 「비켜 주지 않는 알림」이 필요해지면 그것은 여기서 한 번 정해진다.
 */
export function useToastDismiss(onDismiss?: () => void, lingerMs: number | null = TOAST_LINGER_MS): ToastDismiss {
  const swipe = useSwipeDismiss(onDismiss);
  const cb = useRef(onDismiss);
  cb.current = onDismiss;

  const armed = onDismiss !== undefined && lingerMs !== null;
  const { held } = swipe;

  useEffect(() => {
    if (!armed || held) return;
    const t = setTimeout(() => cb.current?.(), lingerMs as number);
    return () => clearTimeout(t);
  }, [armed, held, lingerMs]);

  return swipe;
}
