/**
 * 알림 — 의미 클래스 `.notice` 계열이 해체되어 온 곳. 015 T021.
 *
 * 출처: 015 (손으로 만든 부품) · 017 T066 — 클래스 잇기를 `ui/cn` 으로 · T088 — 루트에 `data-slot`
 *
 * 세 가지가 한 뿌리에서 갈린다.
 *
 * | 부품 | 정본 | 자리 |
 * |---|---|---|
 * | `Notice` | `.notice` | 문서 흐름 안. 한 줄 띠(32px) |
 * | ~~`Toast`~~ · ~~`ToastLayer`~~ | — | **`ui/Toast` 로 옮겼다** (2026-09-16 · 017 Phase 10) |
 *
 * ## 정본이 기록한 사고 둘을 되풀이하지 않는다
 *
 * **(1) 모든 토스트가 흰색이었다.** `.notice.float` 의 `background:var(--panel)` 이
 * 특이도 (0,2,0) 으로 `.tint-*` (0,1,0) 를 이겼고, 경고와 오류가 형태로 구별되지
 * 않았다. 정본은 같은 (0,2,0) 규칙을 뒤에 놓아 고쳤다.
 *
 * Tailwind 에서는 그 수를 쓸 수 없다 — 유틸리티는 특이도가 같고 **CSS 파일 안의 순서**가
 * 결정하는데, 그 순서는 우리가 정하지 않는다. 그래서 **배경을 조건에 따라 하나만
 * 내보낸다.** `TONE` 표에서 완성된 문자열을 꺼내므로 다툴 규칙이 애초에 없다.
 *
 * **(2) 두 줄짜리 알림이 잘렸다.** `.notice` 의 `flex:0 0 32px` 가 기준 크기로 높이를
 * 못 박아 `height:auto` 로는 이기지 못했다. 토스트는 `flex:0 0 auto` + `min-height` 로
 * 푼다 — 아래 `Toast` 가 그 값을 그대로 갖는다.
 *
 * ## 상태 스타일
 *
 * 이 군에는 `:hover`·`:focus`·`:disabled` 규칙이 없다
 * ([state-styles.md](../../../specs/015-tailwind-css-migration/contracts/state-styles.md)
 * 목록에 해당 줄이 없다). 옮길 것이 없다는 것을 확인했다.
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "./cn";

/** 정본 `.tint-*` 에 대응한다. `default` 는 바탕 없음(흐름 안 알림의 기본). */
export type NoticeTone = "default" | "pass" | "fail" | "warn" | "run" | "ai";

/**
 * 뜻의 바탕. **배경과 테두리를 함께** 정한다 — 하나만 바꾸면 대비가 무너진다.
 *
 * 정본 `.tint-*` 를 그대로 옮겼다. `--warn-line`·`--fail-line` 은 경고·오류 전용
 * 테두리색 토큰이고, 나머지는 본색을 테두리에 쓴다.
 */
const TONE: Record<NoticeTone, string> = {
  default: "bg-panel border-hair",
  pass: "bg-pass-t border-pass",
  fail: "bg-fail-t border-fail-line",
  warn: "bg-warn-t border-warn-line",
  run: "bg-run-t border-run",
  ai: "bg-ai-t border-ai",
};

/**
 * 뜻 → 바탕을 **알림 부품도 같은 표에서 가져간다** (017 Phase 10 · T099).
 *
 * 흐름 안 띠(`Notice`)와 떠 있는 알림(`ui/Toast`)은 같은 뜻을 같은 바탕으로 말한다. 표를 두 벌 두면
 * 한쪽만 고쳐진다 — 015 가 부품을 한 곳으로 모은 이유와 같다.
 */
export const NOTICE_TINT = TONE;

export interface NoticeProps extends Omit<ComponentPropsWithRef<"div">, "className"> {
  readonly tone?: NoticeTone;
  /** **배치만.** 모양은 `tone` 으로 정한다. */
  readonly layout?: string;
  readonly children?: ReactNode;
}

/**
 * 흐름 안의 한 줄 띠. 정본 `.notice`.
 *
 * `flex-none h-notice` 가 정본의 `flex:0 0 32px` 다 (`--h-notice` = 32px).
 * **높이를 못 박는 것이 이 부품의 성질이다** — 흐름 안에 있으므로 커지면 아래가 밀린다.
 */
export function Notice({ tone = "default", layout, children, ...rest }: NoticeProps) {
  const cls = cn(
    "grow-0 shrink-0 basis-notice h-notice flex items-center gap-s2 px-s4",
    "font-sans text-[12px] leading-none font-normal border-b border-hair",
    tone === "default" ? "" : TONE[tone],
    layout,
  );
  return (
    <div className={cls} data-slot="notice" data-tone={tone} {...rest}>
      {children}
    </div>
  );
}

/*
  **떠 있는 알림과 그 층은 이 파일에 없다** (2026-09-16 · 017 Phase 10).

  `Toast`(`.notice.float.toast`)와 `ToastLayer`·`TOAST_LAYER_CLASSES`(`.toast-layer`)가 여기 있었다.
  지금은 `ui/Toast` 가 부품 하나로 갖는다 — 모양·자리·퇴장(5초·밀어내기·`×`)·상한이 한 곳이다.
  이 파일에는 **흐름 안 한 줄 띠**(`Notice`)만 남는다. 뜻별 바탕 표(`NOTICE_TINT`)는 둘이 함께 쓴다.

  옛 층이 들고 있던 「문서에 있는 띠가 자리를 정한다」 규칙(B-01)은 자리가 화면 아래로 내려가며
  필요 없어졌다. 그 경위는 contracts/layout-contract-v3.md L2 에 기록으로 남아 있다.
*/

