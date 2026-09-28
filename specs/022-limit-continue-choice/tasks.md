---

description: "Task list template for feature implementation"
---

# Tasks: 022 — 예산 소진을 막힘과 갈라 말한다

**Input**: Design documents from `/specs/022-limit-continue-choice/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/blocked-view.md](./contracts/blocked-view.md)

**Tests**: 포함한다. 이 저장소의 관행이며, 특히 **기존 막힘 화면이 바뀌지 않음**(SC-005)과
**이어가기가 이미 한 일을 반복하지 않음**(SC-001)은 테스트 없이 지킬 수 없다.

**Organization**: 사용자 이야기 단위로 묶는다. 각 단계 끝에서 독립적으로 검증 가능하다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 완료되지 않은 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 이야기인가 (US1·US2·US3)
- 파일 경로를 반드시 적는다

## Path Conventions

- 백엔드: `backend/src/itb/...` · 테스트 `backend/tests/...`
- 프론트: `frontend/src/...` · 테스트 `frontend/tests/...`

---

## Phase 1: Setup

**Purpose**: 새 구조를 만들지 않는다. 시작 상태를 고정하는 것이 전부다.

- [X] T001 시작 시점의 기존 실패를 기록한다 — `cd backend && bash scripts/test-backend.sh` 와 `.venv/bin/python -m ruff check src tests` 를 돌려, 이 기능과 무관한 실패 목록을 [quickstart.md](./quickstart.md) 「자동 검증」 절과 대조한다. **새 실패를 기존 실패와 섞지 않기 위한 기준선**이다 (021 작업분: `test_ui_surface.py` AS-009·025·037·046, ruff 4건)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 세 이야기가 모두 딛고 서는 자료구조. 이것 없이는 어느 이야기도 시작할 수 없다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 US1~US3 작업을 시작하지 않는다

- [X] T002 `backend/src/itb/authoring/tools.py` 의 `BlockedKind` 에 `BUDGET_EXHAUSTED = "budget_exhausted"` 를 더한다. docstring 에 **`product_mismatch` 와 묶지 않는 이유**를 적는다 — 둘 다 「사람이 알려 줄 것이 없다」지만 이어가기의 의미가 정반대다(제품 불일치는 이어가도 같은 결과, 예산 소진은 진행된다). `DEFAULT_BLOCKED_KIND` 는 그대로 `NEEDS_INPUT` ([data-model.md](./data-model.md) §1)

- [X] T003 `backend/src/itb/authoring/tools.py` 의 `AttemptLimits` 에 `total_calls: int = 0` 과 `steps_at_attempt_start: int | None = None` 을 더한다. `record_call()` 이 `calls` 와 `total_calls` 를 **함께** 올린다 — 같은 자리에서 세므로 어긋날 수 없다는 근거를 docstring 에 적는다 ([research.md](./research.md) R2)

- [X] T004 `backend/src/itb/authoring/tools.py` 의 `reset()` 을 `reset_attempt(step_count: int | None = None)` 으로 바꾼다. **`total_calls` 를 지우지 않는다.** `step_count` 를 받으면 `steps_at_attempt_start` 에 넣는다 — `AttemptLimits` 는 Step 을 세지 않으므로 아는 쪽이 넘겨야 한다. docstring 에 하는 일이 「전부 되돌린다」에서 「이번 시도의 예산만 되돌린다」로 좁아졌음을 적는다

- [X] T005 `reset()` 호출부 네 곳을 `reset_attempt(...)` 로 바꾸고 현재 Step 수를 넘긴다 — 예산이 새로 주어지는 자리다 (FR-008) — `backend/src/itb/authoring/agent.py` 의 `chat`·`resume_with_answer`·`resume_after_takeover`(`self._count()` 를 넘긴다), `backend/src/itb/api/routes/sessions.py` 의 `_start_agent_note`(`w.compiler` 에서 얻는다). T004 의존

- [X] T006 `backend/src/itb/authoring/agent.py` 의 `AgentOutcome` 에 `total_tool_calls: int = 0` 과 `made_progress: bool | None = None` 을 더한다. docstring 에 **판정 시점의 값을 싣는 것이지 상태를 소유하는 것이 아니**라고 적는다 — `step_count`·`tool_calls` 가 이미 그렇다 ([data-model.md](./data-model.md) §3)

- [X] T007 [P] `backend/tests/unit/test_attempt_limits.py` 를 넓힌다 — `total_calls` 가 `reset_attempt()` 를 **건너 남는가**, `calls` 는 0 이 되는가, `steps_at_attempt_start` 가 넘긴 값으로 갱신되는가, `MAX_TOOL_CALLS == 40` 은 그대로인가. **세 번 연속 `reset_attempt()` 해도 막히지 않는지**도 본다 (FR-010) — 「횟수 제한을 두지 않는다」는 아무것도 하지 않음으로 지켜지므로, 나중에 누가 제한을 넣어도 울릴 것이 없다. T003·T004 의존

**Checkpoint**: 자료구조가 준비됐다. 아직 아무 동작도 바뀌지 않았다 — 기존 테스트가 모두 통과해야 한다

---

## Phase 3: User Story 1 — 이어가면 남은 일을 한다 (Priority: P1) 🎯 MVP

**Goal**: 상한 도달을 `budget_exhausted` 로 판정하고, 이어갈 때 AI 에게 **「남은 지시를
이어서」**를 보낸다. 지금은 「같은 동작을 다시」가 가서 이미 성공한 일을 반복한다.

**Independent Test**: 상한에 닿은 세션에서 이어가기를 눌러, 마지막으로 성공한 동작이
반복되지 않고 남은 지시가 진행되는지 확인한다.

### Tests for User Story 1 ⚠️

> 먼저 쓰고, **실패하는 것을 확인한 뒤** 구현한다

- [X] T008 [P] [US1] `backend/tests/unit/test_budget_exhausted_kind.py` 를 만든다 — 도구 호출 상한 도달과 `DriverTurnLimitError` 가 **둘 다** `budget_exhausted` 로 판정되고(FR-001·FR-004), 같은 요소 연속 실패는 **아니며**(FR-002), 모델이 `report_blocked` 로 어떤 문구를 신고하든 아니다(FR-003)

- [X] T009 [P] [US1] `backend/tests/integration/test_budget_resume_instruction.py` 를 만든다 — `budget_exhausted` 막힘에서 `retry` 를 고르면 에이전트가 받는 지시에 **「이어서」**가 들어 있고 **「다시 시도」가 없으며**, 예산 소진이 **아닌** 막힘에서는 **지금 그대로**인지 (FR-006·FR-007 · US1 시나리오 3). **이어가기 전후 Step 수가 같은지도 함께 본다** (FR-009·SC-003) — `reset_attempt` 개명이 바로 이 자리를 지나가므로 회귀 위험이 실재한다. 도구 호출이 반복되지 않는지는 대본 드라이버로 확인한다 (SC-001)

### Implementation for User Story 1

- [X] T010 [US1] `backend/src/itb/authoring/tools.py` 의 `record_call()` 이 상한 도달로 `exceeded_reason` 을 세울 때, 그것이 **예산 소진임을 남긴다.** `record_failure()` 의 연속 실패는 남기지 않는다 — 둘은 같은 필드(`exceeded_reason`)를 쓰지만 종류가 다르다 (FR-002)

- [X] T011 [US1] `backend/src/itb/authoring/agent.py` 의 `_drive` 가 막힘 결말을 만들 때 `blocked_kind` 를 정한다 — 예산 소진이면 `BUDGET_EXHAUSTED`, 모델이 신고한 막힘이면 `toolbox.blocked_kind` 를 그대로. **제품이 센 값이 모델의 말을 이긴다** (FR-003). T010 의존

- [X] T012 [US1] `backend/src/itb/authoring/agent.py` 의 `DriverTurnLimitError` 처리부(커밋 `24dcef9` 가 만든 자리)도 `BUDGET_EXHAUSTED` 로 보낸다 — 두 상한이 사용자에게 같게 보여야 한다 (FR-004)

- [X] T013 [US1] `backend/src/itb/api/routes/sessions.py` 의 `ai_choice` 에서 `retry` 의 지시를 막힘 종류로 가른다. 종류는 `w.last_blocked` 에서 읽는다 — `_blocked_view` 가 이미 같은 자리를 읽고 있으므로 **새 저장소를 만들지 않는다**. 예산 소진이면 「남은 지시를 이어서 수행하세요. 이미 끝낸 동작은 다시 하지 마세요.」, 그 밖이면 지금 문장 그대로 ([contracts/blocked-view.md](./contracts/blocked-view.md) §5). T011 의존

- [X] T014 [US1] `backend/tests/unit/test_budget_exhausted_kind.py` 와 `backend/tests/integration/test_budget_resume_instruction.py` 가 통과하는지 확인하고, 통과하지 않으면 구현을 고친다

**Checkpoint**: 이어가기가 올바른 일을 시킨다. 화면은 아직 지금과 같다 — 백엔드만으로 SC-001 이 지켜진다

---

## Phase 4: User Story 2 — 화면이 상황에 맞는 말을 한다 (Priority: P2)

**Goal**: 예산 소진 화면이 제목·칸·선택지에서 그 상황의 말을 쓴다. **예산 소진이 아닌
막힘은 지금과 한 글자도 달라지지 않는다.**

**Independent Test**: 예산 소진 세션과 요소를 못 찾아 막힌 세션을 나란히 열어, 전자는
알려 주기 칸이 없고 후자는 지금과 같은지 확인한다.

### Tests for User Story 2 ⚠️

- [ ] T015 [P] [US2] `frontend/tests/BudgetExhaustedBlocked.test.tsx` 를 만든다 — `kind: "budget_exhausted"` 일 때 알려 주기 칸이 **없고**(FR-013), 제목이 「막혔습니다」가 **아니며**(FR-012), 「이 동작 건너뛰기」가 **보이지 않고**(FR-015), 이어가기 버튼 글자가 「다시」가 아닌지(FR-014). `frontend/tests/ProductMismatchBlocked.test.tsx` 가 같은 구조의 선례다

- [ ] T016 [P] [US2] `frontend/tests/AiBlockedAnswer.test.tsx` 에 **회귀 검증**을 더한다 — `kind` 가 `needs_input`·`product_mismatch` 일 때 화면이 **지금과 같은지** (FR-016 · SC-005)

### Implementation for User Story 2

- [ ] T017 [US2] `backend/src/itb/api/routes/sessions.py` 의 `BlockedView` 와 `backend/src/itb/authoring/blocked.py` 의 `ai_blocked` 이벤트가 **같은 새 필드**를 싣게 한다 (FR-005 — 구별이 화면까지 전달된다). `choices` 는 **줄이지 않는다** — 받을 수 있는 것과 권하는 것은 다른 사실이며, 걸러내기는 화면이 한다 ([contracts/blocked-view.md](./contracts/blocked-view.md) §1)

- [ ] T018 [US2] `frontend/src/pages/SessionScreen.tsx` 가 `BlockedView` 의 새 필드를 화면 모델로 옮긴다. 없으면 그리지 않는 **선택적 읽기**여야 한다 — 구버전 백엔드와 섞여도 깨지지 않는다 ([contracts/blocked-view.md](./contracts/blocked-view.md) §3)

- [ ] T019 [US2] `frontend/src/components/workbench/WorkArea.tsx` 에 예산 소진 분기를 더한다. **기존 `product_mismatch` 분기를 건드리지 않는다.** 제목·사유 문구, 알려 주기 칸 닫기, 선택지 걸러내기(`skip` 제외)를 한 자리에서 판단한다. 새 부품을 만들지 않고 기존 `Button` 을 쓴다

- [ ] T020 [US2] `frontend/src/components/workbench/WorkArea.tsx` 의 `AI_CHOICE_LABEL` 을 막힘 종류에 따라 갈라 쓴다 — 예산 소진에서 `retry` 는 「이어서 계속」, `abort` 는 「여기까지」로 읽힌다 (FR-014). 사전에 없는 값이 값 그대로 보이는 **기존 안전장치를 유지한다**

- [ ] T021 [US2] `backend/src/itb/api/routes/sessions.py` 의 `ai_choice` 에서 예산 소진 막힘에도 `answer` 경로가 살아 있는지 확인한다 (FR-011) — 화면이 칸을 열지 않을 뿐 서버가 답변을 거절해서는 안 된다

- [ ] T022 [US2] `frontend/tests/BudgetExhaustedBlocked.test.tsx` 와 `frontend/tests/AiBlockedAnswer.test.tsx` 가 통과하는지 확인한다

**Checkpoint**: 예산 소진과 기존 막힘이 화면에서 갈린다. SC-004·SC-005 가 지켜진다

---

## Phase 5: User Story 3 — 얼마나 썼는지 보고 판단한다 (Priority: P3)

**Goal**: 누적 동작 수·Step 수·진전 여부를 막힘 정보에 실어 화면에 보인다.

**Independent Test**: 두 번 이어간 세션에서 누적 수치가 합쳐지고, Step 이 늘지 않은
이어가기 뒤에는 진전 없음 안내가 뜨는지 확인한다.

### Tests for User Story 3 ⚠️

- [ ] T023 [P] [US3] `backend/tests/integration/test_budget_cumulative.py` 를 만든다 — 이어가기를 거쳐 `total_tool_calls` 가 **누적되고**(FR-018), 새 지시문에서 **0 으로 돌아가며**, 화면을 새로 고쳐 얻는 `BlockedView` 에도 같은 값이 실리는지(FR-022)

- [X] T024 [P] [US3] `backend/tests/unit/test_progress_detection.py` 를 만든다 — Step 이 늘었으면 `made_progress is True`, 늘지 않았으면 `False`, **첫 시도면 `None`**(판정 불가와 진전 없음은 다른 사실). [data-model.md](./data-model.md) §2

- [ ] T025 [P] [US3] `frontend/tests/BudgetExhaustedBlocked.test.tsx` 에 더한다 — 누적·Step 수가 보이고, `made_progress === false` 일 때만 진전 없음 안내가 뜨며(`null` 에는 뜨지 않는다), 안내가 떠도 **이어가기 버튼이 눌리는지**(FR-021)

### Implementation for User Story 3

- [X] T026 [US3] `backend/src/itb/authoring/agent.py` 의 `_drive` 가 결말에 `total_tool_calls` 와 `made_progress` 를 싣는다. 진전은 `self._count() > limits.steps_at_attempt_start` 이며, 시작 값이 `None` 이면 `made_progress` 도 `None`. T006·T011 의존

- [X] T027 [US3] ~~새 지시문에서 누적이 0 으로 돌아가는 자리를 만든다~~ — **코드 변경 불필요로 판정.** `run()` 은 이어가기(`_start_agent_note` → `_run_agent(instruction=note)`)도 지나므로 거기서 누적을 지우면 FR-018 이 깨진다. 새 지시문은 `_start_agent` 를 통해 **새 세션**에서 오고, 그때 `AttemptLimits` 가 새로 만들어져 누적이 이미 0 이다 ([data-model.md](./data-model.md) §5)

- [ ] T028 [US3] `backend/src/itb/api/routes/sessions.py` 의 `BlockedView` 와 `backend/src/itb/authoring/blocked.py` 의 `ai_blocked` 에 `total_tool_calls`·`step_count`·`made_progress` 를 싣는다. **두 통로가 같은 값을 실어야 한다** — 한쪽만 실으면 새로 고친 화면이 수치를 잃는다. T017 의존

- [ ] T029 [US3] `frontend/src/components/workbench/WorkArea.tsx` 가 누적·Step 수를 예산 소진 안내 안에 그린다 (FR-017·FR-019). 진전 없음은 `made_progress === false` 일 때만 (FR-020). 안내는 이어가기를 **막지 않는다** (FR-021)

- [ ] T030 [US3] `backend/tests/integration/test_budget_cumulative.py`·`backend/tests/unit/test_progress_detection.py`·`frontend/tests/BudgetExhaustedBlocked.test.tsx` 가 통과하는지 확인한다

**Checkpoint**: 세 이야기가 모두 동작한다

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T031 [P] 020 과의 정합을 확인한다 — `product_mismatch` 막힘의 동작·화면·문구가 **하나도 바뀌지 않았는지** (`frontend/tests/ProductMismatchBlocked.test.tsx` 와 020 의 관련 백엔드 테스트)

- [ ] T032 [P] 호환을 확인한다 — 구버전 프론트(새 `kind` 를 모르는)가 `?? "needs_input"` 와 `else` 분기로 **지금 화면**이 되는지, 구버전 백엔드(새 필드를 안 보내는)에서 프론트가 표시를 생략하는지 ([contracts/blocked-view.md](./contracts/blocked-view.md) §3)

- [ ] T033 전량 검증 — `cd backend && bash scripts/test-backend.sh`, `cd frontend && npm test`, `.venv/bin/lint-imports`(계약 4개 유지), `.venv/bin/python -m ruff check src tests`. **T001 의 기준선과 대조해** 새 실패가 0 인지 확인한다

- [ ] T034 [quickstart.md](./quickstart.md) §1~§6 을 사람이 손으로 수행하고 결과를 기록한다 — 자동 검증이 덮지 못하는 것(문구가 읽히는지, 적어야 하는 것으로 보이지 않는지, 수치가 판단에 쓸 만한지)을 본다. **§2 가 가장 중요하다** (이어가기가 이미 한 일을 반복하지 않는지)

- [ ] T035 상한 값을 낮춰 확인했다면 **되돌렸는지** 확인한다 — `git diff backend/src/itb/authoring/tools.py` 로 `MAX_TOOL_CALLS`·`MAX_DRIVER_TURNS` 가 원래대로인지

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존 없음
- **Foundational (Phase 2)**: Setup 후. **모든 이야기를 막는다**
- **US1 (Phase 3)**: Foundational 후. 다른 이야기에 의존하지 않는다
- **US2 (Phase 4)**: Foundational 후. US1 없이도 화면은 갈라지지만, **US1 없이 US2 만
  내보내면 화면은 「이어서」라고 말하는데 서버는 「다시 시도」를 보낸다** — 순서대로 할 것
- **US3 (Phase 5)**: Foundational 후. T028 이 T017(US2)에 의존하므로 US2 뒤가 자연스럽다
- **Polish (Phase 6)**: 원하는 이야기가 모두 끝난 뒤

### Within Each User Story

- 테스트를 먼저 쓰고 **실패를 확인한 뒤** 구현한다
- 백엔드 판정 → 전달 → 화면 순서. 화면이 먼저 가면 보여 줄 값이 없다

### Parallel Opportunities

- T007 은 T003·T004 뒤에 다른 작업과 병렬
- T008·T009 (US1 테스트) 병렬
- T015·T016 (US2 테스트) 병렬 — 다른 파일
- T023·T024·T025 (US3 테스트) 병렬 — 다른 파일
- T031·T032 병렬

**병렬 불가**: T017·T019·T028·T029 는 같은 파일(`sessions.py`·`WorkArea.tsx`)을 고친다

---

## Parallel Example: User Story 1

```bash
# US1 테스트 둘을 함께
Task: "backend/tests/unit/test_budget_exhausted_kind.py 를 만든다"
Task: "backend/tests/integration/test_budget_resume_instruction.py 를 만든다"
```

---

## Implementation Strategy

### MVP First (US1 만)

1. Phase 1 Setup — 기준선 기록
2. Phase 2 Foundational — **모든 이야기를 막는다**
3. Phase 3 US1
4. **멈추고 검증**: [quickstart.md](./quickstart.md) §2 를 손으로. 이어가기가 이미 한 일을
   반복하지 않는가
5. 여기까지만으로도 **가장 해로운 결함(SC-001)이 사라진다** — 화면은 아직 지금과 같지만
   데이터 중복 생성이 멈춘다

### Incremental Delivery

1. Foundational → 자료구조 준비, 동작 변화 없음
2. US1 → 이어가기가 올바른 일을 시킨다 (**MVP**)
3. US2 → 화면이 상황에 맞는 말을 한다
4. US3 → 판단 근거가 보인다

---

## Notes

- `[P]` = 다른 파일, 의존 없음
- 각 작업 또는 논리적 묶음마다 커밋한다
- **T004 의 개명은 놓치면 즉시 터진다**(`AttributeError`) — 조용히 틀리지 않는 것이 이
  방식을 고른 이유다
- 기존 실패(021 작업분)를 새 실패와 섞지 말 것. T001 의 기준선이 그 판단의 근거다
