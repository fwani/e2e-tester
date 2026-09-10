# Implementation Plan: 프로젝트 이름 변경과 삭제

**Branch**: `012-project-rename-delete` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-project-rename-delete/spec.md`

## Summary

프로젝트만 이름 변경과 삭제가 없다. 테스트에는 둘 다 있고 Step 에도 삭제가 있다.

**접근**: 새 구조를 만들지 않는다. 이 저장소에는 이 기능이 필요한 부품이 **이미 다 있다** —
원자적 쓰기(`storage/atomic.py`), 이름 충돌 회피(`allocate_workspace_path`), 경로 경계
판정(`_known_root_outside_home`), 살아 있는 세션 판정(`state_machine.is_active`), 인라인 이름
편집 관용어(`PhaseBar`). 012 는 그것들을 **잇는다.**

| 요구 | 무엇을 한다 | 새로 만드는 것 |
|---|---|---|
| 이름 변경 | 프로젝트 파일 `name` 쓰기 → 레지스트리 `name` 갱신 | 라우트 1개 · `registry.rename()` |
| 삭제 | 디렉터리를 `trash/` 로 이동 → 레지스트리에서 제거 | 라우트 1개 · `paths.trash_dir()` · 이동 함수 1개 |
| 구분 | 기존 「목록에서 치우기」는 손대지 않고 문구·자리만 가른다 | 없음 |
| 사유 표시 | 줄 상태(`accessible`×`origin`)가 조작을 정한다 | 없음 (기존 필드) |

**설계를 바꾼 세 발견** (research R1·R2·R6):

| 확인한 것 | 결과 | 이것이 없었으면 |
|---|---|---|
| 목록의 표시 이름을 **이미 디스크에서 읽는다** (`_name_from_disk`) | 레지스트리 갱신은 "접근 불가가 됐을 때 옛 이름이 되살아나는 것" 을 막는 보조다 | 레지스트리만 고쳐 다음 조회에 되돌아갔거나, 파일만 고쳐 FR-401 을 놓쳤다 |
| `registry.remember()` 가 `last_opened_at` 을 갱신한다 | 이름 변경 전용 `rename()` 이 필요하다 | 이름만 고쳤는데 프로젝트가 목록 맨 위로 올라와 "최근 연 순" 이 깨졌다 |
| 열린 프로젝트가 **하나뿐이다** (`AppState.repository`) | 세션에 프로젝트 식별자를 달지 않고 FR-417 을 판정할 수 있다 | 세션 ↔ 프로젝트 연결을 새로 만들고, 그것을 갱신하지 않는 경로에서 판정이 틀렸다 |

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript + React (frontend)

**Primary Dependencies**: FastAPI, React. **새 의존성 없음** — 이동은 표준 라이브러리
`shutil.move` 다 (research R4).

**Storage**: 파일. 변경은 `~/.local/share/itb/trash/` 디렉터리가 새로 생기는 것뿐이다
([data-model.md](data-model.md) §0). **Step DSL·테스트 정의·레지스트리 형식은 바뀌지 않는다.**

**Testing**: pytest (backend, 계층별 tier), vitest + Testing Library (frontend)

**Target Platform**: 로컬 실행. 이 기능은 브라우저를 열지 않는다 — 헤드리스 여부와 무관하다.

**Project Type**: web application (backend + frontend)

**Performance Goals**:
- **목록 조회를 무겁게 하지 않는다.** 저장된 테스트 수는 목록 응답에 싣지 않고 확인 단계에
  들어갈 때 그 프로젝트 하나만 센다 (ui-contract UC-012-03). `registry._probe` 가 "목록을
  그리려고 프로젝트 N개를 파싱하지 않는다" 를 지킨 것과 같은 이유다.
- 이름 변경은 파일 쓰기 1회 + 레지스트리 쓰기 1회.

**Constraints**:
- 삭제 대상은 **도구가 아는 프로젝트**로 제한한다 (FR-419). 임의 경로를 받아 디렉터리를
  옮기는 엔드포인트를 만들지 않는다 — 헌법 §보안.
- **파일이 먼저, 레지스트리가 나중.** 실패했을 때 "목록에서는 사라졌는데 자산은 원래 자리"
  가 나올 수 없어야 한다 (FR-402·FR-414 · research R5).
- 휴지통은 `workspace_dir()` 의 형제여야 한다. 스캔 제외 규칙을 새로 만들지 않는다 (FR-421).
- 새 CSS 클래스·새 오류 표시 부품을 만들지 않는다 (ui-contract 머리말).
- 오류 코드를 더하면 `CATEGORY`·`NEXT_ACTION` 대응표와 생성 스키마를 함께 갱신한다.

**Scale/Scope**: 요구사항 27건(FR-399~FR-425), 성공 기준 8건, 사용자 이야기 3개.
백엔드 신규 라우트 2개 · 수정 모듈 5개, 프런트 수정 파일 2개, 개정되는 기존 검사 5건
(research R10).

## Constitution Check

*GATE: Phase 0 전 통과. Phase 1 후 재확인 — 아래 「Phase 1 후 재확인」 참조.*

### I. Unified Step Model (NON-NEGOTIABLE) — 통과 (해당 없음)

**Step 을 읽지도 쓰지도 않는다.** 이 기능이 다루는 것은 프로젝트 디렉터리와 그 표시
이름이다. [data-model.md](data-model.md) §0 의 Step DSL 줄이 「없음」이다. 테스트 정의 파일은
**내용도 경로도** 바뀌지 않는다 (FR-400).

### II. Deterministic Replay (NON-NEGOTIABLE) — 통과 (해당 없음)

LLM 을 부르는 경로가 늘지 않는다. 두 라우트 모두 파일 시스템 조작이다.

### III. Stateful Interactive Runner — 통과

**세션을 끊지 않는다.**

- 이름 변경은 `AppState.repository` 도 세션도 건드리지 않는다 (FR-404 · api-contract §1).
- 삭제는 **살아 있는 세션이 있으면 거절한다** (FR-417). 거절 경로에서도 브라우저를 닫지
  않는다 — 거절은 요청을 받지 않은 것과 같아야 한다 (SC-621).
- 열린 프로젝트를 삭제한 경우에만 `repository` 를 비운다. 그 시점에 살아 있는 세션은 없다
  (없어야 통과했다).

### IV. Locator Resilience — 통과 (해당 없음)

Locator 를 다루지 않는다.

### V. Asset Portability — **이 기능의 근거 원칙**

**사용자 자산을 파괴하지 않는 것이 이 기능의 설계 전제다.**

- `tests/*.yaml` 은 "사용자가 버전 관리에 넣는 사람이 읽을 수 있는 평문" 이라는 원칙 V 의
  대상이다. 그래서 삭제가 `rmtree` 가 아니라 **이동**이다 (FR-409).
- 옮겨진 위치를 사용자에게 알린다 (FR-410) — 자산을 계속 쓸 수 있으려면 어디 있는지 알아야
  한다.
- 도구는 휴지통을 자동으로 비우지 않는다 (data-model §2). 도구가 사용자 자산을 예고 없이
  파괴하는 경로를 만들지 않는다.
- Export 미구현 상태는 이 기능이 바꾸지 않는다 (Incremental delivery 규칙 하에 유지).

### 보안 제약 — 통과

- **경로 경계**: `root` 는 관리 위치 아래이거나 레지스트리에 있어야 한다 (FR-419 · research
  R7). `open_project` 가 이미 쓰는 판정을 공유 함수로 끌어올려 세 라우트가 같은 것을 쓴다.
- **하드코딩된 비밀값 없음**: 이 기능은 비밀값을 읽지 않는다. `secrets.local.yaml` 은
  디렉터리와 함께 옮겨지며 내용을 열지 않는다.
- **오류 메시지에 내부 정보를 넣지 않는다**: 실패 사유는 사용자가 할 일(권한·공간)로
  표현한다. 스택·내부 경로를 노출하지 않는다 (data-model §4).

### Cross-language schema duty — **조치 필요**

`ErrorCode` 에 2개를 더하므로 `frontend/src/types/generated/error-response.d.ts` 를 다시
생성해야 한다. `python -m itb.schema.export --check` 가 어긋남을 잡는다. tasks 에 명시적
작업으로 넣는다.

### Phase 1 후 재확인 — 통과

설계 산출물([data-model.md](data-model.md) · [contracts/](contracts/))을 만든 뒤 다시 봤을 때
새로 걸리는 항목이 없다. 원칙 III 은 오히려 계약에 명시적으로 못 박혔다(api-contract §2
불변식). 원칙 V 는 응답 형태 자체에 드러난다 — `trashed_to` 를 돌려주지 않으면 204 로 끝낼
수 있었고, 그러면 자산을 되찾을 방법이 사라진다.

## Project Structure

### Documentation (this feature)

```text
specs/012-project-rename-delete/
├── plan.md              # 이 파일
├── research.md          # Phase 0 — R1~R10
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1 — 손 검증 6가지
├── contracts/
│   ├── api-contract.md  # 두 라우트 + 기존 라우트와의 구분
│   └── ui-contract.md   # UC-012-01 ~ UC-012-07
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks 가 만든다)
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── api/
│   │   ├── routes/project.py     # ★ PATCH /name · POST /trash 추가. 기존 라우트 불변
│   │   └── ...
│   ├── domain/error.py           # ★ ErrorCode 2개 + CATEGORY + NEXT_ACTION
│   └── storage/
│       ├── paths.py              # ★ trash_dir() · allocate_trash_path()
│       ├── registry.py           # ★ rename() · known_project_root()
│       └── repository.py         # ★ move_to_trash() (또는 storage/trash.py)
└── tests/
    ├── contract/
    │   ├── test_project_rename_api.py   # ★ 신규
    │   └── test_project_trash_api.py    # ★ 신규
    └── unit/
        ├── test_paths.py                # 개정 — trash_dir
        ├── test_registry.py             # 개정 — rename
        └── test_trash.py                # ★ 신규 — 충돌 회피·실패 시 원본 보존

frontend/
├── src/
│   ├── api/client.ts                    # ★ renameProject · trash
│   ├── pages/ProjectSetup.tsx           # ★ ProjectRow 에 인라인 편집 + 확인 상태
│   └── types/generated/error-response.d.ts  # ★ 재생성 (커밋 대상)
└── tests/
    ├── ProjectSetup.test.tsx            # 개정
    └── ProjectRowActions.test.tsx       # ★ 신규 — 줄 상태 × 조작 표
```

**Structure Decision**: 기존 web application 구조(backend + frontend)를 그대로 쓴다. 새
패키지·새 계층을 만들지 않는다. 휴지통 이동 로직의 자리만 선택지가 있었고
(`repository.py` 안 vs `storage/trash.py` 별도 모듈), **`storage/trash.py` 로 가른다** —
`ProjectRepository` 는 "열린 프로젝트 하나의 안쪽" 을 다루는 객체이고, 프로젝트 디렉터리
자체를 옮기는 일은 그 바깥이다. `paths.py`·`atomic.py` 와 같은 층이다.

## Complexity Tracking

> Constitution Check 에 위반이 없다. 이 표는 비워 둔다.

정당화가 필요한 복잡도 없음. 새 의존성 0개, 새 계층 0개, 새 도메인 모델 0개.
