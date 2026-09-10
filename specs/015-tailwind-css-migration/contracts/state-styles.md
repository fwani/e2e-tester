# Contract: 상태 스타일 이관 목록

**Feature**: 015 | **Status**: 살아 있는 문서 (T067) | **작성**: 2026-09-10

## 왜 이 문서가 있는가

정본(`tokens.css`)을 `layer(base)` 로 들여야 Tailwind 유틸리티가 이긴다. 그러지 않으면
요소 규칙(`button{…}`)이 레이어 밖에서 모든 레이어를 이겨 **015 가 통째로 막힌다**
([tailwind-theme.md](tailwind-theme.md) C-8).

그 해결이 대가를 만든다. **요소 규칙의 상태 스타일도 함께 base 로 내려가 유틸리티에 진다.**

```
button:hover { background: var(--sunken-2) }      ← @layer base
.bg-panel    { background-color: var(--panel) }   ← @layer utilities  ✅ 이긴다
```

부품에 `bg-panel` 을 붙이면 **hover 상태에서도 `bg-panel` 이 이겨 배경 변화가 사라진다.**

**이 회귀는 눈으로 잡히지 않는다.** 화면은 멀쩡해 보이고 테스트도 통과한다 —
마우스를 올리거나, Tab 키를 누르거나, 비활성 상태를 만들어야만 보인다.
`ui/Button` 에서 실제로 겪었다 (T016).

FR-009(상호작용 상태 보존)와 SC-008(초점 표시 0건 유실)이 이것을 요건으로 못 박은 이유다.

## 규칙

**부품을 만들 때 아래 목록에서 그 부품에 해당하는 줄을 찾아 함께 옮긴다.**
옮긴 줄은 `이관` 칸에 부품 이름을 적는다. **빠뜨리면 조용한 회귀가 된다.**

## 목록 — 상태 규칙 17개 (2026-09-10 실측)

### 요소 규칙 (레이어 강등의 영향을 받는다)

| # | 셀렉터 | 선언 | 이관 |
|---|---|---|---|
| S-01 | `button:hover` | `background: var(--sunken-2)` | ✅ `ui/Button` BASE `hover:bg-sunken-2` |
| S-02 | `button:active` | `box-shadow: none` | ✅ `ui/Button` BASE `active:shadow-none` |
| S-03 | `button:disabled` | 점선 테두리·투명 배경·`--ink-3`·그림자 없음·`font-weight:500`·`cursor:not-allowed` | ✅ `ui/Button` BASE `disabled:*` |
| S-04 | `button.ghost:hover` | `background: var(--sunken)` | ✅ `ui/Button` VARIANT.ghost `hover:bg-sunken` |
| S-05 | `button.danger:hover` | `background: var(--fail-t)` | ✅ `ui/Button` VARIANT.danger `hover:bg-fail-t` |
| S-06 | `input::placeholder`, `textarea::placeholder` | `color: var(--ink-3)` | ✅ `ui/Field` Field `[&_input]:placeholder:text-ink-3` |
| S-07 | `input:disabled`, `select:disabled`, `textarea:disabled` | 투명 배경·점선 테두리·`--ink-3` | ✅ `ui/Field` Field `[&_input]` disabled 계열 |
| S-08 | `input.phase-name:hover:not(:disabled)` | `border-color: var(--hair-2)` | ⬜ 국면 이름 입력 (T026) |
| S-09 | `input.phase-name:focus` | `border-color: var(--hair-2)`·`background: var(--panel)`·`outline: none` | ⬜ 국면 이름 입력 (T026) |
| S-10 | `input.phase-name:disabled` | `border-color: transparent`·`color: var(--ink-2)` | ⬜ 국면 이름 입력 (T026) |
| S-11 | `.tabs > button:disabled` | `border-style: solid`·`color: var(--ink-3)` | ✅ `ui/Table` Tabs `[&>button:disabled]` |
| S-12 | `.segmented > button:disabled` | 투명 배경·`border-style: solid`·`--ink-3` | ⬜ 분절 조작 (T027) |
| S-13 | `.srow-check input[type="checkbox"]:disabled` | `cursor: default`·`opacity: .4` | ✅ `ui/StepRow` StepCheck `[&_input:disabled]` |

### 클래스 규칙 (레이어 안에서도 특이도로 이길 수 있으나, 함께 옮긴다)

| # | 셀렉터 | 선언 | 이관 |
|---|---|---|---|
| S-14 | `:focus-visible` | `outline: 2px solid var(--run)`·`outline-offset: 2px` | ⬜ **전역** — T068 가드가 지킨다 |
| S-15 | `.navlink:hover` | `background: var(--sunken)` | ⬜ 수식 군 (T027) |
| S-16 | `.btn.file:focus-within` | `outline: 2px solid var(--run)`·`outline-offset: 2px` | ✅ `ui/Field` FileButton `focus-within:outline-run` |
| S-17 | `.btn.disabled:focus-within` | `outline: 2px solid var(--hair-2)`·`outline-offset: 2px` | ✅ `ui/Field` FileButton off `focus-within:outline-hair-2` |

**진행**: 이관 12 / 17 (S-15 `.navlink:hover` 가 유틸리티 대응표에 들어가며 함께 옮겨졌다).

남은 것은 S-08~S-10(국면 이름 입력)·S-12(분절 조작)·S-14(전역 초점 링)다.
S-14 는 옮기는 것이 아니라 **지우지 않는 것**이 요구이며 T068 가드가 지킨다.
나머지 넷은 그 부품이 아직 해체되지 않았다 — 해체할 때 함께 옮긴다.

**이관된 것이 실제로 지켜지는지는 `tests/InteractionStates.test.tsx`(T058)가 본다.**
hover 하나를 지우거나 초점 링의 한 분기만 지워도 잡는 것을 확인했다.

## S-14 는 특별하다 — 지우는 것이 회귀다

`:focus-visible` 전역 규칙은 「초점 링을 지우지 않는다. 키보드로 도는 도구다」라는 주석과
함께 정본에 있다. 부품이나 화면에 `outline-none` 계열 유틸리티가 하나라도 들어가면
**그 요소의 초점 링이 사라진다.**

S-09 (`input.phase-name:focus { outline: none }`) 는 **의도된 예외**다 — 테두리 색으로
초점을 표시하므로 링을 뺀다. 이런 예외는 `theme/exceptions.ts` 에 이유와 함께 등록한다.

가드는 T068 (`FocusRing.test.tsx`) 이다.
