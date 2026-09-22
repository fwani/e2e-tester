import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it } from "vitest";
import { ToolPanel } from "../src/ui/ToolPanel";

afterEach(cleanup);
it("opens a labelled panel, closes with Escape, restores focus and preserves input", async () => {
  const user = userEvent.setup();
  render(<ToolPanel label="테스트 설정"><input aria-label="시작 주소" defaultValue="" /></ToolPanel>);
  const trigger = screen.getByRole("button", { name: "테스트 설정" });
  await user.click(trigger);
  expect(screen.getByRole("dialog", { name: "테스트 설정" })).toBeTruthy();
  await user.type(screen.getByRole("textbox"), "https://example.com");
  await user.keyboard("{Escape}");
  await waitFor(() => expect(trigger.getAttribute("aria-expanded")).toBe("false"));
  expect(document.activeElement).toBe(trigger);
  await user.click(trigger);
  expect((screen.getByRole("textbox") as HTMLInputElement).value).toBe("https://example.com");
  await user.click(screen.getByRole("button", { name: "닫기" }));
  expect(trigger.getAttribute("aria-expanded")).toBe("false");
});
it("opens automatically when recording becomes active and dismisses on an outside click", async () => {
  const user = userEvent.setup();
  const view = render(<><ToolPanel label="Step 추가"><button>녹화 중지</button></ToolPanel><button>외부</button></>);
  view.rerender(<><ToolPanel label="Step 추가" active><button>녹화 중지</button></ToolPanel><button>외부</button></>);
  expect(await screen.findByRole("dialog", { name: "Step 추가" })).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "외부" }));
  expect(screen.getByRole("button", { name: "Step 추가" }).getAttribute("aria-expanded")).toBe("false");
});
