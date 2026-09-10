---
description: "Task list for 015 Tailwind CSS 전환"
---

# Tasks: Tailwind CSS 전환

**Input**: Design documents from `/specs/015-tailwind-css-migration/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) ·
[data-model.md](data-model.md) · [contracts/](contracts/)

**Tests**: 이 기능은 **기존 테스트를 지키는 것**이 요건이다 (FR-012·FR-013, 헌법 Quality
Gate 4). 새 테스트는 회귀 가드 4종과 기존 13개 파일의 판정 방법 전환이며, 둘 다 요건에서
직접 나온 것이므로 선택 사항이 아니다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일 · 미완료 작업에 의존하지 않음)
- **[Story]**: US1 / US2 / US3
- 모든 작업에 파일 경로가 있다

## Path Conventions

Web app 구조. `frontend/src/` · `frontend/tests/` · 저장소 루트 `scripts/`.
**백엔드는 건드리지 않는다** (plan.md Constitution Check — 원칙 II 증거).

## 규모 (전환 전 실측, 2026-09-10)

| 축 | 값 | 출처 |
|---|---|---|
| 의미 클래스 | **109개** (규칙 블록 139개) | `tokens.css` 주석 제외 셀렉터 추출 |
| 배치 인라인 | **455곳 / `.tsx` 39개** | `grep -c 'style={{'` |
| 영향받는 테스트 | **13개 파일 · 45+ 단언** | `.style.` 직접 읽기 |
| 현재 시각 언어 위반 | **0건** | `count-violations.mjs` |

---

## Phase 1: Setup — 기준선과 스파이크

**Purpose**: 전환을 시작하기 전에 (1) 되돌아볼 기준선을 남기고 (2) research 의 미해결
3건을 해소한다.

**⚠️ T002 가 실패하면 research R2 를 다시 정해야 한다.** 그 전에는 T005 이후로 갈 수 없다.

- [X] T001 [P] 전환 전 기준선 수치를 `specs/015-tailwind-css-migration/baseline.md` 에 기록한다 — 단언 총수(`grep -rc 'expect(' frontend/tests`), 인라인 455곳의 파일별 분포, `npm run build` 후 CSS 크기, `count-violations.mjs` 출력, 테스트 통과 수. **이 수치가 없으면 "줄지 않았다"를 나중에 증명할 수 없다**
- [X] T002 스파이크 S1 — `frontend/src/theme/tailwind.css` 초안으로 `@theme inline { --color-pass: var(--pass) }` 가 동작하는지 확인한다. 확인 항목: 기본 유틸리티(`bg-pass`), **불투명도 수식(`bg-pass/50`)**, 임의값과의 조합. 결과를 [research.md](research.md) 미해결 표에 기록한다. 실패 시 R2 대안(정본 파이프라인 확장)으로 전환하고 그 사실을 적는다
- [X] T003 [P] 스파이크 S2 — 빌드 산출 CSS 에서 클래스 실재를 확인하는 방법을 정한다 (Vite 빌드 결과 파싱 vs 테스트 내 Tailwind 실행). 판단 기준은 **테스트 실행 시간**과 **오타를 실제로 잡는가**. 결과를 research.md 에 기록
- [X] T004 [P] 스파이크 S3 — L2 대조(전환 전↔후)의 구현 방법을 정한다. `scripts/design_render.py` 의 chromium 사용 방식을 재사용하며, 전환 전 상태를 `git worktree` 로 꺼낼지 정적 기준선 JSON 으로 뜰지 결정한다. 빌드 시간이 실용성을 좌우하므로 실측한다. 결과를 research.md 에 기록
- [X] T005 Tailwind v4 를 설치하고 `frontend/vite.config.ts` 에 `@tailwindcss/vite` 플러그인을 추가한다 — `npm i -D tailwindcss@4 @tailwindcss/vite`. 버전을 고정해 `package-lock.json` 에 남긴다 (T002 의존)
- [X] T006 `frontend/src/theme/tailwind.css` 를 만든다 — `@import "tailwindcss"` · `@import "./tokens.css"` · `@theme inline` 으로 정본 토큰 전량에 Tailwind 이름을 붙인다. 이름 규약은 [contracts/tailwind-theme.md](contracts/tailwind-theme.md) C-3. **오른쪽은 전부 `var(정본토큰)` 이며 리터럴 값이 하나도 없어야 한다** (C-1)
- [X] T007 진입점에서 `theme/tailwind.css` 를 불러오도록 바꾼다 (`frontend/src/main.tsx` 또는 현재 `tokens.css` 를 불러오는 곳). **이 시점에 화면이 하나도 바뀌지 않아야 한다** — 아직 유틸리티를 쓰는 곳이 없다. `npm test -- --run` 전량 통과 확인

**Checkpoint**: Tailwind 가 설치됐고 정본을 참조하며, 기존 화면은 그대로다.

---

## Phase 2: Foundational — 가드를 먼저 세운다

**Purpose**: 전환을 시작하기 **전에** 감시 장치를 세운다.

**⚠️ 이 순서는 뒤집을 수 없다.** 가드 없이 전환하면 무엇이 언제 깨졌는지 알 수 없고,
전환이 끝난 뒤 가드를 만들면 이미 들어온 위반을 기준선으로 삼게 된다.

- [X] T008 [P] [contracts/class-migration.md](contracts/class-migration.md) 의 표를 채운다 — 의미 클래스 109개 각각에 대해 이름·`.tsx` 사용처 수·행선지(미정)·상태(미착수). 사용처가 0인 클래스는 「삭제 — 쓰이지 않음」으로 표시한다. **이 표가 SC-009 의 판정 대상이다**
- [X] T009 [P] 가드 G-A1 을 `frontend/tests/TailwindThemeLiteral.test.ts` 에 만든다 — `theme/tailwind.css` 의 모든 `--*:` 선언 오른쪽이 `var(…)` 인지 검사한다. 리터럴이 하나라도 있으면 실패 (FR-016 · C-1)
- [X] T010 가드 G-B 를 `frontend/tests/ClassExistence.test.ts` 에 만든다 — `.tsx` 가 쓰는 Tailwind 클래스가 빌드 산출 CSS 에 실재하는지 확인한다. **오타를 일부러 넣어 실패하는 것을 확인한다.** 이 가드가 없으면 `toHaveClass` 는 거짓말을 할 수 있다 ([contracts/layout-contract-v2.md](contracts/layout-contract-v2.md) LC-4 ③) (T003 의존)
- [X] T011 [P] 가드 G-C 를 `frontend/tests/SingleSystem.test.ts` 에 만든다 — 한 요소의 `className` 에 의미 클래스와 Tailwind 유틸리티가 동시에 있으면 실패 (LC-5). 전환 중에는 이 수치가 **진행률 계기**이므로, 실패 메시지가 남은 곳을 `파일:줄` 로 지목해야 한다
- [X] T012 [P] 가드 G-D 를 `frontend/tests/ClassMigration.test.ts` 에 만든다 — `tokens.css` 에 남은 의미 클래스 수와 대응표의 「완료」 아닌 행 수가 일치하는지 검사한다 (T008 의존)
- [ ] T013 L2 대조 스크립트 `scripts/design_compare_ba.py` 를 만들고 `--baseline` 으로 **전환 전 기준선을 뜬다**. `design_render.py` 의 digest 규약을 따라 낡은 보고서로 통과할 수 없게 한다 (T004 의존). **기준선은 부품 전환을 시작하기 전에 떠야 한다**
- [ ] T014a **L1 대조의 측정 대상을 부품으로 옮긴다** — `scripts/design_render.py` 의 `FORMS`
      가 `["btn", "chip pass", …]` 처럼 **클래스 이름**으로 형태를 지정하고 있어, 의미 클래스를
      해체하면 정본 쪽에서 그 이름이 사라져 대조가 통째로 무너진다 (research R5 · FR-002).
      **확정 디자인 쪽은 손대지 않는다** — 그것이 기준이다. 관측 쪽만 `tokens.css` + 클래스에서
      **부품 렌더 결과**로 바꾼다. 질문("우리 부품이 확정 디자인과 같은 것을 그리는가")은 그대로다
- [ ] T014b `frontend/tests/CanonMatchesDesign.test.ts` 를 T014a 의 새 보고서 형식에 맞춘다.
      digest 로 낡은 보고서를 거르는 성질을 유지한다 — **이 성질이 없으면 재지 않고도 통과한다**
- [X] T014 [P] 단언 총수 계수기를 `frontend/scripts/count-assertions.mjs` 에 만든다 — 헌법 Quality Gate 4 를 수치로 확인하는 장치다. T001 의 기준선과 비교해 줄면 그 파일을 지목한다

**Checkpoint**: 가드 4종이 살아 있고, 각각 일부러 어겨서 실제로 잡는 것을 확인했다.

---

## Phase 3: User Story 1 — 토큰을 Tailwind 로 소비하는 길 (Priority: P1) 🎯 MVP

**Goal**: 정본 토큰이 Tailwind 이름으로 소비되고, 그 값이 복제되지 않았음을 실증한다.

**Independent Test**: 시범 전환한 부품 하나와 화면 하나가 전과 동일하게 보이고,
정본 토큰 값을 바꾸면 그 화면도 함께 바뀐다. 나머지 38개 파일은 그대로여도 성립한다.

- [X] T015 [US1] `frontend/src/ui/Button.tsx` 를 만들어 `.btn` 계열(`.btn`·`.primary`·`.secondary`·`.ghost`·`.danger`·`.disabled`·`.bare`)을 대체한다. 도메인을 모르는 순수 부품이어야 한다. 대응표(T008)의 해당 행을 「구현」으로 갱신
- [X] T016 [US1] `.btn` 계열 사용처를 `ui/Button` 으로 전량 교체하고 `tokens.css` 정의를 **삭제한다**. 대응표를 「완료」로 갱신. **정의를 남긴 채 부품만 만들면 두 체계가 공존한 채 굳는다** — 007 이 겪은 「전사」 실패의 형태 (data-model.md 상태 전이)
- [X] T017 [US1] 작은 화면 하나(`frontend/src/components/TabStrip.tsx`, 인라인 2곳)를 배치까지 완전 전환해 **부품+배치가 함께 동작하는 것**을 확인한다. 이 화면을 이후 전환의 본보기로 삼는다
- [X] T018 [US1] US1 수용 시나리오 3건을 검증한다 — (1) 통과 색을 Tailwind 이름 하나로 지정하고 코드에 `#1A7F45` 가 없다, (2) 시범 화면의 전후 시각 차이 0, (3) **정본 토큰 값을 임시로 바꾸면 화면도 바뀐다**(값 복제가 없다는 증거). 확인 후 되돌린다

**Checkpoint**: 길이 뚫렸다. 이후 작업은 이 길을 따라가는 반복이다.

---

## Phase 4: User Story 2 — 전면 해체 (Priority: P2)

**Goal**: 의미 클래스 109개와 배치 인라인 455곳이 사라진다.

**Independent Test**: `style={{` 검색 결과가 등록된 예외뿐이고, `tokens.css` 에 부품
클래스가 남지 않으며, 기존 테스트가 전량 통과한다.

### 4-A. 부품 해체 — 의미 클래스 109개 → `frontend/src/ui/`

**순서 근거**: 화면은 부품의 조합이다. 부품을 먼저 세우면 화면 전환이 치환이 된다.
반대로 가면 같은 버튼이 화면마다 다른 조합을 얻어 SC-010 이 깨진다 (research R6).

---

#### ⚠️ 2026-09-10 T019 착수 시 드러난 것 — 「군 단위 전환」은 성립하지 않는다

계획은 클래스를 9군으로 나누고 각 군을 독립 작업으로, 그것도 **전부 병렬로** 두었다.
`.btn` 은 우연히 그렇게 되었지만 (버튼이 독립적이라) 나머지는 그렇지 않다.

**의미 클래스는 서로 조합되어 쓰인다.**

```
.chip.pass  .chip.fail  .chip.warn      상태 색조가 칩 부품의 variant 다
.srow.pass  .srow.fail  .srow.run       Step 행 부품의 variant 다
className="row tint-warn"               수식이 다른 부품 위에 얹힌다
className="btn sm quiet"                (이미 겪었다)
```

한 요소의 클래스는 **동시에** 전환되어야 한다. 하나만 유틸리티로 바꾸면 그 요소에 두
체계가 걸리고 가드 G-C 가 잡는다 — 그것이 LC-5 의 요구이고, 특이도 사고를 막는 장치다.

그리고 **같은 `.tsx` 파일을 여러 군이 건드린다.** `TestList.tsx` 하나가 칩·알림·필드·표를
모두 쓴다. 9군 병렬은 같은 파일에 동시에 손대는 것이라 성립하지 않는다.

**정정된 순서** — 「부품 만들기」와 「사용처 교체」를 분리한다:

| 단계 | 내용 | 왜 |
|---|---|---|
| **4-A-1** | 부품 컴포넌트를 **전부 만든다.** `tokens.css` 도 사용처도 손대지 않는다 | 부품 정의가 한 곳에 모이는 것이 SC-010 의 요구다. 만들기만 하는 동안 화면은 무사하다 |
| **4-A-2** | **화면을 하나씩** 전환한다. 그 파일 안의 모든 요소를 부품+유틸리티로 **동시에** 옮긴다 | 한 요소에 두 체계가 걸리지 않는 유일한 방법이다 |
| **4-A-3** | 사용 0 이 된 클래스 정의를 파생 구획에서 삭제한다 | 정본 구획은 남는다 (「완료」의 정의 참조) |

4-A-2 는 4-B(배치 전환)와 같은 단위이므로 **화면별로 합쳐진다.** T029~T051 이 그 자리다 —
각 화면에서 부품 교체와 배치 전환을 함께 한다.

아래 T019~T027 은 이제 **4-A-1(부품 만들기)** 이며 사용처 교체를 포함하지 않는다.

---

**각 부품 작업의 완료 조건** (정정): 부품 구현 + `data-*` 로 의도 노출 + 대응표 「구현」 +
테스트 전량 통과. **사용처 교체와 정의 삭제는 화면별 작업(T029~T051)에서 한다.**

- [ ] T019 [P] [US2] 상태·색조 군을 `frontend/src/ui/tone.ts` + 관련 부품으로 해체한다 — `.pass` `.fail` `.warn` `.run` `.ai` `.paused` `.pass-ink` `.fail-ink` `.warn-ink` `.run-ink` `.ai-ink` `.tint-pass` `.tint-fail` `.tint-warn` `.tint-run` `.tint-ai` `.in-use` `.off` `.on`. 기존 `theme/tone.ts` 와 합류시킨다. **새 색을 만들지 않는다** (FR-003 · 008 규율)
- [X] T020 [P] [US2] 칩·배지 군을 `frontend/src/ui/Chip.tsx`·`Badge.tsx` 로 해체한다 — `.chip` `.pill` `.dot` `.band` `.num` `.sel` `.last-resort`. `Badges.test.tsx`·`OutcomeVocabulary.test.tsx` 가 검증 대상
- [ ] T021 [P] [US2] 알림·토스트 군을 `frontend/src/ui/Notice.tsx`·`Toast.tsx` 로 해체한다 — `.notice` `.notice-body` `.toast` `.toast-body` `.toast-layer` `.why` `.hint-line`. **`tokens.css` 주석이 기록한 두 사고(특이도로 모든 토스트가 흰색이 된 일, 기준 크기가 `height` 를 이겨 두 줄이 잘린 일)가 재발하지 않는지 확인한다.** `NoticesAreToasts.test.tsx`·`ToastPlacement.test.tsx` 가 검증 대상
- [ ] T022 [P] [US2] 모달·층 군을 `frontend/src/ui/Modal.tsx`·`Overlay.tsx` 로 해체한다 — `.modal` `.modal-scrim` `.scrim` `.overlay-pane` `.float`. 승강(z-index) 관계가 보존되어야 한다
- [ ] T023 [P] [US2] 판·머리 군을 `frontend/src/ui/Pane.tsx`·`Header.tsx` 로 해체한다 — `.pane` `.pane-hd` `.hdr` `.body` `.title` `.subtitle` `.brand` `.brand-name` `.divider` `.spacer` `.rule-top` `.rule-bottom`
- [ ] T024 [P] [US2] 폼·필드 군을 `frontend/src/ui/Field.tsx`·`FileInput.tsx` 로 해체한다 — `.field` `.field-label` `.lbl` `.file` `.file-input` `.ime-capture` `.answer-q` `.commit-bar`. **`.ime-capture` 의 한글 입력 처리가 보존되어야 한다** (FR-010)
- [ ] T025 [P] [US2] 표·격자 군을 `frontend/src/ui/Table.tsx`·`Grid.tsx` 로 해체한다 — `.table` `.thead` `.tfoot` `.trow` `.row` `.grid-head` `.key-cell` `.tabs`. `LocatorPriorityTable.test.tsx` 가 검증 대상
- [ ] T026 [P] [US2] Step 행 군을 `frontend/src/ui/` 또는 기존 `components/workbench/` 로 해체한다 — `.steps` `.steps-hd` `.steps-ft` `.srow` `.srow-check` `.srow-name` `.srow-ops` `.phase` `.phase-name` `.phase-progress`. **행 높이 52px 고정이 유지되어야 한다** (009 FR-304). `StepRowLayout`·`DesignStepRow`·`StepRowStates`·`StepListPerformance` 가 검증 대상
- [ ] T027 [P] [US2] 타이포·수식 군을 유틸리티로 해체한다 — `.mono` `.muted` `.dim` `.quiet` `.meta` `.note` `.log` `.code-block` `.addr` `.loc` `.line` `.name` `.left` `.sunken` `.strong-sm` `.sm` `.d` `.m` `.n` `.t` `.danger-edge` `.op` `.pick` `.segmented` `.textlink` `.navlink`. 부품이 아니라 수식이므로 컴포넌트를 만들지 않고 유틸리티 조합으로 옮긴다.
      **`.disabled`·`.bare` 는 T015(Button), `.float` 은 T022(모달·층) 관할이므로 여기서 다루지 않는다** — 병렬 실행 시 같은 정의를 두 곳에서 지우는 것을 막는다
- [ ] T028 [US2] 4-A 완료를 확인한다 — `tokens.css` 에 의미 클래스 0개, 대응표 「완료」 109/109, 가드 G-C 0건, 테스트 전량 통과, L2 대조 불일치 0.
      **아울러 두 가지를 판정한다** (analyze 가 찾은 공백): (1) **SC-010** — 같은 종류의 부품이 화면마다 다른 모습을 갖지 않는가. `ui/` 밖에서 버튼·칩·알림 모양을 조립하는 곳이 있으면 위반이다. (2) **SC-006** — 어떤 요소의 스타일을 고칠 때 찾아야 할 곳이 부품 파일 하나와 정본 하나뿐인가. 세 번째 장소가 생겼으면 그것이 무엇인지 적는다

### 4-B. 배치 전환 — 인라인 455곳 → 유틸리티

**⚠️ 각 작업에 해당 테스트의 판정 방법 전환이 포함된다.** 화면을 바꾸면 그 화면을 보던
테스트가 함께 깨지므로 같은 커밋에서 처리한다. 판정 *방법*만 바꾸고 **무엇을 검증하던
테스트인지는 바꾸지 않는다** (LC-6 · 헌법 Quality Gate 4).

**그리고 바꾼 테스트마다 무엇을 왜 바꿨는지 그 파일 머리주석에 적는다** (FR-014).
이 저장소의 기존 관행이며, 적지 않으면 다음 사람이 그 테스트가 원래 무엇을 보던 것인지
알 수 없다 — 그때 테스트는 지워지기 쉬워진다. 각 4-B 작업의 완료 조건에 포함된다.

- [ ] T029 [US2] `frontend/src/lib/layout.ts` 의 배치 표 출력을 클래스 문자열로 바꾼다 — `Record<Phase, …>` 표 자체와 「부모가 내려준다」 구조는 **그대로 둔다**. 새로 더하는 것은 `Record<VerticalSplit, string>` 전수 대응뿐이다 (research R3 · LC-2). 이것이 4-B 전체의 기반이므로 먼저 한다
- [ ] T030 [US2] `frontend/src/components/workbench/Workbench.tsx` (4곳) 전환 + `WorkbenchShell.test.tsx`(단언 12개)·`WorkbenchHeight.test.tsx` 판정 방법 전환. **국면별 세로 배분이 전과 같은지가 S-12 재발 여부다**
- [ ] T031 [P] [US2] `frontend/src/pages/TestList.tsx` (55곳) 전환 + `TestListFilters`·`TestListActions`·`TestListSelection`·`RowMenuVisible` 판정 방법 전환. **최대 화면이므로 커밋을 쪼갠다** (RK-5)
- [ ] T032 [P] [US2] `frontend/src/pages/ProjectSetup.tsx` (55곳) 전환 + `ProjectSetup.test.tsx`·`ProjectRowActions.test.tsx`. 커밋을 쪼갠다
- [ ] T033 [P] [US2] `frontend/src/pages/ImportPreview.tsx` (41곳) 전환 + `ImportPreview.test.tsx`·`ImportExportAccess.test.tsx`
- [ ] T034 [P] [US2] `frontend/src/components/workbench/WorkArea.tsx` (30곳) 전환 + `PromptDoesNotShrinkMirror.test.tsx`·`ResultAttemptsVisible.test.tsx`
- [ ] T035 [P] [US2] `frontend/src/pages/KeyManagement.tsx` (28곳) 전환 + `KeyManagement.test.tsx`
- [ ] T036 [P] [US2] `frontend/src/components/workbench/StepDetail.tsx` (24곳) 전환 + `DetailPlacement.test.tsx`(단언 6개)·`DetailBlocksMirrorInput.test.tsx`(단언 6개). **상세 층이 목록을 덮지 않는 자리·폭 640px 이 계약이다**
- [ ] T037 [P] [US2] `frontend/src/pages/DraftList.tsx` (17곳) 전환 + `DraftList.test.tsx`·`DraftsFirstOnEmpty.test.tsx`
- [ ] T038 [P] [US2] `frontend/src/pages/EditView.tsx` (15곳) · `frontend/src/components/TestBulkConfirm.tsx` (15곳) 전환 + `EditEntryPoints`·`DeleteSelection`·`TestBulkConfirm` 관련 테스트
- [ ] T039 [P] [US2] `frontend/src/pages/SecretValues.tsx` (13곳) · `frontend/src/components/InlineSecretInput.tsx` (7곳) 전환 + `InlineSecret.test.tsx`·`SensitiveAcrossPhases.test.tsx`. **마스킹 표현이 보존되어야 한다** (헌법 보안 요건)
- [ ] T040 [P] [US2] `frontend/src/components/workbench/PhaseBar.tsx` (13곳) 전환 + `PhaseBarWidth.test.tsx`(단언 11개)·`PhaseContext.test.tsx`. 줄임표·`min-width:0` 처리가 계약이다
- [ ] T041 [P] [US2] `frontend/src/components/workbench/ActionPalette.tsx` (13곳) · `ActionButton.tsx` (5곳) 전환 + `CapabilityUI.test.tsx`
- [ ] T042 [P] [US2] `frontend/src/components/workbench/InsertStepForm.tsx` (12곳) 전환 + `StepInsert.test.tsx`·`InsertViaBrowser.test.tsx`
- [ ] T043 [P] [US2] `frontend/src/components/workbench/TargetPane.tsx` (11곳) 전환 + `TargetPane.test.tsx`. **이 파일 주석이 「1회차에 `pane.style.flex` 를 넣었고 그것이 크기까지 고정했다」는 실패를 기록하고 있다 — 읽고 같은 함정을 피한다**
- [ ] T044 [P] [US2] `frontend/src/components/MirrorView.tsx` (11곳) 전환 + `MirrorView.test.tsx`·`MirrorInput.test.ts`. **미러 스케일이 런타임 계산값이면 예외 등록 대상이다** (LC-3)
- [ ] T045 [P] [US2] `frontend/src/components/workbench/StepList.tsx` (10곳) · `StepRowOps.tsx` (1곳) 전환 + `StepRowLayout`·`StepRowActions`·`StepNumberConsistency`
- [ ] T046 [P] [US2] `frontend/src/components/LocatorPriorityTable.tsx` (9곳) · `AssertionForm.tsx` (9곳) 전환 + `LocatorPriorityTable.test.tsx`
- [ ] T047 [P] [US2] `frontend/src/pages/SessionScreen.tsx` (7곳) · `frontend/src/components/TestGroupBar.tsx` (7곳) · `SessionLostBanner.tsx` (6곳) 전환 + `TestGroups.test.tsx`·`ActiveSessions.test.tsx`
- [ ] T048 [P] [US2] 워크벤치 잔여 소형 전환 — `NoticeStack.tsx`(4) · `BulkDeleteConfirm.tsx`(1) + `NoticesAreToasts.test.tsx`
- [ ] T049 [P] [US2] 디자인 껍데기 전환 — `frontend/src/components/design/Chrome.tsx`(4) · `BrowserFrame.tsx`(4) + `WindowFallback.test.tsx`
- [ ] T050 [P] [US2] 잔여 소형 전환 — `StepEditFields.tsx`(4) · `ResultView.tsx`(3) · `StartingIndicator.tsx`(3) · `PacingControl.tsx`(3) · `ErrorNotice.tsx`(3) · `ComposeView.tsx`(2) · `LiveConnectionBanner.tsx`(2) · `BrowserPromptPanel.tsx`(1) · `App.tsx`(1) + 관련 테스트
- [ ] T051 [US2] 남은 인라인을 전부 `frontend/src/theme/exceptions.ts` 에 등록한다 — 각 항목에 `file`·`pattern`·`axis`·`reason`. **자격은 런타임 계산값뿐이다** (LC-3). `reason` 이 비면 등록이 아니다. 자격 없는 것은 등록하지 말고 전환한다

**Checkpoint**: 인라인 잔량 = 등록된 예외뿐. 의미 클래스 0개. 테스트 전량 통과.

---

## Phase 5: User Story 3 — 회귀 방지를 새 체계에 심는다 (Priority: P3)

**Goal**: 값 리터럴 유입과 계약 이탈을 자동으로 막는다. 이번 정리가 다음 개정에서
무너지지 않게 한다.

**Independent Test**: 화면 코드에 색 리터럴을 일부러 넣으면 테스트가 실패한다.

- [ ] T052 [P] [US3] `frontend/scripts/count-violations.mjs` 를 새 체계에 맞게 갱신한다 — G-1(색 리터럴)은 유지하고, G-2(시각 속성 인라인)의 근거였던 「허용 목록」이 폐지됐으므로 판정을 LC-3(런타임 계산값만)으로 바꾼다. **규칙의 정의처가 이 파일이라는 성질을 유지한다** — 테스트가 여기서 함수를 가져다 쓴다
- [ ] T053 [P] [US3] `frontend/tests/VisualLanguage.test.tsx` 의 판정 방법을 전환한다. 이 테스트는 「화면 코드가 `className` 으로 정본을 소비하는가」를 봤는데, 의미 클래스가 사라져 전제가 없어졌다. **같은 목적(정본 이탈 없음)을 새 체계에서 확인하도록 고친다 — 삭제하지 않는다** (US3 시나리오 4). 무엇을 왜 바꿨는지 파일 머리주석에 적는다
- [ ] T054 [P] [US3] `frontend/tests/DesignTokens.test.tsx` 를 확인·갱신한다 — 정본 자체는 바뀌지 않았으므로 통과해야 한다. 통과하지 않으면 정본을 건드린 것이다 (C-2 위반)
- [ ] T055 [P] [US3] `frontend/src/theme/exceptions.ts` 의 죽은 예외를 정리한다 — 등록됐으나 쓰이지 않는 항목을 가드가 보고하면 삭제한다 (008 C-14)
- [ ] T056 [US3] SC-011 을 실증한다 — `Phase` 에 국면을 임시로 추가하고 `npm run typecheck` 가 **실패하는지** 확인한다. 통과하면 FR-020a 가 깨진 것이다. 확인 후 되돌리고 결과를 기록 ([quickstart.md](quickstart.md) §1-7)
- [ ] T057 [US3] SC-012 를 확인한다 — 표시 컴포넌트가 자기 자리 크기를 스스로 정하는 곳이 있는지 훑는다. `frontend/src/components/workbench/TargetPane.tsx`·`WorkArea.tsx` 와 `PhaseAside` 가 007 S-12 의 당사자였으므로 특히 본다. 결과를 `specs/015-tailwind-css-migration/baseline.md` 에 기록
- [ ] T058 [P] [US3] 상호작용 상태 보존을 검증한다 (FR-009) — hover·focus·선택·비활성 네 상태의 표현이 전환 전후로 같은지 확인한다. 자동으로 볼 수 있는 부분(상태별 클래스가 붙는가)은 `frontend/tests/InteractionStates.test.tsx` 로, 실제 모습은 T066 H-7 로 본다. **analyze 가 찾은 커버리지 공백이다** — 기존 계획은 초점만 보고 hover·비활성을 어디서도 보지 않았다
- [ ] T059 [US3] 가드 4종이 실제로 실패를 잡는지 확인한다 — 각각 일부러 어기고 되돌린다 (quickstart.md §1-3·§1-4). **가드가 동작하지 않으면 없는 것과 같다**

---

## Phase 6: 계약 문서와 최종 판정

- [ ] T060 [P] `specs/008-visual-language/contracts/visual-language.md` §2 「허용되는 인라인 `style`」이 폐지되고 [contracts/layout-contract-v2.md](contracts/layout-contract-v2.md) 로 대체됐음을 원문에 표시한다. **지우지 말고 「015 가 개정함」을 적는다** — 왜 그 목록이 있었는지가 기록으로 남아야 한다
- [ ] T061 [P] `frontend/src/theme/tokens.css` 머리주석 중 「화면 코드는 `className` 으로 소비하며 값을 다시 적지 않는다」가 사실과 달라졌으므로 갱신을 요청하는 항목을 만든다. **이 파일은 `extract_canon.py` 의 출력이므로 직접 고치지 않는다** — 주석 생성 부분을 스크립트에서 고치거나, 파생 구획에 주석을 남긴다 (C-2)
- [ ] T062 [P] `specs/015-tailwind-css-migration/contracts/class-migration.md` 를 최종 상태로 확정한다 — 109행 전부 「완료」, 미상 0건 (SC-009)
- [ ] T063 L2 대조를 실행한다 — `scripts/design_compare_ba.py --compare`. 불일치가 있으면 각각 의도된 것인지 판단한다. **의도되지 않은 불일치가 하나라도 있으면 전환이 끝난 것이 아니다** (SC-001)
- [ ] T064 배포 산출물 크기를 기준선과 비교한다 — `npm run build` 후 CSS 크기가 T001 기록보다 늘지 않았는지 (SC-007). 늘었으면 원인을 찾는다. 비교 결과를 `specs/015-tailwind-css-migration/baseline.md` 에 기록
- [ ] T065 단언 총수를 기준선과 비교한다 — `node frontend/scripts/count-assertions.mjs`. **줄었으면 그 자리를 지목하고 이유를 댄다** (헌법 Quality Gate 4). 줄어든 채로 넘어가지 않는다
- [ ] T066 손 검증을 등록하고 돌린다 (**사람이 판정한다** · `docs/PENDING-HUMAN-VERIFICATION.md` §15) — [quickstart.md](quickstart.md) §4 의 H-1~H-8. **H-1(국면별 세로 배분)과 H-7(키보드 순회)이 가장 중요하다**. 미판정이면 미완료로 보고하며, 통과로 가정하지 않는다

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음. **T002 스파이크가 T005~T007 을 막는다**
- **Phase 2 (Foundational)**: Phase 1 완료 후. **모든 전환 작업을 막는다** — 가드 없이 전환하지 않는다
- **Phase 3 (US1)**: Phase 2 완료 후. MVP
- **Phase 4 (US2)**: Phase 3 완료 후. 4-A 가 4-B 를 **막지 않는다**(독립)이나, **4-A 를 먼저 하는 것이 R6 의 결정**이다 — 부품 일관성 때문
- **Phase 5 (US3)**: Phase 4 완료 후 (전환이 끝나야 새 체계의 가드를 확정할 수 있다)
- **Phase 6**: 전부 완료 후

### 특별한 순서 제약

| 제약 | 이유 |
|---|---|
| T013(L2 기준선)은 **어떤 전환보다 먼저** | 전환 후에 기준선을 뜨면 비교 대상이 없다 |
| T001(수치 기준선)은 **가장 먼저** | 같은 이유 |
| T029(배치 표)는 4-B 의 다른 모든 작업보다 먼저 | 나머지가 이 표의 출력을 쓴다 |
| T016(정의 삭제)은 T015(부품 구현) 직후 | 정의를 남기면 두 체계가 공존한 채 굳는다 |
| T002 실패 시 T005 이전으로 되돌아감 | research R2 재설계 |

### Parallel Opportunities

- **Phase 1**: T001·T003·T004 병렬 (T002 는 단독 — 결과가 나머지를 좌우)
- **Phase 2**: T008·T009·T011·T012·T014 병렬. T010·T013 은 스파이크 결과 의존
- **Phase 4-A**: T019~T027 병렬 가능 — **부품 파일만 만들 때에 한해서다.** 사용처를 함께 고치면 같은 `.tsx` 를 여러 작업이 건드린다 (위 정정)
- **Phase 4-B**: T031~T050 **20개 병렬** — 서로 다른 화면. 단 T029·T030 완료 후
- **Phase 5**: T052~T055·T058 병렬
- **Phase 6**: T060~T062 병렬

### Parallel Example: Phase 4-A

```bash
# 부품 9군을 동시에 — 서로 다른 파일이고 의존이 없다
Task: "상태·색조 군을 ui/tone.ts 로 해체 (T019)"
Task: "칩·배지 군을 ui/Chip.tsx 로 해체 (T020)"
Task: "알림·토스트 군을 ui/Notice.tsx 로 해체 (T021)"
Task: "모달·층 군을 ui/Modal.tsx 로 해체 (T022)"
...
```

---

## Implementation Strategy

### MVP (User Story 1 까지)

1. Phase 1 Setup — **T002 스파이크가 관문이다**
2. Phase 2 Foundational — 가드를 먼저 세운다
3. Phase 3 US1 — 길이 뚫린 것을 실증
4. **멈추고 판정**: 시범 화면의 전후 차이 0, 토큰 변경이 화면에 전파됨

여기서 멈춰도 의미가 있다. Tailwind 가 정본을 참조하며 동작하고, 나머지는 같은 길의 반복이다.

### Incremental Delivery

1. Setup + Foundational → 기반과 감시 장치
2. US1 → 시범 부품·화면 (MVP)
3. US2 4-A → 부품 전량. **여기서 멈춰도 화면은 정상이다**
4. US2 4-B → 배치 전량
5. US3 → 회귀 가드 확정
6. Phase 6 → 판정

각 단계 끝에서 테스트 전량이 통과하고 화면이 정상이다.

---

## Notes

- **커밋 단위**: 작업 하나 또는 논리적 묶음. 대형 화면(T031·T032)은 더 쪼갠다 (RK-5)
- **각 전환 작업의 완료 조건**: 코드 전환 + 해당 테스트 판정 방법 전환 + **변경 사유를 그 테스트
  파일 머리주석에 기록**(FR-014) + 대응표 갱신 + `npm test -- --run` 전량 통과.
  다섯 중 하나라도 빠지면 미완료
- **하지 말 것**: 테스트를 지우거나 `toBeDefined()` 로 무르게 바꿔 통과시키기 (헌법 Quality
  Gate 4). 새 색·새 치수 만들기 (FR-003). `tokens.css` 직접 수정 (C-2).
  `git add -A` 로 커밋하기
- **막히면**: 진행이 안 되는 이유를 적고 멈춘다. 요건을 낮춰 통과시키지 않는다
