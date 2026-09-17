/**
 * jsdom 환경 보완 — 한 곳에서 채운다. 017 research R10 · T008.
 *
 * ## 이것은 제품의 성질이 아니라 환경의 한계다
 *
 * jsdom 25 에는 브라우저가 늘 가진 API 몇 개가 없다. 017 이 들인 `radix-ui` 부품은 그것을
 * 부르고, 없으면 **부품이 아니라 환경 때문에** 예외를 던진다 (조사 실측 — vitest 2.1 ·
 * jsdom 25 · React 19).
 *
 * | API | 부르는 것 | 없으면 |
 * |---|---|---|
 * | `ResizeObserver` | `Tooltip` 화살표 · 떠 있는 내용의 크기 추적 | 툴팁을 여는 순간 예외 |
 * | `IntersectionObserver` | 떠 있는 내용의 자리 추적(기준 요소가 화면에서 움직였는가) | 툴팁·메뉴가 열리다 멈춘다 |
 * | `PointerEvent` | `DropdownMenu` 트리거(pointerdown 의 `button`) | `fireEvent.pointerDown` 이 `button` 없는 사건을 만든다 |
 * | `has/set/releasePointerCapture` | 누르고 끄는 조작 | 호출 즉시 `is not a function` |
 * | `scrollIntoView` | 메뉴·목록이 고른 항목을 보이게 한다 | 키보드 이동 시 예외 |
 * | `matches(':popover-open')`·`matches(':modal')` | 떠 있는 내용의 자리 계산(floating-ui `isTopLayer`) | **예외가 아니라 느려진다** — 아래 절 |
 *
 * **이미 있는 것은 덮지 않는다.** 모든 줄이 「없을 때만」 심는다. 테스트가 요소 하나에
 * 따로 심은 대역(`MirrorView.test.tsx` 의 포인터 캡처 등)은 인스턴스 속성이라 그대로 이긴다.
 * `PointerEvent` 도 `MirrorView.test.tsx:63` 의 지역 폴리필과 같은 형태이며, 그쪽 역시
 * 없을 때만 심으므로 둘이 부딪치지 않는다.
 *
 * **동작을 흉내 내지 않는다.** `ResizeObserver` 는 아무것도 관찰하지 않고, 캡처 함수는
 * 캡처하지 않는다. jsdom 은 배치를 계산하지 않으므로 흉내 낼 값이 애초에 없다 — 크기와
 * 자리는 화면 순회(chromium)가 잰다 (screen-sweep.md).
 *
 * ## 최상위 층 의사 클래스 — 틀린 답이 아니라 **느린 답**이었다 (017 T056)
 *
 * floating-ui 는 떠 있는 내용의 자리를 계산할 때 조상마다 `el.matches(':popover-open')`·`el.matches(':modal')`
 * 로 최상위 층(top layer)에 있는지 묻는다. jsdom 의 선택자 엔진은 이 둘을 모르지만 **예외를 던지지 않고** 한 번에
 * 약 150ms 를 쓴 뒤 거짓을 돌려준다. 실측(2026-09-15 · jsdom 25 · floating-ui 1.8):
 *
 * | | 시간 |
 * |---|---|
 * | `matches` 두 선택자 × 100회 | 30.6초 |
 * | `computePosition` 한 번 (그대로) | 5.8초 |
 * | `computePosition` 한 번 (두 선택자만 바로 거짓) | 1ms |
 *
 * 그래서 Radix 메뉴·툴팁 하나를 여는 검사가 2~10초씩 걸려 기본 제한(5초)을 넘었다 (Foundational 스파이크의
 * 「툴팁이 열리는 데 8초」가 이것이었다). jsdom 에는 최상위 층이 없으므로 **두 선택자에 맞는 요소는 있을 수 없다** —
 * 거짓을 바로 돌려주는 것은 흉내가 아니라 jsdom 이 느리게 내던 같은 답이다. 다른 선택자는 원래 함수가 받는다.
 */

if (typeof window !== "undefined") {
  if (typeof window.ResizeObserver === "undefined") {
    class ResizeObserverStub implements ResizeObserver {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    }
    window.ResizeObserver = ResizeObserverStub;
  }

  if (typeof window.IntersectionObserver === "undefined") {
    class IntersectionObserverStub implements IntersectionObserver {
      readonly root = null;
      readonly rootMargin = "0px";
      readonly thresholds: readonly number[] = [0];
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
      takeRecords(): IntersectionObserverEntry[] {
        return [];
      }
    }
    window.IntersectionObserver = IntersectionObserverStub;
  }

  if (typeof window.PointerEvent === "undefined") {
    class PointerEventPolyfill extends MouseEvent {
      readonly pointerId: number;
      readonly pointerType: string;
      readonly isPrimary: boolean;
      constructor(type: string, init: PointerEventInit = {}) {
        super(type, init);
        this.pointerId = init.pointerId ?? 1;
        this.pointerType = init.pointerType ?? "mouse";
        this.isPrimary = init.isPrimary ?? true;
      }
    }
    // @ts-expect-error jsdom 에 없는 생성자를 심는다
    window.PointerEvent = PointerEventPolyfill;
  }

  const proto = Element.prototype as Element & {
    hasPointerCapture?: (id: number) => boolean;
    setPointerCapture?: (id: number) => void;
    releasePointerCapture?: (id: number) => void;
    scrollIntoView?: (arg?: boolean | ScrollIntoViewOptions) => void;
  };
  if (typeof proto.hasPointerCapture !== "function") proto.hasPointerCapture = () => false;
  if (typeof proto.setPointerCapture !== "function") proto.setPointerCapture = () => {};
  if (typeof proto.releasePointerCapture !== "function") proto.releasePointerCapture = () => {};
  if (typeof proto.scrollIntoView !== "function") proto.scrollIntoView = () => {};

  // 머리주석 「최상위 층 의사 클래스」. 한 번만 감싼다 — 설정 파일이 여러 번 실행돼도 겹겹이 감싸지 않는다.
  const TOP_LAYER = new Set([":popover-open", ":modal"]);
  const marked = Element.prototype.matches as typeof Element.prototype.matches & { __topLayerShortcut?: true };
  if (marked.__topLayerShortcut !== true) {
    const original = Element.prototype.matches;
    const matches = function (this: Element, selectors: string): boolean {
      return TOP_LAYER.has(selectors) ? false : original.call(this, selectors);
    } as typeof Element.prototype.matches & { __topLayerShortcut?: true };
    matches.__topLayerShortcut = true;
    Element.prototype.matches = matches;
  }
}
