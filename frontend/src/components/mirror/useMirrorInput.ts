/**
 * 미러 표시 좌표 → 대상 화면 좌표 (010 T028 · FR-330·FR-331 · research R3 · data-model §2).
 *
 * **상수 1280·800 을 쓰지 않는다.** 서버가 스크린캐스트에 요청하는 상한과 실제 프레임
 * 크기는 **다르다** — 실측에서 1280×800 을 요청해 1067×800 을 받았다 (높이 제약이 먼저
 * 걸린다). 상한을 배율 계산에 쓰면 좌표가 어긋나고, 그 어긋남은 밀집 UI 에서만 드러난다.
 *
 * 그래서 배율은 셋으로 만든다.
 *
 * 1. `<img>` 의 **자연 크기** (`naturalWidth`/`naturalHeight`) — 프레임의 실제 픽셀 크기
 * 2. `<img>` 의 **표시 크기** (`getBoundingClientRect`) — 화면에 그려진 크기
 * 3. 프레임이 실어 온 **대상 화면 크기** (`width`/`height`) 와 `pageScale`·`offsetTop`
 *
 * 1 과 2 는 클라이언트가 직접 읽고, 3 은 서버가 보낸다. 서버가 프레임 픽셀 크기를 보내지
 * 않는 이유가 여기 있다 — 보낸 값과 실제 이미지가 어긋날 여지를 만들지 않는다.
 *
 * **`pageScale`·`offsetTop` 을 변환에 포함한다** (FR-331). 실측 환경에서는 각각 1 과 0
 * 이었지만, 그렇지 않은 환경에서만 좌표가 어긋나고 원인이 드러나지 않는 것을 막는다.
 */

import type { MutableRefObject } from "react";

/** 프레임 한 장이 실어 온 좌표 변환의 근거 (data-model §2). */
export interface FrameGeometry {
  /** 대상 화면 크기. **프레임 이미지의 픽셀 크기가 아니다** */
  width: number;
  height: number;
  /** 페이지 배율 (`pageScaleFactor`). 옛 서버에는 없으므로 기본 1 */
  pageScale?: number;
  /** 화면 상단 오프셋. 옛 서버에는 없으므로 기본 0 */
  offsetTop?: number;
  /** 프레임 일련번호. 조작 사건이 되돌려 보낸다 */
  frameSeq?: number;
}

/** 대상 화면 좌표 하나. */
export interface TargetPoint {
  x: number;
  y: number;
}

/**
 * 이미지의 자연 크기와 표시 크기. 테스트가 `<img>` 없이도 변환을 잴 수 있게 분리한다.
 *
 * jsdom 은 이미지를 실제로 디코드하지 않으므로 `naturalWidth` 가 0 이다. 변환식이
 * `<img>` 에 직접 붙어 있으면 검증이 브라우저를 요구하게 되고, 그러면 SC-512 가
 * 요구하는 밀집 요소 검증을 빠른 계층에서 돌릴 수 없다.
 */
export interface DisplayBox {
  /** 프레임 이미지의 실제 픽셀 크기 */
  naturalWidth: number;
  naturalHeight: number;
  /** 화면에 그려진 크기 */
  clientWidth: number;
  clientHeight: number;
  /** 그려진 영역의 좌상단 (뷰포트 기준) */
  left: number;
  top: number;
}

/**
 * 표시 좌표를 대상 화면 좌표로 되돌린다 (FR-330 · data-model §2 역변환식).
 *
 * 표시 영역 밖이면 `null` — 밀어 넣지 않는다. 밀어 넣으면 사용자가 누르지 않은 요소가
 * 눌리고, 그 클릭이 Step 으로 저장된다 (서버도 같은 이유로 거절한다 · FR-341).
 *
 * **반올림으로 충분하다.** 배율이 비정수(1.4995 × 1.5)인 축소 프레임에서 12px 짜리 밀집
 * 요소 3개를 3/3 정확히 눌렀다 (research R3 측정 3 · SC-512).
 */
export function toTargetPoint(
  point: { clientX: number; clientY: number },
  box: DisplayBox,
  frame: FrameGeometry,
): TargetPoint | null {
  if (box.clientWidth <= 0 || box.clientHeight <= 0) return null;
  if (box.naturalWidth <= 0 || box.naturalHeight <= 0) return null;
  if (frame.width <= 0 || frame.height <= 0) return null;

  // 좌표가 수치가 아니면 보내지 않는다. `NaN` 은 모든 범위 비교를 거짓으로 만들어
  // **아래 화면 밖 검사를 그대로 통과한다** — 그러면 `NaN` 좌표가 채널로 나가고 서버가
  // 거절한다. 여기서 막으면 사용자가 읽을 필요 없는 거절 사유가 하나 줄어든다.
  if (!Number.isFinite(point.clientX) || !Number.isFinite(point.clientY)) return null;

  const dx = point.clientX - box.left;
  const dy = point.clientY - box.top;
  // 표시 영역 밖은 거절한다 (위 주석).
  if (dx < 0 || dy < 0 || dx > box.clientWidth || dy > box.clientHeight) return null;

  // 표시 크기 → 프레임 픽셀 → 대상 화면. 두 단계를 곱해 하나의 배율로 만든다.
  const scaleX = (box.naturalWidth / box.clientWidth) * (frame.width / box.naturalWidth);
  const scaleY = (box.naturalHeight / box.clientHeight) * (frame.height / box.naturalHeight);

  // `pageScale` 이 0 이면 나눗셈이 무한대가 된다. 서버가 이미 막지만(FR-331 구현),
  // 옛 서버·손상된 페이로드에서도 좌표가 무너지지 않아야 한다.
  const pageScale = frame.pageScale !== undefined && frame.pageScale > 0 ? frame.pageScale : 1;
  const offsetTop = frame.offsetTop ?? 0;

  const x = Math.round((dx * scaleX) / pageScale);
  const y = Math.round((dy * scaleY) / pageScale + offsetTop);

  // 반올림이 경계를 한 픽셀 넘길 수 있다. 좌표계 안으로 되돌리는 것은 밀어 넣기가
  // 아니라 반올림 오차의 정정이다 — 사용자가 화면 안을 눌렀다는 사실은 위에서 확인했다.
  return {
    x: Math.min(Math.max(x, 0), frame.width),
    y: Math.min(Math.max(y, 0), frame.height),
  };
}

/** `<img>` 에서 `DisplayBox` 를 읽는다. */
export function boxOf(image: HTMLImageElement): DisplayBox {
  const rect = image.getBoundingClientRect();
  return {
    naturalWidth: image.naturalWidth,
    naturalHeight: image.naturalHeight,
    clientWidth: rect.width,
    clientHeight: rect.height,
    left: rect.left,
    top: rect.top,
  };
}

/** 채널로 보내는 조작 사건 (data-model §1). */
export interface InputEvent {
  kind: string;
  tab: number;
  x?: number;
  y?: number;
  button?: "left" | "middle" | "right";
  deltaX?: number;
  deltaY?: number;
  key?: string;
  code?: string;
  modifiers?: number;
  text?: string;
  compositionRange?: [number, number];
  frameSeq?: number;
  fileIds?: string[];
}

const BUTTON_NAMES: Record<number, "left" | "middle" | "right"> = {
  0: "left",
  1: "middle",
  2: "right",
};

/** CDP 수정자 비트 — Alt(1)·Ctrl(2)·Meta(4)·Shift(8). 서버가 같은 비트만 받는다. */
export function modifiersOf(event: {
  altKey: boolean;
  ctrlKey: boolean;
  metaKey: boolean;
  shiftKey: boolean;
}): number {
  return (
    (event.altKey ? 1 : 0) |
    (event.ctrlKey ? 2 : 0) |
    (event.metaKey ? 4 : 0) |
    (event.shiftKey ? 8 : 0)
  );
}

export function buttonNameOf(button: number): "left" | "middle" | "right" {
  return BUTTON_NAMES[button] ?? "left";
}

/**
 * 이동 사건의 전송량을 억제한다 (FR-336).
 *
 * 마우스 이동은 초당 수십 건 발생한다. 전부 보내면 채널이 이동으로 가득 차고, 그 뒤의
 * 클릭이 밀린다 — 조작 전달과 프레임 수신이 서로를 막지 않아야 한다는 요구가 여기서
 * 깨진다.
 *
 * **버리지 않고 미룬다.** 마지막 위치는 반드시 보낸다 — 마우스 올리기(hover)로 열리는
 * 메뉴는 포인터가 **머무는 위치**로 판정되므로, 마지막 이동을 버리면 메뉴가 열리지 않는다.
 */
export const MOVE_INTERVAL_MS = 40;

export interface MoveThrottle {
  /** 이동 하나를 넣는다. 지금 보낼 것이면 그 사건을, 미룰 것이면 `null` */
  offer(event: InputEvent, now: number): InputEvent | null;
  /** 미뤄 둔 마지막 이동. 없으면 `null` */
  flush(now: number): InputEvent | null;
}

export function createMoveThrottle(intervalMs = MOVE_INTERVAL_MS): MoveThrottle {
  let lastSentAt = -Infinity;
  let pending: InputEvent | null = null;

  return {
    offer(event, now) {
      if (now - lastSentAt >= intervalMs) {
        lastSentAt = now;
        pending = null;
        return event;
      }
      pending = event;
      return null;
    },
    flush(now) {
      if (pending === null) return null;
      const event = pending;
      pending = null;
      lastSentAt = now;
      return event;
    },
  };
}

/**
 * 미러 영역의 포인터 사건을 조작 사건으로 옮긴다 (T035).
 *
 * 컴포넌트가 아니라 순수 함수 모음인 이유는 검증 때문이다 — 좌표 변환의 정확성(SC-512)은
 * React 를 그리지 않고도 재야 한다.
 */
export interface PointerContext {
  imageRef: MutableRefObject<HTMLImageElement | null>;
  frame: FrameGeometry | null;
  tab: number;
}

export function pointerEventOf(
  kind: "pointer.down" | "pointer.up" | "pointer.move",
  native: { clientX: number; clientY: number; button: number } & Parameters<
    typeof modifiersOf
  >[0],
  context: PointerContext,
): InputEvent | null {
  const image = context.imageRef.current;
  if (image === null || context.frame === null) return null;
  const point = toTargetPoint(native, boxOf(image), context.frame);
  if (point === null) return null;

  const event: InputEvent = {
    kind,
    tab: context.tab,
    x: point.x,
    y: point.y,
    modifiers: modifiersOf(native),
  };
  if (context.frame.frameSeq !== undefined) event.frameSeq = context.frame.frameSeq;
  if (kind !== "pointer.move") event.button = buttonNameOf(native.button);
  return event;
}

export function wheelEventOf(
  native: { clientX: number; clientY: number; deltaX: number; deltaY: number } & Parameters<
    typeof modifiersOf
  >[0],
  context: PointerContext,
): InputEvent | null {
  const image = context.imageRef.current;
  if (image === null || context.frame === null) return null;
  const point = toTargetPoint(native, boxOf(image), context.frame);
  if (point === null) return null;
  return {
    kind: "wheel",
    tab: context.tab,
    x: point.x,
    y: point.y,
    deltaX: native.deltaX,
    deltaY: native.deltaY,
    modifiers: modifiersOf(native),
    ...(context.frame.frameSeq !== undefined ? { frameSeq: context.frame.frameSeq } : {}),
  };
}
