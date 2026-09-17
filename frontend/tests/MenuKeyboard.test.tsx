/**
 * 떠 있는 메뉴의 **키보드** (017 T057 · FR-012).
 *
 * 017 전 행 메뉴는 손으로 만든 포털이었다. 단추의 클릭으로 열리고 닫혔을 뿐 — 항목 사이를 화살표로 오갈 수 없었고,
 * Esc 는 아무 일도 하지 않았으며, 닫혀도 초점이 여는 단추로 돌아오지 않았다. 보조기술에는 이 단추가 메뉴를 연다는
 * 사실(`aria-haspopup`)도, 열렸는지(`aria-expanded`)도 없었다. 이 파일은 부품(`ui/DropdownMenu`)이 그것을 지키는지,
 * 그리고 목록의 실제 행 메뉴 단추가 그 부품을 쓰는지 본다.
 */
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TestList } from "../src/pages/TestList";
import { Button } from "../src/ui/Button";
import { Menu, MenuContent, MenuItem, MenuTrigger } from "../src/ui/DropdownMenu";

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

function RowActions({ onRename }: { onRename: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Menu open={open} onOpenChange={setOpen}>
      <MenuTrigger>
        <Button size="icon" aria-label="로그인 추가 동작">
          <span aria-hidden="true">⋮</span>
        </Button>
      </MenuTrigger>
      <MenuContent>
        <MenuItem>편집</MenuItem>
        <MenuItem onClick={onRename}>이름</MenuItem>
        <MenuItem variant="danger">삭제</MenuItem>
      </MenuContent>
    </Menu>
  );
}

/**
 * 여는 단추. **열린 동안에도 찾는다** — 메뉴는 모달이라 열리면 뒤쪽(여는 단추 포함)에 `aria-hidden` 이 걸리고,
 * 역할 검색은 가려진 요소를 기본으로 건너뛴다. 단추 자체의 속성(`aria-expanded`)과 초점을 보려는 것이므로
 * 가려진 요소까지 찾는다.
 */
const trigger = () => screen.getByRole("button", { name: "로그인 추가 동작", hidden: true });

describe("메뉴 키보드 (ui/DropdownMenu · FR-012)", () => {
  it.each([
    ["Enter", "{Enter}"],
    ["Space", "[Space]"],
    ["ArrowDown", "{ArrowDown}"],
  ])("여는 단추에 초점을 두고 %s 로 열린다", async (_name, key) => {
    const user = userEvent.setup();
    render(<RowActions onRename={vi.fn()} />);
    act(() => trigger().focus());

    await user.keyboard(key);

    expect((await screen.findByRole("menu")).hasAttribute("data-open"), "메뉴가 열리지 않았다").toBe(true);
    expect(trigger().getAttribute("aria-expanded")).toBe("true");
  });

  it("열리면 첫 항목에 초점이 가고, 화살표로 항목 사이를 오간다", async () => {
    const user = userEvent.setup();
    render(<RowActions onRename={vi.fn()} />);
    act(() => trigger().focus());
    await user.keyboard("{ArrowDown}");
    await screen.findByRole("menu");

    await waitFor(() => expect(document.activeElement?.textContent).toBe("편집"));
    await user.keyboard("{ArrowDown}");
    expect(document.activeElement?.textContent).toBe("이름");
    await user.keyboard("{ArrowDown}");
    expect(document.activeElement?.textContent).toBe("삭제");
    await user.keyboard("{ArrowUp}");
    expect(document.activeElement?.textContent).toBe("이름");
  });

  it("Esc 로 닫히고, 초점이 여는 단추로 돌아온다", async () => {
    const user = userEvent.setup();
    render(<RowActions onRename={vi.fn()} />);
    act(() => trigger().focus());
    await user.keyboard("{Enter}");
    await screen.findByRole("menu");

    await user.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
    await waitFor(() => expect(document.activeElement, "닫힌 뒤 초점이 문서 처음으로 떨어졌다").toBe(trigger()));
    expect(trigger().getAttribute("aria-expanded")).toBe("false");
  });

  it("항목에서 Enter 를 누르면 그 조작을 하고 메뉴가 닫힌다", async () => {
    const user = userEvent.setup();
    const onRename = vi.fn();
    render(<RowActions onRename={onRename} />);
    act(() => trigger().focus());
    await user.keyboard("{ArrowDown}");
    await waitFor(() => expect(document.activeElement?.textContent).toBe("편집"));

    await user.keyboard("{ArrowDown}{Enter}");

    expect(onRename).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
  });
});

describe("목록의 행 메뉴 단추가 이 부품이다 (017 T056)", () => {
  it("행의 `⋮` 가 메뉴를 연다는 사실과 열림 상태를 보조기술에 알린다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              counts: { total: 1, pass: 1, fail: 0 },
              problems: [],
              tests: [
                {
                  id: "TC-001",
                  name: "로그인",
                  step_count: 3,
                  authoring_mode: "record",
                  outcome: "pass",
                  last_run_at: null,
                  failure_summary: null,
                },
              ],
            }),
            { status: 200 },
          ),
      ),
    );
    const user = userEvent.setup();
    const noop = () => undefined;
    render(<TestList onCreate={noop} onOpenResult={noop} onRun={noop} onOpenDefinition={noop} />);
    const button = await screen.findByRole("button", { name: "로그인 추가 동작" });
    expect(button.getAttribute("aria-haspopup")).toBe("menu");
    expect(button.getAttribute("aria-expanded")).toBe("false");

    await user.click(button);

    // 누름은 `mousedown` → **rAF** 로 열린다 (T105 실측) — `userEvent` 가 기다리는 마이크로태스크보다 늦다.
    // 키보드로 여는 길은 rAF 를 거치지 않으므로 위의 검사들은 그대로다.
    await waitFor(() => expect(button.getAttribute("aria-expanded")).toBe("true"));
    const items = screen.getAllByRole("menuitem").map((el) => el.textContent);
    expect(items).toEqual(["편집", "이름", "삭제"]);
  });
});
