---

description: "Task list for 019 프로젝트·테스트 공유용 내보내기·가져오기"
---

# Tasks: 프로젝트·테스트 공유용 내보내기·가져오기

**Input**: Design documents from `/specs/019-project-test-sharing/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/rest-api.md](contracts/rest-api.md),
[quickstart.md](quickstart.md)

**Tests**: 포함한다. 선택이 아니라 **헌법 §Development Workflow & Quality Gates 3** 이
요구한다 — "제품은 테스트 도구다. 자기 테스트 없이 내보내는 것은 허용되지 않는다."
게이트 2(왕복 무결성)도 이 기능에 직접 걸린다.

**Organization**: 사용자 스토리별로 묶어, 스토리 하나만 끝내도 독립적으로 검증·전달할 수 있다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 사용자 스토리인가 (US1~US5)

## Path Conventions

웹 애플리케이션 구조 — `backend/src/itb/`, `backend/tests/`, `frontend/src/`.

---

## Phase 1: Setup (공용 기반)

**Purpose**: 새 패키지의 자리를 만들고, 이 기능의 **불변식을 강제하는 장치를 먼저 건다.**

- [ ] T001 `backend/src/itb/sharing/__init__.py` 를 만들어 빈 패키지를 둔다. 모듈 목록과 각 모듈의 책임을 docstring 에 적는다 (plan.md Source Code 트리 기준)
- [ ] T002 `backend/src/itb/sharing/limits.py` 에 이 기능 고유 상한을 둔다 — `MAX_BUNDLE_BYTES`(20MB), `MAX_BUNDLE_TESTS`(2000), `MAX_BUNDLE_GROUPS`(100), `SHARE_PLAN_TTL_SECONDS`(1800), `MAX_SHARE_PLANS`(8), `BUNDLE_MEDIA_TYPE`, `BUNDLE_SUFFIX`. **그룹당 999 는 두지 않고** `itb.domain.test_case.MAX_TEST_NUMBER` 를 참조한다는 사실을 docstring 에 적는다 (research R12)
- [ ] T003 `backend/.importlinter` 에 계약 2건을 추가한다 — ① `execution-no-llm` 의 `source_modules` 에 `itb.sharing` 추가 (헌법 원칙 II) ② 신규 계약 `sharing-cannot-reach-secrets`: `itb.sharing` 이 `itb.secrets` 를 임포트하지 못하게 한다 (research R3)
- [ ] T004 `backend/src/itb/api/errors.py` 의 `ErrorCode` 에 data-model.md §7 의 코드 11개를 추가한다 — `SHARE_EXPORT_EMPTY`, `SHARE_BUNDLE_TOO_LARGE`, `SHARE_BUNDLE_MALFORMED`, `SHARE_BUNDLE_UNSUPPORTED_VERSION`, `SHARE_BUNDLE_INVALID_TEST`, `SHARE_PLAN_NOT_FOUND`, `SHARE_PLAN_STALE`, `SHARE_IMPORT_BLOCKED`, `SHARE_IMPORT_FAILED`, `SHARE_IMPORT_PARTIAL`, `SECRET_VALUE_MISSING`
- [ ] T005 `uv run lint-imports` 를 돌려 T003 의 두 계약이 **현재 상태에서 통과**하는지 확인한다. 통과하지 않으면 나머지 작업의 전제가 깨진 것이므로 여기서 멈추고 원인을 밝힌다

**Checkpoint**: 계약이 걸렸다. 이후 누가 `itb.sharing` 에서 `itb.secrets` 를 끌어오면 빌드가 실패한다.

---

## Phase 2: Foundational (차단 선행 작업)

**Purpose**: 모든 스토리가 딛고 서는 도메인·모델·스키마. **⚠️ 이 단계가 끝나기 전에는 어떤 스토리도 시작할 수 없다.**

- [ ] T006 `backend/src/itb/domain/test_case.py` 에 `VARIABLE_VALUE_FIELDS = ("value", "assertion.value", "url")` 상수를 추가하고, `referenced_variable_names` 와 `Test.referenced_variables` 가 **그 상수를 돌도록** 고친다. 자리 목록이 세 곳에 흩어져 있던 것을 하나로 모은다 (research R7, data-model §5.1)
- [ ] T007 `backend/src/itb/domain/test_case.py` 에 `ImportProvenance` 모델(`source_file`, `imported_at`, `original_id`)을 추가하고 `Test.imported_from: ImportProvenance | None = None` 필드를 더한다. **`dsl_version` 을 올리지 않는다** (data-model §5)
- [ ] T008 [P] `backend/tests/unit/test_domain_provenance.py` — 019 이전 형식의 `tests/*.yaml`(키 없음)이 그대로 읽히고 `imported_from` 이 `None` 이 되는지, `imported_from` 이 있는 테스트가 실행 의미에 영향을 주지 않는지 확인한다 (헌법 원칙 I)
- [ ] T009 [P] `backend/tests/unit/test_domain_variable_fields.py` — `VARIABLE_VALUE_FIELDS` 의 세 자리 각각에 `{{VAR}}` 를 넣었을 때 `referenced_variable_names` 가 전부 찾아내는지 확인한다
- [ ] T010 `backend/src/itb/sharing/bundle.py` 에 묶음 모델을 정의한다 — `ShareBundle`(`bundle_version`, `generator`, `created_at`, `project`, `required_values`, `tests`), `BundleProject`(`next_test_number` 제외), `RequiredValue`(`sensitive`·`declared` 포함), `ValueUsage`. 상한은 `limits.py` 에서 온다 (data-model §2)
- [ ] T011 `backend/src/itb/sharing/bundle.py` 에 `collect_required_values(tests) -> list[RequiredValue]` 를 둔다. `VARIABLE_VALUE_FIELDS` 를 돌며 `(test_id, step_id, step_label, field)` 를 모은다. **민감 변수는 전부**, **비민감 변수는 값이 빈 것만** 담는다. 각 항목에 `sensitive`·`declared` 를 싣는다 (data-model §2.3, FR-040)
- [ ] T012 [P] `backend/tests/unit/test_sharing_bundle.py` — `collect_required_values` 가 세 자리 모두에서 자리를 찾고, 값이 **있는** 비민감 변수는 담지 않으며, 값이 **빈** 비민감 변수는 담고, 참조가 없는 민감 변수는 `usages` 가 비어 제외되는지 확인한다
- [ ] T013 `backend/schema/share-bundle.schema.json` 을 `itb.schema.export` 에 등록해 `ShareBundle` 에서 생성되게 한다. `uv run python -m itb.schema.export --check` 가 통과하는지 확인한다 (헌법 §교차 언어 스키마 의무)
- [ ] T014 `frontend/` 에서 `npm run gen:types` 를 돌려 `frontend/src/types/generated/share-bundle.d.ts` 를 만든다. 생성물이 커밋에 포함되는지 확인한다
- [ ] T015 `backend/src/itb/api/routes/sharing.py` 라우터 뼈대를 만들고(`APIRouter(prefix="/api/share", tags=["sharing"])`) `backend/src/itb/api/app.py` 에 등록한다. **`/api/project` 아래에 두지 않는 이유**를 라우터 docstring 에 적는다 (contracts §머리말)
- [ ] T016 `_content_disposition`(ASCII 대체 이름 + RFC 5987)을 `backend/src/itb/api/routes/excel.py` 에서 공용 위치(`backend/src/itb/api/routes/__init__.py` 또는 신규 `_download.py`)로 옮기고 양쪽이 **한 곳을 쓰게** 한다. 엑셀 쪽 기존 테스트가 그대로 통과하는지 확인한다

**Checkpoint**: 묶음 모델·스키마·도메인 변경이 끝났다. 여기서부터 스토리들이 갈라진다.

---

## Phase 3: User Story 1 — 만든 테스트를 파일 하나로 내보낸다 (P1) 🎯 MVP

**Goal**: 프로젝트 전체 또는 고른 테스트를 묶음 파일 하나로 만들어 내려받는다.

**Independent Test**: 프로젝트를 열고 내보내기를 실행해 파일이 생성되고, 그 파일이 선택한
테스트를 전부 담고 있으며, 민감 값이 **어떤 형태로도** 들어 있지 않음을 확인한다.

### Tests (구현 전에 쓴다 — 헌법 게이트 3)

- [ ] T017 [P] [US1] `backend/tests/contract/test_sharing_export.py` — `POST /api/share/export` 가 200 과 `Content-Disposition`·`X-ITB-Share-Test-Count` 를 주고, 본문이 `bundle_version: 1` 로 시작하는 YAML 인지 (contracts §2)
- [ ] T018 [P] [US1] `backend/tests/contract/test_sharing_export.py` 에 **C1** 를 추가한다 — 응답 바이트에 `secrets.local.yaml` 의 어떤 암호문도, 알려진 평문 비밀값도 나타나지 않는다 (SC-004). 이것이 이 기능의 유일한 절대 조건이다
- [ ] T019 [P] [US1] `backend/tests/unit/test_sharing_builder.py` — 고른 테스트만 담기(US1 AS2), 민감 변수는 이름만(US1 AS3), 실행 산출물 미포함(FR-005), `imported_from` 이 `None` 으로 비워짐(research R9)
- [ ] T020 [P] [US1] `backend/tests/contract/test_sharing_export.py` — `POST /api/share/export` 호출 **전후로 프로젝트 디렉터리가 바뀌지 않는지**(파일 목록·mtime) 확인한다. 미리보기만이 아니라 내보내기 자체에 FR-008 이 걸린다
- [ ] T021 [P] [US1] `backend/tests/abnormal/test_sharing_export_empty.py` — 테스트가 없는 프로젝트에서 `SHARE_EXPORT_EMPTY`(400) 이고 파일이 만들어지지 않는다 (US1 AS4)

### Implementation

- [ ] T022 [US1] `backend/src/itb/sharing/builder.py` 에 `build_bundle(project, tests, *, generator) -> ShareBundle` 를 구현한다. `Test` 를 그대로 싣되 `imported_from` 만 비운다. 고른 테스트만 내보낼 때는 **그 테스트가 쓰는 접두어의 그룹만** 담는다 (data-model §2.2)
- [ ] T023 [US1] `backend/src/itb/sharing/builder.py` 에 `dump_bundle(bundle) -> bytes` 를 구현한다. 파일 머리에 "민감 값이 들어 있지 않습니다" 주석을 넣고, `yaml.safe_dump(sort_keys=False, allow_unicode=True, default_flow_style=False)` 로 키 순서를 고정한다 (data-model §2)
- [ ] T024 [US1] `backend/src/itb/api/routes/sharing.py` 에 `POST /api/share/export` 를 구현한다. `test_ids` 가 없거나 `null` 이면 전체. 읽을 수 없는 테스트는 빠지되 `X-ITB-Share-Unreadable` 로 알린다. 파일명은 `<slug>-<YYYYMMDD-HHMMSS>.itbshare.yaml` (contracts §2)
- [ ] T025 [US1] 묶음은 **메모리에서 완성된 뒤에야** 응답 본문이 되게 한다. 실패는 언제나 "파일이 없다" 여야지 "파일이 이상하다" 가 되면 안 된다 (014 `export_project` 와 같은 성질)
- [ ] T026 [P] [US1] `frontend/src/api/client.ts` 에 `exportShareBundle(testIds)` 를 더한다. blob 으로 받아 `Content-Disposition` 의 파일명으로 저장한다 — 014 의 엑셀 내려받기 처리를 따른다
- [ ] T027 [US1] `frontend/src/pages/ShareExport.tsx` 를 만든다. 대상(전체/고른 것) 표시 → 내려받기. 확인 요약은 US4 에서 붙인다
- [ ] T028 [US1] `frontend/src/app/routes/ShareExportRoute.tsx` 를 만들고 라우터에 등록한다
- [ ] T029 [US1] `frontend/src/pages/TestList.tsx` 에 「공유용 내보내기」 진입점을 더한다. 엑셀 내보내기와 **이름으로 구별되게** 둔다 — 두 산출물이 전혀 다르다 (research R13)
- [ ] T030 [P] [US1] `frontend/src/pages/__tests__/ShareExport.test.tsx` — 선택 없음이면 전체, 선택이 있으면 그 목록을 보내는지

**Checkpoint**: 파일이 만들어져 동료에게 보낼 수 있다. 받는 기능은 아직 없다.

---

## Phase 4: User Story 2 — 받은 파일을 가져와 내 목록에서 본다 (P1)

**Goal**: 묶음 파일을 골라 계획을 확인하고, 새 프로젝트로 복원한다.

**Independent Test**: 내보낸 파일을 **다른 작업 공간**에서 가져와 테스트 목록·스텝 내용(로케이터
후보 포함)이 원본과 일치하는지 확인한다.

### Tests

- [ ] T031 [P] [US2] `backend/tests/unit/test_sharing_reader.py` — 정상 묶음 해석, 바이트 상한 초과 거부(파싱 전), `bundle_version` 불일치 거부, 최상위 비매핑 거부
- [ ] T032 [P] [US2] `backend/tests/abnormal/test_sharing_bad_bundle.py` — **C5** YAML 별칭 폭탄이 전개 없이 즉시 `SHARE_BUNDLE_MALFORMED` 로 거부되는지 (research R4). 처리 시간이 상한 안인지도 함께 본다
- [ ] T033 [P] [US2] `backend/tests/abnormal/test_sharing_bad_bundle.py` — **C3·C4** 손상 파일과 `bundle_version: 99` 가 거부되고, **그 뒤 대상 프로젝트의 파일 수가 그대로**인지 (FR-023·FR-030)
- [ ] T034 [P] [US2] `backend/tests/unit/test_sharing_repair.py` — **C11** 선언 없는 `{{VAR}}` 참조가 **거부되지 않고** 보충되는지. `SECRET_` 접두사는 민감으로, 그 외는 값이 빈 비민감으로 보충되고 `repaired_variables` 에 남는지 (FR-047)
- [ ] T035 [P] [US2] `backend/tests/unit/test_sharing_planner.py` — 새 프로젝트 이름 충돌 시 비껴 만들기(US2 AS3), 그룹 `action` 판정, `capacity` 산출
- [ ] T036 [P] [US2] `backend/tests/contract/test_sharing_import.py` — plan → commit 흐름, 계획 단계에서 **디스크가 그대로**인지(014 FR-016 과 같은 성질), 만료된 `plan_id` 가 `SHARE_PLAN_NOT_FOUND`
- [ ] T037 [P] [US2] `backend/tests/integration/test_sharing_roundtrip.py` — **C2** 내보낸 묶음을 그대로 가져오면 스텝이 **로케이터 후보까지** 완전히 같은지 (SC-003, 헌법 원칙 IV·게이트 2)
- [ ] T038 [P] [US2] `backend/tests/abnormal/test_sharing_commit_failure.py` — **C7** 쓰기 실패 시 만들어진 파일이 하나도 남지 않고 `SHARE_IMPORT_FAILED`, 되돌리기까지 실패하면 `SHARE_IMPORT_PARTIAL` 인지 (FR-024)

### Implementation

- [ ] T039 [US2] `backend/src/itb/sharing/reader.py` 에 별칭 금지 로더를 구현한다 — `yaml.SafeLoader` 를 상속해 `compose_node` 에서 별칭을 만나면 오류. 정상 묶음은 별칭을 쓰지 않으므로 잃는 것이 없다 (research R4)
- [ ] T040 [US2] `backend/src/itb/sharing/reader.py` 에 `read_bundle(data: bytes) -> ShareBundle` 를 구현한다. **다섯 겹을 순서대로** 통과시킨다 — 바이트 상한 → YAML → `ShareBundle` → **선언 보충** → 각 `Test` 도메인 검증. 앞 겹을 통과 못 하면 뒤를 시도하지 않는다 (data-model §6)
- [ ] T041 [US2] `backend/src/itb/sharing/reader.py` 에 선언 보충 단계를 구현한다 — 참조는 있는데 선언이 없는 변수를 `SENSITIVE_VARIABLE_PREFIX` 로 갈라 채워 넣고 `repaired_variables` 에 기록한다. **도메인 검증보다 먼저** 돈다. 없는 값을 지어내는 것이 아니라 빈 자리를 드러내는 것이다 (FR-047, data-model §6)
- [ ] T042 [US2] 테스트 정의 검증 실패는 **전부 모아 한 번에** 보고한다. 한 건이라도 실패하면 가져오기 전체를 거부한다 (FR-023·FR-024, data-model §6)
- [ ] T043 [US2] `backend/src/itb/sharing/plan_store.py` 에 `SharePlanStore` 를 구현한다. 메모리에만 두고 TTL 30분, 상한 8개, 넘으면 오래된 것부터 버린다. `AppState` 에 하나 둔다 (data-model §3)
- [ ] T044 [US2] `backend/src/itb/sharing/planner.py` 에 `plan_import(bundle, *, target, existing_project, existing_test_ids) -> SharePlan` 를 구현한다. 이 단계에서는 `already_stored`/`env_provided` 를 `None` 으로 둔다 — `itb.sharing` 은 `itb.secrets` 에 닿을 수 없다 (research R3)
- [ ] T045 [US2] `planner.py` 에 새 프로젝트 이름 충돌 회피를 구현한다. `allocate_workspace_path` 를 재사용하고 `project_renamed_from` 을 남긴다 (US2 AS3)
- [ ] T046 [US2] `planner.py` 에 `notices` 산출을 구현한다 — `START_URL_CHECK`(항상), `REIMPORT`(대상에 같은 `imported_from.source_file` 이 있을 때), `NAME_SANITIZED`(파일시스템이 허용하지 않는 문자를 바꿨을 때)
- [ ] T047 [US2] `backend/src/itb/sharing/applier.py` 에 `apply_new_project(plan, ...) -> ShareReport` 를 구현한다. **임시 디렉터리에 완성한 뒤 `os.replace`**, 레지스트리 등록은 옮기기가 성공한 **뒤**에 한다 (research R5)
- [ ] T048 [US2] `applier.py` 에서 `itb-project.yaml` 의 `groups` 를 테스트 파일보다 **먼저** 쓴다. 실패 시 프로젝트 파일도 되돌린다 (research R5)
- [ ] T049 [US2] `applier.py` 가 각 테스트에 `imported_from`(`source_file`, `imported_at`, `original_id`)을 채워 저장하게 한다 (FR-028, research R9)
- [ ] T050 [US2] `backend/src/itb/api/routes/sharing.py` 에 `POST /api/share/import/plan` 을 구현한다. 업로드 상한은 **상한 + 1 바이트만 읽어** 판정한다. 파일 표시 이름은 `sanitize_display_name` 으로 정규화한다 (contracts §3)
- [ ] T051 [US2] 라우터에서 `already_stored`(`SecretStore.has`)와 `env_provided`(`os.environ`)를 채운다. **교차 참조는 라우터가 맡는다** (research R3, data-model §3.3)
- [ ] T052 [US2] `GET /api/share/import/plan/{plan_id}` 를 구현한다 (contracts §4)
- [ ] T053 [US2] `POST /api/share/import/commit` 을 구현한다. **확정은 계획을 다시 세운다** — 결과가 예고와 달라졌으면 `SHARE_PLAN_STALE`(409) 과 함께 새 계획을 돌려준다 (contracts §5)
- [ ] T054 [US2] `target=new` 확정 후 새 프로젝트를 서버가 열고, 응답의 `project_root` 로 화면이 상태를 맞출 수 있게 한다 (contracts §5)
- [ ] T055 [P] [US2] `frontend/src/api/client.ts` 에 `planShareImport(file, target)`, `getSharePlan(id)`, `commitShareImport(body)` 를 더한다
- [ ] T056 [US2] `frontend/src/pages/ShareImport.tsx` 를 만든다 — 파일 선택 → 계획 요약(프로젝트 이름, 테스트 목록, 그룹, 필요 민감 변수, notices) → 확정 → 결과. `blocking` 이 비어 있지 않으면 확정 버튼을 잠근다
- [ ] T057 [US2] `frontend/src/app/routes/ShareImportRoute.tsx` 를 만들고 라우터에 등록한다
- [ ] T058 [US2] `frontend/src/app/routes/ProjectsRoute.tsx` 에 「공유 파일에서 가져오기」 진입점을 더한다
- [ ] T059 [US2] 확정 화면에서 `default_start_url` 을 바꿀 수 있게 한다 — 받는 쪽 환경이 다른 경우다 (spec Edge Cases, contracts §5)
- [ ] T060 [P] [US2] `frontend/src/pages/__tests__/ShareImport.test.tsx` — `blocking` 이 있으면 확정이 막히고, `SHARE_PLAN_STALE` 응답이 오면 새 계획으로 갈아 끼우는지

**Checkpoint**: 공유가 성립한다. 다만 받은 테스트는 아직 민감 값이 비어 실행할 수 없다.

---

## Phase 5: User Story 3 — 받은 테스트를 내 비밀값으로 실행 가능하게 만든다 (P1)

**Goal**: 채워야 할 값을 **어디에 쓰이는지와 함께** 보여 주고, 채운 값을 받는 사람의 키로 봉인한다.
값이 비면 **브라우저를 띄우기 전에** 막는다.

**Independent Test**: 민감 변수를 쓰는 테스트를 가져온 뒤, 값을 채우기 전에는 실행이 막히고
값을 채운 뒤 실행이 통과하는지 확인한다.

### Tests

- [ ] T061 [P] [US3] `backend/tests/unit/test_sharing_readiness.py` — 민감 변수에 암호문이 없으면 `missing_secrets` 에 들어가고, **C9** 같은 이름 환경 변수가 있으면 들어가지 않는지 (research R10). **복호화를 시도하지 않는지**도 확인한다 (잠긴 키에서도 판정이 돌아야 한다)
- [ ] T062 [P] [US3] `backend/tests/contract/test_sharing_readiness.py` — **C8** 값이 빈 테스트로 `POST /api/sessions` 하면 409 `SECRET_VALUE_MISSING` 이고 **세션이 만들어지지 않는지** (FR-044)
- [ ] T063 [P] [US3] `backend/tests/contract/test_sharing_values.py` — **C12** `variable_values` 에 민감 변수 이름을 넣으면 400 으로 거절되는지(봉인 경로는 하나뿐이다), **C13** 값이 빈 비민감 변수만 있는 테스트는 `POST /api/sessions` 가 막지 않는지 (FR-044)
- [ ] T064 [P] [US3] `backend/tests/integration/test_sharing_secret_handover.py` — 가져오기 → 값 채우기 → 실행 통과까지, 그리고 채운 평문이 `tests/*.yaml`·API 응답·로그 어디에도 나타나지 않는지 (FR-043)

### Implementation

- [ ] T065 [US3] `backend/src/itb/api/routes/tests.py` 에 `GET /api/tests/{test_id}/readiness` 를 구현한다 — `runnable`, `missing_secrets`, `empty_variables`, `key_available`. **`empty_variables` 는 실행을 막지 않는다** (FR-044, contracts §6)
- [ ] T066 [US3] 판정은 `VariableResolver` 와 **같은 해석 순서**를 따르되 값을 읽지 않고 존재만 본다 — 환경 변수 → `SecretStore.has`. 판정하려고 복호화하면 잠긴 키에서 실패한다 (research R10)
- [ ] T067 [US3] `backend/src/itb/api/routes/sessions.py` 의 `POST /api/sessions` 에 선행 검사를 넣는다. **`mode in ("replay", "rerecord")` 에 건다** — `rerecord` 도 앞 스텝을 재생하므로 같은 값이 필요하다. `record`·AI 작성 세션은 값을 만드는 중이므로 걸지 않는다 (contracts §7)
- [ ] T068 [US3] 409 응답의 `detail` 에 빠진 이름 목록과 `test_id` 를 싣는다. 브라우저를 띄우기 **전에** 막는다
- [ ] T069 [US3] `frontend/src/pages/ShareImport.tsx` 의 결과 화면에 「필요한 값 채우기」를 붙인다. **민감·비민감을 한 목록**에 두되 저장 위치가 다름을 구분해 보여 주고, 각 항목을 **이름 + 어느 테스트의 어느 스텝** 과 함께 보여 준다. `declared: false` 인 것은 「선언이 없어 보충했다」로 표시한다 (FR-040·FR-047·FR-048)
- [ ] T070 [US3] 값 입력은 `frontend/src/pages/SecretValues.tsx` 의 입력 구성요소를 **재사용**하고, 저장은 기존 `PUT /api/secrets/{name}` 으로 한다. 봉인 경로를 두 벌로 만들지 않는다 (research R13, contracts §8)
- [ ] T071 [US3] `POST /api/share/import/commit` 의 `variable_values` 를 구현한다 — **비민감** 변수 값만 받아 테스트 정의에 기록한다. 민감 변수 이름이 오면 400 으로 거절한다 (FR-048, contracts §5)
- [ ] T072 [US3] 키가 없을 때 키 생성 안내와 키 관리 화면 경로를 보여 준다. **가져오기 자체는 키 없이도 완료된다** — 막히는 것은 값 입력 시점이다 (FR-045). 나중에 채우는 경로(민감 → `SecretsRoute`, 비민감 → 테스트 편집 화면)도 결과에 안내한다 (FR-041)
- [ ] T073 [US3] 값 입력 화면에서 민감 항목은 `PUT /api/secrets/{name}`(봉인), 비민감 항목은 테스트 정의 기록으로 **경로를 갈라** 저장하고, 화면이 어느 쪽인지 구분해 보여 주게 한다 (FR-048)
- [ ] T074 [US3] `already_stored: true` 인 변수는 기존 값 유지 / 다시 입력을 고르게 한다. 조용히 덮어쓰지 않는다 (FR-046)
- [ ] T075 [US3] `frontend/src/pages/TestList.tsx` 에 테스트별 「값 필요」 표시를 붙인다. 누르기 전에 보여야 한다 (FR-044)
- [ ] T076 [P] [US3] `frontend/src/pages/__tests__/ShareImportSecrets.test.tsx` — 사용 위치가 보이는지, `already_stored` 일 때 선택지가 나오는지, 입력값이 화면에 평문으로 되돌아오지 않는지

**Checkpoint**: 받은 사람이 테스트를 실행할 수 있다. **여기까지가 이 기능의 핵심 가치다.**

---

## Phase 6: User Story 4 — 내보내기 전에 무엇이 나가는지 확인한다 (P2)

**Goal**: 파일을 만들기 전에 평문으로 나가는 값을 **가리지 않고** 보여 준다. 되돌릴 수 없는
조작 앞의 유일한 방어선이다.

**Independent Test**: 민감 표시가 없는 평문 입력값을 가진 테스트를 내보낼 때 그 값이 확인
화면에 나열되는지 확인한다.

### Tests

- [ ] T077 [P] [US4] `backend/tests/contract/test_sharing_preview.py` — `plaintext_values` 에 스텝의 평문 입력값이 위치와 함께 나오고 `{{VAR}}` 참조는 제외되는지, 120자 초과가 `truncated: true` 로 잘리는지 (contracts §1)
- [ ] T078 [P] [US4] `backend/tests/contract/test_sharing_preview.py` — 미리보기가 **파일을 만들지 않고 프로젝트를 바꾸지 않는지** (FR-008). 호출 전후 프로젝트 디렉터리의 mtime 비교
- [ ] T079 [P] [US4] `backend/tests/unit/test_sharing_preview.py` — 읽을 수 없는 테스트가 `unreadable` 에 잡히되 미리보기를 실패시키지 않는지 (research R11)

### Implementation

- [ ] T080 [US4] `backend/src/itb/sharing/builder.py` 에 `review_export(project, tests, unreadable) -> ExportReview` 를 구현한다 — `test_count`, `group_count`, `start_urls`, `plaintext_values`, `required_values`, `unreadable` (contracts §1)
- [ ] T081 [US4] `plaintext_values` 는 **마스킹하지 않는다.** 가려 놓으면 사번이 섞여 있어도 발견할 수 없다 — 이 화면의 목적이 값을 보여 주는 것이다. 판단 근거를 코드 주석에 남긴다 (research R11)
- [ ] T082 [US4] `backend/src/itb/api/routes/sharing.py` 에 `GET /api/share/export/preview` 를 구현한다. `test_ids` 쿼리를 받는다 (contracts §1)
- [ ] T083 [US4] `frontend/src/pages/ShareExport.tsx` 에 확인 단계를 넣는다 — 요약을 본 뒤에만 내려받기가 활성화된다. 취소하면 파일이 만들어지지 않는다 (US4 AS2)
- [ ] T084 [US4] 시작 URL 을 「함께 나가는 정보」로 표시한다 (US4 AS3)
- [ ] T085 [P] [US4] `frontend/src/pages/__tests__/ShareExportPreview.test.tsx` — 확인 전에는 내려받기가 막히고, 평문 값이 가려지지 않은 채 나열되는지

**Checkpoint**: 실수로 내보내는 경로가 닫혔다.

---

## Phase 7: User Story 5 — 이미 있는 프로젝트에 받은 테스트를 더한다 (P3)

**Goal**: 열린 프로젝트에 테스트를 더하되, 식별자가 겹쳐도 기존 테스트가 사라지지 않는다.

**Independent Test**: `TC-001` 이 있는 프로젝트에 `TC-001` 을 담은 파일을 가져와 둘 다
남아 있는지 확인한다.

### Tests

- [ ] T086 [P] [US5] `backend/tests/integration/test_sharing_merge.py` — **C6** `TC-001` 충돌 시 둘 다 남고 `renumbered` 에 `TC-001 → TC-00N` 이 보고되는지 (FR-025, SC-005)
- [ ] T087 [P] [US5] `backend/tests/unit/test_sharing_group_mapping.py` — research R6 의 표 4행 각각 — 같은 이름 재사용, 신규 생성, 접두어 충돌 시 대체 접두어, 확보 실패 시 건너뜀 — 을 확인한다
- [ ] T088 [P] [US5] `backend/tests/unit/test_sharing_capacity.py` — 그룹 999 가 찼을 때 **계획 단계에서** `blocking` 에 잡히고 확정 중 바닥나는 상태가 생기지 않는지 (research R6)
- [ ] T089 [P] [US5] `backend/tests/abnormal/test_sharing_merge_failure.py` — 병합 도중 실패 시 새 파일이 하나도 남지 않는지 (US5 AS4)

### Implementation

- [ ] T090 [US5] `backend/src/itb/sharing/planner.py` 에 `target="current"` 경로를 구현한다. 식별자 재부여는 `repository.allocate_test_id` 의 규칙(그룹마다 1번부터, 빈 번호 채움)을 따른다 (research R6)
- [ ] T091 [US5] `planner.py` 에 그룹 대응 규칙을 구현한다 — 이름 기준 재사용, 접두어 충돌 시 대체 접두어(`USER` → `USER2`, 8자 상한 안), 확보 실패 시 그 그룹 건너뜀 + 사유 (research R6 표)
- [ ] T092 [US5] `planner.py` 에 그룹별 `capacity` 를 산출해 계획에 싣는다. 부족하면 `blocking` 에 넣는다
- [ ] T093 [US5] `backend/src/itb/sharing/applier.py` 에 `apply_current_project(plan, ...) -> ShareReport` 를 구현한다. `itb.storage.test_moves.run_all(validate, do, undo)` 를 쓴다 — `AllOrNothingError` / `PartialFailureError` 를 각각 `SHARE_IMPORT_FAILED` / `SHARE_IMPORT_PARTIAL` 로 옮긴다 (research R5, data-model §7)
- [ ] T094 [US5] `frontend/src/pages/TestList.tsx` 에 「이 프로젝트로 가져오기」 진입점을 더한다
- [ ] T095 [US5] `ShareImport.tsx` 가 `target=current` 계획에서 **바뀔 식별자를 강조**해 보여 주게 한다. 확정 후에도 `renumbered` 를 결과에 남긴다 (US5 AS2)

**Checkpoint**: 다섯 스토리 전부 동작한다.

---

## Phase 8: Polish & 교차 관심사

- [ ] T096 [P] `backend/tests/e2e/test_share_roundtrip.py` — 헌법 게이트 2(왕복 무결성). `record → store → export → import → replay` 를 **작업 공간을 갈라** 끝까지 돌리고 실행 결과가 일치하는지 (SC-003, quickstart §3-3·§4-4)
- [ ] T097 [P] 규모 확인 — 테스트 50건으로 내보내기·가져오기가 각각 10초 이내이고 화면이 멈추지 않는지 (SC-008, quickstart §6). 넘으면 어디서 시간이 드는지 기록한다
- [ ] T098 [P] `backend/tests/abnormal/test_sharing_limits.py` — 20MB 초과 파일이 **파싱 없이** `SHARE_BUNDLE_TOO_LARGE` 로 거부되는지 (research R12)
- [ ] T099 [P] `backend/tests/contract/test_sharing_guard.py` — **C10** `/api/share/*` 가 어긋난 `X-ITB-Project-Root` 에서 `PROJECT_MISMATCH` 로 거절되는지 (contracts §머리말)
- [ ] T100 [P] 진행 상황 표시 — 내보내기·가져오기 중 화면에 진행이 보이게 한다 (spec Edge Cases, SC-008)
- [ ] T101 [P] `docs/` 에 묶음 형식을 문서화한다 — 최상위 키, 버전 정책, **민감 값이 들어가지 않는 이유**. 헌법 원칙 V 의 "문서화된 평문 형식" 의무를 이 파일이 받는다
- [ ] T102 [P] 모르는 스텝 종류를 만났을 때의 처리를 확인한다 — 조용히 빠뜨리지 않고 결과에 명시하는지 (spec Edge Cases). 현재 `Test` 검증이 거부하므로 그 사유가 사용자에게 읽히는 말로 나오는지 본다
- [ ] T103 [P] `frontend/` 에서 `npm run gen:types` 후 `git diff --exit-code src/types/generated` 가 깨끗한지 CI 관점에서 확인한다 (quickstart §1)
- [ ] T104 [quickstart.md](quickstart.md) 7장 완료 판정 항목을 **실제로 돌려** 전부 통과시킨다. SC-007(원인 파악 가능성)은 자동 검증이 불가능하므로 **수동 확인 항목**으로 남기고 결과를 적는다. 통과하지 못한 항목은 사유와 함께 남긴다 — 통과한 것처럼 보고하지 않는다

---

## Dependencies & 실행 순서

### 단계 의존

```
Phase 1 (Setup) → Phase 2 (Foundational) ─┬→ Phase 3 (US1) ──→ Phase 6 (US4)
                                          │
                                          ├→ Phase 4 (US2) ─┬→ Phase 5 (US3)
                                          │                 └→ Phase 7 (US5)
                                          │
                                          └────────────────────→ Phase 8 (Polish)
```

- **Phase 2 는 절대 차단이다.** 묶음 모델·도메인 변경 없이는 어떤 스토리도 시작할 수 없다.
- **US1 → US4**: US4 는 US1 의 내보내기 화면에 확인 단계를 붙인다.
- **US2 → US3**: US3 는 가져오기 결과 화면에 값 입력을 붙인다.
- **US2 → US5**: US5 는 planner/applier 에 `target=current` 경로를 더한다.
- **US1 과 US2 는 서로 독립이다.** 다만 US2 의 왕복 테스트(T037)는 US1 의 산출물을 입력으로
  쓰므로, 두 스토리를 병렬로 진행하면 T037 는 US1 완료 후에 돈다.

### 스토리별 독립 검증

| 스토리 | 이것만 끝냈을 때 확인할 수 있는 것 |
|---|---|
| US1 | 파일이 만들어지고, 민감 값이 들어 있지 않다 (SC-004) |
| US2 | 파일이 복원되고, 스텝이 로케이터 후보까지 같다 (SC-003의 절반) |
| US3 | 값을 채우면 실행이 통과하고, 비면 브라우저가 뜨기 전에 막힌다 |
| US4 | 나가는 평문 값이 미리 보이고, 취소하면 아무것도 만들어지지 않는다 |
| US5 | 겹치는 식별자가 있어도 기존 테스트가 사라지지 않는다 (SC-005) |

### 병렬 실행 예

**Phase 2 에서** — T008·T009 는 서로 다른 파일이므로 함께:

```
T008 tests/unit/test_domain_provenance.py
T009 tests/unit/test_domain_variable_fields.py
```

**Phase 3 에서** — 테스트 4건이 전부 다른 파일:

```
T017 T018 (contract/test_sharing_export.py — 같은 파일이므로 순서대로)
T019 (unit/test_sharing_builder.py)
T021 (abnormal/test_sharing_export_empty.py)
```

**Phase 4 에서** — 테스트 7건이 서로 다른 파일이므로 T031~T038 을 함께 쓴다.
구현은 `reader.py`(T039~T042) → `plan_store.py`(T043) → `planner.py`(T044~T046) →
`applier.py`(T047~T049) 순으로, 앞의 산출이 뒤의 입력이므로 직렬이다.
프론트엔드 T055·T060 은 백엔드와 병렬로 진행할 수 있다.

---

## Implementation Strategy

### MVP 범위

**Phase 1 + 2 + 3 (US1)** — 파일을 만들어 건넬 수 있다. 여기서 멈춰도 "무엇을 공유하는가"
가 검증된다. 다만 받는 쪽이 없으므로 **사용자에게 내보내는 증분은 아니다.**

**실질적인 최소 전달 단위는 Phase 1+2+3+4+5 (US1·US2·US3)** 이다. 셋이 모여야 "동료의
테스트를 받아 실행한다" 가 성립한다. 스펙이 셋 모두에 P1 을 준 이유다.

### 증분 전달

1. **1차** — Phase 1~5 (US1·US2·US3). 공유가 끝까지 동작한다
2. **2차** — Phase 6 (US4). 되돌릴 수 없는 조작 앞의 방어선
3. **3차** — Phase 7 (US5). 기존 프로젝트로 합치기
4. **마무리** — Phase 8. 왕복 e2e·규모·문서

### 중간에 멈출 때의 안전

각 Phase 끝의 Checkpoint 에서 멈춰도 제품이 깨지지 않는다. 다만 **Phase 4 만 하고 Phase 5 를
건너뛰면 안 된다** — 가져왔는데 실행되지 않는 테스트가 목록에 쌓이고, 받은 사람은 이유를 알
방법이 없다. 그 상태가 이 기능이 없는 것보다 나쁘다.
