/**
 * 표·격자·행. 017 T035.
 *
 * 출처: shadcn new-york-v4/table @ shadcn 4.21.0 (2026-09-15) — `Table`·`TableHeader`·`TableBody`·`TableFooter`·
 * `TableRow`·`TableHead`·`TableCell` 의 구조와 `data-slot`, 가로로 넘치는 표를 감싸는 컨테이너를 가져왔다. 클래스는
 * 정본 `.table`·`.thead`·`.grid-head`·`.tfoot` 으로 옮겼다. 원본의 `hover:bg-muted/50`·`data-[state=selected]`·
 * `text-sm`·`[&:has([role=checkbox])]` 는 남지 않는다 — 정본 표에는 hover 강조가 없다.
 *
 * 015 의 손으로 만든 표 부품(`Table`·`TableHead`(thead)·`TableFoot`·`GridHead`·`TableRow`)은 **화면이 하나도 쓰지 않아**
 * 같은 자리에서 교체했다. 화면이 쓰는 `Row`·`Spacer`·`rowClasses`·`Segmented`·`Tabs` 는 그대로다
 * (`Segmented`·`Tabs` 는 017 T058~T062 에서 `ToggleGroup`·`Tabs` 부품으로 옮기며 지운다).
 *
 * ## 표는 두 밀도다
 *
 * | variant | 정본 | 쓰는 곳 |
 * |---|---|---|
 * | `panel` | `.table` — 판 테두리 · 칸 12px 여백 · 40px · 12px 글자 · 줄 사이 실선 | 후보 우선순위 표 |
 * | `grid` | `.grid-head` 표 — 칸 6px/8px 여백 | 초안 목록 · 가져오기 미리보기 |
 *
 * 칸의 형태를 **표가 정한다** (정본 `.table td`). 칸마다 여백을 적으면 같은 표 안에서 칸이 서로 달라진다.
 *
 * ## 머리 칸은 한 모양이다 (B-09)
 *
 * 015 전환에서 초안 표의 머리가 `.grid-head` 가 아닌 옅은 우물 바탕만 받아, 브라우저 기본 `th{text-align:center;
 * font-weight:bold}` 이 드러났다 — 머리 칸이 가운데, 본문 칸이 왼쪽에 서고, 마지막 머리만 모노 대문자였다.
 * `TableHead` 가 정본 `.grid-head th` 를 명시해 기본값에 기대지 않는다. 오른쪽에 서는 열은 `layout` 으로
 * 정렬만 준다 (본문 칸과 같은 쪽).
 *
 * ## 행 결말은 왼쪽 테두리로 말한다 (`rowClasses`)
 *
 * `.trow.pass|fail|run|sel` 이 `border-left-color` 를 바꾼다. 폭은 `--mark`(3px) 로 항상 자리를 차지하므로,
 * **결말이 없어도 행이 흔들리지 않는다.** 색만 바뀐다.
 */
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { cn } from "./cn";

type LayoutProps = { layout?: string; children?: ReactNode };

export type TableVariant = "panel" | "grid";

export const tableVariants = cva("w-full border-collapse", {
  variants: {
    variant: {
      // 정본 `.table{width:100%;border-collapse:collapse;background:var(--panel)}` · `.table td{padding:0 12px;
      // height:40px;font:400 12px/1}` · `.table tr + tr td{border-top:1px solid var(--hair)}` + 판 테두리
      panel:
        "bg-panel border border-hair rounded-base " +
        "[&_td]:px-s3 [&_td]:h-[40px] [&_td]:font-sans [&_td]:text-[12px] [&_td]:leading-none " +
        "[&_tr+tr_td]:border-t [&_tr+tr_td]:border-hair",
      grid: "[&_th]:py-[6px] [&_th]:px-s2 [&_td]:py-[6px] [&_td]:px-s2",
    },
  },
  defaultVariants: { variant: "grid" },
});

/** 표. 가로로 넘치면 **표만** 스크롤한다 — 화면 전체가 옆으로 밀리지 않는다 (shadcn 컨테이너). */
export function Table({
  variant = "grid",
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<"table">, "className"> & LayoutProps & { variant?: TableVariant }) {
  return (
    <div className="relative w-full overflow-x-auto" data-slot="table-container">
      <table className={cn(tableVariants({ variant }), layout)} data-slot="table" data-variant={variant} {...rest}>
        {children}
      </table>
    </div>
  );
}

/** 정본 `.thead` — 옅은 우물 바탕 · 아래 실선. */
export function TableHeader({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"thead">, "className"> & LayoutProps) {
  return (
    <thead className={cn("bg-sunken border-b border-hair-2", layout)} data-slot="table-header" {...rest}>
      {children}
    </thead>
  );
}

export function TableBody({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"tbody">, "className"> & LayoutProps) {
  return (
    <tbody className={cn(layout)} data-slot="table-body" {...rest}>
      {children}
    </tbody>
  );
}

/** 정본 `.tfoot` — 옅은 바닥 · 위 실선. */
export function TableFooter({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"tfoot">, "className"> & LayoutProps) {
  return (
    <tfoot className={cn("bg-sunken-2 border-t border-hair", layout)} data-slot="table-footer" {...rest}>
      {children}
    </tfoot>
  );
}

/** 표 행의 뜻. 정본 `.table tr.in-use td`(지금 쓰이는 줄) · `.table tr.last-resort td`(최후 수단). */
export type TableRowTone = "default" | "in-use" | "last-resort";

const ROW_TONE: Record<TableRowTone, string> = {
  default: "",
  // 옅은 통과 바탕 — 나머지와 구분되되 주장하지 않는다.
  "in-use": "[&>td]:bg-pass-t",
  // 옅은 우물 — 쓸 수는 있으나 마지막이라는 뜻이다 (원칙 IV).
  "last-resort": "[&>td]:bg-sunken-2",
};

export function TableRow({
  tone = "default",
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<"tr">, "className"> & LayoutProps & { tone?: TableRowTone }) {
  return (
    <tr className={cn(ROW_TONE[tone], layout)} data-slot="table-row" data-tone={tone} {...rest}>
      {children}
    </tr>
  );
}

/**
 * 머리 칸 — 정본 `.grid-head th{text-align:left;font:600 11px/1 mono;letter-spacing:.08em;uppercase;color:--ink-3}`.
 * 여백은 표의 `variant` 가 정한다.
 */
export function TableHead({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"th">, "className"> & LayoutProps) {
  return (
    <th
      className={cn(
        "text-left align-middle font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3 whitespace-nowrap",
        layout,
      )}
      data-slot="table-head"
      {...rest}
    >
      {children}
    </th>
  );
}

/** 본문 칸. 여백·높이·글자는 표의 `variant` 가 정한다 (정본 `.table td`). */
export function TableCell({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"td">, "className"> & LayoutProps) {
  return (
    <td className={cn("align-middle", layout)} data-slot="table-cell" {...rest}>
      {children}
    </td>
  );
}

/** 정본 `.trow.{pass,fail,run,sel}`. `none` 은 결말 없음(투명 테두리). */
export type RowMark = "none" | "pass" | "fail" | "run" | "sel";

/**
 * 결말별 왼쪽 테두리와 바탕. `pass` 는 바탕을 바꾸지 않는다 — 통과가 기본이므로 강조하면 목록이 시끄러워진다.
 */
const MARK: Record<RowMark, string> = {
  none: "border-l-transparent",
  pass: "border-l-pass",
  fail: "border-l-fail bg-fail-t",
  run: "border-l-run bg-run-t",
  sel: "border-l-ink bg-sunken-2",
};

/**
 * 격자 행 껍데기의 클래스 — 테스트 목록의 행은 `<div>` 격자다 (열 폭을 `grid-template-columns` 로 정하므로 표
 * 요소를 쓸 수 없다). 그 행이 자기 힘으로 같은 모양을 조립하면 같은 종류의 행이 두 모습을 갖는다 (SC-010).
 *
 * 왼쪽 테두리 **폭**에 주의한다. `border-l-mark` 는 색 이름공간이라 존재하지 않고 `border-l-solid` 도 없다 —
 * 둘 다 가드 G-B 가 잡았다.
 */
export function rowClasses(mark: RowMark = "none"): string {
  // **위·오른쪽 폭을 0 으로 못 박는다.** `border-solid` 는 네 변 전부에 선 종류를 주는데, 폭을 지정하지 않은
  // 변은 초기값 `medium`(3px)을 받는다 — 이것을 빠뜨리면 모든 행이 위·오른쪽에 3px 회색 선을 얻는다 (015 L2).
  return (
    "h-[44px] items-center border-b border-hair border-solid border-t-0 border-r-0 " +
    `border-l-[length:var(--mark)] ${MARK[mark]}`
  );
}

/** 정본 `.row` — 가로로 늘어놓는 줄. 간격은 `--s-2`(8px). */
export function Row({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  return (
    <div className={cn("flex items-center gap-s2", layout)} {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.spacer` — 남는 자리를 먹는다. `Row` 안에서 다음 것을 오른쪽으로 민다. */
export function Spacer({ layout, ...rest }: Omit<ComponentPropsWithRef<"span">, "className"> & { layout?: string }) {
  return <span className={cn("flex-1", layout)} {...rest} />;
}

/**
 * 정본 `.segmented` — 분절 선택 띠 (실행 속도 고르기 등). **017 T060 에서 `ToggleGroup` 으로 옮기며 지운다.**
 *
 * 정본이 `> button` 으로 정하던 것을 그대로 옮겼다: 테두리는 왼쪽만(첫째는 없음), 배경 없음, 글자 `--ink-2`·500,
 * 고른 것은 `--sunken` 바탕에 `--ink`·700, 못 누르는 것은 실선 테두리에 `--ink-3` (S-12).
 */
export function Segmented({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  const cls = cn(
    "inline-flex border border-hair-2 rounded-base overflow-hidden " +
      "[&>button]:border-0 [&>button]:border-l [&>button]:border-hair-2 [&>button]:rounded-none " +
      "[&>button]:bg-transparent [&>button]:shadow-none [&>button]:text-ink-2 [&>button]:font-medium " +
      "[&>button:first-child]:border-l-0 " +
      "[&>button[aria-pressed=true]]:bg-sunken [&>button[aria-pressed=true]]:text-ink [&>button[aria-pressed=true]]:font-bold " +
      "[&>button:disabled]:bg-transparent [&>button:disabled]:border-solid [&>button:disabled]:text-ink-3",
    layout,
  );
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.tabs` — 분절된 탭 띠. **017 T058 에서 `ui/Tabs` 부품으로 옮기며 지운다.**
 *
 * 안쪽 버튼의 형태를 여기서 정한다 (정본 `.tabs > button`). **S-11 을 함께 옮겼다** — 비활성 탭은 실선 테두리에
 * 흐린 글자다. 빠뜨리면 활성과 구별되지 않는다.
 */
export function Tabs({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  const cls = cn(
    "bg-sunken border-b border-hair-2 " +
      "[&>button]:border-0 [&>button]:border-r [&>button]:border-hair-2 [&>button]:rounded-none " +
      "[&>button]:bg-transparent [&>button]:shadow-none [&>button]:text-ink-2 " +
      "[&>button]:font-mono [&>button]:text-[11px] [&>button]:font-semibold [&>button]:leading-none " +
      "[&>button]:tracking-[0.1em] " +
      "[&>button[aria-pressed=true]]:bg-panel [&>button[aria-pressed=true]]:text-ink " +
      // S-11 — 비활성 탭.
      "[&>button:disabled]:border-solid [&>button:disabled]:text-ink-3",
    layout,
  );
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
