---
description: "Task list for 009 — Step 을 원하는 자리에 넣고, 행에서 옮기고 지운다"
---

# Tasks: Step 을 원하는 자리에 넣고, 행에서 옮기고 지운다

**Input**: `specs/009-step-editing-flow/` 의 설계 문서

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Tests**: **선택이 아니다.** 헌법 품질 게이트 3(테스트 동반)과 2(왕복 무결성)가 요구하며,
SC-508(실행 중 활성 0건)·SC-509(기존 경로 회귀 0건)·SC-510(왕복 무결성)은 검사로만 판정된다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (서로 다른 파일, 선행 의존 없음)
- **[Story]**: US1~US3
- 모든 작업에 정확한 파일 경로를 적었다

## 이 목록의 세 가지 규칙

1. **표를 먼저 고친다.** UC-000 이 정한 순서다. 화면을 먼저 고치면 표와 코드가 갈리고,
   갈린 표는 「눌러도 아무 일이 없는 칸」을 만든다. Phase 2 가 끝나기 전에는 어떤 화면도
   손대지 않는다.
2. **정본은 한 방향으로만 흐른다.** `dc.html 의 <style>`(18장 동일) → `extract_canon.py`
   → `tokens.css`. `tokens.css` 를 먼저 고치면 다음 추출에서 되돌아간다.
3. **검증 절차는 [quickstart.md](./quickstart.md) 하나다.** 작업마다 절차를 복사하지 않고
   해당 절을 가리킨다. 작업에는 **그 작업에만 해당하는 것**만 적는다.

## 기준선 (측정 대상 — T001 이 채운다)

| 지표 | 현재 | 근거 |
|---|---|---|
| 조작 수 | 34 | `frontend/src/lib/actions.ts` |
| 표 칸 수 | 272 (8 × 34) | `frontend/tests/CapabilityCoverage.test.ts` |
| `insertStep` 호출처 | **0** | 관찰 M-03 |
| `rowActions` 전달 화면 | **0** | 관찰 M-08 |
| Step 을 3칸 내리는 조작 수 (편집 화면) | **6** | 관찰 M-05 · SC-503 |
| Step 삭제 시 목록↔팔레트 왕복 | **1건** (횟수는 2회 — `baseline.md` §2-2) | 관찰 M-07 · SC-504 |
| 순서 변경 시 화면의 Step 목록 수 (일시정지) | **2** | 관찰 M-06 · SC-505 |
| 요소 지목 없이 Step 을 넣는 방법 | **없음** | 관찰 M-02 · SC-501 |
| Step 삭제 확인 절차 | **없음** | 확인 상태를 가진 화면은 `TestList.tsx` 뿐 · FR-302 |
| 경고 문장이 번호를 박는가 | **박는다** | `step_edits.already_executed_warning` · FR-311 |

---

## Phase 1: Setup — 판정 기준을 고정한다

**Purpose**: SC-501~SC-505 가 "몇 회에서 몇 회로 줄었는가"를 주장하므로, 줄기 전의 값을
실측으로 남긴다. 기준선이 틀리면 이후 판정이 전부 틀린다.

- [X] T001 위 기준선 표의 8개 지표를 실측해 `specs/009-step-editing-flow/baseline.md` 에 남긴다. 조작 횟수는 **실제로 눌러 보고** 센다 (편집 화면에서 5번 Step 을 8번 자리로 내리기 · Step 하나 지우기). 표에 적힌 값과 다르면 그 차이를 먼저 조사한다
- [X] T002 [P] 회귀 기준선을 남긴다 — `cd backend && uv run pytest -m "not browser and not timing" -q` 와 `cd frontend && npm test -- --run` 의 통과 건수를 `baseline.md` 에 적는다. 이후 모든 단계에서 이 수가 줄면 회귀다

**Checkpoint**: 무엇이 몇 회였는지가 파일에 남았다.

---

## Phase 2: Foundational — 표와 시각 언어 정본 (US1~US3 전체를 막는 선행 작업)

**⚠️ 이 단계가 끝나기 전에는 어떤 화면도 옮길 수 없다.**

새 조작을 화면에 먼저 붙이면 표가 그 조작을 모르는 상태가 생기고, 표를 모르는 조작은
화면이 스스로 `disabled` 를 판정하게 만든다 — 005 U-06 이 그 형태였다.

### 조작 표 (FR-305 · SC-506)

- [X] T003 `frontend/src/lib/actions.ts` 의 `ACTION_IDS` 를 34 → 36 으로 바꾼다. `step.insertManual` · `step.moveDown` 을 추가하고 `step.reorder` 를 `step.moveUp` 으로 **개칭**한다. 개칭이므로 컴파일러가 남은 참조 21곳을 전수로 요구한다 ([contracts/step-editing.md](./contracts/step-editing.md) §1)
- [X] T004 `frontend/src/lib/wording.ts` 의 `ACTION_LABEL` 에 라벨을 넣는다 — `step.insertManual`「직접 입력으로 Step 추가」· `step.moveDown`「아래로 옮기기」· `step.moveUp`「위로 옮기기」. `browser.openAt` 라벨을 「브라우저 열어 이 Step **앞에서** 멈추기」로 고친다. **새 `DISABLED_REASON` 키를 만들지 않는다** — 기존 `NOT_STARTED_YET`·`NEEDS_PAUSE`·`RUNNING_NO_EDIT`·`RESULT_NO_EDIT`·`C7` 로 충분하다 (계약 §2)
- [X] T005 `frontend/src/lib/capabilities.ts` 의 `PHASE_TABLE` 을 채운다 — **신규 2개(`step.insertManual`·`step.moveDown`)의 16칸을 새로 쓰고, 개칭된 `step.moveUp` 의 8칸은 `step.reorder` 의 값을 그대로 이관한다**. 값은 계약 §2 의 표가 정본이다. 각 셀에 그 국면을 그렇게 정한 이유를 주석으로 적는다 — 특히 **EDT 열의 `step.insertManual` 이 `NEEDS_BROWSER` 가 아니라 `C7` 인 근거**(FR-307)를 적는다
- [X] T006 `frontend/src/lib/capabilities.ts` 의 런타임 덮어쓰기 목록에 조작 id 를 더한다 — `O2`·`O3`·`O6` 에 `step.insertManual`, `O4`·`O6` 에 `step.moveUp`·`step.moveDown`. **`step.insertManual` 을 `O4` 에 넣지 않는다** (Step 이 0개일 때야말로 넣을 수 있어야 한다). 그 판단을 주석으로 남긴다 (계약 §2-2)
- [X] T007 `frontend/tests/CapabilityCoverage.test.ts` 를 36 조작 기준으로 갱신한다 — 조작 수 단언 `34` → `36`, 커버리지 8 × 36 = **288칸**. 개칭된 `step.reorder` 참조를 `step.moveUp` 으로 고친다. 해소 방법이 36개 목록 안을 가리키는지 보는 단언은 그대로 둔다
- [X] T008 남은 개칭 참조를 정리한다 — `frontend/src/components/workbench/ActionPalette.tsx` · `frontend/src/pages/SessionScreen.tsx` · `frontend/src/pages/EditView.tsx` · `frontend/tests/RunnerReview.test.tsx`. **이 단계에서는 동작을 바꾸지 않는다** — 이름만 바꾼다. 동작 변경은 Phase 5 가 한다
- [X] T009 `frontend/` 에서 `npm run typecheck && npm test -- --run` — T002 의 건수가 줄지 않았고 새 검사가 통과하는지 확인한다. 이 시점에 화면 동작은 하나도 바뀌지 않았으므로 기존 검사는 그대로 통과해야 한다

### 시각 언어 정본 (FR-304 · FR-313)

- [X] T010 `docs/design/008-visual-language/*.dc.html` **18장 전부**의 `<style>` 블록에서 `.srow` 격자를 `26px 1fr 58px 20px` → `26px 1fr 58px 20px auto` 로 고치고 `.srow-ops`(행 조작 묶음, 간격 4px)를 정의한다. **18장이 글자 하나까지 같아야 한다** — 하나라도 다르면 `extract_canon.py` 가 멈춘다 (계약 §6 의 1번)
- [X] T011 `python3 scripts/extract_canon.py --check` 로 18장 동일성을 확인한 뒤 `python3 scripts/extract_canon.py` 결과로 `frontend/src/theme/tokens.css` 를 갱신한다. **손으로 고치지 않는다** (계약 §6 의 3번)
- [X] T012 `cd frontend && npm test -- --run` — L1 대조(`CanonMatchesDesign.test.ts`)와 L2 가드(`VisualLanguage.test.tsx`)가 통과하는지 확인한다. 격자만 바뀌었으므로 값 대조는 영향을 받지 않아야 한다

**Checkpoint**: 표가 288칸을 갖고, 정본 격자에 조작 칸이 생겼다. 화면 작업을 시작할 수 있다.

---

## Phase 3: User Story 1 — 브라우저 없이 Step 을 원하는 자리에 넣는다 (Priority: P1) 🎯 MVP

**Goal**: 요소 지목을 요구하지 않는 Step 종류 넷은 브라우저 없이 정의만으로 원하는 자리에
들어간다. 요구하는 종류는 감춰지지 않고 이유와 갈 길이 그 자리에 남는다.

**Independent Test**: 저장된 테스트를 편집 화면에서 열어 **브라우저를 열지 않은 채** 주소
이동 Step 을 3번과 4번 사이에 넣고 저장한다. 다시 열었을 때 그 자리에 있으면 이 이야기는
단독으로 가치를 낸다 — US2·US3 이 없어도 「그냥 추가」는 된다.

**검증 절차**: [quickstart.md](./quickstart.md) 「US1」 절

### 정본 모델 — 손으로 만들 수 있는 종류 (FR-286)

- [X] T013 [US1] `backend/src/itb/domain/manual_step.py` 를 만든다 — `InsertableKind`(`navigate`·`close_tab`·`assert_url`·`assert_text`) · `ManualStepSpec` 판별 유니온 · 순수 함수 `build_step(spec, step_id) -> Step`. 필드와 검증 규칙은 [data-model.md](./data-model.md) §1·§2 가 정본이다. **`target` 필드를 두지 않는다** — 요청 모델에 그 종류가 없는 것이 원칙 IV 를 타입으로 지키는 방법이다. 라벨 파생 규칙(§2)과 200자 절단을 포함한다
- [X] T014 [P] [US1] `backend/tests/unit/test_manual_step.py` — 네 종류가 각각 올바른 도메인 Step 을 만드는지, 라벨이 파생되는지, `label` 을 주면 그것을 쓰는지, `assert_url` 에 `target` 을 실으면 **모델 단계에서** 거절되는지, 긴 값이 200자로 잘리는지
- [X] T015 [US1] `backend/src/itb/schema/export.py` 의 `MODELS` 에 `"manual-step": TypeAdapter(ManualStepSpec)` 를 더하고 `uv run python -m itb.schema.export` 로 `backend/schema/manual-step.schema.json` 을 생성한다. 이어서 `cd frontend && npm run gen:types` 로 `frontend/src/types/generated/manual-step.d.ts` 를 만들고 `frontend/src/types/generated/README.md` 의 파일 목록에 추가한다
- [X] T016 [US1] `.github/workflows/ci.yml` 의 스키마 드리프트 비교 경로에 `backend/schema/manual-step.schema.json` 을 추가한다. 지금은 `step-dsl.schema.json` 만 비교하므로 새 스키마의 드리프트가 잡히지 않는다
- [X] T017 [US1] `cd backend && uv run lint-imports` — `domain-is-pure` 가 통과하는지 확인한다. 실패하면 `manual_step.py` 가 domain 밖을 임포트한 것이며 [research.md](./research.md) R1 의 결정이 깨진 것이다

### 세션 없는 편집에 삽입 연산 (FR-285·FR-288·FR-289·FR-312)

- [X] T018 [US1] `backend/src/itb/api/routes/tests.py` 에 `InsertStepOp`(`op`·`at`·`spec`)를 더하고 `EditOp` 유니온에 넣는다. `_apply_edits` 에 분기를 추가해 `build_step(spec, allocate_step_id(steps))` 로 만든 Step 을 `itb.execution.step_edits.insert_step(steps, 0, step, op.at)` 로 넣는다. **`step_edits` 를 고치지 않는다** — 그 모듈이 연산을 갖는다는 규칙은 그대로다 ([data-model.md](./data-model.md) §3)
- [X] T019 [US1] `backend/src/itb/api/routes/tests.py` 에 삽입 경고를 더한다 (FR-312 · 막지 않는다) — `close_tab` 의 `tab` 이 현재 정의에서 열리지 않는 번호일 때, `navigate` 를 목록 중간에 넣었을 때(기존 `_reorder_warning` 문장 재사용). 문장은 **한 곳에서만** 만든다
- [X] T020 [P] [US1] `backend/tests/contract/test_definition_edit_api.py` 에 삽입 계약을 더한다 — 네 종류가 각각 지정 위치에 들어가는지, `at` 범위 초과가 `DEFINITION_INVALID` 로 거절되는지, 요소를 요구하는 `kind` 가 거절되는지, **거절 응답 본문에 넘어온 값이 없는지**(003 EC-005 — 판별 유니온 거절은 전역 `RequestValidationError` 핸들러를 타고 `itb/api/errors.py` 의 `_reason` 이 닫힌 문구 집합만 쓴다. 그 경로를 실제로 타는지까지 확인한다), `revision` 없이 저장이 거절되는지, 삽입과 순서 변경이 한 묶음에서 순서대로 적용되는지, 하나가 실패하면 파일이 쓰이지 않는지(전부 또는 전무)

### 일시정지 세션에 직접 입력 삽입 (FR-290)

- [X] T021 [US1] `backend/src/itb/api/routes/steps.py` 에 `POST /{session_id}/steps:manual` 을 더한다 — `require_paused` 를 지나고, `at` 을 생략하면 일시정지 위치, 응답은 기존 `StepsResponse`, 이벤트는 기존 `step_added` 를 그대로 발행한다. **브라우저에 아무 명령도 보내지 않는다** ([data-model.md](./data-model.md) §4). 기존 `POST /{session_id}/steps` 는 **건드리지 않는다** ([research.md](./research.md) R2)
- [X] T022 [P] [US1] `backend/tests/contract/test_step_edit_api.py` 에 새 입구의 계약을 더한다 — 일시정지가 아니면 거절되는지(FR-306), `at` 생략 시 일시정지 위치에 들어가는지, 실행 위치가 밀리지 않아 방금 넣은 Step 이 다음에 실행되는지, 기존 입구의 거절 규칙이 **그대로 통과하는지**(회귀)
- [X] T023 [US1] `backend/tests/integration/test_manual_insert_roundtrip.py` — 왕복 무결성 (SC-510 · 헌법 품질 게이트 2). 삽입 → 저장 → `GET /definition` 재확인 → `replay` 실행으로 그 Step 이 **실제로 수행됐음**까지 본다 ([research.md](./research.md) R9)

### 화면 — 편집 국면 (FR-287·FR-289·FR-310)

- [X] T024 [US1] `frontend/src/api/client.ts` 에 래퍼를 더한다 — 정의 편집의 `insert` 연산 타입과 `insertStepManual(sessionId, spec, at)`. 종류와 필드 타입은 `types/generated/manual-step.d.ts` 에서 가져온다. **프론트에 종류 목록을 상수로 두지 않는다**
- [X] T025 [US1] `frontend/src/pages/EditView.tsx` 에 「이 앞에 추가」 자리를 만든다 — 종류를 고르고 값을 입력해 `insert` 연산을 편집 묶음에 넣는다. 위치는 **미리보기 목록 기준으로 저장 직전에 확정한다**([research.md](./research.md) R7). 요소를 요구하는 종류는 같은 자리에 비활성으로 두고 이유와 `browser.openAt` 으로 가는 길을 붙인다 (FR-287)
- [X] T026 [US1] `frontend/src/pages/EditView.tsx` 에서 저장 전 삽입 관리 규칙을 구현한다 — 삽입한 Step 을 저장 전에 지우면 `insert` 연산 자체를 묶음에서 뺀다(두 건으로 남기지 않는다 · FR-289). 되돌리기가 삽입도 되돌린다. 저장할 변경 수가 사용자가 인지한 것과 같다
- [X] T027 [US1] `frontend/src/components/workbench/StepList.tsx` 에 「미저장」 칩을 더한다 (FR-310) — 저장 전 삽입 Step 의 행에만 붙는다. 정본 `.chip` 을 쓰고 **새 색을 만들지 않는다** (계약 §3-4)
- [X] T028 [US1] `frontend/src/pages/SessionScreen.tsx` 에 일시정지 중 직접 입력 삽입을 붙인다 — 같은 「이 앞에 추가」 자리를 쓰고 `insertStepManual` 을 부른다. 기존 추가 경로 셋은 **그대로 둔다** (FR-309)
- [X] T029 [P] [US1] `frontend/tests/StepInsert.test.tsx` — 브라우저를 열지 않은 편집 화면에서 네 종류를 넣을 수 있는지, 요소를 요구하는 종류가 **자리에 있고** 비활성이며 해소 경로를 가리키는지(감춰지면 실패), 저장 전 삽입에 「미저장」 칩이 붙는지, 삽입 후 지우면 변경 수가 0으로 돌아가는지, 실행 중에는 비활성인지(SC-508)
- [X] T030 [US1] 삽입이 **이미 쌓인 경고 문장**을 어긋나게 하지 않는지 고친다 (FR-311) — `backend/src/itb/execution/step_edits.py` 의 `already_executed_warning(index)` 는 「step 05 는 이미 실행된 Step입니다」처럼 **번호를 문장에 박아** 세션의 `edit_warnings` 에 쌓는다. 그 뒤 앞쪽에 삽입이 일어나면 저장된 문장이 다른 Step 을 가리킨다. 문장을 Step id 기준으로 다시 만들거나, 삽입으로 위치가 밀린 경고를 무효화한다. **번호는 자리이고 정체성이 아니다**
- [X] T031 [P] [US1] `backend/tests/unit/test_step_edits.py` 에 T030 의 검사를 더한다 — 경고가 쌓인 뒤 그 앞에 삽입하면 경고가 가리키는 Step 이 바뀌지 않는지(또는 무효화되는지). 현재 동작을 먼저 실측해 기록한 뒤 고친다
- [X] T032 [US1] [quickstart.md](./quickstart.md) 「US1」 절 전체를 실측하고 조작 횟수를 `baseline.md` 에 대비로 적는다 — SC-501 은 **3회 이내**를 요구한다

**Checkpoint**: 브라우저 없이 Step 이 들어간다. US2·US3 이 없어도 사용자가 처음 물은
「그냥 추가하는 방법」이 생겼다.

---

## Phase 4: User Story 2 — 「이 앞에 추가」 한 번으로 그 앞까지 재생하고 멈춘다 (Priority: P2)

**Goal**: 요소를 지목해야 하는 Step 을 넣기 위해 「저장 → 브라우저 열기 → 목표 앞까지
재생 → 일시정지 → 추가 도구 열림」에 **조작 하나**로 도달한다.

**Independent Test**: 저장된 테스트의 12번 앞에서 브라우저를 여는 조작을 한 번 누른다.
11번까지 재생되고 12번 앞에서 멈춘 뒤 녹화가 켜진 상태로 도착하는지 본다.

**검증 절차**: [quickstart.md](./quickstart.md) 「US2」 절

### 목표 지점을 상태로 노출한다 (FR-293·FR-294)

- [X] T033 [US2] `backend/src/itb/execution/runner.py` 의 `RunnerTask` 에 읽기 전용 `pause_before_index` 접근자를 더한다. **값의 뜻은 「아직 도달하지 않은 목표」**이며 도달 시 `None` 이 되는 기존 동작(`self._pause_before = None`)을 그대로 쓴다. 재생 경로에 새 분기를 만들지 않는다 (원칙 II)
- [X] T034 [US2] `backend/src/itb/api/routes/sessions.py` 의 `SessionView` 에 `pause_before_index: int | None = None` 를 더하고 `view_of(work)` 가 러너에서 읽게 한다. 러너가 없으면 `None` 이다. 필드 주석에 **왜 스냅샷에 싣는지**(005 U-18 — 이벤트 없이도 화면이 복원되게 한다)를 적는다 ([data-model.md](./data-model.md) §5)
- [X] T035 [P] [US2] `backend/tests/integration/test_pause_before_target.py` — 목표 앞에서 멈추는지, 멈추기 전 스냅샷에 목표가 실려 있는지, 도달 후 `None` 이 되는지, **목표 앞의 Step 이 실패하면 목표가 남아 있고 실패한 자리에서 멈추는지**(FR-294), 목표가 0이면 시작 주소만 열고 멈추는지(FR-296)

### 화면 — 한 조작 흐름 (FR-291·FR-292·FR-295·FR-297)

- [X] T036 [US2] `frontend/src/pages/SessionScreen.tsx` 에 진행 표시를 더한다 — 목표가 있고 실행 중이면 「Step nn 앞에서 멈춥니다 — 지금 Step mm」, 목표가 있고 실패한 Step 이 있으면 「Step nn 에 도달하기 전에 Step mm 에서 실패했습니다」. 문구는 `lib/wording.ts` 가 만든다. 그만두는 길은 그 국면의 `run.stop` 이다 (FR-293·FR-294)
- [X] T037 [US2] `frontend/src/App.tsx` 와 `frontend/src/pages/EditView.tsx` 에서 `browser.openAt` 을 한 흐름으로 잇는다 — 저장(미저장이 있으면) → 세션 생성(`pause_before_index`) → 도착 후 기존 `record:start` 호출. 단계별 실패 처리는 계약 §5 의 표를 따른다. **도구 의도는 화면이 기억한다** — 서버 상태에 저장하지 않는다 ([research.md](./research.md) R5)
- [X] T038 [US2] `frontend/src/pages/SessionScreen.tsx` 의 도착 알림을 더한다 — 「지금부터 브라우저 조작이 기록됩니다」. 녹화가 자동으로 켜지는 것을 사용자가 모르는 상태를 만들지 않는다 (R5 의 완화 장치)
- [X] T039 [US2] `frontend/src/pages/ResultView.tsx` 의 「고치기」(`nav.editStep`)가 **그 Step 을 고른 상태로** 편집 화면을 열게 한다 (FR-297). 셀은 바뀌지 않고 해소 방법의 동작이 정확해진다
- [X] T040 [P] [US2] `frontend/tests/InsertViaBrowser.test.tsx` — 조작 한 번으로 저장·세션 생성·녹화 시작이 순서대로 일어나는지, 미저장이 있으면 「먼저 저장합니다」가 **누르기 전에** 보이는지, 진행 문구가 목표와 현재를 함께 말하는지, 도달 전 실패 문구가 「일시정지됨」과 구분되는지, 다른 세션이 잡고 있으면 그 세션으로 가는 길을 보이는지
- [X] T041 [US2] [quickstart.md](./quickstart.md) 「US2」 절 전체를 실측한다 — 2-1(새로 고침 후에도 목표가 남는가) · 2-2(도달 전 실패) · 2-3(목표가 맨 앞)을 포함한다. SC-502 는 **1회**를 요구한다

**Checkpoint**: 요소가 필요한 Step 도 한 조작으로 넣을 수 있다. 다섯 걸음이 없어졌다.

---

## Phase 5: User Story 3 — 행에서 바로 옮기고 지운다 (Priority: P3)

**Goal**: 옮기기·지우기·이 앞에 추가가 그 Step 의 행 안에 있다. 별도 패널과 "먼저 Step 을
고르세요" 왕복이 사라지고 아래로 옮기기가 생긴다.

**Independent Test**: 편집 화면과 일시정지 화면에서 각각 한 Step 을 세 칸 아래로 옮긴다.
누른 횟수가 3회이고 키보드만으로도 같은 일이 되는지 본다.

**검증 절차**: [quickstart.md](./quickstart.md) 「US3」 절

- [X] T042 [US3] `frontend/src/components/workbench/StepList.tsx` 의 `StepRow` 에 칸 5 를 만든다 (FR-298·FR-299·FR-303) — **결과 국면에서는 칸 5 를 그리지 않는다**(계약 §3-3-1 — 행마다 같은 이유의 비활성 조작 4개가 최대 200개가 된다). 그 국면에서는 팔레트가 자리를 갖는다.
  나머지 국면에서는 `.srow-ops` 안에 위로 · 아래로 · 이 앞에 추가 · 지우기 순서로 고정. **hover 로 드러내지 않고 항상 보인다**(계약 §3-2). 기존 칸 넷의 자리와 행 높이 52px 는 바뀌지 않는다 (FR-304)
- [X] T043 [US3] `frontend/src/components/workbench/StepList.tsx` 에서 끝단을 좁힌다 (FR-300) — 첫 행의 위로와 마지막 행의 아래로는 자리를 남기고 비활성이며 「맨 위입니다」·「맨 아래입니다」를 말한다. **해소 방법을 달지 않는다**(해소할 방법이 없는 사실이다). 표가 아니라 화면이 아는 사실로 좁히는 것이며 국면 판정을 하지 않는다 (계약 §2-3)
- [X] T044 [US3] `frontend/src/components/workbench/model.ts` 에 행 조작 모델을 더하고 `Workbench.tsx` 가 `rowActions` 를 화면에서 받아 넘기게 한다. 자리는 이미 열려 있다 (관찰 M-08) — 만드는 것은 넘기는 쪽이다
- [X] T045 [US3] `frontend/src/pages/SessionScreen.tsx` 에서 `ReorderPanel` 을 **제거**하고(FR-301 · SC-505) 행 조작으로 순서 변경·삭제를 연결한다. `reordering` 상태와 그것을 여닫는 조작도 함께 없앤다 — 화면에 Step 목록이 둘 뜨는 경로를 남기지 않는다
- [X] T046 [US3] `frontend/src/pages/EditView.tsx` 에서 팔레트의 「위로 옮기기」 단독 버튼을 없애고 (FR-299 — 세 칸 내리기가 여섯 번이던 것이 세 번이 된다) 행 조작으로 위로·아래로·삭제를 연결한다. `narrowByPick` 의 "먼저 Step 을 고르세요" 왕복이 이동·삭제에서 사라진다 (FR-298 · SC-504)
- [X] T047 [US3] 행의 지우기에 확인 절차를 만든다 (FR-302) — 지금 Step 삭제에는 확인이 **없다**(확인 상태를 가진 화면은 `frontend/src/pages/TestList.tsx` 의 테스트 삭제뿐이다). 그 선례처럼 **행 안에서** 무엇이 지워지는지 보이고 확인을 받는다. 자리는 `frontend/src/components/workbench/StepList.tsx` 가 갖고 **겹침 대화상자를 새로 만들지 않는다** — 행 조작의 결과를 행이 아닌 곳에서 확인하면 대상이 무엇이었는지 다시 확인해야 한다
- [X] T048 [US3] 팔레트의 선언된 자리를 **그대로 둔다** — 계약 §3-3-0 이 구현 중 확인한 사실을 기록했다. 행에 `data-action` 을 달면 「한 조작에 한 자리」(`CapabilityUI.duplicated`)가 깨지고, 팔레트에서 숨기면 「감춰진 조작 0건」이 깨진다. `step.select` 의 선례처럼 **자리는 담는 것이 선언하고 행은 사례**다(`data-row-action`). 이 작업은 팔레트 경로(`selectedIndex` 기준 이동·삭제)가 실제로 동작하는지 확인하는 것으로 바뀐다 — 표가 거짓말하지 않아야 한다. — 기존 `hidden` 목록 방식을 쓴다(「이 국면에서 이 조작은 다른 자리가 갖는다」를 표현하는 기존 방법이다). 표가 요구하는 조작을 화면에서 **없애는 것이 아니다** (계약 §3-3)
- [X] T049 [P] [US3] `docs/design/008-visual-language/*.dc.html` 중 행을 그리는 8장(`Main`·`Paused`·`Run`·`Record`·`Takeover`·`AiWriting`·`Result`·`StepDetail`)의 **마크업**에 칸 5 를 그린다. `Main` 장에는 「이 앞에 추가」 선택 자리와 「미저장」 칩도 함께 넣는다 (계약 §6 의 2번)
- [X] T050 [P] [US3] `docs/design/008-visual-language/conformance/*.md` 의 같은 8장 대조표에 칸 5 행을 추가하고, `docs/design/008-visual-language/replacement-map.md` 의 정본 클래스 목록에 `.srow-ops` 를 더한다 (계약 §6 의 4·5번)
- [X] T051 [P] [US3] `frontend/tests/StepRowActions.test.tsx` — 5번을 8번으로 옮기는 데 「아래로」 3회로 끝나는지(SC-503), 첫 행·마지막 행의 방향이 비활성이고 이유를 말하는지, 삭제가 확인을 거치는지, **화면에 Step 목록이 하나만 있는지**(SC-505), 키보드만으로 모든 행 조작에 도달하고 접근 가능한 이름이 「〈이름〉 위로」·「〈이름〉 아래로」인지(SC-507), 실행 중과 결과 화면에서 비활성인지(SC-508 · FR-308)
- [X] T052 [US3] [quickstart.md](./quickstart.md) 「US3」 절 전체를 실측하고 조작 횟수를 `baseline.md` 대비로 적는다 — SC-503 은 3회, SC-504 는 왕복 0건과 확인 없는 경로 0건을 요구한다(횟수가 아니다)

**Checkpoint**: 세 이야기가 전부 독립으로 동작한다.

---

## Phase 6: Polish — 회귀와 전량 검증

**Purpose**: 이 기능이 **없애지 않았어야 하는 것**을 확인한다. 새 기능이 도는 것보다
기존 경로가 그대로인 것이 더 자주 깨진다.

- [X] T053 [P] `frontend/tests/StepInsert.test.tsx` 에 기존 추가 경로 회귀를 더한다 (SC-509) — 일시정지 상태에서 「직접 조작으로 Step 추가」·「자연어로 Step 추가」·「검증 추가」의 **자리·문구·동작**이 이전과 같은지. 하나라도 달라지면 FR-309 위반이다
- [X] T054 [P] `backend/tests/contract/test_step_edit_api.py` 에 실행 중 잠금 회귀를 더한다 (FR-306) — 세 입구(기존 삽입 · 신규 직접 입력 · 정의 편집) 전부가 실행 중에 거절되는지. `require_paused` 를 지나지 않는 경로가 생기지 않았는지
- [X] T055 [P] `backend/tests/contract/test_step_edit_api.py` 에 세 입구의 결과 일치를 확인하는 검사를 더한다 — 같은 위치에 같은 종류를 넣으면 세 입구가 **같은 목록**을 만든다. 삽입 규칙이 갈리지 않는다는 것이 [research.md](./research.md) R2 의 전제다
- [X] T056 전량 기계 검증을 돌린다 — [quickstart.md](./quickstart.md) 「기계 검증」 절 6개(스키마 드리프트 · `lint-imports` · ruff · pytest · vitest · `extract_canon.py --check` · `count-violations.mjs`). T002 의 통과 건수가 줄지 않았는지 확인한다
- [X] T057 `specs/009-step-editing-flow/baseline.md` 를 완성한다 — SC-501~SC-510 각각의 **이전 값 → 이후 값**을 표로 적는다. 달성하지 못한 항목이 있으면 그것을 감추지 않고 이유와 함께 적는다
- [X] T058 `docs/prd.md` §18 의 성공 지표 중 「테스트 생성 시간」에 이 기능이 준 영향을 한 줄로 적는다 (헌법 품질 게이트 5). 측정값이 없으면 조작 횟수 감소를 근거로 적고 측정이 필요하다고 표시한다

**Checkpoint**: 새로 생긴 것이 돌고, 있던 것이 그대로다.

---

## Dependencies & Execution Order

### Phase 의존

- **Phase 1 (Setup)**: 의존 없음 — 즉시 시작
- **Phase 2 (Foundational)**: Phase 1 이후. **US1~US3 전부를 막는다.** 표와 정본이 먼저다
- **Phase 3 (US1)**: Phase 2 이후
- **Phase 4 (US2)**: Phase 2 이후. US1 의 「이 앞에 추가」 자리를 쓰므로 **T025 에 의존한다**
- **Phase 5 (US3)**: Phase 2 이후. US1·US2 가 만든 자리를 행으로 내리므로 **T025·T037 에 의존한다**
- **Phase 6 (Polish)**: 원하는 이야기가 전부 끝난 뒤

### 이야기 사이 의존

US1 → US2 → US3 **순서가 실제 의존이다.** 이 기능의 세 이야기는 서로 독립적으로
*가치*를 내지만, 뒤의 것이 앞의 것이 만든 자리를 쓴다.

- **US1 (P1)**: Phase 2 이후 단독으로 완결된다. **MVP 는 여기까지다**
- **US2 (P2)**: US1 의 삽입 지점(T025)이 있어야 입구를 붙일 곳이 있다
- **US3 (P3)**: US1 의 삽입 지점과 US2 의 브라우저 경로를 행으로 내린다

### 이야기 안에서

- 모델(T013) → 스키마·타입(T015) → 라우트(T018·T021) → 화면(T024~T028)
- 검사는 그 대상이 생긴 직후에 쓴다. `[P]` 가 붙은 검사는 다른 검사와 병렬 가능하다
- 백엔드와 프론트엔드는 계약(`contracts/step-editing.md` §4)이 정해져 있으므로 병렬 가능

### 병렬 기회

| 묶음 | 함께 돌릴 수 있는 작업 |
|---|---|
| Phase 1 | T001 · T002 |
| Phase 3 검사 | T014 · T020 · T022 · T029 · T031 |
| Phase 4 검사 | T035 · T040 |
| Phase 5 디자인 정본 | T049 · T050 (화면 작업 T042~T048 와도 병렬) |
| Phase 6 회귀 | T053 · T054 · T055 |

**Phase 2 는 병렬로 돌리지 않는다.** T003 의 개칭이 T005~T008 이 손대는 파일 전부를
건드린다 — 동시에 고치면 충돌한다.

---

## Parallel Example: Phase 3 검사

```bash
# 대상이 생긴 직후 함께 돌린다
Task: "backend/tests/unit/test_manual_step.py — 네 종류 조립·라벨·거절"
Task: "backend/tests/contract/test_definition_edit_api.py — 정의 편집 insert 계약"
Task: "backend/tests/contract/test_step_edit_api.py — steps:manual 계약"
Task: "frontend/tests/StepInsert.test.tsx — 편집 화면 삽입과 비활성 표시"
```

---

## Implementation Strategy

### MVP 먼저 (US1 까지)

1. Phase 1 — 기준선 실측
2. Phase 2 — 표 288칸과 정본 격자 (**여기서 멈추면 아무 가치도 없다. 반드시 끝낸다**)
3. Phase 3 — US1
4. **멈추고 검증한다** — quickstart US1 절. SC-501 이 3회 이내인가
5. 여기까지가 사용자가 처음 물은 「그냥 추가하는 방법」이다

### 증분 전달

1. Phase 1 + 2 → 표와 정본이 섰다 (사용자에게 보이는 변화 없음)
2. + US1 → 브라우저 없이 넣는다 → **검증 → 전달**
3. + US2 → 요소가 필요한 Step 도 한 조작으로 → **검증 → 전달**
4. + US3 → 행에서 옮기고 지운다 → **검증 → 전달**
5. + Phase 6 → 회귀 확인

각 단계가 이전을 깨지 않는다. 특히 **기존 추가 경로 셋은 어느 단계에서도 없어지지
않는다** (FR-309).

---

## Notes

- `[P]` = 서로 다른 파일, 선행 의존 없음
- `[Story]` 라벨은 요구사항 추적을 위한 것이다 — 작업이 어느 이야기의 인수 조건을 채우는지
- **표를 고치지 않고 화면에 조작을 붙이지 않는다** (UC-000)
- **`tokens.css` 를 손으로 고치지 않는다** — `extract_canon.py` 의 산출물이다
- 검사가 실패한 채로 커밋할 때는 제목에 `wip:` 를 붙이고 본문에 실패 출력을 적는다
- 각 Checkpoint 에서 멈춰 그 이야기를 단독으로 검증할 수 있다

---

## Phase 7: Convergence

**Purpose**: 코드를 명세·계획·계약에 대조해 남은 갭을 채운다 (converge 1회차).

CRITICAL 0건 · 헌법 위반 0건. HIGH 하나가 이 저장소가 가장 경계하는 결함 유형이다 —
**활성인데 동작하지 않는 조작**이다 (005 U-01).

- [X] T059 `frontend/src/pages/SessionScreen.tsx` 의 `STEP_SCOPED` 에 `step.moveUp`·`step.moveDown` 을 더한다 per 계약 §3-3-0 · FR-234 (contradicts) — **CRITICAL 급 결함 유형이다.** 지금 일시정지 국면에서 Step 을 고르지 않은 채 팔레트의 「위로/아래로 옮기기」를 누르면 `moveStep(-1, …)` 이 조용히 아무 일도 하지 않는다. 계약 §3-3-0 이 「팔레트 경로도 동작해야 한다 — 그것이 곧 표가 거짓말하지 않는다는 뜻이다」라고 적은 그 자리다. `EditView` 는 이미 넷을 좁히고 있으므로 두 화면의 규칙이 갈려 있다. 좁힌 뒤 `frontend/tests/StepRowActions.test.tsx` 에 「고른 Step 이 없으면 팔레트 이동이 비활성이고 이유가 붙는다」를 더한다
- [X] T060 `scripts/design_render.py` 의 `FORMS` 에 `srow-ops` · `op` · `op off` · `op danger` 를 더하고 `backend/.venv/bin/python scripts/design_render.py --compare` 로 `frontend/tests/l1-report.json` 을 재생성한다 per FR-313 (partial) — 새 정본 형태가 **L1 값 대조를 받지 않는다.** 지금은 `dc.html` 시트와 `tokens.css` 가 그 클래스에서 벌어져도 검사가 초록이다. 008 이 고친 V-09(가드가 소비처를 보지 않는다)와 같은 종류의 구멍이다. `page()` 의 마크업 생성이 `.op` 를 자식으로 갖는 형태를 다룰 수 있는지 함께 확인한다
- [X] T061 `docs/design/008-visual-language/Main.dc.html` 에 **「이 앞에 추가」 입력면**과 **「미저장」 칩**을 그린다 per FR-313 · 계약 §6 (missing) — 계약이 그 둘을 `Main` 장에 넣으라고 적었고 행 조작만 들어갔다. 입력면이 새 정본 클래스를 요구하면 18장 시트 전부에 정의하고 `extract_canon.py` → `tokens.css` 순서를 지킨다. 칩은 기존 `.chip.warn` 이므로 새 클래스가 필요 없다. 끝나면 `python3 scripts/extract_canon.py --check` 가 통과해야 한다
- [X] T062 `frontend/src/api/client.ts` 의 `InsertableKind` 를 **생성 타입에서 파생**시킨다 per FR-286 (partial) — 지금 `ManualStepSpec` 이 손으로 쓴 타입이라 백엔드가 다섯째 종류를 더해도 화면은 모르고 아무 검사도 실패하지 않는다. `import type { ManualStep } from "../types/generated/manual-step"` 후 `type InsertableKind = ManualStep["kind"]` 로 두고, 요청 타입의 `kind` 가 그 집합과 같은지 타입 수준으로 못박는다(`never` 단언). `frontend/src/components/workbench/InsertStepForm.tsx` 의 `KINDS` 배열은 망라를 강제하지 않으므로 `frontend/tests/StepInsert.test.tsx` 에 「`KINDS` 가 `INSERTABLE_KIND_LABEL` 의 키 전부를 덮는다」를 더한다

**Checkpoint**: 팔레트 경로가 표대로 동작하고, 새 정본 형태가 L1 대조를 받고, 종류 목록이 한 곳에서만 자란다.

---

## Phase 8: Convergence (2회차)

**Purpose**: 1회차 갭 넷을 닫은 뒤 다시 대조했다. 남은 것은 하나이며 1회차 T059 와 **같은
종류**다 — 활성인데 서버가 거절하는 조작.

- [X] T063 `frontend/src/lib/capabilities.ts` 의 편집 국면 `browser.openAt` 을 `ON` → `cond("C7")` 으로 바꾼다 per US2/AC5 · FR-234 (contradicts) — 다른 세션이 그 테스트를 잡고 있어도 지금은 활성으로 보이고, 누르면 저장 또는 세션 생성이 `409 SESSION_ALREADY_ACTIVE` 로 거절된다. 005 U-01 의 형태이며 US2 인수 시나리오 5 가 「같은 자리에 비활성으로 있고 그 세션으로 가는 방법을 가리킨다」를 요구한다. `C7`(정의가 편집 가능하다)이 맞는 조건이다 — 그 테스트를 잡은 세션이 있으면 두 번째 세션을 열 수 없고, `CONDITION_REMEDY["C7"]` 이 이미 `session.open` 이다. `frontend/tests/InsertViaBrowser.test.tsx` 에 「다른 세션이 잡고 있으면 비활성이고 그 세션으로 가는 길을 가리킨다」를 더한다

**Checkpoint**: 편집 화면의 어떤 조작도 「눌렀는데 서버가 거절」로 끝나지 않는다.
