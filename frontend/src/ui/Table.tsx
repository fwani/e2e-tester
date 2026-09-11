/**
 * 표·격자·행. 015 T025.
 *
 * ## 상태 스타일
 *
 * S-11 (`.tabs > button:disabled`) 이 여기로 온다. 정본을 `layer(base)` 로 내렸으므로
 * 옮기지 않으면 **비활성 탭이 활성처럼 보인다** (state-styles.md).
 *
 * ## 행 결말은 왼쪽 테두리로 말한다
 *
 * `.trow.pass|fail|run|sel` 이 `border-left-color` 를 바꾼다. 폭은 `--mark`(3px) 로
 * 항상 자리를 차지하므로, **결말이 없어도 행이 흔들리지 않는다.** 색만 바뀐다.
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

/** 정본 `.trow.{pass,fail,run,sel}`. `none` 은 결말 없음(투명 테두리). */
export type RowMark = "none" | "pass" | "fail" | "run" | "sel";

/**
 * 결말별 왼쪽 테두리와 바탕.
 *
 * `pass` 는 바탕을 바꾸지 않는다 — 통과가 기본이므로 강조하면 목록이 시끄러워진다.
 * 정본의 판단을 그대로 옮겼다.
 */
const MARK: Record<RowMark, string> = {
  none: "border-l-transparent",
  pass: "border-l-pass",
  fail: "border-l-fail bg-fail-t",
  run: "border-l-run bg-run-t",
  sel: "border-l-ink bg-sunken-2",
};

/** 정본 `.table` — 표. */
export function Table({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"table">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = [
    "w-full border-collapse bg-panel",
    // 정본 `.table td` · `.table tr + tr td` — 칸의 형태는 표가 정한다.
    "[&_td]:px-s3 [&_td]:h-[40px] [&_td]:font-sans [&_td]:text-[12px] [&_td]:leading-none",
    "[&_tr+tr_td]:border-t [&_tr+tr_td]:border-hair",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <table className={cls} {...rest}>
      {children}
    </table>
  );
}

/** 정본 `.thead` — 표 머리. */
export function TableHead({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"thead">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = ["bg-sunken border-b border-hair-2", layout].filter(Boolean).join(" ");
  return (
    <thead className={cls} {...rest}>
      {children}
    </thead>
  );
}

/** 정본 `.tfoot` — 표 바닥. */
export function TableFoot({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"tfoot">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = ["bg-sunken-2 border-t border-hair", layout].filter(Boolean).join(" ");
  return (
    <tfoot className={cls} {...rest}>
      {children}
    </tfoot>
  );
}

/**
 * 정본 `.grid-head` — 격자 머리 (`<th>` 가 라벨처럼 보인다).
 *
 * `.lbl` 과 같은 형태다 (11px 대문자 모노) — 같은 값이므로 새로 만들지 않았다.
 */
export function GridHead({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"thead">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = [
    "[&_th]:text-left [&_th]:font-mono [&_th]:text-[11px] [&_th]:font-semibold [&_th]:leading-none",
    "[&_th]:tracking-[.08em] [&_th]:uppercase [&_th]:text-ink-3",
    "[&_th]:bg-sunken [&_th]:border-b [&_th]:border-hair-2",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <thead className={cls} {...rest}>
      {children}
    </thead>
  );
}

/**
 * 정본 `.trow` — 표의 한 행. 높이 44px 고정.
 *
 * 왼쪽 테두리 폭이 `--mark`(3px)로 항상 차지하므로 결말이 생겨도 행이 밀리지 않는다.
 */
/**
 * 행 껍데기의 클래스. **`<tr>` 이 아닌 행도 이것을 쓴다.**
 *
 * 테스트 목록의 행은 `<div>` 격자다 (열 폭을 `grid-template-columns` 로 정하므로
 * 표 요소를 쓸 수 없다). 그 행이 자기 힘으로 같은 모양을 조립하면 같은 종류의 행이
 * 두 모습을 갖게 되고, 그것이 SC-010 이 막으려는 것이다. 그래서 여기서 꺼내 쓴다.
 *
 * 왼쪽 테두리 **폭**에 주의한다. `border-l-mark` 는 색 네임스페이스라 존재하지 않고,
 * `border-l-solid` 도 없다 (`border-solid` 다) — 둘 다 가드 G-B 가 잡았다.
 * 화면에서는 「테두리가 없네」로만 보이고 테스트는 통과했을 오류다.
 */
export function rowClasses(mark: RowMark = "none"): string {
  return `h-[44px] items-center border-b border-hair border-solid border-l-[length:var(--mark)] ${MARK[mark]}`;
}

export function TableRow({ mark = "none", layout, children, ...rest }: Omit<ComponentPropsWithRef<"tr">, "className"> & { mark?: RowMark; layout?: string; children?: ReactNode }) {
  const cls = [rowClasses(mark), layout].filter(Boolean).join(" ");
  return (
    <tr className={cls} data-mark={mark} {...rest}>
      {children}
    </tr>
  );
}

/** 정본 `.row` — 가로로 늘어놓는 줄. 간격은 `--s-2`(8px). */
export function Row({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = ["flex items-center gap-s2", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.spacer` — 남는 자리를 먹는다. `Row` 안에서 다음 것을 오른쪽으로 민다. */
export function Spacer({ layout, ...rest }: Omit<ComponentPropsWithRef<"span">, "className"> & { layout?: string }) {
  const cls = ["flex-1", layout].filter(Boolean).join(" ");
  return <span className={cls} {...rest} />;
}

/**
 * 정본 `.segmented` — 분절 선택 띠 (실행 속도 고르기 등).
 *
 * `Tabs` 와 형태가 다르다. 탭은 아래 경계선으로 판을 나누고, 이쪽은 **테두리로 감싼 한
 * 덩어리**다. 안쪽 버튼의 형태를 여기서 정하는 규율은 같다 — 화면이 버튼 모양을 조립하면
 * 같은 종류의 조작이 화면마다 달라진다 (SC-010).
 *
 * 정본이 `> button` 으로 정하던 것을 그대로 옮겼다: 테두리는 왼쪽만(첫째는 없음),
 * 배경 없음, 글자 `--ink-2`·500, 고른 것은 `--sunken` 바탕에 `--ink`·700,
 * 못 누르는 것은 실선 테두리에 `--ink-3`.
 */
export function Segmented({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = [
    "inline-flex border border-hair-2 rounded-base overflow-hidden",
    "[&>button]:border-0 [&>button]:border-l [&>button]:border-hair-2 [&>button]:rounded-none",
    "[&>button]:bg-transparent [&>button]:shadow-none [&>button]:text-ink-2 [&>button]:font-medium",
    "[&>button:first-child]:border-l-0",
    "[&>button[aria-pressed=true]]:bg-sunken [&>button[aria-pressed=true]]:text-ink [&>button[aria-pressed=true]]:font-bold",
    "[&>button:disabled]:bg-transparent [&>button:disabled]:border-solid [&>button:disabled]:text-ink-3",
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
 * 정본 `.tabs` — 분절된 탭 띠.
 *
 * 안쪽 버튼의 형태를 여기서 정한다 (정본 `.tabs > button`). **S-11 을 함께 옮겼다** —
 * 비활성 탭은 실선 테두리에 흐린 글자다. 빠뜨리면 활성과 구별되지 않는다.
 */
export function Tabs({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = [
    "bg-sunken border-b border-hair-2",
    "[&>button]:border-0 [&>button]:border-r [&>button]:border-hair-2 [&>button]:rounded-none",
    "[&>button]:bg-transparent [&>button]:shadow-none [&>button]:text-ink-2",
    "[&>button]:font-mono [&>button]:text-[11px] [&>button]:font-semibold [&>button]:leading-none",
    "[&>button]:tracking-[0.1em]",
    "[&>button[aria-pressed=true]]:bg-panel [&>button[aria-pressed=true]]:text-ink",
    // S-11 — 비활성 탭.
    "[&>button:disabled]:border-solid [&>button:disabled]:text-ink-3",
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
