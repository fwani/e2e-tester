---

description: "Task list for 004-run-pacing-readiness"
---

# Tasks: 실행 속도 조절과 로딩 대기

**Input**: Design documents from `/specs/004-run-pacing-readiness/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: 포함한다. 헌법 품질 게이트 3이 요구한다 — "제품은 테스트 도구다. 자기 테스트 없이
내보내는 것은 허용되지 않는다." Recorder·Runner 상태 기계·Generator 각각 단위 테스트와
사용자 흐름당 e2e 1건 이상이 의무다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리인가 (US1·US2·US3)
- 파일 경로를 정확히 적는다

## Path Conventions

Web app 구조. 백엔드 `backend/src/itb/`, 백엔드 테스트 `backend/tests/`,
프런트엔드 `frontend/src/`.

---

## 스토리 순서에 대한 결정

**US2(대기)를 US1(속도)보다 먼저 구현한다.** 둘 다 P1 이지만 순서에 이유가 있다.

속도 조절이 먼저 들어가면 대기 결함이 "느려서 그런 것" 으로 보여 검증이 흐려진다. 대기를
먼저 고쳐 SC-001·SC-002 를 **속도 변경 없이 독립적으로** 확인한다 (plan 구현 순서 2·3).

각 스토리는 여전히 독립적으로 테스트 가능하다 — US1 은 US2 없이도, US2 는 US1 없이도
값을 준다.

---

## Phase 1: Setup

**Purpose**: 결함을 재현하는 픽스처를 먼저 만든다. 고치기 전에 실패를 봐야 무엇을 고쳤는지
알 수 있다 (quickstart §1).

- [X] T001 [P] 지연 로딩 화면을 `fixtures/sample-app/lazy.html` 에 추가한다 — 2초 뒤 목록을 그리고, 그 전에는 같은 텍스트의 스켈레톤 행 2개를 보여준다 (research R1·R2 의 재현 조건)
- [X] T002 [P] 늦게 보이게 되는 요소 화면을 `fixtures/sample-app/late-visible.html` 에 추가한다 — DOM 에는 즉시 붙지만 1초 뒤 `display:block` 이 되는 버튼 (research R3)
- [X] T003 `fixtures/sample-app/README.md` 에 두 화면의 용도와 지연 시간을 적는다 — 픽스처가 왜 이 값인지 모르면 나중에 누군가 "느리다" 며 줄인다

**Checkpoint**: 결함 재현 조건이 파일로 고정됐다.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 두 스토리가 모두 의존하는 도메인 정의. 이 단계가 끝나기 전에는 어떤 스토리도
시작할 수 없다.

**⚠️ CRITICAL**: 아래 모든 작업이 끝나야 US1·US2 작업을 시작한다.

- [X] T004 [P] `RunPacing` 열거형과 간격 대응표를 `backend/src/itb/domain/run_pacing.py` 에 만든다 — `FAST/NORMAL/SLOW/STEP`, `delay_ms`·`auto_pause`·표시 이름을 이 한 곳에서만 낸다 (data-model §1)
- [X] T005 [P] `ELEMENT_NOT_READY`·`ELEMENT_AMBIGUOUS` 를 `backend/src/itb/domain/error.py` 의 `ErrorCode` 와 `CATEGORY` 대응표에 더한다 — 둘 다 `blocked` (contracts/error-contract.md §1)
- [X] T006 [P] `DEFAULT_TIMEOUT_MS` 를 `backend/src/itb/domain/step.py` 에서 5000 → 10000 으로 바꾸고, 독스트링의 근거를 research R5 참조로 갱신한다. **파일을 옮기지 않는다** — `domain-is-pure` 계약이 `itb.domain` → `itb.locator` 임포트를 금지한다 (data-model §8)
- [X] T007 [P] `POLL_INTERVAL_MS = 100` 과 대기 정책 문서를 `backend/src/itb/locator/strategy.py` 에 더한다 — Runner 와 Generator 의 공유 지점이므로 여기 둔다. 순수성을 깨는 임포트를 더하지 않는다 (data-model §8)
- [X] T008 [P] `StepResult` 에 `element_wait_ms: int = 0` 을 `backend/src/itb/domain/run_result.py` 에 더한다 — 기존 필드 이름·의미를 바꾸지 않는다 (data-model §3)
- [X] T009 [P] `RunPacing` 대응표 단위 테스트를 `backend/tests/unit/test_run_pacing.py` 에 쓴다 — 네 값의 `delay_ms`·`auto_pause`, `SLOW >= 1000ms`(SC-004), 열거형 밖 값 거절
- [X] T010 [P] 신규 오류 코드의 분류·다음 행동 테스트를 `backend/tests/unit/test_error_handling.py` 에 더한다 — `category == "blocked"`, `next_action` 이 비어 있지 않음
- [X] T011 `uv run lint-imports` 가 세 계약 모두 통과하는지 확인한다 — `domain-is-pure` 가 `run_pacing.py` 에서, `locator-strategy-is-pure` 가 `strategy.py` 변경에서 깨지지 않아야 한다 (T004·T007 이후)

**Checkpoint**: 도메인 정의 완료. US1·US2 를 병렬로 시작할 수 있다.

---

## Phase 3: User Story 2 - 로딩 중인 데이터를 기다린다 (Priority: P1) 🎯 MVP

**Goal**: 요소 탐색이 예산 안에서 **모든 후보를 계속 다시 확인**하고, 조작 가능해진 요소에
동작을 수행한다. 잘못된 요소를 조용히 채택하지 않는다.

**Independent Test**: 지연 로딩 픽스처를 대상으로 Step 을 실행하면 통과한다. 속도 조절
없이 확인된다. 현재는 실패한다 (research R1: 5004ms 실패).

### Tests for User Story 2 ⚠️

> **먼저 쓰고, 구현 전에 실패하는 것을 확인한다.**

- [X] T012 [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_element_appears_after_delay` — 2초 뒤 등장 요소로 Step 통과 (SC-001)
- [X] T013 [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_lower_candidate_appears_late` — 최상위 후보(testId)가 끝내 안 맞고 하위 후보(role)만 2초 뒤 맞는 경우 통과 (SC-002). **이 테스트가 구현 전 실패해야 한다**
- [X] T014 [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_attached_but_invisible_waits` — DOM 에 붙었지만 1초 뒤 보이는 요소를 기다린 뒤 조작 (FR-112)
- [X] T015 [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_ambiguous_does_not_silently_pick_first` — 후보가 2개를 매칭할 때 `.first` 로 통과하지 않고 `ELEMENT_AMBIGUOUS` 로 실패 (research R2)
- [X] T016 [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_budget_exhausted_reports_not_ready` — 예산 초과 시 `ELEMENT_NOT_READY` 와 실제 대기 시간
- [X] T017 [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_hidden_assertion_still_passes_when_absent` — 처음부터 없는 요소에 대한 `hidden` 검증이 대기 정책 변경 후에도 통과 (FR-119)
- [X] T018 [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_immediate_element_does_not_poll` — 요소가 즉시 존재하면 폴링 루프에 들어가지 않는다 (FR-113)
- [X] T019 [P] [US2] `backend/tests/integration/test_performance.py` 에 정상 경로 비용 테스트를 더한다 — 즉시 존재하는 요소의 Step 소요가 100ms 미만 증가 (SC-003)
- [X] T019a [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_step_never_exceeds_budget` — 요소가 끝내 나타나지 않는 화면에서 Step 소요가 `timeout_ms` 를 넘지 않는다. 탭 대기·요소 탐색·동작이 하나의 예산을 나눠 쓴다 (FR-117)
- [X] T019b [P] [US2] `backend/tests/integration/test_lazy_loading.py` 에 `test_candidate_disagreement_still_recorded` — 두 후보가 서로 다른 요소를 매칭할 때 불일치가 실행 기록에 남는다. `resolve()` 재작성이 이 기능을 떨어뜨리지 않았음을 고정한다 (spec 엣지 케이스, T020a 와 짝)

### Implementation for User Story 2

- [X] T020 [US2] `backend/src/itb/execution/locator_runtime.py` 의 `resolve()` 를 폴링 알고리즘으로 바꾼다 — 1라운드에서 즉시 채택되면 반환하고, 아니면 `POLL_INTERVAL_MS` 주기로 **모든 후보를 다시 확인**한다 (FR-111, research R1)
- [X] T020a [US2] `backend/src/itb/execution/locator_runtime.py` 의 재작성에서 `_detect_disagreement()` 호출을 **보존한다** — 후보들이 서로 다른 요소를 가리킨 기록이 사라지면 나중에 테스트가 엉뚱한 요소에 대해 통과했을 때 단서가 없다 (spec 엣지 케이스 "여러 후보가 서로 다른 시점에")
- [X] T021 [US2] `backend/src/itb/execution/locator_runtime.py` 의 `resolve()` 에서 `locator.first.wait_for(state="attached")` 폴백을 제거한다 — 후보가 여러 개를 매칭할 때 조용히 첫 번째를 잡던 경로다 (research R2)
- [X] T022 [US2] `backend/src/itb/execution/locator_runtime.py` 의 `resolve()` 에 보임 선호 채택 규칙을 넣는다 — `count()==1` 이고 보이는 후보를 우선순위 순으로 즉시 채택하고, 보이지 않는 것만 있으면 계속 폴링하되, **남은 예산이 `MIN_ACTION_TIMEOUT_MS`(250ms) 이하가 되는 라운드에서** `count()==1` 인 최상위 후보를 채택한다 (research R3, FR-119 를 위해 실패시키지 않는다)
- [X] T023 [US2] `ElementNotFoundError` 가 `timed_out`·`waited_ms`·`ambiguous` 를 들도록 확장한다 — 호출부가 문구를 파싱하지 않고 분류할 수 있어야 한다 (`backend/src/itb/execution/locator_runtime.py`)
- [X] T024 [US2] `backend/src/itb/execution/locator_runtime.py` 에서 폴링 라운드마다 `LocatorAttempt` 를 갱신한다 — `waited_ms` 는 모든 후보가 총 대기 시간을 갖고, `match_count` 는 마지막 라운드 값이다 (data-model §4)
- [X] T025 [US2] `backend/src/itb/execution/step_executor.py` 에서 `ElementNotFoundError` 를 신규 오류 코드로 매핑한다 — `timed_out` → `ELEMENT_NOT_READY`, `ambiguous` → `ELEMENT_AMBIGUOUS`, 후보 없음 → 기존 `STEP_FAILED` (T023 이후, contracts/error-contract.md §2)
- [X] T026 [US2] `StepExecution` 에 `element_wait_ms` 를 더하고 `_locate`·`_locate_target`·`_drag` 가 채우게 한다 (`backend/src/itb/execution/step_executor.py`)
- [X] T027 [US2] `backend/src/itb/execution/runner.py` 의 `ReplayEngine.run_step` 이 성공·실패 양쪽에서 `element_wait_ms` 를 `StepResult` 와 `step_finished`·`step_failed` 이벤트에 싣는다 (contracts/websocket.md §2·§3)
- [X] T028 [US2] `_humanize` 와 신규 코드의 메시지가 **실제 기다린 시간과 후보별 시도 내역**을 담게 한다 (`backend/src/itb/execution/step_executor.py`, FR-121)
- [X] T029 [US2] `backend/src/itb/schema/export.py` 를 돌려 `backend/schema/*.json` 을 갱신하고, `cd frontend && npm run gen:types` 로 TypeScript 타입을 재생성한다. 생성 파일을 손으로 고치지 않는다 (헌법 Cross-language schema duty)

**Checkpoint**: US2 완료. 지연 로딩 화면에서 Step 이 통과하고, 실패 시 분류가 갈린다.
`uv run python -m pytest tests/integration/test_lazy_loading.py -v` 가 전부 통과한다.

---

## Phase 4: User Story 1 - 실행을 눈으로 따라갈 수 있다 (Priority: P1)

**Goal**: Step 사이에 사용자가 고른 간격이 생기고, 속도를 실행 중에 바꿀 수 있으며,
`한 스텝씩` 으로 하나씩 확인할 수 있다. 속도는 판정을 바꾸지 않는다.

**Independent Test**: Step 3개 이상인 테스트를 `느림` 으로 실행하면 총 시간이 간격만큼
늘고, 판정은 `빠름` 과 동일하다. US2 없이도 확인된다.

### Tests for User Story 1 ⚠️

- [X] T030 [P] [US1] `backend/tests/unit/test_preferences.py` — 파일 없음·손상·알 수 없는 값에서 기본값 `normal` 로 진행하고 경고 사유를 낸다. 읽기 실패가 예외를 던지지 않는다 (data-model §5)
- [X] T031 [P] [US1] `backend/tests/unit/test_preferences.py` 에 원자적 쓰기 테스트 — 부분 기록된 파일을 남기지 않는다
- [X] T032 [P] [US1] `backend/tests/integration/test_pacing_interrupt.py` — `slow`(1500ms) 간격 도중 일시정지 요청 후 1초 안에 `state == "paused"` (SC-007, FR-106)
- [X] T033 [P] [US1] `backend/tests/integration/test_pacing_interrupt.py` 에 간격 도중 중지 테스트 — 1초 안에 중지된다
- [X] T034 [P] [US1] `backend/tests/integration/test_pacing_interrupt.py` 에 `test_pacing_change_does_not_interrupt_running_step` — 실행 중 속도 변경이 진행 중 Step 을 끊지 않고 다음 경계부터 적용된다 (FR-103)
- [X] T035 [P] [US1] `backend/tests/integration/test_pacing_interrupt.py` 에 `test_no_delay_after_last_step` — 마지막 Step 뒤에는 간격이 없다 (spec 엣지 케이스)
- [X] T035a [P] [US1] `backend/tests/integration/test_pacing_interrupt.py` 에 `test_delay_excluded_from_step_budget` — `느림` 실행에서 각 Step 의 `duration_ms` 에 1500ms 간격이 포함되지 않고, 간격이 시간 초과 판정에 영향을 주지 않는다 (FR-105)
- [X] T036 [P] [US1] `backend/tests/integration/test_pause_resume.py` 에 `한 스텝씩` 테스트를 더한다 — 매 Step 경계에서 `PAUSED` 가 되고, 그 상태에서 Step 편집이 허용된다 (FR-108)
- [X] T037 [P] [US1] `backend/tests/contract/test_ws_events.py` 에 `pacing_changed` 이벤트 계약 테스트를 더한다 — `pacing`·`delay_ms`·`auto_pause`·`preference_saved` (contracts/websocket.md §1)
- [X] T038 [P] [US1] `backend/tests/e2e/test_us2_replay_and_diagnose.py` 에 속도 4단계 판정 동일 테스트를 더한다 — 통과/실패와 실패 Step 위치가 모두 같다 (SC-005, FR-104)
- [X] T038a [P] [US1] `backend/tests/contract/test_preferences_api.py` 를 만든다 — `GET`·`PUT /api/preferences` 응답 형태, 열거형 밖 값 422, 읽기 실패 시 `warning` 필드 (contracts/rest-api.md §3)
- [X] T038b [P] [US1] `backend/tests/contract/test_preferences_api.py` 에 `LOST` 세션의 pacing 변경이 409 로 거절되는지 더한다 (contracts/rest-api.md §2)
- [X] T038c [P] [US1] `backend/tests/contract/test_dsl_roundtrip.py` 에 **저장된 테스트 YAML 에 속도 관련 키가 없음**을 단언한다 — 속도가 테스트 자산으로 새어 들어가는 것을 구조가 아니라 테스트로도 막는다 (FR-110, 헌법 원칙 V)

### Implementation for User Story 1

- [X] T039 [P] [US1] `backend/src/itb/storage/preferences.py` 를 만든다 — `~/.config/itb/preferences.json` 읽기·쓰기. 읽기 실패는 기본값 + 경고, 쓰기는 `storage/atomic.py` 재사용. **취향만 담는다** (data-model §5)
- [X] T040 [US1] `backend/src/itb/execution/session.py` 의 `BrowserSession` 에 `pacing: RunPacing` 과 `_pause_requested: asyncio.Event` 를 더한다 (data-model §2)
- [X] T041 [US1] `backend/src/itb/execution/session.py` 의 `apply()` 에서 `_pause_requested` 를 관리한다 — `PAUSE` 에 set, `RESUME`·`RUN_FROM` 에 clear. `mark_running()` 에서도 clear. **두 이벤트를 한 곳에서만 조작한다** (T040 이후)
- [X] T042 [US1] `backend/src/itb/execution/session.py` 에 `wait_pause_requested()` 를 더한다 — 간격이 이것을 `asyncio.wait_for` 로 기다린다 (research R6)
- [X] T043 [US1] `backend/src/itb/execution/runner.py` 의 `RunnerTask._advance()` 에 Step 간 간격을 넣는다 — `asyncio.wait_for(session.wait_pause_requested(), timeout=delay_s)` 로 자며, 일시정지 요청 시 즉시 반환한다. **다음 Step 이 있을 때만** 적용한다 (T042 이후, FR-101·FR-105·FR-106)
- [X] T044 [US1] `backend/src/itb/execution/runner.py` 의 `RunnerTask._advance()` 에 `한 스텝씩` 자동 일시정지를 넣는다 — `pacing.auto_pause` 이고 다음 Step 이 있으면 `session.apply(Command.PAUSE)`. 새 상태를 만들지 않는다 (research R7)
- [X] T045 [US1] `backend/src/itb/execution/runner.py` 에서 간격·자동 일시정지를 **저장된 Step 실행 구간에만** 적용한다 — `AI_RUNNING` 에서 AI 가 다음 동작을 판단하는 시간에는 적용하지 않는다 (spec 엣지 케이스)
- [X] T046 [P] [US1] `backend/src/itb/api/routes/preferences_routes.py` 를 만든다 — `GET`·`PUT /api/preferences` (contracts/rest-api.md §3). `T039` 이후
- [X] T047 [US1] `backend/src/itb/api/app.py` 에 `preferences_routes` 를 등록한다 (T046 이후)
- [X] T048 [US1] `backend/src/itb/api/routes/sessions.py` 의 `CreateSessionRequest` 에 `pacing` 을 더하고, 기본값 해석 순서를 구현한다 — 요청 → 취향 파일 → `normal` (contracts/rest-api.md §1)
- [X] T049 [US1] 같은 파일에 `POST /api/sessions/{id}/pacing` 을 더한다 — 속도를 바꾸고 취향 파일에 남기며 `pacing_changed` 를 발행한다. 취향 쓰기 실패는 `preference_saved: false` 로 알리되 **이 호출은 성공한다** (contracts/rest-api.md §2)
- [X] T050 [US1] 같은 파일의 `SessionView` 에 `pacing` 을 더한다 — 재연결 시 화면이 속도를 복원한다 (contracts/rest-api.md §4)
- [X] T051 [US1] `backend/src/itb/schema/export.py` 재실행 + `npm run gen:types` 로 `pacing` 관련 타입을 생성한다
- [X] T052 [P] [US1] `frontend/src/components/PacingControl.tsx` 를 만든다 — 네 단계 선택. 실행 중에도 활성이며 선택 시 `POST /api/sessions/{id}/pacing` 을 부른다
- [X] T053 [US1] `frontend/src/api/client.ts` 에 `setPacing`·`getPreferences`·`putPreferences` 를 더한다
- [X] T054 [US1] `frontend/src/pages/Runner.tsx` 에 `PacingControl` 을 붙이고, 현재 실행 중인 Step 을 강조한다. 간격 동안에는 방금 끝난 Step 과 결과가 보인다 (FR-107). `pacing_changed` 이벤트를 구독해 다른 창의 변경을 반영한다
- [X] T055 [US1] `frontend/src/pages/RunnerPaused.tsx` 가 `pacing === "step"` 일 때 문구를 가른다 — "한 스텝씩 — 다음 Step 을 기다립니다" vs "일시정지됨" (research R7)

- [X] T055a [P] [US1] `backend/tests/integration/test_ai_authoring.py` 에 AI 가 다음 동작을 판단하는 시간에는 간격이 적용되지 않음을 단언한다 (spec 엣지 케이스, T045 와 짝)

**Checkpoint**: US1 완료. 네 속도가 동작하고 판정을 바꾸지 않으며, 간격 중 일시정지·중지가
즉시 먹는다.

---

## Phase 5: User Story 3 - 실패했을 때 "아직 로딩 중이었다" 를 알 수 있다 (Priority: P2)

**Goal**: 시간 초과 실패가 정의 문제와 구별되어 보이고, 다음 행동이 제시된다.

**Independent Test**: 예산보다 오래 걸리는 화면에서 Step 을 실패시키고, 결과 화면에서
대기 시간·후보별 시도 내역·다음 행동을 읽을 수 있다.

**의존**: US2 의 T023·T025 가 분류를 만든다. 이 단계는 그것을 **화면에 드러낸다.**

### Tests for User Story 3 ⚠️

- [X] T056 [P] [US3] `backend/tests/integration/test_lazy_loading.py` 에 `test_timeout_failure_carries_next_action` — `ELEMENT_NOT_READY` 실패의 `next_action` 이 예산 상향과 속도 하향을 안내한다 (FR-122)
- [X] T057 [P] [US3] `backend/tests/integration/test_lazy_loading.py` 에 `test_no_usable_candidate_is_step_failed` — 후보가 하나도 없는 실패는 `STEP_FAILED` 로 남아 시간 문제와 구별된다 (FR-120)

### Implementation for User Story 3

- [X] T058 [US3] `backend/src/itb/execution/step_executor.py` 의 신규 코드 `next_action` 문구를 확정한다 — `ELEMENT_NOT_READY` 는 "실행 속도를 '느림'으로 낮춰 화면을 확인하거나 Step 상세에서 대기 시간을 늘리세요", `ELEMENT_AMBIGUOUS` 는 "Step 상세에서 요소를 다시 집으세요" (contracts/error-contract.md §3)
- [X] T059 [US3] `frontend/src/pages/RunResult.tsx` 가 `element_wait_ms` 를 표시한다 — `tab_wait_ms` 와 나란히, 성공한 Step 에도 보인다 (FR-114)
- [X] T060 [US3] `frontend/src/pages/RunResult.tsx` 가 신규 오류 코드를 **`code` 로 분기해** 표시한다. `message` 를 파싱하지 않는다 (FR-123)
- [X] T061 [US3] `frontend/src/pages/RunResult.tsx` 에서 `ELEMENT_NOT_READY` 실패에 Step 상세로 가는 경로를 준다 — 사용자가 예산을 늘리고 그 Step 부터 다시 실행할 수 있어야 한다 (US3 시나리오 3)
- [X] T062 [P] [US3] `frontend/src/components/ErrorNotice.tsx` 가 신규 코드를 알려진 코드로 처리하는지 확인한다 — 모르는 코드로 떨어져 기본 문구가 나오면 안 된다

**Checkpoint**: 세 스토리 모두 독립적으로 동작한다.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T063 [P] `docs/design/` 문서의 RunResult 표기에서 `timeout 5000 ms` 를 갱신한다 — 기본값이 10000ms 로 바뀌었다 (research R5 부수 영향)
- [X] T064 [P] `docs/DEVELOPMENT.md` 에 지연 로딩 픽스처 사용법과 속도 설정 파일 위치를 적는다
- [X] T065 [P] `backend/tests/integration/test_roundtrip.py` 에서 예산 기본값 상향이 생성 Playwright 코드의 `timeout:` 에 반영되는지 확인한다 (품질 게이트 2, SC-008)
- [X] T066 `uv run ruff check src/ tests/` 와 `uv run lint-imports` 를 통과시킨다
- [ ] T067 `uv run python -m pytest` 전체를 돌린다 — 기존 921건이 줄지 않는다. **테스트를 지우거나 건너뛰어 통과시키지 않는다** (품질 게이트 4). `.first` 폴백 제거로 깨지는 기존 테스트가 있으면 되돌리지 말고 대상 정의를 고친다 (plan 위험표)
- [X] T068 `backend/tests/contract/test_schema_drift.py` 로 생성 타입과 스키마가 어긋나지 않았는지 확인한다
- [X] T069 [quickstart.md](./quickstart.md) §5 의 화면 절차 6단계를 실제로 수행하고 결과를 기록한다 — 자동 테스트가 못 보는 FR-107·SC-006 을 사람이 확인한다
- [X] T070 [quickstart.md](./quickstart.md) §7 성공 기준 대조표 8개 항목을 모두 확인하고, 미달 항목이 있으면 사유와 함께 기록한다

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** — 의존 없음. 즉시 시작
- **Phase 2 (Foundational)** — Phase 1 이후. **US1·US2 를 모두 막는다**
- **Phase 3 (US2)** — Phase 2 이후
- **Phase 4 (US1)** — Phase 2 이후. US2 와 병렬 가능
- **Phase 5 (US3)** — US2 의 T023·T025 이후 (분류가 있어야 화면에 드러낼 수 있다)
- **Phase 6 (Polish)** — 원하는 스토리가 모두 끝난 뒤

### User Story Dependencies

- **US2 (P1)** — Phase 2 이후 독립. 다른 스토리에 의존하지 않는다
- **US1 (P1)** — Phase 2 이후 독립. US2 없이도 테스트된다
- **US3 (P2)** — US2 의 오류 분류에 의존한다. 화면 표시만 담당하므로 US1 과는 무관하다

### Within User Story 2

```
T012~T019 (테스트, 병렬) → 실패 확인
   ↓
T020 폴링 → T021 폴백 제거 → T022 보임 선호   [같은 함수, 순차]
   ↓
T023 예외 확장 → T025 코드 매핑
   ↓
T024 시도 기록 → T026 실행 기록 → T027 이벤트
   ↓
T028 메시지 → T029 스키마 생성
```

### Within User Story 1

```
T030~T038 (테스트, 병렬) → 실패 확인
   ↓
T039 preferences (독립)        T040 세션 필드
                                  ↓
                               T041 이벤트 관리 → T042 대기 함수
                                  ↓
                               T043 간격 → T044 자동 일시정지 → T045 AI 구간 제외
   ↓                              ↓
T046 → T047 라우트 등록        T048 → T049 → T050 세션 API
   ↓
T051 스키마 → T052 컨트롤 → T053 클라이언트 → T054·T055 화면
```

### Parallel Opportunities

- **Phase 1**: T001·T002 병렬 (다른 파일)
- **Phase 2**: T004~T010 전부 병렬 (전부 다른 파일). T011 은 T004·T007 이후
- **Phase 3 테스트**: T012~T019 전부 병렬 (같은 파일이지만 독립 함수 — 한 사람이 이어서 쓰거나 함수 단위로 나눈다)
- **Phase 4 테스트**: T030~T038 전부 병렬
- **US1 과 US2**: Phase 2 이후 서로 병렬. 겹치는 파일은 `runner.py`(T027 vs T043) 하나뿐이며 함수가 다르다
- **Phase 6**: T063·T064·T065 병렬

---

## Parallel Example: Phase 2

```bash
# 전부 다른 파일이므로 함께 진행한다
Task: "RunPacing 열거형을 backend/src/itb/domain/run_pacing.py 에"
Task: "신규 오류 코드를 backend/src/itb/domain/error.py 에"
Task: "DEFAULT_TIMEOUT_MS 를 backend/src/itb/domain/step.py 에서 10000 으로"
Task: "POLL_INTERVAL_MS 를 backend/src/itb/locator/strategy.py 에"
Task: "element_wait_ms 를 backend/src/itb/domain/run_result.py 에"
```

---

## Implementation Strategy

### MVP First (US2 만)

1. Phase 1 (픽스처) — 결함이 재현되는 것을 본다
2. Phase 2 (도메인)
3. Phase 3 (US2) — **여기서 멈추고 검증한다**
4. `uv run python -m pytest tests/integration/test_lazy_loading.py -v` 전부 통과
5. 사용자가 보고한 두 증상 중 하나(오탐)가 사라진다

US2 만으로도 값이 있다 — 정상 동작해야 할 테스트가 실패하던 것이 멈춘다.

### Incremental Delivery

1. Setup + Foundational → 기반 완료
2. US2 추가 → 독립 검증 → **MVP**
3. US1 추가 → 독립 검증 → 사용자가 실행을 눈으로 따라갈 수 있다
4. US3 추가 → 독립 검증 → 남은 실패의 원인이 화면에서 갈린다
5. Polish → 전체 회귀와 사람 확인

### 주의: 되돌리면 안 되는 실패

`.first` 폴백 제거(T021)로 기존 테스트가 깨질 수 있다. **그 테스트는 잘못된 요소에 대해
통과하고 있던 것이다** (research R2 실측). 폴백을 되살리지 말고 대상 정의를 고친다.
헌법 품질 게이트 4가 이것을 요구한다 — 테스트를 약화시켜 빌드를 통과시키지 않는다.

---

## Notes

- `[P]` = 다른 파일, 미완료 작업에 의존하지 않음
- 각 작업 또는 논리적 묶음마다 커밋한다
- 체크포인트에서 멈춰 스토리를 독립적으로 검증할 수 있다
- **Step DSL 에 필드를 더하지 않는다** — 헌법 원칙 I. 이 목록에 그런 작업이 없는 것이
  의도다
- **속도 설정을 테스트 자산에 넣지 않는다** — 헌법 원칙 V. `preferences.json` 은 프로젝트
  트리 밖이다
