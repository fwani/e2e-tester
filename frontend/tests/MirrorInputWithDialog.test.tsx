/**
 * 대화상자와 **미러 입력** (017 T053 · FR-016 · SC-013).
 *
 * 미러는 키 입력을 대상 브라우저로 보낸다(010). 한글은 미러 면 안의 보이지 않는 조합 칸이 받는다. 017 이 대화상자를
 * Radix 로 바꾸면서 두 가지가 새로 성립해야 한다.
 *
 * 1. **대화상자가 열린 동안 미러로 가는 입력이 0 이다.** 017 전 대화상자는 초점을 옮기지 않았으므로 미러 조합 칸에
 *    초점이 남은 채 확인 창이 떴고, 사용자가 창의 이름 칸에 적으려던 글자가 대상 앱에 들어갈 수 있었다. 이제 초점이
 *    대화상자 안으로 간다.
 * 2. **닫은 뒤 미러 입력 경로가 전과 같다.** 초점이 연 자리(조합 칸)로 돌아오고, 키와 조합이 그대로 나간다.
 *    Radix 가 초점을 문서 처음으로 떨어뜨리면 사용자는 미러를 다시 눌러야 하고, 그 전의 타이핑은 사라진다.
 */
import { act, cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MirrorView } from "../src/components/MirrorView";
import type { FrameGeometry } from "../src/components/mirror/useMirrorInput";
import type { CapabilityState } from "../src/lib/capabilities";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from "../src/ui/AlertDialog";

afterEach(cleanup);

const FRAME = "AAAABBBBCCCC";
const ENABLED: CapabilityState = { kind: "enabled" };
const GEOMETRY: FrameGeometry = { width: 800, height: 600, pageScale: 1, offsetTop: 0 };

function Screen({ confirming, onInput }: { confirming: boolean; onInput: (e: { kind: string }) => void }) {
  return (
    <>
      <MirrorView frame={FRAME} phase="manipulation" control={ENABLED} geometry={GEOMETRY} tabIndex={0} onInput={onInput} />
      {confirming && (
        <AlertDialog open>
          <AlertDialogContent>
            <AlertDialogTitle>실행 화면을 닫습니다</AlertDialogTitle>
            <AlertDialogDescription>결과는 목록에서 다시 볼 수 있습니다.</AlertDialogDescription>
            <AlertDialogFooter>
              <AlertDialogCancel>돌아가기</AlertDialogCancel>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </>
  );
}

function imeOf(): HTMLTextAreaElement {
  const surface = document.querySelector('[data-action="mirror.control"]') as HTMLElement;
  return surface.querySelector("textarea") as HTMLTextAreaElement;
}

describe("대화상자와 미러 입력 (017 FR-016)", () => {
  it("대화상자가 열린 동안 키 입력은 미러로 가지 않는다", async () => {
    const user = userEvent.setup();
    const onInput = vi.fn();
    const { rerender } = render(<Screen confirming={false} onInput={onInput} />);
    act(() => imeOf().focus());
    expect(document.activeElement, "준비 — 미러 조합 칸에 초점이 있어야 한다").toBe(imeOf());

    rerender(<Screen confirming onInput={onInput} />);
    await waitFor(() => expect(document.activeElement?.closest('[role="alertdialog"]')?.getAttribute("role")).toBe("alertdialog"));

    await user.keyboard("abc{Enter}");

    expect(
      onInput.mock.calls.map(([e]) => e.kind),
      "대화상자가 열린 동안 키가 대상 브라우저로 나갔다",
    ).toEqual([]);
    // 포인터는 Radix 가 body 에 건 `pointer-events:none` 이 막는다 (실제 브라우저의 성질 — 여기서는 그 표시만 본다).
    expect(document.body.style.pointerEvents).toBe("none");
  });

  it("닫으면 초점이 미러 조합 칸으로 돌아오고, 키와 한글 조합이 전과 같이 나간다", async () => {
    const onInput = vi.fn();
    const { rerender } = render(<Screen confirming={false} onInput={onInput} />);
    act(() => imeOf().focus());

    rerender(<Screen confirming onInput={onInput} />);
    await waitFor(() => expect(document.activeElement?.closest('[role="alertdialog"]')?.getAttribute("role")).toBe("alertdialog"));
    rerender(<Screen confirming={false} onInput={onInput} />);

    await waitFor(() => expect(document.activeElement, "닫은 뒤 초점이 미러로 돌아오지 않았다").toBe(imeOf()));
    expect(document.body.style.pointerEvents, "닫은 뒤에도 포인터가 막혀 있다").not.toBe("none");

    const ime = imeOf();
    fireEvent.keyDown(ime, { key: "a", code: "KeyA" });
    fireEvent.compositionStart(ime);
    fireEvent.compositionUpdate(ime, { data: "ㅈ" });
    fireEvent.compositionEnd(ime, { data: "주" });

    expect(onInput.mock.calls.map(([e]) => [e.kind, e.text])).toEqual([
      ["key.down", undefined],
      ["ime.compose", "ㅈ"],
      ["ime.commit", "주"],
    ]);
  });
});
