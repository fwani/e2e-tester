/**
 * 겹쳐 뜨는 상세 판 — **모달이 아니다.** 017 T052 · **Base UI 이식 T104**.
 *
 * 출처: 015 — 정본 `.overlay-pane` 모양(`ui/Surface` 의 `OverlayPane`)에 `@base-ui/react` `Dialog` 의 동작을
 * 입혔다. shadcn 에 대응하는 부품이 없다 (`sheet` 는 모달이고 포털로 body 에 붙는다 — research R7).
 *
 * ## 무엇을 부품에게 맡기는가
 *
 * `Dialog` 를 `modal={false}` + `disablePointerDismissal` 로 쓴다.
 *
 * | 동작 | 누가 |
 * |---|---|
 * | 열리면 초점이 **판 자체**로 간다 | `Popup` 의 `initialFocus={판}` — 첫 조작(닫기)에 두면 그 툴팁이 판을 열 때마다 뜬다. 판에 초점이 가면 낭독기는 판의 이름(「STEP 상세」)을 먼저 읽고, Tab 한 번이 닫기다 |
 * | Esc 로 닫힌다 | 부품 (`onOpenChange` 의 이유 `escape-key`) |
 * | 닫히면 연 자리로 초점이 돌아간다 | `finalFocus` **기본값** — 트리거가 없어도 직전 초점으로 돌아온다(T104 실측). 수제 `useReturnFocus` 는 지웠다 |
 * | 역할 `dialog` · 제목과의 연결(`aria-labelledby`) | 부품 |
 * | **초점을 가두지 않는다** · 뒤쪽을 `aria-hidden` 으로 숨기지 않는다 | `modal={false}` |
 *
 * ## 바깥 클릭·바깥 초점은 닫힘이 아니다
 *
 * 판은 Step 목록 **옆에** 뜨고, 사용자는 판을 연 채 다른 행을 눌러 옮겨 간다(`DetailPlacement`). 비모달
 * 대화상자는 기본적으로 바깥 누름(`outside-press`)과 **초점 이탈**(`focus-out`)로 닫히므로, 그대로 두면
 * 행을 누르는 순간 판이 닫힌다. `disablePointerDismissal` 이 **둘 다** 막는다 (T104 실측 — 017 이
 * `onInteractOutside` 로 하던 일을 부품의 스위치 하나가 한다). 닫는 길은 판 안의 「닫기」와 Esc 둘이다.
 *
 * ## 자리는 부모가 정한다 — 그래서 포털을 **제자리로** 보낸다
 *
 * 판의 자리(목록 왼쪽 가장자리 · `Workbench` 의 가림막 안)는 007 배치 계약이다. Base UI 의 `Popup` 은
 * `Portal` 없이 그릴 수 없으므로(research S6 — 「`<Dialog.Portal>` is missing」), **`container` 로 제자리를
 * 가리킨다**: 판을 감싼 `display:contents` 상자를 호스트로 준다. 그러면 판은 `Workbench` 의 가림막 안에
 * 그대로 있고(`DetailPlacement`·`DetailBlocksMirrorInput` 이 재는 구조가 그대로다), 감싼 상자는 배치에
 * 끼어들지 않는다 — 가림막의 `flex justify-end` 에 대해 판이 여전히 flex 자식이다.
 *
 * `Viewport` 는 쓰지 않는다. 없는 부품을 알리는 오류는 `Root`·`Portal` 둘뿐이고(패키지 소스), 자리는
 * 이미 부모가 정하므로 마디를 늘릴 이유가 없다.
 */
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { useCallback, useRef, type ComponentPropsWithRef, type ReactNode } from "react";

import { cn } from "./cn";

type LayoutProps = { layout?: string; children?: ReactNode };

export function DetailPanel({
  onClose,
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Popup>, "className" | "initialFocus"> &
  LayoutProps & {
    /** Esc 나 판 안의 닫기 조작이 부른다. */
    onClose: () => void;
  }) {
  /*
    포털이 돌아올 자리. `display:contents` 라 배치에 끼어들지 않는다 (머리주석 「자리는 부모가 정한다」).

    **`useRef` 다 — 상태로 잡으면 판이 한 박자 늦게 열린다.** 처음에 `useState` 로 호스트를 잡고
    「호스트가 생긴 뒤에」 `Root` 를 그렸더니 마운트가 **두 번**이 되었고, 판이 열리는 순간
    `initialFocus` 가 초점을 판으로 가져갔다. 그 순간이 사용자가 **다른 칸에 글자를 치는 중**이면
    첫 글자만 들어가고 나머지를 판이 먹는다 — `AuthoringParity` 가 「지시문이 실리지 않았다:
    expected '장' to be '장바구니에 담아'」로 잡았다(2026-09-16). `Portal` 의 `container` 는
    **`RefObject` 를 받으므로**(설치된 타입) 한 번에 그리면 된다.
  */
  const host = useRef<HTMLDivElement | null>(null);
  const panel = useRef<HTMLDivElement | null>(null);
  const focused = useRef(false);

  /*
    **초점은 판이 DOM 에 붙는 그 순간, 한 번만 준다** (2026-09-16 · 실측으로 두 번 고쳐 얻은 모양).

    ① 부품의 `initialFocus={판}` 은 **때를 놓친다.** 팝업 참조가 아직 비어 있을 때 값을 읽어 아무 데도
       두지 않다가, 렌더가 더 도는 화면(EditView)에서는 **뒤늦게** 옮겼다. 그 늦은 이동이 사용자가
       옆 칸(「자연어로 Step 추가」)에 치던 글자를 가로챘다 — 첫 글자만 칸에 남았다.
       `AuthoringParity` 가 「expected '장' to be '장바구니에 담아'」로 잡았다.
    ② 마운트 효과로 옮기는 것도 **이르다.** 팝업은 포털을 거쳐 부품의 효과에서 붙으므로 부모의 효과가
       먼저 돈다 — 그때 `panel.current` 는 아직 `null` 이고, `?.` 때문에 조용히 아무 일도 안 했다
       (실측: 「부모 마운트 효과: panel.current=없다(null)」). 계약이 깨진 채로 통과할 뻔했다.

    그래서 **붙는 순간**에 건다. 요소가 생겨야 불리므로 이를 수 없고, 깃발이 있으니 늦게 다시 걸리지도
    않는다. 붙은 뒤의 초점은 아무도 뺏지 않는다(실측: 다음 틱에도 판에 남아 있다).
    `DialogFocus` 의 「상세 판의 초점」 두 검사가 이 계약의 양면을 못 박는다.
  */
  const attachPanel = useCallback((el: HTMLDivElement | null) => {
    panel.current = el;
    if (el === null || focused.current) return;
    focused.current = true;
    el.focus({ preventScroll: true });
  }, []);

  return (
    <div ref={host} className="contents" data-slot="detail-panel-host">
      <DialogPrimitive.Root
        open
        modal={false}
        disablePointerDismissal
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
      >
        <DialogPrimitive.Portal container={host} className="contents">
          <DialogPrimitive.Popup
            ref={attachPanel}
            // 초점은 **붙는 순간 위에서** 한 번만 준다 — 부품에게 맡기면 늦게 옮겨져 옆 칸의 입력을 가로챈다.
            initialFocus={false}
            // 정본 `.overlay-pane`. `shadow-e2` 는 `Toast` 와 같다 — 같은 층에 뜨는 것은 같은 높이다.
            className={cn("bg-panel border-l border-hair-2 shadow-e2", layout)}
            data-slot="detail-panel"
            // 설명 문단이 따로 없다 — 제목과 내용이 판 전체다. 부품이 설명을 찾지 않게 명시한다.
            aria-describedby={undefined}
            {...rest}
          >
            {children}
          </DialogPrimitive.Popup>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>
    </div>
  );
}

/** 판의 머리 문구 — 정본 `.pane-hd` 의 라벨 글자. 부품이 `<h2>` 로 그리므로 기본 여백·크기를 끊는다. */
export function DetailPanelTitle({
  layout,
  children,
  ...rest
}: Omit<ComponentPropsWithRef<typeof DialogPrimitive.Title>, "className"> & LayoutProps) {
  return (
    <DialogPrimitive.Title
      className={cn("m-0 font-sans text-[12px] font-semibold leading-[1.4] text-ink-2", layout)}
      data-slot="detail-panel-title"
      {...rest}
    >
      {children}
    </DialogPrimitive.Title>
  );
}
