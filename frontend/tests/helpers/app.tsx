/**
 * 앱 전체를 **메모리 라우터**로 그린다 (018).
 *
 * 제품은 브라우저 라우터를 쓰지만 검사는 주소를 직접 쥐어야 한다 — 시작 주소, `history.state`, 이동 뒤의
 * 위치를 `router.state` 로 읽는다. 라우트 표와 저장소는 제품과 **같은 함수**(`createRoutes` ·
 * `createAppStore`)로 만든다.
 *
 * 검사가 끝나면 라우터를 버린다 — 남겨 두면 진행 중이던 loader 가 다음 검사의 가짜 서버를 부른다.
 * 저장소가 세운 프로젝트 경로도 되돌린다 (`client.ts` 의 모듈 값이다).
 */
import { render } from "@testing-library/react";
import { createMemoryRouter, type DataRouter } from "react-router";
import { afterEach } from "vitest";

import { setExpectedProjectRoot } from "../../src/api/client";
import { AppRoot } from "../../src/app/AppRoot";
import { createAppStore, type AppStore } from "../../src/app/appStore";
import { createRoutes } from "../../src/app/router";

const live: DataRouter[] = [];

afterEach(() => {
  for (const router of live.splice(0)) router.dispose();
  setExpectedProjectRoot(null);
});

export function renderApp(
  url: string,
  options: { state?: unknown; prepare?: (store: AppStore) => void } = {},
) {
  const store = createAppStore();
  options.prepare?.(store);
  const at = new URL(url, "http://localhost");
  const router = createMemoryRouter(createRoutes(store), {
    initialEntries: [{ pathname: at.pathname, search: at.search, state: options.state ?? null }],
  });
  live.push(router);
  return { ...render(<AppRoot store={store} router={router} />), store, router };
}
