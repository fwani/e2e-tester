/**
 * Step 목록의 부품. 015 T026.
 *
 * ## 행 높이 52px 는 계약이다
 *
 * v1 「브루탈리스트」에서 125px 였다. 900px 창에서 5행밖에 보이지 않았고, 실무 테스트는
 * 20~50 Step 이므로 **도구가 자기가 다루는 규모를 감당하지 못했다.** v2 가 52px 로
 * 줄이며 13행이 됐다.
 *
 * 그래서 **칸이 늘어도 높이는 바뀌지 않는다.** 삭제 체크 칸이 생기면 격자 열이 하나
 * 늘 뿐이다 (011 UC-011-12 · 009 FR-304 「행 높이는 국면과 무관하게 고정」).
 *
 * ## 결말과 지목은 다른 채널을 쓴다
 *
 * 011 이전에는 결말·일시정지·지목이 `border-left-color` 와 `background` 둘을 다퉜고,
 * 삼항이 셋을 줄 세워 **언제나 하나만 남았다** — 통과한 Step 을 고르면 결말이 사라지고,
 * 일시정지 행은 골라도 선택이 보이지 않았다 (사용자 보고 7).
 *
 * 지금은 채널이 갈린다. 결말·일시정지는 왼쪽 테두리와 바탕, **지목은 안쪽 링**이다.
 * 두 값이 겹치지 않으므로 함께 보인다. 아래 `MARK` 와 `selected` 가 그 구조다.
 *
 * ## 상태 스타일
 *
 * S-13 (`.srow-check input[type=checkbox]:disabled`) 이 `StepCheck` 로 온다.
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

/** 정본 `.srow.{pass,fail,run,paused}`. `none` 은 결말 없음. */
export type StepMark = "none" | "pass" | "fail" | "run" | "paused";

/**
 * 결말별 왼쪽 테두리와 바탕. **지목(`selected`)과 다른 채널이다.**
 *
 * `pass` 는 바탕을 바꾸지 않는다 — 통과가 기본이므로 강조하면 목록이 시끄러워진다.
 */
const MARK: Record<StepMark, string> = {
  none: "border-l-transparent",
  pass: "border-l-pass",
  fail: "border-l-fail bg-fail-t",
  run: "border-l-run bg-run-t",
  paused: "border-l-transparent bg-warn-t",
};

type DivProps = Omit<ComponentPropsWithRef<"div">, "className">;

/** 정본 `.steps` — Step 패널. 폭 460px 고정 (007 FR-218a). */
export function StepPanel({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = ["flex-none basis-steps border-l border-hair-2 bg-panel flex flex-col", layout]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.steps-hd` — Step 패널의 머리 띠 (36px). */
export function StepPanelHead({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = [
    "grow-0 shrink-0 basis-[36px] h-[36px] flex items-center gap-s2 px-s3 bg-sunken border-b border-hair-2",
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

/**
 * 정본 `.steps-ft` — Step 패널의 바닥.
 *
 * **그 국면의 Step 조작이 모이는 유일한 자리다** (007 FR-235). 조작이 여기저기 흩어지면
 * 사용자가 찾지 못한다.
 */
export function StepPanelFoot({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = ["border-t border-hair-2 bg-sunken-2", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.srow` — Step 한 줄.
 *
 * 격자 5칸(번호·본문·시각·결말·조작). 체크 칸이 있으면 6칸이 되지만 **높이는 그대로다.**
 * 정본은 `:has(> [data-cell="check"])` 로 열을 바꿨고, 여기서는 `withCheck` 로 명시한다 —
 * 부모가 아는 사실을 CSS 선택자로 되묻지 않는다.
 */
export function StepRow({
  mark = "none",
  selected = false,
  withCheck = false,
  layout,
  children,
  ...rest
}: DivProps & { mark?: StepMark; selected?: boolean; withCheck?: boolean; layout?: string; children?: ReactNode }) {
  const cls = [
    "grid items-center gap-[10px] h-step pt-[6px] pr-s3 pb-[6px] pl-[9px]",
    "border-b border-hair border-l-[3px] border-solid",
    withCheck ? "grid-cols-[22px_26px_1fr_58px_20px_auto]" : "grid-cols-[26px_1fr_58px_20px_auto]",
    MARK[mark],
    // 지목 — **안쪽 링.** 결말이 쓰는 테두리·바탕을 건드리지 않으므로 함께 보인다.
    // 2px 인 이유는 1px 이 행 경계선(`--hair`)과 구별되지 않기 때문이고,
    // 잉크를 쓰는 이유는 지목이 상태가 아니라 「지금 보고 있는 곳」이어서다.
    selected ? "shadow-[inset_0_0_0_2px_var(--ink)]" : "",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} data-mark={mark} data-selected={selected ? "true" : undefined} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.srow-check` — 삭제 대상 체크 칸.
 *
 * **결말 아이콘과 형태가 갈린다** — 이것만 사각형이다. 입력칸 기본 스타일(높이 32px·
 * 폭 100%)을 받지 않게 크기를 명시한다. S-13(비활성 커서·투명도)을 함께 옮겼다.
 */
export function StepCheck({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = [
    "flex items-center justify-center",
    "[&_input]:w-[14px] [&_input]:h-[14px] [&_input]:min-h-0 [&_input]:m-0 [&_input]:p-0",
    // S-13
    "[&_input:disabled]:cursor-default [&_input:disabled]:opacity-40",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} data-cell="check" {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.srow-ops` — 행 조작 (위로·아래로·이 앞에 추가·지우기).
 *
 * **항상 보인다.** hover 로 드러내면 없는 조작이 된다 (009 계약 §3-2).
 */
export function StepOps({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = ["flex items-center gap-s1", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.srow-ops .op` 의 변종. */
export type OpTone = "default" | "off" | "danger";

const OP_TONE: Record<OpTone, string> = {
  default: "border-hair-2 text-ink-2 bg-panel",
  off: "border-dashed border-hair-2 text-ink-3 bg-transparent",
  danger: "border-fail text-fail bg-panel",
};

/** 정본 `.srow-ops .op` — 20px 사각 조작 단추. */
export function StepOpButton({ tone = "default", layout, children, ...rest }: Omit<ComponentPropsWithRef<"button">, "className"> & { tone?: OpTone; layout?: string; children?: ReactNode }) {
  const cls = [
    "inline-flex items-center justify-center w-[20px] h-[20px] p-0",
    "border rounded-chip font-sans text-[12px] font-medium leading-none shadow-none",
    OP_TONE[tone],
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={cls} data-tone={tone} {...rest}>
      {children}
    </button>
  );
}

/** 정본 `.phase` — 국면 띠 (48px). */
export function PhaseBand({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = [
    "grow-0 shrink-0 basis-phase h-phase flex items-center gap-s3 px-s4 bg-panel border-b border-hair-2",
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
