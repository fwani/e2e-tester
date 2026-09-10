---

description: "012 프로젝트 이름 변경과 삭제 — 실행 작업 목록"
---

# Tasks: 프로젝트 이름 변경과 삭제

**Input**: Design documents from `specs/012-project-rename-delete/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) ·
[data-model.md](data-model.md) · [contracts/](contracts/) · [quickstart.md](quickstart.md)

**Tests**: 포함한다. 이 저장소는 계약 테스트(`backend/tests/contract/`)와 단위
테스트(`backend/tests/unit/`), 화면 테스트(`frontend/tests/`)를 기존 관행으로 갖는다.
**되돌릴 수 없는 실패 모드(자산 유실)를 다루는 기능이므로 실패 경로 검사가 특히 중요하다.**

**Organization**: 사용자 이야기별로 묶는다. US1(이름 변경)만 구현해도 독립적으로 쓸 수 있다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 미완료 작업에 의존하지 않음)
- **[Story]**: US1 = 이름 변경 · US2 = 삭제 · US3 = 두 조작 구분

## Path Conventions

Web app 구조다. 백엔드는 `backend/src/itb/`, 프런트엔드는 `frontend/src/`.

---

## Phase 1: Setup (기준선 확인)

**Purpose**: 시작 전 기준선을 고정한다. 새 의존성·새 패키지를 만들지 않으므로 초기화 작업이 없다.

- [X] T001 기준선 검증을 돌려 **012 이전이 초록인지** 기록한다 — `cd backend && uv run ruff check src/ tests/ && uv run lint-imports && uv run python -m itb.schema.export --check && uv run pytest -m "not browser" -q`, `cd frontend && npx tsc --noEmit && npx vitest run`. 여기서 이미 실패하는 항목이 있으면 012 가 깬 것과 구분할 수 없다
- [X] T002 [P] `backend/src/itb/storage/paths.py`·`registry.py`·`api/routes/project.py` 와 `frontend/src/pages/ProjectSetup.tsx` 를 읽고, [research.md](research.md) R1·R2·R6 의 세 발견이 지금 코드에서 실제로 그러한지 확인한다 — 다르면 설계를 먼저 고친다

---

## Phase 2: Foundational (두 이야기의 공통 전제)

**Purpose**: US1·US2 **양쪽이 쓰는 것**들이다. 이 단계가 끝나기 전에는 어느 이야기도 시작할 수 없다.

**⚠️ 반드시 먼저 끝나야 한다**

- [X] T003 [P] `backend/src/itb/storage/paths.py` 에 `trash_dir()` 을 더한다 — `data_dir() / "trash"`. `XDG_DATA_HOME` 을 존중하는 기존 규약을 그대로 따르고, **`workspace_dir()` 의 형제**여야 한다 ([data-model.md](data-model.md) §2 · FR-421)
- [X] T004 `backend/src/itb/storage/paths.py` 에 `allocate_trash_path(root, when=None)` 을 더한다 — `<trash_dir>/<YYYYMMDD-HHMMSS>-<root.name>`, 겹치면 `-2`·`-3`. **`allocate_workspace_path` 와 같은 회피 규칙**을 쓴다 (FR-415). T003 에 의존
- [X] T005 [P] `backend/tests/unit/test_paths.py` 를 개정한다 — `trash_dir()` 이 `XDG_DATA_HOME` 을 따르는지, `workspace_dir()` 의 **하위가 아닌지**(FR-421), `allocate_trash_path` 가 같은 초에 두 번 불려도 서로 다른 경로를 주는지 (FR-415)
- [X] T006 [P] `backend/src/itb/storage/registry.py` 에 `known_project_root(raw) -> pathlib.Path | None` 을 더한다 — 관리 위치 아래이거나 레지스트리에 있는 경로만 돌려준다. `api/routes/project.py` 의 `_known_root_outside_home()` 논리를 여기로 끌어올린 것이다 (FR-419 · [research.md](research.md) R7)
- [X] T007 `backend/src/itb/api/routes/project.py` 의 `_known_root_outside_home()` 이 T006 의 함수를 쓰도록 고친다 — 두 벌이 남으면 한쪽이 갈린다. `open_project` 의 기존 동작은 바뀌지 않아야 한다. T006 에 의존
- [X] T008 [P] `backend/src/itb/domain/error.py` 에 `ErrorCode.PROJECT_IN_USE`·`PROJECT_DELETE_FAILED` 를 더하고 **`CATEGORY` 와 `NEXT_ACTION` 대응표 양쪽에 넣는다** — 빠지면 `error_payload()` 가 `KeyError` 로 죽어 오류 응답 자체가 깨진다 ([data-model.md](data-model.md) §4 · [research.md](research.md) R9)
- [X] T009 `cd frontend && npm run gen:types` 로 `frontend/src/types/generated/error-response.d.ts` 를 다시 만들고 커밋 대상에 넣는다 — 헌법 Cross-language schema duty. `uv run python -m itb.schema.export --check` 가 통과해야 한다. T008 에 의존
- [X] T010 [P] `backend/tests/unit/test_domain_invariants.py` 에 **모든 `ErrorCode` 가 `CATEGORY`·`NEXT_ACTION` 양쪽에 있는지** 세는 검사가 있는지 확인하고, 없으면 더한다 — 이 구멍은 코드가 늘 때마다 다시 열린다

**Checkpoint**: Foundation 완료. US1 과 US2 를 병렬로 진행할 수 있다.

---

## Phase 3: User Story 1 — 프로젝트 이름을 그 자리에서 고친다 (Priority: P1) 🎯 MVP

**Goal**: 목록의 줄에서 이름을 인라인으로 고치면 프로젝트 파일과 레지스트리 양쪽에 남는다.

**Independent Test**: 프로젝트를 만들고 목록에서 이름을 고친 뒤 서버를 다시 시작해도 새 이름이
남아 있다 ([quickstart.md](quickstart.md) §2 이야기 1·2).

### 백엔드

- [X] T011 [P] [US1] `backend/src/itb/storage/registry.py` 에 `rename(root, name, path=None) -> bool` 을 더한다 — 기존 항목의 `name` 만 바꾸고 **`last_opened_at`·`origin` 은 그대로 둔다** ([research.md](research.md) R2). 항목이 없으면 `False`. 형식을 읽지 못했으면 쓰지 않는다 (`remember()` 와 같은 규칙)
- [X] T012 [P] [US1] `backend/tests/unit/test_registry.py` 를 개정한다 — `rename()` 이 `last_opened_at` 을 **바꾸지 않는지**, 없는 항목에 `False` 를 주는지, 알 수 없는 형식의 파일을 덮어쓰지 않는지
- [X] T013 [US1] `backend/src/itb/api/routes/project.py` 에 `PATCH /api/project/name` 을 더한다 — 요청 `{root, name}`, 응답은 갱신된 `ProjectListItem`. `name` 은 `strip_whitespace=True, min_length=1, max_length=100` (생성과 동일). 순서: `known_project_root` → `read_project` → 이름이 같으면 쓰지 않고 반환(FR-407) → `write_project` → `registry.rename` ([contracts/api-contract.md](contracts/api-contract.md) §1). T006·T011 에 의존
- [X] T014 [US1] T013 의 오류 대응을 붙인다 — 모르는 경로 `INVALID_PATH`(400), 프로젝트 없음 `PROJECT_NOT_FOUND`(404), 깨진 정의 `DEFINITION_INVALID`(400), 쓰기 실패 `STORAGE_WRITE_FAILED`(500). **`write_project` 가 실패하면 `registry.rename` 을 부르지 않는다** (FR-402)
- [X] T015 [P] [US1] `backend/tests/contract/test_project_rename_api.py` 를 만든다 — 성공 응답 형태, **`last_opened_at` 불변**, 빈 이름·공백뿐인 이름 422, 모르는 경로 400, 같은 이름 재요청 시 파일 mtime 불변(FR-407), 열린 프로젝트 이름 변경 후 `GET /api/project` 가 새 이름을 주는지(FR-405)
- [X] T016 [P] [US1] `backend/tests/contract/test_project_rename_api.py` 에 **파일 쓰기 실패 시 레지스트리가 그대로인지** 검사를 더한다 (FR-402) — 프로젝트 파일을 읽기 전용으로 만들어 확인

### 프런트엔드

- [X] T017 [P] [US1] `frontend/src/api/client.ts` 에 `project.renameProject(root, name): Promise<ProjectListItem>` 을 더한다 — `PATCH /api/project/name`. 기존 `project.forget` 의 이름과 동작은 건드리지 않는다 ([contracts/api-contract.md](contracts/api-contract.md) §4)
- [X] T018 [US1] `frontend/src/pages/ProjectSetup.tsx` 의 `ProjectRow` 에 인라인 이름 편집을 더한다 — 평상/편집/확정/취소/거절 다섯 상태, `Enter` 확정 · `Esc` 취소 · 포커스 이탈 확정, 요청 중 입력 잠금, 빈 이름은 요청 전에 막는다 ([contracts/ui-contract.md](contracts/ui-contract.md) UC-012-02). 관용어는 `frontend/src/components/workbench/PhaseBar.tsx` 의 테스트 이름 편집을 따른다
- [X] T019 [US1] T018 의 성공 처리를 **그 줄만 갈아 끼우게** 한다 — 목록 전체를 다시 불러오면 편집 중이던 다른 줄의 상태가 날아간다 (UC-012-02)
- [X] T020 [US1] `accessible === false` 인 줄에는 이름 편집을 제공하지 않고 **왜 지금 할 수 없는지** 한 줄을 표시한다 (FR-406 · [data-model.md](data-model.md) §3)
- [X] T021 [P] [US1] `frontend/tests/ProjectSetup.test.tsx` 에 US1 검사를 더한다 — 확인 창 없이 두 조작으로 끝나는지(SC-614), 빈 이름이 요청을 만들지 않는지, `Esc` 가 원래 이름으로 되돌리는지, 접근 불가 줄에 편집이 없는지

**Checkpoint**: US1 단독으로 배포 가능. 삭제 없이도 사용자에게 가치가 있다.

---

## Phase 4: User Story 2 — 프로젝트를 삭제하면 휴지통으로 간다 (Priority: P1)

**Goal**: 확인 단계를 거쳐 프로젝트 디렉터리를 휴지통으로 옮기고, 옮겨진 위치를 알린다.

**Independent Test**: 테스트를 저장한 프로젝트를 삭제하고, 화면이 알려 준 위치에 자산이
온전한지, 원래 자리로 되돌리면 목록에 다시 나타나는지 확인한다
([quickstart.md](quickstart.md) §2 이야기 3·4·5).

### 백엔드 — 이동

- [X] T022 [P] [US2] `backend/src/itb/storage/trash.py` 를 만든다 — `move_to_trash(root) -> pathlib.Path | None`. `shutil.move` 로 옮기고(다른 볼륨 대응 · [research.md](research.md) R4), 목적지 부모를 먼저 만들고, **실패하면 목적지의 부분 결과를 치운 뒤 원래 예외를 그대로 올린다**. 대상이 이미 없으면 `None` (FR-420). `ProjectRepository` 에 넣지 않는 이유는 [plan.md](plan.md) Structure Decision 에 있다. T004 에 의존
- [X] T023 [P] [US2] `backend/tests/unit/test_trash.py` 를 만든다 — 디렉터리 통째 이동(내용 동일), 같은 이름 두 번 삭제 시 **덮어쓰지 않음**(FR-415·SC-619), 대상이 없으면 `None`(FR-420), 이동 실패 시 **원본이 그대로 남는지**(FR-414), 실패 후 목적지에 부분 결과가 남지 않는지
- [X] T024 [P] [US2] `backend/tests/unit/test_trash.py` 에 **휴지통이 목록 스캔에 걸리지 않는지** 검사를 더한다 — 삭제 후 `registry.list_projects()` 에 그 항목이 없어야 한다 (FR-421 · SC 회귀)

### 백엔드 — 라우트

- [X] T025 [US2] `backend/src/itb/api/routes/project.py` 에 `POST /api/project/trash` 를 더한다 — 요청 `{root}`, 응답 `{root, name, trashed_to, was_open}` 200. 순서: `known_project_root` → 세션 검사 → `move_to_trash` → `registry.forget` → 열려 있었으면 `state.repository = None` ([contracts/api-contract.md](contracts/api-contract.md) §2). T006·T022 에 의존
- [X] T026 [US2] T025 의 세션 검사를 붙인다 — 대상이 **현재 열린 프로젝트이면서** `state.sessions.all_sessions()` 중 `state_machine.is_active(...)` 인 것이 있으면 409 `PROJECT_IN_USE`. 새 상태 목록을 만들지 않고 기존 `ACTIVE_STATES` 판정을 쓴다 (FR-417 · [research.md](research.md) R6)
- [X] T027 [US2] T025 의 실패 대응을 붙인다 — 이동 실패는 500 `PROJECT_DELETE_FAILED`, **그 경로에서 `registry.forget` 을 부르지 않는다** (FR-414). 메시지에 내부 스택·경로를 넣지 않는다
- [X] T028 [P] [US2] `backend/tests/contract/test_project_trash_api.py` 를 만든다 — 성공 응답에 `trashed_to` 가 있고 그 자리에 자산이 온전한지(FR-410·SC-616), 목록에서 사라지는지(FR-413), 이미 없는 디렉터리는 `trashed_to: null` 로 성공하는지(FR-420), 모르는 경로 400(FR-419)
- [X] T029 [P] [US2] `backend/tests/contract/test_project_trash_api.py` 에 거절·실패 검사를 더한다 — 살아 있는 세션이 있으면 409 이고 **세션이 그대로 살아 있는지**(FR-417·SC-621), 이동 실패 시 500 이고 **목록에 그대로 남아 있는지**(FR-414·SC-618), 열린 프로젝트를 지우면 `was_open: true` 이고 `GET /api/project` 가 `PROJECT_NOT_OPEN` 을 주는지(FR-416)

### 백엔드 — 확인 단계에 쓸 테스트 수

- [X] T030 [P] [US2] 확인 단계가 보여줄 **저장된 테스트 수**를 얻는 길을 정한다 — 목록 응답에 싣지 않는다 ([plan.md](plan.md) Performance Goals). 기존 `GET /api/tests` 는 열린 프로젝트만 대상이므로 쓸 수 없다. `POST /api/project/trash` 와 같은 파일에 **조회 전용** 경로를 두거나(예: `GET /api/project/summary?root=...`), 확인 단계에서 수를 생략하고 경로·이름만 보이게 한다 — 어느 쪽이든 [contracts/ui-contract.md](contracts/ui-contract.md) UC-012-03 을 그에 맞게 고친다

### 프런트엔드

- [X] T031 [P] [US2] `frontend/src/api/client.ts` 에 `project.trash(root)` 와 응답 타입 `TrashProjectResponse` 를 더한다. **`delete` 라는 이름을 쓰지 않는다** — 어느 쪽이 `forget` 인지 헷갈리는 순간 화면이 잘못된 쪽을 부른다 (api-contract §4)
- [X] T032 [US2] `frontend/src/pages/ProjectSetup.tsx` 의 `ProjectRow` 에 **줄 안 확인 상태**를 더한다 — 모달을 새로 만들지 않는다. 이름·경로·(T030 의 결정에 따라) 테스트 수·「휴지통으로 옮깁니다 · 되돌릴 수 있습니다」·「휴지통으로 옮기기」/「취소」, 포커스는 취소에 (UC-012-03)
- [X] T033 [US2] **확인 전에는 어떤 요청도 보내지 않는다** (FR-412 · SC-617). 취소하면 줄이 평상 상태로 돌아가고 목록이 그대로다
- [X] T034 [US2] 완료 표시를 더한다 — 목록 위에 옮겨진 위치를 `mono` 로 잘리지 않게 표시하고, 되돌리는 방법 한 줄을 붙인다. **자동으로 사라지지 않는다** (FR-410·FR-425 · UC-012-04). `trashed_to` 가 `null` 이면 「목록에서 뺐습니다」로 문구가 바뀐다
- [X] T035 [US2] `was_open === true` 면 열린 프로젝트 상태를 비운다 — `frontend/src/App.tsx` 의 `opened` 를 `null` 로 만들고 사용자는 선택 화면에 남는다. 「돌아가기」가 사라진다 (FR-416 · UC-012-05). `App.tsx` 와 `ProjectSetup.tsx` 사이의 콜백이 필요하다
- [X] T036 [US2] 거절·실패 사유를 그 줄에 표시한다 — 기존 `ErrorNotice` 를 쓴다. `PROJECT_DELETE_FAILED` 문구에 **「프로젝트는 그대로 있습니다」가 반드시 들어간다** (UC-012-06). 400/404 는 목록을 다시 불러온다
- [X] T037 [P] [US2] `frontend/tests/ProjectSetup.test.tsx` 에 US2 검사를 더한다 — 확인 전 요청 0건(SC-617), 취소가 아무것도 바꾸지 않음, 완료 표시에 `trashed_to` 가 그대로 나오는지, 409 사유가 그 줄에 붙는지, 500 문구에 「그대로 있습니다」가 있는지

**Checkpoint**: US1 + US2 로 명세의 P1 이 모두 선다.

---

## Phase 5: User Story 3 — 삭제와 목록 정리를 헷갈리지 않는다 (Priority: P2)

**Goal**: 한 줄의 두 조작이 서로 다른 이름과 설명을 갖고, 줄의 상태가 조작 집합을 정한다.

**Independent Test**: 관리/외부/접근 불가 세 종류의 줄에 어떤 조작이 있는지, 각 설명이 디스크의
파일이 어떻게 되는지 말하는지 확인한다 ([quickstart.md](quickstart.md) §2 이야기 6).

- [X] T038 [US3] `frontend/src/pages/ProjectSetup.tsx` 의 `ProjectRow` 가 **`accessible` × `origin` 표**로 조작 집합을 고르게 한다 — 줄마다 따로 판단하는 코드를 남기지 않는다 ([data-model.md](data-model.md) §3 · UC-012-01)
- [X] T039 [US3] 두 조작의 라벨과 설명을 확정한다 — 「삭제」는 「프로젝트 폴더를 휴지통으로 옮깁니다. 파일은 지워지지 않고 되돌릴 수 있습니다.」, 「목록에서 치우기」는 기존 문구 유지. **둘 다 디스크의 파일이 어떻게 되는지 말한다** (FR-422·FR-423 · UC-012-07)
- [X] T040 [US3] `origin === "external"` 인 줄의 확인 단계에 「도구 바깥에서 만든 위치입니다」를 표시한다 (FR-424 · UC-012-03)
- [X] T041 [US3] `accessible === false` 인 줄에서 삭제를 **제공하지 않고** 「목록에서 치우기」만 남긴다 (FR-418). 기존 동작이므로 회귀시키지 않는 것이 요점이다
- [X] T042 [P] [US3] `frontend/tests/ProjectRowActions.test.tsx` 를 만든다 — [data-model.md](data-model.md) §3 의 표를 그대로 검사로 옮긴다. 세 줄 상태 × 네 조작의 유무, 두 설명의 문구, external 확인 문구

---

## Phase 6: Polish & Cross-Cutting

- [X] T043 [P] `backend/tests/contract/test_project_and_tests_api.py` — **개정할 것이 없었다.** 이 파일은 라우트 목록을 세지 않고 개별 라우트의 동작만 본다. 라우트가 늘어도 걸리지 않는다 (research R10 의 예측이 빗나간 항목)
- [X] T044 [P] `backend/tests/contract/test_project_list_api.py` 에 **삭제된 프로젝트가 목록에 다시 나타나지 않는지** 회귀 검사를 더한다 (FR-421)
- [X] T045 [P] `docs/` 의 사용자 문서에 두 조작을 적는다 — 특히 **휴지통 위치와 되돌리는 방법**. 도구 안에 복구 화면이 없으므로 문서가 유일한 안내다
- [X] T046 [P] `README.md` 또는 `docs/DEVELOPMENT.md` 에 `~/.local/share/itb/trash/` 가 생긴다는 사실을 적는다 — 디스크를 차지하고 도구가 비우지 않는다
- [X] T047 전체 검증을 돌린다 — `cd backend && uv run ruff check src/ tests/ && uv run lint-imports && uv run python -m itb.schema.export --check && uv run pytest -q`, `cd frontend && npx tsc --noEmit && npx vitest run`. T001 의 기준선과 비교해 **012 가 깬 것이 없는지** 확인한다
- [ ] T048 손 검증을 돌린다 (**사람이 판정한다** · [docs/PENDING-HUMAN-VERIFICATION.md](../../docs/PENDING-HUMAN-VERIFICATION.md) §12 에 등록했다) — [quickstart.md](quickstart.md) §2 의 여섯 이야기와 §3 의 회귀 5건. `XDG_DATA_HOME`·`XDG_CONFIG_HOME` 을 임시 디렉터리로 지정해 실제 자산을 건드리지 않는다

---

## Dependencies & Execution Order

```
Phase 1 (T001~T002)
      ↓
Phase 2 (T003~T010)  ← 반드시 먼저. 두 이야기가 모두 쓴다
      ↓
   ┌──┴──────────────┐
Phase 3 (US1)     Phase 4 (US2)     ← 서로 독립. 병렬 가능
 T011~T021         T022~T037
   └──┬──────────────┘
      ↓
Phase 5 (US3, T038~T042)  ← US1·US2 의 화면이 있어야 구분할 대상이 생긴다
      ↓
Phase 6 (T043~T048)
```

**이야기 간 의존**

| 이야기 | 선행 | 이유 |
|---|---|---|
| US1 | Phase 2 | `known_project_root`(T006), 오류 코드 아님 — US1 은 기존 코드만 쓴다 |
| US2 | Phase 2 | `trash_dir`·`allocate_trash_path`(T003·T004), 오류 코드(T008·T009), `known_project_root`(T006) |
| US3 | US1 · US2 | 구분할 두 조작이 화면에 있어야 한다 |

**Phase 2 안의 의존**: T003 → T004, T006 → T007, T008 → T009. 나머지는 `[P]`.

## Parallel Execution Examples

**Phase 2** — 세 갈래가 서로 다른 파일이다:

```
T003 (paths.py) ∥ T006 (registry.py) ∥ T008 (domain/error.py)
그 뒤: T004 ← T003 · T007 ← T006 · T009 ← T008 · T005·T010 은 언제든
```

**Phase 3 ∥ Phase 4** — 겹치는 파일은 `api/routes/project.py`(T013·T025)와
`pages/ProjectSetup.tsx`(T018·T032), `api/client.ts`(T017·T031) 셋뿐이다. 이 셋은 **직렬로**
하고 나머지는 병렬로 한다.

**검사 작업**: T005·T010·T012·T015·T016·T023·T024·T028·T029·T037·T042·T043·T044 는 각자
다른 파일이라 모두 `[P]` 다.

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3 (US1).** 이름 변경만으로도 단독 가치가 있고, 되돌릴 수
있는 조작이라 위험이 가장 낮다.

**증분 2 = Phase 4 (US2).** 여기서 명세의 P1 이 모두 선다.

**증분 3 = Phase 5 + 6.** 문구·표·문서를 맞춘다.

**중간에 멈춰도 되는 지점**: Phase 3 끝, Phase 4 끝. 각 지점에서 검증이 초록이어야 한다.

## 이 기능에서 특히 조심할 것

1. **순서를 뒤집지 않는다** — 파일이 먼저, 레지스트리가 나중. 뒤집으면 목록에서는 사라졌는데
   자산은 원래 자리에 남는다 (T014·T027 · SC-618).
2. **`registry.remember()` 를 이름 변경에 쓰지 않는다** — 목록 순서가 흔들린다 (T011).
3. **오류 코드를 더하면 표 두 개와 생성 스키마를 함께 고친다** (T008·T009·T010).
4. **휴지통을 `projects/` 안에 두지 않는다** — 스캔 제외 규칙이 새로 필요해지고, 빠뜨린
   경로에서 삭제한 프로젝트가 목록에 돌아온다 (T003).
5. **확인 전에 요청을 보내지 않는다** (T033 · SC-617).

---

## Phase 7: Convergence (1회차)

- [X] T049 이름 변경이 **열린 프로젝트**를 대상으로 했을 때 `App` 의 `opened` 를 갱신한다 per FR-405 · SC-615 (partial) — `frontend/src/App.tsx:387` 이 `opened.name` 을 `TestList` 의 프로젝트 표시로 넘긴다. 목록 화면에서 열린 프로젝트의 이름을 고치고 「돌아가기」로 돌아가면 **옛 이름**이 보인다. 서버는 이미 맞다(`GET /api/project` 가 파일을 다시 읽는다) — 낡은 것은 화면이 들고 있는 사본이다. `ProjectSetup` 이 이름 변경 결과를 위로 올리고(`onProjectRenamed`), `App` 이 대상이 `opened.root` 와 같을 때만 `opened` 의 `name` 을 갈아 끼운다. `frontend/tests/ProjectRowActions.test.tsx` 에 검사를 더한다

---

## Phase 8: Convergence (2회차)

- [X] T050 완료 표시에 **원래 경로**를 함께 남긴다 per SC-616 · FR-425 (partial) — `frontend/src/pages/ProjectSetup.tsx` 의 `TrashedNotice` 가 `trashed_to` 만 그린다. 되돌리기는 **출발지와 도착지 둘 다** 있어야 하는데 「원래 자리로 옮기세요」의 "원래 자리" 가 화면에 없다. 관리 위치 프로젝트라면 짐작할 수 있지만 **외부 위치 프로젝트는 추측이 불가능하다** — 사용자가 직접 고른 경로이기 때문이다. `result.root` 가 응답에 이미 있으므로 그리기만 하면 된다. `frontend/tests/ProjectRowActions.test.tsx` 에 검사를 더한다
