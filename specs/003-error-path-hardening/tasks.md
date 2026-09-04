---

description: "Task list for 003 이상 경로 견고성 (비정상 조작 결함 라운드)"
---

# Tasks: 이상 경로 견고성 (비정상 조작 결함 라운드)

**Input**: Design documents from `/specs/003-error-path-hardening/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: 이 라운드의 산출물 자체가 검증이다 (헌법 게이트 3).

## 이 목록이 시나리오 51건을 작업으로 쪼개지 않는 이유

시나리오마다 "돌린다 / 고친다" 작업을 만들면 목록이 같은 모양으로 반복되고, 작업이 늘어도
정보는 늘지 않는다. 대신 **면(surface)마다 실행기 하나**를 두고 목록
(`contracts/abnormal-scenarios.json`)을 읽어 시나리오를 자동으로 펼친다 (research R8).

- 시나리오 하나 = 등록된 **실행 수단(driver)** 하나. 식별자(`AS-NNN`)로 등록한다
- **등록되지 않은 시나리오는 건너뛰기가 아니라 실패다** (RG-106). 조용히 건너뛰면 "전건 통과"(SC-201)가 거짓이 된다
- 작업 목록에는 "장치를 만든다"와 "드러난 결함을 고친다"만 남는다

시나리오가 51건에서 더 늘어도 이 목록의 작업 수는 늘지 않는다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리에 속하는가 (US1~US6)

## 면별 시나리오 수

| 면 | 시나리오 | 실행 수단이 있어야 할 곳 |
|---|---|---|
| `api` 요청 경계 | 19건 | `backend/tests/abnormal/drivers/api_drivers.py` |
| `ui` 화면 | 18건 | `backend/tests/abnormal/drivers/ui_drivers.py` (**실브라우저**) |
| `boundary` 외부 경계 | 14건 | `backend/tests/abnormal/drivers/boundary_drivers.py` |

---

## Phase 1: 오류 계약 (US1 기반) — 완료

커밋 `9023506`. 백엔드 965건·프런트 135건 통과, typecheck 통과로 회귀 없음을 확인했다.

- [X] T001 `backend/tests/abnormal/` 와 `frontend/tests/abnormal/` 를 만들고 `backend/tests/abnormal/README.md` 에 규칙(목록은 한 곳, 판정은 3축, 실패 주입은 검증 코드에만)을 적는다
- [X] T002 `backend/src/itb/domain/error.py` 신설 — `Category`(blocked/broken) · `ErrorCode`(기존 22개 유지 + `INTERNAL_ERROR`) · `CATEGORY` 전수 대응표 · `NEXT_ACTION` 기본 문구 (EC-001·EC-003·EC-004)
- [X] T003 `ErrorBody` 에 `category`·`next_action` 을 더하고, `category` 는 `code` 에서 대응표로 **자동 결정**해 호출부가 정하지 못하게 한다 (EC-002)
- [X] T004 `backend/src/itb/api/errors.py` 를 FastAPI 결합부만 남기고 도메인 모델을 재수출한다. 상태 코드별 생성자에 키워드 전용 `next_action` 을 더한다. 기존 임포트 경로 유지 (RG-102)
- [X] T005 `backend/src/itb/schema/export.py` 에 `error-response` 추가 → `backend/schema/error-response.schema.json` → `frontend/src/types/generated/error-response.d.ts` 생성. `frontend/src/api/client.ts` 의 손으로 쓴 `ErrorCode` union 을 지우고 `ApiError` 에 `category`·`nextAction` 을 싣는다 (EC-006)
- [X] T006 `backend/src/itb/api/app.py` 의 처리되지 않은 오류 처리기가 `INTERNAL_ERROR`·`broken` 을 내고 서버 로그에 남기게 한다. 응답에 스택·경로를 싣지 않는다 (EC-003·EC-005)
- [X] T007 `backend/tests/contract/test_project_and_tests_api.py` 의 오류 형태 단언을 새 계약으로 갱신한다 — 필드 집합에 더해 `category` 값과 `next_action` 이 비지 않았는지까지 확인해 **강화**한다 (헌법 게이트 4)

---

## Phase 2: 검증 장치 (모든 시나리오의 선행 조건)

**이 단계가 없으면 시나리오를 한 건도 돌릴 수 없다.**

- [ ] T008 [US1] `backend/tests/abnormal/catalogue.py` — `specs/003-error-path-hardening/contracts/abnormal-scenarios.json` 로더, 판정 3축 헬퍼(`assert_axis1/2/3`), 그리고 식별자로 실행 수단을 등록하는 레지스트리(`@driver("AS-001")`)를 만든다. 실패 메시지에 시나리오 식별자와 **어긋난 축**을 싣는다
- [ ] T009 [US1] `backend/tests/abnormal/test_catalogue.py` — ① 12개 조합이 각 3건 이상, 식별자 중복 없음, 필드 누락 없음 (SC-206) ② **목록의 모든 시나리오에 실행 수단이 등록되어 있는지** 확인한다. 등록되지 않은 항목은 실패다 (RG-106·SC-211)
- [ ] T010 [P] [US4] `backend/tests/abnormal/fakes.py` — AI 클라이언트 대역(오류를 던지는 것 · 형식이 깨진 응답 · 시간을 끄는 것). `itb.llm.client.create_client` 를 대체한다. **제품에 실패 주입 스위치를 넣지 않는다** (헌법 원칙 II)
- [ ] T011 [P] [US4] `fixtures/sample-app/` 에 지연·무응답·오류를 내는 경로를 더한다. 제품 코드가 아니다
- [ ] T012 [US3] `backend/tests/abnormal/product_ui.py` — **제품 UI 를 실제로 띄우는 세션 범위 픽스처** (RG-105). 격리된 작업 디렉터리로 제품 서버를 띄우고, 제품 화면을 띄우고(기존 개발 서버 설정이 이미 `/api`·`/ws` 를 넘긴다), 둘 다 응답할 때까지 기다린 뒤 주소를 넘긴다. 도구·포트가 없으면 **건너뛰지 않고 실패**로 알린다 (RG-106)

**Checkpoint**: 시나리오를 목록에서 읽어 세 면 모두에서 돌릴 수 있다.

---

## Phase 3: 훑는 검증 (RG-104) — 여기서 나오는 실패가 결함 목록이다

- [ ] T013 [P] [US1] `backend/tests/abnormal/test_error_contract.py` — ① 모든 `ErrorCode` 가 `CATEGORY`·`NEXT_ACTION` 에 있다 (RG-104-1) ② 처리되지 않은 오류가 정상 거부와 **코드만으로** 구별된다 (EC-003) ③ 오류 어디에도 내부 경로·스택·비밀 값이 없다 (EC-005·SC-209)
- [ ] T014 [US1] `backend/tests/abnormal/test_route_sweep.py` — 앱에 등록된 **모든** 요청 경로를 열거해 각각 거부를 유발하고, 응답이 오류 스키마를 만족하며 `category`·`next_action` 을 담는지 확인한다. 거부 유발 방법이 등록되지 않은 새 경로는 실패로 취급한다 (RG-104-2)
- [ ] T015 [P] [US1] `backend/tests/abnormal/test_no_bypass.py` — `backend/src/itb/api/` 를 훑어 오류 계약을 우회해 응답을 만드는 곳이 `api/errors.py` 밖에 없는지 확인한다 (RG-104-3)

---

## Phase 4: 화면 공용 오류 통로 (판정축 ②의 전제)

- [ ] T016 [US1] `frontend/src/components/ErrorNotice.tsx` — 오류 표시의 **공용 통로**. `message` 와 `next_action` 을 **함께** 보여주고, `broken` 을 사용자가 고칠 수 있는 것처럼 보이지 않게 한다. 계약 형태가 아닌 응답(연결 실패)도 같은 통로로 표시한다
- [ ] T017 [US1] `frontend/src/pages/` 14개 화면이 오류를 `ErrorNotice` 로 표시하게 고친다. 화면이 `err.message` 를 직접 그리지 않는다
- [ ] T018 [P] [US1] `frontend/tests/abnormal/error-notice.test.tsx` — 공용 통로가 두 필드를 함께 보여주는지, `broken`/`blocked` 를 구분하는지, 그리고 **각 화면이 공용 통로를 지나는지** 훑어 확인한다 (RG-104-4)
- [ ] T019 [US1] `backend/src/itb/api/ws/session_events.py` 가 실시간 통로로 보내는 오류에 같은 `ErrorBody` 를 싣게 한다 (EC-008)
- [ ] T020 [P] [US1] `specs/001-interactive-ai-test-builder/contracts/rest-api.md` 의 오류 응답 공통 형태를 새 필드 둘을 포함하도록 갱신하고 `contracts/error-contract.md` 를 참조로 건다

---

## Phase 5: 면별 실행 수단 — 시나리오 51건을 펼친다

각 작업은 **실행기 하나 + 그 면의 수단 전부**다. 시나리오마다 작업을 만들지 않는다.

- [ ] T021 [US2] [US3] [US5] `backend/tests/abnormal/drivers/api_drivers.py` 와 `test_api_surface.py` — 요청 경계 **19건**(AS-001~006·018~023·033~036·043~045)의 수단을 등록하고, 실행기가 목록을 읽어 판정 3축으로 펼친다
- [ ] T022 [US4] [US5] `backend/tests/abnormal/drivers/boundary_drivers.py` 와 `test_boundary_surface.py` — 외부 경계 **14건**(AS-013~017·030~032·040~042·049~051)의 수단을 등록한다. T010·T011 의 대역을 쓴다
- [ ] T023 [US2] [US3] [US4] [US5] `backend/tests/abnormal/drivers/ui_drivers.py` 와 `test_ui_surface.py` — 화면 **18건**(AS-007~012·024~029·037~039·046~048)의 수단을 등록한다. **T012 의 실브라우저 픽스처로 제품 화면을 실제로 조작한다.** 버튼 연타가 요청을 몇 번 내보내는지, 화면을 벗어났다 돌아오면 무엇이 보이는지, 두 창에서 조작하면 어떻게 되는지는 여기서만 판정된다 (RG-105)

**Checkpoint**: 51건 전부가 판정된다. 통과하지 못한 것이 이 라운드의 결함 목록이다.

---

## Phase 6: 드러난 결함 수정

- [ ] T024 [US5] `backend/src/itb/storage/atomic.py` 를 만들어 `registry.py:151-153` 의 임시 파일 + 바꿔치기 방식을 꺼내고, `yaml_io.py` `dump_model()`(**Step DSL 을 쓰는 경로이며 현재 곧바로 덮어쓴다**) · `secrets/store.py` · `repository.py` · `registry.py` 가 모두 그것을 지나게 한다 (AP-042·AS-049·AS-050)
- [ ] T025 [US3] `backend/src/itb/api/routes/sessions.py` 의 상태 위반 거부가 `execution/state_machine.py` 의 `allowed_commands(state)` 를 `detail` 에 실어 "지금 무엇이 가능한지"를 알리게 한다. 상태 기계 자체는 바꾸지 않는다 (AP-020)
- [ ] T026 [US2] [US3] T021 이 낸 요청 경계 실패를 고친다 — 경계 검증 누락, 경로 탈출·중복 이름 미거부(AP-013·014), 거부 메시지가 원본 입력을 되돌려 화면을 훼손하는 것(AP-015), 거부가 세션을 못 쓰게 만드는 것(AP-024)
- [ ] T027 [US2] [US3] [US5] T023 이 낸 화면 실패를 고친다 — 연타로 요청이 두 번 나가는 것(AP-022), 화면 복귀 시 옛 상태로 멈춘 것(AP-023·AS-026), 반영되지 않은 조작이 조용히 무시되는 것(AP-041)
- [ ] T028 [US4] T022 가 낸 외부 경계 실패를 고친다 — 대상 무응답에 무한정 기다리는 것(AP-031), AI 실패 뒤 만들어진 Step 유실(AP-032), 브라우저 상실 뒤 저장 불가(AP-030). `SESSION_LOST` 의 분류가 실제 동작과 맞는지 확인하고 근거를 `data-model.md §1.3` 에 반영한다 (AP-033)

---

## Phase 7: 회귀와 마감

- [ ] T029 [US6] 전체 회귀 — `cd backend && uv run python -m pytest` 와 `cd frontend && npm run test -- --run && npm run typecheck` 가 실패 0건. 실패하면 검증이 아니라 구현을 고친다 (헌법 게이트 4·RG-102·SC-207)
- [ ] T030 [US6] 스키마 드리프트 확인 — `uv run python -m itb.schema.export --check` 와 `npm run gen:types && git diff --exit-code src/types/generated/` (EC-006)
- [ ] T031 [US6] 재실행 경로에 LLM 호출이 도달하지 않음을 확인한다. 이 라운드가 AI 대역을 도입했으므로 그것이 **검증 코드에만** 있다는 증거를 남긴다 (헌법 원칙 II·게이트 1)
- [ ] T032 판정 결과를 집계해 `SC-201`~`SC-211` 각각의 충족 여부를 `specs/003-error-path-hardening/` 아래 결과 문서에 기록한다. 미달 항목은 이유와 함께 남긴다
- [ ] T033 [P] `quickstart.md` 의 10단계를 실제로 돌려 문서와 실제가 어긋나지 않는지 확인하고, `README.md` 의 "현재 상태" 표에 003 을 더한다. **릴리스 게이트 RG-1(Playwright Export)이 여전히 미완임을 흐리지 않는다**
- [ ] T034 Edge Case 둘을 확인한다 — 이상 조작을 연달아 반복해도 자원이 누적되지 않는가, 오류 처리 자체가 실패하면 사용자가 무엇을 보는가

---

## Dependencies

```
Phase 1 오류 계약 [완료]
  └─> Phase 2 검증 장치 (T008~T012)        ← 시나리오를 한 건도 못 돌린다
        ├─> Phase 3 훑는 검증 (T013~T015)   ┐ 병렬 가능
        ├─> Phase 4 화면 통로 (T016~T020)   ┘
        │     └─> T023 (화면 면은 공용 통로가 있어야 판정축 ②가 성립한다)
        └─> Phase 5 면별 수단 (T021~T023)
              └─> Phase 6 결함 수정 (T024~T028)
                    └─> Phase 7 회귀·마감 (T029~T034)
```

**핵심 의존**

- **T008 → 나머지 전부.** 로더·판정 헬퍼·레지스트리가 없으면 시나리오를 펼칠 수 없다
- **T012 → T023.** 실브라우저 픽스처가 없으면 화면 18건은 판정할 수 없다 (지금까지 이 저장소에 그런 검증이 없었다)
- **T016·T017 → T023.** 공용 통로가 없으면 "다음 행동이 화면에 있는가"를 볼 수 없다
- **T021~T023 → T026~T028.** 무엇을 고칠지는 실행기가 알려준다. 미리 짐작해 고치지 않는다

**스토리 독립성**: 면별 실행기 셋(T021·T022·T023)은 서로 독립이다. 하나만 만들어도 그 면에
대해서는 51건 중 해당 몫이 판정된다.

---

## Implementation Strategy

### MVP

Phase 1(완료) + Phase 2 + Phase 3. 여기까지면 **오류가 분류되어 전달되고, 모든 경로가 규약을
지키는지 자동으로 훑어진다.** 시나리오 실행 수단이 없어도 규약 위반은 드러난다.

### 증분 전달

| 증분 | 범위 | 얻는 것 |
|---|---|---|
| 1 | Phase 1~3 | 오류 분류 + 전 경로 규약 준수 자동 점검 |
| 2 | Phase 4 + T021 | 화면 공용 통로 + 요청 경계 19건 판정 |
| 3 | T012 + T023 | **제품 UI 실브라우저 계층** + 화면 18건 판정 |
| 4 | T022 + Phase 6~7 | 외부 경계 14건 + 결함 수정 + 회귀 |

증분 3 이 이 라운드에서 가장 값이 크다 — 이 저장소가 한 번도 갖지 못한 검증 계층이고,
앞으로 모든 화면 변경이 그 보호를 받는다.

### 완료 판정

`SC-201`(51건 전부 3축 통과) 과 `SC-211`(수단 없이 건너뛴 건수 0) 이 완료 조건이다.
실패가 결함이면 고치고, 시나리오 정의가 틀린 것이면 목록을 고친다.

---

## 이 라운드에서 다루지 않는 것

- 저장소·파일 계층 고장 (자산 파일 손상, 키 파일 손상, 디스크 가득참, 권한 없음)
- 사람이 따라 하는 수동 검증 시나리오서 — 화면 면도 사람이 아니라 실브라우저가 판정한다
- 대상 애플리케이션의 에러를 분류해 주는 제품 기능
- 001 의 미완 항목 T155·T156, 002 의 미완 항목 T099
- 릴리스 게이트 RG-1 (Playwright Export) — **출하 전 필수이며 여전히 미완이다**
