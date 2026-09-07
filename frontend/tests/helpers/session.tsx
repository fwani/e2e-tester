/**
 * 세션 국면 화면의 검사 도우미 (007 T035·T039).
 *
 * 007 이전에는 국면마다 페이지 컴포넌트가 따로 있어서 검사도 그것을 직접 그렸다
 * (`Runner`·`RunnerPaused`·`Takeover`·`AiRecord`). 통합 뒤에는 그릴 것이 `SessionWorkbench`
 * 하나이고, **국면을 정하는 것은 `SessionView` 다** — 그래서 픽스처가 세션 뷰를 만들고
 * 화면은 그것으로 국면을 판정한다.
 *
 * `workbench.ts` 의 규칙을 그대로 따른다 — **팩토리는 항상 온전한 객체를 만든다.**
 */
import { render } from "@testing-library/react";

import { SessionWorkbench, type SessionWorkbenchProps } from "../../src/pages/SessionScreen";
import type { SessionView } from "../../src/api/client";
import { sessionView } from "./workbench";

const noop = () => undefined;

export function sessionProps(
  overrides: Partial<SessionWorkbenchProps> = {},
): SessionWorkbenchProps {
  return {
    view: sessionView(),
    outcomeOf: () => "pending",
    durationOf: () => undefined,
    mirror: <div data-testid="mirror" />,
    currentUrl: "https://x.test/",
    onSelectStep: noop,
    ...overrides,
  };
}

/** 세션 뷰 덮개까지 한 번에 준다 — 국면은 `state`·`authoring_mode` 가 정한다. */
export function renderSession(
  view: Partial<SessionView> = {},
  overrides: Partial<SessionWorkbenchProps> = {},
) {
  return render(
    <SessionWorkbench {...sessionProps({ view: sessionView(view), ...overrides })} />,
  );
}
