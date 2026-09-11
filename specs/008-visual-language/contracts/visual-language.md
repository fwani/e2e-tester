# 계약 — 시각 언어 정본

**대상**: `frontend/src/theme/tokens.css` · `frontend/src/theme/exceptions.ts` · 화면 파일 33개
**요구사항**: FR-263 ~ FR-273 · FR-278 · FR-279
**기존 계약과의 관계**: [`specs/007-unify-test-screens/contracts/ui-contract.md`](../../007-unify-test-screens/contracts/ui-contract.md) 를 **대체하지 않는다.** 아래 §0 이 경계를 긋는다.

---

## §0 — 무엇이 이 계약의 관할인가

두 계약이 같은 화면을 다루므로 경계를 먼저 긋는다. 007→008 사이에 이 경계가 흐려서 값이 두 곳에
생겼다.

| | 이 계약 (시각 언어) | 007 `ui-contract.md` (배치) |
|---|---|---|
| 다루는 것 | 색 · 서체 · 모서리 · 그림자 · 형태(조작·칩·행·패널) · 상태 표현 | 층의 순서 · 자리의 크기 배분 · 무엇이 어느 국면에 열리는가 |
| 정본 | `theme/tokens.css` | `ui-contract.md` §1-2 표 · `lib/layout.ts` |
| 표현 수단 | **CSS 클래스** | **인라인 `style` + 타입 표** |
| 왜 다른가 | 형태는 33곳에서 반복되므로 클래스가 중복을 없앤다 | 배치는 국면별 판단이라 `Record<Phase, …>` 의 컴파일 시점 강제가 필요하다 (007 S-05·S-12 가 그 강제 없이 생긴 결함이다) |

**겹치는 수치의 처리**: 껍데기 치수(56·48·32·52·460·640·1440)는 **양쪽에 나타난다.**
`ui-contract.md` §1-2 표가 정본이고 `tokens.css` 는 사본이다. 사본이 정본과 다르면 검사가
멈춘다 (아래 C-5).

---

## §1 — 정본의 의무

- **C-1 (유일성)** 시각 언어의 값은 `theme/tokens.css` 에만 존재한다. 화면 파일은 그 값을 다시
  적지 않는다
- **C-2 (추출)** 정본의 값은 `docs/design/008-visual-language/*.dc.html` 의 `<style>` 블록에서
  **기계적으로** 온다. 사람이 값을 고르거나 다듬는 단계가 없다
- **C-3 (무증식)** 확정 디자인에 나타나지 않는 값을 정본에 추가할 수 없다. 추가하려면 먼저
  디자인에서 그 값을 찾아야 한다
- **C-4 (이름 보존)** 형태의 이름과 뜻은 확정 디자인 그대로다 — `.btn` `.chip` `.srow` `.pane`
  `.lbl` `.mono` `.why` `.hdr` `.phase` `.notice` `.body` `.left` `.steps` `.steps-hd` 와 변형
  13개, 합 27종
- **C-5 (사본 일치)** 껍데기 치수 토큰은 `ui-contract.md` §1-2 표와 값이 같아야 한다

> **C-2 의 예외 하나 — 토큰 *이름*.** dc.html 은 축약형(`--r` `--sans` `--e-1`), 현행 코드는
> 서술형(`--radius` `--font-sans` `--e-1`)을 쓴다. **이름은 현행을 유지하고 값만 정본에서 받는다.**
> 이름을 바꾸면 이미 옳게 쓰이는 46곳이 함께 깨지는데, 대조 대상은 이름이 아니라 값이다.
> 추출기가 이름 대응표를 갖는다.

---

## §2 — 소비의 의무 (화면 파일 33개)

- **C-6 (색 금지)** 화면 파일에 색 리터럴을 적을 수 없다 — `#rgb` `#rrggbb` `rgb(` `rgba(` `hsl(`
- **C-7 (형태 금지)** 시각 언어 속성을 인라인으로 선언할 수 없다 —
  `background` `border` `borderRadius` `boxShadow` `font` `fontSize` `fontWeight` `fontFamily`
  `color` `letterSpacing`
- **C-8 (클래스 한정)** 정본이 정의하지 않은 클래스 이름을 쓸 수 없다
- **C-9 (형태 사용)** 조작·상태 표식·Step 행·패널은 정본의 형태로 그린다. 같은 모양을 인라인으로
  다시 만들지 않는다
- **C-10 (주 동작 1개)** `.btn.primary`(잉크 채움)는 한 화면에 하나다

### 허용되는 인라인 `style`

> ## ⚠️ 이 절은 015 가 개정했다 (2026-09-11)
>
> **지우지 않는다** — 왜 이 목록이 있었는지가 기록으로 남아야 한다.
>
> 015 「Tailwind CSS 전환」이 배치까지 유틸리티 클래스로 옮기면서 이 허용 목록을
> 폐지했다. 대체 계약은
> [`specs/015-tailwind-css-migration/contracts/layout-contract-v2.md`](../../015-tailwind-css-migration/contracts/layout-contract-v2.md)
> 이며, 인라인에 남을 자격은 **런타임 계산값**뿐이다 (LC-3).
>
> **개정된 것은 표현이지 구조가 아니다.** `lib/layout.ts` 의 `Record<Phase, …>` 표와
> 「부모가 자식에 내려준다」는 흐름은 그대로다 — 007 이 S-12(편집 국면에서 두 자리가
> 뒤바뀜)를 고치며 세운 성질은 개정 대상이 아니었다 (015 FR-020).
>
> 아래 목록은 **2026-09-11 이전의 규칙**이다.

C-7 이 금지하지 않는 것만. 아래는 **배치**이며 007 계약의 관할이다.

`display` · `flex` · `flexGrow` · `flexBasis` · `flexDirection` · `gap` · `gridTemplateColumns` ·
`width` · `minWidth` · `maxWidth` · `height` · `minHeight` · `maxHeight` · `padding` · `margin` ·
`position` · `top`/`right`/`bottom`/`left` · `zIndex` · `overflow` · `alignItems` ·
`justifyContent` · `textAlign` · `whiteSpace` · `textOverflow`

> 치수 값은 정본 토큰 또는 `lib/layout.ts` 에서 와야 하며, 화면 파일이 지어낼 수 없다.

---

## §3 — 예외

- **C-11** 정본을 벗어나야 하는 값은 `theme/exceptions.ts` 에 등록되어야 한다
- **C-12** 등록 항목은 `file` · `pattern` · `axis` · `reason` 을 갖는다. **`reason` 이 비면 등록이
  아니다**
- **C-13** 등록되지 않은 예외는 존재할 수 없다 — 가드가 잡는다
- **C-14** 등록되었으나 실제로 쓰이지 않는 항목(죽은 예외)은 가드가 보고한다

---

## §4 — 가드 (기계가 세는 것)

**자리**: `frontend/tests/VisualLanguage.test.tsx`
**대상 열거**: `import.meta.glob("../src/**/*.tsx", { query: "?raw", eager: true })` —
**손으로 import 하지 않는다.** 새 파일이 자동으로 대상이 된다 (V-09 의 원인 제거)

| 축 | 세는 것 | 계약 |
|---|---|---|
| G-1 | 색 리터럴 | C-6 |
| G-2 | 시각 언어 속성의 인라인 선언 | C-7 |
| G-3 | 정본에 없는 클래스 이름 | C-8 |
| G-4 | 정본에 있으나 dc.html 에 없는 값 | C-3 |
| G-5 | 껍데기 치수 사본 ↔ `ui-contract.md` §1-2 | C-5 |
| G-6 | 죽은 예외 | C-14 |

**보고 형식** (FR-279):

```
frontend/src/pages/TestList.tsx:371 — 색 리터럴 '#14171C' (G-1)
frontend/src/pages/TestList.tsx:371 — 인라인 'background' (G-2)
```

수치만 보고하는 검사는 고칠 곳을 알려주지 못하므로 계약 위반이다.

### 엄격도 전이

| 단계 | 상한 | 뜻 |
|---|---|---|
| 0 | 327 (측정된 현재값) | 경고. 33파일이 전부 위반 상태이므로 처음부터 실패시키면 첫 커밋도 못 만든다 |
| 1~3 | 단계마다 내림 | 상한은 **내려가기만 한다** |
| 4 | **0** | 위반 1건이면 실패 |

상한을 올리려면 커밋 본문에 이유를 적어야 한다. 조용히 올릴 수 없다.

---

## §5 — 이 계약이 하지 않는 것

- **배치를 정하지 않는다.** 층의 순서·자리 크기·국면별 열림은 007 계약 관할이다
- **동작을 정하지 않는다.** 무엇을 보여줄지·언제 비활성인지는 각 기능의 FR 이 정한다
- **확정 디자인을 고치지 않는다.** dc.html 18장은 입력이다. 디자인 쪽 문제는 불일치로 기록하고
  별도 개정으로 넘긴다
- **반응형을 정하지 않는다.** 최소 기준 폭 1440 규칙을 유지할 뿐이다
