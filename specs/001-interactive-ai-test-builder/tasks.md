---

description: "Task list for Interactive AI Test Builder (MVP — P0 + P1)"
---

# Tasks: Interactive AI Test Builder (MVP — P0 + P1)

**Input**: Design documents from `/specs/001-interactive-ai-test-builder/`

**Prerequisites**: plan.md · spec.md (FR 134 / SC 12 / US 7) · research.md (R1~R8) · data-model.md ·
contracts/ (4) · quickstart.md · 헌법 v1.0.0

**Tests**: **포함한다.** 헌법 품질 게이트 3이 Recorder·Runner 상태 기계·Generator 각각의 단위 테스트와
사용자 향 흐름당 최소 1개의 종단 테스트를 요구한다. 게이트 4는 테스트 삭제·비활성화를 금지한다.
제품이 테스트 도구이므로 자체 테스트 없이 출하하는 것은 허용되지 않는다.

**Organization**: 작업은 사용자 스토리별로 묶어 각 스토리를 독립적으로 구현·검증할 수 있게 한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (서로 다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 대응 사용자 스토리 (US1~US7). Setup·Foundational·Polish 단계에는 붙이지 않는다
- 모든 작업에 정확한 파일 경로를 포함한다

## Path Conventions

`backend/src/itb/` · `backend/tests/{unit,contract,integration,e2e}/` · `frontend/src/` ·
`fixtures/sample-app/` — plan.md의 Project Structure를 따른다.

---

## Phase 0: 가정 검증 (Verification Spikes)

**Purpose**: research의 "검증 필요 사항" 8건은 **가정**이다. 틀리면 설계가 바뀐다. 코드를 쌓기 전에 확인한다.

**⚠️ 이 단계의 결과를 research.md에 반영한 뒤 다음 단계로 간다.** 가정이 깨지면 해당 R 항목을 다시 결정한다.

- [x] T001 `backend/` 에 최소 pyproject.toml 을 만들고 Playwright for Python + Python 3.13 설치 가능 여부를 확인한다. 실패 시 3.12로 내리고 research.md R1의 검증 항목을 갱신한다
- [x] T002 [P] PyNaCl 이 Python 3.13 / macOS arm64 에서 휠로 설치되는지 확인하고 결과를 `specs/001-interactive-ai-test-builder/research.md` R7의 검증 필요 사항에 기록한다
- [x] T003 `scripts/spikes/spike_session.py` — `async_playwright().start()` 로 띄운 `BrowserContext` 를 10분 이상 유지하며 CDP 연결이 끊기지 않는지 확인한다 (research R1)
- [x] T004 [P] `scripts/spikes/spike_binding.py` — `add_init_script` + `expose_binding` 을 **컨텍스트 단위로** 등록해 새 탭·네비게이션 직후에도 콜백이 유실 없이 도착하는지, `source` 인자로 발신 페이지를 식별할 수 있는지 확인한다 (research R2)
- [x] T005 [P] `scripts/spikes/spike_tabs.py` — `context.on("page")` 가 `window.open` 팝업과 `target="_blank"` 링크 **양쪽에서** 발생하는지 확인한다. 한쪽만 잡히면 `page.on("popup")` 보완이 필요하다 (research R1)
- [x] T006 [P] `scripts/spikes/spike_screencast.py` — headed 모드에서 `Page.startScreencast` 프레임률·프레임 크기를 실측하고, **창이 최소화·가려졌을 때 프레임이 계속 오는지** 확인한다. 멈추면 그것을 정상 동작으로 문서화한다 (research R3)
- [x] T007 [P] `scripts/spikes/spike_locator.py` — `get_by_role(role, name=...)` 의 이름 매칭이 부분 일치인지 완전 일치인지 확인해 `exact` 인자 사용 여부를 결정하고, `selectors.set_test_id_attribute` 호출 위치를 확인한다 (research R4)
- [x] T008 [P] `scripts/spikes/spike_agent.py` — `@beta_async_tool` + `tool_runner` 의 async 반복이 장기 실행 중 취소(사용자 일시정지)에 어떻게 반응하는지, `fallbacks="default"` 를 tool_runner 경로로 전달할 수 있는지 확인한다 (research R5)
- [x] T009 [P] `scripts/spikes/spike_schema.py` — Pydantic v2 판별 유니온이 `json-schema-to-typescript` 에서 판별 유니온으로 떨어지는지 확인한다. 안 되면 스키마 후처리 단계가 필요하다 (research R6)
- [x] T010 T001~T009 결과를 `specs/001-interactive-ai-test-builder/research.md` 의 각 "검증 필요 사항" 절에 반영하고, 가정이 깨진 항목의 Decision 절을 다시 쓴다

**Checkpoint**: 8개 가정이 확인되었고 설계 변경 사항이 research.md에 반영됨

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로젝트 초기화와 기본 구조

- [ ] T011 plan.md의 Project Structure대로 `backend/src/itb/{domain,locator,recording,execution,mirror,secrets,storage,generator,authoring,llm,schema,api}/` 와 `backend/tests/{unit,contract,integration,e2e}/` 디렉터리·`__init__.py` 를 만든다
- [ ] T012 `backend/pyproject.toml` 을 확정한다 — fastapi, uvicorn, playwright, pydantic, pyyaml, pynacl, anthropic, pytest, pytest-asyncio, import-linter
- [ ] T013 [P] `frontend/` 를 React + Vite + TypeScript 로 초기화하고 `frontend/package.json` 에 vitest·json-schema-to-typescript 를 추가한다
- [ ] T014 [P] `backend/pyproject.toml` 에 린터·포매터 설정을 넣고 `frontend/` 에 동등한 설정을 넣는다
- [ ] T015 `backend/.importlinter` 에 `execution-no-llm` **forbidden 계약**을 작성한다 — `source_modules = itb.execution, itb.storage, itb.generator, itb.locator, itb.domain` / `forbidden_modules = itb.llm, itb.authoring, anthropic` (헌법 원칙 II, research R5)
- [ ] T016 `.github/workflows/ci.yml` 을 만들고 `lint-imports` 를 **다른 검사보다 먼저** 실행하는 잡으로 넣는다. 실패 시 후속 잡을 실행하지 않고 빌드를 중단한다 (헌법 원칙 II)
- [x] T017 [P] `fixtures/sample-app/` 에 검증용 대상 앱을 만든다 — 로그인 화면, 프로젝트 목록·생성·삭제(⋮ 메뉴 안 삭제 포함), 새 창으로 열리는 약관 화면. **`data-testid` 가 붙은 요소와 붙지 않은 요소를 섞는다** (SC-008 측정이 이 구성에 의존, quickstart §0)

**Checkpoint**: `lint-imports` 가 빈 프로젝트에서 통과하고, 픽스처 앱이 뜬다

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 사용자 스토리가 의존하는 핵심 기반. 원칙 I·IV의 단일 지점들이 여기서 만들어진다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 사용자 스토리도 시작할 수 없다

### 도메인 모델 — 원칙 I의 단일 Step 모델

- [ ] T018 [P] `backend/src/itb/domain/locator.py` — `Candidate`(value, status: verified/unverified/not_collected), `TargetLocator`(7후보). **후보가 하나도 없으면 무효**라는 불변식 포함 (data-model §6, FR-017)
- [ ] T019 [P] `backend/src/itb/domain/assertion.py` — `Assertion`(kind: visible/hidden/text/url, target, match, value). `url` 은 target 이 null, 나머지는 필수 (data-model §5, FR-013a)
- [ ] T020 `backend/src/itb/domain/step.py` — `type` 판별 유니온으로 `ClickStep`/`FillStep`/`SelectStep`/`NavigateStep`/`AssertionStep`/`CloseTabStep`. 공통 필드 id·label·author·**tab**·timeout_ms·frame_url (data-model §4, FR-010·FR-012·FR-013·FR-030a) — T018, T019 의존
- [ ] T021 [P] `backend/src/itb/domain/test_case.py` — `Project`, `Test`, `Variable`. **`sensitive and value is not None` 이면 검증 실패**하는 불변식 (data-model §3·§7, FR-082)
- [ ] T022 [P] `backend/src/itb/domain/run_result.py` — `RunResult`, `StepResult`(tab, tab_wait_ms 포함), `LocatorAttempt`, `Artifacts`(trace는 항상 null) (data-model §9)
- [ ] T023 `backend/tests/unit/test_domain_invariants.py` — 도메인 불변식 단위 테스트: 민감 변수 value null, Step 목록 1개 이상, 후보 최소 1개, timeout 범위, `TC-\d{3}` 패턴, 변수 이름 패턴, `{{변수}}` 참조 정의 여부 (contracts/step-dsl §검증 규칙)

### 스키마 파이프라인 — 헌법 Cross-language schema duty

- [ ] T024 `backend/src/itb/schema/export.py` — Pydantic 모델에서 `schema/step-dsl.schema.json` 을 내보낸다 (research R6) — T020 의존
- [ ] T025 `frontend/package.json` 에 `gen:types` 스크립트를 넣고 `frontend/src/types/generated/step-dsl.d.ts` 를 생성한다. **생성물도 커밋한다** — T024 의존
- [ ] T026 `backend/tests/contract/test_schema_drift.py` — 스키마를 새로 생성해 커밋된 파일과 바이트 단위로 비교한다. 다르면 실패 (research R6)

### Locator 단일 지점 — 원칙 IV

- [ ] T027 `backend/src/itb/locator/strategy.py` — **순수 함수 `choose_strategy(target) -> LocatorStrategy`**. 우선순위 testId → role+name → label → text → 고정속성 → CSS. 탭을 알지 못한다(그래야 Generator와 공유 가능, research R4) — T018 의존
- [ ] T028 `backend/tests/unit/test_locator_strategy.py` — 후보 조합별 선택 결과, 우선순위 준수, 후보 없음 처리 단위 테스트 (FR-018)
- [ ] T029 `backend/src/itb/locator/collector.py` — 후보 수집 규칙과 **기록 시점 검증** 규칙(수집한 후보가 방금 조작한 그 요소를 가리키는지 확인해 status 부여) (research R4, FR-017)

### 저장 계층

- [ ] T030 [P] `backend/src/itb/storage/yaml_io.py` — 안전 로더만 사용. 검증 실패 시 **파일 경로와 문제 위치를 알려** 사용자가 직접 고칠 수 있게 한다 (contracts/step-dsl, FR-085)
- [ ] T031 `backend/src/itb/storage/repository.py` — 프로젝트 디렉터리 레이아웃 입출력. `itb-project.yaml`, `tests/*.yaml`, `.runs/<id>/`, **`.gitignore` 자동 작성**(`secrets.local.yaml`, `.runs/`, 키 경로) (data-model §1, FR-088b·FR-088c) — T030 의존
- [ ] T032 `backend/tests/unit/test_repository.py` — 레이아웃 생성, 경로 검증(절대 경로·경로 탐색 문자 거절), `TC-001` 자동 부여, `.gitignore` 내용 단위 테스트

### 비밀 값 — FR-089

- [ ] T033 [P] `backend/src/itb/secrets/keys.py` — 키 쌍 생성·적재, `~/.config/itb/keys/`, `0600` 권한 설정, 선택적 암호구(argon2id + SecretBox). **사용 전 권한 확인 후 과도 개방 시 경고**(FR-089e-1), 암호구 오류를 복호화 실패와 구분(FR-089e-2)
- [ ] T034 `backend/src/itb/secrets/store.py` — `SealedBox` 봉인·개봉, `secrets.local.yaml` 입출력, 공개키 지문 기록·불일치 감지. **봉인은 공개키만으로 가능해야 한다**(FR-089b·FR-089c) — T033 의존
- [ ] T035 [P] `backend/src/itb/secrets/scrubber.py` — 복호화 값 집합을 받아 산출물 기록 직전 마스킹. 부분 문자열·URL 인코딩·base64·JSON 이스케이프 형태까지 처리 (FR-089d, research R7)
- [ ] T036 `backend/src/itb/secrets/resolver.py` — 값 해석 순서: 환경 변수 → 암호문 복호화 → 비민감 변수 값 → **없으면 명확한 사유로 실패**(빈 값 진행 금지) (data-model §7, FR-089f·FR-089g) — T034 의존
- [ ] T037 `backend/tests/unit/test_secrets.py` — 봉인·개봉 왕복, 공개키만으로 봉인, 비밀키 없음, 복호화 실패, 암호구 오류, 권한 경고, 지문 불일치, 스크러버 형태 범위 단위 테스트 (SC-010·SC-011)

### 세션과 상태 기계 — 원칙 III의 구현체

- [ ] T038 `backend/src/itb/api/app.py` — FastAPI lifespan 에서 `async_playwright().start()` / `stop()`. **로컬 인터페이스에만 바인딩**(FR-088a). `async with` 컨텍스트 매니저를 쓰지 않는다 (research R1)
- [ ] T039 `backend/src/itb/execution/session.py` — `SessionManager` 싱글턴. 세션 ID → `Browser`+`BrowserContext`+**여러 `Page`**. `TabHandle` 목록(tab_index 부여 후 불변, **번호 재사용 금지**), active/mirrored tab 추적, 동시 탭 상한 10 (data-model §8, research R1·R2, FR-030a·FR-030g) — T038 의존
- [ ] T040 `backend/src/itb/execution/state_machine.py` — `RunSession` 10상태 전이. **불변식 1**(PAUSED·AI_BLOCKED에서 세션 종료 금지) **2**(편집은 PAUSED에서만) **3**(편집은 정의만 변경). **정의되지 않은 명령은 거절하고 현재 상태·가능한 행동을 알린다**(FR-043a) (data-model §8)
- [ ] T041 `backend/tests/unit/test_state_machine.py` — **10상태 × 모든 명령 전수 테스트.** 불변식 3개, 정의되지 않은 전이 거절(FR-035a·FR-043a), `LOST` 진입과 그 후 허용 행동(FR-041c), `TAKEOVER_RECORDING` 중 일시정지 허용 여부 (헌법 품질 게이트 3 필수 항목)
- [ ] T042 `backend/src/itb/execution/runner.py` — 세션당 러너 `asyncio.Task`. **Pause = `asyncio.Event` await, Resume = set.** 브라우저에 아무 명령도 보내지 않는다 (research R1, FR-031·FR-038) — T039, T040 의존
- [ ] T043 `backend/src/itb/api/ws/session_events.py` — WebSocket 이벤트 송신기. **서버 → 클라이언트 단방향**, `type`+`seq`. 재연결 시 재전송하지 않는다 (contracts/websocket)
- [ ] T044 [P] `backend/src/itb/api/errors.py` — 공통 오류 응답 형태 `{error:{code,message,detail}}` 와 오류 코드 목록(`STEP_LIST_EMPTY`, `NOT_PAUSED`, `SESSION_ALREADY_ACTIVE` …) (contracts/rest-api)
- [ ] T045 [P] `frontend/src/api/client.ts` + `frontend/src/api/ws.ts` — REST 클라이언트와 WebSocket 구독. **재연결 시 `GET /api/sessions/{sid}` 로 전체 상태를 다시 받는다** (contracts/websocket)
- [ ] T046 [P] `frontend/src/theme/` — 디자인 8화면에서 공통 시각 언어(색·타이포·간격·배지)를 추출한다. `docs/design/*.dc.html` 의 폰트·색 토큰을 따른다

**Checkpoint**: 도메인 모델·Locator 단일 지점·저장·비밀·세션 상태 기계가 준비됨. `lint-imports` 통과.
사용자 스토리 구현을 시작할 수 있다

---

## Phase 3: User Story 1 - 직접 녹화로 첫 테스트를 만든다 (Priority: P1) 🎯 MVP

**Goal**: 사용자가 실제 브라우저 창을 조작해 클릭·입력·선택·화면 이동을 Step으로 기록하고, 이름을 붙여
저장한다. 새 탭에서의 조작과 탭 닫기도 기록된다.

**Independent Test**: 픽스처 앱에서 녹화 시작 → 클릭·입력·선택·화면 이동 각 1회 이상 + 새 탭 조작 + 탭 닫기
→ 정지 → 생성된 Step 목록이 실제 수행 순서·동작 종류·탭을 정확히 반영하고, 저장 후 목록에서 다시 열린다.
**재실행 기능 없이도 검증 가능하다.**

### Tests for User Story 1 ⚠️ 먼저 작성해 실패를 확인한다

- [ ] T047 [P] [US1] `backend/tests/contract/test_project_api.py` — 프로젝트 생성·열기·조회 계약 (contracts/rest-api §프로젝트)
- [ ] T048 [P] [US1] `backend/tests/contract/test_tests_api.py` — 테스트 목록·조회·이름 변경·삭제 계약, `counts` 집계 (contracts/rest-api §테스트)
- [ ] T049 [P] [US1] `backend/tests/contract/test_dsl_roundtrip.py` — contracts/step-dsl 의 단일 탭·멀티 탭 예제 YAML 을 적재→직렬화→비교. 검증 규칙 위반 케이스 전부 거절 확인
- [ ] T050 [P] [US1] `backend/tests/integration/test_recording.py` — 픽스처 앱 대상 녹화 통합 테스트: 4종 동작 기록, 연속 입력 병합(FR-025), 한글 입력 최종값(research R2)
- [ ] T051 [P] [US1] `backend/tests/integration/test_multitab_record.py` — 새 탭 조작 기록, `tab` 값 부여, 탭 닫기 Step, 탭 상한 도달 (FR-030a~c·FR-030g)
- [ ] T052 [P] [US1] `backend/tests/e2e/test_us1_manual_record.py` — 녹화 → 저장 → 목록 표시 종단 테스트

### Implementation for User Story 1

- [ ] T053 [US1] `backend/src/itb/recording/injected/recorder.js` — capture 단계 `click`(`composedPath()[0]` 사용), `change`+`blur`(입력), `<select>` `change`. **`keydown`/`input` 은 쓰지 않는다**(한글 IME 회피, FR-025 자동 충족). 후보 수집 + 기록 시점 검증 수행 후 `window.__itbRecord(payload)` 호출 (research R2·R4)
- [ ] T054 [US1] `backend/src/itb/recording/recorder.py` — `context.add_init_script()` + `context.expose_binding("__itbRecord")` **컨텍스트 단위 등록**. `source` 로 발신 페이지 → `tab_index` 변환. 페이로드 → Step 변환 (research R2, FR-024·FR-027) — T029, T039, T053 의존
- [ ] T055 [US1] `backend/src/itb/recording/tabs.py` — `context.on("page")` 로 열린 순서 `tab_index` 부여, `page.on("close")` → `close_tab` Step, 상한 초과 시 기록 중단. **새 탭 열림은 Step으로 만들지 않는다**(FR-030b) — T039 의존
- [ ] T056 [US1] `backend/src/itb/recording/navigation.py` — `page.on("framenavigated")`(main frame) → navigate Step. **클릭 직후 1000ms 창 안의 네비게이션은 중복 제거**(research R2)
- [ ] T057 [US1] `backend/src/itb/recording/file_input.py` — 파일 입력을 감지해 Step을 만들되 파일 경로는 Step 편집기에서 지정하게 한다. 미지원 사유를 사용자에게 알린다 (research R2 알려진 한계)
- [ ] T058 [US1] `backend/src/itb/recording/sensitive.py` — 비밀번호 유형 필드 자동 민감 판정, 값을 변수 참조로 치환하고 공개키로 봉인 (FR-082a) — T034 의존
- [ ] T059 [US1] `backend/src/itb/api/routes/project.py` — `GET /api/project`, `POST /api/project/create`(디렉터리 검증 + `.gitignore` 작성), `POST /api/project/open` (FR-001·FR-008) — T031, T044 의존
- [ ] T060 [US1] `backend/src/itb/api/routes/tests.py` — 목록(검색 `q`, `counts` 집계, 실패 요약), 조회, 이름 변경, 삭제 (FR-002~FR-007) — T031 의존
- [ ] T061 [US1] `backend/src/itb/api/routes/sessions.py` — `POST /api/sessions`(mode=record), `GET /api/sessions/{sid}`, `POST .../stop`, `POST .../save`. 활성 세션 중복 시 `409`(FR-043), Step 0개 저장 거절(FR-029) — T039, T042 의존
- [ ] T062 [US1] `backend/src/itb/execution/window.py` — 조작 국면에서 실제 브라우저 창·대상 탭을 앞으로 가져온다(`bring_to_front`). 창을 다시 앞으로 가져오는 수단 제공 (FR-023a·FR-030e, spec 엣지 케이스)
- [ ] T063 [US1] `backend/src/itb/api/routes/tabs.py` — `GET /api/sessions/{sid}/tabs` (FR-030f) — T055 의존
- [ ] T064 [P] [US1] `frontend/src/pages/TestList.tsx` — `TestList.dc.html` 이식. 상태 배지·ID·이름·Step 수·작성 배지·마지막 실행·실패 요약 인라인 표시·검색·집계 (FR-002~FR-006·FR-002a)
- [ ] T065 [P] [US1] `frontend/src/pages/CreateTest.tsx` — `CreateTest.dc.html` 이식. 직접 녹화 / AI로 만들기 선택, 시작 URL, 브라우저 선택, **"어느 쪽으로 만들어도 같은 Step 모델로 저장된다" 문구**(FR-009)
- [ ] T066 [P] [US1] `frontend/src/pages/ProjectSetup.tsx` — **확정 디자인에 없는 화면.** 디렉터리 선택 + 프로젝트 메타 입력. 8화면의 시각 언어를 따른다 (spec 디자인 차이 3)
- [ ] T067 [US1] `frontend/src/components/StepList.tsx` — 번호·표시 이름·동작 종류 배지·적용된 식별 정보 요약·작성 주체 배지·탭 표시. **사람·AI·자연어 경로가 같은 `step_added` 이벤트를 쓰므로 분기를 두지 않는다**(원칙 I, contracts/websocket) — T045 의존
- [ ] T068 [US1] `frontend/src/pages/Runner.tsx` — `Main.dc.html` 이식(녹화 상태). 헤더 배지·테스트명·`step N / M`·정지 버튼, 좌측 브라우저 영역, 우측 Step 목록, 하단 "Step 추가" (FR-026)
- [ ] T069 [US1] `frontend/src/components/TabStrip.tsx` — **확정 디자인에 없는 화면.** 미러 위 탭 표시·전환 (FR-030f, spec 디자인 차이 3)
- [ ] T070 [US1] 녹화 이벤트 → Step 목록 반영 지연을 계측해 `backend/tests/integration/test_performance.py` 에 p95 < 200ms 검증을 추가한다 (research R8)

- [ ] T157 [US1] `backend/src/itb/recording/recorder.py` 에서 민감 값 치환이 `step_added` 이벤트 발행보다 **반드시 먼저** 일어나도록 파이프라인 순서를 고정한다. 리코더가 비밀번호 평문을 포착한 뒤 변수 참조로 치환하기 전에 이벤트가 나가면 평문이 프론트에 도달한다 (FR-083, FR-089d, 헌법 보안 요건) — analyze C2
- [ ] T158 [P] [US1] `backend/tests/unit/test_sensitive_ordering.py` — 치환 전 이벤트 발행을 깨뜨리는 회귀 테스트. 리코더 파이프라인에 평문이 이벤트 페이로드로 들어가는 경로가 없음을 확인한다 (FR-083, SC-010) — analyze C2

**Checkpoint**: US1이 독립적으로 동작하고 검증 가능하다. quickstart §2·§3 절차를 통과한다

---

## Phase 4: User Story 2 - 저장한 테스트를 반복 실행하고 실패 원인을 확인한다 (Priority: P2)

**Goal**: 저장된 테스트를 언어모델 없이 결정적으로 실행하고, Step별 결과·소요 시간을 실시간으로 보여주며,
실패 시 시도한 후보·스크린샷·로그로 원인을 파악할 수 있게 한다.

**Independent Test**: US1로 만든 테스트를 대상 앱 변경 없이 10회 연속 실행해 매번 동일한 `PASS`. 이어서
버튼 이름을 바꾼 뒤 실행해 해당 Step에서 실패하고 시도한 후보 목록·실패 시점 스크린샷이 제공된다.

### Tests for User Story 2 ⚠️

- [ ] T071 [P] [US2] `backend/tests/integration/test_replay_no_llm.py` — **재실행 중 `anthropic` 클라이언트 생성에 스파이를 심어 호출 0건 확인**(SC-006, 헌법 원칙 II 동적 검증)
- [ ] T072 [P] [US2] `backend/tests/integration/test_roundtrip.py` — 녹화 → 저장 → 재실행 결과 일치. 10회 연속 실행 결정성 (헌법 품질 게이트 2, SC-003)
- [ ] T073 [P] [US2] `backend/tests/integration/test_locator_coverage.py` — 픽스처 앱 녹화 결과에서 `verified` 후보 2개 이상 Step 비율 90% 이상 (SC-008)
- [ ] T074 [P] [US2] `backend/tests/integration/test_secret_leakage.py` — 정의 파일·비밀 파일·로그·실패 메시지·스크린샷 메타데이터·임시 파일·API 응답·WS 이벤트·**생성 코드** 전수 grep 으로 평문 0건 (SC-010, FR-089d)
- [ ] T075 [P] [US2] `backend/tests/integration/test_multitab_replay.py` — 탭 대기 후 실행, 탭 미개설 시 실패 사유, 탭 순서 불일치 (FR-030d, SC-012)
- [ ] T076 [P] [US2] `backend/tests/contract/test_ws_events.py` — WebSocket 이벤트 형태·`seq` 단조 증가·`mirror_*` 유실 허용성 (contracts/websocket)
- [ ] T077 [P] [US2] `backend/tests/e2e/test_us2_replay_and_diagnose.py` — 실행 → 실패 유도 → 결과 진단 → 실패 Step부터 재실행 종단 테스트

### Implementation for User Story 2

- [ ] T078 [US2] `backend/src/itb/execution/tab_resolver.py` — Step의 `tab` 으로 대상 `Page` 해석. 없으면 `timeout_ms` 까지 `context.on("page")` 대기, 초과 시 **"탭 N이 열리기를 기다렸으나 열리지 않았다"** 로 실패 (FR-030d, research R2) — T039 의존
- [ ] T079 [US2] `backend/src/itb/execution/locator_runtime.py` — `choose_strategy` 결과를 Playwright `Locator` 로 변환. 해석 알고리즘: 즉시 `count()` 순회 → 미발견 시 최상위 후보에 남은 예산 집중 → 채택 후보 기록 → **후보 간 불일치를 로그에 남긴다** (research R4, FR-018·FR-021) — T027, T078 의존
- [ ] T080 [US2] `backend/src/itb/execution/step_executor.py` — Step 6종 실행. 변수 치환(T036 경유), 대기 시간 상한, `hidden` 검증은 처음부터 없던 경우도 통과 (FR-013a·FR-015·FR-057, spec 엣지 케이스) — T036, T079 의존
- [ ] T081 [US2] `backend/src/itb/execution/artifacts.py` — 실패 시점 스크린샷, 콘솔 기록, 네트워크 기록 수집. **디스크 기록 직전 스크러버 통과**(FR-052·FR-053·FR-089d) — T035 의존
- [ ] T082 [US2] `backend/src/itb/execution/runner.py` 확장 — 순차 실행, `step_started`/`step_finished`/`step_failed`/`run_finished` 이벤트, 실패 시 중단, 결과 집계(총 시간·통과/전체·멈춘 Step) (FR-046·FR-048~FR-051) — T042, T080 의존
- [ ] T083 [US2] `backend/src/itb/execution/session_loss.py` — 세션 유실을 **모든 상태에서** 감지. 재실행 중 유실 → 실패 종료 + 부분 결과 보존(FR-041a), AI 수행 중 → 루프 중단 + 저장 확인(FR-041b), 이후 저장·처음부터 재실행만 허용(FR-041c) — T040 의존
- [ ] T084 [US2] `backend/src/itb/mirror/screencast.py` — 전용 CDP 세션에서 `Page.startScreencast`(jpeg/q60/1280×800) → `mirror_frame` 이벤트 + `screencastFrameAck`. **`Input` 도메인을 임포트하지도 호출하지도 않는다**(FR-047a). WS 끊김 시 ack 중단·`stopScreencast`, 실행 무영향(FR-047b). 스크린캐스트 불가 시 1fps 스크린샷 강등 (research R3) — T039, T043 의존
- [ ] T085 [US2] `backend/src/itb/mirror/tab_switch.py` — 한 번에 한 탭만 스트리밍. 탭 변경 시 이전 탭 stop → 새 탭 start. 실행 중에는 현재 Step 대상 탭을 따라간다. **모든 세션 상태에서 미러를 유지**하고 종료·유실 시 중단 (FR-030f·FR-047c~e, research R3) — T084 의존
- [ ] T086 [US2] `backend/src/itb/api/routes/sessions.py` 확장 — `mode=replay` 세션, `POST .../run-from`, `POST .../mirror-tab` (FR-039·FR-055) — T061, T082 의존
- [ ] T087 [US2] `backend/src/itb/api/routes/results.py` — `GET /api/tests/{id}/result`, `GET .../artifacts/{kind}`. **`trace` 는 `501`**(spec 디자인 차이 1) — T081 의존
- [ ] T088 [P] [US2] `frontend/src/components/MirrorView.tsx` — 읽기 전용 프레임 표시. **사용자 입력을 대상 브라우저로 전달하지 않는다**(FR-047a). 조작 국면에서는 "실제 창에서 조작 중" 표시(FR-023b). 프레임 끊김·강등 표시 — T069 의존
- [ ] T089 [P] [US2] `frontend/src/pages/RunResult.tsx` — `RunResult.dc.html` 이식. 요약 3항목, Step 결과 목록, 실패 상세(시도한 후보 우선순위 순 + timeout), `SCREENSHOT`/`CONSOLE`/`NETWORK` 탭, **`TRACE` 탭 비활성**, "실패한 Step부터 실행"/"처음부터 실행", "Step 고치기" (FR-050~FR-056·FR-058)
- [ ] T090 [US2] `frontend/src/pages/Runner.tsx` 확장 — 실행 중 상태(`RUNNING` 배지, 현재 Step 강조, 소요 시간, 브라우저 오버레이) (FR-046·FR-047)
- [ ] T091 [US2] Step 실행 제품 오버헤드 계측을 `backend/tests/integration/test_performance.py` 에 추가한다 — p95 < 50ms (research R8)

**Checkpoint**: 원칙 II가 정적·동적으로 검증된다. quickstart §4 절차를 통과한다

---

## Phase 5: User Story 3 - 실행 중 멈춰서 고치고 그 자리에서 이어서 실행한다 (Priority: P3)

**Goal**: 일시정지 상태에서 Step을 편집하고 직접 조작으로 Step을 추가한 뒤, 브라우저 상태를 유지한 채
이어서 실행한다. 이미 실행된 Step 편집은 정의만 바꾸고 브라우저를 되돌리지 않는다.

**Independent Test**: 로그인을 포함해 사전 Step이 5개 이상인 시나리오에서 일시정지 → 실행된 Step 삭제 →
직접 동작 추가 → Assertion 추가 → 계속하기. **로그인이 재실행되지 않고** 이어서 진행된다.

### Tests for User Story 3 ⚠️

- [ ] T092 [P] [US3] `backend/tests/integration/test_pause_resume.py` — 일시정지 중 세션·인증·화면 상태 유지, 계속하기 시 **사전 Step 재실행 없음**(SC-007), 브라우저 재시작 없음
- [ ] T093 [P] [US3] `backend/tests/integration/test_edit_executed_step.py` — 이미 실행된 Step 편집 시 브라우저 미복원 + 경고 반환(FR-040a~c), 이후 계속하기가 현재 상태 기준으로 진행
- [ ] T094 [P] [US3] `backend/tests/contract/test_step_edit_api.py` — 편집 엔드포인트 계약. **`PAUSED` 아닌 상태에서 `409 NOT_PAUSED`**(FR-035a), 정의되지 않은 명령 거절(FR-043a)
- [ ] T095 [P] [US3] `backend/tests/e2e/test_us3_pause_edit_resume.py` — quickstart §5 13단계 종단 테스트

### Implementation for User Story 3

- [ ] T096 [US3] `backend/src/itb/execution/step_edits.py` — 삽입·수정·삭제·순서 변경. **편집은 세션의 작업 중 Step 목록만 변경하고 브라우저에 명령을 보내지 않는다.** 편집 지점이 `current_step_index` 이전이면 `edit_warnings` 를 세운다 (FR-035·FR-040a~d) — T040 의존
- [ ] T097 [US3] `backend/src/itb/api/routes/steps.py` — `POST/PATCH/DELETE .../steps`, `.../steps:reorder`, `.../assertions`. 모두 `PAUSED` 게이트. 응답에 `steps` + `edit_warnings` (contracts/rest-api) — T096 의존
- [ ] T098 [US3] `backend/src/itb/api/routes/sessions.py` 확장 — `POST .../pause`, `POST .../resume`, `record-actions:start`/`stop`. 중지 시 편집 Step 저장 여부 확인 (FR-031·FR-038·FR-042) — T086 의존
- [ ] T099 [US3] `backend/src/itb/recording/inline_record.py` — 일시정지 중 직접 동작 추가. 실제 창·대상 탭 전면 배치, 기록된 Step을 **일시정지 위치에 삽입** (FR-036·FR-023a) — T054, T062, T096 의존
- [ ] T100 [US3] `backend/src/itb/execution/assertion_builder.py` — 4종 검증 조건 구성. 대상 요소 지정 시 후보 수집·검증 수행 (FR-037·FR-013a·FR-013b) — T029 의존
- [ ] T101 [US3] `backend/src/itb/execution/runner.py` 확장 — 임의 Step부터 실행. 브라우저 상태를 되돌리지 않고 그 지점부터 시작 (FR-039, FR-040c와 일관) — T082 의존
- [ ] T102 [P] [US3] `frontend/src/pages/RunnerPaused.tsx` — `RunnerPaused.dc.html` 이식. `PAUSED` 배지, "step N 이후 정지", **"브라우저 세션과 화면 상태를 그대로 유지하고 있습니다" 배너**(FR-033), 일시정지 위치 구분선(FR-034), 계속하기·중지
- [ ] T103 [P] [US3] `frontend/src/components/PauseActions.tsx` — "지금 할 수 있는 것" 6개 액션(직접 동작 추가 / Assertion 추가 / Step 수정 / 순서 변경 / 이 Step부터 / Step 삭제) + 자연어 입력 박스 (FR-035~FR-039)
- [ ] T104 [US3] `frontend/src/components/EditWarningBanner.tsx` — `edit_warning` 이벤트 표시. "이 편집은 현재 화면 상태에 적용되지 않았습니다" (FR-040b)
- [ ] T105 [US3] `frontend/src/components/AssertionForm.tsx` — 4종 조건 선택 + 대상 지정 + 비교 값(변수 참조 가능) (FR-013a·FR-013b)

**Checkpoint**: 원칙 III가 검증된다. quickstart §5의 9단계에서 로그인이 재실행되지 않는다

---

## Phase 6: User Story 4 - 자연어로 지시하면 AI가 브라우저에서 해보고 그 결과가 테스트가 된다 (Priority: P4)

**Goal**: 자연어 지시로 AI가 실제 브라우저를 조작하고, 성공한 동작만 Step으로 기록해 저장한다.
저장된 테스트는 언어모델 없이 재실행된다.

**Independent Test**: 자연어 시나리오를 실행해 Step으로 저장한 뒤 **네트워크를 끊고** 재실행해 통과한다.

### Tests for User Story 4 ⚠️

- [ ] T106 [P] [US4] `backend/tests/unit/test_agent_tools.py` — 도구 표면이 Step 종류와 1:1 대응함을 확인. `execute_javascript` 류 도구 부재 확인 (research R5, FR-086)
- [ ] T107 [P] [US4] `backend/tests/unit/test_attempt_limits.py` — 도구 호출 총 상한 40회, 동일 요소 연속 실패 상한 3회, 상한 도달 시 중단 (FR-066)
- [ ] T108 [P] [US4] `backend/tests/integration/test_ai_authoring.py` — 성공 동작만 Step 기록(FR-061), 지시문이 실행 대상으로 저장되지 않음(FR-063), 언어모델 실패 시 Step 보존(FR-067)
- [ ] T109 [P] [US4] `backend/tests/e2e/test_us4_nl_authoring.py` — 지시문 → 저장 → 네트워크 차단 재실행 통과 종단 테스트

### Implementation for User Story 4

- [ ] T110 [US4] `backend/src/itb/llm/client.py` — `AsyncAnthropic()` 인자 없는 생성자(env → `ant auth login` 프로필 순 해석, **키 하드코딩 금지** FR-084). 모델 `claude-opus-5`, `output_config={"effort":"xhigh"}`, `thinking` 파라미터 생략(Opus 5는 기본 adaptive), `betas=["server-side-fallback-2026-07-01"]` + `fallbacks="default"`, `content` 읽기 전 `stop_reason` 확인. **`budget_tokens`·`temperature`·프리필을 쓰지 않는다**(400) (research R5)
- [ ] T111 [US4] `backend/src/itb/authoring/tools.py` — `@beta_async_tool` 로 `list_tabs`, `observe_page(tab)`, `click`, `fill`, `select`, `navigate`, `assert_condition`, `close_tab(tab)`, `report_blocked`. `element_ref` 는 `observe_page` 가 부여하며 **에이전트가 CSS 셀렉터를 짜지 않는다**(원칙 IV 유지). 도구 실행 시 후보 수집은 제품이 한다. 새 탭 열림을 도구 결과에 덧붙인다 (research R5) — T029, T080 의존
- [ ] T112 [US4] `backend/src/itb/authoring/agent.py` — `client.beta.messages.tool_runner(...)` 를 `async for` 로 순회. **하드 루프 카운터가 1차 방어선**(T107 상한). 서버 도구를 쓰지 않으므로 `pause_turn` 을 다루지 않는다. 사용자 일시정지 시 취소 처리 (research R5, FR-060·FR-065·FR-066) — T110, T111 의존
- [ ] T113 [US4] `backend/src/itb/authoring/compiler.py` — 성공한 도구 호출을 Step으로 확정. **도구 표면이 Step과 1:1이므로 변환 실패가 원리적으로 없다**(research R5, FR-061·FR-062) — T111 의존
- [ ] T114 [US4] `backend/src/itb/api/routes/sessions.py` 확장 — `mode=ai` 세션, 지시문 길이·내용 검증(FR-085), `ai_progress`/`ai_finished`/`ai_error` 이벤트 (FR-059·FR-067) — T098, T112 의존
- [ ] T115 [US4] `backend/src/itb/storage/repository.py` 확장 — `ai_instruction` 을 정의 파일에 원문으로 보관. **`itb.execution` 은 이 필드를 읽지 않는다**(FR-063) — T031 의존
- [ ] T116 [P] [US4] `frontend/src/pages/AiRecord.tsx` — `AiRecord.dc.html` 이식. 자연어 지시 박스, `AI 수행 중` 배지, AI CONTROL 표시, 기록된 Step 목록, **"지시문은 테스트로 저장되지 않습니다. 다시 돌릴 때는 AI를 쓰지 않습니다" 문구**(FR-064), "테스트로 저장"
- [ ] T117 [US4] `frontend/src/components/AiProgress.tsx` — `ai_progress` 표시. AI가 무엇을 하는 중인지 (FR-060)
- [ ] T118 [US4] `backend/tests/integration/test_replay_no_llm.py` 확장 — **AI로 만든 테스트**의 재실행에서도 호출 0건 확인. `replay` 모드 세션에서 `ai_*` 이벤트가 관측되지 않음을 확인 (SC-006, contracts/websocket)

**Checkpoint**: quickstart §6 통과. 7단계(네트워크 없이 재실행)가 원칙 II의 직관적 증거다

---

## Phase 7: User Story 5 - AI가 실패하면 그 세션에서 사람이 이어받는다 (Priority: P5)

**Goal**: AI가 막히면 브라우저 세션을 유지한 채 4선택지를 제시하고, "직접 수행"으로 사람이 이어받아
완료한 뒤 AI에게 되돌려준다.

**Independent Test**: AI가 찾기 어려운 요소를 포함한 지시문으로 실패를 유도하고, "직접 수행"으로 이어받아
완료한 뒤 "계속하기". 브라우저가 재시작되지 않고 AI Step과 HUMAN Step이 한 목록에 남는다.

### Tests for User Story 5 ⚠️

- [ ] T119 [P] [US5] `backend/tests/unit/test_ai_blocked_transitions.py` — `AI_BLOCKED` 4선택지 각각의 전이, 그 상태에서 일시정지·저장 요청 처리(FR-043a) (data-model §8)
- [ ] T120 [P] [US5] `backend/tests/integration/test_takeover.py` — 실패 시 세션 유지, 화면 상태 보존, HUMAN Step 기록, 계속하기 후 AI 재개 (FR-069~FR-077)
- [ ] T121 [P] [US5] `backend/tests/e2e/test_us5_takeover.py` — quickstart §7 종단 테스트

### Implementation for User Story 5

- [ ] T122 [US5] `backend/src/itb/authoring/blocked.py` — 도구 실패를 `AI_BLOCKED` 로 전이. **세션 유지**, 실패한 동작·이유·4선택지를 `ai_blocked` 이벤트로 전달 (FR-069·FR-070) — T040, T112 의존
- [ ] T123 [US5] `backend/src/itb/api/routes/sessions.py` 확장 — `POST .../ai-choice` 4종. takeover → `TAKEOVER_RECORDING`(실제 창 전면, 세션 유지 표시), retry → 현재 상태에서 재시도, skip → Step 미기록 후 다음 지시, abort → 종료 + 저장 확인 (FR-071~FR-074) — T114, T122 의존
- [ ] T124 [US5] `backend/src/itb/recording/takeover.py` — 사람 인수 녹화. AI가 남긴 화면 상태 그대로 기록 시작, Step에 `author=human` (FR-071·FR-075) — T054, T099 의존
- [ ] T125 [US5] `backend/src/itb/authoring/agent.py` 확장 — 사람 인수 후 "계속하기" 시 현재 브라우저 상태에서 남은 지시를 이어서 수행 (FR-076) — T112, T124 의존
- [ ] T126 [P] [US5] `frontend/src/pages/Takeover.tsx` — `Takeover.dc.html` 이식. `사람이 녹화 중` 배지, `세션 유지` 표시, REC 표시, HUMAN 배지, **"이어서 진행하면 AI가 남은 지시를 다시 맡습니다" 문구**(FR-077)
- [ ] T127 [P] [US5] `frontend/src/components/AiBlockedCard.tsx` — 실패한 동작 + 이유 + 4선택지 버튼 (FR-070)

**Checkpoint**: PRD §20의 핵심 가설이 검증 가능해진다. quickstart §7 통과

---

## Phase 8: User Story 6 - 일시정지 상태에서 자연어로 Step을 추가한다 (Priority: P6)

**Goal**: 일시정지 중 자연어로 지시하면 AI가 현재 화면을 분석해 Step 하나를 만들어 삽입한다.

**Independent Test**: 일시정지 상태에서 자연어 5건(검증 3·동작 2)을 입력해 각각 Step이 만들어지고,
수동 작성 Step과 동일한 형태로 실행된다.

### Tests for User Story 6 ⚠️

- [ ] T128 [P] [US6] `backend/tests/integration/test_nl_step.py` — 자연어 → Step 삽입, 수동 Step과 구조 동일, 재실행 시 언어모델 미호출, 대상 미발견 시 Step 미생성·일시정지 유지 (FR-078~FR-081)
- [ ] T129 [P] [US6] `backend/tests/e2e/test_us6_nl_step.py` — quickstart §8 종단 테스트

### Implementation for User Story 6

- [ ] T130 [US6] `backend/src/itb/authoring/nl_step.py` — 현재 브라우저 화면 분석 → 단일 Step 생성. **대상을 찾지 못하면 Step을 만들지 않고 알리며 일시정지 상태를 유지한다**(FR-081) — T111, T112 의존
- [ ] T131 [US6] `backend/src/itb/api/routes/sessions.py` 확장 — `POST .../ai-step`. `PAUSED` 게이트, 삽입 위치는 일시정지 위치 (FR-078·FR-079) — T097, T130 의존
- [ ] T132 [US6] `frontend/src/components/PauseActions.tsx` 확장 — 자연어 입력 처리와 실패 안내 연결 (FR-081) — T103 의존
- [ ] T133 [US6] `backend/tests/integration/test_replay_no_llm.py` 확장 — 자연어로 추가한 Step의 재실행에서도 호출 0건 (FR-080)

**Checkpoint**: quickstart §8 통과

---

## Phase 9: User Story 7 - Step이 어떤 기준으로 요소를 찾는지 확인하고 고친다 (Priority: P7)

**Goal**: Step 상세에서 후보 우선순위와 수집 상태를 보고, 깨진 Step의 요소를 다시 지정한다.

**Independent Test**: 녹화된 Step의 상세에 수집된 후보와 우선순위가 표시되고, 대상 앱 요소 속성을 바꾼 뒤
"다시 집기"로 갱신해 실행이 다시 통과한다.

### Tests for User Story 7 ⚠️

- [ ] T134 [P] [US7] `backend/tests/unit/test_candidate_display.py` — 표시 상태 4종(`사용 중`/`대체 N`/`최후`/`수집되지 않음`)이 저장 상태 3값과 우선순위에서 파생되는 규칙. **표시 상태를 저장하지 않음**을 확인 (FR-019a)
- [ ] T135 [P] [US7] `backend/tests/integration/test_repick.py` — 다시 집기로 후보 갱신 후 실행 통과 (FR-020)
- [ ] T136 [P] [US7] `backend/tests/e2e/test_us7_step_inspector.py` — quickstart §9 종단 테스트

### Implementation for User Story 7

- [ ] T137 [US7] `backend/src/itb/locator/display.py` — 표시 상태 파생 함수 (FR-019a) — T018, T027 의존
- [ ] T138 [US7] `backend/src/itb/recording/repick.py` — "다시 집기" 대기 상태 진입, 브라우저에서 요소 재지정 → 후보 재수집·재검증 → Step 갱신 (FR-020) — T029, T054 의존
- [ ] T139 [US7] `backend/src/itb/api/routes/steps.py` 확장 — `POST .../steps/{step_id}/repick`, 표시 이름·입력값·타임아웃·민감 여부 수정(FR-082b) — T097, T138 의존
- [ ] T140 [US7] `backend/src/itb/domain/test_case.py` 확장 — 민감 지정 시 기존 평문 값을 변수 참조로 이전하고 암호화해 옮긴다 (FR-082b) — T034, T036 의존
- [ ] T141 [P] [US7] `frontend/src/components/StepInspector.tsx` — `StepInspector.dc.html` 이식. 후보 6단 우선순위 표, 수집된 원본 값, 테스트 DSL 미리보기, 저장·다시 집기 (FR-016·FR-019·FR-020)
- [ ] T142 [P] [US7] `frontend/src/components/LocatorPriorityTable.tsx` — 순위·후보 종류·값·상태 배지 표시 (FR-019a)

**Checkpoint**: quickstart §9 통과. 원칙 IV의 사용자 노출 지점이 완성됨

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 스토리에 걸치는 마무리와 헌법 게이트 최종 확인

### 이번 범위에 있으나 스토리에 속하지 않는 것

- [ ] T143 [P] `backend/src/itb/generator/playwright_gen.py` — Step → Playwright 코드 생성. `choose_strategy` 를 공유하고, **민감 변수는 변수 참조로만 생성**(FR-089d-1). 대상 화면 유래 텍스트를 **이스케이프**하고 문자열 접합으로 만들지 않는다(헌법 보안 요건). 탭은 `waitForEvent('page')` 패턴 (contracts/step-dsl §Export 대비) — T027 의존
- [ ] T144 [P] `backend/tests/unit/test_generator.py` — 생성 코드 단위 테스트: 후보별 표현, 4종 검증, 멀티 탭, 민감 변수 참조, 이스케이프 (헌법 품질 게이트 3 필수 항목)
- [ ] T145 [P] `frontend/src/pages/KeyManagement.tsx` — **확정 디자인에 없는 화면.** 키 상태·지문 표시, 생성, 권한 경고, 암호구 (FR-089a·FR-089e-1, spec 디자인 차이 3)
- [ ] T146 [P] `frontend/src/pages/SecretValues.tsx` — **확정 디자인에 없는 화면.** 변수 목록(**값 미표시**), 값 입력·재입력, 지문 불일치 안내 (FR-082b·FR-089b, spec 디자인 차이 3)
- [ ] T147 `backend/src/itb/api/routes/secrets.py` — `GET /api/keys/status`, `POST /api/keys/generate`, `GET /api/secrets`(이름·존재 여부만), `PUT /api/secrets/{name}`(공개키로 즉시 봉인, 값 미반환), `DELETE`. **복호화 값을 반환하는 응답이 없다** (contracts/rest-api §비밀 값과 키) — T033, T034 의존
- [ ] T148 `backend/tests/contract/test_secrets_api.py` — 어떤 응답에도 값이 없음을 확인. 비밀키 없이 `PUT` 성공(FR-089b)

### 마감 항목

- [ ] T149 [P] `frontend/src/components/SessionLostBanner.tsx` — `LOST` 상태 표시와 허용 행동 안내(저장·처음부터 재실행만) (FR-041c)
- [ ] T150 [P] `frontend/src/components/StartingIndicator.tsx` — `STARTING` 상태 표시 (spec 디자인 차이 3, data-model §8)
- [ ] T151 [P] `frontend/tests/` — Vitest 로 Step 200개 목록 렌더 성능과 컴포넌트 단위 테스트 (research R8)
- [ ] T152 `backend/src/itb/execution/` 전체와 `backend/src/itb/api/errors.py` 의 오류 처리·로깅 일관성을 점검하고 `backend/tests/unit/test_error_handling.py` 를 추가한다 — 실패한 Step이 항상 진단 가능한 결과(사유·스크린샷·로그)를 남기고, 처리되지 않은 오류로 러너 태스크가 죽지 않음을 확인 (FR-087)
- [ ] T153 `README.md` 와 `docs/DEVELOPMENT.md` — quickstart.md §0의 설치·실행 절차를 개발자 문서로 정리한다
- [ ] T154 `specs/001-interactive-ai-test-builder/quickstart.md` §12 완료 체크리스트 13항목을 실제로 수행하고, 결과를 그 파일의 체크박스에 반영한다
- [ ] T155 SC-001·SC-002·SC-004·SC-005 수동 측정 세션 — 시나리오 20건 규모. **자동 테스트로 대체할 수 없다.** 표본 선정 기준과 측정 결과를 `docs/mvp-metrics.md` 에 기록한다 (quickstart §12)
- [ ] T156 `specs/001-interactive-ai-test-builder/checklists/design-review.md` 의 미체크 55항목을 리뷰어가 검토하고 결과를 반영한다

**Checkpoint**: 헌법 게이트 전부 통과. MVP 완료

---

## Dependencies & Execution Order

### 단계 의존

```
Phase 0 (가정 검증)  ← 반드시 먼저. 결과가 설계를 바꿀 수 있다
      ↓
Phase 1 (Setup)      ← T015·T016(import-linter)을 여기서 붙인다. 나중에 붙이면 경계를 넘은 코드를 되돌려야 한다
      ↓
Phase 2 (Foundational) ← 모든 스토리의 전제. domain → locator → execution 순
      ↓
Phase 3 (US1, P1) 🎯 MVP
      ↓
Phase 4 (US2, P2)    ← US1의 Step 모델이 있어야 실행할 것이 있다
      ↓
Phase 5 (US3, P3)    ← US2의 러너가 있어야 멈출 것이 있다
      ↓
Phase 6 (US4, P4)    ← US1의 Step 모델 + US2의 실행이 있어야 "AI 결과가 결정적 테스트로 변환됨"을 검증할 수 있다
      ↓
Phase 7 (US5, P5)    ← US4(AI) + US3(세션 유지 편집) 둘 다 필요
      ↓
Phase 8 (US6, P6)    ← US3(수동 편집) + US4(AI 실행) 둘 다 필요
      ↓
Phase 9 (US7, P7)    ← 독립적. 앞 스토리 없이도 되지만 가치가 낮아 마지막
      ↓
Phase 10 (Polish)
```

### 스토리별 독립성

| 스토리 | 선행 스토리 | 이유 |
|--------|-------------|------|
| US1 | 없음 | Step 모델을 처음 만든다. 단독으로 가치 있음 |
| US2 | US1 | 실행할 테스트가 필요 |
| US3 | US2 | 멈출 실행이 필요 |
| US4 | US1, US2 | Step 모델 + 결정적 실행 검증 필요 |
| US5 | US3, US4 | AI 실행 + 세션 유지 편집 필요 |
| US6 | US3, US4 | 수동 편집 위치 + AI 실행 필요 |
| US7 | US1 | 후보 데이터가 필요. US2~US6와는 독립 |

**US7은 US2 직후에도 넣을 수 있다.** 실패 진단 가치가 커지므로 일정이 허락하면 앞으로 당긴다.

### 주요 파일 경합 (병렬 실행 시 주의)

| 파일 | 손대는 작업 | 순서 |
|------|-------------|------|
| `api/routes/sessions.py` | T061 → T086 → T098 → T114 → T123 → T131 | 직렬 |
| `api/routes/steps.py` | T097 → T139 | 직렬 |
| `execution/runner.py` | T042 → T082 → T101 | 직렬 |
| `authoring/agent.py` | T112 → T125 | 직렬 |
| `frontend/pages/Runner.tsx` | T068 → T090 | 직렬 |
| `frontend/components/PauseActions.tsx` | T103 → T132 | 직렬 |
| `tests/integration/test_replay_no_llm.py` | T071 → T118 → T133 | 직렬 |
| `tests/integration/test_performance.py` | T070 → T091 | 직렬 |

## Parallel Execution Examples

**Phase 0 — 가정 검증 (T003 이후 대부분 병렬)**

```
T002, T004, T005, T006, T007, T008, T009  ← 서로 다른 스파이크 스크립트
```

**Phase 2 — 도메인 모델**

```
T018, T019  ← 병렬 (locator.py, assertion.py)
       ↓
T020        ← 둘에 의존
T021, T022  ← T020과 병렬 가능 (다른 파일)
```

**Phase 2 — 저장·비밀·프론트 기반**

```
T030, T033, T035, T044, T045, T046  ← 서로 다른 파일, 병렬
```

**Phase 3 — US1 테스트 먼저**

```
T047, T048, T049, T050, T051, T052  ← 6개 병렬 작성
```

**Phase 3 — US1 프론트엔드**

```
T064, T065, T066  ← 병렬 (TestList, CreateTest, ProjectSetup)
```

**Phase 4 — US2 테스트**

```
T071, T072, T073, T074, T075, T076, T077  ← 7개 병렬
```

**Phase 10 — 마감**

```
T143, T144, T145, T146  ← 병렬
T149, T150, T151        ← 병렬
```

## Implementation Strategy

### MVP 우선 (권장)

1. **Phase 0 → Phase 1 → Phase 2** 를 끝낸다. 여기까지가 기반이며 가장 되돌리기 어렵다
2. **Phase 3 (US1)** 을 완료한다 → **여기서 멈추고 검증한다.** 녹화해서 Step 목록을 얻는 것만으로도
   PRD §3 G1(코드 없이 테스트 생성)의 최소 약속이 성립한다
3. quickstart §2·§3 을 통과하면 MVP 데모 가능

### 증분 인도

- **증분 1**: Phase 0~3 — 녹화해서 Step 목록을 얻고 저장한다
- **증분 2**: + Phase 4 (US2) — 저장한 테스트를 반복 실행하고 실패를 진단한다. **여기서 원칙 II·IV가
  검증된다.** 제품의 핵심 가치(결정적 재실행)가 완성되는 지점
- **증분 3**: + Phase 5 (US3) — **제품의 핵심 차별점**(Pause → Edit → Resume)이 동작한다.
  원칙 III가 검증된다
- **증분 4**: + Phase 6~8 (US4~US6) — AI 작성과 사람 인수. PRD §20의 핵심 가설을 검증할 수 있게 된다
- **증분 5**: + Phase 9~10 — Locator 진단과 마감

### 중단 판단 지점

**증분 2 이후가 가장 중요한 판단 지점이다.** 여기까지 왔을 때 SC-003(재실행 성공률 95%)과
SC-008(후보 2개 이상 90%)이 목표에 미달하면, AI 기능(증분 4)을 추가해도 가치가 나오지 않는다.
결정적 실행의 신뢰도가 AI 작성의 전제이기 때문이다. 이 경우 Locator 전략(R4)을 먼저 개선한다.

### 병렬 팀 전략

Phase 2 완료 후, 프론트엔드와 백엔드를 나눠 진행할 수 있다. 계약(`contracts/`)과 생성된 타입
(`frontend/src/types/generated/`)이 경계가 된다. **다만 US1~US3은 백엔드 동작 없이는 검증이 불가하므로,
프론트엔드가 앞서 가면 검증되지 않은 UI가 쌓인다.** 스토리 단위로 함께 완료하는 것을 권한다.
