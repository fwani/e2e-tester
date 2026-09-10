---

description: "013 테스트 복수 삭제와 그룹 — 실행 작업 목록"
---

# Tasks: 테스트 목록의 복수 삭제와 테스트 그룹

**Input**: Design documents from `specs/013-test-groups-bulk-delete/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) ·
[data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md)

**Tests**: 포함한다. 이 기능은 **식별자 형식을 바꾸고 사용자 자산을 옮긴다** — 이 저장소에서
지금까지 한 변경 중 가장 넓은 종류다. 되돌릴 수 없는 실패 모드를 다루므로 실패 경로 검사가
특히 중요하다.

**Organization**: 사용자 이야기별로 묶는다. US1(복수 삭제)만 구현해도 독립적으로 쓸 수 있다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: US1 = 복수 삭제 · US2 = 그룹 · US3 = 그룹 정리

## Path Conventions

Web app 구조. 백엔드 `backend/src/itb/`, 프런트엔드 `frontend/src/`.

---

## Phase 1: Setup (기준선 고정)

**Purpose**: 새 의존성·새 패키지가 없으므로 초기화 작업이 없다. **012 이전이 초록인지**만
고정한다 — 이 기능은 기존 자산 호환이 핵심이라 기준선이 없으면 무엇이 깨졌는지 못 가린다.

- [X] T001 기준선 검증을 돌려 기록한다 — `cd backend && uv run ruff check src/ tests/ && uv run lint-imports && uv run python -m itb.schema.export --check && uv run pytest -m "not browser" -q`, `cd frontend && npx tsc --noEmit && npx vitest run`. **미리 알려진 것**: `pytest` 에 pytest-asyncio 설정 오류 15건이 012 이전부터 있다. 개수가 늘면 013 이 깬 것이다
- [X] T002 **013 이전 상태로 프로젝트 하나를 만들어 둔다** — 테스트 2~3개를 저장하고 한 번 실행해 결과를 남긴다. [quickstart.md](quickstart.md) §2 이야기 1(기존 자산이 그대로다 · SC-629)의 재료이며, 나중에 만들면 이미 새 코드로 만든 것이라 검증이 성립하지 않는다

---

## Phase 2: Foundational (모든 이야기의 공통 전제)

**Purpose**: 식별자 형식 확장과 오류 계약. **이 단계가 이 기능에서 가장 위험하다** — 도메인
모델·저장소·라우트·화면·기존 자산에 모두 걸친다.

**⚠️ 반드시 먼저 끝나야 한다**

### 식별자 형식 (research R1)

- [X] T003 `backend/src/itb/domain/test_case.py` 의 `TEST_ID_PATTERN` 을 `^[A-Z][A-Z0-9]{0,7}-\d{3}$` 로 넓힌다 — **대문자 ASCII 만.** 식별자가 파일·디렉터리 이름이 되고 macOS 기본 파일 시스템은 대소문자를 구별하지 않아, 두 대소문자를 허용하면 한 자리를 두 식별자가 다툰다. `TC-001` 이 이 패턴을 만족하는지 확인한다
- [X] T004 `backend/src/itb/domain/test_case.py` 에 `GROUP_PREFIX_PATTERN = ^[A-Z][A-Z0-9]{0,7}$` 과 `RESERVED_PREFIX = "TC"` 를 더한다 ([data-model.md](data-model.md) §2)
- [X] T005 `backend/src/itb/storage/repository.py` 의 `TEST_ID_RE` 를 T003 과 **같은 패턴 하나에서** 오게 한다 — 두 벌로 두면 한쪽이 갈리고, 갈린 자리가 「저장은 되는데 못 읽는」 상태가 된다. `run_dir`·`find_test_path` 의 검증은 **없애지 않는다** (헌법 §보안)
- [X] T006 `backend/src/itb/storage/repository.py` 의 `list_test_paths()` 가 `glob("TC-*.yaml")` 이 아니라 **모든 접두어**를 찾게 한다 — [research.md](research.md) R1 이 「가장 조용한 함정」으로 표시한 곳이다. 넓히지 않으면 새 접두어 테스트가 저장은 되는데 목록에 아예 안 나온다. 테스트 파일이 아닌 `.yaml` 을 집지 않도록 이름을 식별자 정규식으로 거른다
- [X] T007 `backend/src/itb/storage/repository.py` 의 `allocate_test_id()` 가 **접두어를 무시하고 번호만** 세게 한다 ([research.md](research.md) R3) — `USER-003` 이 있으면 `003` 은 쓰이지 않는다. 번호가 프로젝트 전체에서 고유해야 그룹 이동이 번호를 다시 뽑지 않는다. 카운터와 파일을 함께 보는 기존 방식은 유지한다. 접두어 인자를 받아 `<접두어>-<번호>` 를 돌려준다
- [X] T008 [P] `backend/tests/unit/test_repository.py` 를 개정한다 — 새 접두어 테스트가 `list_test_paths` 에 잡히는지, `allocate_test_id` 가 접두어를 넘어 번호를 건너뛰는지, `run_dir`·`find_test_path` 가 잘못된 식별자를 여전히 거절하는지
- [X] T009 [P] `backend/tests/unit/test_domain_invariants.py` 를 개정한다 — `TC-001` 과 `USER-001` 이 통과하고, 소문자·경로 구분자·9자 접두어·상위 이동이 거절되는지 (허용 목록 방식임을 검사로 고정)
- [X] T010 **기존 자산 호환을 여기서 한 번 확인한다** — T002 에서 만든 프로젝트를 열어 목록·조회·실행·결과가 전부 되는지 본다 (SC-629). Phase 2 를 벗어난 뒤에 깨진 것을 발견하면 원인이 어디인지 넓어진다

### 오류 계약

- [X] T011 [P] `backend/src/itb/domain/error.py` 에 `ErrorCode` 7개를 더한다 — `TEST_IN_USE`·`TEST_DELETE_FAILED`·`TEST_DELETE_PARTIAL`·`TEST_MOVE_FAILED`·`GROUP_NOT_FOUND`·`GROUP_ALREADY_EXISTS`·`GROUP_PREFIX_RESERVED`. **전부 `BLOCKED` 다** — 이 저장소에서 `BROKEN` 은 `INTERNAL_ERROR` 하나뿐이고 `tests/abnormal/test_error_contract.py` 가 그것을 센다 (012 에서 같은 실수를 했다). `CATEGORY`·`NEXT_ACTION` **양쪽**에 넣는다 ([contracts/api-contract.md](contracts/api-contract.md) §6)
- [X] T012 `cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types` 로 생성물을 갱신하고 커밋 대상에 넣는다. **백엔드가 먼저다** — 012 에서 순서를 틀려 한 번 헛돌았다. T011·T017 뒤에 한 번에 한다

### 공통 순서 규약 (research R4·R5)

- [X] T013 `backend/src/itb/storage/test_moves.py` 를 만든다 — **전부 검증 → 하나씩 실행 → 실패 시 되돌림** 세 걸음을 한 곳에 둔다. 삭제와 그룹 이동이 **같은 규약을 공유하므로** 라우트에 두면 두 벌이 되고 한쪽만 고치면 다른 쪽에서 되돌림이 빠진다 ([plan.md](plan.md) Structure Decision). 되돌리기까지 실패한 경우를 **삼키지 않고** 호출자에게 구별해 알린다
- [X] T014 [P] `backend/tests/unit/test_test_moves.py` 를 만든다 — 검증에서 걸리면 아무것도 건드리지 않는지, 중간 실패 시 이미 옮긴 것이 되돌려지는지, 되돌리기 실패가 다른 결과로 구별되는지

**Checkpoint**: Foundation 완료. 기존 자산이 그대로 돌고, US1·US2 를 병렬로 진행할 수 있다.

---

## Phase 3: User Story 1 — 여러 테스트를 한 번에 고르고 지운다 (Priority: P1) 🎯 MVP

**Goal**: 체크로 고른 테스트들을 확인 한 번으로 휴지통에 보낸다. 전부 되거나 전부 안 된다.

**Independent Test**: 테스트 5개 중 3개를 골라 지운다. 확인이 한 번인지, 나머지 2개가
그대로인지, 휴지통에 정의가 온전한지 확인한다 ([quickstart.md](quickstart.md) §2 이야기 2·3·4).

### 백엔드 — 휴지통

- [X] T015 [P] [US1] `backend/src/itb/storage/trash.py` 에 `move_test_to_trash(repo, test_id)` 를 더한다 — `<trash_dir>/<시각>-<ID>-<이름>/` 안에 정의 `.yaml` 을 **원래 파일명 그대로** 두고 산출물을 `runs/` 로 옮긴다 ([data-model.md](data-model.md) §4). 원래 파일명을 유지하는 것이 요점이다: 되돌리기가 「이 `.yaml` 을 `tests/` 로 옮긴다」 한 걸음이 된다. 자리 잡기는 기존 `allocate_trash_path` 를 쓴다
- [X] T016 [P] [US1] `backend/src/itb/storage/trash.py` 에 `restore_test(entry, repo)` 를 더한다 — **되돌림에 필요하다** (T013 의 3번 걸음). 사용자용 복구 조작이 아니라 실패 롤백용이다
- [X] T017 [P] [US1] `backend/tests/unit/test_trash.py` 를 개정한다 — 테스트 항목이 정의와 산출물을 함께 담는지, 원래 파일명이 유지되는지, 같은 테스트를 두 번 지워도 덮어쓰지 않는지(FR-437c), `restore_test` 가 원래 자리로 정확히 되돌리는지

### 백엔드 — 라우트

- [X] T018 [US1] `backend/src/itb/api/routes/tests.py` 의 `DELETE /{test_id}` 를 **휴지통 이동**으로 바꾸고 응답을 204 → 200 `{id, name, trashed_to}` 로 한다 ([contracts/api-contract.md](contracts/api-contract.md) §2). **204 를 버리는 것이 이 계약의 핵심 변경이다** — 옮겨진 위치를 돌려주지 않으면 되돌릴 수 없고, 그러면 「파괴하지 않는다」가 사용자에게는 삭제와 구별되지 않는다. 실행 중이면 409 `TEST_IN_USE`. T015 에 의존
- [X] T019 [US1] `backend/src/itb/api/routes/tests.py` 에 `POST /api/tests:delete` 를 더한다 — 요청 `{test_ids}`, 응답 `{deleted: [{id, name, trashed_to}]}`. T013 의 규약을 쓴다. 실패는 `TEST_DELETE_FAILED`(되돌렸다) 와 `TEST_DELETE_PARTIAL`(되돌리지도 못했다)로 **구별해서** 답한다 (api-contract §3). T013·T015 에 의존
- [X] T020 [P] [US1] `backend/tests/contract/test_tests_bulk_delete_api.py` 를 만든다 — 셋을 지우면 셋만 사라지는지, `trashed_to` 자리에 정의가 온전한지(SC-631), 한 줄 삭제와 복수 삭제의 **결과가 같은지**(SC-632), 이미 없는 식별자가 섞였을 때(FR-436)
- [X] T021 [P] [US1] `backend/tests/contract/test_tests_bulk_delete_api.py` 에 실패 경로를 더한다 — 하나가 실행 중이면 **하나도 지워지지 않고** 409 이며 **세션이 살아 있는지**(FR-432·FR-433·SC-624·SC-630), 옮기다 실패하면 전부 원래 자리인지, 되돌리기 실패가 `TEST_DELETE_PARTIAL` 로 구별되는지

### 프런트엔드

- [X] T022 [P] [US1] `frontend/src/api/client.ts` 에 `tests.deleteMany(ids)` 를 더하고 `tests.remove` 의 반환 타입을 바꾼다(204 → 본문 있음). 기존 호출부를 함께 고친다
- [X] T023 [P] [US1] `frontend/src/lib/wording.ts` 에 테스트용 복수 삭제 문구를 더한다 — 개수와 **이름**을 함께 말한다. `deleteManyConfirm(indices)` 는 **쓰지 않는다**: 그것은 Step 번호의 범위를 말하는데 테스트는 순서 없는 집합이라 「범위」가 성립하지 않는다 ([research.md](research.md) R7). 「지울 테스트를 먼저 고르세요」를 기존 `NO_DELETE_SELECTION` 옆에 나란히 둔다
- [X] T024 [US1] `frontend/src/pages/TestList.tsx` 의 행에 **체크 칸**을 더한다 — 행 누름(열기)과 **갈라 둔다** (UC-013-01). 011 이 Step 목록에서 정한 규칙이다
- [X] T025 [US1] `frontend/src/pages/TestList.tsx` 에 **선택 띠**를 더한다 — 고른 것이 0개면 **그리지 않는다** (UC-013-02 · SC-627). 「N개 선택됨」, 「보이는 것 전부 선택」/「선택 해제」, 「선택한 항목 삭제」
- [X] T026 [US1] **걸러 보기가 바뀌면 선택도 따라가게** 한다 (FR-429 · UC-013-03) — 화면에서 사라진 행은 선택에서 빠지고 개수 표시가 즉시 반영한다. 「전체 선택」의 대상도 **보이는 것**뿐이다 (FR-428 · SC-625)
- [X] T027 [P] [US1] `frontend/src/components/TestBulkConfirm.tsx` 를 만든다 — 목록 바로 아래 확인 띠. 개수와 이름, 「휴지통으로 옮깁니다 · 되돌릴 수 있습니다」, 「지우기」/「돌아가기」(포커스는 돌아가기) (UC-013-04). `BulkDeleteConfirm` 을 재사용하지 않는 근거는 research R7 에 있다
- [X] T028 [US1] 완료 표시를 더한다 — 옮겨진 자리들을 `mono` 로 남기고 되돌리는 방법 한 줄. **자동으로 사라지지 않는다** (UC-013-05). 여러 개면 접었다 펼 수 있게 하되 **기본은 펼친 상태**다 — 접어 두면 되돌리는 방법을 못 본 채 닫는다
- [X] T029 [US1] 거절·실패 사유를 표시한다 (UC-013-07) — 409 는 사유와 다음 행동, 500 `TEST_DELETE_FAILED` 는 **「전부 원래 자리에 있습니다」**, `TEST_DELETE_PARTIAL` 은 어느 것이 어디 있는지. **거절 뒤 선택을 비우지 않는다**. 기존 `ErrorNotice` 를 쓴다
- [X] T030 [P] [US1] `frontend/tests/TestListSelection.test.tsx` 를 만든다 — 0개면 띠가 없는지, 확인 전 요청 0건인지, 걸러 보기가 선택을 줄이는지(SC-625), 「전체 선택」이 보이는 것만 고르는지, 409 뒤 선택이 남는지, 500 문구에 「원래 자리」가 있는지

**Checkpoint**: US1 단독 배포 가능. 그룹 없이도 가치가 있다.

---

## Phase 4: User Story 2 — 테스트를 그룹으로 묶어 본다 (Priority: P1)

**Goal**: 그룹을 만들고, 목록이 그룹별로 묶여 보이고, 한 그룹만 골라 본다.

**Independent Test**: 그룹 둘을 만들고 테스트를 나눠 넣은 뒤, 묶여 보이는지·걸러지는지·그룹
없는 테스트가 남는지 확인한다 ([quickstart.md](quickstart.md) §2 이야기 5).

### 백엔드 — 모델과 그룹 라우트

- [X] T031 [P] [US2] `backend/src/itb/domain/test_case.py` 에 `TestGroup{prefix, name}` 과 `Project.groups: list[TestGroup] = []` 를 더한다 — **기본값이 빈 목록이어야 기존 프로젝트 파일이 그대로 읽힌다** ([data-model.md](data-model.md) §2). T004 의 패턴을 쓴다
- [X] T032 [US2] `backend/src/itb/api/routes/groups.py` 를 만든다 — `GET`·`POST`·`PATCH /{prefix}`·`DELETE /{prefix}` ([contracts/api-contract.md](contracts/api-contract.md) §5). `tests.py` 에 넣지 않는 이유는 [plan.md](plan.md) Structure Decision 에 있다: 그룹은 테스트가 아니라 **프로젝트 설정**이다. `app.py` 에 라우터를 등록한다. T031 에 의존
- [X] T033 [US2] T032 의 검증을 붙인다 — 접두어 형식(422), `TC` 예약(409 `GROUP_PREFIX_RESERVED`), 접두어·이름 중복(409 `GROUP_ALREADY_EXISTS`), 없는 그룹(404). `GET /api/groups` 는 **테스트가 없는 그룹도 싣는다** — 그룹을 고르는 자리에서는 비어 있는 그룹도 골라야 한다
- [X] T034 [P] [US2] `backend/tests/contract/test_test_groups_api.py` 를 만든다 — 만들기·이름 변경·조회, `TC` 거절, 중복 거절, 빈 그룹도 `GET /api/groups` 에 실리는지

### 백엔드 — 목록

- [X] T035 [US2] `backend/src/itb/api/routes/tests.py` 의 `GET /api/tests` 에 `group` 질의와 `groups` 응답 필드를 더한다 ([contracts/api-contract.md](contracts/api-contract.md) §1). `q` 와 **함께** 적용된다(FR-441). `groups[].count` 는 **걸러 보기 전** 개수다 — 걸러 본 상태에서도 다른 그룹으로 갈 수 있어야 한다. 테스트가 없는 그룹은 **싣지 않는다**(FR-450). **기존 필드는 하나도 바꾸지 않는다**
- [X] T036 [US2] 응답 행에 `group_prefix` 를 더한다 — **식별자에서 유도한다.** 저장된 필드가 아니다 ([data-model.md](data-model.md) §3): 소속을 별도 필드로도 저장하면 접두어와 어긋날 수 있고 어느 쪽이 맞는지 정할 근거가 없다
- [X] T037 [US2] **그룹 정의가 없는 접두어**를 목록이 막지 않게 한다 — 접두어를 이름 삼아 보여주고 정의가 없다는 사실을 함께 싣는다 (data-model §3). 「목록을 그리는 일이 파일 하나 때문에 통째로 실패하면 안 된다」는 기존 규칙과 같다
- [X] T038 [US2] 테스트를 새로 만들 때 그룹을 지정할 수 있게 한다 (FR-443) — 지정하지 않으면 `TC-###` 다 (FR-445b · SC-627). `allocate_test_id` 에 접두어를 넘긴다. T007 에 의존
- [X] T039 [P] [US2] `backend/tests/contract/test_project_and_tests_api.py` 를 개정한다 — 목록 응답에 `groups` 가 늘었고, `group` 질의가 `q` 와 함께 걸리는지, 기존 필드가 그대로인지

### 프런트엔드

- [X] T040 [P] [US2] `frontend/src/api/client.ts` 에 `groups.{list,create,rename,remove}` 와 `tests.list` 의 `group` 질의를 더한다
- [X] T041 [US2] `frontend/src/pages/TestList.tsx` 에 **그룹 띠**를 더한다 — 「전체」 + 그룹 칩(이름 + 개수). **그룹이 하나도 없으면 그리지 않는다** (UC-013-06 · SC-627)
- [X] T042 [US2] 목록을 **그룹별 소제목**으로 묶는다 (FR-440). 「그룹 없음」은 마지막에 오고, 그룹 없는 테스트가 없으면 그리지 않는다
- [X] T043 [US2] 그룹 만들기를 더한다 (UC-013-08) — 이름과 접두어 **두 칸**. 접두어 칸이 왜 필요한지 한 줄로 말한다: 「테스트 식별자에 들어갑니다 (예: `USER-001`)」
- [X] T044 [P] [US2] `frontend/tests/TestGroups.test.tsx` 를 만든다 — 그룹 0개면 띠가 없는지(SC-627), 묶여 보이는지, 칩이 걸러 보는지, 검색과 함께 걸리는지, 그룹 없는 테스트가 남는지

**Checkpoint**: US1 + US2 로 명세의 P1 이 모두 선다.

---

## Phase 5: User Story 3 — 그룹을 바꾸고 그룹을 정리한다 (Priority: P2)

**Goal**: 테스트를 그룹 사이로 옮기고 그룹을 없앤다. 옮겨도 결과가 따라온다.

**Independent Test**: 결과가 있는 테스트를 다른 그룹으로 옮기고 결과가 그대로인지, 그룹을
없애도 테스트가 남는지 확인한다 ([quickstart.md](quickstart.md) §2 이야기 6·7).

- [X] T045 [US3] `backend/src/itb/storage/test_moves.py` 에 `move_test_to_group(repo, test_id, to_prefix)` 를 더한다 — **순서가 계약이다** ([contracts/api-contract.md](contracts/api-contract.md) §4): 검증 → `.runs/<옛ID>` → `.runs/<새ID>` → 새 정의 쓰기 → 옛 정의 지우기 → 실패 시 되돌림. **산출물이 먼저인 이유**: 반대로 하면 「테스트는 새 자리, 결과는 옛 자리」가 되어 사용자에게는 결과가 사라진 것으로 보인다. 이 순서의 실패는 목록에 나타나지 않는 흔적만 남긴다. **번호는 그대로다** — 접두어만 바뀐다. T013 에 의존
- [X] T046 [P] [US3] `backend/tests/unit/test_test_moves.py` 에 그룹 이동 검사를 더한다 — 번호가 유지되는지, 산출물이 따라오는지(SC-628), 정의 쓰기 실패 시 산출물이 되돌려지는지(SC-628a), 새 식별자가 이미 있으면 거절하는지(FR-444c)
- [X] T047 [US3] `backend/src/itb/api/routes/tests.py` 에 `POST /api/tests:move` 를 더한다 — 요청 `{test_ids, to_prefix}`, 응답 `{moved: [{from_id, to_id, name}]}`. `to_prefix` 가 `TC` 면 그룹에서 뺀다. 여러 개도 T013 의 3단계 규약을 쓴다. T045 에 의존
- [X] T048 [US3] `DELETE /api/groups/{prefix}` 가 **그 그룹의 테스트를 `TC-###` 로 되돌리게** 한다 (FR-451) — 지우지 않는다. 응답에 `ungrouped` 를 담는다. **§4 의 이동을 그 그룹 전부에 적용하는 것이며 같은 원자성 규약을 따른다.** T045 에 의존
- [X] T049 [P] [US3] `backend/tests/contract/test_test_groups_api.py` 에 이동·해체 검사를 더한다 — 번호 유지, 결과 따라옴, 그룹 삭제가 테스트를 지우지 않음(FR-451), 실행 중이면 하나도 안 옮겨짐
- [X] T050 [US3] `frontend/src/pages/TestList.tsx` 의 선택 띠에 「그룹으로 옮기기」를 더한다 (FR-448) — 그룹이 하나도 없으면 그리지 않는다. 이미 있는 선택을 그대로 쓴다
- [X] T051 [US3] 그룹 칩에 이름 변경(제자리 편집, 확인 없음)과 없애기를 더한다 (UC-013-08). **없애기에만 확인이 있다** — 그것만이 자산을 움직인다(그 안 테스트들의 파일 이름과 산출물 디렉터리가 바뀐다). 확인 문구가 「테스트 N개가 그룹 없음으로 돌아가고 식별자가 `TC-###` 로 바뀝니다 · **지워지지 않습니다**」를 말한다
- [X] T052 [P] [US3] `frontend/tests/TestGroups.test.tsx` 에 US3 검사를 더한다 — 이름 변경에 확인이 없고 없애기에는 있는지, 없애기 확인에 「지워지지 않습니다」가 있는지, 복수 이동이 선택을 쓰는지

---

## Phase 6: Polish & Cross-Cutting

- [X] T053 [P] `backend/tests/contract/test_dsl_roundtrip.py` 를 개정한다 — `Project` 에 `groups` 가 생겼다. **기존 프로젝트 파일(`groups` 없음)이 그대로 읽히는지**를 함께 센다
- [X] T054 [P] `README.md` 의 「저장 위치」에 테스트 휴지통 자리와 **되돌리는 방법**을 적는다 — 도구 안에 복구 화면이 없으므로 문서가 유일한 안내다. 012 가 프로젝트 휴지통을 적은 자리 옆에 나란히 둔다
- [X] T055 [P] `README.md` 또는 `docs/DEVELOPMENT.md` 에 **그룹과 식별자 접두어**를 적는다 — `TC` 가 예약이라는 것과, 그룹을 옮기면 식별자가 바뀐다는 것
- [X] T056 전체 검증을 돌린다 — T001 의 기준선과 비교해 **013 이 깬 것이 없는지** 확인한다. 특히 `schema.export --check` 와 pytest 오류 15건이 그대로인지
- [ ] T057 손 검증을 돌린다 (**사람이 판정한다** · [docs/PENDING-HUMAN-VERIFICATION.md](../../docs/PENDING-HUMAN-VERIFICATION.md) §13-3 에 등록했다) — [quickstart.md](quickstart.md) §2 의 일곱 이야기와 §3 의 회귀 7건. **이야기 1(기존 자산이 그대로다)을 가장 먼저** 한다. `XDG_DATA_HOME`·`XDG_CONFIG_HOME` 을 임시 디렉터리로 지정해 실제 자산을 건드리지 않는다

---

## Dependencies & Execution Order

```
Phase 1 (T001~T002)
      ↓
Phase 2 (T003~T014)  ← 반드시 먼저. 식별자 확장이 전부의 바탕이다
      ↓
   ┌──┴──────────────┐
Phase 3 (US1)     Phase 4 (US2)     ← 서로 독립. 병렬 가능
 T015~T030         T031~T044
   └──┬──────────────┘
      ↓
Phase 5 (US3, T045~T052)  ← 그룹(US2)이 있어야 옮길 곳이 생긴다
      ↓
Phase 6 (T053~T057)
```

**이야기 간 의존**

| 이야기 | 선행 | 이유 |
|---|---|---|
| US1 | Phase 2 | 순서 규약(T013), 오류 코드(T011) |
| US2 | Phase 2 | 식별자 확장(T003~T007) — 그룹 접두어가 식별자에 들어간다 |
| US3 | US2 · T013 | 옮길 그룹이 있어야 하고, 이동이 삭제와 같은 규약을 쓴다 |

**Phase 2 안의 의존**: T003 → T005 → T006·T007, T004 → T031, T011 → T012, T013 → T014.
T010 은 T003~T007 이 끝난 뒤.

## Parallel Execution Examples

**Phase 2** — 두 갈래가 서로 다른 파일이다:

```
식별자 갈래: T003 → T005 → {T006, T007} → T010
오류 갈래:   T011 → (T012 는 T017 뒤로 미룬다)
규약 갈래:   T013 → T014
검사: T008·T009 는 앞 갈래가 끝나는 대로
```

**Phase 3 ∥ Phase 4** — 겹치는 파일은 `routes/tests.py`(T018·T019 ↔ T035~T038),
`pages/TestList.tsx`(T024~T029 ↔ T041~T043), `api/client.ts`(T022 ↔ T040) 셋이다.
이 셋은 **직렬로** 하고 나머지는 병렬로 한다.

**검사 작업**: T008·T009·T014·T017·T020·T021·T030·T034·T039·T044·T046·T049·T052·T053 은
각자 다른 파일이라 모두 `[P]` 다.

## Implementation Strategy

**MVP = Phase 1 + 2 + 3 (US1).** 복수 삭제만으로 단독 가치가 있고, 그룹 없이도 쓸 수 있다.

**증분 2 = Phase 4 (US2).** 여기서 명세의 P1 이 모두 선다.

**증분 3 = Phase 5 + 6.**

**중간에 멈춰도 되는 지점**: Phase 2 끝(기존 자산이 그대로 도는지 확인된 상태), Phase 3 끝,
Phase 4 끝.

## 이 기능에서 특히 조심할 것

1. **`list_test_paths()` 의 glob 을 넓히는 것을 잊지 않는다** (T006). 넓히지 않으면 새 접두어
   테스트가 **저장은 되는데 목록에 안 나온다** — 가장 찾기 어려운 종류의 결함이다.
2. **기존 자산을 도구가 먼저 움직이지 않는다** (T010 · SC-629). 업그레이드만으로 사용자의
   git diff 는 0줄이어야 한다.
3. **순서를 뒤집지 않는다** — 그룹 이동은 **산출물이 먼저, 정의가 나중**이다 (T045). 뒤집으면
   사용자에게 결과가 사라진 것으로 보인다.
4. **되돌리기 실패를 삼키지 않는다** (T013·T019). `TEST_DELETE_FAILED`(되돌렸다)와
   `TEST_DELETE_PARTIAL`(못 되돌렸다)은 사용자가 할 일이 다르므로 코드를 가른다.
5. **새 오류 코드는 전부 `BLOCKED` 다** (T011). 012 에서 `BROKEN` 으로 두었다가 기존 불변식
   검사에 걸렸다.
6. **`BulkDeleteConfirm` 을 재사용하지 않는다** (T027). Step 번호 범위를 말하는 부품이고,
   테스트는 순서 없는 집합이다.

---

## Phase 7: Convergence (1회차)

- [X] T058 이미 없는 테스트를 **건너뛰고 나머지를 처리한다** per FR-436 · Edge Case (contradicts) — `backend/src/itb/api/routes/tests.py` 의 `_require_test_exists` 가 없는 식별자를 404 로 거절해 **고른 것 전부를 막는다.** 명세는 「요청 시점에 이미 없으면 실패로 보고하지 않아야 한다」이고, 012 FR-420 이 프로젝트 삭제에서 같은 취지로 구현돼 있다 — **사용자가 원한 결과가 이미 이루어져 있는데 실패로 답할 이유가 없다.** 고른 뒤 목록이 밖에서 바뀐 경우가 실제 상황이다. 삭제(`:delete`)와 한 줄 삭제 양쪽을 고치고, 응답의 `deleted` 에는 실제로 옮긴 것만 싣는다. FR-432(전부 되거나 전부 안 되거나)와 어긋나지 않는다 — 없는 것은 「지울 필요가 없는 것」이지 실패가 아니다. `test_an_unknown_id_stops_everything` 검사와 [contracts/api-contract.md](contracts/api-contract.md) §3 의 404 줄을 함께 고친다
- [X] T059 그룹 이동의 부분 실패에 **이동용 코드를 따로 둔다** per contracts §4·§6 (contradicts) — 지금 `move_tests` 와 `delete_group` 이 `TEST_DELETE_PARTIAL` 을 쓰는데, 그 코드의 `NEXT_ACTION` 은 「일부가 **휴지통에** 남아 있습니다」다. **이동 실패에서는 휴지통이 아니라 다른 그룹 자리에 있다** — 사용자를 없는 곳으로 보낸다. `TEST_MOVE_PARTIAL` 을 더하고(`CATEGORY`·`NEXT_ACTION` 양쪽, `BLOCKED`), 안내는 「일부가 새 그룹으로 옮겨졌습니다. 지워진 것은 없습니다」로 한다. 스키마 재생성과 [contracts/api-contract.md](contracts/api-contract.md) §4·§6 갱신을 함께 한다
- [X] T060 [P] 명세의 US1 수용 시나리오 7 을 계약에 맞춘다 per US1/AC7 (partial) — 「아무것도 고르지 않았을 때 「선택한 항목 삭제」는 쓸 수 없는 상태이며 왜 그런지가 표시된다」로 적혀 있으나, SC-627(그룹·복수 삭제를 쓰지 않는 사용자에게 자리를 뺏지 않는다)에 따라 **띠 자체를 그리지 않기로** [contracts/ui-contract.md](contracts/ui-contract.md) UC-013-02 에서 정했다. 명세 안에서 갈린 것이며 코드는 SC-627 을 따랐다. `spec.md` 의 그 시나리오를 실제 결정으로 고치고 왜 그렇게 정했는지 한 줄을 남긴다

---

## Phase 8: Convergence (2회차)

- [X] T061 그룹 띠가 **빈 그룹도 보이게** 한다 per US3/AC4 · FR-450 (missing) — 띠가 `data?.groups`(목록 응답)를 쓰는데 거기엔 테스트가 **있는** 그룹만 실린다(FR-450 이 그렇게 정했다). 그래서 테스트를 전부 옮긴 그룹은 **띠에서 사라져 고를 수도, 이름을 고칠 수도, 없앨 수도 없고** 프로젝트 파일에만 남는다 — 012 에서 사용자가 지적한 「없앨 방법이 화면에 없는 줄」과 같은 형태다. `GET /api/groups`(빈 그룹 포함)를 함께 불러 띠의 근거로 삼는다. **두 응답의 규칙을 합치지 않는다** — 목록을 어지럽히지 않는 것(FR-450)은 **소제목** 이야기이고, 띠는 **고르는 자리**라 비어 있어도 있어야 한다 ([contracts/api-contract.md](contracts/api-contract.md) §5 가 이미 그렇게 갈라 두었다). `frontend/tests/TestGroups.test.tsx` 에 「테스트 0개인 그룹을 띠에서 골라 없앨 수 있다」를 더한다
- [X] T062 저장할 때 **그룹을 고를 수 있게** 한다 per FR-443 · US2/AC5 (missing) — 백엔드 `SaveRequest.group` 은 이미 받는데 `frontend/src/api/client.ts` 의 `sessions.save` 가 `{ name }` 만 보낸다. 화면에서 그룹을 골라 테스트를 만들 길이 없어, 만든 뒤 옮기는 수밖에 없다. 클라이언트에 `group` 을 싣고 저장 자리(테스트 이름을 받는 곳)에 그룹 선택을 더한다. **그룹이 하나도 없으면 그리지 않는다** (SC-627). 이미 저장된 테스트를 다시 저장할 때는 그리지 않는다 — 그룹 변경은 `:move` 가 원자성 규약과 함께 하는 일이고, 저장에 자산 이동을 숨기지 않는다
