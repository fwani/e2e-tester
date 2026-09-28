---

description: "Task list for 024 AI 의 손이 어디에 있는지 보인다"
---

# Tasks: AI 의 손이 어디에 있는지 보인다 — 조작 대상을 미러 위에 표시

**Input**: Design documents from `/specs/024-ai-focus-overlay/`

**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/](./contracts/)

**Tests**: **포함한다.** 헌법 품질 게이트 3 이 요구한다 — 「제품은 테스트 도구다. 자기
테스트 없이 내보내는 것은 허용되지 않는다」. 이 기능에는 그보다 구체적인 이유가 하나 더
있다: **좌표가 한 칸 어긋나도 눈으로는 잘 안 보인다.** 변환식은 자기 자신과만 맞으면
단위 검증을 전부 통과한다. 그래서 라운드트립 검증과 종단 검증이 둘 다 필요하다.

**Organization**: User Story 별로 묶는다. 각 Story 는 독립적으로 구현·검증된다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: US1 자리가 보인다 · US2 된 것과 안 된 것 · US3 믿을 수 없으면 안 그린다
- 파일 경로를 반드시 적는다

## Path Conventions

- 백엔드: `backend/src/itb/…` · 테스트 `backend/tests/{unit,contract,e2e}/…`
- 프론트: `frontend/src/…` · 테스트 `frontend/tests/…`
- 고정 대상: `fixtures/sample-app/…` — **제품이 아니라 테스트 대상**이다

---

## Phase 1: Setup (좌표계를 먼저 확인한다)

**Purpose**: 이 기능 전체가 **하나의 가정** 위에 서 있다 — 「경계 상자의 좌표계와 미러
프레임의 좌표계가 같다」. 그 가정이 틀리면 뒤의 모든 작업이 틀린 자리를 그린다. 코드를
쓰기 전에 확인한다.

- [ ] T001 **경계 상자와 프레임 좌표계가 같은지 실측한다.** 실제 브라우저를 띄워 한
  요소의 `bounding_box()` 값과 같은 순간 `mirror_frame` 이 싣는 `width`·`height` 를
  나란히 찍어 비교한다. 확인할 것: 둘 다 CSS 픽셀인가, 원점이 같은가, 스크롤된 상태에서
  경계 상자가 뷰포트 기준인가. **결과를 [research.md](./research.md) R3 에 실측으로
  기록한다** — 지금은 문서상의 근거만 있다
- [ ] T002 [P] **iframe 안의 요소도 주 프레임 기준으로 나오는지 실측한다.**
  `fixtures/sample-app/embedded.html` 의 하위 프레임 요소로 확인한다. 다르면
  [research.md](./research.md) R1 과 [data-model §2](./data-model.md) 를 고친다 — 그
  경우 프레임 오프셋을 더하는 일이 늘어난다
- [ ] T003 [P] **`pageScale`·`offsetTop` 의 실제 값을 이 환경에서 확인한다.** 데스크톱
  크롬에서 각각 1 과 0 으로 알려져 있으나, 변환식이 그 값에 의존하므로 확인해 둔다.
  0 이 나올 수 있는 값(`pageScale`)이 실제로 0 으로 오는 경우가 있는지도 본다
- [ ] T004 **지금 상태를 기록한다** ([quickstart §1](./quickstart.md)) — AI 작성을 한 번
  돌려 진행 문구만 나오고 미러에 아무 표시가 없음을 확인해 적는다. 고친 뒤 무엇이
  달라졌는지 증명할 기준이 된다

**Checkpoint**: 좌표계 가정이 실측으로 확인됐다. 틀렸다면 설계 문서를 먼저 고친다

---

## Phase 2: Foundational (자리라는 값을 만든다)

**Purpose**: 「요소가 화면에서 차지하는 자리」를 제품이 **값으로 들 수 있게** 한다.
발행도 표시도 아직 하지 않는다.

**⚠️ CRITICAL**: 이 단계가 끝나기 전에는 어떤 User Story 도 시작할 수 없다.

### 백엔드 — 실행기가 자리를 읽는다

- [ ] T005 `backend/src/itb/execution/step_executor.py` 에 `ElementRect` 를 정의한다 —
  `x`·`y`·`width`·`height` 넷. [data-model §2](./data-model.md) 의 유효성 규칙(너비·높이
  0 이하 금지, 수치 아님 금지, **음수 좌표는 유효**)을 생성 지점에서 지킨다
- [ ] T006 같은 파일의 `StepExecution` 에 `rect: ElementRect | None = None` 을 더한다.
  **`None` 이 정상 값**임을 docstring 에 적는다 — 「자리를 모른다」와 「자리가 없다」를
  구별하지 않는 이유를 함께 (둘 다 「그리지 않는다」로 귀결된다)
- [ ] T007 같은 파일에서 **요소를 확정한 직후** 경계 상자를 읽어 `StepExecution.rect` 에
  싣는다. 읽는 대상은 **실행기가 채택한 그 요소**다 — CSS 로 다시 찾지 않는다
  ([research R1](./research.md))
- [ ] T008 같은 파일에서 **측정 실패를 흡수한다.** 경계 상자 읽기가 예외를 던지거나
  `None` 을 돌려주면 `rect` 를 `None` 으로 두고 **실행을 그대로 진행한다** (FR-006).
  표시 때문에 작성이 끊기면 안 된다 — `_announce` 가 같은 규칙으로 되어 있다
- [ ] T009 **요소를 대상으로 하지 않는 Step 에서는 재지 않는다** — 이동·탭 닫기.
  잴 요소가 없는 자리에서 헛되이 시도하지 않는다

### 백엔드 — 통로

- [ ] T010 [P] `backend/src/itb/authoring/tools.py` 에 `FocusSink` 와 `FocusNotice` 를
  정의한다 ([data-model §6](./data-model.md)). `ProgressSink` 바로 옆에 두고, **왜 진행
  통로와 나누는지**를 적는다 — 진행 통로는 자리를 모르는 자리에서도 불린다
- [ ] T011 [P] 같은 파일의 `BrowserToolbox` 에 `on_focus: FocusSink | None = None` 을
  더한다. 없으면 아무것도 알리지 않고 나머지는 지금과 같이 동작한다

### 프론트 — 정변환

- [ ] T012 `frontend/src/components/mirror/useMirrorInput.ts` 에 `toDisplayRect` 를
  더한다 — `toTargetPoint` **바로 옆**에 둔다. 두 식이 서로의 역이어야 하고, 떨어져
  있으면 한쪽만 고쳐지는 날이 온다 ([research R3](./research.md))
- [ ] T013 같은 파일에서 `toDisplayRect` 가 `DisplayBox` 를 인자로 받는 **순수 함수**
  형태를 유지한다 — 실제 이미지 요소를 요구하면 jsdom 에서 검증할 수 없다 (자연 크기가
  0 이다). 역변환이 같은 이유로 이 형태를 택했다
- [ ] T014 같은 파일에서 역변환과 **같은 방어**를 건다 — 표시 크기·자연 크기·프레임
  크기가 0 이하면 `null`, 좌표가 수치가 아니면 `null`, `pageScale` 이 0 이하면 1 로 본다
- [ ] T015 [P] `frontend/src/api/ws.ts` 의 `SessionEvent` 유니온에 `ai_focus` 를 더한다
  — [contracts/ai-focus.md §1](./contracts/ai-focus.md) 이 권위다. **AI 이벤트 절**에
  두고, 재생 세션에서 관측되면 원칙 II 위반임을 기존 주석과 같은 형식으로 적는다

### 검증 — 여기서 틀리면 전부 틀린다

- [ ] T016 [P] `frontend/tests/MirrorFocusGeometry.test.ts` 에 **라운드트립 검증**을
  쓴다 — `toDisplayRect` 로 옮긴 자리의 좌상단을 `toTargetPoint` 로 되돌리면 원래 좌표와
  1~2픽셀 안에서 같다. **배율이 비정수인 경우**(축소 프레임)를 반드시 포함한다
- [ ] T017 [P] 같은 파일에 `toDisplayRect` 의 `null` 조건을 고정한다 — 크기 0, 수치 아님,
  프레임 크기 0
- [ ] T018 [P] `backend/tests/unit/test_step_executor_rect.py` 에 실행기가 자리를 실어
  돌려주는지 고정한다. **요소를 대상으로 하지 않는 Step 에서는 `None`** 임도 함께
- [ ] T019 [P] 같은 파일에 **측정 실패가 실행을 멈추지 않음**을 고정한다 — 경계 상자
  읽기가 예외를 던져도 Step 은 성공하고 `rect` 만 `None` 이다 (FR-006)

**Checkpoint**: 자리가 값으로 존재하고 양쪽 변환이 서로의 역임이 고정됐다. 아직 아무것도
발행되지 않고 그려지지 않는다

---

## Phase 3: User Story 1 — AI 가 만지는 자리가 보인다 (Priority: P1) 🎯 MVP

**Goal**: AI 가 요소를 조작하면 미러의 그 자리에 테두리가 나타난다. 한 번에 하나이고,
멈추면 사라진다.

**Independent Test**: AI 작성을 시작하고 미러를 본다. 조작할 때마다 그 요소 자리에
테두리가 나타나고, 테두리 안에 있는 것이 진행 문구가 말하는 요소와 같으면 통과다
([quickstart §1~§2](./quickstart.md)).

### 백엔드 — 발행

- [ ] T020 [US1] `backend/src/itb/authoring/tools.py` 의 `_execute` 에서 실행 성공 후
  `StepExecution.rect` 를 꺼내 `on_focus` 로 알린다. `status="done"`, `label` 은 Step 의
  이름표와 **같은 값**
- [ ] T021 [US1] 같은 자리에서 **`rect` 가 `None` 이면 알리지 않는다** — 「자리 없음」을
  나타내는 값을 보내지 않는다 ([contracts §1](./contracts/ai-focus.md))
- [ ] T022 [US1] 같은 파일에서 **알림 실패가 작성을 멈추지 않게 한다** — `_announce` 와
  같은 방식으로 예외를 삼킨다 (FR-006)
- [ ] T023 [US1] `backend/src/itb/api/routes/sessions.py` 의 AI 작성 배선 **두 곳**
  (T112 경로와 재녹화 경로)에 `on_focus=lambda notice: work.session.emit("ai_focus", …)`
  를 잇는다. **두 곳 다 잇는다** — 한쪽만 이으면 경로에 따라 표시가 생겼다 없어진다
- [ ] T024 [P] [US1] `backend/tests/contract/test_ai_focus_event.py` 에 이벤트 모양을
  고정한다 — 필드 넷, `status` 가 `done`, 좌표가 수치. [contracts §1](./contracts/ai-focus.md) 이 권위다
- [ ] T025 [P] [US1] 같은 파일에 **자리 없는 조작에서 이벤트가 나가지 않음**을 고정한다

### 프론트 — 받고, 재고, 판정한다

- [ ] T026 [US1] `frontend/src/pages/SessionScreen.tsx` 에 `ai_focus` 수신을 더한다 —
  `mirror_frame` 상태 옆에 `FocusMark` 하나를 둔다. **목록으로 쌓지 않는다** (FR-014)
- [ ] T027 [US1] 같은 파일에 수명을 둔다 — `FOCUS_MARK_TTL_MS = 2500` 상수를 이름 붙여
  두고, 지나면 표시가 사라진다 (FR-015). **화면이 센다** — 서버가 「지워라」를 보내지
  않는 이유를 주석으로 적는다 ([research R6](./research.md))
- [ ] T028 [US1] 같은 파일에서 **무엇을 그릴지 계산해 `MirrorView` 에 넘긴다** — 탭
  일치·프레임 존재·좌표 근거 존재를 여기서 판정하고 `toDisplayRect` 로 변환한 결과만
  넘긴다. 컴포넌트가 국면을 보지 않는다 (FR-316 과 같은 원칙 · [research R7](./research.md))
- [ ] T029 [US1] `frontend/src/components/mirror/FocusOverlay.tsx` 를 만든다 — 표시
  좌표를 받아 테두리 하나를 그린다. `pointer-events: none` (FR-020). 색은 정본 토큰에서
  가져온다 — 성공은 `run` 계열 (FR-022)
- [ ] T030 [US1] `frontend/src/components/MirrorView.tsx` 에서 `<img>` 를 **크기가
  이미지에 딱 맞는 `relative` 래퍼**로 감싸고 오버레이를 그 안에 절대 배치한다. 이미지는
  가운데 정렬되므로 부모 기준으로 놓으면 밀린 만큼 어긋난다 ([research R7](./research.md))
- [ ] T031 [US1] 같은 파일에서 **포인터 처리기가 `<img>` 에 그대로 남아 있는지 확인**
  한다 — 래퍼가 조작 전달 경로를 바꾸면 안 된다
- [ ] T032 [US1] 같은 파일에 `focus` props 를 더한다. **이미 변환되고 판정된 결과**를
  받는다 ([data-model §7](./data-model.md))

### 검증

- [ ] T033 [P] [US1] `frontend/tests/MirrorFocusOverlay.test.tsx` 에 테두리가 나타남을
  고정한다 — 알림이 오면 그려지고, 새 알림이 오면 **앞의 것이 사라진다** (FR-014)
- [ ] T034 [P] [US1] 같은 파일에 수명을 고정한다 — 2.5초가 지나면 사라진다 (FR-015)
- [ ] T035 [P] [US1] 같은 파일에 **진행 문구가 줄지 않았음**을 고정한다 — 이 기능이
  문구를 대체하지 않는다 (FR-023)

**Checkpoint**: MVP 완성. AI 가 만지는 자리가 미러에 보인다

---

## Phase 4: User Story 2 — 된 것과 안 된 것이 구분된다 (Priority: P2)

**Goal**: 조작이 실패한 자리가 성공과 다른 모습으로 보인다. 단, **자리를 아는 실패에
한한다.**

**Independent Test**: 비활성 요소를 조작하게 시키고 실패 표시가 성공과 눈으로 구분되는지
본다. 없는 요소를 조작하게 시키면 아무 표시도 없어야 한다 ([quickstart §5](./quickstart.md)).

- [ ] T036 [US2] `backend/src/itb/execution/step_executor.py` 의 `StepFailure` 에
  `rect: ElementRect | None` 을 더한다 ([data-model §4](./data-model.md))
- [ ] T037 [US2] 같은 파일에서 **요소는 찾았으나 동작이 실패한 경우** 자리를 실어
  던진다 — 가려짐·비활성·시간 초과가 그렇다. 요소를 찾지 못한 실패에서는 `None` 이다
- [ ] T038 [US2] `backend/src/itb/authoring/tools.py` 의 `_execute` 실패 경로에서
  `StepFailure.rect` 를 꺼내 `status="failed"` 로 알린다
- [ ] T039 [US2] 같은 파일에서 **가리키는 자리가 하나로 좁혀지지 않아 거절한 경우**에는
  알리지 않는다 — 어느 것인지 제품도 모른다. 하나를 골라 그리면 거짓말이다 (FR-010)
- [ ] T040 [US2] `frontend/src/components/mirror/FocusOverlay.tsx` 에 실패 모습을 더한다
  — 정본의 `fail` 계열. 성공과 **눈으로 구분**되어야 한다 (FR-013)
- [ ] T041 [P] [US2] `backend/tests/contract/test_ai_focus_event.py` 에 실패 알림을
  고정한다 — 동작 실패에는 자리가 실리고, 요소를 못 찾은 실패에는 **이벤트가 나가지
  않는다**
- [ ] T042 [P] [US2] `frontend/tests/MirrorFocusOverlay.test.tsx` 에 성공·실패가 서로
  다른 모습임을 고정한다
- [ ] T043 [P] [US2] 같은 파일에 실패 표시도 새 알림에 밀려남을 고정한다

**Checkpoint**: 어디서 막혔는지가 화면에 보인다

---

## Phase 5: User Story 3 — 믿을 수 없으면 그리지 않는다 (Priority: P3)

**Goal**: 잘못된 자리에 뜬 테두리는 표시가 없는 것보다 나쁘다. 그리지 않는 조건 전부를
닫는다.

**Independent Test**: [research R8](./research.md) 의 판정 표를 그대로 훑는다. 각 조건에서
테두리가 없으면 통과다 ([quickstart §6~§7](./quickstart.md)).

- [ ] T044 [US3] `frontend/src/pages/SessionScreen.tsx` 의 판정에 **프레임 없음·미러
  중단**을 더한다 (FR-016)
- [ ] T045 [US3] 같은 자리에 **좌표 근거(`geometry`) 없음**을 더한다 (FR-017)
- [ ] T046 [US3] 같은 자리에 **탭 불일치**를 더한다 — 알림의 탭과 지금 보고 있는 탭이
  다르면 그리지 않는다 (FR-018)
- [ ] T047 [US3] 같은 자리에 **표시 영역과 겹치지 않는 자리**를 더한다 — 밀어 넣지
  않는다 (FR-019). 일부만 벗어난 경우는 **잘라서 그린다** — 보이는 부분은 사실이다
- [ ] T048 [US3] 같은 파일에서 **탭이 바뀌면 표시를 버린다** — 다른 탭으로 옮겨 간 뒤
  이전 탭의 자리가 남아 있으면 안 된다
- [ ] T049 [US3] `frontend/src/components/MirrorView.tsx` 에서 **중단 사유 안내가 나올
  때는 오버레이 자체가 없음**을 보장한다 — 프레임이 없는 분기에는 오버레이가 붙지
  않는다 (FR-021)
- [ ] T050 [P] [US3] `frontend/tests/MirrorFocusSuppression.test.tsx` 에
  [research R8](./research.md) 의 판정 표를 **한 줄씩** 고정한다 — 표와 검증이 1:1 이어야
  나중에 한 줄이 빠진 것을 알 수 있다
- [ ] T051 [P] [US3] 같은 파일에 **화면을 새로 고치면 복원되지 않음**을 고정한다
- [ ] T052 [P] [US3] `frontend/tests/MirrorFocusOverlay.test.tsx` 에 **포인터가 통과함**을
  고정한다 — 테두리가 덮인 자리의 클릭이 `<img>` 에 닿는다 (FR-020 · SC-005)
- [ ] T053 [US3] 강등(초당 1장) 상태에서 표시를 **억제하지 않음**을 확인한다 — 좌표는
  옳고, 강등 사실은 이미 화면이 말한다 ([research R8](./research.md))

**Checkpoint**: 믿을 수 없는 상황에서 아무것도 그리지 않는다

---

## Phase 6: 헌법 경계와 마무리

**Purpose**: 원칙 II 경계를 고정하고, 실제 좌표가 맞는지 사람이 보는 것과 같은 것을
기계가 본다.

### 원칙 II — 가장 중요한 고정

- [ ] T054 `backend/tests/test_principle_ii_timeline.py` 에 **재생 세션에서 `ai_focus`
  가 0 건**임을 더한다 (FR-007 · SC-006). 기존 `ai_*` 검증이 이미 그 일을 하는 자리다
- [ ] T055 `backend/src/itb/execution/step_executor.py` 의 머리말에 **이 모듈이 아무것도
  발행하지 않는다**는 사실과 그 이유를 적는다 — 콜백을 달지 않은 것이 원칙 II 통과의
  핵심이다 ([research R5](./research.md))
- [ ] T056 `uv run lint-imports` 로 임포트 계약이 그대로임을 확인한다 — 실행 계층이
  작성 계층을 임포트하지 않는다

### 대상 화면 무변경

- [ ] T057 `backend/tests/e2e/test_focus_no_page_mutation.py` 에 **대상 페이지의 요소
  수가 조작 전후로 같음**을 고정한다 (FR-025 · SC-008). 이 기능이 대상 화면에 아무것도
  심지 않는다는 것의 증명이다

### 종단 — 좌표가 진짜 맞는가

- [ ] T058 `backend/tests/e2e/test_focus_coordinates.py` 에 **실제 브라우저에서 좌표가
  맞는지** 고정한다 — 알려진 크기·위치의 요소를 조작하고, 알림의 자리가 그 요소의
  실제 자리와 일치하는지 본다. **이것 없이는 좌표 정확성이 검증되지 않는다** — 변환식은
  자기 자신과만 맞으면 단위 검증을 통과한다
- [ ] T059 [P] 같은 파일에 **스크롤 뒤의 자리**를 고정한다 — 살펴본 시점이 아니라
  조작 직전의 자리여야 한다 (FR-002). 스크롤은 좌표가 낡는 유일한 경로다

### 마무리

- [ ] T060 [P] `specs/024-ai-focus-overlay/quickstart.md` 를 실제로 훑고, 다른 곳이
  있으면 문서를 고친다. **§3 밀집 화면과 §4 스크롤을 반드시 본다**
- [ ] T061 [P] `specs/001-interactive-ai-test-builder/contracts/websocket.md` 의 AI
  이벤트 표에 `ai_focus` 한 줄을 더한다 — 이벤트 목록의 권위가 그 표다
- [ ] T062 전량 검증 — `uv run pytest` · `uv run ruff check src/ tests/` ·
  `uv run lint-imports` · `npm test` · `npm run build`

**Checkpoint**: 헌법 경계가 고정됐고 좌표 정확성이 기계로 확인됐다

---

## Dependencies & Execution Order

### Phase 의존

- **Phase 1 (Setup)**: 의존 없음. **가장 먼저** — 좌표계 가정이 틀리면 뒤가 전부 틀린다
- **Phase 2 (Foundational)**: Phase 1 완료에 의존. **모든 Story 를 막는다**
- **Phase 3~5 (User Stories)**: Phase 2 완료에 의존
- **Phase 6**: 원하는 Story 가 끝난 뒤

### Story 의존

| Story | 시작 조건 | 다른 Story 에 의존하는가 |
|---|---|---|
| US1 (P1) | Phase 2 완료 | 아니다 |
| US2 (P2) | Phase 2 완료 | 아니다 — 실패 경로는 성공 경로와 별개다 |
| US3 (P3) | Phase 2 완료 | 아니다 — 「안 그린다」는 「그린다」 없이도 검증된다 |

셋 다 독립이지만, **US1 없이 US2·US3 만 만드는 것은 값이 없다.** 우선순위대로 간다.

### Story 안에서

- 백엔드 발행 → 프론트 수신·판정 → 그리기 순
- 판정(SessionScreen)이 그리기(FocusOverlay)보다 먼저다 — 무엇을 그릴지가 정해져야 한다

### 병행 기회

- T002·T003 (실측 둘)
- T010·T011 (도구 통로) · T015 (프론트 타입) — 서로 다른 파일
- T016~T019 (검증 넷) — 서로 다른 파일
- T024·T025 (계약 검증)
- T033~T035 (US1 검증 셋)
- T041~T043 (US2 검증 셋)
- T050~T052 (US3 검증 셋)
- T059~T061 (마무리)

---

## Parallel Example: Phase 2 검증

```bash
Task: "라운드트립 검증 — frontend/tests/MirrorFocusGeometry.test.ts"
Task: "null 조건 고정 — frontend/tests/MirrorFocusGeometry.test.ts"
Task: "실행기 자리 반환 — backend/tests/unit/test_step_executor_rect.py"
Task: "측정 실패 흡수 — backend/tests/unit/test_step_executor_rect.py"
```

---

## Implementation Strategy

### MVP (US1 만)

1. Phase 1 — 좌표계 확인
2. Phase 2 — 자리라는 값
3. Phase 3 — US1
4. **멈추고 확인**: [quickstart §1~§4](./quickstart.md) 를 손으로 훑는다. 특히 §3
   밀집 화면 — 좌표가 맞는지는 여기서만 드러난다

### 점진 전달

1. Setup + Foundational → 자리가 값으로 존재한다
2. US1 → 자리가 보인다 (MVP)
3. US2 → 막힌 자리가 구분된다
4. US3 → 믿을 수 없을 때 안 그린다
5. Phase 6 → 헌법 경계와 좌표 정확성 고정

**Phase 6 의 T054(재생 0 건)는 늦추면 안 된다.** 원칙 II 는 NON-NEGOTIABLE 이고 헌법이
「모든 증분에서 성립해야 한다」고 못 박은 것이다. US1 이 끝나면 바로 건다.

---

## Notes

- `[P]` = 다른 파일, 미완료 작업에 의존하지 않음
- 이 기능은 **저장되는 것을 하나도 만들지 않는다** — 마이그레이션이 없다
- **대상 화면에 아무것도 심지 않는다.** 그 사실을 T057 이 증명한다
- 좌표가 틀렸는지 의심되면 미러를 직접 클릭해 보라 — 클릭이 맞는 요소에 가는데 테두리만
  어긋나면 정변환 쪽이 틀렸다
- 작업 하나 또는 논리적 묶음마다 커밋한다
