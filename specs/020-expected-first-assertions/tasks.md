---

description: "Task list template for feature implementation"
---

# Tasks: 기대 동작 기준 검증

**Input**: Design documents from `/specs/020-expected-first-assertions/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/)

**Tests**: 포함한다. **헌법 품질 게이트 3이 요구한다** — 「제품은 테스트 도구다. 자기
테스트 없이 내보내는 것은 허용되지 않는다」. 선택 사항이 아니다.

**Organization**: 사용자 스토리별로 묶는다. 스토리 번호는 명세의 것이고, **실행 순서는
우선순위(P)를 따른다** — US6 은 번호가 뒤지만 P1 이다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리인가 (US1, US2, US3, US4, US5, US6)
- 파일 경로를 정확히 적는다

## Path Conventions

웹 애플리케이션 2계층: `backend/src/itb/`, `frontend/src/`. 검증은
`backend/tests/{unit,integration,contract}/`, `frontend/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 이 기능을 확인할 수 있는 대상과, 무엇이 깨질지에 대한 목록을 먼저 만든다.

- [ ] T001 결함이 있는 고정 대상을 `fixtures/sample-app/defective-save.html` 로 추가하고 `fixtures/sample-app/serve.py` 에 경로를 붙인다 — 저장 시 `저장되었습니다` 가 아니라 `처리 완료` 가 뜨는 폼. 기존 고정 대상 파일은 고치지 않는다
- [ ] T002 [P] 「검증 실패가 실행을 멈춘다」를 전제로 짜인 기존 검증을 전수 조사해 `specs/020-expected-first-assertions/baseline.md` 에 목록으로 남긴다 — 최소한 `backend/tests/us5_support.py`(중간 Step 에서 반드시 실패하는 테스트)와 그것을 쓰는 통합 검증이 포함된다. **이 목록이 T019 의 작업 범위다**
- [ ] T003 [P] `backend/scripts/test-backend.sh` 와 `cd frontend && npm run typecheck && npm test` 를 지금 상태에서 돌려 **기준선을 기록**한다. 이후 실패가 이 기능 때문인지 원래 그랬는지 가릴 근거다

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 나머지 전부가 참조할 도메인 타입과 생성 스키마.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어느 사용자 스토리도 시작할 수 없다.

- [ ] T004 [P] `AuthoringMismatch` 모델을 `backend/src/itb/domain/assertion.py` 에 추가한다 — `observed`(1~4000자, 비어 있을 수 없음) · `truncated`(bool) · `recorded_at`(datetime). `model_config` 는 같은 파일의 `Assertion` 과 동일하게 (`extra="forbid"`, `json_schema_serialization_defaults_required=True`). data-model.md §1
- [ ] T005 `AssertionStep.mismatch: AuthoringMismatch | None = None` 을 `backend/src/itb/domain/step.py` 에 추가하고, **왜 `_StepBase` 가 아니라 여기인지**를 docstring 에 남긴다 (research.md R1). T004 에 의존
- [ ] T006 [P] `AssertionClass` StrEnum(`known_defect`·`regression`·`resolved`)과 `StepResult.assertion_class: AssertionClass | None = None` 을 `backend/src/itb/domain/run_result.py` 에 추가한다. **`Outcome` enum 과 `decide_outcome()` 은 건드리지 않는다** (FR-021)
- [ ] T007 [P] `BlockedKind` StrEnum(`needs_input`·`product_mismatch`)을 `backend/src/itb/authoring/blocked.py` 에 추가한다. data-model.md §4
- [ ] T008 [P] 도메인 단위 검증을 `backend/tests/unit/test_authoring_mismatch.py` 에 작성한다 — 빈 `observed` 거부, 4000자 경계, `mismatch` 없는 옛 정의의 재검증 통과, `AssertionStep` 이외의 Step 종류에 `mismatch` 가 없음
- [ ] T009 스키마를 재생성한다: `cd backend && uv run python -m itb.schema.export` 후 `cd frontend && npm run gen:types`. `backend/schema/{step,run-result}.schema.json` 과 `frontend/src/types/generated/{step,run-result}.d.ts` 가 새 필드를 담아야 한다. T005·T006 에 의존

**Checkpoint**: 도메인 준비 완료 — 사용자 스토리 시작 가능. US1 과 US6 은 서로 독립이므로 병렬 가능

---

## Phase 3: User Story 1 - AI 가 기대값을 지킨다 (Priority: P1) 🎯 MVP

**Goal**: 지시문이 요구한 기대값이 화면의 값으로 대체되지 않고, 어긋난 검증도 정의에 남는다.

**Independent Test**: T001 의 고정 대상에 대해 AI 작성을 돌려, 저장된 검증의 기대값이
`저장되었습니다`(지시문의 값)이고 어긋남으로 표시되는지 확인한다. 화면 표시가 없어도 검증된다.

### Tests for User Story 1 ⚠️

> 먼저 쓰고, 실패하는 것을 확인한 뒤 구현한다.

- [ ] T010 [P] [US1] `AttemptLimits.record_mismatch` 단위 검증을 `backend/tests/unit/test_attempt_limits_mismatch.py` 에 작성한다 — 연속 실패 계수가 오르지 않음, `last_failed_element` 가 바뀌지 않음, **앞선 실패의 연속성이 초기화되지도 않음**, 총 호출 상한에는 걸림 (contracts/tool-surface.md C-4·C-5)
- [ ] T011 [P] [US1] 도구 반환 계약 검증을 `backend/tests/contract/test_assert_condition_mismatch.py` 에 작성한다 — 어긋남이면 `{"ok": true, "assertion_failed": true, ...}` 이고 Step 이 기록됨, 참조 해석 실패면 `{"error": ...}` 이고 Step 이 기록되지 않음 (FR-007)
- [ ] T012 [P] [US1] 불변식 검사를 `backend/tests/unit/test_mismatch_isolation.py` 에 작성한다 — `itb/execution/step_executor.py` 와 `itb/generator/playwright_gen.py` 소스에 `mismatch` 참조가 없음 (contracts/tool-surface.md C-2·C-3 · 헌법 원칙 I·V)
- [ ] T013 [P] [US1] AI 작성 통합 검증을 `backend/tests/integration/test_expected_value_kept.py` 에 작성한다 — 드라이버를 갈아 끼워(`backend/tests/us4_support.py` 방식) 자격 증명 없이 돌린다. 기대값이 지시문의 값으로 남는지, 어긋남 후에도 작성이 계속되는지 (US1 AS-1·AS-2·AS-3)

### Implementation for User Story 1

- [ ] T014 [US1] `AttemptLimits.record_mismatch(element)` 를 `backend/src/itb/authoring/tools.py` 에 추가한다 — 연속 실패 계수와 `last_failed_element` 를 **둘 다 건드리지 않는다.** 왜 `record_success` 를 부르지 않는지를 docstring 에 남긴다 (research.md R5)
- [ ] T015 [US1] `BrowserToolbox._execute` 에 `keep_on_failure: bool = False` 키워드 인자를 더하고 실패 분기를 가른다 (`backend/src/itb/authoring/tools.py`) — 켜져 있으면 `StepFailure` 에서 `mismatch` 를 채운 Step 을 기록하고 `record_mismatch` 를 부른다. 진행 알림 문구는 `— 기대와 다름`. T014 에 의존
- [ ] T016 [US1] `BrowserToolbox.assert_condition` 이 `_execute(..., keep_on_failure=True)` 로 부르게 하고, 어긋남 반환값에 `assertion_failed`·`observed`·`note` 를 싣는다 (`backend/src/itb/authoring/tools.py`). `observed` 는 `Scrubber` 를 거친 실패 설명이며 4000자에서 자르고 `truncated` 를 표시한다. T015 에 의존
- [ ] T017 [P] [US1] `SYSTEM_PROMPT` 를 `backend/src/itb/authoring/agent.py` 에서 고친다 — 「성공한 동작만 테스트로 남습니다」를 동작 Step 한정으로 좁히고, **검증 전용 절을 새로 연다** (contracts/tool-surface.md §3 의 문면 그대로)
- [ ] T018 [P] [US1] `NL_STEP_SYSTEM_HINT` 에 같은 규칙의 요약본을 더한다 (`backend/src/itb/authoring/nl_step.py`) — 일시정지 중 자연어 Step 추가도 같은 경로를 겪는다 (research.md R12)
- [ ] T019 [US1] `TOOL_SCHEMAS` 의 `assert_condition` 설명에 「기대와 달라도 기록된다」를 더한다 (`backend/src/itb/authoring/tools.py`) — 개발용 드라이버가 보는 문구도 제품 경로와 같아야 한다

**Checkpoint**: 기대값이 지켜지고 어긋난 검증이 정의에 남는다. 화면은 아직 그것을 모른다

---

## Phase 4: User Story 6 - 실패한 검증이 그 뒤를 가리지 않는다 (Priority: P1)

**Goal**: 검증 실패가 실행을 멈추지 않아, 저장된 스텝이 끝까지 돈다.

**Independent Test**: 앞쪽에 실패하는 검증이 있는 정의를 재실행해, 뒤 Step 들이 `실행 안 함`
이 아니라 실제 결과를 갖는지 확인한다. **AI 가 필요 없다** — 손으로 만든 정의로 검증된다.

**의존**: Phase 2 만. US1 과 병렬 가능

### Tests for User Story 6 ⚠️

- [ ] T020 [P] [US6] 계속 진행 통합 검증을 `backend/tests/integration/test_assertion_does_not_halt.py` 에 작성한다 — 중간 검증이 실패하는 정의에서 뒤 Step 이 모두 실행되고(US6 AS-1), 결말은 실패이며(AS-2), 동작 Step 실패는 여전히 멈춘다(AS-3)
- [ ] T021 [P] [US6] FR-037 회귀 검증을 `backend/tests/integration/test_run_controls_unchanged.py` 에 작성한다 — 표의 **8종을 전부** 확인한다: 재시도 · 건너뛰기(`PARTIAL_PASS`) · 인수 후 재개 · 부분 실행(`RunScope.PARTIAL` 과 앞선 Step 의 `SKIPPED`) · 중지(검증 실패 직후에도) · 일시정지·재개 · 세션 유실 · 실행 속도 조절
- [ ] T022 [P] [US6] `failed_index` 의미 보존을 `backend/tests/unit/test_failed_index_meaning.py` 에 고정한다 — 검증이 여러 번 실패해도 「멈춘 자리」가 만들어지지 않음 (FR-038)

### Implementation for User Story 6

- [ ] T023 [US6] `Runner.run_step()` 의 `StepFailure` 경로를 `backend/src/itb/execution/runner.py` 에서 가른다 — `AssertionStep` 이면 `True`(계속)를 돌려주고 **`failed_index` 와 `_failure_tab` 을 설정하지 않는다.** 그 이유(멈춘 자리 ≠ 실패한 Step)를 주석으로 남긴다 (research.md R8)
- [ ] T024 [US6] T002 가 만든 목록의 기존 검증을 새 기대로 고친다 — **지우거나 건너뛰지 않는다**(헌법 품질 게이트 4). 각 수정에 「020 FR-033 으로 기대가 바뀌었다」를 적는다

**Checkpoint**: 저장된 스텝이 끝까지 돈다. 결과는 아직 알려진 결함과 회귀를 구분하지 않는다

---

## Phase 5: User Story 2 - 작성이 끝나면 결함 후보가 눈에 띈다 (Priority: P1)

**Goal**: 작성 직후 사용자가 몇 건이 어긋났는지, 어느 Step 인지, 무엇을 기대했는지 본다.

**Independent Test**: US1 로 만든 정의를 열어 종료 알림과 Step 목록·상세를 확인한다.
재실행하지 않아도 검증된다.

**의존**: Phase 3 (US1) · T009(생성 타입)

### Tests for User Story 2 ⚠️

- [ ] T025 [P] [US2] `ai_finished` 이벤트 계약 검증을 `backend/tests/contract/test_ai_finished_mismatch_count.py` 에 작성한다 — 어긋남이 있으면 `mismatch_count` 가 실리고, **0건이면 필드 자체가 없다** (FR-013)
- [ ] T026 [P] [US2] Step 목록·상세 표시 검증을 `frontend/tests/StepMismatchDisplay.test.tsx` 에 작성한다 — 어긋난 검증 행이 구별되고, 상세에 기대값과 관찰값이 함께 나오며, 잘린 경우 그 사실이 보인다
- [ ] T027 [P] [US2] 민감값 검증을 `backend/tests/unit/test_mismatch_scrubbing.py` 에 작성한다 — 비밀번호 칸을 대상으로 한 검증의 `observed` 에 실제 값이 남지 않는다 (FR-015)

### Implementation for User Story 2

- [ ] T028 [US2] 어긋남 건수를 세어 `ai_finished` 에 싣는다 — 세는 주체를 `backend/src/itb/authoring/compiler.py` 의 `StepCompiler` 로 두고(`count` 의 선례), `backend/src/itb/api/routes/sessions.py` 의 `emit("ai_finished", ...)` 에 0 초과일 때만 더한다
- [ ] T029 [P] [US2] 결함 후보 칩을 `frontend/src/components/Badges.tsx` 에 더한다 — 008 확정 디자인의 `.chip` 변형을 쓰고 **새 시각 요소를 만들지 않는다**. 색 역할은 `frontend/src/theme/tone.ts`, 문구는 `frontend/src/lib/wording.ts` 가 정한다
- [ ] T030 [US2] Step 목록 행에 칩을 붙인다 (`frontend/src/components/workbench/StepList.tsx`). T029 에 의존
- [ ] T031 [US2] Step 상세에 기대값과 작성 시점 관찰값을 나란히 표시한다 (`frontend/src/components/workbench/StepDetail.tsx`) — 잘린 경우 그 사실도. 민감값은 **다시 거르지 않는다** (저장 시점에 이미 걸렀다)
- [ ] T032 [US2] 작성 종료 화면이 어긋남 건수를 보여주게 한다 (`frontend/src/pages/SessionScreen.tsx` 또는 `frontend/src/components/workbench/AiAuthoringPanel.tsx` 중 종료 알림을 그리는 쪽)

**Checkpoint**: 작성 직후 결함 후보가 보인다. MVP 로서 US1+US6+US2 가 완결된다

---

## Phase 6: User Story 3 - 재실행이 알려진 결함과 회귀를 구분한다 (Priority: P2)

**Goal**: 실패한 검증이 「원래 알던 것」과 「오늘 깨진 것」으로 갈린다.

**Independent Test**: 어긋남 표시가 있는 정의와 없는 정의를 각각 재실행해 분류를 확인한다.

**의존**: Phase 4 (US6) · Phase 2

### Tests for User Story 3 ⚠️

- [ ] T033 [P] [US3] `classify_assertion` 판정표 전수 검증을 `backend/tests/unit/test_classify_assertion.py` 에 작성한다 — data-model.md §3 의 **여섯 줄 전부** (건너뜀·실행 안 함·검증 아닌 Step 포함)
- [ ] T034 [P] [US3] 결과 화면 제시 검증을 `frontend/tests/ResultAssertionClass.test.tsx` 에 작성한다 — 회귀가 알려진 결함보다 먼저 나오고, **0건인 분류는 실리지 않는다** (FR-019·FR-020)

### Implementation for User Story 3

- [ ] T035 [P] [US3] 순수 함수 `classify_assertion(step, result)` 와 `counts_by_class(steps, results)` 를 `backend/src/itb/domain/run_result.py` 에 추가한다 — `decide_outcome` 의 선례를 따른다. **건수는 저장하지 않는다** (research.md R7)
- [ ] T036 [US3] `Runner` 가 Step 결과를 확정할 때 `assertion_class` 를 채우게 한다 (`backend/src/itb/execution/runner.py`). T035 에 의존
- [ ] T037 [US3] 결과 화면에 분류를 제시한다 (`frontend/src/pages/ResultView.tsx`) — 회귀 먼저·강하게, 알려진 결함 다음·약하게, 해소됨은 안내로. 요약줄 형식은 contracts/execution.md §4
- [ ] T038 [P] [US3] 분류 라벨을 `frontend/src/lib/wording.ts` 에 둔다 — 화면이 문구를 직접 만들면 화면마다 다른 말이 생긴다 (005 U-20 의 선례)

**Checkpoint**: 한 번의 실행으로 회귀의 존재와 위치를 안다 (SC-009)

---

## Phase 7: User Story 4 - 결함으로 막히면 그 사실이 전해진다 (Priority: P2)

**Goal**: 「제품이 지시문과 다르게 동작해 막혔다」가 「AI 가 모른다」와 구별된다.

**Independent Test**: 지시문이 요구한 화면 전이가 일어나지 않는 고정 대상으로 작성을 돌려,
막힘 사유의 종류와 답변 칸의 부재를 확인한다.

**의존**: Phase 2 (T007)

### Tests for User Story 4 ⚠️

- [ ] T039 [P] [US4] 막힘 종류 계약 검증을 `backend/tests/contract/test_blocked_kind.py` 에 작성한다 — `kind="product_mismatch"` 이면 `question` 이 **버려지고**(FR-024), 인식하지 못한 값은 `needs_input` 으로 떨어지며, 기존 세 종류의 동작이 그대로다(FR-025)
- [ ] T040 [P] [US4] 프론트엔드 검증을 `frontend/tests/BlockedKindPanel.test.tsx` 에 작성한다 — `product_mismatch` 면 답변 칸이 열리지 않고, `needs_input` 이면 현행대로 열린다

### Implementation for User Story 4

- [ ] T041 [US4] `report_blocked(reason, question="", kind="needs_input")` 로 인자를 더하고 `blocked_kind` 를 남긴다 (`backend/src/itb/authoring/tools.py`). **도구 개수를 늘리지 않는다** — `TOOL_NAMES` 16종이 그대로여야 하고 `test_tool_surface.py` 가 통과해야 한다. `TOOL_SCHEMAS` 문구도 함께 고친다
- [ ] T042 [US4] `AgentOutcome.blocked_kind` 를 더하고 `_drive()` 의 BLOCKED 경로에서 채운다 (`backend/src/itb/authoring/agent.py`). T041 에 의존
- [ ] T043 [US4] `ai_blocked` 이벤트에 `kind` 를 **항상** 싣는다 (`backend/src/itb/api/routes/sessions.py` · `backend/src/itb/api/ws/session_events.py`)
- [ ] T044 [US4] 화면이 `kind === "product_mismatch"` 일 때 답변 칸을 열지 않게 한다 (`frontend/src/components/workbench/AiAuthoringPanel.tsx` 및 선택지를 그리는 곳). 나머지 세 선택지(재시도·건너뛰기·인수)는 그대로 둔다 (FR-026)

**Checkpoint**: 사용자가 알림 문구만으로 자기가 알려 줄 것이 없음을 안다 (SC-005)

---

## Phase 8: User Story 5 - 결함이 고쳐지면 표시를 정리한다 (Priority: P3)

**Goal**: 사람이 어긋남 표시를 걷어내, 이후 같은 실패가 회귀로 잡히게 한다.

**Independent Test**: 표시를 걷어낸 뒤 같은 검증이 실패할 때 분류가 `regression` 으로
바뀌는지 확인한다.

**의존**: Phase 6 (US3) — 분류가 있어야 걷어낸 효과를 확인할 수 있다

### Tests for User Story 5 ⚠️

- [ ] T045 [P] [US5] 걷어내기 검증을 `backend/tests/unit/test_clear_mismatch.py` 에 작성한다 — 걷어내면 `mismatch` 가 `None` 이 되고 기록도 함께 사라지며(FR-029), 제품이 **자동으로는 지우지 않는다**(FR-028)
- [ ] T046 [P] [US5] 분류 전환 통합 검증을 `backend/tests/integration/test_mismatch_cleared_becomes_regression.py` 에 작성한다 — 걷어낸 뒤 같은 실패가 `regression` 으로 분류된다

### Implementation for User Story 5

- [ ] T047 [US5] 어긋남 표시를 걷어내는 편집을 **기존 Step 편집 경로**로 구현한다 (`backend/src/itb/execution/step_edits.py` 의 순수 함수 + 그것을 부르는 API 경로) — 새 편집 방식을 만들지 않는다. 원칙 I 상 사람의 편집과 AI 의 편집이 같은 함수를 지나야 한다
- [ ] T048 [US5] Step 상세에 걷어내기 조작을 붙인다 (`frontend/src/components/workbench/StepDetail.tsx`). T047 에 의존
- [ ] T049 [P] [US5] 결과 화면의 `resolved` 안내에 「표시를 걷어낼 수 있습니다」를 담는다 (`frontend/src/pages/ResultView.tsx` · 문구는 `frontend/src/lib/wording.ts`) — FR-022 가 요구하는 신호

**Checkpoint**: 모든 사용자 스토리가 독립적으로 동작한다

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 여러 스토리에 걸친 보증과 문서.

- [ ] T050 [P] `docs/prd.md` 의 Replay Success Rate 정의에 판정 단위 문장을 더한다 — 「판정은 Step 단위다. 작성 시점에 어긋남으로 기록된 검증 Step 은 분모에서 제외하고, 같은 테스트의 나머지 Step 은 분모에 남는다」. **목표치(≥95%)는 바꾸지 않는다** (research.md R11 · FR-030)
- [ ] T051 [P] 공유 왕복 검증을 `backend/tests/integration/test_share_preserves_mismatch.py` 에 작성한다 — 내보내기·가져오기 후 `mismatch` 가 동일하고, 020 이전 번들은 `None` 으로 읽힌다 (FR-017)
- [ ] T052 [P] Playwright 내보내기 검증을 `backend/tests/integration/test_export_keeps_assertion.py` 에 작성한다 — 어긋난 검증이 통상의 검증과 **동일하게** 생성되고, 제품 내 실행과 같은 결과를 낸다 (FR-016 · SC-007 · 헌법 원칙 V)
- [ ] T053 [P] 라운드트립 무결성 검증 — `record → store → replay → export → run` 이 일관된 결과를 내는지 확인한다 (헌법 품질 게이트 2). Step DSL 을 바꿨으므로 필수다
- [ ] T054 [P] 재실행 경로에 LLM 호출이 없음을 재확인한다 — 기존 `backend/tests/integration/test_replay_no_llm.py` 가 계속 통과해야 한다 (헌법 원칙 II)
- [ ] T055 [quickstart.md](./quickstart.md) 의 §2·§3·§6 을 사람이 손으로 수행하고 결과를 기록한다
- [ ] T056 전량 검증을 돌린다 — `backend/scripts/test-backend.sh` 와 `cd frontend && npm run typecheck && npm test`. T003 의 기준선과 대조해 **새로 깨진 것이 없는지** 확인한다
- [ ] T057 [checklists/invariants.md](./checklists/invariants.md) 55항목을 검토자가 평가한다 — 이 작업은 항목을 `[x]` 로 바꾸는 것이 아니라, **비어 있는 항목이 실제 누락인지 판단**하는 것이다

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존 없음
- **Foundational (Phase 2)**: Setup 후. **모든 사용자 스토리를 막는다**
- **US1 (Phase 3)** · **US6 (Phase 4)**: Phase 2 후. **서로 독립 — 병렬 가능**
- **US2 (Phase 5)**: Phase 3(US1) 후 — 표시할 어긋남이 있어야 한다
- **US3 (Phase 6)**: Phase 4(US6) 후 — 끝까지 도는 실행이 있어야 분류가 의미를 갖는다
- **US4 (Phase 7)**: Phase 2 후. **다른 스토리와 독립 — 언제든 병렬 가능**
- **US5 (Phase 8)**: Phase 6(US3) 후 — 걷어낸 효과를 분류로 확인한다
- **Polish (Phase 9)**: 원하는 스토리가 전부 끝난 뒤

### User Story Dependencies

```
Phase 2 ──┬── US1 (P1) ── US2 (P1)
          ├── US6 (P1) ── US3 (P2) ── US5 (P3)
          └── US4 (P2)
```

**US4 는 어디에도 의존하지 않는다.** 인력이 여유 있으면 가장 먼저 병렬로 붙일 수 있다.

### Within Each User Story

- 검증을 먼저 쓰고 **실패하는 것을 확인한 뒤** 구현한다
- 도메인 → 서비스 → 경로 → 화면
- 한 스토리를 끝내고 다음 우선순위로

### Parallel Opportunities

- Phase 1 의 T002·T003
- Phase 2 의 T004·T006·T007·T008 (T005 는 T004 에, T009 는 T005·T006 에 의존)
- 각 스토리의 `[P]` 검증 작업 전부
- **US1 과 US6 전체** — 다른 파일을 건드리고 서로를 참조하지 않는다
- **US4 전체** — 다른 모든 스토리와 독립
- Phase 9 의 T050~T054

---

## Parallel Example: Phase 2 Foundational

```bash
# 도메인 타입을 함께 만든다 (서로 다른 파일):
Task: "AuthoringMismatch 모델을 backend/src/itb/domain/assertion.py 에 추가"
Task: "AssertionClass + StepResult.assertion_class 를 backend/src/itb/domain/run_result.py 에 추가"
Task: "BlockedKind 를 backend/src/itb/authoring/blocked.py 에 추가"
Task: "도메인 단위 검증을 backend/tests/unit/test_authoring_mismatch.py 에 작성"
```

## Parallel Example: US1 과 US6 동시 진행

```bash
# 개발자 A — 작성 경로 (backend/src/itb/authoring/*)
Task: "AttemptLimits.record_mismatch"
Task: "_execute 의 keep_on_failure 분기"
Task: "SYSTEM_PROMPT 검증 절"

# 개발자 B — 실행 경로 (backend/src/itb/execution/*)
Task: "run_step 의 AssertionStep 분기"
Task: "FR-037 실행 제어 8종 회귀 검증"
```

---

## Implementation Strategy

### MVP First (US1 + US6 + US2 — P1 셋)

1. Phase 1 Setup
2. Phase 2 Foundational (**필수 · 전부를 막는다**)
3. Phase 3 (US1) 과 Phase 4 (US6) — 병렬
4. Phase 5 (US2)
5. **멈추고 확인**: quickstart §2 를 수행한다. 기대값이 지켜지고, 실행이 끝까지 돌며,
   사용자가 결함 후보를 본다

이 지점에서 **사용자가 제기한 문제 자체는 해결된다.** 남은 셋은 그 뒤에 생기는 운영
문제(구분·보고·정리)를 다룬다.

### Incremental Delivery

1. Setup + Foundational → 기반 완료
2. US1 + US6 + US2 → **MVP**
3. US3 → 회귀와 알려진 결함이 갈린다
4. US4 → 결함으로 막힌 것이 구별된다
5. US5 → 고쳐진 결함의 표시를 정리한다

### Parallel Team Strategy

1. 팀이 Setup + Foundational 을 함께 끝낸다
2. 그 뒤:
   - 개발자 A: US1 → US2
   - 개발자 B: US6 → US3 → US5
   - 개발자 C: US4 → Phase 9 의 검증 작업
3. Phase 9 는 모두가 끝난 뒤 함께

---

## Notes

- `[P]` = 다른 파일, 의존 없음
- 각 스토리는 단독으로 완결·검증 가능해야 한다
- 구현 전에 검증이 실패하는 것을 확인한다
- 작업마다 또는 논리적 묶음마다 커밋한다
- 어느 체크포인트에서든 멈추고 스토리 단위로 확인할 수 있다
- **T024 는 특별히 주의한다** — 기존 검증을 고치는 작업이다. 지우거나 건너뛰면 헌법 품질
  게이트 4 위반이다
- **`checklists/invariants.md` 는 검토자 소유다.** 구현 중에 `[x]` 로 바꾸지 않는다
