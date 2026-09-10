---

description: "Task list for 014 엑셀로 프로젝트 내보내기·가져오기"
---

# Tasks: 엑셀로 프로젝트 내보내기·가져오기

**Input**: Design documents from `/specs/014-excel-project-io/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/rest-api.md](contracts/rest-api.md), [quickstart.md](quickstart.md)

**Tests**: 테스트 과제를 **포함한다**. 선택이 아니라 헌법 품질 게이트 3의 요구다 —
"제품은 테스트 도구다. 자기 테스트 없이 내보내는 것은 받아들일 수 없다."
Recorder·Runner·Generator 는 건드리지 않으므로 그쪽 단위 테스트 의무는 발생하지 않지만,
사용자에게 보이는 흐름마다 e2e 시나리오가 하나씩 필요하다.

**Organization**: 사용자 이야기별로 묶었다. 각 묶음은 독립적으로 구현·검증·전달할 수 있다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (서로 다른 파일, 미완료 과제에 의존하지 않음)
- **[Story]**: 어느 사용자 이야기에 속하는지 (US1~US4)
- 모든 과제에 정확한 파일 경로가 있다

## Path Conventions

웹 애플리케이션 2분할이다 — `backend/src/itb/`, `frontend/src/`.
테스트는 `backend/tests/{unit,contract,integration,e2e,abnormal}/`, `frontend/tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 의존성과 경계 계약을 먼저 세운다. 계약을 나중에 넣으면 이미 어긴 코드를 고치게 된다.

- [X] T001 `openpyxl` 을 런타임 의존성에 추가한다 — `backend/pyproject.toml` 의 `dependencies` 에 `"openpyxl>=3.1"` 을 넣고 `uv sync` 로 잠금 파일을 갱신한다 ([research.md](research.md) R1)
- [X] T002 `backend/.importlinter` 의 `execution-no-llm` 계약 `source_modules` 에 `itb.portability` 를 추가한다. **T003 보다 먼저 한다** — 계약을 먼저 세워야 이후 코드가 처음부터 그 안에서 자란다 ([research.md](research.md) R2)
- [X] T003 [P] `backend/src/itb/portability/__init__.py` 를 만들어 패키지를 연다. 모듈 머리말에 "남의 파일 형식을 다루는 곳이며, 우리 자산 형식은 `itb.storage` 가 맡는다"를 적는다
- [X] T004 [P] `backend/src/itb/portability/limits.py` — 이 기능 고유 상한을 정의한다: `MAX_UPLOAD_BYTES = 100 * 1024 * 1024`, `MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024`, `MAX_COMPRESSION_RATIO = 100`, `MAX_SHEETS = 200`, `MAX_DATA_ROWS = 5000`, `MAX_CELL_CHARS = 32767`. 제품 공통 상한(999 등)은 **여기서 정의하지 않는다** ([contracts/rest-api.md](contracts/rest-api.md) §6)
- [X] T005 `uv run lint-imports` 와 `uv run pytest` 를 돌려 T001~T004 가 기존 것을 깨지 않았는지 확인한다

**Checkpoint**: 의존성과 경계가 서 있다. 이제 도메인을 건드릴 수 있다.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 사용자 이야기가 딛는 바닥. 도메인 모델·오류 코드·스키마 재생성·초안 저장.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 사용자 이야기도 시작할 수 없다.

### 도메인

- [X] T006 `backend/src/itb/domain/test_case.py` 에 `MAX_TEST_NUMBER = 999` 를 정의하고 `Project.next_test_number` 의 `le=999` 를 `le=MAX_TEST_NUMBER` 로 바꾼다 ([data-model.md](data-model.md) §4)
- [X] T007 흩어진 999 를 T006 의 상수로 모은다 — `backend/src/itb/storage/repository.py:323` 과 `backend/src/itb/api/routes/tests.py:482` 두 곳. FR-036c 가 요구하는 것은 "값이 같다"가 아니라 "출처가 하나다"이다
- [X] T008 `backend/src/itb/domain/test_case.py` 의 `Test` 에 `description: str | None`(max_length=2000)과 `actor: str | None`(max_length=100)을 더한다. 기본값 `None`, 필드 위치는 `name` 뒤. **`dsl_version` 은 올리지 않는다** — 올리면 `_check_refs` 가 기존 파일을 전부 거절한다 ([research.md](research.md) R11)
- [X] T009 [P] `backend/src/itb/domain/draft.py` 를 새로 만든다 — `DRAFT_ID_PATTERN`, `MAX_DRAFT_NUMBER`, `DraftSource`, `Draft`. **`steps` 필드를 두지 않는다** (원칙 I). 검증 규칙 4개를 모두 넣는다 ([data-model.md](data-model.md) §2)
- [X] T010 [P] `backend/src/itb/domain/draft.py` 에 지시문 조립 순수 함수 `compose_instruction(draft) -> str` 을 더한다. 빈 항목은 줄째로 뺀다. 결과가 `MAX_INSTRUCTION_LENGTH`(8000)를 넘지 않음을 필드 상한의 합으로 보장한다 ([research.md](research.md) R12)
- [X] T011 `backend/src/itb/domain/error.py` 에 오류 코드 7개를 더하고 `CATEGORY`·`NEXT_ACTION` **두 표를 함께** 채운다 — 빠지면 `tests/abnormal/test_error_contract.py` 가 실패한다 ([data-model.md](data-model.md) §7)

### 스키마 재생성 (건너뛰면 CI 가 막는다)

- [X] T012 `backend/src/itb/schema/export.py` 의 `MODELS` 에 `"draft": TypeAdapter(Draft)` 를 더한다
- [X] T013 `cd backend && uv run python -m itb.schema.export` 를 돌려 `backend/schema/` 를 재생성하고 커밋한다 — `step-dsl`, `error-response`, 신규 `draft` 세 개가 바뀐다
- [X] T014 `cd frontend && npm run gen:types` 를 돌려 `frontend/src/types/generated/` 를 재생성하고 커밋한다
- [X] T015 `cd backend && uv run python -m itb.schema.export --check` 로 드리프트가 없음을 확인한다

### 저장

- [X] T016 [P] `backend/src/itb/storage/drafts.py` 를 새로 만든다 — `drafts/` 경로 해석, `list_drafts()`, `read_draft(id)`, `write_draft(draft)`, `delete_draft(id)`, `allocate_draft_id()`. 파일명은 `<draft_id>-<slug>.yaml`, 기존 `yaml_io` 를 그대로 쓴다 ([data-model.md](data-model.md) §2)
- [X] T017 `backend/src/itb/storage/repository.py` 에 `drafts_dir` 경로와 초안 접근자를 잇는다. `list_test_paths()` 가 `drafts/` 를 훑지 않음을 확인한다 (디렉터리가 다르므로 구조적으로 보장되지만 테스트로 못박는다)

### 공유 규약

- [X] T018 [P] `backend/src/itb/portability/columns.py` — 7개 컬럼의 이름·순서·머리글 대조 규칙. 내보내기와 가져오기가 **같은 정의**를 쓴다. 머리글 대조는 앞뒤 공백 제거 + 대소문자 무시, 필수 컬럼은 `TC ID`·`대상기능` ([data-model.md](data-model.md) §6)
- [X] T019 [P] `backend/src/itb/portability/sheet_name.py` — 그룹 이름 → 시트 이름 변환 순수 함수 6단계와, 그룹 없음 시트 이름 상수 `그룹 없음` ([research.md](research.md) R6)
- [X] T020 [P] `backend/src/itb/portability/workbook.py` 에 수식 주입 방어 `escape_cell(value)` 를 둔다 — `= + - @`, 탭, 캐리지리턴으로 시작하면 앞에 `'` 를 붙인다 ([research.md](research.md) R13)

### 기반 테스트

- [X] T021 [P] `backend/tests/unit/test_sheet_name.py` — 금지문자, 31자 초과, 빈 이름, `History` 예약어, 충돌 시 `~2` 접미, 충돌 접미가 31자를 넘지 않음
- [X] T022 [P] `backend/tests/unit/test_excel_columns.py` — 머리글 대조(공백·대소문자), 필수 컬럼 누락 판정, 컬럼 순서 고정
- [X] T023 [P] `backend/tests/unit/test_formula_escape.py` — `=1+1`·`+A1`·`-1`·`@SUM` 이 텍스트로 고정되는지, 정상 문자열은 건드리지 않는지
- [X] T024 [P] `backend/tests/unit/test_draft_model.py` — `Draft` 검증 규칙 4개, `compose_instruction` 의 빈 항목 생략과 길이 상한
- [X] T025 [P] `backend/tests/integration/test_legacy_project_reads.py` — **`description`·`actor` 가 없는 기존 테스트 YAML 이 그대로 읽히는지.** T008 이 하위호환을 깼는지 잡는 유일한 검사다 ([quickstart.md](quickstart.md) §3 회귀 1)
- [X] T026 `cd backend && uv run pytest && uv run lint-imports && uv run ruff check src/ tests/` 로 Phase 2 전체를 확인한다

**Checkpoint**: 바닥이 섰다. US1·US2 를 병렬로 시작할 수 있다.

---

## Phase 3: User Story 1 - 프로젝트를 스프레드시트로 내보낸다 (Priority: P1) 🎯 MVP

**Goal**: 열린 프로젝트를 워크북 하나로 만들어 내려받는다. 그룹 = 시트, 테스트 = 행, 컬럼 7개 고정.

**Independent Test**: 그룹 2개와 미그룹 테스트가 섞인 프로젝트에서 내보내기를 실행하고, 받은 파일을 스프레드시트 도구로 열어 시트 수·행 수·각 칸을 눈으로 확인한다. 가져오기는 필요 없다.

### Tests for User Story 1 ⚠️

> 먼저 쓰고, 실패하는 것을 확인한 뒤 구현한다.

- [X] T027 [P] [US1] `backend/tests/contract/test_excel_export_api.py` — `GET /api/project/export` 의 200 응답(MIME·`Content-Disposition` 두 이름·`X-ITB-Export-Warnings`), 404 `PROJECT_NOT_OPEN`, `GET /api/project/export/warnings` 의 응답 형태 ([contracts/rest-api.md](contracts/rest-api.md) §1)
- [X] T028 [P] [US1] `backend/tests/integration/test_export_no_secrets.py` — 민감 변수를 쓰는 테스트가 있는 프로젝트를 내보내고, 만들어진 워크북 바이트 어디에도 그 값이 없으며 `{{SECRET_*}}` 참조는 남아 있는지 (FR-007 · SC-008)
- [X] T029 [P] [US1] `backend/tests/integration/test_export_shapes.py` — 시트 수·순서(`그룹 없음` 우선 → `Project.groups` 저장 순), 빈 그룹의 머리글만 있는 시트, 행의 TC ID 정렬, 절차/기대 결과의 검증 스텝 분리, 결과 칸 다섯 표기, 셀 한도 초과 시 자름 표시 (FR-002~FR-006a · FR-010)
- [X] T030 [P] [US1] `backend/tests/e2e/test_us7_excel_export.py` — 프로젝트를 만들고 테스트를 저장하고 실행한 뒤 내보내 워크북을 다시 읽어 확인하는 한 흐름
- [X] T031 [P] [US1] `frontend/tests/ExcelExport.test.tsx` — 내보내기 버튼이 blob 을 받아 저장을 트리거하는지, 실패 시 오류 알림이 뜨는지

### Implementation for User Story 1

- [X] T032 [US1] `backend/src/itb/portability/workbook.py` 에 쓰기 쪽을 구현한다 — `write_workbook(sheets) -> bytes`. `openpyxl` 과 닿는 유일한 지점이며 `BytesIO` 로 만든다 ([research.md](research.md) R9)
- [X] T033 [US1] `backend/src/itb/portability/exporter.py` — `Project` + `Test[]` + 최근 실행 결과 → 시트·행. 절차/기대 결과 조립(번호 매김·자름 표시), 결과 칸 다섯 표기 매핑, 경고 수집 ([research.md](research.md) R5 · [data-model.md](data-model.md) §6)
- [X] T034 [US1] `backend/src/itb/api/routes/project.py` 에 `GET /api/project/export` 와 `GET /api/project/export/warnings` 를 더한다. `Content-Disposition` 은 ASCII 대체 이름과 RFC 5987 이름을 **둘 다** 싣는다. 읽을 수 없는 정의가 있어도 성공하고 경고에 잡는다
- [X] T035 [US1] `frontend/src/api/client.ts` 에 `excel` 네임스페이스를 더한다 — `exportProject()` 는 `send()` 로 헤더를 붙여 요청하고 `blob()` 으로 받는다. `<a href>` 로 끝내지 않는다 (`X-ITB-Project-Root` 가드가 빠진다) ([research.md](research.md) R10)
- [X] T036 [US1] `frontend/src/api/client.ts` 에 blob 저장 도우미를 더한다 — `createObjectURL` → 보이지 않는 `<a download>` 클릭 → `revokeObjectURL`. 이 저장소의 첫 파일 내려받기 사례다
- [X] T037 [US1] `frontend/src/pages/TestList.tsx` 의 목록 조작 띠(「번호 정리」가 있는 줄)에 「엑셀로 내보내기」를 더한다. **`btn primary` 를 쓰지 않는다** — 이 화면의 잉크 채움은 「테스트 만들기」 하나뿐이라는 규칙이 파일 주석에 있다
- [X] T038 [US1] 내보내기 실패와 경고를 사용자에게 알린다 — 기존 알림 체계(`NoticeStack`)를 쓰고 새 알림 방식을 만들지 않는다 (FR-013)

**Checkpoint**: US1 만으로 "설계·결과를 팀 형식으로 꺼낸다"가 성립한다. 여기까지가 MVP다.

---

## Phase 4: User Story 2 - 설계 스프레드시트를 넣어 초안을 만든다 (Priority: P1)

**Goal**: 파일을 해석해 미리보기를 보이고, 확정하면 그룹과 초안을 전부-아니면-전무로 만든다.

**Independent Test**: 시트 2개짜리 파일을 가져와 프로젝트에 그룹 2개와 예상한 수의 초안이 생겼는지 목록에서 확인한다. 녹화는 하지 않아도 된다.

### Tests for User Story 2 ⚠️

- [X] T039 [P] [US2] `backend/tests/unit/test_import_defenses.py` — 3겹 방어: 바이트 상한, 압축 해제 총량·압축비(zip 폭탄), 시트·행 구조 상한. 각각 해석을 **시작하기 전에** 거절하는지 ([research.md](research.md) R3)
- [X] T040 [P] [US2] `backend/tests/unit/test_import_planning.py` — 접두어 읽어내기, 읽어낼 수 없는 시트의 `needs_prefix`, 한 시트 안 접두어 혼재, 파일 내 TC ID 중복 재번호, 건너뛸 행 3종(`no_title`·`no_columns`·`empty`), 기존 그룹 이름 유지 판정 (FR-022~FR-024a)
- [X] T041 [P] [US2] `backend/tests/contract/test_excel_import_api.py` — `POST /api/import/preview`·`/commit`·`/create-project` 의 요청·응답 형태와 오류 코드 전부 ([contracts/rest-api.md](contracts/rest-api.md) §2·§3)
- [X] T042 [P] [US2] `backend/tests/integration/test_import_atomicity.py` — 확정 도중 실패 시 그룹도 초안도 하나도 남지 않는지(`IMPORT_FAILED`), 되돌림까지 실패하면 `IMPORT_PARTIAL` 과 `stranded` 가 나오는지 (FR-025)
- [X] T043 [P] [US2] `backend/tests/integration/test_import_capacity.py` — 남은 번호보다 많이 만들려 할 때 **아무것도 만들기 전에** 거절하고 필요한 수·남은 수를 알리는지 (FR-036b · SC-010)
- [X] T044 [P] [US2] `backend/tests/integration/test_import_new_project.py` — 새 프로젝트를 만들며 가져오기 성공 흐름과, 도중 실패 시 만들다 만 프로젝트가 남지 않는지 (FR-014a~c)
- [X] T045 [P] [US2] `backend/tests/e2e/test_us8_excel_import.py` — 시트 3개(그룹 없음·접두어 있음·접두어 없음)짜리 파일로 미리보기 → 취소 → 다시 → 접두어 입력 → 확정까지 한 흐름
- [X] T046 [P] [US2] `frontend/tests/ImportPreview.test.tsx` — 미리보기가 그룹 수·초안 수·건너뛸 행·번호 변경·이름 차이를 보이는지, 접두어 입력 칸이 `needs_prefix` 시트에만 나오는지, 취소가 아무것도 만들지 않는지
- [X] T047 [P] [US2] `frontend/tests/abnormal/excel-blockers.test.tsx` — 파일 거절·계획 만료·수용량 초과 각각에 대해 사유와 다음 행동이 화면에 나오는지

### Implementation for User Story 2

- [X] T048 [US2] `backend/src/itb/portability/workbook.py` 에 읽기 쪽을 구현한다 — `read_workbook(data) -> ParsedWorkbook`. `zipfile.ZipFile.infolist()` 로 **열기 전에** 압축 해제 총량을 검사하고, `read_only=True` 로 흘려 읽으며 구조 상한에서 즉시 중단한다. openpyxl 타입을 밖으로 흘리지 않는다
- [X] T049 [US2] `backend/src/itb/portability/importer.py` — `ParsedWorkbook` + 열린 프로젝트 상태 → `ImportPlan`. `SheetPlan`·`RowPlan`·`SkippedRow` 를 채우고, 접두어 판정·중복 재번호·기존 그룹 대조를 한다 ([data-model.md](data-model.md) §5)
- [X] T050 [US2] `backend/src/itb/api/state.py` 에 가져오기 계획 보관소를 더한다 — 30분 수명, 최대 8개, 넘으면 오래된 것부터 버린다. 디스크에 쓰지 않는다 ([research.md](research.md) R8)
- [X] T051 [US2] `backend/src/itb/api/routes/excel.py` 를 새로 만들고 `POST /api/import/preview` 를 구현한다. 업로드는 상한+1 바이트만 읽어 판정하는 기존 수법을 쓴다 (`session_files.py:66`)
- [X] T052 [US2] `backend/src/itb/api/routes/excel.py` 에 `POST /api/import/commit` 을 구현한다. 순서가 계약이다 — 수용량 검사 → 그룹 쓰기 → `test_moves.run_all` 로 초안 쓰기 → 실패 시 역순 되돌림 ([data-model.md](data-model.md) §8)
- [X] T053 [US2] `backend/src/itb/api/routes/excel.py` 에 `POST /api/import/create-project` 를 구현한다. 실패 시 만든 프로젝트를 휴지통으로 옮기고 레지스트리에서 지운다 (FR-014c)
- [X] T054 [US2] `backend/src/itb/api/routes/drafts.py` 를 새로 만든다 — `GET /api/drafts`, `GET /api/drafts/{id}`, `DELETE /api/drafts/{id}` ([contracts/rest-api.md](contracts/rest-api.md) §4)
- [X] T055 [US2] `backend/src/itb/api/app.py` 의 `ROUTERS` 에 `excel` 과 `drafts` 라우터를 등록한다
- [X] T056 [US2] `backend/src/itb/api/routes/tests.py` 의 `TestListResponse` 에 `draft_count` 를 더한다. 초안을 `tests` 에 섞지 않는다 (FR-027)
- [X] T057 [US2] `frontend/src/api/client.ts` 에 `imports`·`drafts` 네임스페이스를 더한다. 업로드는 `FormData` + `fetch` 이되 **`X-ITB-Project-Root` 를 손으로 붙인다** — 기존 `sessions.uploadFile` 을 그대로 베끼면 가드가 빠진다 ([research.md](research.md) R10)
- [X] T058 [P] [US2] `frontend/src/pages/ImportPreview.tsx` 를 새로 만든다 — 요약, 시트별 행(접두어 입력 칸 포함), 건너뛸 행 목록, 번호 변경 목록, 이름 차이 알림, 취소·확정
- [X] T059 [US2] `frontend/src/pages/TestList.tsx` 에 「엑셀에서 가져오기」 진입점과 초안 영역을 더한다. 초안은 테스트와 시각적으로 구분되어야 한다 (FR-027)
- [X] T060 [US2] `frontend/src/pages/ProjectSetup.tsx` 의 버튼 줄에 「엑셀에서 새 프로젝트」를 세 번째로 더하고, 이름·시작 URL·저장 위치를 받는 흐름을 잇는다. 프로젝트 이름은 파일 이름을 기본값으로 제안한다 (FR-014b)
- [X] T061 [US2] `frontend/src/App.tsx` 의 `Screen` 유니온에 미리보기 화면을 더하고 전환을 잇는다

**Checkpoint**: US1 과 US2 가 각각 독립적으로 동작한다. 설계서를 손 입력 없이 옮길 수 있다.

---

## Phase 5: User Story 3 - 초안을 AI 녹화로 완성한다 (Priority: P1)

**Goal**: 초안에서 기존 AI 작성 경로로 진입하고, 저장하면 희망 번호를 받고 초안이 사라진다.

**Independent Test**: 초안 1건을 만들어 두고(손으로 파일을 놓거나 US2 로) 녹화를 시작해 저장한 뒤, 초안이 사라지고 테스트가 생겼는지 확인한다. US2 없이도 검증 가능하다.

### Tests for User Story 3 ⚠️

- [X] T062 [P] [US3] `backend/tests/contract/test_drafts_api.py` — 초안 목록·조회·삭제, `suggested_instruction` 이 실리는지, `desired_id_available` 판정, 404 `DRAFT_NOT_FOUND`
- [X] T063 [P] [US3] `backend/tests/integration/test_draft_to_test.py` — 희망 번호가 비어 있을 때 그 번호를 받는지, 이미 쓰였을 때 다른 번호를 받고 **그 사실이 응답에 실리는지**, 저장 성공 시 초안이 사라지고 버렸을 때 남는지 (FR-032·FR-033)
- [X] T064 [P] [US3] `backend/tests/integration/test_draft_no_number_reservation.py` — 초안이 있는 상태에서 새 테스트를 만들거나 「번호 정리」를 돌려도 충돌하지 않는지. 초안은 번호를 예약하지 않는다 ([quickstart.md](quickstart.md) §3 회귀 3·4)
- [X] T065 [P] [US3] `backend/tests/e2e/test_us9_draft_recording.py` — 초안에서 세션을 열어 지시문이 채워져 있고, 녹화·저장까지 가서 테스트가 되고, 다시 내보내면 `테스트항목`·`수행자` 가 살아 있는 한 흐름 (**왕복이 이어지는지**)
- [X] T066 [P] [US3] `frontend/tests/DraftList.test.tsx` — 초안 목록이 남은 수를 보이고 녹화 시작·삭제가 되는지
- [X] T067 [P] [US3] `frontend/tests/DraftToRecording.test.tsx` — 초안에서 시작한 작성 화면의 지시문 칸이 채워져 있고 고칠 수 있는지, 희망 번호를 못 받았을 때 알림이 뜨는지

### Implementation for User Story 3

- [X] T068 [US3] `backend/src/itb/api/routes/sessions.py` 의 `CreateSessionRequest` 에 `draft_id` 를 더한다. `mode == "ai"` 일 때만 허용하고, `ai_instruction` 이 함께 오면 그것을 쓴다. **새 상태나 전이를 만들지 않는다** ([contracts/rest-api.md](contracts/rest-api.md) §5)
- [X] T069 [US3] `backend/src/itb/api/routes/sessions.py` 의 `SessionWork` 가 `draft_id` 를 저장까지 들고 가게 한다
- [X] T070 [US3] `backend/src/itb/api/routes/sessions.py` 의 저장 경로를 고친다 — 초안의 희망 번호를 부여하려 시도하고, 실패하면 `allocate_test_id` 로 받고 `desired_id_taken` 을 응답에 싣는다. 저장이 성공하면 초안 파일을 지운다 (FR-032·FR-033)
- [X] T071 [US3] 저장 시 초안의 `description`·`actor` 를 `Test` 에 옮긴다. 이것이 없으면 다시 내보낼 때 두 칸이 빈다 — 왕복이 끊긴다 ([research.md](research.md) R11)
- [X] T072 [P] [US3] `frontend/src/pages/DraftList.tsx` 를 새로 만든다 — 초안 목록, 남은 수, 출처(파일·시트·행), 희망 번호와 그 가용 여부, 녹화 시작·삭제
- [X] T073 [US3] `frontend/src/pages/ComposeView.tsx` 가 초안에서 온 경우 지시문을 미리 채우고 고칠 수 있게 한다 (FR-031)
- [X] T074 [US3] 희망 번호를 주지 못했을 때 사용자에게 알린다 — 조용히 다른 번호를 주면 안 된다 (FR-032)

**Checkpoint**: 세 P1 이야기가 모두 동작한다. 스프레드시트에서 실제 테스트 자산까지 이어진다.

---

## Phase 6: User Story 4 - 내보낸 파일을 결과 보고로 쓴다 (Priority: P3)

**Goal**: 표에 서식을 입혀 가공 없이 회의 자료가 되게 한다.

**Independent Test**: 통과·실패·미실행이 섞인 프로젝트를 내보내 파일을 열고 세 상태가 시각적으로 구분되는지 본다.

- [ ] T075 [P] [US4] `backend/tests/integration/test_export_formatting.py` — 머리글 행 고정, 결과 칸의 상태별 서식이 서로 다른지, 열 너비가 설정되는지
- [ ] T076 [US4] `backend/src/itb/portability/workbook.py` 에 서식을 더한다 — 머리글 행 굵게·배경, `freeze_panes`, 결과 칸의 통과·실패·미실행·부분 통과·중지 다섯 상태 서식
- [ ] T077 [US4] `backend/src/itb/portability/workbook.py` 에 열 너비를 더한다. 「수행 절차」·「기대 결과」는 여러 줄이므로 줄바꿈을 켜고 넉넉히 잡는다

**Checkpoint**: 모든 사용자 이야기가 동작한다.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T078 [P] `README.md` 에 엑셀 내보내기·가져오기를 더한다. **「Playwright 로 내보내기」(릴리스 게이트 RG-1)와 다른 것임을 명시한다** — 두 「내보내기」가 헷갈리면 RG-1 이 해소된 것으로 오해된다 ([plan.md](plan.md) 헌법 점검)
- [ ] T079 [P] `docs/PENDING-HUMAN-VERIFICATION.md` 에 §14 를 더해 사람이 판정할 항목 5건을 등록한다 ([quickstart.md](quickstart.md) §4)
- [ ] T080 [P] `frontend/src/theme/tokens.css` 에 초안 구분용 토큰이 필요하면 더한다. 새 색을 즉석에서 만들지 않고 기존 시각 언어(008)를 따른다
- [ ] T081 `openpyxl` 이 XML 폭탄에 대해 `defusedxml` 을 자동으로 쓰는지 실물로 확인한다. 쓰지 않는다면 `portability/workbook.py` 의 읽기 경로에 XML 엔티티 검사를 더한다 ([research.md](research.md) R1 미해결 항목)
- [ ] T082 [quickstart.md](quickstart.md) §3 의 회귀 8건을 돌린다. **회귀 1(기존 프로젝트가 그대로 열린다)을 가장 먼저** 한다
- [ ] T083 전체 검증을 돌린다 — `uv run lint-imports`, `uv run ruff check src/ tests/`, `uv run pytest`, `uv run python -m itb.schema.export --check`, `npx tsc --noEmit`, `npm test -- --run`
- [ ] T084 손 검증을 돌린다 (**사람이 판정한다** · [docs/PENDING-HUMAN-VERIFICATION.md](../../docs/PENDING-HUMAN-VERIFICATION.md) §14) — [quickstart.md](quickstart.md) §2 의 네 이야기와 §4 의 판정 5건. `XDG_DATA_HOME`·`XDG_CONFIG_HOME` 을 임시 디렉터리로 지정해 실제 자산을 건드리지 않는다

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음. 바로 시작
- **Foundational (Phase 2)**: Setup 완료에 의존. **모든 사용자 이야기를 막는다**
- **US1 (Phase 3)** · **US2 (Phase 4)**: Foundational 완료 후 **병렬 가능**
- **US3 (Phase 5)**: Foundational 완료 후 시작 가능. 초안 파일을 손으로 놓으면 US2 없이도 검증된다
- **US4 (Phase 6)**: US1 의 `workbook.py` 쓰기 경로에 의존
- **Polish (Phase 7)**: 원하는 이야기가 모두 끝난 뒤

### 순서가 계약인 곳

- **T002 → T003**: import-linter 계약을 코드보다 먼저 세운다. 나중에 넣으면 이미 어긴 코드를 고치게 된다
- **T006 → T007**: 상수를 정의한 뒤 사용처를 고친다
- **T008 → T013 → T014**: 도메인 변경 → 백엔드 스키마 재생성 → 프론트 타입 재생성. 이 순서를 어기면 CI 의 `schema-drift` 가 막는다
- **T009 → T016**: 모델이 있어야 저장을 쓸 수 있다
- **T052 내부**: 수용량 검사 → 그룹 쓰기 → 초안 쓰기. 그룹을 먼저 쓰는 이유는 [data-model.md](data-model.md) §8 에 있다
- **T070 → T071**: 번호 부여가 정해진 뒤 필드를 옮긴다

### Within Each User Story

- 테스트를 먼저 쓰고 실패를 확인한 뒤 구현한다
- 모델 → 저장 → 서비스 → 엔드포인트 → 화면
- 한 이야기를 끝낸 뒤 다음 우선순위로 간다

### Parallel Opportunities

- **Phase 1**: T003·T004 병렬
- **Phase 2**: T009·T010 병렬 / T016·T018·T019·T020 병렬 / T021~T025 전부 병렬
- **Phase 3**: T027~T031 전부 병렬 (테스트)
- **Phase 4**: T039~T047 전부 병렬 (테스트), T058 은 백엔드와 병렬
- **Phase 5**: T062~T067 전부 병렬 (테스트), T072 는 백엔드와 병렬
- **Phase 7**: T078·T079·T080 병렬
- Foundational 이 끝나면 **US1 과 US2 를 서로 다른 사람이 동시에** 진행할 수 있다

---

## Parallel Example: User Story 2

```
# 테스트를 한꺼번에 쓴다 (전부 다른 파일)
T039 test_import_defenses.py      T040 test_import_planning.py
T041 test_excel_import_api.py     T042 test_import_atomicity.py
T043 test_import_capacity.py      T044 test_import_new_project.py
T045 test_us8_excel_import.py     T046 ImportPreview.test.tsx
T047 excel-blockers.test.tsx

# 그다음 구현은 의존 사슬을 탄다
T048 (workbook 읽기) → T049 (importer) → T050 (계획 보관소)
                                       → T051 (preview) → T052 (commit) → T053 (create-project)
# 화면은 계약이 정해져 있으므로 백엔드와 병렬로 간다
T058 (ImportPreview.tsx)
```

---

## Implementation Strategy

### MVP (여기서 멈춰도 가치가 있다)

**Phase 1 → 2 → 3 (US1)**. 내보내기만 있어도 "설계·결과를 팀 형식으로 꺼낸다"가 성립한다.
가져오기가 없어도 쓸모가 완결된다.

### 증분 전달

| 증분 | 얻는 것 |
|---|---|
| + Phase 4 (US2) | 설계서를 손 입력 없이 제품 안으로 옮긴다. 초안 목록이 "무엇을 만들어야 하는지"를 보여준다 |
| + Phase 5 (US3) | 초안이 실제 테스트 자산이 된다. 왕복이 닫힌다 |
| + Phase 6 (US4) | 내보낸 파일이 가공 없이 회의 자료가 된다 |

### 병렬 진행 (사람이 여럿일 때)

Phase 2 가 끝나면 US1 과 US2 를 나눠 가질 수 있다. 둘은 `columns.py`(T018)만 공유하고
그 밖에는 서로 다른 파일을 만진다. US3 는 US2 의 산출물을 쓰지만, 초안 YAML 을 손으로 놓으면
US2 를 기다리지 않고 시작할 수 있다.
