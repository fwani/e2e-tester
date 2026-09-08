---
description: "Task list for 008 — v1 잔재를 걷어내고 v2「계기판」을 코드에 세운다"
---

# Tasks: v1 잔재를 걷어내고 v2「계기판」을 코드에 세운다

**Input**: `specs/008-visual-language/` 의 설계 문서

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: 이 기능은 **검사가 산출물의 일부다.** 가드(L2)와 정본 대조(L1)가 요구사항
FR-278~FR-284 이므로 검사 작성 작업이 선택이 아니다. 기존 657건은 회귀 기준선이다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (서로 다른 파일, 선행 의존 없음)
- **[Story]**: US1~US4
- 모든 작업에 정확한 파일 경로를 적었다

## 이 목록의 두 가지 규칙

1. **작업 단위는 파일이 아니라 화면이다.** 한 화면에 딸린 파일을 다 옮긴 뒤 검사를 돌린다.
   파일 단위로 자르면 화면이 반쯤 옮겨진 상태가 생기고, 그 상태의 검사 실패는 진단이 어렵다.
2. **화면을 옮기는 절차는 [quickstart.md](./quickstart.md) 6단계 하나다.** 작업마다 절차를
   복사하지 않는다. 작업에는 **그 화면에만 해당하는 것**(쓰는 형태 목록·잔존색·특이사항)만 적는다.

## 기준선 (커밋 `b033ee0` · 2026-09-08)

| 지표 | 값 |
|---|---|
| 프런트엔드 검사 | **50파일 · 657건 전부 통과** |
| 색 리터럴 (tsx) | **327** |
| 인라인 `style={{` | **437** |
| v2 팔레트 밖 색 | **17종** |
| 대조표 미판정 | **509칸** |

---

## Phase 1: Setup — 측정 기준을 고정한다

**Purpose**: 이후 모든 단계가 "줄었는가"를 판정할 수 있게 한다

- [X] T001 `frontend/scripts/count-violations.mjs` 를 만들어 색 리터럴·인라인 시각 언어 선언·팔레트 밖 색을 파일별로 세고 합계를 출력한다. `contracts/visual-language.md` §4 의 G-1·G-2 정의를 따르고 출력에 `파일:줄` 을 포함한다 (FR-279)
- [X] T002 T001 로 기준선을 측정해 `specs/008-visual-language/baseline.md` 에 파일별 표로 남긴다. 합계가 색 327 · 인라인 437 · 팔레트 밖 17종과 일치하는지 확인한다. 다르면 그 차이를 먼저 조사한다 — 기준선이 틀리면 이후 판정이 전부 틀린다

**Checkpoint**: 위반 수가 파일별로 보인다. 이후 단계가 이 수를 내린다.

---

## Phase 2: Foundational — 정본을 세운다 (US1~US4 전체를 막는 선행 작업)

**⚠️ 이 단계가 끝나기 전에는 어떤 화면도 옮길 수 없다.** 정본 없이 화면을 옮기면 다시 전사가 된다.

- [X] T003 `scripts/extract_canon.py` 를 만든다. `docs/design/008-visual-language/*.dc.html` 의 `<style>` 블록을 읽어 정본 CSS 를 뽑는다. **18장이 동일함을 먼저 단언하고**(research R1 · md5 일치), 하나라도 다르면 멈춘다. dc.html 축약 토큰명 → 현행 서술 토큰명 대응표(`--r`→`--radius`, `--sans`→`--font-sans`, `--surface`→`--panel` 등)를 가지며, **값은 절대 변형하지 않는다** (`contracts/visual-language.md` C-2)
- [X] T004 T003 을 돌려 `frontend/src/theme/tokens.css` 를 정본으로 교체한다. 재사용 형태 27종(`.btn`+4변형 · `.chip`+5 · `.srow`+4 · `.pane` · `.lbl` · `.mono` · `.why` · `.hdr` · `.phase` · `.notice` · `.body` · `.left` · `.steps` · `.steps-hd`)이 전부 들어간다. 기존 파일 머리 주석의 「왜 v1 을 버렸나」는 보존하고 「추출 방법」 절을 추가한다
- [X] T005 [P] `frontend/src/theme/exceptions.ts` 를 만든다. `data-model.md` §2 의 필드(`file`·`pattern`·`axis`·`reason`)를 갖는 타입과 배열. 초기 항목은 배치 계약 하나뿐이며 `reason` 에 research R3 의 근거를 적는다. `reason` 이 빈 문자열이면 타입 수준에서 막는다
- [X] T006 [P] `scripts/design_render.py` 를 만든다. `backend/.venv` 의 playwright 로 chromium 을 띄워 (a) `Language.dc.html` (b) `tokens.css` 를 적용한 동일 마크업 을 렌더해 형태 27종의 `getComputedStyle` 을 뽑는다. `contracts/design-conformance.md` §3 의 속성 목록을 잰다. `--json` 으로 사실만 출력한다
- [X] T007 `frontend/tests/CanonMatchesDesign.test.ts` — **L1 대조.** T006 의 출력으로 정본 시트와 확정 디자인 시트의 계산값이 같은지 단언한다. 계산값 비교이므로 `#FFF`/`#ffffff`/`rgb(255,255,255)` 표기 차이에 걸리지 않는다 (FR-281)
- [X] T008 `frontend/tests/VisualLanguage.test.tsx` — **L2 가드.** `import.meta.glob("../src/**/*.tsx", { query: "?raw", eager: true })` 로 화면 파일 **전체를 열거**한다. 손으로 import 하지 않는다 (V-09 의 원인 제거). 축 G-1~G-6 을 세고 `파일:줄 — 발견한 값 (축)` 형식으로 보고한다. `theme/exceptions.ts` 를 읽어 등록된 예외를 제외한다
- [X] T009 T008 을 **경고 모드**로 시작한다 — 상한을 색 327 · 인라인 437 로 두고, 그 이하면 통과한다. 상한 상수에 「내려가기만 한다. 올리려면 커밋 본문에 이유를 적는다」를 주석으로 적는다 (`contracts/visual-language.md` §4)
- [X] T010 `frontend/tests/DesignTokens.test.tsx` 를 정본 기준으로 갱신한다. 기존 v2 단언(모서리 3종·하드 그림자 금지·배경 `#F2F4F7`·디스플레이 서체 없음)은 **유지**하고, 손으로 import 하던 파일 5개 목록을 제거한다 — 그 역할은 T008 이 전부 가져간다
- [X] T011 `npx vitest run` — **657건 + 신규 검사가 전부 초록**인지 확인한다. 이 시점에 화면은 하나도 안 바뀌었으므로 657건은 그대로 통과해야 한다. 깨지면 정본 교체가 기존 동작을 바꾼 것이므로 되돌려 원인을 찾는다

**Checkpoint**: 정본이 서고, L1·L2 가 돌고, 위반 수가 상한으로 고정됐다. 화면 전환을 시작할 수 있다.

---

## Phase 3: User Story 1 — 목록 화면 (Priority: P1) 🎯 MVP

**Goal**: 첫 화면이 디자인과 같아지고, 그 화면을 그리는 코드에 시각 언어 값이 하나도 남지 않는다.

**Independent Test**: `TestList.dc.html`·`EmptyList.dc.html` 과 제품 목록 화면을 나란히 놓고 대조한다. 동시에 `pages/TestList.tsx` 의 색 리터럴이 0인지 센다. 다른 화면이 아직 v1 이어도 목록은 옳다.

**이 화면이 쓰는 형태**: `TestList` — `btn`(+`primary`·`sm`·`off`) · `chip`(+`pass`·`fail`·`run`·`ai`) · `hdr` · `notice` · `pane` · `lbl` · `mono` · `why` / `EmptyList` — `btn`(+`primary`·`off`) · `chip`(+`warn`) · `hdr` · `pane` · `lbl` · `mono` · `why`

**이 묶음의 잔존색**: `#E4DFD1`(크림 띠 — v1 잔재) · `#B8860B`(골드)

> **US1 은 US2 와 병렬로 돌릴 수 없다.** 정본이 실제 화면 하나를 감당하는지 여기서 판명된다.
> 감당 못 하면 여기서 정본을 고치는 것이 33파일 뒤에 고치는 것보다 싸다 (plan 위험표 1번).

- [X] T012 [P] [US1] `frontend/src/components/design/Chrome.tsx` 를 정본 소비로 바꾼다 (hex 11 · 인라인 11). `Artboard`·`HeaderBar`·`BrandMark`·`HeaderDivider` 가 `.hdr` 과 토큰만 쓴다. 껍데기 폭·높이는 배치 계약이므로 인라인 유지, 값 출처만 정본 토큰
- [X] T013 [P] [US1] `frontend/src/components/Badges.tsx` 를 `.chip` 변형으로 바꾼다. 결말 5종(`pass`·`fail`·`warn`·`run`·`ai`)과 미실행(점선 중립)이 **색과 형태를 함께** 쓰는지 확인한다 (FR-271 · SC-410)
- [X] T014 [US1] `frontend/src/pages/TestList.tsx` 의 표 머리와 행을 디자인 격자로 바꾼다 — CSS grid `96px 82px 1fr 64px 92px 150px 168px` / gap 12 / 행 높이 44 / 표 머리 34. **표 머리와 행이 같은 격자를 공유해야 한다** (FR-273 · V-08). 표 머리 바탕 `#14171C` → `--sunken`, 글자 → `.lbl` (V-04)
- [X] T015 [US1] 같은 파일에 **행 왼쪽 3px 결말 마커**를 넣는다 — `border-left: 3px solid var(--pass|--fail|--run|transparent)`. 실패 행 배경 `--fail-t`, 실행 중 행 배경 `--run-t` (FR-271 · V-05)
- [X] T016 [US1] 같은 파일의 행 조작을 `.btn.sm` 중립으로 바꾼다. **잉크 채움은 헤더의 「테스트 만들기」 하나뿐**이다 (FR-269 · C-10 · V-04). 「실행」·「결과 보기」·「실행 화면 보기」가 전부 잉크 채움이던 것을 되돌린다
- [X] T017 [US1] 같은 파일의 글자 크기를 디자인 단계로 내린다 — 테스트 이름 `600 16px` → `500 13px` · ID `600 14px` → mono 12px · STEP mono 14px → mono 12px · 마지막 실행 14px → mono 11.5px (FR-270 · V-06)
- [X] T018 [US1] 같은 파일에 **결말 필터 칩 4종**(전체·통과·실패·미실행)을 만든다. 각 칩이 개수를 함께 보이고 실제로 목록을 거른다. **클라이언트에서 계산한다** — 백엔드 `list_tests` 는 `q` 만 받고 응답이 이미 `outcome` 을 담는다 (research R7 · FR-272 · V-07)
- [X] T019 [US1] 같은 파일에 **정렬 조작**「최근 실행 순」을 만든다. 디자인이 정의한 것만 만들고 그 이상 늘리지 않는다 (FR-272 · Out of Scope)
- [X] T020 [US1] 같은 파일의 빈 목록 상태를 `EmptyList.dc.html` 과 맞춘다. 지금은 `undefined-states` 로만 기록돼 있고 디자인이 생겼다 (`replacement-map.md` §3)
- [X] T021 [US1] 같은 파일의 잔존색을 판정한다 — `#E4DFD1`·`#B8860B`. quickstart 4단계의 판정표를 따른다. v1 잔재면 대응 토큰으로, 대응이 없으면 `exceptions.ts` 에 **사유와 함께** 등록
- [X] T022 [US1] `frontend/tests/TestListFilters.test.tsx` 를 새로 만든다 — 필터 4종이 목록을 거르는지, 정렬이 순서를 바꾸는지, 개수가 맞는지 (FR-272 회귀 가드)
- [X] T023 [US1] `npx vitest run` — **657건 + 신규가 전부 초록.** 깨지면 quickstart 5단계 판정표를 따르고 판정을 커밋 본문에 적는다. 고쳐서 통과시키지 않는다 (헌법 게이트 4)
- [X] T024 [US1] T001 로 재측정해 `baseline.md` 에 US1 후 수치를 추가한다. `pages/TestList.tsx`·`Chrome.tsx`·`Badges.tsx` 의 색 리터럴이 **0** 이어야 한다 (기준선 83+11+0)
- [X] T025 [US1] T009 의 상한을 US1 후 실측값으로 **내린다**. 상한은 내려가기만 한다

**Checkpoint**: 목록 화면이 단독으로 옳다. 정본이 실제 화면을 감당함이 판명됐다.

---

## Phase 4: User Story 2 — 통합 작업 화면 아홉 국면 (Priority: P2)

**Goal**: 만들기·녹화·AI 작성·AI 막힘·이어받기·실행·일시정지·실행 종료·편집 아홉 국면과 Step 상세가 각자의 dc.html 과 같아진다.

**Independent Test**: 아홉 국면을 각각 띄우고 대응 dc.html 과 대조한다. 만들기→녹화→실행→일시정지→이어받기→종료를 한 번 완주해 정보가 사라지지 않았는지 본다.

**이 묶음의 잔존색**: `#E5D3AC` · `#FFF6D9` · `#FFF6D8` · `#EFC7BC` · `#1F7A3D` · `#8A6A16`(WorkArea) · `#F5D000`(ActionButton) · `#B8860B`(PhaseBar) · `#8A6A16`(NoticeStack) · `#EAF5EE`(LocatorPriorityTable) · `#8A5A00`(PacingControl) · `#F0F7F2`(SessionScreen)

### 4-1. 껍데기와 Step 목록 (모든 국면이 공유)

- [X] T026 [US2] `frontend/src/components/workbench/Workbench.tsx` 를 정본 소비로 바꾼다 (hex 3 · 인라인 6). **`data-workbench-*` 속성과 `style.flex` 는 그대로 둔다** — `WorkbenchShell.test.tsx` 의 인라인 단언 4건이 배치 계약이며 초록 유지가 목표다 (research R3)
- [X] T027 [P] [US2] `frontend/src/components/workbench/PhaseBar.tsx` 를 `.phase` 로 바꾼다 (hex 9 · 인라인 7). 국면 띠 높이 48 유지
- [X] T028 [P] [US2] `frontend/src/components/workbench/StepList.tsx` 를 `.steps`·`.steps-hd`·`.srow`(+`pass`·`fail`·`run`·`sel`)로 바꾼다 (hex 37 · 인라인 21 — **단일 파일 최다 잔재**). 행 높이 52 · 격자 `26px 1fr 58px 20px` / gap 10. **`data-step-row`·`data-cell`·`data-outcome` 속성을 전부 보존한다** — `StepRowLayout.test.tsx` 26곳이 그것으로 질의한다
- [X] T029 [P] [US2] `frontend/src/components/workbench/ActionButton.tsx` 를 `.btn`(+`primary`·`danger`·`off`·`sm`)으로 바꾼다 (hex 12 · 인라인 3). **비활성은 `.btn.off` — 점선이고 자리를 지킨다.** 비활성 사유는 `.why` (006 ui-contract §2 유지). 잔존색 `#F5D000` 판정
- [X] T030 [P] [US2] `frontend/src/components/workbench/ActionPalette.tsx` 를 정본 소비로 바꾼다 (hex 13 · 인라인 15)
- [X] T031 [P] [US2] `frontend/src/components/workbench/TargetPane.tsx` 를 정본 소비로 바꾼다 (hex 12 · 인라인 13). 세로 배분은 `lib/layout.ts` 가 정하므로 건드리지 않는다 (007 FR-256·FR-257)
- [X] T032 [P] [US2] `frontend/src/components/workbench/WorkArea.tsx` 를 정본 소비로 바꾼다 (hex 28 · 인라인 38 — **인라인 최다**). 잔존색 6종(`#E5D3AC`·`#FFF6D9`·`#FFF6D8`·`#EFC7BC`·`#1F7A3D`·`#8A6A16`)을 하나씩 판정한다
- [X] T033 [P] [US2] `frontend/src/components/workbench/NoticeStack.tsx` 를 `.notice` 로 바꾼다 (hex 6 · 인라인 4). `States.dc.html` 의 알림 형태를 따른다. 잔존색 `#8A6A16` 판정
- [X] T034 [US2] `npx vitest run` — 껍데기 묶음 회귀 확인. **`WorkbenchShell.test.tsx` 4건과 `StepRowLayout.test.tsx` 26건이 초록인지 특히 확인한다**

### 4-2. Step 상세 (겹침 640)

- [X] T035 [P] [US2] `frontend/src/components/workbench/StepDetail.tsx` 를 정본 소비로 바꾼다 (hex 20 · 인라인 30). 겹침 폭 640 · 모서리 `--radius-lg` 6px · 그림자 `--e-2`. `StepDetail.dc.html` 기준
- [X] T036 [P] [US2] `frontend/src/components/LocatorPriorityTable.tsx` 를 `.pane`·`.lbl`·`.mono`·`.chip` 으로 바꾼다 (hex 10 · 인라인 13). 잔존색 `#EAF5EE` 판정. **우선순위 로직은 건드리지 않는다** (헌법 원칙 IV)
- [X] T037 [P] [US2] `frontend/src/components/StepEditFields.tsx` 를 정본 소비로 바꾼다 (인라인 11)
- [X] T038 [P] [US2] `frontend/src/components/AssertionForm.tsx` 를 정본 소비로 바꾼다 (인라인 11)
- [X] T039 [P] [US2] `frontend/src/components/InlineSecretInput.tsx` 를 정본 소비로 바꾼다 (hex 9 · 인라인 8). **가림 표시 로직을 건드리지 않는다** (FR-277 · 헌법 보안 제약)
- [X] T040 [US2] `npx vitest run` — Step 상세 묶음 회귀. **`InlineSecret.test.tsx`·`SensitiveAcrossPhases.test.tsx` 가 초록인지 특히 확인한다**

### 4-3. 국면 화면

- [X] T041 [US2] `frontend/src/pages/SessionScreen.tsx` 를 정본 소비로 바꾼다 (hex 29 · 인라인 18). 일곱 국면(REC·AI·AI 막힘·TKO·RUN·PAU·실행 종료)이 각자의 dc.html 과 맞는지 국면별로 확인한다. 잔존색 `#F0F7F2` 판정
- [X] T042 [P] [US2] `frontend/src/pages/EditView.tsx` 를 정본 소비로 바꾼다 (hex 5 · 인라인 18). `Main.dc.html` 기준. `.srow.sel` 선택 상태 포함
- [X] T043 [P] [US2] `frontend/src/pages/ComposeView.tsx` 를 정본 소비로 바꾼다 (인라인 1). `Create.dc.html` 기준
- [X] T044 [P] [US2] `frontend/src/components/MirrorView.tsx` 를 정본 소비로 바꾼다 (인라인 7)
- [X] T045 [P] [US2] `frontend/src/components/TabStrip.tsx` 를 정본 소비로 바꾼다 (인라인 2)
- [X] T046 [P] [US2] `frontend/src/components/PacingControl.tsx` 를 정본 소비로 바꾼다 (hex 9 · 인라인 5). 잔존색 `#8A5A00` 판정
- [X] T047 [P] [US2] `frontend/src/App.tsx` 의 인라인 3곳을 정본 소비로 바꾼다
- [X] T048 [US2] **국면 완주 확인.** 만들기→녹화→실행→일시정지→이어받기→실행 종료를 한 번 완주하고, 각 국면에서 이전 판에 보이던 정보·조작·문구가 하나도 사라지지 않았는지 확인한다 (FR-274 · SC-406 · 헌법 원칙 III)
- [X] T049 [US2] `npx vitest run` — **657건 + 신규 전부 초록**
- [X] T050 [US2] T001 재측정 → `baseline.md` 갱신. US2 대상 파일의 색 리터럴이 0인지 확인
- [X] T051 [US2] T009 상한을 US2 후 실측값으로 **내린다**

**Checkpoint**: 아홉 국면 + Step 상세가 디자인과 같다. 잔재의 대부분이 사라졌다.

---

## Phase 5: User Story 3 — 남은 화면 여섯 장 (Priority: P3)

**Goal**: 프로젝트 설정·키 관리·비밀 값·결과 보기와 알림/오류 형태가 디자인과 같아진다.

**Independent Test**: 여섯 화면을 각각 띄우고 대응 dc.html 과 대조한다. 비밀 값 화면은 가림이 유지되는지 함께 본다.

**이 묶음의 잔존색**: `#C9A227` · `#FDF8E7` · `#FBEDEB` · `#B4453C`(ErrorNotice) · `#2A303A`(BrowserFrame)

- [X] T052 [P] [US3] `frontend/src/pages/ProjectSetup.tsx` 를 정본 소비로 바꾼다 (hex 11 · 인라인 46 — **인라인 2위**). `ProjectSetup.dc.html` 기준. **제품의 첫 화면**이므로 첫 실행 경로를 실제로 지나가 본다
- [X] T053 [P] [US3] `frontend/src/pages/KeyManagement.tsx` 를 정본 소비로 바꾼다 (hex 4 · 인라인 29). `Keys.dc.html` 기준. **키 값 가림을 건드리지 않는다** (FR-277)
- [X] T054 [P] [US3] `frontend/src/pages/SecretValues.tsx` 를 정본 소비로 바꾼다 (인라인 15). `Secrets.dc.html` 기준. **비밀 값 가림을 건드리지 않는다** (FR-277)
- [X] T055 [P] [US3] `frontend/src/pages/ResultView.tsx` 를 정본 소비로 바꾼다 (hex 3 · 인라인 6). `Result.dc.html` 기준. 실패 사유·시도한 locator 표·산출물이 이전과 같이 도달 가능한지 확인
- [X] T056 [P] [US3] `frontend/src/components/ErrorNotice.tsx` 를 `.notice`·`.pane`·`.why` 로 바꾼다 (hex 5 · 인라인 4). `States.dc.html` 의 문구·형태 규칙을 따른다. 잔존색 4종(`#C9A227`·`#FDF8E7`·`#FBEDEB`·`#B4453C`) 판정
- [X] T057 [P] [US3] `frontend/src/components/SessionLostBanner.tsx` 를 `.notice` 로 바꾼다 (인라인 7)
- [X] T058 [P] [US3] `frontend/src/components/LiveConnectionBanner.tsx` 를 `.notice` 로 바꾼다 (인라인 2)
- [X] T059 [P] [US3] `frontend/src/components/StartingIndicator.tsx` 를 정본 소비로 바꾼다 (인라인 3)
- [X] T060 [P] [US3] `frontend/src/components/design/BrowserFrame.tsx` 를 정본 소비로 바꾼다 (hex 8 · 인라인 7). 잔존색 `#2A303A` 판정
- [X] T061 [US3] `npx vitest run` — **657건 + 신규 전부 초록.** `KeyManagement.test.tsx`·`InlineSecret.test.tsx`·`ProjectSetup.test.tsx`·`abnormal/error-notice.test.tsx` 를 특히 확인
- [X] T062 [US3] T001 재측정 → `baseline.md` 갱신
- [X] T063 [US3] T009 상한을 **0 직전까지** 내린다

**Checkpoint**: 18장 전부의 대상 코드가 정본을 소비한다.

---

## Phase 6: User Story 4 — 다시 어긋나지 않게 한다 (Priority: P4)

**Goal**: 우회를 가드가 막고, 대조 축이 규칙이 되고, 18장의 판정이 실제로 채워진다.

**Independent Test**: 화면 코드에 색 리터럴을 하나 일부러 넣고 검사가 실패하는지 본다. 대조표 18장의 `미판정`이 0인지 센다.

- [X] T064 [US4] T009 의 상한을 **0 으로 고정**한다. 위반 1건이면 검사가 실패한다. 상한 상수를 제거하고 "0 이 아니면 실패"로 바꾼다 (`contracts/visual-language.md` §4 엄격도 전이 4단계)
- [X] T065 [US4] **가드가 실제로 잡는지 확인한다 (SC-405).** `frontend/tests/VisualLanguage.test.tsx` 에 "위반을 심으면 잡는다" 검사를 넣는다 — 인위적인 소스 문자열에 색 리터럴·인라인 선언·미등록 클래스를 각각 넣고 가드 함수가 그것을 `파일:줄` 과 함께 보고하는지 단언한다. 실제 소스 파일을 더럽히지 않는다
- [X] T066 [US4] `frontend/tests/VisualLanguage.test.tsx` 에 **죽은 예외** 검사를 넣는다 (G-6 · `data-model.md` EX-2) — 등록됐으나 해당 파일에서 실제로 쓰이지 않는 항목을 보고한다. 예외가 관성으로 쌓이는 것을 막는다
- [X] T067 [US4] `scripts/design_baseline.py` 를 `contracts/design-conformance.md` §6 형식으로 개편한다. 뽑는 대상을 **텍스트 통계에서 L1 렌더 계산값 + L2 가드 결과 + L3 3항목**으로 바꾼다. `SCREENS` 표와 `--json`/`--write` 구조는 유지한다. `assert_baseline` 의 「디자인이 바뀌면 먼저 멈춘다」 동작도 유지한다 (FR-280 · DC-D)
- [X] T068 [US4] `python3 scripts/design_baseline.py --write` 로 `docs/design/008-visual-language/conformance/*.md` 18장을 재생성한다. **L1·L2 칸은 검사가 채운다** — 사람이 손으로 적지 않는다 (DC-A). L3 는 화면당 3항목이며 비어 있다 (DC-B)
- [X] T069 [US4] `docs/design/008-visual-language/conformance/undefined-states.md` 를 갱신한다. 전환 중 발견한 미정의 상태(로딩·삭제 확인·정의 읽기 실패·세션 유실 등)를 `screen`·`state`·`why_undefined`·`drawn_with` 로 기록한다. **`drawn_with` 가 정본 형태의 조합임을 보인다** — 새 형태를 만들지 않았다는 증거다 (FR-266·FR-276 · US-1)
- [ ] T070 [US4] **L3 판정 54항목을 채운다** (18장 × 3). 확정 디자인을 열고(`open docs/design/008-visual-language/<Screen>.dc.html` — 그대로 열린다, research R2) 제품의 같은 화면과 대조한다. **구현자가 자기 구현을 판정하지 않는다** (DC-C · 002 가 세운 규칙). `불일치` 면 `비고` 에 차이를 적는다
- [ ] T071 [US4] T070 의 `불일치` 를 고친다. 고친 뒤 다시 판정한다. **완료 조건은 `불일치` 0건 그리고 `미판정` 0건** (SC-401)
- [X] T072 [US4] `docs/design/008-visual-language/replacement-map.md` §4 를 갱신한다. 「인라인 값을 **전사**한다」방침이 이번 라운드에 **폐기됐음**과 그 이유(전사는 1회성이라 다음 변경에서 깨진다)를 적는다. 이 문장이 남아 있으면 다음 라운드가 같은 방식을 되풀이한다

**Checkpoint**: 미판정 0 · 불일치 0 · 가드 상한 0.

---

## Phase 7: 완료 판정 (Polish & Cross-Cutting)

quickstart.md 「완료 판정」의 명령을 그대로 돌린다.

- [X] T073 [P] **SC-402** — 색 리터럴 0: `grep -roE '#[0-9A-Fa-f]{6}' --include='*.tsx' frontend/src | wc -l` 이 0
- [X] T074 [P] **SC-403** — 팔레트 밖 색 0종: `comm -23 <사용색> <정본색>` 이 빈 출력
- [X] T075 [P] **SC-404** — 값이 두 곳에 없다: T008 의 G-2 가 0건. 정본 시트의 어떤 선언도 화면 코드에 중복돼 있지 않다
- [X] T076 [P] **SC-407** — `cd frontend && npx vitest run` 이 **657건 이상 전부 통과**. 삭제·비활성화된 검사가 0건임을 `git diff --stat` 으로 확인한다 (헌법 게이트 4)
- [X] T077 [P] **SC-408** — 확정 디자인에 있는데 코드에 없는 요소 0개. L3-1(가감) 판정 18장이 전부 `일치`
- [X] T078 [P] **SC-409** — 900px 높이에서 Step 13행: `.srow` 52px × 13 = 676px 가 Step 패널 가용 높이에 들어가는지 렌더로 확인한다. v1 의 5행에서 v2 가 노린 밀도가 실제로 나오는지 센다
- [X] T079 [P] **SC-410** — 결말 네 가지가 색 없이도 구분된다. L3-3(상태) 판정으로 확인. 각 결말이 표식·테두리 형태를 색과 함께 쓴다
- [ ] T080 **SC-401** — `grep -c '미판정\|불일치' docs/design/008-visual-language/conformance/*.md` 가 전부 0
- [X] T081 `specs/008-visual-language/baseline.md` 에 최종 표를 완성한다 — 기준선 → US1 → US2 → US3 → 최종. 327→0 · 17종→0 · 509칸→0 의 궤적이 한 표에 보인다
- [X] T082 완료 보고에 **남은 것을 명시한다.** L3 판정이 남았거나 `불일치` 를 미해결로 남겼으면 그 사실과 이유를 적는다. 조용히 넘어가지 않는다 — 그것이 001 T156·002 T099 를 만든 방식이다

---

## Dependencies & Execution Order

### Phase 의존

```
Phase 1 (Setup)         측정 기준 고정
   ↓
Phase 2 (Foundational)  정본·L1·L2  ⚠️ 모든 US 를 막는다
   ↓
Phase 3 (US1)  목록      ← 정본이 실제 화면을 감당하는지 판명
   ↓                       US2 와 병렬 불가 (plan 위험표 1)
Phase 4 (US2)  아홉 국면
   ↓
Phase 5 (US3)  나머지 6장
   ↓
Phase 6 (US4)  가드 조이기·대조   ← 대상이 전부 옮겨진 뒤에만 가능
   ↓
Phase 7        완료 판정
```

### User Story 의존

- **US1 (P1)**: Phase 2 완료 후 시작. 다른 이야기에 의존하지 않는다. **MVP**
- **US2 (P2)**: US1 완료 후. 정본이 검증된 뒤에 큰 표면을 옮긴다
- **US3 (P3)**: US2 완료 후. 정본을 소비하기만 하므로 순서상 마지막 전환
- **US4 (P4)**: US1~US3 전부 완료 후. 대상이 없으면 가드를 조일 수 없다

**왜 US 가 병렬이 아닌가**: 네 이야기가 **같은 정본**을 공유한다. US1 에서 정본이 바뀔 수 있고
(위험표 1번), 그 변경은 US2·US3 을 전부 다시 만지게 한다. 순차가 총비용이 낮다.

### 병렬 기회

| 묶음 | 병렬 가능 작업 |
|---|---|
| Phase 2 | T005·T006 |
| Phase 3 (US1) | T012·T013 (서로 다른 파일). T014~T021 은 같은 `TestList.tsx` 라 순차 |
| Phase 4-1 | T027·T028·T029·T030·T031·T032·T033 (7개, 전부 다른 파일) |
| Phase 4-2 | T035·T036·T037·T038·T039 (5개) |
| Phase 4-3 | T042·T043·T044·T045·T046·T047 (6개) |
| Phase 5 (US3) | T052~T060 (9개, 전부 다른 파일) |
| Phase 7 | T073~T079 (7개, 읽기만 한다) |

---

## Parallel Example: Phase 4-1 (껍데기와 Step 목록)

```text
Task: "PhaseBar.tsx 를 .phase 로 (hex 9 · 인라인 7)"
Task: "StepList.tsx 를 .steps/.srow 로 (hex 37 · 인라인 21) — data-* 보존"
Task: "ActionButton.tsx 를 .btn 변형으로 (hex 12) — 비활성은 .btn.off"
Task: "ActionPalette.tsx 를 정본 소비로 (hex 13 · 인라인 15)"
Task: "TargetPane.tsx 를 정본 소비로 (hex 12 · 인라인 13)"
Task: "WorkArea.tsx 를 정본 소비로 (hex 28 · 인라인 38) — 잔존색 6종 판정"
Task: "NoticeStack.tsx 를 .notice 로 (hex 6) — 잔존색 #8A6A16 판정"
```

T026(Workbench.tsx)은 이 일곱이 붙을 껍데기이므로 **먼저** 끝나야 한다.

---

## Implementation Strategy

### MVP (US1 까지)

1. Phase 1 — 측정 기준 고정
2. Phase 2 — 정본·L1·L2 (**모든 것을 막는 선행 작업**)
3. Phase 3 — 목록 화면
4. **멈추고 확인**: 목록이 디자인과 같은가. 정본이 실제 화면을 감당했는가
5. 감당하지 못한 형태가 있으면 여기서 정본을 조정한다 — 33파일 뒤보다 싸다

### 점진 인도

1. Phase 1+2 → 정본이 선다
2. + US1 → 첫 화면이 옳다 (**MVP**)
3. + US2 → 사용 시간의 대부분이 옳다
4. + US3 → 전부 옳다
5. + US4 → **다시 어긋나지 않는다**

**US4 는 선택 사항이 아니다.** L1·L2 중 하나라도 없으면 plan 의 논증이 무너지고, 사람이
509칸을 채우는 일로 돌아간다 (plan「이 계획이 성립하는 논증」).

---

## Notes

- `[P]` = 서로 다른 파일, 선행 의존 없음
- **화면 하나를 옮기는 절차는 [quickstart.md](./quickstart.md) 6단계 하나다.** 작업마다 다시 정하지 않는다
- **검사가 깨지면 고쳐서 통과시키지 않는다.** quickstart 5단계 판정표를 따르고 판정을 커밋 본문에 적는다 (헌법 게이트 4)
- **확정 디자인 `docs/design/008-visual-language/*.dc.html` 을 수정하지 않는다.** 입력이다
- **백엔드를 수정하지 않는다.** 필터·정렬은 클라이언트다 (research R7)
- **새 의존성을 추가하지 않는다.** playwright 는 `backend/.venv` 에 이미 있고 대조 도구 전용이다
- 가드 상한은 **내려가기만 한다.** 올리려면 커밋 본문에 이유를 적는다
- 작업 또는 논리적 묶음마다 커밋한다

---

## 남은 것 (2026-09-08 · 구현자가 끝낼 수 없는 것)

| 작업 | 왜 남았나 |
|---|---|
| T070 L3 판정 54항목 | **구현자가 자기 구현을 판정하면 대조가 아니라 자기 확인이다** (DC-C · 002 가 세운 규칙). 이 라운드의 구현자가 판정하면 001 T156·002 T099 와 같은 형태가 된다 |
| T071 불일치 수정 | T070 이 끝나야 대상이 생긴다 |
| T080 SC-401 (미판정·불일치 0) | T070·T071 의 결과다 |

**기계가 할 수 있는 것은 전부 끝났다.** L1 625칸·L2 54칸이 18장 전부에서 `일치`이고,
남은 54항목은 화면당 3개다 — 한 자리에서 끝낼 수 있는 양으로 줄인 것이 이 라운드가
501칸을 없앤 이유다.

### 판정하는 방법

```bash
# 1. 확정 디자인을 연다 (그대로 열린다 — support.js 404 는 무해)
open docs/design/008-visual-language/<Screen>.dc.html

# 2. 제품의 같은 화면을 띄운다
# 3. 그 화면의 대조표에서 L3 셋만 본다
open docs/design/008-visual-language/conformance/<Screen>.md
```

**시작 전에 알아야 할 것** — 구현자가 아는 차이 2건이
`conformance/undefined-states.md` §2·§3 에 적혀 있다. 판정을 대신하지는 않는다.

---

## Phase 8: Convergence

**수렴 1회차 (2026-09-08).** 요구사항 22 · 성공 기준 10 · 헌법 5원칙을 코드와 대조해
남은 것을 찾았다. **헌법 위반 0건.** 아래는 전부 「기계가 할 수 있는데 아직 안 한 것」이다.

- [ ] T083 `frontend/tests/CanonMatchesDesign.test.ts` 에 **확정 디자인 쪽 digest 단언**을 넣는다 per FR-280 · DC-D (partial). 지금은 `canonDigest` 만 본다 — 확정 디자인이 바뀌어도 `tokens.css` 가 그대로면 통과한다. `assert_baseline` 은 `npm test` 가 부르지 않으므로 빈틈이 남는다. vitest 가 `../../docs/design/008-visual-language/Language.dc.html?raw` 로 확정 디자인을 읽을 수 있음을 실험으로 확인했다 — 그 원문에서 `<style>` 을 뽑아 `design_render.py` 의 `digest()` 와 같은 규칙(SHA-256 앞 16자리)으로 재고 `report.designDigest` 와 비교한다
- [ ] T084 `frontend/tests/VisualLanguage.test.tsx` 에 **G-4 를 구현한다** per FR-266 · `contracts/visual-language.md` C-3 (missing). 「정본에 있으나 확정 디자인에 없는 값」을 센다. 정본은 두 구획으로 나뉘어 있다 — 추출 구획(디자인에서 기계로 온 것)과 파생 구획(`.pill`·`.navlink`·`.tint-*`·`.modal`·`.segmented`·`.table` 등). **파생 구획이 더한 값이 확정 디자인의 원문(시트 + 인라인)에 실제로 나타나는지** 확인하고, 나타나지 않으면 실패시킨다. 002 가 확정 디자인에 `border-radius` 가 0회인데 `--radius:10px` 를 지어낸 것과 같은 자리가 지금 열려 있다. **`Language.dc.html` 의 v1 대조 예시(「03 · 기하」)는 출처로 인정하지 않는다** — 그 값들은 폐기된 언어다
- [ ] T085 `frontend/tests/VisualLanguage.test.tsx` 에 **G-5 를 구현한다** per FR-263 · C-5 (missing). 껍데기 치수 토큰(`--h-header` 56 · `--h-phase` 48 · `--h-notice` 32 · `--h-control` 32 · `--h-control-sm` 26 · `--h-step` 52 · `--w-steps` 460 · `--w-detail` 640 · `--w-min` 1440)은 `specs/007-unify-test-screens/contracts/ui-contract.md` §1-2 표의 **사본**이다. 정본은 그 표이므로 둘이 어긋나면 멈춰야 한다. 그 표도 vitest 가 `?raw` 로 읽을 수 있다
- [ ] T086 **FR-269 와 확정 디자인의 충돌을 기록한다** per FR-269 (contradicts). FR-269 는 「잉크 채움(`.btn.primary`)은 한 화면에 주 동작 하나」인데 확정 디자인은 화면당 **1~3개**를 쓴다 — TestList 2(헤더 「테스트 만들기」 + 고른 결말 필터) · Secrets 3 · Result 1 · Keys 0. 코드는 디자인을 따랐고 그것이 옳다 (spec Assumptions — 코드가 디자인과 다르면 코드를 고친다). 따라서 **FR-269 문장이 확정 디자인보다 엄격하다.** `conformance/undefined-states.md` §3 에 근거와 함께 적고, 문장을 「주 동작은 화면당 하나이며 선택 상태 표시는 그와 별개다」로 고칠지 판단을 받는다. **spec.md 를 이 작업에서 직접 고치지 않는다**
- [ ] T087 `frontend/src/components/workbench/StepDetail.tsx:343` 의 인라인 `height: "36px"` 를 없앤다 per SC-404 (partial). 정본의 `.pane-hd` 가 이미 그 자리의 형태이고, 높이만 코드가 다시 적고 있다 — 값이 두 곳에 있는 마지막 자리다. `.pane-hd` 에 높이를 주거나 그 자리 전용 파생 클래스로 옮긴다
- [ ] T088 `frontend/tests/TestListFilters.test.tsx` 에 **표 머리와 행이 같은 격자를 쓰는지** 세는 검사를 넣는다 per FR-273 (partial). 지금은 `GRID` 상수 하나로 지켜지지만 강제하는 것이 없어서, 누가 한쪽만 고쳐도 아무도 모른다 — V-08 이 정확히 그 형태였다(열 폭 7개 중 6개가 달랐다). 렌더한 DOM 에서 표 머리와 행의 `gridTemplateColumns` 가 같은 문자열인지 본다

**Checkpoint**: 이 여섯이 끝나면 기계가 셀 수 있는 것은 전부 센다. 남는 것은 L3 판정
54항목뿐이며 그것은 사람의 몫이다 (DC-C).
