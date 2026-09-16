/**
 * 툴팁과 접었다 펴는 자리의 **동작** (017 T063·T065 · FR-019 · ui-parts §4).
 *
 * 017 전에는 글자 없는 아이콘 조작(행 메뉴 `⋮` · 알림 `×` · Step 상세 닫기)의 이름이 `aria-label` 과 `title` 뿐이었다 —
 * `title` 은 포인터를 올려야만 뜨고 **키보드 초점에는 뜨지 않는다.** 잘린 글자도 같았다. 접었다 펴는 자리는 단추가 ▸/▾
 * 글자를 바꿔 그려 펼침 상태가 보조기술에 없었다. 이 파일은 부품이 그 셋을 지키는지 본다.
 */
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Button } from "../src/ui/Button";
import { Disclosure } from "../src/ui/Disclosure";
import { Tooltip, Truncate } from "../src/ui/Tooltip";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("툴팁 (ui/Tooltip)", () => {
  it("키보드 초점에 뜬다 — `title` 이 하지 못하던 것", async () => {
    render(
      <Tooltip content="닫기">
        <Button size="icon" aria-label="닫기">
          <span aria-hidden="true">×</span>
        </Button>
      </Tooltip>,
    );
    const user = userEvent.setup();
    await user.tab();
    expect(document.activeElement?.getAttribute("aria-label")).toBe("닫기");

    /*
      **판정 방법만 옮겼다** (T106 · test-ledger 09-16). 새 갈래의 툴팁 팝업에는 `role="tooltip"` 이 없다
      (실측 — 팝업은 `data-open`·`data-slot=tooltip-content`, 자리 상자는 `role="presentation"`). **뜨는 것
      자체는 그대로다.** 그래서 남의 역할 이름 대신 **우리 표식**으로 집는다. 묻는 것은 그대로다:
      초점만으로 전체 문구가 뜨는가.
    */
    const tip = await waitFor(() => {
      const el = document.querySelector("[data-slot=tooltip-content]");
      expect(el, "툴팁이 뜨지 않았다").not.toBe(null);
      return el as HTMLElement;
    });
    expect(tip.textContent).toBe("닫기");
  });

  it("포인터를 올리면 뜨고 Esc 로 닫힌다", async () => {
    render(
      <Tooltip content="추가 동작">
        <Button size="icon" aria-label="로그인 추가 동작">
          <span aria-hidden="true">⋮</span>
        </Button>
      </Tooltip>,
    );
    const user = userEvent.setup();
    await user.hover(screen.getByRole("button", { name: "로그인 추가 동작" }));
    const tip = await waitFor(() => {
      const el = document.querySelector("[data-slot=tooltip-content]");
      expect(el, "툴팁이 뜨지 않았다").not.toBe(null);
      return el as HTMLElement;
    });
    expect(tip.textContent).toBe("추가 동작");

    await user.keyboard("{Escape}");
    await waitFor(() => expect(document.querySelector("[data-slot=tooltip-content]")).toBe(null));
  });
});

describe("잘린 글자 (ui/Tooltip Truncate · FR-019)", () => {
  const NAME = "비밀번호를 틀리면 막히고 오류 문구가 입력칸 아래에 뜬다 — 목록과 국면 띠에서 아주 긴 테스트 이름";

  it("잘리지 않았으면 초점 자리도 툴팁도 두지 않는다", async () => {
    render(<Truncate>{NAME}</Truncate>);
    const text = screen.getByText(NAME);
    expect(text.getAttribute("tabindex")).toBeNull();
    expect(text.getAttribute("data-clipped")).toBeNull();
  });

  it("잘렸으면 초점을 받고, 초점에 전체 문구가 뜬다", async () => {
    // jsdom 은 배치를 계산하지 않는다 — 넘친 상태를 심는다. 실제 넘침은 화면 순회가 잰다.
    vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockReturnValue(480);
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(200);
    render(<Truncate>{NAME}</Truncate>);
    const text = screen.getByText(NAME);
    expect(text.getAttribute("data-clipped")).toBe("true");
    expect(text.getAttribute("tabindex")).toBe("0");

    act(() => text.focus());
    // T106 — 팝업에 `role="tooltip"` 이 없다. 우리 표식으로 집는다 (위 주석).
    const tip = await waitFor(() => {
      const el = document.querySelector("[data-slot=tooltip-content]");
      expect(el, "툴팁이 뜨지 않았다").not.toBe(null);
      return el as HTMLElement;
    });
    expect(tip.textContent).toBe(NAME);
  });
});

describe("접었다 펴는 자리 (ui/Disclosure)", () => {
  it("네이티브 요약 줄이 펼침을 바꾸고, 표식 글자는 낭독 대상이 아니다", async () => {
    const onOpenChange = vi.fn();
    render(
      <Disclosure summary="테스트 DSL 미리보기" tone="action" onOpenChange={onOpenChange}>
        <pre>steps: []</pre>
      </Disclosure>,
    );
    const details = document.querySelector('[data-slot="disclosure"]') as HTMLDetailsElement;
    const summary = details.querySelector("summary") as HTMLElement;
    expect(details.open).toBe(false);
    expect(
      Array.from(summary.querySelectorAll('[aria-hidden="true"]')).map((m) => m.textContent),
      "표식 두 글자가 낭독에서 빠져 있지 않다",
    ).toEqual(["▸", "▾"]);

    const user = userEvent.setup();
    await user.click(summary);

    expect(details.open).toBe(true);
    await waitFor(() => expect(onOpenChange).toHaveBeenLastCalledWith(true));
  });

  it("처음부터 펼친 채로 둘 수 있다 — 되돌리는 방법을 먼저 보여 줄 자리(UC-013-05)", () => {
    render(
      <Disclosure summary="옮긴 자리 2곳" open>
        <div>~/.local/share/itb/trash/TC-001</div>
      </Disclosure>,
    );
    const details = document.querySelector('[data-slot="disclosure"]') as HTMLDetailsElement;
    expect(details.open).toBe(true);
    expect(details.querySelector("summary")?.textContent).toContain("옮긴 자리 2곳");
  });
});
