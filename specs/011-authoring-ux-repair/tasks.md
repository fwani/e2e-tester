---

description: "작성 화면의 저장·선택·삭제·기록을 실사용에 맞춘다 — 작업 목록"
---

# Tasks: 작성 화면의 저장·선택·삭제·기록을 실사용에 맞춘다

**Input**: Design documents from `specs/011-authoring-ux-repair/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) ·
[data-model.md](data-model.md) · [contracts/](contracts/)

**Tests**: 포함한다. 선택이 아니라 **헌법 §품질 게이트 3 의 요구**다 — 「제품은 테스트 도구이며,
자기 테스트 없이 내보내는 것은 허용되지 않는다」. 사용자 화면 흐름마다 최소 하나의 종단 검증이
필요하다.

**Organization**: 사용자 이야기별로 묶어 각각 독립적으로 붙이고 확인할 수 있게 한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 완료되지 않은 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 이야기인가 (US1~US5)
- 파일 경로를 정확히 적는다

## Path Conventions

web application — `backend/src/itb/`, `backend/tests/`, `frontend/src/`, `frontend/tests/`

## 이 목록의 성격

011 은 **정본을 고치고 지나간다.** 그래서 「기존 검증 개정」이 각 이야기 안에 작업으로 들어 있다.
그것을 마지막에 몰면 어느 변경이 어느 검사를 깨뜨렸는지 가릴 수 없고, 지우거나 건너뛰면 헌법
§품질 게이트 4 위반이다. 개정 대상 목록은 [research.md](research.md) R8 에 있다.

---

## Phase 1: Setup

**Purpose**: 이 기능은 새 프로젝트·새 의존성을 만들지 않는다. 설치는 기존 절차 그대로다.

- [X] T001 기존 개발 환경을 확인한다 — `cd backend && uv sync` · `cd frontend && npm install` 후 `cd backend && uv run pytest -m "not browser" -q` 와 `cd frontend && npx vitest run` 이 **지금** 통과하는지 본다 (011 이 깨뜨린 것과 이미 깨져 있던 것을 가르는 기준선)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 조작 정본 3개(`actions`·`capabilities`·`wording`)와 화면 모델. **표를 먼저 고친다** —
나중에 고치면 표시 컴포넌트가 「표에 없는 조작」을 그리게 되고, 그 상태로는 `CapabilityUI` 검사가
무엇을 세야 할지 모른다 (plan 「구현 순서와 그 이유」 1).

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 사용자 이야기도 시작할 수 없다.

- [X] T002 [P] 조작 식별자 4개를 더한다 — `frontend/src/lib/actions.ts` 에 `step.toggleDeleteTarget`·`step.selectAllDeleteTargets`·`step.deleteSelected`·`step.deleteAfter` 를 `STEP_ACTIONS` 에 넣고 `ACTION_GROUP` 매핑이 자동으로 따라오는지 확인한다 (data-model §3-3)
- [X] T003 [P] 문구를 더한다 — `frontend/src/lib/wording.ts` 에 새 조작 4개의 `ACTION_LABEL`, 복수 삭제 확인 문구(개수 + 범위, UC-011-18), 「마지막 Step 입니다」(UC-011-19), 스크린샷 없음 사유 4종(UC-011-21), 고른 개수 표시(UC-011-17)
- [X] T004 권한표를 채운다 — `frontend/src/lib/capabilities.ts` 의 `PHASE_TABLE` 열 국면 전부에 새 조작 4개 값을 넣고(`Record<Phase, …>` 가 컴파일 시점에 요구한다), `editing` 행의 `step.recordStart`·`step.addNaturalLanguage` 를 `off("NEEDS_BROWSER", …)` → `ON` 으로 바꾼다 (research R7 · data-model §3-5) — T002·T003 의뢰
- [X] T005 [P] 화면 모델을 넓힌다 — `frontend/src/components/workbench/model.ts` 에 `WorkbenchStep.isDeleteTarget`·`screenshotUrl`·`screenshotNote` 와 `WorkbenchModel.deleteSelection: string[]` 을 더한다. `focusedStepId` 는 **그대로 둔다** (data-model §3-1·3-2)
- [X] T006 007 계약의 조작의 집 표를 고친다 — `specs/007-unify-test-screens/contracts/ui-contract.md` §4-1 에서 `save`·`edits.revert`·`test.rename` 을 국면 띠로 옮기고, 새 조작 4개의 집을 적고, 011 계약(`specs/011-authoring-ux-repair/contracts/ui-contract.md`)을 참조로 건다
- [X] T007 조작 커버리지 검사를 갱신한다 — `frontend/tests/CapabilityCoverage.test.ts` 가 새 조작 4개와 `editing` 두 셀의 변경을 반영하게 고친다 (T004 의뢰)

**Checkpoint**: 정본이 새 계약을 말한다. 이제 사용자 이야기를 붙일 수 있다.

---

## Phase 3: User Story 1 - 저장이 눈에 보이는 자리에 있고 이름을 두 번 묻지 않는다 (Priority: P1) 🎯 MVP

**Goal**: 저장·되돌리기·이름 변경의 집을 국면 띠로 옮기고, 이름이 이미 있는 테스트에는 이름을
다시 묻지 않는다.

**Independent Test**: 새 테스트를 녹화해 저장하고(이름 1회), 그 테스트를 다시 열어 Step 하나를
고쳐 저장한다(이름 0회). 저장 조작이 스크롤 없이 보인다. → [quickstart.md](quickstart.md) §2 US1

### Tests for User Story 1

> 먼저 쓰고, **실패하는 것을 확인한 뒤** 구현한다.

- [X] T008 [P] [US1] 저장 자리 검증 — `frontend/tests/SavePlacement.test.tsx`: `data-action="save"`·`edits.revert`·`test.rename` 요소의 조상에 `data-workbench-phase-bar` 가 있고 Step 패널 안에는 없다 (UC-011-1). 이름을 표시하는 요소와 고치는 요소가 하나다 (UC-011-2)
- [X] T009 [P] [US1] 이름 요구 조건 검증 — `frontend/tests/SaveNamePrompt.test.tsx`: `test_id` 유무 × (저장 라벨 · 이름칸 유무) 조합표 (UC-011-4), 나가기·다시 실행 확인의 이름칸 조건부 (UC-011-5), 빈 이름 저장 거절과 그 자리의 사유 (UC-011-6)

### Implementation for User Story 1

- [X] T010 [US1] 국면 띠에 저장 묶음을 만든다 — `frontend/src/components/workbench/PhaseBar.tsx`: 기존 테스트 이름 표시를 **그 자리에서 고칠 수 있는 형태**로 바꾸고(새 칸을 더하지 않는다), 오른쪽 조작 자리에 저장·되돌리기가 들어갈 수 있게 한다. 조작 묶음과 이름칸 모두 `flex: 0 1 auto`·`minWidth: 0` 로 줄어들 수 있어야 한다 (UC-011-3)
- [X] T011 [US1] 팔레트에서 저장 블록과 이름 칸을 뺀다 — `frontend/src/components/workbench/ActionPalette.tsx`: `save`·`edits.revert`·`test.rename` 제거. **`test.setStartUrl`·`ai.compose` 는 남긴다** (research R1). `PALETTE_ACTIONS` 와 props 를 그에 맞춘다
- [X] T012 [US1] 배선 — `frontend/src/components/workbench/Workbench.tsx`: 어댑터가 국면 띠에 내려주는 `phaseActions` 에 저장 묶음이 들어갈 수 있게 하고, 이름 값·변경 콜백을 `PhaseBar` 로 넘긴다
- [X] T013 [US1] 저장 판정식을 고친다 — `frontend/src/pages/SessionScreen.tsx`: `sessionSaveLabel(view.saved_at != null)` → **`view.test_id != null`** 기준으로. `saveCapability` 의 「이름이 비었다」 좁히기도 `test_id === null` 일 때만 걸리게 한다 (UC-011-4 · research R2)
- [X] T014 [US1] 확인 대화상자의 이름칸을 조건부로 만든다 — `frontend/src/pages/SessionScreen.tsx` 의 `RerunConfirm`·`LeaveConfirm`: `test_id === null` 일 때만 `rerun-save-name`·`leave-save-name` 을 그린다. 이름이 있으면 「저장하고 …」 버튼이 이름 없이 활성이다 (UC-011-5)
- [X] T015 [US1] 편집 국면의 저장을 국면 띠로 옮긴다 — `frontend/src/pages/EditView.tsx`: `saveEditsLabel` 을 쓰는 저장·`edits.revert` 를 `phaseActions` 로 보내고 팔레트에서 뺀다. 이름은 국면 띠의 `test.name` 인라인 편집이 받고 `set_name` 연산으로 이어진다
- [X] T016 [US1] 기존 검증을 개정한다 — `frontend/tests/CapabilityUI.test.tsx`(자리 이동), `frontend/tests/PhaseBarWidth.test.tsx`(띠에 조작·입력칸이 늘었다), `frontend/tests/SaveFeedback.test.tsx`(판정식 변경). 기대값을 새 계약에 맞춰 고친다 — 지우거나 건너뛰지 않는다

**Checkpoint**: US1 이 독립적으로 동작한다. 저장이 국면 띠에 있고 이름을 두 번 묻지 않는다.

---

## Phase 4: User Story 2 - 어느 Step 을 보고 있는지 화면이 분명히 말한다 (Priority: P1)

**Goal**: Step 상세를 목록 왼쪽 겹침으로 옮기고, 한 행이 다투던 세 상태를 네 자리로 나눈다.

**Independent Test**: Step 10개 이상인 테스트에서 행을 차례로 고른다. 상세가 열려도 고른 행이
보이고, 통과·일시정지 행에서 결말·일시정지와 선택이 **함께** 보인다.
→ [quickstart.md](quickstart.md) §2 US2

### Tests for User Story 2

- [X] T017 [P] [US2] 상세 자리 검증 — `frontend/tests/DetailPlacement.test.tsx`: 열 국면 전부에서 상세의 자리가 같고(UC-011-7), Step 목록이 가려지지 않으며, 상세를 열고 닫아도 대상 앱 영역의 폭이 변하지 않는다(UC-011-8). 닫는 조작이 상세 안에 있다(UC-011-10)
- [X] T018 [P] [US2] 네 상태 검증 — `frontend/tests/StepRowStates.test.tsx`: 결말 × 일시정지 × 지목 × 삭제 대상의 **성립 가능한 모든 조합**에서 넷의 표시가 동시에 존재한다 (UC-011-11). 지목이 결말을 대체하지 않고, 일시정지가 지목을 대체하지 않는다
- [X] T019 [P] [US2] 입력 차단 검증 — `frontend/tests/DetailBlocksMirrorInput.test.tsx`: 상세가 열린 동안 상세가 덮은 영역의 포인터·키 입력이 미러 조작 채널로 나가지 않는다 (UC-011-9)

### Implementation for User Story 2

- [X] T020 [US2] 겹침 자리를 오른쪽 → 왼쪽으로 옮긴다 — `frontend/src/components/workbench/Workbench.tsx`: 상세 640px 의 **오른쪽 가장자리가 Step 패널의 왼쪽 가장자리에 붙는다.** `lib/layout.ts` 는 손대지 않는다 — 이 변경은 가로에만 걸린다 (UC-011-7)
- [X] T021 [US2] 상세가 덮은 영역의 입력을 막는다 — `frontend/src/components/workbench/Workbench.tsx` (또는 `StepDetail.tsx` 의 컨테이너): 010 의 미러 조작이 그 아래에 있으므로 통과시켜서는 안 된다 (UC-011-9)
- [X] T022 [US2] 행의 네 상태를 나눈다 — `frontend/src/components/workbench/StepList.tsx` 의 `StepRow`: `className={paused ? … : selected ? … : OUTCOME_MARK[…]}` 의 **배타 삼항을 없애고** 결말(왼쪽 3px + 결말 칸)·일시정지(`data-paused-here`)·지목(행 배경 + `aria-current="true"`)을 각자 자리로 보낸다. 삭제 대상 칸은 US4 가 붙인다 (UC-011-11)
- [X] T023 [US2] 지목 표시의 형태를 정본에서 가져온다 — `frontend/src/theme/tokens.css`(또는 `theme/tone.ts`): 지목 표시를 위한 **새 색을 만들지 않는다.** 008 정본의 기존 토큰 조합으로 만들고, 어느 토큰을 쓰는지 근거를 주석으로 남긴다
- [X] T024 [US2] 상세 안에 닫는 조작을 둔다 — `frontend/src/components/workbench/StepDetail.tsx`: 모든 국면에서 같은 자리 (UC-011-10)
- [X] T025 [US2] 기존 검증을 개정한다 — `frontend/tests/VisualLanguage.test.tsx`·`frontend/tests/CanonMatchesDesign.test.ts`(새 표시가 정본 토큰을 쓴다), `frontend/tests/StepRowLayout.test.tsx`(상태 축이 늘었다)

**Checkpoint**: US1·US2 가 각각 독립적으로 동작한다. 네 번째 축(삭제 대상)의 자리가 열려 있다.

---

## Phase 5: User Story 4 - 여러 Step 을 한 번에 지우고, 새로 녹화한 뒤의 것을 정리한다 (Priority: P2)

**Goal**: 행에 체크 칸을 붙여 삭제 대상을 지목과 분리하고, 고른 것과 「이 뒤 전부」를 원자적으로
지운다.

> **US2 뒤에 온다**: 체크 칸이 US2 가 만든 네 번째 축 위에 올라간다 (plan 「구현 순서와 그 이유」).
> P2 두 이야기 중 이것을 먼저 두는 이유는 그것이고, US3 와는 서로 의존하지 않는다.

**Independent Test**: Step 15개 테스트에서 임의의 세 행을 체크해 한 번에 지우고, 5번째를 지목해
「이 뒤 전부」로 10개를 지운다. 체크한 상태에서 행 본문을 눌러도 체크가 유지된다.
→ [quickstart.md](quickstart.md) §2 US4

### Tests for User Story 4

- [X] T026 [P] [US4] 배치 삭제 계약 검증 — `backend/tests/contract/test_step_batch_delete.py`: `POST /api/sessions/{id}/steps:delete` 의 요청 형(`min_length=1`·`extra="forbid"`), 응답 `StepsResponse`, 오류표 4종 (api-contract §1)
- [X] T027 [P] [US4] 원자성 검증 — `backend/tests/integration/test_batch_delete_atomicity.py`: 없는 `step_id` 를 하나 섞으면 `404` 이고 **아무것도 지워지지 않는다**. 중복 id 는 `400`. 부분 적용이 남지 않는다 (FR-388)
- [X] T028 [P] [US4] 선택 모델 검증 — `frontend/tests/DeleteSelection.test.tsx`: 행 본문 클릭 후 `deleteSelection` 불변 · 체크 칸 클릭 후 `focusedStepId` 불변 (UC-011-15), 순서 변경 후에도 같은 Step 이 선택 상태 (UC-011-16), 고른 개수 표시 (UC-011-17), 확인 문구에 개수와 범위 (UC-011-18), 「이 뒤 전부」 대상 0개면 비활성 + 사유 (UC-011-19)

### Implementation for User Story 4

- [X] T029 [US4] 세션 배치 삭제 라우트를 만든다 — `backend/src/itb/api/routes/steps.py`: `POST /{session_id}/steps:delete`. 검증(존재·중복) → 새 목록 구성 → **한 번에 교체** 순. 기존 `DELETE /{session_id}/steps/{step_id}` 는 남긴다. `execution/step_edits.py` 의 삭제 규칙을 그대로 쓰고 두 벌로 만들지 않는다 (api-contract §1)
- [X] T030 [US4] 행에 체크 칸을 붙인다 — `frontend/src/components/workbench/StepList.tsx`: 칸 구성을 `[체크 22][번호 26][이름 1fr][시간 58][결말 20][조작]` 으로 (UC-011-12). 체크 칸은 결말 아이콘(체크 ✓)과 **다른 형태**를 쓴다 (UC-011-13). 삭제 대상 선택이 없는 국면에서는 그리지 않는다 (UC-011-14)
- [X] T031 [US4] 패널 머리에 전부 고르기를 둔다 — `frontend/src/components/workbench/StepList.tsx` 의 `StepPanelHeader`: `step.selectAllDeleteTargets` 와 고른 개수 (UC-011-17 · FR-380c)
- [X] T032 [US4] 팔레트에 복수 삭제 조작을 둔다 — `frontend/src/components/workbench/ActionPalette.tsx`: `PALETTE_ACTIONS` 에 `step.deleteSelected`·`step.deleteAfter` 를 고정 순서로 넣고, 대상이 0개면 화면이 아는 사실로 좁힌다(`narrow`)
- [X] T033 [US4] API 호출을 만든다 — `frontend/src/api/client.ts`: 세션 배치 삭제 호출. 편집 경로는 라우트를 더하지 않고 `edits` 에 `{"op":"delete","step_id":…}` 를 **id 로** 여러 개 싣는다 (api-contract §2 — 인덱스로 보내면 앞의 삭제가 뒤 인덱스를 밀어 다른 Step 이 지워진다)
- [X] T034 [US4] 세션 화면이 선택을 소유한다 — `frontend/src/pages/SessionScreen.tsx`: `deleteSelection` 상태와 전이(체크 토글·전부·삭제 후 비우기·목록 변경 시 사라진 id 제거·화면 이동 시 비우기, data-model §4-1). 상세가 열린 채 대상이 지워지면 기존 `data-focus-missing` 안내가 그대로 뜬다 (FR-387)
- [X] T035 [US4] 편집 화면이 선택을 소유한다 — `frontend/src/pages/EditView.tsx`: 같은 상태·같은 전이. 저장은 `edits` 에 `delete` 를 모아 한 번에 보낸다 (원자적)
- [X] T036 [US4] 기존 검증을 개정한다 — `frontend/tests/StepRowActions.test.tsx`(행 조작 옆에 체크 칸이 생겼다), `frontend/tests/StepListPerformance.test.tsx`(칸이 늘어도 기준선을 지킨다)

**Checkpoint**: US1·US2·US4 가 각각 독립적으로 동작한다.

---

## Phase 6: User Story 3 - 녹화와 대등하게 AI 지시문으로 Step 을 더한다 (Priority: P2)

**Goal**: 편집 국면에서 녹화와 지시문이 같은 자리·같은 무게로 제시되고, 브라우저가 닫혀 있으면
자동으로 연다.

**Independent Test**: 저장된 테스트를 편집으로 열고(브라우저 닫힘) 「지시문으로 더하기」를 누르면
브라우저가 열려 지시문 수행으로 이어진다. → [quickstart.md](quickstart.md) §2 US3

### Tests for User Story 3

- [X] T037 [P] [US3] 대등성 검증 — `frontend/tests/AuthoringParity.test.tsx`: 브라우저가 닫힌 편집 국면에서 `step.recordStart`·`step.addNaturalLanguage` 가 같은 자리에 **둘 다 활성**(UC-011-23), 저장하지 않은 변경이 있으면 기존 「저장하고 열기」 확인이 걸리고 **새 확인이 생기지 않는다**(UC-011-24), 브라우저 열기 실패 시 진행 표시를 켜지 않는다(UC-011-25)

### Implementation for User Story 3

- [X] T038 [US3] 두 조작 앞에 브라우저 열기를 붙인다 — `frontend/src/pages/EditView.tsx`: 기존 `openBrowser()`(457~480행)를 `step.recordStart`·`step.addNaturalLanguage` 실행의 선행 단계로 쓴다. **둘 다 같은 규칙으로** — 하나만 자동으로 열면 대등성이 다시 깨진다 (research R7)
- [X] T039 [US3] 실패 경로를 만든다 — `frontend/src/pages/EditView.tsx`: 브라우저 열기가 실패하면 사유를 알리고 지시문·녹화를 시작하지 않는다. 진행 표시를 켰다가 끄지 않는다 (UC-011-25 · FR-374c)
- [X] T040 [US3] 두 조작을 같은 자리·같은 무게로 놓는다 — `frontend/src/components/workbench/ActionPalette.tsx`: 지금 자연어 입력칸은 버튼 줄 **위**에, `step.recordStart` 는 버튼 줄 **안**에 있다. 둘이 같은 묶음에서 같은 무게로 읽히게 배치한다 (FR-374)
- [X] T041 [US3] 쓰이지 않게 된 문구를 정리한다 — `frontend/src/lib/wording.ts`: `NEEDS_BROWSER` 사유가 다른 국면에서 아직 쓰이는지 확인하고, 쓰이지 않으면 근거를 남기고 지운다. 쓰이면 그대로 둔다 (research R7 주의)

**Checkpoint**: US1·US2·US3·US4 가 각각 독립적으로 동작한다.

---

## Phase 7: User Story 5 - Step 마다 스크린샷이 남고 결과보기에서 Step 별로 본다 (Priority: P3)

**Goal**: Step 이 끝난 시점의 화면을 남기고, 테스트당 최근 실행 1회분만 보관하며, 결과보기에서
Step 별로 본다.

**Independent Test**: Step 8개 테스트를 실행하면 `.runs/TC-xxx/steps/` 에 PNG 가 남고, 결과보기의
각 행에서 그 화면이 보인다. 다시 실행하면 이전 실행 것이 사라진다.
→ [quickstart.md](quickstart.md) §2 US5

### Tests for User Story 5

- [X] T042 [P] [US5] 촬영·보관 단위 검증 — `backend/tests/unit/test_step_screenshots.py`: 정상 촬영, 민감 값이 있으면 **쓰지 않고 사유만**(FR-392), 촬영 오류 시 사유 기록 후 계속(FR-398), `clear_step_screenshots` 가 `steps/` 를 비우고 실패해도 예외를 밖으로 내지 않음(FR-396c)
- [X] T043 [P] [US5] 서빙 계약 검증 — `backend/tests/contract/test_step_screenshot_route.py`: `GET /api/tests/{id}/result/steps/{index}/screenshot` 의 성공과 오류표 6종 — 결과 없음·읽을 수 없음·인덱스 범위 밖·`screenshot === null`(사유 포함)·파일 없음·루트 밖 경로 (api-contract §3)
- [X] T044 [P] [US5] 실행 왕복 검증 — `backend/tests/integration/test_step_screenshot_lifecycle.py`: 실행 후 `steps/` 에 실행 대상 Step 수만큼 남고, 재실행 시 이전 실행 파일이 **사라지며**(FR-396a), Step 수를 줄여 재실행하면 높은 인덱스 파일이 남지 않는다. 건너뜀·미도달 Step 은 파일도 사유도 없다(FR-393). 실패 Step 의 `screenshot` 이 `failure.png` 를 가리키고 파일이 **두 벌이 아니다**(FR-394)
- [X] T045 [P] [US5] 호환 검증 — `backend/tests/integration/test_old_result_compat.py`: 새 필드가 없는 구버전 `result.json` 을 그대로 읽고, 결말·소요 시간이 정상이며 스크린샷은 「없음 + 사유」가 된다 (SC-613 · FR-396b)
- [X] T046 [P] [US5] 결과 화면 검증 — `frontend/tests/StepScreenshot.test.tsx`: Step 을 고르면 그 화면이 상세에 보이고(UC-011-20), 없음의 네 상황 각각에 사유 문구가 있으며(UC-011-21), 결말·소요 시간·시도한 locator 표시를 밀어내지 않는다(UC-011-22)

### Implementation for User Story 5

- [X] T047 [P] [US5] 결과 모델을 넓힌다 — `backend/src/itb/domain/run_result.py`: `StepResult.screenshot: str | None = None` 과 `screenshot_note: str | None = None`. 둘 다 기본값이 있어 기존 파일이 그대로 읽힌다. `Artifacts` 는 바꾸지 않는다 (data-model §1-1·1-2)
- [X] T048 [US5] 산출물 수집기를 넓힌다 — `backend/src/itb/execution/artifacts.py`: `STEP_SHOTS_DIR = "steps"`, `write_step_screenshot(...)`, `clear_step_screenshots(...)`. **`_write_screenshot` 을 복제하지 않는다** — 민감 값 검사(`_contains_secret`)가 두 벌이 되면 한쪽만 고쳐지는 날 평문이 남는다 (data-model §1-3)
- [X] T049 [US5] Step 종료 시 촬영한다 — `backend/src/itb/execution/step_executor.py`: **`duration_ms` 를 확정한 뒤** 찍는다. 촬영 시간이 시간 초과 판정에 들어가지 않는다 (FR-395). 촬영 실패가 결말을 바꾸지 않는다 (FR-398)
- [X] T050 [US5] 실행 시작 시 비우고 결과에 싣는다 — `backend/src/itb/execution/runner.py`: 실행 시작에 `clear_step_screenshots(run_dir)`, 결과 조립 시 각 `StepResult` 에 경로·사유를 채운다. 실패 Step 은 기존 `failure.png` 의 상대 경로를 가리킨다 (FR-394·FR-396a)
- [X] T051 [US5] 서빙 라우트를 만든다 — `backend/src/itb/api/routes/tests.py`: 먼저 `get_artifact` 안의 **루트 밖 경로 거절 검사를 함수로 뽑고**(복제 금지), `GET /{test_id}/result/steps/{index}/screenshot` 을 그 함수 위에 만든다. 기존 `kind` Literal 은 늘리지 않는다 (api-contract §3)
- [X] T052 [US5] 스키마 생성물과 드리프트 검사를 갱신한다 — `cd backend && uv run python -m itb.schema.export` · `cd frontend && npm run gen:types` 로 생성물을 갱신해 **함께 커밋**하고, `backend/tests/contract/test_schema_drift.py` 의 기대값을 고친다 (헌법 Cross-language schema duty)
- [X] T053 [US5] 화면 API 를 넓힌다 — `frontend/src/api/client.ts`: Step 스크린샷 URL 만들기(`stepScreenshotUrl(testId, index)`)와 없음 응답의 사유 읽기
- [X] T054 [US5] 상세에 스크린샷 자리를 둔다 — `frontend/src/components/workbench/StepDetail.tsx`: 결과 국면에서 그 Step 의 화면. **새 영역을 만들지 않는다** — 상세가 그 자리다 (UC-011-20). 없으면 사유를 말한다 (UC-011-21)
- [X] T055 [US5] 결과 화면이 전달한다 — `frontend/src/pages/ResultView.tsx`: `WorkbenchStep.screenshotUrl`·`screenshotNote` 를 채운다. 「이후 실행으로 대체됨」 사유도 여기서 판단한다 (FR-396b)
- [X] T056 [US5] 기존 검증을 개정한다 — `frontend/tests/RunResult.test.tsx`·`frontend/tests/ResultAttemptsVisible.test.tsx`: 상세에 자리가 하나 늘었고 기존 표시가 밀려나지 않는다

**Checkpoint**: 다섯 이야기가 모두 독립적으로 동작한다.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T057 [P] 개발 문서를 갱신한다 — `docs/DEVELOPMENT.md`: `.runs/<ID>/steps/` 구조와 「테스트당 최근 실행 1회분」 보관 규칙, 저장·이름의 새 자리
- [X] T058 [P] 사람만 확인할 수 있는 항목을 등록한다 — `docs/PENDING-HUMAN-VERIFICATION.md`: 상세가 대상 앱을 덮는 정도가 실제로 받아들일 만한가(clarify 결정 1 의 사후 확인), 체크 칸과 결말 아이콘이 눈으로 혼동되지 않는가(UC-011-13)
- [X] T059 시간 초과 판정 회귀를 고정한다 — `backend/tests/integration/test_timeout_unaffected_by_shots.py`: 같은 Step 을 촬영 켠 상태·끈 상태로 돌려 `duration_ms` 와 시간 초과 판정이 같은지 본다. 촬영 시간이 판정에 들어가면 안 된다 (SC-611 · FR-395)
- [X] T060 쓰이지 않게 된 문구·상수를 정리한다 — `frontend/src/lib/wording.ts`·`ActionPalette.tsx` 의 props: 자리 이동으로 남은 것을 화면에 쓰거나 근거를 남기고 지운다 (010 T092 와 같은 성격)
- [X] T061 전체 자동 검증을 돌린다 — [quickstart.md](quickstart.md) §1 의 7개 명령 전부. 개정된 기존 검증 10건이 함께 통과해야 한다
- [ ] T062 손 검증을 돌린다 — [quickstart.md](quickstart.md) §2 의 다섯 이야기와 §3 의 호환 확인 1·2
      **열어 둔다.** 구현자가 자기 구현을 판정하면 대조가 아니라 자기 확인이 된다
      (002 T099 · 001 T156 이 같은 이유로 사람에게 넘긴 항목이다). 자동 검증은 전부
      통과했고 준비물은 다 있다 — 판정 칸만 비어 있다. 사람이 봐야 하는 세 가지는
      `docs/PENDING-HUMAN-VERIFICATION.md` 11번에 절차까지 적어 두었다.
- [X] T063 계약이 실제로 세지는지 확인한다 — [contracts/ui-contract.md](contracts/ui-contract.md) §8 의 9개 항목이 각각 자동 검사로 세지고 있는지 대조한다. 세지 않는 것이 있으면 검사를 더한다

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음
- **Phase 2 (Foundational)**: Phase 1 후. **모든 사용자 이야기를 막는다** — 조작 정본이 새 계약을 말하기 전에는 표시를 고칠 수 없다
- **Phase 3~7 (사용자 이야기)**: Phase 2 후
- **Phase 8 (Polish)**: 원하는 이야기가 다 붙은 뒤

### User Story Dependencies

| 이야기 | 시작 조건 | 다른 이야기 의존 |
|---|---|---|
| US1 (P1) 저장·이름 | Phase 2 | 없음 |
| US2 (P1) 상세 자리·네 상태 | Phase 2 | 없음 |
| US4 (P2) 복수 삭제 | Phase 2 + **US2 의 T022** | 체크 칸이 US2 가 만든 네 번째 축 위에 올라간다 |
| US3 (P2) 지시문 대등성 | Phase 2 | 없음 (US1 의 「저장하고 열기」 경로와 맞물리지만 기존 규칙을 쓴다) |
| US5 (P3) Step 별 스크린샷 | Phase 2 | 없음 (US2 의 상세 자리를 쓰지만 그 자리는 이미 존재한다) |

**US4 만 실제 의존이 있다.** 나머지 넷은 Phase 2 이후 순서가 자유롭다.

### Within Each User Story

- 검증을 먼저 쓰고 **실패를 확인한 뒤** 구현한다
- 백엔드 모델 → 수집·실행 → 라우트 → 화면
- 「기존 검증 개정」은 그 이야기의 **마지막 작업**이다 — 구현 전에 고치면 무엇이 깨졌는지 못 본다

### Parallel Opportunities

- Phase 2: T002·T003·T005 가 [P] (다른 파일). T004 는 T002·T003 을 기다린다
- 각 이야기의 검증 작업은 전부 [P]
- Phase 7 의 T042~T046 다섯 검증이 [P], T047 도 [P] (모델 파일 단독)
- Phase 8 의 T057·T058 이 [P]
- 사람이 여럿이면 Phase 2 후 US1·US2·US3·US5 를 동시에 진행할 수 있다. US4 는 US2 의 T022 를 기다린다

---

## Parallel Example: User Story 5

```bash
# 검증 다섯 개를 함께 (다른 파일, 서로 의존 없음)
Task: "촬영·보관 단위 검증 in backend/tests/unit/test_step_screenshots.py"
Task: "서빙 계약 검증 in backend/tests/contract/test_step_screenshot_route.py"
Task: "실행 왕복 검증 in backend/tests/integration/test_step_screenshot_lifecycle.py"
Task: "호환 검증 in backend/tests/integration/test_old_result_compat.py"
Task: "결과 화면 검증 in frontend/tests/StepScreenshot.test.tsx"
```

---

## Implementation Strategy

### MVP (US1 만)

1. Phase 1 → Phase 2 (정본)
2. Phase 3 (US1)
3. **멈추고 확인**: quickstart §2 US1 여섯 항목
4. 저장 손실 경로가 사라진다 — 이것만으로도 값이 있다

### 증분 전달

1. Setup + Foundational → 정본이 새 계약을 말한다
2. US1 → 확인 → 저장이 보이는 자리에 있고 이름을 두 번 묻지 않는다 (MVP)
3. US2 → 확인 → 어느 Step 을 보는지 분명해진다
4. US4 → 확인 → 재녹화 뒤 정리가 22회에서 3회 이하로 (SC-607)
5. US3 → 확인 → 녹화와 지시문이 대등해진다
6. US5 → 확인 → Step 별 화면 기록이 생긴다

각 단계가 앞 단계를 깨뜨리지 않는다.

---

## Notes

- [P] = 다른 파일, 의존 없음
- 각 이야기는 독립적으로 완료·검증 가능하다 (US4 의 T022 의존만 예외)
- 검증이 실패하는 것을 먼저 확인한다
- 작업마다 또는 논리 묶음마다 커밋한다
- **기존 검증을 지우거나 건너뛰어 통과시키지 않는다** (헌법 §품질 게이트 4). 011 은 정본을 바꾸므로 그것을 세는 검사가 깨지는 것이 정상이고, 기대값을 새 계약에 맞춰 고치는 것이 작업이다
- 피할 것: 모호한 작업, 같은 파일 충돌, 이야기 독립성을 깨는 교차 의존

---

## Phase 9: Convergence

**1회차** (2026-09-10). spec·plan·헌법 대비 잔여 5건.

점검 범위: FR 50건 · SC 17건 · 인수 시나리오 33건 · plan 결정 9건(research R1~R9) ·
헌법 원칙 5개. **위반 0건**, 요청하지 않은 코드 0건.

- [X] T064 지시문을 세션의 **기록**으로도 남긴다 — `frontend/src/App.tsx` 의 `openBrowserAt` 이 `instructionOnArrival` 만 싣고 `aiInstruction` 을 싣지 않아, 도착한 세션의 지시문 칸이 비어 있다. 사용자는 자기가 무엇을 시켰는지 잃는다 (001 FR-063 이 UX U-07 로 막은 그 형태) per FR-377 (missing)
- [X] T065 되돌릴 수 없는 복수 삭제는 확인에서 그 사실을 밝힌다 — `frontend/src/components/workbench/BulkDeleteConfirm.tsx` 에 되돌림 가능 여부를 받아 문구를 가른다. 세션은 즉시 서버에 적용되어 되돌릴 수 없고(`sessions.deleteSteps`), 편집은 `edits.revert` 로 되돌릴 수 있다 — 두 경로의 성질이 다른데 같은 문장을 쓰고 있다 per FR-386 (partial)
- [X] T066 저장 확인줄이 **이름**을 말하게 한다 — `frontend/src/pages/SessionScreen.tsx` 의 `editSavedNotice(title)` 이 `title = testId ?? "새 테스트"` 라 「저장했습니다 · TC-001」로 id 가 나온다. 011 이 `SessionView.test_name` 을 실었으므로 이름을 쓸 수 있다 per FR-367 (partial)
- [X] T067 세션에서도 저장 이후 더해진 행에 미저장 표식을 세운다 — `frontend/src/pages/SessionScreen.tsx` 가 `WorkbenchStep.isUnsaved` 를 채우지 않아 지시문·녹화로 더해진 Step 이 저장된 것과 구별되지 않는다. 판정 근거는 `view.saved_snapshot` 이후에 생긴 Step 인가다 per FR-379 (partial)
- [X] T068 [P] 조작 횟수와 다시 실행 확인을 검사로 고정한다 — `frontend/tests/DeleteSelection.test.tsx` 에 「Step 15개 중 뒤의 11개를 3회 이하로 정리」를 세는 검사를, `frontend/tests/SaveNamePrompt.test.tsx` 에 `RerunConfirm` 의 이름칸 조건부 검사를 더한다. 지금은 SC-607 을 세는 자동 검사가 없고 이름칸 조건부는 `LeaveConfirm` 만 검증됐다 per SC-607 · FR-364 (partial)
