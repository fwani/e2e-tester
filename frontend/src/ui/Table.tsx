/**
 * 표·격자·행. 017 T035.
 *
 * 출처: shadcn new-york-v4/table @ shadcn 4.21.0 (2026-09-15) — `Table`·`TableHeader`·`TableBody`·`TableFooter`·
 * `TableRow`·`TableHead`·`TableCell` 의 구조와 `data-slot`, 가로로 넘치는 표를 감싸는 컨테이너를 가져왔다. 클래스는
 * 정본 `.table`·`.thead`·`.grid-head`·`.tfoot`·`.dim` 으로 옮겼다. 원본의 `hover:bg-muted/50`·`data-[state=selected]`·
 * `text-sm`·`[&:has([role=checkbox])]` 는 남지 않는다 — 정본 표에는 hover 강조가 없다.
 *
 * 015 의 손으로 만든 표 부품(`Table`·`TableHead`(thead)·`TableFoot`·`GridHead`·`TableRow`)은 **화면이 하나도 쓰지 않아**
 * 같은 자리에서 교체했다. 화면이 쓰는 `Row`·`Spacer`·`rowClasses` 는 그대로다. 여기 있던 `Segmented`·`Tabs`(부모가
 * `[&>button]` 로 자식 단추를 칠하던 형태)는 017 T062 에서 `ui/ToggleGroup`·`ui/Tabs` 로 옮기며 지웠다.
 *
 * ## 표는 세 밀도다
 *
 * | variant | 정본 | 쓰는 곳 |
 * |---|---|---|
 * | `panel` | `.table` — 판 테두리 · 칸 12px 여백 · 40px · 12px 글자 · 줄 사이 실선 | 후보 우선순위 표 |
 * | `grid` | `.grid-head` 표 — 칸 6px/8px 여백 | 초안 목록 · 가져오기 미리보기 |
 * | `compact` | `.why` 글자의 작은 표본 — 칸 2px/6px 여백, 폭은 내용만큼 | 가져오기 미리보기의 머리글 행 고르기 |
 *
 * 칸의 형태를 **표가 정한다** (정본 `.table td`). 칸마다 여백을 적으면 같은 표 안에서 칸이 서로 달라진다.
 *
 * ## 칸의 글자 모양을 칸(`TableCell`)에 주지 않는다 — 칸 안의 글자에 준다 (017 N-05)
 *
 * 표가 모든 칸에 주는 규칙은 `[&_td]:…` 로 쓰여 **선택자가 한 단계 깊다**(`.표 td` · 명시도 0,1,1). 칸 자신에게
 * 준 유틸리티(`.font-mono` · 0,1,0)는 순서와 상관없이 **진다.** 015 는 정본의 인라인 값을 칸의 유틸리티로 옮겼고,
 * 후보 우선순위 표의 값 칸이 모노 글꼴을, 이름 칸이 13px 을, 양 끝 칸이 14px 여백을 잃었다 — 클래스는 붙어 있고
 * 가드 G-B 는 그 클래스가 CSS 를 만든다는 것만 보므로 아무도 몰랐다.
 *
 * 그래서 글자 모양은 칸 안의 `<span>` 이 갖고, 칸마다 다른 여백은 표가 **같은 깊이 이상의 선택자**
 * (`[&_td:first-child]:…`)로 준다. 오른쪽 정렬은 `align` 으로 준다(표가 정렬을 정하지 않으므로 다투지 않는다).
 *
 * ## 머리 칸은 한 모양이다 (B-09)
 *
 * 015 전환에서 초안 표의 머리가 `.grid-head` 가 아닌 옅은 우물 바탕만 받아, 브라우저 기본 `th{text-align:center;
 * font-weight:bold}` 이 드러났다 — 머리 칸이 가운데, 본문 칸이 왼쪽에 서고, 마지막 머리만 모노 대문자였다.
 * `TableHead` 가 정본 `.grid-head th` 를 명시해 기본값에 기대지 않는다. 오른쪽에 서는 열은 머리와 본문에
 * **같은 `align`** 을 준다.
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

export type TableVariant = "panel" | "grid" | "compact";

export const tableVariants = cva("border-collapse", {
  variants: {
    variant: {
      // 정본 `.table{width:100%;border-collapse:collapse;background:var(--panel)}` · `.table td{padding:0 12px;
      // height:40px;font:400 12px/1}` · `.table tr + tr td{border-top:1px solid var(--hair)}` + 판 테두리
      panel:
        "w-full bg-panel border border-hair rounded-base " +
        "[&_td]:px-s3 [&_td]:h-[40px] [&_td]:font-sans [&_td]:text-[12px] [&_td]:leading-none " +
        "[&_tr+tr_td]:border-t [&_tr+tr_td]:border-hair",
      grid: "w-full [&_th]:py-[6px] [&_th]:px-s2 [&_td]:py-[6px] [&_td]:px-s2",
      // 정본 `.why{font:400 11px/1.4 sans;color:--ink-3}` 글자의 작은 표본. 폭은 내용만큼이다 — 칸 안에 놓인다.
      compact:
        "[&_td]:py-[2px] [&_td]:px-[6px] [&_td]:font-sans [&_td]:text-[12px] [&_td]:leading-[1.4] [&_td]:text-ink-3",
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

/**
 * 표 행의 뜻. 정본 `.table tr.in-use td`(지금 쓰이는 줄) · `.table tr.last-resort td`(최후 수단) ·
 * `.dim`(가져오지 않기로 한 줄처럼 **빠진** 줄 — 글자만 흐리다).
 */
export type TableRowTone = "default" | "in-use" | "last-resort" | "muted";

const ROW_TONE: Record<TableRowTone, string> = {
  default: "",
  // 옅은 통과 바탕 — 나머지와 구분되되 주장하지 않는다.
  "in-use": "[&>td]:bg-pass-t",
  // 옅은 우물 — 쓸 수는 있으나 마지막이라는 뜻이다 (원칙 IV).
  "last-resort": "[&>td]:bg-sunken-2",
  // 정본 `.dim{color:var(--ink-3)}` — 칸이 물려받는다. 칸 안 글자가 제 색을 가지면 그것이 이긴다.
  muted: "text-ink-3",
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

/** 칸의 가로 정렬. 오른쪽에 서는 열은 머리와 본문에 같은 값을 준다 (B-09). */
export type TableAlign = "left" | "right";

/**
 * 머리 칸 — 정본 `.grid-head th{text-align:left;font:600 11px/1 mono;letter-spacing:.08em;uppercase;color:--ink-3}`.
 * 여백은 표의 `variant` 가 정한다.
 */
export const tableHeadVariants = cva(
  "align-middle font-sans text-[12px] font-semibold leading-[1.4] text-ink-2 whitespace-nowrap",
  {
    variants: { align: { left: "text-left", right: "text-right" } },
    defaultVariants: { align: "left" },
  },
);

export function TableHead({
  align = "left",
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<"th">, "className" | "align"> & LayoutProps & { align?: TableAlign }) {
  return (
    <th className={cn(tableHeadVariants({ align }), layout)} data-slot="table-head" {...rest}>
      {children}
    </th>
  );
}

/**
 * 본문 칸. 여백·높이·글자는 표의 `variant` 가 정한다 (정본 `.table td`). `left` 는 정렬을 정하지 않는다 — 표나
 * 행이 물려주는 값을 그대로 쓴다.
 */
export const tableCellVariants = cva("align-middle", {
  variants: { align: { left: "", right: "text-right" } },
  defaultVariants: { align: "left" },
});

export function TableCell({
  align = "left",
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<"td">, "className" | "align"> & LayoutProps & { align?: TableAlign }) {
  return (
    <td className={cn(tableCellVariants({ align }), layout)} data-slot="table-cell" {...rest}>
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
 * 2026-09 가시성 개선: 테스트 행은 최소 64px, 이름과 실패 요약 두 줄을 수용한다.
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
    "min-h-[64px] items-center border-b border-hair border-solid border-t-0 border-r-0 " +
    `border-l-[length:var(--mark)] ${MARK[mark]}`
  );
}

/** 정본 `.row` — 가로로 늘어놓는 줄. 간격은 `--s-2`(8px). */
export function Row({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"div">, "className"> & LayoutProps) {
  return (
    <div className={cn("flex items-center gap-s2", layout)} data-slot="row" {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.spacer` — 남는 자리를 먹는다. `Row` 안에서 다음 것을 오른쪽으로 민다. */
export function Spacer({ layout, ...rest }: Omit<ComponentPropsWithRef<"span">, "className"> & { layout?: string }) {
  return <span className={cn("flex-1", layout)} data-slot="spacer" {...rest} />;
}
