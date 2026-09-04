---
description: "Task list for 002 — 결함 수정과 확정 디자인 준수"
---

# Tasks: 결함 수정과 확정 디자인 준수

**Input**: Design documents from `/specs/002-defect-fix-design-conformance/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: 테스트 작업을 **포함한다.** 선택이 아니다 — 헌법 "Development Workflow & Quality
Gates" 3이 "제품은 테스트 도구다. 자기 테스트 없이 출시하는 것은 허용되지 않는다"고 요구하고,
spec RG-001·RG-002 가 기준선 유지와 테스트 무약화를 요구한다.

**Organization**: 사용자 스토리별로 묶어 각각을 독립적으로 구현·검증할 수 있게 한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: 대응하는 사용자 스토리 (US1~US7)
- 모든 작업에 정확한 파일 경로를 적는다

## Path Conventions

웹 애플리케이션 구조 — `backend/src/itb/`, `backend/tests/`, `frontend/src/`, `frontend/tests/`

## 기준선 (RG-001 판정 근거 · 이 라운드 시작 시점 실측)

| 대상 | 명령 | 시작 시점 |
|---|---|---|
| 백엔드 unit+contract | `cd backend && .venv/bin/python -m pytest tests/unit tests/contract -q` | **726 passed** |
| 프런트엔드 | `cd frontend && npx vitest run` | **62 passed / 8 files** |

**이 수는 줄어들 수 없다.** 늘어나는 것은 정상이다.

---

## Phase 1: Setup (Shared Infrastructure)

**목적**: 디자인 대조의 기준값을 기계적으로 확보한다. 이것이 없으면 DC-012 판정이
"보고 비슷한가"로 되돌아간다.

- [X] T001 [P] `scripts/design_baseline.py` 를 만든다. `docs/design/*.dc.html` 8종에서 루트 치수·색 목록·글꼴·테두리 두께·그림자·주요 영역 높이를 추출해 JSON 으로 출력한다. **판정하지 않는다 — 사실만 뽑는다** (contracts/design-conformance.md §4)
- [X] T002 `scripts/design_baseline.py` 로 `specs/002-defect-fix-design-conformance/design-conformance/<Screen>.md` 8개를 생성한다. 축 6개(구조·컴포넌트·치수·타이포색·상태·가감)의 `기준값` 칸만 채우고 `관측값`·`판정` 은 비워 둔다
- [X] T003 [P] `specs/002-defect-fix-design-conformance/design-conformance/undefined-states.md` 를 빈 표로 만든다 (화면·상태·근거·결정 4열, DC-009)
- [X] T004 [P] `scripts/design_baseline.py` 검증 — `docs/design` 에 `border-radius` 가 0회임을 재확인하는 단언을 스크립트에 넣는다. 기준이 바뀌면 즉시 드러나야 한다

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ 이 단계가 끝나기 전에는 어떤 사용자 스토리도 시작할 수 없다.**

전역 422 핸들러는 US5 를 거쳐 US4 까지 막고 있고(plan.md 구현 순서), 토큰은 8화면 전부의
기반이다.

### 전역 오류 표현 (DR-022·DR-030 — US5·US4 의 선행 조건)

- [X] T005 `backend/src/itb/api/app.py` 에 `RequestValidationError` 핸들러를 등록한다. 응답을 계약 형태 `{error:{code,message,detail}}` 로 바꾼다. `code` 는 **기존 `DEFINITION_INVALID` 를 재사용한다** — 새 코드를 만들면 프런트엔드 유니온과 계약 문서를 함께 늘려야 하는데 의미가 이미 같다 (contracts/rest-api-delta.md §0)
- [X] T006 `backend/src/itb/api/app.py` 의 핸들러가 `error.message` 에 **어느 필드가 왜 거절됐는지** 한국어 한 문장으로 담게 한다. `error.detail.fields` 에 `[{loc, reason}]` 배열을 넣는다
- [X] T007 [P] `backend/tests/contract/test_validation_errors.py` 신규 — 잘못된 본문을 여러 엔드포인트에 보내 **모두** 계약 형태로 오는지 확인한다. `{"detail":[...]}` 가 나오면 실패

### 저장 위치 (US1 의 선행 조건)

- [X] T008 [P] `backend/src/itb/storage/paths.py` 신규 — XDG 경로를 결정한다. `~/.config/itb/`(설정·키·레지스트리), `~/.local/share/itb/projects/`(사용자 자산). 기존 `secrets/keys.py:26` 의 `~/.config/itb/keys` 선례를 잇는다 (research R4)
- [X] T009 [P] `backend/tests/unit/test_paths.py` 신규 — 경로 결정과 `HOME` 이 바뀌었을 때의 동작을 확인한다

### 디자인 토큰 (US6 의 기반 · 모든 화면에 영향)

- [X] T010 `frontend/src/theme/tokens.css` 를 확정 디자인 실측값으로 재작성한다. **`--radius`·`--radius-sm` 을 삭제한다** — dc.html 8종에 `radius` 문자열이 0회다. 테두리 기본을 `3px`(강조)·`2px`(보조)로, `body` 배경을 `#EFEBE0` 로 바꾸고 하드 오프셋 그림자를 도입한다 (contracts/design-conformance.md §3)
- [X] T011 `frontend/src/theme/tokens.css` 의 `button`·`input`·`select`·`textarea` 기본 스타일에서 둥근 모서리와 1px 테두리를 없앤다. 팔레트는 이미 정확하므로 색 값을 바꾸지 않는다
- [X] T012 [P] `frontend/tests/DesignTokens.test.tsx` 신규 — `tokens.css` 에 `border-radius`·`--radius` 가 없음을 단언한다. 회귀 가드다 (DC-004)

**Checkpoint**: T005~T012 완료 후 `pytest tests/unit tests/contract` 와 `vitest run` 이 기준선 이상이어야 한다.

---

## Phase 3: User Story 1 — 도구를 다시 열면 내 프로젝트가 그대로 거기 있다 (Priority: P1) 🎯 MVP

**Goal**: 경로를 한 글자도 타이핑하지 않고 기존 프로젝트를 열 수 있다.

**Independent Test**: 프로젝트를 만들고 도구를 재시작한 뒤, 경로 입력 없이 그 프로젝트를 다시 연다.

**왜 이것이 MVP 인가**: 이 화면을 통과하지 못하면 제품의 나머지 전부에 도달할 수 없다.
그리고 이 스토리가 건드리는 `ProjectSetup.tsx` 는 확정 디자인에 대응이 없어(DC-010)
US6 전사와 파일이 겹치지 않는다 — 먼저 해도 덮어쓰이지 않는다.

### Tests for User Story 1

- [X] T013 [P] [US1] `backend/tests/unit/test_registry.py` 신규 — 레지스트리 읽기·쓰기, 모르는 `version` 일 때 빈 목록 + 경고(덮어쓰지 않음), 중복 `root` 제거
- [X] T014 [P] [US1] 슬러그 변환 검증 — **`backend/tests/unit/test_paths.py` 에 넣었다** (슬러그가 `paths.py` 에 있어 파일을 나눌 이유가 없다). 이름→슬러그 변환. 경로 구분자·`..`·제어 문자 제거, 빈 결과는 `project`, 충돌 시 `-2`·`-3`
- [X] T015 [P] [US1] `backend/tests/contract/test_fs_browse_api.py` 신규 — **경계 검증이 핵심이다.** 홈 밖 거절, `..` 정규화 후 거절, 심볼릭 링크 재검사, **응답에 파일 이름이 하나도 없음**, 숨김 디렉터리 제외, 홈 최상위에서 `parent` 가 `null`
- [X] T016 [P] [US1] `backend/tests/contract/test_project_list_api.py` 신규 — 스캔 ∪ 레지스트리 합집합, `last_opened_at` 내림차순, 빈 목록이 200, 접근 불가 항목의 `accessible:false` + 사유

### Implementation for User Story 1

- [X] T017 [US1] `backend/src/itb/storage/registry.py` 신규 — `ProjectRegistryEntry` 읽기·쓰기. `~/.config/itb/registry.json`, 필드 `root`·`name`·`last_opened_at`·`origin`. `accessible`·`unavailable_reason` 은 **저장하지 않고 조회 시 계산한다** (data-model.md §1)
- [X] T018 [US1] `backend/src/itb/storage/repository.py` 변경 — 프로젝트 생성 시 관리 위치(`~/.local/share/itb/projects/<슬러그>/`)를 쓰도록 한다. 슬러그 충돌은 `-2`·`-3` 으로 피하고 `PROJECT_ALREADY_EXISTS` 를 내지 않는다 — 사용자가 위치를 모르는데 위치 충돌로 실패시킬 수 없다
- [X] T019 [US1] `backend/src/itb/api/routes/fs.py` 신규 — `GET /api/fs/browse`. 홈 하위 한정, `resolve()` 후 경계 검사, 심볼릭 링크 추적 후 재검사, **디렉터리만 반환**, 숨김 제외, 각 항목에 `is_project` (contracts/rest-api-delta.md §4)
- [X] T020 [US1] `backend/src/itb/api/routes/project.py` 에 `GET /api/project/list` 를 추가한다. 관리 위치 스캔 ∪ 레지스트리, `root` 로 중복 제거, `last_opened_at` 내림차순
- [X] T021 [US1] `backend/src/itb/api/routes/project.py` 의 `POST /api/project/create` 에서 **`path` 필드를 제거한다** (DR-001). 관리 위치에 만들고 레지스트리에 `origin:"managed"` 로 등록한다
- [X] T022 [US1] `backend/src/itb/api/routes/project.py` 의 `POST /api/project/open` 에 경계 검증을 적용하고, 성공 시 레지스트리에 `origin:"external"` 로 등록·`last_opened_at` 갱신한다. 실패 시 **무엇이 없어서 열 수 없는지** 메시지에 담는다 (DR-008)
- [X] T023 [US1] `backend/src/itb/api/routes/project.py` 에 `DELETE /api/project/registry` 를 추가한다. **레지스트리 항목만 지운다. 디스크의 프로젝트는 지우지 않는다** (DR-009)
- [X] T024 [US1] `backend/src/itb/api/app.py` 에 `fs` 라우터를 등록한다
- [X] T025 [US1] `frontend/src/api/client.ts` 에 `project.list()`·`project.forget(root)`·`fs.browse(path)` 를 추가하고 `project.create` 에서 `path` 를 뺀다
- [X] T026 [US1] `frontend/src/pages/ProjectSetup.tsx` 를 재작성한다 — **경로 자유 입력란을 없애고**(DR-001) 프로젝트 목록 + "새 프로젝트 만들기" + "기존 프로젝트 열기" 세 갈래로 만든다. 확정 디자인에 대응이 없으므로 8화면의 시각 언어를 따른다 (DC-010)
- [X] T027 [US1] `frontend/src/pages/ProjectSetup.tsx` 에 폴더 선택기를 넣는다 — `GET /api/fs/browse` 로 홈 하위를 탐색하고 `is_project` 인 항목을 구분해 보여준다 (DR-005)
- [X] T028 [US1] `frontend/src/pages/ProjectSetup.tsx` 에 접근 불가 항목 표시와 목록에서 치우기를 넣는다 (DR-009). 치우기가 **자산 삭제가 아님**을 문구로 밝힌다
- [X] T029 [US1] `frontend/src/App.tsx` 의 최초 진입을 바꾼다 — `GET /api/project` 404 시 목록을 먼저 불러 보여준다. 새로 만든 프로젝트의 위치를 사용자에게 표시한다 (DR-006)
- [X] T030 [P] [US1] `frontend/tests/ProjectSetup.test.tsx` 신규 — 경로 자유 입력란이 **없음**을 단언하고(SC-102), 목록 렌더·선택·접근 불가 표시를 확인한다
- [X] T031 [US1] `specs/002-defect-fix-design-conformance/design-conformance/undefined-states.md` 에 ProjectSetup 의 미정의 상태(빈 목록·로딩·오류)와 근거를 기록한다 (DC-009)

**Checkpoint**: quickstart.md §1 이 통과해야 한다. 서버를 임의 디렉터리에서 띄워도 동작한다.

---

## Phase 4: User Story 6 — 화면이 확정 디자인 그대로다 (Priority: P1)

**Goal**: 8화면이 `docs/design/*.dc.html` 과 구조·배치·치수·타이포·색·상태에서 일치한다.

**Independent Test**: 8화면 각각을 대응 dc.html 과 나란히 놓고 대조표의 판정 칸을 채운다.

**⚠️ US2·US3 보다 먼저 한다.** 전사는 파일을 통째로 다시 쓰므로 나중에 하면 앞선
동작 수정을 덮는다 (plan.md 구현 순서).

**전사 절차는 화면마다 동일하다** (contracts/design-conformance.md §2):
DOM 순서대로 옮기고 → 인라인 style 을 손대지 않고 → SVG 를 `viewBox`·`d` 까지 그대로 →
데이터에서 오는 문자열만 props 로 → 상호작용을 붙인다.

### 화면 골격 분리 (DC-008)

- [X] T032 [US6] `frontend/src/App.tsx` 의 화면 상태를 확정 디자인 8종 + 미대응 4종에 맞춰 늘린다. **세션 상태(`view.state`)와 화면 선택을 분리한다** — 지금은 `Runner` 하나가 세션 상태 조합으로 4개 화면을 그리고, 그 얽힘이 research R2 가 규명한 "AI 실패가 안 보이는" 원인이다
- [X] T033 [US6] `frontend/src/components/StepInspector.tsx` 를 `frontend/src/pages/StepInspector.tsx` 로 옮긴다. `canvas.json` 이 독립 artboard 로 정의했고 DC-008 이 독립 화면을 요구한다

### 전사 — 8화면 (서로 다른 파일이므로 병렬 가능)

- [X] T034 [P] [US6] `frontend/src/pages/TestList.tsx` 를 `docs/design/TestList.dc.html`(1440×760) 로 전사한다. 헤더 60px·하단 테두리 3px, 검색행, 전체/PASS/FAIL 카운터, 테스트 목록 행
- [X] T035 [P] [US6] `frontend/src/pages/CreateTest.tsx` 를 `docs/design/CreateTest.dc.html`(1000×700) 로 전사한다
- [X] T036 [P] [US6] `frontend/src/pages/AiRecord.tsx` 를 `docs/design/AiRecord.dc.html`(1440×900) 로 전사하고 **독립 화면으로** 만든다. Runner 안의 조건부 패널에서 분리한다
- [X] T037 [P] [US6] `frontend/src/pages/Runner.tsx` 를 `docs/design/Main.dc.html`(1440×900) 로 전사한다 — 실행 중 화면
- [X] T038 [P] [US6] `frontend/src/pages/RunnerPaused.tsx` 를 `docs/design/RunnerPaused.dc.html`(1440×900) 로 전사하고 **독립 화면으로** 만든다
- [X] T039 [P] [US6] `frontend/src/pages/Takeover.tsx` 를 `docs/design/Takeover.dc.html`(1440×900) 로 전사하고 **독립 화면으로** 만든다
- [X] T040 [P] [US6] `frontend/src/pages/RunResult.tsx` 를 `docs/design/RunResult.dc.html`(1440×900) 로 전사한다 — FAIL 상태
- [X] T041 [P] [US6] `frontend/src/pages/StepInspector.tsx` 를 `docs/design/StepInspector.dc.html`(640×1140) 로 전사한다 — locator 우선순위 표
- [X] T042 [US6] 8화면의 인라인 `<svg>` 98개를 `viewBox`·`stroke-width`·`d` 까지 그대로 옮겼는지 확인한다. **아이콘 라이브러리로 대체하지 않는다** — 대체는 해석이다

### 미대응 화면의 시각 언어 정렬 (DC-010)

- [X] T043 [P] [US6] `frontend/src/pages/TestDefinition.tsx` 를 8화면의 시각 언어에 맞춘다. 1:1 대조 의무는 없다
- [X] T044 [P] [US6] `frontend/src/components/` 의 공용 컴포넌트(`Badges`·`StepList`·`MirrorView`·`TabStrip`·`LocatorPriorityTable` 등)를 전사된 화면의 시각 언어에 맞춘다. **미리 추상화하지 않는다** — 전사 결과를 보고 실제로 같은 것만 공유한다

### 검증과 기록

- [X] T045 [US6] `frontend/src/` 전체에 `border-radius`·`--radius` 가 없음을 확인한다 (DC-004, quickstart §6)
- [X] T046 [US6] 8종 각각에 화면 전이로 도달 가능한지 확인한다. 특히 D3·D5·D6·D8 — 시작 시점에 Runner 안의 패널이었다 (SC-109)
- [X] T047 [US6] 전사 중 결정한 미정의 상태를 **전부** `design-conformance/undefined-states.md` 에 기록한다. 근거 없는 항목이 있으면 그것은 해석이고 DC-001 위반이다 (SC-110)
- [X] T048 [US6] `frontend/tests/` 의 기존 62건 중 문구 변경으로 깨진 것의 기대값을 **dc.html 의 문구로** 고친다. 각 수정에 "어느 파일의 어느 문구"를 근거로 남긴다. **그 밖의 이유로는 고치지 않는다** (RG-002)
- [X] T049 [US6] `design-conformance/<Screen>.md` 8개의 `관측값` 칸을 채운다. **`판정` 칸은 비워 둔다 — 구현자가 자기 구현을 판정하면 대조가 아니라 자기 확인이다** (001 T156 이 같은 이유로 미완이다)

**Checkpoint**: `vitest run` 이 기준선(62) 이상. `tsc --noEmit` 통과.

---

## Phase 5: User Story 2 — 녹화를 멈추면 기록한 것이 남아 있고 저장할 수 있다 (Priority: P1)

**Goal**: 중지 후에도 화면에 머물러 Step 을 검토하고 저장할 수 있다.

**Independent Test**: 녹화 → 3개 이상 조작 → 중지 → Step 목록 확인 → 이름 붙여 저장.

**원인은 두 겹이다** (research R1). 프런트엔드만 고치면 저장이 여전히 `SESSION_NOT_FOUND` 다.

### Tests for User Story 2

- [X] T050 [P] [US2] `backend/tests/contract/test_session_review_api.py` 신규 — 중지 후 세션이 **살아 있고** `state:"review"` 인지, `GET`·스텝 편집·`save`·`discard` 를 받고 실행·이어서·다시집기·탭전환을 `409 INVALID_TRANSITION` 으로 거절하는지 (001 FR-043a)
- [X] T051 [P] [US2] `backend/tests/integration/test_stop_then_save.py` 신규 — **이 라운드의 핵심 회귀 테스트다.** 녹화 → 중지 → 저장이 성공하는지. 시작 시점에는 `SESSION_NOT_FOUND` 로 실패했다

### Implementation for User Story 2

- [X] T052 [US2] `backend/src/itb/api/routes/sessions.py` 의 `stop` 에서 `state.sessions.close()`·`_WORK.pop()`·`broker.drop()` 을 **제거한다.** 리코더·에이전트·미러·러너·인라인 정리와 브라우저 종료는 그대로 두고 상태를 `review` 로 옮긴다 (contracts/rest-api-delta.md §6)
- [X] T053 [US2] `backend/src/itb/api/routes/sessions.py` 에 `review` 상태를 추가한다. **종료 상태가 아니다** — 기존 `stopped` 와 달리 명령을 받는다. 상태 기계에 전이를 정의한다
- [X] T054 [US2] `backend/src/itb/api/routes/sessions.py` 에 `POST /api/sessions/{id}/discard` 를 추가한다. **여기서 비로소 `SessionWork` 가 파괴된다.** 확인 대화상자는 화면의 책임이다 — 서버가 두 번 묻는 구조를 만들지 않는다
- [X] T055 [US2] `backend/src/itb/api/routes/sessions.py` 의 `save` 가 `review` 상태에서 동작하는지 확인하고, 저장 후 `SessionWork` 를 정리한다
- [X] T056 [US2] 브라우저 창이 외부에서 닫혀 세션이 유실된 경우에도 Step 이 보존되어 `review` 로 가도록 한다 (DR-015)
- [X] T057 [US2] `frontend/src/api/client.ts` 에 `sessions.discard(id)` 를 추가한다
- [X] T058 [US2] `frontend/src/pages/Runner.tsx` 의 중지 버튼에서 **`onFinished()` 호출을 없앤다**(3곳: 기존 287·377·533 위치). 중지 후 화면에 머물러 Step 목록과 저장 수단을 보여준다 (DR-010·DR-013)
- [X] T059 [US2] `frontend/src/pages/Runner.tsx` 의 `review` 상태에서 Step 삭제·수정·순서 변경이 되게 한다 (DR-012)
- [X] T060 [US2] `frontend/src/pages/Runner.tsx` 에 화면 이탈 시 유실 경고를 넣는다. `has_unsaved_changes` 로 판단하고, 확인 후 `discard` 를 호출한다 (DR-014)
- [X] T061 [P] [US2] `frontend/tests/RunnerReview.test.tsx` 신규 — 중지 후 Step 목록이 보이고 저장 수단이 있으며 이탈 시 경고가 뜨는지

**Checkpoint**: quickstart.md §2 통과. 특히 2번(화면 유지)과 4번(저장 성공).

---

## Phase 6: User Story 3 — "AI로 만들기"를 누르면 AI가 실제로 움직인다 (Priority: P1)

**Goal**: 실행하면 화면이 반응하고, 실패해도 사유가 보인다.

**Independent Test**: 자격 증명 없이 실행해도 **사유가 화면에 뜬다**. 무반응이 0건이다.

**원인**: 실패는 발생·전달되는데 그리는 컴포넌트가 세션 상태 조건 뒤에 숨어 있다 (research R2).

### Tests for User Story 3

- [X] T062 [P] [US3] `backend/tests/contract/test_ai_availability_api.py` 신규 — `GET /api/ai/availability` 가 자격 증명 조각을 **반환하지 않고**, 언어모델을 호출하지 않으며, 점검 실패 시에도 200 + `available:false` 로 답하는지
- [X] T063 [P] [US3] `frontend/tests/AiRecord.test.tsx` 신규 — **세션 상태와 무관하게** 실패 사유가 렌더되는지. `state:"paused"` + `aiMessages:[]` 조합에서도 오류가 보여야 한다. 이것이 시작 시점의 결함이다

### Implementation for User Story 3

- [X] T064 [US3] `backend/src/itb/api/routes/ai.py` 신규 — `GET /api/ai/availability`. 자격 증명 **해석 가능 여부만** 본다. 언어모델을 호출하지 않는다 (contracts/rest-api-delta.md §8)
- [X] T065 [US3] `backend/src/itb/api/app.py` 에 `ai` 라우터를 등록한다. **`itb.api` 계층이므로 `.importlinter` 의 `execution-no-llm` 계약을 위반하지 않는다** — 등록 후 `lint-imports` 로 확인한다 (RG-004)
- [X] T066 [US3] `frontend/src/api/client.ts` 에 `ai.availability()` 를 추가한다
- [X] T067 [US3] `frontend/src/pages/Runner.tsx`(또는 화면 분리 후의 상위)에서 **AI 세션 판정을 `view.state` 가 아니라 `authoring_mode` 로 바꾼다.** 그것이 세션의 불변 속성이다. `isAiSession` 이 `paused` 에서 거짓이 되는 것이 원인이었다 (research R2)
- [X] T068 [US3] `frontend/src/pages/AiRecord.tsx` 가 **실패 사유를 세션 상태와 무관하게** 렌더하게 한다 (DR-020)
- [X] T069 [US3] `ai_error` 수신 시 진행 로그에도 실패를 남긴다. 렌더 조건이 하나 어긋나도 사용자가 볼 경로가 둘이 되게 한다 (research R2 결정)
- [X] T070 [US3] `frontend/src/pages/CreateTest.tsx` 에서 AI 모드를 고르면 `ai.availability()` 를 확인하고, 사용할 수 없으면 **실행 전에** 무엇이 준비되지 않았고 무엇을 하면 되는지 안내한다 (DR-021)
- [X] T071 [US3] AI 실행 요청 접수 즉시 화면이 전환되게 한다. 화면에 아무 변화가 없는 상태로 끝나지 않아야 한다 (DR-016·SC-104)
- [X] T072 [US3] AI 수행 완료 시 Step 목록·저장 수단·"지시문은 저장되지 않으며 재실행 시 AI 를 쓰지 않는다" 안내를 표시한다 (DR-019, 001 FR-064)
- [X] T073 [P] [US3] `backend/tests/integration/test_ai_failure_visible.py` 신규 — 자격 증명 없이 AI 세션을 만들면 `ai_error` 가 발행되고 Step 이 보존되는지 (DR-020, 001 FR-067)

**Checkpoint**: quickstart.md §3 통과. 자격 증명 없는 상태에서 먼저 확인한다.

---

## Phase 7: User Story 5 — 키 쌍 만들기가 성공한다 (Priority: P2)

**Goal**: 키 쌍 생성이 화면에서 성공하고, 실패해도 읽을 수 있는 사유가 나온다.

**Independent Test**: 키 관리에서 키 쌍 만들기 → 성공, 키 상태 갱신.

**⚠️ US4 보다 먼저 한다.** DR-028 은 DR-025 의 선행 조건이다 — 키 생성이 고쳐지지 않으면
비밀 값 인라인 입력의 탈출구가 막힌다 (contracts/rest-api-delta.md §9).

**서버 계약은 거의 그대로다.** 실제 수정의 대부분은 Phase 2 의 T005~T007(전역 422 핸들러)이
이미 했다.

### Tests for User Story 5

- [X] T074 [P] [US5] `backend/tests/contract/test_secrets_api.py` 에 추가 — 8자 미만 암호구절이 **계약 형태**로 거절되는지. `{"detail":[...]}` 가 나오면 실패 (research R3)

### Implementation for User Story 5

- [X] T075 [US5] `backend/src/itb/api/routes/secrets_routes.py` 의 키 파일 쓰기 권한 부족을 500 이 아니라 `400` + 권한 문제임을 밝히는 문장으로 바꾼다 (DR-030)
- [X] T076 [US5] `frontend/src/pages/KeyManagement.tsx` 에 암호구절 제약(8~200자)을 **입력 시점에** 안내하고, 제약에 맞지 않으면 제출 자체를 막는다 (DR-029)
- [X] T077 [US5] `frontend/src/pages/KeyManagement.tsx` 의 실패 표시가 원시 상태 코드가 아닌 서버의 계약 메시지를 보여주는지 확인한다 (DR-030·SC-107)
- [X] T078 [US5] `frontend/src/pages/KeyManagement.tsx` 를 8화면의 시각 언어에 맞춘다 (DC-010)
- [X] T079 [P] [US5] `frontend/tests/KeyManagement.test.tsx` 신규 — 제약 안내가 제출 전에 보이고, 실패 시 HTTP 상태 코드가 화면에 노출되지 않는지

**Checkpoint**: quickstart.md §5 통과. `curl` 로 422 응답이 계약 형태인지 확인한다.

---

## Phase 8: User Story 4 — 비밀 값을 스텝에서 그 자리에 넣는다 (Priority: P2)

**Goal**: 비밀 값이 필요한 Step 에서 화면 이동 없이 값을 넣고 연결한다.

**Independent Test**: Step 편집에서 화면 이동 0회로 비밀 값을 넣고, 그 테스트가 실행된다.

**새 엔드포인트를 만들지 않는다.** `PUT /api/secrets/{name}` 이 **공개키만으로 동작하는 것**이
인라인 입력을 가능하게 한다 — 비밀키는 실행 시에만 필요하다 (research R5).

### Tests for User Story 4

- [X] T080 [P] [US4] `backend/tests/integration/test_secret_leakage.py` 에 추가 — 인라인 경로로 넣은 값이 테스트 정의·화면·로그·결과 어디에도 평문으로 없는지 (001 SC-010)
- [X] T081 [P] [US4] `frontend/tests/InlineSecret.test.tsx` 신규 — 입력 후 값이 컴포넌트 상태에 남지 않는지, Step 에 `{{변수명}}` 만 남는지

### Implementation for User Story 4

- [X] T082 [US4] `frontend/src/components/InlineSecretInput.tsx` 신규 — Step 편집 안에서 비밀 값을 입력해 `PUT /api/secrets/{name}` 으로 봉인한다. **전송 후 즉시 상태를 비운다** (DR-023·DR-024)
- [X] T083 [US4] `frontend/src/components/InlineSecretInput.tsx` 에 기존 변수 이름 선택을 넣는다. `GET /api/secrets` 는 **이름과 존재 여부만** 준다 (DR-026)
- [X] T084 [US4] `frontend/src/components/InlineSecretInput.tsx` 에 공개키가 없을 때의 경로를 넣는다 — 그 자리에서 `POST /api/keys/generate` 를 호출하고 이어서 진행한다. **US5 가 선행되어야 성립한다** (DR-025)
- [X] T085 [US4] `frontend/src/pages/StepInspector.tsx` 와 Step 편집 지점에 `InlineSecretInput` 을 붙인다. 비밀번호 유형·민감 표시 필드에서 노출한다
- [X] T086 [US4] `frontend/src/pages/SecretValues.tsx` 를 유지하되 **Step 작업 흐름이 이 화면을 거치도록 강제하지 않는지** 확인한다 (DR-027). 시각 언어를 8화면에 맞춘다 (DC-010)

**Checkpoint**: quickstart.md §4 통과. 화면 이동 0회.

---

## Phase 9: User Story 7 — 이번 라운드가 되던 것을 깨지 않는다 (Priority: P1)

**Goal**: 기준선 아래로 내려가지 않고, 헌법 원칙 I·II 가 유지된다.

**Independent Test**: 자동 테스트 전체를 돌려 기준선 이상으로 통과.

- [X] T087 [US7] `cd backend && .venv/bin/python -m pytest tests/unit tests/contract -q` — **726 이상** (RG-001·SC-111)
- [X] T088 [US7] `cd backend && .venv/bin/lint-imports` — `execution-no-llm`·`domain-is-pure`·`locator-strategy-is-pure` 세 계약 통과. 이 라운드가 임포트 그래프를 바꾸므로 반드시 확인한다 (RG-004·SC-112)
- [X] T089 [US7] `cd frontend && npx vitest run` — **62 이상**. `npx tsc --noEmit` 통과 (RG-001)
- [X] T090 [US7] `cd backend && .venv/bin/python -m pytest tests/integration tests/e2e -q` — 브라우저와 픽스처 앱이 필요하다. 실패하면 **원인과 함께 보고한다.** 통과한 것처럼 적지 않는다
- [X] T091 [US7] 이 라운드에서 삭제·`skip`·단언 제거된 테스트가 **0건**인지 확인한다. 문구 변경으로 인한 기대값 수정만 허용되며 각각에 근거가 있어야 한다 (RG-002)
- [X] T092 [US7] 기존에 저장된 테스트 정의가 그대로 열리고 실행되는지 확인한다. 저장 위치 변경(T018)이 기존 프로젝트를 깨지 않아야 한다 (RG-003)
- [X] T093 [US7] 사람 Step 과 AI Step 이 여전히 하나의 저장 경로를 쓰는지 확인한다 — 화면 분리(T032)가 저장을 나누지 않았는지 (RG-005·원칙 I)

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T094 [P] `specs/002-defect-fix-design-conformance/design-conformance/undefined-states.md` 의 기록 건수가 실제 결정 건수와 같은지 확인한다. 기록 없는 임의 결정이 있으면 그것은 DC-001 위반이다 (SC-110)
- [X] T095 [P] `backend/README.md` 와 루트 `README.md` 에 새 저장 위치(`~/.config/itb/`, `~/.local/share/itb/projects/`)를 적는다
- [X] T096 [P] `specs/001-interactive-ai-test-builder/tasks.md` 의 T155·T156 이 이 라운드로 영향받는지 확인하고 필요하면 메모를 남긴다 — 001 SC 측정은 이 라운드가 성립시키는 흐름에 달려 있다
- [X] T097 `backend/.venv/bin/` 의 stale `itb` 콘솔 스크립트를 정리하거나 `itb/cli.py` 를 만든다. `pyproject.toml` 이 `itb = "itb.cli:main"` 을 선언하는데 그 모듈이 없다 (plan 조사 중 발견)
- [X] T098 quickstart.md §1~§7 실행 — **자동 확인 가능한 절은 전부 통과**, 결과를 `design-conformance/smoke-results.md` 에 기록했다. 서버를 `/tmp` 에서 띄워 실행 경로가 무관함(DR-001)을 함께 확인했다. **사람이 화면을 조작해야 하는 항목(§2 녹화 흐름, §4 화면 이동 0회, §6 대조 판정)은 실행하지 못했고 그렇게 적어 두었다**

---

## ⚠️ 사람이 해야 하는 작업 (구현자가 대신할 수 없다)

- [ ] T099 [US6] **[리뷰어]** `design-conformance/<Screen>.md` 8개의 `판정` 칸을 채운다. 확정 디자인과 제품을 나란히 놓고 축 6개를 대조한다. **`불일치`·`미판정` 0건이어야 완료다** (DC-012·SC-108). 구현자가 자기 구현을 판정하면 대조가 아니라 자기 확인이다 — 001 T156 이 같은 이유로 미완으로 남아 있다

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
   └─▶ Phase 2 (Foundational) ──┬─▶ Phase 3 (US1) ─────────────┐
                                │                              │
                                ├─▶ Phase 4 (US6 전사) ─┬─▶ Phase 5 (US2)
                                │                       └─▶ Phase 6 (US3)
                                │                              │
                                └─▶ Phase 7 (US5) ─▶ Phase 8 (US4)
                                                               │
                                       Phase 9 (US7 회귀) ◀────┘
                                                    │
                                       Phase 10 (Polish)
                                                    │
                                       T099 (리뷰어)
```

### 강제 순서 — 이유가 있는 것만

| 앞 | 뒤 | 이유 |
|---|---|---|
| T005~T007 (전역 422) | Phase 7 (US5) | 키 쌍 결함의 대부분이 이 핸들러 부재였다 (research R3) |
| Phase 7 (US5) | Phase 8 (US4) | DR-028 이 DR-025 의 선행 조건. 키 생성이 막히면 인라인 입력의 탈출구가 없다 |
| T008~T009 (paths) | Phase 3 (US1) | 레지스트리와 관리 위치가 경로 결정에 의존한다 |
| T010~T012 (tokens) | Phase 4 (US6) | 8화면 전부의 기반 |
| Phase 4 (US6 전사) | Phase 5·6 (US2·US3) | **전사가 파일을 통째로 다시 쓴다.** 나중에 하면 앞선 동작 수정을 덮는다 |
| T032 (화면 분리) | T036·T038·T039 | 독립 화면이 될 자리가 먼저 있어야 한다 |

### 스토리 독립성

- **US1** — 다른 스토리에 의존하지 않는다. `ProjectSetup.tsx` 는 확정 디자인에 대응이 없어 US6 전사와 파일이 겹치지 않는다. **MVP 로 단독 배포 가능**
- **US6** — 백엔드와 독립. US1 과 병렬 가능
- **US2·US3** — US6 전사 이후. 서로는 독립
- **US5 → US4** — 위 표의 유일한 스토리 간 강제 순서
- **US7** — 전부 끝난 뒤 검증

### Parallel Opportunities

- **Phase 1**: T001·T003·T004 동시 (T002 는 T001 이후)
- **Phase 2**: 세 묶음이 서로 독립 — (T005~T007) · (T008~T009) · (T010~T012)
- **Phase 3**: 테스트 T013~T016 동시. 백엔드 T017~T024 와 프런트엔드 T025~T031 은 계약 확정 후 병렬
- **Phase 4**: **T034~T041 여덟 화면이 서로 다른 파일이라 전부 동시** — 이 라운드에서 병렬 이득이 가장 큰 지점
- **Phase 3(US1) 과 Phase 4(US6)** 는 통째로 병렬 가능 — 백엔드 중심과 프런트엔드 중심으로 갈린다

---

## Parallel Example: Phase 4 (US6 전사)

```
# 8화면을 동시에 전사한다. 서로 다른 파일이고 의존이 없다.
T034 TestList.tsx      ← docs/design/TestList.dc.html
T035 CreateTest.tsx    ← docs/design/CreateTest.dc.html
T036 AiRecord.tsx      ← docs/design/AiRecord.dc.html
T037 Runner.tsx        ← docs/design/Main.dc.html
T038 RunnerPaused.tsx  ← docs/design/RunnerPaused.dc.html
T039 Takeover.tsx      ← docs/design/Takeover.dc.html
T040 RunResult.tsx     ← docs/design/RunResult.dc.html
T041 StepInspector.tsx ← docs/design/StepInspector.dc.html
```

## Parallel Example: Phase 3 (US1) 테스트

```
T013 test_registry.py      T014 test_project_slug.py
T015 test_fs_browse_api.py T016 test_project_list_api.py
```

---

## Implementation Strategy

### MVP First (US1 단독)

Phase 1 → Phase 2 → Phase 3 만으로 **첫 화면이 뚫린다.** 사용자가 도구에 들어올 수
있게 되는 것이 단독으로 가치가 있다 — 지금은 여기서 막혀 나머지 전부에 도달하지 못한다.

### Incremental Delivery

| 증분 | 범위 | 사용자가 얻는 것 |
|---|---|---|
| 1 | Phase 1~3 (US1) | 프로젝트에 들어갈 수 있다 |
| 2 | Phase 4 (US6) | 화면이 합의된 물건이 된다 |
| 3 | Phase 5 (US2) | 녹화한 것을 잃지 않는다 |
| 4 | Phase 6 (US3) | AI 작성이 동작하거나, 최소한 왜 안 되는지 안다 |
| 5 | Phase 7~8 (US5·US4) | 비밀 값을 흐름 안에서 다룬다 |
| 6 | Phase 9~10 + T099 | 회귀 없음과 디자인 준수가 증명된다 |

### 병렬 팀 전략

Phase 2 완료 후 두 갈래로 나뉜다.

- **백엔드 갈래**: Phase 3 백엔드(T017~T024) → Phase 5 백엔드(T052~T056) → Phase 6 백엔드(T064~T065)
- **프런트엔드 갈래**: Phase 4 전사 8화면(T034~T041) → Phase 3 프런트엔드(T025~T031) → Phase 5·6 프런트엔드

---

## Notes

- **전사는 해석이 아니다.** dc.html 의 인라인 style 값을 손대지 않는다. 축약·토큰 치환·
  "더 나은" 간격으로 바꾸는 것 전부 DC-001 위반이다
- **미리 추상화하지 않는다** (T044). 이번 결함의 원인이 바로 추상화 층에서 일어난 재해석이다
- **테스트를 삭제·비활성화하지 않는다.** 문구 변경으로 인한 기대값 수정만 허용하고 각각에
  근거를 남긴다 (헌법 품질 게이트 4)
- **T099 는 구현자가 할 수 없다.** 리뷰어의 판정이 없으면 SC-108 이 미충족으로 남는다.
  이것을 구현자가 채우면 001 T156 과 같은 상태가 된다
- Export(헌법 원칙 V)는 이 라운드의 범위가 아니다. release-gate 항목으로 여전히 남아 있다

---

## Phase 11: Convergence

converge 1회차가 찾은 잔여 작업. 심각도 순.

- [X] T100 [US2] `frontend/src/pages/SessionScreen.tsx` 에서 `lost` 를 검토 화면으로 보낸다 — 브라우저가 유실돼도 이름을 붙여 저장할 수 있어야 한다 per DR-015·US2/AC7 (partial). 지금은 `lost` 가 `TERMINAL_STATES` 라 Main 화면으로 가고, 그 화면에는 저장 상자가 없다. `SessionLostBanner` 도 이름 입력이 없어 `onSave` 가 늘 `undefined` 다 — 배너는 "저장하거나" 라고 적어 두고 저장할 방법을 주지 않는다. `review` 와 같은 상황(브라우저 없음·Step 살아 있음)이므로 `RunnerPaused` 로 보내고, 배너는 사유만 알리게 한다
- [X] T101 200개 렌더 예산 가드를 **실제 렌더 경로로 옮긴다** per RG-001·plan(research R8) (contradicts). `frontend/tests/StepListPerformance.test.tsx` 와 `StepList.test.tsx` 18건이 `components/StepList.tsx` 를 재는데 어느 페이지도 그 모듈을 임포트하지 않는다. 실제 경로인 `components/design/DesignStepList.tsx` 의 `DesignStepRow` 에는 테스트가 0건이다. **테스트 수가 줄지 않아 RG-001 이 초록으로 보이지만 가드는 아무것도 지키지 않는다.** 예산 테스트를 `DesignStepRow` 기준으로 다시 쓰고, `StepList.test.tsx` 가 검증하던 동작(번호·표시 이름·동작 종류·식별 정보·일시정지 표식)도 실제 경로에서 확인한다. **기존 단언을 지우지 말고 옮긴다** (헌법 품질 게이트 4)
- [X] T102 `frontend/src/pages/RunnerPaused.tsx:467` 의 중복 `AssertionForm` 을 없애고 `components/AssertionForm.tsx` 를 쓴다 per DC-003 (unrequested). 기존 것은 테스트가 있고 `tab` 인자를 지원한다 — 전사하면서 같은 것을 두 번 쓴 것이라 한쪽만 고쳐지면 어긋난다
- [X] T103 `frontend/src/pages/TestDefinition.tsx` 를 나머지 DC-010 화면과 같은 시각 언어로 맞춘다 per DC-010 (partial). 이 화면만 `className="card"` 3곳에 3px 테두리가 0곳이다. `SecretValues`·`KeyManagement` 는 3px 로 맞췄다
- [X] T104 임포트되지 않는 옛 시각 언어 컴포넌트 6개를 제거하거나 남길 이유를 기록한다 per DC-001·DC-007 (unrequested): `components/AppHeader.tsx`·`PauseActions.tsx`·`AiProgress.tsx`·`EditWarningBanner.tsx`·`AiBlockedCard.tsx`·`StepList.tsx`. 전부 001 의 지어낸 시각 언어(1px 테두리·어두운 헤더)를 담고 있어, 남겨 두면 다음 편집에서 되살아날 수 있다. **T101 이 `StepList` 의 테스트를 실제 경로로 옮긴 뒤에 지운다** — 순서를 바꾸면 검증이 사라진다

---

## Phase 12: Convergence 2

converge 2회차. 1회차 5건은 전부 닫혔고 아래 1건이 남았다.

- [ ] T105 [US6] `frontend/src/pages/CreateTest.tsx` 와 `StepInspector` 겹침을 나머지 6화면처럼 `Artboard` 로 감싼다 per DC-011 (partial). 8화면 중 6개는 `overflowX: auto` + 기준 폭 컨테이너를 쓰는데 이 둘만 고정 폭을 맨몸으로 둔다. **`StepInspector` 가 특히 문제다** — `SessionScreen.tsx` 의 `position: fixed` 겹침 안에 있어 페이지 스크롤이 닿지 않는다. 창이 640px 보다 좁으면 잘린 채 접근할 수 없다. `CreateTest` 는 `width: 1000px; margin: 0 auto` 라 다른 화면과 동작이 갈린다. 임의 재배치를 하지 말고 기준 폭을 유지한 채 스크롤하게 한다
