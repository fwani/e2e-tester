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

- [X] T032 [US1] `SessionScreen` 이 실행 중 국면의 `WorkbenchModel` 을 만든다 in `frontend/src/pages/SessionScreen.tsx` — 세션 구독·상태·명령 소유는 그대로 둔다 (research R2)
- [X] T033 [US1] `Workbench` 로 실행 중 국면을 그린다 in `frontend/src/pages/SessionScreen.tsx`
- [X] T034 [US1] `frontend/src/pages/Runner.tsx` **삭제** + `grep -rn "Runner\"" frontend/src` 참조 0건 확인
- [X] T035 [US1] 기존 테스트 갱신 — `frontend/tests/RunnerPacing.test.tsx` · `RunFinished.test.tsx` · `PauseTransition.test.tsx` · `DesignStepRow.test.tsx`. **선택자와 구조 기대만 고친다. 검증하는 행동이 바뀌면 회귀다**

### 이행 2 — 일시정지 / 검토 국면

- [X] T036 [US1] 일시정지/검토 국면의 `WorkbenchModel` in `frontend/src/pages/SessionScreen.tsx` — `paused_tools` 보조 영역(검증 추가 폼·순서 변경)
- [X] T037 [US1] 권한표 PAU 열을 **현재 동작과 대조**하고 차이를 `contracts/ui-contract.md` §3 에 반영 (UC-401). 대조 결과를 커밋 메시지에 남긴다
- [X] T038 [US1] `frontend/src/pages/RunnerPaused.tsx` **삭제** + 참조 0건 확인
- [X] T039 [US1] 기존 테스트 갱신 — `frontend/tests/RunnerReview.test.tsx` · `SaveFeedback.test.tsx` · `StepListPerformance.test.tsx` · `ResumeRequestBody.test.ts`

### 이행 3 — 사람이 직접 조작 국면

- [X] T040 [US1] 사람이 직접 조작 국면의 `WorkbenchModel` in `frontend/src/pages/SessionScreen.tsx` — `takeover_guide` 보조 영역
- [X] T041 [US1] 런타임 조건 C4 확정 — 사람이 조작하는 동안 실행 속도 설정이 적용되는지 현재 동작을 확인하고 `contracts/ui-contract.md` §3-5 를 확정값으로 고친다
- [X] T042 [US1] `frontend/src/pages/Takeover.tsx` **삭제** + 참조 0건 확인

### 이행 4 — AI 작성 국면

- [X] T043 [US1] AI 작성 국면의 `WorkbenchModel` in `frontend/src/pages/SessionScreen.tsx` — `ai_progress` 보조 영역(지시문 · 진행 로그 · `error` · `blocked`)
- [X] T044 [US1] `error` · `blocked` 가 **국면·세션 상태와 무관하게** 그려지는지 보장 + `frontend/tests/AiFailureVisible.test.tsx` 신설 (FR-218f · FR-253 · 001 R2)
- [X] T045 [US1] AI 작성 국면 Step 행에 **번호 표시**(S-08) 와 `recorded` 표식 적용(S-09) in `frontend/src/components/workbench/StepList.tsx` 경유
- [X] T046 [US1] `frontend/src/pages/AiRecord.tsx` **삭제** + `frontend/tests/AiRecord.test.tsx` 갱신 + 참조 0건 확인

### 이행 5 — 결과보기 국면

- [X] T047 [US1] `ResultView` 어댑터 신설 in `frontend/src/pages/ResultView.tsx` — 결과 조회 + 정의 조회를 함께 읽고 `step_id` 로 매칭해 행을 채운다 (research R3)
- [X] T048 [US1] 매칭 실패 알림 「이 결과 이후 정의가 바뀌었습니다」 in `frontend/src/pages/ResultView.tsx` + 문구는 `lib/wording.ts`
- [X] T049 [US1] 결과 국면 좌측을 산출물로 in `frontend/src/pages/ResultView.tsx` — `TargetPane` 의 `artifacts` (FR-244)
- [X] T050 [US1] `frontend/src/pages/RunResult.tsx` **삭제** + `frontend/tests/RunResult.test.tsx` 갱신 + `frontend/src/App.tsx` 배선 교체. **통합 대상이 아닌 화면(목록·테스트 만들기)에서 결과 국면으로 들어오는 진입점이 그대로 동작하는지 확인한다** (FR-217a)
- [X] T051 [US1] 부분 실행 표시 유지 확인 in `frontend/src/pages/ResultView.tsx` + `frontend/tests/RecheckPhase12.test.tsx` 갱신 — 건너뜀/미실행 구별 · 부분 실행 진단 · 직전 전체 실행 (005 FR-151·FR-152·FR-153 회귀 금지)

### 이행 6 — 편집 국면 + Step 상세

- [X] T052 [US1] `EditView` 어댑터 신설 in `frontend/src/pages/EditView.tsx` — 정의 조회 + 편집 연산 초안. 초안은 브라우저 저장소에 넣지 않는다 (006 R8)
- [X] T053 [US1] 편집 국면을 `Workbench` 껍데기로 in `frontend/src/pages/EditView.tsx` — 최대 폭 1080 가운데 정렬 본문을 버린다 (S-06 해소)
- [X] T054 [US1] Step 상세를 `StepDetail` 하나로 in `frontend/src/pages/EditView.tsx` — 인라인 패널을 만들지 않고 `frontend/src/components/workbench/StepDetail.tsx` 의 겹침 패널을 쓴다 (FR-230)
- [X] T055 [US1] `frontend/src/pages/TestDefinition.tsx` · `frontend/src/pages/StepInspector.tsx` **삭제** + 참조 0건 확인
- [X] T056 [US1] 기존 테스트 갱신 — `frontend/tests/TestDefinition.test.tsx` · `EditEntryPoints.test.tsx` · `LocatorPriorityTable.test.tsx` · `InlineSecret.test.tsx` · `TestListActions.test.tsx`. **목록 행 메뉴와 결과 화면에서 편집 국면으로 들어오는 진입점 3개가 모두 동작해야 한다** (FR-217a · 006 FR-179)
- [X] T057 [US1] `frontend/tests/ImplementationCount.test.tsx` **통과** 확인 — Step 목록 1개 · Step 상세 1개 (SC-001)

**Checkpoint**: 일곱 국면이 하나의 껍데기를 쓴다. `WorkbenchShell` · `StepRowLayout` ·
`ImplementationCount` 통과. `quickstart.md` W-1 통과

---

## Phase 4: User Story 2 - 지금 무엇을 할 수 있는지 화면이 말해 준다 (Priority: P1)

**Goal**: 쓸 수 없는 조작이 같은 자리에 비활성으로 남고, 이유와 해소 방법이 붙는다

**Independent Test**: 권한표가 「불가」로 정한 조작이 각 국면 화면에 **남아 있고** 이유가
붙어 있는지 센다 (`quickstart.md` W-2 · §1-4)

> Phase 3 은 `ActionButton` 이 `CapabilityMap` 을 읽는 **배선**을 깐다. 이 단계는 그 위에
> 이유·해소 방법의 **내용**과 커버리지 보장을 얹는다

- [X] T058 [US2] 실행 중 국면의 편집 조작 비활성 처리 in `frontend/src/lib/capabilities.ts` + `frontend/src/lib/wording.ts` — 값 수정·삭제·순서 변경이 같은 자리에 남고 이유 + 「실행 중인 세션 보기」가 붙는다 (006 FR-206·FR-207 유지)
- [X] T059 [US2] 결과 국면의 편집 조작 비활성 처리 in `frontend/src/lib/capabilities.ts` — 비활성으로 남고 해소 방법 「편집으로 이동」(`nav.editStep`)이 붙는다
- [X] T060 [US2] 편집 국면의 브라우저 요구 조작 비활성 처리 in `frontend/src/lib/capabilities.ts` — 해소 방법 「브라우저 열어 Step nn 에서 멈추기」(`browser.openAt`)가 붙는다 (006 FR-200·FR-202 유지)
- [X] T061 [US2] 편집 국면 실행 조작을 **저장 여부와 무관하게** 노출 in `frontend/src/pages/EditView.tsx` — 선행 상태가 필요하면 비활성 + 이유 (S-07 · FR-237)
- [X] T062 [US2] 실행·부분 실행 조작의 자리와 라벨 규칙 통일 in `frontend/src/components/workbench/PhaseBar.tsx` — 시작 지점이 라벨에 드러난다 (FR-236 · 005 FR-149)
- [X] T063 [US2] 결말 요약 유일성 보장 in `frontend/src/components/workbench/PhaseBar.tsx` + `frontend/tests/WorkbenchShell.test.tsx` 에 `data-run-summary` 유일성 검사 추가 (FR-218d · 005 FR-140)
- [X] T064 [US2] 비활성 이유의 접근성 연결 in `frontend/src/components/workbench/ActionButton.tsx` — 이유가 접근 가능한 이름 또는 설명으로 전달된다
- [X] T065 [US2] `frontend/tests/CapabilityUI.test.tsx` 신설 — 7국면 각각에서 `○` 조작이 화면에 존재하고 이유를 가진다. 감춰진 조작 0건 (SC-004)
- [X] T066 [US2] `frontend/tests/RunTrigger.test.tsx` · `RunRejectNavigation.test.tsx` 갱신 — 실행 진입 단일 경로와 중복 방지가 모든 국면에서 유지된다 (FR-248·FR-249)
- [X] T067 [US2] 라벨↔동작 대응의 유일성 보장 in `frontend/src/lib/wording.ts` + `frontend/tests/LabelUniqueness.test.ts` 신설 — 한 라벨이 두 `ActionId` 에 쓰이지 않는다. `run.stop` 처럼 상황에 따라 라벨이 바뀌는 조작은 **라벨 집합이 다른 조작과 겹치지 않아야** 한다 (FR-235 · 005 FR-147)
- [X] T068 [US2] 민감 값 표시 검사 in `frontend/tests/SensitiveAcrossPhases.test.tsx` 신설 — 일곱 국면 전부에서 민감 변수를 참조하는 값이 `{{NAME}}` 형태로만 보이고 평문이 화면·요청 본문에 없다 (FR-252 · 006 FR-212·FR-215)

**Checkpoint**: 권한표가 화면의 유일한 근거다. 감춰진 조작 0건

---

## Phase 5: User Story 3 - 국면을 넘어도 보던 Step 을 잃지 않는다 (Priority: P2)

**Goal**: 결과 → 편집 → 브라우저 세션 → 결과 왕복에서 지목한 Step 이 이어진다

**Independent Test**: 실패 Step 을 지목해 한 바퀴 돌린 뒤 그 Step 을 다시 찾는 조작이
0회인지 센다 (`quickstart.md` W-3)

- [X] T069 [US3] `WorkbenchLocation`(국면 · testId · stepId)로 주소 반영 정리 in `frontend/src/hooks/useScreenUrl.ts`
- [X] T070 [US3] 세션 → 결과 구간의 지목 Step 전달 in `frontend/src/App.tsx` — `onShowResult` 가 Step 식별자를 함께 넘긴다 (S-10 해소)
- [X] T071 [US3] 지목한 Step 이 더 이상 없을 때의 진입 처리 in `frontend/src/components/workbench/StepList.tsx` — 사실을 밝히고 목록을 정상 표시 (FR-243)
- [X] T072 [US3] 저장하지 않은 변경이 있을 때 국면 이동 확인 절차 유지 in `frontend/src/pages/EditView.tsx` (006 FR-208 · FR-242)
- [X] T073 [US3] 뒤로 가기가 앱 안의 이전 국면으로 돌아가는지 확인 in `frontend/src/hooks/useScreenUrl.ts` (005 FR-167 · FR-241)
- [X] T074 [US3] 사용자 조작 없는 국면 전환 처리 in `frontend/src/pages/SessionScreen.tsx` + `frontend/src/components/workbench/NoticeStack.tsx` — 실행이 끝나 결과 국면으로 넘어가는 순간 무엇이 바뀌었는지 알리고 보던 대상(지목 Step·스크롤 위치)을 잃지 않는다 (FR-220)
- [X] T075 [US3] `frontend/tests/PhaseContext.test.tsx` 신설 — 왕복 전 구간 지목 유지 + 새로 고침 복원 10/10 (SC-005·SC-006)
- [X] T076 [US3] `frontend/tests/ScreenUrl.test.ts` 갱신 — 국면·stepId 왕복 변환

**Checkpoint**: 지목한 Step 을 다시 찾는 조작 0회

---

## Phase 6: User Story 4 - 대상 앱을 보는 자리가 하나다 (Priority: P3)

**Goal**: 좌측 영역의 위치·크기가 국면과 무관하게 같고 내용만 바뀐다

**Independent Test**: 네 국면을 차례로 열어 좌측 영역의 자리가 같고 내용만 바뀌는지 대조한다
(`quickstart.md` W-4)

> 결과 국면의 좌측 전환 자체는 이행 5(T049)에서 구조적으로 이루어진다. 이 단계는 그 영역의
> 남은 요구 — 빈 이유 구별 · 선택 조작 위치 · 비어 있는 국면 — 를 완성한다

- [X] T077 [US4] 빈 이유 4종 구별 in `frontend/src/components/workbench/TargetPane.tsx` — 아직 시작하지 않음 / 수집되지 않음 / 세션 유실 / 지원되지 않음 (FR-245 · 005 FR-173)
- [X] T078 [US4] 산출물 선택 조작을 좌측 영역 안에 배치하고 TRACE 를 비활성 + 이유로 유지 in `frontend/src/components/workbench/TargetPane.tsx` (FR-246 · DC-007)
- [X] T079 [US4] 편집 국면 좌측의 「브라우저 열어 Step nn 에서 멈추기」 배치 in `frontend/src/components/workbench/TargetPane.tsx`
- [X] T080 [US4] 국면 보조 영역이 빈 국면에서 자리를 차지하지 않되 다른 영역의 자리를 바꾸지 않음 in `frontend/src/components/workbench/Workbench.tsx` (FR-218e)
- [X] T081 [US4] `frontend/tests/TargetPane.test.tsx` 신설 — 네 내용이 같은 자리를 쓰고 빈 이유가 구별된다

**Checkpoint**: 좌측 영역이 한 자리다

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 기록을 남기고 회귀를 확인한다. **기록 없는 임의 결정 0건**이 목표다

- [X] T082 [P] `specs/007-unify-test-screens/design-conformance/undefined-states.md` 작성 — 007 이 정한 모든 미정의 상태와 **근거**. 최소 목록은 `contracts/design-conformance-007.md` §6
- [X] T083 [P] 대조 기록 기준값 채우기 in `specs/007-unify-test-screens/design-conformance/Workbench.md` — `scripts/design_baseline.py` 로 추출. **판정 칸은 비워 둔다 — 사람이 채운다**
- [X] T084 [P] `docs/DEVELOPMENT.md` 갱신 — 화면 구조 설명을 7국면 하나의 화면으로 고친다
- [X] T085 [P] `contracts/ui-contract.md` 최종화 — T037·T041 의 실측 대조 결과를 반영한 표가 정본임을 확인
- [X] T086 타입 검사 통과 — `cd frontend && npm run typecheck` (`frontend/tsconfig.json` 의 `noUncheckedIndexedAccess` 아래)
- [X] T087 전량 테스트 — `cd frontend && npm test` · `cd backend && bash scripts/test-backend.sh`. **삭제·건너뛰기로 통과시키지 않는다** (헌법 게이트 4)
- [X] T088 `quickstart.md` §1 자동 검사 4종 전부 통과 확인 — `ImplementationCount` · `StepRowLayout` · `WorkbenchShell` · `CapabilityCoverage`
- [X] T089 성능 확인 — Step 200개 목록에서 `frontend/tests/StepListPerformance.test.tsx` 기준을 낮추지 않고 통과
- [X] T090 `docs/PENDING-HUMAN-VERIFICATION.md` 최종 갱신 — 사람 판정 2건(artboard 승인 · 대조 판정)의 준비물 위치와 남은 판정 칸 수를 적는다
- [X] T091 `quickstart.md` §2 의 걷기 항목 W-1~W-6 을 실제로 걸어 `docs/ux/` 에 기록 (W-7 은 사람 판정 대기)

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

---

## Phase 8: Convergence

`/speckit-converge` 1회차가 찾은 잔여 작업이다. CRITICAL·HIGH 는 없다 — 명세가 요구한
기능은 전부 서 있고, 남은 것은 **기록이 실제와 어긋난 곳 하나**와 **세어 두기로 한 것을
아직 세지 않은 곳 넷**이다.

- [X] T092 대체 관계 기록을 실제 자리로 고친다 in `specs/007-unify-test-screens/design-conformance/replacement-map.md` §2 per FR-254b (contradicts) — 기록은 「RunnerPaused 편집 도구 격자·검증 추가 폼·순서 변경 패널·저장 영역 → ③ 좌 아래 국면 보조 영역」인데, 구현은 **조작 팔레트를 Step 패널 바닥(③ 우)** 에 뒀고 보조 영역에는 검증 추가 폼과 순서 변경 패널만 펼친다. 자리를 그렇게 정한 근거(확정 디자인 3종이 460px 패널 아래에 조작 블록을 갖는다)도 함께 적는다. **기록이 실제와 다르면 대조가 성립하지 않는다**
- [X] T093 SC-009 의 통합 후 값을 재어 기록 in `specs/007-unify-test-screens/design-conformance/baseline.md` per SC-009 (missing) — 기준선 §3 이 「전환 3회 + 재탐색 1회」와 판정 기준(3회 이하)을 적어 뒀는데 이후 값이 없다. 결과 확인 → 수정 → 재실행 → 결과 확인 한 바퀴를 `App.tsx` 의 국면 전환으로 세고, SC-005 의 재탐색 0회(걷기 W-3 에서 관측)와 함께 적는다
- [X] T094 뒤로 가기 회귀 검사 in `frontend/tests/ScreenUrl.test.ts` per FR-241 · 005 FR-167 (missing) — `popstate` 가 `src/hooks/useScreenUrl.ts` 에만 있고 검사가 없다. **변환만 재는 검사는 이 결함을 못 잡는다** — 005 N-01 이 정확히 「변환은 옳은데 첫 렌더의 화면이 틀린」 형태였다. 뒤로 가기가 앱 안의 이전 국면으로 돌아가고 `about:blank` 로 이탈하지 않는지 센다
- [X] T095 판정 모듈이 규칙만으로 이루어짐을 검사 in `frontend/tests/DeterministicPhase.test.ts` (신설) per FR-251 · Constitution II (missing) — `lib/phase.ts`·`lib/capabilities.ts`·`lib/actions.ts` 가 값 임포트를 갖지 않고(타입만) 언어모델·네트워크를 부르지 않는지 원문으로 센다. 지금 실제로 그러하나 **그 성질을 지키는 것이 없다** — 백엔드의 `lint-imports` 가 하는 일을 화면 쪽 판정 모듈에 대해 하는 것이다
- [X] T096 W-6 을 사람 판정 항목으로 등록 in `docs/PENDING-HUMAN-VERIFICATION.md` per quickstart W-6 · FR-253 (missing) — 걷기에서 **확인 불가(환경)** 로 남았다. 자격 증명이 없어 AI 작성 국면에 도달할 수 없었고, 제품이 누르기 전에 그 사실을 말하는 것(AP-003)까지가 관측의 전부다. 준비물(`AiFailureVisible.test.tsx` 가 다섯 세션 상태를 이미 센다)과 남은 것(실브라우저에서 실제 실패를 만들었을 때도 같은가)을 적는다

---

## Phase 9: Convergence (2회차)

1회차의 5건은 전부 닫혔다. 2회차가 찾은 것은 하나이며 **판정 주체**에 관한 것이다.

- [X] T097 SC-008 을 사람 재확인 항목으로 등록 in `docs/PENDING-HUMAN-VERIFICATION.md` per SC-008 (missing) — 걷기(`docs/ux/ux-walkthrough-007.md`)는 **구현자가** 걸었고 「지금 무엇을 할 수 있는지 몰랐다 / 화면이 바뀌어 보던 것을 잃었다 0건」도 구현자의 판정이다. 이 저장소의 규칙은 그것을 검증으로 세지 않는다 (`PENDING-HUMAN-VERIFICATION.md` 서문 · 002 T099 · 001 T156 이 같은 이유로 열려 있다). 005 T124(「상」 9건 재확인)와 같은 형태로 등록한다 — 무엇을 다시 걷는지, 판정 값이 무엇인지, 구현자의 관측이 무엇이었는지

---

# 2회차 개정 (2026-09-08) — 주 자리와 보조 자리가 뒤바뀐 것을 고친다

1회차 T001~T097 은 완료다. 아래는 2회차 개정(spec S-12~S-15 · FR-256~262 · US5·US6)의
작업이다. `plan.md` 「Phase 2b」가 정한 **두 묶음이며 순서를 바꾸지 않는다.**

## Phase 10: User Story 5 - 지금 하는 일이 큰 자리를 갖는다 (Priority: P1) 🎯 2회차 MVP

**Goal**: ③ 좌측 두 자리의 세로 비율을 국면이 정한다. 편집 국면에서 편집면이 남는 높이
전부를, 결과 국면에서 「왜 멈췄나」가 정해진 높이를 갖는다

**Independent Test**: 여덟 국면을 차례로 열어 ③ 좌측 두 자리의 높이를 재고, 그 국면의 주
작업이 들어간 자리가 다른 자리보다 크거나 같은지 대조한다 (`quickstart.md` W-8)

**⚠️ 이 묶음은 쪼개서 멈출 수 없다** (research R13). 중간에 멈추면 어떤 국면은 새 규칙,
어떤 국면은 옛 규칙이 되어 FR-256 이 성립하지 않는다. **T098~T108 이 한 커밋이다** —
T108(기존 테스트 갱신)이 빠지면 그 커밋은 깨진 테스트를 남긴 상태가 된다

### 규칙을 먼저 세운다

- [X] T098 [US5] 세로 배분 표 in `frontend/src/lib/layout.ts` (신설) — `SlotSize`(`fill` · `content` · `fixed`) · `VERTICAL_SPLIT: Record<Phase, VerticalSplit>` 여덟 국면. 값은 `ui-contract.md` §1-5 표 그대로. **`Record<Phase, …>` 이므로 국면을 더하면 컴파일러가 배분을 요구한다** — `PHASE_TABLE` 과 같은 규율 (research R9)
- [X] T099 [P] [US5] 배분 검사 in `frontend/tests/VerticalSplit.test.ts` (신설) per SC-010 · UC-100 — 넷을 센다: ① 여덟 국면 전부 채움 ② **한 국면에서 두 자리가 동시에 `fill` 이 아니고 동시에 `content` 도 아니다** ③ **`fill` 인 자리의 `kind` 가 그 국면이 선언한 작업 종류와 일치한다** — 「주 작업」을 검사가 알 방법이 필요하다. `PRIMARY_SLOT: Record<Phase, "target" | "work">` 를 `layout.ts` 에 함께 두고, `fill`(또는 국면이 `fixed` 를 쓰는 경우 더 큰 쪽)인 자리가 그것과 같은지 센다 ④ `TargetPane.tsx`·`WorkArea.tsx` 원문에 `flex: "1"`·`flex: 0 0 auto` 리터럴이 없다 (S-12 재발 방지)

### 타입과 이름을 고친다

- [X] T100 [US5] `PhaseAside` → `WorkAreaView` 개명 + `kind` 3종 추가 in `frontend/src/components/workbench/model.ts` per FR-218e-1 · data-model §2-3 — `WorkbenchModel.aside` → `.work`, `edit_summary` → `edit_fields`, 신설 `compose_form`(만들기) · `run_progress`(실행·녹화 42px 띠) · `failure_detail.attempts`(FR-262). **이름을 바꾸는 것이 이 작업의 목적이다** — 1회차 이름이 이 자리를 보조로 규정했고 그 규정이 편집 폼을 42px 띠에 넣는 판단으로 이어졌다 (S-12)
- [X] T101 [US5] `PhaseAside.tsx` → `WorkArea.tsx` 개명 in `frontend/src/components/workbench/` per FR-218e-1 — **`AlwaysVisibleFailure` 의 구조·인자·호출 위치를 손대지 않는다.** 국면·세션 상태를 인자로 받지 않는 성질이 001 R2 방지 장치의 전부다 (research R15). `AiFailureVisible.test.tsx` 통과를 유지한 채 개명한다

### 크기를 인자로 내린다

- [X] T102 [US5] `TargetPane` 이 크기를 인자로 받는다 in `frontend/src/components/workbench/TargetPane.tsx` per FR-256 — 지금 하드코딩된 `flex: "1"` 을 제거하고 `size: SlotSize` 를 받는다. **자기 크기를 모르게 만드는 것이 요점이다**
- [X] T103 [US5] `WorkArea` 가 크기를 인자로 받는다 in `frontend/src/components/workbench/WorkArea.tsx` per FR-256 — 지금 하드코딩된 `flex: 0 0 auto` · `minHeight: 42` 를 제거하고 `size: SlotSize` 를 받는다. `content` 일 때만 최소 42px 을 적용한다
- [X] T104 [US5] `Workbench` 가 배분을 국면으로 조회해 두 자리에 내려 준다 in `frontend/src/components/workbench/Workbench.tsx` per FR-218c · FR-256 · UC-100 — ③ 좌측이 **③-a 대상 앱 슬롯 + ③-b 국면 작업 영역 두 자리**임을 이 파일이 정한다 (FR-218c) — `VERTICAL_SPLIT[model.phase]` 하나만 읽는다. 표시 컴포넌트가 표를 직접 읽지 않는다

### 국면 어댑터를 새 자리로 옮긴다

- [X] T105 [US5] 편집 필드를 작업 영역으로 in `frontend/src/pages/EditView.tsx` per FR-257 · FR-261 — `work: { kind: "edit_fields", fields }` 가 남는 높이 전부를 갖고, `target: open_browser` 는 `fixed 118`. **브라우저 여는 조작은 그 자리 안에 유지한다** — 자리를 없애는 것과 줄이는 것은 다르다 (S-12)
- [X] T106 [US5] 시도한 locator 기록을 작업 영역으로 in `frontend/src/pages/ResultView.tsx` per FR-262 — `work: { kind: "failure_detail", attempts }`. 지금은 `StepDetail` 겹침을 열어야 보인다 (S-13). **겹침 상세의 표는 남긴다** — 그것은 지목한 Step 의 것이고 작업 영역의 것은 실패 Step 고정이다
- [X] ~~T107~~ **드롭 (전제 오류)** — 계획은 「실행·녹화의 42px 진행 띠가 `noticesExtra` 로 우회해 들어가 있으니 타입 안으로 들이자」였는데, 구현에서 대조하니 **그런 띠가 없다.** `noticesExtra` 가 나르는 것은 실시간 통로 끊김 배너이며 그것은 알림이고 알림 자리(국면 띠 아래)가 제 집이다. 진행은 `phaseBar.progressLabel`, 실행 속도는 `phaseActions` 에 이미 있다. 없는 것을 만들면 (가) 없던 요소가 생기고 (나) `run.pacing` 이 확립된 자리에서 옮겨져 FR-235 를 어긴다. 두 국면은 `work: null` 로 남고 판정 근거를 `model.ts` 에 적었다
- [X] ~~T107a~~ **표시가 거짓이었다 → T132 가 실제로 닫았다** — 파일을 만들지 않은 채 `[X]` 로 뒀고 converge 가 찾았다. 원문: 결과 국면 시도 기록 검사 in `frontend/tests/ResultAttemptsVisible.test.tsx` (신설) per SC-012 · FR-262 · quickstart §1-8 — 실패 결과로 `ResultView` 를 렌더하고 **겹침 상세를 열지 않은 상태에서** 시도한 locator 행이 보이는지 센다. 1회차에는 `StepDetail` 을 열어야 보였다 (S-13). **동작을 만드는 T106 만으로는 회귀를 막지 못한다** — 다음 라운드에 누가 다시 겹침으로 옮겨도 아무것도 세지 않는다
- [X] T108 [US5] 개명·이동으로 깨지는 기존 테스트 갱신 in `frontend/tests/` — 헌법 게이트 4: **삭제·건너뛰기 금지, 갱신으로만 통과시킨다.** 검증하는 행동이 바뀌면 회귀다

**Checkpoint**: `VerticalSplit` 통과 · `AiFailureVisible` 통과 유지 · 편집 국면에서 아래가
위보다 크다 · 결과 국면에서 겹침을 열지 않고 시도 기록이 보인다

---

## Phase 11: User Story 6 - 만들기부터 같은 화면이다 (Priority: P2)

**Goal**: 만들기가 여덟째 국면이 된다. 한 번의 「테스트를 만든다」 안에서 껍데기가 바뀌는
횟수가 0이 된다

**Independent Test**: 목록에서 「새 테스트」로 들어가 방법을 고르고 시작할 때까지 껍데기
(기준 폭·헤더 구성·영역 배치)가 바뀌는 횟수를 센다 — 0회여야 한다 (`quickstart.md` W-9)

**⚠️ Phase 10 뒤에 온다** (research R13). 만들기 국면의 배분(③-a `fixed 118` / ③-b `fill`)이
Phase 10 이 만든 규칙을 쓴다. 먼저 하면 만들기만 규칙 없이 서고 Phase 10 이 다시 고친다

**⚠️ `CreateTest`·`AiCompose` 삭제가 이 묶음에 포함된다.** 남기면 껍데기가 3벌인 상태가
유지된다 (1회차 R7 과 같은 규율)

### 국면과 조작을 더한다

- [X] T109 [US6] `Phase` 에 `composing` 추가 in `frontend/src/lib/phase.ts` per FR-217b · research R10 — `PHASES` 에도 넣는다. **`phaseOfSession` 은 손대지 않는다** — 세션이 생기는 순간 이미 다른 국면이다. `SESSION_PHASES` 에 넣지 않는다
- [X] T110 [US6] `record.start` 조작 추가 in `frontend/src/lib/actions.ts` per FR-258b · UC-401 — `ACTION_IDS` · `ACTION_LABEL` 「녹화 시작」. 33 → 34. **이것은 `step.recordStart`(열린 세션 안에서 기록을 켠다)와 다른 조작이다** — 세션 자체를 녹화 모드로 만든다. 1회차가 만들기를 범위에서 빼 목록에 오르지 않았다 (research R11)
- [X] T111 [US6] CRE 열 34칸 + 조건 C14 in `frontend/src/lib/capabilities.ts` per ui-contract §3 · §3-5 — 표 그대로. C14(지시문이 비어 있지 않다)는 지금 `AiCompose.tsx:144` 의 `disabled` 가 하던 판정을 표로 옮긴 것이다. **`record.start`·`ai.start` 를 O2(`busy`) 덮어쓰기 대상에 넣는다** — 만들기 국면에서도 연타를 막는다 (005 U-06)
- [X] T112 [P] [US6] C14 이유와 만들기 국면 문구 in `frontend/src/lib/wording.ts` per ui-contract §5 — 「지시문을 쓰면 시작할 수 있습니다」 · 만들기의 `test.rename` 이유 「저장할 때 이름을 정합니다」. 컴포넌트에 문자열 리터럴을 두지 않는다

### 국면 어댑터를 만들고 옛 화면을 없앤다

- [X] T113 [US6] 만들기 국면 어댑터 in `frontend/src/pages/ComposeView.tsx` (신설) per FR-258 · FR-258a — `target: { kind: "empty", reason: "not_started" }` · `work: { kind: "compose_form" }` · `steps: []` · `testId: null`. 항목은 **시작 URL · 방법 2택 · 지시문 · 취소뿐이다.** 테스트 이름 필드와 「빈 테스트」를 만들지 않는다 — 제품에 없는 조작이며 범위 위반이다 (research R11)
- [X] T114 [US6] Step 목록이 0개일 때 자리를 지킨다 in `frontend/src/pages/ComposeView.tsx` per FR-260 · S-15 — 기존 `stepEmptyNotice` 를 쓴다. 「아직 Step 이 없습니다 · 시작하면 여기 쌓입니다」. **목록을 그리지 않는 선택을 하지 않는다** — 조작이 어디에 쌓이는지 시작하기 전에 보여야 한다
- [X] T115 [US6] `create`·`ai-compose` 화면을 `compose` 하나로 in `frontend/src/App.tsx` per FR-259 — `sessions.create` 호출은 **기존 경로를 그대로** 쓴다. 경로를 새로 만들지 않는다 (FR-248 · 005 U-01·U-06). 화면을 갈아타지 않고 국면만 바뀐다
- [X] T116 [US6] 주소에 `compose` 추가 + 옛 이름 정규화 in `frontend/src/hooks/useScreenUrl.ts` per FR-240 · research R12 — `?screen=create` · `?screen=ai-compose` 로 들어온 주소를 `compose` 로 떨어뜨린다. **열어 둔 탭을 끊지 않는다.** 시작 주소·지시문·고른 방법은 주소에 싣지 않는다
- [X] T117 [US6] `pages/CreateTest.tsx` · `pages/AiCompose.tsx` 삭제 per FR-259 · SC-011 — 참조 0건 확인. **이 삭제가 이 묶음의 완료 조건이다**

### 센다

- [X] T118 [US6] 껍데기 개수 검사 갱신 in `frontend/tests/ImplementationCount.test.tsx` per SC-011 — 한 테스트를 다루는 국면에서 `Artboard` 를 직접 부르는 페이지가 0개다. `CreateTest.tsx`·`AiCompose.tsx` 부재를 센다
- [X] T119 [US6] 권한 커버리지 검사 갱신 in `frontend/tests/CapabilityCoverage.test.ts` per SC-007 · FR-247 — 8국면 × 34조작. 모든 `–` 이 근거(N1·N2·N3)를 갖고 모든 `○` 이 이유를 갖는지
- [X] T120 [P] [US6] 만들기 국면 검사 in `frontend/tests/ComposePhase.test.tsx` (신설) per FR-258·FR-259·FR-260 — 껍데기 구성 · Step 목록 0개 자리 · 방법 2택 · C14 비활성 + 이유 · **테스트 이름 필드가 없음**(FR-258a 회귀 방지)
- [X] T121 [US6] 옛 `CreateTest`·`AiCompose` 테스트를 `ComposeView` 대상으로 갱신 in `frontend/tests/` — 헌법 게이트 4: **삭제하지 않는다.** 검증하던 행동(시작 URL 입력 · 방법 고르기 · 지시문 · 취소 · 세션 생성)이 새 자리에서도 성립하는지로 옮긴다

**Checkpoint**: 두 파일 없음 · 참조 0건 · 옛 주소 둘이 만들기 국면으로 열림 · `ComposePhase`
통과 · 껍데기 개수 0

---

## Phase 12: 기록과 대조 (2회차)

**⚠️ 기록이 실제와 다르면 대조가 성립하지 않는다** (1회차 T092 가 같은 이유로 열렸다)

- [X] T122 [P] 대체 관계 기록 in `specs/007-unify-test-screens/design-conformance/replacement-map.md` per FR-254b · FR-254d — `Workbench.dc.html`(초안) + `CreateTest.dc.html`(**확정 디자인**) → `docs/design/007-rework/`. `CreateTest.dc.html` 의 모든 요소(시작 URL 필드 · 방법 2택의 설명 문구 · 취소 · 1000px 셸)가 어디로 갔는지 판정 넷(`그대로`/`이동`/`분리`/`옮기지 않음`)으로 적는다. **`옮기지 않음` 은 이유가 필수다**
- [X] T123 [P] 2회차 대조 기록 in `specs/007-unify-test-screens/design-conformance/Workbench.md` per DC-012 · FR-254c — B1~B10 의 기준값과 구현값. **첫 줄의 「승인 대기 중이며 대조 기준으로 확정되지 않았다」를 유지한다.** 만들기 국면은 승인 전까지 `CreateTest.dc.html` 이 기준임을 명시한다 (research R14)
- [X] T124 [P] 미정의 상태 갱신 in `specs/007-unify-test-screens/design-conformance/undefined-states.md` per DC-009 — 1회차의 `AiCompose` 항목을 **해소로 닫는다**(만들기 국면이 되었다). 2회차가 만든 미정의 상태를 등록한다
- [X] T125 [P] 캔버스 갱신 in `docs/design/canvas.json` per FR-254b · FR-254d — `Workbench.dc.html` 항목에 `007-rework` 로 대체됨을 표시. `CreateTest.dc.html` 의 `replaces` 관계 기록
- [X] T125a [P] 구조 문서 개명 반영 in `docs/DEVELOPMENT.md` per FR-218e-1 — `PhaseAside.tsx 국면 보조 영역` → `WorkArea.tsx 국면 작업 영역`. **FR-218e-1 은 계약·코드 식별자·대조 기록이 함께 바뀌어야 한다고 요구한다** — 리포지토리 구조 문서가 옛 이름을 적고 있으면 다음 사람이 그 이름으로 읽는다
- [X] T126 사람 판정 항목 등록 in `docs/PENDING-HUMAN-VERIFICATION.md` per FR-254c — B1~B10 승인 요청 · **`CreateTest.dc.html`(확정 디자인) 대체 승인** · W-8·W-9 걷기의 사람 재확인. 1회차 T096·T097 과 같은 형식

---

## Phase 13: 묶음 B 가 만든 회귀 (구현 중 발견)

전체 검증에서 **백엔드 테스트 1건이 실패**했다. 2회차는 백엔드 코드를 바꾸지 않았으나,
이상 조작 시나리오의 **실행 수단이 사라진 화면을 조작**하고 있었다.

- [X] T127 `AS-011` 실행 수단을 만들기 국면으로 이관 in `backend/tests/abnormal/drivers/ui_drivers.py` per 003 RG-105·RG-106 · 007 FR-259 — 수단이 「테스트 만들기」 화면에서 **「지시문 쓰기」 버튼**을 눌러 `AiCompose` 로 넘어가는 것을 전제했다. 그 이동이 사라졌으므로 (FR-259) `Locator.wait_for` 가 8초 뒤 시간을 넘겼다. 「AI로 만들기」를 고르고 **같은 화면에서** 「AI 시작」이 잠겼는지·이유가 있는지·시작 URL 이 남는지를 재도록 고쳤다. **건너뛰거나 지우지 않았다** (헌법 게이트 4)
- [X] T128 `AS-011` 시나리오 기록 갱신 in `specs/003-error-path-hardening/contracts/abnormal-scenarios.json` per 003 RG-104 — `target` 을 `AiCompose` → `ComposeView` 로. **1회차의 우회를 `note` 에서 지웠다**: 「자격 증명이 없으면 지시문 화면에 닿기 전에 막힌다」는 별도 화면이 있을 때의 사정이었고, 이제 지시문 자리가 같은 화면에 있으므로 **목록에 적힌 그대로**(지시문을 비운 채 요청) 잴 수 있다

### 이 회귀가 알려 준 것

**프런트엔드 검사 635개가 전부 통과한 상태에서 백엔드 테스트가 잡았다.** 실브라우저로
제품 화면을 여는 검사(003 RG-105)만이 「그 버튼이 실제로 없다」를 알 수 있다 — 프런트엔드
단위 검사는 자기가 그린 DOM 만 보므로, 다른 곳에 있는 조작 대본이 깨진 것을 볼 수 없다.

**묶음 B 의 완료 판정에 이것이 빠져 있었다.** `plan.md` Phase 2b 의 판정은 「두 파일 없음 ·
참조 0건 · 옛 주소가 열림 · 껍데기 개수」였고, `참조 0건` 을 `frontend/src` 안에서만 셌다.
화면을 지우는 묶음의 판정에는 **그 화면을 조작하는 대본**도 들어가야 한다.

---

## 2회차 의존 관계

```
Phase 10 (묶음 A · 세로 배분)  ──▶  Phase 11 (묶음 B · 만들기 흡수)  ──▶  Phase 12 (기록)
   T098~T108 한 커밋                    T109~T121 한 커밋                  T122~T126
```

- **Phase 10 안에서**: T098(표) → T099(검사) → T100·T101(타입·개명) → T102·T103(크기 인자)
  → T104(전달) → T105~T107(어댑터) → T108(기존 테스트). T099 는 `[P]`
- **Phase 11 안에서**: T109·T110 → T111 → T113·T114 → T115·T116 → T117(삭제) → T118~T121.
  T112·T120 은 `[P]`
- **Phase 12**: T122~T125a 전부 `[P]`. T126 은 나머지가 끝난 뒤

## 2회차에서 하지 말아야 할 것

- **묶음 A 를 쪼개서 커밋** — 어떤 국면은 새 규칙, 어떤 국면은 옛 규칙이 된다
- **`CreateTest`·`AiCompose` 를 남긴 채 `ComposeView` 추가** — 껍데기가 3벌에서 4벌이 된다
- **만들기 국면에 테스트 이름 필드나 「빈 테스트」 추가** — 제품에 없는 조작이다 (FR-258a).
  설계 초안이 이 둘을 그렸고 Phase 0 대조가 걸렀다
- **최소 기준 폭 변경** — 2회차가 고치는 것은 세로 배분이다 (FR-218 유지)
- **`AlwaysVisibleFailure` 의 구조 변경** — 개명은 파일명·타입명까지다 (001 R2)
- **백엔드 변경** — 1회차와 같다. 필요해지면 설계가 틀렸다는 신호다
- **깨진 테스트를 삭제·건너뛰기로 통과** — 헌법 게이트 4

## 2회차 작업 수

34개. Phase 10 이 12 · Phase 11 이 13 · Phase 12 가 7 · Phase 13 이 2.
누적 T001~T128 (T107a·T125a 포함).

`analyze` 가 찾아 더한 셋: T107a(SC-012 를 세는 작업이 없었다) · T125a(구조 문서가 옛
이름을 적는다) · T099 ③ 의 조작적 정의(「주 작업」을 검사가 알 방법이 없었다).

---

## Phase 14: Convergence (2회차)

`/speckit-converge` 가 찾은 잔여 6건이다. CRITICAL 은 없다. **HIGH 4건 중 셋이 한
뿌리**다 — 구현 중에 권한표를 고쳐야 할 것을 코드에서만 고쳤고, 그것이 UC-000(표가
정본)이 금지하는 형태다.

- [X] T129 조건 C15 를 계약 표에 올린다 in `specs/007-unify-test-screens/contracts/ui-contract.md` §3-5 per UC-000 (contradicts) — `capabilities.ts` 에 `C15`(만드는 방법으로 AI 를 골랐다)가 있는데 계약 §3-5 의 런타임 조건 표에 없다. **화면이 표에 없는 조건으로 판정하고 있다.** 거짓일 때의 이유(「「AI로 만들기」를 고르면 쓸 수 있습니다」)와 해소 방법(`ai.compose`)을 함께 적는다
- [X] T130 CRE 열의 `ai.compose` 를 `◐ C15` 로 고친다 in `specs/007-unify-test-screens/contracts/ui-contract.md` §3-4 per UC-000 (contradicts) — 표는 `●` 인데 코드는 `cond("C15")` 다. 지시문 자리는 방법을 고르기 전에도 있어야 하므로(FR-234) 조건이 맞고, **표를 코드에 맞춘다** — 이 경우는 UC-401 의 「표가 틀렸다」에 해당한다 (현재 쓸 수 있는 조작을 표가 잘못 적었다)
- [X] T131 CRE 열의 `step.update`·`step.markSensitive`·`step.repick` 을 `– N2` 로 고친다 in `specs/007-unify-test-screens/contracts/ui-contract.md` §3-3 per UC-000 · §4-2 (contradicts) — 표는 `○` 인데 코드는 `na("N2")` 다. **자리가 Step 상세이고 Step 이 0개면 상세가 열릴 수 없다.** §3-4 아래의 「갈릴 수 있는 다섯 칸」 표에 그 근거를 적는다 — `step.select`·`delete`·`reorder` 는 목록과 팔레트가 자리이므로 `○` 로 남고, 이 셋만 `–` 다
- [X] T132 결과 국면 시도 기록 검사를 만든다 in `frontend/tests/ResultAttemptsVisible.test.tsx` (신설) per SC-012 · FR-262 · quickstart §1-8 (missing) — **T107a 를 `[X]` 로 표시했으나 파일을 만들지 않았다.** 거짓 완료 표시이며 가장 나쁜 종류다. 실패 결과로 `ResultView` 를 렌더하고 ③-b 의 배분이 `fixed 424` 인지, 겹침 상세를 열지 않은 상태에서 실패 사유와 시도한 locator 행이 보이는지 센다. **이 검사는 「보이는가」가 아니라 「자리가 충분한가」를 센다** — 1회차에도 표는 그려졌고 `maxHeight: 45%` 에 갇혔던 것이 결함이었다 (S-13 정정)
- [X] T133 옛 주소 정규화 검사를 더한다 in `frontend/tests/ScreenUrl.test.ts` per FR-240 · research R12 · quickstart W-9 ⑧ (missing) — `?screen=create` · `?screen=ai-compose` 가 `compose` 국면으로 열리는지 세는 것이 없다. **열어 둔 탭을 끊지 않는 것이 이 정규화의 목적**인데 그것을 지키는 것이 없다. `locationToSearch` 왕복도 함께 센다
- [X] T134 죽은 옛 이름을 정리한다 in `frontend/src/components/workbench/model.ts` per FR-218e-1 (unrequested) — `export type PhaseAside = WorkAreaView` 별칭을 **쓰는 곳이 0건**이다. 이행 중 호환을 위해 뒀으나 이행이 끝났다. 개명을 요구한 조항(FR-218e-1)에 죽은 옛 이름이 남아 있으면 다음 사람이 그것을 쓴다 — 제거한다

---

## Phase 15: Convergence (3회차)

2회차의 6건은 전부 닫혔다. 3회차는 **계약 표 272칸(34조작 × 8국면)을 코드와 기계적으로
대조**했고, 그 과정에서 2회차가 만든 표기 불일치 하나를 찾아 되돌렸다.

- [X] T135 CRE 열의 `– Nn` 인라인 근거를 `–` 로 되돌린다 in `specs/007-unify-test-screens/contracts/ui-contract.md` §3 per UC-000 (contradicts) — 2회차가 CRE 열에만 근거를 셀 안에 적어 **한 열만 표기가 달랐다** (21칸). `–` 의 근거는 §4-2 의 닫힌 목록과 코드가 갖고 `CapabilityCoverage.test.ts` 가 세는 것이 1회차부터의 관례다. 열마다 표기가 다르면 근거 없는 `–` 를 찾을 때 무엇을 봐야 하는지 흐려진다. §3 기호표에 관례를 명시해 다시 붙지 않게 했고, 갈릴 수 있는 칸의 근거는 표 아래 산문(§3-4 끝)에 남긴다
- [X] T136 `save` 셀의 키 표기를 파일 스타일에 맞춘다 in `frontend/src/lib/capabilities.ts` per 일관성 (contradicts) — 다른 7국면은 `save:` 인데 만들기 국면만 `"save":` 였다. 기능 차이는 없지만 **표를 기계로 대조할 때 그 한 칸이 빠져** 265/272 만 검증됐다

### 3회차 대조 결과

| 대상 | 결과 |
|---|---|
| 계약 §3 권한표 ↔ `capabilities.ts` | **272 / 272 일치** (34조작 × 8국면) |
| 런타임 조건 C1~C15 | 코드·계약 양쪽에 15건 |
| 미완료 작업 | 0 |
| 코드에 남은 옛 이름(`PhaseAside`·`edit_summary`·`.aside`) | 실체 0건 — 남은 것은 전부 내력을 적은 주석 |
| `frontend` | `tsc --noEmit` 통과 · vitest **647 passed** (50 files) |
| `backend` | pytest **1428 passed** · timing **42 passed** (`-n 0`) |

### 이 회차가 알려 준 것

**표를 기계로 대조하는 것이 실제로 값이 있었다.** 2회차 수렴은 사람이 읽어 어긋남 3건을
찾았고, 3회차는 272칸을 대조해 **표기 불일치와 파싱 사각 하나**를 더 찾았다. 다만 그
대조는 이 회차에 임시로 쓴 스크립트이며 리포지토리에 남지 않는다 — 계약 문서를 기계가
읽는 형식으로 옮기는 것은 이 기능의 범위를 넘는다 (표를 코드에서 생성하거나 그 반대로
하는 일이며, UC-000 이 정한 「표가 정본」의 뜻을 바꾼다).

### 이 회차가 알려 준 것 (2회차 기록)

**표와 코드가 어긋나는 것을 세는 검사가 없다.** `CapabilityCoverage` 는 코드의 표를
자기 자신과 대조하므로(34개가 다 있나 · `–` 이 근거를 갖나) **계약 문서와의 어긋남은
보지 못한다.** F2~F4 셋이 그 형태였고, 구현 중 검사가 전부 통과하는 동안 남아 있었다.

계약 문서를 기계가 읽을 수 있게 만드는 것은 이 라운드의 범위를 넘는다. 대신 **UC-401 의
절차를 지키는 것**이 유일한 방어이므로, 표를 고칠 때 코드와 문서를 같은 커밋에 담는
규율을 `plan.md` 의 이행 판정에 남긴다 (T129~T131 이 그 자리다).
