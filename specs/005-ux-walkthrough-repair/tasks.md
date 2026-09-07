---

description: "Task list for 005 — UX 워크스루 결함 수정"
---

# Tasks: UX 워크스루 결함 수정 — 실행 왕복과 정직한 상태 표시

**Input**: Design documents from `/specs/005-ux-walkthrough-repair/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: 포함한다. 헌법 Quality Gate 3 이 자동 테스트를 요구하고("제품은 테스트 도구다.
자기 테스트 없이 내보내는 것은 허용되지 않는다"), 명세에 시간·횟수가 박힌 요구사항은
사람이 다시 걸어 확인하는 것으로 회귀를 막을 수 없다 (research R11).

**Organization**: 사용자 스토리별로 묶었다. 각 스토리는 독립적으로 구현·검증·전달할 수 있다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리인가 (US1~US8)
- 설명에 정확한 파일 경로를 넣는다

## Path Conventions

웹 앱 구조다 — `backend/src/itb/`, `frontend/src/`, 테스트는
`backend/tests/{unit,contract,integration,abnormal}/`, `frontend/tests/`.

---

## Phase 1: Setup (검증 재료)

**Purpose**: 22건을 검증할 재료를 먼저 만든다. 재료 없이는 어느 스토리도 검증할 수 없다.

- [X] T001 [P] `fixtures/sample-app` 위에서 도는 검증용 테스트 정의 두 개를 픽스처로 만든다 — `backend/tests/fixtures/tc_fail_midstep.yaml` (7 Step, Step 06 이 존재하지 않는 `testId` 로 대기 예산을 소진하며 실패, Step 07 은 미실행으로 남는다) 와 `backend/tests/fixtures/tc_pass.yaml` (5 Step, 항상 통과). quickstart.md §0 의 재료 표와 일치시킨다
- [X] T002 [P] 정적 페이지 세션에서 미러 프레임 도달을 재는 통합 테스트 하니스를 `backend/tests/integration/conftest.py` 에 추가한다 — 세션을 만들고 **구독을 늦게 붙이는** 픽스처. U-24 검증(FR-161)의 전제다
- [X] T003 [P] 프론트 컴포넌트 테스트에서 응답을 지연시킬 수 있는 헬퍼를 `frontend/tests/helpers/pending.ts` 에 추가한다 — 클릭 직후(응답 전) 화면을 단정하기 위한 pending Promise. FR-129·FR-142 검증의 전제다

**Checkpoint**: 재료 준비 완료 — 실패·통과·전이·미러를 각각 재현할 수 있다

---

## Phase 2: Foundational (차단 전제)

**Purpose**: 모든 스토리가 읽는 계약과 어휘. 여기가 끝나기 전에는 어느 스토리도 시작할 수 없다.

**⚠️ CRITICAL**: T004~T006 은 **한 흐름으로 끝낸다.** 부분적으로 재생성하면
`test_schema_drift.py` 가 중간 상태에서 실패해 원인을 가린다 (헌법 Cross-language schema duty).

- [X] T004 `backend/src/itb/domain/run_result.py` 에서 `Outcome` 을 `pass·fail·stopped·partial_pass` 로 넓히고 `RunScope`(`full·partial`) 를 추가한다. data-model.md §1·§2 의 판정 우선순위를 docstring 에 적는다
- [X] T005 같은 파일의 `RunResult` 에 `start_index`·`scope`·`attempted_count`·`stopped_step_index` 를 추가한다. `total_count`·`passed_count` 의 뜻은 바꾸지 않는다 (data-model.md §2)
- [X] T006 스키마 생성물을 갱신한다 — `cd backend && uv run python -m itb.schema.export` 로 `backend/schema/run-result.schema.json` 을 재생성하고, `cd frontend && npm run gen:types` 로 `frontend/src/types/` 를 재생성해 **함께 커밋한다**
- [X] T007 [P] `backend/tests/contract/test_schema_drift.py` 가 통과하는지 확인하고, 새 결말 값이 스키마에 실렸음을 단정하는 계약 테스트를 `backend/tests/contract/test_run_outcome_contract.py` 에 추가한다 (FR-131·FR-137)
- [X] T008 [P] `backend/tests/unit/test_outcome_decision.py` — 결말 판정 우선순위를 순수 함수로 고정한다: 중지 > 실패 건너뜀 > 실패 > 통과. 세션 유실은 `fail` (data-model.md §1)
- [X] T009 `backend/src/itb/api/routes/sessions.py` 의 `SessionView` 에 `step_results: list[StepProgress]`·`pause_settled: bool`·`run_scope`·`run_start_index`·`saved_at` 을 추가하고 `StepProgress` 모델을 정의한다. `view_of()` 가 러너의 `results` 와 `at_boundary` 에서 값을 채운다 (contracts/rest-api.md §2)
- [X] T010 [P] `backend/tests/contract/test_session_view_contract.py` — 세션 뷰가 다섯 필드를 싣는지, `step_results` 의 `outcome` 이 `StepOutcome` 네 값인지 단정한다 (FR-171)
- [X] T011 [P] `frontend/src/lib/wording.ts` 를 만든다 — `outcomeLabel()`·`outcomeChip()`·`stepLabel(index0)`·`runSummary()`. contracts/ui-contract.md §1~§4 의 표를 그대로 구현한다. **`stepLabel` 이 0-기반 → 표시 변환의 유일한 지점**이다 (FR-138·FR-141)
- [X] T012 [P] `frontend/tests/wording.test.ts` — `stepLabel(5) === "Step 06"`, 결말 4값이 각각 한 문장·한 칩으로만 대응하는지, 요약 문장의 분모가 `attempted_count` 인지 단정한다 (FR-138·FR-141·U-02)

**Checkpoint**: 계약과 어휘가 준비됐다 — 스토리 구현을 병렬로 시작할 수 있다

---

## Phase 3: User Story 1 — 실패를 읽고 그 자리에서 다시 건다 (Priority: P1) 🎯 MVP

**Goal**: 실패 진단 → 재실행 왕복이 결과 화면에서 끊기지 않는다. 리포트가 "가장 아픈 것"
으로 지목한 것이다.

**Independent Test**: 실패하는 테스트의 결과 화면에서 「처음부터 실행」·「Step 06부터 실행」
을 눌러 실제로 실행이 시작되는지만 보면 검증된다.

### Tests for User Story 1

- [X] T013 [P] [US1] `backend/tests/integration/test_rerun_after_finish.py` — 종료된 세션(`failed`)이 등록에 남아 있어도 같은 테스트의 `POST /api/sessions` 가 201 인지 단정한다 (FR-124·SC-212). 현재는 409 다
- [X] T014 [P] [US1] `backend/tests/integration/test_concurrent_session_create.py` — 같은 `test_id` 로 동시 생성 5건을 보내 **정확히 1건만 201**, 나머지는 409 `SESSION_ALREADY_ACTIVE` 인지 단정한다 (FR-128·SC-213)
- [X] T015 [P] [US1] `backend/tests/abnormal/test_session_reject_payload.py` — 정말 실행 중일 때의 409 본문이 `detail.session_id` 를 싣고, `message`·`next_action` 에는 세션 식별자가 **없는지** 단정한다 (FR-126·FR-135)
- [X] T016 [P] [US1] `frontend/tests/RunTrigger.test.tsx` — 실행 버튼 클릭 직후(응답 전) 버튼이 비활성이고 준비 문구가 보이는지, 100 ms 안에 5회 클릭해도 호출이 1회인지 단정한다 (FR-127·FR-129·SC-213·SC-214). T003 헬퍼를 쓴다
- [X] T017 [P] [US1] `frontend/tests/TestListRowActions.test.tsx` — 결말이 실패·통과·중지·부분 성공 각각일 때 행에서 「실행」에 항상 도달하고, 결과가 있으면 「결과 보기」에도 도달하는지 단정한다 (FR-130)

### Implementation for User Story 1

- [X] T018 [US1] `backend/src/itb/execution/session.py` 의 `active_session_for_test()` 가 **살아 있는 세션만** 돌려주게 한다. 판정은 기존 `ACTIVE_STATES` 를 쓰고 새 목록을 만들지 않는다. 종료 상태에 도달한 세션은 `_by_test` 등록에서 떼어낸다 (FR-124, research R4-A)
- [X] T019 [US1] `backend/src/itb/api/routes/sessions.py` 의 세션 생성에 **테스트별 락과 예약**을 넣는다. 락 안에서 확인과 예약을 함께 하고, 브라우저 기동은 락 밖에서 한다. 생성 실패 시 예약을 되돌린다 (FR-128, research R4-B)
- [X] T020 [US1] 같은 파일의 거절 응답 본문을 contracts/rest-api.md §1 형태로 바꾼다 — `detail.session_id` 를 싣고 사용자 문구에서 식별자를 뺀다 (FR-126·FR-135)
- [X] T021 [P] [US1] `frontend/src/App.tsx` 에 `startRun(testId, { fromIndex })` 단일 실행 경로를 만든다. 진행 중 상태(pending)를 여기서 관리해 in-flight 가드가 한 곳에 있게 한다. 결과 화면과 실행 화면이 이것만 부른다 (FR-127, research R4-C)
- [X] T022 [US1] `frontend/src/pages/RunResult.tsx` 의 재실행 버튼 두 개를 `startRun` 으로 옮긴다. 클릭 즉시 비활성 + 「실행을 준비하는 중…」 (FR-125·FR-129, ui-contract §5)
- [X] T023 [US1] `frontend/src/pages/SessionScreen.tsx` 의 `rerun` 도 `startRun` 을 쓰게 한다. 종료 세션이 다음 실행을 막지 않으므로 `discard` 선행이 필요 없어진다 (FR-125)
- [X] T024 [US1] 실행 거절 시 화면에 **이동 수단**을 붙인다 — `detail.session_id` 로 그 세션 화면으로 가는 버튼. `RunResult.tsx` 와 `TestList.tsx` 양쪽 (FR-126)
- [X] T025 [P] [US1] `frontend/src/pages/TestList.tsx` 의 행 액션을 고친다 — 「실행」은 항상, 결과가 있으면 「결과 보기」도. 한 자리에 둘 중 하나만 두는 분기를 없앤다 (FR-130, U-12·U-13)
- [X] T026 [P] [US1] 목록 행의 실행 버튼에도 in-flight 가드와 「준비 중…」 라벨을 적용한다 (FR-127·FR-129)

**Checkpoint**: 실패 → 진단 → 재실행 왕복이 성립한다. **여기까지가 MVP다.**

---

## Phase 4: User Story 2 — 화면이 말하는 결말이 실제 결말과 같다 (Priority: P1)

**Goal**: 중지는 중지로, 실패는 실패로 기록·표시된다. 실패한 Step 이 화면에서 사라지지 않고
목록과 결과 화면이 같은 Step 번호를 말한다.

**Independent Test**: 실패하는 테스트로 중지·재개·완료 경로를 걷고 화면 표시와 저장된 실행
결과가 일치하는지 비교하면 검증된다.

### Tests for User Story 2

- [X] T027 [P] [US2] `backend/tests/integration/test_stop_outcome.py` — 실행 중 중지 후 저장된 `outcome == "stopped"` 이고 `stopped_step_index` 가 채워지며 실패 집계에 없는지 단정한다 (FR-131·SC-215)
- [X] T028 [P] [US2] 같은 파일에서 의도적 중지가 `session_lost` 이벤트를 **발행하지 않는지** 단정한다. 진짜 유실(탭 전부 닫힘)에서는 발행되는지도 함께 단정한다 (FR-132, U-03)
- [X] T029 [P] [US2] `backend/tests/unit/test_session_loss_guard.py` — 유실 감지 가드가 `REVIEW` 를 정상 종료로 취급하는지 단정한다 (FR-132)
- [X] T030 [P] [US2] `backend/tests/integration/test_resume_with_failed_step.py` — 실패 Step 이 있는 일시정지에서 재개가 그 Step 을 지나가지 않는지, 건너뛰기 경로의 결말이 `partial_pass` 인지 단정한다 (FR-136·FR-137)
- [X] T031 [P] [US2] `backend/tests/abnormal/test_stop_twice.py` — 이미 끝난 세션에 중지가 다시 도착하면 오류가 아니라 현재 뷰를 돌려주는지 단정한다 (contracts/rest-api.md §4, 엣지 케이스)
- [X] T032 [P] [US2] `frontend/tests/StepNumberConsistency.test.tsx` — 목록 행·결과 화면·실행 화면이 같은 실패 Step 번호를 내는지 단정한다. 모두 `stepLabel()` 을 지나야 한다 (FR-138·SC-216)
- [X] T033 [P] [US2] `frontend/tests/OutcomeVocabulary.test.tsx` — 한 화면에 결말 어휘 체계가 하나만 나타나는지, 결말 요약이 한 번만 나오는지 단정한다 (FR-140·FR-141·SC-222)

### Implementation for User Story 2

- [X] T034 [US2] `backend/src/itb/execution/session_loss.py` 의 "정상 종료면 유실이 아니다" 가드에 `REVIEW` 를 더한다 (FR-132, U-03)
- [X] T035 [US2] 같은 파일과 `api/routes/sessions.py` 의 `stop` 경로에서 **의도적 중지 시 감지기를 먼저 떼어낸다.** 가드는 그물이고 이것이 원인 제거다 (FR-132, data-model.md §6)
- [X] T036a [US2] **결말 판정의 입력 계약을 먼저 정한다** — `backend/src/itb/execution/runner.py` 의 `finalize(passed: bool, session_lost: bool)` 를 `finalize(*, session_lost: bool = False, stop_requested: bool = False, skipped_failures: bool = False)` 로 바꾸고, 결말을 그 세 값과 `results` 에서 계산하는 **순수 함수**로 분리한다. `passed` 불리언을 넘기던 호출부가 판정을 나눠 갖지 않게 한다 (FR-131·FR-137, F6)
- [X] T036b [US2] 그 순수 함수를 data-model.md §1 의 우선순위로 구현한다 — 중지 > 실패 건너뜀 > 실패 > 통과. 세션 유실은 `fail`. T008 단위 테스트가 이것을 고정한다 (FR-131·FR-137)
- [X] T036c [US2] 호출부를 갱신한다 — `_loss_handler`(`api/routes/sessions.py`)·`stop` 경로·러너 종료 경로가 각각 맞는 인자를 넘기게 한다. 중지 경로가 `stop_requested=True` 를 넘기는 것이 U-03 수정의 마지막 조각이다 (FR-131)
- [X] T037 [US2] 같은 파일에서 `attempted_count` 를 계산해 싣고(`total_count` − 건너뜀), `run_finished` 이벤트에 `attempted_count`·`scope`·`start_index` 를 더한다 (contracts/websocket.md §2)
- [X] T038 [US2] `backend/src/itb/api/routes/sessions.py` 의 `resume` 이 실패 Step 을 지나 재개하지 않게 한다. 실패 Step 이 있으면 거절하고 사유를 준다. 「건너뛰고 계속」은 **별도 요청 필드**로 분리하고 그 경로의 결말을 `partial_pass` 로 만든다 (FR-136·FR-137)
- [X] T039 [P] [US2] `frontend/src/components/Badges.tsx` 의 결말 칩을 4값으로 넓히고 `wording.ts` 에서만 라벨을 받게 한다 (FR-141, ui-contract §1)
- [X] T040 [P] [US2] `frontend/src/pages/TestList.tsx` 의 실패 Step 번호를 `stepLabel()` 로 바꾼다. 0-기반을 그대로 쓰던 곳을 없앤다 (FR-138, U-07)
- [X] T041 [US2] 저장소 전역에서 `index + 1` 을 직접 하는 Step 표시를 `stepLabel()` 로 모은다 — `RunResult.tsx`·`StepInspector.tsx`·`TestDefinition.tsx`·`SessionScreen.tsx` (FR-138)
- [X] T042 [US2] `frontend/src/pages/SessionScreen.tsx` 에서 결말 요약 **중복을 없앤다** — 얇은 회색 띠를 제거하고 결말 바 하나만 남긴다. 확정 디자인에 얇은 띠는 없다 (FR-140, research R10)
- [X] T043 [US2] 같은 파일의 진행 표시를 끝난 실행에서는 **결말 표시로 바꾼다.** `Step 07 / 07` 을 쓰지 않는다 (FR-139, ui-contract §4)
- [X] T044 [US2] 중지 결과 화면을 만든다 — `SessionScreen.tsx`/`RunnerPaused.tsx` 에서 중지 후 저장 프롬프트 대신 ui-contract §8 의 구성(중지 요약 + 네 개의 다음 행동)을 보여준다 (FR-133)
- [X] T045 [US2] 저장된 테스트를 실행하는 세션에서 「초안」 표기를 없앤다 (FR-134, U-03)
- [X] T046 [US2] 종료된 세션 조회 실패(404)를 오류 배너로 띄우지 않게 한다. 사용자 문구에서 세션 식별자를 뺀다 (FR-135)
- [X] T047 [P] [US2] `frontend/src/pages/SessionScreen.tsx` 가 `step_results` 로 Step별 결과를 복원하게 한다 — WebSocket 이벤트가 없어도 그때까지의 결과가 남는다. U-05 의 "실패가 사라지는" 현상이 여기서 함께 잡힌다 (FR-171·U-18)

**Checkpoint**: 결말이 정직하다. 화면과 저장된 결과가 어긋나지 않는다

---

## Phase 5: User Story 3 — 멈춤은 실제로 멈춘 뒤에 멈췄다고 말한다 (Priority: P2)

**Goal**: 일시정지 전이를 드러내고, 종료 후 버튼이 실행 중 버튼과 구분된다.

**Independent Test**: 20초 대기 Step 이 도는 중에 「일시정지」를 누르고, 누른 직후부터 실제로
멈출 때까지 화면이 무엇을 말하는지 관찰하면 검증된다.

### Tests for User Story 3

- [X] T048 [P] [US3] `backend/tests/integration/test_pause_transition.py` — 오래 걸리는 Step 중 pause 요청 시 세션 뷰의 `pause_settled` 가 `false` 이고, 경계 도달 후 `true` 가 되는지 단정한다 (FR-142)
- [X] T049 [P] [US3] 같은 파일에서 전이 중 실행이 끝나면 응답 `state` 가 `paused` 가 아니라 종료 상태인지 단정한다 — **결말이 일시정지를 이긴다** (FR-146, research R7)
- [X] T050 [P] [US3] `frontend/tests/PauseTransition.test.tsx` — pause 응답 지연 중 전이 배지·즉시 안내 문구가 보이고, Step 편집 팔레트가 열려 있지 않으며, 「중지」가 활성인지 단정한다 (FR-142·FR-143·FR-144). T003 헬퍼를 쓴다
- [X] T051 [P] [US3] `frontend/tests/TerminalControls.test.tsx` — 종료 상태에서 「중지」가 아니라 「닫기」이고 강조가 없으며, 결과 접근을 끊는 조작에 확인이 붙는지 단정한다 (FR-147·FR-148·SC-220)

### Implementation for User Story 3

- [X] T052 [US3] ~~전이표에 `PAUSED + FINISH_*` 를 허용한다~~ → **하지 않기로 결정했다.** 불변식 1 테스트(`test_session_held_states_do_not_auto_terminate`)가 거절했고 그 거절이 옳다 — `PAUSED` 에서 브라우저 세션은 종료되지 않는다(FR-032, 헌법 원칙 III). 실행 결말과 세션 상태는 다른 축이며, FR-146 은 화면에서 이행했다(T058). 결정 근거를 `state_machine.py` 의 `PAUSED` 항목에 남겼다
- [X] T053 [US3] `backend/src/itb/api/routes/sessions.py` 의 `pause` 가 `pause_settled` 를 뷰에 싣게 하고, 러너 종료가 일시정지를 이기는 순서를 명시한다 (FR-142·FR-146)
- [X] T054 [US3] `frontend/src/pages/SessionScreen.tsx` 에 전이 상태를 넣는다 — 요청 직후 낙관적으로 켜고 응답의 `pause_settled` 로 확정한다. 응답 실패 시에도 전이 표시를 걷는다 (FR-142, plan 위험표)
- [X] T055 [US3] 전이 중 표시를 ui-contract §7 대로 구성한다 — 배지 `일시정지 중…`, `현재 Step 이 끝나면 멈춥니다` **즉시** 표시, 남은 대기 시간 (FR-142·FR-145)
- [X] T056 [US3] 전이 중 Step 편집 팔레트를 열지 않고 `정지되면 편집할 수 있습니다` 를 대신 보여준다 (FR-143)
- [X] T057 [US3] 전이 중에도 「중지」를 활성으로 유지한다. 나머지 컨트롤만 비활성 (FR-144)
- [X] T058 [US3] 전이 중 실행이 끝난 경우의 표시를 만든다 — 배지를 결말로 바꾸고 `멈추기 전에 실행이 끝났습니다` 와 실패 사유·「결과 자세히 보기」를 붙이고 낡은 전이 안내를 지운다 (FR-146)
- [X] T059 [US3] `frontend/src/pages/SessionScreen.tsx` 의 종료 후 버튼을 「닫기」로 바꾼다 — 라벨·위치·강조를 실행 중 「중지」와 구분한다. 중지 요청 중에는 `중지 중…` 전이 상태를 준다 (FR-147, ui-contract §6)
- [X] T060 [US3] 세션 정리가 결과 접근을 끊을 수 있으면 확인을 붙인다 — ui-contract §6-3 문구 (FR-148)

**Checkpoint**: 화면이 아직 아닌 것을 됐다고 말하지 않는다

---

## Phase 6: User Story 4 — 부분 실행이 부분 실행으로 보인다 (Priority: P2)

**Goal**: 건너뛴 사실을 누르기 전에 알리고, 결과에서 건너뜀과 미실행을 구분하고, 이전 전체
실행 결과를 지우지 않는다.

**Independent Test**: 로그인이 선행 Step 인 테스트에서 중간 Step 부터 실행을 걸고 실행 전·중·후
화면이 건너뛴 사실을 어떻게 말하는지 확인하면 검증된다.

### Tests for User Story 4

- [X] T061 [P] [US4] `backend/tests/integration/test_partial_run_result.py` — 부분 실행 후 `scope == "partial"`·`start_index` 가 저장되고, `result-full.json` 의 이전 전체 실행이 **덮이지 않는지** 단정한다 (FR-152·U-02)
- [X] T062 [P] [US4] 같은 파일에서 요약 분모가 `attempted_count` 인지 단정한다 — 5개를 건너뛴 부분 실행이 `0 / 7` 이 아니라 `0 / 2` 다 (FR-152)
- [X] T063 [P] [US4] `backend/tests/unit/test_partial_diagnosis.py` — 부분 실행에서 요소를 찾지 못한 실패의 진단 첫 줄이 선행 Step 건너뜀을 먼저 지시하는지, 그 함수가 **순수 함수이며 언어모델을 부르지 않는지** 단정한다 (FR-153, 헌법 원칙 II)
- [X] T064 [P] [US4] `frontend/tests/SkippedVsNotRun.test.tsx` — `skipped` 와 `not_run` 이 서로 다른 표시이고 각각 텍스트 라벨을 갖는지 단정한다 (FR-151·U-21)
- [X] T065 [P] [US4] `frontend/tests/PartialRunLabels.test.tsx` — 재실행 버튼 라벨에 시작 Step 번호가 있고, 보조 문구에 건너뛰는 구간과 선행 상태 경고가 있는지 단정한다 (FR-149·FR-150)

### Implementation for User Story 4

- [X] T066 [US4] `backend/src/itb/execution/runner.py` 가 `.runs/<테스트ID>/result-full.json` 을 전체 실행에서만 갱신하게 한다. 부분 실행은 `result.json` 만 쓴다 (FR-152, data-model.md §5)
- [X] T067 [US4] `backend/src/itb/api/routes/tests.py` 의 결과 조회에 `last_full_run` 을 싣는다. 파일이 없으면 `null` (contracts/rest-api.md §7)
- [X] T068 [US4] 부분 실행 실패 진단 문구 생성을 규칙 기반 순수 함수로 만든다 — `backend/src/itb/domain/` 또는 결과 조립부. 첫 줄이 선행 Step 건너뜀 가능성을 지시한다 (FR-153)
- [X] T069 [P] [US4] `frontend/src/pages/RunResult.tsx` 의 재실행 버튼 라벨에 시작점을 박고(`Step 06부터 실행`) 보조 문구를 붙인다 (FR-149·FR-150, ui-contract §5)
- [X] T070 [P] [US4] 같은 파일의 Step 목록에서 `skipped`·`not_run` 을 ui-contract §3 대로 구분해 표시한다. 색만이 아니라 텍스트 라벨을 병기한다 (FR-151)
- [X] T071 [US4] 부분 실행 요약을 ui-contract §1 의 문장으로 만든다 — **결말이 앞에 온다**: `실패 · 부분 실행 Step 06~07 · 0 / 2 · (01~05 건너뜀)`. 분모는 `attempted_count`. spec.md US4-4 의 예시는 어순이 다르므로 **ui-contract 표를 권위로 삼는다** (FR-152·FR-141)
- [X] T072 [US4] 결과 화면에 「최근 전체 실행」 보조 표시를 붙인다. `last_full_run` 이 `null` 이면 생략한다 (FR-152)
- [X] T073 [P] [US4] 실행 중 화면의 Step 목록에서도 건너뛴 Step 을 구분해 표시한다 — `SessionScreen.tsx` (FR-151, U-02 관찰 1)

**Checkpoint**: 부분 실행이 전체 실행을 덮지 않고, 건너뜀이 드러난다

---

## Phase 7: User Story 5 — 저장이 저장으로 보인다 (Priority: P2)

**Goal**: 화면을 옮기지 않고 저장 성공을 안다. 정리 문구가 저장된 테스트를 위협하지 않는다.

**Independent Test**: 녹화 후 이름을 넣고 저장을 한 번 누른 뒤, 화면을 옮기지 않고 저장 성공을
알 수 있는지만 보면 검증된다.

### Tests for User Story 5

- [X] T074 [P] [US5] `frontend/tests/SaveFeedback.test.tsx` — 저장 성공 후 인라인 확인과 저장된 이름이 보이고, 제목에 「초안」이 없고, 버튼이 「변경 저장」이며 변경 없으면 비활성인지 단정한다. **저장 여부 확인에 추가 화면 이동이 필요하지 않은지**도 단정한다 (FR-154·FR-155·FR-156·SC-217)
- [X] T075 [P] [US5] 같은 파일에서 저장 실패 시 사실과 사유가 표시되고, 성공 시 이전 오류 배너가 걷히는지 단정한다 (FR-157·FR-158)
- [X] T076 [P] [US5] `backend/tests/contract/test_session_saved_at.py` — 저장 후 세션 뷰의 `saved_at` 이 채워지는지 단정한다 (FR-154)

### Implementation for User Story 5

- [X] T077 [US5] `backend/src/itb/api/routes/sessions.py` 의 저장 경로가 세션에 저장 시각을 남기고 `SessionView.saved_at` 에 싣게 한다 (FR-154, data-model.md §4)
- [X] T078 [US5] `frontend/src/pages/RunnerPaused.tsx` 의 저장 영역에 성공 확인을 붙인다 — ui-contract §9 의 구성(`저장했습니다 · TC-001` + 「목록에서 보기」) (FR-154)
- [X] T079 [US5] `frontend/src/pages/SessionScreen.tsx` 의 제목에서 저장 후 「초안」을 떼고 `TC-001 · 저장됨` 으로 바꾼다 (FR-155)
- [X] T080 [US5] 저장 버튼 라벨을 「변경 저장」으로 바꾸고 변경이 없으면 비활성으로 둔다 (FR-156)
- [X] T081 [US5] 저장 실패 표시를 확인하고, 성공 시 이전 오류 배너를 걷어낸다 (FR-157·FR-158)
- [X] T082 [P] [US5] `frontend/src/pages/TestList.tsx` 의 세션 정리 확인 문구를 저장 이력에 따라 갈라 쓴다 — 저장된 세션에는 ui-contract §9-6 문구 (FR-159, U-10)

**Checkpoint**: 작성 흐름의 끝이 확실하게 끝난다

---

## Phase 8: User Story 6 — 제품 안에서 대상 화면을 본다 (Priority: P2)

**Goal**: 미리보기가 정적 화면에서도 대상 화면을 보여준다. 원인은 실측으로 확정됐다.

**Independent Test**: 세션을 만들고 대상 화면을 건드리지 않은 채 미리보기 영역만 보면
검증된다. 현재는 프레임이 0건이다.

### Tests for User Story 6

- [X] T083 [P] [US6] `backend/tests/integration/test_mirror_late_subscribe.py` — 정적 페이지 세션에서 **구독을 늦게 붙여도 3초 안에** `mirror_frame` 이 도달하는지 단정한다 (FR-161·FR-162·SC-218). T002 하니스를 쓴다. 현재는 0건이다
- [X] T084 [P] [US6] 같은 파일에서 화면이 5초 이상 변하지 않아도 프레임이 계속 오는지(무프레임 감시) 단정한다 (FR-160)
- [X] T085 [P] [US6] `backend/tests/unit/test_mirror_no_input.py` — 미러 모듈이 CDP `Input.*` 을 보내지 않고 허용 명령 화이트리스트가 3개로 유지되는지 단정한다 (FR-165, 헌법 FR-047a)
- [X] T086 [P] [US6] `backend/tests/unit/test_mirror_failure_isolation.py` — 감시 태스크의 예외가 실행에 전파되지 않는지 단정한다 (FR-164, FR-047b)

### Implementation for User Story 6

- [X] T087 [US6] `backend/src/itb/mirror/screencast.py` 의 `TabScreencast` 가 **마지막 프레임을 캐시**하게 한다. 캐시는 미러 모듈 안에 둔다 (FR-162, research R6-A)
- [X] T088 [US6] `backend/src/itb/api/ws/session_events.py` 의 `SessionEventHub.connect()` 가 새 구독자에게 **마지막 프레임 한 장**을 보내게 한다. 보낼 것이 없으면 아무것도 보내지 않는다 (FR-162, contracts/websocket.md §1-a)
- [X] T089 [US6] `backend/src/itb/mirror/screencast.py` 에 **무프레임 감시**를 넣는다 — 마지막 프레임 후 `MIRROR_IDLE_S`(2초) 조용하면 스크린샷 한 장을 같은 이벤트로 보낸다. 기존 `_screenshot_loop` 코드를 재사용하고 주기만 바꾼다 (FR-160, research R6-B)
- [X] T090 [US6] 무프레임 감시가 `mirror_degraded` 를 발행하지 않게 한다 — 강등이 아니라 정상 동작의 보완이다 (contracts/websocket.md §1-b)
- [X] T091 [US6] 미러 허브를 세션에 잇는 지점을 확인해 캐시가 탭 전환 시에도 올바른 탭의 프레임을 주게 한다 — `backend/src/itb/mirror/tab_switch.py` (FR-162)
- [X] T092 [P] [US6] `frontend/src/components/MirrorView.tsx` 의 빈 상태 문구를 ui-contract §10 으로 바꾼다 — 곧 올 것처럼 말하지 않고 표시 조건을 사실대로 말한다 (FR-163)

**Checkpoint**: 제품 안에서 대상 화면이 보인다

---

## Phase 9: User Story 7 — 새로 고쳐도, 다시 열어도 잃지 않는다 (Priority: P3)

**Goal**: 새로고침·뒤로가기가 앱을 날리지 않고, 실행 중임이 목록에 보이며, 배너가 스스로
갱신된다.

**Independent Test**: 실행 중과 결과 화면에서 각각 새로고침·뒤로가기를 눌러 보고, 목록 배너를
25초 방치한 뒤 갱신 여부를 확인하면 검증된다.

### Tests for User Story 7

- [X] T093 [P] [US7] `frontend/tests/useScreenUrl.test.ts` — 화면 상태 ↔ URL 양방향 변환과 `popstate` 처리가 앱 내부 이동인지 단정한다 (FR-166·FR-167·SC-219)
- [X] T094 [P] [US7] `frontend/tests/RunningRowState.test.tsx` — 실행 중인 테스트의 행이 `RUNNING` 칩과 복귀 수단을 갖는지, 같은 테스트의 배너가 여럿일 때 구분 정보가 있는지 단정한다 (FR-168·FR-170)

### Implementation for User Story 7

- [X] T095 [US7] `frontend/src/hooks/useScreenUrl.ts` 를 만든다 — `history.pushState`/`popstate` 로 `Screen` 상태를 잇는 얇은 훅. **라우팅 라이브러리를 추가하지 않는다** (research R8). 먼저 뒤로가기 이탈 방지만 넣어 값을 일찍 낸다 (FR-167)
- [X] T096 [US7] `frontend/src/App.tsx` 에 훅을 붙여 결과·실행·정의 화면을 URL 로 복원한다 — ui-contract §14 의 URL 표 (FR-166)
- [X] T097 [P] [US7] `frontend/src/pages/TestList.tsx` 에 실행 중 행 표시를 넣는다 — `RUNNING` 칩 + 「실행 화면 보기」 (FR-168)
- [X] T098 [P] [US7] 목록의 세션 배너가 실제 상태를 따라 갱신되게 한다 — 세션 이벤트를 붙이거나 짧은 주기로 다시 읽는다 (FR-169, U-17)
- [X] T099 [P] [US7] 같은 테스트의 배너가 여럿일 때 시작 시각으로 구분한다 (FR-170, U-06)

**Checkpoint**: 브라우저 기본 조작이 앱을 날리지 않는다

---

## Phase 10: User Story 8 — 비활성·무관한 컨트롤이 자기 상태를 설명한다 (Priority: P3)

**Goal**: 누를 수 없는 것은 이유를, 빈 것은 없다는 사실을, 무관한 것은 용도를 말한다.

**Independent Test**: 결과 화면의 증거 탭 4개를 모두 눌러 보고 녹화 중 헤더의 속도 컨트롤을
확인하면 검증된다.

### Tests for User Story 8

- [X] T100 [P] [US8] `frontend/tests/EvidenceTabs.test.tsx` — 비활성 탭에 이유가 붙고, 기록 없는 탭이 없다는 사실을 긍정문으로 말하는지 단정한다 (FR-172·FR-173)
- [X] T101 [P] [US8] `frontend/tests/PacingLabel.test.tsx` — 녹화·인수 국면에서 속도 라벨이 「다음 실행 속도」인지 단정한다 (FR-174)

### Implementation for User Story 8

- [X] T102 [P] [US8] `frontend/src/pages/RunResult.tsx` 의 증거 탭 문구를 ui-contract §11 로 바꾼다 (FR-172·FR-173)
- [X] T103 [P] [US8] `frontend/src/components/PacingControl.tsx` 이 국면에 따라 라벨을 바꾸게 한다 — 녹화·인수에서 「다음 실행 속도」. 감추지 않는 이유는 004 FR-109 다 (FR-174, research R10)

**Checkpoint**: 모든 스토리가 독립적으로 동작한다

---

## Phase 11: Polish & Cross-Cutting

**Purpose**: 여러 스토리에 걸친 마무리와 회귀 확인

- [X] T104 결말 값 추가로 단정이 바뀌는 기존 테스트를 갱신한다. **약화하지 않는다** — 중지가 `fail` 이던 단정은 `stopped` 로 고치되 삭제·skip 하지 않는다 (헌법 Quality Gate 4)
- [X] T105 [P] 프론트에서 결말을 읽는 모든 분기가 4값을 다루는지 확인한다 — `outcome === "fail"` 로만 갈리는 곳을 `switch` 로 바꿔 타입 검사가 누락을 잡게 한다 (plan 위험표)
- [X] T106 [P] 알 수 없는 결말 값을 만난 프론트가 `fail` 로 취급하는지 확인하는 테스트를 `frontend/tests/UnknownOutcome.test.ts` 에 추가한다 (data-model.md §1 보수적 기본값)
- [X] T107 [P] `docs/DEVELOPMENT.md` 에 결말 4값과 스키마 재생성 순서를 적는다. 미러 무프레임 감시가 정상 동작임을 한 줄 남긴다
- [X] T108 `backend` 전체 테스트와 스키마 드리프트를 돌린다 — `uv run pytest` · `uv run python -m itb.schema.export && git diff --exit-code schema/`
- [X] T109 `frontend` 전체 테스트를 돌린다 — `npm run gen:types && npm test`
- [ ] T110 [quickstart.md](./quickstart.md) §2 의 S1~S8 을 사람이 직접 걸어 **상 9건 재발 여부**를 확인한다. 하나라도 재발하면 U 번호를 들어 남은 작업으로 등록한다 (SC-221)
- [X] T111 quickstart.md §3 의 기존 성질 8개가 유지되는지 확인한다 — 특히 재실행 경로에 언어모델 없음(원칙 II), 일시정지가 브라우저 상태 유지(원칙 III), 미러가 입력 전달 없음(FR-047a)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음. 즉시 시작
- **Phase 2 (Foundational)**: Phase 1 후. **모든 스토리를 차단한다**
  - T004 → T005 → T006 은 **직렬**이고 한 흐름으로 끝낸다 (스키마 드리프트)
  - T007·T008·T010·T011·T012 는 T006 후 병렬
  - T009 는 T005 후 (새 필드가 모델을 참조한다)
- **Phase 3~10 (스토리)**: Phase 2 완료 후. 스토리끼리는 대체로 독립
- **Phase 11 (Polish)**: 원하는 스토리들이 끝난 후

### User Story Dependencies

| 스토리 | 선행 | 이유 |
|---|---|---|
| US1 (P1) | Phase 2 | 없음 — 곧바로 MVP |
| US2 (P1) | Phase 2 | 결말 4값(T004~T006)이 전제 |
| US3 (P2) | Phase 2 | `pause_settled`(T009)가 전제. T052 전이표는 US3 안에서 직렬 |
| US4 (P2) | Phase 2 | `RunScope`·`attempted_count`(T005)가 전제. US2 의 T037 과 같은 파일을 만지므로 **순차 권장** |
| US5 (P2) | Phase 2 | `saved_at`(T009)가 전제 |
| US6 (P2) | Phase 1 | **완전 독립** — 미러 모듈만 만진다. 계약 변경과 무관하므로 Phase 2 를 기다릴 필요가 없다 |
| US7 (P3) | Phase 2 | US1 의 `startRun`(T021)과 같은 파일(`App.tsx`)을 만진다 — 순차 |
| US8 (P3) | Phase 2 | 없음 |

**주의**: US2 의 T037 과 US4 의 T066·T067 은 `runner.py` 를 함께 만진다. 병렬로 두지 않는다.

### Within Each User Story

- 테스트를 먼저 쓰고 **실패를 확인한 뒤** 구현한다
- 백엔드 판정 → 계약 → 화면 순서
- 스토리를 끝내고 다음 우선순위로 간다

### Parallel Opportunities

- Phase 1 의 T001~T003 전부 병렬
- Phase 2 의 T007·T008·T010·T011·T012 병렬 (T006 후)
- 각 스토리의 테스트 작업 전부 병렬
- **US6(미리보기)은 Phase 1 직후부터 다른 모든 것과 병렬** — 만지는 파일이 겹치지 않는다
- US5·US8 은 서로, 그리고 US1~US4 와 병렬 가능

---

## Parallel Example: Phase 2 이후 첫 묶음

```bash
# 계약이 준비된 직후 병렬로 띄울 수 있는 것들
Task: "T013 종료 세션 후 재실행 통합 테스트 (backend/tests/integration/test_rerun_after_finish.py)"
Task: "T014 동시 생성 5건 통합 테스트 (backend/tests/integration/test_concurrent_session_create.py)"
Task: "T016 실행 트리거 프론트 테스트 (frontend/tests/RunTrigger.test.tsx)"
Task: "T083 미러 늦은 구독 통합 테스트 (backend/tests/integration/test_mirror_late_subscribe.py)"
Task: "T085 미러 입력 금지 단위 테스트 (backend/tests/unit/test_mirror_no_input.py)"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (재료) → Phase 2 (계약·어휘) → Phase 3 (US1)
2. **멈추고 검증**: quickstart §2 의 S1 을 걷는다
3. 이 시점에 리포트가 "가장 아픈 것"으로 지목한 왕복이 성립한다

### Incremental Delivery

1. Phase 1 + 2 → 토대
2. US1 → 검증 → **MVP**
3. US2 → 검증 (결말이 정직해진다)
4. US6 → 검증 (미리보기가 보인다 — 독립적이라 언제든 끼울 수 있다)
5. US3 → US4 → US5 → US7 → US8
6. Phase 11 → 회귀 확인

각 스토리가 앞선 스토리를 깨지 않고 값을 더한다.

### 값이 가장 빨리 나오는 조합

시간이 제한되면 **US1 + US2 + US6** 을 먼저 한다. 리포트 영향도 **상 9건 중 7건**이
여기에 있고(U-01·U-03·U-05·U-06·U-07·U-08 일부·U-24), US6 은 다른 무엇도 기다리지 않는다.

---

## Notes

- `[P]` = 다른 파일, 의존 없음
- `[Story]` 라벨로 요구사항까지 추적된다 — 각 작업 설명에 FR 번호와 U 번호를 달아 두었다
- 구현 전 테스트가 **실패하는 것을 확인**한다. 통과하면 그 테스트는 결함을 재현하지 못한 것이다
- 작업 또는 논리적 묶음마다 커밋한다
- 검증이 실패한 채 커밋하면 제목에 `wip:` 를 붙이고 본문에 실패 출력을 적는다 (거짓 보고 금지)
- 어느 체크포인트에서든 멈춰 스토리를 독립적으로 검증할 수 있다
