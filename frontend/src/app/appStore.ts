/**
 * 앱 저장소 — 화면을 넘어 사는 상태 (018 design §3.1).
 *
 * 옛 `App.tsx` 가 `useState` 로 쥐던 것 중 **loader 도 닿아야 하는 것**을 여기로 옮겼다.
 *
 * - 열린 프로젝트 — 루트 미들웨어가 loader 보다 먼저 채운다 (§3.2)
 * - 오류 — 초안 조회에 실패한 loader 가 알린다 (§5). 문자열이 아니라 `ErrorInfo` 다 (003 EC-004)
 * - 가져오기 결과·계획 — 미리보기에서 만들어지고 목록에서 확인한다 (014 FR-018a · §3.4)
 *
 * **React 상태가 아니라 바깥 저장소다.** loader 는 React 밖에서 돈다. 화면은 `useAppState` 로 구독한다.
 * **라우터마다 하나다** (`createAppStore`) — 모듈 전역이면 검사끼리 상태가 새고, 새로 고친 앱이 옛
 * 가져오기 계획을 기억하는 것처럼 보이게 된다.
 */
import { createContext, useContext, useSyncExternalStore } from "react";

import {
  project as projectApi,
  setExpectedProjectRoot,
  type ImportPlanView,
  type ImportResultView,
  type ProjectView,
} from "../api/client";
import type { ErrorInfo } from "../components/ErrorNotice";

export interface AppState {
  /** `undefined` = 아직 모른다. `null` = 열린 프로젝트가 없다. */
  readonly project: ProjectView | null | undefined;
  readonly error: ErrorInfo | null;
  /** 방금 끝난 가져오기의 결과. 목록 위에 한 번 보이고 사용자가 닫는다 (014 FR-018a). */
  readonly importDone: ImportResultView | null;
}

export interface AppStore {
  getState(): AppState;
  subscribe(listener: () => void): () => void;
  /** 열린 프로젝트를 한 번만 조회한다. 이미 알면 묻지 않는다. 실패는 「없다」(`null`)다. */
  ensureProject(): Promise<ProjectView | null>;
  openProject(p: ProjectView | null): void;
  renameProject(root: string, name: string): void;
  setError(error: ErrorInfo | null): void;
  setImportDone(result: ImportResultView | null): void;
  keepImportPlan(plan: ImportPlanView): void;
  importPlan(planId: string): ImportPlanView | null;
  dropImportPlan(planId: string): void;
}

export function createAppStore(): AppStore {
  let state: AppState = { project: undefined, error: null, importDone: null };
  const listeners = new Set<() => void>();
  /**
   * 가져오기 계획 (§3.4). **구독 대상이 아니다** — 화면은 이것을 그리지 않고 loader 만 읽는다.
   * `location.state` 에 두지 않는 이유: 그것은 새로 고쳐도 남아 만료된 계획을 그린다.
   */
  const plans = new Map<string, ImportPlanView>();
  let pending: Promise<ProjectView | null> | null = null;

  const update = (patch: Partial<AppState>) => {
    state = { ...state, ...patch };
    for (const listener of listeners) listener();
  };

  /*
    2026-09-10 사용자 보고 1번 — **화면이 보고 있는 프로젝트를 모든 요청이 함께 말한다.**

    「a 프로젝트에서 새 테스트를 만들었는데 b 프로젝트 목록에 들어갔다」의 원인은 시작
    URL 이 아니라 이 값이 서버와 갈라질 수 있다는 것이었다 (`client.ts` 의
    `setExpectedProjectRoot` 주석).

    **효과로 미루지 않고 여기서 곧바로 세운다.** 효과는 렌더 뒤에 돌고, 자식의 효과가
    부모보다 먼저 돈다 — 프로젝트를 바꾼 직후 새로 붙는 목록 화면의 첫 조회가 **옛
    프로젝트의 경로**를 달고 나가게 된다. 그러면 자동 복구가 사용자가 방금 떠난 프로젝트를
    다시 열어, 고치려던 것과 같은 뒤바뀜이 된다.
  */
  const openProject = (p: ProjectView | null) => {
    setExpectedProjectRoot(p?.root ?? null);
    update({ project: p });
  };

  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    ensureProject() {
      if (state.project !== undefined) return Promise.resolve(state.project);
      pending ??= projectApi
        .current()
        .then(
          (p) => p,
          // 열린 프로젝트가 없으면 선택 화면부터다 — 그 화면이 기존 프로젝트를 불러 보여준다 (DR-002).
          () => null,
        )
        .then((p) => {
          pending = null;
          // 기다리는 사이 사용자가 연 프로젝트가 있으면 그것이 이긴다.
          if (state.project === undefined) openProject(p);
          return state.project ?? null;
        });
      return pending;
    },
    openProject,
    renameProject(root, name) {
      /*
        **경로가 같을 때만 갈아 끼운다** (012 FR-405). 목록의 어느 줄에서나 이름을 고칠 수 있으므로,
        지금 열려 있는 것과 다른 프로젝트를 고쳤는데 열린 것의 이름을 바꾸면 안 된다.
      */
      const p = state.project;
      if (p && p.root === root) update({ project: { ...p, name } });
    },
    setError(error) {
      update({ error });
    },
    setImportDone(importDone) {
      update({ importDone });
    },
    keepImportPlan(plan) {
      plans.set(plan.plan_id, plan);
    },
    importPlan(planId) {
      return plans.get(planId) ?? null;
    },
    dropImportPlan(planId) {
      plans.delete(planId);
    },
  };
}

export const AppStoreContext = createContext<AppStore | null>(null);

export function useAppStore(): AppStore {
  const store = useContext(AppStoreContext);
  if (store === null) throw new Error("AppStoreContext 가 없습니다 — AppRoot 안에서만 쓸 수 있습니다.");
  return store;
}

/**
 * 저장소의 한 조각을 구독한다.
 *
 * **선택 함수는 필드를 그대로 돌려줘야 한다.** 새 객체를 만들면 매번 다른 값이 되어 무한히 다시 그린다.
 * 저장소는 바뀌지 않은 필드를 같은 객체로 두므로 필드를 꺼내는 것은 안전하다.
 */
export function useAppState<T>(select: (s: AppState) => T): T {
  const store = useAppStore();
  return useSyncExternalStore(store.subscribe, () => select(store.getState()));
}
