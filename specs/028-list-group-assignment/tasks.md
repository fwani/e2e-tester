---

description: "028 목록에서 그룹 지정하기 — 작업 목록"
---

# Tasks: 목록에서 그룹 지정하기 — 하이픈 접두어와 끌어 놓기

**Input**: `specs/028-list-group-assignment/` 의 설계 문서

**Prerequisites**: plan.md · spec.md · research.md · data-model.md · contracts/

**Tests**: **포함한다.** 이 증분은 저장된 자산의 식별자를 읽는 방법을 바꾼다 — 잘못되면
「목록에는 보이는데 못 찾는」 상태가 되고, 그것은 사고가 나야 드러난다. 하위 호환은
주장이 아니라 검증으로만 증명된다 (FR-011 · R7).

**두 벌을 만들지 않는다.** 접두어를 읽는 규칙도, 접두어 정규식도 한 곳에서만 산다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 가능 (다른 파일 · 미완료 작업에 의존하지 않음)
- **[Story]**: 어느 User Story 인가 (US1~US4)

## Path Conventions

`backend/src/itb/` · `backend/tests/` · `frontend/src/` · `frontend/tests/`

---

## Phase 1: Setup — 기준선

**Purpose**: 이 저장소에는 028 이전부터 실패하던 검증이 있다. 새로 깨뜨린 것과 원래
깨져 있던 것을 가르지 못하면 판단이 전부 틀린다.

- [X] T001 시작 시점 전량 검증을 돌려 `specs/028-list-group-assignment/baseline.md` 에 적는다 — `cd backend && bash scripts/test-backend.sh` · `uv run ruff check src/ tests/` · `uv run lint-imports` · `uv run python -m itb.schema.export --check` · `cd frontend && npx tsc --noEmit` · `npx vitest run`. **실패 건은 이름까지 적는다**
- [X] T002 [P] 접두어·식별자를 쓰는 기존 검증 목록을 `baseline.md` 에 적는다 — 그룹·이동·엑셀·공유·저장소 관련. 각각 지금 몇 건 통과인지 함께 적는다. 이것이 회귀 판정의 근거다

**Checkpoint**: 「원래 빨간 것」이 문서로 남았다.

---

## Phase 2: Foundational — 규칙과 읽기 함수 (차단 선행)

**Purpose**: 나머지 전부가 여기에 기댄다. 규칙이 한 곳에 있고 읽는 법이 한 곳에 있어야
17개 자리를 옮기는 일이 「두 벌 만들기」가 되지 않는다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 호출 지점을 하나도 건드리지 않는다.

- [X] T003 `backend/tests/` 에 접두어 규칙 검증을 먼저 쓴다 — `IT-PM`·`IT-DM`·`A-B-C` 통과, `IT-`·`-PM`·`IT--PM`·`it-pm`·`IT-001`·13자 이상 거부, `TC` 예약. **옛 규칙 상위집합 검증을 포함한다** (옛 패턴을 만족하는 표본이 새 패턴도 만족한다 — R7-1)
- [X] T004 `backend/src/itb/domain/test_case.py` 의 `GROUP_PREFIX_PATTERN` 을 `^[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*$` 로 바꾸고, 길이 상한 12를 **정규식 밖**에 둔다 (`max_length` — Pydantic 의 Rust regex 는 선읽기를 컴파일하지 못한다, R1)
- [X] T005 `backend/src/itb/domain/test_case.py` 의 `TEST_ID_PATTERN` 을 새 접두어에 맞춰 바꾼다 (`<새 접두어>-\d{3}`)
- [X] T006 `backend/tests/` 에 읽기 함수 검증을 쓴다 — `prefix_of("IT-PM-001") == "IT-PM"`, `number_of("IT-PM-001") == 1`, `test_id_from_filename("IT-PM-001-로그인.yaml") == "IT-PM-001"`. **옛 식별자 동치**(`USER-001`·`TC-014` 에서 옛 `split("-", 1)` 과 같은 값)와 **형식 위반 시 예외**를 함께 본다 (R7-2)
- [X] T007 `backend/src/itb/domain/test_case.py` 에 `prefix_of` · `number_of` · `test_id_from_filename` 을 둔다 — 식별자 패턴이 이미 여기 있으므로 읽는 법도 여기 있어야 갈리지 않는다 (data-model §3)
- [X] T008 `backend/src/itb/domain/test_case.py` 의 `TestGroup.prefix` 필드에 새 패턴과 `max_length` 를 반영한다 (JSON Schema 로 흘러가는 지점이다)

**Checkpoint**: 규칙과 읽는 법이 한 곳에 있다. 아직 아무 호출 지점도 바뀌지 않았고
기존 검증은 전부 통과해야 한다 (새 규칙이 옛 규칙의 상위집합이므로).

---

## Phase 3: User Story 1 — 내가 쓰는 식별 체계로 그룹을 만든다 (P1) 🎯 MVP

**Goal**: `IT-PM`·`IT-DM` 으로 그룹을 만들고, 목록·엑셀·공유 어디에서나 하나의 그룹으로
취급된다.

**Independent Test**: 접두어 `IT-PM` 으로 그룹을 만들고 테스트를 옮긴 뒤, 그룹 건수·엑셀
시트·공유 묶음에서 그 테스트가 `IT-PM` 으로 집계되는지 확인한다.

### 파일 이름 읽기

- [X] T009 [US1] `backend/tests/` 에 파일 이름 파싱 검증을 쓴다 — `IT-PM-001-단계-002-확인.yaml` · `IT-PM-001-ABC-002.yaml` · `IT-PM-DM-003-x.yaml` 에서 식별자를 정확히 끊고, 옛 이름(`USER-001-로그인.yaml` · `TC-999-a.yaml`)도 옛 정규식과 같은 결과를 낸다 (R4 · R7-3)
- [X] T010 [US1] `backend/src/itb/storage/repository.py` 의 `_TEST_FILE_RE` 를 최소 일치 형태로 바꾼다 — 접두어 마디에 3자리 숫자가 올 수 없으므로 왼쪽 첫 「하이픈+3자리」가 언제나 진짜 번호다

### 호출 지점 17곳 (읽기 함수로 교체)

- [X] T011 [US1] `backend/src/itb/storage/repository.py:330` (`used_numbers` 의 접두어 비교)와 `backend/src/itb/storage/test_moves.py:162` (번호)를 읽기 함수로 바꾼다
- [X] T012 [P] [US1] `backend/src/itb/sharing/planner.py:244·249` · `backend/src/itb/sharing/builder.py:45` 를 읽기 함수로 바꾼다
- [X] T013 [P] [US1] `backend/src/itb/portability/importer.py:211·231·372·455·498` 과 `backend/src/itb/portability/exporter.py:85` 를 읽기 함수로 바꾼다
- [X] T014 [P] [US1] `backend/src/itb/api/routes/tests.py:519·531` 과 `backend/src/itb/domain/draft.py:135` 를 읽기 함수로 바꾼다
- [X] T015 [US1] `backend/src/itb/api/routes/groups.py:81` 을 읽기 함수로 바꾸고, **`:177` 의 파일 이름 손 복원**(`split("-", 2)[0] + "-" + [1]`)을 `test_id_from_filename` 으로 바꾼다 — 여기가 하이픈 접두어에서 그룹 해체를 깨뜨리는 자리다
- [X] T016 [US1] `backend/src/itb/api/routes/sharing.py:499` 의 파일 이름 자르기를 `test_id_from_filename` + `prefix_of` 로 바꾼다
- [X] T017 [US1] `grep -rn 'split("-"' backend/src` 로 남은 자리가 없는지 확인한다. 남아 있다면 식별자와 무관한 것인지 근거를 남긴다

### 접두어를 검증하는 자리

- [X] T018 [US1] `backend/src/itb/portability/importer.py` 의 `validate_prefix()` 가 도메인 규칙을 쓰게 하고, 안내 문구를 하이픈을 쓸 수 있다는 사실이 담기도록 고친다 (FR-006)
- [X] T019 [US1] `backend/src/itb/sharing/planner.py:153` 의 **자동 접두어 생성**이 새 규칙을 만족하는 값만 내놓는지 확인하고, 검증을 붙인다 (FR-012)
- [X] T020 [P] [US1] `backend/src/itb/api/routes/groups.py` · `tests.py` · `sessions.py` 의 접두어 제약(`StringConstraints` · `Field(pattern=...)`)에 길이 상한이 함께 붙었는지 확인한다

### 규칙을 화면까지 한 벌로 (헌법 Cross-language schema duty)

- [X] T021 [US1] `cd backend && uv run python -m itb.schema.export` 로 `backend/schema/project.schema.json` 을 갱신한다 (`TestGroup.prefix` 의 `pattern`·`maxLength`)
- [X] T022 [US1] `frontend/scripts/gen-types.mjs` 를 확장해 스키마의 접두어 `pattern`·`maxLength` 를 상수 모듈로 뽑는다 — 생성물이므로 손으로 고치지 않는다는 배너를 유지한다 (data-model §5)
- [X] T023 [US1] `cd frontend && npm run gen:types` 로 생성하고, `frontend/src/components/TestGroupBar.tsx:142` 의 손으로 적은 `/^[A-Z][A-Z0-9]{0,7}$/` 를 생성 상수로 바꾼다
- [X] T024 [US1] `frontend/tests/` 에 검증을 더한다 — 화면이 `IT-PM` 을 받아들이고 `IT-`·`IT-001` 을 거부하며, **정규식이 생성물에서 온다**(파일 안에 정규식 리터럴이 없다)
- [X] T025 [US1] `TestGroupBar` 의 접두어 안내 문구를 고친다 — 「영문 대문자·숫자 1~8자」는 이제 거짓이다. 예시도 `IT-PM` 을 보이게 한다 (FR-006)

### 하위 호환 증명

- [X] T026 [US1] `backend/tests/` 에 028 이전 자산으로 목록·집계·이동·엑셀 왕복이 그대로인지 보는 검증을 더한다 (FR-011 · SC-002). **마이그레이션 단계를 만들지 않는다**
- [X] T027 [US1] 엑셀·공유 왕복 검증에 하이픈 접두어 사례를 더한다 (SC-007)

**Checkpoint**: `IT-PM` 그룹을 만들고 쓸 수 있다. **이 지점에서 사용자가 겪은 문제의
절반이 풀린다** — 목록의 「그룹으로 옮기기」가 이제 나타난다.

---

## Phase 4: User Story 2 — 목록에서 끌어서 그룹에 넣는다 (P1)

**Goal**: 목록 행을 끌어 그룹 표적에 놓으면 옮겨진다. 끌지 않을 때 화면은 그대로다.

**Independent Test**: 그룹이 둘 있는 목록에서 행을 끌어 다른 그룹에 놓고, 식별자와 그룹
건수가 바뀌는지 확인한다.

- [X] T028 [US2] `frontend/tests/` 에 표적 노출 검증을 먼저 쓴다 — **끌기 전에는 표적이 없고**(FR-014 · SC-005 · 013 SC-627), `dragstart` 후 나타나고, `dragend`·`drop` 후 사라진다
- [X] T029 [US2] `frontend/tests/` 에 끌기 대상 규칙 검증을 쓴다 — 체크된 행을 끌면 체크 전부, 체크 밖의 행을 끌면 그 행만이며 체크는 유지된다 (FR-017 · UC-028-03)
- [X] T030 [US2] 끌기 표적 띠 부품을 `frontend/src/components/` 에 만든다 — 그룹 전부(테스트 0개인 것 포함) · 「그룹에서 빼기」 · 「새 그룹으로」. 목록 위에 고정되어 스크롤 중에도 닿는다 (FR-015 · FR-022)
- [X] T031 [US2] `frontend/src/pages/TestList.tsx` 의 행을 끌 수 있게 하고 끌기 상태를 둔다 — 끌고 있는 대상 · 표적 노출 · 올라와 있는 표적 (data-model §6)
- [X] T032 [US2] 놓기를 `tests.move` 에 잇는다. 이미 그 그룹인 것을 같은 그룹에 놓으면 아무 일도 하지 않는다 (FR-020)
- [X] T033 [US2] 올라와 있는 표적을 시각적으로 구분한다 (FR-016). 기존 디자인 토큰을 쓰고 새 색을 만들지 않는다
- [X] T034 [US2] 옮긴 뒤 무엇이 몇 건 어느 그룹으로 갔는지 알리고 목록을 갱신한다. 실패하면 사유를 알린다 — 번호 상한 초과가 대표적이다 (FR-019 · FR-021)
- [X] T035 [P] [US2] `frontend/tests/` 에 취소 경로 검증을 더한다 — 표적 밖에 놓기, `dragend` 로 끝내기, 끌기 중 목록이 갱신되는 경우 (FR-018 · Edge Cases)

**Checkpoint**: 목록 안에서 끌어 그룹을 지정할 수 있다.

---

## Phase 5: User Story 3 — 그룹이 하나도 없어도 길이 있다 (P2)

**Goal**: 그룹이 0개인 프로젝트에서도 목록 화면만으로 그룹을 만들어 넣을 수 있다.

**Independent Test**: 그룹이 0개인 프로젝트에서 테스트를 체크하고, 목록 화면을 떠나지
않고 새 그룹을 만들어 그 그룹에 넣는다.

- [X] T036 [US3] `frontend/tests/` 에 검증을 먼저 쓴다 — 그룹이 0개이고 체크한 것이 있으면 선택 띠에 그룹 지정 수단이 있다. **체크한 것이 없으면 선택 띠는 여전히 그려지지 않는다** (UC-028-04)
- [X] T037 [US3] `frontend/src/pages/TestList.tsx:835` 의 「그룹이 하나도 없으면 그리지 않는다」 조건을 고친다 — 그룹 0개일 때는 「새 그룹 만들어 옮기기」만, 하나 이상일 때는 기존 선택칸에 그 항목을 더한다 (FR-023 · FR-027)
- [X] T038 [US3] 「새 그룹으로」 흐름을 만든다 — 013 의 「+ 그룹」과 **같은 두 칸·같은 규칙·같은 안내**를 쓴다. 새 입력 부품을 만들지 않는다 (UC-028-05)
- [X] T039 [US3] 확인 시 `groups.create` → `tests.move` 순서로 부른다. 취소하면 둘 다 일어나지 않는다 (FR-025 · api-contract §2)
- [X] T040 [US3] 만들기는 됐는데 옮기기가 실패하면 **그룹이 남았다는 사실과 사유를 함께** 알린다. 되돌리지 않는다 — 사용자가 방금 지은 이름을 다시 치게 만들지 않는다 (FR-026 · R6)
- [X] T041 [P] [US3] `frontend/tests/` 에 「새 그룹으로」 표적이 **그룹 0개일 때도** 나타나는지 검증한다 (FR-024)

**Checkpoint**: 첫 사용자가 막히던 자리가 열렸다.

---

## Phase 6: User Story 4 — 포인터 없이도 같은 일을 한다 (P2)

**Goal**: 끌어 놓기로 가능한 모든 이동이 체크 → 선택칸 경로로도 가능하다.

**Independent Test**: 마우스를 쓰지 않고 키보드만으로 그룹에 넣고 뺀다.

- [X] T042 [US4] `frontend/tests/` 에 키보드 경로 검증을 쓴다 — 체크 → 「그룹으로 옮기기」 → 이동, 그리고 새 그룹 만들어 옮기기까지 (FR-027 · SC-006)
- [X] T043 [US4] 끌기 표적 띠가 키보드 초점 순서를 어지럽히지 않는지 확인한다 — 표적은 끌기에 딸린 것이고 포인터 없는 사용자가 반드시 거치는 자리가 아니다 (FR-028 · UC-028-07)
- [X] T044 [P] [US4] 끌 수 있는 행이 기존 행 조작(선택·열기·삭제)을 가리지 않는지 확인한다

**Checkpoint**: 네 이야기가 모두 선다.

---

## Phase 7: Polish & 교차 관심사

- [ ] T045 전량 검증을 돌리고 `baseline.md` 와 대조한다 — 새로 깨진 것이 있으면 그것만 고친다. **기존 실패를 이 증분의 성과로 세지 않는다**
- [ ] T046 [P] `uv run python -m itb.schema.export --check` 로 스키마 드리프트가 없는지 확인한다 (생성물을 커밋했는지)
- [ ] T047 [P] `uv run ruff check src/ tests/` · `uv run lint-imports` · `npx tsc --noEmit` 을 통과시킨다
- [ ] T048 `quickstart.md` 의 §2 를 손으로 따라가며 확인한다 — 특히 2-2(옛 자산)와 2-3의 1번(끌기 전 화면이 그대로인가)
- [ ] T049 [P] `README.md:258-275` 의 그룹 설명을 고친다 — 「접두어는 영문 대문자·숫자 1~8자」가 **이 변경으로 거짓이 된다.** 새 규칙과 길이 상한 12를 반영하고 `IT-PM` 예시를 넣는다

---

## Dependencies & Execution Order

### Phase 의존

- **Phase 1 (기준선)**: 의존 없음
- **Phase 2 (규칙·읽기 함수)**: Phase 1 이후. **모든 이야기를 막는다**
- **Phase 3 (US1)**: Phase 2 이후
- **Phase 4 (US2)**: Phase 3 이후 — 옮길 그룹이 있어야 표적이 뜻을 갖는다
- **Phase 5 (US3)**: Phase 3 이후. Phase 4 와 독립이다 (선택 띠 구멍은 끌기 없이도 막힌다)
- **Phase 6 (US4)**: Phase 5 이후 (새 그룹 경로까지 키보드로 되는지 보므로)
- **Phase 7**: 전부 이후

### 이야기 사이

- **US1 (P1)**: 독립. 단독으로 값을 낸다 — `IT-PM` 그룹을 만들 수 있게 된다
- **US2 (P1)**: US1 이 있어야 의미가 산다 (그룹이 있어야 놓을 곳이 있다)
- **US3 (P2)**: US1 이후 US2 와 **병렬 가능**. 선택 띠 구멍 막기는 끌기와 다른 자리다
- **US4 (P2)**: US3 의 새 그룹 경로를 포함해 확인하므로 US3 이후

### 병렬 기회

- T012·T013·T014 — 서로 다른 파일의 호출 지점 전환
- T020 — 다른 라우트 파일의 제약 확인
- T035·T041·T044 — 각 이야기의 추가 검증
- Phase 4 와 Phase 5 — 다른 개발자가 함께 진행 가능 (T031/T037 이 같은 파일을 만지므로 조율 필요)

---

## Implementation Strategy

### MVP (US1 만)

1. Phase 1 기준선
2. Phase 2 규칙과 읽기 함수
3. Phase 3 US1
4. **멈추고 확인**: `IT-PM` 그룹을 만들고 옛 자산이 그대로인지 본다
5. 이 지점에서 사용자가 보고한 「안 된다」의 원인이 사라진다

### 증분

1. Phase 1~2 → 기반
2. + US1 → 하이픈 접두어 (MVP)
3. + US3 → 그룹이 없어도 길이 있다 (끌기 없이도 값이 난다)
4. + US2 → 끌어 놓기
5. + US4 → 포인터 없이

**US3 을 US2 보다 먼저 넣어도 된다.** 우선순위는 US2 가 높지만, US3 이 더 작고 첫
사용자가 막히는 자리를 먼저 연다.

---

## Notes

- 이 증분은 **저장된 자산을 읽는 방법**을 바꾼다. 검증 없이 넘어가는 호출 지점을 만들지 않는다
- `split("-", 1)` 을 자리마다 `rsplit` 으로 바꾸지 않는다 — 읽기 함수를 부른다 (R3)
- 새 색·새 입력 부품·새 엔드포인트를 만들지 않는다
- 전량 검증은 `scripts/test-backend.sh` 와 `npx vitest run` 으로 한다 (`uv run pytest`·`npm test` 는 틀린 결과를 준다 — R8)
- 작업 단위 또는 논리 묶음마다 커밋한다
