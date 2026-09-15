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

    // 칸 · 돌아가기 · 저장 — 세 번을 넘겨 한 바퀴 이상 돈다.
    for (let i = 0; i < 5; i += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement), `Tab ${i + 1}회에 초점이 밖으로 나갔다`).toBe(true);
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
    expect(overlay?.getAttribute("data-state"), "열린 가림막을 찾지 못했다").toBe("open");
    await user.click(overlay as HTMLElement);

    expect(screen.getByRole("alertdialog").getAttribute("data-state"), "확인 대화상자가 닫혔다").toBe("open");
    expect(onConfirm).not.toHaveBeenCalled();
  });
});

function within(el: HTMLElement) {
  return {
    getByRole: (role: string, options: { name: string }) =>
      screen.getAllByRole(role, options).find((node) => el.contains(node)) as HTMLElement,
  };
}
