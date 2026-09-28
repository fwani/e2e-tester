---

description: "Task list for 023 입력 칸의 두 빈칸"
---

# Tasks: 입력 칸의 두 빈칸 — 값을 읽지 못하고, 키로 확정하지 못한다

**Input**: Design documents from `/specs/023-input-value-assertion/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/)

**Tests**: **포함한다.** 선택이 아니라 헌법의 품질 게이트 3이 요구한다 — 「제품은 테스트
도구다. 자기 테스트 없이 내보내는 것은 허용되지 않는다」. **녹화기**·실행기 상태 기계·
생성기는 각각 단위 테스트가 필요하고, 사용자 대면 흐름마다 통합 시나리오가 최소 하나
필요하다. 녹화기는 이번에 처음 변경되므로 특히 해당한다.

**Organization**: User Story 별로 묶는다. 각 Story 는 독립적으로 구현·검증·전달된다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: US1 키 입력 · US2 입력값 검증 · US3 내보내기 · US4 오용 방지
- 파일 경로를 반드시 적는다

## Path Conventions

- 백엔드: `backend/src/itb/…` · 테스트 `backend/tests/{unit,contract,integration}/…`
- 프론트: `frontend/src/…`
- 고정 대상: `fixtures/sample-app/…` — **제품이 아니라 테스트 대상**이다

---

## Phase 1: Setup (고정 대상과 실측)

**Purpose**: 재료를 갖추고, 문구를 쓰기 전에 사실을 확인하고, **고친 것을 나중에 증명할 수
있도록 고장을 먼저 기록한다.**

- [X] T001 [P] `fixtures/sample-app/projects.html` 의 생성 모달에 여러 줄 입력 칸(`<textarea id="pdesc">`)을 더한다 — FR-008(줄바꿈 포함 관찰) 검증용
- [X] T002 [P] 같은 화면에 **키로 확정하는 태그 칸**을 더한다 — 입력 후 Enter 또는 Space 를 누르면 칩이 추가되고 **칸이 비워진다.** 마지막 성질이 이 기능이 고치는 결함의 원인이므로 빠뜨리면 검증이 아무것도 하지 않는다
- [X] T003 **`<select>` 의 값이 실제로 무엇으로 관찰되는지 실측한다** — `#ptype`(보이는 글자 `분석`, 값 `analysis`)에 Playwright 의 값 읽기를 걸어 확인하고 [research.md](./research.md) R8 의 미확인 항목을 해소한다. **결과를 확인하기 전에는 FR-033 문구를 쓰지 않는다** — 안내가 사실과 다르면 없느니만 못하다
- [X] T004 [P] **숨겨진 요소의 값이 읽히는지 실측한다** *(analyze U1)* — 명세 Edge Cases 의 「숨겨져 있어도 값은 읽힌다」는 확인되지 않은 주장이다. `display:none` 인 칸으로 확인하고, 다르면 [spec.md](./spec.md) 를 고친다
- [X] T005 **키 입력의 고장을 먼저 재현해 기록한다** ([quickstart §10-1](./quickstart.md)) — T002 의 태그 칸에서 `E2E` + Enter 를 녹화하고, **입력 Step 하나가 빈 값으로 남는 것**을 확인해 적는다. 이것을 보지 않으면 나중에 무엇을 고쳤는지 증명할 수 없다

**Checkpoint**: 재료가 갖춰졌고, 안내 문구의 근거가 확정됐고, 고장이 기록됐다

---

## Phase 2: Foundational (모든 Story 의 전제)

**Purpose**: DSL 에 값을 둘 더하고 소비자가 따라갈 수 있게 한다

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 User Story 도 시작할 수 없다. 헌법 원칙 I —
**DSL 스키마를 먼저 바꾸고 소비자가 따른다.**

### 검증 종류

- [X] T006 `backend/src/itb/domain/assertion.py` 의 `AssertionKind` 에 `VALUE = "value"` 를 더하고, 「화면에 표시된 텍스트」와의 차이를 docstring 으로 적는다
- [X] T007 같은 파일의 **모듈 docstring 첫머리를 정정한다** — 「입력 필드 현재값 검증은 범위가 아니다 (001 FR-013c)」가 이제 사실이 아니다. 023 이 그 판단을 뒤집었음과 그 이유를 적는다
- [X] T008 같은 파일에서 `VALUE_COMPARING_KINDS` 에 `VALUE` 를 더한다 — 이것만으로 부정 비교가 열린다. `_check_negation` 은 **고치지 않는다**
- [X] T009 같은 파일의 `_check_shape` 에 `VALUE` 규칙을 더한다 — `target` 필수, 비어 있지 않은 `value` 필수. [data-model §2](./data-model.md) 의 표가 권위다. **기존 종류의 허용 범위는 넓히지도 좁히지도 않는다**
- [X] T010 [P] `backend/tests/unit/test_domain_invariants.py` 에 `value` 형태 규칙 테스트를 더한다 — 대상 없음 거절 · 값 없음 거절 · 부정 비교 넷 모두 허용 · **기존 6종 동작 불변**

### Step 종류

- [X] T011 `backend/src/itb/domain/step.py` 에 `PressKey` 열거형(`Enter`·`Space`·`Tab`·`Escape`)과 `PressStep`(`target` 필수 + `key` 필수)을 더하고 `StepType`·`Step` 판별 유니온에 연결한다. [data-model §7](./data-model.md) 이 권위다. **왜 자유 문자열이 아닌지**를 docstring 에 적는다 ([research R12](./research.md))
- [X] T012 [P] `backend/tests/unit/test_domain_invariants.py` 에 `PressStep` 형태 테스트를 더한다 — 대상 없음 거절 · 범위 밖 키 거절 · 네 키 모두 허용 · **기존 9종 동작 불변**

### 공통

- [X] T013 스키마를 재생성한다 — `cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types`. 생성 타입에 `"value"` 와 `press` Step 이 들어왔는지 확인한다
- [X] T014 `backend/src/itb/execution/element_probe.py` 에 **후보 묶음과 요소 서술(`tag`·`attributes`)을 함께 돌려주는 진입점**을 더한다. 기존 `collect_by_selector` 는 서술을 버리는데 대상 성질 판정에 `type` 이 필요하다 ([research R1](./research.md)). **Python 에 판별 규칙을 복제하지 않는다** — `__itbDescribe` 가 주는 것을 전달만 한다
- [X] T015 [P] `backend/tests/unit/` 에 T014 진입점의 단위 테스트를 더한다

**Checkpoint**: 두 종류가 존재하고, 양쪽 언어가 그것을 알고, 성질을 읽을 통로가 있다

---

## Phase 3: User Story 1 — 키를 눌러 값을 확정한다 (Priority: P1) 🎯

**Goal**: 태그 칸에 값을 넣고 Enter/Space 로 확정하는 것이 Step 으로 남고 재실행된다.
녹화가 값을 잃지 않는다.

**Independent Test**: 태그 칸 조작을 녹화해 Step 두 개(입력 + 키 입력)가 남는지 보고
재실행한다. 입력값 검증 없이도 독립적으로 가치를 낸다.

**Why first**: 이것이 없으면 **작성이 거기서 멈춘다.** 검증 하나가 실패하는 것과 다른
종류의 고장이다.

### 녹화 — 이번에 처음 손대는 곳이다

- [X] T016 [US1] `backend/src/itb/recording/injected/recorder.js` 에 `keydown` 경로를 더한다. **목록에 있는 넷만** 보낸다. 모듈 docstring 에 **왜 이제 `keydown` 을 듣는지**를 적는다 — 기존 주석은 「키 단위가 아니라 확정된 값을 잡는다」이고, 그 논거는 *값*에 대한 것이지 *키*에 대한 것이 아니다 ([research R10](./research.md))
- [X] T017 [US1] 같은 파일에서 **IME 조합 중의 키를 버린다** (FR-055). 브라우저가 주는 조합 상태로 가른다 — **시간 간격이나 값 변화로 추측하지 않는다.** 추측은 한국어·일본어·중국어에서 각각 다르게 틀린다. [contracts/key-input-surface §3](./contracts/key-input-surface.md) 이 권위다
- [X] T018 [US1] `backend/src/itb/recording/recorder.py` 에 `PressStep` 기록 경로를 더한다. 후보 수집은 기존 경로를 그대로 쓴다 (원칙 IV). **같은 키를 연달아 누르면 접지 않는다** (FR-057) — Enter 두 번은 Enter 한 번과 다른 동작이다
- [X] T019 [US1] 같은 파일에서 **키 입력 뒤의 빈 값 확정이 앞선 입력 Step 을 갱신하지 않게 한다** (FR-056). `_find_recent_fill` 의 갱신 조건에 「그 사이에 키 입력이 있었는가」를 더한다. [research R11](./research.md) 이 이 동작의 현재 모습을 적어 두었다
- [X] T020 [US1] 목록에 없는 키를 눌렀을 때 **기록되지 않았다는 사실을 알린다** (FR-060). 021 의 경고 통로(`add_edit_warning`)를 쓴다. 조용히 빠지면 사용자는 재실행이 왜 다른지 알 수 없다
- [X] T021 [P] [US1] `backend/tests/integration/test_press_recording.py` 를 만든다 — **영문**: `E2E` + Enter 가 Step 둘로 남고 입력 값이 `E2E` 로 보존됨
- [X] T022 [P] [US1] **한글 IME 테스트를 같은 파일에 더한다** ★ — `테스트` 입력 후 Enter 두 번(조합 확정 + 제출)에서 **키 입력 Step 이 하나만** 남는지. **영문 테스트만으로는 이 결함을 잡을 수 없다** — 영문은 Enter 가 한 번뿐이라 언제나 통과한다
- [X] T023 [P] [US1] 같은 파일에 FR-057(연속 키를 접지 않음)과 FR-060(범위 밖 키 안내) 시나리오를 더한다

### 실행

- [X] T024 [US1] `backend/src/itb/execution/step_executor.py` 에 `PressStep` 실행을 더한다 — **대상 요소에** 키를 보낸다. 포커스에 보내지 않는다 (FR-051). 대상을 찾지 못하면 기존 규칙대로 실패한다
- [X] T025 [P] [US1] `backend/tests/integration/` 에 실행 테스트를 더한다 — 태그가 실제로 추가됨 · 대상 없으면 실패 · **키를 눌렀는데 화면이 안 바뀌어도 성공**(동작 Step 은 결과를 판정하지 않는다)

### AI 작성

- [X] T026 [US1] `backend/src/itb/authoring/tools.py` 에 **키 입력 도구**를 더하고 `STEP_PRODUCING_TOOLS` 에 넣는다 (9 → 10). 도구 설명에 **입력 후 키로 확정하는 칸(태그 입력 등)에 쓴다**를 적는다 (FR-058). 지원하는 넷을 명시해 모델이 없는 키를 지어내지 않게 한다
- [X] T027 [US1] 범위 밖 키 요청을 **거절하고 지원 목록을 함께 알린다.** 「지원하지 않습니다」로 끝내면 모델이 다른 키를 또 시도한다 ([contracts/key-input-surface §5](./contracts/key-input-surface.md))
- [X] T028 [P] [US1] `backend/tests/unit/test_tool_surface.py` 의 기존 검사가 10:10 대응을 요구하므로 그대로 통과해야 한다. 거절 문구가 지원 목록을 담는지 확인하는 테스트를 더한다

### 표시

- [X] T029 [US1] 표시 이름에 **어느 키인지**를 넣는다 (FR-059) — `Enter 키 입력` 형태. 「키 입력」만 있으면 목록에서 Enter 와 Escape 를 구별할 수 없고 그 둘은 정반대 동작이다. 녹화 경로와 AI 경로가 **같은 문구**를 쓴다
- [X] T030 [US1] 프론트의 Step 종류별 표시 문구에 `press` 를 더한다 (`frontend/src/lib/wording.ts` 와 Step 목록·상세). 문구의 소유자는 `wording.ts` 다
- [X] T031 [P] [US1] 표시 이름 테스트를 더한다 — **네 키 모두** 이름이 다른지

**Checkpoint**: 태그 칸이 녹화되고 재실행된다. **한글에서도 그렇다.**

---

## Phase 4: User Story 2 — 「그 칸에 이 값이 들어 있어야 한다」 (Priority: P1)

**Goal**: 입력값 검증을 만들고 실행할 수 있다. 비밀번호 값은 어디에도 남지 않는다.

**Independent Test**: 이름 칸에 값을 넣고 입력값 검증을 만들어 실행한다. 지금 100%
실패하던 시나리오가 통과한다.

### 실행

- [X] T032 [US2] `backend/src/itb/execution/step_executor.py` 에 `_assert_value` 를 더한다. **관찰 함수만 다르게 하여** 기존 `_watch` 에 넘긴다 — 대기·비교·실패 설명 조립은 재사용한다 ([research R5](./research.md)). `_matches` 와 `_EXPECTATION_VERBS` 는 손대지 않는다
- [X] T033 [US2] 같은 파일의 `_assert` 분기에 `AssertionKind.VALUE` 를 연결한다. 대상을 찾지 못하면 **긍정·부정 모두 실패**한다 (FR-006)
- [X] T034 [P] [US2] `backend/tests/integration/test_input_value_assertion.py` 를 만든다 — 값 일치 통과 · 빈 칸 실패(관찰값 `''` 가 설명에 나옴) · 포함 통과 · 여러 줄 칸의 줄바꿈 보존(FR-008) · 늦게 채워지는 값을 기다려 통과
- [X] T035 [P] [US2] 같은 파일에 부정 비교 시나리오를 더한다 — `not_equals` 실패 · 021 의 관찰 기간이 값 비교에서도 같게 도는지

### 작성

- [X] T036 [US2] `backend/src/itb/execution/assertion_builder.py` 의 `ELEMENT_KINDS` 에 `VALUE` 를 더한다
- [X] T037 [US2] 같은 파일의 `default_label` 에 `VALUE` 분기를 더한다 — `입력값이 '…'{비교} 확인`. 주어가 `텍스트` 가 아니라 `입력값` 인 것이 목록에서 두 종류를 가르는 단서다. **`# pragma: no cover - enum 이 6종을 덮는다` 주석도 함께 고친다**
- [X] T038 [P] [US2] `backend/tests/unit/test_definition_summary.py` 에 **7종 전부의 표시 이름** 테스트를 더한다. `default_label` 의 폴백은 조용하므로 ([data-model §5](./data-model.md)) 테스트가 유일한 방어다
- [X] T039 [US2] `backend/src/itb/authoring/tools.py` 의 `assert_condition` docstring 의 `kind` 목록에 `value` 를 더하고 대상이 필요함을 적는다. **기존의 「기대와 달라도 Step 으로 기록된다 — 값을 바꾸거나 조건을 뒤집어 다시 시도하면 안 된다」는 그대로 둔다** (FR-009)
- [X] T040 [P] [US2] `backend/tests/unit/test_tool_surface.py` 에 도구 설명이 `value` 를 담는지 확인하는 테스트를 더한다

### 화면

- [X] T041 [US2] `frontend/src/lib/wording.ts` 에 `value` 문구를 더한다 — `ASSERTION_KIND_LABEL` 은 `입력값`, `ASSERTION_KIND_HINT` 는 **텍스트 검증과의 차이를 직접 말한다**(「입력 칸·선택 목록에 담긴 값을 본다. 화면에 보이는 글자가 아니다」). `comparesValue`·`assertionSummary` 도 덮는다
- [X] T042 [US2] `frontend/src/components/AssertionForm.tsx` 의 `KINDS` 에 `value` 를 **텍스트 바로 아래** 넣고, `NEEDS_TARGET`·`NEEDS_VALUE` 양쪽에 더한다. 두 집합에 함께 드는 첫 종류다
- [X] T043 [P] [US2] 프론트 테스트에 입력값 검증 선택 시의 폼 상태를 더한다

### 보안 — 비밀번호 값이 남지 않는다 (FR-015~FR-017)

**이 기능의 유일한 새 보안 위험이다.** 위 층이 동작한 뒤 얹는다 — 섞어 만들면 마스킹
때문에 실패한 것인지 관찰이 틀린 것인지 가릴 수 없다.

- [X] T044 [US2] `backend/src/itb/execution/assertion_builder.py` 에 **비밀번호 대상 평문 비교 값 거절**을 더한다. 판별은 T014 서술의 `attributes.type === "password"` — 녹화(`recorder.js:889`)와 **같은 출처·같은 규칙**이다. 민감하지 않은 변수 참조도 거절한다 ([contracts/assertion-surface §3](./contracts/assertion-surface.md))
- [X] T045 [US2] 거절을 **두 작성 경로에 모두 연결한다** — `api/routes/steps.py` 와 `authoring/tools.py`. [research R3](./research.md): AI 경로는 `build_assertion` 을 지나지 않으므로 한쪽에만 두면 규칙이 절반만 걸린다
- [X] T046 [US2] `backend/src/itb/execution/step_executor.py` 에서 **대상이 비밀번호 칸이면 관찰값을 무조건 마스킹한다.** 스크러버에 기대지 않는다 — 스크러버는 복호화된 값만 알고, 검증이 실패했다는 것은 관찰값이 그 목록에 없다는 뜻이다 ([research R2](./research.md)). **판정은 실제 값으로 한다**
- [X] T047 [P] [US2] `backend/tests/integration/test_value_assertion_secrets.py` 를 만든다 — 평문 거절 · 비민감 변수 참조 거절 · 민감 변수 참조 허용 · **실패 시 관찰값이 설명·실행 결과·어긋남 기록 어디에도 없음** · 그런데도 판정은 정확함
- [X] T048 [P] [US2] 같은 파일에 **저장 후 파일 검사**를 더한다 — 테스트 정의·실행 결과·공유 묶음에 평문이 없는지 기계적으로 확인한다
- [X] T049 [P] [US2] **FR-009·FR-010 이 새 종류에도 성립함을 테스트로 고정한다** *(analyze C1·C2)* — `test_classify_assertion.py` 와 `test_authoring_mismatch.py` 에 `value` 사례를 더한다. `classify_assertion`(`domain/run_result.py:341`)은 종류 무관 함수라 저절로 만족되지만, **그 사실이 적혀 있지 않으면 잊은 것인지 의도한 것인지 알 수 없다**

**Checkpoint**: 입력값 검증이 동작하고, 비밀번호 값은 어디에도 남지 않는다

---

## Phase 5: User Story 3 — 내보낸 테스트도 같은 동작과 판정을 한다 (Priority: P2)

**Goal**: 두 새 종류가 표준 Playwright 로 옮겨지고, 제품 없이 실행해도 같은 결과가 나온다.

**Independent Test**: 같은 정의를 제품 안에서 한 번, 내보낸 프로젝트에서 한 번 실행해
비교한다.

**Note**: 생성기는 모르는 종류에 `UnsupportedStepError` 를 던진다 — **US1·US2 가 끝나
사용자가 그 정의를 만들 수 있게 되는 순간부터 내보내기가 깨진다.** 조용히 틀리지 않는 것이
다행이지만, 미루면 원칙 V 위반 상태가 길어진다. **둘을 함께 한다** — 생성기는 같은 파일에서
두 종류를 다루고, 하나만 반영하면 다른 쪽 정의가 든 테스트가 여전히 깨진다.

- [X] T050 [US3] `backend/src/itb/generator/playwright_gen.py` 에 `PressStep` 분기를 더한다 — `locator.press('Enter', { timeout })`. **`keyboard.press` 가 아니다** (FR-051). 키 열거값이 표준 도구의 키 이름과 같은 철자라 변환표를 두지 않는다 ([contracts/export-mapping §6](./contracts/export-mapping.md))
- [X] T051 [US3] 같은 파일의 `_assertion_lines` 에 `VALUE` 긍정 비교를 더한다 — `equals` → `toHaveValue`, `contains` → `expect.poll(…).toContain(…)` ([contracts/export-mapping §2](./contracts/export-mapping.md) — 정규식으로 감싸지 않는 이유가 거기 있다)
- [X] T052 [US3] 같은 파일에 `VALUE` 부정 비교를 더한다 — 021 의 `_watch_window` 로 감싼다. 루프가 관찰 기간을 담당하므로 안쪽에서 또 기다리지 않는다
- [X] T053 [P] [US3] `backend/tests/unit/test_generator.py` 에 `press` 네 키와 `value` 네 비교 방식의 생성 결과 테스트를 더한다 — **[contracts/export-mapping.md](./contracts/export-mapping.md) 의 표와 글자 단위로 대조한다**
- [X] T054 [P] [US3] `backend/tests/unit/test_export_keeps_assertion.py` 에 두 종류가 내보내기에서 보존되는지, 민감 변수가 `process.env.NAME` 으로 나가는지 더한다
- [X] T055 [US3] **왕복 정합을 한 번 완주한다** (헌법 품질 게이트 2) — 기록 → 저장 → 제품 내 실행 → 내보내기 → 내보낸 테스트 실행. **두 종류를 함께 넣는다.** 키 입력은 녹화 경로가 바뀌므로 이 게이트가 특히 중요하다

**Checkpoint**: 원칙 V 가 회복됐다

---

## Phase 6: User Story 4 — 잘못 고른 검증이 조용히 지나가지 않는다 (Priority: P3)

**Goal**: 값이 없는 대상은 거절하고, 선택 목록의 함정은 알리고, 입력 칸에 텍스트 검증을
고른 사람에게 올바른 길을 가리킨다.

**Independent Test**: 각 오용 상황을 하나씩 만들어 보고 화면·결과·작성 도구가 그 사실을
말하는지 확인한다.

- [X] T056 [US4] `backend/src/itb/execution/assertion_builder.py` 에 **대상 성질 판정 함수**를 더한다. 세 갈래는 [data-model §3](./data-model.md) 의 표가 권위다. **태그를 읽지 못하면 거절하지 않는다** — 판정 실패를 거절로 바꾸면 정당한 대상이 막힌다
- [X] T057 [US4] 거절 문구를 쓴다. **무엇을 할 수 없는지만이 아니라 무엇을 대신 할 수 있는지를 담는다** — 체크박스는 「값이 체크 여부와 무관하고 체크 상태 검증은 아직 없다」, 값 없는 태그는 **텍스트 검증을 가리킨다**(이 기능이 고치려는 실수의 반대 방향이다)
- [X] T058 [US4] T056 을 **두 작성 경로에 연결한다** — `steps.py`(오류 응답)와 `tools.py`(`{"error": …}`)
- [X] T059 [US4] 선택 목록 안내를 더한다 (FR-033) — **경고가 아니라 조언의 문체**로 쓴다. **T003 실측 결과와 문구가 일치하는지 확인한다**
- [X] T060 [US4] 입력 칸 대상 텍스트 검증 경고를 더한다 (FR-030) — 「이 대상에서는 언제나 빈 문자열로 관찰됩니다. 칸에 담긴 값을 보려면 입력값 검증을 쓰세요」. **막지 않는다** — 하위 호환(FR-040)과 충돌한다. `select` 는 자식 `option` 의 글자를 텍스트로 가지므로 경고하지 않는다
- [X] T061 [US4] `backend/src/itb/authoring/tools.py` 의 도구 설명에 **「입력 칸·선택 목록의 값을 볼 때는 `text` 가 아니라 `value`」** 를 더한다 (FR-034). 비밀번호 칸은 민감 변수 참조로만 비교한다는 것도 적는다
- [X] T062 [US4] `frontend/src/lib/wording.ts` 에 선택 목록 안내를 더하고 `AssertionForm.tsx` 가 대상이 선택 목록일 때 보여 준다
- [X] T063 [P] [US4] `backend/tests/contract/test_value_target_surface.py` 를 만든다 — 세 갈래 판정 · 거절 문구가 대안을 담는지 · **두 경로가 같은 판정을 하는지**(한쪽만 거절하면 실패)
- [X] T064 [P] [US4] `backend/tests/integration/` 에 오용 시나리오를 더한다 — 체크박스 거절 · 버튼 거절 · 선택 목록은 만들어지고 안내가 붙음 · 입력 칸 텍스트 검증은 경고만 뜨고 Step 은 만들어짐

**Checkpoint**: 네 User Story 가 모두 독립적으로 동작한다

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: 하위 호환 확인과 전량 검증. **여기서 조용한 누락을 잡는다.**

- [X] T065 [P] **검증 종류의 `match` 분기가 전부 7종을 덮는지 훑는다.** 프론트는 타입 검사가 잡아 주지만 백엔드는 아니다 ([data-model §5](./data-model.md)). `AssertionKind` 를 쓰는 모든 파일을 확인한다
- [X] T066 [P] **Step 종류의 분기가 전부 10종을 덮는지 훑는다** ([data-model §10](./data-model.md)). 조용한 넷이 여기 있다 — `STEP_PRODUCING_TOOLS`·녹화기 이벤트 경로·Step 표시 문구·**Excel 내보내기의 수행 절차 문구**
- [X] T067 [P] **하위 호환 검증** — 023 이전에 저장된 테스트를 파일 변경 없이 열고·실행하고·내보내고·공유한다. 입력 칸 대상 텍스트 검증이 **자동으로 바뀌지 않았는지** 확인한다 (FR-041)
- [X] T068 **FR-043 — 녹화 변경으로 기대값이 달라지는 기존 테스트를 고친다.** 태그 칸 계열 녹화 테스트가 있으면 결과가 「빈 값 입력 Step 하나」에서 「입력 + 키 입력 둘」로 바뀐다. **끄지 말고 새 기대값으로 고치고, 고친 것을 커밋 메시지에 남긴다** (헌법 품질 게이트 4)
- [X] T069 [P] `backend/tests/unit/test_run_controls_unchanged.py` 계열의 기존 테스트가 그대로 통과하는지 확인한다
- [X] T070 **재실행 경로에 LLM 도달 경로가 없음을 확인한다** (헌법 품질 게이트 1, 원칙 II). 이번에 더한 관찰 함수·마스킹·성질 판정·키 전송 중 실행 경로에 드는 것들이 대상이다
- [ ] T071 백엔드 전량 검증 — **`cd backend && bash scripts/test-backend.sh`** · `uv run ruff check src tests` · `uv run lint-imports`. *(구현 중 정정: 초안은 `uv run pytest` 라고 적었는데, 그 명령은 `timing` 계층을 병렬에 섞어 60건을 errors 로 만든다. 표준 스크립트가 두 계층을 나눠 돈다.)*
- [ ] T072 프론트 전량 검증 — `cd frontend && npx tsc --noEmit && npx vitest run`. *(구현 중 정정: `npm test` 는 watch 모드라 끝나지 않고, `npm run lint` 스크립트는 없다.)*
- [ ] T073 **[quickstart.md](./quickstart.md) §1~§12 를 사람이 손으로 수행하고 결과를 기록한다.** 자동 검증이 덮지 못하는 것(거절 문구가 다음 행동을 알려 주는지, 목록에서 종류들이 구별되는지, 안내가 눈에 들어오는지)을 본다. **§10-3(한글 태그)과 §6(비밀번호)이 가장 중요하다.** §8 은 SC-007(AI 가 입력값 검증을 고름)의 **유일한** 검증 수단이다 *(analyze C3 — 모델의 선택은 자동 신호로 고정할 수 없다)*

---

## Dependencies & Execution Order

### Phase 의존

```
Phase 1 (Setup)                    — 즉시 시작 가능
      ↓
Phase 2 (Foundational)             — 모든 Story 를 막는다. 스키마가 먼저다 (원칙 I)
      ↓
  ┌───┴────────┬──────────┐
Phase 3      Phase 4    Phase 6    — Phase 2 후 서로 독립. 병행 가능
 (US1 키)     (US2 값)   (US4 안내)
  └───┬────────┴──────────┘
      ↓
Phase 5 (US3 내보내기)             — 두 종류가 정의에 존재해야 내보낼 것이 생긴다
      ↓
Phase 7 (Polish)
```

### Phase 를 건너뛰는 의존

| 의존 | 왜 |
|---|---|
| T003(select 실측) → T059(안내 문구) | 문구가 사실과 달라서는 안 된다 |
| T005(고장 재현) → T021·T022(녹화 테스트) | 고장을 보지 않으면 무엇을 고쳤는지 증명할 수 없다 |
| T016(keydown) → T019(갱신 차단) | **「방금 키가 눌렸다」를 알아야 막을 수 있다.** 순서를 뒤집으면 무엇을 기준으로 막을지 알 수 없다 |
| T014(서술 진입점) → T044·T056 | `type` 을 읽을 통로가 있어야 판정이 된다 |

### User Story 의존

- **US1 (P1)**: Phase 2 후 시작. 다른 Story 에 의존하지 않는다
- **US2 (P1)**: Phase 2 후 시작. US1 과 독립 — 둘 중 **어느 하나만 해도** 못 하던 일이 된다
- **US3 (P2)**: US1·US2 중 만든 것이 있어야 내보낼 것이 생긴다
- **US4 (P3)**: Phase 2 후 시작. US2 와 같은 파일을 만지므로 순차가 편하다

### Phase 3 내부 순서

```
T016~T017 (keydown · IME)
      ↓
T018~T020 (Step 기록 · 갱신 차단 · 안내)    ← 키의 존재를 전제한다
      ↓
T021~T023 (녹화 테스트)
T024~T031 (실행 · AI · 표시)                 ← 위와 독립, 병행 가능
```

### Phase 4 내부 순서

```
T032~T035 (실행)  ─┐
T036~T040 (작성)  ─┼→ T044~T049 (보안)   ← 위 층들이 동작한 뒤에 얹는다
T041~T043 (화면)  ─┘
```

### 병행 가능한 것

- T001·T002·T004 (Setup, 서로 무관 — T003·T005 는 실측이라 단독)
- T010·T012·T015 (Foundational 의 테스트)
- T021·T022·T023 (녹화 테스트) · T025 · T028 · T031
- T034·T035 (실행 테스트) · T038·T040·T043
- T047·T048·T049 (보안 테스트)
- T053·T054 (생성기 테스트)
- T063·T064 (오용 테스트)
- T065·T066·T067·T069 (Polish 의 훑기 작업들)
- **Phase 3·4·6 전체** — 사람이 여럿이면 Story 단위로 나눈다

### 같은 파일이라 병행하면 안 되는 것

| 파일 | 부딪히는 작업 |
|---|---|
| `authoring/tools.py` | T026·T027 (키 도구) · T039 (검증 설명) · T045 (보안) · T058·T061 (거절·안내) |
| `execution/assertion_builder.py` | T036·T037 · T044 · T056·T057 |
| `execution/step_executor.py` | T024 (키 실행) · T032·T033 (값 관찰) · T046 (마스킹) |
| `generator/playwright_gen.py` | T050·T051·T052 |
| `frontend/src/lib/wording.ts` | T030 (키) · T041 (검증) · T062 (안내) |

---

## Implementation Strategy

### 두 MVP 중 하나를 고를 수 있다

US1 과 US2 는 독립이고 각각 지금 깨져 있는 시나리오를 하나씩 고친다.

| 먼저 하면 | 무엇이 풀리나 |
|---|---|
| **US1 (키 입력)** | 태그 칸에서 **멈추던 작성이 끝까지 간다.** 녹화가 값을 잃지 않는다 |
| **US2 (입력값 검증)** | 100% 실패하던 검증이 통과한다 |

**US1 을 먼저 권한다** — 작성이 중단되는 것이 검증 하나가 실패하는 것보다 나쁘다.

### 점진 전달

1. Phase 1~2 → 기반 (두 종류가 존재한다)
2. **US1** → 태그 칸이 동작한다. **한글로 검증한다**
3. **US2** → 입력값 검증이 동작한다. 비밀번호가 새지 않는다
4. **US3** → 내보낸 테스트도 같다 (원칙 V 회복)
5. **US4** → 오용이 조용히 지나가지 않는다
6. Phase 7 → 하위 호환과 전량 검증

---

## Notes

- `[P]` = 다른 파일, 의존 없음
- 각 작업 또는 논리적 묶음마다 커밋한다
- **체크포인트에서 멈춰 Story 를 독립적으로 검증할 수 있다**
- **조용히 누락되는 자리**를 기억한다:
  - 검증 종류 ([data-model §5](./data-model.md)) — `default_label` · `assertion_builder` 의
    집합 · AI 도구 설명 · 프론트 `KINDS` 배열
  - Step 종류 ([data-model §10](./data-model.md)) — `STEP_PRODUCING_TOOLS` · 녹화기 이벤트
    경로 · Step 표시 문구 · Excel 내보내기 문구
  - 생성기와 프론트 문구 사전은 **알아서 깨지므로** 걱정하지 않아도 된다
- **한글 없이 이 기능을 검증했다면 검증하지 않은 것이다** (T022 · quickstart §10-3)


---

## 구현 후 기록 — 전량 검증이 찾은 것 (2026-09-28)

부분 실행만 보고 통과라고 판단한 것을 전량이 정정했다. **실제 결함이 둘 있었고, 둘 다
저장소의 자체 방어 장치가 잡았다.**

| 무엇 | 왜 몰랐나 | 무엇이 잡았나 |
|---|---|---|
| `build_tools` 반환 목록에 `press` 누락 | `test_tool_surface.py` 는 **이름 목록**을 보고, 이쪽은 **실제로 만들어진 도구 객체**를 본다. 앞의 것만 보고 통과라고 판단했다 | `test_browser_tools_are_the_only_allowed_tools` |
| `url` 검증의 조기 반환을 `BuiltAssertion` 으로 안 감쌈 | 주소 검증은 요소를 보지 않아 **안내가 붙을 일이 없으므로** 형태를 맞출 이유가 없어 보였다 | e2e `test_us3_pause_edit_resume` |

둘째가 더 나쁘다 — **023 과 무관한 기존 기능(주소 검증)을 깨뜨렸다.**

### 검증 실행 방식도 틀렸었다

`uv run pytest` 로 돌려 `timing` 계층 60건이 errors 로 나왔다. 그 계층은 **순차로만**
돌게 설계돼 있고(병렬에 섞이면 건너뛰지 않고 일부러 실패한다 — 헌법 품질 게이트 4),
표준 명령 `scripts/test-backend.sh` 가 두 계층을 나눠 돈다. 순차로 돌리니 **60/60 통과.**

### 기존 실패로 확인된 것

| 항목 | 근거 |
|---|---|
| `test_ui_surface.py` AS-009·025·037·046 | 020 `baseline.md` 가 「020 이전과 같음」으로, 022 T001 이 기준선으로 기록 |
| ruff 4건 (`step_executor.py:726` 등) | 022 T001 이 「ruff 4건」을 기준선으로 기록. `git show` 로 021 파일에도 같은 위반 확인 |
| `ScreenSweep.test.ts` 2건 | 순회 보고서가 019(`aa481ae`, 9/23) 이후 재생성되지 않음. 그 뒤 020·021·022 가 화면 코드를 7개 커밋에 걸쳐 바꿨다. **재생성을 시도했으나 시드 단계에서 멈춤** — 별도 처리가 필요하다 |
