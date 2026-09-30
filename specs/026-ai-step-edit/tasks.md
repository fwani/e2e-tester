---

description: "026 고른 Step 을 AI 에게 고쳐 달라기 — 작업 목록"
---

# Tasks: 고른 Step 을 AI 에게 고쳐 달라기

**Input**: `specs/026-ai-step-edit/` 의 설계 문서

**Prerequisites**: plan.md · spec.md · research.md · data-model.md · contracts/

**Tests**: **포함한다.** 헌법 Quality Gates 3 이 「제품은 테스트 도구이며, 자기 테스트
없이 내보내지 않는다」로 요구한다. 이 기능은 **권한 경계를 다시 긋는** 변경이므로, 넓힌
자리와 넓히지 않은 자리를 검사가 고정하지 않으면 회귀를 볼 방법이 없다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일 · 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 User Story 인가 (US1~US4)

## Path Conventions

Web app — `backend/src/itb/`, `backend/tests/`, `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup — 기준선

**Purpose**: 고치기 전 상태를 수치로 남긴다. 없으면 끝에서 무엇이 달라졌는지 말할 수 없다.

- [ ] T001 시작 시점 전량 검증을 돌려 기준선을 `specs/026-ai-step-edit/baseline.md` 에 기록한다 — `cd backend && bash scripts/test-backend.sh` · `uv run ruff check src/ tests/` · `uv run lint-imports` · `cd frontend && npx vitest run` · `npx tsc --noEmit`. **기존 실패를 새 실패와 섞지 않기 위한 것이다**
- [ ] T002 [P] 016 의 재녹화 관련 검사 파일 목록을 `baseline.md` 에 적는다 — FR-030(016 이 그대로 돈다)의 판정 근거가 될 목록이다. `grep -rln "rerecord" backend/tests/ frontend/src/` 로 찾는다

**Checkpoint**: 기준선이 문서로 남았다.

---

## Phase 2: Foundational — 순수 함수와 트랜잭션

**Purpose**: 모든 User Story 가 이 둘 위에 선다. 세션도 브라우저도 모르는 순수한 층이며,
여기가 틀리면 위의 전부가 틀린다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 User Story 도 시작할 수 없다.

- [ ] T003 [P] `backend/tests/test_step_edits_restore.py` 에 `restore_step()` 검사를 쓴다 — ① 대상이 목록에 있으면 그 자리를 원본으로 교체한다 ② 대상이 지워졌으면 `at_index` 에 되끼운다 ③ 목록이 짧아졌으면 클램프한다 ④ 원본을 바꾸지 않고 새 상태를 돌려준다. **구현 전에 쓰고 실패를 확인한다**
- [ ] T004 `backend/src/itb/execution/step_edits.py` 에 `restore_step(steps, current_step_index, origin, at_index) -> EditResult` 를 더한다 (data-model §2). **기존 `_clamp()` 를 재사용한다** — 위치 계산을 새로 만들지 않는다
- [ ] T005 [P] `backend/tests/test_step_edit_transaction.py` 에 `StepEditTransaction` 검사를 쓴다 — 불변식 A~D (data-model §1). 특히 ① `owns()` 가 `target_id` 와 `created` 에만 참 ② `can_commit()` 이 **만든 것이 없어도 참** (016 과 다른 자리) ③ 버리기 뒤 id 수열까지 동일 ④ `settled` 뒤 `owns()` 가 쓰이지 않음
- [ ] T006 `backend/src/itb/authoring/step_edit.py` 를 신설한다 — `StepEditTransaction`(`target_id`·`origin`·`arrival_index`·`baseline_ids`·`settled`)과 `created`·`owns`·`can_commit`·`commit`·`discard`·`close`. **`discard` 는 하나의 `EditResult` 를 돌려준다** — 먼저 지우고 나중에 되돌린다 (research R7). 모듈 docstring 에 「왜 형제 모듈인가」(research R2)를 적는다
- [ ] T007 `backend/src/itb/authoring/rerecord.py` 가 **바뀌지 않았는지** 확인한다 — `git diff` 로 빈 결과여야 한다 (FR-030)

**Checkpoint**: 순수 층이 검사로 고정됐다. 세션 배선을 시작할 수 있다.

---

## Phase 3: User Story 1 — 고른 Step 을 AI 가 화면을 보며 고친다 (P1) 🎯 MVP

**Goal**: Step 하나를 골라 시작하면 브라우저가 그 Step 직전까지 실행되고, AI 가 지금
화면을 보며 그 Step 을 보존한 채 고친다.

**Independent Test**: Step 5개짜리 저장된 테스트에서 3번을 고르고 대상 재지정을 지시한 뒤,
3번의 대상만 바뀌고 나머지 속성·다른 Step 이 그대로인지 확인한다.

### Tests for User Story 1

- [ ] T008 [P] [US1] `backend/tests/test_session_step_edit_start.py` 에 세션 시작 계약 검사를 쓴다 (contracts/api-contract §1) — ① `mode="step_edit"` + `step_edit_step_id` 로 세션이 열린다 ② id 가 없으면 `DEFINITION_INVALID` ③ 정의에 없는 id 면 거절 ④ 대상이 첫 Step 이면 실행 없이 시작 주소만 연다 ⑤ 도착점 실패 시 세션을 열지 않는다
- [ ] T009 [P] [US1] `backend/tests/test_tool_descriptions_scope.py` 에 **`TOOL_SCHEMAS` 를 직접 보는** 검사를 쓴다 — 편집 도구 넷의 설명문에 「사용자가 고쳐 달라고 지목한 Step」이 들어 있고, 옛 문구(「다른 Step 은 고칠 수 없다 — 사람에게 말하라」)가 남아 있지 않다. **docstring 이 아니라 `TOOL_SCHEMAS` 를 본다** — 그것이 모델이 실제로 받는 것이고 선택 의존성도 필요 없다 (research R8)
- [ ] T010 [P] [US1] `backend/tests/test_principle_ii_timeline.py` 에 `step_edit` 모드 경우를 더한다 — 도착점 실행 구간에 에이전트 태스크가 살아 있지 않다 (원칙 II · 016 불변식 6)

### Implementation for User Story 1

- [ ] T011 [US1] `backend/src/itb/api/routes/sessions.py` 의 `SessionWork` 에 `step_edit: StepEditTransaction | None = None` 을 더한다 (data-model §3)
- [ ] T012 [US1] 같은 파일의 `SessionStartRequest` 에 `mode="step_edit"` 과 `step_edit_step_id: str | None` 을 더한다. **배열이 아니다** — 「둘 이상」이 경계에서 표현조차 되지 않는다 (data-model §4)
- [ ] T013 [US1] 같은 파일의 세션 시작에 `elif body.mode == "step_edit":` 분기를 더한다 — `BEGIN_REPLAY` → `_build_engine` → 트랜잭션 생성 → `_start_runner(start_index=0, pause_before_index=arrival)`. **`rerecord` 분기와 3번만 다르다** (research R4). 순서가 계약이라는 주석을 남긴다
- [ ] T014 [US1] 같은 파일의 `in_scope` 람다에 `step_edit` 항을 더한다 (research R1) — 둘째 항이 거짓이면 판정이 016 과 글자 그대로 같다는 사실을 주석에 적는다
- [ ] T015 [P] [US1] `backend/src/itb/authoring/tools.py` 의 `TOOL_SCHEMAS` 에서 `update_step`·`delete_step`·`move_step`·`repick_target` 넷의 설명문을 고친다 (contracts/agent-tools §2). **여기가 원천이다**
- [ ] T016 [P] [US1] 같은 파일의 `BrowserToolbox` 편집 메서드 docstring 과 `_editable()` 의 거절문을 고친다 — 거절문은 **무엇이 허용되는지 함께** 말한다 (FR-016)
- [ ] T017 [P] [US1] `backend/src/itb/authoring/agent.py` 의 `SYSTEM_PROMPT` 에서 편집 권한 지침을 고친다. **T015~T017 셋이 같이 가야 모델 행동이 바뀐다**
- [ ] T018 [US1] `backend/src/itb/api/routes/sessions.py` 의 `summary_source` 에 「고쳐 달라고 요구받은 Step」 표시를 넘긴다 (FR-011 · contracts/agent-tools §3) — 016 의 `range_ids` 와 **같은 통로**를 쓴다. 새 통로를 만들지 않는다
- [ ] T019 [US1] 같은 파일에 `StepEditView` 와 `_step_edit_view()` 를 더하고 `SessionView` 에 싣는다 (contracts/api-contract §4)
- [ ] T020 [US1] `step_edit_changed` 이벤트를 발행한다 — 편집이 반영될 때(`_apply_ai_edit` 이후)와 트랜잭션이 끝날 때. **`rerecord_changed` 를 재사용하지 않는다** (data-model §5)
- [ ] T021 [P] [US1] `frontend/src/api/client.ts` 에 `step_edit` 모드 세션 시작과 `StepEditView` 타입을 더한다
- [ ] T022 [P] [US1] `frontend/src/api/ws.ts` 에 `step_edit_changed` 이벤트 타입을 더한다
- [ ] T023 [US1] `frontend/src/lib/actions.ts` 에 `ai.stepEdit` 을 등록한다 (contracts/ui-contract §1)
- [ ] T024 [US1] `frontend/src/lib/capabilities.ts` 의 **모든 국면**에 `ai.stepEdit` 셀을 채운다. 빈칸을 허용하지 않는 것이 011 이 이 표를 만든 이유다
- [ ] T025 [US1] `frontend/src/pages/EditView.tsx` 에 시작 입구를 붙인다 — 고른 것이 **정확히 하나**인지 화면이 먼저 보고, 아니면 시작하지 않고 이유를 말한다 (FR-003 · 016 FR-016 이 세운 규칙)
- [ ] T026 [US1] `frontend/src/pages/SessionScreen.tsx` 가 `step_edit` 상태를 소유하고 `step_edit_changed` 를 소비한다. **소비하는 코드가 없으면 타입만 있고 아무 일도 일어나지 않는다**
- [ ] T027 [US1] `SessionWorkbench` → `Workbench` 로 `step_edit` 을 통과시킨다 (contracts/ui-contract §6). **가운데 둘은 통과만 하므로 빠뜨려도 타입 검사가 통과한다** — `grep -rn` 으로 쓰이는 곳이 둘 이상인지 확인한다
- [ ] T028 [US1] 수정 대상 Step 을 목록에서 구분해 그린다 (FR-033). 새 CSS 클래스는 `frontend/src/theme/workspace.css` 정본에 선언한다

**Checkpoint**: Step 하나를 골라 AI 에게 고쳐 달라고 할 수 있다. 되돌릴 수는 아직 없다.

---

## Phase 4: User Story 2 — 마음에 안 들면 원래대로 되돌린다 (P1)

**Goal**: 확정과 버리기. 버리면 대상이 시작 전 모습으로 돌아오고 화면도 맞춰진다.

**Independent Test**: Step 하나를 AI 로 고친 뒤 버리기를 누르고, Step 목록이 시작 전과
완전히 같은지(식별자 포함) 20회 반복해 확인한다.

### Tests for User Story 2

- [ ] T029 [P] [US2] `backend/tests/test_session_step_edit_settle.py` 에 확정·버리기 계약 검사를 쓴다 (contracts/api-contract §2·§3) — ① 확정은 **아무 Step 도 지우지 않는다** ② 만든 것이 없어도 확정된다 ③ 버리기는 만든 것을 지우고 대상을 원본으로 되돌린다 ④ 끝난 트랜잭션에 다시 걸면 `CONFLICT` ⑤ 버리기가 세션을 끝내지 않는다
- [ ] T030 [P] [US2] 같은 파일에 **부분 적용이 남지 않는지** 검사를 쓴다 — 버리기가 하나의 `EditResult` 로 적용된다 (research R7). 중간 상태가 세션에 반영되는 경로가 없어야 한다
- [ ] T031 [P] [US2] AI 가 **대상 Step 을 지운 뒤** 버리기를 눌렀을 때 원래 자리로 되돌아오는지 검사한다 — `restore_step` 의 둘째 경우가 실제 경로에서 쓰이는 자리다
- [ ] T032 [P] [US2] 확정되지 않은 수정이 **디스크에 내려가지 않는지** 검사한다 (FR-024)

### Implementation for User Story 2

- [ ] T033 [US2] `backend/src/itb/api/routes/sessions.py` 에 `POST /{session_id}/step-edit/commit` 을 더한다 — 트랜잭션을 닫고 `step_edit_changed(null)` 을 낸다. **브라우저를 요구하지 않는다** (FR-023)
- [ ] T034 [US2] 같은 파일에 `POST /{session_id}/step-edit/discard` 를 더한다 — `discard()` 결과를 `_apply_rerecord_edit`(기존 반영 함수)으로 한 번에 적용하고 트랜잭션을 닫는다
- [ ] T035 [US2] 버리기 뒤 `_return_to_start()` → `_realign_to_arrival()` 로 화면을 되맞춘다 (FR-025). **016 의 함수를 그대로 부른다** — 새로 만들지 않는다
- [ ] T036 [US2] 되맞춤 실패 시 `step_edit_realign_failed` 를 낸다 — `definition_reverted: true` 와 사유를 함께 싣는다 (FR-028 · contracts/api-contract §3)
- [ ] T037 [US2] `_require_open_step_edit()` 헬퍼를 더한다 — 016 의 `_require_open_rerecord()` 와 같은 모양
- [ ] T038 [P] [US2] `frontend/src/api/client.ts` 에 확정·버리기 호출을 더한다
- [ ] T039 [P] [US2] `frontend/src/api/ws.ts` 에 `step_edit_realign_failed` 를 더한다
- [ ] T040 [US2] `frontend/src/lib/actions.ts`·`capabilities.ts` 에 `ai.stepEditCommit`·`ai.stepEditDiscard` 를 등록하고 모든 국면의 셀을 채운다
- [ ] T041 [US2] 확정·버리기 자리를 화면에 붙인다 — 016 의 재녹화 확정·버리기와 같은 모양으로, 같은 자리에 (contracts/ui-contract §3)
- [ ] T042 [US2] 되맞춤 실패를 화면이 **두 사실로** 알린다 — 정의는 되돌아갔고 화면은 어긋나 있다
- [ ] T043 [US2] 대상 Step 의 **바뀐 자리**를 화면이 보여준다 (FR-034) — 시작 시점 모습을 화면이 들고 있다가 비교한다. 서버가 차이를 계산해 주지 않는다 (data-model §5)

**Checkpoint**: 되돌릴 수 있다. 이 기능이 실제로 쓸 만해지는 지점이다.

---

## Phase 5: User Story 3 — 고르지 않은 것은 AI 가 건드리지 않는다 (P2)

**Goal**: 권한 경계가 말이 아니라 코드로 성립한다. 016 의 기존 경계는 그대로다.

**Independent Test**: 고르지 않은 Step 을 지목하는 지시를 주고, 그 Step 이 바뀌지 않으며
거절 사실이 사용자에게 보이는지 확인한다.

### Tests for User Story 3

- [ ] T044 [P] [US3] `backend/tests/test_step_edit_scope.py` 에 권한 검사를 쓴다 — ① 고른 Step 은 고칠 수 있다 ② 이번에 만든 Step 도 고칠 수 있다 ③ **그 밖은 전부 거절** ④ 거절이 예외가 아니라 반환값이다 (016 FR-038 의 성질)
- [ ] T045 [P] [US3] **FR-014 회귀 검사**를 쓴다 — `step_edit` 이 `None` 인 세션에서 `in_scope` 판정이 016 과 동일하다. 재녹화 세션·일반 AI 작성 세션 둘 다
- [ ] T046 [P] [US3] 거절문이 **무엇이 허용되는지 말하는지** 검사한다 (FR-016) — 허용 대상의 식별자가 문장에 들어 있어야 한다
- [ ] T047 [P] [US3] 권한이 **세션 도중 넓어지지 않는지** 검사한다 (FR-017) — 트랜잭션 생성 후 `target_id` 가 바뀌는 경로가 없다

### Implementation for User Story 3

- [ ] T048 [US3] `backend/src/itb/authoring/tools.py` 의 `_editable()` 거절문에 허용 대상을 싣는다. **판정은 여전히 `in_scope` 가 한다** — 도구는 정책을 알지 않는다 (research R1)
- [ ] T049 [US3] 거절이 사용자에게 보이도록 기존 통로를 확인한다 — 016 FR-038 이 이미 세운 길이며, 새로 만들지 않는다
- [ ] T050 [US3] 016 의 재녹화 검사 전부를 돌려 **하나도 깨지지 않았는지** 확인한다 (FR-030 · T002 의 목록)

**Checkpoint**: 경계가 검사로 고정됐다. 넓힌 자리와 넓히지 않은 자리가 둘 다 증명된다.

---

## Phase 6: User Story 4 — 두 조작의 차이를 누르기 전에 안다 (P2)

**Goal**: 편집 화면의 두 AI 입구가 「고른 Step 이 남는가」로 갈린다.

**Independent Test**: 두 조작을 나란히 두고 설명과 잠금 사유를 읽었을 때, 처음 보는
사용자가 「고른 Step 이 남는가」를 정확히 답할 수 있는지 확인한다.

### Tests for User Story 4

- [ ] T051 [P] [US4] `frontend/tests/` 에 두 조작의 **잠금 사유가 서로 다른지** 검사한다 (FR-032 · contracts/ui-contract §2) — 같은 문장이면 실패
- [ ] T052 [P] [US4] 고른 개수별 조작 상태를 검사한다 — 0개 / 1개 / 2개 연속 / 2개 불연속 네 경우에 대해 두 조작의 활성·잠금이 표대로인지
- [ ] T053 [P] [US4] 기존 편집 흐름이 달라지지 않았는지 검사한다 (FR-035) — 기존 화면 검사가 그대로 통과해야 한다

### Implementation for User Story 4

- [ ] T054 [US4] 두 조작의 라벨과 한 줄 설명을 정한다 (contracts/ui-contract §2) — 「고른 Step 을 **버리고** 새로 만든다」 / 「고른 Step 을 **남긴 채** 고친다」
- [ ] T055 [US4] `frontend/src/lib/capabilities.ts` 의 잠금 사유를 조작별로 다르게 쓴다 — `ai.stepEdit` 의 「둘 이상」 사유를 새로 더한다
- [ ] T056 [US4] `frontend/src/pages/EditView.tsx` 에서 두 조작을 **나란히** 놓고 설명을 함께 보인다
- [ ] T057 [US4] 편집 국면의 `ai.chat` 해소 조작을 검토한다 — `ai.rerecord` 를 계속 가리킨다 (contracts/ui-contract §4). 바꾸지 않기로 한 결정도 주석으로 남긴다

**Checkpoint**: 네 User Story 가 전부 동작한다.

---

## Phase 7: Polish & Cross-Cutting

- [ ] T058 [P] 민감 값이 대화 이력·에이전트 컨텍스트에 나타나지 않는지 검사한다 (FR-041 · SC-008) — 016 의 검사 형식을 따른다
- [ ] T059 [P] 세션 유실 시 확정되지 않은 수정의 운명이 명확한지 확인하고 검사한다 (FR-039)
- [ ] T060 [P] 도구 호출 상한에 닿았을 때 그때까지의 수정이 보존되는지 검사한다 (FR-037)
- [ ] T061 [P] `test_tool_surface.py` 가 여전히 16종을 고정하는지 확인한다 — 도구가 늘지 않았다
- [ ] T062 `frontend/src/theme/workspace.css` 에 새 클래스가 정본으로 선언됐는지 확인한다 — `VisualLanguage.test.tsx`·`ClassExistence.test.ts` 가 잡는다
- [ ] T063 새로 만든 프론트 컴포넌트가 **쓰이는 곳이 둘 이상인지** 확인한다 — 하나면 배선이 덜 된 것이다 (contracts/ui-contract §6)
- [ ] T064 전량 검증을 돌리고 결과를 `baseline.md` 의 시작 시점과 비교해 적는다 — 새로 깨진 것이 없어야 한다
- [ ] T065 `specs/026-ai-step-edit/quickstart.md` 의 §1~§4 를 실제 모델로 손으로 확인한다. **가짜 드라이버로는 대신할 수 없다** — 「모델이 권한이 넓어진 것을 아는가」는 실제 설명문을 읽을 때만 드러난다
- [ ] T066 [P] `README.md`·`PRODUCT.md` 에 이 조작이 설명되어 있는지 확인하고 필요하면 더한다

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음
- **Phase 2 (Foundational)**: Phase 1 후. **모든 User Story 를 막는다** — 순수 층이 틀리면 위가 전부 틀린다
- **Phase 3 (US1)**: Phase 2 후. MVP
- **Phase 4 (US2)**: **Phase 3 후** — 되돌릴 대상이 있어야 되돌리기를 만들 수 있다
- **Phase 5 (US3)**: Phase 3 후. Phase 4 와 병렬 가능
- **Phase 6 (US4)**: Phase 3 후. Phase 4·5 와 병렬 가능
- **Phase 7 (Polish)**: 원하는 User Story 가 전부 끝난 뒤

### User Story Dependencies

- **US1 (P1)**: Foundational 후 즉시. 다른 Story 에 의존하지 않는다
- **US2 (P1)**: **US1 에 의존한다.** 예외적으로 독립이 아니다 — 수정 세션이 없으면 확정·버리기가 무엇에 걸릴지 정의되지 않는다
- **US3 (P2)**: US1 후. US2 와 독립
- **US4 (P2)**: US1 후. 화면만 건드리므로 US2·US3 와 완전 독립

### Parallel Opportunities

- T003 · T005 (Foundational 의 두 검사) — 다른 파일
- T008 · T009 · T010 (US1 검사 셋)
- T015 · T016 · T017 (설명문 세 자리) — **다른 파일이지만 셋이 같이 가야 뜻이 있다.** 따로 커밋하지 않는다
- T021 · T022 (프론트 타입 둘)
- T029~T032 (US2 검사 넷)
- T044~T047 (US3 검사 넷)
- T051~T053 (US4 검사 셋)
- Phase 5 와 Phase 6 전체 — 백엔드와 프론트로 갈린다

---

## Implementation Strategy

### MVP (US1 만)

1. Phase 1 → Phase 2 → Phase 3
2. **멈추고 확인한다**: Step 하나를 골라 AI 가 고치는가. quickstart §2 를 손으로 본다
3. 이 시점에서 되돌리기가 없으므로 **사용자에게 내보내지 않는다** — 되돌릴 수 없는 수정은 저장된 테스트에 쓸 수 없다

### 증분 전달

1. Setup + Foundational → 순수 층 준비
2. US1 → 고칠 수 있다 (아직 내보내지 않는다)
3. **US2 → 되돌릴 수 있다 (여기가 실제 전달 지점)**
4. US3 → 경계가 검사로 고정된다
5. US4 → 두 입구가 갈린다

### 주의

- **US2 를 건너뛰지 않는다.** US1 만으로는 기능이 아니라 위험이다.
- **T015~T017 을 나누지 않는다.** 하나만 고치면 코드는 넓어졌는데 모델은 옛 안내를 따른다.
- **T007·T050 을 건너뛰지 않는다.** 016 이 그대로 도는지가 이 기능의 전제다 (FR-030).

---

## Notes

- `[P]` = 다른 파일 · 의존 없음
- 각 작업 또는 논리적 묶음 뒤에 커밋한다
- 검증은 저장소 표준 명령으로 한다 — `uv run pytest`·`npm test` 는 틀린 결과를 준다
- 기존 실패(기준선)와 새 실패를 섞지 않는다
