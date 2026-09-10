/**
 * `count-violations.mjs` 의 타입 선언.
 *
 * 계수기는 `.mjs` 로 두고(사람이 직접 돌리는 도구다) 검사는 TypeScript 다. 검사가
 * 규칙을 **가져다 쓰려면** 타입이 필요하고, 규칙을 복제하지 않는 것이 그보다 중요하다
 * (015 T052 · 008 「규칙을 두 곳에 두면 그것 자체가 결함」).
 */
declare module "*/count-violations.mjs" {
  /** G-2 의 속성 목록에서 만든 정규식 원본. 검사가 자기 플래그로 다시 만든다. */
  export const VISUAL_PROP_SOURCE: string;
  export const SRC_ROOT: string;
  export const REPO_ROOT: string;
  export function canonColors(): Set<string>;
  export function screenFiles(root?: string): string[];
  export function scan(
    text: string,
    palette?: Set<string>,
  ): { line: number; axis: string; value: string; offPalette: boolean }[];
}
