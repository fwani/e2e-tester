/**
 * 018 §4 — 링크 부품. 모습은 버튼 그대로, 요소는 `<a href>`.
 *
 * 순수 이동을 버튼으로 두면 Cmd·가운데 클릭으로 새 탭을 열 수 없고 링크 주소를 복사할 수도 없다.
 * 그렇다고 문서를 새로 열면 앱 상태가 날아간다. 그래서 **보통 클릭만** 앱 안에서 옮기고 나머지는
 * 브라우저에 맡긴다. 이 파일이 그 경계를 고정한다.
 *
 * 브라우저에 맡기는 경우는 `href="#…"` 를 쓴다 — jsdom 은 해시 이동만 구현하고, 그 밖의 주소로
 * 기본 동작이 일어나면 「Not implemented: navigation」을 콘솔에 남긴다.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button, ButtonLink } from "../src/ui/Button";
import { Menu, MenuContent, MenuLinkItem, MenuTrigger } from "../src/ui/DropdownMenu";

const click = (el: Element, init: MouseEventInit = {}) => {
  const event = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0, ...init });
  el.dispatchEvent(event);
  return event;
};

describe("ButtonLink — 모양은 버튼, 요소는 링크 (018 §4)", () => {
  it("href 를 가진 a 요소이고 변종 표의 모양을 그대로 쓴다", () => {
    render(
      <ButtonLink href="/keys" onNavigate={() => undefined} variant="nav">
        키 관리
      </ButtonLink>,
    );
    const link = screen.getByRole("link", { name: "키 관리" });
    expect(link.tagName).toBe("A");
    expect(link.getAttribute("href")).toBe("/keys");
    expect(link.getAttribute("data-variant")).toBe("nav");
    // 정본 `.navlink` 의 높이 — `plainButtonVariants` 에서 온 것이다.
    expect(link.className).toContain("h-[28px]");
  });

  it("상자 변종은 border-box 다 — a 의 기본값(content-box)이면 테두리만큼 높아진다", () => {
    render(
      <ButtonLink href="/tests/new" onNavigate={() => undefined} variant="primary">
        테스트 만들기
      </ButtonLink>,
    );
    const link = screen.getByRole("link", { name: "테스트 만들기" });
    expect(link.className).toContain("box-border");
    expect(link.className).toContain("h-control");
  });

  it("같은 변종의 버튼과 모양 클래스가 같다 — 모양의 정의는 하나다 (017 FR-003)", () => {
    render(
      <>
        <Button variant="nav">버튼</Button>
        <ButtonLink href="#x" variant="nav">
          링크
        </ButtonLink>
      </>,
    );
    const button = screen.getByRole("button", { name: "버튼" }).className;
    const link = screen.getByRole("link", { name: "링크" }).className;
    expect(link).toBe(`${button} box-border text-center`);
  });

  it("보통 클릭은 앱 안에서 옮긴다 — 문서를 새로 열지 않는다", () => {
    const onNavigate = vi.fn();
    render(
      <ButtonLink href="/keys" onNavigate={onNavigate}>
        키 관리
      </ButtonLink>,
    );
    const event = click(screen.getByRole("link"));
    expect(onNavigate).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });

  it.each(["metaKey", "ctrlKey", "shiftKey", "altKey"] as const)(
    "%s 를 누른 클릭은 브라우저에 맡긴다 — 새 탭·새 창",
    (key) => {
      const onNavigate = vi.fn();
      render(
        <ButtonLink href="#keys" onNavigate={onNavigate}>
          키 관리
        </ButtonLink>,
      );
      const event = click(screen.getByRole("link"), { [key]: true });
      expect(onNavigate).not.toHaveBeenCalled();
      expect(event.defaultPrevented).toBe(false);
    },
  );

  it("주 단추가 아닌 클릭은 브라우저에 맡긴다", () => {
    const onNavigate = vi.fn();
    render(
      <ButtonLink href="#keys" onNavigate={onNavigate}>
        키 관리
      </ButtonLink>,
    );
    click(screen.getByRole("link"), { button: 1 });
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("호출부의 onClick 이 막으면 옮기지 않는다", () => {
    const onNavigate = vi.fn();
    render(
      <ButtonLink href="#keys" onNavigate={onNavigate} onClick={(e) => e.preventDefault()}>
        키 관리
      </ButtonLink>,
    );
    click(screen.getByRole("link"));
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("onNavigate 가 없으면 평범한 링크다", () => {
    render(<ButtonLink href="#list">목록으로</ButtonLink>);
    const event = click(screen.getByRole("link"));
    expect(event.defaultPrevented).toBe(false);
  });
});

describe("MenuLinkItem — 메뉴 항목인 링크 (018 §4)", () => {
  it("메뉴 항목 역할의 a 요소이고, 누르면 옮긴다", async () => {
    const onNavigate = vi.fn();
    render(
      <Menu>
        <MenuTrigger>
          <Button size="icon" aria-label="추가 동작">
            ⋯
          </Button>
        </MenuTrigger>
        <MenuContent>
          <MenuLinkItem href="/tests/TC-001/edit" onNavigate={onNavigate}>
            편집
          </MenuLinkItem>
        </MenuContent>
      </Menu>,
    );
    await userEvent.setup().click(screen.getByLabelText("추가 동작"));
    const item = await screen.findByRole("menuitem", { name: "편집" });
    expect(item.tagName).toBe("A");
    expect(item.getAttribute("href")).toBe("/tests/TC-001/edit");
    const event = click(item);
    expect(onNavigate).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
  });
});
