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

/** URL 로 표현할 수 있는 화면. 세션처럼 수명이 짧은 것은 식별자만 싣는다. */
export interface ScreenLocation {
  name: string;
  testId?: string | null;
  sessionId?: string | null;
}

const PARAM = "screen";

/** 화면 상태를 질의 문자열로. 목록은 `/` 다 — 기본 화면에 파라미터를 남기지 않는다. */
export function locationToSearch(loc: ScreenLocation): string {
  if (loc.name === "list" || loc.name === "loading" || loc.name === "setup") return "";
  const params = new URLSearchParams();
  params.set(PARAM, loc.name);
  if (loc.testId) params.set("test", loc.testId);
  if (loc.sessionId) params.set("session", loc.sessionId);
  return `?${params.toString()}`;
}

/** 질의 문자열을 화면 상태로. 알 수 없는 값은 목록으로 떨어뜨린다. */
export function searchToLocation(search: string): ScreenLocation {
  const params = new URLSearchParams(search);
  const name = params.get(PARAM);
  if (!name) return { name: "list" };
  return {
    name,
    testId: params.get("test"),
    sessionId: params.get("session"),
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
  current: ScreenLocation,
  onPopState: (loc: ScreenLocation) => void,
): void {
  const lastSearch = useRef<string | null>(null);
  const handler = useRef(onPopState);
  handler.current = onPopState;

  // 화면 → URL
  useEffect(() => {
    if (typeof window === "undefined") return;
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
export function initialLocation(): ScreenLocation {
  if (typeof window === "undefined") return { name: "list" };
  return searchToLocation(window.location.search);
}
