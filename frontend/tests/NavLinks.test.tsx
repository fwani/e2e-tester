/**
 * 018 §4 — 순수 이동은 링크다.
 *
 * 누르면 다른 화면으로 가기만 하는 조작이 `<a href>` 여야 Cmd·가운데 클릭으로 새 탭을 열고 링크 주소를
 * 복사할 수 있다. 보통 클릭은 지금처럼 콜백을 부른다 — 화면은 라우터를 모른다.
 *
 * 부수효과가 있는 조작(실행 · 녹화)과 비활성 사유를 보여야 하는 조작은 버튼으로 남는다 — 그것도 본다.
 */
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KeyManagement } from "../src/pages/KeyManagement";
import { SecretValues } from "../src/pages/SecretValues";
import { TestList, type TestListProps } from "../src/pages/TestList";
import { LIST } from "./helpers/fakeServer";

const noop = () => undefined;

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const u = String(url);
      if (u.startsWith("/api/tests")) return new Response(JSON.stringify(LIST), { status: 200 });
      if (u === "/api/secrets") {
        return new Response(
          JSON.stringify({ public_key_fingerprint: null, fingerprint_matches_key: true, names: [] }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({}), { status: 200 });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("목록 화면 (018 §4)", () => {
  it.each([
    ["바꾸기", "/projects", "onOpenProjects"],
    ["비밀 값", "/secrets", "onOpenSecrets"],
    ["키 관리", "/keys", "onOpenKeys"],
    ["테스트 만들기", "/tests/new", "onCreate"],
  ] as const)("머리띠의 「%s」는 %s 로 가는 링크다", async (name, href, prop) => {
    const spy = vi.fn();
    const props: TestListProps = {
      projectName: "P",
      onCreate: noop,
      onOpenResult: noop,
      onRun: noop,
      onOpenProjects: noop,
      onOpenSecrets: noop,
      onOpenKeys: noop,
    };
    (props as unknown as Record<string, unknown>)[prop] = spy;
    render(<TestList {...props} />);
    const link = await screen.findByRole("link", { name });
    expect(link.getAttribute("href")).toBe(href);
    act(() => link.click());
    expect(spy).toHaveBeenCalledOnce();
  });

  it("행의 「결과 보기」는 그 테스트의 결과로 가는 링크다", async () => {
    const onOpenResult = vi.fn();
    render(<TestList projectName="P" onCreate={noop} onOpenResult={onOpenResult} onRun={noop} />);
    const link = await screen.findByRole("link", { name: "결과 보기" });
    expect(link.getAttribute("href")).toBe("/tests/TC-001/result");
    act(() => link.click());
    expect(onOpenResult).toHaveBeenCalledWith("TC-001");
  });

  it("행 메뉴의 「편집」은 그 테스트의 편집으로 가는 링크 항목이다", async () => {
    const onOpenDefinition = vi.fn();
    render(
      <TestList
        projectName="P"
        onCreate={noop}
        onOpenResult={noop}
        onRun={noop}
        onOpenDefinition={onOpenDefinition}
      />,
    );
    await userEvent.setup().click(await screen.findByLabelText("로그인 추가 동작"));
    const item = await screen.findByRole("menuitem", { name: "편집" });
    expect(item.tagName).toBe("A");
    expect(item.getAttribute("href")).toBe("/tests/TC-001/edit");
    act(() => item.click());
    expect(onOpenDefinition).toHaveBeenCalledWith("TC-001");
  });

  it("실행은 버튼으로 남는다 — 부수효과가 있는 조작이다", async () => {
    render(<TestList projectName="P" onCreate={noop} onOpenResult={noop} onRun={noop} />);
    await screen.findByRole("link", { name: "결과 보기" });
    expect(screen.queryByRole("link", { name: /실행/ })).toBeNull();
  });
});

describe("비밀 값 · 키 관리 (018 §4)", () => {
  it("비밀 값의 「키 관리」와 「닫기」는 링크다", async () => {
    const onManageKeys = vi.fn();
    const onClose = vi.fn();
    render(<SecretValues onClose={onClose} onManageKeys={onManageKeys} />);
    const keys = await screen.findByRole("link", { name: "키 관리" });
    const close = screen.getByRole("link", { name: "닫기" });
    expect(keys.getAttribute("href")).toBe("/keys");
    expect(close.getAttribute("href")).toBe("/");
    act(() => keys.click());
    act(() => close.click());
    expect(onManageKeys).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("키 관리의 「닫기」는 목록으로 가는 링크다", async () => {
    const onClose = vi.fn();
    render(<KeyManagement onClose={onClose} />);
    const close = await screen.findByRole("link", { name: "닫기" });
    expect(close.getAttribute("href")).toBe("/");
    act(() => close.click());
    expect(onClose).toHaveBeenCalledOnce();
  });
});
