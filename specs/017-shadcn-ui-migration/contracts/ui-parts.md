# Contract: 부품 목록과 이식 대응표

**Feature**: 017 | **Status**: 계약 · 살아 있는 문서 (전환하며 `상태` 칸을 갱신한다)

## §0 — 규칙 요약

1. 부품은 `frontend/src/ui/` 에 산다. 파일 이름은 PascalCase. 도메인을 모른다.
2. shadcn 원본을 이식할 때 **파일 머리에 출처를 적는다** — 갈래까지 적는다:
   `shadcn base/<item> @ shadcn 4.21.x (style base-nova) · @base-ui/react 1.8.x`.
   *2026-09-16 개정: 017 의 출처 줄은 갈래를 적지 않아 **Radix 갈래를 옮긴 사실이 문서에 드러나지
   않았다.** 갈래는 출처의 일부다.*
   원본에서 무엇을 바꿨는지는 §2 대응표를 따랐다고 적고, 표에 없는 변경만 따로 적는다.
3. 부품은 `className` 을 받지 않는다. `layout?: string` 은 배치만 (015).
4. 변종은 `cva` 로, 파일 안에 둔다. 조합 잇기는 `ui/cn.ts`.
5. 부품이 그리는 루트 요소에 `data-slot="<부품-이름>"` 을 둔다 (shadcn 관례 · 순회 SW-7 이 집는다).
6. `lucide-react`·`tw-animate-css`·`tailwind-merge` 를 가져오지 않는다. 표식은 글자 기호(✓ ▾ × ⋮)나
   이미 쓰는 인라인 SVG 로 그리고 `aria-hidden` 을 둔다.

## §1 — 부품 목록

`behavior`: **base** = `@base-ui/react` 1.8.x 가 구조·동작 · **native** = 네이티브 요소의 동작 ·
**raw** = 동작 없음. *2026-09-16 개정 전에는 **radix** = `radix-ui` 1.6.x 였다 — 아래 §1-2 가 부품별로
무엇이 달라지는지 적는다.*

| 부품 (파일) | 내보내는 것 | behavior | shadcn 원본 | 대체하는 것 | 상태 |
|---|---|---|---|---|---|
| `cn.ts` | `cn` | — | (로컬) | `[…].filter(Boolean).join(" ")` 37곳 | ✅ T010 |
| `Button.tsx` | `Button` · `buttonVariants` | raw (+ `Slot` 로 `asChild`) | `button` | `ui/Button` · `navLinkClasses` · 밑줄 해소 링크 3곳 · 클래스 없는 원시 `<button>` 16곳 | ✅ T025·T026 — `nav` 26곳 전환 |
| `Chip.tsx` | `Chip` · `chipVariants` · `Pill` | raw | `badge` | `ui/Chip` · `chipClasses` | ✅ T027 |
| `Input.tsx` | `Input` | native | `input` | 원시 텍스트형 `<input>` 40곳 · `ui/Field` 안쪽 벗기기 · 국면 이름 입력 · 인라인 이름 고치기 2곳 | ✅ T029 · 화면 적용 T036~T047 (`ai` 변종 · `font` 축 추가) |
| `Textarea.tsx` | `Textarea` | native | `textarea` | 원시 `<textarea>` 5곳 (IME 칸 제외) | ✅ T030 · 화면 적용 T041·T042 |
| `NativeSelect.tsx` | `NativeSelect` · `NativeSelectOption` | native | `native-select` | 원시 `<select>` 4곳 | ✅ T031 · 화면 적용 T038·T042·T045·T047 (`width` 축 추가) |
| `Checkbox.tsx` | `Checkbox` | native | (원본 `checkbox` 은 Radix — **쓰지 않는다**, research R2) | 원시 체크박스 5곳 · `StepCheck` | ✅ T032 · 화면 적용 T042·T043·T045·T047 |
| `Radio.tsx` | `Radio` | native | (원본 `radio-group` 은 Radix — 쓰지 않는다) | 원시 라디오 4곳 | ✅ T033 · 화면 적용 T036·T045 |
| `Label.tsx` | `Label` · `Lbl` · `FieldLabel` | raw | `label` (Radix `Label` 은 쓰지 않는다 — 텍스트 선택 방지뿐) | `ui/Field` 의 `Lbl`·`FieldLabel` · 전역 `label{}` 에 기대던 폼 라벨 | ✅ T028 |
| `Field.tsx` | `Field` · `FileButton` · `CommitBar` · `AnswerQuestion` | raw | — (015 계승) | 같음. `FileButton` 이 `multiple` 을 받는다 (`BrowserPromptPanel`) | ✅ T034 — 안쪽 입력 벗기기를 지우고 `Input bare` 로 |
| `Dialog.tsx` | `Dialog` · `DialogContent` · `DialogHeader` · `DialogTitle` · `DialogDescription` · `DialogFooter` · `DialogClose` | **radix** `Dialog` | `dialog` | `SessionScreen` 지역 `Modal` (닫기·재실행·떠나기 확인) · `ui/Modal` | ✅ T048 · 화면 적용 T050 (떠나기 확인) — 가림막이 내용을 감싼다 · `useReturnFocus` |
| `AlertDialog.tsx` | `AlertDialog` · `AlertDialogContent` · … · `AlertDialogAction` · `AlertDialogCancel` | **radix** `AlertDialog` | `alert-dialog` | `EditView` 저장 안 한 채 떠나기 확인 | ✅ T048 · 화면 적용 T050 (닫기·재실행 확인)·T051 — `AlertDialogAction` 은 들이지 않음(busy 동안 창이 남는다) |
| `OverlayPane.tsx` | `DetailPanel` · `DetailPanelTitle` | **radix** `Dialog` `modal={false}` · 포털 없음 | — (research R7) | `ui/Surface` `OverlayPane` · `StepDetail` 의 `role="dialog"` 수제 판 | ✅ T052 — `StepDetail` · 바깥 상호작용은 닫힘이 아님 |
| `DropdownMenu.tsx` | `Menu` · `MenuTrigger` · `MenuContent` · `MenuItem` | **radix** `DropdownMenu` | `dropdown-menu` | `TestList` 행 메뉴(수제 포털·위치 계산·스크롤 닫힘) | ✅ T055 · 화면 적용 T056 (`TestList` 행 메뉴) — 닫힐 때 이미 다른 칸이 초점을 가졌으면 빼앗지 않는다 |
| `Tabs.tsx` | `Tabs` · `TabsList` · `TabsTrigger` · `TabsContent` | **radix** `Tabs` | `tabs` | `ui/Table` `Tabs` · `TargetPane` 산출물 탭(클래스 복사본) | ✅ T058 — `TargetPane` 산출물 탭 (뿌리 `asChild`) |
| `ToggleGroup.tsx` | `ToggleGroup` · `ToggleGroupItem` (`appearance`: `segmented` · `filter` · `chip` · `card`) | **radix** `ToggleGroup` `type="single"` | `toggle-group` · `toggle` | `ui/Table` `Segmented` · `PacingControl` · `TestList` 거르기·정렬 · `TestGroupBar` 칩 · `WorkArea` 만드는 방법 카드 · `InsertStepForm` 가짜 라디오 2곳 | ✅ T059~T061 — 실행 속도(segmented) · 결말 거르기·Step 넣기 종류·일치 방식(filter) · 그룹 칩(chip · N-06) · 만드는 방법(card). 묶음은 `radiogroup` |
| `Tooltip.tsx` | `Tooltip` · `Truncate` — 공급자(`TooltipProvider`)는 **내보내지 않는다.** 원본 `Tooltip` 처럼 툴팁마다 뿌리를 공급자로 감싼다 | **radix** `Tooltip` | `tooltip` | 잘린 글자·아이콘 단추의 `title` 만으로 보이던 전체 이름 (비활성 사유의 `title` 은 **유지**) | ✅ T063·T064 — 행 메뉴 `⋮` · 알림 `×` · Step 상세 닫기. `Truncate` 는 US3 T074 에서 쓴다 · T089 — 내보내는 것을 실제와 맞췄다 |
| `Disclosure.tsx` | `Disclosure` | native `<details>` | — (Radix `Collapsible` 은 쓰지 않는다) | `StepDetail` ▸/▾ 수제 토글 3곳 · 모양이 제각각인 `<details>` 10곳 | ✅ T065 — `<details>` 10곳 · Step 상세 수제 토글 3곳 (요약 줄 세 모양 · 표식 ▸/▾ 하나) |
| `Table.tsx` | `Table` · `TableHeader` · `TableBody` · `TableFooter` · `TableRow` · `TableHead` · `TableCell` · `rowClasses` · `Row` · `Spacer` | raw | `table` | `ui/Table` 전부 · `DraftList` 원시 `<table>` · `LocatorPriorityTable` · `ImportPreview` 표 2곳 | ✅ T035 · 화면 적용 T044·T045 (`compact` 변종 · `align` · `muted` 추가 · N-05) |
| `Notice.tsx` | `Notice` · `Toast` · `ToastLayer` · `TOAST_LAYER_CLASSES` | raw | — (015 계승 · research R6) | 같음 + `Workbench` 알림 층 복사본 | ✅ T021(US1)·T066 — 층 클래스 하나 · 클래스 잇기 `cn` |
| `Surface.tsx` | `Pane` · `PaneHead` · `AppHeader` · `Scrim` · `Divider` | raw | — (015 계승) | 같음. `Modal`·`OverlayPane` 은 위 부품으로 옮긴다 | ✅ T052·T066 — `Modal`·`OverlayPane` 을 지웠다 · 클래스 잇기 `cn` |
| `StepRow.tsx` | (015 그대로) | raw | — | 체크 칸은 `Checkbox` 를 쓴다 | ✅ T066 — 클래스 잇기 `cn` (체크 칸의 입력은 `Checkbox` 로 T042) |
| `useToastDismiss.ts` | (그대로) | — | — | — | — |

**들이지 않는 shadcn 부품**: `select` · `checkbox` · `radio-group` · `collapsible` · `sonner` · `label`.
이유는 research R2 — 네이티브가 모습과 동작을 이미 갖는다.

## §1-2 — 갈래를 Base UI 로 (2026-09-16 개정)

위 표의 `behavior = radix` 부품 여덟을 **같은 자리에서** Base UI 로 옮긴다. 화면 코드는 바뀌지
않는다 — 부품이 감싸기 때문이다.

| 부품 | 지금 (Radix) | Base UI | 바뀌는 것 |
|---|---|---|---|
| `Button` | `Slot` 로 `asChild` | (동작 층 없음) | **`asChild` 제거.** 부모가 `render={<Button/>}` 로 받는다 |
| `Dialog` | Root/Portal/Overlay/Content · `onInteractOutside` · 수제 `useReturnFocus` | Root/Portal/**Backdrop**/**Popup** | 바깥 누름은 `onOpenChange` 의 **닫힌 이유**로 · 초점은 `initialFocus`/`finalFocus` (수제 훅 삭제) |
| `AlertDialog` | 같은 구조 | 같은 구조 | 취소 단추가 `Close render={<Button/>}` |
| `OverlayPane` | `Dialog modal={false}` · 포털 없음 | `Dialog modal={false}` · **`Portal container=` 로 작업대 안에** (S6 — 포털은 뺄 수 없다) | 바깥 누름 무시를 이유 판정으로 · 자리 계약은 그대로 |
| `DropdownMenu` | Trigger/Portal/Content 가 자리도 갖는다 | Root/Trigger/Portal/**Positioner**/Popup | 자리 속성이 `Positioner` 로 · `onCloseAutoFocus` → Popup `finalFocus`(N-08 의 「이름」 초점이 여기로) |
| `Tabs` | Root/List/Trigger/Content · `data-state=active` | Root/List/**Tab**/**Panel** · **`data-active`** | 선택 상태 문자 · 뿌리 `asChild` → `render` |
| `ToggleGroup` | `type="single"` → `radiogroup`/`radio` · `aria-checked` | 기본 배타 · **눌림**(`aria-pressed`·`data-pressed`) · 값이 배열 | 낭독되는 의미가 바뀐다 · **빈 값 금지를 부품이 강제**(S7) |
| `Tooltip` | 툴팁마다 공급자 | **앱 뿌리에 공급자 하나** · Positioner/Popup | `delayDuration` → 공급자의 `delay` |
| `Toast` (신규) | `ui/Notice` + `components/Toast` + `useToastDismiss` + `NoticeStack` 타이머 | Provider/Portal/Viewport/Root + 관리자 | 화면은 **뜻과 문구만** 넘긴다 · 자리는 Viewport 한 곳 (layout-contract-v3 L2 개정) |

## §2 — 이식 대응표 (shadcn → 정본)

원본 클래스를 **이 표대로** 옮긴다. 표에 없는 원본 클래스를 만나면 표에 줄을 더한 뒤 옮긴다 —
부품마다 다른 대응을 즉석에서 고르지 않는다 (015 SC-010).

### 색

| shadcn | 정본 | 비고 |
|---|---|---|
| `bg-background` · `text-foreground` | `bg-bg` · `text-ink` | |
| `bg-primary` · `text-primary-foreground` | `bg-ink` · `text-panel` | 주 동작은 채움으로 말한다 (FR-269) |
| `hover:bg-primary/90` | `hover:bg-ink-2` | 015 `ui/Button` primary |
| `bg-secondary` · `text-secondary-foreground` | `bg-panel` · `text-ink` + `border-hair-2` + `shadow-e1` | 정본 기본형 `.btn` |
| `bg-accent` · `text-accent-foreground` (hover·지목) | `bg-sunken-2` · `text-ink` | `button:hover` |
| `bg-muted` | `bg-sunken` | |
| `text-muted-foreground` | `text-ink-2` (보조 글) · `text-ink-3` (흐린 글·자리 표시) | `.muted` · `.dim` |
| `bg-destructive` · `text-white` | `bg-panel border-fail text-fail` · `hover:bg-fail-t` | **위험은 채우지 않는다** — 정본 `.btn.danger` 는 테두리형 |
| `text-destructive` | `text-fail` | |
| `bg-popover` · `text-popover-foreground` | `bg-panel` · `text-ink` + `border border-hair-2 shadow-e2` | 떠 있는 것은 `e2` (정본 규율) |
| `border-border` | `border-hair` | |
| `border-input` | `border-hair-2` | |
| `bg-black/50` (가림막) | `bg-scrim-strong` (대화상자) · `bg-scrim` (겹침 판) | |
| `aria-invalid:border-destructive` | `aria-[invalid=true]:border-fail` | **`aria-invalid:` 는 Tailwind v4 에 없는 변종이다** — v4 가 기본으로 주는 aria 변종은 불리언 목록(`checked`·`disabled`·`expanded` 등)뿐이다. shadcn 원본은 자기 `shadcn/tailwind.css` 가 등록한 변종에 기대고, 그 CSS 를 들이지 않는 이 저장소에서는 **아무 CSS 도 생기지 않는다.** 017 T029 에서 G-B 가 잡았다 |
| `aria-invalid:ring-destructive/20` | **삭제** | 링을 쓰지 않는다 |
| `placeholder:text-muted-foreground` | `placeholder:text-ink-3` | S-06 |
| `selection:bg-primary selection:text-primary-foreground` | **삭제** | 정본에 선택 색이 없다 |

### 기하

| shadcn | 정본 | 비고 |
|---|---|---|
| `rounded-md` | `rounded-base` (3px) | |
| `rounded-sm` · `rounded-xs` · `rounded-[4px]` · `rounded-[2px]` | `rounded-chip` (2px) | |
| `rounded-lg` (대화상자) | `rounded-lg` (6px, 정본 `--radius-lg`) | 이름은 같고 값은 정본이다 |
| `shadow-xs` (버튼) | `shadow-e1` | |
| `shadow-xs` (입력칸) | **삭제** | 정본 입력칸은 그림자가 없다 |
| `shadow-md` · `shadow-lg` | `shadow-e2` | |
| `h-9` · `h-8` | `h-control` (32) · `h-control-sm` (26) | |
| `size-9` (아이콘 단추) | `h-control-sm px-[7px]` | 015 `icon` 크기 |
| `px-4 py-2` · `px-3` | `px-s3` · `px-[9px]` (sm) | |
| `gap-2` (버튼) | `gap-[6px]` | 정본 `.btn` |
| `text-sm` · `text-xs` | `text-[13px]` · `text-[12px]` · `text-[11px]` | |
| `font-medium` (버튼) | `font-semibold` | 정본 `.btn` 600 |
| `border-2` · `ring-[3px]` | **삭제** | 정본 선은 1px |

### 상태

| shadcn | 정본 | 비고 |
|---|---|---|
| `disabled:pointer-events-none disabled:opacity-50` | `disabled:bg-transparent disabled:border-dashed disabled:border-hair-2 disabled:text-ink-3 disabled:shadow-none disabled:font-medium disabled:cursor-not-allowed` | **자리를 지키는 점선.** 포인터를 막지 않는다 — 사유의 `title` 이 떠야 한다 (FR-014) |
| `has-[select:disabled]:opacity-50` | `has-[select:disabled]:…` 위와 같은 점선 형태 | `native-select` 감싸개 |
| `focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring` | **삭제** | 전역 `:focus-visible{outline:2px solid var(--run)}` (S-14) |
| `outline-none` · `outline-hidden` | **삭제** | G-F · `FocusRing` 이 막는다 |
| `data-[state=open]:bg-accent` | `data-[state=open]:bg-sunken-2` | |
| `data-[state=active]:bg-background data-[state=active]:shadow-sm` (탭) | `data-[state=active]:bg-panel data-[state=active]:text-ink` | 정본 `.tabs > button[aria-pressed=true]` |
| `data-[state=on]:bg-accent` (토글) | `data-[state=on]:bg-sunken data-[state=on]:text-ink data-[state=on]:font-bold` | 정본 `.segmented` |
| `data-[disabled]:opacity-50` (메뉴 항목) | `data-[disabled]:text-ink-3 data-[disabled]:cursor-not-allowed` | |
| `data-[variant=destructive]:text-destructive` (메뉴 항목) | `data-[variant=danger]:text-fail` | |

### 움직임 · 테마 · 아이콘

| shadcn | 정본 | 비고 |
|---|---|---|
| `animate-in` · `animate-out` · `fade-*` · `zoom-*` · `slide-in-from-*` · `transition-*` · `duration-*` | **삭제** | 정본에 움직임 언어가 없다 (FR-010) |
| `dark:*` | **삭제** | 다크 모드 없음 |
| `data-open:` · `data-closed:` · `data-checked:` (레지스트리의 사용자 정의 변종) | `data-[state=open]:` · `data-[active]:` · `data-[pressed]:` 등 표준 형태 | 사용자 정의 변종을 등록하지 않는다 |
| **(09-16)** 탭 선택 상태 `data-[state=active]:` | `data-[active]:` | 갈래가 쓰는 속성 이름이 다르다 |
| **(09-16)** 고르기 상태 `data-[state=on]:` | `data-[pressed]:` | 같음 |
| `lucide-react` `XIcon` · `CheckIcon` · `ChevronDownIcon` · `CircleIcon` | `×` · `✓` · `▾` · (없음) — `<span aria-hidden>` | |
| `[&_svg]:size-4` · `[&_svg:not([class*='size-'])]:size-4` | **삭제** | 아이콘 묶음이 없다 |

## §3 — 부품이 흡수하는 특수 자리

원시 요소 예외로 두지 않고 부품의 변종으로 받는 자리다 (FR-002 의 예외를 늘리지 않는다).

| 자리 | 부품 · 변종 | 이유 |
|---|---|---|
| 국면 띠의 테스트 이름 (`PhaseBar.tsx:206`) | `Input variant="title"` | 평소 표시처럼 보이고 hover·초점에 테두리가 드러난다 (S-08~S-10). 초점 링 대신 테두리 — `exceptions.ts` 등록 유지 |
| 인라인 이름 고치기 (`TestGroupBar.tsx:130` · `ProjectSetup.tsx:540`) | `Input` (기본 크기) + `layout` 폭 | Enter·Esc·blur 처리는 화면 몫. **계획의 `size="sm"` 은 두지 않았다** (T040·T046) — 두 자리 모두 전환 전 32px 칸이었고, 줄이면 옆 버튼(32px)과 높이가 어긋난다. 크기 축이 필요한 자리가 생기면 그때 더한다 |
| 옮겨 적는 글자 칸 (주소·셀렉터·변수 이름·확인 문구) | `Input font="mono"` | 전환 전 `className="font-mono"` 를 화면이 입혔다. `layout` 으로 넘기면 부품의 `font-sans` 와 같은 속성을 다툰다 — 축으로 둔다 (N-03) |
| AI 에게 건네는 한 줄 (`ActionPalette` 자연어 Step 추가) | `Input variant="ai"` | `Textarea variant="ai"` 와 같은 문법 — 테두리만 `--ai` |
| 폼 안에서 위아래 칸과 폭을 맞추는 선택칸 (`InlineSecretInput` · `ImportPreview` 열 짝짓기 · `PhaseBar` 그룹) | `NativeSelect width="fill"` | 기본은 내용 폭(B-07). 폭을 `layout` 으로 넘기면 `w-auto` 와 다툰다 |
| `Field` 안의 입력 (검색) | `Input variant="bare"` | 테두리는 `Field` 가 그린다 |
| AI 지시문 | `Textarea variant="ai"` | 정본 `textarea.ai{border-color:var(--ai)}` |
| 클릭 전파를 멈추는 행 체크박스 (`TestList.tsx:1280` · `StepList.tsx:551`) | `Checkbox` 의 `onClick` 통과 | 부품이 사건을 삼키지 않는다 |
| 행 선택 글자 단추 (`StepList.tsx:573`) | `Button variant="bare"` | 이름 모양 그대로 누를 수 있는 요소 (정본 `.srow-name`) |
| 브라우저 파일 선택 중계 (`BrowserPromptPanel.tsx:96`) | `FileButton multiple` | 보이지 않되 초점은 남는 015 구조 |
| 밑줄 해소 링크 (`ActionButton:161` · `PhaseBar:256` · `ActionPalette:410`) | `Button variant="link"` | 정본 `.textlink` |
| 버튼인데 모양이 없는 것 (`ErrorNotice` · `SessionLostBanner` · `KeyManagement` 등 16곳) | `Button` | 전역 `button{}` 에 기대던 자리 |

**원시 요소 예외로 남는 것** (`theme/exceptions.ts` · `raw-element` 축):

| 자리 | 이유 |
|---|---|
| `components/MirrorView.tsx` IME 조합 칸 `<textarea>` | 보이지 않고 포인터를 받지 않으며 한글 조합만 받는다. 부품의 모습·초점 규칙이 전부 방해가 된다 (010) |

## §4 — 부품이 지켜야 할 동작

| 부품 | 요구 | 확인 |
|---|---|---|
| `Dialog` · `AlertDialog` | 열리면 초점이 안으로, Tab 이 밖으로 나가지 않는다, Esc 로 닫힌다(`AlertDialog` 는 되돌릴 수 없는 조작을 실행하지 않고 닫는다), 닫히면 연 조작으로 초점이 돌아온다 (FR-011) | 부품 테스트 + 화면 테스트 |
| `Dialog` · `AlertDialog` | 알림 층 안에서 시작한 바깥 상호작용은 닫힘이 아니다 (research R6 ④) | 부품 테스트 |
| `DetailPanel` | 초점 이동·Esc·되돌림은 같고 **초점을 가두지 않는다.** Step 목록 안 클릭은 닫힘이 아니다 (R7) | `DetailPlacement` |
| `Menu` | 트리거에 `aria-haspopup`·`aria-expanded`. 키보드로 열고 화살표로 오가고 Esc·바깥 클릭으로 닫는다. 트리거는 `aria-label` 을 유지한다(`{행 이름} 추가 동작`) (FR-012) | `RowMenuVisible` 외 |
| `ToggleGroup` | 고른 항목을 보조기술에 알린다(`role="radio"`·`aria-checked`). 화살표로 오간다 (FR-013) | `PacingControl` 외 |
| `Tabs` | `tablist`·`tab`·`tabpanel`, 화살표 이동 | `TargetPane` |
| `Tooltip` | hover 와 **초점**에 뜬다. 비활성 조작에는 쓰지 않는다 | 부품 테스트 |
| 모든 조작 | 비활성은 점선으로 자리를 지키고 포인터를 막지 않는다 (FR-014) · 초점 윤곽선을 지우지 않는다 (FR-015) | G-F · `FocusRing` · `InteractionStates` |
| 버튼 · 칩 · 표 머리 | 한국어가 단어 중간에서 줄바꿈되지 않는다 — `whitespace-nowrap`, 줄어들 자리에 놓이면 `shrink-0` 또는 `Truncate` (FR-019) | 순회 |
| `NativeSelect` · `Checkbox` | 정본 요소 규칙(`width:100%`·`min-height:32px`)이 번지지 않도록 크기를 명시한다 (B-07 · B-08) | 순회 |
