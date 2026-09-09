/**
 * MirrorView 컴포넌트 테스트 (T088 · **010 T030 에서 방향을 바꿨다**).
 *
 * ## 무엇이 왜 뒤집혔나
 *
 * 001 은 여기에 이렇게 적었다 — 「FR-047a 를 UI 계층에서 고정한다: 읽기 전용 표시 영역은
 * 사용자 입력을 대상 브라우저로 전달하지 않는다. 나중에 누군가 «미러에서 바로 클릭하게 해
 * 달라»는 요청을 받아 핸들러를 붙이면 이 테스트가 먼저 실패한다.」
 *
 * 010 이 정확히 그 요청이다. 그리고 이 파일은 **의도한 대로 먼저 실패했다** — 그것이
 * 이 검증이 제 일을 했다는 증거다.
 *
 * **삭제하지 않는다** (헌법 품질 게이트 4). 지키려던 성질은 사라지지 않았고 조건이
 * 붙었다: 「전달하지 않는다」가 「**관찰 국면에서** 전달하지 않는다」가 된다. 판정은
 * 컴포넌트가 아니라 국면 × 조작 권한표가 하므로(FR-316), 이 파일은 **표가 준 판정을
 * 컴포넌트가 그대로 따르는지**를 본다.
 *
 * 지우는 것과 방향을 바꾸는 것은 다르다. 지우면 「미러는 아무 때나 조작을 받는다」로
 * 흘러가도 아무도 알려 주지 않는다.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MirrorView } from "../src/components/MirrorView";
import type { CapabilityState } from "../src/lib/capabilities";
import type { FrameGeometry } from "../src/components/mirror/useMirrorInput";

const FRAME = "AAAABBBBCCCC";

/** 표가 「쓸 수 있다」고 답한 경우 */
const ENABLED: CapabilityState = { kind: "enabled" };

/** 표가 「지금은 안 된다」고 답한 경우 — 관찰 국면이 그렇다 */
const DISABLED: CapabilityState = {
  kind: "disabled",
  reason: "실행을 멈춘 뒤에 할 수 있습니다",
  remedy: null,
};

const GEOMETRY: FrameGeometry = { width: 800, height: 600, pageScale: 1, offsetTop: 0 };

/**
 * jsdom 은 이미지를 디코드하지 않아 `naturalWidth` 가 0 이고 `getBoundingClientRect` 가
 * 전부 0 이다. 좌표 변환이 성립하려면 둘 다 필요하므로 여기서 심는다.
 *
 * 좌표 변환 자체의 정확성은 `MirrorInput.test.ts` 가 순수 함수로 잰다 — 이 파일이 재는
 * 것은 「국면이 조작 여부를 정하는가」이지 좌표가 아니다.
 */
/**
 * jsdom 은 `PointerEvent` 를 구현하지 않는다 — `fireEvent.pointerDown` 이 만드는 사건에
 * `clientX`·`button` 이 없고, React 는 그것을 `null` 로 넘긴다.
 *
 * **이것은 제품의 성질이 아니라 환경의 한계다.** 실제 브라우저에서는 좌표가 온다.
 * 폴리필을 두지 않으면 「조작 국면에서 전달한다」를 잴 수 없고, 재지 않으면 그 경로가
 * 깨져도 아무도 알려 주지 않는다.
 */
if (typeof window.PointerEvent === "undefined") {
  class PointerEventPolyfill extends MouseEvent {
    readonly pointerId: number;
    readonly pointerType: string;
    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init);
      this.pointerId = init.pointerId ?? 1;
      this.pointerType = init.pointerType ?? "mouse";
    }
  }
  // @ts-expect-error jsdom 에 없는 생성자를 심는다
  window.PointerEvent = PointerEventPolyfill;
}

function layoutImage(img: HTMLImageElement): void {
  Object.defineProperty(img, "naturalWidth", { value: 800, configurable: true });
  Object.defineProperty(img, "naturalHeight", { value: 600, configurable: true });
  img.getBoundingClientRect = () =>
    ({ left: 0, top: 0, width: 800, height: 600, right: 800, bottom: 600, x: 0, y: 0 }) as DOMRect;
}

describe("MirrorView", () => {
  it("프레임을 이미지로 그린다", () => {
    render(<MirrorView frame={FRAME} phase="observation" />);
    const img = screen.getByAltText("대상 브라우저 화면 (읽기 전용)") as HTMLImageElement;
    expect(img.src).toContain(`base64,${FRAME}`);
  });

  /* ─── 010 T030 — 방향을 바꾼 검증 ─────────────────────────────────── */

  it("**관찰 국면에서** 입력을 대상 브라우저로 전달하지 않는다 (FR-315 · 옛 FR-047a)", () => {
    const onInput = vi.fn();
    render(
      <MirrorView
        frame={FRAME}
        phase="observation"
        control={DISABLED}
        geometry={GEOMETRY}
        onInput={onInput}
      />,
    );
    const img = screen.getByAltText("대상 브라우저 화면 (읽기 전용)") as HTMLImageElement;
    layoutImage(img);

    fireEvent.pointerDown(img, { clientX: 10, clientY: 10, button: 0 });
    fireEvent.wheel(img, { clientX: 10, clientY: 10, deltaY: 100 });

    expect(onInput).not.toHaveBeenCalled();
    expect(img.getAttribute("draggable")).toBe("false");
  });

  it("표가 「안 된다」고 하면 그 이유를 화면에 남긴다 (SC-516 · FR-234)", () => {
    /*
      조용히 아무 일도 일어나지 않는 것이 SC-516 이 0건으로 두려는 상태다. 전달하지
      않는 것과 이유를 말하지 않는 것은 다르다.
    */
    const onBlocked = vi.fn();
    render(
      <MirrorView
        frame={FRAME}
        phase="observation"
        control={DISABLED}
        geometry={GEOMETRY}
        onBlockedAttempt={onBlocked}
      />,
    );
    const img = screen.getByAltText("대상 브라우저 화면 (읽기 전용)") as HTMLImageElement;
    layoutImage(img);
    fireEvent.pointerDown(img, { clientX: 10, clientY: 10, button: 0 });

    expect(onBlocked).toHaveBeenCalledWith("실행을 멈춘 뒤에 할 수 있습니다");
    expect(screen.getByText("실행을 멈춘 뒤에 할 수 있습니다")).toBeDefined();
  });

  it("조작 국면에서 표가 「된다」고 하면 전달한다 (FR-314)", () => {
    const onInput = vi.fn();
    render(
      <MirrorView
        frame={FRAME}
        phase="manipulation"
        control={ENABLED}
        geometry={GEOMETRY}
        onInput={onInput}
      />,
    );
    const img = screen.getByAltText("대상 브라우저 화면 (조작 가능)") as HTMLImageElement;
    layoutImage(img);
    fireEvent.pointerDown(img, { clientX: 400, clientY: 300, button: 0 });

    expect(onInput).toHaveBeenCalledTimes(1);
    expect(onInput.mock.calls[0]?.[0]).toMatchObject({
      kind: "pointer.down",
      x: 400,
      y: 300,
      button: "left",
    });
  });

  it("**컴포넌트가 스스로 국면을 보지 않는다** (FR-316)", () => {
    /*
      같은 `phase` 에 판정만 다르게 준다. 컴포넌트가 국면을 보고 스스로 정한다면 두
      경우가 같아야 하고, 표를 따른다면 갈려야 한다.

      이것이 research R9 가 세운 설계다 — 표 밖에 판정을 두면 둘이 갈리는 날 화면은 켤
      수 있다고 그리고 서버는 거절한다.
    */
    const allowed = vi.fn();
    const { unmount } = render(
      <MirrorView
        frame={FRAME}
        phase="observation"
        control={ENABLED}
        geometry={GEOMETRY}
        onInput={allowed}
      />,
    );
    const img = screen.getByAltText("대상 브라우저 화면 (조작 가능)") as HTMLImageElement;
    layoutImage(img);
    fireEvent.pointerDown(img, { clientX: 10, clientY: 10, button: 0 });
    expect(allowed).toHaveBeenCalledTimes(1);
    unmount();

    const refused = vi.fn();
    render(
      <MirrorView
        frame={FRAME}
        phase="manipulation"
        control={DISABLED}
        geometry={GEOMETRY}
        onInput={refused}
      />,
    );
    const img2 = screen.getByAltText("대상 브라우저 화면 (읽기 전용)") as HTMLImageElement;
    layoutImage(img2);
    fireEvent.pointerDown(img2, { clientX: 10, clientY: 10, button: 0 });
    expect(refused).not.toHaveBeenCalled();
  });

  it("조작 국면이어도 프레임이 없으면 전달하지 않는다 (FR-333)", () => {
    /*
      무엇을 클릭하는지 볼 수 없는 상태에서 좌표를 보내면 그것은 조작이 아니라 추측이다.
      서버도 같은 이유로 거절한다 (`control_channel.validate`).
    */
    const onInput = vi.fn();
    render(
      <MirrorView frame={null} phase="manipulation" control={ENABLED} onInput={onInput} />,
    );
    expect(screen.queryByAltText(/대상 브라우저 화면/)).toBeNull();
    expect(onInput).not.toHaveBeenCalled();
  });

  it("실제 창으로 전환한 동안에는 미러가 관찰용이라고 말한다 (FR-350 · M-05)", () => {
    /*
      **001 의 문구를 지우지 않았다.** 「실제 브라우저 창에서 조작 중 · 이 영역은
      관찰용이며 조작 대상이 아닙니다」는 이 상태에서 여전히 정확하다. 010 은 그 문구가
      참인 상태를 `window` 로 좁혔을 뿐이다.
    */
    const onInput = vi.fn();
    render(
      <MirrorView
        frame={FRAME}
        phase="manipulation"
        surface="window"
        control={ENABLED}
        geometry={GEOMETRY}
        onInput={onInput}
      />,
    );
    expect(screen.getByText(/실제 브라우저 창에서 조작 중/)).toBeDefined();
    expect(screen.getByText(/조작 대상이 아닙니다/)).toBeDefined();

    const img = screen.getByAltText("대상 브라우저 화면 (읽기 전용)") as HTMLImageElement;
    layoutImage(img);
    fireEvent.pointerDown(img, { clientX: 10, clientY: 10, button: 0 });
    expect(onInput).not.toHaveBeenCalled();
  });

  it("미러에서 조작하는 동안에는 그 사실을 말한다 (FR-319·FR-350)", () => {
    render(
      <MirrorView frame={FRAME} phase="manipulation" control={ENABLED} geometry={GEOMETRY} />,
    );
    expect(screen.getByText(/이 화면에서 조작합니다/)).toBeDefined();
    expect(screen.getByText(/대상 브라우저에 전달됩니다/)).toBeDefined();
    // 조작을 받는 자리인지가 눈으로 구분되어야 한다 (FR-319).
    expect(
      document.querySelector('[data-action="mirror.control"][data-controllable="true"]'),
    ).not.toBeNull();
  });

  it("일시정지에서는 세션이 유지되고 있음을 알린다 (FR-033)", () => {
    render(<MirrorView frame={FRAME} phase="paused" />);
    expect(screen.getByText("일시정지")).toBeDefined();
    expect(screen.getByText(/그대로 유지하고 있습니다/)).toBeDefined();
  });

  it("미러가 중단되면 사유를 보여주고 프레임을 그리지 않는다 (FR-047e)", () => {
    render(
      <MirrorView frame={FRAME} phase="terminated" stoppedReason="세션을 종료했습니다." />,
    );
    expect(screen.getByText("세션을 종료했습니다.")).toBeDefined();
    expect(screen.queryByAltText("대상 브라우저 화면 (읽기 전용)")).toBeNull();
  });

  it("스크린샷으로 강등되면 그 사실을 표시한다 (research R3 폴백)", () => {
    render(
      <MirrorView
        frame={FRAME}
        phase="observation"
        degradedReason="스크린캐스트를 시작할 수 없어 1초에 한 장으로 표시합니다."
      />,
    );
    expect(screen.getByText("1 FPS")).toBeDefined();
    expect(screen.getByText(/1초에 한 장으로 표시합니다/)).toBeDefined();
  });

  it("프레임이 아직 없으면 국면에 맞는 안내를 보여준다", () => {
    render(<MirrorView frame={null} phase="observation" />);
    // 005 FR-163 (U-24) — 문구가 사실에 맞게 바뀌었다. 기존 문구는 "기다리면 온다"고
    // 말했지만 정적 화면에서는 한 장도 오지 않았다(실측 0건). 단정은 그대로 —
    // 국면에 맞는 안내가 있는지 확인한다 (헌법 Quality Gate 4).
    expect(
      screen.getByText(/대상 화면이 표시되기를 기다리고 있습니다/),
    ).toBeDefined();
    /*
      010 T037 — **「창」을 말하지 않는다.** 창 없이 뜬 세션에서 그 문장은 거짓이고
      (FR-352), 거짓을 말하는 안내는 사용자를 없는 창을 찾게 만든다.
    */
    expect(screen.getByText(/대상 브라우저 세션은 이미 열려 있습니다/)).toBeDefined();
  });

  it("최초 탭이 아니면 어느 탭을 보고 있는지 알려 준다 (FR-030f)", () => {
    render(<MirrorView frame={FRAME} phase="observation" tabIndex={2} />);
    expect(screen.getByText(/탭 2/)).toBeDefined();
  });

  /* ─── 010 T089 — 끌어놓기가 미러 밖에서 끝나는 경우 (FR-318) ─────────── */

  it("**포인터를 붙잡는다** — 미러 밖에서 놓아도 놓음이 전달된다 (FR-318)", () => {
    /*
      붙잡지 않으면 누른 채 미러 밖으로 끌고 나가 놓았을 때 `pointerup` 이 이 요소로
      오지 않는다. 그러면 대상 페이지는 누른 상태로 남는다 — 서버가 채널을 닫을 때
      풀어 주지만 채널이 열려 있는 동안은 그대로다.

      목록에서 끌어 화면 밖으로 빼는 조작은 흔하고, 그때 사용자는 미러 밖에서 손을 뗀다.
    */
    const captured: number[] = [];
    render(
      <MirrorView
        frame={FRAME}
        phase="manipulation"
        control={ENABLED}
        geometry={GEOMETRY}
        onInput={vi.fn()}
      />,
    );
    const img = screen.getByAltText("대상 브라우저 화면 (조작 가능)") as HTMLImageElement;
    layoutImage(img);
    img.setPointerCapture = (id: number) => captured.push(id);
    img.hasPointerCapture = () => captured.length > 0;
    img.releasePointerCapture = () => captured.pop();

    fireEvent.pointerDown(img, { clientX: 100, clientY: 100, button: 0, pointerId: 7 });
    expect(captured, "포인터를 붙잡지 않았다").toContain(7);
  });

  it("포인터가 취소되면 **놓음을 보낸다** (FR-318)", () => {
    /*
      창이 가려지거나 다른 제스처가 시작되면 `pointerup` 없이 `pointercancel` 이 온다.
      그때도 놓지 않으면 대상 페이지가 누른 상태로 남는다.
    */
    const onInput = vi.fn();
    render(
      <MirrorView
        frame={FRAME}
        phase="manipulation"
        control={ENABLED}
        geometry={GEOMETRY}
        onInput={onInput}
      />,
    );
    const img = screen.getByAltText("대상 브라우저 화면 (조작 가능)") as HTMLImageElement;
    layoutImage(img);
    img.setPointerCapture = () => undefined;
    img.hasPointerCapture = () => true;
    img.releasePointerCapture = () => undefined;

    fireEvent.pointerDown(img, { clientX: 100, clientY: 100, button: 0, pointerId: 7 });
    onInput.mockClear();
    fireEvent.pointerCancel(img, { clientX: 120, clientY: 120, button: 0, pointerId: 7 });

    expect(onInput).toHaveBeenCalledTimes(1);
    expect(onInput.mock.calls[0]?.[0]).toMatchObject({ kind: "pointer.up" });
  });

  it("캡처를 잡을 수 없어도 조작은 전달된다", () => {
    /*
      `setPointerCapture` 가 없는 환경(오래된 브라우저·테스트 도구)에서 조작 자체가
      멈추면 안 된다. 미러 안에서 끝나는 끌어놓기는 캡처 없이도 동작한다.
    */
    const onInput = vi.fn();
    render(
      <MirrorView
        frame={FRAME}
        phase="manipulation"
        control={ENABLED}
        geometry={GEOMETRY}
        onInput={onInput}
      />,
    );
    const img = screen.getByAltText("대상 브라우저 화면 (조작 가능)") as HTMLImageElement;
    layoutImage(img);
    img.setPointerCapture = () => {
      throw new Error("이 환경에는 없다");
    };

    fireEvent.pointerDown(img, { clientX: 100, clientY: 100, button: 0, pointerId: 7 });
    expect(onInput).toHaveBeenCalledTimes(1);
    expect(onInput.mock.calls[0]?.[0]).toMatchObject({ kind: "pointer.down" });
  });
});
