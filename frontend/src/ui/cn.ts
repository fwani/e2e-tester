/**
 * 클래스 잇기 — 거짓 값을 걸러 공백으로 잇는다. 그뿐이다. 017 T010 (research R5).
 *
 * ## shadcn 의 `cn` 과 이름은 같고 하는 일은 다르다
 *
 * shadcn 의 `cn` 은 `clsx` + `tailwind-merge` 다. 병합기는 같은 속성을 다투는 유틸리티
 * 가운데 **뒤에 적은 것만 남긴다** — 호출자가 `className` 으로 부품의 모양을 덮어쓰게 하려고
 * 있는 장치다. 이 저장소에서는 그것을 쓰지 않는다. 이유 셋:
 *
 * 1. **병합기는 이 테마를 모른다.** 실측(2026-09-15 · tailwind-merge 3.7): `h-9` + `h-control`,
 *    `rounded-md` + `rounded-base`, `shadow-xs` + `shadow-e1`, `px-3` + `px-s2` 를 **둘 다
 *    남긴다.** 정본 스케일을 전부 등록해야 동작하고, 등록이 빠진 축은 조용히 병합되지 않는다.
 * 2. **덮어쓰기가 금지다.** 부품은 `className` 을 받지 않고 `layout`(배치만)을 받는다
 *    (015 — 같은 버튼이 화면마다 달라지는 것을 막는다, SC-010). 덮어쓰기가 없으면 병합할
 *    충돌도 없고, 변종 표 **안의** 충돌은 가드 G-E 가 빌드 전에 잡는다.
 * 3. **번들** — 병합기가 gzip 8.5 kB 다. 동작 층(Radix 여섯 가지) 전체의 4분의 1이다.
 *
 * 그러므로 이 함수가 두 클래스를 모두 남기는 것은 결함이 아니라 설계다. 두 클래스가 같은
 * 속성을 다투면 그것을 **고치는 곳은 변종 표**다 (`tests/ClassConflict.test.ts`).
 */
export function cn(...parts: ReadonlyArray<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}
