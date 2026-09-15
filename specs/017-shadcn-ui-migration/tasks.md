---
description: "Task list for 017 shadcn/ui 부품 체계 전환과 화면 깨짐 전수 수정"
---

# Tasks: shadcn/ui 부품 체계 전환과 화면 깨짐 전수 수정

**Input**: Design documents from `/specs/017-shadcn-ui-migration/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) ·
[data-model.md](data-model.md) · [contracts/](contracts/) · [baseline.md](baseline.md)

**Tests**: 이 기능은 **기존 테스트를 지키는 것**(FR-028, 헌법 Quality Gate 4)과 **깨짐이 다시 들어오지 않게 하는
것**(FR-029·FR-030·US4)이 요건이다. 새 가드·순회 보고서 테스트·동작 테스트는 요건에서 직접 나오므로 선택
사항이 아니다. 테스트를 고칠 때마다 [contracts/test-ledger.md](contracts/test-ledger.md) 에 줄을 채운다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일 · 미완료 작업에 의존하지 않음)
- **[Story]**: US1 / US2 / US3 / US4
- 모든 작업에 파일 경로가 있다

## Path Conventions

Web app 구조. `frontend/src/` · `frontend/tests/` · 저장소 루트 `scripts/`.
**백엔드는 건드리지 않는다** (plan.md Constitution Check — 원칙 II 증거).

## 규모 (전환 전 실측 — [baseline.md](baseline.md))

| 축 | 값 |
|---|---|
| 테스트 | 110 파일 · 1364 건 · 단언 2148 · 무른 단언 639 |
| 원시 조작 요소 (앱 코드) | `<button>` 50 · `<input>` 50 · `<select>` 4 · `<textarea>` 5 |
| 부품 사용 | `<Button` 88 · `navLinkClasses` 26 · `<Chip`류 41 |
| 수제 상호작용 | 대화상자 5 · 행 메뉴 1 · 탭 줄 1 · 분절·토글 6 · ▸/▾ 펼침 3 — **초점 처리 0** |
| 알림 층 정의 | 3곳 (정본 클래스 · `ui/Notice` · `Workbench` 복사본) |
| 화면 깨짐 | 11건 (B-01~B-11) |
| 산출물 gzip | CSS 6.16 kB · JS 139.48 kB |

## 공통 규칙 — 모든 작업에 적용

- **한 부품·한 화면 = 한 커밋.** 커밋 전에 `cd frontend && npx tsc --noEmit && npx vitest run` 전량 통과.
- `src/` 가 바뀌면 `BeforeAfterParity` 가 실패한다 — 커밋 전에
  `backend/.venv/bin/python scripts/design_compare_ba.py --compare` 를 돌리고, 차이는 고치거나 사유와 함께
  `INTENDED` 에 등록한다.
- 원시 요소를 옮긴 커밋은 `frontend/tests/RawElements.test.ts` 의 `REMAINING_BUDGET` 을 같은 커밋에서 내린다.
- shadcn 원본을 이식할 때는 [contracts/ui-parts.md](contracts/ui-parts.md) §2 대응표를 따르고 파일 머리에 출처를
  적는다. 표에 없는 클래스는 표에 줄을 더한 뒤 옮긴다.
- 테스트를 고치면 [contracts/test-ledger.md](contracts/test-ledger.md) 에 `verifies`·`change`·`why`·전후 단언 수를 적는다.

---

## Phase 1: Setup — 스파이크와 의존성

**Purpose**: research 의 스파이크 S1~S5 를 해소하고 의존성을 들인다. **화면은 하나도 바뀌지 않는다.**

**⚠️ 스파이크가 실패하면 research 의 해당 「버린 대안」으로 되돌아가 결정을 고친 뒤 진행한다.**

- [X] T001 스파이크 S1 — `frontend/src/theme/tailwind.css` 의 `@theme inline` 에 `--radius-*: initial; --shadow-*: initial; --inset-shadow-*: initial; --drop-shadow-*: initial; --text-*: initial; --animate-*: initial;` 을 넣고 **정본 이름을 되살린 뒤**(`--radius-base`·`--radius-chip`·`--radius-lg`·`--shadow-e1`·`--shadow-e2`) `npx vite build` 산출 CSS 를 전후 비교한다. 확인: 산출 CSS 에서 사라진 선언이 기본 스케일뿐인가, `shadow-none`·`rounded-none`·`rounded-full`·`leading-none` 이 여전히 생성되는가. 결과를 [research.md](research.md) 스파이크 표 S1 에 기록하고, 이 시점에는 변경을 되돌린다 (적용은 T009)
- [X] T002 [P] 스파이크 S2 — 임시 파일 `frontend/src/ui/__spike_cva.tsx` 에 `cva` 로 된 버튼 변종 표를 두고 `frontend/tests/helpers/tailwind.ts` 의 G-E 조합기가 `cva(base, {variants, compoundVariants})` 를 읽도록 시험 구현한다. 역전 쌍을 일부러 넣어 `ClassConflict` 가 실패하는지 확인하고, 결과를 research S2 에 기록한다. 임시 파일은 지운다 (헬퍼 변경은 T012 에서 확정)
- [X] T003 [P] 스파이크 S3 — `radix-ui`·`class-variance-authority` 를 **임시로** 설치하고 `frontend/tests/setup/dom.ts` 초안(ResizeObserver · PointerEvent · has/set/releasePointerCapture · scrollIntoView)을 `vite.config.ts` `test.setupFiles` 로 실은 뒤 (1) 기존 1364건이 그대로 통과하는지 (2) 임시 테스트에서 Radix `Dialog`·`DropdownMenu`·`Tooltip` 이 jsdom 에서 열리고 닫히는지 확인한다. `MirrorView.test.tsx:63` 의 지역 폴리필과 충돌이 없는지 본다. research S3 에 기록
- [X] T004 [P] 스파이크 S4 — `scripts/screen_sweep.py` 초안이 제품 서버(빈 포트) + **Vite 개발 서버**(`ITB_API_PORT`·`ITB_UI_PORT`·`ITB_HEADLESS=1`)로 녹화 세션 화면을 열었을 때 「실시간 연결이 끊겼습니다」가 **뜨지 않는지** 확인한다. 격리 `XDG_*` 는 `.sweep/data` 로 고정. 방식은 `backend/tests/abnormal/product_ui.py` 와 전환 전 실측 스크립트(세션 스크래치 `ui_sweep.py`)를 따른다. research S4 에 기록
- [X] T005 [P] 스파이크 S5 — `:root:has([data-shell=phase]) &` 와 `:root:has([data-shell=header]):not(:has([data-shell=phase])) &` 형태의 Tailwind 임의 변종이 생성되는지(`npx @tailwindcss/cli`), chromium 에서 셋이 서로 배제되는지(Playwright 로 빈 페이지) 확인한다. research S5 에 기록
- [X] T006 `radix-ui`(1.6.x)·`class-variance-authority`(0.7.x)를 버전 고정으로 `frontend/package.json` 에 설치한다 — `cd frontend && npm i radix-ui@1.6.7 class-variance-authority@0.7.1`. `frontend/package-lock.json` 에 남긴다. `npm ls tailwind-merge lucide-react tw-animate-css` 가 비어 있음을 확인 (T003 의존)
- [X] T007 [P] `.gitignore` 에 `.sweep/` 를 더한다 (순회 캡처·격리 데이터 — screen-sweep.md SW-8)

**Checkpoint**: 스파이크 다섯이 결론을 냈고 research.md 에 적혔다. 의존성이 들어왔고 화면은 그대로다.

---

## Phase 2: Foundational — 가드와 순회를 먼저 세운다

**Purpose**: 부품을 옮기기 **전에** 감시 장치를 세운다. 015 가 배운 순서다 — 가드 없이 옮기면 무엇이 언제
깨졌는지 알 수 없고, 옮긴 뒤 만들면 이미 들어온 위반이 기준선이 된다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에 사용자 스토리 작업을 시작하지 않는다.

- [X] T008 `frontend/tests/setup/dom.ts` 를 확정하고 `frontend/vite.config.ts` `test.setupFiles` 에 싣는다 — 각 폴리필에 **왜 필요한가**(어느 Radix 부품이 무엇을 부르는가)를 주석으로 적는다 (research R10 · T003 결과)
- [X] T009 `frontend/src/theme/tailwind.css` 에 이름공간 비우기를 적용한다 (T001 결과대로). 머리주석의 「색 네임스페이스를 비우는 이유」 절을 radius·shadow·text·animate 로 넓혀 적는다. `TailwindThemeLiteral`·`ClassExistence` 통과 · L2 `--compare` 불일치 0 확인 (research R4)
- [X] T010 [P] `frontend/src/ui/cn.ts` 를 만든다 — 거짓 값을 걸러 공백으로 잇는 함수 하나. **`tailwind-merge` 를 쓰지 않는 이유**(병합기가 정본 스케일을 모른다 · 호출자 덮어쓰기 금지)를 머리주석에 적는다 (research R5)
- [X] T011 `frontend/tests/helpers/tailwind.ts` 의 클래스 목록 판정 문자 집합을 넓힌다 — **대괄호 안에서만** `= & > ( ) , + * ~ " '` 허용 (guards H-2). 넓힌 뒤 새로 실패하는 기존 클래스(예: `frontend/src/ui/Table.tsx:162` 의 `[&>button[aria-pressed=true]]:…`)는 가드를 좁히지 않고 **코드를 고친다**. 무엇이 새로 드러났는지 헬퍼 머리주석에 적는다
- [X] T012 `frontend/tests/helpers/tailwind.ts` 의 G-E 조합기가 `cva(base, { variants, compoundVariants, defaultVariants })` 와 `cn(…)` 인자를 읽게 넓힌다 (guards H-1 · T002 결과). `frontend/tests/ClassConflict.test.ts` 자체 점검 하한(`> 20`)을 유지하고, 머리주석에 무엇을 넓혔는지 적는다
- [X] T013 [P] `frontend/tests/FocusRing.test.tsx` 금지 목록에 `outline-hidden` 을 더한다 (Tailwind v4 이름 · guards 표)
- [X] T014 [P] 가드 G-F 를 `frontend/tests/UiSkin.test.ts` 에 만든다 — `frontend/src/ui/**/*.tsx` 에서 [guards.md](contracts/guards.md) G-F 금지 목록(비활성 흐림 · 비활성 포인터 차단 · `ring-` · `outline-none|hidden|0` · 움직임 · `dark:` · 사용자 정의 상태 변종 · `lucide-react`·`tailwind-merge`·`cn`·`tw-animate-css` 가져오기)을 검사한다. 요구(조작 부품의 `disabled:border-dashed` · `radix-ui` 가져오기 허용 파일 · 출처 줄)는 **파일이 있을 때만** 검사한다. 기존 `src/ui/*.tsx` 7개 머리에 출처 줄 `015` 를 더한다. 금지 형태를 일부러 넣어 실패를 확인하고 되돌린다
- [X] T015 [P] `frontend/src/theme/exceptions.ts` 에 `raw-element` 축을 더하고 미러 IME 칸(`frontend/src/components/MirrorView.tsx` 의 `<textarea>`)을 사유와 함께 등록한다. 가드 G-G 를 `frontend/tests/RawElements.test.ts` 에 만든다 — `src/ui/` 밖 `.tsx` 의 `<button|input|select|textarea` 를 세고, 등록된 예외와 짝짓고, **`REMAINING_BUDGET`**(전환 전 기준값)을 둔다. 센 수 > 예산이면 실패, 센 수 < 예산이면 「예산을 내려라」로 실패 (guards G-G)
- [X] T016 `scripts/screen_sweep.py` 를 [contracts/screen-sweep.md](contracts/screen-sweep.md) SW-1~SW-8 대로 만든다 — 격리 · 시드(실제 재실행으로 결과) · 개발 서버 · 뷰포트 4종 · SW-5 화면 목록과 「닿았다」 증거 확인 · SW-6 판정 규칙(덮임은 중심점, 줄바꿈은 세로 겹침으로 묶은 줄 수) · SW-7 허용 등록부 · `.sweep/shots/` 캡처 · `frontend/tests/sweep-report.json`(소스 digest 포함). **알려진 깨짐 등록부**를 두어 B-01~B-11 을 `pending` 으로 싣는다 — 검출이 `pending` 과 맞으면 따로 보고하고, `pending` 항목이 더는 어떤 검출과도 맞지 않으면 「고쳐졌으니 등록부에서 지워라」로 실패한다 (T004 의존)
- [X] T017 `frontend/tests/ScreenSweep.test.ts` 를 만든다 — `sweep-report.json` 의 digest 가 지금 소스와 같은가(낡음) · 등록되지 않은 검출 0 · SW-5 화면 × SW-4 폭 전부 존재 · `pending` 항목 수를 출력한다. 첫 보고서를 생성해 커밋한다 (T016 의존). 이 시점 보고서에서 B-01~B-11 이 전환 전 실측([baseline.md](baseline.md))과 같이 검출되는지 대조한다
- [X] T018 L2 기준을 이 단계 끝 상태로 맞춘다 — `backend/.venv/bin/python scripts/design_compare_ba.py --compare` 불일치 0 · `frontend/tests/BeforeAfterParity.test.ts` 통과

**Checkpoint**: 가드 G-E·G-F·G-G·`FocusRing` 이 새 체계를 읽고, 순회가 깨짐 11건을 `pending` 으로 재고, 화면은 그대로다. 테스트 전량 통과.

---

## Phase 3: User Story 1 — 보이는 조작은 누를 수 있다 (Priority: P1) 🎯 MVP

**Goal**: 결과·녹화·목록 화면에서 알림이 떠 있어도 국면 띠와 흐름 안 띠의 조작을 누를 수 있다 (B-01 · B-02).

**Independent Test**: 순회의 `result-fail`·`runner-record`·`runner-disconnected`·`test-list-session` 을 폭 4종에서
돌려 국면 띠·세션 띠 조작의 덮임이 0 이고 B-01·B-02 가 `pending` 에서 빠진다. 부품 전환이 없어도 성립한다.

### Tests for User Story 1

- [X] T019 [US1] `frontend/tests/ToastPlacement.test.tsx` 에 단언을 **더한다** — `TOAST_LAYER_CLASSES` 가 띠 조건 셋(없음 · 머리띠만 · 국면 띠)을 `:has` 변종으로 갖고 머리띠 조건이 `:not(:has([data-shell=phase]))` 로 국면 띠 조건을 배제한다 · 층이 `aria-live="polite"` 를 갖는다. 먼저 실패를 확인한다 (layout-contract-v3 L2 · test-ledger)

### Implementation for User Story 1

- [X] T020 [US1] (Foundational T016 에서 앞당겼다 — 순회가 머리띠 표식으로 B-11 을 잰다) 머리띠 부품이 `data-shell="header"` 를 내보낸다 — `frontend/src/ui/Surface.tsx` `AppHeader`, `frontend/src/components/design/Chrome.tsx` `HeaderBar`. 국면 띠가 `data-shell="phase"` 를 내보낸다 — `frontend/src/components/workbench/PhaseBar.tsx`
- [X] T021 [US1] `frontend/src/ui/Notice.tsx` 의 `TOAST_LAYER_CLASSES` 를 v3 L2 표대로 고친다 (서로 배제하는 `top`·`max-height` 셋) · `ToastLayer` 에 `aria-live="polite"`. 머리주석에 B-01 의 원인(09-11 수정이 앱에 실리지 않는 정본 클래스 규칙에만 들어갔다)을 적는다 (T019·T020 의존)
- [X] T022 [US1] `frontend/src/components/Toast.tsx` 의 포털 층에 `aria-live="polite"` 를 두고 `frontend/src/components/workbench/Workbench.tsx:321` 의 알림 층 **클래스 복사본을 지워** `TOAST_LAYER_CLASSES` 를 쓴다 (T021 의존). `NoticesAreToasts`·`ChatDoesNotCoverMirror`·`PromptDoesNotShrinkMirror` 통과 확인
- [X] T023 [US1] B-02 — `frontend/src/pages/TestList.tsx` 의 진행 중 세션 **토스트**(`data-open-session`, 546~579행 부근)를 지운다. 흐름 안 `ActiveSessionsBanner` 가 그 사실을 말한다. `frontend/tests/NoticesAreToasts.test.tsx` 의 진행 중 세션 경우를 「그 사실을 흐름 안 띠 **하나**가 말한다」로 바꾸고 test-ledger 에 사유(research R6 ⑤ · 09-10 사용자 결정과의 긴장)를 적는다. `ActiveSessions.test.tsx` 통과 확인. 토스트의 「실행 화면 보기」에 기대던 `ListLiveState.test.tsx:81`·`RecheckPhase12.test.tsx:354` 는 복귀 조작을 띠의 「이어서 보기」로 찾도록 바꾼다 — 검증 대상(005 FR-168 복귀 수단)은 그대로이고, 같은 조작이 둘이던 것이 008 의 「복귀 조작은 화면에 하나뿐」을 어겼다
- [X] T024 [US1] 순회를 다시 돌려 `sweep-report.json` 을 갱신한다 — B-01·B-02 검출이 사라졌음을 확인하고 알려진 깨짐 등록부에서 지운다. L2 `--compare` 의 알림 층 `top` 차이를 사유(B-01)와 함께 `scripts/design_compare_ba.py` `INTENDED` 에 등록한다

**Checkpoint**: 알림이 조작을 덮지 않는다. MVP — 여기서 멈춰도 사용자가 겪던 작업 차단이 풀린다.

---

## Phase 4: User Story 2 — 부품이 한 체계에서 온다 (Priority: P2)

**Goal**: 조작·표시 부품이 shadcn 방식의 `src/ui/` 한 곳에서 오고, 모습은 정본, 동작은 표준이다.

**Independent Test**: G-G 예산 = 등록된 예외 수 · 옛 부품 참조 0 · [ui-parts.md](contracts/ui-parts.md) §1 상태 전부 ✅ ·
동작 테스트(`DialogFocus`·`MenuKeyboard`·`ToastOverModal`·`MirrorInputWithDialog`) 통과 · L2 등록되지 않은 차이 0.

### 4-A. 기본 부품 — 원본 이식

- [X] T025 [US2] `frontend/src/ui/Button.tsx` 를 shadcn `button` 이식으로 다시 쓴다 — `buttonVariants = cva(…)`, 변종 `default·primary·danger·off·quiet·ghost·nav·link·bare`, 크기 `md·sm·icon`, `asChild`(`radix-ui` `Slot`), `data-slot`·`data-variant`·`data-size` 유지, `whitespace-nowrap`. 정본 `.navlink`·`.textlink`·`.srow-name` 형태를 `nav`·`link`·`bare` 로 흡수한다. `navLinkClasses` 는 호출부 전환(T026)까지 `buttonVariants({variant:"nav"})` 를 돌려주는 얇은 함수로 둔다. `frontend/tests/InteractionStates.test.tsx`·`DesignTokens.test.tsx` 의 찾는 문자열을 갱신하고 test-ledger 에 적는다
- [X] T026 [US2] `navLinkClasses` 호출부 26곳을 `<Button variant="nav">` 로 옮기고 `navLinkClasses` 를 지운다 — `frontend/src/components/TestBulkConfirm.tsx`·`TestGroupBar.tsx`·`workbench/StepDetail.tsx`·`frontend/src/pages/EditView.tsx`·`ProjectSetup.tsx`·`SecretValues.tsx`·`TestList.tsx`(행 메뉴 항목 3곳은 T046 에서). 원시 `<button>` 이 줄면 G-G 예산을 내린다 (T025 의존)
- [X] T027 [P] [US2] `frontend/src/ui/Chip.tsx` 를 shadcn `badge` 이식으로 — `chipVariants`(tone `default·pass·fail·warn·run·ai·off`), `Pill`, 부품 차원의 `shrink-0 whitespace-nowrap` (B-05 의 칩 넘침). `chipClasses` 는 `chipVariants` 로 대체하고 호출부(`TestGroupBar.tsx`)를 옮긴다. `Badges.test.tsx`·`OutcomeVocabulary.test.tsx` 통과
- [X] T028 [P] [US2] `frontend/src/ui/Label.tsx` 를 만든다 — `Label`(폼 라벨 · 정본 `label{}` 형태를 명시), `Lbl`, `FieldLabel` 을 `ui/Field.tsx` 에서 옮기고 `Field.tsx` 가 다시 내보낸다(호출부 무변경)
- [X] T029 [P] [US2] `frontend/src/ui/Input.tsx` 를 shadcn `input` 이식으로 — 변종 `default·bare·title`, 크기 `md·sm`, 정본 비활성 점선·`placeholder:text-ink-3`·`aria-invalid:border-fail`. `title` 은 국면 이름 입력(S-08~S-10)의 형태를 갖는다
- [X] T030 [P] [US2] `frontend/src/ui/Textarea.tsx` 를 shadcn `textarea` 이식으로 — 변종 `default·ai`
- [X] T031 [P] [US2] `frontend/src/ui/NativeSelect.tsx` 를 shadcn `native-select` 이식으로 — 실제 `<select>`, **`w-auto` 가 기본**(정본 `width:100%` 번짐 차단 · B-07), 펼침 표시 `▾`(`aria-hidden`), 감싸개 비활성 점선
- [X] T032 [P] [US2] `frontend/src/ui/Checkbox.tsx` 를 만든다 — **네이티브** `<input type="checkbox">` 14px 명시(`accent-color` 잉크 · B-08), `checked`·`onCheckedChange`·`onClick` 통과(전파를 삼키지 않는다). `frontend/src/ui/StepRow.tsx` `StepCheck` 가 이것을 쓴다. `StepRowActions`·`RerecordStart`·`DeleteOutcome` 무변경 통과 확인 (research R2)
- [X] T033 [P] [US2] `frontend/src/ui/Radio.tsx` 를 만든다 — 네이티브 `<input type="radio">`, 크기 명시
- [X] T034 [US2] `frontend/src/ui/Field.tsx` 를 고친다 — `Field` 안쪽 입력은 `Input variant="bare"` 를 쓴다(`[&_input]` 벗기기 제거), `FileButton` 이 `multiple` 을 받는다, `cn` 사용 (T028·T029 의존)
- [X] T035 [P] [US2] `frontend/src/ui/Table.tsx` 를 shadcn `table` 이식으로 — `Table·TableHeader·TableBody·TableFooter·TableRow(mark)·TableHead·TableCell`, 머리 칸은 왼쪽 정렬·정본 머리 글꼴을 부품이 정한다(B-09). `rowClasses`·`Row`·`Spacer` 유지. `Tabs`·`Segmented` 는 T052·T053 까지 남긴다

### 4-B. 화면의 원시 요소를 부품으로 (파일마다 한 커밋 · 커밋마다 G-G 예산을 내린다)

- [X] T036 [P] [US2] `frontend/src/components/AssertionForm.tsx` — 버튼 1 · 입력 3 · 라디오 3 → `Button`·`Input`·`Radio` (T025·T029·T033 의존)
- [X] T037 [P] [US2] `frontend/src/components/BrowserPromptPanel.tsx` — 입력 1 · 파일 입력 1 → `Input`·`FileButton multiple`. `BrowserPrompt.test.tsx` 통과 (T034 의존)
- [X] T038 [P] [US2] `frontend/src/components/ErrorNotice.tsx` · `SessionLostBanner.tsx` · `InlineSecretInput.tsx` — 버튼 4 · 입력 2(비밀번호 포함) · 선택칸 1 → 부품. `InlineSecret`·`SensitiveAcrossPhases`·`abnormal/error-notice` 통과 (마스킹 유지)
- [X] T039 [P] [US2] `frontend/src/components/StepEditFields.tsx` — 입력 6(숫자 2 포함) → `Input`
- [X] T040 [P] [US2] `frontend/src/components/TestBulkConfirm.tsx` · `TestGroupBar.tsx` — 버튼 10 · 입력 3(인라인 이름 고치기 `Input size="sm"`) → 부품. 선택 띠의 「N개 선택됨」·「보이는 것 전부 선택」이 `whitespace-nowrap shrink-0` 을 갖는다 (B-07). `TestListSelection`·`TestGroups` 통과
- [X] T041 [P] [US2] `frontend/src/components/workbench/ActionButton.tsx` · `ActionPalette.tsx` — 밑줄 해소 링크 → `Button variant="link"`, 입력 2 · 여러 줄 1 · 지역 `Field` → `Input`·`Textarea variant="ai"`. `AuthoringParity`·`StepInsert` 통과
- [X] T042 [P] [US2] `frontend/src/components/workbench/PhaseBar.tsx` · `StepList.tsx` · `WorkArea.tsx` · `InsertStepForm.tsx` — 버튼 3 · 국면 이름 `Input variant="title"` · 선택칸 → `NativeSelect` · 체크박스 → `Checkbox` · 행 선택 글자 단추 → `Button variant="bare"` · 입력 4 · 여러 줄 2. `PhaseBarWidth`·`StepRowLayout`·`StepRowStates`·`ComposePhase` 통과
- [X] T043 [P] [US2] `frontend/src/components/workbench/StepDetail.tsx` — 버튼 3 · 입력 4 · 체크박스 1 → 부품 (판 자체는 T050)
- [X] T044 [P] [US2] `frontend/src/pages/DraftList.tsx` · `frontend/src/components/LocatorPriorityTable.tsx` — 원시 `<table>` → 표 부품 (B-09). `DraftList`·`DraftsFirstOnEmpty`·`LocatorPriorityTable` 통과
- [X] T045 [P] [US2] `frontend/src/pages/ImportPreview.tsx` — 입력 · 체크박스 · 라디오 · 선택칸 · 표 2 → 부품. `ImportPreview.test.tsx` 의 `fireEvent.change` 무변경 통과 확인
- [X] T046 [P] [US2] `frontend/src/pages/KeyManagement.tsx` · `SecretValues.tsx` · `ProjectSetup.tsx` — 버튼 14 · 입력 10(비밀번호 4 · 인라인 이름 고치기) → 부품. `KeyManagement`·`ProjectSetup`·`ProjectRowActions` 통과
- [X] T047 [US2] `frontend/src/pages/TestList.tsx` — 버튼(행 메뉴 제외) · 검색 입력(`Field` + `Input bare`) · 체크박스 2(머리 전체 선택 포함 · 같은 `Checkbox` · B-08) · 「그룹으로 옮기기」 선택칸 → `NativeSelect`(B-07). `TestListSelection`·`TestListFilters`·`TestGroups` 통과

### 4-C. 대화상자

- [X] T048 [US2] `frontend/src/ui/Dialog.tsx` 와 `frontend/src/ui/AlertDialog.tsx` 를 shadcn `dialog`·`alert-dialog` 이식으로 — `radix-ui` `Dialog`·`AlertDialog`, 포털, 가림막 `bg-scrim-strong`, z 30(v3 L1), 내용 `bg-panel border-hair-2 rounded-lg shadow-e2`, 닫기 표시 `×`, **`onInteractOutside`·`onPointerDownOutside` 에서 `[data-toast-layer]`·`[data-workbench-notice-layer]` 안이면 `preventDefault`**(research R6 ④), 움직임 없음
- [X] T049 [P] [US2] 동작 테스트 `frontend/tests/DialogFocus.test.tsx` · `frontend/tests/ToastOverModal.test.tsx` 를 쓴다 — 열면 초점이 안으로 · Tab 이 밖으로 나가지 않음 · Esc 닫힘(확인 대화상자는 조작 미실행) · 닫으면 연 조작으로 초점 복귀 · 모달이 열린 동안 알림 층이 `aria-hidden` 이 아니고 「닫기」를 눌러도 대화상자가 닫히지 않음 (FR-011 · SC-009 · T048 의존)
- [X] T050 [US2] `frontend/src/pages/SessionScreen.tsx` 의 지역 `Modal` 과 닫기·재실행·떠나기 확인 3개를 `Dialog`·`AlertDialog` 로 옮긴다 (떠나기 확인의 이름 입력은 `Dialog` + `Input`, 자동 초점은 `onOpenAutoFocus`). 지역 `Modal` 을 지운다. 확인 대화상자가 열린 동안 뒤쪽을 찾던 테스트(`SaveNamePrompt`·`RunTrigger`·`RunFinished`·`PauseTransition` 등)는 **닫은 뒤 찾도록 순서만** 바꾸고 test-ledger 에 적는다 (T048 의존)
- [X] T051 [US2] `frontend/src/pages/EditView.tsx` 의 저장 안 한 채 떠나기 확인(`role="alertdialog"` 수제 판)을 `AlertDialog` 로 옮긴다. `EditAfterFailure`·`EditEntryPoints` 통과 (T048 의존)
- [X] T052 [US2] `frontend/src/ui/OverlayPane.tsx` 에 `DetailPanel` 을 만든다 — `radix-ui` `Dialog` **`modal={false}`**, 포털 없음, 초점 이동·Esc·되돌림, Step 목록(`[data-step-row]`) 안 바깥 클릭은 닫힘이 아님 (research R7). `frontend/src/components/workbench/StepDetail.tsx` 와 `Workbench.tsx` 가 이것을 쓰고 `frontend/src/ui/Surface.tsx` 의 `OverlayPane`·`Modal` 을 지운다. `DetailPlacement`·`DetailBlocksMirrorInput`·`WorkbenchShell` 통과 — 판정 방법이 바뀌면 test-ledger (T048 의존)
- [X] T053 [P] [US2] 동작 테스트 `frontend/tests/MirrorInputWithDialog.test.tsx` — 대화상자가 열린 동안 미러로 가는 입력 0 · 닫은 뒤 미러 키 입력·한글 조합 경로가 전환 전과 같다 (FR-016 · SC-013 · T050 의존)
- [X] T054 [US2] `frontend/tests/ImplementationCount.test.ts` `RETIRED` 에 `SessionScreen` 지역 `Modal` · `ui/Surface` `Modal`·`OverlayPane` 을 올린다 (T050~T052 의존)

### 4-D. 메뉴

- [X] T055 [US2] `frontend/src/ui/DropdownMenu.tsx` 를 shadcn `dropdown-menu` 이식으로 — `Menu·MenuTrigger·MenuContent·MenuItem`(`data-variant=danger` → `text-fail`), 포털, z 40, 내용 `bg-panel border-hair-2 shadow-e2 rounded-base`, 움직임 없음, 트리거 `aria-haspopup`·`aria-expanded`
- [X] T056 [US2] `frontend/src/pages/TestList.tsx` 행 메뉴를 `Menu` 로 옮긴다 — 트리거는 `Button size="icon"`(`aria-label` `{행 이름} 추가 동작` 유지), 항목에 `data-row-menu-item` 유지, 내용에 `data-row-menu={row.id}` 유지. 수제 포털·`MENU_Z`·위치 계산·스크롤 1px 닫힘·창 크기 닫힘 코드를 지운다. `RowMenuVisible`·`TestListActions`·`EditEntryPoints` 의 열기를 `userEvent` 로 바꾸고 test-ledger 에 적는다. `ImplementationCount` `RETIRED` 에 수제 행 메뉴 추가 (T055 의존)
- [X] T057 [P] [US2] 동작 테스트 `frontend/tests/MenuKeyboard.test.tsx` — 트리거에 초점을 두고 Enter·Space·ArrowDown 으로 열림 · 화살표로 항목 이동 · Esc 로 닫히고 트리거로 초점 복귀 (FR-012 · T056 의존)

### 4-E. 탭과 분절 선택

- [X] T058 [US2] `frontend/src/ui/Tabs.tsx` 를 shadcn `tabs` 이식으로 — 정본 `.tabs` 모습(`bg-sunken` 줄 · 고른 탭 `bg-panel` · 11px 모노 대문자). `frontend/src/components/workbench/TargetPane.tsx` 산출물 탭(클래스 복사본)을 옮긴다 — `data-artifact-tab`·`data-action="artifact.select"` 유지. `TargetPane.test.tsx` 통과, 판정 방법이 바뀌면 test-ledger
- [X] T059 [US2] `frontend/src/ui/ToggleGroup.tsx` 를 shadcn `toggle-group`·`toggle` 이식으로 — `type="single"`, `appearance`: `segmented`(정본 `.segmented`) · `filter`(목록 거르기 · 고른 것 채움) · `chip`(그룹 칩) · `card`(정본 `.pick`)
- [X] T060 [US2] `frontend/src/components/PacingControl.tsx` 를 `ToggleGroup appearance="segmented"` 로 — `data-testid="pacing-*"` 유지. `PacingControl.test.tsx`·`RunnerPacing.test.tsx` 의 `aria-pressed` 를 `role="radio"`·`aria-checked` 로 바꾸고 test-ledger 에 적는다 (T059 의존)
- [X] T061 [US2] (정렬 「최근 실행 순」은 하나를 고르는 묶음이 아니라 누를 때마다 순서를 바꾸는 단추라 `Button` 으로 두었다 · 그룹 칩의 고른 표시 N-06) `frontend/src/pages/TestList.tsx` 거르기·정렬 · `frontend/src/components/TestGroupBar.tsx` 그룹 칩 · `frontend/src/components/workbench/WorkArea.tsx` 만드는 방법 카드 · `frontend/src/components/workbench/InsertStepForm.tsx` 가짜 라디오 2곳을 `ToggleGroup` 으로 — `data-compose-mode`·`data-group-chip` 유지. `TestListFilters`·`TestGroups`·`ComposePhase`·`StepInsert` 통과 (T059 의존)
- [X] T062 [US2] `frontend/src/ui/Table.tsx` 에서 `Tabs`·`Segmented` 를 지운다 — 참조 0 확인 (T058·T060·T061 의존)

### 4-F. 툴팁과 펼침

- [X] T063 [US2] (공급자는 앱 뿌리가 아니라 **툴팁마다** — shadcn 원본의 형태이며 화면을 낱개로 렌더하는 검사가 공급자 밖 예외로 멈추지 않는다 · z 는 알림 위 70 으로 L1 표를 고쳤다) `frontend/src/ui/Tooltip.tsx` 를 shadcn `tooltip` 이식으로 — `TooltipProvider`(`frontend/src/App.tsx` 뿌리에 한 번) · `Tooltip` · `Truncate`(넘칠 때만 hover·**초점**에 전체 문구). z 50, 움직임 없음, 화살표 없음 가능. **비활성 조작에는 쓰지 않는다** — 사유의 `title` 유지 (research R2)
- [X] T064 [US2] (Step 상세 판은 열릴 때 초점을 닫기가 아니라 **판 자체**에 둔다 — 닫기에 두면 그 툴팁이 판을 열 때마다 뜬다) 아이콘 단추에 툴팁 — `frontend/src/pages/TestList.tsx` 행 메뉴 `⋮` · `frontend/src/components/Toast.tsx` `×` · `frontend/src/components/workbench/StepDetail.tsx` 닫기 (T063 의존)
- [X] T065 [US2] `frontend/src/ui/Disclosure.tsx`(네이티브 `<details>` · 정본 요약 줄 형태)를 만들고 `frontend/src/components/workbench/StepDetail.tsx` ▸/▾ 수제 토글 3곳과 `<details>` 10곳(`frontend/src/components/TestBulkConfirm.tsx`·`frontend/src/pages/ImportPreview.tsx`·`frontend/src/pages/TestList.tsx`)을 옮긴다 — `data-header-row-picker`·`data-column-mapping` 등 속성 유지. `ImportPreview`·`TestBulkConfirm` 관련 테스트 통과

### 4-G. 부품 층 마감

- [X] T066 [US2] `frontend/src/ui/Notice.tsx` · `Surface.tsx` · `StepRow.tsx` 의 `[…].filter(Boolean).join(" ")` 을 `cn`·`cva` 로 옮기고 출처 줄을 갱신한다. `ClassConflict` 자체 점검 하한 통과 (T012 의존)
- [X] T067 [US2] (완료 — 4-B 에서 앞당겨 옮긴 뒤 4-E 로 남은 5 를 옮겨 `REMAINING_BUDGET` 0 · 등록된 원시 요소 예외는 미러 한글 조합 칸 1. 이전 메모: `SessionScreen` 입력 1·버튼 3 · `EditView` 버튼 1 · `ChatPanel` 여러 줄 1 은 4-B 에서 앞당겨 옮겼다. 남은 원시 요소 5 는 T058·T060·T061 의 고르기 단추) 남은 원시 요소를 정리한다 — `frontend/src/pages/SessionScreen.tsx` 입력 1 · `frontend/src/pages/EditView.tsx` 버튼 2 · 그 밖 G-G 가 지목하는 자리. **`REMAINING_BUDGET` = 등록된 `raw-element` 예외 수** 에 도달한다 (SC-005)
- [X] T068 [US2] (grep 결과: **코드 참조 0** — 남은 줄은 전부 주석 속 이력(`Button` 의 `navLinkClasses()` 언급 · `Surface`·`OverlayPane` 머리주석) · `filter(Boolean).join` 은 `ui/cn.ts` 의 구현 한 줄뿐 · `OverlayPane\b` 는 계약이 정한 **파일 이름** `ui/OverlayPane`(DetailPanel) 의 가져오기 경로 — 옛 `ui/Surface` 의 `OverlayPane` 함수는 없다) [contracts/ui-parts.md](contracts/ui-parts.md) §1 `상태` 칸을 전부 ✅ 로 갱신하고, 이식 중 대응표 §2 에 더한 줄을 확인한다. `grep -rn "ui/Modal\|OverlayPane\b\|navLinkClasses\|filter(Boolean).join" frontend/src` 결과 0
- [X] T069 [US2] (단계마다 L2·순회를 돌려 커밋했다 — 의도된 차이 106건 등록(4-B) · B-07·B-08·B-09 등록부에서 지움 · 4-F 뒤 L2 불일치 0 · 순회 등록되지 않은 검출 0 · 알려진 깨짐 46) 순회 · L2 를 돌려 `frontend/tests/sweep-report.json` · `frontend/tests/l2-report.json` 을 갱신한다 — 부품 전환에서 생긴 구조 차이(`NativeSelect` 감싸개 · 표 부품 · 포털)를 사유와 함께 `scripts/design_compare_ba.py` `INTENDED` 에 등록하고, 순회에서 부품 층으로 해결된 B-07·B-08·B-09 를 알려진 깨짐 등록부에서 지운다(사라졌을 때만)

**Checkpoint**: 부품이 한 체계에서 온다. 옛 부품·수제 대화상자·수제 메뉴가 없다. 동작 테스트 4종 통과.

---

## Phase 5: User Story 3 — 깨진 배치가 사라진다 (Priority: P3)

**Goal**: 지원 폭 어디서든 끊긴 조작 이름·넘친 안내·쪼그라든 입력칸·어긋난 표가 없고, 편집 국면에서 Step 목록이
8행 이상 보인다 (B-03~B-06 · B-10 · B-11 · US2 에서 남은 B-07~B-09).

**Independent Test**: 순회의 알려진 깨짐 등록부가 비고 등록되지 않은 검출이 0 이다. `edit@1440` 에서 Step 목록 8행 이상.

- [ ] T070 [US3] 화면 정책 — `frontend/src/components/design/Chrome.tsx` `Artboard` 가 `policy: "data" | "form"` 과 머리띠 자리를 받는다. **머리띠는 가로 스크롤 영역 밖**, `data` 본문은 `min-width 1440 · width 100%`, `form` 은 읽기 폭 가운데 (layout-contract-v3 L3). `WorkbenchShell.test.tsx`·`WorkbenchHeight.test.tsx`·`DesignTokens.test.tsx` 의 틀 구조 판정을 갱신하고 test-ledger 에 적는다 (B-11)
- [ ] T071 [US3] 화면마다 정책을 배정한다 — `frontend/src/pages/TestList.tsx`·`ImportPreview.tsx`·`frontend/src/components/workbench/Workbench.tsx` → `data`, `frontend/src/pages/ProjectSetup.tsx`(960)·`SecretValues.tsx`·`KeyManagement.tsx`(720) → `form`. 목록 격자(`TestList.tsx` `GRID`)의 늘어나는 칸이 이름 칸인지 확인한다. `ImplementationCount` 의 `Artboard` 사용 규칙이 여전히 의미를 갖는지 확인 (B-10 · T070 의존)
- [ ] T072 [US3] Step 패널 세로 배분 — `frontend/src/lib/layout.ts` 에 국면별 바닥 상한 표(`Record<Phase, …>`)를 두고 편집·만들기에 `calc(100% - 36px - 8 * var(--h-step))` 를 배정한다. `frontend/src/components/workbench/StepList.tsx:470` 의 `max-h-[52%]` 리터럴을 표에서 내려받게 바꾼다 (layout-contract-v3 L4 · B-03). `VerticalSplit`·`StepRowLayout`·`SavePlacement`·`RerecordBandPlacement` 통과, 판정 방법이 바뀌면 test-ledger
- [ ] T073 [US3] 만들기 국면 대상 앱 자리 — `frontend/src/lib/layout.ts` `VERTICAL_SPLIT.composing.targetSlot` 을 `content` 로. `frontend/src/components/workbench/TargetPane.tsx`·`frontend/src/pages/ComposeView.tsx` 의 낡은 높이 주석(118)을 고친다. `VerticalSplit.test.ts`·`TargetPane.test.tsx`·`ComposePhase.test.tsx` 기대값을 바꾸고 test-ledger 에 판단이 바뀐 근거(B-04 · 순회)를 적는다
- [ ] T074 [US3] 비활성 사유가 먼저 줄어든다 — `frontend/src/components/workbench/ActionButton.tsx` 사유 문구 `min-w-0` + `Truncate`, `frontend/src/components/workbench/StepList.tsx` Step 패널 머리의 「TEST STEPS」·개수 `shrink-0 whitespace-nowrap`, `frontend/src/components/workbench/ActionPalette.tsx` 자연어 입력 최소 폭 240px (layout-contract-v3 L6 · B-05 · B-06). `PhaseBarWidth`·`AuthoringParity`·`DeleteSelection` 통과
- [ ] T075 [US3] 순회를 돌려 남은 검출을 처리한다 — 알려진 깨짐 등록부의 남은 항목을 고치고, 전환 중 새로 찾은 깨짐은 `N-xx` 로 [baseline.md](baseline.md) 뒤 「전환 중 발견」 표에 적은 뒤 고치거나 사유와 함께 허용 등록한다. **알려진 깨짐 등록부 0 · 등록되지 않은 검출 0** (SC-001~SC-003)
- [ ] T076 [US3] L2 `--compare` 를 돌려 배치 수정(B-03·B-04·B-10·B-11)의 차이를 사유와 함께 `scripts/design_compare_ba.py` `INTENDED` 에 등록하고 `frontend/tests/l2-report.json` 을 갱신한다. 등록되지 않은 차이 0 (SC-007)

**Checkpoint**: 순회가 깨끗하다. 넓은 창·좁은 창 정책이 화면마다 하나다.

---

## Phase 6: User Story 4 — 깨짐이 다시 들어오지 않는다 (Priority: P4)

**Goal**: 가드와 순회가 새 체계에서 실제로 실패를 잡고, 그 증거가 남는다.

**Independent Test**: quickstart §1-2 의 금지 형태를 하나씩 넣었을 때 해당 가드가 실패하고, 순회 보고서가 낡으면
`ScreenSweep` 이 실패한다.

- [ ] T077 [US4] G-F 요구를 확정한다 — `frontend/tests/UiSkin.test.ts` 가 모든 `src/ui/*.tsx` 의 출처 줄 · 조작 부품의 `disabled:border-dashed` · `radix-ui` 가져오기 허용 파일 목록([ui-parts.md](contracts/ui-parts.md) §1 `behavior = radix`)을 **파일 존재와 무관하게** 요구한다
- [ ] T078 [US4] `scripts/screen_sweep.py` SW-5 화면 목록을 마감한다 — `test-list-row-menu`(Radix 트리거) · `edit-delete-confirm` · `runner-disconnected`(이벤트 소켓 끊기) 가 닿았다는 증거와 함께 순회된다. 알려진 깨짐 등록부 기능은 남기되 비어 있어야 한다는 단언을 `frontend/tests/ScreenSweep.test.ts` 에 더한다
- [ ] T079 [US4] quickstart §1-2 를 실행한다 — 금지 형태 8가지를 하나씩 넣어 실패하는 가드를 확인하고 되돌린다. 결과(가드 이름 · 실패 메시지 첫 줄)를 [quickstart.md](quickstart.md) §1-2 표 옆에 기록한다 (SC-010)
- [ ] T080 [US4] 번들을 잰다 — `cd frontend && npx vite build`. CSS gzip ≤ 6.78 kB · JS gzip ≤ 181.3 kB. 결과를 [baseline.md](baseline.md) 「빌드 산출물」 아래 「전환 후」 줄로 적는다. 넘으면 plan RK-5 절차 (SC-011). **Foundational 에서 드러난 것**: Tailwind 자동 소스 탐지가 `frontend/tests/` 까지 훑어 가드 테스트의 금지 예시(`disabled:opacity-50` 등)가 배포 CSS 에 실렸다(26.90 → 28.59 kB). `frontend/src/theme/tailwind.css` 에 `@source not` 으로 `tests`·`scripts` 를 뺀다 — US1 첫 커밋(T021)에서 함께 한다
- [ ] T081 [US4] [contracts/test-ledger.md](contracts/test-ledger.md) 를 마감한다 — 예상 줄마다 `상태`(고침·불필요) 채우기, `node frontend/scripts/count-assertions.mjs` 로 단언 총수 ≥ 2148 · 무른 단언 증가분의 사유, 파일 단위 전후 수 (SC-008)

**Checkpoint**: 가드가 실제로 잡는다는 기록이 남았다.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T082 [P] `docs/PENDING-HUMAN-VERIFICATION.md` 에 §17 「017 — shadcn 전환이 모습을 지키고 동작을 표준화했는가」를 더한다 — quickstart H-1~H-8 절차 · 기록 칸 · 닫히는 조건
- [ ] T083 [P] `README.md` 「현재 상태」에 017 절을 더한다 — 무엇이 바뀌었나(부품 층 · 알림 자리 · 화면 정책) · 들이지 않은 것 · 검증 방법(순회 · L2 · 가드) 한 단락씩
- [ ] T084 [P] 015 계약 문서에 개정 표시를 단다 — `specs/015-tailwind-css-migration/contracts/layout-contract-v2.md` 머리에 「v3 가 L1~L6 을 더했다」 링크, `specs/015-tailwind-css-migration/spec.md` FR-007 에 「017 이 대체」 표시
- [ ] T085 quickstart §1~§5 전체를 실행한다 — 타입 검사 · 테스트 · 단언 수 · 가드 · 순회 · L2 · 번들 · `git diff --stat 75520ee -- backend/` 0 (원칙 II 증거). 결과를 [quickstart.md](quickstart.md) 끝 「실행 기록」 절에 날짜와 함께 적는다
- [ ] T086 소스 차이를 훑어 정리한다 — 스파이크 잔재(`__spike_*`) · 쓰이지 않는 가져오기 · 옛 주석(「초점을 가둔다」 등 사실과 달라진 주석) · 이식 중 남긴 원본 클래스. `node frontend/scripts/count-violations.mjs` 가 전환 전(색 0 · 팔레트 밖 0종)보다 나빠지지 않았음을 확인

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존 없음. T006 은 T003 뒤
- **Foundational (Phase 2)**: Setup 완료 뒤. **모든 사용자 스토리를 막는다.** T016 → T017 → T018 순
- **US1 (Phase 3)**: Foundational 뒤. 다른 스토리에 의존하지 않는다
- **US2 (Phase 4)**: Foundational 뒤. US1 과 독립이지만 **T048 의 알림 층 보호는 T022 의 층 표식을 쓴다** — US1 이 먼저면 그대로, 아니면 `[data-workbench-notice-layer]` 를 함께 지목한다
- **US3 (Phase 5)**: Foundational 뒤. **T070~T074 는 US2 와 독립**이지만 T074 의 `Truncate` 는 T063 을 쓴다. T075 의 「등록부 0」은 B-07~B-09 를 해결하는 US2 4-A·4-B 뒤에만 성립한다
- **US4 (Phase 6)**: US1~US3 뒤
- **Polish (Phase 7)**: 전부 뒤

### 특별한 순서 제약

- **가드 넓히기(T011·T012)는 부품 이식(T025~)보다 먼저다.** 넓히기 전에 `cva` 로 옮기면 G-E 자체 점검이 실패하고,
  그 실패를 피하려고 가드를 끄는 유혹이 생긴다.
- **T025(Button) 가 4-B 전부보다 먼저다.** 모든 화면이 버튼을 쓴다.
- **대화상자(4-C)는 폼 부품(4-A·4-B) 뒤, 한 화면씩.** 모달의 `aria-hidden` 이 테스트에 주는 영향을 폼 부품 변경과
  섞지 않는다 (plan RK-1).
- **`TestList.tsx` 를 건드리는 작업(T023·T026·T047·T056·T061·T064·T065·T071)은 병렬로 하지 않는다** — 같은 파일이다.
- **`StepDetail.tsx`(T026·T043·T052·T064·T065)·`StepList.tsx`(T042·T072·T074)·`layout.ts`(T072·T073) 도 같다.**

### Parallel Opportunities

- Phase 1: T002~T005·T007 병렬 (T001 은 `tailwind.css` 를 만지므로 단독)
- Phase 2: T010·T013·T014·T015 병렬
- Phase 4-A: T027~T033·T035 병렬 (각자 새 파일)
- Phase 4-B: T036~T046 병렬 (파일이 겹치지 않는 묶음으로 나눴다). T047 은 `TestList.tsx` 단독
- Phase 7: T082~T084 병렬

---

## Parallel Example: Phase 4-A · 4-B

```bash
# T025(Button) 완료 뒤 — 새 부품 파일은 서로 겹치지 않는다
Task: "T027 ui/Chip.tsx badge 이식"
Task: "T029 ui/Input.tsx input 이식"
Task: "T031 ui/NativeSelect.tsx native-select 이식"
Task: "T032 ui/Checkbox.tsx 네이티브 체크박스"

# 4-A 완료 뒤 — 화면 묶음은 파일이 겹치지 않는다 (커밋마다 G-G 예산을 내리므로 병합 순서만 주의)
Task: "T036 AssertionForm"
Task: "T039 StepEditFields"
Task: "T044 DraftList · LocatorPriorityTable"
Task: "T046 KeyManagement · SecretValues · ProjectSetup"
```

**병렬 작업의 합류 주의**: `RawElements.test.ts` 의 `REMAINING_BUDGET` 은 한 줄이다. 병렬로 진행한 커밋을 합칠 때
예산을 **합산해서** 내린다.

---

## Implementation Strategy

### MVP (User Story 1 까지)

1. Phase 1 Setup — 스파이크 다섯
2. Phase 2 Foundational — 가드와 순회 (**깨짐 11건이 `pending` 으로 잰 상태**)
3. Phase 3 US1 — 알림 층 하나 · 띠 조건 자리 · 세션 토스트 삭제
4. **멈추고 확인**: 순회에서 B-01·B-02 가 사라졌는가. 결과 화면에서 「Step 05부터 실행」, 녹화 화면에서 「저장」을
   알림이 떠 있는 채로 누를 수 있는가

### Incremental Delivery

1. Setup + Foundational → 감시 장치 준비
2. US1 → 작업 차단 해소 (MVP)
3. US2 → 부품 한 체계 · 대화상자·메뉴 동작 표준화
4. US3 → 배치 깨짐 0 · 화면 정책 통일
5. US4 → 가드가 잡는다는 증거
6. 각 단계는 앞 단계를 깨지 않는다 — 테스트 전량 통과 · 순회 · L2 가 매 커밋의 조건이다

---

## Notes

- [P] = 다른 파일 · 미완료 작업에 의존하지 않음
- 테스트를 지우거나 건너뛰거나 무르게 만들지 않는다. 판정 방법을 바꿀 때는 test-ledger 에 먼저 `verifies` 를 적는다
- 「고쳤다」는 순회 보고서에서 그 검출이 사라진 것이다 — 코드 커밋만으로는 아니다 (data-model §9)
- 가드를 넓혀 새로 실패하는 것은 가드를 좁혀 통과시키지 않고 코드를 고친다
- 확정 디자인(`docs/design/008-visual-language/*.dc.html`)과 정본 구획을 고치지 않는다
