/**
 * 모달이 열린 동안의 **알림** (017 T049 · research R6 ③④ · FR-011).
 *
 * 알림 층은 body 의 자식이고 z 60 이다 — 대화상자(z 30) 위에 뜬다. 모양이 위에 있어도 두 가지가 깨질 수 있었다.
 *
 * 1. **낭독되지 않는다.** Radix 는 모달이 열릴 때 body 의 다른 자식에 `aria-hidden` 을 건다. 알림 층이 거기
 *    휩쓸리면 대화상자가 열린 동안 뜬 오류가 보조기술에는 없다. 층의 `aria-live` 가 그것을 비켜 간다.
 * 2. **알림을 닫으면 대화상자가 닫힌다.** Radix 는 내용 바깥의 포인터·초점을 닫힘으로 친다 — 조사에서 실측했다.
 *    `ui/Dialog` 가 알림 층 안에서 시작한 상호작용을 막는다.
 */
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Toast } from "../src/ui/Toast";
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogFooter, AlertDialogTitle } from "../src/ui/AlertDialog";
import { Button } from "../src/ui/Button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from "../src/ui/Dialog";

afterEach(() => {
  cleanup();
  // 알림 층은 `Toast` 가 body 에 직접 만든다 — 다음 검사가 지난 층을 보지 않게 치운다.
  document.querySelectorAll("[data-toast-layer]").forEach((el) => el.remove());
});

function NameDialog({ onClose }: { onClose: () => void }) {
  return (
    <Dialog open onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent>
        <DialogTitle>저장하지 않은 기록이 있습니다</DialogTitle>
        <DialogDescription>저장하지 않고 나가면 사라집니다.</DialogDescription>
        <DialogFooter>
          <Button onClick={onClose}>돌아가기</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * jsdom 은 Tailwind 산출 CSS 를 싣지 않는다. Radix 가 모달을 열며 body 에 인라인 `pointer-events:none` 을 걸면,
 * 알림 층 자식의 `pointer-events-auto`(클래스)는 여기서 계산되지 않으므로 userEvent 가 「누를 수 없다」고 거절한다.
 * **실제 브라우저에서 누를 수 있는지**는 층의 클래스 형태(`ToastPlacement`)와 화면 순회가 본다. 이 파일이 재는 것은
 * 「눌렀을 때 대화상자가 닫히는가」이므로 그 점검만 끈다.
 */
const clicker = () => userEvent.setup({ pointerEventsCheck: 0 });

describe("모달이 열린 동안의 알림 (research R6)", () => {
  it("알림이 먼저 떠 있었어도, 대화상자가 열린 동안 알림 층은 가려지지 않는다 (③)", async () => {
    render(
      <>
        <Toast tone="error" onDismiss={vi.fn()}>
          저장하지 못했습니다
        </Toast>
        <NameDialog onClose={vi.fn()} />
      </>,
    );
    await screen.findByRole("dialog");

    const layer = document.querySelector("[data-toast-layer]");
    expect(layer?.getAttribute("aria-live"), "알림 층이 없거나 낭독 속성을 잃었다").toBe("polite");
    expect(layer!.getAttribute("aria-hidden"), "대화상자가 알림 층을 보조기술에서 숨겼다").toBeNull();
    expect(screen.getByRole("alert").textContent).toContain("저장하지 못했습니다");
  });

  it("대화상자가 열린 뒤에 뜬 알림도 낭독 대상이다 (③)", async () => {
    const { rerender } = render(<NameDialog onClose={vi.fn()} />);
    await screen.findByRole("dialog");

    rerender(
      <>
        <NameDialog onClose={vi.fn()} />
        <Toast tone="error" onDismiss={vi.fn()}>
          실행을 시작하지 못했습니다
        </Toast>
      </>,
    );

    expect(screen.getByRole("alert").textContent).toContain("실행을 시작하지 못했습니다");
  });

  it("알림의 닫기를 눌러도 대화상자는 닫히지 않는다 (④)", async () => {
    const user = clicker();
    const onDismiss = vi.fn();
    const onClose = vi.fn();
    render(
      <>
        <Toast tone="warn" onDismiss={onDismiss}>
          연결이 잠시 끊겼습니다
        </Toast>
        <NameDialog onClose={onClose} />
      </>,
    );
    await screen.findByRole("dialog");

    await user.click(screen.getByRole("button", { name: "알림 닫기" }));

    expect(onDismiss, "알림이 닫히지 않았다").toHaveBeenCalledTimes(1);
    expect(onClose, "알림을 닫는 조작이 대화상자를 닫았다").not.toHaveBeenCalled();
    // 열림 표식이 `data-state="open"` → **`data-open`**(값 없는 속성)으로 바뀌었다. 판정 방법만 옮겼다 (T104).
    expect(screen.getByRole("dialog").hasAttribute("data-open"), "알림을 닫는 조작이 대화상자를 닫았다").toBe(true);
  });

  it("확인 대화상자도 알림을 닫는 조작으로 닫히지 않는다", async () => {
    const user = clicker();
    const onDismiss = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <>
        <Toast tone="warn" onDismiss={onDismiss}>
          연결이 잠시 끊겼습니다
        </Toast>
        <AlertDialog open onOpenChange={onOpenChange}>
          <AlertDialogContent aria-describedby={undefined}>
            <AlertDialogTitle>실행 화면을 닫습니다</AlertDialogTitle>
            <AlertDialogFooter>
              <AlertDialogCancel>돌아가기</AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </>,
    );
    await screen.findByRole("alertdialog");

    await user.click(screen.getByRole("button", { name: "알림 닫기" }));
    await act(async () => undefined);

    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onOpenChange, "알림을 닫는 조작이 확인 대화상자를 닫으려 했다").not.toHaveBeenCalled();
    expect(screen.getByRole("alertdialog").hasAttribute("data-open")).toBe(true);
  });
});
