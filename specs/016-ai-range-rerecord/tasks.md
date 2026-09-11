---

description: "Task list for 016 편집 중 AI 구간 재녹화"
---

# Tasks: 편집 중 AI 구간 재녹화

**Input**: Design documents from `/specs/016-ai-range-rerecord/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **포함한다.** 헌법 Quality Gate 3 이 요구한다 — 「제품은 테스트 도구다. 자기
테스트 없이 출하하는 것은 허용되지 않는다」. 원칙 II 관련 검사는 선택이 아니다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: US1 · US2 · US3
- 파일 경로를 반드시 적는다

## Path Conventions

- 백엔드: `backend/src/itb/…` · 테스트 `backend/tests/…`
- 프론트: `frontend/src/…` · 테스트 `frontend/tests/…`

---

## Phase 1: Setup

**Purpose**: 기준선을 확인한다. 새 의존성은 없다.

- [X] T001 현재 브랜치에서 전체 검증을 돌려 **기준선이 초록**임을 확인한다 — `cd backend && uv run lint-imports && uv run ruff check src/ tests/ && uv run pytest && uv run python -m itb.schema.export --check` · `cd frontend && npx tsc --noEmit && npm test -- --run`. 실패가 있으면 그 목록을 `specs/016-ai-range-rerecord/baseline.md` 에 적고 이 기능과 무관함을 확인한다
- [X] T002 [P] `specs/016-ai-range-rerecord/contracts/agent-tools.md` §1 의 도구 분류표를 기준으로, `backend/src/itb/authoring/tools.py` 의 현재 `TOOL_NAMES` 12개가 네 분류에 빠짐없이 들어가는지 손으로 대조하고 결과를 `specs/016-ai-range-rerecord/baseline.md` 에 적는다 (계약 문서는 고치지 않는다 — 구현 작업이 계약을 수정하면 순서가 뒤집힌다)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 세 스토리가 전부 이 위에 선다. **완료 전에는 어떤 스토리도 시작할 수 없다.**

**⚠️ 원칙 II 검사(T014·T015)를 이 단계에서 세운다** — 나중에 붙이면 이미 깨진 배선 위에
검사를 맞추게 된다.

### 정의 요약 (FR-001~FR-006 · R8)

- [X] T003 [P] `backend/tests/unit/test_definition_summary.py` 에 **실패하는** 테스트를 먼저 쓴다: (a) 요약에 순번·id·label·종류·대상 요약·탭이 있다 (b) **어떤 Step 의 `value` 도 없다** — 값 100종(사번·주소·카드번호 형태 포함) property 검사 (c) 교체 구간이 표시된다 (d) 예산 초과 시 `… (Step n~m 생략) …` 가 명시된다
- [X] T004 `backend/src/itb/authoring/summary.py` 신규 — `build_definition_summary(steps, range_ids, budget) -> str`. **`Step.value` 에 접근하지 않는다** (R8). 입력값이 있는 Step 은 `값 있음` 또는 변수 참조 이름만 적는다. `budget` 기본값은 **잠정 8KB** 로 박고 T064 가 실측값으로 교체한다 (A1). T003 을 통과시킨다
- [X] T005 `backend/src/itb/authoring/agent.py` 에 요약 주입을 배선한다 — `AuthoringAgent` 가 `summary_source: Callable[[], str] | None` 을 받고, **매 턴의 사용자 메시지 앞에** 요약을 덧붙인다 (FR-003 · agent-tools.md §3). 첫 메시지에만 넣지 않는다
- [X] T006 `backend/src/itb/authoring/agent.py` 의 `SYSTEM_PROMPT` 에 agent-tools.md §3 의 4줄을 더한다. **기존 줄은 하나도 지우지 않는다**
- [X] T006a `backend/src/itb/api/routes/sessions.py` — **기존 AI 작성(US4)·자연어 Step 추가(US6) 경로에도 같은 요약을 주입한다** (FR-005). 마감이 아니라 여기서 한다 — T005 가 주입 지점을 이미 만들었고, 나중에 붙이면 US4·US6 회귀가 마지막에 드러난다 (analyze I1)
- [X] T006b [P] `backend/tests/unit/test_definition_summary.py` 에 회귀 단언을 더한다 — US4·US6 경로의 에이전트도 요약을 받는지 (FR-005)

### 교체 트랜잭션 (data-model §1-2 · R7)

- [X] T007 [P] `backend/tests/unit/test_rerecord_transaction.py` 에 **실패하는** 테스트를 먼저 쓴다: 구간 검증(존재·연속·비어있지 않음), 확정이 `range.step_ids` 를 지운다, 버리기가 `created_step_ids` 를 지운다, 불변식 9(버리면 시작 전과 id·순서·내용이 같다), 불변식 10(만든 것이 없으면 확정 거절)
- [X] T008 `backend/src/itb/authoring/rerecord.py` 신규 — `StepRange`·`RerecordTransaction` 과 `validate_range`·`commit`·`discard`. 확정·버리기 모두 `itb.execution.step_edits.delete_steps` **한 번**을 지난다 (전부-또는-전무). **스냅샷을 만들지 않는다** (R7). T007 을 통과시킨다

### 상태 기계 (data-model §3 · R4)

- [X] T009 `backend/tests/unit/test_state_machine.py` 에 전이 하나를 단언하는 테스트를 더한다 — `PAUSED + BEGIN_AI → AI_RUNNING`, 그리고 **다른 상태의 전이표가 바뀌지 않았음**
- [X] T010 `backend/src/itb/execution/state_machine.py` 의 `_TRANSITIONS[SessionState.PAUSED]` 에 `Command.BEGIN_AI: SessionState.AI_RUNNING` 한 줄을 더한다. 주석에 근거(research R4)를 적는다

### 세션 생성 — `mode: "rerecord"` (api-contract §1 · R5)

- [X] T011 `backend/src/itb/api/routes/sessions.py` — `CreateSessionRequest` 에 `mode: "rerecord"` 와 `rerecord_step_ids: list[str]` 를 더한다. `ai_instruction` 은 이 모드에서 **거절**한다. 경계 검증: 구간 존재·연속·비어있지 않음 → `400 DEFINITION_INVALID`(003 의 `category`·`next_action` 포함)
- [X] T012 `backend/src/itb/api/routes/sessions.py` — `mode=rerecord` 분기를 구현한다. `authoring_mode = AI`, `BEGIN_REPLAY`, `_build_engine`, `_start_runner(pause_before_index=구간 첫 Step 순번)`. **러너가 멈춘 뒤에** `_build_agent` 를 부른다 (api-contract §1 의 순서가 계약이다). 도착점 실패 시 세션을 남기고 실패한 Step 정보를 실어 `409` (FR-020)
- [X] T013 `backend/src/itb/api/routes/sessions.py` — `SessionWork.rerecord: RerecordTransaction | None` 필드와 `mode=rerecord` 시 트랜잭션 생성
- [X] T013a [P] `backend/tests/us_rerecord/test_arrival_point.py` 신규 — 도착점 경계: **구간이 Step 1 부터면 아무것도 실행하지 않고 시작 주소만 연다** (FR-021), 구간 끝이 목록 끝인 경우, 앞 구간이 깨져 도착점에 닿지 못하는 경우 (FR-020)

### 원칙 II 시간 축 검사 (R9 · 불변식 6) ⚠️ 이연 불가

- [X] T014 [P] `backend/tests/test_principle_ii_timeline.py` 신규 — 가짜 드라이버로 호출 횟수를 세어 **도착점 만들기 구간에서 0회**임을 단언한다. `AuthoringAgent.driver` 교체 지점을 쓴다
- [X] T015 `backend/tests/test_principle_ii_timeline.py` (T014 와 같은 파일) — `work.runner` 와 `work.agent_task` 의 **생존 구간이 겹치지 않음**을 단언한다 (불변식 6). 러너 시작/종료·에이전트 시작/종료 시각을 기록해 비교한다

### 조작 목록과 권한표 (ui-contract §1·§2)

- [X] T016 `frontend/src/lib/actions.ts` — `AI_ACTIONS` 에 `ai.rerecord`·`ai.chat`·`ai.rerecordCommit`·`ai.rerecordDiscard` 를 더한다 (3 → 7). 각 조작에 ui-contract §1-1 의 설명을 주석으로 붙인다
- [X] T017 `frontend/src/lib/actions.ts` — `step.toggleDeleteTarget → step.toggleSelection`, `step.selectAllDeleteTargets → step.selectAll` 개칭. **개칭 근거를 주석에 적는다** (체크의 뜻이 하나에서 둘로 늘었다)
- [X] T018 `frontend/src/lib/capabilities.ts` — 새 조건 `C16: canCommitRerecord`·`C17: hasRerecord`, 새 비활성 사유 `ALREADY_IN_SESSION`·`NEEDS_SESSION` 을 등록한다. 가시성: `ai.rerecord`·`ai.chat` 은 `keep`
- [X] T019 `frontend/src/lib/capabilities.ts` — 10개 국면 × 새 조작 4개 = 40셀을 ui-contract §2 의 표대로 채운다. 개칭 2건을 모든 행에 반영한다
- [X] T020 `frontend/tests/CapabilityCoverage.test.ts` 수정 — 조작 수 42 → 46, 개칭 2건, 새 조건의 사실 이름 등록을 반영한다
- [X] T021 [P] `frontend/src/api/client.ts` — `SessionView` 에 `rerecord: RerecordView | null`, `RerecordView` 타입(`range_step_ids`·`created_step_ids`·`can_commit`), 이벤트 이름 3개(`chat_turn`·`rerecord_changed`·`rerecord_realign_failed`)를 더한다
- [X] T022 `backend/src/itb/api/routes/sessions.py` — `SessionView` 응답에 `rerecord` 를 싣는다. **`can_commit` 은 서버가 판정한다** (화면이 조건을 복제하지 않는다)

**Checkpoint**: `uv run lint-imports` 와 T014·T015 가 통과해야 다음으로 간다. 원칙 II 가
깨진 상태에서 쌓은 것은 전부 되돌려야 한다.

---

## Phase 3: User Story 1 — 테스트를 아는 AI 와 대화한다 (P1) 🎯 MVP

**Goal**: 재녹화 세션 안에서 사용자가 먼저 말을 걸고, AI 가 그 테스트의 실제 Step 을
근거로 답한다.

**Independent Test**: 재녹화 세션을 열고 **Step 을 만들지 않는 질문**만 던져, 답이 실제
Step 을 가리키고 민감 값이 나오지 않는지 본다. 구간을 확정하지 않아도 검증된다.

### Tests for US1 ⚠️ 먼저 쓰고 실패를 확인한다

- [X] T023 [P] [US1] `backend/tests/us_rerecord/test_chat_turn.py` — 채팅 한 턴이 `PAUSED → AI_RUNNING → PAUSED` 를 지나고, 이력에 사용자·AI 차례가 순서대로 붙는지
- [X] T024 [P] [US1] `backend/tests/us_rerecord/test_chat_boundary.py` — 빈 입력·상한 초과·`paused` 아닌 상태에서의 호출이 전부 `400`/`409` 로 거절되고 사유가 있는지 (FR-010)
- [X] T025 [P] [US1] `frontend/tests/ChatPanel.test.tsx` — 자리가 편집 국면에서 **보이되 잠기고** 해소 조작을 가리키는지, `paused` 에서 활성인지 (FR-234 · ui-contract §2)

### Implementation for US1

- [X] T026 [US1] `backend/src/itb/api/routes/sessions.py` — `POST /{session_id}/chat` 구현 (api-contract §2-1). `paused` 게이트 → 요약 생성 → `BEGIN_AI` → 에이전트 태스크 → 턴 종료 시 `PAUSE`. 요청은 즉시 반환한다
- [X] T027 [US1] `backend/src/itb/api/routes/sessions.py` — `_run_agent` 의 종료 처리를 **두 결말로 가른다**: 기존 US4 의 「지시 완수 → `FINISH_PASS`」와 016 의 「턴 완료 → `PAUSE`」. 호출자가 어느 쪽인지 넘긴다. 막힘·실패 처리는 **한 곳을 그대로 지난다**
- [X] T028 [US1] `backend/src/itb/api/routes/sessions.py` — `GET /{session_id}/chat` 구현 (api-contract §2-4). `AuthoringAgent.messages` 에서 `ChatTurn` 목록을 만든다. **디스크에 쓰지 않는다** (FR-014)
- [X] T029 [US1] `backend/src/itb/api/routes/sessions.py` — `chat_turn` 이벤트 발행 (api-contract §4-1)
- [X] T030 [P] [US1] `frontend/src/components/workbench/ChatPanel.tsx` 신규 — 이력·입력(상한 표시)·진행 표시(`ai_progress` 재사용)·중지(`run.pause` 재사용)·**언어모델 없음 안내**(`GET /api/ai/availability` 의 `reason` 을 그대로, FR-012). **막힘은 그리지 않는다** — 기존 `ai_blocked` 5선택지가 뜨고 패널은 그리로 가리킨다 (ui-contract §3-1 · `USE_BLOCKED_ANSWER`)
- [X] T031 [US1] `frontend/src/components/workbench/model.ts`·`Workbench.tsx` — 대화 패널을 국면 배치에 넣는다. `frontend/src/lib/layout.ts` 의 `Record<Phase, …>` 표를 지난다 (007 배치 계약)
- [X] T032 [US1] `frontend/src/pages/SessionScreen.tsx` — `chat_turn` 구독, `POST /chat` 호출, 새로 고침 시 `GET /chat` 복구
- [X] T033 [US1] `frontend/src/components/workbench/ActionPalette.tsx` — `ai.rerecord` 를 팔레트에 놓고, **브라우저를 연다는 사실을 이름 옆에서 미리 말한다** (ui-contract §1-1)
- [X] T034 [US1] `frontend/src/pages/SessionScreen.tsx` 또는 편집 화면 — `ai.rerecord` 를 누르면 고른 구간으로 `mode=rerecord` 세션을 만든다. 연속이 아니면 **시작하지 않고** 이유를 말한다 (FR-016)
- [X] T034a [US1] `frontend/src/pages/SessionScreen.tsx` — **저장하지 않은 편집이 있으면 시작 전에 확인을 받는다** (FR-022 · api-contract §1 「저장하지 않은 편집」). 선택지 셋: 저장하고 시작 · 저장하지 않고 시작 · 취소. **편집을 버리지 않는다** — 세션이 끝나면 돌아온다
- [X] T034b [P] [US1] `frontend/tests/RerecordStart.test.tsx` 신규 — 미저장 편집이 있을 때 확인이 뜨는지, 「취소」가 세션을 만들지 않는지, 「저장하지 않고 시작」 후에도 편집이 화면에 남는지 (FR-022)
- [X] T035 [US1] `frontend/tests/CapabilityUI.test.tsx` 수정 — 새 조작 4개의 **자리**가 실제로 있는지 (FR-235)

**Checkpoint**: quickstart §2 가 통과한다. 이 시점에 Step 을 하나도 만들지 않아도
「테스트를 아는 AI」의 가치가 검증된다.

---

## Phase 4: User Story 2 — Step n~m 을 AI 로 다시 만든다 (P1)

**Goal**: 채팅 지시로 새 Step 이 구간 시작 위치에 들어가고, 확정하면 옛 구간이 사라지며,
버리면 목록과 화면이 시작 전으로 돌아간다.

**Independent Test**: Step 10개 이상 테스트의 가운데 구간을 다른 지시로 교체하고, 확정 후
목록이 「앞 + 새 + 뒤」가 되며 전체 실행이 성공하는지 본다.

### Tests for US2 ⚠️

- [X] T036 [P] [US2] `backend/tests/us_rerecord/test_commit.py` — 확정이 옛 구간을 한 번에 지우고(FR-026), 만든 것이 없으면 거절하며(불변식 10), 번호가 빈자리 없이 다시 매겨지는지(FR-030)
- [X] T037 [P] [US2] `backend/tests/us_rerecord/test_discard.py` — 버리기 후 목록이 시작 전과 **id·순서·내용까지 동일**한지 (불변식 9 · SC-004). **20회 반복**으로 단언한다
- [X] T038 [P] [US2] `backend/tests/us_rerecord/test_discard_realign.py` — 버리기가 도착점까지 다시 실행하고(FR-031), 세션이 살아 있으며(FR-031a), 되맞춤 구간에서 드라이버 호출이 0회인지(FR-031b), 되맞춤 실패 시 두 사실을 함께 알리는지(FR-031c · 불변식 11)
- [X] T039 [P] [US2] `backend/tests/us_rerecord/test_no_disk_before_commit.py` — 확정 전 「저장」이 확정되지 않은 교체를 디스크에 내리지 않는지 (FR-029)
- [X] T040 [P] [US2] `frontend/tests/RerecordTransaction.test.tsx` — 재녹화 띠가 구간과 개수를 말하고, `can_commit` 이 거짓이면 확정이 사유와 함께 잠기는지
- [X] T040a [P] [US2] `backend/tests/us_rerecord/test_blocked_in_rerecord.py` 신규 — 재녹화 중 AI 가 막히면 **브라우저가 닫히지 않고**(FR-041 · 원칙 III) 5선택지가 뜨며, 그때까지 만든 Step 이 **보존**되는지(FR-043). 새 경로 `PAUSED → AI_RUNNING → AI_BLOCKED` 를 지난다 — 기존 동작의 재사용이지만 이 전이는 이번에 처음 생긴다
- [X] T040b [P] [US2] `backend/tests/us_rerecord/test_commit_then_replay.py` 신규 — 확정·저장 후 그 테스트를 **처음부터 끝까지 실행해 성공**하는지 (SC-005). 재녹화가 만든 Step 이 이어 붙은 자리에서 깨지지 않음을 본다
- [X] T040c [P] [US2] `backend/tests/us_rerecord/test_sensitive_in_rerecord.py` 신규 — 재녹화로 만든 Step 의 민감값이 기존 녹화와 **같은 규칙**으로 변수 참조가 되는지 (FR-045). `SensitiveCapturer` 가 toolbox 에 붙어 있어 자동으로 될 가능성이 높지만, 가능성은 검사가 아니다

### Implementation for US2

- [X] T041 [US2] `backend/src/itb/api/routes/sessions.py` — 채팅 턴의 `StepCompiler.insert_at` 을 **구간 시작 위치**로 맞춘다 (FR-023). 삽입마다 위치가 밀리는 것은 컴파일러가 이미 처리한다
- [X] T042 [US2] `backend/src/itb/api/routes/sessions.py` — 새 Step 의 id 를 `rerecord.created_step_ids` 에 기록한다 (불변식 8·9 의 근거)
- [X] T043 [US2] `backend/src/itb/api/routes/sessions.py` — `POST /{session_id}/rerecord/commit` 구현 (api-contract §2-2). 게이트·`delete_steps` 한 번·트랜잭션 닫기
- [X] T044 [US2] `backend/src/itb/api/routes/sessions.py` — `POST /{session_id}/rerecord/discard` 구현 (api-contract §2-3). `delete_steps` → 트랜잭션 닫기 → **도착점까지 되맞춤 실행**. 연타는 `409`
- [X] T045 [US2] `backend/src/itb/api/routes/sessions.py` — 되맞춤 실패 시 `rerecord_realign_failed` 이벤트를 낸다. `definition_reverted: true` 를 **함께** 싣는다 (api-contract §4-3)
- [X] T046 [US2] `backend/src/itb/api/routes/sessions.py` — 저장 경로에 확정 전 교체가 내려가지 않도록 게이트를 건다 (FR-029). T039 를 통과시킨다
- [X] T047 [US2] `backend/src/itb/api/routes/sessions.py` — `rerecord_changed` 이벤트 (api-contract §4-2)
- [X] T048 [US2] `backend/src/itb/api/routes/sessions.py` — 세션 유실 시 확정되지 않은 새 Step 을 **보존**하고 그 사실을 알린다 (FR-044). 기존 `_loss_handler` 가 「그때까지의 결과를 보존」하는 것과 같은 판단이다 — 사용자가 버리기를 고르지 않았는데 제품이 버리지 않는다. 다만 **옛 구간도 함께 남으므로** 목록이 「새 + 옛」인 상태임을 안내하고, 유실 후에는 저장만 가능하다는 기존 불변식 5 를 따른다
- [X] T049 [P] [US2] `frontend/src/components/workbench/RerecordBar.tsx` 신규 — 구간·개수·확정·버리기 (ui-contract §3-2)
- [X] T050 [US2] `frontend/src/components/workbench/StepList.tsx` — `range_step_ids` 로 「교체 대상」을 **계산해** 그린다. **Step 에 필드를 더하지 않는다** (불변식 7). 008 시각 언어의 기존 어휘만 쓴다
- [X] T051 [US2] `frontend/src/pages/SessionScreen.tsx` — `rerecord_changed`·`rerecord_realign_failed` 구독, 확정·버리기 호출, 되맞춤 실패 안내 (ui-contract §3-4 의 문면)

**Checkpoint**: quickstart §3 전체(정상·버리기 20회·이상 경로 10종)가 통과한다.

---

## Phase 5: User Story 3 — AI 가 만든 Step 을 AI 가 고친다 (P2)

**Goal**: AI 가 방금 만든 Step 의 이름·순서·대상을 고친다. 결과는 사람이 같은 편집을 한
것과 저장 형식에서 구별되지 않는다.

**Independent Test**: 재녹화로 Step 3개를 만든 뒤 표시 이름·순서·대상 재지정을 각각
지시하고, 저장 결과를 사람의 편집 결과와 비교한다.

### Tests for US3 ⚠️

- [X] T052 [P] [US3] `backend/tests/unit/test_tool_surface.py` 수정 — agent-tools.md §1 의 검사 4개: 네 분류 합집합 == `TOOL_NAMES`·교집합 없음, `STEP_PRODUCING_TOOLS` ↔ Step 종류 1:1(기존), `TOOL_SCHEMAS` 키 == `TOOL_NAMES`
- [X] T053 [P] [US3] `backend/tests/unit/test_agent_edit_tools.py` 신규 — **편집 도구의 결과가 사람 편집 경로의 결과와 Step 으로서 같은지** (SC-006 · agent-tools.md §1 검사 3), 그리고 **같은 이벤트로 화면에 나가는지** (FR-039). 같은 함수를 지나는 것과 같은 이벤트를 내는 것은 다른 보장이므로 둘 다 단언한다
- [X] T054 [P] [US3] `backend/tests/unit/test_edit_tool_scope.py` 신규 — 불변식 8: 구간 밖·옛 구간 Step 에 대한 편집이 **거절을 반환**하고(예외 아님) 사유가 있는지 (FR-038)

### Implementation for US3

- [X] T055 [US3] `backend/src/itb/authoring/tools.py` — 분류 튜플 4개를 만든다: `READ_ONLY_TOOLS`·`STEP_PRODUCING_TOOLS`(기존)·`STEP_EDITING_TOOLS`·`CONTROL_TOOLS`. `TOOL_NAMES` 를 네 분류의 합으로 정의한다
- [X] T056 [US3] `backend/src/itb/authoring/tools.py` — `BrowserToolbox` 에 권한 범위 판정을 더한다. 편집 도구의 `step_id` 는 이번 세션이 만든 Step 이어야 한다 (불변식 8). 범위 밖이면 `{"error": ...}` 반환
- [X] T057 [US3] `backend/src/itb/authoring/tools.py` — `update_step` 도구. `itb.execution.step_edits.update_step` 을 지난다. `FieldNotSupportedError` 사유를 그대로 돌려준다 (agent-tools.md §2-1)
- [X] T058 [US3] `backend/src/itb/authoring/tools.py` — `delete_step` 도구. `step_edits.delete_step` 을 지난다. **복수 삭제 도구는 만들지 않는다** (agent-tools.md §2-2)
- [X] T059 [US3] `backend/src/itb/authoring/tools.py` — `move_step` 도구. `direction: "up"|"down"` 만 받고 `step_edits.reorder_steps` 를 지난다. 이동 범위도 권한 범위 안이다 (agent-tools.md §2-3)
- [X] T060 [US3] `backend/src/itb/authoring/tools.py` — `repick_target` 도구. **`element_ref` 만 받는다**(원칙 IV). 후보를 `itb.locator.collector` 로 **살아 있는 페이지에서** 새로 수집한다. `RepickController` 를 쓰지 않는다 (agent-tools.md §2-4)
- [X] T061 [US3] `backend/src/itb/authoring/tools.py` — `build_tools`·`TOOL_SCHEMAS` 에 새 도구 4종을 등록한다. `QUALIFIED_TOOL_NAMES` 는 자동으로 따라온다
- [X] T062 [US3] `backend/tests/unit/test_claude_code_driver.py` 수정 — 개발용 드라이버에서도 편집 도구가 표면에 있는지 (기본과 개발용의 표면이 갈리지 않게)

**Checkpoint**: quickstart §4 가 통과한다. 세 스토리가 전부 독립적으로 동작한다.

---

## Phase 6: Polish & Cross-Cutting

- [X] T064 [P] `backend/tests/unit/test_definition_summary.py` 에 **예산 실측**을 더한다 — Step 100개 요약의 실제 바이트 수를 재고, 그 값으로 T004 의 잠정 `budget`(8KB)을 교체한다 (plan.md 알려진 위험 2 · analyze A1)
- [X] T065 [P] `backend/tests/unit/test_attempt_limits.py` 수정 — 편집 도구도 호출 1회로 세는지, 구간 크기와 무관하게 상한이 적용되는지 (FR-042)
- [X] T066 [P] `frontend/tests/` — 회귀 확인 quickstart §8 의 6항목을 자동 검사로 가능한 것만 옮긴다 (SC-009)
- [X] T067 `README.md` 갱신 — 016 을 기능 표에 넣고, 「AI 로 다시 만들기」를 사용법에 적는다. 도구 표면이 16종이 된 사실을 아키텍처 절에 반영한다
- [X] T068 `docs/PENDING-HUMAN-VERIFICATION.md` 에 §16 을 더한다 — SC-002(조작 횟수 비교)·SC-003(10건 중 7건)은 **사람이 측정**해야 한다. 개발용 드라이버 결과는 SC-003 의 근거로 쓰지 않는다
- [X] T069 전체 검증을 돌린다 — `uv run lint-imports` → `ruff check` → `pytest` → `schema.export --check`(**변경 없이 통과해야 한다**) → `tsc --noEmit` → `npm test -- --run`
- [X] T070 quickstart.md 를 처음부터 끝까지 실수행하고 §7 성공 기준 표의 자동 측정 가능 항목을 채운다

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 Setup
   ↓
Phase 2 Foundational  ← ★ 원칙 II 검사(T014·T015)가 여기 있다. 통과 전 진행 금지
   ↓
Phase 3 US1 (P1) ─┐
   ↓              │  US2 는 US1 의 채팅 통로를 쓴다 (지시가 채팅으로 온다)
Phase 4 US2 (P1) ─┤
   ↓              │  US3 는 US2 의 created_step_ids 를 권한 범위로 쓴다
Phase 5 US3 (P2) ─┘
   ↓
Phase 6 Polish
```

**스토리 독립성에 대한 정직한 기록**: 템플릿은 스토리가 서로 독립이기를 권하지만, 이
기능의 US2 는 US1 의 채팅 통로 없이 성립하지 않는다 — 재녹화의 지시가 채팅으로 오기
때문이다(api-contract §1, `ai_instruction` 을 받지 않는 이유). US3 도 US2 의
`created_step_ids` 를 권한 범위로 쓴다. **독립적인 것은 검증이지 구현이 아니다** — 각
스토리는 앞 스토리 위에서 **따로 검증**되고, 앞 스토리만으로도 가치가 있다.

### Within Each Story

- 테스트를 먼저 쓰고 **실패를 확인한 뒤** 구현한다
- 백엔드 → 프론트 순. 프론트가 `SessionView` 델타를 기다린다
- 같은 파일(`sessions.py`)을 건드리는 작업은 `[P]` 를 붙이지 않았다

### Parallel Opportunities

| 묶음 | 함께 돌릴 수 있는 작업 |
|---|---|
| Phase 2 테스트 선행 | T003 · T006b · T007 · T013a · T014 (다른 파일). T015 는 T014 와 같은 파일이므로 직렬 |
| Phase 2 프론트 | T021 은 백엔드와 병렬 (타입만 먼저 맞춘다) |
| Phase 3 테스트 | T023 · T024 · T025 · T034b |
| Phase 4 테스트 | T036 · T037 · T038 · T039 · T040 · T040a · T040b · T040c |
| Phase 5 테스트 | T052 · T053 · T054 |
| Phase 6 | T064 · T065 · T066 |

**주의**: `backend/src/itb/api/routes/sessions.py` 를 건드리는 작업은 T011·T012·T013·
T022·T026·T027·T028·T029·T041~T048·T006a 로 많다. 전부 직렬이다 — 병렬로 돌리면
같은 파일에서 충돌한다.

---

## Parallel Example: Phase 2 테스트 선행

```bash
Task: "T003 정의 요약 테스트 — 값 비유출 property 포함"
Task: "T007 교체 트랜잭션 테스트 — 불변식 9·10"
Task: "T014 원칙 II — 도착점 구간 드라이버 호출 0회"
# T015 는 T014 와 같은 파일 — T014 뒤에 이어서
```

---

## Implementation Strategy

### MVP (US1 까지)

1. Phase 1 Setup
2. Phase 2 Foundational — **T014·T015 통과가 관문이다**
3. Phase 3 US1
4. **멈추고 검증**: quickstart §2. 「테스트를 아는 AI」가 단독으로 쓸 만한지 본다
5. 여기서 멈춰도 가치가 있다 — 사용자가 처음으로 자기 테스트에 대해 AI 와 말할 수 있다

### Incremental Delivery

1. Setup + Foundational → 기반
2. US1 → quickstart §2 → 대화 가능
3. US2 → quickstart §3 → **사용자가 요청한 것이 동작한다**
4. US3 → quickstart §4 → 고치기가 싸진다
5. Polish → 기존 경로에도 요약이 붙고(FR-005) 회귀가 확인된다

### 중단 시 되돌리기

각 작업 뒤에 커밋한다. Phase 2 가 깨지면 그 위의 전부를 되돌려야 하므로,
**Phase 2 체크포인트에서 반드시 멈춰 검증한다.**

---

## Notes

- `[P]` = 다른 파일, 의존 없음
- 헌법 원칙 I·II 는 **이연 불가**다. 관련 검사(T014·T015·T052·T053)를 약화시켜 통과시키지
  않는다 — Quality Gate 4(비활성 테스트 금지)에 걸린다
- `uv run python -m itb.schema.export --check` 가 **변경을 보고하면 실패다.** 이 기능은
  저장 형식을 건드리지 않기로 했다
- 사람이 해야 하는 측정(SC-002·SC-003)은 T068 로 넘긴다. 자동으로 재지 않는다


---

## 016 검증 기록 (2026-09-11)

### T069 — 전체 검증

| 검사 | 결과 |
|---|---|
| `uv run lint-imports` | **통과** — Contracts: 3 kept, 0 broken |
| `uv run ruff check src/ tests/` | **통과** |
| `bash scripts/test-backend.sh` | **통과** — 병렬 2643 · 순차 48 (1 skipped) |
| `uv run python -m itb.schema.export --check` | **통과** — 드리프트 없음 |
| `npx tsc --noEmit` | **통과** |
| `npx vitest run` | **통과** — 108 파일 · 1340건 |
| `design_compare_ba.py --compare` | **통과** — 불일치 0건 |

**1차 실행에서 16건이 실패했다.** 원인은 하나였다 — `SessionWork.__new__` 로 만드는
테스트 픽스처 둘(`test_draft_to_test.py`·`test_us9_draft_recording.py`)이 `slots=True`
아래에서 필요한 필드만 손으로 채우는데, 016 이 저장 경로에 `rerecord` 를 읽게 하면서
`AttributeError` 가 났다.

**픽스처를 고쳤고, 터진 것이 옳다.** 조용히 `None` 이 되면 「저장 경로가 무엇을
보는가」가 픽스처에 기록되지 않는다. 픽스처의 머리말도 그 사실에 맞춰 다시 썼다.

### T070 — quickstart 실수행

**자동으로 잴 수 있는 것은 전부 검사가 됐다.** quickstart §7 을 「누가 재나」 표로
다시 썼고, 아홉 중 여섯이 자동이다. 절차 문서(§2~§6)의 손 확인은 실제 브라우저와
언어모델 자격 증명이 필요하므로 **사람이 한다.**

| 기준 | 상태 |
|---|---|
| SC-004 버리기 20/20 | 자동 — 통합 20회 + 단위 20회 |
| SC-005 확정 후 전체 실행 | 자동 — `test_commit_then_replay` |
| SC-006 형식 구별 불가 | 자동 — 값·구조 양쪽 |
| SC-007 원칙 II | 자동 — 린터 + 시간 축 3건 |
| SC-008 민감값 | 자동 — 값 100종 + 구조 2 + 디스크 |
| SC-009 기존 흐름 불변 | 자동(일부) — 회귀 6건 |
| **SC-001·002·003** | **사람** — `docs/PENDING-HUMAN-VERIFICATION.md` §16 |

### 남은 것

`PENDING-HUMAN-VERIFICATION.md` §16 의 넷. 전부 사람이 판단해야 하는 것이다 —
조작 횟수 측정, 성공률 측정, 시행착오 루프의 체감, 「브라우저 열림」 표시의 충분함.


---

## Phase 7: Convergence

**2026-09-11 수렴 1회차** — 발견 5건 (CRITICAL 0 · HIGH 1 · MEDIUM 3 · LOW 1).
헌법 원칙 I~V 위반 없음.

- [X] T071 **도착점에 닿지 못하면 재녹화를 시작하지 않는다** per FR-020 (contradicts) — `backend/src/itb/api/routes/sessions.py` 의 `mode=rerecord` 분기가 러너를 띄우기 **전에** `RerecordTransaction` 을 만든다. 앞 구간이 깨져 도착점에 닿지 못해도 교체가 시작된 상태로 남고, 그때 화면은 재녹화 띠를 그린다. 러너 실패를 관측해 트랜잭션을 닫고 그 사실을 알린다 (`rerecord_changed: null` + 실패한 Step 을 가리키는 안내)
- [X] T072 `specs/016-ai-range-rerecord/contracts/api-contract.md` §1 실패표를 **실제 흐름에 맞게** 고친다 per api-contract §1 (contradicts) — 「도착점에 닿지 못했다 → `409`」는 성립하지 않는다. 러너를 요청 안에서 기다려야 하는데 그것은 research R1(요청 수명과 분리)을 깬다. 실제는 `201` 뒤 `state: failed` 이며, T071 이 그 자리에서 트랜잭션을 닫는다
- [X] T073 [P] `backend/tests/us_rerecord/test_discard_realign.py` 에 **되맞춤 실패** 경로를 더한다 per FR-031c · 불변식 11 (missing) — 지금은 성공 경로만 본다. 실패를 유도해 `rerecord_realign_failed` 가 **두 사실**(`definition_reverted: true` + 사유)을 함께 싣는지 확인한다. 하나만 말하면 사용자는 무엇을 믿어야 할지 모른다
- [X] T074 [P] `backend/tests/us_rerecord/test_session_lost_in_rerecord.py` 신규 per FR-044 (missing) — 재녹화 중 세션 유실을 유도한다. 확정되지 않은 Step 이 **보존**되고, 목록이 「새 + 옛」 중간 상태임을 알리며, 트랜잭션이 닫히는지 확인한다
- [X] T075 [P] `backend/tests/us_rerecord/test_sensitive_in_rerecord.py` 에 **대화 이력이 디스크에 없음**을 더한다 per FR-014 (partial) — 지금은 정의 파일만 본다. FR-013(민감값이 이력에 남지 않는다)의 실질적 방어가 「쓰지 않는다」이므로, 세션 종료 후 프로젝트 디렉터리 전체에서 대화 문장을 찾아 없음을 확인한다
- [X] T076 [P] `frontend/tests/RerecordStart.test.tsx` 에 **점유 중 잠김** 1건을 더한다 per FR-017 (partial) — 다른 세션이 그 테스트를 잡고 있으면(`blocking_session_id`) 「AI 로 다시 만들기」가 보이되 잠기고 해소 조작을 가리키는지. 서버의 409 는 기존 기제로 동작하지만 화면이 **미리** 막는지는 확인되지 않았다
