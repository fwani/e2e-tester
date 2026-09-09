/**
 * 브라우저 요구 표시와 응답 (010 T071 · FR-338·FR-339 · SC-516).
 *
 * **이 화면이 없으면 대상 페이지가 멈춘 채로 남는다.** 대화상자는 응답이 올 때까지
 * 페이지를 세우고, 창이 없으면 그 사실이 어디에도 나타나지 않는다 — 사용자에게는
 * 「클릭했는데 아무 일도 없다」로 보인다.
 *
 * 그래서 재는 것이 셋이다.
 *
 * 1. 요구가 **보인다.** 종류마다 무엇을 고르는지가 화면에 있다.
 * 2. 고른 결과가 **나간다.** 취소도 응답이다 — 보내지 않으면 페이지가 계속 기다린다.
 * 3. 처리할 수 없는 요구에서 **남은 수단이 그 자리에 있다** (FR-353a).
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  BrowserPromptPanel,
  type BrowserPromptState,
} from "../src/components/BrowserPromptPanel";

const CONFIRM: BrowserPromptState = {
  promptId: "p_1",
  kind: "dialog.confirm",
  message: "이 항목을 삭제할까요?",
  blocking: true,
};

const FILE: BrowserPromptState = {
  promptId: "p_2",
  kind: "file.choose",
  message: "",
  multiple: false,
  blocking: false,
};

const UNSUPPORTED: BrowserPromptState = {
  promptId: "p_3",
  kind: "unsupported",
  message: "인증 요구 팝업입니다. 제품 화면이 대신 받을 수 없습니다. 실제 창에서 처리하세요.",
  blocking: false,
};

describe("브라우저 요구 표시 (FR-338)", () => {
  it("요구가 없으면 아무것도 그리지 않는다", () => {
    const { container } = render(
      <BrowserPromptPanel prompt={null} onAnswer={() => undefined} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("대화상자의 문구와 선택지를 보여 준다", () => {
    render(<BrowserPromptPanel prompt={CONFIRM} onAnswer={() => undefined} />);
    expect(screen.getByText("이 항목을 삭제할까요?")).toBeDefined();
    expect(screen.getByText(/확인을 요청합니다/)).toBeDefined();
    expect(document.querySelector("[data-prompt-accept]")).not.toBeNull();
    expect(document.querySelector("[data-prompt-dismiss]")).not.toBeNull();
  });

  it("**대상 페이지에서 온 문구를 그대로 실행하지 않는다** (contracts §4 · 헌법 보안 요건)", () => {
    /*
      `message` 는 대상 페이지가 정한다. HTML 로 그리면 대상 페이지가 제품 화면에
      마크업을 넣을 수 있다 — 외부 입력은 경계에서 검증한다는 요구가 여기 걸린다.

      React 가 텍스트 노드로 이스케이프하므로 `dangerouslySetInnerHTML` 을 쓰지 않는
      것으로 충분하다. 이 검증은 그것이 유지되는지를 본다.
    */
    const hostile: BrowserPromptState = {
      ...CONFIRM,
      message: "<img src=x onerror=alert(1)>주의",
    };
    const { container } = render(
      <BrowserPromptPanel prompt={hostile} onAnswer={() => undefined} />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x onerror=alert\(1\)>주의/)).toBeDefined();
  });

  it("문구가 비어 있어도 무엇을 고르는지 말한다", () => {
    /*
      대화상자의 문구는 대상 페이지가 정하고 비어 있을 수 있다. 그때 아무것도 그리지
      않으면 사용자는 무엇을 고르는지 모른 채 버튼 둘을 만난다.
    */
    render(<BrowserPromptPanel prompt={FILE} onAnswer={() => undefined} />);
    expect(screen.getByText(/파일을 고르면 대상 브라우저에 전달됩니다/)).toBeDefined();
  });

  it("입력 요구에는 입력칸이 있다", () => {
    render(
      <BrowserPromptPanel
        prompt={{ ...CONFIRM, kind: "dialog.prompt" }}
        onAnswer={() => undefined}
      />,
    );
    expect(document.querySelector("[data-prompt-text]")).not.toBeNull();
  });

  it("페이지를 세우는 요구는 그 사실을 보조 기술에 알린다", () => {
    /*
      `blocking` 은 「응답이 없으면 대상 페이지가 멈춘다」는 뜻이다. 화면을 보지 않는
      사용자에게도 그 긴급함이 전달되어야 한다.
    */
    render(<BrowserPromptPanel prompt={CONFIRM} onAnswer={() => undefined} />);
    expect(screen.getByRole("alertdialog")).toBeDefined();

    render(<BrowserPromptPanel prompt={FILE} onAnswer={() => undefined} />);
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });
});

describe("응답 (FR-338 · SC-517)", () => {
  it("확인을 누르면 수락이 나간다", () => {
    const onAnswer = vi.fn();
    render(<BrowserPromptPanel prompt={CONFIRM} onAnswer={onAnswer} />);
    fireEvent.click(document.querySelector("[data-prompt-accept]")!);
    expect(onAnswer).toHaveBeenCalledWith(expect.objectContaining({ accept: true }));
  });

  it("**취소도 응답이다** — 보내지 않으면 대상 페이지가 계속 기다린다 (FR-339)", () => {
    const onAnswer = vi.fn();
    render(<BrowserPromptPanel prompt={CONFIRM} onAnswer={onAnswer} />);
    fireEvent.click(document.querySelector("[data-prompt-dismiss]")!);
    expect(onAnswer).toHaveBeenCalledWith(expect.objectContaining({ accept: false }));
  });

  it("입력한 값이 함께 나간다", () => {
    const onAnswer = vi.fn();
    render(
      <BrowserPromptPanel
        prompt={{ ...CONFIRM, kind: "dialog.prompt" }}
        onAnswer={onAnswer}
      />,
    );
    const input = document.querySelector("[data-prompt-text]") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "주문 내역" } });
    fireEvent.click(document.querySelector("[data-prompt-accept]")!);
    expect(onAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ accept: true, text: "주문 내역" }),
    );
  });

  it("파일을 고르기 전에는 보낼 수 없다", () => {
    /*
      빈 목록을 「보내기」로 내보내면 사용자는 파일을 보냈다고 믿고 대상 페이지는
      아무것도 받지 않는다. 고르지 않겠다는 선택은 「취소」다.
    */
    render(<BrowserPromptPanel prompt={FILE} onAnswer={() => undefined} />);
    const accept = document.querySelector("[data-prompt-accept]") as HTMLButtonElement;
    expect(accept.disabled).toBe(true);
  });

  it("고른 파일이 응답에 실린다 (FR-337)", () => {
    const onAnswer = vi.fn();
    render(<BrowserPromptPanel prompt={FILE} onAnswer={onAnswer} />);
    const picker = document.querySelector("[data-prompt-file]") as HTMLInputElement;
    const file = new File(["a,b"], "주문내역.csv", { type: "text/csv" });
    fireEvent.change(picker, { target: { files: [file] } });

    const accept = document.querySelector("[data-prompt-accept]") as HTMLButtonElement;
    expect(accept.disabled).toBe(false);
    fireEvent.click(accept);
    expect(onAnswer).toHaveBeenCalledWith(
      expect.objectContaining({ accept: true, files: [file] }),
    );
  });
});

describe("처리할 수 없는 요구 (FR-339 · FR-353a)", () => {
  it("무엇이 막혔는지 말한다 — 조용히 넘어가지 않는다 (SC-516)", () => {
    render(<BrowserPromptPanel prompt={UNSUPPORTED} onAnswer={() => undefined} />);
    expect(screen.getByText(/대신 받을 수 없는 요구입니다/)).toBeDefined();
    expect(screen.getByText(/인증 요구 팝업입니다/)).toBeDefined();
  });

  it("**전환 수단이 그 자리에 있다** (FR-353a)", () => {
    /*
      무엇이 막혔는지 읽은 자리에서 바로 전환할 수 있어야 한다. 사실만 말하고 수단을
      다른 곳에 두면 사용자는 읽은 자리에서 할 수 있는 일이 없다.
    */
    const onUseWindow = vi.fn();
    render(
      <BrowserPromptPanel
        prompt={UNSUPPORTED}
        onAnswer={() => undefined}
        onUseWindow={onUseWindow}
        canUseWindow
      />,
    );
    const button = document.querySelector("[data-prompt-use-window]") as HTMLButtonElement;
    expect(button).not.toBeNull();
    fireEvent.click(button);
    expect(onUseWindow).toHaveBeenCalled();
  });

  it("전환할 수 없는 환경에서는 그 버튼을 그리지 않는다 (FR-351)", () => {
    /*
      누를 수 없는 수단을 보여 주면 사용자는 그것을 시도하고 다시 거절당한다. 창을
      띄울 수 없는 환경에서는 남은 수단이 미러뿐이고, 그 사실은 서버가 사유로 말한다.
    */
    render(
      <BrowserPromptPanel
        prompt={UNSUPPORTED}
        onAnswer={() => undefined}
        canUseWindow={false}
      />,
    );
    expect(document.querySelector("[data-prompt-use-window]")).toBeNull();
  });

  it("처리할 수 없는 요구에는 확인·취소를 두지 않는다", () => {
    /*
      고를 것이 없는데 선택지를 그리면 사용자는 누르고, 아무 일도 일어나지 않는다 —
      그것이 SC-516 이 0건으로 두려는 조용한 실패다.
    */
    render(<BrowserPromptPanel prompt={UNSUPPORTED} onAnswer={() => undefined} />);
    expect(document.querySelector("[data-prompt-accept]")).toBeNull();
    expect(document.querySelector("[data-prompt-dismiss]")).toBeNull();
  });
});
