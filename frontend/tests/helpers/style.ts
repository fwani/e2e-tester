/**
 * 요소의 배치 성질을 **인라인과 클래스 양쪽에서** 읽는다. 015.
 *
 * ## 왜 필요한가
 *
 * 015 가 배치를 인라인 `style` 에서 Tailwind 유틸리티로 옮기는 중이라, 전환된 화면과
 * 아직인 화면이 공존한다. 검사가 `element.style.flex` 만 읽으면 전환된 화면에서
 * **빈 문자열**을 보고 실패한다 — 화면은 멀쩡한데 검사만 깨진다.
 *
 * 그렇다고 클래스 이름만 읽으면 아직 전환하지 않은 화면을 놓친다.
 *
 * 두 표기를 같은 뜻으로 환산해 읽으면, 검사가 **묻는 것**(「버튼이 줄어들지 않는가」,
 * 「이유 문구가 말줄임하는가」)이 전환 중에도 그대로 성립한다. 판정 방법만 바꾸고
 * 검증 대상은 유지한다는 것이 이 저장소의 규율이고 (헌법 Quality Gate 4 ·
 * contracts/layout-contract-v2.md LC-6), 이 헬퍼가 그것을 한 곳에서 처리한다.
 *
 * ## 한계
 *
 * jsdom 은 CSS 를 계산하지 않으므로 **선언된 것**만 읽는다. 클래스가 실제로 그 CSS 를
 * 만드는지는 가드 G-B(`ClassExistence.test.ts`)가 따로 본다 — 셋으로 나뉜 검증의
 * 두 번째 겹이다 (LC-4).
 */

/** `flex` 축약값. 인라인 `flex: "0 0 auto"` 와 유틸리티 `flex-none` 을 같게 읽는다. */
export function flexOf(el: HTMLElement): string {
  if (el.style.flex !== "") return el.style.flex;
  const c = el.className;
  if (/\bflex-none\b/.test(c)) return "0 0 auto";
  if (/\bflex-1\b/.test(c)) return "1 1 0%";
  if (/\bflex-initial\b/.test(c)) return "0 1 auto";
  if (/\bflex-auto\b/.test(c)) return "1 1 auto";
  const arb = /\bflex-\[([^\]]+)\]/.exec(c);
  if (arb !== null) return (arb[1] as string).replace(/_/g, " ");
  return "";
}

/**
 * 「이 요소가 줄어들 수 있는가」 — `flex-shrink` 가 0 이 아닌가.
 *
 * `flex` 축약 말고 **`shrink-0` 단독 유틸리티**도 읽는다 (2026-09-11). 축약은 basis 까지
 * 함께 정하므로, 「높이는 내용이 정하되 줄지는 않는다」를 말할 때는 `shrink-0` 만 붙는
 * 것이 맞다 — `ChatPanel` 의 입력 폼이 그 경우다. 이것을 못 읽으면 선언이 있는데도
 * 「없으므로 기본값 1」로 판정해 검사가 헛돈다.
 */
export function canShrink(el: HTMLElement): boolean {
  if (el.style.flexShrink !== "") return Number.parseFloat(el.style.flexShrink) !== 0;
  if (/\bshrink-0\b/.test(el.className)) return false;
  const f = flexOf(el);
  if (f === "") return true; // 선언이 없으면 기본값(1)이다
  const parts = f.split(/\s+/);
  return parts[1] !== "0";
}

/** 「최소 폭이 0 으로 풀려 있는가」 — 없으면 flex 자식이 내용 폭 밑으로 줄지 못한다. */
export function minWidthIsZero(el: HTMLElement): boolean {
  const inline = el.style.minWidth;
  if (inline !== "") return Number.parseFloat(inline) === 0;
  return /\bmin-w-0\b/.test(el.className);
}

/** 「최소 높이가 0 으로 풀려 있는가」 — 스크롤 영역이 자기 높이를 줄일 수 있는 조건. */
export function minHeightIsZero(el: HTMLElement): boolean {
  const inline = el.style.minHeight;
  if (inline !== "") return Number.parseFloat(inline) === 0;
  return /\bmin-h-0\b/.test(el.className);
}

/** 「말줄임하는가」 — `nowrap` + `ellipsis` + `overflow:hidden` 셋이 함께 있어야 한다. */
export function truncates(el: HTMLElement): boolean {
  const c = el.className;
  const nowrap = el.style.whiteSpace === "nowrap" || /\bwhitespace-nowrap\b/.test(c);
  const ellipsis = el.style.textOverflow === "ellipsis" || /\btext-ellipsis\b|\btruncate\b/.test(c);
  const hidden = el.style.overflow === "hidden" || /\boverflow-hidden\b|\btruncate\b/.test(c);
  return nowrap && ellipsis && hidden;
}

/** 「폭 상한이 있는가」 — 없으면 긴 문구가 띠를 밀어낸다. */
export function hasMaxWidth(el: HTMLElement): boolean {
  return el.style.maxWidth !== "" || /\bmax-w-/.test(el.className);
}

/** 세로로 쌓이는가 (`column`) / 가로로 서는가 (`row`). */
export function stackDirection(el: HTMLElement): string {
  if (el.style.flexDirection !== "") return el.style.flexDirection;
  if (/\bflex-col\b/.test(el.className)) return "column";
  if (/\bflex-row\b/.test(el.className)) return "row";
  return "";
}

/** 스크롤 영역인가 — 넘치는 것을 자기 안에서 처리하는가. */
export function scrolls(el: HTMLElement): boolean {
  const c = el.className;
  return (
    ["auto", "scroll"].includes(el.style.overflowY) ||
    ["auto", "scroll"].includes(el.style.overflow) ||
    /\boverflow-y-auto\b|\boverflow-auto\b|\boverflow-y-scroll\b/.test(c)
  );
}
