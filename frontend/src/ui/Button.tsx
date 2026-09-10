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
  "inline-flex items-center gap-[6px] px-s3 " +
  "border border-hair-2 rounded-base bg-panel text-ink " +
  "font-sans text-[13px] font-semibold leading-none shadow-e1 whitespace-nowrap " +
  // 상태 — 정본의 `button:hover`·`button:active`·`button:disabled` 를 옮겼다.
  // **이것을 빠뜨리면 조용한 회귀가 된다.** 정본을 `layer(base)` 로 들이므로
  // 요소 규칙(`button:hover{…}`)이 유틸리티(`bg-panel`)에 지고, hover 배경 변화가
  // 사라진다. 화면은 멀쩡해 보이고 테스트도 통과한다 — 마우스를 올려야만 보인다.
  // FR-009(상호작용 상태 보존)가 이것을 요건으로 못 박은 이유다.
  "hover:bg-sunken-2 active:shadow-none " +
  "disabled:bg-transparent disabled:border-dashed disabled:border-hair-2 " +
  "disabled:text-ink-3 disabled:shadow-none disabled:font-medium disabled:cursor-not-allowed";

/**
 * 변종별 덧칠. **`Record` 로 두어 종류가 늘 때 빠뜨릴 수 없게 한다** —
 * `lib/layout.ts` 의 배치 표와 같은 규율이다 (FR-020a 의 정신).
 */
const VARIANT: Record<ButtonVariant, string> = {
  // `button.secondary` 도 여기로 온다 — 정본 주석이 「이전 판의 이름. 지금은 기본형이
  // 곧 보조 조작이다」라고 적었고, 선언이 실제로 `button{}` 기본과 같다.
  default: "",
  // 정본: background:var(--ink); border-color:var(--ink); color:#fff
  primary: "bg-ink border-ink text-panel hover:bg-ink-2",
  // 정본: background:var(--panel); border-color:var(--fail); color:var(--fail)
  danger: "bg-panel border-fail text-fail hover:bg-fail-t",
  // 정본: background:transparent; border:1px dashed; color:var(--ink-3); box-shadow:none; font-weight:500
  off: "bg-transparent border-dashed border-hair-2 text-ink-3 shadow-none font-medium hover:bg-transparent",
  // 정본: color:var(--ink-2); box-shadow:none
  quiet: "text-ink-2 shadow-none",
  // 정본 `button.ghost`: 투명 배경·테두리, 그림자 없음, hover 시 sunken
  ghost: "bg-transparent border-transparent text-ink-2 shadow-none hover:bg-sunken",
};

/** 정본: `.btn` 은 32px, `.btn.sm` 은 26px·padding 9px·12px 글자. */
const SIZE: Record<ButtonSize, string> = {
  md: "h-control",
  sm: "h-control-sm px-[9px] text-[12px]",
};

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
