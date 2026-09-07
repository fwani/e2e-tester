---

description: "Task list for 006-edit-saved-test"
---

# Tasks: 저장된 테스트를 고치는 길 — 편집 진입점과 브라우저 없는 편집

**Input**: Design documents from `/specs/006-edit-saved-test/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: 포함한다. 헌법 Quality Gate 3 이 요구한다 — "제품은 테스트 도구다. 자기 테스트
없이 내보내는 것은 받아들일 수 없다." 이 기능은 **브라우저 없이 검증되는 성질**이므로 단위·계약
테스트 비중이 높다.

**Organization**: 사용자 스토리별로 묶는다. 각 스토리는 독립적으로 구현·검증·인도된다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리인가 (US1~US5)
- 파일 경로를 반드시 적는다

## Path Conventions

웹 애플리케이션: `backend/src/itb/`, `backend/tests/`, `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup

**Purpose**: 이 기능은 **의존성을 추가하지 않는다**. 설정 작업은 검증 재료 준비뿐이다.

- [ ] T001 [P] [quickstart.md](./quickstart.md) §0 의 검증 재료 TC-FAIL(7 Step, Step 06 이 없는 `testId` 로 실패) 과 TC-PASS(5 Step, `fill` Step + 민감 참조 `{{SECRET_VALUE_1}}` 포함)를 격리 XDG 환경에 만드는 절차를 `backend/tests/fixtures/` 의 기존 정의 픽스처 방식으로 준비한다
- [ ] T002 [P] 이 라운드의 작업 흐름을 확인한다 — 대상 앱을 **띄우지 않은 채** `backend` `uv run pytest` 와 `frontend` `npx vitest run` 이 통과하는 기준선을 기록한다 (SC-302 의 기준선)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 세션 편집과 정의 편집이 **같은 것**을 쓰게 만드는 공유 핵심. 이것이 끝나기 전에는
어떤 스토리도 시작할 수 없다 — 순서를 뒤집으면 규칙이 두 벌로 생긴다 (research R2·R3·R5).

**⚠️ CRITICAL**: 이 단계가 이 기능의 설계 주장 그 자체다.

### 공유 편집 핵심

- [ ] T003 `backend/src/itb/execution/step_edits.py` 의 `update_step()` 에 `tab: int | None = None` 인자를 더한다. FR-183 이 대상 탭 수정을 요구하고, 편집 핵심은 한 곳이므로 인자를 그곳에 더한다 (research R3 후단). 세션 라우터의 `PatchStepRequest` 는 **건드리지 않는다** — 세션 계약은 그대로다
- [ ] T004 [P] `backend/tests/unit/test_step_edits.py` 에 `tab` 수정 단위 테스트를 더한다. `current_step_index=0` 으로 부르면 경고가 **하나도 생기지 않는다**는 것도 함께 단정한다 (data-model §2 적용 규칙)

### 변수 파생 로직 이식 (R5)

- [ ] T005 `backend/src/itb/api/routes/sessions.py` 의 `_variables_for(w: SessionWork)` 를 `backend/src/itb/domain/test_case.py` 의 순수 함수 `derive_variables(steps, base_variables, sealed_names, captured_names)` 로 **옮긴다**. 복사하지 않는다 — 두 벌이면 한쪽에서 민감 표시가 강등된다 (FR-214)
- [ ] T006 `backend/src/itb/api/routes/sessions.py` 의 저장 경로가 `derive_variables()` 를 부르게 바꾼다. 기존 동작이 그대로인지 확인한다 (세션 저장 회귀 금지)
- [ ] T007 [P] `backend/tests/unit/test_derive_variables.py` — 불러온 정의의 민감 변수가 유지되는 것, 새 참조가 비민감·빈 값으로 추가되는 것, 봉인 이름이 민감으로 판정되는 것을 단정한다 (FR-214)

### 정의 파일 revision (R4)

- [ ] T008 `backend/src/itb/storage/repository.py` 에 `definition_revision(test_id) -> str` 을 더한다. 정의 파일 바이트의 SHA-256 앞 16자. 파일이 없으면 `TEST_NOT_FOUND` 계열 예외
- [ ] T009 [P] `backend/tests/unit/test_definition_revision.py` — 내용이 같으면 같고 한 바이트만 달라도 다르다. mtime 만 바뀌어도 값이 같다는 것을 단정한다 (R4 의 mtime 기각 근거를 테스트로 고정)

### 오류 코드와 전송 모델

- [ ] T010 `backend/src/itb/domain/error.py` 의 `ErrorCode` 에 `DEFINITION_STALE` 을 더한다. `DEFINITION_INVALID` 와 갈라 두는 이유를 주석에 적는다 — 사용자가 할 일이 다르다 ([contracts/rest-api.md](./contracts/rest-api.md) §4)
- [ ] T011 `backend/src/itb/api/routes/tests.py` 에 전송 모델을 정의한다 — `EditOp`(`update`·`delete`·`reorder`·`set_name`·`set_start_url`·`set_assertion_value` 판별 유니온), `SaveDefinitionRequest`(`revision`, `edits`), `DefinitionView`(`test`, `revision`, `editable`, `blocked_by`, `blocking_session_id`, `locked_fields`, `warnings`). 전부 `extra="forbid"` (FR-211)
- [ ] T012 **`EditOp` 에 locator 관련 필드를 넣지 않는다**는 것을 구조로 고정한다 — `backend/tests/contract/test_definition_edit_model.py` 에서 `target`·`css`·`test_id`·`role` 등을 보낸 요청이 거절되는 것을 단정한다 (FR-187 제외 결정 · 원칙 IV · data-model §7 불변식 3)
- [ ] T013 **평문 민감 값을 받는 필드가 없다**는 것을 고정한다 — 같은 계약 테스트에서 `secret`·`plaintext` 류 필드가 거절되는 것을 단정한다 (FR-215 · 불변식 4)
- [ ] T014 스키마를 내보내고 프론트 타입을 생성한다 — `cd backend && uv run python -m itb.schema.export`, `cd frontend && npm run gen:types`. `git diff --exit-code schema/` 가 깨끗해야 한다 (헌법 Cross-language schema duty)

**Checkpoint**: 공유 핵심 준비 완료 — 스토리 구현을 시작할 수 있다. 이 시점에 편집 규칙의
구현은 여전히 `step_edits` **한 곳**이다.

---

## Phase 3: User Story 1 — 목록에서 열어 고치고 저장한다 (Priority: P1) 🎯 MVP

**Goal**: 저장된 테스트를 브라우저 없이 열어 값·라벨·대기시간·탭·순서·삭제·이름을 고치고
저장한다. 대상 앱이 떠 있지 않아도 된다.

**Independent Test**: 대상 앱을 **끈 상태**로 목록에서 테스트를 열어 `fill` 값 하나를 바꾸고
저장한 뒤, 정의 파일에 그 값이 반영됐는지 본다 ([quickstart.md](./quickstart.md) S1).

### Tests for User Story 1 ⚠️ 먼저 쓰고 실패를 확인한다

- [ ] T015 [P] [US1] `backend/tests/contract/test_get_definition.py` — `GET /api/tests/{id}/definition` 이 200 이고 `test`·`revision`·`editable`·`locked_fields` 를 준다. **Playwright 를 기동하는 코드 경로가 닿지 않는다**는 것을 단정한다 (FR-182 · SC-302)
- [ ] T016 [P] [US1] `backend/tests/contract/test_put_definition.py` — `update`·`delete`·`reorder`·`set_name`·`set_start_url`·`set_assertion_value` 각 연산이 정의 파일에 반영된다 (FR-183~186)
- [ ] T017 [P] [US1] 같은 파일에 거절 계약을 단정한다 — 알 수 없는 `step_id`(400 `DEFINITION_INVALID`), 값을 갖지 않는 종류에 `value`(400), `reorder` 집합 불일치(400), 결과 Step 0개(400 `STEP_LIST_EMPTY`, FR-197), 빈 `edits`(400) ([contracts/rest-api.md](./contracts/rest-api.md) §2)
- [ ] T018 [P] [US1] `backend/tests/contract/test_definition_sensitive.py` — 민감 참조를 평문으로 바꾸는 편집이 400 이고 `next_action` 이 비밀 값 화면을 가리킨다. 비민감 참조를 평문으로 바꾸는 것은 성공한다 (FR-213 · data-model §4 V6)
- [ ] T019 [P] [US1] 같은 파일에서 편집·저장 후 민감 변수의 `sensitive: true` 가 유지되는 것과, 응답·로그에 평문이 없는 것을 단정한다 (FR-214·FR-215)
- [ ] T020 [P] [US1] `backend/tests/unit/test_definition_warnings.py` — 정의되지 않은 참조가 저장을 막지 않고 `warnings` 로 나온다 (FR-216)
- [ ] T021 [P] [US1] `backend/tests/abnormal/test_definition_invalid_file.py` — 스키마 위반 정의 파일에 대해 `GET /definition` 이 400 `DEFINITION_INVALID` 이고 어느 지점이 왜 잘못됐는지 `message` 에 있다. 깨진 파일을 반쯤 읽어 저장하지 않는다 (FR-196 · Edge Case)
- [ ] T022 [P] [US1] `backend/tests/contract/test_definition_no_llm.py` — 신규 엔드포인트 2개에서 작성(authoring) 계층 호출이 **도달 불가**하다 (FR-210 · 원칙 II NON-NEGOTIABLE)
- [ ] T023 [P] [US1] `backend/tests/unit/test_definition_reuses_step_edits.py` — 정의 편집 경로가 `itb.execution.step_edits` 를 부른다. 편집 규칙의 두 번째 구현이 없다는 것을 import·호출로 단정한다 (FR-192 · 원칙 I)
- [ ] T024 [P] [US1] `frontend/tests/TestDefinitionEdit.test.tsx` — 값을 바꾸면 변경 건수가 1이 되고, 두 번째 변경에 2가 되고, 하나를 되돌리면 1로 준다 (FR-188·FR-189·FR-190)
- [ ] T025 [P] [US1] `frontend/tests/TestListEditEntry.test.tsx` — 목록 행 메뉴에 「편집」이 있고 「정의 보기」가 없다 (FR-175 · [contracts/ui-contract.md](./contracts/ui-contract.md) §1)

### Implementation for User Story 1 — 백엔드

- [ ] T026 [US1] `backend/src/itb/api/routes/tests.py` 에 `GET /api/tests/{test_id}/definition` 을 구현한다. `repo.read_test()` + `definition_revision()` + `state.sessions.reservation_for_test()` 로 `DefinitionView` 를 만든다. **브라우저를 만들지 않는다** (FR-182)
- [ ] T027 [US1] `locked_fields` 를 한 곳에서 만든다 — `backend/src/itb/api/routes/tests.py` 의 상수 또는 `domain` 의 표. [data-model.md](./data-model.md) §1 의 편집 가능 표가 유일한 근거다. 화면이 이 목록을 하드코딩하지 않게 한다 (FR-191)
- [ ] T028 [US1] `PUT /api/tests/{test_id}/definition` 을 구현한다. 순서: V1 요청 형태 → V2 `revision` → V3 실행 중 → V4 연산 적용(`step_edits`) → V5 Step 1개 이상(FR-197) → V6 민감 참조 → V7 `Test` 검증 → V8 `derive_variables()` → V9 경고 ([data-model.md](./data-model.md) §4)
- [ ] T029 [US1] 연산 적용을 **전부 또는 전무**로 만든다. 하나라도 실패하면 파일을 쓰지 않는다. `step_edits` 예외를 계약의 오류 코드로 옮긴다 (`ValueNotSupportedError`·`ReorderMismatchError`·`StepNotFoundError` → 400/404)
- [ ] T030 [US1] 저장을 `repo.write_test()` 로 수렴시킨다. 원자적 쓰기(`itb.storage.atomic`)를 쓰고 `updated_at` 을 갱신한다. **같은 `test_id` 를 덮어쓴다** (FR-193 · 불변식 5·6)
- [ ] T031 [US1] 저장 실패를 조용히 넘기지 않는다 — 파일 쓰기 실패는 500 `STORAGE_WRITE_FAILED` 와 다음 행동 (FR-198)
- [ ] T032 [US1] 정의 형식이 편집으로 바뀌지 않는지 확인한다 — 저장 후 YAML 이 여전히 사람이 읽는 평문이고 필드 구성이 같다. `git diff` 가 편집한 값만 보여야 한다 (FR-199 · 원칙 V · quickstart §4)
- [ ] T032a [US1] 순서 변경 경고를 붙인다 — `reorder` 로 `navigate` Step 이 뒤로 밀렸으면 "앞선 상태가 필요한 Step 이 앞으로 왔습니다" 를 `warnings` 에 싣는다. **막지 않는다** (명세 Edge Case · research Q1). 규칙은 얕게 시작하고, 규칙이 늘어나면 별도 결정으로 다룬다
- [ ] T032b [P] [US1] `backend/tests/unit/test_reorder_warning.py` — `navigate` 가 뒤로 밀린 순서 변경이 저장은 성공하고 경고를 낸다. 순서가 그대로면 경고가 없다

### Implementation for User Story 1 — 프론트엔드

- [ ] T033 [P] [US1] `frontend/src/api/client.ts` 에 `definition.get(testId)` 와 `definition.save(testId, {revision, edits})` 를 더한다. 생성된 타입을 쓴다 (손으로 형태를 다시 적지 않는다)
- [ ] T034 [P] [US1] `frontend/src/lib/wording.ts` 에 [ui-contract.md](./contracts/ui-contract.md) §9 의 어휘를 더한다. Step 번호는 기존 `stepNumber(index)` 를 쓴다 — 여기서 `index + 1` 을 쓰면 005 U-07 이 되살아난다
- [ ] T035 [US1] `frontend/src/pages/TestDefinition.tsx` 를 편집 모드로 확장한다. `DefinitionView` 를 읽고, 편집 연산 목록(`ops`)과 표시용 `preview` 를 상태로 둔다. **`preview` 는 판정하지 않는다** ([data-model.md](./data-model.md) §5)
- [ ] T036 [P] [US1] `frontend/src/components/StepEditFields.tsx` — 값·라벨·대기시간·탭 입력. 각 입력이 하나의 `update` 연산을 만들고, 같은 Step 의 연속 편집은 하나로 합친다 (FR-183)
- [ ] T037 [US1] Step 삭제와 순서 변경을 편집 화면에 붙인다. 삭제는 `delete` 연산, 순서 변경은 `reorder` 연산 하나로 유지한다 (앞선 `reorder` 를 대체한다) (FR-184·FR-185)
- [ ] T038 [US1] 테스트 이름과 시작 주소 편집을 붙인다 (`set_name`·`set_start_url`) (FR-186)
- [ ] T039 [US1] 저장 버튼의 어휘와 상태를 [ui-contract.md](./contracts/ui-contract.md) §3 대로 만든다 — 「변경 저장 (N건)」·「저장 중…」·비활성·초록 확인줄. **화면을 옮기지 않는다.** 「초안」을 쓰지 않는다 (FR-194·FR-195 · 005 FR-156·FR-158)
- [ ] T040 [US1] 저장 응답의 새 `revision` 을 받아 다음 저장에 쓴다. 저장 후 다시 조회하지 않는다 (계약 §2)
- [ ] T041 [US1] 편집 불가 항목의 표시를 붙인다 — `locked_fields[].reason` 별 문구. **회색 버튼만 두지 않는다** ([ui-contract.md](./contracts/ui-contract.md) §4 · FR-191)
- [ ] T042 [US1] 민감 참조 값 칸을 참조 전용으로 만든다. 평문 입력을 화면에서도 막고, 그래도 보낸 경우 서버 거절 문구를 그 자리에 보여준다 (FR-212·FR-213)
- [ ] T043 [US1] 목록 행 메뉴의 「정의 보기」를 **「편집」으로 바꾼다** — `frontend/src/pages/TestList.tsx`. 보기만 하는 별도 항목을 남기지 않는다 (FR-175 · ui-contract §1)
- [ ] T044 [US1] 정의 보기 화면이 읽기 전용일 때 「편집하기」를 제공한다 — "실행을 시작해 일시정지한 뒤 하세요" 같은 **화면에 없는 조작을 지시하는 안내만 두지 않는다** (FR-177 · E-03)
- [ ] T045 [US1] `frontend/src/App.tsx` 의 `definition` 화면 배선을 편집 화면에 맞춘다. URL 규칙은 기존 `?screen=definition&test=` 를 그대로 쓴다 (FR-179·FR-181)
- [ ] T046 [P] [US1] `frontend/tests/ScreenUrl.test.ts` 에 `step` 질의를 더한다 — `?screen=definition&test=TC-001&step=step-06` 왕복 (FR-181)

**Checkpoint**: US1 완료 — 대상 앱 없이 열어 고치고 저장하는 왕복이 동작한다. 이 시점이 MVP다.

---

## Phase 4: User Story 2 — 실패한 Step 에서 「고치기」를 누르면 고칠 수 있다 (Priority: P1)

**Goal**: 결과 화면의 「Step nn 고치기」가 그 Step 이 펼쳐진 **편집 가능한** 화면으로 데려가고,
고쳐 저장한 뒤 그 자리에서 다시 실행을 건다.

**Independent Test**: 실패하는 테스트로 결과 화면 → 「Step 06 고치기」 → 값 수정 → 저장 →
「Step 06부터 실행」을 화면 이탈 없이 이어 건다 ([quickstart.md](./quickstart.md) S2).

### Tests for User Story 2 ⚠️

- [ ] T047 [P] [US2] `frontend/tests/EditEntryPoints.test.tsx` — 「편집」·「고치기」라는 이름의 컨트롤이 **모두** 편집 모드 화면에 도착한다. 읽기 전용 도착이 0건이다 (FR-178 · SC-304)
- [ ] T048 [P] [US2] 같은 파일에서 결과 화면 「Step 06 고치기」가 `focusStepId` 를 넘겨 Step 06 이 지목·펼쳐진 상태로 시작하는 것을 단정한다 (FR-180)

### Implementation for User Story 2

- [ ] T049 [US2] `frontend/src/pages/RunResult.tsx` 의 「Step nn 고치기」가 편집 모드로 열리게 한다. 지금은 읽기 전용 화면으로 데려간다 (FR-176 · E-04)
- [ ] T050 [US2] 편집 화면이 `focusStepId` 로 열릴 때 그 Step 을 지목·펼치고 화면 안에서 그 위치로 스크롤한다 (FR-180)
- [ ] T051 [US2] 저장 성공 확인줄 아래에 **「Step nn부터 실행」·「처음부터 실행」**을 둔다. 실행 진입은 005 가 만든 `startRun(testId, fromStepIndex)` **하나**를 쓴다 — 화면마다 새 경로를 만들면 005 U-01 이 되살아난다
- [ ] T052 [US2] 실행 버튼의 in-flight 가드를 그대로 따른다 (`pendingRun`). 저장 직후 연타로 세션이 둘 뜨지 않아야 한다 (005 FR-127·FR-129)
- [ ] T053 [P] [US2] `frontend/tests/EditThenRerun.test.tsx` — 저장 → 「Step 06부터 실행」이 `startRun(testId, 5)` 를 한 번 부른다

**Checkpoint**: 실패 진단 → 수정 → 재실행 한 바퀴가 화면 이탈 없이 이어진다 (SC-303).

---

## Phase 5: User Story 3 — 브라우저가 필요한 편집은 그 자리에서 브라우저를 연다 (Priority: P2)

**Goal**: 편집 화면에서 「브라우저 열어 Step nn 에서 멈추기」를 누르면 선행 Step 을 실행한 뒤
그 Step **직전**에서 멈춘 편집 가능 세션이 열린다. 달리는 실행을 잡을 필요가 없다.

**Independent Test**: 편집 화면에서 그 버튼을 눌러, 실행 도중 「일시정지」를 누르지 않고
편집 가능한 일시정지 상태에 도달하는지 본다 ([quickstart.md](./quickstart.md) S7).

### Tests for User Story 3 ⚠️

- [ ] T054 [P] [US3] `backend/tests/integration/test_pause_before_index.py` — `pause_before_index: 5` 로 만든 세션이 인덱스 0~4 를 실행한 뒤 인덱스 5 를 **실행하기 전에** `paused` 다. 그 과정에서 「일시정지」 요청이 한 번도 오지 않았다는 것도 함께 단정한다 (FR-200·FR-201)
- [ ] T055 [P] [US3] 같은 파일에서 `pause_before_index: 0` 이면 아무 Step 도 실행하지 않고 멈추는 것과, 범위 밖 값이 400 인 것을 단정한다 ([contracts/rest-api.md](./contracts/rest-api.md) §3)
- [ ] T056 [P] [US3] `backend/tests/unit/test_pacing_boundary.py` — `pause_before_index` 가 004 의 `한 스텝씩` 동작을 바꾸지 않는다. 상태 집합에 새 상태가 늘지 않는다 (R7 · 원칙 III)
- [ ] T057 [P] [US3] `frontend/tests/OpenBrowserAtStep.test.tsx` — 버튼 라벨에 Step 번호가 박혀 있고, 미저장 변경이 있으면 「저장하고 열기」가 되는 것을 단정한다 (FR-203 · ui-contract §5)

### Implementation for User Story 3

- [ ] T058 [US3] `backend/src/itb/execution/runner.py` 의 `_pace(next_index)` 에 멈춤 지점 비교를 더한다. 목표 인덱스에 도달하면 기존 `Command.PAUSE` 를 적용한다. **새 상태를 만들지 않는다** (R7)
- [ ] T059 [US3] `backend/src/itb/api/routes/sessions.py` 의 `CreateSessionRequest` 에 `pause_before_index: int | None` 을 더한다. `mode: "replay"` 에서만 허용하고 범위를 검증한다 (FR-211)
- [ ] T060 [US3] `_start_runner()` 로 그 값을 전달한다. 생략·`null` 이면 지금과 완전히 같아야 한다 (기존 클라이언트 무영향)
- [ ] T061 [P] [US3] `frontend/src/api/client.ts` 의 세션 생성에 `pause_before_index` 를 더한다
- [ ] T062 [US3] 편집 화면에 「브라우저 열어 Step nn 에서 멈추기」를 붙인다. 조건별 상태는 [ui-contract.md](./contracts/ui-contract.md) §5 표 대로 (Step 미지목 / 미저장 변경 / 실행 중) (FR-200)
- [ ] T063 [US3] 미저장 변경이 있으면 **먼저 저장한 뒤** 세션을 연다. 두 경로가 같은 Step 을 다르게 들고 있는 상태를 만들지 않는다 (FR-203)
- [ ] T064 [US3] locator 표 자리에 「이 대상은 살아 있는 화면에서만 다시 집을 수 있습니다」 + 그 버튼을 둔다. `live_browser_required` 만 경로를 준다 (FR-202 · FR-187 제외 결정의 화면 쪽 짝)
- [ ] T065 [US3] 세션에서 저장한 뒤 편집 화면으로 돌아오면 반영된 정의가 보이게 한다 — 화면 복귀 시 `GET /definition` 재조회 (FR-204)
- [ ] T066 [US3] 세션 편집 팔레트를 **건드리지 않는다**는 것을 확인한다. 새 편집 UI 를 만들지 않았음을 리뷰로 확인하고, 세션 편집 기존 테스트가 그대로 통과하는지 본다 (FR-205)

**Checkpoint**: 브라우저가 필요한 편집에 도달하는 데 「일시정지」를 누를 필요가 없다 (SC-305).

---

## Phase 6: User Story 4 — 저장하지 않은 변경을 잃지 않는다 (Priority: P2)

**Goal**: 미저장 변경이 확인 없이 사라지는 경로가 없다. 외부에서 파일이 바뀌었으면 조용히
덮어쓰지 않고 사용자가 고른다.

**Independent Test**: 값 2개를 바꾼 상태에서 「목록으로」를 눌러 확인 대화가 나오는지,
「버리기」 후 다시 열었을 때 원본이 그대로인지 본다 ([quickstart.md](./quickstart.md) S4·S6).

### Tests for User Story 4 ⚠️

- [ ] T067 [P] [US4] `backend/tests/contract/test_definition_stale.py` — 저장 사이에 파일이 바뀌면 409 `DEFINITION_STALE` 이고 `detail` 에 현재 `test` 와 `revision` 이 실린다 (FR-209 · 계약 §2)
- [ ] T068 [P] [US4] 같은 파일에서 `detail.revision` 을 실어 다시 보내면 저장이 성공하는 것을 단정한다. **강제 플래그가 없다**는 것도 확인한다 (계약 §2 후단)
- [ ] T069 [P] [US4] `frontend/tests/UnsavedGuard.test.tsx` — 변경 2건에서 이탈 시 건수를 밝힌 확인이 나오고, 변경 0건에서는 확인 없이 나간다 (FR-208)
- [ ] T070 [P] [US4] `frontend/tests/StaleConflict.test.tsx` — `DEFINITION_STALE` 응답에 두 버튼이 나오고 각각 무엇을 버리는지 라벨 옆에 적혀 있다 (ui-contract §7)

### Implementation for User Story 4

- [ ] T071 [US4] 이탈 확인을 붙인다 — 앱 안 이동은 인앱 확인(저장·버리기·머무르기), 새로고침·탭 닫기는 브라우저 기본 이탈 확인. 변경 0건이면 **묻지 않는다** (FR-208 · ui-contract §6)
- [ ] T072 [US4] 초안을 브라우저 저장소에 넣지 않는다는 것을 확인한다 — `localStorage`·`sessionStorage` 사용이 없음을 확인한다 (R8: 진실이 둘이 되는 것을 막는다)
- [ ] T073 [US4] 개별 변경 되돌리기를 붙인다. 되돌리기는 `ops` 목록에서 그 연산을 빼는 것이다 (FR-190)
- [ ] T074 [US4] `DEFINITION_STALE` 처리를 저장 버튼 자리에 붙인다. **화면을 옮기지 않는다.** 「바뀐 내용으로 다시 읽기」(내 편집 N건을 버린다) · 「내 편집으로 덮어쓰기」(파일의 변경을 버린다) (FR-209 · ui-contract §7)
- [ ] T075 [US4] 「다시 읽기」가 버리는 변경 건수를 라벨에 밝힌다. 어느 쪽도 되돌릴 수 없으므로 고르기 전에 알아야 한다

**Checkpoint**: 미저장 변경이 확인 없이 사라지는 경로가 0건이다 (SC-306).

---

## Phase 7: User Story 5 — 실행 중인 테스트는 왜 못 고치는지 말한다 (Priority: P3)

**Goal**: 같은 테스트가 실행 중이면 편집 화면은 열리되 읽기 전용이고, 이유와 그 실행으로 가는
버튼을 준다. 실행 중인 정의를 밑에서 바꾸지 않는다.

**Independent Test**: 테스트를 실행해 둔 상태에서 목록의 「편집」을 눌러 이유와 이동 버튼이
나오는지 본다 ([quickstart.md](./quickstart.md) S5).

### Tests for User Story 5 ⚠️

- [ ] T076 [P] [US5] `backend/tests/contract/test_definition_while_running.py` — 살아 있는 세션이 있으면 `GET /definition` 은 **200** 이면서 `editable: false`·`blocked_by: "running"`·`blocking_session_id` 를 준다 (FR-206)
- [ ] T077 [P] [US5] 같은 파일에서 그 상태의 `PUT /definition` 이 409 `SESSION_ALREADY_ACTIVE` 인 것과, 실행이 끝난 뒤 편집이 정상 동작하는 것을 단정한다 (FR-207)
- [ ] T078 [P] [US5] 같은 파일에서 사용자에게 보이는 `message`·`next_action` 에 세션 식별자가 **없다**는 것을 단정한다 (005 FR-135)
- [ ] T079 [P] [US5] `frontend/tests/EditBlockedByRun.test.tsx` — 읽기 전용 모드에서 편집 컨트롤이 **감춰지지 않고 비활성 + 이유**이며 「실행 중인 세션 보기」가 있다 (ui-contract §2)

### Implementation for User Story 5

- [ ] T080 [US5] 실행 중 판정을 `state.sessions.reservation_for_test(test_id)` **하나로** 한다. 새 기준을 만들지 않는다 — 재점검 리포트 N-02 가 두 기준의 결과였다 (R9)
- [ ] T081 [US5] `PUT /definition` 의 V3 게이트를 붙인다. 거절 응답은 005 와 같은 형태(`SESSION_ALREADY_ACTIVE` + `next_action` + `detail.session_id`) (FR-207)
- [ ] T082 [US5] 편집 화면의 읽기 전용 모드를 만든다. 컨트롤을 감추지 않고 비활성으로 두고 이유를 붙인다 (ui-contract §2)
- [ ] T083 [US5] 「실행 중인 세션 보기」를 `App.tsx` 의 기존 `openSession(sessionId)` 하나로 잇는다. 화면마다 새 이동 수단을 만들지 않는다 (005 FR-126)

**Checkpoint**: 실행 중 충돌이 조용히 실패하지 않고 사용자가 갈 곳을 안다.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T084 [P] 문구를 어휘 사전 한 곳으로 모았는지 확인한다 — `grep` 으로 편집 관련 한글 문장이 화면 파일에 직접 박혀 있지 않은지 본다 (005 가 결말 어휘에 대해 세운 규칙)
- [ ] T085 [P] `docs/DEVELOPMENT.md` 에 정의 편집 경로를 적는다 — 편집 규칙의 유일한 구현이 `step_edits` 이고, 정의 편집이 두 번째 호출자라는 것. 다음 사람이 세 번째 구현을 만들지 않게 한다
- [ ] T086 [P] `specs/006-edit-saved-test/checklists/requirements.md` 를 최종 상태로 갱신한다 (FR-187 제외 결정 반영)
- [ ] T087 스키마 생성물이 최신인지 재확인한다 — `uv run python -m itb.schema.export && git diff --exit-code schema/`, `npm run gen:types` 후 `git diff --exit-code frontend/src/types/generated/`
- [ ] T088 전체 자동 검증을 돌린다 — `cd backend && uv run pytest` · `cd frontend && npx vitest run`. **대상 앱을 띄우지 않은 채** 통과해야 한다 (T002 의 기준선과 비교, SC-302)
- [ ] T089 왕복 정합성을 확인한다 — 편집 → 저장 → 재실행이 반영된다 (SC-308). TC-FAIL 의 Step 06 대기 시간을 5000 으로 줄여 저장하고 실행해 약 20초 → 약 5초가 되는지 본다 (quickstart §4)
- [ ] T090 정의 형식 불변을 확인한다 — 편집·저장 후 `git diff` 가 편집한 값만 보여준다. 저장이 파일 전체를 재배치하면 사용자의 버전 관리가 쓸모 없어진다 (원칙 V)
- [ ] T091 원칙 준수 증거를 남긴다 — 신규 코드 경로에서 재생 경로에 언어모델이 닿지 않음(원칙 II), locator 해석 순서·후보 상태가 바뀌지 않음(원칙 IV), Step DSL 이 바뀌지 않음(원칙 I)을 한 곳에 정리한다 (헌법 Quality Gate 1)
- [ ] T092 [quickstart.md](./quickstart.md) §2·§3 의 S1~S8 을 **사람이 직접 걸어** 확인한다. 기대와 다른 것은 §5 기준으로 남은 작업으로 등록한다 (SC-301·SC-303·SC-304·SC-305·SC-306·SC-307·SC-309)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음
- **Phase 2 (Foundational)**: Setup 후. **모든 스토리를 막는다** — 공유 핵심이 먼저 서지 않으면
  각 스토리가 자기 규칙을 만든다 (이 기능이 없애려는 문제 그 자체)
- **Phase 3~7 (스토리)**: Foundational 후. 우선순위 순으로 진행하거나 병렬 가능
- **Phase 8 (Polish)**: 원하는 스토리가 모두 끝난 뒤

### User Story Dependencies

- **US1 (P1)**: Foundational 후 즉시. 다른 스토리에 의존하지 않는다 — **MVP**
- **US2 (P1)**: US1 의 편집 화면이 있어야 도착지가 존재한다 → **US1 후**
- **US3 (P2)**: 백엔드(T054~T060)는 US1 과 **병렬 가능**. 프론트(T062~T065)는 US1 의 편집 화면 필요
- **US4 (P2)**: 백엔드(T067·T068)는 US1 의 저장 경로 필요. 프론트는 US1 후
- **US5 (P3)**: US1 의 두 엔드포인트 필요. 화면은 US1 의 편집 화면 필요

### Within Each User Story

- 테스트를 먼저 쓰고 실패를 확인한 뒤 구현한다
- 백엔드 계약 → 백엔드 구현 → 프론트 클라이언트 → 프론트 화면
- 어휘는 화면보다 먼저 (T034 가 T035 앞에 있는 이유)

### Parallel Opportunities

- Phase 1 의 T001·T002
- Phase 2 의 T004·T007·T009 (다른 테스트 파일)
- US1 의 테스트 T015~T025 전부 (파일이 다르다)
- US1 의 T033·T034·T036 (클라이언트·어휘·입력 컴포넌트)
- **US3 의 백엔드(T054~T060)는 US1 진행 중에 병렬로 갈 수 있다** — 건드리는 파일이 겹치지 않는다
  (`runner.py`·`sessions.py` vs `tests.py`·프론트)
- Phase 8 의 T084·T085·T086

---

## Parallel Example: User Story 1 테스트

```bash
# US1 의 계약·단위 테스트를 함께 띄운다 (파일이 모두 다르다)
Task: "backend/tests/contract/test_get_definition.py — 브라우저 미기동 200"
Task: "backend/tests/contract/test_put_definition.py — 6개 연산 반영"
Task: "backend/tests/contract/test_definition_sensitive.py — 민감 참조 규칙"
Task: "backend/tests/unit/test_definition_warnings.py — 미정의 참조 경고"
Task: "backend/tests/abnormal/test_definition_invalid_file.py — 스키마 위반"
Task: "frontend/tests/TestDefinitionEdit.test.tsx — 변경 건수"
Task: "frontend/tests/TestListEditEntry.test.tsx — 목록 진입점"
```

---

## Implementation Strategy

### MVP First (US1 만)

1. Phase 1 Setup
2. Phase 2 Foundational — **여기가 이 기능의 설계 주장이다.** 건너뛰면 안 된다
3. Phase 3 US1
4. **멈추고 검증**: quickstart S1 을 사람이 직접 걷는다. 브라우저 창이 0개인지 본다
5. 이 시점에 사용자 불만("수정하는 방법이 명확하지 않다")의 대부분이 해소된다

### Incremental Delivery

1. Setup + Foundational → 공유 핵심 준비
2. US1 → 검증 → **MVP** (목록에서 열어 고치고 저장)
3. US2 → 검증 (실패 진단 → 수정 → 재실행 한 바퀴)
4. US3 → 검증 (브라우저가 필요한 편집)
5. US4 → 검증 (변경 보호)
6. US5 → 검증 (실행 중 충돌)
7. Polish

### 이 기능에서 특별히 주의할 것

- **Phase 2 를 건너뛰고 스토리부터 시작하지 않는다.** 그러면 편집 규칙이 정의 경로에 다시
  구현되고, 그것이 사용자가 금지한 "두 벌" 이다 (research R2·R3)
- **FR-187 을 되살리지 않는다.** 편집 요청 모델에 locator 필드를 넣고 싶어지면 R6 을 다시
  읽는다. 헌법 원칙 IV 개정 없이는 할 수 없다
- **「초안」 어휘를 쓰지 않는다.** 저장된 테스트를 편집하는 화면이다 (005 U-03 잔존 1번)
- **실행 진입·세션 이동은 005 가 만든 단일 경로를 쓴다.** 화면마다 새로 만들면 U-01·U-06 이
  되살아난다

---

## Notes

- [P] = 다른 파일, 미완료 의존 없음
- 각 작업 또는 논리적 묶음 뒤에 커밋한다
- Checkpoint 에서 멈춰 스토리를 독립적으로 검증할 수 있다
- 요구사항 42건 중 FR-187 은 범위 제외이며, 그 사실을 T012·T064 가 테스트와 화면으로 고정한다
