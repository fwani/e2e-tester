# Contract: 정본 토큰 ↔ Tailwind 테마

**Feature**: 015 | **Status**: 계약 (구현이 지켜야 할 것)

## C-1 — 값은 정본 한 곳에만 있다

`frontend/src/theme/tokens.css` 의 `:root` 가 유일한 값의 출처다.
Tailwind 테마 파일은 **이름을 다시 붙이기만** 한다.

```css
/* frontend/src/theme/tailwind.css */
@theme inline {
  --color-pass: var(--pass);   /* ✅ 참조 */
  --color-pass: #1A7F45;       /* ❌ 값. C-1 위반 */
}
```

## C-2 — 정본 파일을 수정하지 않는다

`tokens.css` 는 `scripts/extract_canon.py` 의 출력이다. Tailwind 지시문을 그 안에 넣으면
다음 추출에서 사라진다. 모든 Tailwind 관련 선언은 `tailwind.css` 에 둔다.

## C-3 — 이름 규약

| 정본 축 | Tailwind 이름공간 | 예 |
|---|---|---|
| 색 | `--color-*` | `--pass` → `--color-pass` → `bg-pass` `text-pass` |
| 간격 | `--spacing-*` | 정본 간격 토큰 → `p-*` `gap-*` |
| 타이포 | `--font-*` `--text-*` | `--font-sans` → `--font-sans` (그대로) |
| 모서리 | `--radius-*` | `--radius` → `--radius-DEFAULT` |
| 그림자 | `--shadow-*` | `--e-1` `--e-2` → `--shadow-e1` `--shadow-e2` |

**정본에 없는 이름을 만들지 않는다.** 대응표에 없는 Tailwind 이름이 필요해지면,
그것은 정본에 없는 값을 쓰려 한다는 신호다 — 멈추고 기록한다 (FR-003).

## C-4 — 임의값 문법의 제한

`bg-[#1A7F45]` 같은 임의값 표기는 **색과 시각 속성에 금지**한다. 값 리터럴을 화면 코드로
되돌리는 것이고, 008 이 고친 문제의 재발이다.

**배치 치수의 임의값은 허용한다** — `basis-[460px]` 처럼. 다만 그 숫자는 `lib/layout.ts`
또는 상수 모듈에서 와야 하며, 화면 파일이 지어낼 수 없다 (007 계약에서 그대로 이어짐).

## C-5 — 가드

| # | 검사 | 실패 조건 |
|---|---|---|
| G-A1 | `tailwind.css` 에 리터럴 값 없음 | `var(…)` 가 아닌 오른쪽 값 발견 |
| G-A2 | `.tsx` 에 색 리터럴 없음 | 기존 `count-violations.mjs` 규칙 유지 |
| G-A3 | `tokens.css` 무변경 | 이 기능의 커밋에서 정본 구획이 바뀜 |
