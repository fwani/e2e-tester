/**
 * 폼 — 입력칸·라벨·파일 선택. 015 T024.
 *
 * ## 상태 스타일을 함께 옮겼다 — 이 군은 그것이 본체다
 *
 * [state-styles.md](../../../specs/015-tailwind-css-migration/contracts/state-styles.md)
 * 의 S-06·S-07·S-16·S-17 이 여기로 온다. 정본을 `layer(base)` 로 내렸으므로
 * `input:disabled{…}` 같은 요소 규칙이 유틸리티에 진다 — **옮기지 않으면 비활성 입력칸이
 * 활성처럼 보인다.** 화면은 멀쩡해 보이고 테스트도 통과한다.
 *
 * | # | 정본 | 여기서 |
 * |---|---|---|
 * | S-06 | `input::placeholder{color:--ink-3}` | `placeholder:text-ink-3` |
 * | S-07 | `input:disabled{투명·점선·--ink-3}` | `disabled:*` |
 * | S-16 | `.btn.file:focus-within{링}` | `FileButton` 의 `focus-within:outline-*` |
 * | S-17 | `.btn.disabled:focus-within{흐린 링}` | `FileButton` 의 off 상태 |
 *
 * S-16·S-17 이 `:focus-within` 인 이유: `<label>` 은 초점을 받지 못한다. 안쪽 `<input>` 이
 * 받고 라벨이 링을 그린다. 그 구조를 깨면 **파일 선택 버튼이 키보드에서 사라진다.**
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

type DivProps = Omit<ComponentPropsWithRef<"div">, "className">;

/**
 * 정본 `.field` — 입력칸을 감싸는 테두리 상자.
 *
 * 안쪽 `<input>` 은 테두리·바탕·그림자를 벗는다 (정본 `.field input`). 테두리는 이
 * 상자가 그리므로, 안쪽이 또 그리면 두 겹이 된다.
 *
 * `off` 는 정본 `.field.off` — 담을 것이 아직 없는 상태다. 점선이고 **자리를 지킨다**
 * (`.btn.off` 와 같은 문법 · 006 ui-contract §2 「쓸 수 없는 조작은 감추지 않는다」).
 */
export function Field({ off = false, layout, children, ...rest }: DivProps & { off?: boolean; layout?: string; children?: ReactNode }) {
  const cls = [
    "h-control flex items-center gap-s2 px-[10px] border rounded-base",
    off ? "border-dashed border-hair-2 bg-transparent" : "border-hair-2 bg-panel",
    // 안쪽 입력칸을 벗긴다 — 정본 `.field input` 을 그대로 옮겼다.
    "[&_input]:flex-1 [&_input]:min-h-auto [&_input]:p-0 [&_input]:border-0",
    "[&_input]:bg-transparent [&_input]:shadow-none [&_input]:outline-none",
    "[&_input]:font-sans [&_input]:text-[13px] [&_input]:leading-none",
    "[&_input]:placeholder:text-ink-3",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} data-off={off ? "true" : undefined} {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.field-label` — 칸 위의 설명. 라벨(`Lbl`)과 다르다 — 이쪽은 문장이다. */
export function FieldLabel({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = ["font-sans text-[12px] leading-none font-normal text-ink-3", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.lbl` — 구획 라벨. 11px 대문자 모노다.
 *
 * **문장을 담지 않는다.** 정본 주석이 답 칸(`.answer-q`)을 따로 둔 이유가 이것이다 —
 * 라벨 형태로 한 문장을 읽게 하면 읽히지 않는다.
 */
export function Lbl({ layout, children, ...rest }: Omit<ComponentPropsWithRef<"span">, "className"> & { layout?: string; children?: ReactNode }) {
  const cls = [
    "font-mono text-[11px] font-semibold leading-none tracking-[.08em] uppercase text-ink-3",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={cls} {...rest}>
      {children}
    </span>
  );
}

/**
 * 정본 `.answer-q` — AI 가 막혔을 때 사람이 답을 적는 자리의 질문.
 *
 * 라벨이 아니라 **본문**이다 (위 `Lbl` 주석 참조).
 */
export function AnswerQuestion({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = ["font-sans text-[13px] leading-[1.4] font-normal text-ink", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.commit-bar` — 목록 아래에 붙는 확정·취소 자리.
 *
 * **화면 아래에 붙어 따라온다** (`sticky bottom-0`). 목록이 길어도 확정 조작이 화면 밖으로
 * 밀려나지 않게 하는 것이 이 부품의 성질이다.
 */
export function CommitBar({ layout, children, ...rest }: DivProps & { layout?: string; children?: ReactNode }) {
  const cls = ["sticky bottom-0 z-10 bg-panel border-t border-hair-2", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.btn.file` + `.file-input` — 파일 선택.
 *
 * `<label>` 안에 보이지 않는 `<input type="file">` 을 둔다. 브라우저 기본 파일 선택
 * 위젯은 형태를 정할 수 없으므로 이 구조를 쓴다.
 *
 * **입력칸을 `display:none` 으로 감추지 않는다.** 감추면 초점을 받지 못해 키보드로
 * 도달할 수 없다. 1px 로 줄이고 `clip-path` 로 잘라 **보이지 않되 초점은 남긴다** —
 * 그리고 라벨이 `:focus-within` 으로 링을 그린다 (S-16·S-17).
 *
 * `off` 는 정본 `.btn.disabled` 다. `<label>` 은 `:disabled` 를 받지 못하므로 형태를
 * 따로 둔다 — `button:disabled` 와 같은 점선이고, 감추지 않고 자리를 지킨다.
 */
export function FileButton({
  off = false,
  small = false,
  layout,
  children,
  inputProps,
  ...rest
}: Omit<ComponentPropsWithRef<"label">, "className"> & {
  off?: boolean;
  small?: boolean;
  layout?: string;
  children?: ReactNode;
  /**
   * 안쪽 `<input type=file>` 에 그대로 넘긴다. `data-*` 도 받는다 — 검사가 그 입력칸을
   * 지목하는 통로이며(`data-import-file`), 부품이 감싼다고 사라지면 안 된다.
   */
  inputProps?: Omit<ComponentPropsWithRef<"input">, "className" | "type"> & Record<`data-${string}`, unknown>;
}) {
  const cls = [
    // `.btn` 의 형태 — `ui/Button` 과 같은 값이다. 라벨이므로 컴포넌트를 나눴다.
    //
    // **크기·상태가 정하는 속성은 여기 적지 않는다.** 같은 속성을 두 번 적으면 이기는
    // 쪽을 Tailwind 의 정렬 순서가 정하고, `className` 에 나중에 적은 쪽이 진다 —
    // 그래서 `small` 이 글자 크기도 좌우 여백도 바꾸지 못하고 있었다 (G-E).
    "relative inline-flex items-center gap-[6px] border rounded-base",
    "font-sans leading-none whitespace-nowrap",
    "m-0 tracking-normal normal-case",
    small ? "h-control-sm px-[9px] text-[12px]" : "h-control px-s3 text-[13px]",
    off
      ? "bg-transparent border-dashed border-hair-2 text-ink-3 shadow-none font-medium cursor-not-allowed"
      : "bg-panel border-hair-2 text-ink shadow-e1 font-semibold cursor-pointer hover:bg-sunken-2",
    // S-16·S-17 — 라벨이 링을 그린다. 안쪽 입력칸이 초점을 받기 때문이다.
    off
      ? "focus-within:outline focus-within:outline-2 focus-within:outline-hair-2 focus-within:outline-offset-2"
      : "focus-within:outline focus-within:outline-2 focus-within:outline-run focus-within:outline-offset-2",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <label className={cls} data-off={off ? "true" : undefined} {...rest}>
      {children}
      <input
        type="file"
        disabled={off}
        // 정본 `.file-input` — 보이지 않되 초점은 남긴다.
        className="absolute w-px h-px min-h-0 p-0 m-0 border-0 overflow-hidden [clip-path:inset(50%)] whitespace-nowrap"
        {...inputProps}
      />
    </label>
  );
}
