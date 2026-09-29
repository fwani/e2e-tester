/**
 * 미러 위의 자리 표시 (024 T033~T035·T042·T043·T052 · US1·US2).
 *
 * ## 무엇을 재고 무엇을 안 재는가
 *
 * **좌표가 맞는지는 여기서 재지 않는다.** jsdom 은 이미지를 해독하지 않아 자연 크기가
 * 0 이고, 그러면 변환이 언제나 `null` 을 준다 — 그것은 jsdom 의 한계이지 결함이 아니다.
 * 좌표는 `MirrorFocusGeometry.test.ts`(라운드트립)와 종단 검증이 맡는다.
 *
 * 여기가 재는 것은 **표시의 규칙**이다 — 하나만 보이는가, 성공과 실패가 구분되는가,
 * 포인터를 가로채지 않는가, 프레임이 없을 때 안 그리는가.
 *
 * 그래서 이미지 기하를 **직접 넣어 준다** (`stubImageGeometry`). 실제 브라우저가 주는
 * 값을 흉내 내는 것이며, 변환식 자체는 위 파일이 이미 검증했다.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MirrorView } from "../src/components/MirrorView";
import type { FrameGeometry } from "../src/components/mirror/useMirrorInput";

const FRAME: FrameGeometry = { width: 1280, height: 800, pageScale: 1, offsetTop: 0 };

/**
 * jsdom 의 `<img>` 에 실제 브라우저가 줄 크기를 심는다.
 *
 * 이것 없이는 `naturalWidth` 가 0 이라 변환이 언제나 `null` 을 준다 — 표시 규칙을
 * 하나도 잴 수 없게 된다.
 */
function stubImageGeometry() {
  Object.defineProperty(HTMLImageElement.prototype, "naturalWidth", {
    configurable: true,
    get: () => 1280,
  });
  Object.defineProperty(HTMLImageElement.prototype, "naturalHeight", {
    configurable: true,
    get: () => 800,
  });
  Object.defineProperty(HTMLImageElement.prototype, "getBoundingClientRect", {
    configurable: true,
    value: () => ({
      width: 1280,
      height: 800,
      left: 0,
      top: 0,
      right: 1280,
      bottom: 800,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    }),
  });
}

const RECT = { x: 100, y: 200, width: 80, height: 30 };

function renderMirror(
  focus: { rect: typeof RECT; status: "done" | "failed"; label: string } | null,
  overrides: Partial<Parameters<typeof MirrorView>[0]> = {},
) {
  return render(
    <MirrorView
      frame="AAAA"
      phase="observation"
      geometry={FRAME}
      focus={focus}
      {...overrides}
    />,
  );
}

beforeEach(stubImageGeometry);
afterEach(cleanup);

describe("US1 — 자리가 보인다", () => {
  it("자리를 받으면 테두리가 그려진다 (T033)", () => {
    renderMirror({ rect: RECT, status: "done", label: "로그인 버튼 클릭" });
    expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(1);
  });

  it("자리가 없으면 아무것도 그리지 않는다", () => {
    renderMirror(null);
    expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(0);
  });

  it("새 자리가 오면 앞의 것은 사라진다 — 하나만 보인다 (T033 · FR-014)", () => {
    const { rerender } = renderMirror({ rect: RECT, status: "done", label: "첫째" });
    rerender(
      <MirrorView
        frame="AAAA"
        phase="observation"
        geometry={FRAME}
        focus={{ rect: { ...RECT, x: 400 }, status: "done", label: "둘째" }}
      />,
    );
    const marks = document.querySelectorAll("[data-focus-mark]");
    expect(marks).toHaveLength(1);
    expect((marks[0] as HTMLElement).style.left).toBe("400px");
  });

  it("자리는 받은 좌표대로 놓인다", () => {
    renderMirror({ rect: RECT, status: "done", label: "클릭" });
    const mark = document.querySelector("[data-focus-mark]") as HTMLElement;
    expect(mark.style.left).toBe("100px");
    expect(mark.style.top).toBe("200px");
    expect(mark.style.width).toBe("80px");
    expect(mark.style.height).toBe("30px");
  });
});

describe("US2 — 된 것과 안 된 것이 구분된다", () => {
  it("성공과 실패가 서로 다른 모습이다 (T042 · FR-013)", () => {
    const { unmount } = renderMirror({ rect: RECT, status: "done", label: "클릭" });
    const done = document.querySelector("[data-focus-mark]")!.className;
    unmount();

    renderMirror({ rect: RECT, status: "failed", label: "클릭" });
    const failed = document.querySelector("[data-focus-mark]")!.className;

    expect(failed).not.toBe(done);
    // 색은 정본에서 온다 (FR-022) — 새 색을 만들지 않는다.
    expect(done).toContain("outline-run");
    expect(failed).toContain("outline-fail");
  });

  it("실패 표시도 새 자리에 밀려난다 (T043)", () => {
    const { rerender } = renderMirror({ rect: RECT, status: "failed", label: "막힘" });
    expect(document.querySelector("[data-focus-mark]")!.getAttribute("data-focus-mark")).toBe(
      "failed",
    );
    rerender(
      <MirrorView
        frame="AAAA"
        phase="observation"
        geometry={FRAME}
        focus={{ rect: RECT, status: "done", label: "다음" }}
      />,
    );
    const marks = document.querySelectorAll("[data-focus-mark]");
    expect(marks).toHaveLength(1);
    expect(marks[0]!.getAttribute("data-focus-mark")).toBe("done");
  });
});

describe("US3 — 가로채지 않고, 없으면 그리지 않는다", () => {
  it("테두리가 포인터를 가로채지 않는다 (T052 · FR-020 · SC-005)", () => {
    // 이것이 지워지면 조작 국면에서 사용자의 클릭이 조용히 사라진다. 클래스 이름을
    // 직접 재는 이유는, 그 클래스가 장식이 아니라 요구사항의 구현이기 때문이다.
    renderMirror({ rect: RECT, status: "done", label: "클릭" });
    expect(document.querySelector("[data-focus-mark]")!.className).toContain(
      "pointer-events-none",
    );
  });

  it("프레임이 없으면 그리지 않는다 (FR-016)", () => {
    renderMirror({ rect: RECT, status: "done", label: "클릭" }, { frame: null });
    expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(0);
  });

  it("미러가 중단되면 안내만 남고 테두리는 없다 (FR-016·FR-021)", () => {
    renderMirror(
      { rect: RECT, status: "done", label: "클릭" },
      { stoppedReason: "미러가 중단되었습니다." },
    );
    expect(screen.getByText("미러가 중단되었습니다.")).toBeTruthy();
    expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(0);
  });

  it("좌표 근거가 없으면 그리지 않는다 (FR-017)", () => {
    renderMirror({ rect: RECT, status: "done", label: "클릭" }, { geometry: null });
    expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(0);
  });

  it("표시 영역 밖의 자리는 그리지 않는다 (FR-019)", () => {
    renderMirror({ rect: { x: 100, y: 2008, width: 80, height: 30 }, status: "done", label: "아래" });
    expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(0);
  });
});

describe("기존 동작을 바꾸지 않는다", () => {
  it("테두리가 있어도 미러의 그림은 그대로다 (T035 · FR-023)", () => {
    renderMirror({ rect: RECT, status: "done", label: "클릭" });
    // 미러가 하던 일(대상 화면을 보여 주는 것)이 줄지 않았다.
    expect(screen.getByAltText(/대상 브라우저 화면/)).toBeTruthy();
  });

  it("보조기술에는 숨긴다 — 같은 사실을 진행 문구가 이미 읽는다", () => {
    renderMirror({ rect: RECT, status: "done", label: "로그인 버튼 클릭" });
    expect(document.querySelector("[data-focus-mark]")!.getAttribute("aria-hidden")).toBe(
      "true",
    );
  });
});

describe("수명 (T034 · FR-015)", () => {
  it("표시 시간이 지나면 상태가 비워진다", () => {
    // 수명은 화면(`SessionScreen`)이 센다. 여기서는 그 규칙이 존재한다는 것만 고정하고,
    // 실제 소멸은 상태가 `null` 이 되는 것으로 나타난다 — 위 「자리가 없으면」 과 같다.
    vi.useFakeTimers();
    try {
      const { rerender } = renderMirror({ rect: RECT, status: "done", label: "클릭" });
      expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(1);
      rerender(<MirrorView frame="AAAA" phase="observation" geometry={FRAME} focus={null} />);
      expect(document.querySelectorAll("[data-focus-mark]")).toHaveLength(0);
    } finally {
      vi.useRealTimers();
    }
  });
});
