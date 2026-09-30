---

description: "027 Step 편집면과 조작 배선을 한 곳으로 — 작업 목록"
---

# Tasks: Step 편집면과 조작 배선을 한 곳으로

**Input**: `specs/027-shared-step-editing/` 의 설계 문서

**Prerequisites**: plan.md · spec.md · research.md · data-model.md · contracts/

**Tests**: **포함한다.** 이 증분의 값 절반이 **검사**에 있다 — 구조를 고치는 것과
고쳐진 채로 두는 것은 다른 일이고(US3), 검사가 없으면 시간이 지나며 다시 갈린다.

**이 증분은 프론트만 바꾼다.** 백엔드 파일을 수정하는 작업이 하나도 없다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일 · 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 User Story 인가 (US1~US4)

## Path Conventions

`frontend/src/` · `frontend/tests/`

---

## Phase 1: Setup — 기준선

**Purpose**: 겉모습이 바뀌지 않아야 하는 증분이다. 무엇이 「그대로」인지 먼저 적는다.

- [X] T001 시작 시점 전량 검증을 돌려 `specs/027-shared-step-editing/baseline.md` 에 적는다 — `cd frontend && npx vitest run` · `npx tsc --noEmit` · `cd backend && bash scripts/test-backend.sh` · `uv run ruff check src/ tests/` · `uv run lint-imports`. **백엔드는 건드리지 않으므로 끝에서 글자 그대로 같아야 한다**
- [X] T002 [P] 회귀 확인 대상 검사 목록을 `baseline.md` 에 적는다 — `CapabilityCoverage` · `CapabilityUI` · `ScreenSweep` · `VisualLanguage` · `ClassExistence` · 006·009·011·016·026 의 화면 검사. 각각 **지금 몇 건 통과인지** 함께 적는다 (quickstart §0 의 표가 근거)
- [X] T003 [P] 지금 어댑터별 `runAction` 이 처리하는 조작 목록을 `baseline.md` 에 적는다 — 이전이 끝났을 때 **하나도 빠지지 않았는지** 대조할 근거다

**Checkpoint**: 「그대로여야 하는 것」이 문서로 남았다.

---

## Phase 2: Foundational — 배선 모듈과 그것을 지키는 검사

**Purpose**: 모든 이전이 이 둘 위에 선다. **검사를 먼저 만든다** — 검사 없이 옮기면
무엇이 빠졌는지 옮기는 도중에 알 수 없다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 조작도 옮기지 않는다.

- [X] T004 `frontend/src/lib/actionWiring.ts` 를 신설한다 — `ScreenCapabilities`(전부 선택적) · `ACTION_WIRING`(조작 → 능력) · `makeRunAction(caps, fallback?)` (data-model §1~§3). **국면을 인자로 받지 않는다** (contracts/wiring-contract §2). 모듈 docstring 에 「하지 않을 것」 목록과 research R7 의 실패 정의를 적는다
- [X] T005 [P] `frontend/tests/ActionWiring.test.ts` 에 모듈 자체의 검사를 쓴다 — ① 능력이 없으면 그 조작이 이어지지 않는다 ② `fallback` 이 있으면 표에 없는 조작이 거기로 간다 ③ **모듈이 국면을 받지 않는다**(시그니처 고정) ④ 같은 조작이 두 능력에 이어지지 않는다
- [X] T006 `makeRunAction` 이 **이어 둔 조작 목록을 돌려준다** — 화면이 `data-wired-actions` 로 내보낼 값이다 (data-model §4). 화면이 손으로 적지 않는 것이 요점이다
- [X] T007 `frontend/tests/ActionWiringCoverage.test.tsx` 에 **표 ↔ 배선 대조** 검사를 쓴다 (FR-014~FR-016) — 각 국면 화면을 **실제로 그려** `data-wired-actions` 를 읽고, 조작표가 그 국면에서 **「해당 없음」(`na`)이 아니라고** 말하는 조작이 전부 들어 있는지 본다. **아직 이전 전이므로 실패한다** — 그 실패 목록이 곧 이전할 일감이다

      > **판정 기준이 `na` 인 것이 요점이다** (analyze A1). 「활성(`enabled`)」으로 잡으면
      > 검사가 절반만 잡는다 — `cond(...)`·`off(...)` 인 조작도 **배선은 있어야 하기**
      > 때문이다. 조건이 풀리거나 사유가 해소되면 눌리고, 그때 아무 일도 일어나지 않으면
      > 그것이 바로 이 기능이 막으려는 결함이다. 「해당 없음」만이 「이을 필요가 없다」다.
- [X] T008 T007 의 실패 문구가 **어느 조작이 어느 화면에서 빠졌는지** 말하는지 확인한다 (FR-015). 「어딘가 잘못됐다」로 끝나면 고친다

**Checkpoint**: 배선 모듈이 있고, 무엇이 안 이어졌는지 검사가 목록으로 말해 준다.

---

## Phase 3: User Story 1 — 조작을 한 곳에 이으면 모든 화면이 받는다 (P1) 🎯 MVP

**Goal**: 13개 중복 조작이 한 자리에서 이어진다.

**Independent Test**: 조작 하나를 새로 더하고 한 곳만 이은 뒤, 조작표가 활성이라고
말하는 모든 화면에서 동작하는지 확인한다.

**이전 순서가 설계다** (research R5). 쉬운 것부터가 아니라 **설계가 시험되는 것을 뒤에**
둔다 — 앞이 쉽게 옮겨진다고 설계가 옳다는 뜻이 아니다.

### 무리 1 — Step 하나에 대한 편집 (가장 단순)

- [X] T009 [US1] `SessionScreen`·`EditView` 가 `step.delete` · `step.moveUp` · `step.moveDown` 을 능력 묶음으로 제공하게 고친다. 두 화면의 `runAction` 에서 해당 `case` 를 지운다
- [X] T010 [US1] 두 화면이 `makeRunAction` 의 결과를 `ActionPalette` 에 넘기게 한다. **호출부의 모양이 바뀌지 않는다** (FR-021)
- [X] T011 [US1] 화면 뿌리에 `data-wired-actions` 를 붙인다 (T006 의 값)
- [X] T012 [US1] 무리 1 검증 — `npx vitest run` · `npx tsc --noEmit`. **기준선과 같아야 한다**. T007 의 실패 목록에서 이 셋이 사라졌는지 확인한다

### 무리 2 — 여러 Step · 삽입 (확인 대화가 낀다)

- [X] T013 [US1] `step.deleteSelected` · `step.deleteAfter` · `step.insertManual` 을 옮긴다. **확인 대화는 화면에 남는다** — 능력은 「지운다」이고 「물어본다」는 화면의 사정이다
- [X] T014 [US1] 무리 2 검증 (T012 와 같은 방식)

### 무리 3 — 화면을 옮기는 일 (**FR-004 의 시험대**)

- [X] T015 [US1] `run.all` · `run.from` · `result.show` · `nav.back` 을 옮긴다. **네 조작이 화면마다 다른 일을 한다** — 능력의 구현이 다르고 배선은 같다는 것이 여기서 증명된다
- [X] T016 [US1] 무리 3 검증. **여기서 설계가 무너지면 되돌린다** (research R7 의 실패 정의)

### 무리 4 — 선행 확인이 다른 것 (**FR-005 의 시험대**)

- [X] T017 [US1] `save` · `step.recordStart` · `step.addNaturalLanguage` 를 옮긴다. `EditView` 의 「먼저 저장하고 열기」가 **능력 구현 안에** 남아야 한다 — 배선이 그것을 알면 안 된다
- [X] T018 [US1] 무리 4 검증
- [X] T019 [US1] `ResultView` 의 조작 8종도 같은 방식으로 잇는다 — 세 번째 화면이 같은 모양을 쓰는지가 이 설계의 마지막 확인이다
- [X] T020 [US1] 어댑터의 `runAction` 에 남은 `case` 가 **그 화면 고유의 것뿐인지** 확인한다 (T003 의 목록과 대조)
- [X] T020a [US1] **화면이 자기가 아는 사실로 조작을 더 좁히는 통로가 살아 있는지** 확인하고 검사한다 (FR-007 · analyze D1) — `EditView` 의 `narrowByAiEntry`·`narrowByDeleteSelection`·`narrowByPick` 이 그것이다. 배선 통합은 **조작이 눌렸을 때 무엇을 하는가**를 옮기는 일이고, **언제 누를 수 있는가**는 건드리지 않는다. 이 통로가 끊기면 「고칠 Step 을 고르세요」 같은 잠금 사유가 사라진다 — 026 이 만든 것이 조용히 없어지는 자리다

**Checkpoint**: 13개 조작이 한 자리에서 이어진다. 편집면은 아직 두 벌이다.

---

## Phase 4: User Story 2 — 어느 화면에서 고치든 같은 편집면 (P1)

**Goal**: Step 편집면이 하나가 되고, `Workbench` 의 우회 props 둘이 없어진다.

**Independent Test**: 같은 Step 을 두 화면에서 고치고, 고칠 수 있는 항목과 결과가 같은지
확인한다.

### Tests for User Story 2

- [ ] T021 [P] [US2] `frontend/tests/StepEditFieldsShared.test.tsx` 에 **두 화면의 편집면이 같은지** 보는 검사를 쓴다 (FR-009 · SC-004) — 같은 Step 을 편집 화면과 세션 화면에서 각각 열고 **고칠 수 있는 항목 집합이 같은지** 본다. 목록을 적어 두지 않고 **렌더 결과에서 읽는다**
- [ ] T022 [P] [US2] Step 종류별로 그리는 칸이 다른지 검사한다 (FR-010) — 클릭 Step 에 입력값 칸이 없고 채우기 Step 에 있다. **두 화면 모두** 그렇다
- [ ] T023 [P] [US2] 민감 참조를 담은 값 칸이 **두 화면 모두** 읽기 전용인지 검사한다

### Implementation for User Story 2

- [X] T024 [US2] `frontend/src/components/workbench/StepDetail.tsx` 의 `ownFields` 갈래를 걷어내고 그 자리에서 `StepEditFields` 를 쓴다 (research R3). **정본은 작은 쪽이다**
- [X] T025 [US2] `frontend/src/components/workbench/Workbench.tsx` 에서 `stepDetailOwnFields` · `stepDetailExtra` 를 제거한다. **추상이 줄어드는 자리다** (R7)
- [X] T026 [US2] `EditView` 가 `stepDetailOwnFields={false}` · `stepDetailExtra` 로 하던 우회를 걷어낸다 — 이제 공용 편집면이 그 일을 한다
- [X] T027 [US2] `step.update` 를 능력 묶음으로 옮긴다 — 지금은 세션 `runAction` 에만 있다
- [ ] T028 [US2] 같은 값을 두 화면에서 입력했을 때 **저장 결과가 구별되지 않는지** 검사한다 (FR-012 · SC-005)

**Checkpoint**: 편집면이 하나다. 「어느 편집면을 쓸까」라는 선택지가 없어졌다.

---

## Phase 5: User Story 3 — 비대칭이 생기면 검사가 먼저 말한다 (P1)

**Goal**: T007 이 통과 상태가 되고, **일부러 깨면 실패하는지** 확인한다.

**Independent Test**: 조작 하나의 배선을 한 화면에서만 빼고, 검사가 실패하는지 확인한다.

- [ ] T029 [US3] T007(표 ↔ 배선 대조)이 **통과**하는지 확인한다. 아직 실패가 남아 있으면 그것이 이전이 덜 끝난 자리다
- [ ] T030 [US3] **검사가 실제로 잡는지 시험한다** (SC-003 · quickstart §1) — 조작 하나의 능력을 한 화면에서 일부러 빼고 `npx vitest run` 을 돌려 **실패하는지** 본다. 실패 문구가 어느 조작·어느 화면인지 말하는지 확인한 뒤 되돌린다. **이 시험을 건너뛰면 검사가 거짓으로 통과하고 있어도 모른다**
- [ ] T031 [US3] 편집면 항목이 한쪽에만 더해졌을 때도 검사가 잡는지 같은 방식으로 시험한다 (FR-017)
- [ ] T032 [US3] 두 검사의 실패 문구를 다듬는다 — 읽고 **무엇을 하면 되는지** 알 수 있어야 한다

**Checkpoint**: 다음 사람이 한쪽에만 붙이면 검사가 먼저 말한다. **026 재발이 막혔다.**

---

## Phase 6: User Story 4 — 국면이 다른 것은 그대로 다르다 (P2)

**Goal**: 통합이 국면 고유의 것을 지우지 않았음을 확인한다.

**Independent Test**: 통합 전후로 각 화면의 고유 요소가 그대로인지 확인한다.

- [ ] T033 [P] [US4] 결과 화면의 스크린샷·산출물 선택이 그대로인지 검사한다 (FR-018)
- [ ] T034 [P] [US4] 편집 화면의 외부 변경 충돌 해소가 그대로인지 검사한다
- [ ] T035 [P] [US4] AI 작성 세션의 곁줄·작업 계획·재녹화 띠·Step 수정 띠가 그대로인지 검사한다
- [ ] T036 [US4] 조작표(`capabilities.ts`)가 **한 글자도 바뀌지 않았는지** 확인한다 — `git diff` 가 빈 결과여야 한다 (FR-020)
- [ ] T037 [US4] `Workbench` 의 3층 구조가 바뀌지 않았는지 확인한다 (FR-019) — 제거한 props 둘 외에 변경이 없어야 한다

**Checkpoint**: 네 User Story 가 전부 동작한다.

---

## Phase 7: Polish & 회귀

- [ ] T038 `frontend/src/lib/capabilities.ts` 가 여전히 **유일한 권한 판정**인지 확인한다 (FR-006) — `actionWiring.ts` 에 국면·권한 관련 낱말이 없어야 한다
- [ ] T038a **백엔드가 한 파일도 바뀌지 않았는지** 확인한다 (FR-023 · 헌법 원칙 I · analyze D2) — `git diff --stat backend/` 가 빈 결과여야 한다. 사람·AI 편집이 같은 순수 함수를 지나는 성질은 백엔드가 그대로이면 자동으로 유지되며, **자명한 것을 확인하지 않아 깨지는 것**이 이 저장소가 겪은 패턴이다
- [ ] T038b [P] 읽기 전용 편집면이 실제로 동작하는지 검사한다 (FR-011 · analyze D3) — `editable={false}` 일 때 모든 입력칸이 잠긴다. 지금 쓰는 곳이 없더라도 **능력이 살아 있어야** 나중에 결과 화면이 쓸 수 있다
- [ ] T038c [P] 「한 조작에 한 자리」와 「감춰진 조작 0건」이 유지되는지 확인한다 (FR-024·FR-025 · analyze D4) — `LabelUniqueness`·`CapabilityUI` 가 잡지만, 이 증분이 조작의 **자리**를 옮기므로 명시적으로 돌려 본다
- [ ] T039 [P] `makeRunAction` 의 `fallback` 이 **비어 있는지** 확인한다 (contracts §5) — 이행이 끝났으면 쓰이지 않아야 한다
- [ ] T040 [P] 새 CSS 클래스를 만들지 않았는지 확인한다 — 이 증분은 겉모습을 바꾸지 않는다
- [ ] T041 전량 검증을 돌리고 `baseline.md` 의 시작 시점과 비교해 적는다. **백엔드는 글자 그대로 같아야 한다**
- [ ] T042 `quickstart.md` §2~§4 를 손으로 확인한다 — 세 화면이 그대로인가 · 편집면이 하나인가 · 새 조작이 한 곳만 고쳐도 붙는가
- [ ] T043 [P] 어댑터 세 파일의 줄 수를 재어 `baseline.md` 에 적는다 — 줄어야 한다. 늘었으면 research R7 의 실패 정의에 해당하는지 판단한다

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 의존 없음
- **Phase 2 (Foundational)**: Phase 1 후. **모든 이전을 막는다** — 검사가 없으면 무엇이 빠졌는지 옮기는 도중에 알 수 없다
- **Phase 3 (US1)**: Phase 2 후. 무리 1 → 2 → 3 → 4 **순서대로** (research R5)
- **Phase 4 (US2)**: Phase 3 후 — 편집면 통합이 `step.update` 이전을 포함하므로
- **Phase 5 (US3)**: Phase 3·4 후 — 이전이 끝나야 검사가 통과 상태가 된다
- **Phase 6 (US4)**: Phase 4 후. Phase 5 와 병렬 가능
- **Phase 7 (Polish)**: 전부 후

### User Story Dependencies

- **US1 (P1)**: Foundational 후. 이 증분의 뼈대
- **US2 (P1)**: US1 에 의존 — 편집면 통합이 배선을 쓴다
- **US3 (P1)**: US1·US2 에 의존 — 이전이 끝나야 「통과」가 뜻을 갖는다
- **US4 (P2)**: US2 후. US3 와 독립

### Parallel Opportunities

- T002 · T003 (기준선 둘)
- T021 · T022 · T023 (US2 검사 셋)
- T033 · T034 · T035 (US4 검사 셋)
- T039 · T040 · T043 (Polish 확인들)

**무리 이전(T009~T019)은 병렬로 하지 않는다.** 같은 파일을 만지고, 무엇보다 **한 무리씩
검증하는 것이 이 계획의 안전장치**다.

---

## Implementation Strategy

### 멈출 수 있는 지점

이 증분은 회귀 위험이 크므로 **무리마다 멈출 수 있게** 짰다.

1. Phase 2 까지 → 배선 모듈만 있고 아무것도 옮기지 않은 상태. 사용자에게 변화 없음
2. 무리 1 후 → 조작 3개만 옮긴 상태. **두 경로가 공존한다** (FR-022)
3. 무리 3 후 → **여기가 판단 지점이다.** FR-004 가 실제로 성립하는지 보인다
4. Phase 4 후 → 편집면이 하나. 이 증분의 값 대부분이 나온 상태
5. Phase 5 후 → 재발이 막힌 상태

### 주의

- **T030 을 건너뛰지 않는다.** 검사가 실제로 잡는지 시험하지 않으면, 거짓으로 통과하는 검사를 믿게 된다.
- **무리 3 에서 멈출 각오를 한다.** 거기서 설계가 무너지면 되돌리는 것이 맞다 (R7).
- **「이왕 만지는 김에」를 하지 않는다.** 겉모습이 바뀌면 SC-007 을 잴 수 없다.
- **백엔드를 건드리지 않는다.** 건드렸다면 범위를 벗어난 것이다.

---

## Notes

- `[P]` = 다른 파일 · 의존 없음
- 무리마다 커밋한다 — 되돌릴 지점이 그것이다
- 검증은 저장소 표준 명령으로 한다
- 기존 실패 8건(AS-009 계열 4 · ruff 2 · ScreenSweep 2)을 새 실패로 세지 않는다
