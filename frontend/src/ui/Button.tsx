/**
 * 버튼 — 의미 클래스 `.btn` 계열이 해체되어 온 곳. 015 T015.
 *
 * ## 이 부품이 값을 갖는 이유
 *
 * 015 는 「값은 정본 한 곳에만」을 지킨다 (FR-001). 그런데 아래에는 `gap-[6px]` ·
 * `text-[13px]` · `px-[9px]` 같은 값이 있다. 모순처럼 보이지만 그렇지 않다 —
 * **그 값들은 정본에도 토큰이 아니라 리터럴로 있었다.**
 *
 *     .btn{…gap:6px;…font:600 13px/1 var(--font-sans);…}
 *     .btn.sm{height:26px;padding:0 9px;font-size:12px;}
 *
 * 토큰화되지 않은 이 값들이 해체와 함께 화면 코드 44곳으로 흩어지면, 그것이 008 이
 * 고친 문제(값 리터럴 338개)의 재발이다. 부품이 값을 안고 있으면 **정의가 여전히 한
 * 곳**이고 화면 코드에는 값이 없다. 그것이 이 부품의 존재 이유다 (SC-006·SC-010).
 *
 * 토큰이 있는 값은 반드시 토큰을 쓴다 — `h-control`(32px) · `px-s3`(12px) ·
 * `rounded-base` · `border-hair-2` · `shadow-e1`.
 *
 * ## 시각 동일성에서 딱 하나 바꾼 것
 *
 * `.btn.primary` 의 글자색이 정본에서 `#fff` 리터럴이었다. 여기서는 `text-panel`
 * (`--panel` = `#FFFFFF`)을 쓴다. **값은 같고** 팔레트 밖 리터럴 하나가 사라진다.
 *
 * ## 왜 BASE 에 색·배경·그림자·굵기가 없는가
 *
 * **`className` 의 순서는 승부를 정하지 않는다.** 같은 속성을 두 유틸리티가 선언하면
 * 이기는 쪽은 **산출 CSS 에서 뒤에 오는 것**이고, 그 순서는 Tailwind 가 정한다.
 *
 * 이 파일의 1회차는 BASE 에 `bg-panel text-ink` 를 두고 변종이 `bg-ink text-panel` 로
 * 덮어쓰게 했다. 덮이지 않았다 — `.bg-panel` 이 `.bg-ink` 보다 뒤에 놓이기 때문이다.
 * 결과는 **흰 배경 위의 흰 글자**였고, 강조 버튼이 보이지 않았다 (2026-09-11 신고).
 * danger 는 테두리도 글자도 빨갛지 않았고, `sm` 은 글자 크기와 좌우 여백이 `md` 였다.
 *
 * `toHaveClass("bg-ink")` 는 통과했다. 클래스는 실제로 붙어 있었기 때문이다.
 *
 * 그래서 규율을 뒤집었다 — **변종이 건드리는 속성은 BASE 가 아예 갖지 않는다.**
 * 배경·테두리색·글자색·그림자·글자굵기·hover 배경은 `VARIANT` 가, 높이·좌우 여백·
 * 글자 크기는 `SIZE` 가 **각자 온전히** 갖는다. 표의 항목마다 같은 속성을 다 적어야
 * 하므로 조금 길어지지만, 한 요소에 같은 속성이 두 번 붙는 일이 없어진다.
 *
 * 가드 `tests/ClassConflict.test.ts`(G-E)가 이 규율을 강제한다.
 *
 * ## 왜 `<button>` 만 받는가
 *
 * 착수 시점 실측에서 `.btn` 은 44곳 전부 `<button>` 에 쓰였다. 파일 선택 버튼
 * (`.btn.file`)만 `<label>` 이며, 그것은 폼 부품 관할이다 (T024).
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

/** 정본의 `.btn.{primary,danger,off,quiet}` 에 대응한다. `default` 는 수식 없는 `.btn`. */
export type ButtonVariant = "default" | "primary" | "danger" | "off" | "quiet" | "ghost";

/** 정본의 `.btn.sm`. `md` 는 수식 없는 기본 크기(32px)다. */
export type ButtonSize = "md" | "sm";

// React 19 는 함수 컴포넌트가 `ref` 를 일반 prop 으로 받는다. `ComponentPropsWithRef`
// 를 쓰면 호출부가 하던 `ref` 전달이 그대로 이어진다 — 기존 코드를 고치지 않는다.
export interface ButtonProps extends Omit<ComponentPropsWithRef<"button">, "className"> {
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  /**
   * **배치만.** 이 버튼이 놓인 자리가 요구하는 것 — 폭 제한, 줄바꿈, 넘침 처리 따위다.
   *
   * 모양(색·테두리·글꼴·그림자)을 여기로 넘기면 같은 버튼이 화면마다 달라지고,
   * 그것이 SC-010 이 막으려는 것이다. 모양이 필요하면 `variant` 를 늘린다 —
   * 그러면 그 결정이 이 파일 한 곳에 남는다.
   *
   * 배치를 부품이 아니라 **부모**가 정하는 것은 007 배치 계약의 원칙이기도 하다:
   * 표시 컴포넌트는 자기 자리 크기를 모른다 (layout-contract-v2 LC-1).
   */
  readonly layout?: string;
  readonly children?: ReactNode;
}

/**
 * 기본 모양. 정본 `.btn` 을 그대로 옮긴 것이다.
 *
 * `gap-[6px]`·`text-[13px]` 는 정본에 토큰이 없는 값이다 (위 주석 참조).
 * `font-semibold`=600, `leading-none`=line-height:1.
 */
const BASE =
  "inline-flex items-center gap-[6px] " +
  "border rounded-base " +
  "font-sans leading-none whitespace-nowrap " +
  // 상태 — 정본의 `button:active`·`button:disabled` 를 옮겼다.
  // **이것을 빠뜨리면 조용한 회귀가 된다.** 정본을 `layer(base)` 로 들이므로
  // 요소 규칙(`button:hover{…}`)이 유틸리티에 지고, 상태 변화가 사라진다.
  // 화면은 멀쩡해 보이고 테스트도 통과한다 — 마우스를 올려야만 보인다.
  // FR-009(상호작용 상태 보존)가 이것을 요건으로 못 박은 이유다.
  //
  // `hover` 배경은 여기 두지 않는다 — 변종마다 다르기 때문이다. 아래 「왜 BASE 가
  // 비어 있는가」 참조.
  "active:shadow-none disabled:bg-transparent disabled:border-dashed disabled:border-hair-2 " +
  "disabled:text-ink-3 disabled:shadow-none disabled:font-medium disabled:cursor-not-allowed";

/**
 * 변종별 덧칠. **`Record` 로 두어 종류가 늘 때 빠뜨릴 수 없게 한다** —
 * `lib/layout.ts` 의 배치 표와 같은 규율이다 (FR-020a 의 정신).
 */
const VARIANT: Record<ButtonVariant, string> = {
  // `button.secondary` 도 여기로 온다 — 정본 주석이 「이전 판의 이름. 지금은 기본형이
  // 곧 보조 조작이다」라고 적었고, 선언이 실제로 `button{}` 기본과 같다.
  default: "bg-panel border-hair-2 text-ink shadow-e1 font-semibold hover:bg-sunken-2",
  // 정본: background:var(--ink); border-color:var(--ink); color:#fff
  primary: "bg-ink border-ink text-panel shadow-e1 font-semibold hover:bg-ink-2",
  // 정본: background:var(--panel); border-color:var(--fail); color:var(--fail)
  danger: "bg-panel border-fail text-fail shadow-e1 font-semibold hover:bg-fail-t",
  // 정본: background:transparent; border:1px dashed; color:var(--ink-3); box-shadow:none; font-weight:500
  off: "bg-transparent border-dashed border-hair-2 text-ink-3 shadow-none font-medium hover:bg-transparent",
  // 정본: color:var(--ink-2); box-shadow:none. 배경·테두리는 기본형과 같다.
  quiet: "bg-panel border-hair-2 text-ink-2 shadow-none font-semibold hover:bg-sunken-2",
  // 정본 `button.ghost`: 투명 배경·테두리, 그림자 없음, hover 시 sunken
  ghost: "bg-transparent border-transparent text-ink-2 shadow-none font-semibold hover:bg-sunken",
};

/** 정본: `.btn` 은 32px·padding 12px·13px 글자, `.btn.sm` 은 26px·9px·12px. */
const SIZE: Record<ButtonSize, string> = {
  md: "h-control px-s3 text-[13px]",
  sm: "h-control-sm px-[9px] text-[12px]",
};


/**
 * 정본 `.navlink` — **확정 디자인에 없는 화면으로 가는 길.** 015 T073·T074.
 *
 * 버튼이지만 버튼처럼 보이지 않는다: 테두리도 그림자도 배경도 없고 글자가 한 톤 연하다.
 * 목록 위의 「바꾸기」·「비밀 값」·「키 관리」, 행 메뉴의 항목, 접었다 펴는 토글이
 * 이것이다. 눈에 띄지 않게 두는 것이 의도다 (`pages/TestList.tsx` 주석).
 *
 * ## 왜 함수인가
 *
 * 26곳이 쓰고, 그중 여럿이 `<button>` 그대로여야 한다 (행 메뉴가 `data-row-menu-item`
 * 으로 집는 자리, `justify-start` 로 왼쪽 정렬하는 자리 등). 부품으로 감싸는 대신
 * **정의를 한 곳에 두고 클래스를 꺼내 쓴다** — `ui/Chip` 의 `chipClasses`,
 * `ui/Table` 의 `rowClasses` 와 같은 규율이다.
 *
 * ## 빠뜨리면 버튼이 된다
 *
 * 1회차 전환은 `h-[28px] inline-flex items-center px-[10px] border-0 rounded-base
 * hover:bg-sunken` 까지만 옮기고 **배경·글자색·굵기·그림자를 빠뜨렸다.** 그것들은
 * 전역 `button{}` 규칙이 주므로, 빠진 자리에서 `.navlink` 는 **보통 버튼으로
 * 그려졌다** — 흰 바탕에 회색 테두리와 그림자. 26곳 전부가 그랬고, 눈으로도 기존
 * 검사로도 잡히지 않았다. L2 대조(`scripts/design_compare_ba.py`)가 찾았다.
 */
export function navLinkClasses(layout?: string): string {
  return [
    "h-[28px] inline-flex items-center px-[10px] border-0 rounded-base",
    // 전역 `button{}` 이 주는 것을 되돌린다. 이 넷이 `.navlink` 의 정체다.
    "bg-transparent text-ink-2 font-sans text-[13px] font-medium leading-none shadow-none",
    "hover:bg-sunken",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
}

export function Button({ variant = "default", size = "md", layout, children, ...rest }: ButtonProps) {
  // 클래스 이름을 조립하지 않는다 — 표에서 완성된 문자열을 꺼내 이어 붙일 뿐이다.
  // Tailwind 는 소스를 텍스트로 스캔하므로 `bg-${x}` 같은 것을 찾지 못한다 (가드 G-B).
  const cls = [BASE, SIZE[size], VARIANT[variant], layout].filter(Boolean).join(" ");
  // `data-variant`·`data-size` 로 **의도**를 내보낸다. 유틸리티 클래스는 그 의도가
  // 어떻게 그려지는지를 말할 뿐이라, 검사가 `text-ink-2 shadow-none` 을 읽으면 구현
  // 세부에 묶인다 — 색 하나만 바꿔도 검사가 깨지고, 정작 「강조가 없는가」라는 질문은
  // 사라진다. 클래스가 실제로 CSS 를 만드는지는 가드 G-B 가 따로 본다 (LC-4 의 3겹).
  return (
    <button className={cls} data-variant={variant} data-size={size} {...rest}>
      {children}
    </button>
  );
}
