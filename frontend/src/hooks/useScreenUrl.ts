/**
 * 화면 상태 ↔ URL (005 T095 · FR-166·FR-167).
 *
 * 리포트 U-15 가 본 것 — 결과 화면에서도 주소는 `http://127.0.0.1:4410/` 였다.
 * 새로고침하면 목록으로 되돌아가고, **브라우저 뒤로가기를 누르면 `about:blank` 로 나가
 * 앱을 완전히 이탈**했다. 로컬 도구라도 화면은 브라우저 안에 있고, 뒤로가기는 사용자가
 * 가장 먼저 누르는 키다.
 *
 * **라우팅 라이브러리를 추가하지 않는다** (research R8). 현재 의존성은 `react` ·
 * `react-dom` 둘뿐이고, 라우터를 넣으면 화면 트리 전체를 라우트로 재편하게 되어 이
 * 기능의 다른 부분과 같은 시점에 충돌한다. 요구된 것은 두 가지뿐이다 —
 * 결과 화면의 새로고침 복원(FR-166)과 뒤로가기 이탈 방지(FR-167).
 */

import { useEffect, useRef } from "react";

/**
 * 주소가 나르는 것 — **국면 · 테스트 · Step** 셋이다 (007 T069 · FR-239·FR-240).
 *
 * 007 이 이름을 바꾼 이유: 007 이전에는 화면 이름이 곧 위치였다. 이제 화면은 하나이고
 * 위치는 **한 테스트를 놓고 사용자가 지금 있는 국면**이다. 새로 고침으로 되찾아야 하는
 * 것도 화면이 아니라 그 위치다 — 어느 테스트의 어느 국면에서 어느 Step 을 보고 있었나.
 *
 * `name` 의 값은 007 이전 그대로 둔다. 주소 문자열을 바꾸면 사용자가 열어 둔 탭과
 * 북마크가 끊기는데, 그것은 이 라운드가 고치려는 문제와 무관하다.
 *
 *   `compose`    → 만들기 국면 (2회차)
 *   `runner`     → 세션 다섯 국면 (녹화·AI 작성·사람이 직접 조작·실행 중·일시정지)
 *   `result`     → 결과 국면
 *   `definition` → 편집 국면
 *
 * 2회차가 `compose` 를 더하면서 1회차의 `create`·`ai-compose` 두 이름을 **하나로
 * 합쳤다.** 옛 이름으로 들어온 주소는 `compose` 로 정규화한다 — 열어 둔 탭과 북마크를
 * 끊지 않는 것이 이 파일의 원래 규율이다.
 *
 * 세션처럼 수명이 짧은 것은 식별자만 싣는다 — URL 만으로 되살리면 죽은 세션을 그린다.
 */
export interface WorkbenchLocation {
  name: string;
  testId?: string | null;
  sessionId?: string | null;
  /**
   * 지목한 Step (006 FR-181 · 007 FR-239).
   *
   * 결과 화면의 「Step nn 고치기」로 들어온 뒤 새로고침하면 그 Step 이 다시 펼쳐져야
   * 한다 — 지목을 잃으면 사용자는 어느 Step 을 고치러 왔는지부터 다시 찾는다.
   *
   * **007 이 이것을 결과 국면까지 넓혔다.** 국면을 넘어도 보던 Step 을 잃지 않는 것이
   * US3 이고, 주소는 그 유지가 새로 고침을 견디게 하는 자리다.
   */
  stepId?: string | null;
}

/** 007 이전 이름. 부르는 곳이 남아 있어도 같은 것을 가리킨다. */
export type ScreenLocation = WorkbenchLocation;

const PARAM = "screen";

/**
 * 1회차 이름 → 2회차 이름 (research R12).
 *
 * 만들기가 화면 둘에서 국면 하나로 합쳐졌다. 옛 주소를 떨어뜨리면 사용자가 열어 둔
 * 탭이 목록으로 튕긴다 — 그것은 이 라운드가 고치려는 문제와 무관한 손해다.
 */
const RENAMED: Record<string, string> = {
  create: "compose",
  "ai-compose": "compose",
};

/** 화면 상태를 질의 문자열로. 목록은 `/` 다 — 기본 화면에 파라미터를 남기지 않는다. */
export function locationToSearch(loc: WorkbenchLocation): string {
  if (loc.name === "list" || loc.name === "loading" || loc.name === "setup") return "";
  const params = new URLSearchParams();
  params.set(PARAM, loc.name);
  if (loc.testId) params.set("test", loc.testId);
  if (loc.sessionId) params.set("session", loc.sessionId);
  if (loc.stepId) params.set("step", loc.stepId);
  return `?${params.toString()}`;
}

/** 질의 문자열을 화면 상태로. 알 수 없는 값은 목록으로 떨어뜨린다. */
export function searchToLocation(search: string): WorkbenchLocation {
  const params = new URLSearchParams(search);
  const raw = params.get(PARAM);
  if (!raw) return { name: "list" };
  const name = RENAMED[raw] ?? raw;
  return {
    name,
    testId: params.get("test"),
    sessionId: params.get("session"),
    stepId: params.get("step"),
  };
}

/**
 * 화면 상태를 주소에 반영하고, 뒤로가기를 앱 내부 이동으로 만든다.
 *
 * @param current 지금 화면
 * @param onPopState 뒤로가기·앞으로가기가 가리키는 화면으로 이동하는 함수
 *
 * **첫 렌더에서는 `pushState` 하지 않는다.** 히스토리에 같은 화면을 두 번 쌓으면
 * 뒤로가기를 두 번 눌러야 이전 화면으로 간다.
 */
export function useScreenUrl(
  current: WorkbenchLocation,
  onPopState: (loc: WorkbenchLocation) => void,
): void {
  const lastSearch = useRef<string | null>(null);
  const handler = useRef(onPopState);
  handler.current = onPopState;

  // 화면 → URL
  useEffect(() => {
    if (typeof window === "undefined") return;
    /**
     * **앱이 아직 화면을 정하지 못했으면 주소를 건드리지 않는다** (006 T046 · FR-181).
     *
     * 재점검 리포트 N-01 의 원인이 이것이었다 — 결과·편집 화면에서 새로고침하면 목록으로
     * 튀고 주소창까지 `/` 로 바뀌었다. `ScreenUrl.test.ts` 의 변환 함수 테스트는 통과하는데
     * 실제 새로고침이 복원되지 않은 이유는, 첫 렌더의 화면이 `loading` 이고 그 화면의
     * 질의 문자열이 빈 문자열이어서, **프로젝트 조회가 끝나 `initialLocation()` 을 읽기
     * 전에** 이 효과가 주소를 지워 버렸기 때문이다.
     *
     * 변환 함수를 고칠 문제가 아니다. 아직 모르는 것을 주소에 쓰지 않는 것이 맞다.
     */
    if (current.name === "loading") return;
    const search = locationToSearch(current);
    if (lastSearch.current === search) return;
    const first = lastSearch.current === null;
    lastSearch.current = search;
    const url = `${window.location.pathname}${search}`;
    try {
      if (first) {
        // 최초 진입은 **교체**다. 앱을 열자마자 히스토리에 항목이 쌓이면 첫
        // 뒤로가기가 아무것도 하지 않는 것처럼 보인다.
        window.history.replaceState({ screen: current.name }, "", url);
      } else {
        window.history.pushState({ screen: current.name }, "", url);
      }
    } catch {
      // 히스토리를 못 쓰는 환경(파일 프로토콜 등)에서도 앱은 동작해야 한다.
      // URL 반영은 편의이고, 그것 때문에 화면이 죽으면 안 된다.
    }
  }, [current]);

  // URL → 화면 (뒤로가기·앞으로가기)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onPop = () => {
      const loc = searchToLocation(window.location.search);
      lastSearch.current = locationToSearch(loc);
      handler.current(loc);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
}

/**
 * 최초 로드 시 주소가 가리키는 화면.
 *
 * 새로고침 복원의 근거다 (FR-166). 결과 화면에서 새로고침하면 같은 결과 화면으로
 * 돌아온다.
 */
export function initialLocation(): WorkbenchLocation {
  if (typeof window === "undefined") return { name: "list" };
  return searchToLocation(window.location.search);
}
