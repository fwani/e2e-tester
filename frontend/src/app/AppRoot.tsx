/**
 * 앱 뿌리 — 저장소와 라우터를 잇는다 (018 design §2).
 *
 * 제품은 `createBrowserApp()` 로 한 벌을 **시작할 때 한 번** 만든다 — 브라우저 라우터는 `popstate` 를 듣고,
 * 컴포넌트 안에서 만들면 StrictMode 의 이중 마운트가 두 벌을 만든다. 검사는 같은 `createRoutes` 로 메모리
 * 라우터를 만들어 `AppRoot` 에 넘긴다 (`tests/helpers/app.tsx`).
 */
import { createBrowserRouter, type DataRouter } from "react-router";
import { RouterProvider } from "react-router/dom";

import { AppStoreContext, createAppStore, type AppStore } from "./appStore";
import { createRoutes } from "./router";

export interface AppParts {
  readonly store: AppStore;
  readonly router: DataRouter;
}

export function createBrowserApp(): AppParts {
  const store = createAppStore();
  return { store, router: createBrowserRouter(createRoutes(store)) };
}

export function AppRoot({ store, router }: AppParts) {
  return (
    <AppStoreContext.Provider value={store}>
      <RouterProvider router={router} />
    </AppStoreContext.Provider>
  );
}
