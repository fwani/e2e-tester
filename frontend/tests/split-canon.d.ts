/**
 * `split-canon.mjs` 의 타입 선언.
 *
 * 뽑는 도구는 `.mjs` 로 둔다 — 사람이 직접 돌리고(`node scripts/split-canon.mjs`)
 * 빌드 이전에 실행되기 때문이다. 검사가 그 규칙을 **가져다 써야** 낡음을 판정할 수
 * 있고, 규칙을 복제하지 않는 것이 그보다 중요하다 (`count-violations.d.ts` 와 같은 이유).
 */
declare module "*/split-canon.mjs" {
  /** 정본 원본 경로 (`src/theme/tokens.css`). */
  export const SOURCE: string;
  /** 앱이 들이는 산출물 경로 (`src/theme/tokens.app.css`). */
  export const TARGET: string;
  /** 정본 CSS 에서 `:root` 변수와 요소 규칙만 남긴다. 의미 클래스 규칙은 뺀다. */
  export function splitCanon(css: string): string;
}
