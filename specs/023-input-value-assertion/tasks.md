---

description: "Task list for 023 입력값 검증"
---

# Tasks: 입력값 검증 — 칸에 무엇이 들어 있는지 묻는다

**Input**: Design documents from `/specs/023-input-value-assertion/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/)

**Tests**: **포함한다.** 선택이 아니라 헌법의 품질 게이트 3이 요구한다 — 「제품은 테스트
도구다. 자기 테스트 없이 내보내는 것은 허용되지 않는다」. 녹화기·실행기 상태 기계·생성기는
각각 단위 테스트가 필요하고, 사용자 대면 흐름마다 통합 시나리오가 최소 하나 필요하다.

**Organization**: User Story 별로 묶는다. 각 Story 는 독립적으로 구현·검증·전달된다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 User Story 에 속하는가 (US1 · US2 · US3)
- 파일 경로를 반드시 적는다

## Path Conventions

- 백엔드: `backend/src/itb/…` · 테스트 `backend/tests/{unit,contract,integration}/…`
- 프론트: `frontend/src/…`
- 고정 대상: `fixtures/sample-app/…` — **제품이 아니라 테스트 대상**이다

---

## Phase 1: Setup (고정 대상과 실측)

**Purpose**: 검증에 쓸 재료를 갖추고, 문구를 쓰기 전에 사실을 확인한다

- [ ] T001 [P] `fixtures/sample-app/projects.html` 의 생성 모달에 여러 줄 입력 칸(`<textarea id="pdesc">`)을 더한다 — FR-008(줄바꿈 포함 관찰) 검증용. [research R8](./research.md) 에서 이것만 없다고 확인했다
- [ ] T002 **`<select>` 의 값이 실제로 무엇으로 관찰되는지 실측한다** — `fixtures/sample-app/projects.html` 의 `#ptype`(보이는 글자 `분석`, 값 `analysis`)에 Playwright 의 값 읽기를 걸어 결과를 확인하고 [research.md](./research.md) R8 의 미확인 항목을 해소한다. **결과를 문서에 적기 전에는 FR-033 문구를 쓰지 않는다** — 안내가 사실과 다르면 없느니만 못하다

**Checkpoint**: 재료가 갖춰졌고, 안내 문구가 근거할 사실이 확정됐다

---

## Phase 2: Foundational (모든 Story 의 전제)

**Purpose**: DSL 에 종류를 더하고 소비자가 따라갈 수 있게 한다

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 User Story 도 시작할 수 없다. 헌법 원칙 I —
**DSL 스키마를 먼저 바꾸고 소비자가 따른다.**

- [ ] T003 `backend/src/itb/domain/assertion.py` 의 `AssertionKind` 에 `VALUE = "value"` 를 더하고, 무엇을 보는 종류인지 docstring 으로 적는다 — 「화면에 표시된 텍스트」와의 차이를 명시한다
- [ ] T004 같은 파일의 **모듈 docstring 첫머리를 정정한다** — 「입력 필드 현재값 검증은 범위가 아니다 (001 FR-013c)」가 이제 사실이 아니다. 023 이 그 판단을 뒤집었음과 그 이유를 적는다
- [ ] T005 같은 파일에서 `VALUE_COMPARING_KINDS` 에 `VALUE` 를 더한다 — 이것만으로 부정 비교가 열린다. `_check_negation` 은 **고치지 않는다**
- [ ] T006 같은 파일의 `_check_shape` 에 `VALUE` 규칙을 더한다 — `target` 필수, 비어 있지 않은 `value` 필수. [data-model §2](./data-model.md) 의 표가 권위다. **기존 종류의 허용 범위는 넓히지도 좁히지도 않는다**
- [ ] T007 [P] `backend/tests/unit/test_domain_invariants.py` 에 `value` 종류의 형태 규칙 테스트를 더한다 — 대상 없음 거절 · 값 없음 거절 · 부정 비교 네 가지 모두 허용 · 기존 6종의 동작 불변
- [ ] T008 스키마를 재생성한다 — `cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types`. `frontend/src/types/generated/*.d.ts` 의 `AssertionKind` 에 `"value"` 가 들어왔는지 확인한다
- [ ] T009 `backend/src/itb/execution/element_probe.py` 에 **후보 묶음과 요소 서술(`tag`·`attributes`)을 함께 돌려주는 진입점**을 더한다. 기존 `collect_by_selector` 는 서술을 버리는데, 대상 성질 판정에 `type` 이 필요하다 ([research R1](./research.md)). **Python 에 판별 규칙을 복제하지 않는다** — `__itbDescribe` 가 주는 것을 그대로 전달만 한다
- [ ] T010 [P] `backend/tests/unit/` 에 T009 진입점의 단위 테스트를 더한다 — 서술이 `tag` 와 `attributes.type` 을 담아 오는지, 요소가 없으면 `None` 인지

**Checkpoint**: 종류가 존재하고, 양쪽 언어가 그것을 알고, 성질을 읽을 통로가 있다

---

## Phase 3: User Story 1 — 「그 칸에 이 값이 들어 있어야 한다」 (Priority: P1) 🎯 MVP

**Goal**: 입력값 검증을 만들고 실행할 수 있다. 비밀번호 값은 어디에도 남지 않는다.

**Independent Test**: 프로젝트명 칸에 값을 넣고 입력값 검증을 만들어 실행한다. 지금
100% 실패하던 시나리오가 통과한다. 내보내기·오용 방지 없이도 제품 안에서 가치를 낸다.

### 실행 — 값을 관찰한다

- [ ] T011 [US1] `backend/src/itb/execution/step_executor.py` 에 `_assert_value` 를 더한다. 대상을 찾고(기존 `_locate_target`) **관찰 함수만 다르게 하여** 기존 `_watch` 에 넘긴다 — 대기·비교·실패 설명 조립은 재사용한다 ([research R5](./research.md)). `_matches` 와 `_EXPECTATION_VERBS` 는 손대지 않는다
- [ ] T012 [US1] 같은 파일의 `_assert` 분기에 `AssertionKind.VALUE` 를 연결한다. 대상을 찾지 못하면 **긍정·부정 모두 실패**한다 (FR-006)
- [ ] T013 [P] [US1] `backend/tests/integration/test_input_value_assertion.py` 를 만든다 — 값 일치 통과 · 빈 칸 실패(관찰값 `''` 가 설명에 나옴) · 포함 통과 · 여러 줄 칸의 줄바꿈 보존(FR-008) · 늦게 채워지는 값을 기다려 통과
- [ ] T014 [P] [US1] 같은 파일에 부정 비교 시나리오를 더한다 — `not_equals` 실패 · 021 의 관찰 기간이 값 비교에서도 같게 도는지 (제한 시간을 모두 소모하는지)

### 작성 — 두 경로가 같은 것을 만든다

- [ ] T015 [US1] `backend/src/itb/execution/assertion_builder.py` 의 `ELEMENT_KINDS` 에 `VALUE` 를 더한다 — 대상이 없을 때 「대상 요소가 필요합니다」로 안내된다
- [ ] T016 [US1] 같은 파일의 `default_label` 에 `VALUE` 분기를 더한다 — `입력값이 '…'{비교} 확인`. 주어가 `텍스트` 가 아니라 `입력값` 인 것이 목록에서 두 종류를 가르는 단서다 ([contracts/assertion-surface §7](./contracts/assertion-surface.md)). **`# pragma: no cover - enum 이 6종을 덮는다` 주석도 함께 고친다**
- [ ] T017 [P] [US1] `backend/tests/unit/test_definition_summary.py` 에 **7종 전부의 표시 이름** 테스트를 더한다. `default_label` 의 폴백은 조용하므로 ([data-model §5](./data-model.md)) 테스트가 유일한 방어다
- [ ] T018 [US1] `backend/src/itb/authoring/tools.py` 의 `assert_condition` 도구 docstring 의 `kind` 목록에 `value` 를 더하고, 대상이 필요하다는 것을 적는다. **기존의 「기대와 달라도 Step 으로 기록된다 — 값을 바꾸거나 조건을 뒤집어 다시 시도하면 안 된다」는 그대로 둔다** (FR-009)
- [ ] T019 [P] [US1] `backend/tests/unit/test_tool_surface.py` 에 도구 설명이 `value` 를 담고 있는지 확인하는 테스트를 더한다

### 화면

- [ ] T020 [US1] `frontend/src/lib/wording.ts` 에 `value` 문구를 더한다 — `ASSERTION_KIND_LABEL` 은 `입력값`, `ASSERTION_KIND_HINT` 는 **텍스트 검증과의 차이를 직접 말한다**(「입력 칸·선택 목록에 담긴 값을 본다. 화면에 보이는 글자가 아니다」). `comparesValue` 와 `assertionSummary` 도 새 종류를 덮는다. `Record<AssertionKind, …>` 라 누락은 컴파일이 잡는다
- [ ] T021 [US1] `frontend/src/components/AssertionForm.tsx` 의 `KINDS` 에 `value` 를 **텍스트 바로 아래** 넣고, `NEEDS_TARGET`·`NEEDS_VALUE` 양쪽에 더한다. 두 집합에 함께 드는 첫 종류다 ([data-model §2](./data-model.md))
- [ ] T022 [P] [US1] 프론트 테스트에 입력값 검증 선택 시의 폼 상태를 더한다 — 대상 필수 · 값 필수 · 비교 방식 네 가지 노출 · 부정 안내 유지

### 보안 — 비밀번호 값이 남지 않는다 (FR-015~FR-017)

**이것이 이 기능의 유일한 새 위험이다.** 위 층이 동작한 뒤 그 위에 얹는다 — 섞어 만들면
마스킹 때문에 실패한 것인지 관찰이 틀린 것인지 가릴 수 없다.

- [ ] T023 [US1] `backend/src/itb/execution/assertion_builder.py` 에 **비밀번호 대상 평문 비교 값 거절**을 더한다. 판별은 T009 서술의 `attributes.type === "password"` — 녹화(`recorder.js:889`)와 **같은 출처·같은 규칙**이다. 민감하지 않은 변수 참조도 거절한다 (정의 파일에 값이 남으므로 평문과 같다, [contracts/assertion-surface §3](./contracts/assertion-surface.md))
- [ ] T024 [US1] 거절을 **두 작성 경로에 모두 연결한다** — `backend/src/itb/api/routes/steps.py` 와 `backend/src/itb/authoring/tools.py`. [research R3](./research.md): AI 경로는 `build_assertion` 을 지나지 않으므로 한쪽에만 두면 새 규칙이 절반만 걸린다
- [ ] T025 [US1] `backend/src/itb/execution/step_executor.py` 에서 **대상이 비밀번호 칸이면 관찰값을 무조건 마스킹한다.** 스크러버에 기대지 않는다 — 스크러버는 복호화된 값만 알고, 검증이 실패했다는 것은 관찰값이 그 목록에 없다는 뜻이다 ([research R2](./research.md)). **판정은 실제 값으로 한다** — 마스킹은 설명 문자열만 바꾼다 (원칙 II)
- [ ] T026 [P] [US1] `backend/tests/integration/test_value_assertion_secrets.py` 를 만든다 — 평문 거절 · 비민감 변수 참조 거절 · 민감 변수 참조 허용 · **실패 시 관찰값이 설명·실행 결과·작성 시점 어긋남 어디에도 나오지 않음** · 그런데도 판정은 정확함
- [ ] T027 [P] [US1] 같은 파일에 **저장 후 파일 검사**를 더한다 — 테스트 정의·실행 결과·공유 묶음에 평문이 없는지 기계적으로 확인한다 (quickstart §6-3 의 `grep` 을 자동화)

**Checkpoint**: 입력값 검증이 동작하고, 비밀번호 값은 어디에도 남지 않는다. **MVP 완성.**

---

## Phase 4: User Story 2 — 내보낸 테스트도 같은 판정을 한다 (Priority: P2)

**Goal**: 정의를 표준 Playwright 로 내보내 제품 없이 실행해도 같은 결과가 나온다.

**Independent Test**: 같은 정의를 제품 안에서 한 번, 내보낸 프로젝트에서 한 번 실행해
통과·실패를 비교한다.

**Note**: 생성기는 모르는 종류에 `UnsupportedStepError` 를 던진다 — **Phase 2 가 끝난
순간부터 입력값 검증이 든 테스트는 내보낼 수 없다.** 조용히 틀리지 않는 것이 다행이지만,
이 Phase 는 미루면 미룰수록 원칙 V 위반 상태가 길어진다.

- [ ] T028 [US2] `backend/src/itb/generator/playwright_gen.py` 의 `_assertion_lines` 에 `VALUE` 분기를 더한다. 긍정 `equals` → `toHaveValue`, 긍정 `contains` → `expect.poll(…).toContain(…)` ([contracts/export-mapping §2](./contracts/export-mapping.md) — 정규식으로 감싸지 않는 이유가 거기 있다)
- [ ] T029 [US2] 같은 파일에 부정 비교를 더한다 — 021 의 `_watch_window` 로 감싼다. `not_equals` → `not.toHaveValue(…, { timeout: 1 })`, `not_contains` → `expect(await loc.inputValue()).not.toContain(…)`. 루프가 관찰 기간을 담당하므로 안쪽에서 또 기다리지 않는다
- [ ] T030 [P] [US2] `backend/tests/unit/test_generator.py` 에 네 비교 방식의 생성 결과 테스트를 더한다 — **[contracts/export-mapping.md](./contracts/export-mapping.md) 의 표와 글자 단위로 대조한다**
- [ ] T031 [P] [US2] `backend/tests/unit/test_export_keeps_assertion.py` 에 입력값 검증이 내보내기에서 보존되는지, 민감 변수가 `process.env.NAME` 으로 나가는지 더한다
- [ ] T032 [US2] **왕복 정합을 한 번 완주한다** (헌법 품질 게이트 2) — 기록 → 저장 → 제품 내 실행 → 내보내기 → 내보낸 테스트 실행. 입력값 검증 네 비교 방식으로 결과가 일치하는지 확인한다

**Checkpoint**: 원칙 V 가 회복됐다. 정의가 제품 밖에서도 같은 검증을 한다

---

## Phase 5: User Story 3 — 잘못 고른 검증이 조용히 지나가지 않는다 (Priority: P3)

**Goal**: 값이 없는 대상은 거절하고, 선택 목록의 함정은 알리고, 입력 칸에 텍스트 검증을
고른 사람에게 올바른 길을 가리킨다.

**Independent Test**: 각 오용 상황을 하나씩 만들어 보고 화면·결과·작성 도구가 그 사실을
말하는지 확인한다.

- [ ] T033 [US3] `backend/src/itb/execution/assertion_builder.py` 에 **대상 성질 판정 함수**를 더한다. 세 갈래는 [data-model §3](./data-model.md) 의 표가 권위다 — 값을 갖는다(받는다) · 체크박스·라디오(거절) · 그 밖(거절). **태그를 읽지 못하면 거절하지 않는다** — 판정 실패를 거절로 바꾸면 정당한 대상이 막힌다
- [ ] T034 [US3] 거절 문구를 쓴다. **무엇을 할 수 없는지만이 아니라 무엇을 대신 할 수 있는지를 담는다** ([contracts/assertion-surface §2](./contracts/assertion-surface.md)) — 체크박스는 「값이 체크 여부와 무관하고 체크 상태 검증은 아직 없다」, 값 없는 태그는 **텍스트 검증을 가리킨다**(이 기능이 고치려는 실수의 반대 방향이다)
- [ ] T035 [US3] T033 을 **두 작성 경로에 연결한다** — `steps.py`(오류 응답)와 `tools.py`(`{"error": …}`). 거절 문구는 모델이 **다음에 무엇을 할지 알 수 있어야** 한다. 「지원하지 않습니다」로 끝나면 같은 도구를 반복 호출한다
- [ ] T036 [US3] 선택 목록 안내를 더한다 (FR-033) — 만들되 「보이는 항목 이름이 아니라 내부 식별자를 비교한다」를 알린다. **경고가 아니라 조언의 문체**로 쓴다 (021 의 `NEGATED_MATCH_NOTE` 와 같은 성격). **T002 실측 결과와 문구가 일치하는지 확인한다**
- [ ] T037 [US3] 입력 칸 대상 텍스트 검증 경고를 더한다 (FR-030) — 「이 대상에서는 언제나 빈 문자열로 관찰됩니다. 칸에 담긴 값을 보려면 입력값 검증을 쓰세요」. **막지 않는다** — 하위 호환(FR-040)과 충돌한다. `select` 는 자식 `option` 의 글자를 텍스트로 가지므로 경고하지 않는다
- [ ] T038 [US3] `backend/src/itb/authoring/tools.py` 의 도구 설명에 **「입력 칸·선택 목록의 값을 볼 때는 `text` 가 아니라 `value`」** 를 더한다 (FR-034). 비밀번호 칸은 민감 변수 참조로만 비교한다는 것도 적는다 — 모델이 거절당하고 헤매지 않도록
- [ ] T039 [US3] `frontend/src/lib/wording.ts` 에 선택 목록 안내 문구를 더하고, `frontend/src/components/AssertionForm.tsx` 가 대상이 선택 목록일 때 그것을 보여 준다. 문구의 소유자는 `wording.ts` 다 (021 FR-023)
- [ ] T040 [P] [US3] `backend/tests/contract/test_value_target_surface.py` 를 만든다 — 세 갈래 판정 · 거절 문구가 대안을 담고 있는지 · **두 경로가 같은 판정을 하는지**(한쪽만 거절하면 실패)
- [ ] T041 [P] [US3] `backend/tests/integration/` 에 오용 시나리오를 더한다 — 체크박스 거절 · 버튼 거절 · 선택 목록은 만들어지고 안내가 붙음 · 입력 칸 텍스트 검증은 경고만 뜨고 Step 은 만들어짐

**Checkpoint**: 세 User Story 가 모두 독립적으로 동작한다

---

## Phase 6: Polish & Cross-Cutting

**Purpose**: 하위 호환 확인과 전량 검증. 여기서 조용한 누락을 잡는다.

- [ ] T042 [P] **파이썬의 `match` 분기가 전부 7종을 덮는지 훑는다.** 프론트는 타입 검사가 잡아 주지만 백엔드는 잡아 주지 않는다 ([data-model §5](./data-model.md)). `AssertionKind` 를 쓰는 모든 파일을 확인한다 — `domain/` · `execution/` · `generator/` · `authoring/` · `api/routes/`
- [ ] T043 [P] **하위 호환 검증** — 023 이전에 저장된 테스트를 파일 변경 없이 열고·실행하고·내보내고·공유한다. 입력 칸 대상 텍스트 검증이 **자동으로 바뀌지 않았는지** 확인한다 (FR-041 — 친절하게 고쳐 주는 것이 여기서는 틀린 동작이다)
- [ ] T044 [P] `backend/tests/unit/test_run_controls_unchanged.py` 계열의 기존 테스트가 그대로 통과하는지 확인한다. **끄거나 약화시키지 않는다** (헌법 품질 게이트 4)
- [ ] T045 **재실행 경로에 LLM 도달 경로가 없음을 확인한다** (헌법 품질 게이트 1, 원칙 II). 이번에 더한 관찰 함수·마스킹·성질 판정 중 실행 경로에 드는 것들이 대상이다
- [ ] T046 백엔드 전량 검증 — `cd backend && uv run pytest` · 린트 · 타입 검사 · `.importlinter` 계약(특히 `sharing-cannot-reach-secrets`)
- [ ] T047 프론트 전량 검증 — `cd frontend && npm run lint && npx tsc --noEmit && npm test`
- [ ] T048 **[quickstart.md](./quickstart.md) §1~§9 를 사람이 손으로 수행하고 결과를 기록한다** — 자동 검증이 덮지 못하는 것(거절 문구가 다음 행동을 알려 주는지, 목록에서 두 종류가 구별되는지, 안내가 눈에 들어오는지)을 본다. **§6 이 가장 중요하다** (비밀번호 값이 정말 어디에도 남지 않는지)

---

## Dependencies & Execution Order

### Phase 의존

```
Phase 1 (Setup)              — 즉시 시작 가능
      ↓
Phase 2 (Foundational)       — 모든 Story 를 막는다. 스키마가 먼저다 (원칙 I)
      ↓
  ┌───┴───┬───────┐
Phase 3  Phase 4  Phase 5    — Phase 2 후 서로 독립. 병행 가능
 (US1)    (US2)    (US3)
  └───┬───┴───────┘
      ↓
Phase 6 (Polish)             — 원하는 Story 가 모두 끝난 뒤
```

**T002(select 실측)는 T036(안내 문구)을 막는다.** Phase 를 건너뛰는 유일한 의존이며,
문구가 사실과 다르면 안 되기 때문이다.

### User Story 의존

- **US1 (P1)**: Phase 2 후 시작. 다른 Story 에 의존하지 않는다 — **이것만으로 MVP**
- **US2 (P2)**: Phase 2 후 시작. US1 과 독립이지만 **미루면 원칙 V 위반 상태가 길어진다**
- **US3 (P3)**: Phase 2 후 시작. US1·US2 와 독립

### Phase 3 내부 순서

```
T011~T012 (실행)  ─┐
T015~T019 (작성)  ─┼→ T023~T027 (보안)   ← 위 두 층이 동작한 뒤에 얹는다
T020~T022 (화면)  ─┘
```

보안을 마지막에 두는 이유는 plan 의 ⑦과 같다 — 섞어 만들면 마스킹 때문에 실패한 것인지
관찰이 틀린 것인지 가릴 수 없다.

### 병행 가능한 것

- T001·T002 (Setup, 서로 무관)
- T007·T010 (Foundational 의 테스트)
- T013·T014 (실행 통합 테스트) · T017·T019 (단위 테스트) · T022 (프론트 테스트)
- T026·T027 (보안 테스트)
- T030·T031 (생성기 테스트)
- T040·T041 (오용 테스트)
- T042·T043·T044 (Polish 의 훑기 작업들)
- **Phase 3·4·5 전체** — 사람이 여럿이면 Story 단위로 나눈다

---

## Parallel Example: User Story 1

```bash
# 실행·작성·화면 세 층을 나눠 진행할 수 있다 (파일이 겹치지 않는다)
Task: "T011~T012 step_executor.py 에 _assert_value"
Task: "T015~T017 assertion_builder.py 의 ELEMENT_KINDS·default_label"
Task: "T020~T021 wording.ts·AssertionForm.tsx"

# 테스트도 함께
Task: "T013 실행 통합 테스트"
Task: "T017 표시 이름 단위 테스트"
Task: "T022 폼 상태 테스트"
```

단, **T018·T024·T035 는 같은 파일(`authoring/tools.py`)을 건드린다.** 병행하지 않는다.

---

## Implementation Strategy

### MVP (User Story 1 만)

1. Phase 1 — 고정 대상과 실측
2. Phase 2 — 종류 추가와 스키마 재생성 (**모든 것을 막는다**)
3. Phase 3 — 입력값 검증 + 비밀번호 방어
4. **멈추고 검증**: quickstart §2·§3·§6 을 손으로 돌린다
5. 여기까지면 원래 깨져 있던 것이 고쳐졌다

### 점진 전달

1. Setup + Foundational → 기반
2. **US1** → 제품 안에서 입력값 검증이 동작한다 (MVP)
3. **US2** → 내보낸 테스트도 같은 판정을 한다 (원칙 V 회복)
4. **US3** → 오용이 조용히 지나가지 않는다
5. Polish → 하위 호환과 전량 검증

**US2 를 오래 미루지 않는다.** Phase 2 가 끝난 순간부터 입력값 검증이 든 정의는 내보낼 수
없는 상태이고, 그것은 헌법 원칙 V 위반이다. 조용히 틀리지 않고 크게 깨지므로 사용자가
데이터를 잃지는 않지만, 기능이 반쪽인 채로 오래 두면 안 된다.

---

## Notes

- `[P]` = 다른 파일, 의존 없음
- 각 작업 또는 논리적 묶음마다 커밋한다
- **체크포인트에서 멈춰 Story 를 독립적으로 검증할 수 있다**
- 조용히 누락되는 자리 넷을 기억한다 ([data-model §5](./data-model.md)) — `default_label` ·
  `assertion_builder` 의 집합 · AI 도구 설명 · 프론트 `KINDS` 배열. 생성기와 프론트 문구
  사전은 알아서 깨지므로 걱정하지 않아도 된다
