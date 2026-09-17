/**
 * 라우터가 화면을 그리지 못하는 동안의 두 화면 (018 design §2 · §5).
 */
import { useEffect } from "react";
import { useRouteError } from "react-router";

import { paths } from "../lib/paths";
import { ButtonLink } from "../ui/Button";

/**
 * 첫 조회(열린 프로젝트) 동안의 화면. 옛 `App.tsx` 의 `loading` 화면 그대로다.
 *
 * 실브라우저 하니스가 `main` 이 뜨기를 기다리므로 요소를 바꾸지 않는다 (`ui_context.py` 의 `open`).
 */
export function Loading() {
  return <main className="p-s6 text-ink-2">불러오는 중…</main>;
}

/**
 * 렌더 예외를 받는 루트 오류 화면. 018 전에는 흰 화면이었다.
 *
 * 「목록으로」는 **문서를 새로 연다** (`onNavigate` 없음). 예외가 난 앱의 상태를 믿고 그 안에서 옮기면
 * 같은 예외를 다시 밟을 수 있다. 원인은 콘솔에 남긴다 — 보고할 것이 거기 있다.
 */
export function RouteErrorScreen() {
  const error = useRouteError();
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <main className="p-s6 text-ink-2 flex flex-col items-start gap-s2">
      <div>화면을 그리지 못했습니다. 목록에서 다시 시작하세요.</div>
      <ButtonLink href={paths.list()}>목록으로</ButtonLink>
    </main>
  );
}
