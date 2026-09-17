/**
 * 대화상자·확인 대화상자의 **초점** (017 T049 · FR-011 · SC-009).
 *
 * 017 전 대화상자는 `role="dialog"` 를 단 `<div>` 였다. 보조기술에는 대화상자라고 말했지만 초점은 뒤쪽에 남았고,
 * Tab 은 가림막 뒤의 조작으로 나갔으며, Esc 는 아무 일도 하지 않았다. 이 파일은 부품(`ui/Dialog`·`ui/AlertDialog`)이
 * 그 넷을 지키는지 본다 — 화면마다 다시 재지 않도록 부품 단위로.
 *
 * ## 닫힌 뒤 초점이 **연 조작**으로 돌아오는가
 *
 * Radix 는 닫힐 때 `Trigger` 로 초점을 보낸다. 이 제품의 대화상자는 트리거 없이 화면 상태로 열리므로 보낼 곳이
 * 비어 있다 — 부품이 연 자리를 기억해 돌려준다(`useReturnFocus`). 트리거 없이 여는 것이 이 제품의 형태이므로
 * 여기서도 **트리거 없이** 연다.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "../src/ui/AlertDialog";
import { Button } from "../src/ui/Button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from "../src/ui/Dialog";
import { Input } from "../src/ui/Input";
import { DetailPanel, DetailPanelTitle } from "../src/ui/OverlayPane";

afterEach(cleanup);

/** 화면이 여는 형태 그대로 — 상태가 참일 때만 그린다 (`SessionScreen` 의 `{confirming && <…/>}`). */
function NameDialogScreen() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>이름 정하기</Button>
      <Button>뒤쪽 조작</Button>
      {open && (
        <Dialog open onOpenChange={(next) => (next ? undefined : setOpen(false))}>
          <DialogContent>
            <DialogTitle>이름을 정합니다</DialogTitle>
            <DialogDescription>저장할 이름을 적습니다.</DialogDescription>
            <Input aria-label="테스트 이름" />
            <DialogFooter>
              <Button onClick={() => setOpen(false)}>돌아가기</Button>
              <Button>저장</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}

function CloseConfirmScreen({ onConfirm }: { onConfirm: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>닫기</Button>
      {open && (
        <AlertDialog open onOpenChange={(next) => (next ? undefined : setOpen(false))}>
          <AlertDialogContent>
            <AlertDialogTitle>실행 화면을 닫습니다</AlertDialogTitle>
            <AlertDialogDescription>결과는 목록에서 다시 볼 수 있습니다.</AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogCancel>돌아가기</AlertDialogCancel>
              <Button variant="danger" onClick={onConfirm}>
                닫기
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </>
  );
}

describe("대화상자 (ui/Dialog)", () => {
  it("열면 초점이 대화상자 안으로 간다", async () => {
    const user = userEvent.setup();
    render(<NameDialogScreen />);
    await user.click(screen.getByRole("button", { name: "이름 정하기" }));

    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(dialog.contains(document.activeElement), "초점이 뒤쪽에 남았다").toBe(true));
  });

  it("열린 동안 뒤쪽 조작은 보조기술에서 가려진다", async () => {
    const user = userEvent.setup();
    render(<NameDialogScreen />);
    await user.click(screen.getByRole("button", { name: "이름 정하기" }));
    await screen.findByRole("dialog");

    expect(screen.queryByRole("button", { name: "뒤쪽 조작" }), "대화상자 뒤의 조작이 낭독 대상에 남았다").toBeNull();
  });

  it("Tab 이 대화상자 밖으로 나가지 않는다", async () => {
    const user = userEvent.setup();
    render(<NameDialogScreen />);
    await user.click(screen.getByRole("button", { name: "이름 정하기" }));
    const dialog = await screen.findByRole("dialog");
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    /*
      **판정 방법을 옮겼다 — jsdom 이 `inert` 를 구현하지 않기 때문이다** (T104 · test-ledger 09-16).

      Radix 는 초점이 나가려 하면 **그 자리에서** 되돌렸다. Base UI 는 두 장치로 가둔다: 팝업 옆의
      **초점 울타리**(`<span tabindex=0 data-base-ui-focus-guard>`)와, 열린 동안 바깥에 거는
      `aria-hidden`+`data-base-ui-inert` 다. 실제 브라우저에서 `inert` 안의 조작은 **Tab 순서에서
      빠지므로** 닿을 수 없다. jsdom 은 `inert` 를 무시해 그 조작이 순서에 남고, 울타리의 되돌림도
      한 틱 뒤에 온다 — 실측(T104): Tab 3 회에 울타리 `span`(포털 안), 4 회에 `body`, 5 회에 연 단추에
      앉았다가 **한 틱 뒤 팝업 안으로 되돌아왔다.**

      그래서 묻는 것을 그대로 두고 범위만 정확히 적는다: **초점이 「살아 있는」 뒤쪽 조작에 앉지
      않는다.** 팝업 안 · 울타리 · `inert` 로 덮인 것 · `body` 는 사용자가 닿을 수 있는 조작이 아니다.
      가려짐 자체는 바로 위 검사(「뒤쪽 조작은 보조기술에서 가려진다」)가 따로 못 박는다.
    */
    // 칸 · 돌아가기 · 저장 — 세 번을 넘겨 한 바퀴 이상 돈다.
    for (let i = 0; i < 5; i += 1) {
      await user.tab();
      const el = document.activeElement as HTMLElement;
      const reachable = !dialog.contains(el) && el !== document.body && el.closest("[data-base-ui-inert]") === null;
      expect(reachable, `Tab ${i + 1}회에 초점이 살아 있는 뒤쪽 조작으로 나갔다: ${el.textContent?.trim()}`).toBe(false);
    }
  });

  it("Esc 로 닫히고, 초점이 연 조작으로 돌아온다", async () => {
    const user = userEvent.setup();
    render(<NameDialogScreen />);
    const opener = screen.getByRole("button", { name: "이름 정하기" });
    await user.click(opener);
    await screen.findByRole("dialog");

    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.activeElement, "초점이 문서 처음으로 떨어졌다").toBe(opener));
  });
});

describe("확인 대화상자 (ui/AlertDialog)", () => {
  it("열면 초점이 되돌리는 조작(「돌아가기」)에 앉는다 — 위험한 조작이 아니다", async () => {
    const user = userEvent.setup();
    render(<CloseConfirmScreen onConfirm={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "닫기" }));

    const dialog = await screen.findByRole("alertdialog");
    await waitFor(() =>
      expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "돌아가기" })),
    );
  });

  it("Esc 는 조작을 실행하지 않고 닫는다 · 초점이 연 조작으로 돌아온다", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<CloseConfirmScreen onConfirm={onConfirm} />);
    const opener = screen.getByRole("button", { name: "닫기" });
    await user.click(opener);
    await screen.findByRole("alertdialog");

    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(onConfirm, "Esc 가 되돌릴 수 없는 조작을 실행했다").not.toHaveBeenCalled();
    await waitFor(() => expect(document.activeElement).toBe(opener));
  });

  it("가림막을 눌러도 닫히지 않는다 — 되돌릴 수 없는 선택을 실수로 넘기지 않는다", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(<CloseConfirmScreen onConfirm={onConfirm} />);
    await user.click(screen.getByRole("button", { name: "닫기" }));
    await screen.findByRole("alertdialog");

    const overlay = document.querySelector('[data-slot="alert-dialog-overlay"]');
    /*
      **판정 방법만 옮겼다** (T104 · test-ledger 09-16). 열림을 말하는 표식이 `data-state="open"` 에서
      **`data-open`**(값 없는 속성)으로 바뀌었다 — 묻는 것은 그대로다: 가림막이 열려 있는가, 그것을
      누른 뒤에도 확인 창이 열려 있는가.
    */
    expect(overlay?.hasAttribute("data-open"), "열린 가림막을 찾지 못했다").toBe(true);
    await user.click(overlay as HTMLElement);

    expect(screen.getByRole("alertdialog").hasAttribute("data-open"), "확인 대화상자가 닫혔다").toBe(true);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});

function within(el: HTMLElement) {
  return {
    getByRole: (role: string, options: { name: string }) =>
      screen.getAllByRole(role, options).find((node) => el.contains(node)) as HTMLElement,
  };
}

/**
 * 상세 판의 초점 — **T104 에서 아무도 붙잡고 있지 않다는 것을 알았다.**
 *
 * 「열리면 초점이 판 자체로 간다」는 `ui/OverlayPane` 머리주석과 ui-parts §1-2 에 적힌 계약인데,
 * 검사가 없어서 갈래를 옮기며 **조용히 사라질 수 있었다.** 실제로 그 자리에서 회귀를 하나 만들었다 —
 * 부품의 `initialFocus` 가 초점을 늦게 옮겨 **옆 칸에 치던 글자를 판이 가로챘다**(`AuthoringParity` 가
 * 잡았다). 그래서 계약의 **두 면을 여기서 못 박는다**: 판은 초점을 가져오고, 남의 입력은 먹지 않는다.
 */
describe("상세 판의 초점 (ui/OverlayPane · T104)", () => {
  it("열리면 초점이 판 자체로 간다 — 첫 조작(닫기)이 아니다", async () => {
    render(
      <div data-workbench-detail-layer>
        <DetailPanel onClose={() => undefined} layout="w-detail">
          <DetailPanelTitle>STEP 상세</DetailPanelTitle>
          <Button>닫기</Button>
        </DetailPanel>
      </div>,
    );
    const panel = document.querySelector("[data-slot=detail-panel]") as HTMLElement;
    /*
      **판 자체**여야 한다. 첫 조작(닫기)에 두면 그 툴팁이 판을 열 때마다 뜨고, 낭독기는 판의 이름
      (「STEP 상세」)을 읽지 않는다 (`ui/OverlayPane` 머리주석의 표).
    */
    await waitFor(() => expect(document.activeElement, "초점이 판으로 오지 않았다").toBe(panel));
  });

  it("판이 열려 있어도 **옆 칸**의 입력을 가로채지 않는다", async () => {
    const user = userEvent.setup();
    function Screen() {
      const [text, setText] = useState("");
      return (
        <>
          <Input aria-label="자연어로 Step 추가" value={text} onChange={(e) => setText(e.target.value)} />
          <div data-workbench-detail-layer>
            <DetailPanel onClose={() => undefined} layout="w-detail">
              <DetailPanelTitle>STEP 상세</DetailPanelTitle>
              <Button>닫기</Button>
            </DetailPanel>
          </div>
        </>
      );
    }
    render(<Screen />);
    const box = screen.getByLabelText("자연어로 Step 추가");
    box.focus();

    await user.type(box, "장바구니에 담아");

    // 판이 초점을 **다시** 가져가면 첫 글자만 남는다 — T104 가 실제로 만든 회귀다.
    expect((box as HTMLInputElement).value, "판이 옆 칸의 입력을 가로챘다").toBe("장바구니에 담아");
  });
});
