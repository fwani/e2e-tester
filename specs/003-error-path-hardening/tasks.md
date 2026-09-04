---

description: "Task list for 003 이상 경로 견고성 (비정상 조작 결함 라운드)"
---

# Tasks: 이상 경로 견고성 (비정상 조작 결함 라운드)

**Input**: Design documents from `/specs/003-error-path-hardening/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: 이 라운드의 산출물 자체가 검증이다. 테스트 작업은 선택이 아니라 본체다 (spec 산출물 3종 중 "회귀 방지 자동 테스트", 헌법 게이트 3).

**Organization**: 사용자 스토리별로 묶어 각각 독립적으로 구현·검증할 수 있게 한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리에 속하는가 (US1~US6)
- 설명에 정확한 파일 경로를 포함한다

## Path Conventions

- 백엔드: `backend/src/itb/`, `backend/tests/`
- 프런트엔드: `frontend/src/`, `frontend/tests/`
- 고정 앱(제품 아님): `fixtures/sample-app/`
- 시나리오 권위 목록: `specs/003-error-path-hardening/contracts/abnormal-scenarios.json`

---

## ⚠️ 착수 전 확인 (필수)

- [ ] T001 다른 세션이 같은 저장소를 동시에 수정 중인지 확인한다 — `git log --oneline -5` 와 `git status --porcelain` 로 최근 커밋 작성자와 작업 트리를 본다. 2026-09-04 13:51 커밋 `725a9bb`(다른 세션)이 `backend/src/itb/secrets/`·`frontend/src/pages/KeyManagement.tsx` 를 수정했고 그 뒤로도 수정이 이어졌다. **이 라운드의 구현은 `backend/`·`frontend/` 를 폭넓게 건드리므로 충돌 가능성이 실재한다.** 동시 작업이 확인되면 진행 전에 조율한다

---

## Phase 1: Setup

- [ ] T002 `backend/tests/abnormal/__init__.py` 와 `frontend/tests/abnormal/` 디렉터리를 만든다. 이 라운드의 검증을 한곳에 모아 RG-103(세 면 각각 검증 존재) 충족 여부를 셀 수 있게 한다
- [ ] T003 [P] `backend/tests/abnormal/README.md` 에 이 디렉터리의 규칙을 적는다 — 시나리오 목록은 `specs/003-error-path-hardening/contracts/abnormal-scenarios.json` 하나이며 여기에 복사본을 두지 않는다는 것, 판정은 3축이라는 것

---

## Phase 2: Foundational (모든 사용자 스토리의 선행 조건)

**이 단계가 끝나기 전에는 어떤 스토리도 판정 기준을 갖지 못한다.**

- [ ] T004 `backend/src/itb/domain/error.py` 를 만들고 `ErrorCode`(기존 23개) · `Category`(`blocked`/`broken`) · `ErrorBody` · `ErrorResponse` 를 `backend/src/itb/api/errors.py` 에서 옮긴다. 값과 이름을 바꾸지 않는다 (RG-102)
- [ ] T005 `backend/src/itb/domain/error.py` 에 `INTERNAL_ERROR` 코드를 더한다 — 처리되지 않은 오류 전용. `DEFINITION_INVALID` 재사용을 끝내기 위한 것이다 (EC-003)
- [ ] T006 `backend/src/itb/domain/error.py` 에 `CATEGORY: dict[ErrorCode, Category]` 전수 대응표를 만든다. 분류는 [data-model.md §1.3](./data-model.md) 의 표를 따른다. `SESSION_LOST` 는 기본 `blocked` 로 두고 T044 에서 재검토한다
- [ ] T007 `backend/src/itb/domain/error.py` 에 `NEXT_ACTION: dict[ErrorCode, str]` 코드별 기본 문구를 만든다. 빈 문자열을 허용하지 않는다 (EC-004)
- [ ] T008 `ErrorBody` 에 `category` 와 `next_action` 필드를 더한다. `category` 는 `code` 로부터 `CATEGORY` 대응표로 자동 결정되게 하고 호출부가 직접 넣지 못하게 한다 (EC-001·EC-002)
- [ ] T009 `backend/src/itb/api/errors.py` 를 도메인 모델을 재수출하는 얇은 층으로 줄인다. `ApiError` · `bad_request()` · `not_found()` · `conflict()` · `not_implemented()` · `validation_error_response()` 같은 FastAPI 결합부만 남긴다. **기존 임포트 경로가 그대로 동작해야 한다** (RG-102)
- [ ] T010 `backend/src/itb/schema/export.py` 의 `MODELS` 에 `"error-response": TypeAdapter(ErrorResponse)` 를 더하고 `uv run python -m itb.schema.export` 로 `backend/schema/error-response.schema.json` 을 만든다 (EC-006)
- [ ] T011 `cd frontend && npm run gen:types` 로 `frontend/src/types/generated/error-response.d.ts` 를 만든다
- [ ] T012 `frontend/src/api/client.ts` 의 손으로 쓴 `ErrorCode` union(13~33행)을 지우고 생성된 타입을 임포트한다. `ApiError` 클래스가 `category` 와 `next_action` 을 갖게 한다 (EC-006)
- [ ] T013 `backend/tests/abnormal/catalogue.py` 에 시나리오 목록 로더와 판정 3축 헬퍼를 만든다. `specs/003-error-path-hardening/contracts/abnormal-scenarios.json` 을 읽고, 축별 판정 결과에 시나리오 식별자(`AS-NNN`)를 붙여 실패 메시지에 싣는다
- [ ] T014 [P] `frontend/tests/abnormal/catalogue.ts` 에 같은 목록을 읽는 로더를 만든다. **목록을 복사하지 않고 같은 JSON 파일을 읽는다** (research R3)

**Checkpoint**: 오류 계약이 한 곳에서 정의되고 양쪽이 그것을 쓴다. 시나리오 목록을 양쪽이 읽는다.

---

## Phase 3: User Story 1 — 에러를 만나면 그것이 내 잘못인지 도구 잘못인지 안다 (P1) 🎯 MVP

**Goal**: 모든 사용자 대면 오류가 "막은 것"/"깨진 것"으로 분류되어 다음 행동과 함께 전달된다.

**Independent Test**: 이상 조작 하나만 가해도(빈 이름으로 저장) 응답과 화면에서 분류·이유·다음 행동 셋을 확인할 수 있다.

### 검증 (구현 전에 쓴다)

- [ ] T015 [P] [US1] `backend/tests/abnormal/test_error_contract.py` — 모든 `ErrorCode` 가 `CATEGORY` 와 `NEXT_ACTION` 에 있는지 확인한다. 코드를 추가하고 분류를 빼먹으면 실패한다 (RG-104-1)
- [ ] T016 [P] [US1] `backend/tests/abnormal/test_error_contract.py` — 처리되지 않은 오류가 `code=INTERNAL_ERROR` · `category=broken` 을 내고, 정상 거부와 코드만으로 구별되는지 확인한다 (EC-003)
- [ ] T017 [P] [US1] `backend/tests/abnormal/test_error_contract.py` — 오류 응답에 내부 파일 경로·호출 스택이 없고 비밀 값이 새지 않는지 확인한다 (EC-005·SC-209)
- [ ] T018 [US1] `backend/tests/abnormal/test_route_sweep.py` — 앱에 등록된 **모든** 요청 경로를 열거해 각각 최소 하나의 거부를 유발하고, 응답이 오류 스키마를 만족하며 `category`·`next_action` 을 담는지 확인한다. 거부 유발 방법이 등록되지 않은 새 경로는 **실패**로 취급한다 (RG-104-2)
- [ ] T019 [P] [US1] `backend/tests/abnormal/test_no_bypass.py` — `backend/src/itb/api/` 원본을 훑어 `api/errors.py` 밖에서 오류 계약을 우회해 응답을 만드는 곳이 없는지 확인한다 (RG-104-3)

### 구현

- [ ] T020 [US1] `backend/src/itb/api/app.py` 의 처리되지 않은 오류 처리기(90~101행)가 `INTERNAL_ERROR` · `category=broken` 을 내게 고친다. 스택·경로 비노출은 유지한다 (EC-003·EC-005)
- [ ] T021 [US1] `backend/src/itb/api/app.py` 의 요청 검증 실패 처리기(77~88행)가 `category=blocked` 와 `next_action` 을 담게 한다
- [ ] T022 [P] [US1] `frontend/src/components/ErrorNotice.tsx` 를 만든다 — 오류 표시의 **공용 통로**. `message` 와 `next_action` 을 **함께** 보여주고, `category=broken` 을 사용자가 고칠 수 있는 것처럼 보이지 않게 한다. 계약 형태가 아닌 응답(연결 실패)도 같은 통로로 표시한다
- [ ] T023 [US1] `frontend/src/pages/` 의 14개 화면이 오류를 `ErrorNotice` 로 표시하게 고친다. 각 화면이 `err.message` 를 직접 그리지 않는다 (RG-104-4)
- [ ] T024 [US1] `backend/src/itb/api/ws/session_events.py` 가 실시간 통로로 보내는 오류에 같은 `ErrorBody` 를 싣게 한다 (EC-008)
- [ ] T025 [P] [US1] `frontend/tests/abnormal/ErrorNotice.test.tsx` — 공용 통로가 `message` 와 `next_action` 을 함께 보여주는지, `broken` 과 `blocked` 를 구분해 보여주는지 확인한다
- [ ] T026 [US1] `frontend/tests/abnormal/error-single-path.test.tsx` — 각 화면의 오류 경로가 공용 통로를 지나는지 훑어 확인한다 (RG-104-4)
- [ ] T027 [US1] `specs/001-interactive-ai-test-builder/contracts/rest-api.md` 의 오류 응답 공통 형태(7~10행)를 새 필드 둘을 포함하도록 갱신하고 `specs/003-error-path-hardening/contracts/error-contract.md` 를 참조로 건다

**Checkpoint**: 오류가 분류되어 전달되고 화면이 하나의 통로로 보여준다. 나머지 스토리가 판정할 기준이 섰다.

---

## Phase 4: User Story 2 — 잘못된 값을 넣어도 도구가 깨지지 않는다 (P1)

**Goal**: 경계 입력에 대해 판정 3축이 성립한다. 시나리오 AS-001~AS-017.

**Independent Test**: 각 조작 면에 경계 입력을 넣어 3축을 확인한다.

- [ ] T028 [P] [US2] `backend/tests/abnormal/test_invalid_input.py` — 요청 경계 시나리오 AS-001~AS-006 을 판정 3축으로 돌린다 (AP-010~015)
- [ ] T029 [P] [US2] `frontend/tests/abnormal/invalid-input.test.tsx` — 화면 시나리오 AS-007~AS-012 를 돌린다. 거부 뒤에도 입력하던 다른 값이 화면에 남아 있는지(판정축 ③) 확인한다
- [ ] T030 [P] [US2] `backend/tests/abnormal/test_invalid_input.py` — 외부 경계 시나리오 AS-013~AS-017 을 돌린다. AI 응답 형식 붕괴와 대상 페이지의 이상 내용이 제품을 깨뜨리지 않는지 본다
- [ ] T031 [US2] T028~T030 이 낸 실패를 고친다 — 경계 검증이 새는 지점, 거부 메시지가 원본 입력을 되돌려 화면을 훼손하는 지점(AP-015), 길이 한계가 사용자에게 알려지지 않는 지점(AP-012)
- [ ] T032 [US2] `backend/src/itb/api/routes/` 에서 T031 이 드러낸 경계 검증 누락을 채운다. 경로 탈출(AP-013)과 중복 이름(AP-014)은 반드시 거부되어야 한다

**Checkpoint**: 잘못된 입력값 시나리오 17건이 3축을 통과한다.

---

## Phase 5: User Story 3 — 순서를 어겨도 세션이 엉키지 않는다 (P1)

**Goal**: 상태 위반에 대해 판정 3축이 성립한다. 시나리오 AS-018~AS-032.

**Independent Test**: 세션 하나에 순서를 어긴 조작을 차례로 가하고 3축을 확인한다.

- [ ] T033 [P] [US3] `backend/tests/abnormal/test_order_violation.py` — 요청 경계 시나리오 AS-018~AS-023 을 돌린다 (AP-020~024)
- [ ] T034 [P] [US3] `frontend/tests/abnormal/order-violation.test.tsx` — 화면 시나리오 AS-024~AS-029 를 돌린다. 버튼 연타(AS-024)가 요청을 두 번 내보내지 않거나 두 번째가 거절되고 그 사실이 드러나는지 확인한다 (AP-022)
- [ ] T035 [P] [US3] `backend/tests/abnormal/test_order_violation.py` — 외부 경계 시나리오 AS-030~AS-032 를 돌린다 (닫힌 탭, 해석 중 페이지 이동, 종료된 세션의 미러 연결)
- [ ] T036 [US3] `backend/src/itb/api/routes/sessions.py` 의 상태 위반 거부가 `execution/state_machine.py` 의 `allowed_commands(state)` 를 `detail` 에 실어 "지금 무엇이 가능한지"를 알리게 한다 (AP-020). 상태 기계 자체는 바꾸지 않는다
- [ ] T037 [US3] T033~T035 가 낸 실패를 고친다. 특히 거부가 세션을 못 쓰게 만드는 경우(AP-024)와 존재하지 않는 대상 조작이 주변 자산을 손상시키는 경우(AP-021)
- [ ] T038 [US3] `frontend/src/pages/SessionScreen.tsx` 가 화면 복귀 시 세션의 현재 상태를 반영하게 한다 — 옛 상태로 멈춰 있지 않는다 (AP-023·AS-026)

**Checkpoint**: 순서·상태 위반 시나리오 15건이 3축을 통과한다.

---

## Phase 6: User Story 4 — 바깥이 무너져도 내 작업은 남는다 (P2)

**Goal**: 외부 실패에 대해 판정 3축이 성립한다. 시나리오 AS-033~AS-042.

**Independent Test**: 외부 경계 하나를 실패시키고 3축을 확인한다.

- [ ] T039 [P] [US4] `fixtures/sample-app/` 에 지연·무응답·오류를 내는 경로를 더한다. 제품 코드가 아니다 (research R4)
- [ ] T040 [P] [US4] `backend/tests/abnormal/fakes.py` 에 AI 클라이언트 대역을 만든다 — 오류를 던지는 것, 형식이 깨진 응답을 주는 것, 시간을 끄는 것. `itb.llm.client.create_client` 를 대체한다. **제품에 실패 주입 스위치를 넣지 않는다**
- [ ] T041 [P] [US4] `backend/tests/abnormal/test_external_failure.py` — 요청 경계 시나리오 AS-033~AS-036 을 돌린다 (AP-030~033)
- [ ] T042 [P] [US4] `frontend/tests/abnormal/external-failure.test.tsx` — 화면 시나리오 AS-037~AS-039 를 돌린다
- [ ] T043 [US4] `backend/tests/abnormal/test_external_failure.py` — 외부 경계 시나리오 AS-040~AS-042 를 돌린다. 브라우저를 검증 쪽에서 강제로 닫고 기록된 Step 이 남아 저장 가능한지 확인한다 (AP-030)
- [ ] T044 [US4] `SESSION_LOST` 의 분류를 정한다 — 브라우저 상실 원인이 외부인지 제품인지에 따라 `blocked`/`broken` 이 갈린다. 정한 근거를 `specs/003-error-path-hardening/data-model.md §1.3` 에 반영한다. 판단 근거가 사용자에게 드러나야 한다 (AP-033)
- [ ] T045 [US4] 대상 사이트 무응답에 무한정 기다리지 않게 하고, 결과가 대상 쪽 사정임을 가리키게 한다 (AP-031·AS-041). 제품 결함으로 보이면 안 된다
- [ ] T046 [US4] T041~T043 이 낸 실패를 고친다. AI 실패 뒤 이미 만들어진 Step 유지(AP-032)를 특히 확인한다

**Checkpoint**: 외부 환경 실패 시나리오 10건이 3축을 통과한다.

---

## Phase 7: User Story 5 — 같은 것을 두 번 해도 하나만 일어난다 (P2)

**Goal**: 동시 조작과 중단된 쓰기에 대해 판정 3축이 성립한다. 시나리오 AS-043~AS-051.

**Independent Test**: 같은 대상에 동시 요청을 보내 3축과 자산 무결성을 확인한다.

- [ ] T047 [US5] `backend/src/itb/storage/atomic.py` 를 만든다 — `backend/src/itb/storage/registry.py:151-153` 의 임시 파일 + 바꿔치기 방식을 공용 함수로 꺼낸다
- [ ] T048 [US5] `backend/src/itb/storage/yaml_io.py:73` `dump_model()` 이 원자적 쓰기를 지나게 한다. **여기가 Step DSL(테스트 정의)을 쓰는 경로이며 현재 곧바로 덮어쓴다** (AP-042)
- [ ] T049 [P] [US5] `backend/src/itb/secrets/store.py:61` 과 `backend/src/itb/storage/repository.py:320` 도 원자적 쓰기를 지나게 한다
- [ ] T050 [US5] `backend/src/itb/storage/registry.py` 가 새 공용 함수를 쓰게 바꾼다. 같은 방식이 두 곳에 남지 않게 한다
- [ ] T051 [P] [US5] `backend/tests/abnormal/test_atomic_write.py` — 쓰기 도중 실패를 일으켜 조각난 파일이 남지 않고 원본이 그대로인지 확인한다. 대상은 정의 쓰기·비밀 값 쓰기·등록부 쓰기 셋 (AS-049·AS-050)
- [ ] T052 [P] [US5] `backend/tests/abnormal/test_concurrency.py` — 요청 경계 시나리오 AS-043~AS-045 를 돌린다. 동시 요청을 보내 하나만 효과를 내는지 확인한다 (AP-040)
- [ ] T053 [P] [US5] `frontend/tests/abnormal/concurrency.test.tsx` — 화면 시나리오 AS-046~AS-048 을 돌린다. 반영되지 않은 조작이 조용히 무시되지 않는지 확인한다 (AP-041)
- [ ] T054 [US5] `backend/tests/abnormal/test_concurrency.py` — 외부 경계 시나리오 AS-051(두 탭 동시 이벤트)을 돌린다
- [ ] T055 [US5] T051~T054 가 낸 실패를 고친다

**Checkpoint**: 동시성·중복 실행 시나리오 9건이 3축을 통과한다.

---

## Phase 8: User Story 6 — 이번 라운드가 되던 것을 깨지 않는다 (P1)

**Goal**: 001·002 에서 성립시킨 동작이 그대로 성립한다.

**Independent Test**: 001·002 의 기존 자동 검증을 그대로 돌려 통과를 확인한다.

- [ ] T056 [US6] `cd backend && uv run pytest` 전체를 돌려 실패 0건을 확인한다. 실패하면 검증이 아니라 구현을 고친다 (헌법 게이트 4 — 테스트를 지우거나 건너뛰지 않는다) (RG-102·SC-207)
- [ ] T057 [US6] `cd frontend && npm run test -- --run && npm run typecheck` 로 실패 0건을 확인한다
- [ ] T058 [US6] `cd backend && uv run python -m itb.schema.export --check` 와 `cd frontend && npm run gen:types && git diff --exit-code src/types/generated/` 로 스키마 드리프트가 없는지 확인한다 (EC-006)
- [ ] T059 [P] [US6] `backend/tests/abnormal/test_catalogue.py` — 시나리오 목록이 커버리지 규칙을 만족하는지 확인한다. 12개 조합 각 3건 이상, 식별자 중복 없음, 필드 누락 없음 (SC-206)
- [ ] T060 [US6] 재실행 경로에 LLM 호출이 도달하지 않음을 확인한다 — 001 의 기존 가드가 여전히 통과하는지 본다. 이 라운드가 AI 대역을 도입했으므로 검증 코드에만 있고 제품 경로에 없다는 증거를 남긴다 (헌법 원칙 II·게이트 1)

**Checkpoint**: 되던 것이 그대로다.

---

## Phase 9: Polish & 마감

- [ ] T061 [P] `specs/003-error-path-hardening/quickstart.md` 의 10단계를 실제로 돌려 문서와 실제가 어긋나지 않는지 확인한다
- [ ] T062 [P] `README.md` 의 "현재 상태" 표에 003 라운드를 더한다. **릴리스 게이트 RG-1(Playwright Export)이 여전히 미완임을 지운다거나 흐리지 않는다**
- [ ] T063 판정 결과를 집계해 SC-201~SC-209 각각의 충족 여부를 `specs/003-error-path-hardening/` 아래 결과 문서에 기록한다. 미달 항목은 이유와 함께 남긴다
- [ ] T064 이상 조작을 연달아 반복해도 자원이 누적되거나 느려지지 않는지 확인한다 (Edge Case)
- [ ] T065 오류 처리 자체가 실패하는 경우(분류를 붙이는 도중 예외)에 사용자가 무엇을 보게 되는지 확인하고 필요하면 고친다 (Edge Case)

---

## Dependencies

```
T001 (착수 전 확인)
  └─> Phase 1 (T002~T003)
        └─> Phase 2 Foundational (T004~T014)   ← 모든 스토리의 선행 조건
              ├─> Phase 3 US1 (T015~T027)      ← 판정 기준. 나머지의 선행 조건
              │     ├─> Phase 4 US2 (T028~T032)   ┐
              │     ├─> Phase 5 US3 (T033~T038)   │ 서로 독립. 병렬 가능
              │     ├─> Phase 6 US4 (T039~T046)   │
              │     └─> Phase 7 US5 (T047~T055)   ┘
              │           └─> Phase 8 US6 (T056~T060)
              │                 └─> Phase 9 (T061~T065)
```

**핵심 의존**

- **T004~T012 → 나머지 전부**: 오류 계약에 분류가 없으면 어떤 검증도 "정상인가 결함인가"를 판정할 수 없다
- **T013~T014 → 모든 시나리오 검증**: 목록 로더와 판정 헬퍼가 없으면 시나리오를 돌릴 수 없다
- **T022~T023 → 판정축 ② 전부**: 화면 공용 통로가 없으면 "다음 행동이 화면에 있는가"를 볼 수 없다
- **T047 → T048~T051**: 원자적 쓰기 공용 함수가 먼저다
- **US2~US5 → US6**: 회귀 확인은 변경이 다 끝난 뒤에 의미가 있다

**스토리 독립성**: US2~US5 는 서로 독립이다. 하나만 구현해도 그 고장 유형에 대해 판정할 수 있다. US1 은 나머지의 선행 조건이므로 독립이 아니며, 이것이 US1 을 MVP 로 삼는 이유다.

---

## Parallel Execution Examples

**Phase 2 안에서**

```
T014 (프런트 로더) 는 T013 (백엔드 로더) 과 다른 파일이므로 병렬
T010~T011 (스키마 생성) 은 T004~T009 (모델 정의) 뒤에 순차
```

**Phase 3 안에서**

```
T015 · T016 · T017 · T019  → 병렬 (서로 다른 검증, 같은 파일 T015~T017 은 순차)
T022 (ErrorNotice 신설) 은 T020~T021 (백엔드) 과 병렬
```

**Phase 4~7 사이**

```
US2 · US3 · US4 · US5 는 서로 독립 — 네 묶음을 병렬로 진행할 수 있다
단, 각 묶음 안에서 "검증 작성 → 실패 확인 → 수정" 은 순차다
```

**Phase 6 안에서**

```
T039 (고정 앱) · T040 (AI 대역) → 병렬. 둘 다 T041~T043 의 선행 조건
```

---

## Implementation Strategy

### MVP (US1 만)

Phase 1 → 2 → 3 (T001~T027). 여기까지만 해도 **오류가 분류되어 전달되고 화면이 하나의 통로로
보여준다.** 판정 기준이 서므로 이후 시나리오를 언제든 이어서 돌릴 수 있다.

### 증분 전달

| 증분 | 범위 | 얻는 것 |
|---|---|---|
| 1 | Phase 1~3 (US1) | 오류 분류·다음 행동·공용 통로. 판정 기준 확립 |
| 2 | Phase 4~5 (US2·US3) | 가장 흔한 두 고장 유형 32건 판정 |
| 3 | Phase 6~7 (US4·US5) | 외부 실패·동시성 19건 판정. 저장 원자성 |
| 4 | Phase 8~9 (US6·마감) | 회귀 확인과 결과 집계 |

### 완료 판정

`SC-201`(시나리오 전건 3축 통과)이 이 라운드의 완료 조건이다. 51건 중 하나라도 미판정·불일치면
완료가 아니다. 실패가 결함이면 고치고, 시나리오 정의가 틀린 것이면 목록을 고친다.

---

## 이 라운드에서 다루지 않는 것 (명세의 Scope 재확인)

- 저장소·파일 계층 고장 (자산 파일 손상, 키 파일 손상, 디스크 가득참, 권한 없음)
- 사람이 따라 하는 수동 검증 시나리오서
- 대상 애플리케이션의 에러를 분류해 주는 제품 기능
- 001 의 미완 항목 T155(수동 측정)·T156(리뷰어 검토), 002 의 미완 항목 T099(디자인 준수 판정)
- 릴리스 게이트 RG-1 (Playwright Export) — **출하 전 필수이며 여전히 미완이다**
