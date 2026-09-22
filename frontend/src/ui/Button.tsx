/**
 * 버튼 — shadcn/ui `button` 을 정본 모습으로 이식한 부품. 017 T025.
 *
 * 출처: shadcn new-york-v4/button @ shadcn 4.21.0 (2026-09-15) — 구조(`cva` 변종 표 · `asChild` ·
 * `data-slot`·`data-variant`·`data-size`)를 가져오고, 클래스는 contracts/ui-parts.md §2 대응표대로
 * 정본으로 옮겼다. 원본의 `rounded-lg`·`h-8`·`bg-primary`·`focus-visible:ring-3`·
 * `disabled:opacity-50`·`transition-all`·`dark:*` 는 하나도 남지 않는다.
 *
 * ## 이 부품이 값을 갖는 이유 (015 에서 이어짐)
 *
 * 015 는 「값은 정본 한 곳에만」을 지킨다. 아래의 `gap-[6px]` · `text-[14px]` · `px-[9px]` 는
 * **정본에도 토큰이 아니라 리터럴로 있었다** (`.btn{gap:6px;font:600 13px/1 …}` ·
 * `.btn.sm{height:26px;padding:0 9px;font-size:12px}`). 화면 코드로 흩어지면 008 이 고친 문제(값
 * 리터럴 338개)의 재발이므로 부품이 안고 있다. 토큰이 있는 값은 토큰을 쓴다 — `h-control` ·
 * `px-s3` · `rounded-base` · `border-hair-2` · `shadow-e1`.
 *
 * ## 표가 둘인 이유
 *
 * 정본의 버튼 계열은 **구조가 두 갈래다.**
 *
 * | 갈래 | 정본 | 테두리 | 높이 | 비활성 |
 * |---|---|---|---|---|
 * | 상자 (`buttonVariants`) | `.btn` · `.btn.primary|danger|off|sm` · `button.ghost` | 1px | 32 · 26 | 점선으로 자리를 지킨다 |
 * | 글자 (`plainButtonVariants`) | `.navlink` · `.textlink` · `.srow .srow-name` | 없음 | 28 · 내용 · 18 | 정본에 없음 |
 *
 * 한 `cva` 에 넣으면 크기 축(`h-control`)이 글자 갈래에도 붙고, 가드 G-E 는 표의 조합을 전부 만들어
 * 보므로 **있을 수 없는 조합**(`nav` 에 `md` 높이)의 충돌을 보고한다. 글자 갈래는 `display`·줄 높이·
 * 줄바꿈까지 상자와 달라서 공통 바탕을 둘 수도 없다 — 두면 계산된 스타일이 바뀌고 L2 대조가 어긋난다.
 * 그래서 표를 둘로 두고 `Button` 이 변종 이름으로 고른다. 호출부에게는 여전히 `variant` 하나다.
 *
 * ## 왜 상자 바탕(BASE)에 색·배경·그림자·굵기가 없는가 (015 에서 이어짐)
 *
 * **`className` 의 순서는 승부를 정하지 않는다.** 같은 속성을 두 유틸리티가 선언하면 산출 CSS 에서
 * 뒤에 오는 것이 이긴다. 015 1회차는 BASE 에 `bg-panel` 을 두고 변종이 `bg-ink` 로 덮게 했다가
 * **흰 배경 위의 흰 글자**를 냈다 (2026-09-11 신고). 그래서 변종이 건드리는 속성은 BASE 가 아예
 * 갖지 않는다 — 배경·테두리색·글자색·그림자·굵기·hover 는 `variant` 가, 높이·좌우 여백·글자 크기는
 * `size` 가 각자 온전히 갖는다. `cva` 는 BASE → variant → size 순으로 잇고, 가드 G-E 가 그 조합
 * 전부를 산출 CSS 순서와 대조한다 (017 guards H-1).
 *
 * ## `className` 을 받지 않는다
 *
 * shadcn 원본은 `className` 을 받아 `tailwind-merge` 로 합친다. 이 부품은 받지 않는다 — **`layout`
 * 은 배치만**이다(015 · research R5). 모양을 호출부가 덮어쓰면 같은 버튼이 화면마다 달라진다(SC-010).
 */
import { cva } from "class-variance-authority";
import type { ComponentPropsWithRef, MouseEvent, ReactNode } from "react";

import { cn } from "./cn";

/** 상자 갈래 — 정본 `.btn` 과 그 수식. */
type BoxVariant = "default" | "primary" | "danger" | "off" | "quiet" | "ghost";
/** 글자 갈래 — 정본 `.navlink`(nav) · `.textlink`(link) · `.srow-name`(bare). */
type PlainVariant = "nav" | "link" | "bare";

export type ButtonVariant = BoxVariant | PlainVariant;

/** 정본의 `.btn.sm`. `md` 는 수식 없는 기본 크기(32px)다. 글자 갈래에는 크기가 없다. */
export type ButtonSize = "md" | "sm" | "icon";

/**
 * 상자 갈래. 바탕은 정본 `.btn` 을 그대로 옮긴 것이다.
 *
 * 상태 — 정본의 `button:active`·`button:disabled` 를 옮겼다(015 state-styles S-02·S-03). 정본을
 * `layer(base)` 로 들이므로 요소 규칙의 상태가 유틸리티에 진다 — **빠뜨리면 조용한 회귀가 된다.**
 * 비활성은 흐림이 아니라 점선이며 포인터를 막지 않는다 — 사유를 담은 `title` 이 떠야 한다 (FR-014).
 */
export const buttonVariants = cva(
  "inline-flex items-center gap-[6px] border rounded-base font-sans leading-none whitespace-nowrap " +
    "active:shadow-none disabled:bg-transparent disabled:border-dashed disabled:border-hair-2 " +
    "disabled:text-ink-3 disabled:shadow-none disabled:font-medium disabled:cursor-not-allowed",
  {
    variants: {
      variant: {
        // `button.secondary` 도 여기로 온다 — 정본 주석이 「지금은 기본형이 곧 보조 조작이다」라고 적었다.
        default: "bg-panel border-hair-2 text-ink shadow-e1 font-semibold hover:bg-sunken-2",
        // 정본: background:var(--ink); border-color:var(--ink); color:#fff (→ `text-panel`, 같은 값)
        primary: "bg-ink border-ink text-panel shadow-e1 font-semibold hover:bg-ink-2",
        // 정본: 위험은 **채우지 않는다** — 테두리와 글자만 실패색 (shadcn `destructive` 와 다르다)
        danger: "bg-panel border-fail text-fail shadow-e1 font-semibold hover:bg-fail-t",
        // 정본 `.btn.off`: 투명 · 점선 · --ink-3 · 그림자 없음 · 500
        off: "bg-transparent border-dashed border-hair-2 text-ink-3 shadow-none font-medium hover:bg-transparent",
        // 정본: color:var(--ink-2); box-shadow:none. 배경·테두리는 기본형과 같다.
        quiet: "bg-panel border-hair-2 text-ink-2 shadow-none font-semibold hover:bg-sunken-2",
        // 정본 `button.ghost`: 투명 배경·테두리, 그림자 없음, hover 시 sunken
        ghost: "bg-transparent border-transparent text-ink-2 shadow-none font-semibold hover:bg-sunken",
      },
      size: {
        md: "h-control px-s3 text-[14px]",
        sm: "h-control-sm px-[9px] text-[12px]",
        /*
          아이콘만 담는 작은 단추 — 정본에서 `.btn.sm` 에 `padding: 0 7px` 를 인라인으로 더하던 자리
          (행 메뉴 `⋯` · 상세 닫기 `×`). **`layout` 으로 넘기면 안 된다** — 승부는 산출 CSS 순서가
          정하고 `px-[9px]` 이 `px-[7px]` 을 이긴다(015 L2 대조가 잡았다). 크기를 다투는 값은 이 표에 둔다.
        */
        icon: "h-control-sm px-[7px] text-[12px]",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

/**
 * 글자 갈래 — 버튼이지만 버튼처럼 보이지 않는 것.
 *
 * **각 값이 모양 전부를 갖는다.** 공통 바탕이 없는 이유는 머리주석 「표가 둘인 이유」.
 */
export const plainButtonVariants = cva("", {
  variants: {
    variant: {
      /*
        정본 `.navlink` — 확정 디자인에 없는 화면으로 가는 길 (목록 위의 「바꾸기」·「비밀 값」, 행 메뉴
        항목, 접었다 펴는 토글). 015 에서 `navLinkClasses()` 로 26곳이 쓰던 것이 여기로 왔다.
        테두리·그림자·배경을 **명시해서 되돌린다** — 빠뜨리면 전역 `button{}` 이 흰 바탕·회색
        테두리·그림자를 준다 (015 1회차 · L2 가 찾았다).
      */
      nav:
        "h-[28px] inline-flex items-center px-[10px] border-0 rounded-base bg-transparent text-ink-2 " +
        "font-sans text-[14px] font-medium leading-none shadow-none hover:bg-sunken",
      /*
        정본 `.textlink` — 글 안의 조작. 비활성 사유 옆의 해소 수단이 이것이다. 상자를 만들지 않는다.
      */
      link:
        "border-0 p-0 h-auto bg-transparent shadow-none text-run font-sans text-[12px] font-semibold " +
        "leading-[1.4] underline cursor-pointer",
      /*
        정본 `.srow .t .srow-name` — Step 행 안의 이름. 확정 디자인은 굵은 글자로 그리지만 제품에서는
        **누를 수 있는 요소**여야 한다(행 지목 · 접근성). 형태는 같고 상자만 없앤다. 한 줄로 자른다.
      */
      bare:
        "border-0 p-0 h-[18px] bg-transparent shadow-none text-left text-ink cursor-pointer font-sans " +
        "text-[14px] font-semibold leading-[1.25] whitespace-nowrap overflow-hidden text-ellipsis",
    },
  },
});

const PLAIN: ReadonlySet<ButtonVariant> = new Set<ButtonVariant>(["nav", "link", "bare"]);

/**
 * 변종 이름으로 표를 고른다. `Button` 과 `ButtonLink` 가 **같은 모양**을 얻는 유일한 통로다 (018 §4).
 *
 * 클래스 이름을 조립하지 않는다 — 표에서 완성된 문자열을 꺼낼 뿐이다.
 * Tailwind 는 소스를 텍스트로 스캔하므로 `bg-${x}` 같은 것을 찾지 못한다 (가드 G-B).
 */
function shapeOf(variant: ButtonVariant, size: ButtonSize): string {
  return PLAIN.has(variant)
    ? plainButtonVariants({ variant: variant as PlainVariant })
    : buttonVariants({ variant: variant as BoxVariant, size });
}

// React 19 는 함수 컴포넌트가 `ref` 를 일반 prop 으로 받는다. `ComponentPropsWithRef` 를 쓰면
// 호출부가 하던 `ref` 전달이 그대로 이어진다.
export interface ButtonProps extends Omit<ComponentPropsWithRef<"button">, "className"> {
  readonly variant?: ButtonVariant;
  /** 상자 갈래에만 뜻이 있다. 글자 갈래에서는 무시된다. */
  readonly size?: ButtonSize;
  /**
   * **배치만.** 이 버튼이 놓인 자리가 요구하는 것 — 폭 제한, 줄바꿈, 넘침 처리 따위다.
   *
   * 모양(색·테두리·글꼴·그림자)을 여기로 넘기면 같은 버튼이 화면마다 달라진다(SC-010). 모양이 필요하면
   * `variant` 를 늘린다 — 그 결정이 이 파일 한 곳에 남는다. 배치를 **부모**가 정하는 것은 007 배치
   * 계약의 원칙이다: 표시 컴포넌트는 자기 자리 크기를 모른다 (layout-contract-v2 LC-1).
   */
  readonly layout?: string;
  readonly children?: ReactNode;
}

export function Button({ variant = "default", size = "md", layout, children, ...rest }: ButtonProps) {
  const cls = cn(shapeOf(variant, size), layout);
  /*
    **`asChild` 를 지웠다** (T106). 원본은 자식을 버튼 모양으로 그리는 통로를 두지만, 이 저장소에서 그것을
    쓰는 호출부가 **하나도 없었다**(전수 확인). 부품 층이 Base UI 로 옮겨 가며 `render` 가 그 몫을 하므로
    (`MenuTrigger`·`DialogClose`·`Tooltip` 이 그렇게 쓴다) 쓰이지 않는 통로를 위해 `radix-ui` 의존만 남기지
    않는다 — 이것이 `Button` 의 마지막 radix 참조였다 (T107 이 패키지를 지운다).
  */
  const Comp = "button";
  // `data-variant`·`data-size` 로 **의도**를 내보낸다. 검사가 유틸리티 조합을 읽으면 구현 세부에 묶이고,
  // 정작 「강조가 없는가」라는 질문이 사라진다. 클래스가 실제로 CSS 를 만드는지는 G-B 가 따로 본다.
  return (
    <Comp className={cls} data-slot="button" data-variant={variant} data-size={size} {...rest}>
      {children}
    </Comp>
  );
}

/**
 * 새 탭·새 창·다른 단추가 아닌 **보통 클릭**인가 (018 §4).
 *
 * 링크 부품은 이때만 앱 안에서 옮긴다. 나머지는 브라우저가 한다 — 사용자가 Cmd 를 누르고 눌렀다면
 * 원하는 것은 새 탭이다. 가운데 클릭은 `click` 이 아니라 `auxclick` 으로 오므로 여기까지 오지 않는다.
 */
export function isPlainClick(
  event: Pick<MouseEvent, "button" | "metaKey" | "ctrlKey" | "shiftKey" | "altKey">,
): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

export interface ButtonLinkProps extends Omit<ComponentPropsWithRef<"a">, "className" | "href"> {
  readonly href: string;
  /**
   * 보통 클릭일 때 부른다 — 라우트 어댑터가 `navigate()` 로 채운다.
   *
   * **없으면 평범한 링크다.** 루트 오류 화면처럼 앱 상태를 믿을 수 없는 자리는 문서를 새로 여는 것이 맞다.
   */
  readonly onNavigate?: () => void;
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  /** `Button` 과 같다 — 배치만. */
  readonly layout?: string;
  readonly children?: ReactNode;
}

/**
 * 버튼 모양의 링크 (018 §4).
 *
 * **순수 이동만** 이것으로 그린다 — 누르면 다른 화면으로 가고 그 밖의 일은 하지 않는 조작. 실행·녹화처럼
 * 부수효과가 있거나, 이동 전에 확인을 거치는 조작은 `Button` 이다. 링크는 비활성이 없으므로
 * 비활성 사유를 보여야 하는 조작에도 쓰지 않는다 (FR-014).
 *
 * `react-router` 의 `<Link>` 를 쓰지 않는다 — 라우터 밖에서 예외를 던지고, 화면은 라우터 없이도 그려진다.
 *
 * `box-border`: 전역 `button{}` 규칙과 브라우저 기본값이 버튼에는 `border-box` 를 주지만 `<a>` 는
 * `content-box` 다. 빠뜨리면 32px 상자가 테두리만큼 34px 가 된다. 모양 값이 아니라 상자 계산 방식이다.
 *
 * `text-center`: 브라우저 기본값이 `<button>` 에는 `text-align:center` 를 주지만 `<a>` 는 물려받은 값
 * (`start`)을 쓴다. L2 대조가 찾았다 — 짧은 글자는 눈에 띄지 않지만 계산된 스타일은 다르다. 이것도 상자
 * 계산 방식이지 새 모양 값이 아니다.
 */
export function ButtonLink({
  href,
  onNavigate,
  onClick,
  variant = "default",
  size = "md",
  layout,
  children,
  ...rest
}: ButtonLinkProps) {
  return (
    <a
      href={href}
      className={cn(shapeOf(variant, size), "box-border text-center", layout)}
      data-slot="button-link"
      data-variant={variant}
      data-size={size}
      onClick={(event) => {
        onClick?.(event);
        if (onNavigate === undefined || event.defaultPrevented || !isPlainClick(event)) return;
        event.preventDefault();
        onNavigate();
      }}
      {...rest}
    >
      {children}
    </a>
  );
}
