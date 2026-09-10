/**
 * 면 — 판·머리·층·가림막. 의미 클래스가 해체되어 온 곳. 015 T022·T023.
 *
 * 「무엇을 담는 자리인가」를 정하는 부품들이다. 담기는 내용은 모른다.
 *
 * | 부품 | 정본 | 쓰임 |
 * |---|---|---|
 * | `Pane` | `.pane` | 테두리와 바탕을 가진 판 |
 * | `PaneHead` | `.pane-hd` (`.band` 변종) | 판의 머리 띠 |
 * | `AppHeader` | `.hdr` | 화면 맨 위 머리띠 (56px) |
 * | `OverlayPane` | `.overlay-pane` | 목록 위에 겹쳐 뜨는 상세 판 |
 * | `Modal` | `.modal` | 대화상자 |
 * | `Scrim` | `.scrim` · `.modal-scrim` | 뒤를 덮는 가림막 |
 * | `Divider` | `.divider` | 세로 구분선 |
 *
 * ## 상태 스타일
 *
 * 이 군에는 `:hover`·`:focus`·`:disabled` 규칙이 없다 (state-styles.md 목록 확인).
 *
 * ## 승강은 두 값뿐이다
 *
 * `--e-1`(판) 과 `--e-2`(겹쳐 뜨는 것). **같은 층에 뜨는 것은 같은 높이**라는 규율이
 * 정본에 적혀 있다 — `OverlayPane` 과 `Toast` 가 둘 다 `shadow-e2` 인 이유다.
 */
import type { ComponentPropsWithRef, ReactNode } from "react";

type DivProps = Omit<ComponentPropsWithRef<"div">, "className">;
interface SurfaceProps extends DivProps {
  /** **배치만.** 모양은 부품이 정한다. */
  readonly layout?: string;
  readonly children?: ReactNode;
}

/** 정본 `.pane` — 테두리와 바탕을 가진 판. */
export function Pane({ layout, children, ...rest }: SurfaceProps) {
  const cls = ["bg-panel border border-hair rounded-base", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.pane-hd` — 판의 머리 띠.
 *
 * `band` 는 정본 `.pane-hd.band` 다. 확정 디자인이 표·목록 위의 라벨 줄을 36px 로 둔다.
 */
export function PaneHead({ band = false, layout, children, ...rest }: SurfaceProps & { band?: boolean }) {
  const cls = [
    "bg-sunken border-b border-hair-2 text-ink-2",
    band ? "h-[36px] flex items-center" : "",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} data-band={band ? "true" : undefined} {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.hdr` — 화면 맨 위 머리띠. 높이는 `--h-header`(56px) 고정. */
export function AppHeader({ layout, children, ...rest }: SurfaceProps) {
  const cls = [
    "flex-none h-header flex items-center gap-[14px] px-s4 bg-panel border-b border-hair",
    layout,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <header className={cls} {...rest}>
      {children}
    </header>
  );
}

/**
 * 정본 `.overlay-pane` — 목록 위에 겹쳐 뜨는 상세 판.
 *
 * `shadow-e2` 는 `Toast` 와 같다. 같은 층에 뜨는 것은 같은 높이다.
 */
export function OverlayPane({ layout, children, ...rest }: SurfaceProps) {
  const cls = ["bg-panel border-l border-hair-2 shadow-e2", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/** 정본 `.modal` — 대화상자. 모서리가 `--radius-lg` 로 판보다 크다. */
export function Modal({ layout, children, ...rest }: SurfaceProps) {
  const cls = ["bg-panel border border-hair-2 rounded-lg shadow-e2", layout].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}

/**
 * 정본 `.scrim` · `.modal-scrim` — 뒤를 덮는 가림막.
 *
 * 두 농도는 **뜻이 다르다.** 대화상자(`strong`)는 뒤를 만질 수 없다는 뜻이고,
 * 겹침(`soft`)은 뒤가 아직 거기 있다는 뜻이다. 값은 정본 그대로다.
 */
export function Scrim({ strength = "soft", layout, ...rest }: SurfaceProps & { strength?: "soft" | "strong" }) {
  const TONE: Record<"soft" | "strong", string> = {
    soft: "bg-[rgba(20,23,28,0.28)]",
    strong: "bg-[rgba(20,23,28,0.45)]",
  };
  const cls = [TONE[strength], layout].filter(Boolean).join(" ");
  return <div className={cls} data-strength={strength} {...rest} />;
}

/** 정본 `.divider` — 세로 구분선. */
export function Divider({ layout, ...rest }: Omit<SurfaceProps, "children">) {
  const cls = ["w-px h-[20px] bg-hair-2 flex-none", layout].filter(Boolean).join(" ");
  return <div className={cls} {...rest} />;
}
