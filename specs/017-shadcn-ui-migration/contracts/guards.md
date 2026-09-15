# Contract: 회귀 가드

**Feature**: 017 | **Status**: 계약 | **요구**: FR-004 · FR-007~FR-009 · FR-015 · FR-029 · FR-030 · SC-005 · SC-010

## 가드 한눈에

| # | 이름 · 파일 | 무엇을 막는가 | 017 에서 |
|---|---|---|---|
| G-A1 | `TailwindThemeLiteral` | 테마에 값 리터럴 | **범위 유지.** `--radius-*`·`--shadow-*`·`--text-*`·`--animate-*` 의 `initial` 이 키워드로 통과하는지 확인 |
| G-B | `ClassExistence` | 생성되지 않는 클래스 | 헬퍼 판정 문자 집합을 넓힌다 (아래 H-2). 이름공간을 비워 shadcn 기본 스케일이 여기서 걸린다 (research R4) |
| G-C | `SingleSystem` | 의미 클래스와 유틸리티 혼용 | 그대로 |
| G-D | `ClassMigration` | 해체한 의미 클래스의 재사용 | 그대로 |
| G-E | `ClassConflict` | 나중에 적은 클래스가 CSS 에서 진다 | **`cva`·`cn` 을 읽게 넓힌다** (H-1) |
| G-F | `UiSkin` **(신규)** | 부품에 shadcn 기본 모습·움직임·아이콘 묶음 | 아래 |
| G-G | `RawElements` **(신규)** | 부품 밖 원시 조작 요소 | 아래 |
| — | `FocusRing` | 초점 윤곽선 지우기 | `outline-hidden` 을 금지 목록에 더한다 |
| — | `InteractionStates` | 상태 스타일 유실 | 부품 파일이 `cva` 형태로 바뀐 뒤에도 **같은 상태 선언**을 찾는다 (판정 문자열만 갱신) |
| — | `ImplementationCount` | 구현이 또 한 벌 생긴다 | 옛 부품(`ui/Modal`·`ui/OverlayPane`·`SessionScreen` 지역 `Modal`·수제 행 메뉴)을 `RETIRED` 에 올린다 |
| — | `CanonMatchesDesign` · `CanonSplit` | 정본 이탈 | 그대로 (정본 무변경) |
| — | `BeforeAfterParity` (L2) | 조용한 시각 회귀 | 단계마다 보고서 갱신. 의도된 차이는 사유와 함께 |
| — | `ScreenSweep` **(신규)** | 화면 깨짐 | [screen-sweep.md](screen-sweep.md) SW-8 |

## H-1 — G-E 가 `cva`·`cn` 을 읽는다

**지금** (`tests/helpers/tailwind.ts:382~567`): `const NAME = "…"`·평평한 `Record` 표·
`[…].filter(Boolean).join(" ")` 의 칸을 풀어 조합을 만든다. 조립 38곳 중 37곳이 `src/ui` 에 있다.

**넓히는 것**:

1. `cva(BASE, { variants: { 축: { 값: "…" } }, compoundVariants: [...], defaultVariants })` 를 찾는다.
   `BASE` 는 리터럴이거나 같은 파일의 `const` 다.
2. 조합 = `BASE` × 축마다 값 하나. `compoundVariants` 항목은 **조건 축이 맞는 조합에만** 덧붙인다.
3. `cn(a, b, …)` 의 인자를 기존 조립의 칸과 같게 푼다 (리터럴 · `REC[x]` · `const` · 삼항 · `cond && "…"`).
4. 자체 점검 하한(`composed.length > 20`)을 유지한다. `cva` 로 옮긴 뒤 이 수가 20 이하로 떨어지면 헬퍼가
   `cva` 를 읽지 못하는 것이다.

**확인 (스파이크 S2)**: `ui/Button.tsx` 의 `cva` 에 역전(뒤에 적었는데 CSS 에서 지는 쌍)을 일부러 넣으면
G-E 가 실패한다. 되돌린다.

## H-2 — 상태 변종이 든 문자열을 버리지 않는다

**지금**: 클래스 목록 판정(`tailwind.ts:184`)이 토큰마다 `[a-zA-Z0-9_:./[\]#%!-]` 만 허용한다.
`data-[state=open]:bg-sunken` 의 `=` 때문에 **그 리터럴 전체**(옆 클래스 포함)가 G-B·G-C·G-E 에서 빠진다.
`ui/Table.tsx:162` 의 `[&>button[aria-pressed=true]]:…` 가 지금도 그렇다.

**넓히는 것**: 대괄호 **안에서만** `= & > ( ) , + * ~ " '` 를 허용한다. 대괄호 밖에서는 지금과 같다 —
SVG 경로(`"M4 4l4-4…"`)를 클래스로 오인하지 않던 성질을 지킨다.

**결과로 새로 걸리는 것은 고칠 대상이다.** 가드를 넓혔더니 실패한다면 그 실패는 전부터 있던 것이다.

## G-F — 부품의 모습 (신규 · `tests/UiSkin.test.ts`)

**대상**: `frontend/src/ui/**/*.tsx`

**금지** (주석 제외 소스에서):

| 형태 | 이유 |
|---|---|
| `opacity-` 를 쓰는 `disabled:` · `data-[disabled]:` · `has-[…:disabled]:` 변종 | 비활성은 점선으로 말한다 (FR-006) |
| `pointer-events-none` 을 쓰는 `disabled:` 변종 | 사유의 `title` 을 막는다 (FR-014) |
| `ring-` · `ring-offset-` (모든 변종) | 초점은 전역 윤곽선 (S-14) |
| `outline-none` · `outline-hidden` · `outline-0` | 같음 (`FocusRing` 과 이중으로) |
| `transition-` · `animate-` · `duration-` · `ease-` · `delay-` | 움직임 언어 없음 (FR-010) |
| `dark:` | 다크 모드 없음 |
| `data-open:` · `data-closed:` · `data-checked:` · `data-active:` 류 사용자 정의 변종 | 등록하지 않은 변종 |
| `from "lucide-react"` · `from "tailwind-merge"` · `from "cn"` · `tw-animate-css` | 들이지 않는 의존성 (research R2 · R5) |

**요구**:

- 조작 부품(`Button` · `Input` · `Textarea` · `NativeSelect` · `Checkbox` · `Radio`)의 변종 표에
  `disabled:border-dashed` 가 있다.
- `radix-ui` 가져오기는 [ui-parts.md](ui-parts.md) §1 에서 `behavior = radix` 인 파일에만 있다.
- 부품 파일 머리에 출처 줄(`shadcn` 원본이면 `new-york-v4/<item> @ shadcn 4.21.0`, 아니면 `015`)이 있다.

**확인 (SC-010)**: 부품 하나에 `rounded-md` 를 넣으면 G-B 가, `disabled:opacity-50` 을 넣으면 G-F 가
실패한다. 둘 다 되돌린다.

## G-G — 부품 밖 원시 조작 요소 (신규 · `tests/RawElements.test.ts`)

**대상**: `frontend/src/**/*.tsx` 중 `src/ui/` 밖. 주석 제외.

**센다**: JSX 여는 태그 `<button` · `<input` · `<select` · `<textarea`.

**통과 조건**: 센 자리가 `theme/exceptions.ts` 의 `axis: "raw-element"` 항목과 짝지어진다. 짝이 없는
자리는 실패로 파일·줄과 함께 보고한다. 짝이 없는 등록은 「죽은 예외」로 실패한다 (G-6 과 같다).

**전환 중 — 줄어드는 예산**: `REMAINING_BUDGET` 을 두고 화면을 옮길 때마다 내린다 (`ImplementationCount`
와 같은 규율).

- 센 수가 예산보다 **크면** 실패 — 새 원시 요소가 들어왔다.
- 센 수가 예산보다 **작으면** 실패 — 예산을 내리지 않았다. 예산이 커밋 이력에 남아 어느 단계에서 몇 개가
  줄었는지 보인다.
- 완료 조건: `REMAINING_BUDGET === 등록된 raw-element 예외 수` (SC-005).

**전환 전 기준값** (조사): 원시 `<button>` 50 · `<input>` 50 · `<select>` 4 · `<textarea>` 5 (앱 코드, 주석·
백틱 제외).

## 가드를 바꿀 때의 규칙

- 가드는 **넓히기만** 한다. 금지 목록에서 항목을 빼거나 하한을 낮추는 변경은 이 기능에서 하지 않는다.
- 가드를 넓혀 새로 실패하는 것은 가드를 좁혀 통과시키지 않고 **코드를 고친다.**
- 가드 파일의 머리주석에 무엇을 왜 넓혔는지 적는다 (FR-028).
