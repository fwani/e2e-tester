---

description: "Task list for 025 — 사람이 말한 것을 AI 가 같은 화면에서 본다"
---

# Tasks: 사람이 말한 것을 AI 가 같은 화면에서 본다 (025)

**Input**: Design documents from `specs/025-ai-instruction-context/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/)

**Tests**: 포함한다. 헌법 품질 게이트 3 이 요구하고, 이 기능에는 특별한 이유가 하나 더 있다 —
**지금 검증은 이력 유실을 잡지 못한다** (research R1). 가짜 드라이버가 SDK 의 messages 처리를
대체하기 때문이다. 그 빈칸을 메우는 것이 T004 다.

**Organization**: 사용자 이야기별로 묶는다. 각 이야기는 독립적으로 구현·검증·중단할 수 있다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 완료 안 된 것에 의존하지 않음)
- **[Story]**: 어느 사용자 이야기인가 (US1~US6)
- 파일 경로를 반드시 적는다

## Path Conventions

Web app 구조 — `backend/src/itb/`, `backend/tests/`, `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup — 기준선과 실측

**Purpose**: 고치기 전에 지금 상태를 수치로 남긴다. 이것이 없으면 끝에서 무엇이 달라졌는지
말할 수 없다.

- [ ] T001 시작 시점 전량 검증을 돌려 기준선을 `specs/025-ai-instruction-context/baseline.md` 에
      기록한다 — `cd backend && bash scripts/test-backend.sh` · `uv run ruff check src/ tests/` ·
      `uv run lint-imports` · `cd frontend && npx vitest run` · `npx tsc --noEmit`.
      **기존 실패를 새 실패와 섞지 않기 위한 것이다** (022 T001 과 같은 목적)
- [ ] T002 [P] 현행 관찰 한 번의 크기를 실측해 `baseline.md` 에 적는다 — 실제 화면에서
      `observe_page` 를 불러 요소 수·응답 바이트를 잰다. SC-008·SC-010 의 비교 기준이 된다
- [ ] T003 [P] 한 지시를 끝까지 수행시켜 모델에게 전달된 총 분량을 실측해 `baseline.md` 에
      적는다. SC-008 의 「늘지 않는다」가 무엇 대비인지를 정하는 값이다

**Checkpoint**: 기준선이 문서로 남았다. 이후 모든 수치는 이것과 비교한다.

---

## Phase 2: Foundational — SDK 의 계약을 못 박는다

**Purpose**: 이 기능의 전제가 SDK 의 동작이다. 그것이 바뀌면 설계가 통째로 흔들리므로
검증으로 고정한다.

**⚠️ CRITICAL**: T004 없이 US1 을 구현하면, 고친 뒤에도 유실이 다시 생겼을 때 아무도 모른다.

- [ ] T004 `backend/tests/contract/test_tool_runner_history.py` 에 **SDK 계약 검증**을 쓴다 —
      `BaseToolRunner` 에 messages 리스트를 넘기고 `append_messages` 뒤 **호출자의 리스트가
      수정되지 않음**을 단언한다. research R1 의 실측을 테스트로 고정하는 것이다.
      자격 증명 없이 돈다 (runner 객체만 만든다)
- [ ] T005 `set_messages_params` 로 접은 뒤 runner 가 그 위에 이어 붙이는지 실측하고 결과를
      `research.md` R4 의 「확인 필요」 자리에 적는다. **부정이면 US6(Phase 8)를 이번 증분에서
      뺀다** — 그 판단을 여기서 내린다
- [ ] T006 [P] `backend/tests/us4_support.py` 의 가짜 드라이버에 **주석으로 한계를 명시**한다 —
      이 드라이버는 SDK 의 messages 처리를 대체하므로 이력 유실을 잡지 못한다는 사실.
      다음 사람이 같은 함정에 빠지지 않게 한다

**Checkpoint**: SDK 계약이 검증으로 고정됐고, US6 의 실현 가능성이 판정됐다.

---

## Phase 3: User Story 1 — 지난 턴이 이어진다 (Priority: P1) 🎯 MVP

**Goal**: 한 턴이 끝날 때 그 턴의 수행 기록을 어시스턴트 차례로 이력에 남긴다. 재개가
막힌 자리에서 이어진다.

**Independent Test**: 세 동작 수행 후 막히게 하고 답을 준다. 재개 시점의 이력에 앞선 동작과
막힌 지점이 있는지, 이미 한 동작을 다시 하지 않는지 확인한다.

### Tests for User Story 1

- [ ] T007 [P] [US1] `backend/tests/unit/test_turn_journal.py` — 저널이 무엇을 남기고 무엇을
      남기지 않는지. **요소 참조·입력값·화면 요소 목록이 실리지 않음**을 단언한다 (FR-003·R2)
- [ ] T008 [P] [US1] `backend/tests/integration/test_resume_continuity.py` — 막힘 후 재개에서
      이력에 지난 턴 기록이 실리고 어시스턴트 차례가 존재함을 단언한다 (FR-001·FR-007)
- [ ] T009 [P] [US1] `backend/tests/unit/test_turn_journal.py` 에 **상한 접기** 검증을 더한다 —
      32KB 를 넘으면 오래된 턴부터 접히고 **생략이 명시**됨 (FR-006)

### Implementation for User Story 1

- [ ] T010 [US1] `backend/src/itb/authoring/journal.py` 를 만든다 — `ActionNote`·`BlockedNote`·
      `TurnRecord` 와, 그것을 문자열로 펴는 함수. **값을 읽는 자리를 하나로 묶는다**
      (016 `summary.py` 의 `_value_note` 와 같은 규칙)
- [ ] T011 [US1] `backend/src/itb/authoring/tools.py` 의 `BrowserToolbox` 에 **저널 수집**을
      더한다 — 각 도구가 이미 부르는 `_announce` 자리에서 `ActionNote` 를 쌓는다.
      **새 관찰 로직을 만들지 않는다**, 제품이 이미 아는 사실을 모은다 (R2)
- [ ] T012 [US1] `backend/src/itb/authoring/tools.py` — 막힘 신고(`report_blocked`)가 저널에
      `BlockedNote` 를 남기게 한다. 종류(`blocked_kind`)와 질문을 함께 (FR-002)
- [ ] T013 [US1] `backend/src/itb/authoring/agent.py` 의 `_drive` 끝에서 **어시스턴트 차례를
      이력에 추가**한다 — 저널 + `last_reply` 를 한 메시지로 (FR-001·FR-007·R3).
      **모든 종료 경로에서** 남아야 한다 (막힘·오류·완료). 취소는 예외 — 사용자가 끊은 것이다
- [ ] T014 [US1] `backend/src/itb/authoring/agent.py` — 턴 시작 시 저널을 비운다. 앞선 턴의
      기록이 이번 턴 기록에 섞이면 같은 동작이 두 번 실린 것으로 보인다
- [ ] T015 [US1] `backend/src/itb/authoring/agent.py` — 이력 총량이 상한을 넘으면 오래된 수행
      기록부터 접는다. **생략을 명시한다** (FR-006). 사용자 메시지는 접지 않는다
- [ ] T016 [US1] `backend/src/itb/authoring/agent.py` 의 `resume_with_answer`·
      `resume_after_takeover` 독스트링을 고친다 — 「앞서 무엇을 하다 막혔는지」가 **이제 실제로
      이력에 있다**는 사실로. 지금 문장은 구현되지 않은 의도를 서술하고 있다

**Checkpoint**: 막힘 후 재개가 이어진다. 이 하나만으로도 사용자가 겪던 증상의 큰 몫이 사라진다.

---

## Phase 4: User Story 3 — 사람이 가리킨 것을 AI 가 찾는다 (Priority: P1)

**Goal**: 관찰이 사람이 누를 수 있다고 인지하는 요소까지 포함하고, 화면 글자로 요소를 찾는
수단이 생긴다.

**Independent Test**: 클릭되는 `<div>`·`<li>`·`<td>` 화면에서 「그 글자를 클릭하라」고 지시한다.
AI 가 찾아 누르는지, 조상·자손이 중복으로 실리지 않는지 확인한다.

### Tests for User Story 3

- [ ] T017 [P] [US3] `fixtures/sample-app/` 에 **클릭되는 비의미 요소** 화면을 더한다 —
      `<div>` 트리 항목, `<td>` 행, 카드. `addEventListener` 로 붙이고 `onclick` 속성을 쓰지
      않는다 (실제 웹 앱과 같은 모양이라야 이 검증이 뜻을 갖는다)
- [ ] T018 [P] [US3] `backend/tests/e2e/test_actionable_elements.py` — 그 화면을 관찰했을 때
      비의미 요소가 목록에 실리고 `actionability: "cursor"` 가 붙는지 (FR-039·FR-040)
- [ ] T019 [P] [US3] 같은 파일에 **커서 상속 중복 제거** 검증 — 조상과 자손이 둘 다 실리지
      않고 **가장 바깥만** 실리는지 (R13 의 함정)
- [ ] T020 [P] [US3] 같은 파일에 `find_by_text` 검증 — 글자를 담은 요소와 반응하는 요소가
      **갈라져** 돌아오는지 (FR-042). **같은 글자가 여럿일 때 전부 돌아오는지**도 함께 —
      제품이 고르지 않는다는 것이 이 도구의 규칙이다 (contracts/observation.md §4)
- [ ] T021 [P] [US3] `backend/tests/e2e/test_actionable_elements.py` 에 **녹화 회귀** 검증 —
      같은 화면에서 사람이 조작했을 때 지금과 같은 Step 이 만들어지는지 (FR-045)

### Implementation for User Story 3

- [ ] T022 [US3] `backend/src/itb/recording/injected/recorder.js` 의 `__itbObserve` 에 **2단계
      후보 수집**을 더한다 — 1단계는 지금의 `INTERACTIVE`, 2단계는 보이는 텍스트를 갖거나
      이미지·아이콘인 요소 중 computed `cursor === "pointer"` 인 것.
      **`INTERACTIVE` 상수 자체는 건드리지 않는다** (녹화가 쓴다 · FR-045)
- [ ] T023 [US3] 같은 파일 — 2단계 후보에서 **조상 중에 같은 판정을 받은 것이 있으면 제외**한다.
      `cursor` 는 상속 속성이므로 이 처리가 없으면 목록이 몇 배로 부푼다 (R13)
- [ ] T024 [US3] 같은 파일 — 각 요소에 `actionability` (`semantic`·`role`·`cursor`)를 싣는다
      (FR-040)
- [ ] T025 [US3] 같은 파일 — 상한(200)에 걸려 잘렸으면 `truncated: true` 와 안내를 싣는다
      (FR-044 · contracts/observation.md §3)
- [ ] T026 [US3] `backend/src/itb/authoring/tools.py` 의 `observe_page` 가 `actionability` 와
      `truncated` 를 모델에게 전달하게 한다. `ObservedElement` 에 필드를 더한다
- [ ] T027 [US3] `backend/src/itb/recording/injected/recorder.js` 에 `window.__itbFindByText`
      를 더한다 — 글자를 담은 요소를 찾고, 거기서 **눌렀을 때 반응하는 요소까지 올라가** 둘을
      함께 돌려준다 (FR-042)
- [ ] T028 [US3] `backend/src/itb/authoring/tools.py` 에 `find_by_text` 도구를 더한다.
      **예산을 쓴다** (`record_call()` 을 지난다) — `observe_page` 와 같은 성격이다
      (contracts/observation.md §4)
- [ ] T029 [US3] `backend/src/itb/authoring/tools.py` 의 `TOOL_SCHEMAS` 에 `find_by_text` 를
      등록한다. 개발용 드라이버(`build_mcp_tools`)가 여기서 자동으로 받는다
- [ ] T030 [US3] `backend/src/itb/authoring/agent.py` 의 `SYSTEM_PROMPT` 에 세 줄을 더한다 —
      `cursor` 판정의 불확실성, `find_by_text` 사용, **못 찾으면 짐작하지 말고 알릴 것**
      (FR-043 · contracts/observation.md §5)
- [ ] T031 [US3] T002 의 기준선과 비교해 관찰 크기·지연을 실측하고 `baseline.md` 에 적는다.
      **SC-010 (2배 이내)을 넘으면 2단계 후보 조건을 좁힌다** (R13 의 「확인 필요」)

**Checkpoint**: 실제 웹 앱 화면에서 AI 가 사람이 가리킨 것을 찾는다.

---

## Phase 5: User Story 2 — 요구받은 것이 매 턴 다시 주어진다 (Priority: P1)

**Goal**: 사용자 메시지 앞에 붙는 것이 「지금 테스트」 하나에서 둘로 늘어난다 — 제약과 할 일이
함께 붙는다.

**Independent Test**: 구체값·금지사항이 든 지시문으로 다섯 차례 이상 대화를 이어가고 그것이
지켜지는지 확인한다.

### Tests for User Story 2

- [ ] T032 [P] [US2] `backend/tests/unit/test_work_plan.py` — `WorkPlan`·`PlanItem`·`Constraint`
      의 불변 조건: 순번 1부터 끊기지 않음, 빈 계획 허용, Step 을 참조하지 않음
      (data-model §1·§2)
- [ ] T033 [P] [US2] `backend/tests/unit/test_plan_injection.py` — 주입 문자열의 모양·순서
      (제약이 맨 앞), `▶` 가 가장 앞선 미완료를 가리킴 (contracts/agent-context.md §1)
- [ ] T034 [P] [US2] 같은 파일에 **예산과 축약** 검증 — 6KB 를 넘으면 완료 항목부터 접히고
      생략이 명시됨 (FR-013 · R6)
- [ ] T035 [P] [US2] 같은 파일에 **민감값** 검증 — 자격 증명이 값이 아니라 참조로 실림
      (FR-010). 016 `test_definition_summary.py` 의 `ALLOWED_VALUE_READS` 와 같은 방식으로
      값 읽기를 전수 등록한다
- [ ] T036 [P] [US2] `backend/tests/integration/test_plan_absent.py` — **계획이 없어도 지금과
      같이 동작**하는지 (FR-012). 이것이 이 기능의 회귀 방어선이다

### Implementation for User Story 2

- [ ] T037 [US2] `backend/src/itb/authoring/plan.py` 를 만든다 — `WorkPlan`·`PlanItem`·
      `Constraint` 와 상태 전이 규칙 (data-model §1~§3). **순수 모듈로 둔다** — 언어모델도
      브라우저도 알지 못한다
- [ ] T038 [US2] `backend/src/itb/authoring/summary.py` 에 계획 주입 문자열 생성을 더한다.
      **016 이 정한 예산·축약·민감값 규칙을 그대로 쓴다** — 규칙이 두 곳에 있으면 한쪽만
      고쳐진다 (R5)
- [ ] T039 [US2] `backend/src/itb/authoring/summary.py` — 예산을 16KB 에서 **나눈다**
      (계획 6KB · 정의 요약 10KB). 총량을 늘리지 않는다 (R6)
- [ ] T040 [US2] `backend/src/itb/authoring/agent.py` 의 `_with_summary` 가 계획을 함께 붙이게
      한다. **`plan_source` 를 함수로 받는다** — 016 `summary_source` 와 같은 모양 (R5)
- [ ] T041 [US2] `backend/src/itb/api/routes/sessions.py` 의 `SessionWork` 에 `work_plan` 을
      더하고 `AuthoringAgent` 에 `plan_source` 로 주입한다
- [ ] T042 [US2] `backend/src/itb/api/routes/sessions.py` — 세션 생성 요청이 `work_plan` 을
      받게 한다. `mode != "ai"` 에 오면 거절, 항목 200 초과면 거절
      (contracts/api-contract.md §2)
- [ ] T043 [US2] T003 의 기준선과 비교해 매 턴 전달 분량을 실측하고 `baseline.md` 에 적는다
      (SC-008)

**Checkpoint**: 계획이 있으면 매 턴 실린다. 없으면 지금과 같이 돈다.

---

## Phase 6: User Story 4 — 거친 지시문이 읽을 수 있는 계획이 된다 (Priority: P2)

**Goal**: 세션을 시작하기 전에 지시문이 항목·제약으로 정제되고, 사용자가 확인·수정한다.

**Independent Test**: 구획이 반복되는 지시문을 넣고 (가) 반복 전제가 합쳐졌는지 (나) 구체값이
글자 그대로인지 (다) 전역 제약이 제약 자리로 갔는지 본다.

### Tests for User Story 4

- [ ] T044 [P] [US4] `backend/tests/contract/test_instruction_refine.py` — 정제 성공·실패가
      **둘 다 200** 으로 오는지 (FR-020 · contracts/api-contract.md §1). 실패가 400 이면
      화면이 오류로 다루고, 그러면 정제가 작성의 관문이 된다
- [ ] T044a [P] [US4] 같은 파일에 **정제 1회** 검증 — 세션이 여러 턴 도는 동안 정제 호출이
      한 번뿐인지 (FR-021). 매 턴 다시 정제하는 구현이 들어가도 지금은 검증이 통과한다
- [ ] T045 [P] [US4] 같은 파일에 **구체값 보존** 검증 — 자리마다 다른 값이 각각 남는지
      (FR-015). 이 기능에서 가장 위험한 실패다
- [ ] T046 [P] [US4] 같은 파일에 **자격 증명 치환** 검증 — 평문 비밀번호가 참조로 바뀌고
      그 사실이 `notes` 에 실리는지 (FR-010 · R10)
- [ ] T047 [P] [US4] `frontend/tests/ComposeRefine.test.tsx` — 정제 결과 확인·수정·거절

### Implementation for User Story 4

- [ ] T048 [US4] `backend/src/itb/authoring/refine.py` 를 만든다 — 지시문을 받아 `WorkPlan` 을
      돌려준다. **도구 호출로 구조를 강제한다** (R8): 모델에게 「계획을 제출하는 도구」 하나만
      주고 그것을 부르게 한다
- [ ] T049 [US4] 같은 파일 — 정제 프롬프트를 쓴다. **줄이고 정리하는 일이지 해석하는 일이
      아님**을 명시한다. 구체값·금지사항·기대 문구는 글자 그대로 (FR-015·FR-016)
- [ ] T050 [US4] 같은 파일 — 자격 증명을 변수 참조로 바꾼다. **기존 민감값 규칙을 쓴다**,
      새 규칙을 만들지 않는다 (R10)
- [ ] T051 [US4] 같은 파일 — 실패 경로. 도구 미호출·스키마 불통과·호출 실패 셋 다
      `refined: false` 로 수렴한다 (FR-020)
- [ ] T052 [US4] `backend/src/itb/api/routes/instruction.py` 를 만든다 —
      `POST /api/instruction/refine` (contracts/api-contract.md §1). 세션을 만들지 않는다
- [ ] T053 [US4] `backend/src/itb/api/app.py` 에 라우터를 등록한다
- [ ] T054 [P] [US4] `frontend/src/api/client.ts` 에 `refineInstruction` 을 더한다
- [ ] T055 [US4] `frontend/src/pages/ComposeView.tsx` 에 정제 결과 확인·수정 자리를 만든다.
      **기존 디자인 언어(008)를 따른다.** 새 화면을 만들지 않고 지시문 입력 자리를 넓힌다
- [ ] T056 [US4] `frontend/src/pages/ComposeView.tsx` — 「원문으로 진행」을 둔다 (FR-019).
      정제 실패 시에도 같은 길이 열린다 (FR-020)
- [ ] T057 [US4] `backend/src/itb/api/routes/sessions.py` — 정제 기록(원문 + 계획)을 저장 시
      의도 기록으로 남긴다 (FR-022 · data-model §5). **실행 정보가 아니다**

**Checkpoint**: 사용자가 작성 전에 AI 가 무엇을 할지 목록으로 본다.

---

## Phase 7: User Story 5 — 어디까지 했는지 제품이 들고 간다 (Priority: P2)

**Goal**: AI 가 항목을 끝낼 때마다 기록되고, 사용자와 AI 가 같은 목록에서 진척을 본다.

**Independent Test**: 네 구획 지시문을 중간에 막고 사람이 이어받아 처리한 뒤 재개한다.
끝난 구획을 다시 하지 않고 다음부터 하는지 본다.

### Tests for User Story 5

- [ ] T058 [P] [US5] `backend/tests/unit/test_work_plan.py` 에 **상태 전이** 검증을 더한다 —
      모델은 `done`·`skipped` 로만, 되돌리기는 사용자만, 사유 없는 `skipped` 는 거절,
      같은 항목 반복 표시는 한 번만 (data-model §2)
- [ ] T059 [P] [US5] `backend/tests/contract/test_plan_api.py` — 조회·수정·`plan_progress`
      이벤트 (contracts/api-contract.md §3~§5)
- [ ] T060 [P] [US5] `backend/tests/integration/test_plan_progress.py` — 인수 후 재개에
      **남은 항목이 실리는지** (FR-026), 미완료가 남았는데 끝났다고 할 때 `ai_finished` 에
      `remaining_items` 가 실리는지 (FR-028)
- [ ] T061 [P] [US5] `frontend/tests/PlanPanel.test.tsx` — 진척 목록과 되돌리기

### Implementation for User Story 5

- [ ] T062 [US5] `backend/src/itb/authoring/tools.py` 에 `mark_item` 도구를 더한다.
      **`record_call()` 을 지나지 않는다** — 예산을 쓰지 않는다 (R9 ·
      contracts/agent-context.md §4)
- [ ] T063 [US5] `backend/src/itb/authoring/tools.py` 의 `TOOL_SCHEMAS` 에 등록한다.
      **계획이 없는 세션에는 이 도구를 주지 않는다**
- [ ] T064 [US5] `backend/src/itb/authoring/agent.py` 의 `SYSTEM_PROMPT` 에 네 줄을 더한다 —
      `▶` 의 뜻, 표시 의무, `skipped` 사유, **표시 안 한 항목이 남으면 끝났다고 말하지 말 것**
      (contracts/agent-context.md §4)
- [ ] T065 [US5] `backend/src/itb/api/routes/sessions.py` — `GET /plan`·
      `PATCH /plan/items/{id}` 를 더한다 (contracts/api-contract.md §3·§4)
- [ ] T066 [US5] `backend/src/itb/api/routes/sessions.py` — `plan_progress` 이벤트를 발행한다.
      **AI 가 표시한 것과 사람이 되돌린 것이 같은 통로로 온다** (016 FR-039 와 같은 판단)
- [ ] T067 [US5] `backend/src/itb/api/routes/sessions.py` — `ai_finished` 에 `remaining_items`
      를 싣는다 (FR-028). **모델의 완료 선언이 남은 일을 덮지 않게 하는 제품 쪽 절반**이다
- [ ] T068 [US5] `backend/src/itb/api/routes/sessions.py` — 대화로 온 새 지시가 계획에 항목으로
      더해지게 한다 (FR-029)
- [ ] T069 [P] [US5] `frontend/src/components/workbench/PlanPanel.tsx` 를 만든다 — 진척 목록,
      되돌리기. 기존 디자인 언어(008)를 따른다
- [ ] T070 [US5] `frontend/src/components/workbench/AiAuthoringPanel.tsx` — 남은 항목을
      완료 보고와 함께 보인다 (FR-028)
- [ ] T071 [P] [US5] `frontend/src/api/ws.ts` 에 `plan_progress` 를 더한다

**Checkpoint**: 되풀이와 건너뜀이 멈춘다. 남은 일이 사용자에게 보인다.

---

## Phase 8: User Story 6 — 한 턴 안의 낡은 화면을 접는다 (Priority: P3)

**⚠️ T005 의 판정이 부정이면 이 Phase 를 건너뛴다.** 다른 어느 것도 여기에 매여 있지 않다.

**Goal**: 한 턴 안에서 최신 관찰만 온전히 남고 지난 것은 접힘 표시가 된다.

**Independent Test**: 화면을 여러 번 관찰하는 긴 지시를 수행시키고, 모델에게 전달된 내용에서
온전한 관찰 결과가 몇 개인지 센다.

### Tests for User Story 6

- [ ] T072 [P] [US6] `backend/tests/unit/test_observation_fold.py` — 접기 규칙: 관찰만 접히고
      조작·검증·막힘 신고는 접히지 않음 (FR-034), 접힘 자리에 안내가 남음 (FR-031)
- [ ] T073 [P] [US6] 같은 파일 — 접기가 **모델에게 보내는 사본에만** 적용되고 제품이 든
      기록은 그대로인지 (FR-033)

### Implementation for User Story 6

- [ ] T074 [US6] `backend/src/itb/authoring/fold.py` 를 만든다 — 메시지 목록에서 지난 화면
      관찰 결과를 접는 순수 함수. **SDK 를 알지 못한다**
- [ ] T075 [US6] `backend/src/itb/authoring/agent.py` 의 `_sdk_driver` 가 runner 를 들고
      매 iteration 뒤 `set_messages_params` 로 접게 한다 (R4). 공개 메서드만 쓴다 —
      사적 속성(`_params`)에 손대지 않는다
- [ ] T076 [US6] 온전히 남기는 개수를 **하나의 상수**로 두고 근거를 주석에 적는다 (FR-032).
      기본값 1
- [ ] T077 [US6] `backend/src/itb/authoring/claude_code_driver.py` 에 주석을 남긴다 —
      이 경로는 도구 결과가 이력에 실리지 않으므로 접을 대상이 없다 (FR-038 ·
      contracts/agent-context.md §5)

**Checkpoint**: 턴 내부에서도 지금 화면만 지금 화면이다.

---

## Phase 9: Polish & Cross-Cutting

- [ ] T078 [P] `backend/src/itb/authoring/` 새 모듈들의 문서 문자열을 채운다 — **왜 그렇게
      했는지**를 적는다. 이 저장소의 기존 모듈과 같은 밀도로
- [ ] T079 `uv run lint-imports` 로 헌법 원칙 II 계약이 그대로인지 확인한다 —
      `itb.execution` 이 `itb.llm`·`itb.authoring` 에 닿지 않아야 한다 (FR-035·FR-036)
- [ ] T079a `backend/tests/unit/test_plan_makes_no_steps.py` — **헌법 원칙 I** 확인.
      `mark_item`·계획 수정·수행 기록 중 어느 것도 Step 을 만들거나 바꾸지 않음을 단언한다
      (FR-037). 설계는 통과하지만 확인이 없으면 다음 변경에서 조용히 깨진다
- [ ] T079b `backend/tests/e2e/test_actionable_elements.py` 에 **헌법 원칙 IV** 확인을
      더한다 — `cursor` 로 발견된 요소도 경로가 하나로 좁혀지지 않으면 **지금과 같이
      거절**되는지 (FR-046). US3 가 관찰을 직접 건드리므로 회귀 위험이 실재한다
- [ ] T080 [P] `docs/` 에 이 기능이 바꾼 것을 적는다 — 특히 **관찰 범위가 넓어졌다**는 사실.
      다음 사람이 목록에 왜 `<div>` 가 있는지 묻지 않게
- [ ] T081 [P] `specs/001-interactive-ai-test-builder/contracts/websocket.md` 에
      `plan_progress` 와 `ai_finished.remaining_items` 를 더한다
- [ ] T082 [quickstart.md](./quickstart.md) 의 §1~§5 를 손으로 확인한다. **§2·§3·§3-A 가
      가장 중요하다**
- [ ] T083 전량 검증 — `cd backend && bash scripts/test-backend.sh` ·
      `uv run ruff check src/ tests/` · `uv run lint-imports` ·
      `cd frontend && npx vitest run` · `npx tsc --noEmit` · `npm run build`.
      **T001 의 기준선과 대조해 차이만 이 기능의 것으로 본다**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음. 먼저 돈다 — 기준선이 없으면 끝에서 비교할 것이 없다
- **Phase 2 (Foundational)**: Phase 1 뒤. **T005 가 Phase 8 의 실행 여부를 판정한다**
- **Phase 3 (US1)**: Phase 2 뒤
- **Phase 4 (US3)**: Phase 2 뒤. **US1 과 독립 — 병행 가능**
- **Phase 5 (US2)**: Phase 2 뒤. US1 과 독립이지만 이력이 이어지는 편이 검증하기 쉽다
- **Phase 6 (US4)**: Phase 5 뒤 — `WorkPlan`(T037)을 쓴다
- **Phase 7 (US5)**: Phase 5 뒤 — 같은 이유. Phase 6 과 병행 가능하나 항목이 있어야 의미가 산다
- **Phase 8 (US6)**: Phase 2 뒤. **T005 가 부정이면 건너뛴다**
- **Phase 9 (Polish)**: 실행한 모든 Phase 뒤

### 사용자 이야기 의존

- **US1 (P1)**: 독립. 이것만으로 MVP 가 선다
- **US3 (P1)**: 독립. US1 과 병행 가능
- **US2 (P1)**: 독립 (계획이 없어도 동작해야 하므로 구조상 독립이 강제된다)
- **US4 (P2)**: US2 의 `WorkPlan` 에 의존
- **US5 (P2)**: US2 의 `WorkPlan` 에 의존
- **US6 (P3)**: 독립. 유일하게 **빼도 되는** 조각

### 병렬 기회

- T002·T003 (기준선 실측)
- Phase 3 의 테스트 3건 (T007·T008·T009)
- Phase 4 의 테스트 5건 (T017~T021)
- Phase 5 의 테스트 5건 (T032~T036)
- **Phase 3 과 Phase 4 는 서로 다른 파일을 만진다** — 사람이 둘이면 나눌 수 있다
- Phase 6 과 Phase 7 의 프론트 작업 (T054·T069·T071)

---

## Implementation Strategy

### MVP — US1 만

1. Phase 1 (기준선)
2. Phase 2 (SDK 계약 고정)
3. Phase 3 (US1)
4. **멈추고 확인**: quickstart §2 — 막힘 후 재개가 이어지는가
5. 여기까지가 사용자가 겪던 증상의 큰 몫이다

### 증분 전달

1. Setup + Foundational → 토대
2. **US1** → 재개가 이어진다 → 확인 (MVP)
3. **US3** → 사람이 가리킨 것을 찾는다 → 확인
4. **US2** → 요구받은 것이 매 턴 실린다 → 확인
5. **US4** → 지시문이 계획이 된다 → 확인
6. **US5** → 진척이 보인다 → 확인
7. **US6** → 턴 내부가 깨끗해진다 → 확인 (T005 가 긍정일 때만)

### 멈출 수 있는 자리

각 Checkpoint 가 멈출 수 있는 자리다. 특히 **US1 · US3 까지만 해도 제품이 나아진다** —
나머지는 그 위에 쌓는 것이다.

---

## Notes

- [P] = 다른 파일, 의존 없음
- 각 작업 또는 논리적 묶음 뒤에 커밋한다
- **기존 실패를 새 실패와 섞지 않는다.** T001 의 기준선과 대조한다
- 전량 검증은 저장소 표준 명령으로 — `uv run pytest` 와 `npm test` 는 틀린 결과를 준다
- 016·020·022 가 정한 판단을 뒤집지 않는다. 겹치는 자리가 많다
