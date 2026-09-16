# Research: shadcn/ui 부품 체계 전환과 화면 깨짐 전수 수정

**Feature**: 017 | **Date**: 2026-09-15 | **Phase**: 0

계획 전에 정해야 했던 12가지다. 각 항목은 **결정 · 근거 · 버린 대안** 순이다. 조사는 네 갈래로
나눠 돌렸다 — 화면 코드 전수 목록, 테스트·가드 영향, 깨짐 11건의 원인, shadcn v4 원본(레지스트리
JSON·`shadcn@4.21.0` 을 버리는 앱에 실제로 `init`/`add`·jsdom 에서 Radix 실제 동작·esbuild 크기).
사실은 전부 실측이며, 아직 검증되지 않은 것은 그렇다고 적었다.

---

## R1 — shadcn 을 어떻게 들이는가: CLI 가 아니라 원본 이식

**결정**: 저장소에 `components.json` 을 두지 않고 `shadcn init`/`add` 를 저장소 안에서 돌리지
않는다. `shadcn@4.21.0` 레지스트리(`new-york-v4`)의 부품 원본을 받아 **`frontend/src/ui/` 에 손으로
이식**한다. 이식하며 모든 클래스를 정본 이름으로 바꾸고(→ [ui-parts.md](contracts/ui-parts.md) §2),
파일 머리에 출처(스타일·항목·CLI 버전·받은 날짜)를 적는다.

**근거**:

1. **`init` 이 CSS 에 쓰는 것을 끌 수 없다.** 실측 — `init` 은 `@import "tw-animate-css"`·
   `@import "shadcn/tailwind.css"`·Geist 글꼴·`@custom-variant dark`·oklch `:root`/`.dark`·
   `@layer base { *{@apply border-border outline-ring/50} … }` 를 쓴다. 끄는 옵션이 없다
   (`--no-css-variables` 뿐). 그 하나하나가 015 C-1(값은 정본에만)·C-8(preflight 없음)·
   `TailwindThemeLiteral` 을 깬다.
2. **CSS 파일을 잘못 고른다.** CLI 는 `@import "tailwindcss"` 가 있는 첫 CSS 를 찾는데, 이 저장소는
   `tailwindcss/theme.css`·`utilities.css` 를 따로 들여 그 문자열이 없다. 실측에서 엉뚱한 파일을 잡았다.
3. **`add` 는 CSS 를 건드리지 않지만** 설치 의존성이 따라온다 — `lucide-react`·`tw-animate-css`·
   `cn`(npm)·`@fontsource-variable/geist`, `sonner` 는 `next-themes` 까지. 전부 FR-010 이 막는 것이다.
4. **어차피 전부 고친다.** 부품 18종 원본의 클래스 중 정본 밖이 대부분이다(§R3 표). CLI 가 쓴 파일을
   통째로 고쳐야 한다면 CLI 가 주는 것은 첫 복사뿐이고, 다음 `add` 는 고친 파일을 덮어쓴다.

**`src/ui/` 를 쓰는 이유** (shadcn 관례는 `src/components/ui/`): 테스트 5개가 `src/ui/` 경로를,
그중 4개가 파일 이름(`src/ui/Button.tsx` 등)을 박고 있다(`DesignTokens`·`InteractionStates`·
`FocusRing`·`ToastDismiss`·`ToastPlacement`·`NoticesAreToasts`). 015 가 세운 「`ui/` 는 도메인을 모르고
`components/` 는 안다」는 구분도 그대로다. **옛 부품과 새 부품이 공존하지 않도록 같은 자리에서
교체한다** (FR-003). 파일 이름도 저장소 관례(PascalCase)를 따른다 — 대소문자만 다른 `button.tsx` 는
macOS 파일 시스템에서 `Button.tsx` 와 충돌한다.

**버린 대안**:

| 대안 | 버린 이유 |
|---|---|
| `shadcn init` 후 CSS 되돌리기 | 다음 `init`/업데이트마다 되돌려야 한다. 되돌림을 빠뜨리면 정본이 둘이 된다 |
| `components.json` 을 두고 `tailwind.css` 를 미끼 파일로 가리키기 | 동작한다(조사 확인). 그러나 `add` 가 받아 온 원본은 어차피 전부 고쳐야 하고, 고친 뒤 다시 `add` 하면 덮어쓴다. 미끼 파일이라는 거짓 설정이 저장소에 남는다 |
| `src/components/ui/` 로 옮기기 | 경로를 박은 테스트 5개가 판정 방법이 아니라 **경로 때문에** 바뀐다. 검증 대상이 같은데 고칠 곳만 늘어난다 |

---

## R2 — 동작 층: 무엇을 표준 부품으로, 무엇을 네이티브로

> **2026-09-16 개정 — 갈래를 Radix 에서 Base UI 로 바꾼다.**
>
> **놓친 사실**: shadcn 은 **2026-07 부터 Base UI 를 기본 갈래로 쓴다.** 부품마다 Base UI · React
> Aria · Radix 세 갈래가 있고 설정 없이 받으면 Base UI 가 온다(공식 문서·CLI 로 확인). 이 조사는
> 「Radix 냐 네이티브냐」만 따졌고 **기본 갈래가 두 달 전에 바뀐 사실을 확인하지 않았다.** 그래서
> 아래 표의 「동작 층」 칸이 처음에 `radix-ui` 로 적혔다.
>
> **무엇이 바뀌고 무엇이 그대로인가**: 바뀌는 것은 **갈래 하나**다. 무엇을 표준 부품으로 두고
> 무엇을 네이티브로 둘지, 그 이유(아래 근거 문단들)는 그대로다. 확인한 사실 —
> `@base-ui/react` 1.8.0 · peer React 17~19 · 날짜 부품 peer 는 선택 사항 · 자리 계산은 같은
> floating-ui · 트리셰이킹 지원.

**결정** (동작 층 = `@base-ui/react`):

| 부품 | 동작 층 | 이유 |
|---|---|---|
| 대화상자 · 확인 대화상자 | `Dialog` · `AlertDialog` (Root/Trigger/Portal/**Backdrop**/**Popup**) | 초점 이동·가두기·Esc·되돌리기가 **전환 전에 하나도 없었다** (FR-011). 초점은 `initialFocus`/`finalFocus` 속성이 맡는다 — 017 이 손으로 만든 `useReturnFocus` 가 사라진다 |
| 행 메뉴 | `Menu` (Root/Trigger/Portal/**Positioner**/Popup/Item) | 키보드 열기·화살표·Esc·바깥 클릭이 없었다 (FR-012). 자리 속성은 `Positioner` 가, 닫힌 뒤 초점은 Popup `finalFocus` 가 갖는다 |
| 산출물 탭 | `Tabs` (Root/List/**Tab**/**Panel**) | `aria-pressed` 버튼 줄에 `tablist` 가 없었다. 선택 상태는 `data-active` |
| 분절 선택 (실행 속도 · 목록 거르기·정렬 · 삽입 종류) | `ToggleGroup` + `Toggle` (기본이 배타 선택) | 서로 배타적인 선택이며 화살표 이동이 없었다 (FR-013). 상태는 **눌림**(`aria-pressed`)으로 알린다 — R6 개정 |
| 잘린 글자·아이콘 단추의 전체 이름 | `Tooltip` (공급자는 **앱 뿌리에 하나**) | `title` 은 키보드로 볼 수 없다 (FR-019). 초점에도 뜬다 |
| 버튼 다형성 | **`render` prop** (`asChild`·`Slot` 없음) | 부모가 `render={<Button/>}` 로 우리 부품을 받는다. `mergeProps` 가 핸들러를 모두 실행하고 클래스를 잇는다 |
| **체크박스 · 라디오** | **네이티브 `<input>`** | 아래 |
| **선택칸** | **네이티브 `<select>`** (shadcn `native-select`) | 아래 |
| **펼침(▸/▾)** | **네이티브 `<details>`** | 아래 |
| 입력 · 여러 줄 입력 · 라벨 · 표 · 칩 | 원시 요소 (shadcn 도 동작 층을 쓰지 않는다) | — |
| 토스트 | **`Toast`** (Provider/Portal/Viewport/Root + 관리자) | R6 개정 — 손으로 만든 알림 층·퇴장 처리를 대신한다 |
| Step 상세 판 | `Dialog` **`modal={false}`**, 포털 없음 | 아래 R7 |

**체크박스·라디오를 네이티브로 두는 근거**:

1. **모습이 정본이다.** 정본의 체크 상자는 `accent-color:var(--ink)` 로 그린 네이티브 14px 상자이고
   「결말 아이콘(✓·X·점)과 형태가 갈리는 유일한 사각형」이다(`tokens.css` `.srow-check`). Radix
   `Checkbox` 는 `<button role="checkbox">` 에 표시를 직접 그리므로 **모습을 새로 만들어야 한다** —
   사용자 결정 1(모습은 정본)과 부딪친다.
2. **동작 이득이 없다.** 네이티브 체크박스·라디오는 이미 상태를 보조기술에 알리고 Space·화살표가
   동작한다. Radix 가 더하는 것은 스타일 자유뿐이다.
3. **테스트가 `.checked`·`tagName === "INPUT"`·`input[type=checkbox]` 를 읽는다**
   (`StepRowActions`·`RerecordStart`·`ImportPreview`·`DeleteOutcome`). 판정 방법이 아니라 요소 종류가
   바뀌어 고치게 된다.
4. 번들 — Checkbox·RadioGroup 을 빼면 약 2 kB(gzip) 준다.

*2026-09-16: 이 네 근거는 갈래를 바꿔도 그대로다.* Base UI 의 `Checkbox`·`RadioGroup` 도 표시를 직접
그리는 부품이라 1·2 가 같고, 테스트가 읽는 요소 종류(3)와 번들(4)도 같다. 네이티브로 두는 결정은
유지한다.

**선택칸을 네이티브로 두는 근거**: 네 곳 전부 짧은 목록이다. 네이티브는 첫 글자 이동·키보드 선택·
폼 제출이 이미 있고(FR-017), Radix `Select` 는 jsdom 에서 `hasPointerCapture`·`scrollIntoView` 가 없어
**클릭만 해도 예외**를 던진다(조사 실측). 테스트 8곳이 `fireEvent.change`·`selectOptions` 로 조작한다.
shadcn v4 에 `native-select` 가 정식으로 있다 — 실제 `<select>` 에 `appearance-none` 과 펼침 표시를
얹는 부품이다. **`Select` 를 빼면 5.8 kB(gzip) 준다.**

**펼침을 `<details>` 로 두는 근거**: 저장소에 이미 `<details>` 가 10곳 있다(`TestBulkConfirm`·
`ImportPreview`·`TestList`). ▸/▾ 수제 토글 3곳(`StepDetail`)만 `aria-expanded` 없이 따로 논다.
`<details>` 는 상태를 스스로 알리고 번들 비용이 0 이다. 두 방식이 공존하는 것이 문제이지 네이티브가
모자란 것이 아니다.

**`title` 을 지우지 않는다**: 비활성 사유는 **옆에 보이는 글자**로 이미 있다(006 ui-contract §2).
Tooltip 은 잘린 글자와 아이콘 단추(⋮ · ×)에만 쓴다. Radix Tooltip 은 비활성 `<button>` 에서 포인터
사건을 받지 못하므로 비활성 사유를 Tooltip 에 맡기면 **사유가 사라진다** (spec Edge Cases).

**버린 대안**:

| 대안 | 버린 이유 |
|---|---|
| shadcn 부품을 전부 Radix 로 | 체크박스·선택칸의 모습을 새로 만들어야 하고(결정 1 위반), 번들이 8 kB 늘며, 테스트가 요소 종류 때문에 바뀐다 |
| Radix 없이 수제로 초점 가두기 | 지금 상태가 그것이다 — 5개 대화상자 중 초점을 다루는 곳이 0이다. `StepDetail` 주석은 가둔다고 적었는데 코드가 없다 |
| `sonner` 토스트 | 스타일을 스스로 주입하고(`--normal-bg` 등) `next-themes`·lucide 아이콘을 끌고 온다. 5초 머묾·hover 정지·밀어 닫기가 이미 `useToastDismiss` 로 테스트되어 있다 |

---

## R3 — 모습: shadcn 원본 클래스를 정본 이름으로 옮긴다

**결정**: shadcn 의미 토큰(`--primary`·`--border`·`--ring`…)을 **테마에 등록하지 않는다.** 이식할 때
원본 클래스를 정본 유틸리티로 **옮겨 적는다.** 옮기는 규칙은 대응표 하나로 고정한다
([ui-parts.md](contracts/ui-parts.md) §2 — 예: `bg-primary text-primary-foreground` → `bg-ink text-panel`,
`border-input` → `border-hair-2`, `rounded-md` → `rounded-base`, `disabled:opacity-50` →
`disabled:border-dashed disabled:text-ink-3 …`, `focus-visible:ring-[3px] ring-ring/50` → 삭제하고 전역
`:focus-visible` 윤곽선에 맡김).

**⚠️ 사용자 결정 1의 문구와 다른 점**: 결정 문구는 「shadcn 의미 토큰은 정본 토큰에 `var()` 별칭으로만
붙인다」였다. 이 계획은 별칭을 **테마 변수로 등록하지 않고 이식 대응표로만** 둔다. 결정의 요지 —
값은 정본에서만 오고 shadcn 모습은 나타나지 않는다 — 는 더 강하게 지켜진다. 문구대로 하지 않는 이유:

1. **별칭을 등록하면 가드가 눈을 감는다.** 지금은 `--color-*: initial` 덕에 `bg-primary` 가 생성되지
   않아 G-B 가 잡는다. 별칭을 등록하면 shadcn 원본을 고치지 않고 붙여 넣어도 G-B 를 통과하고, 색만
   정본이고 **모서리·높이·비활성 표현은 shadcn 인** 부품이 조용히 들어온다.
2. **등록해도 쓸 곳이 없다.** 정본 변종(점선 비활성·위험 테두리 버튼·32px)은 shadcn 구조와 다르므로
   원본 클래스를 어차피 고친다. 쓰이지 않는 변수는 015 가 지운 「죽은 예외」와 같은 종류다.
3. **대응표는 같은 역할을 한다** — 한 shadcn 토큰이 어느 정본 값이 되는지가 한 곳에 적힌다.

이 선택은 되돌리기 쉽다. 사용자가 문구대로 원하면 `tailwind.css` 에 `--color-primary: var(--ink)` 류를
더하고 G-B 대신 원본 클래스 금지 가드(R9 ②)로 막으면 된다.

**버린 대안**:

| 대안 | 버린 이유 |
|---|---|
| shadcn 토큰 별칭을 `@theme inline` 에 등록 | 위 1·2 |
| shadcn 기본 모습 | 사용자 결정 1 |

---

## R4 — 정본 밖 스케일을 **구조로** 막는다

**결정**: `theme/tailwind.css` 의 `@theme inline` 에서 색에 더해 **모서리·그림자·글자 크기·움직임**의
기본 이름공간을 비운다. 남는 것은 정본이 등록한 이름뿐이다.

```
--radius-*: initial;       → rounded-base · rounded-chip · rounded-lg 만 남긴다 (정본 등록)
--shadow-*: initial;       → shadow-e1 · shadow-e2 만
--inset-shadow-*: initial; --drop-shadow-*: initial;
--text-*: initial;         → 글자 크기는 지금처럼 임의값(text-[13px])
--animate-*: initial;
```

**근거**:

- **shadcn 원본의 정본 밖 클래스가 지금은 통과한다.** 조사 실측 — 색 이름공간만 비워서 `rounded-md`·
  `rounded-xs`·`shadow-xs`·`shadow-lg`·`text-sm` 이 **생성된다.** G-B(클래스 실재)는 「있는가」만 보므로
  통과하고, 잡을 수 있는 것은 L2 대조뿐이다. 015 R2 가 색에 대해 내린 판단 — 「규칙보다 쓸 수 없게
  만드는 쪽이 강하다」 — 을 나머지 축에 그대로 적용한다.
- **지금 화면 코드가 그 스케일을 하나도 쓰지 않는다.** 실측: 기본 모서리(`rounded-sm|md|xl…`) 0 ·
  기본 그림자 0 · 기본 글자 크기(`text-xs|sm|…`) 0 · 움직임(`animate-|transition-|duration-`) 0.
  비워도 산출 CSS 가 바뀌지 않아야 한다 — **스파이크 S1 이 확인한다.**
- **남기는 것**: 간격(`--spacing`)은 015 가 비우지 않기로 한 판단을 따른다. 글자 굵기(`font-bold` 등
  323곳)는 정본 값과 같다.

**⚠️ 미검증**: `shadow-none`·`rounded-none`·`rounded-full`·`leading-none` 이 이름공간을 비운 뒤에도
생성되는지(정적 유틸리티인지) — S1 에서 확인한다. 생성되지 않으면 해당 이름만 `@theme` 에 되살린다.

---

## R5 — 변종 표: `cva` 는 쓰고 `tailwind-merge` 는 쓰지 않는다

**결정**:

- 변종은 `class-variance-authority` 의 `cva` 로 표현한다 — shadcn 이 쓰는 형태다.
- 클래스 잇기는 `ui/cn.ts` 의 **로컬 함수**(거짓 값을 걸러 공백으로 잇는 것)다. `tailwind-merge`·
  npm `cn` 을 들이지 않는다.
- 부품의 `className` 을 **받지 않는다.** 015 의 `layout` prop(배치만) 규율을 그대로 둔다.

**근거**:

1. **`tailwind-merge` 는 이 테마를 모른다.** 조사 실측 — `h-9`+`h-control`, `rounded-md`+`rounded-base`,
   `shadow-xs`+`shadow-e1`, `px-3`+`px-s2` 를 **둘 다 남긴다.** 쓰려면 `extendTailwindMerge` 에 정본
   스케일 전부를 등록해야 하고, 등록이 빠진 축은 조용히 병합되지 않는다. 그 누락을 잡는 장치가 또 필요하다.
2. **병합이 필요한 설계가 아니다.** `tailwind-merge` 는 호출자가 `className` 으로 모양을 덮어쓰게
   하려고 있다. 015 는 그것을 금지했다(`layout` 은 배치만, 모양은 `variant`) — 같은 버튼이 화면마다
   달라지는 것을 막으려고(SC-010). 덮어쓰기가 없으면 병합할 충돌도 없고, **변종 표 안의 충돌은 G-E 가
   빌드 전에 잡는다** (R9 ①).
3. **번들** — `tailwind-merge` 가 8.5 kB(gzip)다. Radix 여섯 가지 전부(Tabs·ToggleGroup·Tooltip 포함)가
   36.2 kB 이므로 그 4분의 1에 해당한다. `cva` 는 0.4 kB.

**버린 대안**:

| 대안 | 버린 이유 |
|---|---|
| shadcn 기본 `cn` (clsx + tailwind-merge) | 위 1~3 |
| npm `cn` 0.3 (레지스트리 새 기본) | 같은 병합기를 품는다(+10.9 kB). 이 저장소는 병합을 금지한다 |
| `cva` 없이 015 형태(`Record` 표 + `[…].join`) 유지 | G-E 가 그 형태를 이미 읽는다는 장점이 있다. 그러나 사용자가 shadcn 방식을 요청했고, `cva` 는 복합 변종(`compoundVariants`)과 기본값을 한 선언으로 준다. G-E 를 `cva` 에 맞게 넓힌다 (R9 ①) |

---

## R6 — 알림 층: 정의 하나, 자리는 화면의 띠가 정한다 (B-01 · B-02)

**원인** (조사): 토스트 자리 클래스가 **세 곳**에 있었다 — 정본 `.toast-layer`(`--h-header + --h-phase + 8px`),
`ui/Notice.tsx` `TOAST_LAYER_CLASSES`(`--h-header + 8px`), `Workbench.tsx:321` 의 **같은 문자열 복사본.**
2026-09-11 수정(`68d92f5`)이 국면 띠 몫을 **정본 클래스에만** 더했는데, 앱은 015 T075 부터 정본의 클래스
규칙을 싣지 않는다(`tokens.app.css`). 고친 것이 화면에 닿지 않았고, 결과·녹화 화면이 쓰는 층은
`Workbench` 의 복사본이었다.

**그리고 값 하나로는 풀리지 않는다.** 국면 띠가 있는 화면(만들기·녹화·실행·일시정지·편집·결과)과
머리띠만 있는 화면(목록·프로젝트·가져오기), 머리띠도 없는 화면(비밀 값·키 관리)이 섞여 있다.
`header+phase` 로 고정하면 목록에서 48px 가 뜨고, `header` 로 고정하면 작업 화면에서 덮는다.

**결정**:

1. 알림 층 클래스는 `ui/Notice.tsx` 의 `TOAST_LAYER_CLASSES` **하나**다. `Workbench` 의 복사본을 지운다.
2. 자리는 **지금 문서에 어떤 띠가 있는지**가 정한다. 머리띠와 국면 띠가 `data-shell="header"`·
   `data-shell="phase"` 를 내보내고, 층은 `:root:has(…)` 조건 셋 중 **정확히 하나**만 성립하는 변종을 갖는다
   (띠 없음 → `top-s4` · 머리띠만 → `header+8px` · 국면 띠까지 → `header+phase+8px`). 조건이 서로를
   배제하므로 산출 CSS 순서에 승부를 맡기지 않는다 (015 G-E 의 교훈).
3. 층에 `aria-live="polite"` 를 둔다 — 모달이 열릴 때 Radix 가 body 의 다른 자식에 `aria-hidden` 을
   거는데, `aria-live` 요소는 건너뛴다(조사 실측). 층의 `pointer-events-none` + 자식 `auto` 는 이미 있어,
   모달이 body 에 건 `pointer-events:none` 을 이긴다.
4. 모달 대화상자는 알림 층 안에서 시작한 바깥 상호작용을 **닫힘으로 치지 않는다**
   (`onInteractOutside` 에서 층 안이면 `preventDefault`). 이것이 없으면 토스트의 「닫기」를 누르는 순간
   대화상자가 닫혔다(조사 실측).
5. **B-02**: 테스트 목록의 진행 중 세션 **토스트를 지운다.** 흐름 안 띠(`ActiveSessionsBanner`)가 같은
   사실을 말하고, 세션마다 「이어서 보기」·「중지하고 버리기」와 「새로 고침」을 갖는다 (FR-018b).

**B-02 의 결정은 2026-09-10 사용자 결정과 긴장이 있다** — 「알림을 토스트 한 자리로 모은다, 내용을
밀어내지 않는다」(`25a57de`). 그 커밋이 세션 알림도 토스트로 옮기면서 **흐름 안 띠는 남겨 두었다.**
반대로 띠를 지우고 토스트에 조작을 모으면, 이 토스트는 닫기 단추가 없고 사라지지 않으므로(그 커밋의
결정) **목록 도구 줄(「최근 실행 순」·「엑셀로 내보내기」…)을 계속 덮는다** — 전환 전 캡처에서 토스트가
차지한 자리(x 1004~1424, y 64~130)가 띠가 없을 때 도구 줄의 자리다. 덮지 않는 쪽을 택한다.
사용자가 반대를 원하면 토스트 쪽으로 모으고 도구 줄을 옮기는 별도 결정이 필요하다.

**구현 중 확인한 근거 하나 더** (2026-09-15): `TestList.tsx:1368` 에 008 이 적은 규칙이 있다 — 「『실행 화면
보기』는 **화면에 하나뿐이다.** 둘 다 두면 같은 일을 하는 조작이 한 화면에 둘이 되고, 그것이 007 UC-102 가
없앤 형태다」. 지금 목록에는 토스트의 「실행 화면 보기」와 띠의 「이어서 보기」가 **같은 `onResumeSession`** 을
부른다. 토스트를 지우면 그 규칙도 되살아난다. 복귀 수단(005 FR-168)은 띠의 「이어서 보기」로 남는다 —
세션이 끝나 `review` 여도 띠는 세션마다 그 조작을 그린다.

**버린 대안**:

| 대안 | 버린 이유 |
|---|---|
| 층 `top` 을 `header+phase+8px` 로 고정 | 목록·가져오기에서 48px 공백, 비밀 값·키 관리에서 더 크다 |
| 화면이 JS 로 `--toast-top` 을 `:root` 에 쓴다 | 동작하지만 화면마다 설정을 잊을 수 있고 인라인 스타일 예외가 는다. `:has()` 는 DOM 이 이미 가진 사실을 읽는다 |
| 층을 화면 안에 두고 포털을 없앤다 | 모달 포털(`body`)과 층위가 갈라져 모달 위에 토스트가 뜨지 않는다 |
| Radix `Toast` | R2 표 — 머묾·정지·밀어 닫기가 이미 테스트되어 있고, F8 단축키 등 새 동작이 딸려 온다 |

### 2026-09-16 개정 — 알림을 부품으로 옮기고 자리를 아래로

**무엇이 남았나**: 위 결정들로 B-01·B-02 는 닫혔지만, **N-02 가 남았다** — 알림 층이 오른쪽 위에
있어 작업 화면에서 Step 패널의 머리 줄과 첫 행들을 가린다. 017 은 이것을 「의도된 예외 · 사용자
확인」으로 두었다. 브라우저 확인(2026-09-15)에서 녹화를 멈추면 알림 **셋**이 쌓여 Step 01·02 행의
체크 칸과 행 조작까지 가리는 것을 봤다.

**사용자 결정 (2026-09-16)**: 알림을 shadcn 의 toast 부품으로 바꾸고 **가리지 않는 자리**로 옮긴다.

**결정**:

1. **부품으로 옮긴다.** 손으로 만든 것(`ui/Notice` 의 `Toast`·`ToastLayer`·`TOAST_LAYER_CLASSES` ·
   `components/Toast` 의 포털 층 · `ui/useToastDismiss` · `NoticeStack` 의 타이머)을 Base UI `Toast`
   가 대신한다. 확인한 사실 — 표시 수 상한 기본 3 · 머무는 시간 기본 5초 · 밀어서 닫기 ·
   넘친 알림은 `data-limited` · 낭독 우선순위 · 자리는 **우리 CSS 가 정한다**.
2. **자리는 아래다.** shadcn 의 `toast.tsx` 기본값은 오른쪽 아래(`inset-x-4 bottom-4 … sm:right-4`)다.
   그대로 놓고 순회로 재서, 작업 화면 Step 패널 **바닥의 조작**을 덮으면 **아래 가운데**로 옮긴다.
   자리를 정하는 코드는 한 곳(부품의 Viewport)이다.
3. **되풀이를 없앤다** (FR-018b 의 연장). 화면이 이미 말하는 사실은 알림으로 내지 않는다.

   | 내지 않는다 | 화면이 말하는 자리 |
   |---|---|
   | 「화면이 A 에서 B 로 바뀌었습니다」 | 국면 띠의 국면 표시 |
   | 「세션을 종료했습니다」 | 미러 자리의 같은 문장 |

   남는 것: 할 일이 남았다는 알림(저장하지 않은 기록) · 오류 · 사용자 조작의 결과.
4. **순회가 잡게 한다.** 알림이 떠 있는 작업 화면을 순회 목록에 넣는다 (screen-sweep SW-5 개정).
   자리를 옛 자리로 되돌리면 순회가 실패해야 한다 (spec SC-016).

**퇴장 셋(5초·밀어내기·닫기)과 hover 멈춤은 2026-09-11 사용자 결정 그대로다** — 부품이 같은 규칙을
기본으로 갖는다. 밀어내기 방향만 자리에 맞춘다.

### 이식하며 알아낸 것 (2026-09-16 · T099~T102 실측)

문서만 보고는 알 수 없었고, **부품을 쓰다가 드러난** 것들이다. 되돌아오지 않도록 적어 둔다.

| 무엇 | 부품의 기본 | 우리가 한 것 |
|---|---|---|
| 바깥에서 만든 관리자 | 구독자에게 **그 자리에서** 전달하고 쌓아 두지 않는다. 공급자는 효과에서 구독하는데 React 는 자식 효과를 먼저 돌린다 → 등록이 버려져 **층이 비었다** | 공급자 안에서 **훅으로 받은 관리자**에 등록한다 (저장소에 바로 쓴다) |
| 닫기 단추 | 층이 펼쳐지거나 그 단추에 초점이 있을 때만 보조기술에 보인다 (`aria-hidden: !expanded && !hasFocus`) | 우리 규칙은 「닫는 길은 모든 알림에 있고 **이름으로 찾을 수 있다**」 — 속성 병합 순서(`기본값 → 우리 것`)를 이용해 되돌렸다 |
| 높은 우선순위 | 보이는 알림을 `aria-hidden` 으로 덮고 **제목·설명 문자열**을 숨은 `role="alert"` 자리에서 읽는다 | 우리 알림은 문구가 아니라 **그릴 것**(버튼·링크가 든 조각)을 싣는다 → 읽을 내용이 비고 알림 안 조작도 역할로 못 찾는다. 낮은 우선순위 + `role` 만 우리가 얹는다 |
| 밀어내기 끄기 | `swipeDirection` 을 **주지 않으면 기본값**(`['down','right']`)이다. 끄는 것은 **빈 배열**(`swipeEnabled = 길이 > 0`) | 닫을 길이 없는 알림에 `[]` 를 준다 — `undefined` 로 두었다가 「돌고 있습니다」가 밀려 사라졌다 |
| `timeout: 0` | **영영 두기**다 — `duration > 0` 일 때만 타이머를 건다 | 닫을 길이 없는 알림에 그대로 쓴다 |
| 대화상자 내용 | `Popup` 은 **`Portal` 없이 그릴 수 없다** | `Portal container=` 로 작업대 안에 보낸다 (S6) |

---

## R7 — Step 상세 판은 **모달이 아니다**

**결정** *(2026-09-16 개정: Base UI 로 옮기며 포털 전제가 바뀌었다 — S6)*: `StepDetail` 은 `Dialog` 를
`modal={false}` 로 쓴다. **포털은 뺄 수 없다**(부품이 요구한다). 대신 `Portal container=` 로 판을
**작업대 안의 자리**로 보내 아래 근거들을 그대로 지킨다. 바깥
누름은 `onOpenChange` 가 주는 **닫힌 이유**로 걸러 낸다(017 의 `onInteractOutside` 자리). 열리면 초점이 판
안으로 가고 Esc 로 닫히며 닫히면 연 행으로 초점이 돌아간다. 뒤쪽 가림막(`Scrim soft`)은 지금처럼 판과
별개로 둔다. Step 목록 안에서 시작한 바깥 클릭은 닫힘으로 치지 않는다(`onInteractOutside`).

**근거**:

- 판은 목록 **옆에** 뜨고, 사용자는 판을 연 채 다른 행을 눌러 옮겨 간다. `DetailPlacement.test.tsx:217`
  이 그것을 본다. 모달이면 `hideOthers`·`pointer-events:none` 이 목록을 막는다.
- 판의 자리(`absolute left-0 right-steps top-0 bottom-0`)는 `Workbench` 안의 배치 계약이다
  (`DetailBlocksMirrorInput`). 포털로 body 에 붙이면 자리를 다시 계산해야 한다.
- 미러 입력 차단은 가림막이 한다(010). Radix 가 초점을 가두지 않으므로 미러 IME 칸과 다투지 않는다.

---

## R8 — 화면 폭 정책과 머리띠 (B-10 · B-11)

**원인** (조사): `Artboard` 는 가운데 정렬을 할 수 없다 — 바깥 `overflow-x-auto` 안에 고정 폭 또는
`min-width+100%` 열 하나다. 목록은 `width={1440}`(왼쪽 고정), 작업 화면은 `grow`, 가져오기는 `width={1000}`,
프로젝트는 `max-w-[960px] mx-auto`, 비밀 값·키 관리는 `max-w-[720px] mx-auto` 에 머리띠가 없다.
머리띠는 가로 스크롤 영역 **안**에 있어, 1280 폭에서 자동 초점(`TestBulkConfirm` 「돌아가기」)이
스크롤을 160px 옮기면 함께 밀려 나간다.

**결정** (spec FR-021 · 2026-09-14 사용자 결정):

| 정책 | 화면 | 넓은 창 (>1440) | 좁은 창 (<1440) |
|---|---|---|---|
| `data` | 테스트 목록 · 가져오기 미리보기 · 작업 화면 전 국면 | 창 폭을 채운다. 가변 칸이 늘어난 폭을 가져간다 | 본문이 1440 을 지키고 **본문만** 가로로 스크롤한다 (DC-011) |
| `form` | 프로젝트 목록·만들기 · 비밀 값 · 키 관리 | 읽기 폭으로 가운데 선다 (960 · 720) | 가운데 선 채 줄어든다 |

`Artboard` 는 이 정책 둘을 `policy` 로 받는다. **머리띠는 가로 스크롤 영역 밖**에 선다 — 머리띠는
1280 폭에 들어간다(제품 표시·프로젝트 이름·오른쪽 조작 넷). 가로 스크롤은 머리띠 아래 본문만 한다.
그러면 자동 초점이 스크롤을 옮겨도 머리띠는 제자리다 (B-11 · FR-022).

가져오기 미리보기의 1000 폭은 `data` 로 옮긴다 — 시트 표가 넓은 창에서 오른쪽을 비울 이유가 없다.

---

## R9 — 가드: 부품 층이 바뀌어도 막던 것을 막는다

조사가 찾은 구멍 넷과 그 대응이다.

**① G-E(같은 속성 두 번)가 `cva` 를 읽지 못한다.** G-E 는 `const NAME = "…"`·평평한 `Record` 표·
`[…].filter(Boolean).join(" ")` 조립만 읽는다. 조립 38곳 중 37곳이 `src/ui` 에 있어, `cva` 로 바꾸면
자체 점검(`composed.length > 20`)부터 실패한다.
→ **헬퍼를 넓힌다.** `cva(base, { variants, compoundVariants, defaultVariants })` 를 「base × 축마다 값
하나 (+ 맞는 복합 변종)」의 조합으로, `cn(…)` 의 인자를 조립 칸으로 읽는다. 자체 점검 하한은 유지한다.

**② 상태 변종이 든 문자열을 통째로 버린다.** 클래스 목록 판정 문자 집합에 `=` 가 없어
`data-[state=open]:bg-sunken` 이 든 리터럴이 **옆 클래스까지** G-B·G-C·G-E 에서 사라진다. 지금도
`Table.tsx:162` 의 `[&>button[aria-pressed=true]]:…` 가 그렇다.
→ 대괄호 **안에서만** `= & > ( ) , + * ~ " '` 를 허용한다. 드러나지 않던 기존 클래스가 검사에 들어오며,
그 결과로 새로 걸리는 것은 고칠 대상이다.

**③ shadcn 모습이 가드를 통과한다.** R4 가 모서리·그림자·글자 크기를 구조로 막는다. 남는 것은 **정적
유틸리티**라 테마로 막을 수 없는 것들이다 — `disabled:opacity-50`·`focus-visible:ring-*`·
`outline-hidden`·`transition-*`·`dark:*`·`data-open:` 류 사용자 정의 변종·`lucide-react` 가져오기.
→ 새 가드 **G-F(부품 모습)** 가 `src/ui/**` 에서 이것들을 금지하고, 비활성 변종이 점선 형태
(`disabled:border-dashed`)를 갖는지 본다. 기존 `FocusRing` 은 `outline-none`·`outline-0` 을 이미 막는다 —
`outline-hidden`(Tailwind v4 이름)을 더한다.

**④ 원시 조작 요소를 세는 가드가 없다** (FR-002 · FR-030).
→ 새 가드 **G-G(원시 요소)** 가 `src/ui/` 밖의 `.tsx` 에서 `<button`·`<input`·`<select`·`<textarea` JSX 를
센다. 등록부(`theme/exceptions.ts`, 새 축 `raw-element`)에 사유와 함께 있는 것만 통과한다. 전환 중에는
`ImplementationCount` 와 같은 **줄어드는 예산**을 둔다 — 빨강은 언제나 「무언가 깨짐」이고, 예산이 늘면
즉시 실패한다. 완료 조건은 예산 = 등록된 예외 수.

**그 밖**:

- G-B 의 Tailwind 조회는 `--content ./src/**/*.tsx` 만 본다. **변종 표는 부품 `.tsx` 안에 둔다**
  (shadcn 도 `buttonVariants` 를 `button.tsx` 에 둔다). `.ts` 에만 있는 클래스는 조회가 못 보므로 G-B 가
  「생성되지 않음」으로 실패한다 — 규칙 위반이 조용히 넘어가지 않는다.
- `BeforeAfterParity` 는 `src` 가 한 글자만 바뀌어도 실패한다. 단계마다 L2 를 다시 돌리고, 요소 이름·구조가
  바뀐 자리는 사유와 함께 `INTENDED` 에 등록한다.

---

## R10 — jsdom: 환경을 한 곳에서 채운다

**결정**: `frontend/tests/setup/dom.ts` 를 `vite.config.ts` 의 `test.setupFiles` 로 싣는다. 채우는 것:
`ResizeObserver`(Tooltip 화살표가 잰다), `PointerEvent`(`MouseEvent` 상속 — `MirrorView.test.tsx:63` 의
폴리필과 같은 형태이며 그쪽은 `undefined` 일 때만 심으므로 충돌하지 않는다), `Element.prototype`
`hasPointerCapture`·`setPointerCapture`·`releasePointerCapture`·`scrollIntoView`.

**근거** (조사 실측, vitest 2.1.9 · jsdom 25):

| 부품 | 폴리필 없이 |
|---|---|
| Tabs · ToggleGroup | `userEvent.click` 동작 |
| DropdownMenu | `fireEvent.click` 으로 **열리지 않는다.** `userEvent.click`·Enter 는 연다 |
| Tooltip | `ResizeObserver` 없으면 예외 |
| Dialog | 동작. 단 body `pointer-events:none` 이라 `userEvent` 가 바깥 클릭을 거부한다 |

**테스트에 미치는 영향** — [test-ledger.md](contracts/test-ledger.md) 에 파일마다 적는다. 요지:
행 메뉴를 `.click()` 으로 여는 3개(`RowMenuVisible`·`TestListActions`·`EditEntryPoints`)는 `userEvent` 로
연다. 모달이 열리면 뒤쪽 요소가 `aria-hidden` 이 되어 `getByRole` 이 찾지 못한다 — 확인 대화상자를 연 뒤
뒤쪽을 찾는 테스트는 대화상자를 닫은 뒤 찾도록 **순서만** 바꾼다.

---

## R11 — 화면 깨짐의 나머지 원인과 수정 자리 (B-03 ~ B-09)

| # | 원인 (조사) | 수정 자리 |
|---|---|---|
| B-03 | Step 패널 바닥이 `max-h-[52%]` 리터럴이다(`StepList.tsx:470`). 배치 표 밖에 있고, 900px 에서 목록이 6.6행이 된다 | 배치 표에 **국면별 바닥 상한**을 둔다: 목록이 8행을 지키는 `calc(100% - 36px - 8 * var(--h-step))`. 바닥은 안에서 스크롤한다 (LC-1 — 배치 판단은 표에만) |
| B-04 | 만들기 국면 `targetSlot = fixed(88)` 은 한 줄짜리 `open_browser` 용으로 잰 값인데, 만들기는 세 줄짜리 `empty` 안내를 쓴다 | 만들기의 `targetSlot` 을 `content` 로 — 안내 높이만큼 |
| B-05 · B-06 | 비활성 조작의 **사유 문구가 최대 260px** 을 가져간다(`ActionButton.tsx:142`). 옆의 제목·칩·입력칸이 `shrink-0` 없이 줄어든다 | 사유 문구는 `min-w-0 truncate` + Tooltip 으로 전체 문구. 칩은 부품에서 `shrink-0 whitespace-nowrap`. 입력칸은 부품이 쓰임별 최소 폭을 갖는다 |
| B-07 | 선택 띠의 글자·navlink 에 `whitespace-nowrap` 이 없고, `<select>` 가 정본 요소 규칙 `width:100%` 를 받는다 | 부품 층에서 막는다 — 버튼·칩은 `whitespace-nowrap shrink-0`, `NativeSelect` 는 `w-auto` 가 기본 |
| B-08 | 두 체크박스 모두 정본 `input{width:100%;min-height:32px}` 를 받는다. 머리는 블록 안이라 28px, 행은 flex 안에서 줄어 21px | `Checkbox` 부품이 14px 를 명시한다 (지금 `StepCheck` 만 그렇게 한다) |
| B-09 | `DraftList` 가 원시 `<table>` 을 쓰고, 015 가 머리를 `GridHead` 가 아닌 `TableHead` 형태로 옮겨 브라우저 기본 `th{text-align:center;font-weight:bold}` 가 드러났다 | 표 부품 하나(`Table`·`TableHeader`·`TableHead`·`TableCell`)로 — 머리 정렬·글꼴은 부품이 정한다 |

**부품 층이 정본 요소 규칙의 번짐을 끊는다.** B-07·B-08 은 전역 `input,select,textarea{width:100%}` 가
원시 요소에 번진 것이다. 요소 규칙을 지우지 않는다(정본이다) — 부품이 필요한 값을 **명시**해 이긴다.
정본을 `layer(base)` 로 들였으므로 유틸리티가 이긴다 (015 C-8).

---

## R12 — 번들 예산을 실측으로 다시 정한다

**실측** (esbuild, minify, `radix-ui` 1.6.7 이름 가져오기 tree-shaking, react 외부):

| 묶음 | gzip |
|---|---|
| Dialog · AlertDialog · DropdownMenu | 32.4 kB |
| + Tabs · ToggleGroup | 33.9 kB |
| + Tooltip | 36.2 kB |
| + `cva` | 36.6 kB |
| (참고) + `tailwind-merge` | 45.1 kB |
| (참고) + Checkbox · RadioGroup · Collapsible · Select | 54.2 kB |

**결정**: spec SC-011 의 JS 상한을 **+25% → +30%**(139.48 → **181.3 kB**)로 고친다. CSS 상한(+10%)은
그대로다.

> **2026-09-16 개정 — 갈래를 바꾸며 상한을 한 번 더 조인다.** Radix 로 구현한 실측이 **177.41 kB**
> (gzip)다. 기반 교체는 **추가가 아니므로** 이 수치를 넘지 않는 것을 목표로 한다(spec SC-014 계열).
> 손으로 만든 알림 코드가 빠지고 부품이 들어오므로 상쇄를 기대한다. 넘으면 무엇이 들어왔는지
> (`npm ls`) 먼저 보고, 그다음 부품 단위 늦은 불러오기를 검토한다.

**근거**: 명세의 +25% 는 측정 전에 정한 판단값이었다. 실측으로 보면 FR-011·FR-012 를 성립시키는 세 부품
(대화상자·확인 대화상자·메뉴)만으로 +32.4 kB(+23%)이고, 나머지 셋과 `cva` 가 +4.2 kB 다. +25% 를
지키려면 Tooltip(FR-019 의 키보드 전체 문구)을 빼야 하는데, 그것은 요구사항을 예산에 맞춰 줄이는 일이다.
대신 이 계획은 R2·R5 에서 **요구사항이 필요로 하지 않는 17.6 kB 를 이미 뺐다**(`tailwind-merge`·네이티브로 둔
넷). 수제 메뉴 위치 계산·수제 모달이 지워지며 줄어드는 몫은 상한에 반영하지 않았다 — 여유로 둔다.

**버린 대안**:

| 대안 | 버린 이유 |
|---|---|
| +25% 유지, Tooltip 제외 | FR-019 가 요구하는 「전체 문구를 확인할 수단」이 키보드에서 사라진다 |
| 부품을 필요할 때 늦게 불러오기(dynamic import) | 대화상자는 조작 흐름 한가운데(저장·중지 확인)에서 열린다. 첫 열림 지연이 조작을 늦춘다. 복잡도 대비 이득이 작다 |

---

## 스파이크 — 구현 시작 전에 확인할 것

| # | 질문 | 실패하면 |
|---|---|---|
| S1 | R4 의 이름공간 비우기 후 산출 CSS 가 **바뀌지 않는가** (`shadow-none`·`rounded-none`·`rounded-full`·`leading-none` 포함) | 생성되지 않는 이름만 `@theme` 에 되살린다 |
| | **✅ 확인 (2026-09-15 · T001)** — 화면 코드(`./src/**/*.tsx`)로 만든 `@layer utilities` 가 비우기 전후 **바이트 단위로 같다**(35,005자). 정적 유틸리티 `shadow-none`·`rounded-none`·`rounded-full`·`leading-none` 과 정본 `rounded-base|chip|lg`·`shadow-e1|e2` 는 그대로 생성되고, `rounded-md|sm|xs`·`shadow-xs|sm|lg`·`text-sm|xs`·`animate-spin`·`inset-shadow-xs`·`drop-shadow-md` 는 **생성되지 않는다.** 되살릴 이름 없음 | |
| S2 | 넓힌 G-E 헬퍼가 `cva` 한 부품(Button)의 조합 전부를 만들고, 일부러 넣은 역전을 잡는가 | `cva` 대신 015 형태(R5 버린 대안 3)로 되돌린다 |
| | **✅ 확인 (2026-09-15 · T002)** — 시험 부품의 `primary: "bg-panel text-panel bg-ink"`(뒤에 적은 `bg-ink` 가 CSS 에서 진다)를 G-E 가 **세 경로 모두에서** 잡았다: 리터럴(`__spike_cva.tsx:10`) · `cva(spikeVariants)` 조합(`:6`) · `cn(spikeVariants(…), …)` 조합(`:22`). **덧붙여 찾은 구멍 1건**: `className={cn(xVariants({ variant: "primary" }))}` 안의 변종 **이름** `"primary"` 를 클래스 목록 헬퍼가 클래스로 읽어 G-B(「생성되지 않는 `.primary`」)·G-D(「완료된 정본 `.primary` 사용」)가 없는 위반을 보고했다. `이름({ … })` 호출의 객체 인자를 지운 뒤 리터럴을 모으도록 고쳤다 | |
| S3 | `tests/setup/dom.ts` 를 실은 뒤 기존 1364건이 그대로 통과하는가, Radix `Dialog`·`DropdownMenu` 를 쓴 시험 부품이 jsdom 에서 열리고 닫히는가 | 폴리필 범위를 조정한다 |
| | **✅ 확인 (2026-09-15 · T003 · React 19.2.8)** — 보완을 실은 뒤 기존 테스트 전량 통과(가드 실패는 스파이크 파일과 L2 digest 뿐). `Dialog`: 열면 초점이 안으로 · Tab 이 밖으로 나가지 않음 · Esc 닫힘 · 트리거로 초점 복귀. `DropdownMenu`: `userEvent.click` 으로 열림 · 화살표 · Esc · 트리거 복귀 (약 3초). `Tooltip`: 초점(`userEvent.tab`·`act(focus)` 뒤 한 틱)과 hover 에 뜬다. **단 jsdom 에서 한 번 여는 데 약 8초** — 기본 제한 5초에 걸려 첫 시험이 실패로 보였다. **원인 판명 (2026-09-15 · T056)**: floating-ui 가 자리를 계산하며 조상마다 `el.matches(':popover-open')`·`el.matches(':modal')` 을 부르는데, jsdom 의 선택자 엔진은 이 둘을 예외 없이 **한 번에 약 150ms** 를 들여 거짓으로 답한다(두 선택자 × 100회 30.6초 · `computePosition` 한 번 5.8초 → 두 선택자만 바로 거짓이면 1ms). jsdom 에는 최상위 층이 없어 맞는 요소가 있을 수 없으므로 `tests/setup/dom.ts` 가 두 선택자에만 바로 거짓을 돌려준다 — 메뉴를 여는 검사가 10초에서 0.3초가 됐다. 아래 결론의 「제한을 명시하거나 여는 대신」은 더는 필요 없다. 조사 에이전트가 빠뜨린 `IntersectionObserver` 도 보완에 더했다. **결론**: 툴팁을 여는 테스트는 제한을 명시하거나, 여는 대신 트리거의 `aria-describedby`·`data-state` 를 본다 (T063) | |
| S4 | 화면 순회가 **개발 서버**로 녹화 화면을 **실시간 연결된 채** 여는가 | 순회 계약 SW-3 을 다시 정한다 |
| | **✅ 확인 (2026-09-15 · T004)** — `runner-record@1440` 이 「실시간 연결이 끊겼습니다」 없이 녹화 국면으로 그려지고 검출 0. **그리고 한 가지를 바꿨다**: 연결 끊김 화면(`runner-disconnected`)을 `page.route_web_socket(…, lambda ws: ws.close())` 로 만들었더니 동기 API 처리기 안의 `close()` 에서 **순회 전체가 10분간 멈췄다.** 페이지가 뜨기 전에 `WebSocket` 을 감싸 `/events` 만 닫힌 포트로 보내는 초기화 스크립트로 바꿨고, 브라우저가 실제 연결 실패를 겪어 알림이 뜬다(B-01 의 녹화 쪽 덮임이 그대로 재현됐다). 화면 셋 × 폭 하나가 34초 | |
| S5 | `:root:has([data-shell=…])` 임의 변종 셋이 Tailwind 에서 생성되고 chromium 에서 서로 배제되는가 | 화면이 `:root` 에 `--toast-top` 을 쓰는 방식(R6 버린 대안 2)으로 |
| | **✅ 확인 (2026-09-15 · T005)** — `[:root:has([data-shell=phase])_&]:top-[…]` 와 `[:root:has([data-shell=header]):not(:has([data-shell=phase]))_&]:top-[…]` 둘 다 생성된다. chromium 에서 한 요소에 `top-s4` 와 두 변종을 함께 걸고 띠를 바꿔 끼우면 계산된 `top` 이 **띠 없음 16px · 머리띠 64px · 머리띠+국면 띠 112px** — 서로 배제되고 산출 CSS 순서에 기대지 않는다 | |
| S6 **(09-16)** | 포털 없이 비모달 `Dialog.Popup` 이 자리와 초점을 지키는가 · 바깥 누름을 「닫힌 이유」로 거를 수 있는가 (R7) | 포털을 쓰고 층위를 z 로 맞춘다 |
| | **✅ 확인 (2026-09-16 · T094) — 다만 전제 하나가 틀렸다.** `Dialog.Popup` 은 **포털 없이 그릴 수 없다**: 「Base UI: `<Dialog.Portal>` is missing.」으로 막힌다. 017 의 「포털 없음」은 그대로는 불가능하다. **대신 `Portal` 이 `container` 를 받는다**(설치된 타입 정의 확인) — 판을 작업대 안의 자리로 보내면 017 의 자리 계약(`absolute left-0 right-steps top-0 bottom-0`)과 `DetailBlocksMirrorInput` 이 보는 구조를 그대로 쓴다. 그 형태로 시험 4건 전부 통과: 판이 `container` 안에 그려짐 · 열면 초점이 판 안으로 · Esc 로 닫히고 이유가 `escape-key` · 바깥 누름은 이유가 `outside-press` 라 **무시하면 판이 열린 채 남는다**(017 `onInteractOutside` 자리) | |
| S7 **(09-16)** | 고르기 묶음에서 **빈 값 금지**를 부품이 강제할 수 있는가 (R2 개정 · Base UI 는 required 를 주지 않는다) | 라디오 묶음(`RadioGroup` + `render`)으로 분절 단추를 만든다 — 모양은 같고 낭독만 라디오다 |
| | **✅ 확인 (2026-09-16 · T095)** — 값을 부품이 쥐고(`value`·`onValueChange`) **빈 배열이 오면 무시**하면 고른 것을 다시 눌러도 상태가 남는다. 상태 통로는 **`aria-pressed`(단추 역할) + `data-pressed`** 다 — 지금의 `role=radio`·`aria-checked` 와 다르다. 라디오 대안은 쓰지 않는다 | |
| S8 **(09-16)** | 알림 기본 자리(오른쪽 아래)가 작업 화면에서 무엇을 덮는가 (R6 개정) | 아래 가운데로 옮긴다 |
