---

description: "Task list template for feature implementation"
---

# Tasks: 부정 검증과 상태 검증

**Input**: Design documents from `/specs/021-negative-state-assertions/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/)

**Tests**: 포함한다. **헌법 품질 게이트 3이 요구한다** — 「제품은 테스트 도구다. 자기
테스트 없이 내보내는 것은 허용되지 않는다」. 선택 사항이 아니다.

**Organization**: 사용자 스토리별로 묶는다. 실행 순서는 우선순위(P)를 따른다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리인가 (US1, US2, US3)
- 파일 경로를 정확히 적는다

## Path Conventions

웹 애플리케이션 2계층: `backend/src/itb/`, `frontend/src/`. 검증은
`backend/tests/{unit,integration,contract}/`, `frontend/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 이 기능을 확인할 대상 화면과, 무엇이 깨질지에 대한 기준선을 먼저 만든다.

- [X] T001 고정 대상을 `fixtures/sample-app/locked-controls.html` 로 추가하고 `fixtures/sample-app/serve.py` 에 경로를 붙인다 — 네 가지가 한 화면에 있어야 한다: (a) `disabled` 인 삭제 버튼, (b) 같은 모양의 활성 버튼, (c) 누르면 **0.8초 뒤에** `오류가 발생했습니다` 를 띄우는 버튼, (d) 조작 가능 여부를 가질 수 없는 설명용 `<div>`. 기존 고정 대상 파일은 고치지 않는다
- [X] T002 [P] `backend/scripts/test-backend.sh` 와 `cd frontend && npm run typecheck && npm test` 를 지금 상태에서 돌려 **기준선을 기록**한다 — 통과/실패 건수뿐 아니라 **소요 시간**도 적는다. 대기 규칙 통일(T012)이 느리게 만드는 테스트를 이 값과 비교해 가린다. 결과는 `specs/021-negative-state-assertions/baseline.md`
- [X] T003 [P] 텍스트 검증의 **실패**를 기대하는 기존 검증을 전수 조사해 `specs/021-negative-state-assertions/baseline.md` 에 목록으로 남긴다 — 이들이 T012 이후 제한 시간만큼 느려진다. **이 목록이 T019 의 작업 범위다**

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 나머지 전부가 참조할 도메인 열거형과 형태 규칙, 그리고 생성 스키마.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어느 사용자 스토리도 시작할 수 없다. 헌법이
요구하는 순서다 — 스키마가 먼저 바뀌고 소비자가 따라온다 (원칙 I).

- [X] T004 `AssertionKind` 에 `ENABLED = "enabled"` · `DISABLED = "disabled"` 를, `MatchMode` 에 `NOT_EQUALS = "not_equals"` · `NOT_CONTAINS = "not_contains"` 를 `backend/src/itb/domain/assertion.py` 에 추가한다. 각 값에 **무엇을 뜻하는지와 `hidden` 과 무엇이 다른지**를 docstring 으로 남긴다 ([data-model.md §1](./data-model.md))
- [X] T005 `Assertion._check_shape` 를 [data-model.md §2](./data-model.md) 의 표대로 확장한다 — (a) `not_*` 는 `text`·`url` 에서만 허용, (b) `not_*` 에는 비어 있지 않은 `value` 필수, (c) `enabled`·`disabled` 는 `target` 필수·`value` 금지. **기존 `equals`·`contains` 의 허용 범위는 건드리지 않는다** — `visible` + `contains` 가 실린 예전 정의가 거절되면 하위 호환이 깨진다. T004 에 의존
- [X] T006 스키마와 타입을 재생성한다 — `cd backend && uv run python -m itb.schema.export` 후 `cd ../frontend && npm run gen:types`. `backend/schema/step-dsl.schema.json` 과 `frontend/src/types/generated/step-dsl.d.ts` 에 새 값 넷이 실렸는지 확인한다. T004·T005 에 의존
- [X] T007 [P] 형태 규칙 단위 검증을 `backend/tests/unit/test_domain_invariants.py` 에 추가한다 — 허용 조합과 거절 조합을 모두 세운다. 특히 **`visible` + `contains` 가 여전히 통과**하고 **`visible` + `not_contains` 는 거절**되는 두 경우를 함께 세워, 하위 호환과 새 규칙이 같은 표에서 나왔음을 못 박는다. T005 에 의존
- [X] T008 [P] `dsl_version` 을 올리지 않았음을 `backend/tests/contract/test_dsl_roundtrip.py` 에서 확인한다 — 새 종류가 든 정의가 공유 묶음 왕복을 통과해야 한다 ([research.md R4](./research.md))

**Checkpoint**: 도메인 어휘가 확정됐다. 사용자 스토리를 시작할 수 있다.

---

## Phase 3: User Story 1 — 부정 검증 (Priority: P1) 🎯 MVP

**Goal**: 「특정 텍스트가 화면에 없다」와 「주소가 특정 값이 아니다」를 검증 Step 하나로
표현하고, **거짓으로 통과하지 않게** 한다.

**Independent Test**: 상태 검증 없이도 시나리오의 「~가 뜨지 않는지」 계열 문장을 정의로
옮길 수 있다. T001 의 고정 대상에서 0.8초 뒤 뜨는 오류를 부정 검증이 잡는지로 확인한다.

### Tests for User Story 1 ⚠️

> **먼저 쓰고, 실패하는 것을 확인한 뒤 구현한다.**

- [X] T009 [P] [US1] 공통 대기 도우미의 단위 검증을 `backend/tests/unit/test_assertion_settle.py` 로 새로 만든다 — (a) 조건이 처음부터 참이면 **즉시** 통과하고 제한 시간을 소모하지 않는다, (b) 중간에 참이 되면 그 시점에 통과한다, (c) 끝까지 거짓이면 **마지막 관찰값**으로 실패 설명을 만든다
- [X] T010 [P] [US1] 부정 검증의 실행 검증을 `backend/tests/integration/test_negative_assertion.py` 로 새로 만든다 — **핵심은 거짓 통과 방지다**: T001 의 「0.8초 뒤 오류」 화면에서 제한 시간 5초의 「`오류` 를 포함하지 않는다」가 **실패**해야 한다. 이 하나가 통과하지 못하면 기능 전체가 무의미하다. 함께 세울 것: 정상 경로에서 통과하고 5초를 기다리지 않는다는 것

### Implementation for User Story 1

- [X] T011 [US1] 공통 대기 도우미를 `backend/src/itb/execution/step_executor.py` 에 추가한다 — 조건 판정 함수와 제한 시간을 받아 50ms 간격으로 폴링하고, 참이 되면 즉시 끝내고, 넘기면 마지막 관찰값을 돌려준다. **`_assert_url` 의 기존 폴링을 이 도우미로 옮긴다** — 새 경로를 만들고 옛 경로를 남기면 두 대기 규칙이 공존한다
- [X] T012 [US1] `_assert_text` 를 대기 도우미 위로 옮긴다 (`backend/src/itb/execution/step_executor.py`) — 대상이 있으면 요소를 한 번 찾고 그 요소의 텍스트를 다시 읽으며 폴링하고, 없으면 화면 전체 텍스트를 다시 읽는다. **대상을 찾지 못하면 긍정·부정 모두 실패**한다 (FR-006). T011 에 의존
- [X] T013 [US1] 비교 판정 `_matches` 에 `not_equals`·`not_contains` 를 더한다 (`backend/src/itb/execution/step_executor.py`) — 긍정 판정의 부정으로 정의해 두 갈래가 갈리지 않게 한다. T004 에 의존
- [X] T014 [US1] 부정형 실패 설명을 `backend/src/itb/execution/step_executor.py` 에 만든다 — [data-model.md §3.3](./data-model.md) 의 문구를 따른다. **020 이 이 문자열을 `mismatch.observed` 에 그대로 싣는다** — 기대와 실제가 모두 들어 있어야 하고, 긍정형 문구와 같은 문체여야 한다
- [X] T015 [US1] `backend/src/itb/execution/assertion_builder.py` 의 표시 이름 생성이 **비교 방식을 드러내게** 한다 — 지금은 `텍스트 '오류' 확인` 만 만들어 긍정·부정이 구별되지 않는다. T004 에 의존
- [X] T016 [US1] 수동 삽입 서술(`AssertTextSpec`·`AssertUrlSpec`)이 부정 비교를 받게 한다 (`backend/src/itb/domain/manual_step.py`) — 기본값은 그대로 두고 값 범위만 넓힌다. `derive_label` 도 비교 방식을 드러내야 한다 (FR-022)
- [X] T017 [US1] `_assertion_lines` 에 부정형 대응을 더한다 (`backend/src/itb/generator/playwright_gen.py`) — [contracts/export-mapping.md](./contracts/export-mapping.md) 의 6개 행. `url` + `not_contains` 는 기존 판단대로 **정규식이 아니라 문자열 포함**의 부정으로 만든다
- [X] T018 [P] [US1] 내보내기 회귀 조합을 `backend/tests/unit/test_export_keeps_assertion.py` 에 추가한다 — 부정형 6개 조합. T017 에 의존
- [X] T019 [US1] T003 목록의 테스트를 실제로 돌려 **T002 기준선과 소요 시간을 비교**한다. 느려진 테스트는 그 테스트의 `timeout_ms` 를 짧게 주어 고친다 — **제품의 대기 동작을 되돌리지 않는다**. 결과가 바뀐(실패→통과) 테스트가 있으면 `specs/021-negative-state-assertions/baseline.md` 에 **어느 것이 왜 바뀌었는지** 적는다. 조용히 초록으로 넘어가면 안 된다

**Checkpoint**: 부정 검증이 실행·내보내기 양쪽에서 동작한다. 화면 노출은 US3.

---

## Phase 4: User Story 2 — 상태 검증 (Priority: P2)

**Goal**: 「요소를 조작할 수 없다」를 버튼을 누르지 않고 검증한다.

**Independent Test**: US1 과 무관하게, T001 고정 대상의 비활성 버튼과 활성 버튼에 같은
검증을 걸어 통과·실패가 갈리는지로 확인한다.

### Tests for User Story 2 ⚠️

- [X] T020 [P] [US2] 상태 검증의 실행 검증을 `backend/tests/integration/test_state_assertion.py` 로 새로 만든다 — (a) 비활성 버튼에 「조작할 수 없다」가 통과, (b) 활성 버튼에 걸면 실패하고 설명이 기대·실제를 담는다, (c) **대상이 없으면 실패한다** — `hidden` 과 갈리는 지점이므로 반드시 세운다, (d) 늦게 잠기는 버튼을 제한 시간 안에서 기다려 통과한다

### Implementation for User Story 2

- [X] T021 [US2] `_assert` 에 `enabled`·`disabled` 분기를 더한다 (`backend/src/itb/execution/step_executor.py`) — 대상을 찾고 조작 가능 여부를 **공통 대기 도우미로 폴링**한다. `expect()` 를 쓰지 않는다 ([research.md R2](./research.md)). 대상 탐색 실패를 통과로 바꾸지 않는다. T011 에 의존
- [X] T022 [US2] 상태 검증의 실패 설명을 만든다 (`backend/src/itb/execution/step_executor.py`) — [data-model.md §3.3](./data-model.md) 의 두 문구
- [X] T023 [US2] `backend/src/itb/execution/assertion_builder.py` 의 `ELEMENT_KINDS` 에 새 두 종류를 넣어 대상을 필수로 만들고, 표시 이름을 더한다. T004 에 의존
- [X] T024 [US2] 조작 가능 여부를 가질 수 없는 대상에 대한 **작성 시점 경고**를 `backend/src/itb/execution/assertion_builder.py` 에 더한다 — 수집된 후보 묶음의 태그 정보로 판정한다. **Step 은 만든다**: 막으면 `contenteditable` 이나 ARIA 로 잠금을 표현하는 정당한 사용까지 막힌다 ([data-model.md §5](./data-model.md)). 새 수집을 추가하지 않는다
- [X] T025 [US2] `_assertion_lines` 에 `toBeEnabled`·`toBeDisabled` 를 더한다 (`backend/src/itb/generator/playwright_gen.py`)
- [X] T026 [P] [US2] 내보내기 회귀 조합 2개를 `backend/tests/unit/test_export_keeps_assertion.py` 에 추가한다. T025 에 의존
- [X] T027 [P] [US2] 작성 시점 경고의 검증을 `backend/tests/unit/test_state_assertion_warning.py` 로 새로 만든다 — 폼 요소에는 경고가 없고 설명용 요소에는 경고가 있으며, **두 경우 모두 Step 은 만들어진다**

**Checkpoint**: 상태 검증이 실행·내보내기 양쪽에서 동작한다.

---

## Phase 5: User Story 3 — 세 작성 경로와 표시 (Priority: P3)

**Goal**: 새 어휘를 AI 작성·화면 폼·수동 삽입에서 쓸 수 있고, 목록에서 정반대 뜻의 두
검증이 구별된다.

**Independent Test**: 같은 검증을 세 경로로 만들어 정의가 같은지 비교한다.

### Tests for User Story 3 ⚠️

- [X] T028 [P] [US3] 도구 표면 검증을 `backend/tests/unit/test_tool_surface.py` 에서 확장한다 — **도구 개수가 늘지 않았음**(`TOOL_NAMES` 16종 · `STEP_PRODUCING_TOOLS` 9종)과 검증 도구의 종류 열거가 도메인 열거형과 일치함을 함께 세운다. 손으로 옮겨 적은 목록이 도메인과 갈리는 것을 막는다
- [X] T029 [P] [US3] 세 작성 경로의 산출물이 같은지를 `backend/tests/integration/test_authoring_parity_negative.py` 로 새로 만든다 — 화면 API·수동 삽입·작성 도구가 만든 정의가 표시 이름과 식별자를 빼고 동일해야 한다 (원칙 I)
- [X] T030 [P] [US3] 목록 요약 검증을 `frontend/tests/AssertionSummary.test.tsx` 로 새로 만든다 — **같은 값의 긍정·부정 두 검증이 서로 다른 문자열로 요약**되어야 하고, 종류가 영문 원문으로 나오지 않아야 한다 ([research.md R6](./research.md))

### Implementation for User Story 3

- [X] T031 [US3] 검증 도구의 인자 스키마와 설명을 넓힌다 (`backend/src/itb/authoring/tools.py`) — 종류 열거 6종, 비교 방식 4종, 그리고 값을 쓰지 않는 종류에 부정 비교를 줄 수 없다는 제약. **도구를 늘리지 않는다**. 지원하지 않는 값에 대한 오류 문구도 새 목록으로 갱신한다 (지금 「visible / hidden / text / url 중 하나」로 하드코딩되어 있다)
- [X] T032 [US3] 작성 지침에 한 문단을 더한다 (`backend/src/itb/authoring/agent.py`) — 「부정 검증이 통과하지 않는다고 조건을 긍정형으로 뒤집지 마라」. 020 이 같은 자리에 넣은 문장과 같은 취지이며, 없으면 모델에게는 뒤집는 것이 가장 쉬운 길이다 ([contracts/assertion-surface.md §3](./contracts/assertion-surface.md))
- [X] T033 [US3] 검증 추가 API 가 새 값을 그대로 받는지 확인하고, 형태 규칙 위반의 오류 문구를 점검한다 (`backend/src/itb/api/routes/steps.py`) — 요청 모델이 도메인 열거형을 참조하므로 **손으로 옮겨 적은 목록이 없어야 한다**. 있으면 지운다
- [X] T034 [US3] 검증 종류와 비교 방식의 한국어 문구를 `frontend/src/lib/wording.ts` 한곳에 모은다 — 폼·목록·상세가 같은 출처를 읽는다. 세 곳이 각자 만들면 같은 검증이 화면마다 다르게 불린다
- [X] T035 [US3] Step 목록 요약을 고친다 (`frontend/src/components/workbench/StepList.tsx` 의 `locatorSummary`) — 종류를 한국어로, **비교 방식을 함께** 보인다. R6 의 선결 조건이다. T034 에 의존
- [X] T036 [US3] 검증 추가 폼을 넓힌다 (`frontend/src/components/AssertionForm.tsx`) — 종류 6개(`KINDS`), 비교 방식 4개, `NEEDS_TARGET` 에 새 두 종류 추가, 상태 검증을 고르면 비교 값 칸을 숨긴다. **범위 외 기능을 비활성 항목으로 넣지 않는다**. T034 에 의존
- [X] T037 [US3] 부정 비교를 고른 자리에 **한계 안내**를 보인다 (`frontend/src/components/AssertionForm.tsx`) — 조건이 참이 되면 즉시 통과하므로 늦게 나타나는 것을 놓칠 수 있고, 먼저 화면이 안정되었음을 확인하는 검증을 앞에 두는 것이 좋다 (FR-026). 경고가 아니라 **조언**의 문체로 쓴다. T036 에 의존
- [X] T038 [P] [US3] 폼 검증을 `frontend/tests/AssertionForm.test.tsx` 에 추가하거나 새로 만든다 — 상태 검증 선택 시 값 칸이 사라지는지, 부정 비교 선택 시 안내가 나타나는지. T036·T037 에 의존

**Checkpoint**: 세 경로에서 새 어휘를 쓸 수 있고 목록에서 구별된다.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T039 [P] 020 과의 정합을 `backend/tests/unit/test_classify_assertion.py` 와 `backend/tests/unit/test_authoring_mismatch.py` 에서 못 박는다 — 새 종류와 부정 비교에서도 어긋남이 기록되고 분류(이미 아는 결함·오늘 깨진 것·해소됨)가 나온다. **구조상 동작한다는 것과 앞으로도 그렇다는 것은 다르다** ([data-model.md §4](./data-model.md))
- [X] T040 [P] 하위 호환을 `backend/tests/integration/test_legacy_project_reads.py` 에서 확인한다 — 새 값이 없는 예전 정의가 그대로 읽히고 실행된다 (FR-030)
- [X] T041 [P] 검증 어휘 변경을 `docs/prd.md` 의 검증 관련 절에 반영한다 — 4종·2종이던 목록을 6종·4종으로 고치고 범위 외 항목을 갱신한다
- [X] T042 `backend/scripts/test-backend.sh` 와 `cd frontend && npm run typecheck && npm test` 를 전량 돌려 **T002 기준선과 비교**한다. 이 기능이 깬 것이 없는지, 소요 시간이 얼마나 늘었는지 확인하고 결과를 `specs/021-negative-state-assertions/baseline.md` 에 기록한다
- [ ] T043 [quickstart.md](./quickstart.md) 의 §2~§5 를 사람이 손으로 수행하고 결과를 기록한다 — 자동 검증이 덮지 못하는 것(문구가 읽히는지, 안내가 눈에 들어오는지, 목록에서 구별되는지)을 본다
- [ ] T044 [quickstart.md](./quickstart.md) §8 내보내기를 사람이 손으로 확인한다 — 새 종류가 든 테스트를 내보내 **제품 없이** 실행했을 때 제품 안에서와 같은 결과가 나오는지 (원칙 V)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존 없음. 즉시 시작
- **Foundational (Phase 2)**: Setup 후. **모든 사용자 스토리를 막는다**
- **US1 (Phase 3)**: Foundational 후
- **US2 (Phase 4)**: Foundational 후. **T011(대기 도우미)에 의존** — US1 과 완전히 독립은 아니다
- **US3 (Phase 5)**: Foundational 후. 어휘가 있어야 노출할 것이 있으므로 US1 또는 US2 중 최소 하나가 끝나야 의미가 있다
- **Polish (Phase 6)**: 원하는 스토리가 모두 끝난 뒤

### 스토리 간 의존 — 솔직하게

이 기능의 세 스토리는 **완전히 독립적이지 않다.** US2 의 상태 검증은 US1 이 만드는 공통
대기 도우미(T011)를 쓴다. 대기 도우미를 US1 에 둔 이유는 그것이 US1 의 핵심 위험(거짓
통과)을 막는 장치이기 때문이다.

US2 를 먼저 하려면 T011 만 앞당기면 된다. **T011 은 Foundational 로 옮겨도 되는 작업**이고,
US1 에 둔 것은 그것이 US1 의 가치와 직결되기 때문이지 기술적 필연이 아니다.

### Within Each User Story

- 테스트를 먼저 쓰고 실패를 확인한 뒤 구현한다
- 도메인 → 실행 → 생성기 → 작성 경로 → 화면 순서
- **생성기는 실행과 짝이다.** 둘이 갈리면 원칙 V 가 깨지고, 나중에 발견하면 어느 쪽이
  맞는지 판단해야 한다

### Parallel Opportunities

- T002·T003 (Setup)
- T007·T008 (Foundational, T005/T006 후)
- T009·T010 (US1 테스트)
- T018 (US1 내보내기 테스트, T017 후)
- T026·T027 (US2)
- T028·T029·T030 (US3 테스트)
- T039·T040·T041 (Polish)

---

## Parallel Example: User Story 1

```bash
# US1 의 테스트 둘을 함께 쓴다 (구현 전, 실패를 확인)
Task: "공통 대기 도우미 단위 검증 in backend/tests/unit/test_assertion_settle.py"
Task: "부정 검증 실행 검증 in backend/tests/integration/test_negative_assertion.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup — 고정 대상과 기준선
2. Phase 2 Foundational — 도메인 어휘 (**모두를 막는다**)
3. Phase 3 US1 — 부정 검증
4. **멈추고 확인**: T001 의 「0.8초 뒤 오류」 화면에서 부정 검증이 실패하는가.
   통과한다면 기능이 동작하지 않는 것이다
5. 여기까지가 시나리오 문서의 「~가 뜨지 않는지」 계열을 옮길 수 있는 최소 단위

### Incremental Delivery

1. Setup + Foundational → 어휘 확정
2. US1 → 부정 검증 (MVP)
3. US2 → 상태 검증
4. US3 → 세 경로 노출과 표시
5. Polish → 020 정합·호환·문서·전량 검증

**US3 없이 US1·US2 만 끝내면 API 로만 쓸 수 있다.** 화면에서 고를 수 없으므로 실제
사용자에게는 절반이다 — US3 를 「나중에」로 미루지 않는다.

---

## Notes

- [P] = 다른 파일, 의존 없음
- 각 작업 또는 논리적 묶음 뒤에 커밋한다
- **테스트를 지우거나 비활성화해서 통과시키지 않는다** (헌법 품질 게이트 4)
- T019 와 T042 의 기준선 비교를 건너뛰지 않는다 — 이 기능은 기존 동작을 하나 바꾸므로,
  무엇이 바뀌었는지 모르는 채로 끝내면 나중에 원인을 찾을 수 없다

---

## Phase 7: Convergence

명세·계획 대비 남은 일. `/speckit-converge` 가 코드를 실제로 훑어 찾은 것이다.

- [X] T045 Step 상세에 검증 조건 요약을 넣는다 (`frontend/src/components/workbench/StepDetail.tsx`) per FR-023 (partial) — **HIGH**. 지금 상세는 기대값 편집 칸만 보이고 **종류와 비교 방식을 어디에도 표시하지 않는다.** 목록에서 「텍스트가 `오류` 를 포함하지 않음」을 읽고 상세를 열면 그 정보가 사라진다 — 편집하려고 연 화면에서 무엇을 편집하는지 모르는 상태다. `wording.assertionSummary` 를 쓴다 (새 문구를 만들지 않는다)
- [X] T046 상태 검증의 대기를 세운다 per FR-013 · US2/AC3 (missing) — **MEDIUM**. `fixtures/sample-app/locked-controls.html` 에 **0.5초 뒤 잠기는 버튼**을 더하고, `backend/tests/integration/test_state_assertion.py` 에 「제한 시간 안에서 상태가 참이 되기를 기다려 통과한다」를 넣는다. 지금은 상태 검증이 기다리는지를 아무것도 확인하지 않는다 — 즉시 판정으로 바뀌어도 전량 검증이 초록이다
- [X] T047 새 어휘의 어긋남 기록을 `backend/tests/unit/test_authoring_mismatch.py` 에 세운다 per FR-024 (partial) — **MEDIUM**. T039 은 두 파일을 지목했는데 `test_classify_assertion.py` 만 했다. 부정 비교와 상태 검증에서도 **Step 이 남고 관찰값이 적히는지**를 확인한다. 020 이 만든 「어긋나도 버리지 않는다」가 새 종류에서 깨지면, 사용자는 부정 검증이 실패할 때 Step 자체를 잃는다
