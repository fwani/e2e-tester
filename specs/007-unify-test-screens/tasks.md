---

description: "Task list template for feature implementation"
---

# Tasks: 네 화면을 하나로 — 통합 작업 화면과 국면별 조작 권한

**Input**: Design documents from `/specs/007-unify-test-screens/`

**Prerequisites**: plan.md · spec.md · research.md · data-model.md · contracts/ · quickstart.md

**Tests**: 포함한다. 헌법 품질 게이트 3(테스트 동반)이 요구하고, 이 기능의 성공 판정
(SC-001~SC-003·SC-007)이 **기계로 세는 검사**이기 때문이다.

**Organization**: 사용자 스토리별로 묶는다. 단 US1 은 `research.md` R7 이 정한 **국면 단위
제자리 교체** 순서를 내부 순서로 갖는다 — 이 순서는 바꿀 수 없다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완 작업에 의존하지 않음)
- **[Story]**: US1 / US2 / US3 / US4
- 파일 경로를 반드시 적는다

## Path Conventions

- 이 기능은 **`frontend/` 전용**이다. `backend/` 는 변경하지 않는다 (research R6)
- 확정 디자인: `docs/design/`
- 기록: `specs/007-unify-test-screens/design-conformance/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 기록 자리와 검사 골격을 먼저 만든다. 근거 없는 결정이 생기지 않게 하는 것이
목적이다

- [X] T001 기록 파일 골격 3개 생성 in `specs/007-unify-test-screens/design-conformance/` — `replacement-map.md`(표 머리만) · `Workbench.md`(6축 표 머리만) · `undefined-states.md`(표 머리만)
- [X] T002 [P] `scripts/design_baseline.py` 가 `docs/design/Workbench.dc.html` 을 추출 대상에 포함하도록 확장
- [X] T003 [P] `docs/PENDING-HUMAN-VERIFICATION.md` 에 007 항목 2건 자리 추가 — artboard 승인 · 대조 판정
- [X] T004 [P] 국면별 `WorkbenchModel` 픽스처 팩토리 in `frontend/tests/helpers/workbench.ts` — 7국면을 한 줄로 만들 수 있게 한다
- [X] T005 기준선 기록 in `specs/007-unify-test-screens/design-conformance/baseline.md` — ① `cd frontend && npm run typecheck && npm test` 의 통과·실패 목록 ② **현재의 왕복 화면 전환 수** (결과 확인 → 수정 → 재실행 → 결과 확인). ②가 없으면 SC-009 를 판정할 수 없다

**Checkpoint**: 기록 자리와 검사 도구 준비 완료

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 국면 판정 · 권한표 · 표시 층의 공통 계약. **이것 없이는 어느 국면도 옮길 수 없다**

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 국면도 이행하지 않는다. 화면 동작은 아직
바뀌지 않는다

### 국면 판정과 권한

- [X] T006 국면 판정 함수 in `frontend/src/lib/phase.ts` — `data-model.md` §1 의 판정표와 우선순위. **AI 세션 판정은 `authoring_mode` 로 한다 — `state` 가 아니다**
- [X] T007 [P] `frontend/tests/Phase.test.ts` — 세션 상태 × `authoring_mode` 조합이 기대 국면을 낸다. `takeover_recording` 이 AI 세션이면서 TKO 로 판정되는 우선순위 포함
- [X] T008 조작 식별자 33개 in `frontend/src/lib/actions.ts` — `contracts/ui-contract.md` §2 의 목록. 타입으로 고정해 오타가 컴파일에서 잡히게 한다
- [X] T009 정적 권한표 in `frontend/src/lib/capabilities.ts` — `ui-contract.md` §3-1~3-4 의 7×33. `–` 셀은 N1·N2·N3 근거를 값으로 함께 갖는다
- [X] T010 런타임 조건 C1~C13 평가 in `frontend/src/lib/capabilities.ts`
- [X] T011 전 국면 덮어쓰기 O1~O4 in `frontend/src/lib/capabilities.ts` — `pendingRun` · `busy` · 세션 유실 · Step 0개. **표보다 먼저 적용된다** (005 U-06 회귀 방지)
- [X] T012 [P] `frontend/tests/CapabilityCoverage.test.ts` — 33개 전부 표에 있음 · 모든 `–` 이 근거를 가짐 · 모든 `○` 이 이유를 가짐 · 모든 `Remedy.action` 이 33개 안에 있음 (006 E-03 회귀 방지)
- [X] T013 이유·해소 방법 문구를 `frontend/src/lib/wording.ts` 로 모은다 — 컴포넌트에 문자열 리터럴을 두지 않는다

### 표시 모델과 껍데기

- [X] T014 `WorkbenchModel` 타입 in `frontend/src/components/workbench/model.ts` — `data-model.md` §2 그대로
- [X] T015 `StepOutcome` 에 `recorded` 추가 in `frontend/src/components/workbench/model.ts` — 「기록됨」 중립 표식 + 텍스트 라벨. **옛 `components/design/DesignStepList.tsx` 를 고치지 않는다** — T021 이 그 파일을 흡수·삭제하므로 같은 값을 두 곳에 두면 흡수 시점에 어느 쪽이 진실인지 알 수 없다. 근거를 `undefined-states.md` 에 기록
- [X] T016 [P] `frontend/tests/OutcomeVocabulary.test.tsx` · `frontend/tests/UnknownOutcome.test.ts` 갱신 — `recorded` 가 `pass` 와 구별되고 텍스트 라벨을 병기하며, 알 수 없는 결말 처리가 새 값으로 깨지지 않는다
- [X] T017 `ActionButton` in `frontend/src/components/workbench/ActionButton.tsx` — `CapabilityState` 를 받아 그린다. `disabled` 이유를 접근 가능한 설명으로 연결하고 `Remedy` 를 버튼으로 붙인다
- [X] T018 3층 껍데기 `Workbench` in `frontend/src/components/workbench/Workbench.tsx` — 60px 헤더 · 74px 국면 띠 · 본문(좌 유연 / 우 460 고정) · 최소 기준 폭 1440. **데이터를 읽지 않고 명령을 만들지 않는다**
- [X] T019 [P] `PhaseBar` in `frontend/src/components/workbench/PhaseBar.tsx` — 국면 표시 → 테스트 이름 → 결말 요약 → 주요 조작. 결말 요약은 화면에 하나뿐이다
- [X] T020 [P] `NoticeStack` in `frontend/src/components/workbench/NoticeStack.tsx` — `role` 과 `nextAction` 을 별도 칸으로 (003 EC-004)
- [X] T021 **단일 Step 목록** `StepList` in `frontend/src/components/workbench/StepList.tsx` — `DesignStepRow` · `StepPanelHeader` · `OutcomeMark` · `locatorSummary` 를 흡수하고 **`frontend/src/components/design/DesignStepList.tsx` 를 삭제한다.** 칸 순서 고정: 번호 26px / 이름·동작 칩·탭 배지·대상 요약·값 / 소요 시간 / 결말 표식 24px. 남겨 두면 `ImplementationCount` 가 두 구현을 센다
- [X] T022 **단일 Step 상세** `StepDetail` in `frontend/src/components/workbench/StepDetail.tsx` — 우측 겹침 640px. `attempts`(그때 시도) 와 `candidates`(정의의 후보)를 두 축으로 둔다. `pages/StepInspector.tsx` 의 내용을 이식
- [X] T023 [P] `TargetPane` in `frontend/src/components/workbench/TargetPane.tsx` — `mirror` / `artifacts` / `open_browser` / `empty` 네 내용, 한 자리
- [X] T024 [P] `PhaseAside` in `frontend/src/components/workbench/PhaseAside.tsx` — 5종. **`error` · `blocked` 는 값이 있으면 조건 없이 그린다** (001 R2 회귀 방지)

### 검사 골격

- [X] T025 [P] `frontend/tests/WorkbenchShell.test.tsx` — 껍데기 치수와 영역 배치가 7국면에서 같다. **창을 최소 기준 폭보다 넓혔을 때 늘어나는 것이 좌측 대상 앱 영역뿐임을 함께 검사한다** (FR-218a)
- [X] T026 [P] `frontend/tests/StepRowLayout.test.tsx` — 7국면에서 Step 행의 칸 순서·개수가 같고, 값 없는 칸이 다른 칸을 당기지 않는다. **더불어 ① Step 을 지목하는 조작이 7국면에서 같은 방식임(FR-227) ② 작성 주체(사람·AI)가 배지로만 드러나고 행 구조를 바꾸지 않음(FR-228) 을 검사한다**
- [X] T027 `frontend/tests/ImplementationCount.test.tsx` — Step 목록 구현 1개 · Step 상세 구현 1개. **이 시점에는 실패한다.** Phase 3 이 끝나면 통과한다

### 확정 디자인 artboard

- [X] T028 artboard 초안 in `docs/design/Workbench.dc.html` — 1440×900. 일곱 국면을 **하나의 껍데기의 상태로** 정의한다. 값은 기존 6종에서 추출한 것만 쓴다
- [X] T029 `docs/design/canvas.json` 에 항목 추가 + 대체되는 6종의 상태 표시
- [X] T030 대체 관계 기록 in `specs/007-unify-test-screens/design-conformance/replacement-map.md` — 기존 6종의 **모든 영역**을 `그대로`/`이동`/`분리`/`옮기지 않음` 넷으로 판정. `옮기지 않음` 은 이유 필수
- [X] T031 승인 대상 A1~A5 목록 작성 + `docs/PENDING-HUMAN-VERIFICATION.md` 등록. 대조 기록 첫 줄에 「승인 대기 중이며 대조 기준으로 확정되지 않았다」 명시

**Checkpoint**: 공통 계약 완료. `CapabilityCoverage` 통과. 화면 동작은 아직 그대로

---

## Phase 3: User Story 1 - 국면이 바뀌어도 화면 문법이 그대로다 (Priority: P1) 🎯 MVP

**Goal**: 일곱 국면이 같은 껍데기 · 같은 Step 행 · 같은 Step 상세를 쓴다. 구현 개수가
4벌 → 1벌, 2벌 → 1벌이 된다

**Independent Test**: 같은 테스트로 편집 → 실행 → 결과 → 편집을 왕복하면서 Step 행의 칸
자리와 껍데기(기준 폭·헤더 구성)가 국면마다 같은지 대조한다 (`quickstart.md` W-1)

**⚠️ 이 순서는 바꿀 수 없다** (research R7). 각 이행 묶음은 **옛 구현 삭제를 포함해서**
완료다 — 남겨 두면 4벌이 5벌이 된다

### 이행 1 — 실행 중 국면

- [ ] T032 [US1] `SessionScreen` 이 실행 중 국면의 `WorkbenchModel` 을 만든다 in `frontend/src/pages/SessionScreen.tsx` — 세션 구독·상태·명령 소유는 그대로 둔다 (research R2)
- [ ] T033 [US1] `Workbench` 로 실행 중 국면을 그린다 in `frontend/src/pages/SessionScreen.tsx`
- [ ] T034 [US1] `frontend/src/pages/Runner.tsx` **삭제** + `grep -rn "Runner\"" frontend/src` 참조 0건 확인
- [ ] T035 [US1] 기존 테스트 갱신 — `frontend/tests/RunnerPacing.test.tsx` · `RunFinished.test.tsx` · `PauseTransition.test.tsx` · `DesignStepRow.test.tsx`. **선택자와 구조 기대만 고친다. 검증하는 행동이 바뀌면 회귀다**

### 이행 2 — 일시정지 / 검토 국면

- [ ] T036 [US1] 일시정지/검토 국면의 `WorkbenchModel` in `frontend/src/pages/SessionScreen.tsx` — `paused_tools` 보조 영역(검증 추가 폼·순서 변경)
- [ ] T037 [US1] 권한표 PAU 열을 **현재 동작과 대조**하고 차이를 `contracts/ui-contract.md` §3 에 반영 (UC-401). 대조 결과를 커밋 메시지에 남긴다
- [ ] T038 [US1] `frontend/src/pages/RunnerPaused.tsx` **삭제** + 참조 0건 확인
- [ ] T039 [US1] 기존 테스트 갱신 — `frontend/tests/RunnerReview.test.tsx` · `SaveFeedback.test.tsx` · `StepListPerformance.test.tsx` · `ResumeRequestBody.test.ts`

### 이행 3 — 사람이 직접 조작 국면

- [ ] T040 [US1] 사람이 직접 조작 국면의 `WorkbenchModel` in `frontend/src/pages/SessionScreen.tsx` — `takeover_guide` 보조 영역
- [ ] T041 [US1] 런타임 조건 C4 확정 — 사람이 조작하는 동안 실행 속도 설정이 적용되는지 현재 동작을 확인하고 `contracts/ui-contract.md` §3-5 를 확정값으로 고친다
- [ ] T042 [US1] `frontend/src/pages/Takeover.tsx` **삭제** + 참조 0건 확인

### 이행 4 — AI 작성 국면

- [ ] T043 [US1] AI 작성 국면의 `WorkbenchModel` in `frontend/src/pages/SessionScreen.tsx` — `ai_progress` 보조 영역(지시문 · 진행 로그 · `error` · `blocked`)
- [ ] T044 [US1] `error` · `blocked` 가 **국면·세션 상태와 무관하게** 그려지는지 보장 + `frontend/tests/AiFailureVisible.test.tsx` 신설 (FR-218f · FR-253 · 001 R2)
- [ ] T045 [US1] AI 작성 국면 Step 행에 **번호 표시**(S-08) 와 `recorded` 표식 적용(S-09) in `frontend/src/components/workbench/StepList.tsx` 경유
- [ ] T046 [US1] `frontend/src/pages/AiRecord.tsx` **삭제** + `frontend/tests/AiRecord.test.tsx` 갱신 + 참조 0건 확인

### 이행 5 — 결과보기 국면

- [ ] T047 [US1] `ResultView` 어댑터 신설 in `frontend/src/pages/ResultView.tsx` — 결과 조회 + 정의 조회를 함께 읽고 `step_id` 로 매칭해 행을 채운다 (research R3)
- [ ] T048 [US1] 매칭 실패 알림 「이 결과 이후 정의가 바뀌었습니다」 in `frontend/src/pages/ResultView.tsx` + 문구는 `lib/wording.ts`
- [ ] T049 [US1] 결과 국면 좌측을 산출물로 in `frontend/src/pages/ResultView.tsx` — `TargetPane` 의 `artifacts` (FR-244)
- [ ] T050 [US1] `frontend/src/pages/RunResult.tsx` **삭제** + `frontend/tests/RunResult.test.tsx` 갱신 + `frontend/src/App.tsx` 배선 교체. **통합 대상이 아닌 화면(목록·테스트 만들기)에서 결과 국면으로 들어오는 진입점이 그대로 동작하는지 확인한다** (FR-217a)
- [ ] T051 [US1] 부분 실행 표시 유지 확인 in `frontend/src/pages/ResultView.tsx` + `frontend/tests/RecheckPhase12.test.tsx` 갱신 — 건너뜀/미실행 구별 · 부분 실행 진단 · 직전 전체 실행 (005 FR-151·FR-152·FR-153 회귀 금지)

### 이행 6 — 편집 국면 + Step 상세

- [ ] T052 [US1] `EditView` 어댑터 신설 in `frontend/src/pages/EditView.tsx` — 정의 조회 + 편집 연산 초안. 초안은 브라우저 저장소에 넣지 않는다 (006 R8)
- [ ] T053 [US1] 편집 국면을 `Workbench` 껍데기로 in `frontend/src/pages/EditView.tsx` — 최대 폭 1080 가운데 정렬 본문을 버린다 (S-06 해소)
- [ ] T054 [US1] Step 상세를 `StepDetail` 하나로 in `frontend/src/pages/EditView.tsx` — 인라인 패널을 만들지 않고 `frontend/src/components/workbench/StepDetail.tsx` 의 겹침 패널을 쓴다 (FR-230)
- [ ] T055 [US1] `frontend/src/pages/TestDefinition.tsx` · `frontend/src/pages/StepInspector.tsx` **삭제** + 참조 0건 확인
- [ ] T056 [US1] 기존 테스트 갱신 — `frontend/tests/TestDefinition.test.tsx` · `EditEntryPoints.test.tsx` · `LocatorPriorityTable.test.tsx` · `InlineSecret.test.tsx` · `TestListActions.test.tsx`. **목록 행 메뉴와 결과 화면에서 편집 국면으로 들어오는 진입점 3개가 모두 동작해야 한다** (FR-217a · 006 FR-179)
- [ ] T057 [US1] `frontend/tests/ImplementationCount.test.tsx` **통과** 확인 — Step 목록 1개 · Step 상세 1개 (SC-001)

**Checkpoint**: 일곱 국면이 하나의 껍데기를 쓴다. `WorkbenchShell` · `StepRowLayout` ·
`ImplementationCount` 통과. `quickstart.md` W-1 통과

---

## Phase 4: User Story 2 - 지금 무엇을 할 수 있는지 화면이 말해 준다 (Priority: P1)

**Goal**: 쓸 수 없는 조작이 같은 자리에 비활성으로 남고, 이유와 해소 방법이 붙는다

**Independent Test**: 권한표가 「불가」로 정한 조작이 각 국면 화면에 **남아 있고** 이유가
붙어 있는지 센다 (`quickstart.md` W-2 · §1-4)

> Phase 3 은 `ActionButton` 이 `CapabilityMap` 을 읽는 **배선**을 깐다. 이 단계는 그 위에
> 이유·해소 방법의 **내용**과 커버리지 보장을 얹는다

- [ ] T058 [US2] 실행 중 국면의 편집 조작 비활성 처리 in `frontend/src/lib/capabilities.ts` + `frontend/src/lib/wording.ts` — 값 수정·삭제·순서 변경이 같은 자리에 남고 이유 + 「실행 중인 세션 보기」가 붙는다 (006 FR-206·FR-207 유지)
- [ ] T059 [US2] 결과 국면의 편집 조작 비활성 처리 in `frontend/src/lib/capabilities.ts` — 비활성으로 남고 해소 방법 「편집으로 이동」(`nav.editStep`)이 붙는다
- [ ] T060 [US2] 편집 국면의 브라우저 요구 조작 비활성 처리 in `frontend/src/lib/capabilities.ts` — 해소 방법 「브라우저 열어 Step nn 에서 멈추기」(`browser.openAt`)가 붙는다 (006 FR-200·FR-202 유지)
- [ ] T061 [US2] 편집 국면 실행 조작을 **저장 여부와 무관하게** 노출 in `frontend/src/pages/EditView.tsx` — 선행 상태가 필요하면 비활성 + 이유 (S-07 · FR-237)
- [ ] T062 [US2] 실행·부분 실행 조작의 자리와 라벨 규칙 통일 in `frontend/src/components/workbench/PhaseBar.tsx` — 시작 지점이 라벨에 드러난다 (FR-236 · 005 FR-149)
- [ ] T063 [US2] 결말 요약 유일성 보장 in `frontend/src/components/workbench/PhaseBar.tsx` + `frontend/tests/WorkbenchShell.test.tsx` 에 `data-run-summary` 유일성 검사 추가 (FR-218d · 005 FR-140)
- [ ] T064 [US2] 비활성 이유의 접근성 연결 in `frontend/src/components/workbench/ActionButton.tsx` — 이유가 접근 가능한 이름 또는 설명으로 전달된다
- [ ] T065 [US2] `frontend/tests/CapabilityUI.test.tsx` 신설 — 7국면 각각에서 `○` 조작이 화면에 존재하고 이유를 가진다. 감춰진 조작 0건 (SC-004)
- [ ] T066 [US2] `frontend/tests/RunTrigger.test.tsx` · `RunRejectNavigation.test.tsx` 갱신 — 실행 진입 단일 경로와 중복 방지가 모든 국면에서 유지된다 (FR-248·FR-249)
- [ ] T067 [US2] 라벨↔동작 대응의 유일성 보장 in `frontend/src/lib/wording.ts` + `frontend/tests/LabelUniqueness.test.ts` 신설 — 한 라벨이 두 `ActionId` 에 쓰이지 않는다. `run.stop` 처럼 상황에 따라 라벨이 바뀌는 조작은 **라벨 집합이 다른 조작과 겹치지 않아야** 한다 (FR-235 · 005 FR-147)
- [ ] T068 [US2] 민감 값 표시 검사 in `frontend/tests/SensitiveAcrossPhases.test.tsx` 신설 — 일곱 국면 전부에서 민감 변수를 참조하는 값이 `{{NAME}}` 형태로만 보이고 평문이 화면·요청 본문에 없다 (FR-252 · 006 FR-212·FR-215)

**Checkpoint**: 권한표가 화면의 유일한 근거다. 감춰진 조작 0건

---

## Phase 5: User Story 3 - 국면을 넘어도 보던 Step 을 잃지 않는다 (Priority: P2)

**Goal**: 결과 → 편집 → 브라우저 세션 → 결과 왕복에서 지목한 Step 이 이어진다

**Independent Test**: 실패 Step 을 지목해 한 바퀴 돌린 뒤 그 Step 을 다시 찾는 조작이
0회인지 센다 (`quickstart.md` W-3)

- [ ] T069 [US3] `WorkbenchLocation`(국면 · testId · stepId)로 주소 반영 정리 in `frontend/src/hooks/useScreenUrl.ts`
- [ ] T070 [US3] 세션 → 결과 구간의 지목 Step 전달 in `frontend/src/App.tsx` — `onShowResult` 가 Step 식별자를 함께 넘긴다 (S-10 해소)
- [ ] T071 [US3] 지목한 Step 이 더 이상 없을 때의 진입 처리 in `frontend/src/components/workbench/StepList.tsx` — 사실을 밝히고 목록을 정상 표시 (FR-243)
- [ ] T072 [US3] 저장하지 않은 변경이 있을 때 국면 이동 확인 절차 유지 in `frontend/src/pages/EditView.tsx` (006 FR-208 · FR-242)
- [ ] T073 [US3] 뒤로 가기가 앱 안의 이전 국면으로 돌아가는지 확인 in `frontend/src/hooks/useScreenUrl.ts` (005 FR-167 · FR-241)
- [ ] T074 [US3] 사용자 조작 없는 국면 전환 처리 in `frontend/src/pages/SessionScreen.tsx` + `frontend/src/components/workbench/NoticeStack.tsx` — 실행이 끝나 결과 국면으로 넘어가는 순간 무엇이 바뀌었는지 알리고 보던 대상(지목 Step·스크롤 위치)을 잃지 않는다 (FR-220)
- [ ] T075 [US3] `frontend/tests/PhaseContext.test.tsx` 신설 — 왕복 전 구간 지목 유지 + 새로 고침 복원 10/10 (SC-005·SC-006)
- [ ] T076 [US3] `frontend/tests/ScreenUrl.test.ts` 갱신 — 국면·stepId 왕복 변환

**Checkpoint**: 지목한 Step 을 다시 찾는 조작 0회

---

## Phase 6: User Story 4 - 대상 앱을 보는 자리가 하나다 (Priority: P3)

**Goal**: 좌측 영역의 위치·크기가 국면과 무관하게 같고 내용만 바뀐다

**Independent Test**: 네 국면을 차례로 열어 좌측 영역의 자리가 같고 내용만 바뀌는지 대조한다
(`quickstart.md` W-4)

> 결과 국면의 좌측 전환 자체는 이행 5(T049)에서 구조적으로 이루어진다. 이 단계는 그 영역의
> 남은 요구 — 빈 이유 구별 · 선택 조작 위치 · 비어 있는 국면 — 를 완성한다

- [ ] T077 [US4] 빈 이유 4종 구별 in `frontend/src/components/workbench/TargetPane.tsx` — 아직 시작하지 않음 / 수집되지 않음 / 세션 유실 / 지원되지 않음 (FR-245 · 005 FR-173)
- [ ] T078 [US4] 산출물 선택 조작을 좌측 영역 안에 배치하고 TRACE 를 비활성 + 이유로 유지 in `frontend/src/components/workbench/TargetPane.tsx` (FR-246 · DC-007)
- [ ] T079 [US4] 편집 국면 좌측의 「브라우저 열어 Step nn 에서 멈추기」 배치 in `frontend/src/components/workbench/TargetPane.tsx`
- [ ] T080 [US4] 국면 보조 영역이 빈 국면에서 자리를 차지하지 않되 다른 영역의 자리를 바꾸지 않음 in `frontend/src/components/workbench/Workbench.tsx` (FR-218e)
- [ ] T081 [US4] `frontend/tests/TargetPane.test.tsx` 신설 — 네 내용이 같은 자리를 쓰고 빈 이유가 구별된다

**Checkpoint**: 좌측 영역이 한 자리다

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 기록을 남기고 회귀를 확인한다. **기록 없는 임의 결정 0건**이 목표다

- [ ] T082 [P] `specs/007-unify-test-screens/design-conformance/undefined-states.md` 작성 — 007 이 정한 모든 미정의 상태와 **근거**. 최소 목록은 `contracts/design-conformance-007.md` §6
- [ ] T083 [P] 대조 기록 기준값 채우기 in `specs/007-unify-test-screens/design-conformance/Workbench.md` — `scripts/design_baseline.py` 로 추출. **판정 칸은 비워 둔다 — 사람이 채운다**
- [ ] T084 [P] `docs/DEVELOPMENT.md` 갱신 — 화면 구조 설명을 7국면 하나의 화면으로 고친다
- [ ] T085 [P] `contracts/ui-contract.md` 최종화 — T037·T041 의 실측 대조 결과를 반영한 표가 정본임을 확인
- [ ] T086 타입 검사 통과 — `cd frontend && npm run typecheck` (`frontend/tsconfig.json` 의 `noUncheckedIndexedAccess` 아래)
- [ ] T087 전량 테스트 — `cd frontend && npm test` · `cd backend && bash scripts/test-backend.sh`. **삭제·건너뛰기로 통과시키지 않는다** (헌법 게이트 4)
- [ ] T088 `quickstart.md` §1 자동 검사 4종 전부 통과 확인 — `ImplementationCount` · `StepRowLayout` · `WorkbenchShell` · `CapabilityCoverage`
- [ ] T089 성능 확인 — Step 200개 목록에서 `frontend/tests/StepListPerformance.test.tsx` 기준을 낮추지 않고 통과
- [ ] T090 `docs/PENDING-HUMAN-VERIFICATION.md` 최종 갱신 — 사람 판정 2건(artboard 승인 · 대조 판정)의 준비물 위치와 남은 판정 칸 수를 적는다
- [ ] T091 `quickstart.md` §2 의 걷기 항목 W-1~W-6 을 실제로 걸어 `docs/ux/` 에 기록 (W-7 은 사람 판정 대기)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: 의존 없음
- **Phase 2 Foundational**: Phase 1 이후. **모든 사용자 스토리를 막는다**
- **Phase 3 US1**: Phase 2 이후. **내부 순서(이행 1→6)를 바꿀 수 없다** (research R7)
- **Phase 4 US2**: Phase 3 이후. 국면 화면이 존재해야 이유·해소 방법을 얹을 수 있다
- **Phase 5 US3**: Phase 3 이후. Phase 4 와 병행 가능
- **Phase 6 US4**: Phase 3 의 이행 5(T049) 이후. Phase 4·5 와 병행 가능
- **Phase 7 Polish**: 원하는 스토리가 모두 끝난 뒤

### User Story Dependencies

- **US1 (P1)**: Phase 2 이후 시작. 다른 스토리에 의존하지 않는다. **MVP**
- **US2 (P1)**: US1 에 의존한다 — 조작을 얹을 화면이 있어야 한다. 이 기능에서 US1·US2 는
  독립이 아니며, 그것이 사실이므로 그대로 적는다
- **US3 (P2)**: US1 에 의존. US2 와는 독립
- **US4 (P3)**: US1 의 이행 5 에 의존. US2·US3 과는 독립

### Within Each Phase

- 이행 묶음은 **모델 → 렌더 → 옛 구현 삭제 → 테스트 갱신** 순서다. 삭제가 빠지면 미완이다
- 검사(T012·T025·T026·T027)는 대상보다 먼저 있어도 된다 — 실패하는 상태로 두고 이행이
  통과시킨다

### Parallel Opportunities

- Phase 1: T002·T003·T004 병렬
- Phase 2: T007·T012·T016 병렬 / T019·T020·T023·T024 병렬 / T025·T026 병렬
- Phase 2 의 artboard 묶음(T028~T031)은 나머지 Phase 2 와 **병렬 가능** — 표시 층 구현과
  파일이 겹치지 않는다
- Phase 3 내부는 **병렬 불가**. 같은 파일(`SessionScreen.tsx`)을 연속으로 고치고 순서가
  설계의 일부다
- Phase 4·5·6 은 서로 병렬 가능
- Phase 7: T082·T083·T084·T085 병렬

---

## Parallel Example: Phase 2

```bash
# 표시 층 조각 (파일이 서로 다르다)
Task: "PhaseBar in frontend/src/components/workbench/PhaseBar.tsx"
Task: "NoticeStack in frontend/src/components/workbench/NoticeStack.tsx"
Task: "TargetPane in frontend/src/components/workbench/TargetPane.tsx"
Task: "PhaseAside in frontend/src/components/workbench/PhaseAside.tsx"

# 검사 골격
Task: "Phase.test.ts"
Task: "CapabilityCoverage.test.ts"
Task: "OutcomeVocabulary.test.tsx 갱신"

# artboard 묶음 (표시 층과 파일이 겹치지 않는다)
Task: "docs/design/Workbench.dc.html 초안"
Task: "replacement-map.md"
```

---

## Implementation Strategy

### MVP First (US1 만)

1. Phase 1 Setup
2. Phase 2 Foundational — **여기가 막는다**
3. Phase 3 US1 — 이행 1→6 을 순서대로
4. **멈추고 검증**: `quickstart.md` W-1 + 자동 검사 3종
5. 이 시점에 사용자가 제기한 문제의 핵심이 해소된다 — 구현 4벌 → 1벌, 껍데기 하나

### Incremental Delivery

1. Setup + Foundational → 계약 준비
2. US1 → 문법 통일 → **여기서 데모 가능**
3. US2 → 조작 가능 여부가 화면에 드러난다
4. US3 → 맥락이 이어진다
5. US4 → 좌측 영역 완성

각 단계가 이전 것을 깨지 않는다. **단 US1 의 내부 이행은 쪼개서 멈출 수 없다** — 한 국면을
옮기는 중간에 멈추면 그 국면에 구현이 둘 있는 상태가 된다

### 이 기능에서 하지 말아야 할 것

- **기존 화면을 남긴 채 통합 화면을 병행 추가** — 4벌이 5벌이 된다. 사용자가 제기한 문제를
  늘리는 것이다
- **깨진 테스트를 삭제·건너뛰기로 통과** — 헌법 게이트 4. 고쳐서 통과시킨다
- **승인되지 않은 artboard 초안을 근거로 "확정 디자인대로 만들었다" 고 판정** —
  `contracts/design-conformance-007.md` §5
- **백엔드 변경** — 필요해지면 설계가 틀렸다는 신호다. 멈추고 다시 판단한다 (research R6)

---

## Notes

- `[P]` = 다른 파일, 미완 의존 없음
- 이행 묶음마다 커밋한다. 되돌릴 지점을 남기는 것이 목적이다
- 권한표와 코드가 어긋나면 **코드를 고친다.** 단 현재 쓸 수 있는 조작이 표에서 `–` 이면
  표가 틀린 것이다 (UC-401 · FR-247)
- 총 91개 작업. Setup 5 · Foundational 26 · US1 26 · US2 11 · US3 8 · US4 5 · Polish 10
- 마지막 3개(T067·T068·T074)는 `analyze` 가 찾은 커버리지 공백을 닫으려고 추가한 것이다 —
  FR-235(같은 라벨 = 같은 동작) · FR-252(민감 값 7국면) · FR-220(자동 국면 전환 알림)
