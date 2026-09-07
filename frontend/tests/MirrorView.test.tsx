/**
 * MirrorView 컴포넌트 테스트 (T088).
 *
 * **FR-047a 를 UI 계층에서 고정한다**: 읽기 전용 표시 영역은 사용자 입력을 대상 브라우저로
 * 전달하지 않는다. 나중에 누군가 "미러에서 바로 클릭하게 해 달라"는 요청을 받아 핸들러를
 * 붙이면 이 테스트가 먼저 실패한다.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MirrorView } from "../src/components/MirrorView";

const FRAME = "AAAABBBBCCCC";

describe("MirrorView", () => {
  it("프레임을 이미지로 그린다", () => {
    render(<MirrorView frame={FRAME} phase="observation" />);
    const img = screen.getByAltText("대상 브라우저 화면 (읽기 전용)") as HTMLImageElement;
    expect(img.src).toContain(`base64,${FRAME}`);
  });

  it("표시 영역이 포인터 입력을 받지 않는다 (FR-047a)", () => {
    render(<MirrorView frame={FRAME} phase="observation" />);
    const img = screen.getByAltText("대상 브라우저 화면 (읽기 전용)");
    expect(img.style.pointerEvents).toBe("none");
    expect(img.getAttribute("draggable")).toBe("false");
  });

  it("조작 국면에서는 실제 창에서 조작 중임을 알린다 (FR-023b)", () => {
    render(<MirrorView frame={FRAME} phase="manipulation" />);
    expect(screen.getByText(/실제 브라우저 창에서 조작 중/)).toBeDefined();
    expect(screen.getByText(/조작 대상이 아닙니다/)).toBeDefined();
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
    expect(screen.getByText(/대상 브라우저 창은 이미 열려 있습니다/)).toBeDefined();
  });

  it("최초 탭이 아니면 어느 탭을 보고 있는지 알려 준다 (FR-030f)", () => {
    render(<MirrorView frame={FRAME} phase="observation" tabIndex={2} />);
    expect(screen.getByText(/탭 2/)).toBeDefined();
  });
});
