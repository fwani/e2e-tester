# Implementation Plan: 테스트 목록의 복수 삭제와 테스트 그룹

**Branch**: `013-test-groups-bulk-delete` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-test-groups-bulk-delete/spec.md`

## Summary

둘 다 테스트가 늘어났을 때 드러나는 문제다 — 한 줄씩만 지운다, 묶을 방법이 없다.

**접근**: 011·012 가 만든 것을 잇는다. 복수 삭제의 화면 관용어는 011 이, 휴지통은 012 가
이미 갖고 있다. 새로 만드는 것은 **식별자 형식을 넓히는 일**과 **그룹이라는 개념** 둘뿐이다.

| 요구 | 무엇을 한다 | 새로 만드는 것 |
|---|---|---|
| 복수 삭제 | 체크 칸 + 선택 띠 + `POST /api/tests:delete` | 라우트 1개 · 확인 부품 1개 |
| 삭제 = 휴지통 | 012 의 `trash.py` 를 테스트에도 쓴다 | 이동 함수 1개 |
| 그룹 | `Project.groups` + 접두어가 곧 소속 | 모델 필드 1개 · 라우트 4개 |
| 그룹 이동 | 정의 파일과 산출물을 함께 옮긴다 | 라우트 1개 · 이동 함수 1개 |

**설계를 바꾼 네 발견** (research R1·R4·R6·R7):

| 확인한 것 | 결과 | 이것이 없었으면 |
|---|---|---|
| `list_test_paths()` 가 `glob("TC-*.yaml")` 이다 | 넓히지 않으면 **새 접두어 테스트가 목록에 아예 안 나온다** | 저장은 되는데 보이지 않는, 가장 찾기 어려운 결함이 남았다 |
| 삭제를 휴지통으로 바꾼 결정이 **되돌림을 가능하게 한다** | FR-432(전부 되거나 전부 안 되거나)를 파일 시스템에서 지킬 수 있다 — 실패 시 이미 옮긴 것을 되돌린다 | 영구 삭제라면 「셋 중 둘만 지워진 채 오류」가 **구조적으로 피할 수 없었다** |
| `trash.move_to_trash` 는 디렉터리 하나용인데 테스트는 파일 1 + 디렉터리 1 | 휴지통 항목 하나에 **원래 파일명 그대로** 묶는다 → 되돌리기가 한 걸음 | 되돌리려는 사람이 원래 파일 이름을 알아내야 했다 |
| `BulkDeleteConfirm` 이 `deleteManyConfirm(indices)` 로 **Step 번호 범위**를 말한다 | 재사용하지 않는다 — 테스트는 순서 없는 집합이라 「범위」가 없다. 관용어만 잇고 **이름**으로 말한다 | 가짜 인덱스를 만들어 넣어야 했고, 한쪽을 고치면 다른 쪽이 깨졌다 |

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript + React (frontend)

**Primary Dependencies**: FastAPI, React. **새 의존성 없음** — 이동은 표준 라이브러리다.

**Storage**: 파일. 변경은 `Project.groups` 필드 하나와 식별자 형식이 넓어지는 것뿐이다
([data-model.md](data-model.md) §0). **Step DSL 은 바뀌지 않는다.**

**Testing**: pytest (backend, 계층별 tier), vitest + Testing Library (frontend)

**Target Platform**: 로컬 실행. 이 기능은 브라우저를 열지 않는다 — 실행 중 판정만 세션을 본다.

**Project Type**: web application (backend + frontend)

**Performance Goals**:
- **목록 조회를 무겁게 하지 않는다.** 그룹 개수는 이미 읽은 테스트 목록에서 센다 — 프로젝트
  파일 한 번 + 테스트 파일들(이미 읽는다)이면 충분하고, 추가 입출력이 없다.
- 그룹 걸러 보기는 서버에서 한다(`group` 질의). 화면에서 거르면 개수와 목록이 갈릴 수 있다.

**Constraints**:
- **기존 자산을 건드리지 않는다.** `TC-###` 테스트는 파일 이름도 식별자도 바뀌지 않는다
  (FR-445 · SC-629). 업그레이드만으로 사용자의 git diff 는 0줄이어야 한다.
- **식별자는 대문자 ASCII 다.** 파일 이름이 되고, macOS 의 기본 파일 시스템은 대소문자를
  구별하지 않는다 (research R1).
- **전부 되거나 전부 안 되거나** — 먼저 전부 검증하고, 실패하면 이미 옮긴 것을 되돌린다
  (FR-432·FR-444b).
- **그룹 이동은 산출물이 먼저, 정의가 나중이다.** 반대로 하면 사용자에게 결과가 사라진 것으로
  보인다 (research R5).
- 새 CSS 클래스·새 오류 표시 부품을 만들지 않는다.
- 오류 코드를 더하면 `CATEGORY`·`NEXT_ACTION` 과 생성 스키마를 함께 갱신한다.

**Scale/Scope**: 요구사항 40건(FR-426~FR-451 + 하위), 성공 기준 12건, 사용자 이야기 3개.
백엔드 신규 라우트 6개 · 수정 모듈 5개, 프런트 수정 파일 3~4개, 개정되는 기존 검사 6건
(research R9).

## Constitution Check

*GATE: Phase 0 전 통과. Phase 1 후 재확인 — 아래 참조.*

### I. Unified Step Model (NON-NEGOTIABLE) — 통과 (해당 없음)

**Step 을 읽지도 쓰지도 않는다.** [data-model.md](data-model.md) §0 의 Step DSL 줄이
「없음」이다. 테스트 정의의 `steps` 는 그룹 이동에서도 그대로 옮겨진다 — 내용을 건드리지 않고
`id` 와 자리만 바꾼다.

### II. Deterministic Replay (NON-NEGOTIABLE) — 통과 (해당 없음)

LLM 을 부르는 경로가 늘지 않는다. 모두 파일 시스템 조작이다.

### III. Stateful Interactive Runner — 통과

**세션을 끊지 않는다.**

- 삭제·그룹 이동 모두 **살아 있는 세션이 있으면 거절한다** (FR-433). 거절 경로에서도
  브라우저를 닫지 않는다 — 거절은 요청을 받지 않은 것과 같아야 한다 (SC-630).
- 판정은 이미 있는 `SessionManager.active_session_for_test` 를 쓴다. 새 목록을 만들지 않는다.

### IV. Locator Resilience — 통과 (해당 없음)

Locator 를 다루지 않는다.

### V. Asset Portability — **이 기능의 근거 원칙**

**두 곳에서 걸린다. 둘 다 이 원칙이 설계를 정했다.**

1. **삭제를 파괴에서 이동으로 바꾼다.** `tests/*.yaml` 은 「사용자가 버전 관리에 넣는 사람이
   읽을 수 있는 평문」이라는 원칙 V 의 대상이다. 한 번에 여러 개가 사라지는 조작을 만들면서
   되돌릴 길을 두지 않는 것은 이 원칙을 거스른다.
2. **기존 자산을 도구가 먼저 움직이지 않는다** (FR-445). 그룹 기능을 붙였다고 사용자의
   `tests/TC-001-*.yaml` 을 말없이 개명하면, 사용자의 저장소에 대량 변경이 들어간다.
   사용자가 그룹으로 옮길 때만 바꾼다.

**형식은 여전히 평문 YAML 이고 스키마가 문서화된다.** `Project.groups` 는 사람이 읽고 손으로
고칠 수 있는 형태다. Export 미구현 상태는 이 기능이 바꾸지 않는다.

### 보안 제약 — 통과

- **접두어는 경계에서 검증한다** (FR-444e). 파일 이름과 디렉터리 이름이 되므로 경로
  구분자·상위 이동·제어 문자를 거절한다. 패턴이 `^[A-Z][A-Z0-9]{0,7}$` 이므로 그 문자들이
  애초에 들어올 수 없다 — **거절 목록이 아니라 허용 목록**이다.
- 식별자도 같은 방식이다. `find_test_path`·`run_dir` 의 기존 검증을 넓히되 **없애지 않는다.**
- 비밀값을 읽지 않는다. 오류 메시지에 내부 경로·스택을 넣지 않는다.

### Cross-language schema duty — **조치 필요**

`Project` 에 `groups` 가 생기고 `ErrorCode` 가 7개 는다. `backend/schema/*.json` 과
`frontend/src/types/generated/*.d.ts` 를 다시 생성해야 한다. **백엔드가 먼저다** — 012 에서
순서를 틀려 한 번 헛돌았다. tasks 에 명시적 작업으로 넣는다.

### Phase 1 후 재확인 — 통과

설계 산출물을 만든 뒤 다시 봤을 때 새로 걸리는 항목이 없다. 원칙 V 는 오히려 계약에 못
박혔다 — `DELETE /api/tests/{id}` 가 **204 를 버리고 200 에 `trashed_to` 를 싣는 것**이 그
표현이다. 위치를 돌려주지 않으면 되돌릴 수 없고, 그러면 「파괴하지 않는다」가 사용자에게는
삭제와 구별되지 않는다.

## Project Structure

### Documentation (this feature)

```text
specs/013-test-groups-bulk-delete/
├── plan.md              # 이 파일
├── research.md          # Phase 0 — R1~R9
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1 — 손 검증 7가지
├── contracts/
│   ├── api-contract.md  # 라우트 6개 + 의미가 바뀌는 1개
│   └── ui-contract.md   # UC-013-01 ~ UC-013-08
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks 가 만든다)
```

### Source Code (repository root)

```text
backend/
├── src/itb/
│   ├── domain/
│   │   ├── test_case.py          # ★ TEST_ID_PATTERN 확장 · Project.groups · TestGroup
│   │   └── error.py              # ★ ErrorCode 7개 + CATEGORY + NEXT_ACTION
│   ├── storage/
│   │   ├── repository.py         # ★ TEST_ID_RE · list_test_paths · allocate_test_id
│   │   ├── trash.py              # ★ move_test_to_trash() · restore_from_trash()
│   │   └── test_moves.py         # ★ 신규 — 그룹 이동과 복수 삭제의 순서·되돌림
│   └── api/routes/
│       ├── tests.py              # ★ group 질의 · :delete · :move · 삭제 응답 변경
│       └── groups.py             # ★ 신규 — 그룹 4개 라우트
└── tests/
    ├── contract/
    │   ├── test_tests_bulk_delete_api.py  # ★ 신규
    │   ├── test_test_groups_api.py        # ★ 신규
    │   └── test_project_and_tests_api.py  # 개정
    └── unit/
        ├── test_repository.py             # 개정 — 식별자·목록·번호
        ├── test_domain_invariants.py      # 개정 — 패턴
        ├── test_test_moves.py             # ★ 신규 — 원자성·되돌림·순서
        └── test_trash.py                  # 개정 — 테스트 항목

frontend/
├── src/
│   ├── api/client.ts                 # ★ tests.deleteMany · tests.move · groups.*
│   ├── pages/TestList.tsx            # ★ 체크 칸 · 선택 띠 · 그룹 띠 · 확인 · 완료 표시
│   ├── components/TestBulkConfirm.tsx  # ★ 신규 (BulkDeleteConfirm 재사용 불가 · research R7)
│   ├── lib/wording.ts                # ★ 테스트용 복수 삭제 문구
│   └── types/generated/*.d.ts        # ★ 재생성 (커밋 대상)
└── tests/
    ├── TestListSelection.test.tsx    # ★ 신규 — 선택·걸러 보기·확인
    └── TestGroups.test.tsx           # ★ 신규 — 묶어 보기·걸러 보기·그룹 조작
```

**Structure Decision**: 기존 web application 구조를 그대로 쓴다. 새 패키지·새 계층 없음.

두 곳만 판단이 필요했다.

1. **그룹 라우트를 `tests.py` 에 넣지 않고 `groups.py` 로 가른다.** `tests.py` 는 이미 800줄이
   넘고, 그룹은 테스트가 아니라 **프로젝트 설정**이다 (`Project` 에 산다). 같은 파일에 두면
   「테스트 라우트」라는 그 파일의 뜻이 흐려진다.
2. **이동·삭제의 순서 규약을 `storage/test_moves.py` 로 가른다.** 그 규약(전부 검증 → 하나씩 →
   실패 시 되돌림)은 **삭제와 그룹 이동이 공유한다.** 라우트에 두면 두 벌이 되고, 한쪽만
   고치면 다른 쪽에서 되돌림이 빠진다. `ProjectRepository` 에 넣지 않는 이유는 012 와 같다 —
   그 객체는 「열린 프로젝트 하나의 안쪽」을 다루고, 여러 자산을 옮기며 되돌리는 일은 그
   바깥의 조율이다.

## Complexity Tracking

> Constitution Check 에 위반이 없다.

정당화가 필요한 복잡도 없음. 새 의존성 0개, 새 계층 0개.

**다만 한 가지를 기록해 둔다** — 이 기능은 **식별자 형식을 바꾼다.** 그것은 도메인 모델·저장소·
라우트·화면·기존 자산에 모두 걸쳐 있는, 이 저장소에서 지금까지 한 변경 중 가장 넓은 종류다.
`tasks.md` 는 그 확장을 **가장 먼저, 기존 자산이 그대로 읽히는지 확인하면서** 하도록 배치해야
한다 (quickstart 이야기 1 이 그 확인이다).
