import userEvent from "@testing-library/user-event";
/** Follow the visible tool trigger before interacting with its controls. */
export async function revealTool(element: Element | null) {
  const host = element?.closest("[data-tool-name]");
  const trigger = host?.querySelector(":scope > button");
  if (trigger?.getAttribute("aria-expanded") === "false") await userEvent.click(trigger);
}
