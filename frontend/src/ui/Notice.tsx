/**
 * 알림 — 의미 클래스 `.notice` 계열이 해체되어 온 곳. 015 T021.
 *
 * 세 가지가 한 뿌리에서 갈린다.
 *
 * | 부품 | 정본 | 자리 |
 * |---|---|---|
 * | `Notice` | `.notice` | 문서 흐름 안. 한 줄 띠(32px) |
 * | `Toast` | `.notice.float.toast` | 흐름 밖에 겹쳐 뜬다. 여러 줄 |
 * | `ToastLayer` | `.toast-layer` | 토스트가 쌓이는 자리 (뷰포트 오른쪽 위) |
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
  const cls = [
    "flex-none h-notice flex items-center gap-s2 px-s4",
    "font-sans text-[12px] leading-none border-b border-hair",
    tone === "default" ? "" : TONE[tone],
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} data-tone={tone} {...rest}>
      {children}
    </div>
  );
}

/**
 * 흐름 밖에 겹쳐 뜨는 알림. 정본 `.notice.float.toast`.
 *
 * 흐름 안에 두면 알림이 뜰 때마다 아래 전부가 내려갔다 (사용자 보고). 겹쳐 뜨면 미러
 * 위에 놓이므로 그림자 없이는 문장이 미러의 일부처럼 읽힌다 — `shadow-e2` 는 Step
 * 상세(`.overlay-pane`)와 **같은 층에 뜨는 것은 같은 높이**라는 규율에서 온다.
 *
 * 높이를 풀고 최소 높이만 지킨다 (위 사고 (2)).
 */
export function Toast({ tone = "default", layout, children, ...rest }: NoticeProps) {
  const cls = [
    "flex-none min-h-notice flex items-start gap-s2 px-s3 py-s2",
    "font-sans text-[12px] leading-none",
    "border rounded-chip shadow-e2",
    TONE[tone],
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} data-tone={tone} {...rest}>
      {children}
    </div>
  );
}

/**
 * 토스트가 쌓이는 자리. 정본 `.toast-layer`.
 *
 * 뷰포트 오른쪽 위 고정 (2026-09-10 사용자 결정 — 「mac 의 알림과 같은 개념」).
 * 이전에는 좌측 아래였고, 그 자리는 화면마다 달랐다 — 미러가 없는 결과·편집 화면에서는
 * 본문 위에 떴다. 화면 밖(뷰포트 고정)으로 옮기면 그 차이가 사라진다.
 *
 * 비어 있을 때 아래를 막지 않도록 **층에서 포인터를 끄고 알림에서만 되살린다.**
 * 그것을 `[&>*]:pointer-events-auto` 로 옮겼다 — 정본 `.toast-layer > *` 와 같다.
 */
export function ToastLayer({ layout, children, ...rest }: Omit<NoticeProps, "tone">) {
  const cls = [
    "fixed right-s4 z-[60] top-[calc(var(--h-header)+8px)]",
    "w-[min(420px,calc(100vw-32px))] max-h-[calc(100vh-var(--h-header)-24px)]",
    "overflow-y-auto flex flex-col gap-s2",
    "pointer-events-none [&>*]:pointer-events-auto",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
